"""Build viewer-scoped fare estimates for existing match proposals."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.core.config import get_settings
from app.fares.allocation import calculate_fare_allocation
from app.fares.models import (
    FareAccuracy,
    FareComponentEstimate,
    FareModelConfig,
    FareRange,
    MatchFareEstimate,
    PulseQuantizationMode,
    SurchargeStatus,
)
from app.fares.registry import fare_model_registry
from app.fares.tariff import fare_for_distance
from app.matching.service import MatchProposal
from app.routing.models import DistanceSource

IST = ZoneInfo("Asia/Kolkata")
_SOURCE_ACCURACY = {
    DistanceSource.PROVIDER_ROAD_NETWORK_ROUTE.value: FareAccuracy.ROAD_ROUTE,
    DistanceSource.PROVIDER_MATRIX_TABLE.value: FareAccuracy.MATRIX_SCREENING,
    DistanceSource.CALIBRATED_TORTUOSITY_FALLBACK.value: FareAccuracy.CALIBRATED_FALLBACK,
    DistanceSource.GEODESIC_SPHEROID.value: FareAccuracy.GEODESIC_ONLY,
}
_ACCURACY_ORDER = tuple(FareAccuracy)


def _distance(value: float) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite() or result < 0:
        raise ValueError("Route distance must be finite and non-negative")
    return result


def _night_at(value: datetime) -> bool:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Fare timestamps must be timezone-aware")
    local = value.astimezone(IST).timetz().replace(tzinfo=None)
    return time(0) <= local < time(5)


def _window_has(window_start: datetime, window_end: datetime, *, night: bool) -> bool:
    if any(
        t.tzinfo is None or t.utcoffset() is None for t in (window_start, window_end)
    ):
        raise ValueError("Fare timestamps must be timezone-aware")
    start = window_start.astimezone(IST)
    end = window_end.astimezone(IST)
    if end < start:
        raise ValueError("Fare time window end precedes start")
    if start == end:
        return _night_at(start) is night

    date = start.date() - timedelta(days=1)
    while date <= end.date():
        night_start = datetime.combine(date, time.min, IST)
        night_end = datetime.combine(date, time(5), IST)
        if night:
            if start < night_end and end >= night_start:
                return True
        else:
            day_start = night_end
            day_end = datetime.combine(date + timedelta(days=1), time.min, IST)
            if start < day_end and end >= day_start:
                return True
        date += timedelta(days=1)
    return False


def _component(
    distance: Decimal,
    source: str,
    start: datetime,
    end: datetime,
    config: FareModelConfig,
    mode: PulseQuantizationMode,
) -> FareComponentEstimate:
    accuracy = _SOURCE_ACCURACY.get(source)
    if accuracy is None:
        raise LookupError(f"Unsupported pre-trip distance source: {source}")
    midpoint = start + (end - start) / 2
    night = _night_at(midpoint)
    has_night = _window_has(start, end, night=True)
    has_day = _window_has(start, end, night=False)
    status = (
        SurchargeStatus.CONDITIONAL
        if has_night and has_day
        else SurchargeStatus.APPLIED
        if night
        else SurchargeStatus.NONE
    )
    fare_range = None
    if status is SurchargeStatus.CONDITIONAL:
        day = fare_for_distance(distance, config, mode, night=False)
        night_fare = fare_for_distance(distance, config, mode, night=True)
        fare_range = FareRange(minimum=day, maximum=night_fare)
    return FareComponentEstimate(
        amount=fare_for_distance(distance, config, mode, night=night),
        surcharge_status=status,
        fare_range=fare_range,
        distance_meters=distance,
        source=source,
        accuracy=accuracy,
    )


def estimate_match_fare(
    proposal: MatchProposal,
    *,
    mode: PulseQuantizationMode | None = None,
    config: FareModelConfig | None = None,
    bilateral_consent: bool = False,
) -> MatchFareEstimate:
    """Estimate shared fare, both solo baselines, and fair cost allocation."""
    if proposal.shared_departure_end < proposal.shared_departure_start:
        raise ValueError("Shared departure window end precedes start")
    mode = mode or PulseQuantizationMode(get_settings().FARE_PULSE_QUANTIZATION_MODE)
    config = config or fare_model_registry.resolve()
    shared_source = proposal.distance_source
    direct_source = proposal.direct_distance_source
    shared = _component(
        _distance(proposal.total_shared_distance_m),
        shared_source,
        proposal.shared_departure_start,
        proposal.shared_departure_end,
        config,
        mode,
    )
    your_distance = _distance(proposal.direct_a_dist_m)
    own = _component(
        your_distance,
        direct_source,
        proposal.shared_departure_start,
        proposal.shared_departure_end,
        config,
        mode,
    )
    # Candidate baseline is evaluated for composite accuracy determination and proportional
    # cost allocation. Under DEC-013, it is never exposed directly to this viewer without bilateral consent.
    other = _component(
        _distance(proposal.direct_b_dist_m),
        direct_source,
        proposal.shared_departure_start,
        proposal.shared_departure_end,
        config,
        mode,
    )
    weakest = max(
        (shared.accuracy, own.accuracy, other.accuracy),
        key=_ACCURACY_ORDER.index,
    )
    allocation = calculate_fare_allocation(
        shared_fare=shared.amount,
        solo_fare_a=own.amount,
        solo_fare_b=other.amount,
        bilateral_consent=bilateral_consent,
    )
    return MatchFareEstimate(
        shared_journey=shared,
        your_solo_baseline=own,
        co_passenger_solo_baseline=other,
        composite_accuracy=weakest,
        model_id=config.model_id,
        model_version=config.version,
        pulse_quantization_mode=mode,
        minimum_fare_paise=int(config.base_fare * 100),
        viewer_is_canonical_passenger_a=str(proposal.target_request_id)
        < str(proposal.candidate_request_id),
        allocation=allocation,
    )
