"""
Compatibility scoring model for the Smart Share matching engine.
Deterministic, normalised [0,1] multi-factor scoring.
All inputs are plain Python values — no I/O.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

MAX_PICKUP_RADIUS_M: float = 2_000.0
MAX_DEST_RADIUS_M: float = 5_000.0
MID_DEPARTURE_NORMALISER_MINUTES: float = 30.0
VEHICLE_CAPACITY: int = 4

WEIGHT_PICKUP: float = 0.30
WEIGHT_DEST: float = 0.30
WEIGHT_TIME: float = 0.20
WEIGHT_DETOUR: float = 0.20


@dataclass
class ScoreBreakdown:
    pickup_proximity_score: float
    destination_similarity_score: float
    departure_time_score: float
    route_detour_score: float
    composite_score: float

    def as_dict(self) -> dict[str, float]:
        return {
            "pickup_proximity_score": round(self.pickup_proximity_score, 4),
            "destination_similarity_score": round(self.destination_similarity_score, 4),
            "departure_time_score": round(self.departure_time_score, 4),
            "route_detour_score": round(self.route_detour_score, 4),
            "composite_score": round(self.composite_score, 4),
        }


def _pickup_score(pickup_distance_m: float) -> float:
    return max(0.0, 1.0 - pickup_distance_m / MAX_PICKUP_RADIUS_M)


def _destination_score(dest_distance_m: float, angular_delta_deg: float) -> float:
    dist_component = max(0.0, 1.0 - dest_distance_m / MAX_DEST_RADIUS_M)
    heading_component = max(0.0, math.cos(math.radians(angular_delta_deg)))
    return 0.60 * dist_component + 0.40 * heading_component


def _temporal_score(
    overlap_seconds: float,
    window_a_seconds: float,
    window_b_seconds: float,
    midpoint_delta_minutes: float,
) -> float:
    min_window = max(1.0, min(window_a_seconds, window_b_seconds))
    overlap_score = min(1.0, overlap_seconds / min_window)
    mid_score = max(
        0.0, 1.0 - midpoint_delta_minutes / MID_DEPARTURE_NORMALISER_MINUTES
    )
    return 0.70 * overlap_score + 0.30 * mid_score


def _detour_score(
    detour_a_minutes: float,
    detour_b_minutes: float,
    max_extra_a: int,
    max_extra_b: int,
) -> float:
    rho_a = detour_a_minutes / max(1, max_extra_a)
    rho_b = detour_b_minutes / max(1, max_extra_b)
    return max(0.0, 1.0 - (rho_a + rho_b) / 2.0)


def compute_score(
    *,
    pickup_distance_m: float,
    dest_distance_m: float,
    angular_delta_deg: float,
    overlap_seconds: float,
    window_a_seconds: float,
    window_b_seconds: float,
    midpoint_delta_minutes: float,
    detour_a_minutes: float,
    detour_b_minutes: float,
    max_extra_a: int,
    max_extra_b: int,
    seats_a: int,
    seats_b: int,
) -> ScoreBreakdown:
    """
    Compute the full compatibility score breakdown.
    Hard gate violations result in composite_score = 0.0 but component scores are
    still computed for diagnostic purposes.
    """
    s_pickup = _pickup_score(pickup_distance_m)
    s_dest = _destination_score(dest_distance_m, angular_delta_deg)
    s_time = _temporal_score(
        overlap_seconds, window_a_seconds, window_b_seconds, midpoint_delta_minutes
    )
    s_detour = _detour_score(
        detour_a_minutes, detour_b_minutes, max_extra_a, max_extra_b
    )

    composite = (
        WEIGHT_PICKUP * s_pickup
        + WEIGHT_DEST * s_dest
        + WEIGHT_TIME * s_time
        + WEIGHT_DETOUR * s_detour
    )
    if (
        not (0 < seats_a + seats_b <= VEHICLE_CAPACITY)
        or overlap_seconds < 0
        or pickup_distance_m > MAX_PICKUP_RADIUS_M
        or detour_a_minutes > max_extra_a
        or detour_b_minutes > max_extra_b
    ):
        composite = 0.0

    return ScoreBreakdown(
        pickup_proximity_score=s_pickup,
        destination_similarity_score=s_dest,
        departure_time_score=s_time,
        route_detour_score=s_detour,
        composite_score=composite,
    )
