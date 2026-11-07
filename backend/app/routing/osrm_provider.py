"""Credential-free OSRM public routing adapter for hackathon demonstration use."""

from __future__ import annotations

import asyncio
import logging
import time
from urllib.parse import quote

import httpx

from app.routing.base import RoutingProvider, SegmentResult

logger = logging.getLogger(__name__)
DEFAULT_OSRM_BASE_URL = "https://router.project-osrm.org"
OSRM_NOTICE = (
    "Road-network duration from OSRM/OpenStreetMap; estimates use the provider's "
    "fastest-route profile and are not live traffic predictions. Distance is "
    "estimated geographically for the shared stop sequence."
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
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = max(0.1, timeout_seconds)
        self._request_interval_seconds = max(1.0, request_interval_seconds)
        self.routing_notice = OSRM_NOTICE

    async def _get_matrix(self, points: list[tuple[float, float]]) -> dict:
        global _last_request_at
        if not 2 <= len(points) <= 4:
            raise ValueError("OSRM matrix requests must contain 2–4 route points")
        coordinates = ";".join(f"{lon:.6f},{lat:.6f}" for lat, lon in points)
        path = quote(coordinates, safe=",;-")
        url = f"{self._base_url}/table/v1/driving/{path}"
        params = {"annotations": "duration,distance"}
        async with _request_lock:
            wait = self._request_interval_seconds - (
                time.monotonic() - _last_request_at
            )
            if _last_request_at and wait > 0:
                await asyncio.sleep(wait)
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
