"""
Fallback routing provider using calibrated tortuosity approximation.
Used when external routing is unavailable or rate-limited.
Clearly marks all results as approximate.
"""

from __future__ import annotations

from app.matching.geometry import (
    haversine_distance,
    road_distance_estimate,
    road_duration_estimate_seconds,
)
from app.routing.base import RoutingProvider, SegmentResult

FALLBACK_NOTICE = (
    "Route duration estimated using spatial corridor baseline "
    "(tortuosity factor 1.40 × geodesic, 22 km/h). "
    "Actual road times may differ significantly in Mumbai traffic."
)


class FallbackRoutingProvider(RoutingProvider):
    """Approximate routing using geodesic distance × tortuosity factor."""

    async def get_duration_matrix(
        self, points: list[tuple[float, float]]
    ) -> list[list[float]]:
        n = len(points)
        matrix: list[list[float]] = []
        for i in range(n):
            row: list[float] = []
            for j in range(n):
                if i == j:
                    row.append(0.0)
                else:
                    lat1, lon1 = points[i]
                    lat2, lon2 = points[j]
                    geo = haversine_distance(lat1, lon1, lat2, lon2)
                    road = road_distance_estimate(geo)
                    row.append(road_duration_estimate_seconds(road))
            matrix.append(row)
        return matrix

    async def get_route_duration(
        self, origin: tuple[float, float], destination: tuple[float, float]
    ) -> SegmentResult:
        lat1, lon1 = origin
        lat2, lon2 = destination
        geo = haversine_distance(lat1, lon1, lat2, lon2)
        road = road_distance_estimate(geo)
        return SegmentResult(
            duration_seconds=road_duration_estimate_seconds(road),
            distance_meters=road,
            is_approximate=True,
        )
