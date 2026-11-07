"""
OpenRouteService routing provider.
Uses the ORS Matrix API and Directions API.
Wrapped in a 2-second timeout; falls back gracefully on failure.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.matching.geometry import (
    haversine_distance,
    road_distance_estimate,
    road_duration_estimate_seconds,
)
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

ORS_BASE_URL = "https://api.openrouteservice.org"
REQUEST_TIMEOUT_S = 2.0


class ORSRoutingProvider(RoutingProvider):
    def __init__(
        self, api_key: str, timeout_seconds: float = REQUEST_TIMEOUT_S
    ) -> None:
        self._api_key = api_key
        self._timeout_seconds = max(0.1, timeout_seconds)
        self._headers = {
            "Authorization": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json, application/geo+json",
        }
        self._routing_notice = (
            "Road-network route and duration from OpenRouteService; this is not a "
            "live traffic prediction."
        )

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
        return "openrouteservice"

    @property
    def routing_notice(self) -> str:
        return self._routing_notice

    async def get_route_matrix(
        self, points: list[tuple[float, float]]
    ) -> RoutingMatrixResult:
        """
        Call ORS matrix endpoint.
        ORS expects coordinates as [longitude, latitude] pairs.
        """
        coordinates = [[lon, lat] for lat, lon in points]
        payload = {
            "locations": coordinates,
            "metrics": ["duration", "distance"],
            "units": "m",
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                resp = await client.post(
                    f"{ORS_BASE_URL}/v2/matrix/driving-car",
                    headers=self._headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return RoutingMatrixResult(
                    durations=data["durations"],
                    distances=data["distances"],
                    is_approximate=False,
                    provider_name=self.provider_name,
                    routing_accuracy="road_network_duration_road_network_distance",
                    notice=self.routing_notice,
                )
        except (
            httpx.TimeoutException,
            httpx.HTTPStatusError,
            httpx.RequestError,
            KeyError,
        ) as exc:
            logger.warning("ORS matrix call failed (%s).", type(exc).__name__)
            raise

    async def get_multi_waypoint_route(
        self,
        waypoints: list[tuple[float, float]],
        stop_ids: list[str] | None = None,
        stop_labels: list[str | None] | None = None,
    ) -> MultiWaypointRoute:
        """
        Call ORS directions endpoint returning GeoJSON LineString and per-segment metrics.
        """
        coordinates = [[lon, lat] for lat, lon in waypoints]
        payload: dict[str, Any] = {
            "coordinates": coordinates,
            "units": "m",
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                resp = await client.post(
                    f"{ORS_BASE_URL}/v2/directions/driving-car/geojson",
                    headers=self._headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()

            features = data.get("features", [])
            if not features:
                raise ValueError("ORS returned no features in route response")

            feat = features[0]
            props = feat.get("properties", {})
            summary = props.get("summary", {})
            total_dist_m = float(summary.get("distance", 0.0))
            total_dur_s = float(summary.get("duration", 0.0))

            raw_coords = feat.get("geometry", {}).get("coordinates", [])
            cleaned_coords = [[round(c[0], 6), round(c[1], 6)] for c in raw_coords]
            full_geojson = {
                "type": "LineString",
                "coordinates": cleaned_coords,
            }

            segments = props.get("segments", [])
            legs: list[RouteLeg] = []
            for i in range(len(waypoints) - 1):
                seg = segments[i] if i < len(segments) else {}
                leg_dist = float(seg.get("distance", 0.0))
                leg_dur = float(seg.get("duration", 0.0))
                start_id = (
                    stop_ids[i] if stop_ids and i < len(stop_ids) else f"stop_{i}"
                )
                end_id = (
                    stop_ids[i + 1]
                    if stop_ids and i + 1 < len(stop_ids)
                    else f"stop_{i + 1}"
                )
                start_lbl = (
                    stop_labels[i] if stop_labels and i < len(stop_labels) else None
                )
                end_lbl = (
                    stop_labels[i + 1]
                    if stop_labels and i + 1 < len(stop_labels)
                    else None
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
        except Exception as exc:
            logger.warning(
                "ORS directions call failed (%s); using fallback.", type(exc).__name__
            )
            from app.routing.fallback import FallbackRoutingProvider

            fallback = FallbackRoutingProvider()
            return await fallback.get_multi_waypoint_route(
                waypoints=waypoints,
                stop_ids=stop_ids,
                stop_labels=stop_labels,
            )

    async def get_duration_matrix(
        self, points: list[tuple[float, float]]
    ) -> list[list[float]]:
        matrix_res = await self.get_route_matrix(points)
        return matrix_res.durations

    async def get_route_duration(
        self, origin: tuple[float, float], destination: tuple[float, float]
    ) -> SegmentResult:
        lat1, lon1 = origin
        lat2, lon2 = destination
        try:
            matrix_res = await self.get_route_matrix([origin, destination])
            return SegmentResult(
                duration_seconds=float(matrix_res.durations[0][1]),
                distance_meters=float(matrix_res.distances[0][1]),
                is_approximate=False,
            )
        except Exception:
            geo = haversine_distance(lat1, lon1, lat2, lon2)
            road_m = road_distance_estimate(geo)
            return SegmentResult(
                duration_seconds=road_duration_estimate_seconds(road_m),
                distance_meters=road_m,
                is_approximate=True,
            )
