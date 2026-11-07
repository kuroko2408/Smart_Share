"""
Matching engine API endpoints.

POST /api/v1/ride-requests/{id}/matches — Run match discovery for the target request.
GET  /api/v1/ride-requests/{id}/matches — Re-run match discovery (same logic, same response).
GET  /api/v1/matches/{proposal_id}      — Retrieve details of a specific proposal by ID.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db as get_db_session
from app.matching.service import (
    MatchProposal,
    enrich_proposal_geometry,
    run_matching,
)
from app.models.ride_request import RideRequest, RideRequestStatus
from app.routing.provider_factory import get_routing_provider
from app.schemas.auth import AuthUser
from app.schemas.common import DataResponse
from app.schemas.matching import (
    GeoJSONLineStringSchema,
    LocationPointSchema,
    MatchCandidateSummarySchema,
    MatchListResponseSchema,
    MatchProposalSchema,
    PassengerJourneyDetailSchema,
    RouteLegSchema,
    ScoreBreakdownSchema,
    StopPointSchema,
)

router = APIRouter(prefix="/ride-requests", tags=["matching"])
proposal_router = APIRouter(prefix="/matches", tags=["matching"])

logger = logging.getLogger(__name__)


def _parse_uuid(val: Any) -> uuid.UUID:
    """Safely convert any identifier to a UUID object."""
    if isinstance(val, uuid.UUID):
        return val
    try:
        return uuid.UUID(str(val))
    except (ValueError, TypeError):
        return uuid.uuid5(uuid.NAMESPACE_DNS, str(val))


async def _get_active_owned_request(
    request_id: uuid.UUID,
    db: AsyncSession,
    current_user: AuthUser,
) -> RideRequest:
    """Fetch an ACTIVE ride request and verify ownership."""
    result = await db.execute(select(RideRequest).where(RideRequest.id == request_id))
    request = result.scalar_one_or_none()

    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ride request not found."
        )

    if str(request.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied."
        )

    now = datetime.now(UTC)
    effective_expiry = request.expires_at or request.departure_latest
    if effective_expiry.tzinfo is None:
        effective_expiry = effective_expiry.replace(tzinfo=UTC)

    if request.status != RideRequestStatus.ACTIVE or effective_expiry <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ride request is not active or has expired.",
        )

    return request


def _proposal_to_schema(p: MatchProposal) -> MatchProposalSchema:
    """Convert internal MatchProposal dataclass to Pydantic response schema."""
    scores = ScoreBreakdownSchema(
        pickup_proximity_score=round(p.scores.pickup_proximity_score, 4),
        destination_similarity_score=round(p.scores.destination_similarity_score, 4),
        departure_time_score=round(p.scores.departure_time_score, 4),
        route_detour_score=round(p.scores.route_detour_score, 4),
        composite_score=round(p.scores.composite_score, 4),
    )

    candidate = MatchCandidateSummarySchema(
        candidate_request_id=p.candidate_request_id,
        candidate_display_name=p.candidate_display_name,
        candidate_pickup=LocationPointSchema(
            latitude=p.candidate_pickup_lat,
            longitude=p.candidate_pickup_lon,
            label=p.candidate_pickup_label,
        ),
        candidate_destination=LocationPointSchema(
            latitude=p.candidate_dest_lat,
            longitude=p.candidate_dest_lon,
            label=p.candidate_dest_label,
        ),
        seats_requested=p.candidate_seats,
        pickup_distance_meters=round(p.pickup_distance_m, 1),
        destination_distance_meters=round(p.dest_distance_m, 1),
        shared_departure_window_start=p.shared_departure_start,
        shared_departure_window_end=p.shared_departure_end,
        estimated_detour_minutes_target=round(p.detour_target_minutes, 1),
        estimated_detour_minutes_candidate=round(p.detour_candidate_minutes, 1),
        scores=scores,
    )

    stops = [
        StopPointSchema(
            sequence=s.sequence,
            stop_type=s.stop_type,
            location=LocationPointSchema(
                latitude=s.latitude,
                longitude=s.longitude,
                label=s.label,
            ),
            passenger_request_id=s.passenger_request_id,
        )
        for s in p.stops
    ]

    route_legs = [
        RouteLegSchema(
            sequence=leg.sequence,
            start_stop_id=_parse_uuid(leg.start_stop_id),
            end_stop_id=_parse_uuid(leg.end_stop_id),
            start_label=leg.start_label,
            end_label=leg.end_label,
            distance_meters=round(leg.distance_meters, 1),
            distance_km=leg.distance_km,
            duration_seconds=round(leg.duration_seconds, 1),
            duration_minutes=leg.duration_minutes,
        )
        for leg in p.route_legs
    ]

    passenger_metrics = {
        req_id: PassengerJourneyDetailSchema(
            passenger_request_id=_parse_uuid(req_id),
            solo_direct_distance_km=m.solo_direct_distance_km,
            solo_direct_distance_meters=round(m.solo_direct_distance_meters, 1),
            solo_direct_duration_minutes=m.solo_direct_duration_minutes,
            solo_direct_duration_seconds=round(m.solo_direct_duration_seconds, 1),
            pooled_distance_km=m.pooled_distance_km,
            pooled_distance_meters=round(m.pooled_journey_distance_meters, 1),
            pooled_duration_minutes=m.pooled_duration_minutes,
            pooled_duration_seconds=round(m.pooled_journey_duration_seconds, 1),
            detour_distance_km=m.detour_distance_km,
            detour_distance_meters=round(m.detour_distance_meters, 1),
            detour_duration_minutes=round(m.detour_duration_minutes, 1),
        )
        for req_id, m in p.passenger_metrics.items()
    }

    route_geometry = None
    if p.route_geometry:
        raw_coords = p.route_geometry.get("coordinates", [])
        route_geometry = GeoJSONLineStringSchema(
            type="LineString",
            coordinates=[(float(c[0]), float(c[1])) for c in raw_coords],
        )

    return MatchProposalSchema(
        proposal_id=p.proposal_id,
        target_request_id=p.target_request_id,
        candidate=candidate,
        ordered_stops=stops,
        total_shared_distance_km=round(p.total_shared_distance_m / 1000, 2),
        total_shared_distance_meters=round(p.total_shared_distance_m, 1),
        total_shared_duration_minutes=round(p.total_shared_duration_seconds / 60, 1),
        total_shared_duration_seconds=round(p.total_shared_duration_seconds, 1),
        best_sequence=p.best_sequence_label,
        is_route_approximate=p.is_route_approximate,
        distance_is_approximate=p.distance_is_approximate,
        distance_source=p.distance_source,
        routing_accuracy=p.routing_accuracy,
        routing_notice=p.routing_notice,
        compatibility_explanations=[
            f"Pickup points are {round(p.pickup_distance_m)} metres apart.",
            f"Destinations are {round(p.dest_distance_m)} metres apart, with compatible travel directions.",
            f"Departure windows overlap from {p.shared_departure_start.isoformat()} to {p.shared_departure_end.isoformat()}.",
            f"Estimated additional journey time is {p.detour_target_minutes:.1f} minutes for you and {p.detour_candidate_minutes:.1f} minutes for the other passenger.",
            "Combined seat requests fit the standard four-passenger vehicle limit.",
        ],
        created_at=p.created_at,
        route_geometry=route_geometry,
        route_legs=route_legs,
        passenger_metrics=passenger_metrics,
    )


async def _run_and_respond(
    request_id: uuid.UUID,
    db: AsyncSession,
    current_user: AuthUser,
) -> DataResponse[MatchListResponseSchema]:
    """Shared logic for POST and GET matching endpoints."""
    target = await _get_active_owned_request(request_id, db, current_user)
    routing = get_routing_provider()
    proposals = await run_matching(db, routing, target)
    return DataResponse(
        data=MatchListResponseSchema(
            target_request_id=request_id,
            total_candidates_found=len(proposals),
            proposals=[_proposal_to_schema(p) for p in proposals],
        ),
        message="Matching suggestions generated successfully",
    )


@router.post(
    "/{request_id}/matches",
    response_model=DataResponse[MatchListResponseSchema],
    summary="Run match discovery for a ride request",
)
async def trigger_match_discovery(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(get_current_user),
) -> DataResponse[MatchListResponseSchema]:
    """
    Initiate on-demand match discovery for the authenticated user's ACTIVE ride request.
    Returns ranked pairwise match proposals.
    """
    logger.info(
        "POST /ride-requests/%s/matches by user %s", request_id, current_user.id
    )
    return await _run_and_respond(request_id, db, current_user)


@router.get(
    "/{request_id}/matches",
    response_model=DataResponse[MatchListResponseSchema],
    summary="Retrieve match proposals for a ride request",
)
async def get_match_proposals(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(get_current_user),
) -> DataResponse[MatchListResponseSchema]:
    """
    Re-run match discovery and return current proposals.
    Proposals are always freshly computed (transient architecture).
    """
    logger.info("GET /ride-requests/%s/matches by user %s", request_id, current_user.id)
    return await _run_and_respond(request_id, db, current_user)


@proposal_router.get(
    "/{proposal_id}",
    response_model=DataResponse[MatchProposalSchema],
    summary="Retrieve a specific match proposal by ID",
)
async def get_proposal_detail(
    proposal_id: uuid.UUID,
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(get_current_user),
) -> DataResponse[MatchProposalSchema]:
    """
    Retrieve details of a specific proposal.
    Requires the target request_id as a query parameter to verify ownership.
    Re-runs matching and finds the matching proposal_id.
    Enriches with route geometry on-demand if not already populated.
    """
    target = await _get_active_owned_request(request_id, db, current_user)
    routing = get_routing_provider()
    proposals = await run_matching(db, routing, target)
    for p in proposals:
        if p.proposal_id == proposal_id:
            if p.route_geometry is None:
                enriched = await enrich_proposal_geometry(p, routing)
                if enriched is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Proposal not found or no longer valid.",
                    )
                p = enriched
            return DataResponse(
                data=_proposal_to_schema(p),
                message="Match proposal retrieved successfully",
            )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Proposal not found or no longer valid.",
    )
