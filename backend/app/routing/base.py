"""Routing provider protocol and shared data types."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass


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
    @abstractmethod
    async def get_duration_matrix(
        self, points: list[tuple[float, float]]
    ) -> list[list[float]]:
        """
        Return an N×N matrix of estimated travel durations (seconds) between all point pairs.
        points: list of (latitude, longitude) tuples.
        """
        ...

    @abstractmethod
    async def get_route_duration(
        self, origin: tuple[float, float], destination: tuple[float, float]
    ) -> SegmentResult:
        """Return duration and distance for a single origin → destination trip."""
        ...
