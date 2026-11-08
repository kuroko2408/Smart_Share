"""Deterministic tariff math using Decimal throughout the money calculation."""

from __future__ import annotations

from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, Decimal

from app.fares.models import FareAmount, FareModelConfig, PulseQuantizationMode


def fare_for_distance(
    distance_meters: Decimal,
    config: FareModelConfig,
    mode: PulseQuantizationMode,
    *,
    night: bool,
) -> FareAmount:
    if not distance_meters.is_finite() or distance_meters < 0:
        raise ValueError("Distance must be a finite, non-negative number of metres")

    excess = max(Decimal(0), distance_meters - config.base_distance_meters)
    if mode is PulseQuantizationMode.CONTINUOUS:
        distance_fare = excess * config.rate_per_km / Decimal(1000)
    else:
        pulses = (excess / config.pulse_distance_meters).to_integral_value(
            rounding=(
                ROUND_CEILING if mode is PulseQuantizationMode.CEILING else ROUND_FLOOR
            )
        )
        distance_fare = pulses * config.pulse_fare

    total = config.base_fare + distance_fare
    if night:
        total *= config.night_multiplier
    paise = int((total * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    rounded_rupees = int(total.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return FareAmount(
        estimate=(Decimal(paise) / 100).quantize(Decimal("0.01")),
        estimate_paise=paise,
        rounded_estimate_rupees=rounded_rupees,
    )
