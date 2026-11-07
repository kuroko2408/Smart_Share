"""Credential-free OSRM public routing adapter for hackathon demonstration use."""

from __future__ import annotations

import asyncio
import logging
import time
from urllib.parse import quote

import httpx

from app.routing.base import (
    DistanceMetric,
    DistanceSource,
    MultiWaypointRoute,
    RouteLeg,
    RoutingCapability,
    RoutingMatrixResult,
    RoutingProvider,
    SegmentResult,
)

logger = logging.getLogger(__name__)
DEFAULT_OSRM_BASE_URL = "https://router.project-osrm.org"
OSRM_NOTICE = (
    "Road-network route and duration from OSRM/OpenStreetMap; "
    "estimates use the provider's fastest-route profile and are not live traffic predictions. "
    "Distance is normalized along the road network."
)

# The public OSRM demo service asks users to keep request rates below 1 request/s.
_request_lock = asyncio.Lock()
_last_request_at = 0.0


class OSRMRoutingProvider(RoutingProvider):
    def __init__(
        self,
        *,
        base_url: str = DEFAULT_OSRM_BASE_URL,
        timeout_seconds: float = 5.0,
        request_interval_seconds: float = 1.05,
        max_routed_candidates: int = 3,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = max(0.1, timeout_seconds)
        self._request_interval_seconds = max(1.0, request_interval_seconds)
        self.max_routed_candidates = max(1, max_routed_candidates)
        self._routing_notice = OSRM_NOTICE

    @property
    def capabilities(self) -> RoutingCapability:
        return (
            RoutingCapability.DURATION_MATRIX
            | RoutingCapability.DISTANCE_MATRIX
            | RoutingCapability.MULTI_WAYPOINT_ROUTE
            | RoutingCapability.ROUTE_GEOMETRY
            | RoutingCapability.PER_LEG_METRICS
        )

    @property
    def provider_name(self) -> str:
        return "osrm"

    @property
    def routing_notice(self) -> str:
        return self._routing_notice

    async def _throttle(self) -> None:
        global _last_request_at
        wait = self._request_interval_seconds - (time.monotonic() - _last_request_at)
        if _last_request_at and wait > 0:
            await asyncio.sleep(wait)

    async def _get_matrix(self, points: list[tuple[float, float]]) -> dict:
        global _last_request_at
        if not 2 <= len(points) <= 4:
            raise ValueError("OSRM matrix requests must contain 2–4 route points")
        coordinates = ";".join(f"{lon:.6f},{lat:.6f}" for lat, lon in points)
        path = quote(coordinates, safe=",;-")
        url = f"{self._base_url}/table/v1/driving/{path}"
        params = {"annotations": "duration,distance"}
        async with _request_lock:
            await self._throttle()
            try:
                async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    payload = response.json()
            finally:
                _last_request_at = time.monotonic()
        if payload.get("code") != "Ok":
            raise ValueError(f"OSRM returned {payload.get('code', 'unknown status')}")
        expected = len(points)
        for key in ("durations", "distances"):
            matrix = payload.get(key)
            if (
                not isinstance(matrix, list)
                or len(matrix) != expected
                or any(
                    not isinstance(row, list) or len(row) != expected for row in matrix
                )
                or any(value is None for row in matrix for value in row)
            ):
                raise ValueError(f"OSRM returned an incomplete {key} matrix")
        return payload

    async def get_route_matrix(
        self, points: list[tuple[float, float]]
    ) -> RoutingMatrixResult:
        data = await self._get_matrix(points)
        return RoutingMatrixResult(
            durations=data["durations"],
            distances=data["distances"],
            is_approximate=False,
            provider_name=self.provider_name,
            routing_accuracy="road_network_duration_road_network_distance",
            notice=self.routing_notice,
        )

    async def get_multi_waypoint_route(
        self,
        waypoints: list[tuple[float, float]],
        stop_ids: list[str] | None = None,
        stop_labels: list[str | None] | None = None,
    ) -> MultiWaypointRoute:
        global _last_request_at
        if not 2 <= len(waypoints) <= 25:
            raise ValueError("OSRM route requests must contain 2–25 waypoints")

        coordinates = ";".join(f"{lon:.6f},{lat:.6f}" for lat, lon in waypoints)
        path = quote(coordinates, safe=",;-")
        url = f"{self._base_url}/route/v1/driving/{path}"
        params = {
            "overview": "full",
            "geometries": "geojson",
            "steps": "false",
        }

        async with _request_lock:
            await self._throttle()
            try:
                async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    payload = response.json()
            finally:
                _last_request_at = time.monotonic()

        if payload.get("code") != "Ok" or not payload.get("routes"):
            raise ValueError(
                f"OSRM route returned {payload.get('code', 'unknown status')}"
            )

        primary_route = payload["routes"][0]
        total_dist_m = float(primary_route["distance"])
        total_dur_s = float(primary_route["duration"])

        # Coordinates formatted as [longitude, latitude] per RFC 7946
        raw_geometry = primary_route.get("geometry", {})
        raw_coords = raw_geometry.get("coordinates", [])
        cleaned_coords = [
            [round(coord[0], 6), round(coord[1], 6)] for coord in raw_coords
        ]
        full_geojson = {
            "type": "LineString",
            "coordinates": cleaned_coords,
        }

        legs_data = primary_route.get("legs", [])
        legs: list[RouteLeg] = []
        for i in range(len(waypoints) - 1):
            leg_info = legs_data[i] if i < len(legs_data) else {}
            leg_dist = float(leg_info.get("distance", 0.0))
            leg_dur = float(leg_info.get("duration", 0.0))
            start_id = stop_ids[i] if stop_ids and i < len(stop_ids) else f"stop_{i}"
            end_id = (
                stop_ids[i + 1]
                if stop_ids and i + 1 < len(stop_ids)
                else f"stop_{i + 1}"
            )
            start_lbl = stop_labels[i] if stop_labels and i < len(stop_labels) else None
            end_lbl = (
                stop_labels[i + 1] if stop_labels and i + 1 < len(stop_labels) else None
            )

            legs.append(
                RouteLeg(
                    sequence=i + 1,
                    start_stop_id=str(start_id),
                    end_stop_id=str(end_id),
                    start_label=start_lbl,
                    end_label=end_lbl,
                    distance_meters=leg_dist,
                    duration_seconds=leg_dur,
                )
            )

        return MultiWaypointRoute(
            total_distance=DistanceMetric(
                distance_meters=total_dist_m,
                source=DistanceSource.PROVIDER_ROAD_NETWORK_ROUTE,
                is_approximate=False,
                confidence_factor=1.0,
            ),
            total_duration_seconds=total_dur_s,
            legs=legs,
            full_geometry_geojson=full_geojson,
            provider_name=self.provider_name,
            routing_accuracy="road_network_duration_road_network_distance",
            routing_notice=self.routing_notice,
        )

    async def get_duration_matrix(
        self, points: list[tuple[float, float]]
    ) -> list[list[float]]:
        data = await self._get_matrix(points)
        return data["durations"]

    async def get_route_duration(
        self, origin: tuple[float, float], destination: tuple[float, float]
    ) -> SegmentResult:
        data = await self._get_matrix([origin, destination])
        return SegmentResult(
            duration_seconds=float(data["durations"][0][1]),
            distance_meters=float(data["distances"][0][1]),
            is_approximate=False,
        )
