"""Ride request management API endpoints."""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.schemas.auth import AuthUser
from app.schemas.common import (
    DataResponse,
    PaginatedDataResponse,
    PaginationMeta,
)
from app.schemas.ride_request import (
    RideRequestCreate,
    RideRequestResponse,
    RideRequestUpdate,
)
from app.services.ride_request_service import ride_request_service

router = APIRouter(prefix="/ride-requests", tags=["Ride Requests"])


@router.post(
    "",
    response_model=DataResponse[RideRequestResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_ride_request(
    payload: RideRequestCreate,
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[RideRequestResponse]:
    """Create a new travel ride request for the authenticated passenger."""
    created = await ride_request_service.create_ride_request(
        session=db,
        user=current_user,
        data=payload,
    )
    dto = ride_request_service.to_response_dto(created)
    return DataResponse(
        data=dto,
        message="Ride request created successfully",
    )


@router.get("", response_model=PaginatedDataResponse[RideRequestResponse])
async def list_my_ride_requests(
    status_filter: str | None = Query(
        default=None,
        alias="status",
        description="Filter by request status (e.g. ACTIVE, MATCHED)",
    ),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    offset: int = Query(default=0, ge=0, description="Page starting offset"),
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedDataResponse[RideRequestResponse]:
    """List ride requests belonging to the authenticated user."""
    records, total = await ride_request_service.list_user_ride_requests(
        session=db,
        user=current_user,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    dtos = [ride_request_service.to_response_dto(r) for r in records]
    has_more = (offset + len(records)) < total

    return PaginatedDataResponse(
        data=dtos,
        pagination=PaginationMeta(
            total=total,
            limit=limit,
            offset=offset,
            has_more=has_more,
        ),
        message="Ride requests retrieved successfully",
    )


@router.get("/{request_id}", response_model=DataResponse[RideRequestResponse])
async def get_ride_request(
    request_id: uuid.UUID,
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[RideRequestResponse]:
    """Retrieve details of a single ride request. Enforces strict ownership."""
    entity = await ride_request_service.get_ride_request(
        session=db,
        user=current_user,
        request_id=request_id,
    )
    dto = ride_request_service.to_response_dto(entity)
    return DataResponse(
        data=dto,
        message="Ride request retrieved successfully",
    )


@router.patch("/{request_id}", response_model=DataResponse[RideRequestResponse])
async def update_ride_request(
    request_id: uuid.UUID,
    payload: RideRequestUpdate,
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[RideRequestResponse]:
    """Update coordinates, departure window, or seat requirements of an active request."""
    updated = await ride_request_service.update_ride_request(
        session=db,
        user=current_user,
        request_id=request_id,
        update_data=payload,
    )
    dto = ride_request_service.to_response_dto(updated)
    return DataResponse(
        data=dto,
        message="Ride request updated successfully",
    )


@router.post(
    "/{request_id}/cancel",
    response_model=DataResponse[RideRequestResponse],
)
async def cancel_ride_request(
    request_id: uuid.UUID,
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[RideRequestResponse]:
    """Cancel an active or matched ride request."""
    cancelled = await ride_request_service.cancel_ride_request(
        session=db,
        user=current_user,
        request_id=request_id,
    )
    dto = ride_request_service.to_response_dto(cancelled)
    return DataResponse(
        data=dto,
        message="Ride request cancelled successfully",
    )
