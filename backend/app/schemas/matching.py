"""Pydantic schemas for the matching engine API responses."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
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


class FareAmountSchema(BaseModel):
    estimate: float
    estimate_paise: int
    rounded_estimate_rupees: int


class ConditionalFareRangeSchema(BaseModel):
    minimum: FareAmountSchema
    maximum: FareAmountSchema


class FareComponentSchema(BaseModel):
    estimate: float
    estimate_paise: int
    rounded_estimate_rupees: int
    distance_meters: float
    distance_source: str
    accuracy_tier: str
    surcharge_status: Literal["NONE", "APPLIED", "CONDITIONAL"]
    fare_range: ConditionalFareRangeSchema | None = None


class PassengerFareAllocationSchema(BaseModel):
    allocated_fare: FareAmountSchema
    savings: FareAmountSchema
    savings_percent: float
    is_saving: bool
    economic_status: Literal["SAVINGS", "BREAK_EVEN", "UNATTRACTIVE"]
    is_economically_beneficial: bool


class MatchFareEstimateSchema(BaseModel):
    shared_journey: FareComponentSchema
    your_solo_baseline: FareComponentSchema
    your_allocation: PassengerFareAllocationSchema | None = None
    your_allocated_fare: FareAmountSchema | None = None
    your_savings: FareAmountSchema | None = None
    your_savings_percent: float = 0.0
    economic_status: Literal["SAVINGS", "BREAK_EVEN", "UNATTRACTIVE"] = "SAVINGS"
    is_economically_beneficial: bool = True
    co_passenger_contribution: FareAmountSchema | None = None
    composite_accuracy: str
    fare_model_id: str
    fare_model_version: str
    pulse_quantization_mode: Literal["CONTINUOUS", "CEILING", "FLOOR"]
    excluded_charges: list[str]
    disclaimer: str


class EconomicAssessmentSchema(BaseModel):
    classification: Literal["POSITIVE", "BREAK_EVEN", "NEGATIVE", "CONDITIONAL"]
    message: str


class FareAllocationSchema(BaseModel):
    policy: Literal["PROPORTIONAL_TO_SOLO_BASELINE"]
    shared_total: float
    shared_total_paise: int
    your_contribution: float
    your_contribution_paise: int
    co_passenger_contribution: float
    co_passenger_contribution_paise: int
    your_savings: float
    your_savings_paise: int
    your_savings_percent: Decimal


class FareAllocationScenarioSchema(BaseModel):
    tariff_period: Literal["DAY", "NIGHT"]
    economic_classification: Literal["POSITIVE", "BREAK_EVEN", "NEGATIVE"]
    shared_total: float
    shared_total_paise: int
    your_contribution: float
    your_contribution_paise: int
    co_passenger_contribution: float
    co_passenger_contribution_paise: int
    your_savings: float
    your_savings_paise: int
    your_savings_percent: Decimal


class FareAllocationDisclosureSchema(BaseModel):
    consent_text_version: str
    consent_notice: str
    your_consent_active: bool
    co_passenger_consent_active: bool
    exact_disclosure_available: bool
    allocation: FareAllocationSchema | None = None
    conditional_scenarios: list[FareAllocationScenarioSchema] = Field(
        default_factory=list
    )


class MatchDisclosureConsentRequest(BaseModel):
    consent_text_version: str = "DEC-013-2026-11-08-v1"
    disclosure_mode: Literal["EXACT"] = "EXACT"
    action: Literal["GRANTED", "REVOKED"] = "GRANTED"


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
    fare_estimate: MatchFareEstimateSchema | None = None
    # Overall pair comparison only. Personal allocations/savings remain private.
    economic_assessment: EconomicAssessmentSchema | None = None
    fare_allocation_disclosure: FareAllocationDisclosureSchema | None = None


class MatchListResponseSchema(BaseModel):
    target_request_id: uuid.UUID
    total_candidates_found: int
    proposals: list[MatchProposalSchema]
