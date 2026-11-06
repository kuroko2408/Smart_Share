"""User profile API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.schemas.auth import AuthUser
from app.schemas.common import DataResponse
from app.schemas.profile import ProfileResponse, ProfileUpdateRequest
from app.services.profile_service import profile_service

router = APIRouter(prefix="/users", tags=["Profiles"])


@router.get("/me", response_model=DataResponse[ProfileResponse])
async def get_my_profile(
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ProfileResponse]:
    """Retrieve the profile corresponding to the authenticated Supabase user."""
    profile = await profile_service.get_or_create_profile(session=db, user=current_user)
    return DataResponse(
        data=ProfileResponse.model_validate(profile),
        message="Profile retrieved successfully",
    )


@router.patch("/me", response_model=DataResponse[ProfileResponse])
async def update_my_profile(
    update_data: ProfileUpdateRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ProfileResponse]:
    """Update profile fields for the authenticated user."""
    profile = await profile_service.update_profile(
        session=db, user=current_user, update_data=update_data
    )
    return DataResponse(
        data=ProfileResponse.model_validate(profile),
        message="Profile updated successfully",
    )
