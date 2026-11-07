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

FALLBACK_NOTICE = (
    "Route duration estimated using spatial corridor baseline "
    "(tortuosity factor 1.40 × geodesic, 22 km/h). "
    "Actual road times may differ significantly in Mumbai traffic."
)


class FallbackRoutingProvider(RoutingProvider):
    """Approximate routing using geodesic distance × tortuosity factor."""

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
        return "fallback"

    @property
    def routing_notice(self) -> str:
        return FALLBACK_NOTICE

    async def get_route_matrix(
        self, points: list[tuple[float, float]]
    ) -> RoutingMatrixResult:
        n = len(points)
        durations: list[list[float]] = []
        distances: list[list[float]] = []
        for i in range(n):
            dur_row: list[float] = []
            dist_row: list[float] = []
            for j in range(n):
                if i == j:
                    dur_row.append(0.0)
                    dist_row.append(0.0)
                else:
                    lat1, lon1 = points[i]
                    lat2, lon2 = points[j]
                    geo = haversine_distance(lat1, lon1, lat2, lon2)
                    road = road_distance_estimate(geo)
                    dur_row.append(road_duration_estimate_seconds(road))
                    dist_row.append(road)
            durations.append(dur_row)
            distances.append(dist_row)

        return RoutingMatrixResult(
            durations=durations,
            distances=distances,
            is_approximate=True,
            provider_name=self.provider_name,
            routing_accuracy="geographic_approximation",
            notice=self.routing_notice,
        )

    async def get_multi_waypoint_route(
        self,
        waypoints: list[tuple[float, float]],
        stop_ids: list[str] | None = None,
        stop_labels: list[str | None] | None = None,
    ) -> MultiWaypointRoute:
        if not 2 <= len(waypoints) <= 25:
            raise ValueError("Route requests must contain 2–25 waypoints")

        # Synthesize RFC 7946 GeoJSON LineString [lon, lat] connecting stops directly
        cleaned_coords = [[round(lon, 6), round(lat, 6)] for lat, lon in waypoints]
        full_geojson = {
            "type": "LineString",
            "coordinates": cleaned_coords,
        }

        legs: list[RouteLeg] = []
        total_dist_m = 0.0
        total_dur_s = 0.0

        for i in range(len(waypoints) - 1):
            lat1, lon1 = waypoints[i]
            lat2, lon2 = waypoints[i + 1]
            geo = haversine_distance(lat1, lon1, lat2, lon2)
            leg_dist = road_distance_estimate(geo)
            leg_dur = road_duration_estimate_seconds(leg_dist)
            total_dist_m += leg_dist
            total_dur_s += leg_dur

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
                source=DistanceSource.CALIBRATED_TORTUOSITY_FALLBACK,
                is_approximate=True,
                confidence_factor=0.7,
            ),
            total_duration_seconds=total_dur_s,
            legs=legs,
            full_geometry_geojson=full_geojson,
            provider_name=self.provider_name,
            routing_accuracy="geographic_approximation",
            routing_notice=self.routing_notice,
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
        geo = haversine_distance(lat1, lon1, lat2, lon2)
        road = road_distance_estimate(geo)
        return SegmentResult(
            duration_seconds=road_duration_estimate_seconds(road),
            distance_meters=road,
            is_approximate=True,
        )
