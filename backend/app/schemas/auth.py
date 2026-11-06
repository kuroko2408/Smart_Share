"""Authentication schemas and context models."""

import uuid
from typing import Any

from pydantic import BaseModel, Field


class AuthUser(BaseModel):
    """Authenticated user context derived exclusively from validated JWT claims."""

    id: uuid.UUID = Field(
        ...,
        description="Supabase Auth user UUID extracted from verified 'sub' claim",
    )
    email: str | None = Field(
        default=None,
        description="User email address if present in token claims",
    )
    role: str | None = Field(
        default=None,
        description="Auth role claim (e.g. 'authenticated')",
    )
    app_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Application metadata from token claims",
    )
    user_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="User metadata from token claims",
    )
    claims: dict[str, Any] = Field(
        default_factory=dict,
        description="Full verified JWT claims dictionary",
    )
