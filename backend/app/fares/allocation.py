<<<<<<< Updated upstream
=======
<<<<<<< HEAD
>>>>>>> Stashed changes
"""Pairwise proportional fare allocation and economic benefit assessment.

This module consumes Phase 5B estimates. Exact allocation disclosures are
serialized only after both participants affirmatively consent under DEC-013.
<<<<<<< Updated upstream
=======
=======
"""Fair solo-fare proportional fare allocation service (Phase 5C / DEC-008).

Calculates deterministic passenger contributions and savings using each passenger's
own solo fare as their allocation weight. Uses Decimal arithmetic and integer paise
throughout, with deterministic residual rounding preserving the agreed shared fare
down to 0.0000 paise.
>>>>>>> 3dfc1f3 (5C)
>>>>>>> Stashed changes
"""

from __future__ import annotations

<<<<<<< Updated upstream
=======
<<<<<<< HEAD
>>>>>>> Stashed changes
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from app.fares.models import FareAmount, FareComponentEstimate, MatchFareEstimate


class AllocationError(ValueError):
    """Fare input is missing, inconsistent, or outside the pairwise contract."""


class EconomicClassification(StrEnum):
    POSITIVE = "POSITIVE"
    BREAK_EVEN = "BREAK_EVEN"
    NEGATIVE = "NEGATIVE"
    CONDITIONAL = "CONDITIONAL"


# Each of the two solo fares and the shared fare can move by up to half a paise
# when rounded independently. At integer-paise precision, treating a ±1 paise
# result as neutral ensures only a difference of at least 2 paise is classified
# as directional; that exceeds the maximum 1.5-paise aggregate rounding error.
ECONOMIC_ROUNDING_TOLERANCE_PAISE = 1


@dataclass(frozen=True)
class PassengerAllocation:
    solo_baseline: Decimal
    contribution: Decimal
    savings: Decimal
    savings_percent: Decimal


@dataclass(frozen=True)
class PairwiseFareAllocation:
    shared_total: Decimal
    combined_solo_baseline: Decimal
    combined_savings: Decimal
    combined_savings_percent: Decimal
    detour_surcharge: Decimal
    classification: EconomicClassification
    passenger_a: PassengerAllocation
    passenger_b: PassengerAllocation


@dataclass(frozen=True)
class EconomicAssessment:
    """Economic result; scenario allocations remain internal until consent."""

    classification: EconomicClassification
    message: str
    scenarios: tuple[EconomicScenario, ...] = ()


@dataclass(frozen=True)
class EconomicScenario:
    """Bilateral-consent-only allocations for a known tariff scenario."""

    tariff_period: str
    allocation: PairwiseFareAllocation


def _classify_combined_savings(savings_paise: int) -> EconomicClassification:
    if savings_paise > ECONOMIC_ROUNDING_TOLERANCE_PAISE:
        return EconomicClassification.POSITIVE
    if savings_paise < -ECONOMIC_ROUNDING_TOLERANCE_PAISE:
        return EconomicClassification.NEGATIVE
    return EconomicClassification.BREAK_EVEN


def _amount_paise(value: FareAmount, name: str, minimum_paise: int) -> int:
    if type(value.estimate_paise) is not int or value.estimate_paise < minimum_paise:
        raise AllocationError(f"{name} must be at least the configured minimum fare")
    expected = (Decimal(value.estimate_paise) / Decimal(100)).quantize(Decimal("0.01"))
    if not isinstance(value.estimate, Decimal) or value.estimate != expected:
        raise AllocationError(f"{name} estimate and paise fields are inconsistent")
    return value.estimate_paise


def allocate_pairwise_fares(
    shared: FareAmount,
    solo_a: FareAmount,
    solo_b: FareAmount,
    *,
    minimum_fare_paise: int = 3300,
) -> PairwiseFareAllocation:
    """Allocate integer paise proportionally to solo fares, conserving every paisa.

    Passenger A receives ROUND_HALF_UP of their proportional quota; Passenger B
    receives the exact remainder, matching DEC-008's deterministic tie rule.
    """
    if type(minimum_fare_paise) is not int or minimum_fare_paise <= 0:
        raise AllocationError("Configured minimum fare must be positive integer paise")
    shared_p = _amount_paise(shared, "shared fare", minimum_fare_paise)
    solo_a_p = _amount_paise(solo_a, "Passenger A solo baseline", minimum_fare_paise)
    solo_b_p = _amount_paise(solo_b, "Passenger B solo baseline", minimum_fare_paise)

    solo_total_p = solo_a_p + solo_b_p
    quota_a = Decimal(shared_p) * Decimal(solo_a_p) / Decimal(solo_total_p)
    share_a_p = int(quota_a.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    share_b_p = shared_p - share_a_p
    if share_a_p < 0 or share_b_p < 0 or share_a_p + share_b_p != shared_p:
        raise AllocationError("Allocation violated non-negative conservation invariant")

    savings_a_p = solo_a_p - share_a_p
    savings_b_p = solo_b_p - share_b_p
    combined_savings_p = solo_total_p - shared_p

    def money(paise: int) -> Decimal:
        return (Decimal(paise) / Decimal(100)).quantize(Decimal("0.01"))

    def passenger(solo_p: int, share_p: int, savings_p: int) -> PassengerAllocation:
        solo_value = money(solo_p)
        percentage = (Decimal(savings_p) / Decimal(solo_p) * Decimal(100)).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )
        return PassengerAllocation(
            solo_baseline=solo_value,
            contribution=money(share_p),
            savings=money(savings_p),
            savings_percent=percentage,
        )

    classification = _classify_combined_savings(combined_savings_p)
    shared_value = money(shared_p)
    combined_solo_value = money(solo_total_p)
    combined_savings = money(combined_savings_p)
    combined_percentage = (
        Decimal(combined_savings_p) / Decimal(solo_total_p) * Decimal(100)
    ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    result = PairwiseFareAllocation(
        shared_total=shared_value,
        combined_solo_baseline=combined_solo_value,
        combined_savings=combined_savings,
        combined_savings_percent=combined_percentage,
        detour_surcharge=money(max(0, -combined_savings_p)),
        classification=classification,
        passenger_a=passenger(solo_a_p, share_a_p, savings_a_p),
        passenger_b=passenger(solo_b_p, share_b_p, savings_b_p),
    )
    if (
        result.passenger_a.contribution + result.passenger_b.contribution
        != result.shared_total
    ):
        raise AllocationError("Allocation failed exact currency conservation")
    return result


def _possible_amounts(
    component: FareComponentEstimate,
) -> tuple[FareAmount, FareAmount]:
    if component.fare_range is None:
        return component.amount, component.amount
    return component.fare_range.minimum, component.fare_range.maximum


def assess_match_economics(
    fares: MatchFareEstimate,
    *,
    minimum_fare_paise: int = 3300,
) -> tuple[PairwiseFareAllocation, EconomicAssessment]:
    """Calculate pairwise allocation and return a coarse, privacy-safe status."""
    allocation = allocate_pairwise_fares(
        fares.shared_journey.amount,
        fares.your_solo_baseline.amount
        if fares.viewer_is_canonical_passenger_a
        else fares.co_passenger_solo_baseline.amount,
        fares.co_passenger_solo_baseline.amount
        if fares.viewer_is_canonical_passenger_a
        else fares.your_solo_baseline.amount,
        minimum_fare_paise=minimum_fare_paise,
    )
    shared_day, shared_night = _possible_amounts(fares.shared_journey)
    own_day, own_night = _possible_amounts(fares.your_solo_baseline)
    other_day, other_night = _possible_amounts(fares.co_passenger_solo_baseline)
    day_result = allocate_pairwise_fares(
        shared_day,
        own_day if fares.viewer_is_canonical_passenger_a else other_day,
        other_day if fares.viewer_is_canonical_passenger_a else own_day,
        minimum_fare_paise=minimum_fare_paise,
    )
    night_result = allocate_pairwise_fares(
        shared_night,
        own_night if fares.viewer_is_canonical_passenger_a else other_night,
        other_night if fares.viewer_is_canonical_passenger_a else own_night,
        minimum_fare_paise=minimum_fare_paise,
    )

    scenarios = (
        (EconomicScenario("DAY", day_result), EconomicScenario("NIGHT", night_result))
        if any(
            component.fare_range is not None
            for component in (
                fares.shared_journey,
                fares.your_solo_baseline,
                fares.co_passenger_solo_baseline,
            )
        )
        else ()
    )
    if day_result.classification != night_result.classification:
        assessment = EconomicAssessment(
            classification=EconomicClassification.CONDITIONAL,
            message=(
                "Whether sharing costs less or more than two separate rides "
                "depends on whether the day or night tariff applies. The fare "
                "estimates above show the applicable range."
            ),
            scenarios=scenarios,
        )
    elif allocation.classification is EconomicClassification.POSITIVE:
        assessment = EconomicAssessment(
            classification=EconomicClassification.POSITIVE,
            message=(
                "The shared trip is estimated to cost less overall than both "
                "passengers taking separate rides. Individual amounts are shown "
                "only after both passengers consent; paise rounding can make an "
                "individual estimate break even."
            ),
            scenarios=scenarios,
        )
    elif allocation.classification is EconomicClassification.BREAK_EVEN:
        assessment = EconomicAssessment(
            classification=EconomicClassification.BREAK_EVEN,
            message=(
                "Sharing and taking two separate rides have approximately the "
                "same estimated total cost (within ₹0.01 fare-rounding tolerance)."
            ),
            scenarios=scenarios,
        )
    else:
        assessment = EconomicAssessment(
            classification=EconomicClassification.NEGATIVE,
            message=(
                "Taking two separate rides is estimated to cost less overall "
                "than sharing. This compatible match is not a money-saving option."
            ),
            scenarios=scenarios,
        )
    return allocation, assessment
<<<<<<< Updated upstream
=======
=======
from decimal import ROUND_HALF_UP, Decimal

from app.fares.models import (
    EconomicStatus,
    FareAllocationResult,
    FareAmount,
    PassengerAllocation,
)


def paise_to_fare_amount(paise: int) -> FareAmount:
    """Convert integer paise to a FareAmount domain object without float math."""
    rupees_dec = (Decimal(paise) / Decimal(100)).quantize(Decimal("0.01"))
    rounded_rupees = int(
        (Decimal(paise) / Decimal(100)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )
    return FareAmount(
        estimate=rupees_dec,
        estimate_paise=paise,
        rounded_estimate_rupees=rounded_rupees,
    )


def _savings_percent(savings_paise: int, solo_paise: int) -> float:
    """Compute percentage savings rounded to 2 decimal places."""
    if solo_paise <= 0 or savings_paise <= 0:
        return 0.0
    pct = (Decimal(savings_paise) / Decimal(solo_paise) * Decimal(100)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return float(pct)


def calculate_fare_allocation(
    shared_fare: FareAmount,
    solo_fare_a: FareAmount,
    solo_fare_b: FareAmount,
    *,
    bilateral_consent: bool = False,
) -> FareAllocationResult:
    """
    Allocate the agreed shared trip fare between two passengers proportionally to solo fares.

    Invariants:
    1. contribution_a + contribution_b == shared_fare (exact down to 0 paise).
    2. Driver receives 100% of the agreed shared fare (no gross fare reduction).
    3. Both contributions are non-negative.
    4. Economic outcomes:
       - SAVINGS: shared_fare < combined_solo_fare (both save, subject to paise rounding).
       - BREAK_EVEN: shared_fare == combined_solo_fare (neither told they save).
       - UNATTRACTIVE: shared_fare > combined_solo_fare (negative savings reported; no fabricated savings).
    """
    shared_paise = shared_fare.estimate_paise
    solo_a_paise = solo_fare_a.estimate_paise
    solo_b_paise = solo_fare_b.estimate_paise

    if shared_paise < 0 or solo_a_paise < 0 or solo_b_paise < 0:
        raise ValueError("Fare amounts must be non-negative integers in paise")

    combined_solo_paise = solo_a_paise + solo_b_paise
    combined_savings_paise = combined_solo_paise - shared_paise

    if combined_solo_paise == 0:
        if shared_paise == 0:
            contrib_a_paise = 0
            contrib_b_paise = 0
            status = EconomicStatus.BREAK_EVEN
            is_beneficial = False
        else:
            contrib_a_paise = shared_paise // 2
            contrib_b_paise = shared_paise - contrib_a_paise
            status = EconomicStatus.UNATTRACTIVE
            is_beneficial = False
    elif shared_paise == 0:
        contrib_a_paise = 0
        contrib_b_paise = 0
        status = EconomicStatus.SAVINGS
        is_beneficial = True
    else:
        # Proportional solo-fare allocation weights (DEC-008)
        w_a = Decimal(solo_a_paise) / Decimal(combined_solo_paise)
        contrib_a_paise = int(
            (Decimal(shared_paise) * w_a).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        )
        # Deterministic residual rounding: Passenger B receives exact remainder
        contrib_b_paise = shared_paise - contrib_a_paise

        # Enforce non-negative contribution bounds
        if contrib_a_paise < 0:
            contrib_a_paise = 0
            contrib_b_paise = shared_paise
        elif contrib_a_paise > shared_paise:
            contrib_a_paise = shared_paise
            contrib_b_paise = 0

        if combined_savings_paise > 0:
            status = EconomicStatus.SAVINGS
            is_beneficial = True
        elif combined_savings_paise == 0:
            status = EconomicStatus.BREAK_EVEN
            is_beneficial = False
        else:
            status = EconomicStatus.UNATTRACTIVE
            is_beneficial = False

    savings_a_paise = solo_a_paise - contrib_a_paise
    savings_b_paise = solo_b_paise - contrib_b_paise

    # Individual saving flag: True only if strictly saving paise and overall beneficial
    is_saving_a = is_beneficial and (savings_a_paise > 0)
    is_saving_b = is_beneficial and (savings_b_paise > 0)

    pass_a = PassengerAllocation(
        solo_fare=solo_fare_a,
        allocated_fare=paise_to_fare_amount(contrib_a_paise),
        savings=paise_to_fare_amount(savings_a_paise),
        savings_percent=_savings_percent(savings_a_paise, solo_a_paise)
        if is_saving_a
        else 0.0,
        is_saving=is_saving_a,
    )

    pass_b = PassengerAllocation(
        solo_fare=solo_fare_b,
        allocated_fare=paise_to_fare_amount(contrib_b_paise),
        savings=paise_to_fare_amount(savings_b_paise),
        savings_percent=_savings_percent(savings_b_paise, solo_b_paise)
        if is_saving_b
        else 0.0,
        is_saving=is_saving_b,
    )

    return FareAllocationResult(
        total_shared_fare=shared_fare,
        combined_solo_fare=paise_to_fare_amount(combined_solo_paise),
        combined_savings=paise_to_fare_amount(combined_savings_paise),
        economic_status=status,
        is_economically_beneficial=is_beneficial,
        passenger_a=pass_a,
        passenger_b=pass_b,
        bilateral_consent=bilateral_consent,
    )
>>>>>>> 3dfc1f3 (5C)
>>>>>>> Stashed changes
