"""
Matching engine API endpoints.

POST /api/v1/ride-requests/{id}/matches — Run match discovery for the target request.
GET  /api/v1/ride-requests/{id}/matches — Re-run match discovery (same logic, same response).
GET  /api/v1/matches/{proposal_id}      — Retrieve details of a specific proposal by ID.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db as get_db_session
from app.fares.allocation import assess_match_economics
from app.fares.consent import (
    ProposalConsentState,
    load_proposal_consent_states,
    record_consent_event,
)
from app.fares.disclosure import (
    CONSENT_NOTICE,
    CONSENT_TEXT_VERSION,
    disclosure_subject_fingerprint,
)
from app.fares.models import FareComponentEstimate, MatchFareEstimate
from app.fares.service import estimate_match_fare
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
    ConditionalFareRangeSchema,
    EconomicAssessmentSchema,
    FareAllocationDisclosureSchema,
    FareAllocationScenarioSchema,
    FareAllocationSchema,
    FareAmountSchema,
    FareComponentSchema,
    GeoJSONLineStringSchema,
    LocationPointSchema,
    MatchCandidateSummarySchema,
    MatchDisclosureConsentRequest,
    MatchFareEstimateSchema,
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
_UNSET = object()


def _fare_disclaimer(mode: str) -> str:
    return (
        "Estimated pre-trip fare based on the configured Mumbai tariff model. "
        f"The selected {mode.lower()} calculation is an estimate and does not "
        "claim to reproduce the physical taxi meter's legally unresolved pulse "
        "behavior. The final charge is determined by the taxi meter at trip "
        "completion. Tolls, waiting time and parking are not included."
    )


def _fare_component_to_schema(value: FareComponentEstimate) -> FareComponentSchema:
    amount = value.amount
    fare_range = None
    if value.fare_range:
        fare_range = ConditionalFareRangeSchema(
            minimum=FareAmountSchema(
                estimate=float(value.fare_range.minimum.estimate),
                estimate_paise=value.fare_range.minimum.estimate_paise,
                rounded_estimate_rupees=value.fare_range.minimum.rounded_estimate_rupees,
            ),
            maximum=FareAmountSchema(
                estimate=float(value.fare_range.maximum.estimate),
                estimate_paise=value.fare_range.maximum.estimate_paise,
                rounded_estimate_rupees=value.fare_range.maximum.rounded_estimate_rupees,
            ),
        )
    return FareComponentSchema(
        estimate=float(amount.estimate),
        estimate_paise=amount.estimate_paise,
        rounded_estimate_rupees=amount.rounded_estimate_rupees,
        distance_meters=float(value.distance_meters),
        distance_source=value.source,
        accuracy_tier=value.accuracy.value,
        surcharge_status=value.surcharge_status.value,
        fare_range=fare_range,
    )


def _fare_to_schema(value: MatchFareEstimate) -> MatchFareEstimateSchema:
    return MatchFareEstimateSchema(
        shared_journey=_fare_component_to_schema(value.shared_journey),
        your_solo_baseline=_fare_component_to_schema(value.your_solo_baseline),
        composite_accuracy=value.composite_accuracy.value,
        fare_model_id=value.model_id,
        fare_model_version=value.model_version,
        pulse_quantization_mode=value.pulse_quantization_mode.value,
        excluded_charges=["tolls", "waiting time", "parking"],
        disclaimer=_fare_disclaimer(value.pulse_quantization_mode.value),
    )


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


def _allocation_disclosure_to_schema(
    proposal: MatchProposal,
    fares: MatchFareEstimate,
    consent: ProposalConsentState,
) -> FareAllocationDisclosureSchema:
    viewer_consented = consent.by_request.get(proposal.target_request_id, False)
    co_passenger_consented = consent.by_request.get(
        proposal.candidate_request_id, False
    )
    allocation_schema = None
    scenario_schemas: list[FareAllocationScenarioSchema] = []
    if viewer_consented and co_passenger_consented:
        allocation, assessment = assess_match_economics(
            fares, minimum_fare_paise=fares.minimum_fare_paise
        )

        def orient(passenger_a, passenger_b):
            return (
                (passenger_a, passenger_b)
                if fares.viewer_is_canonical_passenger_a
                else (passenger_b, passenger_a)
            )

        def to_scenario(tariff_period: str, scenario_allocation):
            viewer, other = orient(
                scenario_allocation.passenger_a,
                scenario_allocation.passenger_b,
            )
            return FareAllocationScenarioSchema(
                tariff_period=tariff_period,
                economic_classification=scenario_allocation.classification.value,
                shared_total=float(scenario_allocation.shared_total),
                shared_total_paise=int(scenario_allocation.shared_total * 100),
                your_contribution=float(viewer.contribution),
                your_contribution_paise=int(viewer.contribution * 100),
                co_passenger_contribution=float(other.contribution),
                co_passenger_contribution_paise=int(other.contribution * 100),
                your_savings=float(viewer.savings),
                your_savings_paise=int(viewer.savings * 100),
                your_savings_percent=viewer.savings_percent,
            )

        if assessment.scenarios:
            scenario_schemas = [
                to_scenario(scenario.tariff_period, scenario.allocation)
                for scenario in assessment.scenarios
            ]
        else:
            viewer, other = orient(allocation.passenger_a, allocation.passenger_b)
            allocation_schema = FareAllocationSchema(
                policy="PROPORTIONAL_TO_SOLO_BASELINE",
                shared_total=float(allocation.shared_total),
                shared_total_paise=int(allocation.shared_total * 100),
                your_contribution=float(viewer.contribution),
                your_contribution_paise=int(viewer.contribution * 100),
                co_passenger_contribution=float(other.contribution),
                co_passenger_contribution_paise=int(other.contribution * 100),
                your_savings=float(viewer.savings),
                your_savings_paise=int(viewer.savings * 100),
                your_savings_percent=viewer.savings_percent,
            )
    return FareAllocationDisclosureSchema(
        consent_text_version=CONSENT_TEXT_VERSION,
        consent_notice=CONSENT_NOTICE,
        your_consent_active=viewer_consented,
        co_passenger_consent_active=co_passenger_consented,
        exact_disclosure_available=allocation_schema is not None
        or bool(scenario_schemas),
        allocation=allocation_schema,
        conditional_scenarios=scenario_schemas,
    )


def _proposal_to_schema(
    p: MatchProposal,
    *,
    fare_domain: MatchFareEstimate | None | object = _UNSET,
    consent_state: ProposalConsentState | None = None,
) -> MatchProposalSchema:
    """Convert internal MatchProposal dataclass to Pydantic response schema."""
    economic_assessment = None
    disclosure = None
    try:
        if fare_domain is _UNSET:
            fare_domain = estimate_match_fare(p)
        if fare_domain is None:
            raise ValueError("Fare estimate is unavailable")
        fare_estimate = _fare_to_schema(fare_domain)
        _, assessment = assess_match_economics(
            fare_domain, minimum_fare_paise=fare_domain.minimum_fare_paise
        )
        economic_assessment = EconomicAssessmentSchema(
            classification=assessment.classification.value,
            message=assessment.message,
        )
        if consent_state is not None:
            disclosure = _allocation_disclosure_to_schema(p, fare_domain, consent_state)
    except (ValueError, LookupError, ArithmeticError) as exc:
        # Fare estimation is informative and must not turn a feasible match into an API failure.
        logger.warning(
            "Fare estimate unavailable for proposal %s (%s)",
            p.proposal_id,
            type(exc).__name__,
        )
        fare_estimate = None

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
        if req_id == str(p.target_request_id)
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
        fare_estimate=fare_estimate,
        economic_assessment=economic_assessment,
        fare_allocation_disclosure=disclosure,
    )


async def _serialize_proposals(
    db: AsyncSession, proposals: Sequence[MatchProposal]
) -> list[MatchProposalSchema]:
    if not proposals:
        return []
    fare_domains: dict[uuid.UUID, MatchFareEstimate | None] = {}
    subjects: dict[uuid.UUID, tuple[uuid.UUID, uuid.UUID, str]] = {}
    for proposal in proposals:
        try:
            fares = estimate_match_fare(proposal)
        except (ValueError, LookupError, ArithmeticError) as exc:
            logger.warning(
                "Fare estimate unavailable for proposal %s (%s)",
                proposal.proposal_id,
                type(exc).__name__,
            )
            fare_domains[proposal.proposal_id] = None
            continue
        fare_domains[proposal.proposal_id] = fares
        subjects[proposal.proposal_id] = (
            proposal.target_request_id,
            proposal.candidate_request_id,
            disclosure_subject_fingerprint(fares),
        )
    consent_states = await load_proposal_consent_states(db, subjects)
    return [
        _proposal_to_schema(
            proposal,
            fare_domain=fare_domains[proposal.proposal_id],
            consent_state=consent_states.get(proposal.proposal_id),
        )
        for proposal in proposals
    ]


async def _find_current_owned_proposal(
    proposal_id: uuid.UUID,
    request_id: uuid.UUID,
    db: AsyncSession,
    current_user: AuthUser,
) -> MatchProposal:
    target = await _get_active_owned_request(request_id, db, current_user)
    routing = get_routing_provider()
    proposals = await run_matching(db, routing, target)
    for proposal in proposals:
        if proposal.proposal_id == proposal_id:
            if proposal.route_geometry is None:
                enriched = await enrich_proposal_geometry(proposal, routing)
                if enriched is None:
                    break
                proposal = enriched
            return proposal
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Proposal not found or no longer valid.",
    )


async def _consent_state_for_proposal(
    db: AsyncSession, proposal: MatchProposal, fares: MatchFareEstimate
) -> ProposalConsentState:
    states = await load_proposal_consent_states(
        db,
        {
            proposal.proposal_id: (
                proposal.target_request_id,
                proposal.candidate_request_id,
                disclosure_subject_fingerprint(fares),
            )
        },
    )
    return states.get(
        proposal.proposal_id,
        ProposalConsentState(
            by_request={
                proposal.target_request_id: False,
                proposal.candidate_request_id: False,
            }
        ),
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
            proposals=await _serialize_proposals(db, proposals),
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
            serialized = (await _serialize_proposals(db, [p]))[0]
            return DataResponse(
                data=serialized,
                message="Match proposal retrieved successfully",
            )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Proposal not found or no longer valid.",
    )


@proposal_router.post(
    "/{proposal_id}/disclosure-consent",
    response_model=DataResponse[FareAllocationDisclosureSchema],
    summary="Affirm exact fare disclosure consent for a match proposal",
)
async def grant_exact_disclosure_consent(
    proposal_id: uuid.UUID,
    request_id: uuid.UUID,
    body: MatchDisclosureConsentRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(get_current_user),
) -> DataResponse[FareAllocationDisclosureSchema]:
    if body.consent_text_version != CONSENT_TEXT_VERSION:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Consent notice version is no longer current. Review the latest notice.",
        )
    proposal = await _find_current_owned_proposal(
        proposal_id, request_id, db, current_user
    )
    try:
        fares = estimate_match_fare(proposal)
    except (ValueError, LookupError, ArithmeticError) as exc:
        logger.warning(
            "Cannot record disclosure consent for proposal %s (%s)",
            proposal_id,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Fare estimate is unavailable for this proposal.",
        ) from exc
    await record_consent_event(
        db,
        proposal_id=proposal_id,
        participant_request_id=request_id,
        participant_user_id=current_user.id,
        subject_fingerprint=disclosure_subject_fingerprint(fares),
        action="GRANTED",
    )
    state = await _consent_state_for_proposal(db, proposal, fares)
    return DataResponse(
        data=_allocation_disclosure_to_schema(proposal, fares, state),
        message="Your exact disclosure consent has been recorded.",
    )


@proposal_router.delete(
    "/{proposal_id}/disclosure-consent",
    response_model=DataResponse[FareAllocationDisclosureSchema],
    summary="Withdraw exact fare disclosure consent for a match proposal",
)
async def withdraw_exact_disclosure_consent(
    proposal_id: uuid.UUID,
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(get_current_user),
) -> DataResponse[FareAllocationDisclosureSchema]:
    proposal = await _find_current_owned_proposal(
        proposal_id, request_id, db, current_user
    )
    try:
        fares = estimate_match_fare(proposal)
    except (ValueError, LookupError, ArithmeticError) as exc:
        logger.warning(
            "Cannot process disclosure consent withdrawal for proposal %s (%s)",
            proposal_id,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Fare estimate is unavailable for this proposal.",
        ) from exc
    await record_consent_event(
        db,
        proposal_id=proposal_id,
        participant_request_id=request_id,
        participant_user_id=current_user.id,
        subject_fingerprint=disclosure_subject_fingerprint(fares),
        action="REVOKED",
    )
    state = await _consent_state_for_proposal(db, proposal, fares)
    return DataResponse(
        data=_allocation_disclosure_to_schema(proposal, fares, state),
        message="Your exact disclosure consent has been withdrawn.",
    )
