"""Integration tests for Phase 5A decisions DEC-001, DEC-002, DEC-003, and Mumbai routing."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.main import app
from app.matching.detour import evaluate_pairwise_detour
from app.matching.service import (
    MatchProposal,
    StopInfo,
    _compute_passenger_metrics,
    _make_proposal_id,
    enrich_proposal_geometry,
    run_matching,
)
from app.models.ride_request import RideRequest, RideRequestStatus
from app.routing.base import (
    DistanceMetric,
    DistanceSource,
    MultiWaypointRoute,
    RouteLeg,
    RoutingCapability,
    RoutingMatrixResult,
    RoutingProvider,
)
from app.schemas.auth import AuthUser


def _empty_consent_db() -> AsyncMock:
    """Async session double returning an empty SQLAlchemy scalar result."""
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value = []
    db.execute.return_value = result
    return db


class MockPhase5ARoutingProvider(RoutingProvider):
    """Controlled mock routing provider for testing Phase 5A decisions."""

    def __init__(self, max_routed_candidates: int = 3) -> None:
        self.max_routed_candidates = max_routed_candidates
        self.matrix_call_count = 0
        self.route_call_count = 0
        self.matrix_called_with: list[list[tuple[float, float]]] = []

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
        return "osrm"

    async def get_route_matrix(
        self, points: list[tuple[float, float]]
    ) -> RoutingMatrixResult:
        self.matrix_call_count += 1
        self.matrix_called_with.append(points)
        # Standard 4x4 matrix for testing: 0=PA, 1=PB, 2=DA, 3=DB
        # Sequence PA(0) -> PB(1) -> DA(2) -> DB(3):
        # 0->1: 2 min (120s), 1000m
        # 1->2: 8 min (480s), 5000m
        # 2->3: 3 min (180s), 1500m
        # Direct A (0->2): 9 min (540s), 5500m -> Detour A: (120+480 - 540) = 60s = 1.0 min
        # Direct B (1->3): 10 min (600s), 6000m -> Detour B: (480+180 - 600) = 60s = 1.0 min
        durations = [
            [0.0, 120.0, 540.0, 660.0],
            [120.0, 0.0, 480.0, 600.0],
            [540.0, 480.0, 0.0, 180.0],
            [660.0, 600.0, 180.0, 0.0],
        ]
        distances = [
            [0.0, 1000.0, 5500.0, 7000.0],
            [1000.0, 0.0, 5000.0, 6000.0],
            [5500.0, 5000.0, 0.0, 1500.0],
            [7000.0, 6000.0, 1500.0, 0.0],
        ]
        return RoutingMatrixResult(
            durations=durations,
            distances=distances,
            is_approximate=False,
            provider_name="osrm",
            routing_accuracy="road_network_duration_road_network_distance",
            notice="Mock OSRM matrix",
        )

    async def get_multi_waypoint_route(
        self,
        waypoints: list[tuple[float, float]],
        stop_ids: list[str] | None = None,
        stop_labels: list[str | None] | None = None,
    ) -> MultiWaypointRoute:
        self.route_call_count += 1
        coords = [[round(lon, 6), round(lat, 6)] for lat, lon in waypoints]
        detailed_coords = []
        for i in range(len(coords) - 1):
            detailed_coords.append(coords[i])
            mid_lon = (coords[i][0] + coords[i + 1][0]) / 2
            mid_lat = (coords[i][1] + coords[i + 1][1]) / 2
            detailed_coords.append([round(mid_lon, 6), round(mid_lat, 6)])
        detailed_coords.append(coords[-1])

        legs = []
        for i in range(len(waypoints) - 1):
            s_id = stop_ids[i] if stop_ids and i < len(stop_ids) else f"stop_{i}"
            e_id = (
                stop_ids[i + 1]
                if stop_ids and i + 1 < len(stop_ids)
                else f"stop_{i + 1}"
            )
            s_lbl = stop_labels[i] if stop_labels and i < len(stop_labels) else None
            e_lbl = (
                stop_labels[i + 1] if stop_labels and i + 1 < len(stop_labels) else None
            )
            legs.append(
                RouteLeg(
                    sequence=i + 1,
                    start_stop_id=str(s_id),
                    end_stop_id=str(e_id),
                    start_label=s_lbl,
                    end_label=e_lbl,
                    distance_meters=2500.0,
                    duration_seconds=300.0,
                )
            )

        return MultiWaypointRoute(
            total_distance=DistanceMetric(
                distance_meters=7500.0,
                source=DistanceSource.PROVIDER_ROAD_NETWORK_ROUTE,
                is_approximate=False,
                confidence_factor=1.0,
            ),
            total_duration_seconds=900.0,
            legs=legs,
            full_geometry_geojson={
                "type": "LineString",
                "coordinates": detailed_coords,
            },
            provider_name="osrm",
            routing_accuracy="road_network_duration_road_network_distance",
            routing_notice="Mock OSRM Route",
        )

    async def get_duration_matrix(
        self, points: list[tuple[float, float]]
    ) -> list[list[float]]:
        res = await self.get_route_matrix(points)
        return res.durations


@pytest.mark.asyncio
async def test_dec001_top1_proposal_geometry_enrichment_and_ondemand() -> None:
    """
    Verify DEC-001:
    - Match discovery enriches Top 1 proposal with full GeoJSON route geometry.
    - Proposals 2-5 have route_geometry is None.
    - On-demand enrichment populates geometry for proposals 2-5.
    """
    provider = MockPhase5ARoutingProvider()
    target_id = uuid.uuid4()
    user_id = uuid.uuid4()
    now = datetime.now(UTC)

    target_req = RideRequest(
        id=target_id,
        user_id=user_id,
        status=RideRequestStatus.ACTIVE,
        pickup_location="POINT(72.8687 19.0657)",
        destination="POINT(72.9060 19.1176)",
        departure_earliest=now + timedelta(minutes=10),
        departure_latest=now + timedelta(minutes=40),
        seats_requested=1,
        max_extra_minutes=15,
        pickup_label="BKC Maker Maxity",
        destination_label="Powai Hiranandani",
    )

    cand1_id = uuid.uuid4()
    cand2_id = uuid.uuid4()
    mock_candidates = [
        {
            "candidate_id": cand1_id,
            "candidate_user_id": uuid.uuid4(),
            "owner_name": "Aarav Sharma",
            "pickup_location": "POINT(72.8690 19.0660)",
            "destination": "POINT(72.9050 19.1170)",
            "pickup_label": "BKC One",
            "destination_label": "Powai Galleria",
            "seats_requested": 1,
            "max_extra_minutes": 15,
            "departure_earliest": now + timedelta(minutes=15),
            "departure_latest": now + timedelta(minutes=35),
            "pickup_distance_m": 45.0,
            "dest_distance_m": 120.0,
            "overlap_seconds": 1200.0,
        },
        {
            "candidate_id": cand2_id,
            "candidate_user_id": uuid.uuid4(),
            "owner_name": "Pooja Mehta",
            "pickup_location": "POINT(72.8695 19.0665)",
            "destination": "POINT(72.9040 19.1165)",
            "pickup_label": "BKC Godrej",
            "destination_label": "Powai Central",
            "seats_requested": 1,
            "max_extra_minutes": 15,
            "departure_earliest": now + timedelta(minutes=12),
            "departure_latest": now + timedelta(minutes=38),
            "pickup_distance_m": 95.0,
            "dest_distance_m": 220.0,
            "overlap_seconds": 1100.0,
        },
    ]

    with patch(
        "app.matching.service.discover_candidates",
        AsyncMock(return_value=mock_candidates),
    ):
        proposals = await run_matching(
            db=AsyncMock(), routing=provider, target=target_req
        )

    assert len(proposals) == 2

    # DEC-001 Check: Top 1 proposal MUST have route_geometry enriched
    top1 = proposals[0]
    assert top1.route_geometry is not None
    assert top1.route_geometry["type"] == "LineString"
    assert len(top1.route_geometry["coordinates"]) > 0
    assert top1.distance_source == DistanceSource.PROVIDER_ROAD_NETWORK_ROUTE.value
    assert not top1.distance_is_approximate
    assert not top1.is_route_approximate

    # DEC-001 Check: Proposal #2 MUST NOT have route_geometry enriched initially
    top2 = proposals[1]
    assert top2.route_geometry is None
    assert top2.distance_source == DistanceSource.PROVIDER_MATRIX_TABLE.value

    # Verify provider call count: 2 matrix calls, exactly 1 route call (Top 1 only)
    assert provider.matrix_call_count == 2
    assert provider.route_call_count == 1

    # On-demand enrichment test for Proposal #2:
    enriched_top2 = await enrich_proposal_geometry(top2, provider)
    assert enriched_top2 is not None
    assert enriched_top2.route_geometry is not None
    assert enriched_top2.route_geometry["type"] == "LineString"
    assert provider.route_call_count == 2


@pytest.mark.asyncio
async def test_dec002_candidate_routing_cap_at_3() -> None:
    """
    Verify DEC-002:
    - Discovery returns 5 candidates.
    - Routing provider has max_routed_candidates = 3.
    - Stage 3 evaluates exactly 3 candidates with matrix routing.
    """
    provider = MockPhase5ARoutingProvider(max_routed_candidates=3)
    target_id = uuid.uuid4()
    now = datetime.now(UTC)

    target_req = RideRequest(
        id=target_id,
        user_id=uuid.uuid4(),
        status=RideRequestStatus.ACTIVE,
        pickup_location="POINT(72.8687 19.0657)",
        destination="POINT(72.9060 19.1176)",
        departure_earliest=now,
        departure_latest=now + timedelta(minutes=30),
        seats_requested=1,
        max_extra_minutes=15,
    )

    mock_candidates = [
        {
            "candidate_id": uuid.uuid4(),
            "candidate_user_id": uuid.uuid4(),
            "owner_name": f"User {i}",
            "pickup_location": "POINT(72.8690 19.0660)",
            "destination": "POINT(72.9050 19.1170)",
            "pickup_label": "BKC",
            "destination_label": "Powai",
            "seats_requested": 1,
            "max_extra_minutes": 15,
            "departure_earliest": now,
            "departure_latest": now + timedelta(minutes=30),
            "pickup_distance_m": float(i * 100),
            "dest_distance_m": float(i * 100),
            "overlap_seconds": 1800.0,
        }
        for i in range(1, 6)
    ]

    with patch(
        "app.matching.service.discover_candidates",
        AsyncMock(return_value=mock_candidates),
    ):
        proposals = await run_matching(
            db=AsyncMock(), routing=provider, target=target_req
        )

    # Exactly 3 candidates routed via Stage 3
    assert provider.matrix_call_count == 3
    assert len(proposals) == 3


@pytest.mark.asyncio
async def test_dec003_strictly_time_based_detour_gating() -> None:
    """
    Verify DEC-003:
    - Detour constraint is strictly time-based (detour_a_minutes <= max_extra_a).
    - Large distance detour does NOT reject a proposal.
    - Exceeding time tolerance DOES reject a proposal.
    """

    class TimeDetourProvider(RoutingProvider):
        @property
        def capabilities(self) -> RoutingCapability:
            return RoutingCapability.DURATION_MATRIX | RoutingCapability.DISTANCE_MATRIX

        @property
        def provider_name(self) -> str:
            return "test_time"

        async def get_route_matrix(
            self, points: list[tuple[float, float]]
        ) -> RoutingMatrixResult:
            durations = [
                [0.0, 300.0, 600.0, 900.0],
                [300.0, 0.0, 600.0, 600.0],
                [600.0, 600.0, 0.0, 300.0],
                [900.0, 600.0, 300.0, 0.0],
            ]
            distances = [
                [0.0, 5000.0, 5000.0, 20000.0],
                [5000.0, 0.0, 15000.0, 5000.0],
                [5000.0, 15000.0, 0.0, 5000.0],
                [20000.0, 5000.0, 5000.0, 0.0],
            ]
            return RoutingMatrixResult(
                durations=durations,
                distances=distances,
                is_approximate=False,
                provider_name="test_time",
                routing_accuracy="road_network_duration_road_network_distance",
            )

        async def get_duration_matrix(
            self, points: list[tuple[float, float]]
        ) -> list[list[float]]:
            res = await self.get_route_matrix(points)
            return res.durations

    provider = TimeDetourProvider()
    pts = [(19.0, 72.0), (19.01, 72.01), (19.1, 72.1), (19.11, 72.11)]

    # 1. Allowed extra time is 10 min -> 5 min detour is <= 10 -> ACCEPTED despite 15 km distance detour
    res_accepted = await evaluate_pairwise_detour(
        provider=provider,
        pickup_a=pts[0],
        dest_a=pts[2],
        pickup_b=pts[1],
        dest_b=pts[3],
        max_extra_a=10,
        max_extra_b=10,
    )
    assert res_accepted is not None
    assert res_accepted.best_sequence.detour_a_minutes == pytest.approx(5.0)
    assert res_accepted.best_sequence.detour_a_distance_meters > 0

    # 2. Allowed extra time is 2 min -> 5 min detour is > 2 -> REJECTED
    res_rejected = await evaluate_pairwise_detour(
        provider=provider,
        pickup_a=pts[0],
        dest_a=pts[2],
        pickup_b=pts[1],
        dest_b=pts[3],
        max_extra_a=2,
        max_extra_b=2,
    )
    assert res_rejected is None


@pytest.mark.asyncio
async def test_stage5_route_synthesis_failure_gracefully_degrades() -> None:
    """
    Verify system resilience:
    If Stage 5 Route API throws an exception, matching does NOT crash,
    retains matrix metrics, and synthesizes fallback straight-line LineString.
    """

    class CrashingRouteProvider(MockPhase5ARoutingProvider):
        async def get_multi_waypoint_route(self, *args, **kwargs) -> MultiWaypointRoute:
            raise httpx.RequestError("OSRM Route API timeout simulation")

    provider = CrashingRouteProvider()
    target_id = uuid.uuid4()
    now = datetime.now(UTC)

    target_req = RideRequest(
        id=target_id,
        user_id=uuid.uuid4(),
        status=RideRequestStatus.ACTIVE,
        pickup_location="POINT(72.8687 19.0657)",
        destination="POINT(72.9060 19.1176)",
        departure_earliest=now,
        departure_latest=now + timedelta(minutes=30),
        seats_requested=1,
        max_extra_minutes=15,
    )

    mock_candidates = [
        {
            "candidate_id": uuid.uuid4(),
            "candidate_user_id": uuid.uuid4(),
            "owner_name": "Test User",
            "pickup_location": "POINT(72.8690 19.0660)",
            "destination": "POINT(72.9050 19.1170)",
            "pickup_label": "BKC",
            "destination_label": "Powai",
            "seats_requested": 1,
            "max_extra_minutes": 15,
            "departure_earliest": now,
            "departure_latest": now + timedelta(minutes=30),
            "pickup_distance_m": 50.0,
            "dest_distance_m": 50.0,
            "overlap_seconds": 1800.0,
        }
    ]

    with patch(
        "app.matching.service.discover_candidates",
        AsyncMock(return_value=mock_candidates),
    ):
        proposals = await run_matching(
            db=AsyncMock(), routing=provider, target=target_req
        )

    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal.route_geometry is not None
    assert proposal.route_geometry["type"] == "LineString"
    assert proposal.routing_accuracy == "matrix_duration_synthesized_geometry"
    assert proposal.is_route_approximate
    assert proposal.distance_is_approximate


@pytest.mark.asyncio
async def test_get_proposal_detail_api_endpoint_ondemand_enrichment() -> None:
    """
    Test GET /api/v1/matches/{proposal_id}?request_id={request_id}
    verifying on-demand route geometry enrichment via the FastAPI endpoint.
    """
    target_id = uuid.uuid4()
    user_id = uuid.uuid4()
    now = datetime.now(UTC)

    target_req = RideRequest(
        id=target_id,
        user_id=user_id,
        status=RideRequestStatus.ACTIVE,
        pickup_location="POINT(72.8687 19.0657)",
        destination="POINT(72.9060 19.1176)",
        departure_earliest=now,
        departure_latest=now + timedelta(minutes=30),
        seats_requested=1,
        max_extra_minutes=15,
    )

    auth_user = AuthUser(
        id=user_id,
        email="test@smartshare.in",
        role="authenticated",
        user_metadata={},
    )

    provider = MockPhase5ARoutingProvider()

    cand1_id = uuid.uuid4()
    cand2_id = uuid.uuid4()
    mock_candidates = [
        {
            "candidate_id": cand1_id,
            "candidate_user_id": uuid.uuid4(),
            "owner_name": "User 1",
            "pickup_location": "POINT(72.8690 19.0660)",
            "destination": "POINT(72.9050 19.1170)",
            "pickup_label": "BKC",
            "destination_label": "Powai",
            "seats_requested": 1,
            "max_extra_minutes": 15,
            "departure_earliest": now,
            "departure_latest": now + timedelta(minutes=30),
            "pickup_distance_m": 40.0,
            "dest_distance_m": 40.0,
            "overlap_seconds": 1800.0,
        },
        {
            "candidate_id": cand2_id,
            "candidate_user_id": uuid.uuid4(),
            "owner_name": "User 2",
            "pickup_location": "POINT(72.8695 19.0665)",
            "destination": "POINT(72.9045 19.1165)",
            "pickup_label": "BKC 2",
            "destination_label": "Powai 2",
            "seats_requested": 1,
            "max_extra_minutes": 15,
            "departure_earliest": now,
            "departure_latest": now + timedelta(minutes=30),
            "pickup_distance_m": 80.0,
            "dest_distance_m": 80.0,
            "overlap_seconds": 1800.0,
        },
    ]

    prop2_id = _make_proposal_id(target_id, cand2_id)

    app.dependency_overrides[get_current_user] = lambda: auth_user
    app.dependency_overrides[get_db] = lambda: _empty_consent_db()

    with (
        patch(
            "app.api.v1.endpoints.matching._get_active_owned_request",
            AsyncMock(return_value=target_req),
        ),
        patch(
            "app.api.v1.endpoints.matching.get_routing_provider",
            return_value=provider,
        ),
        patch(
            "app.matching.service.discover_candidates",
            AsyncMock(return_value=mock_candidates),
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                f"/api/v1/matches/{prop2_id}?request_id={target_id}"
            )
            assert resp.status_code == 200
            data = resp.json()["data"]

            # Proposal #2 was enriched on-demand with route geometry
            assert data["proposal_id"] == str(prop2_id)
            assert data["route_geometry"] is not None
            assert data["route_geometry"]["type"] == "LineString"
            assert len(data["route_geometry"]["coordinates"]) > 0
            assert len(data["route_legs"]) == 3
            assert data["total_shared_distance_meters"] > 0
            assert data["total_shared_duration_seconds"] > 0

    app.dependency_overrides.clear()


# ==============================================================================
# Task 1: Final Route API Feasibility Revalidation Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_route_api_revalidation_accepts_when_both_pass() -> None:
    """Verify Route API revalidation accepts candidate when continuous route satisfies limits."""
    provider = MockPhase5ARoutingProvider()
    target_id = uuid.uuid4()
    now = datetime.now(UTC)

    target_req = RideRequest(
        id=target_id,
        user_id=uuid.uuid4(),
        status=RideRequestStatus.ACTIVE,
        pickup_location="POINT(72.8687 19.0657)",
        destination="POINT(72.9060 19.1176)",
        departure_earliest=now,
        departure_latest=now + timedelta(minutes=30),
        seats_requested=1,
        max_extra_minutes=10,
    )

    mock_candidates = [
        {
            "candidate_id": uuid.uuid4(),
            "candidate_user_id": uuid.uuid4(),
            "owner_name": "Rohan Deshmukh",
            "pickup_location": "POINT(72.8690 19.0660)",
            "destination": "POINT(72.9050 19.1170)",
            "pickup_label": "BKC",
            "destination_label": "Powai",
            "seats_requested": 1,
            "max_extra_minutes": 10,
            "departure_earliest": now,
            "departure_latest": now + timedelta(minutes=30),
            "pickup_distance_m": 50.0,
            "dest_distance_m": 50.0,
            "overlap_seconds": 1800.0,
        }
    ]

    with patch(
        "app.matching.service.discover_candidates",
        AsyncMock(return_value=mock_candidates),
    ):
        proposals = await run_matching(
            db=AsyncMock(), routing=provider, target=target_req
        )

    assert len(proposals) == 1
    p = proposals[0]
    assert p.route_geometry is not None
    assert p.detour_target_minutes <= 10.0
    assert p.detour_candidate_minutes <= 10.0


@pytest.mark.asyncio
async def test_route_api_revalidation_rejects_when_passenger_a_exceeds() -> None:
    """Verify proposal is rejected when Route API continuous route exceeds Passenger A's limit."""

    class PassengerAExceededProvider(MockPhase5ARoutingProvider):
        async def get_multi_waypoint_route(
            self, waypoints, stop_ids=None, stop_labels=None
        ) -> MultiWaypointRoute:
            # Massive detour for passenger A: Leg 1 is 20 minutes (1200s), exceeds max_extra_a (15 min)
            legs = [
                RouteLeg(
                    sequence=1,
                    start_stop_id="s1",
                    end_stop_id="s2",
                    distance_meters=15000.0,
                    duration_seconds=1200.0,
                ),
                RouteLeg(
                    sequence=2,
                    start_stop_id="s2",
                    end_stop_id="s3",
                    distance_meters=5000.0,
                    duration_seconds=600.0,
                ),
                RouteLeg(
                    sequence=3,
                    start_stop_id="s3",
                    end_stop_id="s4",
                    distance_meters=1000.0,
                    duration_seconds=120.0,
                ),
            ]
            coords = [[round(lon, 6), round(lat, 6)] for lat, lon in waypoints]
            return MultiWaypointRoute(
                total_distance=DistanceMetric(
                    distance_meters=21000.0,
                    source=DistanceSource.PROVIDER_ROAD_NETWORK_ROUTE,
                    is_approximate=False,
                ),
                total_duration_seconds=1920.0,
                legs=legs,
                full_geometry_geojson={
                    "type": "LineString",
                    "coordinates": coords,
                },
                provider_name="osrm",
            )

    provider = PassengerAExceededProvider()
    target_id = uuid.uuid4()
    now = datetime.now(UTC)

    target_req = RideRequest(
        id=target_id,
        user_id=uuid.uuid4(),
        status=RideRequestStatus.ACTIVE,
        pickup_location="POINT(72.8687 19.0657)",
        destination="POINT(72.9060 19.1176)",
        departure_earliest=now,
        departure_latest=now + timedelta(minutes=30),
        seats_requested=1,
        max_extra_minutes=15,
    )

    mock_candidates = [
        {
            "candidate_id": uuid.uuid4(),
            "candidate_user_id": uuid.uuid4(),
            "owner_name": "Candidate 1",
            "pickup_location": "POINT(72.8690 19.0660)",
            "destination": "POINT(72.9050 19.1170)",
            "pickup_label": "BKC",
            "destination_label": "Powai",
            "seats_requested": 1,
            "max_extra_minutes": 15,
            "departure_earliest": now,
            "departure_latest": now + timedelta(minutes=30),
            "pickup_distance_m": 50.0,
            "dest_distance_m": 50.0,
            "overlap_seconds": 1800.0,
        }
    ]

    with patch(
        "app.matching.service.discover_candidates",
        AsyncMock(return_value=mock_candidates),
    ):
        proposals = await run_matching(
            db=AsyncMock(), routing=provider, target=target_req
        )

    assert len(proposals) == 0


