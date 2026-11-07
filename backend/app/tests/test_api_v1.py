"""Integration tests for Smart Share Phase 2D Core APIs.

Covers:
- Base prefix: /api/v1
- Profiles: GET /users/me, PATCH /users/me
- Ride Requests:
    - POST /ride-requests
    - GET /ride-requests (pagination, status filtering, user isolation)
    - GET /ride-requests/{id} (ownership enforcement)
    - PATCH /ride-requests/{id} (validation, state lifecycle invariants)
    - POST /ride-requests/{id}/cancel (lifecycle transitions)
- Cryptographic JWT authentication, Bearer scheme, and role verification
- Spatial coordinates, temporal bounds, and domain validation
"""

import json
import time
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from geoalchemy2 import Geography
from httpx import ASGITransport, AsyncClient
from jwt import PyJWKClient
from jwt.algorithms import RSAAlgorithm
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool
from sqlalchemy.schema import CheckConstraint

from app.api.dependencies import get_jwt_verifier
from app.core.database import get_db
from app.core.security import SupabaseJWTVerifier
from app.main import create_application
from app.models import Base
from app.schemas.auth import AuthUser

# ==============================================================================
# SQLite Compatibility Compilers for Spatial and Constraint Support in Tests
# ==============================================================================


@compiles(Geography, "sqlite")
def compile_geography_sqlite(element: Any, compiler: Any, **kw: Any) -> str:
    """Compile PostGIS Geography type to TEXT for in-memory SQLite testing."""
    return "TEXT"


@compiles(CheckConstraint, "sqlite")
def compile_check_constraint_sqlite(element: Any, compiler: Any, **kw: Any) -> str:
    """Strip PostgreSQL-specific ::geometry casts for SQLite in-memory DDL."""
    text_sql = compiler.sql_compiler.process(
        element.sqltext, include_table=False, literal_binds=True
    )
    text_sql = text_sql.replace("::geometry", "")
    preamble = compiler.define_constraint_preamble(element, **kw)
    return f"{preamble}CHECK ({text_sql})"


# ==============================================================================
# Test Fixtures: RSA Key Pair, Mocked Verifier, Isolated DB Engine, and App
# ==============================================================================


