"""Evaluate every precedence-valid pairwise stop order and calculate detours."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

from app.routing.base import RoutingProvider
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
    is_approximate: bool
    notice: str = ""


@dataclass
class BestRouteResult:
    """The best valid stop sequence for a pairwise match, plus direct route durations."""

    best_sequence: StopSequenceResult
    duration_direct_a_seconds: float
    duration_direct_b_seconds: float
    is_approximate: bool
    notice: str = ""


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
        matrix = await provider.get_duration_matrix(points)
        if len(matrix) != len(points) or any(len(row) != len(points) for row in matrix):
            raise ValueError(
                "Routing provider returned an invalid duration matrix shape"
            )
        if any(
            not math.isfinite(value) or value < 0 for row in matrix for value in row
        ):
            raise ValueError("Routing provider returned an invalid duration value")
        is_approx = False
        notice = getattr(provider, "routing_notice", "")
    except Exception as exc:
        logger.warning(
            "Routing provider failed (%s); using approximate fallback.",
            type(exc).__name__,
        )
        from app.routing.fallback import FallbackRoutingProvider

        fallback = FallbackRoutingProvider()
        matrix = await fallback.get_duration_matrix(points)
        is_approx = True
        notice = FALLBACK_NOTICE

    # Direct durations
    # PA→DA (direct A)
    direct_a_s = matrix[0][2]
    # PB→DB (direct B)
    direct_b_s = matrix[1][3]

    # Stop indices: PA=0, PB=1, DA=2, DB=3. A's direct is PA→DA; B's is PB→DB.
    # Permutations enforce both precedence constraints before any route is measured.
    results: list[StopSequenceResult] = []
    stop_names = {0: "PA", 1: "PB", 2: "DA", 3: "DB"}
    for order in valid_pairwise_stop_orders():
        positions = {stop: order.index(stop) for stop in order}
        # A proposal must include a segment with both passengers onboard.
        if max(positions[0], positions[1]) >= min(positions[2], positions[3]):
            continue
        elapsed = 0.0
        for left, right in zip(order, order[1:], strict=False):
            elapsed += matrix[left][right]
        pos_a, pos_b = positions[0], positions[1]
        time_a = sum(matrix[order[i]][order[i + 1]] for i in range(pos_a, positions[2]))
        time_b = sum(matrix[order[i]][order[i + 1]] for i in range(pos_b, positions[3]))
        label = "→".join(stop_names[stop] for stop in order)
        results.append(
            StopSequenceResult(
                sequence_label=label,
                duration_total_seconds=elapsed,
                duration_direct_a_seconds=direct_a_s,
                duration_direct_b_seconds=direct_b_s,
                detour_a_minutes=max(0.0, (time_a - direct_a_s) / 60.0),
                detour_b_minutes=max(0.0, (time_b - direct_b_s) / 60.0),
                is_approximate=is_approx,
                notice=notice,
            )
        )

    # Hard-gate: filter sequences where any passenger exceeds their tolerance
    feasible = [
        r
        for r in results
        if r.detour_a_minutes <= max_extra_a and r.detour_b_minutes <= max_extra_b
    ]

    if not feasible:
        return None

    # Select sequence with minimum total detour
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
        is_approximate=best.is_approximate,
        notice=best.notice,
    )
