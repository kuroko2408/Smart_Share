"""Tests for Profile and RideRequest SQLAlchemy models and database integration."""

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from geoalchemy2 import Geography
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import selectinload
from sqlalchemy.pool import StaticPool
from sqlalchemy.schema import CheckConstraint

from app.models.base import Base
from app.models.profile import Profile, auth_users
from app.models.ride_request import RideRequest, RideRequestStatus


# Register SQLite compilers for testing environment
@compiles(Geography, "sqlite")
def _compile_geography_sqlite(element: Any, compiler: Any, **kw: Any) -> str:
    return "TEXT"


@compiles(CheckConstraint, "sqlite")
def _compile_check_constraint_sqlite(element: Any, compiler: Any, **kw: Any) -> str:
    text_sql = compiler.sql_compiler.process(
        element.sqltext, include_table=False, literal_binds=True
    )
    text_sql = text_sql.replace("::geometry", "")
    preamble = compiler.define_constraint_preamble(element, **kw)
    return f"{preamble}CHECK ({text_sql})"


@pytest.fixture
async def db_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create an isolated in-memory SQLite engine with foreign keys enabled."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def setup_sqlite_connection(dbapi_connection: Any, _: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute("ATTACH DATABASE ':memory:' AS auth;")
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS auth.users (id TEXT PRIMARY KEY, email TEXT);"
        )
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
            "gen_random_uuid", 0, lambda: str(uuid.uuid4())
        )
        dbapi_connection.create_function(
            "now", 0, lambda: datetime.now(UTC).isoformat()
        )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session bound to the test engine."""
    session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session


def test_profile_model_instantiation() -> None:
    """Verify profile instantiation, default values, and onboarding property."""
    user_id = uuid.uuid4()
    profile = Profile(id=user_id)

    assert profile.id == user_id
    assert profile.display_name == ""
    assert profile.avatar_url is None
    assert profile.is_onboarding_completed is False
    assert "<Profile id=" in repr(profile)

    # Set display name and verify onboarding is marked complete
    profile.display_name = "Asta Developer"
    profile.avatar_url = "https://example.com/avatar.png"
    assert profile.is_onboarding_completed is True
    assert "Asta Developer" in repr(profile)


def test_profile_onboarding_whitespace_handling() -> None:
    """Verify that a whitespace-only display name does not satisfy onboarding."""
    profile = Profile(id=uuid.uuid4(), display_name="   ")
    assert profile.is_onboarding_completed is False


def test_ride_request_model_instantiation() -> None:
    """Verify ride request model attributes, default values, and status enum."""
    req_id = uuid.uuid4()
    user_id = uuid.uuid4()
    now = datetime.now(UTC)
    earliest = now + timedelta(minutes=10)
    latest = now + timedelta(minutes=30)

    request = RideRequest(
        id=req_id,
        user_id=user_id,
        pickup_location="POINT(72.8777 19.0760)",
        destination="POINT(72.8258 18.9220)",
        pickup_label="Bandra Terminus",
        destination_label="Gateway of India",
        departure_earliest=earliest,
        departure_latest=latest,
    )

    assert request.id == req_id
    assert request.user_id == user_id
    assert request.seats_requested == 1
    assert request.max_extra_minutes == 15
    assert request.status == RideRequestStatus.ACTIVE.value
    assert request.expires_at is None
    assert request.pickup_label == "Bandra Terminus"
    assert request.destination_label == "Gateway of India"
    assert "<RideRequest" in repr(request)
    assert "ACTIVE" in repr(request)


def test_ride_request_status_enum_values() -> None:
    """Verify that RideRequestStatus contains all approved lifecycle states."""
    expected_statuses = {"ACTIVE", "MATCHED", "CANCELLED", "EXPIRED", "COMPLETED"}
    actual_statuses = {status.value for status in RideRequestStatus}
    assert actual_statuses == expected_statuses


def test_model_relationship_linking() -> None:
    """Verify bidirectional relationship between Profile and RideRequest in memory."""
    user_id = uuid.uuid4()
    profile = Profile(id=user_id, display_name="Commuter One")

    now = datetime.now(UTC)
    request1 = RideRequest(
        id=uuid.uuid4(),
        user_id=profile.id,
        pickup_location="POINT(72.8777 19.0760)",
        destination="POINT(72.8258 18.9220)",
        departure_earliest=now + timedelta(minutes=5),
        departure_latest=now + timedelta(minutes=25),
        seats_requested=2,
        user=profile,
    )

    request2 = RideRequest(
        id=uuid.uuid4(),
        user_id=profile.id,
        pickup_location="POINT(72.8300 19.1000)",
        destination="POINT(72.8500 18.9500)",
        departure_earliest=now + timedelta(hours=1),
        departure_latest=now + timedelta(hours=1, minutes=30),
        seats_requested=1,
    )
    profile.ride_requests.append(request2)

    assert len(profile.ride_requests) == 2
    assert request1.user == profile
    assert request2.user == profile
    assert request2.user_id == profile.id
    assert request1.user_id == profile.id


# ==============================================================================
# Database Integration Tests: Real Persistence, Cascades, and Constraints
# ==============================================================================


@pytest.mark.asyncio
async def test_db_persistence_and_relationships(db_session: AsyncSession) -> None:
    """Verify database persistence and relationship loading across tables."""
    user_id = uuid.uuid4()
    # 1. Insert into auth.users stub
    await db_session.execute(auth_users.insert().values(id=user_id))

    # 2. Insert Profile
    profile = Profile(id=user_id, display_name="Database User")
    db_session.add(profile)
    await db_session.commit()

    # 3. Insert RideRequests associated with profile
    now = datetime.now(UTC)
    req1 = RideRequest(
        id=uuid.uuid4(),
        user_id=user_id,
        pickup_location="POINT(72.8777 19.0760)",
        destination="POINT(72.8258 18.9220)",
        departure_earliest=now + timedelta(minutes=15),
        departure_latest=now + timedelta(minutes=45),
        seats_requested=2,
        max_extra_minutes=20,
    )
    req2 = RideRequest(
        id=uuid.uuid4(),
        user_id=user_id,
        pickup_location="POINT(72.8500 19.0500)",
        destination="POINT(72.8100 18.9100)",
        departure_earliest=now + timedelta(hours=2),
        departure_latest=now + timedelta(hours=2, minutes=30),
        seats_requested=1,
        max_extra_minutes=10,
    )
    db_session.add_all([req1, req2])
    await db_session.commit()

    # 4. Query back with relationship eager loading
    stmt = (
        select(Profile)
        .where(Profile.id == user_id)
        .options(selectinload(Profile.ride_requests))
    )
    result = await db_session.execute(stmt)
    fetched_profile = result.scalar_one()

    assert fetched_profile.display_name == "Database User"
    assert len(fetched_profile.ride_requests) == 2
    req_ids = {r.id for r in fetched_profile.ride_requests}
    assert req1.id in req_ids
    assert req2.id in req_ids


@pytest.mark.asyncio
async def test_db_foreign_key_cascade_deletion(db_session: AsyncSession) -> None:
    """Verify that deleting a Profile cascades to delete its associated RideRequests.

    Note: In PostgreSQL (production/Supabase), auth.users cascades to profiles and
    ride_requests natively. In SQLite in-memory tests, cross-schema foreign keys
    (across ATTACH DATABASE) are not supported by SQLite engine, but intra-database
    cascades from profiles -> ride_requests are fully enforced by SQLite.
    """
    user_id = uuid.uuid4()
    req_id = uuid.uuid4()
    now = datetime.now(UTC)

    # 1. Seed auth user, profile, and ride request
    await db_session.execute(auth_users.insert().values(id=user_id))
    profile = Profile(id=user_id, display_name="Cascade Target")
    db_session.add(profile)
    await db_session.flush()

    ride_req = RideRequest(
        id=req_id,
        user_id=user_id,
        pickup_location="POINT(72.8777 19.0760)",
        destination="POINT(72.8258 18.9220)",
        departure_earliest=now + timedelta(minutes=10),
        departure_latest=now + timedelta(minutes=30),
    )
    db_session.add(ride_req)
    await db_session.commit()

    # Verify rows exist
    prof_res = await db_session.execute(select(Profile).where(Profile.id == user_id))
    assert prof_res.scalar_one_or_none() is not None
    req_res = await db_session.execute(
        select(RideRequest).where(RideRequest.id == req_id)
    )
    assert req_res.scalar_one_or_none() is not None

    # 2. Delete Profile row
    await db_session.delete(profile)
    await db_session.commit()

    # 3. Verify CASCADE deleted associated ride_request
    prof_after = await db_session.execute(select(Profile).where(Profile.id == user_id))
    assert prof_after.scalar_one_or_none() is None
    req_after = await db_session.execute(
        select(RideRequest).where(RideRequest.id == req_id)
    )
    assert req_after.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_db_check_constraints_enforcement(db_session: AsyncSession) -> None:
    """Verify that database CheckConstraints reject invalid data."""
    user_id = uuid.uuid4()
    now = datetime.now(UTC)
    await db_session.execute(auth_users.insert().values(id=user_id))
    profile = Profile(id=user_id, display_name="Constraint Tester")
    db_session.add(profile)
    await db_session.commit()

    # Test 1: seats_requested constraint (1..6) - value 0 must fail
    req_bad_seats = RideRequest(
        id=uuid.uuid4(),
        user_id=user_id,
        pickup_location="POINT(72.8777 19.0760)",
        destination="POINT(72.8258 18.9220)",
        departure_earliest=now + timedelta(minutes=10),
        departure_latest=now + timedelta(minutes=30),
        seats_requested=0,
    )
    db_session.add(req_bad_seats)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

    # Test 2: departure_latest < departure_earliest must fail
    req_bad_window = RideRequest(
        id=uuid.uuid4(),
        user_id=user_id,
        pickup_location="POINT(72.8777 19.0760)",
        destination="POINT(72.8258 18.9220)",
        departure_earliest=now + timedelta(minutes=30),
        departure_latest=now + timedelta(minutes=10),
        seats_requested=1,
    )
    db_session.add(req_bad_window)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

    # Test 3: max_extra_minutes > 180 must fail
    req_bad_detour = RideRequest(
        id=uuid.uuid4(),
        user_id=user_id,
        pickup_location="POINT(72.8777 19.0760)",
        destination="POINT(72.8258 18.9220)",
        departure_earliest=now + timedelta(minutes=10),
        departure_latest=now + timedelta(minutes=30),
        seats_requested=1,
        max_extra_minutes=250,
    )
    db_session.add(req_bad_detour)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()
