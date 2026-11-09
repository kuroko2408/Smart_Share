"""Comprehensive integration tests for Smart Share Phase 6A: Bilateral Consent Workflow.

Verifies all 9 mandatory requirements:
1. Neither passenger has consented.
2. Only passenger A has consented.
3. Only passenger B has consented.
4. Both passengers have consented (exact disclosure revealed, sum conservation, driver invariant).
5. Consent withdrawal / revocation (immediately suppresses exact disclosure for both riders).
6. Unauthorized and invalid access attempts (cross-user 403, unknown proposal 404, unauthenticated 401, version conflict 409).
7. Repeated and duplicate consent requests (idempotency, no duplicate database rows).
8. Unconsented responses do not leak private fields (co-passenger contribution, solo baseline, private savings).
9. Consented responses do not expose more than DEC-013 permits (only co-passenger contribution authorized; baselines & savings remain redacted).
"""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from jwt import PyJWKClient
from jwt.algorithms import RSAAlgorithm
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_jwt_verifier
from app.core.database import get_db
from app.core.security import SupabaseJWTVerifier
from app.fares.disclosure import CONSENT_NOTICE, CONSENT_TEXT_VERSION
from app.main import create_application
from app.models import Base
from app.models.match_disclosure_consent import MatchDisclosureConsentEvent
from app.schemas.auth import AuthUser


@pytest.fixture
def rsa_key_pair() -> tuple[Any, Any, dict[str, Any]]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    jwk_dict = json_jwk = RSAAlgorithm.to_jwk(public_key, as_dict=True)
    json_jwk["kid"] = "test-key-id"
    json_jwk["alg"] = "RS256"
    json_jwk["use"] = "sig"
    return private_key, public_key, jwk_dict


@pytest.fixture
def auth_verifier(rsa_key_pair: tuple[Any, Any, dict[str, Any]]) -> SupabaseJWTVerifier:
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
    email: str,
    role: str = "authenticated",
    full_name: str | None = None,
) -> str:
    now = int(time.time())
    user_metadata = {"full_name": full_name} if full_name else {}
    payload = {
        "sub": str(user_id),
        "email": email,
        "aud": "authenticated",
        "iss": "https://test.supabase.co/auth/v1",
        "role": role,
        "iat": now,
        "exp": now + 3600,
        "user_metadata": user_metadata,
        "app_metadata": {"provider": "email"},
    }
    return jwt.encode(
        payload,
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key-id"},
    )


@pytest.fixture
async def consent_test_engine() -> AsyncGenerator[AsyncEngine, None]:
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
        dbapi_connection.create_function("ST_GeogFromText", 1, lambda val: val)
        dbapi_connection.create_function("AsBinary", 1, lambda val: val)
        dbapi_connection.create_function(
            "ST_Equals", 2, lambda a, b: 1 if a == b else 0
        )
        dbapi_connection.create_function(
            "char_length", 1, lambda s: len(s) if s is not None else 0
        )
        dbapi_connection.create_function(
            "gen_random_uuid", 0, lambda: "00000000-0000-0000-0000-000000000001"
        )
        dbapi_connection.create_function("now", 0, lambda: "2026-11-09T00:00:00")

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
    return AuthUser(
        id=uuid.uuid4(),
        email="commuter_a@smartshare.local",
        role="authenticated",
        app_metadata={"provider": "email"},
        user_metadata={"full_name": "Alice Commuter"},
    )


@pytest.fixture
def user_b() -> AuthUser:
    return AuthUser(
        id=uuid.uuid4(),
        email="commuter_b@smartshare.local",
        role="authenticated",
        app_metadata={"provider": "email"},
        user_metadata={"full_name": "Bob Commuter"},
    )


@pytest.fixture
def user_c() -> AuthUser:
    return AuthUser(
        id=uuid.uuid4(),
        email="commuter_c@smartshare.local",
        role="authenticated",
        app_metadata={"provider": "email"},
        user_metadata={"full_name": "Charlie Thirdparty"},
    )


