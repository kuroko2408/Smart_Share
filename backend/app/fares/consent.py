"""Append-only DEC-013 consent event operations for transient pair proposals."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.fares.disclosure import CONSENT_TEXT_VERSION, DISCLOSURE_MODE
from app.models.match_disclosure_consent import MatchDisclosureConsentEvent


@dataclass(frozen=True)
class ProposalConsentState:
    by_request: dict[UUID, bool]


async def load_proposal_consent_states(
    db: AsyncSession,
    subject_fingerprints: dict[UUID, tuple[UUID, UUID, str]],
) -> dict[UUID, ProposalConsentState]:
    """Load latest events for a bounded proposal batch, keyed by proposal and user request."""
    if not subject_fingerprints:
        return {}
    proposal_ids = list(subject_fingerprints)
    latest_ids = (
        select(func.max(MatchDisclosureConsentEvent.event_id).label("event_id"))
        .where(MatchDisclosureConsentEvent.proposal_id.in_(proposal_ids))
        .group_by(
            MatchDisclosureConsentEvent.proposal_id,
            MatchDisclosureConsentEvent.participant_request_id,
        )
        .subquery()
    )
    result = await db.execute(
        select(MatchDisclosureConsentEvent).join(
            latest_ids, MatchDisclosureConsentEvent.event_id == latest_ids.c.event_id
        )
    )
    latest: dict[tuple[UUID, UUID], MatchDisclosureConsentEvent] = {}
    for event in result.scalars():
        latest[(event.proposal_id, event.participant_request_id)] = event

    states: dict[UUID, ProposalConsentState] = {}
    for proposal_id, (
        request_a,
        request_b,
        fingerprint,
    ) in subject_fingerprints.items():
        flags: dict[UUID, bool] = {}
        for request_id in (request_a, request_b):
            event = latest.get((proposal_id, request_id))
            flags[request_id] = bool(
                event
                and event.action == "GRANTED"
                and event.disclosure_mode == DISCLOSURE_MODE
                and event.consent_text_version == CONSENT_TEXT_VERSION
                and event.subject_fingerprint == fingerprint
            )
        states[proposal_id] = ProposalConsentState(by_request=flags)
    return states


async def record_consent_event(
    db: AsyncSession,
    *,
    proposal_id: UUID,
    participant_request_id: UUID,
    participant_user_id: UUID,
    subject_fingerprint: str,
    action: str,
) -> bool:
    """Append a grant/revoke event only when it changes the latest consent state."""
    if action not in {"GRANTED", "REVOKED"}:
        raise ValueError("Consent action must be GRANTED or REVOKED")
    latest = await db.scalar(
        select(MatchDisclosureConsentEvent)
        .where(
            MatchDisclosureConsentEvent.proposal_id == proposal_id,
            MatchDisclosureConsentEvent.participant_request_id
            == participant_request_id,
        )
        .order_by(MatchDisclosureConsentEvent.event_id.desc())
        .limit(1)
    )
    latest_is_grant = bool(
        latest
        and latest.action == "GRANTED"
        and latest.disclosure_mode == DISCLOSURE_MODE
        and latest.consent_text_version == CONSENT_TEXT_VERSION
    )
    grant_matches_subject = bool(
        latest_is_grant and latest and latest.subject_fingerprint == subject_fingerprint
    )
    if (action == "GRANTED" and grant_matches_subject) or (
        action == "REVOKED" and not latest_is_grant
    ):
        return False

    event_fingerprint = (
        latest.subject_fingerprint
        if action == "REVOKED" and latest is not None and latest_is_grant
        else subject_fingerprint
    )

    db.add(
        MatchDisclosureConsentEvent(
            proposal_id=proposal_id,
            participant_request_id=participant_request_id,
            participant_user_id=participant_user_id,
            action=action,
            disclosure_mode=DISCLOSURE_MODE,
            consent_text_version=CONSENT_TEXT_VERSION,
            subject_fingerprint=event_fingerprint,
        )
    )
    await db.flush()
    return True
