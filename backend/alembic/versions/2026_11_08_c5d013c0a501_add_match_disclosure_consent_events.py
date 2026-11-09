"""add append-only match disclosure consent events

Revision ID: c5d013c0a501
Revises: 5b69062ab3ef
Create Date: 2026-11-08

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "c5d013c0a501"
down_revision: str | None = "5b69062ab3ef"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "match_disclosure_consent_events",
        sa.Column("event_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("proposal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "participant_request_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("participant_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("disclosure_mode", sa.String(length=16), nullable=False),
        sa.Column("consent_text_version", sa.String(length=64), nullable=False),
        sa.Column("subject_fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "action IN ('GRANTED', 'REVOKED')", name="chk_match_consent_action"
        ),
        sa.CheckConstraint("disclosure_mode = 'EXACT'", name="chk_match_consent_mode"),
        sa.ForeignKeyConstraint(
            ["participant_request_id"], ["ride_requests.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["participant_user_id"], ["profiles.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("event_id", name="pk_match_disclosure_consent_events"),
    )
    op.create_index(
        "idx_match_consent_proposal_participant_event",
        "match_disclosure_consent_events",
        ["proposal_id", "participant_request_id", sa.text("event_id DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "idx_match_consent_proposal_participant_event",
        table_name="match_disclosure_consent_events",
    )
    op.drop_table("match_disclosure_consent_events")
