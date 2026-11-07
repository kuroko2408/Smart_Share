"""Focused regression coverage for geometry, scoring, and valid route ordering."""

from __future__ import annotations

import pytest

from app.core.spatial import parse_point_coordinates, to_geography_point
from app.matching.detour import evaluate_pairwise_detour, valid_pairwise_stop_orders
from app.matching.geometry import (
    angular_delta,
    bearing,
    haversine_distance,
    is_directionally_compatible,
)
from app.matching.scoring import compute_score
from app.routing.base import RoutingProvider
from app.routing.osrm_provider import OSRM_NOTICE, OSRMRoutingProvider


def test_mumbai_distance_and_coordinate_order() -> None:
    # BKC to Powai is about 6 km geodesically; swapped coordinates are far away.
    distance = haversine_distance(19.0657, 72.8687, 19.1176, 72.9060)
    assert 6_000 < distance < 7_000
    point = to_geography_point(19.0657, 72.8687)
    assert point.data == "POINT(72.8687 19.0657)"
    assert parse_point_coordinates(point) == (19.0657, 72.8687)


def test_bearing_wrap_and_opposing_direction_rejection() -> None:
    assert angular_delta(359.0, 1.0) == pytest.approx(2.0)
    assert angular_delta(0.0, 180.0) == 180.0
    assert not is_directionally_compatible(0.0, 180.0, 0.0)
    assert is_directionally_compatible(0.0, 45.0, 50_000)
    assert is_directionally_compatible(0.0, 70.0, 2_999)
    assert not is_directionally_compatible(0.0, 70.0, 3_001)


def test_bearing_north_south() -> None:
    assert bearing(19.0, 72.0, 20.0, 72.0) == pytest.approx(0.0)
    assert bearing(20.0, 72.0, 19.0, 72.0) == pytest.approx(180.0)


def test_score_capacity_is_a_gate_not_a_reward() -> None:
    args = {
        "pickup_distance_m": 100,
        "dest_distance_m": 100,
        "angular_delta_deg": 5,
        "overlap_seconds": 300,
        "window_a_seconds": 600,
        "window_b_seconds": 600,
        "midpoint_delta_minutes": 1,
        "detour_a_minutes": 2,
        "detour_b_minutes": 2,
        "max_extra_a": 20,
        "max_extra_b": 20,
    }
    score_2_seats = compute_score(**args, seats_a=1, seats_b=1)
    score_4_seats = compute_score(**args, seats_a=2, seats_b=2)
    score_over_capacity = compute_score(**args, seats_a=3, seats_b=2)
    assert score_2_seats.composite_score == pytest.approx(score_4_seats.composite_score)
    assert score_over_capacity.composite_score == 0.0


def test_hard_detour_failure_cannot_be_overridden_by_other_score_factors() -> None:
    result = compute_score(
        pickup_distance_m=0,
        dest_distance_m=0,
        angular_delta_deg=0,
        overlap_seconds=600,
        window_a_seconds=600,
        window_b_seconds=600,
        midpoint_delta_minutes=0,
        detour_a_minutes=20.1,
        detour_b_minutes=0,
        max_extra_a=20,
        max_extra_b=20,
        seats_a=1,
        seats_b=1,
    )
    assert result.pickup_proximity_score == 1.0
    assert result.destination_similarity_score == 1.0
    assert result.departure_time_score == 1.0
    assert result.composite_score == 0.0


def test_boundary_only_departure_intersection_scores_below_positive_overlap() -> None:
    common = {
        "pickup_distance_m": 0,
        "dest_distance_m": 0,
        "angular_delta_deg": 0,
        "window_a_seconds": 600,
        "window_b_seconds": 600,
        "midpoint_delta_minutes": 10,
        "detour_a_minutes": 0,
        "detour_b_minutes": 0,
        "max_extra_a": 20,
        "max_extra_b": 20,
        "seats_a": 1,
        "seats_b": 1,
    }
    boundary = compute_score(**common, overlap_seconds=0)
    positive = compute_score(**common, overlap_seconds=60)
    disjoint = compute_score(**common, overlap_seconds=-1)

    assert 0 < boundary.departure_time_score < positive.departure_time_score
    assert disjoint.composite_score == 0.0