@pytest.mark.asyncio
async def test_route_api_revalidation_rejects_when_passenger_b_exceeds() -> None:
    """Verify proposal is rejected when Route API continuous route exceeds Passenger B's limit."""

    class PassengerBExceededProvider(MockPhase5ARoutingProvider):
        async def get_multi_waypoint_route(
            self, waypoints, stop_ids=None, stop_labels=None
        ) -> MultiWaypointRoute:
            # Massive detour for passenger B: Leg 2 + Leg 3 is 2000s, exceeds max_extra_b (5 min = 300s)
            legs = [
                RouteLeg(
                    sequence=1,
                    start_stop_id="s1",
                    end_stop_id="s2",
                    distance_meters=1000.0,
                    duration_seconds=100.0,
                ),
                RouteLeg(
                    sequence=2,
                    start_stop_id="s2",
                    end_stop_id="s3",
                    distance_meters=12000.0,
                    duration_seconds=1200.0,
                ),
                RouteLeg(
                    sequence=3,
                    start_stop_id="s3",
                    end_stop_id="s4",
                    distance_meters=8000.0,
                    duration_seconds=800.0,
                ),
            ]
            coords = [[round(lon, 6), round(lat, 6)] for lat, lon in waypoints]
            return MultiWaypointRoute(
                total_distance=DistanceMetric(
                    distance_meters=21000.0,
                    source=DistanceSource.PROVIDER_ROAD_NETWORK_ROUTE,
                    is_approximate=False,
                ),
                total_duration_seconds=2100.0,
                legs=legs,
                full_geometry_geojson={
                    "type": "LineString",
                    "coordinates": coords,
                },
                provider_name="osrm",
            )

    provider = PassengerBExceededProvider()
    target_id = uuid.uuid4()
    now = datetime.now(UTC)

    target_req = RideRequest(
        id=target_id,
        user_id=uuid.uuid4(),
        status=RideRequestStatus.ACTIVE,
        pickup_location="POINT(72.8687 19.0657)",
        destination="POINT(72.9060 19.1176)",
        departure_earliest=now,
        departure_latest=now + timedelta(minutes=30),
        seats_requested=1,
        max_extra_minutes=30,  # Passenger A is fine
    )

    mock_candidates = [
        {
            "candidate_id": uuid.uuid4(),
            "candidate_user_id": uuid.uuid4(),
            "owner_name": "Candidate Strict",
            "pickup_location": "POINT(72.8690 19.0660)",
            "destination": "POINT(72.9050 19.1170)",
            "pickup_label": "BKC",
            "destination_label": "Powai",
            "seats_requested": 1,
            "max_extra_minutes": 5,  # Passenger B has strict 5 min tolerance
            "departure_earliest": now,
            "departure_latest": now + timedelta(minutes=30),
            "pickup_distance_m": 50.0,
            "dest_distance_m": 50.0,
            "overlap_seconds": 1800.0,
        }
    ]

    with patch(
        "app.matching.service.discover_candidates",
        AsyncMock(return_value=mock_candidates),
    ):
        proposals = await run_matching(
            db=AsyncMock(), routing=provider, target=target_req
        )

    assert len(proposals) == 0