@pytest.fixture(scope="session")
def rsa_key_pair() -> tuple[Any, Any, dict[str, Any]]:
    """Generate an ephemeral RSA key pair and JWK dictionary for testing."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    jwk_dict = json.loads(RSAAlgorithm.to_jwk(public_key))
    jwk_dict["kid"] = "test-api-v1-kid"
    jwk_dict["alg"] = "RS256"
    jwk_dict["use"] = "sig"
    return private_key, public_key, jwk_dict


@pytest.fixture
def auth_verifier(
    rsa_key_pair: tuple[Any, Any, dict[str, Any]],
) -> SupabaseJWTVerifier:
    """Create a SupabaseJWTVerifier wired to the test RSA JWKS."""
    _, _, jwk_dict = rsa_key_pair
    jwks_payload = {"keys": [jwk_dict]}

    client = PyJWKClient(
        "https://test.supabase.co/auth/v1/.well-known/jwks.json",
        cache_keys=True,
    )
    client.fetch_data = lambda: jwks_payload  # type: ignore[assignment]

    return SupabaseJWTVerifier(
        jwks_url="https://test.supabase.co/auth/v1/.well-known/jwks.json",
        issuer="https://test.supabase.co/auth/v1",
        audience="authenticated",
        algorithms=["RS256"],
        jwt_secret="super-secret-test-key-32-chars-min!!",
        jwk_client=client,
    )


def generate_test_token(
    private_key: Any,
    user_id: uuid.UUID,
    email: str = "commuter@smartshare.local",
    full_name: str | None = "Test Commuter",
    exp_offset: int = 3600,
) -> str:
    """Generate a signed RS256 JWT token for an authenticated user."""
    now = int(time.time())
    user_meta: dict[str, Any] = {}
    if full_name is not None:
        user_meta["full_name"] = full_name

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "role": "authenticated",
        "aud": "authenticated",
        "iss": "https://test.supabase.co/auth/v1",
        "exp": now + exp_offset,
        "iat": now,
        "app_metadata": {"provider": "email"},
        "user_metadata": user_meta,
    }
    return jwt.encode(
        payload, private_key, algorithm="RS256", headers={"kid": "test-api-v1-kid"}
    )


@pytest.fixture
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Provide a fresh, isolated in-memory SQLite database engine for each test."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("ATTACH DATABASE ':memory:' AS auth;")
        cursor.execute("CREATE TABLE auth.users (id TEXT PRIMARY KEY, email TEXT);")
        cursor.close()
        # Register PostGIS/Postgres emulated SQLite functions
        dbapi_connection.create_function("ST_GeogFromText", 1, lambda val: val)
        dbapi_connection.create_function("AsBinary", 1, lambda val: val)
        dbapi_connection.create_function(
            "ST_Equals", 2, lambda a, b: 1 if a == b else 0
        )
        dbapi_connection.create_function(
            "char_length", 1, lambda s: len(s) if s is not None else 0
        )
        dbapi_connection.create_function(
            "gen_random_uuid",
            0,
            lambda: "00000000-0000-0000-0000-000000000001",
        )
        dbapi_connection.create_function("now", 0, lambda: "2026-11-05T00:00:00")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest.fixture
def user_a() -> AuthUser:
    """Primary authenticated user for testing."""
    return AuthUser(
        id=uuid.uuid4(),
        email="user_a@smartshare.local",
        role="authenticated",
        app_metadata={"provider": "email"},
        user_metadata={"full_name": "Alice Commuter"},
    )


@pytest.fixture
def user_b() -> AuthUser:
    """Secondary authenticated user for testing authorization and isolation."""
    return AuthUser(
        id=uuid.uuid4(),
        email="user_b@smartshare.local",
        role="authenticated",
        app_metadata={"provider": "email"},
        user_metadata={"full_name": "Bob Commuter"},
    )


@pytest.fixture
def test_app(test_engine: AsyncEngine, auth_verifier: SupabaseJWTVerifier) -> FastAPI:
    """Create FastAPI application wired to the test engine and JWT verifier."""
    app = create_application()
    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_jwt_verifier] = lambda: auth_verifier
    return app


@pytest.fixture
def client_user_a(
    test_app: FastAPI,
    user_a: AuthUser,
    rsa_key_pair: tuple[Any, Any, dict[str, Any]],
) -> AsyncClient:
    """AsyncClient authenticated as user_a with valid Bearer token."""
    private_key, _, _ = rsa_key_pair
    token = generate_test_token(
        private_key,
        user_id=user_a.id,
        email=user_a.email,
        full_name=user_a.user_metadata.get("full_name"),
    )
    return AsyncClient(
        transport=ASGITransport(app=test_app, raise_app_exceptions=False),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    )


@pytest.fixture
def client_user_b(
    test_app: FastAPI,
    user_b: AuthUser,
    rsa_key_pair: tuple[Any, Any, dict[str, Any]],
) -> AsyncClient:
    """AsyncClient authenticated as user_b with valid Bearer token."""
    private_key, _, _ = rsa_key_pair
    token = generate_test_token(
        private_key,
        user_id=user_b.id,
        email=user_b.email,
        full_name=user_b.user_metadata.get("full_name"),
    )
    return AsyncClient(
        transport=ASGITransport(app=test_app, raise_app_exceptions=False),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    )


@pytest.fixture
def unauthenticated_client(test_app: FastAPI) -> AsyncClient:
    """AsyncClient with no Authorization header."""
    return AsyncClient(
        transport=ASGITransport(app=test_app, raise_app_exceptions=False),
        base_url="http://test",
    )


# ==============================================================================
# 1. Authentication & Security Enforcement Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_unauthenticated_access_rejected(
    unauthenticated_client: AsyncClient,
) -> None:
    """Verify that all core endpoints reject unauthenticated requests with 401."""
    random_id = uuid.uuid4()
    endpoints = [
        ("GET", "/api/v1/users/me", None),
        ("PATCH", "/api/v1/users/me", {"display_name": "Test"}),
        ("POST", "/api/v1/ride-requests", {}),
        ("GET", "/api/v1/ride-requests", None),
        ("GET", f"/api/v1/ride-requests/{random_id}", None),
        ("PATCH", f"/api/v1/ride-requests/{random_id}", {}),
        ("POST", f"/api/v1/ride-requests/{random_id}/cancel", None),
        ("POST", f"/api/v1/ride-requests/{random_id}/matches", None),
        ("GET", f"/api/v1/ride-requests/{random_id}/matches", None),
        ("GET", f"/api/v1/matches/{uuid.uuid4()}?request_id={random_id}", None),
    ]

    for method, path, payload in endpoints:
        if method == "GET":
            response = await unauthenticated_client.get(path)
        elif method == "POST":
            response = await unauthenticated_client.post(path, json=payload)
        elif method == "PATCH":
            response = await unauthenticated_client.patch(path, json=payload)
        else:
            raise ValueError(f"Unsupported method: {method}")

        assert response.status_code == 401, (
            f"Endpoint {method} {path} should return 401, got {response.status_code}"
        )
        assert response.json()["error_code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_match_access_checks_request_ownership_before_discovery(
    client_user_a: AsyncClient,
    client_user_b: AsyncClient,
) -> None:
    """Missing, non-owned, and cancelled targets fail before PostGIS discovery."""
    now = datetime.now(UTC)
    payload = {
        "pickup": {"latitude": 19.0657, "longitude": 72.8687},
        "destination": {"latitude": 19.1176, "longitude": 72.9060},
        "departure_earliest": (now + timedelta(hours=1)).isoformat(),
        "departure_latest": (now + timedelta(hours=2)).isoformat(),
        "seats_requested": 1,
        "max_extra_minutes": 20,
    }
    created = await client_user_a.post("/api/v1/ride-requests", json=payload)
    assert created.status_code == 201
    request_id = created.json()["data"]["id"]

    missing = await client_user_a.post(f"/api/v1/ride-requests/{uuid.uuid4()}/matches")
    assert missing.status_code == 404

    cross_user = await client_user_b.post(f"/api/v1/ride-requests/{request_id}/matches")
    assert cross_user.status_code == 403

    cancelled = await client_user_a.post(f"/api/v1/ride-requests/{request_id}/cancel")
    assert cancelled.status_code == 200
    stale = await client_user_a.get(f"/api/v1/ride-requests/{request_id}/matches")
    assert stale.status_code == 400


@pytest.mark.asyncio
async def test_matching_e2e_discovery_and_proposal_retrieval(
    client_user_a: AsyncClient,
    client_user_b: AsyncClient,
    user_b: AuthUser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify complete end-to-end matching workflow: discovery, scoring, proposal retrieval, and ownership."""
    now = datetime.now(UTC)
    payload_a = {
        "pickup": {
            "latitude": 19.0657,
            "longitude": 72.8687,
            "label": "BKC Maker Maxity",
        },
        "destination": {
            "latitude": 19.1176,
            "longitude": 72.9060,
            "label": "Powai Hiranandani",
        },
        "departure_earliest": (now + timedelta(hours=1)).isoformat(),
        "departure_latest": (now + timedelta(hours=2)).isoformat(),
        "seats_requested": 1,
        "max_extra_minutes": 20,
    }
    created_a = await client_user_a.post("/api/v1/ride-requests", json=payload_a)
    assert created_a.status_code == 201
    req_a_id = created_a.json()["data"]["id"]

    # Candidate B data to return from discover_candidates
    cand_b_id = uuid.uuid4()
    mock_candidate_row = {
        "candidate_id": cand_b_id,
        "candidate_user_id": user_b.id,
        "owner_name": "Test Commuter B",
        "pickup_location": "POINT(72.8690 19.0660)",
        "destination": "POINT(72.9050 19.1170)",
        "pickup_label": "BKC One",
        "destination_label": "Powai Galleria",
        "departure_earliest": now + timedelta(hours=1),
        "departure_latest": now + timedelta(hours=2),
        "seats_requested": 1,
        "max_extra_minutes": 20,
        "created_at": now,
        "pickup_distance_m": 45.0,
        "dest_distance_m": 120.0,
        "overlap_seconds": 3600.0,
    }

    import app.matching.service as matching_service

    async def mock_discover(db, **kwargs):
        return [mock_candidate_row]

    monkeypatch.setattr(matching_service, "discover_candidates", mock_discover)

    # 1. Trigger match discovery via POST
    post_res = await client_user_a.post(f"/api/v1/ride-requests/{req_a_id}/matches")
    assert post_res.status_code == 200
    post_body = post_res.json()
    assert post_body["data"]["total_candidates_found"] == 1
    proposal = post_body["data"]["proposals"][0]
    proposal_id = proposal["proposal_id"]
    assert proposal["candidate"]["candidate_display_name"] == "Test Commuter B"
    assert proposal["candidate"]["scores"]["composite_score"] > 0.90
    assert len(proposal["ordered_stops"]) == 4
    assert len(proposal["compatibility_explanations"]) >= 4

    # 2. Retrieve proposals via GET
    get_res = await client_user_a.get(f"/api/v1/ride-requests/{req_a_id}/matches")
    assert get_res.status_code == 200
    get_body = get_res.json()
    assert get_body["data"]["proposals"][0]["proposal_id"] == proposal_id

    # 3. Retrieve specific proposal detail by proposal_id
    detail_res = await client_user_a.get(
        f"/api/v1/matches/{proposal_id}?request_id={req_a_id}"
    )
    assert detail_res.status_code == 200
    assert detail_res.json()["data"]["proposal_id"] == proposal_id

    # 4. Cross-user attempt to query proposal with target request_id returns 403
    forbidden_res = await client_user_b.get(
        f"/api/v1/matches/{proposal_id}?request_id={req_a_id}"
    )
    assert forbidden_res.status_code == 403

    # 5. Non-existent proposal returns 404
    non_existent = await client_user_a.get(
        f"/api/v1/matches/{uuid.uuid4()}?request_id={req_a_id}"
    )
    assert non_existent.status_code == 404

    # 6. Cancel target request -> subsequent match query returns 400
    cancel_res = await client_user_a.post(f"/api/v1/ride-requests/{req_a_id}/cancel")
    assert cancel_res.status_code == 200

    cancelled_get = await client_user_a.get(f"/api/v1/ride-requests/{req_a_id}/matches")
    assert cancelled_get.status_code == 400


