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
    serialized = str(fare).lower()
    assert "contribution" not in serialized and "savings" not in serialized
    assert "co_passenger" not in serialized and "candidate_solo" not in serialized
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