@pytest.mark.asyncio
async def test_route_api_revalidation_promotes_next_candidate_if_top1_rejected() -> (
    None
):
    """Verify that if Top 1 is rejected by Route API, the next candidate is evaluated and promoted."""
    call_order = []

    class RejectionPromotionProvider(MockPhase5ARoutingProvider):
        async def get_multi_waypoint_route(
            self, waypoints, stop_ids=None, stop_labels=None
        ) -> MultiWaypointRoute:
            coords = [[round(lon, 6), round(lat, 6)] for lat, lon in waypoints]
            if len(call_order) == 0:
                call_order.append("cand1_exceeded")
                legs = [
                    RouteLeg(
                        sequence=1,
                        start_stop_id="s1",
                        end_stop_id="s2",
                        distance_meters=1000.0,
                        duration_seconds=1800.0,
                    ),
                    RouteLeg(
                        sequence=2,
                        start_stop_id="s2",
                        end_stop_id="s3",
                        distance_meters=5000.0,
                        duration_seconds=500.0,
                    ),
                    RouteLeg(
                        sequence=3,
                        start_stop_id="s3",
                        end_stop_id="s4",
                        distance_meters=1000.0,
                        duration_seconds=100.0,
                    ),
                ]
            else:
                call_order.append("cand2_valid")
                legs = [
                    RouteLeg(
                        sequence=1,
                        start_stop_id="s1",
                        end_stop_id="s2",
                        distance_meters=1000.0,
                        duration_seconds=120.0,
                    ),
                    RouteLeg(
                        sequence=2,
                        start_stop_id="s2",
                        end_stop_id="s3",
                        distance_meters=5000.0,
                        duration_seconds=480.0,
                    ),
                    RouteLeg(
                        sequence=3,
                        start_stop_id="s3",
                        end_stop_id="s4",
                        distance_meters=1000.0,
                        duration_seconds=180.0,
                    ),
                ]
            return MultiWaypointRoute(
                total_distance=DistanceMetric(
                    distance_meters=7000.0,
                    source=DistanceSource.PROVIDER_ROAD_NETWORK_ROUTE,
                    is_approximate=False,
                ),
                total_duration_seconds=sum(leg.duration_seconds for leg in legs),
                legs=legs,
                full_geometry_geojson={
                    "type": "LineString",
                    "coordinates": coords,
                },
                provider_name="osrm",
            )

    provider = RejectionPromotionProvider()
    target_id = uuid.uuid4()
    cand1_id = uuid.uuid4()
    cand2_id = uuid.uuid4()
    now = datetime.now(UTC)

    target_req = RideRequest(
        id=target_id,
        user_id=uuid.uuid4(),
        status=RideRequestStatus.ACTIVE,
        pickup_location="POINT(72.8687 19.0657)",
        destination="POINT(72.9060 19.1176)",
        departure_earliest=now,
        departure_latest=now + timedelta(minutes=30),
        seats_requested=1,
        max_extra_minutes=15,
    )

    mock_candidates = [
        {
            "candidate_id": cand1_id,
            "candidate_user_id": uuid.uuid4(),
            "owner_name": "Candidate 1 (will exceed)",
            "pickup_location": "POINT(72.8690 19.0660)",
            "destination": "POINT(72.9050 19.1170)",
            "pickup_label": "BKC",
            "destination_label": "Powai",
            "seats_requested": 1,
            "max_extra_minutes": 15,
            "departure_earliest": now,
            "departure_latest": now + timedelta(minutes=30),
            "pickup_distance_m": 40.0,
            "dest_distance_m": 40.0,
            "overlap_seconds": 1800.0,
        },
        {
            "candidate_id": cand2_id,
            "candidate_user_id": uuid.uuid4(),
            "owner_name": "Candidate 2 (promoted)",
            "pickup_location": "POINT(72.8695 19.0665)",
            "destination": "POINT(72.9045 19.1165)",
            "pickup_label": "BKC 2",
            "destination_label": "Powai 2",
            "seats_requested": 1,
            "max_extra_minutes": 15,
            "departure_earliest": now,
            "departure_latest": now + timedelta(minutes=30),
            "pickup_distance_m": 80.0,
            "dest_distance_m": 80.0,
            "overlap_seconds": 1800.0,
        },
    ]

    with patch(
        "app.matching.service.discover_candidates",
        AsyncMock(return_value=mock_candidates),
    ):
        proposals = await run_matching(
            db=AsyncMock(), routing=provider, target=target_req
        )

    # Candidate 2 was promoted to Top 1 and enriched with geometry
    assert len(proposals) == 1
    assert proposals[0].candidate_request_id == cand2_id
    assert proposals[0].route_geometry is not None
    assert call_order == ["cand1_exceeded", "cand2_valid"]