@pytest.mark.asyncio
async def test_invalid_scheme_rejected(
    unauthenticated_client: AsyncClient,
) -> None:
    """Verify that authorization header with invalid scheme returns 401 UNAUTHORIZED."""
    headers = {"Authorization": "Basic dXNlcjpwYXNz"}
    response = await unauthenticated_client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 401
    assert response.json()["error_code"] == "UNAUTHORIZED"


# ==============================================================================
# 2. User Profiles Endpoints Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_get_my_profile_lazy_provisioning(
    client_user_a: AsyncClient, user_a: AuthUser
) -> None:
    """Verify that GET /users/me provisions an application profile from verified JWT claims."""
    response = await client_user_a.get("/api/v1/users/me")
    assert response.status_code == 200

    payload = response.json()
    assert payload["message"] == "Profile retrieved successfully"
    data = payload["data"]
    assert data["id"] == str(user_a.id)
    assert data["display_name"] == "Alice Commuter"
    assert data["avatar_url"] is None
    assert data["is_onboarding_completed"] is True


@pytest.mark.asyncio
async def test_get_my_profile_uncompleted_onboarding(
    test_app: FastAPI,
    rsa_key_pair: tuple[Any, Any, dict[str, Any]],
) -> None:
    """Verify that a user without a display name in metadata shows onboarding incomplete."""
    private_key, _, _ = rsa_key_pair
    user_id = uuid.uuid4()
    token = generate_test_token(
        private_key,
        user_id=user_id,
        email="otp_user@smartshare.local",
        full_name=None,  # No display name
    )

    async with AsyncClient(
        transport=ASGITransport(app=test_app, raise_app_exceptions=False),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as client:
        response = await client.get("/api/v1/users/me")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] == str(user_id)
        assert data["display_name"] == ""
        assert data["is_onboarding_completed"] is False


