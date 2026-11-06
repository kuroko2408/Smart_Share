"""FastAPI dependencies for authentication and authorization."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import AuthenticationError
from app.core.security import SupabaseJWTVerifier, create_supabase_jwt_verifier
from app.schemas.auth import AuthUser

# Bearer token security scheme; auto_error=False allows structured AppException responses
bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache
def get_jwt_verifier() -> SupabaseJWTVerifier:
    """Return cached SupabaseJWTVerifier configured from environment settings."""
    return create_supabase_jwt_verifier()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    verifier: Annotated[SupabaseJWTVerifier, Depends(get_jwt_verifier)],
) -> AuthUser:
    """FastAPI dependency requiring a valid Supabase JWT Bearer token.

    Extracts and verifies claims, returning the authenticated user context.
    Never trusts a user ID provided in client headers or request bodies.

    Raises:
        AuthenticationError: If token is missing, expired, forged, or malformed.
    """
    if credentials is None or not credentials.credentials:
        raise AuthenticationError(
            detail="Authentication credentials were not provided",
            error_code="UNAUTHORIZED",
        )

    if credentials.scheme.lower() != "bearer":
        raise AuthenticationError(
            detail="Authorization scheme must be Bearer",
            error_code="INVALID_SCHEME",
        )

    return verifier.verify_token(credentials.credentials)


async def get_optional_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    verifier: Annotated[SupabaseJWTVerifier, Depends(get_jwt_verifier)],
) -> AuthUser | None:
    """FastAPI dependency for endpoints that accept both authenticated and guest access.

    Returns:
        AuthUser if a valid token was supplied; None if no token was present.
    """
    if credentials is None or not credentials.credentials:
        return None

    if credentials.scheme.lower() != "bearer":
        return None

    return verifier.verify_token(credentials.credentials)
