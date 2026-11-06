"""Tests for Supabase JWT verification and FastAPI authentication dependencies."""

import json
import time
import uuid
from typing import Any
from unittest.mock import patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import APIRouter, Depends, FastAPI, status
from fastapi.testclient import TestClient
from jwt import PyJWKClient
from jwt.algorithms import RSAAlgorithm
from jwt.exceptions import PyJWKClientConnectionError

from app.api.dependencies import get_current_user, get_optional_current_user
from app.core.exceptions import AuthenticationError, register_exception_handlers
from app.core.security import SupabaseJWTVerifier
from app.schemas.auth import AuthUser


@pytest.fixture(scope="session")
def rsa_key_pair() -> tuple[Any, Any, dict[str, Any]]:
    """Generate an ephemeral RSA key pair and JWK dictionary for testing."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    jwk_dict = json.loads(RSAAlgorithm.to_jwk(public_key))
    jwk_dict["kid"] = "test-rsa-kid-1"
    jwk_dict["alg"] = "RS256"
    jwk_dict["use"] = "sig"
    return private_key, public_key, jwk_dict


@pytest.fixture
def auth_verifier(rsa_key_pair: tuple[Any, Any, dict[str, Any]]) -> SupabaseJWTVerifier:
    """Create a SupabaseJWTVerifier wired to a mocked JWKS client."""
    _, _, jwk_dict = rsa_key_pair
    jwks_payload = {"keys": [jwk_dict]}

    client = PyJWKClient(
        "https://test.supabase.co/auth/v1/.well-known/jwks.json",
        cache_keys=True,
    )
    # Patch fetch_data so it returns the test JWKS without network requests
    client.fetch_data = lambda: jwks_payload  # type: ignore[assignment]

    return SupabaseJWTVerifier(
        jwks_url="https://test.supabase.co/auth/v1/.well-known/jwks.json",
        issuer="https://test.supabase.co/auth/v1",
        audience="authenticated",
        algorithms=["RS256", "HS256"],
        jwt_secret="super-secret-test-key-32-chars-min!!",
        jwk_client=client,
    )


def create_token(
    private_key: Any,
    sub: str | None = None,
    email: str = "commuter@smartshare.local",
    iss: str = "https://test.supabase.co/auth/v1",
    aud: str = "authenticated",
    exp_offset: int = 3600,
    kid: str = "test-rsa-kid-1",
    alg: str = "RS256",
) -> str:
    """Helper to generate signed test JWTs."""
    now = int(time.time())
    payload: dict[str, Any] = {
        "email": email,
        "role": "authenticated",
        "aud": aud,
        "iss": iss,
        "exp": now + exp_offset,
        "iat": now,
        "app_metadata": {"provider": "email"},
        "user_metadata": {"full_name": "Test Commuter"},
    }
    if sub is not None:
        payload["sub"] = sub

    headers = {"kid": kid} if kid else {}
    return jwt.encode(payload, private_key, algorithm=alg, headers=headers)


# ==============================================================================
# 1. Component Tests for SupabaseJWTVerifier
# ==============================================================================


def test_valid_jwks_rs256_token(
    auth_verifier: SupabaseJWTVerifier,
    rsa_key_pair: tuple[Any, Any, dict[str, Any]],
) -> None:
    """Verify that a valid RS256 token signed with JWKS key verifies successfully."""
    private_key, _, _ = rsa_key_pair
    user_id = uuid.uuid4()
    token = create_token(private_key, sub=str(user_id))

    user = auth_verifier.verify_token(token)

    assert isinstance(user, AuthUser)
    assert user.id == user_id
    assert user.email == "commuter@smartshare.local"
    assert user.role == "authenticated"
    assert user.app_metadata.get("provider") == "email"


def test_valid_hs256_symmetric_token(auth_verifier: SupabaseJWTVerifier) -> None:
    """Verify that a valid HS256 token verifies using the configured symmetric secret."""
    user_id = uuid.uuid4()
    secret = auth_verifier.jwt_secret
    assert secret is not None

    token = create_token(
        secret,
        sub=str(user_id),
        alg="HS256",
        kid="",
    )

    user = auth_verifier.verify_token(token)
    assert user.id == user_id
    assert user.email == "commuter@smartshare.local"


def test_missing_or_empty_token(auth_verifier: SupabaseJWTVerifier) -> None:
    """Verify missing or empty token raises AuthenticationError with UNAUTHORIZED code."""
    for empty_val in ["", "   "]:
        with pytest.raises(AuthenticationError) as exc_info:
            auth_verifier.verify_token(empty_val)
        assert exc_info.value.error_code == "UNAUTHORIZED"


def test_malformed_token(auth_verifier: SupabaseJWTVerifier) -> None:
    """Verify malformed JWT strings raise AuthenticationError with INVALID_TOKEN code."""
    malformed_tokens = [
        "not.a.jwt",
        "invalid_base64_header.payload.signature",
        "only-one-segment",
    ]
    for bad_token in malformed_tokens:
        with pytest.raises(AuthenticationError) as exc_info:
            auth_verifier.verify_token(bad_token)
        assert exc_info.value.error_code == "INVALID_TOKEN"


def test_invalid_signature(
    auth_verifier: SupabaseJWTVerifier,
    rsa_key_pair: tuple[Any, Any, dict[str, Any]],
) -> None:
    """Verify that a token signed with an untrusted private key fails signature verification."""
    # Generate an independent untrusted private key
    untrusted_private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048
    )
    user_id = uuid.uuid4()
    # Sign with untrusted key, but specify test kid so it targets the known public key
    bad_sig_token = create_token(
        untrusted_private_key,
        sub=str(user_id),
        kid="test-rsa-kid-1",
    )

    with pytest.raises(AuthenticationError) as exc_info:
        auth_verifier.verify_token(bad_sig_token)
    assert exc_info.value.error_code == "INVALID_SIGNATURE"


def test_expired_token(
    auth_verifier: SupabaseJWTVerifier,
    rsa_key_pair: tuple[Any, Any, dict[str, Any]],
) -> None:
    """Verify that an expired token raises AuthenticationError with TOKEN_EXPIRED code."""
    private_key, _, _ = rsa_key_pair
    user_id = uuid.uuid4()
    expired_token = create_token(private_key, sub=str(user_id), exp_offset=-300)

    with pytest.raises(AuthenticationError) as exc_info:
        auth_verifier.verify_token(expired_token)
    assert exc_info.value.error_code == "TOKEN_EXPIRED"


def test_invalid_issuer(
    auth_verifier: SupabaseJWTVerifier,
    rsa_key_pair: tuple[Any, Any, dict[str, Any]],
) -> None:
    """Verify that a token with mismatched issuer raises AuthenticationError with INVALID_ISSUER code."""
    private_key, _, _ = rsa_key_pair
    user_id = uuid.uuid4()
    bad_iss_token = create_token(
        private_key,
        sub=str(user_id),
        iss="https://unauthorized-attacker.com/auth/v1",
    )

    with pytest.raises(AuthenticationError) as exc_info:
        auth_verifier.verify_token(bad_iss_token)
    assert exc_info.value.error_code == "INVALID_ISSUER"


def test_invalid_audience(
    auth_verifier: SupabaseJWTVerifier,
    rsa_key_pair: tuple[Any, Any, dict[str, Any]],
) -> None:
    """Verify that a token with mismatched audience raises AuthenticationError with INVALID_AUDIENCE code."""
    private_key, _, _ = rsa_key_pair
    user_id = uuid.uuid4()
    bad_aud_token = create_token(
        private_key,
        sub=str(user_id),
        aud="untrusted-client",
    )

    with pytest.raises(AuthenticationError) as exc_info:
        auth_verifier.verify_token(bad_aud_token)
    assert exc_info.value.error_code == "INVALID_AUDIENCE"


def test_unknown_signing_key_id(
    auth_verifier: SupabaseJWTVerifier,
    rsa_key_pair: tuple[Any, Any, dict[str, Any]],
) -> None:
    """Verify that a token referencing a kid not found in JWKS raises UNKNOWN_SIGNING_KEY code."""
    private_key, _, _ = rsa_key_pair
    user_id = uuid.uuid4()
    unknown_kid_token = create_token(
        private_key,
        sub=str(user_id),
        kid="unknown-kid-does-not-exist",
    )

    with pytest.raises(AuthenticationError) as exc_info:
        auth_verifier.verify_token(unknown_kid_token)
    assert exc_info.value.error_code == "UNKNOWN_SIGNING_KEY"


def test_jwks_retrieval_failure(
    auth_verifier: SupabaseJWTVerifier,
    rsa_key_pair: tuple[Any, Any, dict[str, Any]],
) -> None:
    """Verify that network or HTTP failures fetching JWKS raise JWKS_RETRIEVAL_FAILED code."""
    private_key, _, _ = rsa_key_pair
    user_id = uuid.uuid4()
    token = create_token(private_key, sub=str(user_id))

    # Mock fetch_data raising connection failure
    with patch.object(
        auth_verifier.jwk_client,
        "fetch_data",
        side_effect=PyJWKClientConnectionError(
            "Connection refused: 503 Service Unavailable"
        ),
    ):
        with pytest.raises(AuthenticationError) as exc_info:
            auth_verifier.verify_token(token)
        assert exc_info.value.error_code == "JWKS_RETRIEVAL_FAILED"


def test_invalid_subject_uuid(
    auth_verifier: SupabaseJWTVerifier,
    rsa_key_pair: tuple[Any, Any, dict[str, Any]],
) -> None:
    """Verify that a token without a valid UUID subject claim raises INVALID_SUBJECT code."""
    private_key, _, _ = rsa_key_pair

    # Non-UUID string
    non_uuid_token = create_token(private_key, sub="not-a-valid-uuid")
    with pytest.raises(AuthenticationError) as exc_info:
        auth_verifier.verify_token(non_uuid_token)
    assert exc_info.value.error_code == "INVALID_SUBJECT"

    # Missing sub claim
    missing_sub_token = create_token(private_key, sub=None)
    with pytest.raises(AuthenticationError) as exc_info:
        auth_verifier.verify_token(missing_sub_token)
    assert exc_info.value.error_code == "INVALID_SUBJECT"


def test_disallowed_algorithm(
    auth_verifier: SupabaseJWTVerifier,
    rsa_key_pair: tuple[Any, Any, dict[str, Any]],
) -> None:
    """Verify that tokens using an algorithm not configured in allowed algorithms are rejected."""
    private_key, _, _ = rsa_key_pair
    user_id = uuid.uuid4()

    # Configure verifier strictly allowing only RS256
    strict_verifier = SupabaseJWTVerifier(
        jwks_url=auth_verifier.jwks_url,
        issuer=auth_verifier.issuer,
        audience=auth_verifier.audience,
        algorithms=["RS256"],
        jwk_client=auth_verifier.jwk_client,
    )

    # Attempt HS256 on strict RS256-only verifier
    hs_token = create_token(
        "test-secret-at-least-32-bytes-long-for-hmac",
        sub=str(user_id),
        alg="HS256",
        kid="",
    )
    with pytest.raises(AuthenticationError) as exc_info:
        strict_verifier.verify_token(hs_token)
    assert exc_info.value.error_code == "INVALID_ALGORITHM"


# ==============================================================================
# 2. FastAPI Integration & Dependency Tests
# ==============================================================================


@pytest.fixture
def auth_test_app(auth_verifier: SupabaseJWTVerifier) -> FastAPI:
    """Create a minimal FastAPI app with protected and optional auth test routes."""
    test_app = FastAPI()
    register_exception_handlers(test_app)

    router = APIRouter()

    @router.get("/protected")
    def protected_route(user: AuthUser = Depends(get_current_user)) -> dict[str, Any]:
        return {
            "authenticated": True,
            "user_id": str(user.id),
            "email": user.email,
        }

    @router.get("/optional")
    def optional_route(
        user: AuthUser | None = Depends(get_optional_current_user),
    ) -> dict[str, Any]:
        return {
            "authenticated": user is not None,
            "user_id": str(user.id) if user else None,
        }

    @router.post("/resource/{user_id}")
    def access_user_resource(
        user_id: uuid.UUID,
        user: AuthUser = Depends(get_current_user),
    ) -> dict[str, Any]:
        # Enforce server-side ownership: never trust frontend user_id parameter
        if user_id != user.id:
            raise AuthenticationError(
                detail="You cannot access another user's private resource",
                error_code="FORBIDDEN",
            )
        return {"status": "ok", "user_id": str(user.id)}

    test_app.include_router(router)
    # Override get_jwt_verifier dependency to use test verifier
    from app.api.dependencies import get_jwt_verifier

    test_app.dependency_overrides[get_jwt_verifier] = lambda: auth_verifier
    return test_app


def test_protected_endpoint_valid_token(
    auth_test_app: FastAPI,
    rsa_key_pair: tuple[Any, Any, dict[str, Any]],
) -> None:
    """Verify protected endpoint returns 200 with user context when Bearer token is valid."""
    private_key, _, _ = rsa_key_pair
    user_id = uuid.uuid4()
    token = create_token(private_key, sub=str(user_id), email="rider@test.com")

    with TestClient(auth_test_app) as client:
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["authenticated"] is True
        assert data["user_id"] == str(user_id)
        assert data["email"] == "rider@test.com"


def test_protected_endpoint_missing_token(auth_test_app: FastAPI) -> None:
    """Verify missing Authorization header returns 401 with WWW-Authenticate header."""
    with TestClient(auth_test_app) as client:
        response = client.get("/protected")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.headers.get("www-authenticate") == "Bearer"
        data = response.json()
        assert data["error_code"] == "UNAUTHORIZED"
        assert "Authentication credentials were not provided" in data["detail"]


def test_protected_endpoint_invalid_scheme(auth_test_app: FastAPI) -> None:
    """Verify non-Bearer authorization scheme returns 401."""
    with TestClient(auth_test_app) as client:
        response = client.get(
            "/protected",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error_code"] == "UNAUTHORIZED"


def test_protected_endpoint_invalid_token(auth_test_app: FastAPI) -> None:
    """Verify invalid token on protected endpoint returns 401."""
    with TestClient(auth_test_app) as client:
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer not.a.valid.jwt"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error_code"] == "INVALID_TOKEN"


def test_optional_endpoint_behavior(
    auth_test_app: FastAPI,
    rsa_key_pair: tuple[Any, Any, dict[str, Any]],
) -> None:
    """Verify optional auth endpoint handles both authenticated and unauthenticated callers."""
    private_key, _, _ = rsa_key_pair
    user_id = uuid.uuid4()
    token = create_token(private_key, sub=str(user_id))

    with TestClient(auth_test_app) as client:
        # Case 1: Unauthenticated
        resp_unauth = client.get("/optional")
        assert resp_unauth.status_code == status.HTTP_200_OK
        assert resp_unauth.json()["authenticated"] is False
        assert resp_unauth.json()["user_id"] is None

        # Case 2: Authenticated
        resp_auth = client.get(
            "/optional",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp_auth.status_code == status.HTTP_200_OK
        assert resp_auth.json()["authenticated"] is True
        assert resp_auth.json()["user_id"] == str(user_id)


def test_never_trust_frontend_user_id(
    auth_test_app: FastAPI,
    rsa_key_pair: tuple[Any, Any, dict[str, Any]],
) -> None:
    """Verify backend enforces verified token identity and rejects identity spoofing."""
    private_key, _, _ = rsa_key_pair
    real_user_id = uuid.uuid4()
    spoofed_user_id = uuid.uuid4()
    token = create_token(private_key, sub=str(real_user_id))

    with TestClient(auth_test_app) as client:
        # Access with matching ID succeeds
        good_resp = client.post(
            f"/resource/{real_user_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert good_resp.status_code == status.HTTP_200_OK

        # Attempt to access resource using spoofed ID fails
        bad_resp = client.post(
            f"/resource/{spoofed_user_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert bad_resp.status_code == status.HTTP_401_UNAUTHORIZED
        assert bad_resp.json()["error_code"] == "FORBIDDEN"