@pytest.mark.asyncio
async def test_patch_my_profile_update(
    client_user_a: AsyncClient, user_a: AuthUser
) -> None:
    """Verify updating profile display name and avatar URL."""
    update_payload = {
        "display_name": "Alice Wonderland",
        "avatar_url": "https://cdn.example.com/avatars/alice.png",
    }
    response = await client_user_a.patch("/api/v1/users/me", json=update_payload)
    assert response.status_code == 200

    data = response.json()["data"]
    assert data["id"] == str(user_a.id)
    assert data["display_name"] == "Alice Wonderland"
    assert data["avatar_url"] == "https://cdn.example.com/avatars/alice.png"
    assert data["is_onboarding_completed"] is True

    # Confirm changes persist on subsequent GET
    get_res = await client_user_a.get("/api/v1/users/me")
    assert get_res.json()["data"]["display_name"] == "Alice Wonderland"


# ==============================================================================
# 3. Ride Requests Creation Tests (POST /ride-requests)
# ==============================================================================


@pytest.mark.asyncio
async def test_create_ride_request_success(
    client_user_a: AsyncClient, user_a: AuthUser
) -> None:
    """Verify successful creation of a valid ride request."""
    now = datetime.now(UTC)
    payload = {
        "pickup": {
            "latitude": 19.0760,
            "longitude": 72.8777,
            "label": "Bandra Kurla Complex",
        },
        "destination": {
            "latitude": 18.9220,
            "longitude": 72.8258,
            "label": "Colaba Gateway",
        },
        "departure_earliest": (now + timedelta(minutes=15)).isoformat(),
        "departure_latest": (now + timedelta(minutes=45)).isoformat(),
        "seats_requested": 2,
        "max_extra_minutes": 25,
    }

    response = await client_user_a.post("/api/v1/ride-requests", json=payload)
    assert response.status_code == 201

    body = response.json()
    assert body["message"] == "Ride request created successfully"
    data = body["data"]
    assert data["user_id"] == str(user_a.id)
    assert data["pickup"]["latitude"] == pytest.approx(19.0760)
    assert data["pickup"]["longitude"] == pytest.approx(72.8777)
    assert data["pickup"]["label"] == "Bandra Kurla Complex"
    assert data["destination"]["latitude"] == pytest.approx(18.9220)
    assert data["destination"]["longitude"] == pytest.approx(72.8258)
    assert data["destination"]["label"] == "Colaba Gateway"
    assert data["seats_requested"] == 2
    assert data["max_extra_minutes"] == 25
    assert data["status"] == "ACTIVE"
    assert data["expires_at"] is not None


