"""Pydantic schemas for the matching engine API responses."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ScoreBreakdownSchema(BaseModel):
    pickup_proximity_score: float = Field(..., ge=0.0, le=1.0)
    destination_similarity_score: float = Field(..., ge=0.0, le=1.0)
    departure_time_score: float = Field(..., ge=0.0, le=1.0)
    route_detour_score: float = Field(..., ge=0.0, le=1.0)
    composite_score: float = Field(..., ge=0.0, le=1.0)


class LocationPointSchema(BaseModel):
    latitude: float
    longitude: float
    label: str | None = None


class StopPointSchema(BaseModel):
    sequence: int
    stop_type: str  # "PICKUP" or "DROPOFF"
    location: LocationPointSchema
    passenger_request_id: uuid.UUID


class MatchCandidateSummarySchema(BaseModel):
    candidate_request_id: uuid.UUID
    candidate_display_name: str
    candidate_pickup: LocationPointSchema
    candidate_destination: LocationPointSchema
    seats_requested: int
    pickup_distance_meters: float
    destination_distance_meters: float
    shared_departure_window_start: datetime
    shared_departure_window_end: datetime
    estimated_detour_minutes_target: float
    estimated_detour_minutes_candidate: float
    scores: ScoreBreakdownSchema


class GeoJSONLineStringSchema(BaseModel):
    type: Literal["LineString"] = "LineString"
    coordinates: list[tuple[float, float]] = Field(
        ..., description="Array of [longitude, latitude] coordinate pairs (RFC 7946)"
    )


class RouteLegSchema(BaseModel):
    sequence: int
    start_stop_id: uuid.UUID
    end_stop_id: uuid.UUID
    start_label: str | None = None
    end_label: str | None = None
    distance_meters: float
    distance_km: float
    duration_seconds: float
    duration_minutes: float


class PassengerJourneyDetailSchema(BaseModel):
    passenger_request_id: uuid.UUID
    solo_direct_distance_km: float
    solo_direct_distance_meters: float
    solo_direct_duration_minutes: float
    solo_direct_duration_seconds: float
    pooled_distance_km: float
    pooled_distance_meters: float
    pooled_duration_minutes: float
    pooled_duration_seconds: float
    detour_distance_km: float
    detour_distance_meters: float
    detour_duration_minutes: float


class MatchProposalSchema(BaseModel):
    proposal_id: uuid.UUID
    target_request_id: uuid.UUID
    candidate: MatchCandidateSummarySchema
    ordered_stops: list[StopPointSchema]
    total_shared_distance_km: float
    total_shared_distance_meters: float = 0.0
    total_shared_duration_minutes: float
    total_shared_duration_seconds: float = 0.0
    best_sequence: str
    is_route_approximate: bool
    distance_is_approximate: bool
    distance_source: str = "provider_matrix_table"
    routing_accuracy: str
    routing_notice: str
    compatibility_explanations: list[str]
    created_at: datetime
    route_geometry: GeoJSONLineStringSchema | None = None
    route_legs: list[RouteLegSchema] = Field(default_factory=list)
    passenger_metrics: dict[str, PassengerJourneyDetailSchema] = Field(
        default_factory=dict
    )


class MatchListResponseSchema(BaseModel):
    target_request_id: uuid.UUID
    total_candidates_found: int
    proposals: list[MatchProposalSchema]
