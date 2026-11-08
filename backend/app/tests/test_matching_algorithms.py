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
    shared_segment_orders = [
        order
        for order in valid
        if max(order.index(0), order.index(1)) < min(order.index(2), order.index(3))
    ]
    assert len(shared_segment_orders) == 4


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


class CoordinateSensitiveProvider(RoutingProvider):
    def __init__(self):
        self.calls: list[list[tuple[float, float]]] = []

    async def get_duration_matrix(self, points):
        from app.matching.geometry import haversine_distance

        self.calls.append(list(points))
        return [
            [
                0.0 if i == j else haversine_distance(*points[i], *points[j]) / 8.0
                for j in range(len(points))
            ]
            for i in range(len(points))
        ]


@pytest.mark.asyncio
async def test_shared_route_uses_both_pickups_and_destinations_without_coordinate_reuse():
    provider = CoordinateSensitiveProvider()
    pickup_a = (19.0657, 72.8687)
    pickup_b = (19.0660, 72.8690)
    dest_a = (19.1176, 72.9060)
    dest_b_first = (19.1180, 72.9065)
    dest_b_changed = (19.1300, 72.9200)

    first = await evaluate_pairwise_detour(
        provider=provider,
        pickup_a=pickup_a,
        dest_a=dest_a,
        pickup_b=pickup_b,
        dest_b=dest_b_first,
        max_extra_a=10_000,
        max_extra_b=10_000,
    )
    second = await evaluate_pairwise_detour(
        provider=provider,
        pickup_a=pickup_a,
        dest_a=dest_a,
        pickup_b=pickup_b,
        dest_b=dest_b_changed,
        max_extra_a=10_000,
        max_extra_b=10_000,
    )

    assert first is not None and second is not None
    assert provider.calls == [
        [pickup_a, pickup_b, dest_a, dest_b_first],
        [pickup_a, pickup_b, dest_a, dest_b_changed],
    ]
    assert (
        first.best_sequence.distance_total_meters
        != second.best_sequence.distance_total_meters
    )
    assert first.distance_direct_a_meters == pytest.approx(
        second.distance_direct_a_meters
    )
    assert first.distance_direct_b_meters != second.distance_direct_b_meters


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


def test_directional_compatibility_boundaries() -> None:
    # delta <= 45 deg: always compatible
    assert is_directionally_compatible(0.0, 44.9, 50_000.0) is True
    assert is_directionally_compatible(0.0, 45.0, 50_000.0) is True

    # 45 deg < delta <= 90 deg: compatible only if dest <= 3000m
    assert is_directionally_compatible(0.0, 45.1, 3_000.0) is True
    assert is_directionally_compatible(0.0, 45.1, 3_000.1) is False
    assert is_directionally_compatible(0.0, 90.0, 3_000.0) is True
    assert is_directionally_compatible(0.0, 90.0, 3_000.1) is False

    # delta > 90 deg: hard reject even if destinations are at 0m
    assert is_directionally_compatible(0.0, 90.1, 0.0) is False
    assert is_directionally_compatible(0.0, 120.0, 0.0) is False
    assert is_directionally_compatible(0.0, 180.0, 0.0) is False


def test_mumbai_dadar_colaba_vs_dadar_borivali_opposing_rejected() -> None:
    # Dadar pickup: (19.0178, 72.8478)
    # Colaba dropoff (South): (18.9067, 72.8147) -> bearing ~194 deg
    # Borivali dropoff (North): (19.2307, 72.8567) -> bearing ~2 deg
    dadar_lat, dadar_lon = 19.0178, 72.8478
    colaba_lat, colaba_lon = 18.9067, 72.8147
    borivali_lat, borivali_lon = 19.2307, 72.8567

    bearing_colaba = bearing(dadar_lat, dadar_lon, colaba_lat, colaba_lon)
    bearing_borivali = bearing(dadar_lat, dadar_lon, borivali_lat, borivali_lon)

    delta = angular_delta(bearing_colaba, bearing_borivali)
    assert delta > 150.0  # Nearly anti-parallel (~168 deg)

    # Must be rejected even if pickup distance is 0m
    assert is_directionally_compatible(bearing_colaba, bearing_borivali, 0.0) is False


def test_pickup_proximity_boundary_scoring() -> None:
    args = {
        "dest_distance_m": 0,
        "angular_delta_deg": 0,
        "overlap_seconds": 600,
        "window_a_seconds": 600,
        "window_b_seconds": 600,
        "midpoint_delta_minutes": 0,
        "detour_a_minutes": 0,
        "detour_b_minutes": 0,
        "max_extra_a": 15,
        "max_extra_b": 15,
        "seats_a": 1,
        "seats_b": 1,
    }
    # Within 2000m
    s_0 = compute_score(**args, pickup_distance_m=0.0)
    assert s_0.pickup_proximity_score == 1.0
    assert s_0.composite_score == 1.0

    s_1000 = compute_score(**args, pickup_distance_m=1000.0)
    assert s_1000.pickup_proximity_score == pytest.approx(0.5)
    assert s_1000.composite_score > 0.0

    # Exact boundary 2000m: pickup proximity is 0.0, but other factors make composite > 0
    s_2000 = compute_score(**args, pickup_distance_m=2000.0)
    assert s_2000.pickup_proximity_score == 0.0
    assert s_2000.composite_score > 0.0

    # Beyond 2000m: hard gate violation forces composite_score = 0.0
    s_2001 = compute_score(**args, pickup_distance_m=2000.1)
    assert s_2001.pickup_proximity_score == 0.0
    assert s_2001.composite_score == 0.0


