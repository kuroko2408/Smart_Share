"""Pydantic schemas for user profiles."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProfileResponse(BaseModel):
    """Public profile response model."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        ..., description="User unique identifier (Supabase Auth UUID)"
    )
    display_name: str = Field(..., description="User public display name")
    avatar_url: str | None = Field(default=None, description="Public profile image URL")
    is_onboarding_completed: bool = Field(
        ...,
        description="Whether the user has finalized their public display name",
    )
    created_at: datetime = Field(..., description="Profile creation timestamp (UTC)")
    updated_at: datetime = Field(..., description="Profile last update timestamp (UTC)")


class ProfileUpdateRequest(BaseModel):
    """Payload for updating user profile fields."""

    display_name: str | None = Field(
        default=None,
        max_length=100,
        description="Updated display name (max 100 characters)",
    )
    avatar_url: str | None = Field(
        default=None,
        max_length=2048,
        description="Updated avatar URL",
    )

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, v: str | None) -> str | None:
        """Strip display name if provided."""
        if v is not None:
            return v.strip()
        return v
