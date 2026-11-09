"""Fare estimation domain types; these estimates are not physical meter readings."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class EconomicStatus(StrEnum):
    SAVINGS = "SAVINGS"
    BREAK_EVEN = "BREAK_EVEN"
    UNATTRACTIVE = "UNATTRACTIVE"


class PulseQuantizationMode(StrEnum):
    CONTINUOUS = "CONTINUOUS"
    CEILING = "CEILING"
    FLOOR = "FLOOR"


class SurchargeStatus(StrEnum):
    NONE = "NONE"
    APPLIED = "APPLIED"
    CONDITIONAL = "CONDITIONAL"


class FareAccuracy(StrEnum):
    ROAD_ROUTE = "ROAD_ROUTE"
    MATRIX_SCREENING = "MATRIX_SCREENING"
    CALIBRATED_FALLBACK = "CALIBRATED_FALLBACK"
    GEODESIC_ONLY = "GEODESIC_ONLY"


@dataclass(frozen=True)
class FareModelConfig:
    model_id: str = "mumbai_taxi_standard"
    version: str = "1.0.0"
    currency: str = "INR"
    base_fare: Decimal = Decimal("33.00")
    base_distance_meters: Decimal = Decimal("1500")
    rate_per_km: Decimal = Decimal("21.90")
    pulse_distance_meters: Decimal = Decimal("100")
    pulse_fare: Decimal = Decimal("2.19")
    night_multiplier: Decimal = Decimal("1.25")


@dataclass(frozen=True)
class FareAmount:
    estimate: Decimal
    estimate_paise: int
    rounded_estimate_rupees: int


@dataclass(frozen=True)
class FareRange:
    minimum: FareAmount
    maximum: FareAmount


@dataclass(frozen=True)
class FareComponentEstimate:
    amount: FareAmount
    surcharge_status: SurchargeStatus
    fare_range: FareRange | None
    distance_meters: Decimal
    source: str
    accuracy: FareAccuracy


@dataclass(frozen=True)
class PassengerAllocation:
    solo_fare: FareAmount
    allocated_fare: FareAmount
    savings: FareAmount
    savings_percent: float
    is_saving: bool


@dataclass(frozen=True)
class FareAllocationResult:
    total_shared_fare: FareAmount
    combined_solo_fare: FareAmount
    combined_savings: FareAmount
    economic_status: EconomicStatus
    is_economically_beneficial: bool
    passenger_a: PassengerAllocation
    passenger_b: PassengerAllocation
    bilateral_consent: bool = False


@dataclass(frozen=True)
class MatchFareEstimate:
    shared_journey: FareComponentEstimate
    your_solo_baseline: FareComponentEstimate
    # Internal Phase 5C input only. Never serialize this field to the current viewer.
    co_passenger_solo_baseline: FareComponentEstimate
    composite_accuracy: FareAccuracy
    model_id: str
    model_version: str
    pulse_quantization_mode: PulseQuantizationMode
<<<<<<< Updated upstream
    minimum_fare_paise: int
    viewer_is_canonical_passenger_a: bool
=======
<<<<<<< HEAD
    minimum_fare_paise: int
    viewer_is_canonical_passenger_a: bool
=======
    allocation: FareAllocationResult | None = None
>>>>>>> 3dfc1f3 (5C)
>>>>>>> Stashed changes