@pytest.mark.asyncio
async def test_create_ride_request_invalid_coordinates(
    client_user_a: AsyncClient,
) -> None:
    """Verify rejection of coordinates exceeding WGS 84 boundaries."""
    now = datetime.now(UTC)
    base_payload: dict[str, Any] = {
        "pickup": {"latitude": 19.0760, "longitude": 72.8777},
        "destination": {"latitude": 18.9220, "longitude": 72.8258},
        "departure_earliest": (now + timedelta(minutes=15)).isoformat(),
        "departure_latest": (now + timedelta(minutes=45)).isoformat(),
        "seats_requested": 1,
        "max_extra_minutes": 15,
    }

    # Invalid latitude (> 90.0)
    bad_payload = dict(base_payload)
    bad_payload["pickup"] = {"latitude": 95.0, "longitude": 72.8777}
    res = await client_user_a.post("/api/v1/ride-requests", json=bad_payload)
    assert res.status_code == 422

    # Invalid longitude (< -180.0)
    bad_payload = dict(base_payload)
    bad_payload["destination"] = {"latitude": 18.9220, "longitude": -185.0}
    res = await client_user_a.post("/api/v1/ride-requests", json=bad_payload)
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_create_ride_request_identical_endpoints(
    client_user_a: AsyncClient,
) -> None:
    """Verify rejection when pickup and destination coordinates are identical."""
    now = datetime.now(UTC)
    payload = {
        "pickup": {"latitude": 19.0760, "longitude": 72.8777},
        "destination": {
            "latitude": 19.0760,
            "longitude": 72.8777,
        },  # Same coordinates
        "departure_earliest": (now + timedelta(minutes=10)).isoformat(),
        "departure_latest": (now + timedelta(minutes=30)).isoformat(),
        "seats_requested": 1,
        "max_extra_minutes": 15,
    }
    response = await client_user_a.post("/api/v1/ride-requests", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_ride_request_invalid_departure_window(
    client_user_a: AsyncClient,
) -> None:
    """Verify rejection when departure_latest precedes departure_earliest."""
    now = datetime.now(UTC)
    payload = {
        "pickup": {"latitude": 19.0760, "longitude": 72.8777},
        "destination": {"latitude": 18.9220, "longitude": 72.8258},
        "departure_earliest": (now + timedelta(minutes=40)).isoformat(),
        "departure_latest": (
            now + timedelta(minutes=10)
        ).isoformat(),  # Precedes earliest
        "seats_requested": 1,
        "max_extra_minutes": 15,
    }
    response = await client_user_a.post("/api/v1/ride-requests", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_ride_request_past_departure_rejected(
    client_user_a: AsyncClient,
) -> None:
    """Verify rejection when departure window is in the past."""
    now = datetime.now(UTC)
    payload = {
        "pickup": {"latitude": 19.0760, "longitude": 72.8777},
        "destination": {"latitude": 18.9220, "longitude": 72.8258},
        "departure_earliest": (now - timedelta(minutes=30)).isoformat(),  # In the past
        "departure_latest": (now - timedelta(minutes=10)).isoformat(),
        "seats_requested": 1,
        "max_extra_minutes": 15,
    }
    response = await client_user_a.post("/api/v1/ride-requests", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_ride_request_boundary_seats_and_minutes(
    client_user_a: AsyncClient,
) -> None:
    """Verify seat count (1..6) and detour minutes (0..180) boundary enforcement."""
    now = datetime.now(UTC)
    base_payload = {
        "pickup": {"latitude": 19.0760, "longitude": 72.8777},
        "destination": {"latitude": 18.9220, "longitude": 72.8258},
        "departure_earliest": (now + timedelta(minutes=10)).isoformat(),
        "departure_latest": (now + timedelta(minutes=30)).isoformat(),
    }

    # Seats < 1
    p1 = {**base_payload, "seats_requested": 0, "max_extra_minutes": 15}
    res1 = await client_user_a.post("/api/v1/ride-requests", json=p1)
    assert res1.status_code == 422

    # Seats > 6
    p2 = {**base_payload, "seats_requested": 7, "max_extra_minutes": 15}
    res2 = await client_user_a.post("/api/v1/ride-requests", json=p2)
    assert res2.status_code == 422

    # Detour minutes < 0
    p3 = {**base_payload, "seats_requested": 1, "max_extra_minutes": -5}
    res3 = await client_user_a.post("/api/v1/ride-requests", json=p3)
    assert res3.status_code == 422

    # Detour minutes > 180
    p4 = {**base_payload, "seats_requested": 1, "max_extra_minutes": 200}
    res4 = await client_user_a.post("/api/v1/ride-requests", json=p4)
    assert res4.status_code == 422


# ==============================================================================
# 4. Listing, Pagination & Filtering Tests (GET /ride-requests)
# ==============================================================================


@pytest.mark.asyncio
async def test_list_ride_requests_pagination(
    client_user_a: AsyncClient,
) -> None:
    """Verify pagination controls (limit, offset, total, has_more) on ride request listing."""
    now = datetime.now(UTC)
    for i in range(5):
        payload = {
            "pickup": {"latitude": 19.0 + (i * 0.01), "longitude": 72.8},
            "destination": {"latitude": 18.9, "longitude": 72.82},
            "departure_earliest": (now + timedelta(hours=1, minutes=i * 5)).isoformat(),
            "departure_latest": (now + timedelta(hours=2, minutes=i * 5)).isoformat(),
            "seats_requested": 1,
            "max_extra_minutes": 15,
        }
        res = await client_user_a.post("/api/v1/ride-requests", json=payload)
        assert res.status_code == 201

    # First page: limit 2, offset 0 -> 2 items, total 5, has_more True
    page1 = await client_user_a.get("/api/v1/ride-requests?limit=2&offset=0")
    assert page1.status_code == 200
    p1_body = page1.json()
    assert len(p1_body["data"]) == 2
    assert p1_body["pagination"]["total"] == 5
    assert p1_body["pagination"]["limit"] == 2
    assert p1_body["pagination"]["offset"] == 0
    assert p1_body["pagination"]["has_more"] is True

    # Second page: limit 2, offset 2 -> 2 items, has_more True
    page2 = await client_user_a.get("/api/v1/ride-requests?limit=2&offset=2")
    assert page2.status_code == 200
    assert len(page2.json()["data"]) == 2
    assert page2.json()["pagination"]["has_more"] is True

    # Final page: limit 2, offset 4 -> 1 item, has_more False
    page3 = await client_user_a.get("/api/v1/ride-requests?limit=2&offset=4")
    assert page3.status_code == 200
    assert len(page3.json()["data"]) == 1
    assert page3.json()["pagination"]["has_more"] is False


@pytest.mark.asyncio
async def test_list_ride_requests_status_filtering(
    client_user_a: AsyncClient,
) -> None:
    """Verify status filtering and validation of filter parameters."""
    now = datetime.now(UTC)
    payload = {
        "pickup": {"latitude": 19.0760, "longitude": 72.8777},
        "destination": {"latitude": 18.9220, "longitude": 72.8258},
        "departure_earliest": (now + timedelta(minutes=15)).isoformat(),
        "departure_latest": (now + timedelta(minutes=45)).isoformat(),
        "seats_requested": 1,
        "max_extra_minutes": 15,
    }

    # Create 2 requests
    r1 = await client_user_a.post("/api/v1/ride-requests", json=payload)
    r2 = await client_user_a.post("/api/v1/ride-requests", json=payload)
    id1 = r1.json()["data"]["id"]
    _ = r2.json()["data"]["id"]

    # Cancel the first one
    await client_user_a.post(f"/api/v1/ride-requests/{id1}/cancel")

    # Filter ACTIVE
    active_res = await client_user_a.get("/api/v1/ride-requests?status=ACTIVE")
    assert active_res.status_code == 200
    assert len(active_res.json()["data"]) == 1
    assert active_res.json()["data"][0]["status"] == "ACTIVE"

    # Filter CANCELLED
    cancelled_res = await client_user_a.get("/api/v1/ride-requests?status=CANCELLED")
    assert cancelled_res.status_code == 200
    assert len(cancelled_res.json()["data"]) == 1
    assert cancelled_res.json()["data"][0]["status"] == "CANCELLED"

    # Filter with invalid status
    invalid_res = await client_user_a.get("/api/v1/ride-requests?status=BOGUS_STATUS")
    assert invalid_res.status_code == 400
    assert invalid_res.json()["error_code"] == "VALIDATION_ERROR"


# ==============================================================================
# 5. Ownership Enforcement & Isolation Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_strict_user_data_isolation(
    client_user_a: AsyncClient,
    client_user_b: AsyncClient,
) -> None:
    """Verify that User A cannot see User B's ride requests and vice versa."""
    now = datetime.now(UTC)
    payload_a = {
        "pickup": {"latitude": 19.0760, "longitude": 72.8777},
        "destination": {"latitude": 18.9220, "longitude": 72.8258},
        "departure_earliest": (now + timedelta(minutes=10)).isoformat(),
        "departure_latest": (now + timedelta(minutes=30)).isoformat(),
        "seats_requested": 1,
        "max_extra_minutes": 15,
    }
    res_a = await client_user_a.post("/api/v1/ride-requests", json=payload_a)
    assert res_a.status_code == 201

    # User B lists ride requests: must return empty list
    list_b = await client_user_b.get("/api/v1/ride-requests")
    assert list_b.status_code == 200
    assert len(list_b.json()["data"]) == 0
    assert list_b.json()["pagination"]["total"] == 0

    # User A lists ride requests: must see their 1 request
    list_a = await client_user_a.get("/api/v1/ride-requests")
    assert list_a.status_code == 200
    assert len(list_a.json()["data"]) == 1


@pytest.mark.asyncio
async def test_get_ride_request_ownership_enforcement(
    client_user_a: AsyncClient,
    client_user_b: AsyncClient,
) -> None:
    """Verify that User B cannot retrieve User A's ride request by ID (403 Forbidden)."""
    now = datetime.now(UTC)
    payload = {
        "pickup": {"latitude": 19.0760, "longitude": 72.8777},
        "destination": {"latitude": 18.9220, "longitude": 72.8258},
        "departure_earliest": (now + timedelta(minutes=10)).isoformat(),
        "departure_latest": (now + timedelta(minutes=30)).isoformat(),
        "seats_requested": 1,
        "max_extra_minutes": 15,
    }
    create_res = await client_user_a.post("/api/v1/ride-requests", json=payload)
    req_id = create_res.json()["data"]["id"]

    # User A (owner) can retrieve it
    get_owner = await client_user_a.get(f"/api/v1/ride-requests/{req_id}")
    assert get_owner.status_code == 200
    assert get_owner.json()["data"]["id"] == req_id

    # User B (not owner) is forbidden (403)
    get_other = await client_user_b.get(f"/api/v1/ride-requests/{req_id}")
    assert get_other.status_code == 403
    assert get_other.json()["error_code"] == "FORBIDDEN"

    # Non-existent ID returns 404
    non_existent = uuid.uuid4()
    get_none = await client_user_a.get(f"/api/v1/ride-requests/{non_existent}")
    assert get_none.status_code == 404
    assert get_none.json()["error_code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_patch_ride_request_ownership_enforcement(
    client_user_a: AsyncClient,
    client_user_b: AsyncClient,
) -> None:
    """Verify that User B cannot modify User A's ride request (403 Forbidden)."""
    now = datetime.now(UTC)
    payload = {
        "pickup": {"latitude": 19.0760, "longitude": 72.8777},
        "destination": {"latitude": 18.9220, "longitude": 72.8258},
        "departure_earliest": (now + timedelta(minutes=10)).isoformat(),
        "departure_latest": (now + timedelta(minutes=30)).isoformat(),
        "seats_requested": 1,
        "max_extra_minutes": 15,
    }
    created = await client_user_a.post("/api/v1/ride-requests", json=payload)
    req_id = created.json()["data"]["id"]

    # User B attempts to patch User A's request
    patch_res = await client_user_b.patch(
        f"/api/v1/ride-requests/{req_id}",
        json={"seats_requested": 3},
    )
    assert patch_res.status_code == 403
    assert patch_res.json()["error_code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_cancel_ride_request_ownership_enforcement(
    client_user_a: AsyncClient,
    client_user_b: AsyncClient,
) -> None:
    """Verify that User B cannot cancel User A's ride request (403 Forbidden)."""
    now = datetime.now(UTC)
    payload = {
        "pickup": {"latitude": 19.0760, "longitude": 72.8777},
        "destination": {"latitude": 18.9220, "longitude": 72.8258},
        "departure_earliest": (now + timedelta(minutes=10)).isoformat(),
        "departure_latest": (now + timedelta(minutes=30)).isoformat(),
        "seats_requested": 1,
        "max_extra_minutes": 15,
    }
    created = await client_user_a.post("/api/v1/ride-requests", json=payload)
    req_id = created.json()["data"]["id"]

    # User B attempts to cancel User A's request
    cancel_res = await client_user_b.post(f"/api/v1/ride-requests/{req_id}/cancel")
    assert cancel_res.status_code == 403
    assert cancel_res.json()["error_code"] == "FORBIDDEN"


# ==============================================================================
# 6. Update Operations & Lifecycle Invariants (PATCH /ride-requests/{id})
# ==============================================================================


@pytest.mark.asyncio
async def test_patch_ride_request_success(
    client_user_a: AsyncClient,
) -> None:
    """Verify partial updates to seat count, detour minutes, and coordinates."""
    now = datetime.now(UTC)
    payload = {
        "pickup": {
            "latitude": 19.0760,
            "longitude": 72.8777,
            "label": "Original Pickup",
        },
        "destination": {
            "latitude": 18.9220,
            "longitude": 72.8258,
            "label": "Original Dest",
        },
        "departure_earliest": (now + timedelta(minutes=20)).isoformat(),
        "departure_latest": (now + timedelta(minutes=50)).isoformat(),
        "seats_requested": 1,
        "max_extra_minutes": 10,
    }
    created = await client_user_a.post("/api/v1/ride-requests", json=payload)
    req_id = created.json()["data"]["id"]

    # Apply updates
    patch_payload = {
        "seats_requested": 3,
        "max_extra_minutes": 30,
        "pickup": {
            "latitude": 19.1000,
            "longitude": 72.8500,
            "label": "Updated Pickup",
        },
    }
    res = await client_user_a.patch(
        f"/api/v1/ride-requests/{req_id}", json=patch_payload
    )
    assert res.status_code == 200

    data = res.json()["data"]
    assert data["seats_requested"] == 3
    assert data["max_extra_minutes"] == 30
    assert data["pickup"]["latitude"] == pytest.approx(19.1000)
    assert data["pickup"]["longitude"] == pytest.approx(72.8500)
    assert data["pickup"]["label"] == "Updated Pickup"
    # Unchanged fields remain intact
    assert data["destination"]["label"] == "Original Dest"


@pytest.mark.asyncio
async def test_patch_ride_request_lifecycle_invariant_not_active(
    client_user_a: AsyncClient,
) -> None:
    """Verify that cancelled ride requests cannot be updated."""
    now = datetime.now(UTC)
    payload = {
        "pickup": {"latitude": 19.0760, "longitude": 72.8777},
        "destination": {"latitude": 18.9220, "longitude": 72.8258},
        "departure_earliest": (now + timedelta(minutes=15)).isoformat(),
        "departure_latest": (now + timedelta(minutes=45)).isoformat(),
        "seats_requested": 1,
        "max_extra_minutes": 15,
    }
    created = await client_user_a.post("/api/v1/ride-requests", json=payload)
    req_id = created.json()["data"]["id"]

    # Cancel the request
    cancel_res = await client_user_a.post(f"/api/v1/ride-requests/{req_id}/cancel")
    assert cancel_res.status_code == 200

    # Attempt to update the cancelled request
    patch_res = await client_user_a.patch(
        f"/api/v1/ride-requests/{req_id}",
        json={"seats_requested": 2},
    )
    assert patch_res.status_code == 400
    assert patch_res.json()["error_code"] == "REQUEST_NOT_ACTIVE"


@pytest.mark.asyncio
async def test_patch_ride_request_invalid_departure_interval(
    client_user_a: AsyncClient,
) -> None:
    """Verify that updating departure window to an invalid interval is rejected."""
    now = datetime.now(UTC)
    payload = {
        "pickup": {"latitude": 19.0760, "longitude": 72.8777},
        "destination": {"latitude": 18.9220, "longitude": 72.8258},
        "departure_earliest": (now + timedelta(minutes=30)).isoformat(),
        "departure_latest": (now + timedelta(minutes=60)).isoformat(),
        "seats_requested": 1,
        "max_extra_minutes": 15,
    }
    created = await client_user_a.post("/api/v1/ride-requests", json=payload)
    req_id = created.json()["data"]["id"]

    # Attempt to set latest departure earlier than earliest
    patch_payload = {
        "departure_latest": (now + timedelta(minutes=10)).isoformat(),
    }
    patch_res = await client_user_a.patch(
        f"/api/v1/ride-requests/{req_id}",
        json=patch_payload,
    )
    assert patch_res.status_code == 400
    assert patch_res.json()["error_code"] == "INVALID_DEPARTURE_WINDOW"


@pytest.mark.asyncio
async def test_patch_ride_request_identical_coordinates(
    client_user_a: AsyncClient,
) -> None:
    """Verify that updating coordinates so that pickup equals destination is rejected."""
    now = datetime.now(UTC)
    payload = {
        "pickup": {"latitude": 19.0760, "longitude": 72.8777},
        "destination": {"latitude": 18.9220, "longitude": 72.8258},
        "departure_earliest": (now + timedelta(minutes=30)).isoformat(),
        "departure_latest": (now + timedelta(minutes=60)).isoformat(),
        "seats_requested": 1,
        "max_extra_minutes": 15,
    }
    created = await client_user_a.post("/api/v1/ride-requests", json=payload)
    req_id = created.json()["data"]["id"]

    # Update pickup to match existing destination (18.9220, 72.8258)
    patch_payload = {
        "pickup": {"latitude": 18.9220, "longitude": 72.8258},
    }
    patch_res = await client_user_a.patch(
        f"/api/v1/ride-requests/{req_id}",
        json=patch_payload,
    )
    assert patch_res.status_code == 400
    assert patch_res.json()["error_code"] == "INVALID_COORDINATES"


# ==============================================================================
# 7. Cancellation Operations & Lifecycle Transitions (POST /cancel)
# ==============================================================================


@pytest.mark.asyncio
async def test_cancel_ride_request_success(
    client_user_a: AsyncClient,
) -> None:
    """Verify cancellation transition from ACTIVE to CANCELLED."""
    now = datetime.now(UTC)
    payload = {
        "pickup": {"latitude": 19.0760, "longitude": 72.8777},
        "destination": {"latitude": 18.9220, "longitude": 72.8258},
        "departure_earliest": (now + timedelta(minutes=20)).isoformat(),
        "departure_latest": (now + timedelta(minutes=50)).isoformat(),
        "seats_requested": 1,
        "max_extra_minutes": 15,
    }
    created = await client_user_a.post("/api/v1/ride-requests", json=payload)
    req_id = created.json()["data"]["id"]

    cancel_res = await client_user_a.post(f"/api/v1/ride-requests/{req_id}/cancel")
    assert cancel_res.status_code == 200
    data = cancel_res.json()["data"]
    assert data["status"] == "CANCELLED"

    # Confirm status persisted on GET
    get_res = await client_user_a.get(f"/api/v1/ride-requests/{req_id}")
    assert get_res.json()["data"]["status"] == "CANCELLED"


@pytest.mark.asyncio
async def test_cancel_already_cancelled_request_rejected(
    client_user_a: AsyncClient,
) -> None:
    """Verify that cancelling an already CANCELLED request returns 400."""
    now = datetime.now(UTC)
    payload = {
        "pickup": {"latitude": 19.0760, "longitude": 72.8777},
        "destination": {"latitude": 18.9220, "longitude": 72.8258},
        "departure_earliest": (now + timedelta(minutes=20)).isoformat(),
        "departure_latest": (now + timedelta(minutes=50)).isoformat(),
        "seats_requested": 1,
        "max_extra_minutes": 15,
    }
    created = await client_user_a.post("/api/v1/ride-requests", json=payload)
    req_id = created.json()["data"]["id"]

    # First cancel succeeds
    c1 = await client_user_a.post(f"/api/v1/ride-requests/{req_id}/cancel")
    assert c1.status_code == 200

    # Second cancel rejected with 400 INVALID_STATE_TRANSITION
    c2 = await client_user_a.post(f"/api/v1/ride-requests/{req_id}/cancel")
    assert c2.status_code == 400
    assert c2.json()["error_code"] == "INVALID_STATE_TRANSITION"


@pytest.mark.asyncio
async def test_cancel_non_existent_request(
    client_user_a: AsyncClient,
) -> None:
    """Verify that cancelling a non-existent request returns 404."""
    random_id = uuid.uuid4()
    res = await client_user_a.post(f"/api/v1/ride-requests/{random_id}/cancel")
    assert res.status_code == 404
    assert res.json()["error_code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_delete_ride_request_alias(
    client_user_a: AsyncClient,
) -> None:
    """Verify that DELETE /ride-requests/{id} cancels an ACTIVE request."""
    now = datetime.now(UTC)
    payload = {
        "pickup": {"latitude": 19.0760, "longitude": 72.8777},
        "destination": {"latitude": 18.9220, "longitude": 72.8258},
        "departure_earliest": (now + timedelta(minutes=25)).isoformat(),
        "departure_latest": (now + timedelta(minutes=55)).isoformat(),
        "seats_requested": 1,
        "max_extra_minutes": 15,
    }
    created = await client_user_a.post("/api/v1/ride-requests", json=payload)
    req_id = created.json()["data"]["id"]

    delete_res = await client_user_a.delete(f"/api/v1/ride-requests/{req_id}")
    assert delete_res.status_code == 200
    assert delete_res.json()["data"]["status"] == "CANCELLED"

    get_res = await client_user_a.get(f"/api/v1/ride-requests/{req_id}")
    assert get_res.json()["data"]["status"] == "CANCELLED"
