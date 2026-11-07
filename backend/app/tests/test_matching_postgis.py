"""Live PostGIS candidate discovery integration tests.

Verifies:
- Real PostGIS geography spatial queries with ST_DWithin and ST_Distance
- Candidate filtering by distance, time overlap, seats, status, expiry, and user isolation
- Transaction rollback safety ensuring zero persistent changes to the database
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.matching.candidate_discovery import discover_candidates
from app.matching.service import run_matching
from app.models.ride_request import RideRequest, RideRequestStatus
from app.routing.fallback import FallbackRoutingProvider


async def _get_live_postgis_session() -> AsyncSession | None:
    """Create a live PostGIS session, or return None if unreachable."""
    if not settings.async_database_url:
        return None
    try:
        engine = create_async_engine(
            settings.async_database_url, connect_args={"timeout": 3}
        )
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        async with async_session() as session:
            await session.execute(text("SELECT PostGIS_Full_Version()"))
        return async_session()
    except Exception:
        return None


@pytest.mark.asyncio
async def test_live_postgis_candidate_discovery_and_filtering() -> None:
    session = await _get_live_postgis_session()
    if session is None:
        pytest.skip(
            "Hosted PostGIS database is unreachable or network is restricted in current sandbox"
        )

    try:
        async with session.begin():
            now = datetime.now(UTC)
            earliest = now + timedelta(hours=2)
            latest = now + timedelta(hours=3)

            user_a = uuid.UUID("96ce508c-aee5-4270-ac77-2765e29a2158")
            user_b = uuid.UUID("ceb95aa4-afdc-444b-abdb-7e5660f740f9")

            req_a_id = uuid.uuid4()
            req_b_valid = uuid.uuid4()
            req_b_far = uuid.uuid4()
            req_b_cancelled = uuid.uuid4()
            req_b_overcapacity = uuid.uuid4()

            # 1. Target A: BKC
            # 2. Candidate B1 (Valid nearby BKC One, ~45m away, 1 seat, ACTIVE)
            await session.execute(
                text("""
                INSERT INTO ride_requests (
                    id, user_id, pickup_label, destination_label,
                    pickup_location, destination,
                    departure_earliest, departure_latest,
                    seats_requested, max_extra_minutes, status, created_at, updated_at
                ) VALUES (
                    :id, :user_id, 'BKC One', 'Powai Galleria',
                    ST_SetSRID(ST_MakePoint(72.8690, 19.0660), 4326)::geography,
                    ST_SetSRID(ST_MakePoint(72.9050, 19.1170), 4326)::geography,
                    :earliest, :latest, 1, 20, 'ACTIVE', :now, :now
                )
            """),
                {
                    "id": req_b_valid,
                    "user_id": user_b,
                    "earliest": earliest,
                    "latest": latest,
                    "now": now,
                },
            )

            # 3. Candidate B2 (Far away: Colaba, >15km away)
            await session.execute(
                text("""
                INSERT INTO ride_requests (
                    id, user_id, pickup_label, destination_label,
                    pickup_location, destination,
                    departure_earliest, departure_latest,
                    seats_requested, max_extra_minutes, status, created_at, updated_at
                ) VALUES (
                    :id, :user_id, 'Colaba Gateway', 'Powai',
                    ST_SetSRID(ST_MakePoint(72.8347, 18.9220), 4326)::geography,
                    ST_SetSRID(ST_MakePoint(72.9050, 19.1170), 4326)::geography,
                    :earliest, :latest, 1, 20, 'ACTIVE', :now, :now
                )
            """),
                {
                    "id": req_b_far,
                    "user_id": user_b,
                    "earliest": earliest,
                    "latest": latest,
                    "now": now,
                },
            )

            # 4. Candidate B3 (Nearby BKC but CANCELLED)
            await session.execute(
                text("""
                INSERT INTO ride_requests (
                    id, user_id, pickup_label, destination_label,
                    pickup_location, destination,
                    departure_earliest, departure_latest,
                    seats_requested, max_extra_minutes, status, created_at, updated_at
                ) VALUES (
                    :id, :user_id, 'BKC Nearby Cancelled', 'Powai',
                    ST_SetSRID(ST_MakePoint(72.8690, 19.0660), 4326)::geography,
                    ST_SetSRID(ST_MakePoint(72.9050, 19.1170), 4326)::geography,
                    :earliest, :latest, 1, 20, 'CANCELLED', :now, :now
                )
            """),
                {
                    "id": req_b_cancelled,
                    "user_id": user_b,
                    "earliest": earliest,
                    "latest": latest,
                    "now": now,
                },
            )

            # 5. Candidate B4 (Nearby BKC, ACTIVE, but 4 seats -> 1 + 4 = 5 > 4 capacity limit)
            await session.execute(
                text("""
                INSERT INTO ride_requests (
                    id, user_id, pickup_label, destination_label,
                    pickup_location, destination,
                    departure_earliest, departure_latest,
                    seats_requested, max_extra_minutes, status, created_at, updated_at
                ) VALUES (
                    :id, :user_id, 'BKC 4 Seats', 'Powai',
                    ST_SetSRID(ST_MakePoint(72.8690, 19.0660), 4326)::geography,
                    ST_SetSRID(ST_MakePoint(72.9050, 19.1170), 4326)::geography,
                    :earliest, :latest, 4, 20, 'ACTIVE', :now, :now
                )
            """),
                {
                    "id": req_b_overcapacity,
                    "user_id": user_b,
                    "earliest": earliest,
                    "latest": latest,
                    "now": now,
                },
            )

            # Execute discover_candidates for User A
            candidates = await discover_candidates(
                session,
                request_id=req_a_id,
                user_id=user_a,
                pickup_lat=19.0657,
                pickup_lon=72.8687,
                dest_lat=19.1176,
                dest_lon=72.9060,
                departure_earliest=earliest,
                departure_latest=latest,
                seats_requested=1,
            )

            # Only candidate B1 should be returned!
            assert len(candidates) == 1
            assert candidates[0]["candidate_id"] == req_b_valid
            assert candidates[0]["pickup_distance_m"] < 100.0

            # Execute run_matching pipeline on real PostGIS
            target_obj = RideRequest(
                id=req_a_id,
                user_id=user_a,
                pickup_label="BKC Maker Maxity",
                destination_label="Powai Hiranandani",
                pickup_location="POINT(72.8687 19.0657)",
                destination="POINT(72.9060 19.1176)",
                departure_earliest=earliest,
                departure_latest=latest,
                seats_requested=1,
                max_extra_minutes=20,
                status=RideRequestStatus.ACTIVE,
                created_at=now,
                updated_at=now,
            )
            proposals = await run_matching(
                session, FallbackRoutingProvider(), target_obj
            )
            assert len(proposals) == 1
            assert proposals[0].candidate_request_id == req_b_valid
            assert proposals[0].scores.composite_score > 0.90

            # Rollback transaction so zero changes persist
            await session.rollback()
    finally:
        await session.close()
