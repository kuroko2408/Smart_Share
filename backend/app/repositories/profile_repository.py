"""Repository for Profile database access operations."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import Profile
from app.schemas.auth import AuthUser


class ProfileRepository:
    """Encapsulates database operations for user profiles."""

    async def get_by_id(
        self, session: AsyncSession, user_id: uuid.UUID
    ) -> Profile | None:
        """Retrieve a profile by primary key UUID."""
        stmt = select(Profile).where(Profile.id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_or_get(self, session: AsyncSession, user: AuthUser) -> Profile:
        """Retrieve existing profile or lazily provision a new profile for authenticated user."""
        profile = await self.get_by_id(session, user.id)
        if profile is not None:
            return profile

        # Extract initial name/avatar metadata if provided during Supabase registration
        display_name = (
            user.user_metadata.get("full_name") or user.user_metadata.get("name") or ""
        )
        avatar_url = user.user_metadata.get("avatar_url")

        new_profile = Profile(
            id=user.id,
            display_name=display_name,
            avatar_url=avatar_url,
        )
        session.add(new_profile)
        await session.flush()
        return new_profile

    async def update(
        self,
        session: AsyncSession,
        profile: Profile,
        display_name: str | None = None,
        avatar_url: str | None = None,
    ) -> Profile:
        """Update mutable profile fields."""
        if display_name is not None:
            profile.display_name = display_name
        if avatar_url is not None:
            profile.avatar_url = avatar_url

        profile.updated_at = datetime.now(UTC)
        await session.flush()
        await session.refresh(profile)
        return profile


profile_repository = ProfileRepository()