def test_capacity_boundaries_and_rejection() -> None:
    common = {
        "pickup_distance_m": 100,
        "dest_distance_m": 100,
        "angular_delta_deg": 0,
        "overlap_seconds": 600,
        "window_a_seconds": 600,
        "window_b_seconds": 600,
        "midpoint_delta_minutes": 0,
        "detour_a_minutes": 1,
        "detour_b_minutes": 1,
        "max_extra_a": 15,
        "max_extra_b": 15,
    }
    # Valid combinations (<= 4 seats)
    for a, b in [(1, 1), (1, 2), (1, 3), (2, 2), (3, 1)]:
        score = compute_score(**common, seats_a=a, seats_b=b)
        assert score.composite_score > 0.0, f"Failed for {a}+{b}"

    # Invalid combinations (> 4 seats)
    for a, b in [(1, 4), (2, 3), (3, 2), (4, 1), (3, 3), (4, 2)]:
        score = compute_score(**common, seats_a=a, seats_b=b)
        assert score.composite_score == 0.0, f"Expected 0.0 for {a}+{b}"


class ConfigurableMatrixRoutingProvider(RoutingProvider):
    def __init__(self, matrix: list[list[float]]):
        self._matrix = matrix

    async def get_duration_matrix(
        self, points: list[tuple[float, float]]
    ) -> list[list[float]]:
        return self._matrix

    async def get_route_duration(
        self, origin: tuple[float, float], destination: tuple[float, float]
    ):
        raise NotImplementedError


@pytest.mark.asyncio
async def test_all_four_valid_route_permutations_can_be_selected() -> None:
    # Points order: 0=PA, 1=PB, 2=DA, 3=DB
    # Direct: 0->2 (A), 1->3 (B)
    pts = [(19.0, 72.0), (19.01, 72.01), (19.1, 72.1), (19.11, 72.11)]

    # 1. Favor PA -> PB -> DA -> DB
    # Order: 0 -> 1 -> 2 -> 3
    m1 = [[0.0 if i == j else 500.0 for j in range(4)] for i in range(4)]
    m1[0][2] = 200.0  # direct A
    m1[1][3] = 200.0  # direct B
    m1[0][1] = 10.0
    m1[1][2] = 190.0
    m1[2][3] = 10.0
    r1 = await evaluate_pairwise_detour(
        provider=ConfigurableMatrixRoutingProvider(m1),
        pickup_a=pts[0],
        dest_a=pts[2],
        pickup_b=pts[1],
        dest_b=pts[3],
        max_extra_a=10,
        max_extra_b=10,
    )
    assert r1 is not None
    assert r1.best_sequence.sequence_label == "PA→PB→DA→DB"

    # 2. Favor PA -> PB -> DB -> DA
    # Order: 0 -> 1 -> 3 -> 2
    m2 = [[0.0 if i == j else 500.0 for j in range(4)] for i in range(4)]
    m2[0][2] = 200.0  # direct A
    m2[1][3] = 200.0  # direct B
    m2[0][1] = 10.0
    m2[1][3] = 190.0
    m2[3][2] = 10.0
    r2 = await evaluate_pairwise_detour(
        provider=ConfigurableMatrixRoutingProvider(m2),
        pickup_a=pts[0],
        dest_a=pts[2],
        pickup_b=pts[1],
        dest_b=pts[3],
        max_extra_a=10,
        max_extra_b=10,
    )
    assert r2 is not None
    assert r2.best_sequence.sequence_label == "PA→PB→DB→DA"

    # 3. Favor PB -> PA -> DA -> DB
    # Order: 1 -> 0 -> 2 -> 3
    m3 = [[0.0 if i == j else 500.0 for j in range(4)] for i in range(4)]
    m3[0][2] = 200.0
    m3[1][3] = 200.0
    m3[1][0] = 10.0
    m3[0][2] = 190.0
    m3[2][3] = 10.0
    r3 = await evaluate_pairwise_detour(
        provider=ConfigurableMatrixRoutingProvider(m3),
        pickup_a=pts[0],
        dest_a=pts[2],
        pickup_b=pts[1],
        dest_b=pts[3],
        max_extra_a=10,
        max_extra_b=10,
    )
    assert r3 is not None
    assert r3.best_sequence.sequence_label == "PB→PA→DA→DB"

    # 4. Favor PB -> PA -> DB -> DA
    # Order: 1 -> 0 -> 3 -> 2
    m4 = [[0.0 if i == j else 500.0 for j in range(4)] for i in range(4)]
    m4[0][2] = 200.0
    m4[1][3] = 200.0
    m4[1][0] = 10.0
    m4[0][3] = 10.0
    m4[3][2] = 190.0
    r4 = await evaluate_pairwise_detour(
        provider=ConfigurableMatrixRoutingProvider(m4),
        pickup_a=pts[0],
        dest_a=pts[2],
        pickup_b=pts[1],
        dest_b=pts[3],
        max_extra_a=10,
        max_extra_b=10,
    )
    assert r4 is not None
    assert r4.best_sequence.sequence_label == "PB→PA→DB→DA"


