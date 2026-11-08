"""DEC-013 consent text and fare-snapshot binding for exact disclosures."""

from __future__ import annotations

import hashlib
import json

from app.fares.models import FareComponentEstimate, MatchFareEstimate

CONSENT_TEXT_VERSION = "DEC-013-2026-11-08-v1"
DISCLOSURE_MODE = "EXACT"
CONSENT_NOTICE = (
    "If you consent, the other rider will see your exact contribution. They can "
    "combine that amount with their own solo estimate and the shared total to "
    "estimate your solo fare. Shared trip endpoints or outside information may "
    "also support distance inference. This notice explains a residual privacy "
    "risk; consent does not remove it. Your solo route and solo baseline fare "
    "remain private from the other rider. You may withdraw before any future "
    "group confirmation. Consenting does not accept the proposed ride."
)


def _component_amounts(component: FareComponentEstimate) -> list[int]:
    if component.fare_range is None:
        return [component.amount.estimate_paise]
    return [
        component.amount.estimate_paise,
        component.fare_range.minimum.estimate_paise,
        component.fare_range.maximum.estimate_paise,
    ]


def disclosure_subject_fingerprint(fares: MatchFareEstimate) -> str:
    """Bind consent to the exact fare snapshot without storing private fare values."""
    canonical_a, canonical_b = (
        (fares.your_solo_baseline, fares.co_passenger_solo_baseline)
        if fares.viewer_is_canonical_passenger_a
        else (fares.co_passenger_solo_baseline, fares.your_solo_baseline)
    )
    subject = {
        "model": fares.model_id,
        "version": fares.model_version,
        "mode": fares.pulse_quantization_mode.value,
        "shared": _component_amounts(fares.shared_journey),
        "canonical_solo_a": _component_amounts(canonical_a),
        "canonical_solo_b": _component_amounts(canonical_b),
    }
    encoded = json.dumps(subject, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()
