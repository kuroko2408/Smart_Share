"""Routing provider protocol, capability flags, and shared data types."""

from __future__ import annotations

import enum
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.matching.geometry import (
    haversine_distance,
    road_distance_estimate,
)
from app.routing.models import (
    DistanceMetric,
    DistanceSource,
    MultiWaypointRoute,
    PassengerJourneyMetrics,
    RouteLeg,
    RoutingMatrixResult,
)

__all__ = [
    "DistanceMetric",
    "DistanceSource",
    "MultiWaypointRoute",
    "PassengerJourneyMetrics",
    "RouteLeg",
    "RouteResult",
    "RouteWaypoint",
    "RoutingCapability",
    "RoutingMatrixResult",
    "RoutingProvider",
    "SegmentResult",
]


class RoutingCapability(enum.Flag):
    """Capabilities supported by a routing provider implementation."""

    NONE = 0
    DURATION_MATRIX = enum.auto()
    DISTANCE_MATRIX = enum.auto()
    MULTI_WAYPOINT_ROUTE = enum.auto()
    ROUTE_GEOMETRY = enum.auto()
    PER_LEG_METRICS = enum.auto()
    LIVE_TRAFFIC = enum.auto()


@dataclass
class RouteWaypoint:
    latitude: float
    longitude: float
    stop_type: str  # "PICKUP" or "DROPOFF"
    passenger_request_id: uuid.UUID


@dataclass
class SegmentResult:
    """Duration and distance for a single P→Q leg."""

    duration_seconds: float
    distance_meters: float
    is_approximate: bool = False


@dataclass
class RouteResult:
    """Full ordered-stop route evaluation."""

    total_duration_seconds: float
    total_distance_meters: float
    is_approximate: bool
    notice: str = ""


class RoutingProvider(ABC):
    """Abstract base class for all Smart Share routing providers."""

    @property
    def capabilities(self) -> RoutingCapability:
        """Bitmask of supported provider capabilities."""
        return RoutingCapability.DURATION_MATRIX

    @property
    def provider_name(self) -> str:
        """Identifier for the routing provider (e.g. 'osrm', 'openrouteservice', 'fallback')."""
        return "custom"

    @property
    def routing_notice(self) -> str:
        """Human-readable transparency notice describing routing accuracy and assumptions."""
        return ""

    async def get_route_matrix(
        self, points: list[tuple[float, float]]
    ) -> RoutingMatrixResult:
        """
        Compute an N×N matrix of travel durations (seconds) and distances (metres).
        points: list of (latitude, longitude) tuples.
        Defaults to calling get_duration_matrix and estimating distances if not overridden.
        """
        durations = await self.get_duration_matrix(points)
        n = len(points)
        distances: list[list[float]] = []
        for i in range(n):
            dist_row: list[float] = []
            for j in range(n):
                if i == j:
                    dist_row.append(0.0)
                else:
                    lat1, lon1 = points[i]
                    lat2, lon2 = points[j]
                    dist_row.append(
                        road_distance_estimate(
                            haversine_distance(lat1, lon1, lat2, lon2)
                        )
                    )
            distances.append(dist_row)

        return RoutingMatrixResult(
            durations=durations,
            distances=distances,
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
        """
        Compute a continuous road route through ordered waypoints.
        Returns total metrics, per-leg metrics, and GeoJSON LineString geometry.
        """
        from app.routing.fallback import FallbackRoutingProvider

        fallback = FallbackRoutingProvider()
        return await fallback.get_multi_waypoint_route(
            waypoints=waypoints,
            stop_ids=stop_ids,
            stop_labels=stop_labels,
        )

    @abstractmethod
    async def get_duration_matrix(
        self, points: list[tuple[float, float]]
    ) -> list[list[float]]:
        """
        Return an N×N matrix of estimated travel durations (seconds) between all point pairs.
        points: list of (latitude, longitude) tuples.
        """
        ...

    async def get_route_duration(
        self, origin: tuple[float, float], destination: tuple[float, float]
    ) -> SegmentResult:
        """
        Backward-compatible helper returning duration and distance for a single segment.
        """
        result = await self.get_route_matrix([origin, destination])
        return SegmentResult(
            duration_seconds=float(result.durations[0][1]),
            distance_meters=float(result.distances[0][1]),
            is_approximate=result.is_approximate,
        )
