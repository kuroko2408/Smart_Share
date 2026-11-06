"""Supabase JWT verification and cryptographic security component."""

import logging
import uuid
from typing import Any

import jwt
from jwt import PyJWKClient
from jwt.exceptions import (
    DecodeError,
    ExpiredSignatureError,
    InvalidAlgorithmError,
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidSignatureError,
    PyJWKClientConnectionError,
    PyJWKClientError,
    PyJWKError,
    PyJWTError,
)

from app.core.config import settings
from app.core.exceptions import AuthenticationError
from app.schemas.auth import AuthUser

logger = logging.getLogger(__name__)


class SupabaseJWTVerifier:
    """Cryptographic verification component for Supabase Auth JWT access tokens.

    Supports:
    - Asymmetric keys verified via Supabase JWKS (RS256, ES256).
    - Symmetric keys verified via configured JWT secret (HS256).
    - Thread-safe key caching with configurable lifespan.
    - Strict validation of expiration, issuer, audience, and subject UUID.
    """

    def __init__(
        self,
        jwks_url: str | None = None,
        issuer: str | None = None,
        audience: str | None = "authenticated",
        algorithms: list[str] | None = None,
        jwt_secret: str | None = None,
        cache_lifespan: int = 300,
        jwk_client: PyJWKClient | None = None,
    ) -> None:
        self.jwks_url = jwks_url
        self.issuer = issuer
        self.audience = audience
        self.algorithms = [alg.upper() for alg in (algorithms or ["RS256", "ES256"])]
        self.jwt_secret = jwt_secret
        self.cache_lifespan = cache_lifespan
        self._jwk_client = jwk_client

    @property
    def jwk_client(self) -> PyJWKClient:
        """Return or lazily initialize the cached PyJWKClient for JWKS key retrieval."""
        if self._jwk_client is None:
            if not self.jwks_url:
                raise AuthenticationError(
                    detail="Supabase JWKS endpoint is not configured",
                    error_code="AUTH_MISCONFIGURED",
                )
            self._jwk_client = PyJWKClient(
                self.jwks_url,
                cache_keys=True,
                max_cached_keys=16,
                cache_jwk_set=True,
                lifespan=float(self.cache_lifespan),
            )
        return self._jwk_client

    def _resolve_signing_key(self, token: str, alg: str) -> Any:
        """Resolve the cryptographic verification key based on algorithm."""
        if alg.startswith("HS"):
            if not self.jwt_secret:
                raise AuthenticationError(
                    detail="Symmetric JWT secret is not configured for HS algorithm",
                    error_code="AUTH_MISCONFIGURED",
                )
            return self.jwt_secret

        # Asymmetric algorithms (RS256, ES256, etc.) fetch public key from JWKS
        try:
            signing_key = self.jwk_client.get_signing_key_from_jwt(token)
            return signing_key.key
        except PyJWKClientConnectionError as exc:
            logger.error("Network or connection error fetching JWKS: %s", exc)
            raise AuthenticationError(
                detail="Unable to reach authentication provider key service",
                error_code="JWKS_RETRIEVAL_FAILED",
            ) from exc
        except (PyJWKClientError, PyJWKError) as exc:
            logger.warning("Unrecognized signing key in JWT header: %s", exc)
            raise AuthenticationError(
                detail="Token was signed with an unrecognized key",
                error_code="UNKNOWN_SIGNING_KEY",
            ) from exc
        except Exception as exc:
            logger.error("Unexpected error retrieving signing key: %s", exc)
            raise AuthenticationError(
                detail="Failed to retrieve cryptographic signing key",
                error_code="INVALID_SIGNING_KEY",
            ) from exc

    def verify_token(self, token: str) -> AuthUser:
        """Verify Supabase JWT signature and claims, returning verified AuthUser context.

        Raises:
            AuthenticationError: On any cryptographic, structural, or claim validation failure.
        """
        if not token or not token.strip():
            raise AuthenticationError(
                detail="Authentication token is required",
                error_code="UNAUTHORIZED",
            )

        clean_token = token.strip()

        # 1. Parse unverified header to determine signing algorithm and key identifier
        try:
            unverified_header = jwt.get_unverified_header(clean_token)
        except DecodeError as exc:
            raise AuthenticationError(
                detail="Malformed authorization token",
                error_code="INVALID_TOKEN",
            ) from exc
        except Exception as exc:
            raise AuthenticationError(
                detail="Invalid token header format",
                error_code="INVALID_TOKEN",
            ) from exc

        alg = unverified_header.get("alg")
        if not alg or not isinstance(alg, str):
            raise AuthenticationError(
                detail="Token header missing algorithm ('alg')",
                error_code="INVALID_ALGORITHM",
            )

        upper_alg = alg.upper()
        if upper_alg not in self.algorithms:
            raise AuthenticationError(
                detail=f"Disallowed token signing algorithm '{alg}'. Allowed: {', '.join(self.algorithms)}",
                error_code="INVALID_ALGORITHM",
            )

        # 2. Resolve public verification key or symmetric secret
        verification_key = self._resolve_signing_key(clean_token, upper_alg)

        # 3. Cryptographically verify signature and validate standard claims
        decode_options: dict[str, Any] = {
            "verify_signature": True,
            "verify_exp": True,
            "verify_aud": bool(self.audience),
            "verify_iss": bool(self.issuer),
        }

        try:
            payload: dict[str, Any] = jwt.decode(
                clean_token,
                key=verification_key,
                algorithms=[upper_alg],
                audience=self.audience if self.audience else None,
                issuer=self.issuer if self.issuer else None,
                options=decode_options,
            )
        except ExpiredSignatureError as exc:
            raise AuthenticationError(
                detail="Authentication token has expired",
                error_code="TOKEN_EXPIRED",
            ) from exc
        except InvalidIssuerError as exc:
            raise AuthenticationError(
                detail=f"Token issuer is invalid. Expected: {self.issuer}",
                error_code="INVALID_ISSUER",
            ) from exc
        except InvalidAudienceError as exc:
            raise AuthenticationError(
                detail=f"Token audience is invalid. Expected: {self.audience}",
                error_code="INVALID_AUDIENCE",
            ) from exc
        except InvalidSignatureError as exc:
            raise AuthenticationError(
                detail="Token signature verification failed",
                error_code="INVALID_SIGNATURE",
            ) from exc
        except InvalidAlgorithmError as exc:
            raise AuthenticationError(
                detail=f"Invalid token algorithm: {exc}",
                error_code="INVALID_ALGORITHM",
            ) from exc
        except DecodeError as exc:
            raise AuthenticationError(
                detail="Failed to decode token payload",
                error_code="INVALID_TOKEN",
            ) from exc
        except PyJWTError as exc:
            raise AuthenticationError(
                detail=f"Token validation failed: {exc}",
                error_code="INVALID_TOKEN",
            ) from exc

        # 4. Extract and validate authenticated user UUID from subject ('sub') claim
        sub = payload.get("sub")
        if not sub:
            raise AuthenticationError(
                detail="Token missing required subject claim ('sub')",
                error_code="INVALID_SUBJECT",
            )

        try:
            user_uuid = uuid.UUID(str(sub))
        except (ValueError, TypeError) as exc:
            raise AuthenticationError(
                detail="Token subject claim is not a valid UUID",
                error_code="INVALID_SUBJECT",
            ) from exc

        # 5. Return strongly-typed AuthUser context
        return AuthUser(
            id=user_uuid,
            email=payload.get("email"),
            role=payload.get("role"),
            app_metadata=payload.get("app_metadata") or {},
            user_metadata=payload.get("user_metadata") or {},
            claims=payload,
        )


def create_supabase_jwt_verifier() -> SupabaseJWTVerifier:
    """Factory creating a SupabaseJWTVerifier configured from application settings."""
    return SupabaseJWTVerifier(
        jwks_url=settings.effective_jwks_url,
        issuer=settings.effective_jwt_issuer,
        audience=settings.SUPABASE_JWT_AUDIENCE,
        algorithms=settings.SUPABASE_JWT_ALGORITHMS,
        jwt_secret=settings.SUPABASE_JWT_SECRET,
        cache_lifespan=settings.JWKS_CACHE_LIFESPAN,
    )
