"""Repository for RideRequest database access operations."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ride_request import RideRequest


class RideRequestRepository:
    """Encapsulates database operations for passenger ride requests."""

    async def create(
        self, session: AsyncSession, ride_request: RideRequest
    ) -> RideRequest:
        """Persist a new ride request and return refreshed entity."""
        session.add(ride_request)
        await session.flush()
        await session.refresh(ride_request)
        return ride_request

    async def get_by_id(
        self, session: AsyncSession, request_id: uuid.UUID
    ) -> RideRequest | None:
        """Retrieve a ride request by primary key UUID."""
        stmt = select(RideRequest).where(RideRequest.id == request_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[RideRequest]:
        """List paginated ride requests owned by a specific user."""
        stmt = (
            select(RideRequest)
            .where(RideRequest.user_id == user_id)
            .order_by(RideRequest.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        if status is not None:
            stmt = stmt.where(RideRequest.status == status)

        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_user(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        status: str | None = None,
    ) -> int:
        """Count total matching ride requests owned by a specific user for pagination."""
        stmt = (
            select(func.count())
            .select_from(RideRequest)
            .where(RideRequest.user_id == user_id)
        )
        if status is not None:
            stmt = stmt.where(RideRequest.status == status)

        result = await session.execute(stmt)
        return int(result.scalar_one())

    async def update(
        self, session: AsyncSession, ride_request: RideRequest
    ) -> RideRequest:
        """Flush changes and refresh the ride request entity."""
        await session.flush()
        await session.refresh(ride_request)
        return ride_request


ride_request_repository = RideRequestRepository()
