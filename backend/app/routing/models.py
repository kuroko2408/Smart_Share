"""Data models for normalized routing metrics, legs, and route geometries."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


class DistanceSource(enum.StrEnum):
    """Provenance and accuracy category of a distance metric."""

    GEODESIC_SPHEROID = "geodesic_spheroid"
    CALIBRATED_TORTUOSITY_FALLBACK = "calibrated_tortuosity_fallback"
    PROVIDER_MATRIX_TABLE = "provider_matrix_table"
    PROVIDER_ROAD_NETWORK_ROUTE = "provider_road_network_route"
    ACTUAL_TELEMETRY = "actual_telemetry"


@dataclass(frozen=True)
class DistanceMetric:
    """Normalized distance value with explicit provenance."""

    distance_meters: float
    source: DistanceSource
    is_approximate: bool
    confidence_factor: float = 1.0  # 1.0 = verified road network, 0.7 = fallback

    @property
    def distance_km(self) -> float:
        return round(self.distance_meters / 1000.0, 3)


@dataclass(frozen=True)
class RouteLeg:
    """A single segment between two consecutive stops in a pooled route."""

    sequence: int
    start_stop_id: str
    end_stop_id: str
    start_label: str | None = None
    end_label: str | None = None
    distance_meters: float = 0.0
    duration_seconds: float = 0.0
    geometry_geojson: dict[str, Any] | None = None

    @property
    def distance_km(self) -> float:
        return round(self.distance_meters / 1000.0, 3)

    @property
    def duration_minutes(self) -> float:
        return round(self.duration_seconds / 60.0, 2)


@dataclass(frozen=True)
class PassengerJourneyMetrics:
    """Distance and detour breakdown for a specific passenger on a pooled route."""

    passenger_request_id: str
    solo_direct_distance_meters: float
    solo_direct_duration_seconds: float
    pooled_journey_distance_meters: float
    pooled_journey_duration_seconds: float
    detour_distance_meters: float
    detour_duration_minutes: float
    distance_source: DistanceSource
    is_approximate: bool

    @property
    def solo_direct_distance_km(self) -> float:
        return round(self.solo_direct_distance_meters / 1000.0, 2)

    @property
    def solo_direct_duration_minutes(self) -> float:
        return round(self.solo_direct_duration_seconds / 60.0, 1)

    @property
    def pooled_distance_km(self) -> float:
        return round(self.pooled_journey_distance_meters / 1000.0, 2)

    @property
    def pooled_duration_minutes(self) -> float:
        return round(self.pooled_journey_duration_seconds / 60.0, 1)

    @property
    def detour_distance_km(self) -> float:
        return round(self.detour_distance_meters / 1000.0, 2)


@dataclass
class MultiWaypointRoute:
    """Full synthesized road route for a multi-stop sequence."""

    total_distance: DistanceMetric
    total_duration_seconds: float
    legs: list[RouteLeg]
    full_geometry_geojson: dict[str, Any]
    passenger_metrics: dict[str, PassengerJourneyMetrics] = field(default_factory=dict)
    provider_name: str = ""
    routing_accuracy: str = ""
    routing_notice: str = ""
    calculated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class RoutingMatrixResult:
    """NxN matrix result containing both duration and distance matrices."""

    durations: list[list[float]]
    distances: list[list[float]]
    is_approximate: bool
    provider_name: str
    routing_accuracy: str
    notice: str = ""
