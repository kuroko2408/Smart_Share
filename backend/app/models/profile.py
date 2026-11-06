"""SQLAlchemy model for user profiles."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.ride_request import RideRequest

# External Supabase Auth users table stub.
# Registers auth.users in Base.metadata so ForeignKey("auth.users.id") resolves
# correctly in SQLAlchemy. Alembic excludes schema="auth" from autogeneration.
auth_users = Table(
    "users",
    Base.metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    schema="auth",
)


class Profile(Base):
    """User profile entity mapped 1:1 to Supabase Auth users."""

    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        primary_key=True,
        doc="Primary key corresponding to Supabase Auth user UUID",
    )
    display_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="",
        server_default="",
        doc="Public display name (defaults to empty string for pending onboarding)",
    )
    avatar_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        doc="Optional public profile image URL",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="UTC record creation timestamp",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        doc="UTC record last updated timestamp",
    )

    # Relationships
    ride_requests: Mapped[list["RideRequest"]] = relationship(
        "RideRequest",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint(
            "char_length(display_name) <= 100",
            name="chk_profiles_display_name_length",
        ),
    )

    def __init__(self, **kwargs: Any) -> None:
        """Initialize profile with default display_name."""
        kwargs.setdefault("display_name", "")
        super().__init__(**kwargs)

    @property
    def is_onboarding_completed(self) -> bool:
        """Indicate whether the user has finalized their public profile display name."""
        return bool(self.display_name and self.display_name.strip())

    def __repr__(self) -> str:
        return f"<Profile id={self.id} display_name={self.display_name!r}>"
