"""Integration tests for Phase 5A decisions DEC-001, DEC-002, DEC-003, and Mumbai routing."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.main import app
from app.matching.detour import evaluate_pairwise_detour
from app.matching.service import (
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
        # Add intermediate polyline coordinates to simulate detailed route line
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

    # Mock candidate discovery to return 2 candidates
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

    # Verify provider call count: 2 matrix calls (one for each candidate), exactly 1 route call (Top 1 only)
    assert provider.matrix_call_count == 2
    assert provider.route_call_count == 1

    # On-demand enrichment test for Proposal #2:
    enriched_top2 = await enrich_proposal_geometry(top2, provider)
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
        for i in range(1, 6)  # 5 candidates
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
            # Durations: Detour A is 5 minutes (300s), Detour B is 5 minutes (300s)
            durations = [
                [0.0, 300.0, 600.0, 900.0],
                [300.0, 0.0, 600.0, 600.0],
                [600.0, 600.0, 0.0, 300.0],
                [900.0, 600.0, 300.0, 0.0],
            ]
            # Distances: Massive distance detour (15,000 meters / 15 km)
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
    # Distance detour is computed and informational
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
    # Proposal survived with synthesized geometry
    assert proposal.route_geometry is not None
    assert proposal.route_geometry["type"] == "LineString"
    assert proposal.routing_accuracy == "matrix_duration_synthesized_geometry"


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

    from app.matching.service import _make_proposal_id

    prop2_id = _make_proposal_id(target_id, cand2_id)

    app.dependency_overrides[get_current_user] = lambda: auth_user
    app.dependency_overrides[get_db] = lambda: AsyncMock()

    with (
        patch(
            "app.api.v1.endpoints.matching._get_active_owned_request",
            AsyncMock(return_value=target_req),
        ),
        patch(
            "app.api.v1.endpoints.matching.get_routing_provider", return_value=provider
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