@pytest.mark.asyncio
async def test_route_api_revalidation_differing_durations_both_feasible() -> None:
    """Verify that when Route API duration differs from matrix duration but remains feasible, proposal is updated."""

    class SlightDifferenceProvider(MockPhase5ARoutingProvider):
        async def get_multi_waypoint_route(
            self, waypoints, stop_ids=None, stop_labels=None
        ) -> MultiWaypointRoute:
            legs = [
                RouteLeg(
                    sequence=1,
                    start_stop_id="s1",
                    end_stop_id="s2",
                    distance_meters=1100.0,
                    duration_seconds=140.0,
                ),
                RouteLeg(
                    sequence=2,
                    start_stop_id="s2",
                    end_stop_id="s3",
                    distance_meters=4900.0,
                    duration_seconds=460.0,
                ),
                RouteLeg(
                    sequence=3,
                    start_stop_id="s3",
                    end_stop_id="s4",
                    distance_meters=1600.0,
                    duration_seconds=190.0,
                ),
            ]
            coords = [[round(lon, 6), round(lat, 6)] for lat, lon in waypoints]
            return MultiWaypointRoute(
                total_distance=DistanceMetric(
                    distance_meters=7600.0,
                    source=DistanceSource.PROVIDER_ROAD_NETWORK_ROUTE,
                    is_approximate=False,
                ),
                total_duration_seconds=790.0,
                legs=legs,
                full_geometry_geojson={
                    "type": "LineString",
                    "coordinates": coords,
                },
                provider_name="osrm",
            )

    provider = SlightDifferenceProvider()
    target_id = uuid.uuid4()
    now = datetime.now(UTC)

    target_req = RideRequest(
        id=target_id,
        user_id=uuid.uuid4(),
        status=RideRequestStatus.ACTIVE,
        pickup_location="POINT(72.8687 19.0657)",
        destination="POINT(72.9060 19.1176)",
        departure_earliest=now,
        departure_latest=now + timedelta(minutes=30),
        seats_requested=1,
        max_extra_minutes=15,
    )

    mock_candidates = [
        {
            "candidate_id": uuid.uuid4(),
            "candidate_user_id": uuid.uuid4(),
            "owner_name": "Candidate Valid",
            "pickup_location": "POINT(72.8690 19.0660)",
            "destination": "POINT(72.9050 19.1170)",
            "pickup_label": "BKC",
            "destination_label": "Powai",
            "seats_requested": 1,
            "max_extra_minutes": 15,
            "departure_earliest": now,
            "departure_latest": now + timedelta(minutes=30),
            "pickup_distance_m": 50.0,
            "dest_distance_m": 50.0,
            "overlap_seconds": 1800.0,
        }
    ]

    with patch(
        "app.matching.service.discover_candidates",
        AsyncMock(return_value=mock_candidates),
    ):
        proposals = await run_matching(
            db=AsyncMock(), routing=provider, target=target_req
        )

    assert len(proposals) == 1
    p = proposals[0]
    assert p.total_shared_duration_seconds == 790.0
    assert p.total_shared_distance_meters == 7600.0
    assert p.detour_target_minutes == pytest.approx(1.0, abs=0.1)


