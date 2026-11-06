"""Business service for ride request management and lifecycle transitions."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.spatial import (
    are_coordinates_identical,
    parse_point_coordinates,
    to_geography_point,
    validate_coordinates,
)
from app.models.ride_request import RideRequest, RideRequestStatus
from app.repositories.profile_repository import (
    ProfileRepository,
    profile_repository,
)
from app.repositories.ride_request_repository import (
    RideRequestRepository,
    ride_request_repository,
)
from app.schemas.auth import AuthUser
from app.schemas.ride_request import (
    LocationPoint,
    RideRequestCreate,
    RideRequestResponse,
    RideRequestUpdate,
)


def _ensure_utc(dt: datetime) -> datetime:
    """Ensure datetime object is timezone-aware and converted to UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


class RideRequestService:
    """Coordinates ride request lifecycle and enforces domain rules."""

    def __init__(
        self,
        request_repo: RideRequestRepository | None = None,
        profile_repo: ProfileRepository | None = None,
    ) -> None:
        self.request_repo = request_repo or ride_request_repository
        self.profile_repo = profile_repo or profile_repository

    def to_response_dto(self, entity: RideRequest) -> RideRequestResponse:
        """Convert a database RideRequest entity into a structured response schema."""
        pickup_lat, pickup_lon = parse_point_coordinates(entity.pickup_location)
        dest_lat, dest_lon = parse_point_coordinates(entity.destination)

        return RideRequestResponse(
            id=entity.id,
            user_id=entity.user_id,
            pickup=LocationPoint(
                latitude=pickup_lat,
                longitude=pickup_lon,
                label=entity.pickup_label,
            ),
            destination=LocationPoint(
                latitude=dest_lat,
                longitude=dest_lon,
                label=entity.destination_label,
            ),
            departure_earliest=entity.departure_earliest,
            departure_latest=entity.departure_latest,
            seats_requested=entity.seats_requested,
            max_extra_minutes=entity.max_extra_minutes,
            status=RideRequestStatus(entity.status),
            expires_at=entity.expires_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    async def create_ride_request(
        self,
        session: AsyncSession,
        user: AuthUser,
        data: RideRequestCreate,
    ) -> RideRequest:
        """Create and persist a new ride request owned by the authenticated user."""
        # 1. Ensure owner profile exists
        await self.profile_repo.create_or_get(session, user)

        # 2. Convert coordinates into PostGIS geography points
        pickup_geom = to_geography_point(
            latitude=data.pickup.latitude,
            longitude=data.pickup.longitude,
        )
        dest_geom = to_geography_point(
            latitude=data.destination.latitude,
            longitude=data.destination.longitude,
        )

        # 3. Create entity with ACTIVE status
        ride_request = RideRequest(
            user_id=user.id,
            pickup_location=pickup_geom,
            destination=dest_geom,
            pickup_label=data.pickup.label,
            destination_label=data.destination.label,
            departure_earliest=data.departure_earliest,
            departure_latest=data.departure_latest,
            seats_requested=data.seats_requested,
            max_extra_minutes=data.max_extra_minutes,
            status=RideRequestStatus.ACTIVE.value,
            expires_at=data.departure_latest,
        )

        return await self.request_repo.create(session, ride_request)

    async def get_ride_request(
        self,
        session: AsyncSession,
        user: AuthUser,
        request_id: uuid.UUID,
    ) -> RideRequest:
        """Retrieve a specific ride request, strictly enforcing user ownership."""
        entity = await self.request_repo.get_by_id(session, request_id)
        if entity is None:
            raise AppException(
                detail="The requested ride request was not found",
                status_code=404,
                error_code="RESOURCE_NOT_FOUND",
            )

        if entity.user_id != user.id:
            raise AppException(
                detail="You are not authorized to view or modify this ride request",
                status_code=403,
                error_code="FORBIDDEN",
            )

        return entity

    async def list_user_ride_requests(
        self,
        session: AsyncSession,
        user: AuthUser,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[RideRequest], int]:
        """List paginated ride requests for the authenticated user."""
        bounded_limit = min(max(1, limit), 100)
        bounded_offset = max(0, offset)

        if status is not None:
            clean_status = status.upper().strip()
            if clean_status not in {s.value for s in RideRequestStatus}:
                raise AppException(
                    detail=f"Invalid status filter '{status}'",
                    status_code=400,
                    error_code="VALIDATION_ERROR",
                )
            status = clean_status

        records = await self.request_repo.list_by_user(
            session=session,
            user_id=user.id,
            status=status,
            limit=bounded_limit,
            offset=bounded_offset,
        )
        total_count = await self.request_repo.count_by_user(
            session=session,
            user_id=user.id,
            status=status,
        )
        return records, total_count

    async def update_ride_request(
        self,
        session: AsyncSession,
        user: AuthUser,
        request_id: uuid.UUID,
        update_data: RideRequestUpdate,
    ) -> RideRequest:
        """Update eligible fields of an active ride request."""
        entity = await self.get_ride_request(session, user, request_id)

        # Enforce lifecycle invariant: only ACTIVE requests may be updated
        if entity.status != RideRequestStatus.ACTIVE.value:
            raise AppException(
                detail=f"Cannot update ride request in status '{entity.status}'. Only ACTIVE requests are editable.",
                status_code=400,
                error_code="REQUEST_NOT_ACTIVE",
            )

        # Check endpoints if updated
        curr_pickup_lat, curr_pickup_lon = parse_point_coordinates(
            entity.pickup_location
        )
        curr_dest_lat, curr_dest_lon = parse_point_coordinates(entity.destination)

        new_pickup_lat = (
            update_data.pickup.latitude if update_data.pickup else curr_pickup_lat
        )
        new_pickup_lon = (
            update_data.pickup.longitude if update_data.pickup else curr_pickup_lon
        )
        new_dest_lat = (
            update_data.destination.latitude
            if update_data.destination
            else curr_dest_lat
        )
        new_dest_lon = (
            update_data.destination.longitude
            if update_data.destination
            else curr_dest_lon
        )

        validate_coordinates(new_pickup_lat, new_pickup_lon)
        validate_coordinates(new_dest_lat, new_dest_lon)

        if are_coordinates_identical(
            new_pickup_lat, new_pickup_lon, new_dest_lat, new_dest_lon
        ):
            raise AppException(
                detail="Pickup and destination coordinates cannot be identical",
                status_code=400,
                error_code="INVALID_COORDINATES",
            )

        if update_data.pickup is not None:
            entity.pickup_location = to_geography_point(
                latitude=update_data.pickup.latitude,
                longitude=update_data.pickup.longitude,
            )
            entity.pickup_label = update_data.pickup.label

        if update_data.destination is not None:
            entity.destination = to_geography_point(
                latitude=update_data.destination.latitude,
                longitude=update_data.destination.longitude,
            )
            entity.destination_label = update_data.destination.label

        # Departure window validation
        new_earliest = _ensure_utc(
            update_data.departure_earliest
            if update_data.departure_earliest is not None
            else entity.departure_earliest
        )
        new_latest = _ensure_utc(
            update_data.departure_latest
            if update_data.departure_latest is not None
            else entity.departure_latest
        )

        if new_latest < new_earliest:
            raise AppException(
                detail="Latest departure time must be greater than or equal to earliest departure time",
                status_code=400,
                error_code="INVALID_DEPARTURE_WINDOW",
            )

        if update_data.departure_earliest is not None:
            now = datetime.now(UTC)
            if new_earliest < (now - timedelta(seconds=60)):
                raise AppException(
                    detail="Earliest departure time cannot be in the past",
                    status_code=400,
                    error_code="INVALID_DEPARTURE_WINDOW",
                )
            entity.departure_earliest = new_earliest

        if update_data.departure_latest is not None:
            entity.departure_latest = new_latest
            entity.expires_at = new_latest

        if update_data.seats_requested is not None:
            entity.seats_requested = update_data.seats_requested

        if update_data.max_extra_minutes is not None:
            entity.max_extra_minutes = update_data.max_extra_minutes

        entity.updated_at = datetime.now(UTC)
        return await self.request_repo.update(session, entity)

    async def cancel_ride_request(
        self,
        session: AsyncSession,
        user: AuthUser,
        request_id: uuid.UUID,
    ) -> RideRequest:
        """Cancel an eligible ride request."""
        entity = await self.get_ride_request(session, user, request_id)

        # Enforce valid cancellation transitions
        cancellable_states = {
            RideRequestStatus.ACTIVE.value,
            RideRequestStatus.MATCHED.value,
        }
        if entity.status not in cancellable_states:
            raise AppException(
                detail=f"Ride request in state '{entity.status}' cannot be cancelled.",
                status_code=400,
                error_code="INVALID_STATE_TRANSITION",
            )

        entity.status = RideRequestStatus.CANCELLED.value
        entity.updated_at = datetime.now(UTC)
        return await self.request_repo.update(session, entity)


ride_request_service = RideRequestService()
