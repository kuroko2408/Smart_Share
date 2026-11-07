"""Pydantic schemas for the matching engine API responses."""

from __future__ import annotations

import uuid
from datetime import datetime

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


class MatchProposalSchema(BaseModel):
    proposal_id: uuid.UUID
    target_request_id: uuid.UUID
    candidate: MatchCandidateSummarySchema
    ordered_stops: list[StopPointSchema]
    total_shared_distance_km: float
    total_shared_duration_minutes: float
    best_sequence: str
    is_route_approximate: bool
    distance_is_approximate: bool
    routing_accuracy: str
    routing_notice: str
    compatibility_explanations: list[str]
    created_at: datetime


class MatchListResponseSchema(BaseModel):
    target_request_id: uuid.UUID
    total_candidates_found: int
    proposals: list[MatchProposalSchema]
