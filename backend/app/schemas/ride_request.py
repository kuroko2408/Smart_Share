"""Pydantic schemas for ride request operations."""

import uuid
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.spatial import are_coordinates_identical, validate_coordinates
from app.models.ride_request import RideRequestStatus


def _ensure_utc(dt: datetime) -> datetime:
    """Ensure datetime object is timezone-aware and converted to UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


class LocationPoint(BaseModel):
    """Geographic point coordinates with optional display label."""

    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="WGS 84 latitude in degrees (-90.0 to 90.0)",
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="WGS 84 longitude in degrees (-180.0 to 180.0)",
    )
    label: str | None = Field(
        default=None,
        max_length=255,
        description="Optional human-readable label or landmark name",
    )


class RideRequestCreate(BaseModel):
    """Request payload for creating a new passenger ride request."""

    pickup: LocationPoint = Field(..., description="Pickup location coordinates")
    destination: LocationPoint = Field(
        ..., description="Destination location coordinates"
    )
    departure_earliest: datetime = Field(
        ...,
        description="Start of acceptable departure window (UTC ISO 8601)",
    )
    departure_latest: datetime = Field(
        ...,
        description="End of acceptable departure window (UTC ISO 8601)",
    )
    seats_requested: int = Field(
        default=1,
        ge=1,
        le=6,
        description="Number of passenger seats required (1 to 6)",
    )
    max_extra_minutes: int = Field(
        default=15,
        ge=0,
        le=180,
        description="Maximum acceptable detour/extra travel time in minutes (0 to 180)",
    )

    @model_validator(mode="after")
    def validate_request_bounds(self) -> "RideRequestCreate":
        """Validate spatial and temporal invariants."""
        # 1. Coordinate boundaries
        validate_coordinates(self.pickup.latitude, self.pickup.longitude)
        validate_coordinates(self.destination.latitude, self.destination.longitude)

        # 2. Distinct endpoints: pickup and destination cannot be identical
        if are_coordinates_identical(
            self.pickup.latitude,
            self.pickup.longitude,
            self.destination.latitude,
            self.destination.longitude,
        ):
            raise ValueError("Pickup and destination coordinates cannot be identical.")

        # 3. Departure window ordering: latest cannot precede earliest
        self.departure_earliest = _ensure_utc(self.departure_earliest)
        self.departure_latest = _ensure_utc(self.departure_latest)

        if self.departure_latest < self.departure_earliest:
            raise ValueError(
                "Latest departure time must be greater than or equal to earliest departure time."
            )

        # 4. Temporal freshness: departure window cannot be in the past (60s grace period for clock skew)
        now = datetime.now(UTC)
        skew_allowance = timedelta(seconds=60)
        if self.departure_earliest < (now - skew_allowance):
            raise ValueError("Earliest departure time cannot be in the past.")

        return self


class RideRequestUpdate(BaseModel):
    """Request payload for modifying an active ride request."""

    pickup: LocationPoint | None = Field(default=None, description="Updated pickup")
    destination: LocationPoint | None = Field(
        default=None, description="Updated destination"
    )
    departure_earliest: datetime | None = Field(
        default=None, description="Updated earliest departure"
    )
    departure_latest: datetime | None = Field(
        default=None, description="Updated latest departure"
    )
    seats_requested: int | None = Field(
        default=None, ge=1, le=6, description="Updated seats required (1..6)"
    )
    max_extra_minutes: int | None = Field(
        default=None,
        ge=0,
        le=180,
        description="Updated detour preference (0..180)",
    )

    @model_validator(mode="after")
    def validate_update_bounds(self) -> "RideRequestUpdate":
        """Validate updated coordinates or departure interval if provided."""
        if self.pickup is not None:
            validate_coordinates(self.pickup.latitude, self.pickup.longitude)
        if self.destination is not None:
            validate_coordinates(self.destination.latitude, self.destination.longitude)

        if self.pickup is not None and self.destination is not None:
            if are_coordinates_identical(
                self.pickup.latitude,
                self.pickup.longitude,
                self.destination.latitude,
                self.destination.longitude,
            ):
                raise ValueError(
                    "Pickup and destination coordinates cannot be identical."
                )

        if self.departure_earliest is not None:
            self.departure_earliest = _ensure_utc(self.departure_earliest)
        if self.departure_latest is not None:
            self.departure_latest = _ensure_utc(self.departure_latest)

        if self.departure_earliest is not None and self.departure_latest is not None:
            if self.departure_latest < self.departure_earliest:
                raise ValueError(
                    "Latest departure time must be greater than or equal to earliest departure time."
                )

        return self


class RideRequestResponse(BaseModel):
    """Public ride request representation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Unique ride request identifier")
    user_id: uuid.UUID = Field(..., description="Request owner profile ID")
    pickup: LocationPoint = Field(..., description="Pickup location coordinates")
    destination: LocationPoint = Field(
        ..., description="Destination location coordinates"
    )
    departure_earliest: datetime = Field(
        ..., description="Earliest acceptable departure time"
    )
    departure_latest: datetime = Field(
        ..., description="Latest acceptable departure time"
    )
    seats_requested: int = Field(..., description="Seats requested (1..6)")
    max_extra_minutes: int = Field(
        ..., description="Maximum acceptable detour in minutes"
    )
    status: RideRequestStatus = Field(..., description="Lifecycle status")
    expires_at: datetime | None = Field(
        default=None, description="Request timeout timestamp"
    )
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record update timestamp")