# ==============================================================================
# Task 2: Passenger Journey Distance & Duration Correctness Across 4 Permutations
# ==============================================================================


def test_passenger_journey_metrics_all_four_permutations_exact_math() -> None:
    """
    Verify exact passenger journey distance and duration computation across all
    four valid pairwise permutations using deliberately distinct leg metrics.
    """
    from app.matching.scoring import ScoreBreakdown

    target_id = uuid.uuid4()
    cand_id = uuid.uuid4()

    legs = [
        RouteLeg(
            sequence=1,
            start_stop_id="s1",
            end_stop_id="s2",
            distance_meters=1100.0,
            duration_seconds=110.0,
        ),
        RouteLeg(
            sequence=2,
            start_stop_id="s2",
            end_stop_id="s3",
            distance_meters=2200.0,
            duration_seconds=220.0,
        ),
        RouteLeg(
            sequence=3,
            start_stop_id="s3",
            end_stop_id="s4",
            distance_meters=3300.0,
            duration_seconds=330.0,
        ),
    ]

    direct_a_dist = 2000.0
    direct_a_dur = 200.0
    direct_b_dist = 3000.0
    direct_b_dur = 300.0

    permutations = [
        # 1. PA -> PB -> DA -> DB
        (
            [
                ("PA", target_id),
                ("PB", cand_id),
                ("DA", target_id),
                ("DB", cand_id),
            ],
            3300.0,
            330.0,
            5500.0,
            550.0,
        ),
        # 2. PA -> PB -> DB -> DA
        (
            [
                ("PA", target_id),
                ("PB", cand_id),
                ("DB", cand_id),
                ("DA", target_id),
            ],
            6600.0,
            660.0,
            2200.0,
            220.0,
        ),
        # 3. PB -> PA -> DA -> DB
        (
            [
                ("PB", cand_id),
                ("PA", target_id),
                ("DA", target_id),
                ("DB", cand_id),
            ],
            2200.0,
            220.0,
            6600.0,
            660.0,
        ),
        # 4. PB -> PA -> DB -> DA
        (
            [
                ("PB", cand_id),
                ("PA", target_id),
                ("DB", cand_id),
                ("DA", target_id),
            ],
            5500.0,
            550.0,
            3300.0,
            330.0,
        ),
    ]

    for stop_defs, exp_a_dist, exp_a_dur, exp_b_dist, exp_b_dur in permutations:
        stops = [
            StopInfo(
                sequence=idx + 1,
                stop_type="PICKUP" if code.startswith("P") else "DROPOFF",
                latitude=19.0 + idx * 0.01,
                longitude=72.8 + idx * 0.01,
                passenger_request_id=p_id,
                label=code,
            )
            for idx, (code, p_id) in enumerate(stop_defs)
        ]

        now = datetime.now(UTC)
        proposal = MatchProposal(
            proposal_id=uuid.uuid4(),
            target_request_id=target_id,
            candidate_request_id=cand_id,
            candidate_user_id=uuid.uuid4(),
            candidate_display_name="Test Candidate",
            candidate_pickup_lat=19.01,
            candidate_pickup_lon=72.81,
            candidate_dest_lat=19.11,
            candidate_dest_lon=72.91,
            candidate_pickup_label="PB",
            candidate_dest_label="DB",
            candidate_seats=1,
            candidate_max_extra_minutes=15,
            target_max_extra_minutes=15,
            candidate_departure_earliest=now,
            candidate_departure_latest=now + timedelta(minutes=30),
            pickup_distance_m=100.0,
            dest_distance_m=100.0,
            shared_departure_start=now,
            shared_departure_end=now + timedelta(minutes=30),
            detour_target_minutes=0.0,
            detour_candidate_minutes=0.0,
            best_sequence_label="→".join(c for c, _ in stop_defs),
            stops=stops,
            total_shared_duration_seconds=sum(leg.duration_seconds for leg in legs),
            total_shared_distance_m=sum(leg.distance_meters for leg in legs),
            is_route_approximate=False,
            routing_notice="",
            scores=ScoreBreakdown(1.0, 1.0, 1.0, 1.0, 1.0),
            created_at=now,
            direct_a_dist_m=direct_a_dist,
            direct_a_dur_s=direct_a_dur,
            direct_b_dist_m=direct_b_dist,
            direct_b_dur_s=direct_b_dur,
        )

        metrics = _compute_passenger_metrics(
            proposal=proposal,
            legs=legs,
            source=DistanceSource.PROVIDER_ROAD_NETWORK_ROUTE,
            is_approximate=False,
        )

        mA = metrics[str(target_id)]
        mB = metrics[str(cand_id)]

        assert mA.solo_direct_distance_meters == direct_a_dist
        assert mA.solo_direct_duration_seconds == direct_a_dur
        assert mB.solo_direct_distance_meters == direct_b_dist
        assert mB.solo_direct_duration_seconds == direct_b_dur

        assert mA.pooled_journey_distance_meters == exp_a_dist
        assert mA.pooled_journey_duration_seconds == exp_a_dur
        assert mB.pooled_journey_distance_meters == exp_b_dist
        assert mB.pooled_journey_duration_seconds == exp_b_dur

        assert mA.detour_distance_meters == max(0.0, exp_a_dist - direct_a_dist)
        assert mA.detour_duration_minutes == pytest.approx(
            max(0.0, (exp_a_dur - direct_a_dur) / 60.0)
        )
        assert mB.detour_distance_meters == max(0.0, exp_b_dist - direct_b_dist)
        assert mB.detour_duration_minutes == pytest.approx(
            max(0.0, (exp_b_dur - direct_b_dur) / 60.0)
        )