@pytest.fixture
def consent_app(
    consent_test_engine: AsyncEngine, auth_verifier: SupabaseJWTVerifier
) -> FastAPI:
    app = create_application()
    session_factory = async_sessionmaker(
        bind=consent_test_engine, class_=AsyncSession, expire_on_commit=False
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
def client_a(
    consent_app: FastAPI,
    user_a: AuthUser,
    rsa_key_pair: tuple[Any, Any, dict[str, Any]],
) -> AsyncClient:
    private_key, _, _ = rsa_key_pair
    token = generate_test_token(
        private_key,
        user_id=user_a.id,
        email=user_a.email,
        full_name=user_a.user_metadata.get("full_name"),
    )
    return AsyncClient(
        transport=ASGITransport(app=consent_app, raise_app_exceptions=False),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    )


@pytest.fixture
def client_b(
    consent_app: FastAPI,
    user_b: AuthUser,
    rsa_key_pair: tuple[Any, Any, dict[str, Any]],
) -> AsyncClient:
    private_key, _, _ = rsa_key_pair
    token = generate_test_token(
        private_key,
        user_id=user_b.id,
        email=user_b.email,
        full_name=user_b.user_metadata.get("full_name"),
    )
    return AsyncClient(
        transport=ASGITransport(app=consent_app, raise_app_exceptions=False),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    )


@pytest.fixture
def client_c(
    consent_app: FastAPI,
    user_c: AuthUser,
    rsa_key_pair: tuple[Any, Any, dict[str, Any]],
) -> AsyncClient:
    private_key, _, _ = rsa_key_pair
    token = generate_test_token(
        private_key,
        user_id=user_c.id,
        email=user_c.email,
        full_name=user_c.user_metadata.get("full_name"),
    )
    return AsyncClient(
        transport=ASGITransport(app=consent_app, raise_app_exceptions=False),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    )


@pytest.fixture
def unauthed_client(consent_app: FastAPI) -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=consent_app, raise_app_exceptions=False),
        base_url="http://test",
    )


