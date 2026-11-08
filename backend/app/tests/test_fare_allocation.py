from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.fares.consent import load_proposal_consent_states, record_consent_event
from app.fares.disclosure import CONSENT_TEXT_VERSION, DISCLOSURE_MODE
from app.models.match_disclosure_consent import MatchDisclosureConsentEvent


@pytest.mark.asyncio
async def test_consent_state_is_participant_scoped_and_snapshot_bound():
    proposal_id, request_a, request_b = uuid4(), uuid4(), uuid4()
    event = MatchDisclosureConsentEvent(
        proposal_id=proposal_id,
        participant_request_id=request_a,
        participant_user_id=uuid4(),
        action="GRANTED",
        disclosure_mode=DISCLOSURE_MODE,
        consent_text_version=CONSENT_TEXT_VERSION,
        subject_fingerprint="current",
    )
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value = [event]
    db.execute.return_value = result

    states = await load_proposal_consent_states(
        db, {proposal_id: (request_a, request_b, "current")}
    )
    assert states[proposal_id].by_request == {request_a: True, request_b: False}

    stale = await load_proposal_consent_states(
        db, {proposal_id: (request_a, request_b, "changed-fare-snapshot")}
    )
    assert stale[proposal_id].by_request == {request_a: False, request_b: False}


@pytest.mark.asyncio
async def test_consent_grant_and_revoke_are_audited_append_only_events():
    proposal_id, request_id, user_id = uuid4(), uuid4(), uuid4()
    db = AsyncMock()
    db.add = MagicMock()
    db.scalar.return_value = None

    created = await record_consent_event(
        db,
        proposal_id=proposal_id,
        participant_request_id=request_id,
        participant_user_id=user_id,
        subject_fingerprint="snapshot",
        action="GRANTED",
    )
    assert created is True
    granted = db.add.call_args.args[0]
    assert granted.action == "GRANTED"
    assert granted.participant_request_id == request_id
    assert granted.participant_user_id == user_id
    assert granted.consent_text_version == CONSENT_TEXT_VERSION
    db.flush.assert_awaited_once()

    db.scalar.return_value = granted
    db.add.reset_mock()
    revoked = await record_consent_event(
        db,
        proposal_id=proposal_id,
        participant_request_id=request_id,
        participant_user_id=user_id,
        subject_fingerprint="snapshot",
        action="REVOKED",
    )
    assert revoked is True
    assert db.add.call_args.args[0].action == "REVOKED"


def test_consent_event_model_is_additive_and_contains_no_fare_amount_columns():
    columns = set(MatchDisclosureConsentEvent.__table__.columns.keys())
    assert columns == {
        "event_id",
        "proposal_id",
        "participant_request_id",
        "participant_user_id",
        "action",
        "disclosure_mode",
        "consent_text_version",
        "subject_fingerprint",
        "occurred_at",
    }
    assert not any("fare" in column or "saving" in column for column in columns)