# ==============================================================================
# Task 3: On-Demand Proposal Freshness & Lifecycle Safety Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_proposal_detail_candidate_destination_edited() -> None:
    """Verify that when a candidate edits destination, on-demand proposal reflects new coordinates."""
    target_id = uuid.uuid4()
    user_id = uuid.uuid4()
    cand_id = uuid.uuid4()
    now = datetime.now(UTC)

    target_req = RideRequest(
        id=target_id,
        user_id=user_id,
        status=RideRequestStatus.ACTIVE,
        pickup_location="POINT(72.8687 19.0657)",
        destination="POINT(72.9060 19.1176)",
        departure_earliest=now,
        departure_latest=now + timedelta(minutes=30),
        seats_requested=1,
        max_extra_minutes=15,
    )

    auth_user = AuthUser(
        id=user_id,
        email="test@smartshare.in",
        role="authenticated",
        user_metadata={},
    )
    provider = MockPhase5ARoutingProvider()
    prop_id = _make_proposal_id(target_id, cand_id)

    mock_candidate_updated = [
        {
            "candidate_id": cand_id,
            "candidate_user_id": uuid.uuid4(),
            "owner_name": "Edited User",
            "pickup_location": "POINT(72.8690 19.0660)",
            "destination": "POINT(72.9070 19.1180)",
            "pickup_label": "BKC",
            "destination_label": "Powai Edited",
            "seats_requested": 1,
            "max_extra_minutes": 15,
            "departure_earliest": now,
            "departure_latest": now + timedelta(minutes=30),
            "pickup_distance_m": 45.0,
            "dest_distance_m": 80.0,
            "overlap_seconds": 1800.0,
        }
    ]

    app.dependency_overrides[get_current_user] = lambda: auth_user
    app.dependency_overrides[get_db] = lambda: _empty_consent_db()

    with (
        patch(
            "app.api.v1.endpoints.matching._get_active_owned_request",
            AsyncMock(return_value=target_req),
        ),
        patch(
            "app.api.v1.endpoints.matching.get_routing_provider",
            return_value=provider,
        ),
        patch(
            "app.matching.service.discover_candidates",
            AsyncMock(return_value=mock_candidate_updated),
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/matches/{prop_id}?request_id={target_id}")
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert data["candidate"]["candidate_destination"]["label"] == "Powai Edited"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_proposal_detail_candidate_pickup_edited_out_of_range() -> None:
    """Verify that if candidate edits pickup beyond 2,000m, proposal detail returns 404."""
    target_id = uuid.uuid4()
    user_id = uuid.uuid4()
    cand_id = uuid.uuid4()
    now = datetime.now(UTC)

    target_req = RideRequest(
        id=target_id,
        user_id=user_id,
        status=RideRequestStatus.ACTIVE,
        pickup_location="POINT(72.8687 19.0657)",
        destination="POINT(72.9060 19.1176)",
        departure_earliest=now,
        departure_latest=now + timedelta(minutes=30),
        seats_requested=1,
        max_extra_minutes=15,
    )

    auth_user = AuthUser(
        id=user_id,
        email="test@smartshare.in",
        role="authenticated",
        user_metadata={},
    )
    provider = MockPhase5ARoutingProvider()
    prop_id = _make_proposal_id(target_id, cand_id)

    app.dependency_overrides[get_current_user] = lambda: auth_user
    app.dependency_overrides[get_db] = lambda: _empty_consent_db()

    with (
        patch(
            "app.api.v1.endpoints.matching._get_active_owned_request",
            AsyncMock(return_value=target_req),
        ),
        patch(
            "app.api.v1.endpoints.matching.get_routing_provider",
            return_value=provider,
        ),
        patch(
            "app.matching.service.discover_candidates",
            AsyncMock(return_value=[]),
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/matches/{prop_id}?request_id={target_id}")
            assert resp.status_code == 404
            assert "Proposal not found or no longer valid" in resp.json()["detail"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_proposal_detail_target_cancelled() -> None:
    """Verify that if target ride request is cancelled, proposal retrieval returns 400 Bad Request."""
    target_id = uuid.uuid4()
    user_id = uuid.uuid4()
    now = datetime.now(UTC)

    cancelled_target = RideRequest(
        id=target_id,
        user_id=user_id,
        status=RideRequestStatus.CANCELLED,
        pickup_location="POINT(72.8687 19.0657)",
        destination="POINT(72.9060 19.1176)",
        departure_earliest=now,
        departure_latest=now + timedelta(minutes=30),
        seats_requested=1,
        max_extra_minutes=15,
    )

    auth_user = AuthUser(
        id=user_id,
        email="test@smartshare.in",
        role="authenticated",
        user_metadata={},
    )
    prop_id = uuid.uuid4()

    app.dependency_overrides[get_current_user] = lambda: auth_user
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=cancelled_target)
    mock_db.execute = AsyncMock(return_value=mock_result)
    app.dependency_overrides[get_db] = lambda: mock_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/v1/matches/{prop_id}?request_id={target_id}")
        assert resp.status_code == 400
        assert "Ride request is not active or has expired" in resp.json()["detail"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_proposal_detail_candidate_cancelled() -> None:
    """Verify that if candidate cancels their request, proposal detail returns 404."""
    target_id = uuid.uuid4()
    user_id = uuid.uuid4()
    cand_id = uuid.uuid4()
    now = datetime.now(UTC)

    target_req = RideRequest(
        id=target_id,
        user_id=user_id,
        status=RideRequestStatus.ACTIVE,
        pickup_location="POINT(72.8687 19.0657)",
        destination="POINT(72.9060 19.1176)",
        departure_earliest=now,
        departure_latest=now + timedelta(minutes=30),
        seats_requested=1,
        max_extra_minutes=15,
    )

    auth_user = AuthUser(
        id=user_id,
        email="test@smartshare.in",
        role="authenticated",
        user_metadata={},
    )
    provider = MockPhase5ARoutingProvider()
    prop_id = _make_proposal_id(target_id, cand_id)

    app.dependency_overrides[get_current_user] = lambda: auth_user
    app.dependency_overrides[get_db] = lambda: _empty_consent_db()

    with (
        patch(
            "app.api.v1.endpoints.matching._get_active_owned_request",
            AsyncMock(return_value=target_req),
        ),
        patch(
            "app.api.v1.endpoints.matching.get_routing_provider",
            return_value=provider,
        ),
        patch(
            "app.matching.service.discover_candidates",
            AsyncMock(return_value=[]),
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/matches/{prop_id}?request_id={target_id}")
            assert resp.status_code == 404
            assert "Proposal not found or no longer valid" in resp.json()["detail"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_proposal_detail_candidate_expired() -> None:
    """Verify that if candidate request expires, proposal detail returns 404."""
    target_id = uuid.uuid4()
    user_id = uuid.uuid4()
    cand_id = uuid.uuid4()
    now = datetime.now(UTC)

    target_req = RideRequest(
        id=target_id,
        user_id=user_id,
        status=RideRequestStatus.ACTIVE,
        pickup_location="POINT(72.8687 19.0657)",
        destination="POINT(72.9060 19.1176)",
        departure_earliest=now,
        departure_latest=now + timedelta(minutes=30),
        seats_requested=1,
        max_extra_minutes=15,
    )

    auth_user = AuthUser(
        id=user_id,
        email="test@smartshare.in",
        role="authenticated",
        user_metadata={},
    )
    provider = MockPhase5ARoutingProvider()
    prop_id = _make_proposal_id(target_id, cand_id)

    app.dependency_overrides[get_current_user] = lambda: auth_user
    app.dependency_overrides[get_db] = lambda: _empty_consent_db()

    with (
        patch(
            "app.api.v1.endpoints.matching._get_active_owned_request",
            AsyncMock(return_value=target_req),
        ),
        patch(
            "app.api.v1.endpoints.matching.get_routing_provider",
            return_value=provider,
        ),
        patch(
            "app.matching.service.discover_candidates",
            AsyncMock(return_value=[]),
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/matches/{prop_id}?request_id={target_id}")
            assert resp.status_code == 404
            assert "Proposal not found or no longer valid" in resp.json()["detail"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_proposal_detail_candidate_infeasible_detour() -> None:
    """Verify that if candidate is no longer feasible (e.g. reduced max_extra_minutes), detail returns 404."""
    target_id = uuid.uuid4()
    user_id = uuid.uuid4()
    cand_id = uuid.uuid4()
    now = datetime.now(UTC)

    target_req = RideRequest(
        id=target_id,
        user_id=user_id,
        status=RideRequestStatus.ACTIVE,
        pickup_location="POINT(72.8687 19.0657)",
        destination="POINT(72.9060 19.1176)",
        departure_earliest=now,
        departure_latest=now + timedelta(minutes=30),
        seats_requested=1,
        max_extra_minutes=0,  # 0 tolerance for target
    )

    auth_user = AuthUser(
        id=user_id,
        email="test@smartshare.in",
        role="authenticated",
        user_metadata={},
    )
    provider = MockPhase5ARoutingProvider()
    prop_id = _make_proposal_id(target_id, cand_id)

    # Candidate has 0 tolerance, and target has 0 tolerance -> all sequences have > 0 detour for at least one passenger -> pruned
    mock_candidates = [
        {
            "candidate_id": cand_id,
            "candidate_user_id": uuid.uuid4(),
            "owner_name": "Zero Detour User",
            "pickup_location": "POINT(72.8690 19.0660)",
            "destination": "POINT(72.9050 19.1170)",
            "pickup_label": "BKC",
            "destination_label": "Powai",
            "seats_requested": 1,
            "max_extra_minutes": 0,
            "departure_earliest": now,
            "departure_latest": now + timedelta(minutes=30),
            "pickup_distance_m": 50.0,
            "dest_distance_m": 50.0,
            "overlap_seconds": 1800.0,
        }
    ]

    app.dependency_overrides[get_current_user] = lambda: auth_user
    app.dependency_overrides[get_db] = lambda: _empty_consent_db()

    with (
        patch(
            "app.api.v1.endpoints.matching._get_active_owned_request",
            AsyncMock(return_value=target_req),
        ),
        patch(
            "app.api.v1.endpoints.matching.get_routing_provider",
            return_value=provider,
        ),
        patch(
            "app.matching.service.discover_candidates",
            AsyncMock(return_value=mock_candidates),
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/matches/{prop_id}?request_id={target_id}")
            assert resp.status_code == 404
            assert "Proposal not found or no longer valid" in resp.json()["detail"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_proposal_detail_target_expired_before_enrichment() -> None:
    """Verify that if target ride request has expired before enrichment, retrieval returns 400."""
    target_id = uuid.uuid4()
    user_id = uuid.uuid4()
    now = datetime.now(UTC)

    expired_target = RideRequest(
        id=target_id,
        user_id=user_id,
        status=RideRequestStatus.ACTIVE,
        pickup_location="POINT(72.8687 19.0657)",
        destination="POINT(72.9060 19.1176)",
        departure_earliest=now - timedelta(minutes=45),
        departure_latest=now - timedelta(minutes=15),
        seats_requested=1,
        max_extra_minutes=15,
    )

    auth_user = AuthUser(
        id=user_id,
        email="test@smartshare.in",
        role="authenticated",
        user_metadata={},
    )
    prop_id = uuid.uuid4()

    app.dependency_overrides[get_current_user] = lambda: auth_user
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=expired_target)
    mock_db.execute = AsyncMock(return_value=mock_result)
    app.dependency_overrides[get_db] = lambda: mock_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/v1/matches/{prop_id}?request_id={target_id}")
        assert resp.status_code == 400
        assert "Ride request is not active or has expired" in resp.json()["detail"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_proposal_detail_candidate_destination_moved_beyond_threshold() -> None:
    """Verify that if candidate destination moves beyond 3km proximity threshold with heading delta > 45 deg, detail returns 404."""
    target_id = uuid.uuid4()
    user_id = uuid.uuid4()
    cand_id = uuid.uuid4()
    now = datetime.now(UTC)

    target_req = RideRequest(
        id=target_id,
        user_id=user_id,
        status=RideRequestStatus.ACTIVE,
        pickup_location="POINT(72.8687 19.0657)",
        destination="POINT(72.9060 19.1176)",  # Powai (bearing ~30.6 deg)
        departure_earliest=now,
        departure_latest=now + timedelta(minutes=30),
        seats_requested=1,
        max_extra_minutes=15,
    )

    auth_user = AuthUser(
        id=user_id,
        email="test@smartshare.in",
        role="authenticated",
        user_metadata={},
    )
    provider = MockPhase5ARoutingProvider()
    prop_id = _make_proposal_id(target_id, cand_id)

    # Candidate moved destination to Navi Mumbai: bearing ~87.4 deg (delta 56.8 deg > 45 deg)
    # dest_distance_m is ~9500m > 3000m threshold -> pruned in Stage 2
    mock_candidates = [
        {
            "candidate_id": cand_id,
            "candidate_user_id": uuid.uuid4(),
            "owner_name": "Moved Dest User",
            "pickup_location": "POINT(72.8690 19.0660)",
            "destination": "POINT(72.9800 19.0700)",
            "pickup_label": "BKC",
            "destination_label": "Navi Mumbai",
            "seats_requested": 1,
            "max_extra_minutes": 15,
            "departure_earliest": now,
            "departure_latest": now + timedelta(minutes=30),
            "pickup_distance_m": 40.0,
            "dest_distance_m": 9500.0,
            "overlap_seconds": 1800.0,
        }
    ]

    app.dependency_overrides[get_current_user] = lambda: auth_user
    app.dependency_overrides[get_db] = lambda: _empty_consent_db()

    with (
        patch(
            "app.api.v1.endpoints.matching._get_active_owned_request",
            AsyncMock(return_value=target_req),
        ),
        patch(
            "app.api.v1.endpoints.matching.get_routing_provider",
            return_value=provider,
        ),
        patch(
            "app.matching.service.discover_candidates",
            AsyncMock(return_value=mock_candidates),
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/matches/{prop_id}?request_id={target_id}")
            assert resp.status_code == 404
            assert "Proposal not found or no longer valid" in resp.json()["detail"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_proposal_detail_candidate_matched_returns_404() -> None:
    """Verify that if candidate request is MATCHED, candidate discovery excludes it and detail returns 404."""
    target_id = uuid.uuid4()
    user_id = uuid.uuid4()
    cand_id = uuid.uuid4()
    now = datetime.now(UTC)

    target_req = RideRequest(
        id=target_id,
        user_id=user_id,
        status=RideRequestStatus.ACTIVE,
        pickup_location="POINT(72.8687 19.0657)",
        destination="POINT(72.9060 19.1176)",
        departure_earliest=now,
        departure_latest=now + timedelta(minutes=30),
        seats_requested=1,
        max_extra_minutes=15,
    )

    auth_user = AuthUser(
        id=user_id,
        email="test@smartshare.in",
        role="authenticated",
        user_metadata={},
    )
    provider = MockPhase5ARoutingProvider()
    prop_id = _make_proposal_id(target_id, cand_id)

    app.dependency_overrides[get_current_user] = lambda: auth_user
    app.dependency_overrides[get_db] = lambda: _empty_consent_db()

    # When candidate is MATCHED, DB candidate discovery query (WHERE status = 'ACTIVE') returns []
    with (
        patch(
            "app.api.v1.endpoints.matching._get_active_owned_request",
            AsyncMock(return_value=target_req),
        ),
        patch(
            "app.api.v1.endpoints.matching.get_routing_provider",
            return_value=provider,
        ),
        patch(
            "app.matching.service.discover_candidates",
            AsyncMock(return_value=[]),
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/matches/{prop_id}?request_id={target_id}")
            assert resp.status_code == 404
            assert "Proposal not found or no longer valid" in resp.json()["detail"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_proposal_detail_candidate_completed_returns_404() -> None:
    """Verify that if candidate request is COMPLETED, candidate discovery excludes it and detail returns 404."""
    target_id = uuid.uuid4()
    user_id = uuid.uuid4()
    cand_id = uuid.uuid4()
    now = datetime.now(UTC)

    target_req = RideRequest(
        id=target_id,
        user_id=user_id,
        status=RideRequestStatus.ACTIVE,
        pickup_location="POINT(72.8687 19.0657)",
        destination="POINT(72.9060 19.1176)",
        departure_earliest=now,
        departure_latest=now + timedelta(minutes=30),
        seats_requested=1,
        max_extra_minutes=15,
    )

    auth_user = AuthUser(
        id=user_id,
        email="test@smartshare.in",
        role="authenticated",
        user_metadata={},
    )
    provider = MockPhase5ARoutingProvider()
    prop_id = _make_proposal_id(target_id, cand_id)

    app.dependency_overrides[get_current_user] = lambda: auth_user
    app.dependency_overrides[get_db] = lambda: _empty_consent_db()

    # When candidate is COMPLETED, DB query returns []
    with (
        patch(
            "app.api.v1.endpoints.matching._get_active_owned_request",
            AsyncMock(return_value=target_req),
        ),
        patch(
            "app.api.v1.endpoints.matching.get_routing_provider",
            return_value=provider,
        ),
        patch(
            "app.matching.service.discover_candidates",
            AsyncMock(return_value=[]),
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/matches/{prop_id}?request_id={target_id}")
            assert resp.status_code == 404
            assert "Proposal not found or no longer valid" in resp.json()["detail"]

    app.dependency_overrides.clear()


class RejectAllRouteProvider(MockPhase5ARoutingProvider):
    """Mock provider where all continuous multi-waypoint routes produce excessive detour."""

    async def get_multi_waypoint_route(
        self,
        waypoints: list[tuple[float, float]],
        stop_ids: list[str] | None = None,
        stop_labels: list[str | None] | None = None,
    ) -> MultiWaypointRoute:
        route = await super().get_multi_waypoint_route(waypoints, stop_ids, stop_labels)
        # Each leg duration is 2000s -> pooled travel > 4000s, detour > 50 min > 15 min limit
        inflated_legs = [
            RouteLeg(
                sequence=leg.sequence,
                start_stop_id=leg.start_stop_id,
                end_stop_id=leg.end_stop_id,
                start_label=leg.start_label,
                end_label=leg.end_label,
                distance_meters=leg.distance_meters,
                duration_seconds=2000.0,
            )
            for leg in route.legs
        ]
        return MultiWaypointRoute(
            total_distance=route.total_distance,
            total_duration_seconds=6000.0,
            legs=inflated_legs,
            full_geometry_geojson=route.full_geometry_geojson,
            provider_name=route.provider_name,
        )


@pytest.mark.asyncio
async def test_all_three_externally_routed_candidates_fail_route_api_returns_empty() -> (
    None
):
    """Verify that if all 3 externally routed candidates fail final Route API revalidation, no proposal is returned."""
    target_id = uuid.uuid4()
    user_id = uuid.uuid4()
    now = datetime.now(UTC)

    target_req = RideRequest(
        id=target_id,
        user_id=user_id,
        status=RideRequestStatus.ACTIVE,
        pickup_location="POINT(72.8687 19.0657)",
        destination="POINT(72.9060 19.1176)",
        departure_earliest=now,
        departure_latest=now + timedelta(minutes=30),
        seats_requested=1,
        max_extra_minutes=15,
    )

    mock_candidates = [
        {
            "candidate_id": uuid.uuid4(),
            "candidate_user_id": uuid.uuid4(),
            "owner_name": f"Candidate {i}",
            "pickup_location": f"POINT({72.8687 + i * 0.001} {19.0657 + i * 0.001})",
            "destination": f"POINT({72.9060 + i * 0.001} {19.1176 + i * 0.001})",
            "pickup_label": f"Pickup {i}",
            "destination_label": f"Dest {i}",
            "seats_requested": 1,
            "max_extra_minutes": 15,
            "departure_earliest": now,
            "departure_latest": now + timedelta(minutes=30),
            "pickup_distance_m": 100.0 * (i + 1),
            "dest_distance_m": 100.0 * (i + 1),
            "overlap_seconds": 1800.0,
        }
        for i in range(3)
    ]

    provider = RejectAllRouteProvider(max_routed_candidates=3)
    mock_db = AsyncMock()

    with patch(
        "app.matching.service.discover_candidates",
        AsyncMock(return_value=mock_candidates),
    ):
        proposals = await run_matching(mock_db, provider, target_req)
        # All 3 evaluated by Route API and all 3 rejected due to detour violation
        assert proposals == []
        assert provider.route_call_count == 3


@pytest.mark.asyncio
async def test_candidate_promotion_never_exceeds_external_routing_cap_of_three() -> (
    None
):
    """Verify that candidate promotion never exceeds the approved external routing cap of 3 (DEC-002)."""
    target_id = uuid.uuid4()
    user_id = uuid.uuid4()
    now = datetime.now(UTC)

    target_req = RideRequest(
        id=target_id,
        user_id=user_id,
        status=RideRequestStatus.ACTIVE,
        pickup_location="POINT(72.8687 19.0657)",
        destination="POINT(72.9060 19.1176)",
        departure_earliest=now,
        departure_latest=now + timedelta(minutes=30),
        seats_requested=1,
        max_extra_minutes=15,
    )

    # 5 candidates available in Stage 1
    mock_candidates = [
        {
            "candidate_id": uuid.uuid4(),
            "candidate_user_id": uuid.uuid4(),
            "owner_name": f"Candidate {i}",
            "pickup_location": f"POINT({72.8687 + i * 0.0005} {19.0657 + i * 0.0005})",
            "destination": f"POINT({72.9060 + i * 0.0005} {19.1176 + i * 0.0005})",
            "pickup_label": f"Pickup {i}",
            "destination_label": f"Dest {i}",
            "seats_requested": 1,
            "max_extra_minutes": 15,
            "departure_earliest": now,
            "departure_latest": now + timedelta(minutes=30),
            "pickup_distance_m": 50.0 * (i + 1),
            "dest_distance_m": 50.0 * (i + 1),
            "overlap_seconds": 1800.0,
        }
        for i in range(5)
    ]

    provider = RejectAllRouteProvider(max_routed_candidates=3)
    mock_db = AsyncMock()

    with patch(
        "app.matching.service.discover_candidates",
        AsyncMock(return_value=mock_candidates),
    ):
        proposals = await run_matching(mock_db, provider, target_req)
        assert proposals == []
        # DEC-002: Only top 3 candidates were evaluated; candidates 4 and 5 were never routed
        assert provider.route_call_count == 3


@pytest.mark.asyncio
async def test_match_discovery_api_includes_viewer_scoped_fare_estimate() -> None:
    """Exercise candidate matching through the real response serializer and fare engine."""
    user_id, target_id, candidate_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    now = datetime.now(UTC)
    target = RideRequest(
        id=target_id,
        user_id=user_id,
        status=RideRequestStatus.ACTIVE,
        pickup_location="POINT(72.8687 19.0657)",
        destination="POINT(72.9060 19.1176)",
        departure_earliest=now + timedelta(hours=1),
        departure_latest=now + timedelta(hours=1, minutes=30),
        seats_requested=1,
        max_extra_minutes=15,
    )
    candidate = {
        "candidate_id": candidate_id,
        "candidate_user_id": uuid.uuid4(),
        "owner_name": "Candidate Rider",
        "pickup_location": "POINT(72.8690 19.0660)",
        "destination": "POINT(72.9065 19.1178)",
        "pickup_label": "Candidate pickup",
        "destination_label": "Candidate destination",
        "seats_requested": 1,
        "max_extra_minutes": 15,
        "departure_earliest": target.departure_earliest,
        "departure_latest": target.departure_latest,
        "pickup_distance_m": 50.0,
        "dest_distance_m": 60.0,
        "overlap_seconds": 1800.0,
    }
    auth_user = AuthUser(
        id=user_id, email="test@smartshare.in", role="authenticated", user_metadata={}
    )
    app.dependency_overrides[get_current_user] = lambda: auth_user
    app.dependency_overrides[get_db] = lambda: _empty_consent_db()

    with (
        patch(
            "app.api.v1.endpoints.matching._get_active_owned_request",
            AsyncMock(return_value=target),
        ),
        patch(
            "app.api.v1.endpoints.matching.get_routing_provider",
            return_value=MockPhase5ARoutingProvider(),
        ),
        patch(
            "app.matching.service.discover_candidates",
            AsyncMock(return_value=[candidate]),
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"/api/v1/ride-requests/{target_id}/matches")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    payload = response.json()["data"]["proposals"][0]
    fare = payload["fare_estimate"]
    assert fare["shared_journey"]["estimate_paise"] > 0
    assert fare["your_solo_baseline"]["estimate_paise"] > 0
    assert fare["composite_accuracy"] == "MATRIX_SCREENING"
    assert "does not claim to reproduce" in fare["disclaimer"]
    serialized_proposal = str(payload).lower()
    assert not any(
        forbidden in serialized_proposal
        for forbidden in (
            "your_contribution_paise",
            "co_passenger_contribution_paise",
            "your_savings_paise",
            "co_passenger_savings",
            "co_passenger_solo",
        )
    )
    assert payload["fare_allocation_disclosure"]["allocation"] is None
    assert payload["fare_allocation_disclosure"]["exact_disclosure_available"] is False
    assert list(payload["passenger_metrics"]) == [str(target_id)]
