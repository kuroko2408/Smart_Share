"""SQLAlchemy model for passenger ride requests."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from geoalchemy2 import Geography
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.profile import Profile


class RideRequestStatus(enum.StrEnum):
    """Lifecycle statuses for a ride request."""

    ACTIVE = "ACTIVE"
    MATCHED = "MATCHED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    COMPLETED = "COMPLETED"


class RideRequest(Base):
    """Passenger travel request with geographic and departure windows."""

    __tablename__ = "ride_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        doc="Unique identifier for the ride request",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        doc="Foreign key reference to requesting user profile",
    )

    # PostGIS Geography(Point, 4326) — Spheroid WGS 84. Coordinate convention: (Longitude, Latitude)
    pickup_location: Mapped[Any] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False),
        nullable=False,
        doc="Pickup location geography point (SRID 4326, WGS 84: Longitude X, Latitude Y)",
    )
    destination: Mapped[Any] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False),
        nullable=False,
        doc="Destination location geography point (SRID 4326, WGS 84: Longitude X, Latitude Y)",
    )

    pickup_label: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        default=None,
        doc="Optional human-readable label for pickup location",
    )
    destination_label: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        default=None,
        doc="Optional human-readable label for destination",
    )

    departure_earliest: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="Earliest acceptable departure time (UTC)",
    )
    departure_latest: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="Latest acceptable departure time (UTC)",
    )

    seats_requested: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=1,
        server_default="1",
        doc="Requested seat capacity (1..6)",
    )
    max_extra_minutes: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=15,
        server_default="15",
        doc="Maximum acceptable additional journey/detour time in minutes (0..180)",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=RideRequestStatus.ACTIVE.value,
        server_default=RideRequestStatus.ACTIVE.value,
        doc="Lifecycle state of the ride request",
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        doc="Explicit request timeout (UTC). If null, request expires at departure_latest",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Record creation timestamp (UTC)",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        doc="Record last update timestamp (UTC)",
    )

    # Relationship to requesting user
    user: Mapped["Profile"] = relationship("Profile", back_populates="ride_requests")

    __table_args__ = (
        # 1. Departure window consistency: latest departure must not precede earliest departure
        CheckConstraint(
            "departure_latest >= departure_earliest",
            name="chk_ride_requests_departure_window",
        ),
        # 2. Seat requirements: standard vehicle capacity 1 to 6
        CheckConstraint(
            "seats_requested >= 1 AND seats_requested <= 6",
            name="chk_ride_requests_seats",
        ),
        # 3. Extra journey time tolerance: non-negative and bounded (up to 3 hours)
        CheckConstraint(
            "max_extra_minutes >= 0 AND max_extra_minutes <= 180",
            name="chk_ride_requests_max_extra_minutes",
        ),
        # 4. Valid lifecycle states
        CheckConstraint(
            "status IN ('ACTIVE', 'MATCHED', 'CANCELLED', 'EXPIRED', 'COMPLETED')",
            name="chk_ride_requests_status",
        ),
        # 5. Distinct endpoints: pickup and destination must not be identical
        CheckConstraint(
            "NOT ST_Equals(pickup_location::geometry, destination::geometry)",
            name="chk_ride_requests_distinct_endpoints",
        ),
        # 6. Expiry boundary: if specified, cannot be after the latest departure window
        CheckConstraint(
            "expires_at IS NULL OR expires_at <= departure_latest",
            name="chk_ride_requests_expiry_window",
        ),
        # Spatial Indexes (PostGIS GiST)
        Index(
            "idx_ride_requests_pickup_gist",
            pickup_location,
            postgresql_using="gist",
        ),
        Index(
            "idx_ride_requests_destination_gist",
            destination,
            postgresql_using="gist",
        ),
        # Foreign Key B-Tree Index
        Index("idx_ride_requests_user_id", user_id),
        # Composite Partial Index for Stage 1 Candidate Filtering
        Index(
            "idx_ride_requests_active_departure",
            status,
            departure_earliest,
            departure_latest,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        # Partial Index for Background Expiry Sweeps
        Index(
            "idx_ride_requests_active_expiry",
            expires_at,
            postgresql_where=text("status = 'ACTIVE' AND expires_at IS NOT NULL"),
        ),
    )

    def __init__(self, **kwargs: Any) -> None:
        """Initialize ride request with defaults."""
        kwargs.setdefault("seats_requested", 1)
        kwargs.setdefault("max_extra_minutes", 15)
        kwargs.setdefault("status", RideRequestStatus.ACTIVE.value)
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return (
            f"<RideRequest id={self.id} user_id={self.user_id} "
            f"status={self.status!r} seats={self.seats_requested}>"
        )
