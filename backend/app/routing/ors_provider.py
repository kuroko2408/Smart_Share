"""
OpenRouteService routing provider.
Uses the ORS Matrix API and Directions API.
Wrapped in a 2-second timeout; falls back gracefully on failure.
"""

from __future__ import annotations

import logging

import httpx

from app.matching.geometry import (
    haversine_distance,
    road_distance_estimate,
    road_duration_estimate_seconds,
)
from app.routing.base import RoutingProvider, SegmentResult

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
        self.routing_notice = (
            "Road-network duration from OpenRouteService; this is not a live "
            "traffic prediction. Shared stop-sequence distance is estimated "
            "geographically."
        )

    async def get_duration_matrix(
        self, points: list[tuple[float, float]]
    ) -> list[list[float]]:
        """
        Call ORS matrix endpoint.
        ORS expects coordinates as [longitude, latitude] pairs.
        """
        # ORS coordinate format is [lon, lat]
        coordinates = [[lon, lat] for lat, lon in points]
        payload = {
            "locations": coordinates,
            "metrics": ["duration"],
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
                return data["durations"]
        except (
            httpx.TimeoutException,
            httpx.HTTPStatusError,
            httpx.RequestError,
            KeyError,
        ) as exc:
            logger.warning("ORS matrix call failed (%s).", type(exc).__name__)
            raise

    async def get_route_duration(
        self, origin: tuple[float, float], destination: tuple[float, float]
    ) -> SegmentResult:
        # Simple fallback to haversine for direct single-segment call
        lat1, lon1 = origin
        lat2, lon2 = destination
        try:
            matrix = await self.get_duration_matrix([origin, destination])
            duration_s = matrix[0][1]
            geo = haversine_distance(lat1, lon1, lat2, lon2)
            road_m = road_distance_estimate(geo)
            return SegmentResult(
                duration_seconds=duration_s,
                distance_meters=road_m,
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
