from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.fares.models import FareModelConfig, PulseQuantizationMode
from app.fares.service import estimate_match_fare
from app.fares.tariff import fare_for_distance
from app.matching.scoring import ScoreBreakdown
from app.matching.service import MatchProposal
from app.routing.models import DistanceSource


def test_continuous_tariff_boundaries_and_decimal_arithmetic():
    config = FareModelConfig()
    assert fare_for_distance(
        Decimal("1500"), config, PulseQuantizationMode.CONTINUOUS, night=False
    ).estimate == Decimal("33.00")
    assert fare_for_distance(
        Decimal("1501"), config, PulseQuantizationMode.CONTINUOUS, night=False
    ).estimate == Decimal("33.02")
    assert fare_for_distance(
        Decimal("1600"), config, PulseQuantizationMode.CONTINUOUS, night=False
    ).estimate == Decimal("35.19")


@pytest.mark.parametrize(
    ("mode", "expected"),
    [(PulseQuantizationMode.CEILING, "35.19"), (PulseQuantizationMode.FLOOR, "33.00")],
)
def test_pulse_modes_are_configurable(mode, expected):
    from app.fares.models import FareModelConfig

    fare = fare_for_distance(Decimal("1501"), FareModelConfig(), mode, night=False)
    assert fare.estimate == Decimal(expected)


def test_night_boundary_uses_ist_and_surcharge_applies_after_tariff():
    config = FareModelConfig()
    assert (
        fare_for_distance(
            Decimal("1000"), config, PulseQuantizationMode.CONTINUOUS, night=False
        ).rounded_estimate_rupees
        == 33
    )
    assert (
        fare_for_distance(
            Decimal("1000"), config, PulseQuantizationMode.CONTINUOUS, night=True
        ).rounded_estimate_rupees
        == 41
    )


@pytest.mark.parametrize(
    ("start", "end", "status"),
    [
        ("2026-11-07T23:59:59+05:30", "2026-11-07T23:59:59+05:30", "NONE"),
        ("2026-11-08T00:00:00+05:30", "2026-11-08T00:00:00+05:30", "APPLIED"),
        ("2026-11-08T04:59:59+05:30", "2026-11-08T04:59:59+05:30", "APPLIED"),
        ("2026-11-08T05:00:00+05:30", "2026-11-08T05:00:00+05:30", "NONE"),
    ],
)
def test_ist_surcharge_boundaries(start, end, status):
    estimate = estimate_match_fare(
        _proposal(datetime.fromisoformat(start), datetime.fromisoformat(end))
    )
    assert estimate.shared_journey.surcharge_status.value == status


def _proposal(start: datetime, end: datetime) -> MatchProposal:
    from app.matching.service import StopInfo

    target, candidate = uuid4(), uuid4()
    return MatchProposal(
        proposal_id=uuid4(),
        target_request_id=target,
        candidate_request_id=candidate,
        candidate_user_id=uuid4(),
        candidate_display_name="Rider",
        candidate_pickup_lat=19.0,
        candidate_pickup_lon=72.0,
        candidate_dest_lat=19.1,
        candidate_dest_lon=72.1,
        candidate_pickup_label=None,
        candidate_dest_label=None,
        candidate_seats=1,
        candidate_max_extra_minutes=15,
        candidate_departure_earliest=start,
        candidate_departure_latest=end,
        pickup_distance_m=100,
        dest_distance_m=200,
        shared_departure_start=start,
        shared_departure_end=end,
        detour_target_minutes=2,
        detour_candidate_minutes=2,
        best_sequence_label="PA→PB→DA→DB",
        stops=[StopInfo(1, "PICKUP", 19, 72, target, None)],
        total_shared_duration_seconds=3600,
        total_shared_distance_m=5000,
        is_route_approximate=True,
        routing_notice="approximate",
        scores=ScoreBreakdown(0.8, 0.8, 0.8, 0.8, 0.8),
        created_at=datetime.now(UTC),
        direct_a_dist_m=3000,
        direct_b_dist_m=4000,
        distance_source=DistanceSource.CALIBRATED_TORTUOSITY_FALLBACK.value,
    )