@pytest.mark.asyncio
async def test_detour_exact_allowance_boundary_and_zero_allowance() -> None:
    pts = [(19.0, 72.0), (19.01, 72.01), (19.1, 72.1), (19.11, 72.11)]

    # Matrix where detour is exactly 5.0 minutes (300 seconds)
    m = [[0.0 if i == j else 500.0 for j in range(4)] for i in range(4)]
    m[0][2] = 600.0  # direct A = 10 min
    m[1][3] = 600.0  # direct B = 10 min
    # Sequence PA -> PB -> DA -> DB:
    m[0][1] = 300.0  # 5 min
    m[1][2] = 600.0  # 10 min -> time_a = 900s (detour = 300s = 5.0 min)
    m[2][3] = 300.0  # 5 min -> time_b = 900s (detour = 300s = 5.0 min)

    # Exactly 5 min allowed: Accepted
    r_exact = await evaluate_pairwise_detour(
        provider=ConfigurableMatrixRoutingProvider(m),
        pickup_a=pts[0],
        dest_a=pts[2],
        pickup_b=pts[1],
        dest_b=pts[3],
        max_extra_a=5,
        max_extra_b=5,
    )
    assert r_exact is not None
    assert r_exact.best_sequence.detour_a_minutes == pytest.approx(5.0)

    # 4 min allowed: Rejected
    r_over = await evaluate_pairwise_detour(
        provider=ConfigurableMatrixRoutingProvider(m),
        pickup_a=pts[0],
        dest_a=pts[2],
        pickup_b=pts[1],
        dest_b=pts[3],
        max_extra_a=4,
        max_extra_b=5,
    )
    assert r_over is None

    # Zero allowance test: 0 min detour allowed with 0 detour route
    m_zero = [[0.0 for _ in range(4)] for _ in range(4)]
    r_zero = await evaluate_pairwise_detour(
        provider=ConfigurableMatrixRoutingProvider(m_zero),
        pickup_a=pts[0],
        dest_a=pts[2],
        pickup_b=pts[1],
        dest_b=pts[3],
        max_extra_a=0,
        max_extra_b=0,
    )
    assert r_zero is not None
    assert r_zero.best_sequence.detour_a_minutes == 0.0
    assert r_zero.best_sequence.detour_b_minutes == 0.0


def test_deterministic_proposal_id_and_canonical_symmetry() -> None:
    import uuid

    from app.matching.service import _make_proposal_id

    id1 = uuid.uuid4()
    id2 = uuid.uuid4()

    pid_forward = _make_proposal_id(id1, id2)
    pid_reverse = _make_proposal_id(id2, id1)

    assert pid_forward == pid_reverse
    assert isinstance(pid_forward, uuid.UUID)


def test_spatial_parsing_robustness_all_representations() -> None:
    from geoalchemy2.elements import WKBElement, WKTElement

    # 1. WKT string
    lat, lon = parse_point_coordinates("POINT(72.8687 19.0657)")
    assert pytest.approx(lat, abs=1e-4) == 19.0657
    assert pytest.approx(lon, abs=1e-4) == 72.8687

    # 2. WKTElement
    elem = WKTElement("POINT(72.8687 19.0657)", srid=4326)
    lat, lon = parse_point_coordinates(elem)
    assert pytest.approx(lat, abs=1e-4) == 19.0657
    assert pytest.approx(lon, abs=1e-4) == 72.8687

    # 3. PostGIS Hex EWKB string (as returned by asyncpg/Postgres raw queries)
    hex_str = "0101000020E61000004182E2C798375240E25817B7D1103340"
    lat, lon = parse_point_coordinates(hex_str)
    assert pytest.approx(lat, abs=1e-4) == 19.0657
    assert pytest.approx(lon, abs=1e-4) == 72.8687

    # 4. Binary WKB bytes
    wkb_bytes = bytes.fromhex(hex_str)
    lat, lon = parse_point_coordinates(wkb_bytes)
    assert pytest.approx(lat, abs=1e-4) == 19.0657
    assert pytest.approx(lon, abs=1e-4) == 72.8687

    # 5. GeoAlchemy2 WKBElement wrapping bytes
    wkb_elem = WKBElement(wkb_bytes, srid=4326)
    lat, lon = parse_point_coordinates(wkb_elem)
    assert pytest.approx(lat, abs=1e-4) == 19.0657
    assert pytest.approx(lon, abs=1e-4) == 72.8687
