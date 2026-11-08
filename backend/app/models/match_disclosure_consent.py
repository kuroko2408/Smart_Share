"""Append-only audit events for DEC-013 bilateral exact fare disclosure consent."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MatchDisclosureConsentEvent(Base):
    __tablename__ = "match_disclosure_consent_events"

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    proposal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    participant_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ride_requests.id", ondelete="RESTRICT"),
        nullable=False,
    )
    participant_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    disclosure_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    consent_text_version: Mapped[str] = mapped_column(String(64), nullable=False)
    subject_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "action IN ('GRANTED', 'REVOKED')", name="chk_match_consent_action"
        ),
        CheckConstraint("disclosure_mode = 'EXACT'", name="chk_match_consent_mode"),
        Index(
            "idx_match_consent_proposal_participant_event",
            proposal_id,
            participant_request_id,
            event_id.desc(),
        ),
    )
