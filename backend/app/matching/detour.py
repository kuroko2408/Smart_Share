"""Evaluate every precedence-valid pairwise stop order and calculate detours."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

from app.routing.base import (
    DistanceSource,
    RoutingMatrixResult,
    RoutingProvider,
)
from app.routing.fallback import FALLBACK_NOTICE

logger = logging.getLogger(__name__)


def valid_pairwise_stop_orders() -> list[tuple[int, int, int, int]]:
    """Enumerate all pairwise orders where each passenger is picked up first."""
    import itertools

    valid_orders = []
    for order in itertools.permutations((0, 1, 2, 3)):
        positions = {stop: order.index(stop) for stop in order}
        if positions[0] < positions[2] and positions[1] < positions[3]:
            valid_orders.append(order)
    return valid_orders


@dataclass
class StopSequenceResult:
    """Outcome of evaluating one route permutation."""

    sequence_label: str  # e.g. "PA→PB→DB→DA"
    duration_total_seconds: float
    duration_direct_a_seconds: float
    duration_direct_b_seconds: float
    detour_a_minutes: float
    detour_b_minutes: float
    distance_total_meters: float = 0.0
    distance_direct_a_meters: float = 0.0
    distance_direct_b_meters: float = 0.0
    detour_a_distance_meters: float = 0.0
    detour_b_distance_meters: float = 0.0
    distance_source: DistanceSource = DistanceSource.PROVIDER_MATRIX_TABLE
    is_approximate: bool = False
    notice: str = ""


@dataclass
class BestRouteResult:
    """The best valid stop sequence for a pairwise match, plus direct route metrics."""

    best_sequence: StopSequenceResult
    duration_direct_a_seconds: float
    duration_direct_b_seconds: float
    distance_direct_a_meters: float = 0.0
    distance_direct_b_meters: float = 0.0
    distance_source: DistanceSource = DistanceSource.PROVIDER_MATRIX_TABLE
    routing_accuracy: str = ""
    is_approximate: bool = False
    notice: str = ""
    matrix_result: RoutingMatrixResult | None = None


async def evaluate_pairwise_detour(
    *,
    provider: RoutingProvider,
    pickup_a: tuple[float, float],
    dest_a: tuple[float, float],
    pickup_b: tuple[float, float],
    dest_b: tuple[float, float],
    max_extra_a: int,
    max_extra_b: int,
) -> BestRouteResult | None:
    """Evaluate all six topological orders preserving each pickup before its dropoff."""
    # Build the 4-point matrix: [PA, PB, DA, DB]
    points = [pickup_a, pickup_b, dest_a, dest_b]
    # Indices: 0=PA, 1=PB, 2=DA, 3=DB

    try:
        matrix_res = await provider.get_route_matrix(points)
        durations = matrix_res.durations
        distances = matrix_res.distances

        if (
            len(durations) != len(points)
            or any(len(row) != len(points) for row in durations)
            or len(distances) != len(points)
            or any(len(row) != len(points) for row in distances)
        ):
            raise ValueError("Routing provider returned an invalid matrix shape")
        if any(
            not math.isfinite(value) or value < 0 for row in durations for value in row
        ) or any(
            not math.isfinite(value) or value < 0 for row in distances for value in row
        ):
            raise ValueError(
                "Routing provider returned an invalid duration or distance value"
            )

        is_approx = matrix_res.is_approximate
        source = (
            DistanceSource.CALIBRATED_TORTUOSITY_FALLBACK
            if is_approx
            else DistanceSource.PROVIDER_MATRIX_TABLE
        )
        accuracy = matrix_res.routing_accuracy
        notice = matrix_res.notice or getattr(provider, "routing_notice", "")
    except Exception as exc:
        logger.warning(
            "Routing provider failed (%s); using approximate fallback.",
            type(exc).__name__,
        )
        from app.routing.fallback import FallbackRoutingProvider

        fallback = FallbackRoutingProvider()
        matrix_res = await fallback.get_route_matrix(points)
        durations = matrix_res.durations
        distances = matrix_res.distances
        is_approx = True
        source = DistanceSource.CALIBRATED_TORTUOSITY_FALLBACK
        accuracy = matrix_res.routing_accuracy
        notice = FALLBACK_NOTICE

    # Direct durations and distances: PA→DA (direct A), PB→DB (direct B)
    direct_a_s = durations[0][2]
    direct_b_s = durations[1][3]
    direct_a_m = distances[0][2]
    direct_b_m = distances[1][3]

    results: list[StopSequenceResult] = []
    stop_names = {0: "PA", 1: "PB", 2: "DA", 3: "DB"}
    for order in valid_pairwise_stop_orders():
        positions = {stop: order.index(stop) for stop in order}
        # A proposal must include a segment with both passengers onboard.
        if max(positions[0], positions[1]) >= min(positions[2], positions[3]):
            continue

        elapsed_s = sum(
            durations[left][right]
            for left, right in zip(order, order[1:], strict=False)
        )
        elapsed_m = sum(
            distances[left][right]
            for left, right in zip(order, order[1:], strict=False)
        )

        pos_a, pos_b = positions[0], positions[1]
        time_a = sum(
            durations[order[i]][order[i + 1]] for i in range(pos_a, positions[2])
        )
        time_b = sum(
            durations[order[i]][order[i + 1]] for i in range(pos_b, positions[3])
        )
        dist_a = sum(
            distances[order[i]][order[i + 1]] for i in range(pos_a, positions[2])
        )
        dist_b = sum(
            distances[order[i]][order[i + 1]] for i in range(pos_b, positions[3])
        )

        label = "→".join(stop_names[stop] for stop in order)
        results.append(
            StopSequenceResult(
                sequence_label=label,
                duration_total_seconds=elapsed_s,
                duration_direct_a_seconds=direct_a_s,
                duration_direct_b_seconds=direct_b_s,
                detour_a_minutes=max(0.0, (time_a - direct_a_s) / 60.0),
                detour_b_minutes=max(0.0, (time_b - direct_b_s) / 60.0),
                distance_total_meters=elapsed_m,
                distance_direct_a_meters=direct_a_m,
                distance_direct_b_meters=direct_b_m,
                detour_a_distance_meters=max(0.0, dist_a - direct_a_m),
                detour_b_distance_meters=max(0.0, dist_b - direct_b_m),
                distance_source=source,
                is_approximate=is_approx,
                notice=notice,
            )
        )

    # Hard-gate: filter sequences where any passenger exceeds their time tolerance (DEC-003: strictly time-based)
    feasible = [
        r
        for r in results
        if r.detour_a_minutes <= max_extra_a and r.detour_b_minutes <= max_extra_b
    ]

    if not feasible:
        return None

    # Select sequence with minimum total detour (time)
    best = min(
        feasible,
        key=lambda r: (
            r.detour_a_minutes + r.detour_b_minutes,
            r.duration_total_seconds,
        ),
    )

    return BestRouteResult(
        best_sequence=best,
        duration_direct_a_seconds=direct_a_s,
        duration_direct_b_seconds=direct_b_s,
        distance_direct_a_meters=direct_a_m,
        distance_direct_b_meters=direct_b_m,
        distance_source=best.distance_source,
        routing_accuracy=accuracy,
        is_approximate=best.is_approximate,
        notice=best.notice,
        matrix_result=matrix_res,
    )
