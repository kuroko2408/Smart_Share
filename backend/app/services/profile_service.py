"""Business service for profile management."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import Profile
from app.repositories.profile_repository import (
    ProfileRepository,
    profile_repository,
)
from app.schemas.auth import AuthUser
from app.schemas.profile import ProfileUpdateRequest


class ProfileService:
    """Business logic for user profiles."""

    def __init__(self, repo: ProfileRepository | None = None) -> None:
        self.repo = repo or profile_repository

    async def get_or_create_profile(
        self, session: AsyncSession, user: AuthUser
    ) -> Profile:
        """Retrieve the profile for the authenticated user, lazily creating it if needed."""
        return await self.repo.create_or_get(session, user)

    async def update_profile(
        self,
        session: AsyncSession,
        user: AuthUser,
        update_data: ProfileUpdateRequest,
    ) -> Profile:
        """Update mutable fields of the current user's profile."""
        profile = await self.repo.create_or_get(session, user)
        return await self.repo.update(
            session=session,
            profile=profile,
            display_name=update_data.display_name,
            avatar_url=update_data.avatar_url,
        )


profile_service = ProfileService()