def test_pairwise_precedence_has_exactly_six_valid_orders() -> None:
    valid = valid_pairwise_stop_orders()
    assert len(valid) == 6
    assert all(order.index(0) < order.index(2) for order in valid)
    assert all(order.index(1) < order.index(3) for order in valid)


class MatrixRoutingProvider(RoutingProvider):
    async def get_duration_matrix(
        self, points: list[tuple[float, float]]
    ) -> list[list[float]]:
        matrix = [[0.0 if i == j else 120.0 for j in range(4)] for i in range(4)]
        matrix[0][2] = 600.0  # A direct
        matrix[1][3] = 600.0  # B direct
        matrix[0][1] = 900.0
        matrix[1][0] = 60.0
        return matrix

    async def get_route_duration(
        self, origin: tuple[float, float], destination: tuple[float, float]
    ):
        raise NotImplementedError


@pytest.mark.asyncio
async def test_detour_evaluator_can_choose_candidate_first_stop_order() -> None:
    result = await evaluate_pairwise_detour(
        provider=MatrixRoutingProvider(),
        pickup_a=(19.0, 72.0),
        dest_a=(19.1, 72.1),
        pickup_b=(19.01, 72.01),
        dest_b=(19.11, 72.11),
        max_extra_a=30,
        max_extra_b=30,
    )
    assert result is not None
    sequence = result.best_sequence.sequence_label.split("→")
    assert sequence.index("PA") < sequence.index("DA")
    assert sequence.index("PB") < sequence.index("DB")
    assert max(sequence.index("PA"), sequence.index("PB")) < min(
        sequence.index("DA"), sequence.index("DB")
    )


class ImpossibleDetourProvider(MatrixRoutingProvider):
    async def get_duration_matrix(
        self, points: list[tuple[float, float]]
    ) -> list[list[float]]:
        matrix = [[0.0 if i == j else 120.0 for j in range(4)] for i in range(4)]
        matrix[0][2] = 1.0
        matrix[1][3] = 1.0
        return matrix


@pytest.mark.asyncio
async def test_detour_evaluator_rejects_every_sequence_over_personal_tolerance() -> (
    None
):
    result = await evaluate_pairwise_detour(
        provider=ImpossibleDetourProvider(),
        pickup_a=(19.0, 72.0),
        dest_a=(19.1, 72.1),
        pickup_b=(19.01, 72.01),
        dest_b=(19.11, 72.11),
        max_extra_a=0,
        max_extra_b=0,
    )
    assert result is None


class FailedRoutingProvider(MatrixRoutingProvider):
    async def get_duration_matrix(
        self, points: list[tuple[float, float]]
    ) -> list[list[float]]:
        raise TimeoutError


@pytest.mark.asyncio
async def test_provider_failure_uses_fallback_and_marks_estimate_approximate() -> None:
    result = await evaluate_pairwise_detour(
        provider=FailedRoutingProvider(),
        pickup_a=(19.0, 72.0),
        dest_a=(19.1, 72.1),
        pickup_b=(19.001, 72.001),
        dest_b=(19.101, 72.101),
        max_extra_a=180,
        max_extra_b=180,
    )
    assert result is not None
    assert result.is_approximate
    assert "estimated" in result.notice.lower()


@pytest.mark.asyncio
async def test_osrm_response_is_marked_as_road_network_duration(monkeypatch) -> None:
    provider = OSRMRoutingProvider()

    async def fake_matrix(points):
        assert points == [(19.0657, 72.8687), (19.1176, 72.906)]
        return {
            "durations": [[0, 645.1], [686.0, 0]],
            "distances": [[0, 8803.9], [9387.8, 0]],
        }

    monkeypatch.setattr(provider, "_get_matrix", fake_matrix)
    segment = await provider.get_route_duration((19.0657, 72.8687), (19.1176, 72.906))

    assert segment.duration_seconds == pytest.approx(645.1)
    assert segment.distance_meters == pytest.approx(8803.9)
    assert not segment.is_approximate
    assert "not live traffic" in OSRM_NOTICE