def test_matching_proposal_fare_is_viewer_scoped_and_accuracy_uses_weakest_input():
    from app.api.v1.endpoints.matching import _proposal_to_schema

    proposal = _proposal(
        datetime.fromisoformat("2026-11-08T10:00:00+05:30"),
        datetime.fromisoformat("2026-11-08T10:30:00+05:30"),
    )
    result = _proposal_to_schema(proposal).model_dump(mode="json")
    fare = result["fare_estimate"]
    assert fare["shared_journey"]["accuracy_tier"] == "CALIBRATED_FALLBACK"
    assert fare["composite_accuracy"] == "CALIBRATED_FALLBACK"
    assert fare["your_solo_baseline"]["estimate_paise"] > 0
    # Phase 5C: Authenticated viewer receives their own allocation & savings
    assert fare["your_allocated_fare"]["estimate_paise"] > 0
    assert fare["your_savings"]["estimate_paise"] > 0
    assert fare["your_allocation"]["is_saving"] is True
    assert fare["is_economically_beneficial"] is True
    # DEC-013 Privacy: Co-passenger private baseline, contribution and savings remain strictly redacted
    assert fare["co_passenger_contribution"] is None
    serialized = str(fare).lower()
    assert "candidate_solo" not in serialized
    assert "co_passenger_solo" not in serialized
    assert "does not claim to reproduce" in fare["disclaimer"]


def test_fallback_provenance_is_preserved_for_solo_baseline():
    proposal = _proposal(
        datetime.fromisoformat("2026-11-08T10:00:00+05:30"),
        datetime.fromisoformat("2026-11-08T10:30:00+05:30"),
    )
    proposal.direct_distance_source = (
        DistanceSource.CALIBRATED_TORTUOSITY_FALLBACK.value
    )
    estimate = estimate_match_fare(proposal)
    assert estimate.your_solo_baseline.accuracy.value == "CALIBRATED_FALLBACK"
    assert estimate.composite_accuracy.value == "CALIBRATED_FALLBACK"


def test_crossing_night_boundary_returns_conditional_estimate_range():
    start = datetime.fromisoformat("2026-11-07T23:30:00+05:30")
    end = datetime.fromisoformat("2026-11-08T00:30:00+05:30")
    estimate = estimate_match_fare(_proposal(start, end))
    assert estimate.shared_journey.surcharge_status.value == "CONDITIONAL"
    assert estimate.shared_journey.fare_range is not None
    assert (
        estimate.shared_journey.fare_range.maximum.estimate
        > estimate.shared_journey.fare_range.minimum.estimate
    )


def test_invalid_distance_is_rejected():
    from app.fares.models import FareModelConfig

    with pytest.raises(ValueError):
        fare_for_distance(
            Decimal("-1"),
            FareModelConfig(),
            PulseQuantizationMode.CONTINUOUS,
            night=False,
        )


def test_naive_departure_window_is_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        estimate_match_fare(_proposal(datetime(2026, 11, 8), datetime(2026, 11, 8, 1)))


def test_unavailable_fare_source_does_not_invalidate_match_proposal():
    from app.api.v1.endpoints.matching import _proposal_to_schema

    proposal = _proposal(
        datetime.fromisoformat("2026-11-08T10:00:00+05:30"),
        datetime.fromisoformat("2026-11-08T10:30:00+05:30"),
    )
    proposal.distance_source = DistanceSource.ACTUAL_TELEMETRY.value
    schema = _proposal_to_schema(proposal)
    assert schema.proposal_id == proposal.proposal_id
    assert schema.fare_estimate is None


