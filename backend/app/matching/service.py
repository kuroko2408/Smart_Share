"""
Matching engine orchestration service.
Coordinates all pipeline stages and returns ranked match proposals.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.spatial import parse_point_coordinates
from app.matching.candidate_discovery import discover_candidates
from app.matching.detour import evaluate_pairwise_detour
from app.matching.geometry import (
    angular_delta,
    bearing,
    is_directionally_compatible,
)
from app.matching.scoring import ScoreBreakdown, compute_score
from app.models.ride_request import RideRequest
from app.routing.base import (
    DistanceSource,
    PassengerJourneyMetrics,
    RouteLeg,
    RoutingProvider,
)

logger = logging.getLogger(__name__)

TOP_K_PROPOSALS = 5
MATCH_PROPOSAL_NAMESPACE = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")


@dataclass
class StopInfo:
    sequence: int
    stop_type: str
    latitude: float
    longitude: float
    passenger_request_id: uuid.UUID
    label: str | None


@dataclass
class MatchProposal:
    proposal_id: uuid.UUID
    target_request_id: uuid.UUID
    candidate_request_id: uuid.UUID
    candidate_user_id: uuid.UUID
    candidate_display_name: str
    candidate_pickup_lat: float
    candidate_pickup_lon: float
    candidate_dest_lat: float
    candidate_dest_lon: float
    candidate_pickup_label: str | None
    candidate_dest_label: str | None
    candidate_seats: int
    candidate_max_extra_minutes: int
    candidate_departure_earliest: datetime
    candidate_departure_latest: datetime
    pickup_distance_m: float
    dest_distance_m: float
    shared_departure_start: datetime
    shared_departure_end: datetime
    detour_target_minutes: float
    detour_candidate_minutes: float
    best_sequence_label: str
    stops: list[StopInfo]
    total_shared_duration_seconds: float
    total_shared_distance_m: float
    is_route_approximate: bool
    routing_notice: str
    scores: ScoreBreakdown
    created_at: datetime
    # Phase 5A additions
    total_shared_distance_meters: float = 0.0
    distance_source: str = DistanceSource.PROVIDER_MATRIX_TABLE.value
    distance_is_approximate: bool = False
    routing_accuracy: str = "road_network_duration_road_network_distance"
    route_geometry: dict[str, Any] | None = None
    route_legs: list[RouteLeg] = field(default_factory=list)
    passenger_metrics: dict[str, PassengerJourneyMetrics] = field(default_factory=dict)
    direct_a_dist_m: float = 0.0
    direct_a_dur_s: float = 0.0
    direct_b_dist_m: float = 0.0
    direct_b_dur_s: float = 0.0


def _make_proposal_id(target_id: uuid.UUID, candidate_id: uuid.UUID) -> uuid.UUID:
    """Deterministic proposal ID from the canonical pair (min_id, max_id)."""
    low, high = sorted([str(target_id), str(candidate_id)])
    return uuid.uuid5(MATCH_PROPOSAL_NAMESPACE, f"{low}:{high}")


def _compute_passenger_metrics(
    *,
    proposal: MatchProposal,
    legs: list[RouteLeg],
    source: DistanceSource,
    is_approximate: bool,
) -> dict[str, PassengerJourneyMetrics]:
    """Calculate journey and detour breakdown for target and candidate passengers."""
    pos_a_p = next(
        i
        for i, s in enumerate(proposal.stops)
        if s.passenger_request_id == proposal.target_request_id
        and s.stop_type == "PICKUP"
    )
    pos_a_d = next(
        i
        for i, s in enumerate(proposal.stops)
        if s.passenger_request_id == proposal.target_request_id
        and s.stop_type == "DROPOFF"
    )
    pos_b_p = next(
        i
        for i, s in enumerate(proposal.stops)
        if s.passenger_request_id == proposal.candidate_request_id
        and s.stop_type == "PICKUP"
    )
    pos_b_d = next(
        i
        for i, s in enumerate(proposal.stops)
        if s.passenger_request_id == proposal.candidate_request_id
        and s.stop_type == "DROPOFF"
    )

    legs_a = legs[pos_a_p:pos_a_d]
    legs_b = legs[pos_b_p:pos_b_d]

    pooled_a_dist = sum(leg.distance_meters for leg in legs_a)
    pooled_a_dur = sum(leg.duration_seconds for leg in legs_a)
    pooled_b_dist = sum(leg.distance_meters for leg in legs_b)
    pooled_b_dur = sum(leg.duration_seconds for leg in legs_b)

    metrics_a = PassengerJourneyMetrics(
        passenger_request_id=str(proposal.target_request_id),
        solo_direct_distance_meters=proposal.direct_a_dist_m,
        solo_direct_duration_seconds=proposal.direct_a_dur_s,
        pooled_journey_distance_meters=pooled_a_dist,
        pooled_journey_duration_seconds=pooled_a_dur,
        detour_distance_meters=max(0.0, pooled_a_dist - proposal.direct_a_dist_m),
        detour_duration_minutes=max(
            0.0, (pooled_a_dur - proposal.direct_a_dur_s) / 60.0
        ),
        distance_source=source,
        is_approximate=is_approximate,
    )

    metrics_b = PassengerJourneyMetrics(
        passenger_request_id=str(proposal.candidate_request_id),
        solo_direct_distance_meters=proposal.direct_b_dist_m,
        solo_direct_duration_seconds=proposal.direct_b_dur_s,
        pooled_journey_distance_meters=pooled_b_dist,
        pooled_journey_duration_seconds=pooled_b_dur,
        detour_distance_meters=max(0.0, pooled_b_dist - proposal.direct_b_dist_m),
        detour_duration_minutes=max(
            0.0, (pooled_b_dur - proposal.direct_b_dur_s) / 60.0
        ),
        distance_source=source,
        is_approximate=is_approximate,
    )

    return {
        str(proposal.target_request_id): metrics_a,
        str(proposal.candidate_request_id): metrics_b,
    }


async def enrich_proposal_geometry(
    proposal: MatchProposal,
    routing: RoutingProvider,
) -> MatchProposal:
    """Enrich a match proposal with full multi-waypoint road geometry and per-leg metrics."""
    waypoints = [(s.latitude, s.longitude) for s in proposal.stops]
    stop_ids = [str(s.passenger_request_id) for s in proposal.stops]
    stop_labels = [s.label for s in proposal.stops]

    try:
        route = await routing.get_multi_waypoint_route(
            waypoints=waypoints,
            stop_ids=stop_ids,
            stop_labels=stop_labels,
        )
        proposal.total_shared_distance_m = route.total_distance.distance_meters
        proposal.total_shared_distance_meters = route.total_distance.distance_meters
        proposal.total_shared_duration_seconds = route.total_duration_seconds
        proposal.route_legs = route.legs
        proposal.route_geometry = route.full_geometry_geojson
        proposal.distance_source = route.total_distance.source.value
        proposal.is_route_approximate = route.total_distance.is_approximate
        proposal.distance_is_approximate = route.total_distance.is_approximate
        proposal.routing_accuracy = route.routing_accuracy
        if route.routing_notice:
            proposal.routing_notice = route.routing_notice

        # Recompute per-passenger metrics using Route API legs
        proposal.passenger_metrics = _compute_passenger_metrics(
            proposal=proposal,
            legs=route.legs,
            source=route.total_distance.source,
            is_approximate=route.total_distance.is_approximate,
        )
    except Exception as exc:
        logger.warning(
            "Failed to enrich proposal %s geometry (%s); synthesizing straight-line fallback.",
            proposal.proposal_id,
            type(exc).__name__,
        )
        # Synthesize RFC 7946 GeoJSON LineString connecting stop points directly
        cleaned_coords = [
            [round(s.longitude, 6), round(s.latitude, 6)] for s in proposal.stops
        ]
        proposal.route_geometry = {
            "type": "LineString",
            "coordinates": cleaned_coords,
        }
        proposal.routing_accuracy = "matrix_duration_synthesized_geometry"

    return proposal


async def run_matching(
    db: AsyncSession,
    routing: RoutingProvider,
    target: RideRequest,
) -> list[MatchProposal]:
    """
    Execute the matching pipeline for `target` request.
    Returns up to TOP_K_PROPOSALS ranked proposals.
    """
    started = time.perf_counter()
    now = datetime.now(UTC)

    # Extract target coordinates
    target_pickup_lat, target_pickup_lon = parse_point_coordinates(
        target.pickup_location
    )
    target_dest_lat, target_dest_lon = parse_point_coordinates(target.destination)

    target_bearing = bearing(
        target_pickup_lat,
        target_pickup_lon,
        target_dest_lat,
        target_dest_lon,
    )

    # --- Stage 1: PostGIS Candidate Discovery ---
    candidates_raw = await discover_candidates(
        db,
        request_id=target.id,
        user_id=target.user_id,
        pickup_lat=target_pickup_lat,
        pickup_lon=target_pickup_lon,
        dest_lat=target_dest_lat,
        dest_lon=target_dest_lon,
        departure_earliest=target.departure_earliest,
        departure_latest=target.departure_latest,
        seats_requested=target.seats_requested,
    )

    if not candidates_raw:
        logger.info(
            "Matching completed request=%s candidates=0 elapsed_ms=%.1f",
            target.id,
            (time.perf_counter() - started) * 1000,
        )
        return []

    logger.info(
        "Stage 1: %d candidates found for request %s", len(candidates_raw), target.id
    )

    # --- Stage 2: Directional & Corridor Filtering ---
    feasible_candidates = []
    for row in candidates_raw:
        cand_pickup_lat, cand_pickup_lon = parse_point_coordinates(
            row["pickup_location"]
        )
        cand_dest_lat, cand_dest_lon = parse_point_coordinates(row["destination"])

        dest_dist_m = float(row["dest_distance_m"])
        cand_bearing = bearing(
            cand_pickup_lat, cand_pickup_lon, cand_dest_lat, cand_dest_lon
        )
        delta_deg = angular_delta(target_bearing, cand_bearing)

        if not is_directionally_compatible(target_bearing, cand_bearing, dest_dist_m):
            logger.debug(
                "Stage 2: Pruned %s — angular delta %.1f° with dest %.0fm",
                row["candidate_id"],
                delta_deg,
                dest_dist_m,
            )
            continue

        feasible_candidates.append(
            (
                row,
                cand_pickup_lat,
                cand_pickup_lon,
                cand_dest_lat,
                cand_dest_lon,
                delta_deg,
            )
        )

    # DEC-002: Candidate limit for external routing (default cap 3 for public OSRM demo)
    max_routed = getattr(routing, "max_routed_candidates", 3)
    logger.info(
        "Stage 2: %d directionally compatible candidates; capping at %d for external routing",
        len(feasible_candidates),
        max_routed,
    )
    routed_candidates = feasible_candidates[:max_routed]

    proposals: list[MatchProposal] = []

    for (
        row,
        cand_pickup_lat,
        cand_pickup_lon,
        cand_dest_lat,
        cand_dest_lon,
        delta_deg,
    ) in routed_candidates:
        candidate_id = row["candidate_id"]
        pickup_dist_m = float(row["pickup_distance_m"])
        dest_dist_m = float(row["dest_distance_m"])
        overlap_s = float(row["overlap_seconds"])

        # Temporal window sizes
        tgt_earliest = target.departure_earliest
        tgt_latest = target.departure_latest
        if tgt_earliest.tzinfo is None:
            tgt_earliest = tgt_earliest.replace(tzinfo=UTC)
        if tgt_latest.tzinfo is None:
            tgt_latest = tgt_latest.replace(tzinfo=UTC)

        cand_earliest: datetime = row["departure_earliest"]
        cand_latest: datetime = row["departure_latest"]
        if cand_earliest.tzinfo is None:
            cand_earliest = cand_earliest.replace(tzinfo=UTC)
        if cand_latest.tzinfo is None:
            cand_latest = cand_latest.replace(tzinfo=UTC)

        window_a_s = (tgt_latest - tgt_earliest).total_seconds()
        window_b_s = (cand_latest - cand_earliest).total_seconds()

        shared_start = max(tgt_earliest, cand_earliest)
        shared_end = min(tgt_latest, cand_latest)

        tgt_mid_minutes = (
            tgt_earliest + (tgt_latest - tgt_earliest) / 2
        ).timestamp() / 60
        cand_mid_minutes = (
            cand_earliest + (cand_latest - cand_earliest) / 2
        ).timestamp() / 60
        mid_delta_min = abs(tgt_mid_minutes - cand_mid_minutes)

        # --- Stage 3: Route & Detour Evaluation ---
        route = await evaluate_pairwise_detour(
            provider=routing,
            pickup_a=(target_pickup_lat, target_pickup_lon),
            dest_a=(target_dest_lat, target_dest_lon),
            pickup_b=(cand_pickup_lat, cand_pickup_lon),
            dest_b=(cand_dest_lat, cand_dest_lon),
            max_extra_a=target.max_extra_minutes,
            max_extra_b=int(row["max_extra_minutes"]),
        )

        if route is None:
            logger.debug("Stage 3: Pruned %s — detour exceeds tolerance", candidate_id)
            continue

        best_seq = route.best_sequence

        # Build ordered stops for best sequence
        stops = _build_stops(
            sequence_label=best_seq.sequence_label,
            target_id=target.id,
            candidate_id=candidate_id,
            pickup_a=(target_pickup_lat, target_pickup_lon),
            dest_a=(target_dest_lat, target_dest_lon),
            pickup_b=(cand_pickup_lat, cand_pickup_lon),
            dest_b=(cand_dest_lat, cand_dest_lon),
            label_pickup_a=target.pickup_label,
            label_dest_a=target.destination_label,
            label_pickup_b=row.get("pickup_label"),
            label_dest_b=row.get("destination_label"),
        )

        total_shared_dist_m = best_seq.distance_total_meters
        total_shared_dur_s = best_seq.duration_total_seconds

        # Build Stage 1 matrix legs
        matrix_res = route.matrix_result
        legs: list[RouteLeg] = []
        stop_names = best_seq.sequence_label.split("→")
        name_to_idx = {"PA": 0, "PB": 1, "DA": 2, "DB": 3}
        if matrix_res is not None:
            for i in range(len(stop_names) - 1):
                from_idx = name_to_idx[stop_names[i]]
                to_idx = name_to_idx[stop_names[i + 1]]
                leg_dur = matrix_res.durations[from_idx][to_idx]
                leg_dist = matrix_res.distances[from_idx][to_idx]
                legs.append(
                    RouteLeg(
                        sequence=i + 1,
                        start_stop_id=str(stops[i].passenger_request_id),
                        end_stop_id=str(stops[i + 1].passenger_request_id),
                        start_label=stops[i].label,
                        end_label=stops[i + 1].label,
                        distance_meters=leg_dist,
                        duration_seconds=leg_dur,
                    )
                )

        # --- Stage 4: Scoring ---
        scores = compute_score(
            pickup_distance_m=pickup_dist_m,
            dest_distance_m=dest_dist_m,
            angular_delta_deg=delta_deg,
            overlap_seconds=overlap_s,
            window_a_seconds=window_a_s,
            window_b_seconds=window_b_s,
            midpoint_delta_minutes=mid_delta_min,
            detour_a_minutes=best_seq.detour_a_minutes,
            detour_b_minutes=best_seq.detour_b_minutes,
            max_extra_a=target.max_extra_minutes,
            max_extra_b=int(row["max_extra_minutes"]),
            seats_a=target.seats_requested,
            seats_b=int(row["seats_requested"]),
        )

        proposal = MatchProposal(
            proposal_id=_make_proposal_id(target.id, candidate_id),
            target_request_id=target.id,
            candidate_request_id=candidate_id,
            candidate_user_id=row["candidate_user_id"],
            candidate_display_name=row["owner_name"] or "Unknown",
            candidate_pickup_lat=cand_pickup_lat,
            candidate_pickup_lon=cand_pickup_lon,
            candidate_dest_lat=cand_dest_lat,
            candidate_dest_lon=cand_dest_lon,
            candidate_pickup_label=row.get("pickup_label"),
            candidate_dest_label=row.get("destination_label"),
            candidate_seats=int(row["seats_requested"]),
            candidate_max_extra_minutes=int(row["max_extra_minutes"]),
            candidate_departure_earliest=cand_earliest,
            candidate_departure_latest=cand_latest,
            pickup_distance_m=pickup_dist_m,
            dest_distance_m=dest_dist_m,
            shared_departure_start=shared_start,
            shared_departure_end=shared_end,
            detour_target_minutes=best_seq.detour_a_minutes,
            detour_candidate_minutes=best_seq.detour_b_minutes,
            best_sequence_label=best_seq.sequence_label,
            stops=stops,
            total_shared_duration_seconds=total_shared_dur_s,
            total_shared_distance_m=total_shared_dist_m,
            total_shared_distance_meters=total_shared_dist_m,
            is_route_approximate=best_seq.is_approximate,
            distance_is_approximate=best_seq.is_approximate,
            distance_source=best_seq.distance_source.value,
            routing_accuracy=route.routing_accuracy,
            routing_notice=best_seq.notice,
            scores=scores,
            created_at=now,
            route_legs=legs,
            direct_a_dist_m=route.distance_direct_a_meters,
            direct_a_dur_s=route.duration_direct_a_seconds,
            direct_b_dist_m=route.distance_direct_b_meters,
            direct_b_dur_s=route.duration_direct_b_seconds,
        )

        # Compute initial per-passenger metrics from matrix legs
        proposal.passenger_metrics = _compute_passenger_metrics(
            proposal=proposal,
            legs=legs,
            source=best_seq.distance_source,
            is_approximate=best_seq.is_approximate,
        )

        proposals.append(proposal)

    # Rank: score DESC, then total detour ASC, then pickup_dist ASC
    proposals.sort(
        key=lambda p: (
            -p.scores.composite_score,
            p.detour_target_minutes + p.detour_candidate_minutes,
            p.pickup_distance_m,
        )
    )

    top_proposals = proposals[:TOP_K_PROPOSALS]

    # DEC-001: Enrich Top 1 proposal with full GeoJSON route geometry and Route API metrics
    if top_proposals:
        top_proposals[0] = await enrich_proposal_geometry(top_proposals[0], routing)

    logger.info(
        "Matching completed request=%s candidates=%d proposals=%d elapsed_ms=%.1f",
        target.id,
        len(candidates_raw),
        len(top_proposals),
        (time.perf_counter() - started) * 1000,
    )
    return top_proposals


def _build_stops(
    *,
    sequence_label: str,
    target_id: uuid.UUID,
    candidate_id: uuid.UUID,
    pickup_a: tuple[float, float],
    dest_a: tuple[float, float],
    pickup_b: tuple[float, float],
    dest_b: tuple[float, float],
    label_pickup_a: str | None,
    label_dest_a: str | None,
    label_pickup_b: str | None,
    label_dest_b: str | None,
) -> list[StopInfo]:
    """Build ordered stops for the given sequence label."""
    lat_a_p, lon_a_p = pickup_a
    lat_a_d, lon_a_d = dest_a
    lat_b_p, lon_b_p = pickup_b
    lat_b_d, lon_b_d = dest_b

    stops = {
        "PA": ("PICKUP", lat_a_p, lon_a_p, target_id, label_pickup_a),
        "PB": ("PICKUP", lat_b_p, lon_b_p, candidate_id, label_pickup_b),
        "DA": ("DROPOFF", lat_a_d, lon_a_d, target_id, label_dest_a),
        "DB": ("DROPOFF", lat_b_d, lon_b_d, candidate_id, label_dest_b),
    }
    return [
        StopInfo(index, *stops[name])
        for index, name in enumerate(sequence_label.split("→"), start=1)
    ]