async def _setup_paired_ride_requests(
    client_a: AsyncClient,
    client_b: AsyncClient,
    user_a: AuthUser,
    user_b: AuthUser,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[str, str, str]:
    """Create two active requests for users A and B, wiring mutual candidate discovery."""
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
    payload_b = {
        "pickup": {"latitude": 19.0660, "longitude": 72.8690, "label": "BKC One"},
        "destination": {
            "latitude": 19.1170,
            "longitude": 72.9050,
            "label": "Powai Galleria",
        },
        "departure_earliest": (now + timedelta(hours=1)).isoformat(),
        "departure_latest": (now + timedelta(hours=2)).isoformat(),
        "seats_requested": 1,
        "max_extra_minutes": 20,
    }
    res_a = await client_a.post("/api/v1/ride-requests", json=payload_a)
    assert res_a.status_code == 201
    req_a_id = res_a.json()["data"]["id"]

    res_b = await client_b.post("/api/v1/ride-requests", json=payload_b)
    assert res_b.status_code == 201
    req_b_id = res_b.json()["data"]["id"]

    cand_b = {
        "candidate_id": uuid.UUID(req_b_id),
        "candidate_user_id": user_b.id,
        "owner_name": "Bob Commuter",
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
    cand_a = {
        "candidate_id": uuid.UUID(req_a_id),
        "candidate_user_id": user_a.id,
        "owner_name": "Alice Commuter",
        "pickup_location": "POINT(72.8687 19.0657)",
        "destination": "POINT(72.9060 19.1176)",
        "pickup_label": "BKC Maker Maxity",
        "destination_label": "Powai Hiranandani",
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

    async def mock_discover(db, request_id=None, **kwargs):
        if str(request_id) == req_a_id:
            return [cand_b]
        elif str(request_id) == req_b_id:
            return [cand_a]
        return []

    monkeypatch.setattr(matching_service, "discover_candidates", mock_discover)

    # Trigger match discovery for A to get the proposal
    post_a = await client_a.post(f"/api/v1/ride-requests/{req_a_id}/matches")
    assert post_a.status_code == 200
    proposal_id = post_a.json()["data"]["proposals"][0]["proposal_id"]

    return req_a_id, req_b_id, proposal_id


@pytest.mark.asyncio
async def test_scenario_1_neither_passenger_consented(
    client_a: AsyncClient,
    client_b: AsyncClient,
    user_a: AuthUser,
    user_b: AuthUser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """1. Neither passenger has consented: co-passenger contribution is withheld from both viewers."""
    req_a_id, req_b_id, proposal_id = await _setup_paired_ride_requests(
        client_a, client_b, user_a, user_b, monkeypatch
    )

    # Check via proposal detail endpoint
    res_a = await client_a.get(f"/api/v1/matches/{proposal_id}?request_id={req_a_id}")
    assert res_a.status_code == 200
    prop_a = res_a.json()["data"]

    disc_a = prop_a["fare_allocation_disclosure"]
    assert disc_a["your_consent_active"] is False
    assert disc_a["co_passenger_consent_active"] is False
    assert disc_a["exact_disclosure_available"] is False
    assert disc_a["allocation"] is None
    assert disc_a["consent_notice"] == CONSENT_NOTICE
    assert disc_a["consent_text_version"] == CONSENT_TEXT_VERSION

    # Check fare estimate schema
    fare_a = prop_a["fare_estimate"]
    assert fare_a["your_allocated_fare"]["estimate"] > 0
    assert fare_a["your_savings"]["estimate"] > 0
    assert fare_a["co_passenger_contribution"] is None

    # Check standalone consent status endpoint
    status_a = await client_a.get(
        f"/api/v1/matches/{proposal_id}/disclosure-consent?request_id={req_a_id}"
    )
    assert status_a.status_code == 200
    assert status_a.json()["data"]["your_consent_active"] is False
    assert status_a.json()["data"]["co_passenger_consent_active"] is False
    assert status_a.json()["data"]["exact_disclosure_available"] is False


@pytest.mark.asyncio
async def test_scenario_2_only_passenger_a_consented(
    client_a: AsyncClient,
    client_b: AsyncClient,
    user_a: AuthUser,
    user_b: AuthUser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """2. Only passenger A has consented: co-passenger contribution remains withheld from both."""
    req_a_id, req_b_id, proposal_id = await _setup_paired_ride_requests(
        client_a, client_b, user_a, user_b, monkeypatch
    )

    # Passenger A submits affirmative consent
    consent_payload = {
        "consent_text_version": CONSENT_TEXT_VERSION,
        "disclosure_mode": "EXACT",
        "action": "GRANTED",
    }
    grant_res = await client_a.post(
        f"/api/v1/matches/{proposal_id}/disclosure-consent?request_id={req_a_id}",
        json=consent_payload,
    )
    assert grant_res.status_code == 200
    grant_data = grant_res.json()["data"]
    assert grant_data["your_consent_active"] is True
    assert grant_data["co_passenger_consent_active"] is False
    assert grant_data["exact_disclosure_available"] is False
    assert grant_data["allocation"] is None

    # Passenger A reads proposal: their consent is recorded, other is pending, amounts withheld
    detail_a = await client_a.get(
        f"/api/v1/matches/{proposal_id}?request_id={req_a_id}"
    )
    assert detail_a.status_code == 200
    prop_a = detail_a.json()["data"]
    assert prop_a["fare_allocation_disclosure"]["your_consent_active"] is True
    assert prop_a["fare_allocation_disclosure"]["co_passenger_consent_active"] is False
    assert prop_a["fare_allocation_disclosure"]["exact_disclosure_available"] is False
    assert prop_a["fare_estimate"]["co_passenger_contribution"] is None

    # Passenger B reads proposal: other passenger consented, but B has not; amounts withheld
    detail_b = await client_b.get(
        f"/api/v1/matches/{proposal_id}?request_id={req_b_id}"
    )
    assert detail_b.status_code == 200
    prop_b = detail_b.json()["data"]
    assert prop_b["fare_allocation_disclosure"]["your_consent_active"] is False
    assert prop_b["fare_allocation_disclosure"]["co_passenger_consent_active"] is True
    assert prop_b["fare_allocation_disclosure"]["exact_disclosure_available"] is False
    assert prop_b["fare_allocation_disclosure"]["allocation"] is None
    assert prop_b["fare_estimate"]["co_passenger_contribution"] is None


@pytest.mark.asyncio
async def test_scenario_3_only_passenger_b_consented(
    client_a: AsyncClient,
    client_b: AsyncClient,
    user_a: AuthUser,
    user_b: AuthUser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """3. Only passenger B has consented: symmetric check from Bob's perspective."""
    req_a_id, req_b_id, proposal_id = await _setup_paired_ride_requests(
        client_a, client_b, user_a, user_b, monkeypatch
    )

    # Bob grants consent
    consent_payload = {
        "consent_text_version": CONSENT_TEXT_VERSION,
        "disclosure_mode": "EXACT",
    }
    grant_b = await client_b.post(
        f"/api/v1/matches/{proposal_id}/disclosure-consent?request_id={req_b_id}",
        json=consent_payload,
    )
    assert grant_b.status_code == 200
    assert grant_b.json()["data"]["your_consent_active"] is True
    assert grant_b.json()["data"]["co_passenger_consent_active"] is False
    assert grant_b.json()["data"]["exact_disclosure_available"] is False

    # Alice queries: sees Bob consented, exact amounts remain hidden
    detail_a = await client_a.get(
        f"/api/v1/matches/{proposal_id}?request_id={req_a_id}"
    )
    assert detail_a.status_code == 200
    prop_a = detail_a.json()["data"]
    assert prop_a["fare_allocation_disclosure"]["your_consent_active"] is False
    assert prop_a["fare_allocation_disclosure"]["co_passenger_consent_active"] is True
    assert prop_a["fare_allocation_disclosure"]["exact_disclosure_available"] is False
    assert prop_a["fare_estimate"]["co_passenger_contribution"] is None


@pytest.mark.asyncio
async def test_scenario_4_both_passengers_consented(
    client_a: AsyncClient,
    client_b: AsyncClient,
    user_a: AuthUser,
    user_b: AuthUser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """4. Both passengers consented: exact disclosure available, sum conservation, driver gross invariant."""
    req_a_id, req_b_id, proposal_id = await _setup_paired_ride_requests(
        client_a, client_b, user_a, user_b, monkeypatch
    )

    consent_payload = {
        "consent_text_version": CONSENT_TEXT_VERSION,
        "disclosure_mode": "EXACT",
    }
    # Alice grants
    await client_a.post(
        f"/api/v1/matches/{proposal_id}/disclosure-consent?request_id={req_a_id}",
        json=consent_payload,
    )
    # Bob grants
    res_b = await client_b.post(
        f"/api/v1/matches/{proposal_id}/disclosure-consent?request_id={req_b_id}",
        json=consent_payload,
    )
    assert res_b.status_code == 200
    data_b = res_b.json()["data"]
    assert data_b["your_consent_active"] is True
    assert data_b["co_passenger_consent_active"] is True
    assert data_b["exact_disclosure_available"] is True
    assert data_b["allocation"] is not None

    # Check Alice's view
    detail_a = await client_a.get(
        f"/api/v1/matches/{proposal_id}?request_id={req_a_id}"
    )
    prop_a = detail_a.json()["data"]
    alloc_a = prop_a["fare_allocation_disclosure"]["allocation"]
    assert alloc_a is not None
    assert prop_a["fare_estimate"]["co_passenger_contribution"] is not None

    # Check Bob's view
    detail_b = await client_b.get(
        f"/api/v1/matches/{proposal_id}?request_id={req_b_id}"
    )
    prop_b = detail_b.json()["data"]
    alloc_b = prop_b["fare_allocation_disclosure"]["allocation"]
    assert alloc_b is not None
    assert prop_b["fare_estimate"]["co_passenger_contribution"] is not None

    # Verify mathematical and financial invariants
    shared_total = alloc_a["shared_total"]
    assert alloc_a["your_contribution"] + alloc_a[
        "co_passenger_contribution"
    ] == pytest.approx(shared_total, abs=0.01)
    assert alloc_a["shared_total_paise"] == (
        alloc_a["your_contribution_paise"] + alloc_a["co_passenger_contribution_paise"]
    )
    # Cross-passenger consistency
    assert (
        alloc_a["your_contribution_paise"] == alloc_b["co_passenger_contribution_paise"]
    )
    assert (
        alloc_a["co_passenger_contribution_paise"] == alloc_b["your_contribution_paise"]
    )
    # Driver gross fare invariance: shared_journey estimate is unchanged
    assert prop_a["fare_estimate"]["shared_journey"]["estimate"] == shared_total


@pytest.mark.asyncio
async def test_scenario_5_consent_withdrawal_and_revocation(
    client_a: AsyncClient,
    client_b: AsyncClient,
    user_a: AuthUser,
    user_b: AuthUser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """5. Either passenger withdraws consent: immediately revokes exact disclosure for both."""
    req_a_id, req_b_id, proposal_id = await _setup_paired_ride_requests(
        client_a, client_b, user_a, user_b, monkeypatch
    )

    consent_payload = {
        "consent_text_version": CONSENT_TEXT_VERSION,
        "disclosure_mode": "EXACT",
    }
    # Both grant
    await client_a.post(
        f"/api/v1/matches/{proposal_id}/disclosure-consent?request_id={req_a_id}",
        json=consent_payload,
    )
    await client_b.post(
        f"/api/v1/matches/{proposal_id}/disclosure-consent?request_id={req_b_id}",
        json=consent_payload,
    )

    # Alice withdraws consent via DELETE
    revoke_res = await client_a.delete(
        f"/api/v1/matches/{proposal_id}/disclosure-consent?request_id={req_a_id}"
    )
    assert revoke_res.status_code == 200
    revoke_data = revoke_res.json()["data"]
    assert revoke_data["your_consent_active"] is False
    assert revoke_data["co_passenger_consent_active"] is True
    assert revoke_data["exact_disclosure_available"] is False
    assert revoke_data["allocation"] is None

    # Alice verifies proposal: exact amounts hidden again
    detail_a = await client_a.get(
        f"/api/v1/matches/{proposal_id}?request_id={req_a_id}"
    )
    prop_a = detail_a.json()["data"]
    assert prop_a["fare_allocation_disclosure"]["exact_disclosure_available"] is False
    assert prop_a["fare_allocation_disclosure"]["allocation"] is None
    assert prop_a["fare_estimate"]["co_passenger_contribution"] is None

    # Bob verifies proposal: exact amounts hidden from Bob as well
    detail_b = await client_b.get(
        f"/api/v1/matches/{proposal_id}?request_id={req_b_id}"
    )
    prop_b = detail_b.json()["data"]
    assert prop_b["fare_allocation_disclosure"]["exact_disclosure_available"] is False
    assert prop_b["fare_allocation_disclosure"]["allocation"] is None
    assert prop_b["fare_estimate"]["co_passenger_contribution"] is None

    # Test re-granting consent via POST with action="GRANTED"
    regrant_res = await client_a.post(
        f"/api/v1/matches/{proposal_id}/disclosure-consent?request_id={req_a_id}",
        json={
            "consent_text_version": CONSENT_TEXT_VERSION,
            "disclosure_mode": "EXACT",
            "action": "GRANTED",
        },
    )
    assert regrant_res.status_code == 200
    assert regrant_res.json()["data"]["exact_disclosure_available"] is True


@pytest.mark.asyncio
async def test_scenario_6_unauthorized_and_invalid_access(
    client_a: AsyncClient,
    client_b: AsyncClient,
    client_c: AsyncClient,
    unauthed_client: AsyncClient,
    user_a: AuthUser,
    user_b: AuthUser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """6. Unauthorized and non-participant access attempts fail strictly."""
    req_a_id, req_b_id, proposal_id = await _setup_paired_ride_requests(
        client_a, client_b, user_a, user_b, monkeypatch
    )
    consent_payload = {
        "consent_text_version": CONSENT_TEXT_VERSION,
        "disclosure_mode": "EXACT",
    }

    # 1. Unauthenticated requests fail with 401
    unauth_get = await unauthed_client.get(
        f"/api/v1/matches/{proposal_id}/disclosure-consent?request_id={req_a_id}"
    )
    assert unauth_get.status_code == 401

    unauth_post = await unauthed_client.post(
        f"/api/v1/matches/{proposal_id}/disclosure-consent?request_id={req_a_id}",
        json=consent_payload,
    )
    assert unauth_post.status_code == 401

    unauth_del = await unauthed_client.delete(
        f"/api/v1/matches/{proposal_id}/disclosure-consent?request_id={req_a_id}"
    )
    assert unauth_del.status_code == 401

    # 2. Bob tries to act using Alice's request_id -> 403 Forbidden
    cross_post = await client_b.post(
        f"/api/v1/matches/{proposal_id}/disclosure-consent?request_id={req_a_id}",
        json=consent_payload,
    )
    assert cross_post.status_code == 403

    cross_del = await client_b.delete(
        f"/api/v1/matches/{proposal_id}/disclosure-consent?request_id={req_a_id}"
    )
    assert cross_del.status_code == 403

    # 3. Third-party commuter Charlie tries to access -> 404 or 403
    random_req = uuid.uuid4()
    charlie_res = await client_c.get(
        f"/api/v1/matches/{proposal_id}/disclosure-consent?request_id={random_req}"
    )
    assert charlie_res.status_code in {403, 404}

    # 4. Outdated consent notice version fails with 409 Conflict
    outdated_post = await client_a.post(
        f"/api/v1/matches/{proposal_id}/disclosure-consent?request_id={req_a_id}",
        json={"consent_text_version": "OLD-VERSION-2025", "disclosure_mode": "EXACT"},
    )
    assert outdated_post.status_code == 409

    # 5. Invalid disclosure mode fails with 422 Unprocessable Entity
    invalid_mode = await client_a.post(
        f"/api/v1/matches/{proposal_id}/disclosure-consent?request_id={req_a_id}",
        json={
            "consent_text_version": CONSENT_TEXT_VERSION,
            "disclosure_mode": "ESTIMATE",
        },
    )
    assert invalid_mode.status_code == 422


@pytest.mark.asyncio
async def test_scenario_7_repeated_and_duplicate_consent_idempotency(
    client_a: AsyncClient,
    client_b: AsyncClient,
    user_a: AuthUser,
    user_b: AuthUser,
    consent_test_engine: AsyncEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """7. Repeated or duplicate consent submissions are idempotent and do not duplicate rows."""
    req_a_id, req_b_id, proposal_id = await _setup_paired_ride_requests(
        client_a, client_b, user_a, user_b, monkeypatch
    )
    consent_payload = {
        "consent_text_version": CONSENT_TEXT_VERSION,
        "disclosure_mode": "EXACT",
    }

    # Grant consent 3 times in a row
    for _ in range(3):
        res = await client_a.post(
            f"/api/v1/matches/{proposal_id}/disclosure-consent?request_id={req_a_id}",
            json=consent_payload,
        )
        assert res.status_code == 200
        assert res.json()["data"]["your_consent_active"] is True

    # Check database: only exactly 1 event should be recorded
    session_factory = async_sessionmaker(bind=consent_test_engine, class_=AsyncSession)
    async with session_factory() as session:
        events = (
            await session.scalars(
                select(MatchDisclosureConsentEvent).where(
                    MatchDisclosureConsentEvent.proposal_id == uuid.UUID(proposal_id),
                    MatchDisclosureConsentEvent.participant_request_id
                    == uuid.UUID(req_a_id),
                )
            )
        ).all()
        assert len(events) == 1
        assert events[0].action == "GRANTED"

    # Revoke consent twice in a row
    for _ in range(2):
        del_res = await client_a.delete(
            f"/api/v1/matches/{proposal_id}/disclosure-consent?request_id={req_a_id}"
        )
        assert del_res.status_code == 200
        assert del_res.json()["data"]["your_consent_active"] is False

    # Check database: exactly 1 GRANTED + 1 REVOKED = 2 events total
    async with session_factory() as session:
        events_after = (
            await session.scalars(
                select(MatchDisclosureConsentEvent)
                .where(
                    MatchDisclosureConsentEvent.proposal_id == uuid.UUID(proposal_id),
                    MatchDisclosureConsentEvent.participant_request_id
                    == uuid.UUID(req_a_id),
                )
                .order_by(MatchDisclosureConsentEvent.event_id.asc())
            )
        ).all()
        assert len(events_after) == 2
        assert events_after[0].action == "GRANTED"
        assert events_after[1].action == "REVOKED"


@pytest.mark.asyncio
async def test_scenario_8_unconsented_privacy_leak_prevention(
    client_a: AsyncClient,
    client_b: AsyncClient,
    user_a: AuthUser,
    user_b: AuthUser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """8. Unconsented responses do not leak private fields anywhere in JSON."""
    req_a_id, req_b_id, proposal_id = await _setup_paired_ride_requests(
        client_a, client_b, user_a, user_b, monkeypatch
    )

    detail_res = await client_a.get(
        f"/api/v1/matches/{proposal_id}?request_id={req_a_id}"
    )
    raw_text = detail_res.text.lower()

    forbidden_tokens = [
        "co_passenger_contribution_paise",
        "co_passenger_solo",
        "candidate_solo",
        "co_passenger_savings",
    ]
    for token in forbidden_tokens:
        assert token not in raw_text, (
            f"Forbidden privacy token '{token}' leaked in unconsented response!"
        )

    data = detail_res.json()["data"]
    assert data["fare_estimate"]["co_passenger_contribution"] is None
    assert data["fare_allocation_disclosure"]["allocation"] is None


@pytest.mark.asyncio
async def test_scenario_9_consented_strict_privacy_boundary(
    client_a: AsyncClient,
    client_b: AsyncClient,
    user_a: AuthUser,
    user_b: AuthUser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """9. Consented responses expose ONLY DEC-013 authorized fields; solo baselines & savings remain strictly hidden."""
    req_a_id, req_b_id, proposal_id = await _setup_paired_ride_requests(
        client_a, client_b, user_a, user_b, monkeypatch
    )
    consent_payload = {
        "consent_text_version": CONSENT_TEXT_VERSION,
        "disclosure_mode": "EXACT",
    }
    await client_a.post(
        f"/api/v1/matches/{proposal_id}/disclosure-consent?request_id={req_a_id}",
        json=consent_payload,
    )
    await client_b.post(
        f"/api/v1/matches/{proposal_id}/disclosure-consent?request_id={req_b_id}",
        json=consent_payload,
    )

    detail_res = await client_a.get(
        f"/api/v1/matches/{proposal_id}?request_id={req_a_id}"
    )
    raw_text = detail_res.text.lower()

    # Co-passenger contribution IS authorized and present
    assert "co_passenger_contribution" in raw_text
    data = detail_res.json()["data"]
    assert data["fare_estimate"]["co_passenger_contribution"] is not None

    # BUT co-passenger solo baseline and private savings remain STRICTLY forbidden
    forbidden_tokens = [
        "co_passenger_solo_baseline",
        "co_passenger_solo_fare",
        "candidate_solo_baseline",
        "co_passenger_savings",
    ]
    for token in forbidden_tokens:
        assert token not in raw_text, (
            f"Forbidden privacy token '{token}' leaked in consented response!"
        )

    # Ensure only requester's passenger metrics are returned
    assert list(data["passenger_metrics"]) == [req_a_id]