<<<<<<< Updated upstream
=======
<<<<<<< HEAD
>>>>>>> Stashed changes
def test_dec008_allocation_conserves_paise_and_screens_the_reported_negative_case():
    from app.fares.allocation import EconomicClassification, allocate_pairwise_fares
    from app.fares.models import FareAmount

    def amount(paise: int) -> FareAmount:
        return FareAmount(Decimal(paise) / 100, paise, (paise + 50) // 100)

    result = allocate_pairwise_fares(amount(28327), amount(19296), amount(8361))
    assert result.shared_total == Decimal("283.27")
    assert result.combined_solo_baseline == Decimal("276.57")
    assert result.combined_savings == Decimal("-6.70")
    assert result.detour_surcharge == Decimal("6.70")
    assert result.classification is EconomicClassification.NEGATIVE
    assert result.passenger_a.contribution == Decimal("197.63")
    assert result.passenger_b.contribution == Decimal("85.64")
    assert result.passenger_a.savings == Decimal("-4.67")
    assert result.passenger_b.savings == Decimal("-2.03")
    assert (
        result.passenger_a.contribution + result.passenger_b.contribution
        == result.shared_total
    )
    assert (
        result.passenger_a.savings + result.passenger_b.savings
        == result.combined_savings
    )


def test_dec008_proportional_rounding_has_canonical_a_tie_and_no_negative_share():
    from app.fares.allocation import allocate_pairwise_fares
    from app.fares.models import FareAmount

    def amount(paise: int) -> FareAmount:
        return FareAmount(Decimal(paise) / 100, paise, (paise + 50) // 100)

    # Equal baselines and an odd shared paise exercise the approved A-first residual rule.
    result = allocate_pairwise_fares(amount(6601), amount(3300), amount(3300))
    assert result.passenger_a.contribution == Decimal("33.01")
    assert result.passenger_b.contribution == Decimal("33.00")
    assert min(result.passenger_a.contribution, result.passenger_b.contribution) >= 0


def test_individual_shares_do_not_get_mislabeled_when_pair_economics_are_negative():
    from app.fares.allocation import allocate_pairwise_fares
    from app.fares.models import FareAmount

    def amount(paise: int) -> FareAmount:
        return FareAmount(Decimal(paise) / 100, paise, (paise + 50) // 100)

    result = allocate_pairwise_fares(amount(28327), amount(19296), amount(8361))
    assert result.passenger_a.savings < 0
    assert result.passenger_b.savings < 0
    assert result.combined_savings < 0


def test_invalid_or_inconsistent_fare_inputs_are_rejected():
    from app.fares.allocation import AllocationError, allocate_pairwise_fares
    from app.fares.models import FareAmount

    good = FareAmount(Decimal("33.00"), 3300, 33)
    with pytest.raises(AllocationError, match="minimum fare"):
        allocate_pairwise_fares(FareAmount(Decimal("32.99"), 3299, 33), good, good)
    with pytest.raises(AllocationError, match="inconsistent"):
        allocate_pairwise_fares(FareAmount(Decimal("33.01"), 3300, 33), good, good)


@pytest.mark.parametrize(
    (
        "case_name",
        "direct_a_m",
        "direct_b_m",
        "shared_m",
        "shared_source",
        "direct_source",
        "expected_paise",
        "expected_savings_paise",
        "expected_classification",
        "expected_accuracy",
    ),
    [
        (
            "identical endpoints",
            5000,
            5000,
            5000,
            "provider_road_network_route",
            "provider_road_network_route",
            (10965, 10965, 10965),
            10965,
            "POSITIVE",
            "ROAD_ROUTE",
        ),
        (
            "near pickups, same destination",
            5000,
            5000,
            5200,
            "provider_road_network_route",
            "provider_road_network_route",
            (10965, 10965, 11403),
            10527,
            "POSITIVE",
            "ROAD_ROUTE",
        ),
        (
            "same pickup, nearby destinations",
            5000,
            5100,
            5200,
            "provider_road_network_route",
            "provider_road_network_route",
            (10965, 11184, 11403),
            10746,
            "POSITIVE",
            "ROAD_ROUTE",
        ),
        (
            "near pickups and destinations",
            5000,
            5100,
            6000,
            "provider_road_network_route",
            "provider_road_network_route",
            (10965, 11184, 13155),
            8994,
            "POSITIVE",
            "ROAD_ROUTE",
        ),
        (
            "far destinations, fallback source",
            5000,
            7000,
            20000,
            "calibrated_tortuosity_fallback",
            "calibrated_tortuosity_fallback",
            (10965, 15345, 43815),
            -17505,
            "NEGATIVE",
            "CALIBRATED_FALLBACK",
        ),
        (
            "pooled journey shorter than separate journeys",
            10000,
            10000,
            12000,
            "provider_road_network_route",
            "provider_matrix_table",
            (21915, 21915, 26295),
            17535,
            "POSITIVE",
            "MATRIX_SCREENING",
        ),
        (
            "equal estimated totals",
            3000,
            3000,
            6006.849315068493,
            "provider_road_network_route",
            "provider_road_network_route",
            (6585, 6585, 13170),
            0,
            "BREAK_EVEN",
            "ROAD_ROUTE",
        ),
        (
            "pooled journey more expensive",
            5000,
            5000,
            12000,
            "provider_road_network_route",
            "provider_road_network_route",
            (10965, 10965, 26295),
            -4365,
            "NEGATIVE",
            "ROAD_ROUTE",
        ),
    ],
)
def test_controlled_route_to_fare_and_economic_matrix(
    case_name,
    direct_a_m,
    direct_b_m,
    shared_m,
    shared_source,
    direct_source,
    expected_paise,
    expected_savings_paise,
    expected_classification,
    expected_accuracy,
):
    from app.fares.allocation import assess_match_economics

    start = datetime.fromisoformat("2026-11-08T10:00:00+05:30")
    proposal = _proposal(start, start)
    proposal.direct_a_dist_m = direct_a_m
    proposal.direct_b_dist_m = direct_b_m
    proposal.total_shared_distance_m = shared_m
    proposal.distance_source = shared_source
    proposal.direct_distance_source = direct_source

    fares = estimate_match_fare(proposal)
    allocation, assessment = assess_match_economics(fares)
    actual_paise = (
        fares.your_solo_baseline.amount.estimate_paise,
        fares.co_passenger_solo_baseline.amount.estimate_paise,
        fares.shared_journey.amount.estimate_paise,
    )
    assert actual_paise == expected_paise, case_name
    assert allocation.combined_savings * 100 == expected_savings_paise, case_name
    assert assessment.classification.value == expected_classification, case_name
    assert fares.composite_accuracy.value == expected_accuracy, case_name
    assert (
        allocation.passenger_a.contribution + allocation.passenger_b.contribution
        == allocation.shared_total
    )


def test_one_paisa_is_rounding_break_even_but_two_paise_is_real_outcome():
    from app.fares.allocation import EconomicClassification, allocate_pairwise_fares
    from app.fares.models import FareAmount

    def amount(paise: int) -> FareAmount:
        return FareAmount(Decimal(paise) / 100, paise, (paise + 50) // 100)

    baseline_a, baseline_b = amount(3300), amount(3431)
    one_paisa = allocate_pairwise_fares(amount(6730), baseline_a, baseline_b)
    two_paise = allocate_pairwise_fares(amount(6729), baseline_a, baseline_b)
    assert one_paisa.combined_savings == Decimal("0.01")
    assert one_paisa.classification is EconomicClassification.BREAK_EVEN
    assert two_paise.combined_savings == Decimal("0.02")
    assert two_paise.classification is EconomicClassification.POSITIVE


def test_proportional_policy_cannot_make_one_passenger_lose_when_pair_saves():
    from app.fares.allocation import allocate_pairwise_fares
    from app.fares.models import FareAmount

    def amount(paise: int) -> FareAmount:
        return FareAmount(Decimal(paise) / 100, paise, (paise + 50) // 100)

    # Exhaust the small valid fare range around the ₹33 minimum. Under DEC-008,
    # shares are proportional to each solo fare and B receives the exact remainder.
    for solo_a in range(3300, 3320):
        for solo_b in range(3300, 3320):
            total_solo = solo_a + solo_b
            for shared in range(6600, total_solo):
                result = allocate_pairwise_fares(
                    amount(shared), amount(solo_a), amount(solo_b)
                )
                assert result.passenger_a.savings >= 0
                assert result.passenger_b.savings >= 0
                assert (
                    result.passenger_a.savings + result.passenger_b.savings
                    == result.combined_savings
                )


def test_proportional_policy_cannot_show_opposite_individual_savings_signs():
    from app.fares.allocation import allocate_pairwise_fares
    from app.fares.models import FareAmount

    def amount(paise: int) -> FareAmount:
        return FareAmount(Decimal(paise) / 100, paise, (paise + 50) // 100)

    # DEC-008's proportional quotas have the same sign relative to each solo
    # baseline. A-first rounding plus B's residual can produce zero for one
    # passenger, but cannot make one save while the other pays more.
    for solo_a in range(3300, 3320):
        for solo_b in range(3300, 3320):
            total_solo = solo_a + solo_b
            for shared in range(6600, total_solo + 20):
                result = allocate_pairwise_fares(
                    amount(shared), amount(solo_a), amount(solo_b)
                )
                assert not (
                    result.passenger_a.savings > 0 and result.passenger_b.savings < 0
                )
                assert not (
                    result.passenger_b.savings > 0 and result.passenger_a.savings < 0
                )
                assert (
                    result.passenger_a.savings + result.passenger_b.savings
                    == result.combined_savings
                )


def test_crossing_night_boundary_returns_consent_gated_day_and_night_allocations():
    from app.fares.allocation import (
        EconomicClassification,
        assess_match_economics,
    )

    proposal = _proposal(
        datetime.fromisoformat("2026-11-07T23:30:00+05:30"),
        datetime.fromisoformat("2026-11-08T00:30:00+05:30"),
    )
    proposal.direct_a_dist_m = 1500
    proposal.direct_b_dist_m = 1560
    proposal.total_shared_distance_m = 3066
    proposal.distance_source = DistanceSource.PROVIDER_ROAD_NETWORK_ROUTE.value
    proposal.direct_distance_source = DistanceSource.PROVIDER_MATRIX_TABLE.value

    fares = estimate_match_fare(proposal)
    allocation, assessment = assess_match_economics(fares)
    assert allocation.combined_savings == Decimal("0.02")
    assert assessment.classification is EconomicClassification.CONDITIONAL
    assert [
        (s.tariff_period, s.allocation.combined_savings) for s in assessment.scenarios
    ] == [
        ("DAY", Decimal("0.01")),
        ("NIGHT", Decimal("0.02")),
    ]

    from app.api.v1.endpoints.matching import _proposal_to_schema
    from app.fares.consent import ProposalConsentState

    none = ProposalConsentState(
        {proposal.target_request_id: False, proposal.candidate_request_id: False}
    )
    withheld = _proposal_to_schema(proposal, fare_domain=fares, consent_state=none)
    assert withheld.economic_assessment.classification == "CONDITIONAL"
    assert withheld.fare_allocation_disclosure.conditional_scenarios == []
    assert withheld.fare_allocation_disclosure.exact_disclosure_available is False

    both = ProposalConsentState(
        {proposal.target_request_id: True, proposal.candidate_request_id: True}
    )
    response = _proposal_to_schema(proposal, fare_domain=fares, consent_state=both)
    disclosure = response.fare_allocation_disclosure
    assert disclosure is not None
    assert disclosure.allocation is None
    assert [
        scenario.tariff_period for scenario in disclosure.conditional_scenarios
    ] == [
        "DAY",
        "NIGHT",
    ]
    assert all(
        scenario.shared_total_paise
        == scenario.your_contribution_paise + scenario.co_passenger_contribution_paise
        for scenario in disclosure.conditional_scenarios
    )


def test_exact_disclosure_is_absent_until_both_participants_consent():
    from app.api.v1.endpoints.matching import _proposal_to_schema
    from app.fares.consent import ProposalConsentState
    from app.fares.disclosure import CONSENT_NOTICE
<<<<<<< Updated upstream
=======
=======
def test_allocation_invariants_and_proportional_weighting():
    from app.fares.allocation import calculate_fare_allocation, paise_to_fare_amount
    from app.fares.models import EconomicStatus

    shared = paise_to_fare_amount(18000)  # ₹180.00
    solo_a = paise_to_fare_amount(12000)  # ₹120.00
    solo_b = paise_to_fare_amount(10000)  # ₹100.00

    alloc = calculate_fare_allocation(shared, solo_a, solo_b)

    # Invariant 1: Non-negative contributions
    assert alloc.passenger_a.allocated_fare.estimate_paise >= 0
    assert alloc.passenger_b.allocated_fare.estimate_paise >= 0

    # Invariant 2: Sum conservation in paise and rupees
    assert (
        alloc.passenger_a.allocated_fare.estimate_paise
        + alloc.passenger_b.allocated_fare.estimate_paise
        == shared.estimate_paise
    )
    assert (
        alloc.passenger_a.allocated_fare.estimate
        + alloc.passenger_b.allocated_fare.estimate
        == shared.estimate
    )

    # Invariant 3: Solo fares as weights: higher solo fare pays larger share
    assert solo_a.estimate_paise > solo_b.estimate_paise
    assert (
        alloc.passenger_a.allocated_fare.estimate_paise
        > alloc.passenger_b.allocated_fare.estimate_paise
    )

    # Invariant 4: Both passengers save when shared fare < combined solo fare
    assert shared.estimate_paise < (solo_a.estimate_paise + solo_b.estimate_paise)
    assert alloc.economic_status == EconomicStatus.SAVINGS
    assert alloc.is_economically_beneficial is True
    assert alloc.passenger_a.is_saving is True
    assert alloc.passenger_b.is_saving is True
    assert alloc.passenger_a.savings.estimate_paise > 0
    assert alloc.passenger_b.savings.estimate_paise > 0
    assert alloc.passenger_a.savings_percent > 0
    assert alloc.passenger_b.savings_percent > 0

    # Invariant 9: Original solo fares remain unchanged
    assert alloc.passenger_a.solo_fare == solo_a
    assert alloc.passenger_b.solo_fare == solo_b

    # Invariant 10: Original shared fare remains unchanged
    assert alloc.total_shared_fare == shared

    # Invariant 11: Driver receives full agreed gross fare
    assert (
        alloc.passenger_a.allocated_fare.estimate_paise
        + alloc.passenger_b.allocated_fare.estimate_paise
        == shared.estimate_paise
    )


def test_allocation_break_even_outcome():
    from app.fares.allocation import calculate_fare_allocation, paise_to_fare_amount
    from app.fares.models import EconomicStatus

    solo_a = paise_to_fare_amount(6000)
    solo_b = paise_to_fare_amount(4000)
    shared = paise_to_fare_amount(10000)  # Exactly equal to 6000 + 4000

    alloc = calculate_fare_allocation(shared, solo_a, solo_b)

    # Invariant 5: Break-even reports no savings
    assert alloc.economic_status == EconomicStatus.BREAK_EVEN
    assert alloc.is_economically_beneficial is False
    assert alloc.combined_savings.estimate_paise == 0
    assert alloc.passenger_a.savings.estimate_paise == 0
    assert alloc.passenger_b.savings.estimate_paise == 0
    assert alloc.passenger_a.is_saving is False
    assert alloc.passenger_b.is_saving is False
    assert alloc.passenger_a.savings_percent == 0.0
    assert alloc.passenger_b.savings_percent == 0.0
    # Invariant 2: Still strictly conserved
    assert (
        alloc.passenger_a.allocated_fare.estimate_paise
        + alloc.passenger_b.allocated_fare.estimate_paise
        == shared.estimate_paise
    )


def test_allocation_dissavings_outcome():
    from app.fares.allocation import calculate_fare_allocation, paise_to_fare_amount
    from app.fares.models import EconomicStatus

    solo_a = paise_to_fare_amount(5000)
    solo_b = paise_to_fare_amount(5000)
    shared = paise_to_fare_amount(12000)  # Greater than combined 10000

    alloc = calculate_fare_allocation(shared, solo_a, solo_b)

    # Invariant 6: Dissavings reports negative combined savings and UNATTRACTIVE
    assert alloc.economic_status == EconomicStatus.UNATTRACTIVE
    assert alloc.is_economically_beneficial is False
    assert alloc.combined_savings.estimate_paise == -2000
    assert alloc.passenger_a.savings.estimate_paise == -1000
    assert alloc.passenger_b.savings.estimate_paise == -1000

    # Invariant 7: No fabricated savings
    assert alloc.passenger_a.is_saving is False
    assert alloc.passenger_b.is_saving is False
    assert alloc.passenger_a.savings_percent == 0.0
    assert alloc.passenger_b.savings_percent == 0.0

    # Invariant 11: Driver's gross fare is preserved, not artificially discounted
    assert (
        alloc.passenger_a.allocated_fare.estimate_paise
        + alloc.passenger_b.allocated_fare.estimate_paise
        == 12000
    )


def test_allocation_rounding_cannot_create_false_savings():
    from app.fares.allocation import calculate_fare_allocation, paise_to_fare_amount

    # Invariant 8: Micro-fare edge case where rounding could round share up to solo fare
    solo_a = paise_to_fare_amount(1)
    solo_b = paise_to_fare_amount(10000)
    shared = paise_to_fare_amount(10000)  # combined is 10001, shared is 10000

    alloc = calculate_fare_allocation(shared, solo_a, solo_b)

    # 10000 * 1 / 10001 rounds to 1 paisa for A -> savings = 0
    assert alloc.passenger_a.allocated_fare.estimate_paise == 1
    assert alloc.passenger_a.savings.estimate_paise == 0
    assert alloc.passenger_a.is_saving is False  # False savings claim prevented!
    assert alloc.passenger_b.allocated_fare.estimate_paise == 9999
    assert alloc.passenger_b.savings.estimate_paise == 1
    assert alloc.passenger_b.is_saving is True
    assert (
        alloc.passenger_a.allocated_fare.estimate_paise
        + alloc.passenger_b.allocated_fare.estimate_paise
        == shared.estimate_paise
    )


def test_allocation_zero_and_invalid_inputs():
    from app.fares.allocation import calculate_fare_allocation, paise_to_fare_amount
    from app.fares.models import EconomicStatus

    # Invariant 12: Negative fares are rejected
    with pytest.raises(ValueError, match="non-negative"):
        calculate_fare_allocation(
            paise_to_fare_amount(-100),
            paise_to_fare_amount(100),
            paise_to_fare_amount(100),
        )

    # Zero shared fare
    zero_shared = calculate_fare_allocation(
        paise_to_fare_amount(0), paise_to_fare_amount(1000), paise_to_fare_amount(2000)
    )
    assert zero_shared.passenger_a.allocated_fare.estimate_paise == 0
    assert zero_shared.passenger_b.allocated_fare.estimate_paise == 0
    assert zero_shared.economic_status == EconomicStatus.SAVINGS

    # Both solo fares zero
    zero_solos = calculate_fare_allocation(
        paise_to_fare_amount(1000), paise_to_fare_amount(0), paise_to_fare_amount(0)
    )
    assert zero_solos.economic_status == EconomicStatus.UNATTRACTIVE
    assert zero_solos.is_economically_beneficial is False
    assert (
        zero_solos.passenger_a.allocated_fare.estimate_paise
        + zero_solos.passenger_b.allocated_fare.estimate_paise
        == 1000
    )


def test_dec013_bilateral_consent_toggling():
    from app.api.v1.endpoints.matching import _proposal_to_schema
>>>>>>> 3dfc1f3 (5C)
>>>>>>> Stashed changes
    from app.fares.service import estimate_match_fare

    proposal = _proposal(
        datetime.fromisoformat("2026-11-08T10:00:00+05:30"),
        datetime.fromisoformat("2026-11-08T10:30:00+05:30"),
    )
<<<<<<< Updated upstream
=======
<<<<<<< HEAD
>>>>>>> Stashed changes
    fares = estimate_match_fare(proposal)
    no_consent = ProposalConsentState(
        {proposal.target_request_id: False, proposal.candidate_request_id: False}
    )
    schema = _proposal_to_schema(proposal, fare_domain=fares, consent_state=no_consent)
    assert schema.fare_allocation_disclosure is not None
    assert schema.fare_allocation_disclosure.allocation is None
    assert CONSENT_NOTICE in schema.fare_allocation_disclosure.consent_notice

    both = ProposalConsentState(
        {proposal.target_request_id: True, proposal.candidate_request_id: True}
    )
    approved = _proposal_to_schema(proposal, fare_domain=fares, consent_state=both)
    allocation = approved.fare_allocation_disclosure.allocation
    assert allocation is not None
    assert (
        allocation.your_contribution_paise + allocation.co_passenger_contribution_paise
        == allocation.shared_total_paise
    )
    wire = approved.model_dump(mode="json")
    assert "co_passenger_solo_baseline" not in str(wire)
    assert "candidate_solo" not in str(wire)
    assert "co_passenger_savings" not in str(wire)
<<<<<<< Updated upstream
=======
=======

    # Without bilateral consent (default)
    est_unconsented = estimate_match_fare(proposal, bilateral_consent=False)
    assert est_unconsented.allocation is not None
    assert est_unconsented.allocation.bilateral_consent is False

    schema_unconsented = _proposal_to_schema(proposal)
    assert schema_unconsented.fare_estimate is not None
    assert schema_unconsented.fare_estimate.co_passenger_contribution is None

    # With bilateral consent
    est_consented = estimate_match_fare(proposal, bilateral_consent=True)
    assert est_consented.allocation is not None
    assert est_consented.allocation.bilateral_consent is True

    from app.api.v1.endpoints.matching import _fare_to_schema

    schema_consented = _fare_to_schema(est_consented)
    assert schema_consented.co_passenger_contribution is not None
    # Solo baseline and private savings of co-passenger remain redacted under DEC-013
    serialized_consented = str(schema_consented.model_dump(mode="json")).lower()
    assert "co_passenger_solo" not in serialized_consented
    assert "candidate_solo" not in serialized_consented
    assert (
        schema_consented.your_allocated_fare.estimate_paise
        + schema_consented.co_passenger_contribution.estimate_paise
        == schema_consented.shared_journey.estimate_paise
    )
>>>>>>> 3dfc1f3 (5C)
>>>>>>> Stashed changes
