"""
Stage 1: PostGIS-powered candidate discovery.
Executes the spatial/temporal SQL query to find ACTIVE ride requests
compatible with request A. No Python-level distance filtering.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

CANDIDATE_FETCH_LIMIT = 20
MAX_VEHICLE_CAPACITY = 4
MAX_PICKUP_RADIUS_M = 2_000.0

CANDIDATE_QUERY = text("""
SELECT
    b.id                    AS candidate_id,
    b.user_id               AS candidate_user_id,
    p.display_name          AS owner_name,
    b.pickup_location,
    b.destination,
    b.pickup_label,
    b.destination_label,
    b.departure_earliest,
    b.departure_latest,
    b.seats_requested,
    b.max_extra_minutes,
    b.created_at,
    ST_Distance(b.pickup_location, ST_GeogFromText(:a_pickup_wkt)) AS pickup_distance_m,
    ST_Distance(b.destination,     ST_GeogFromText(:a_dest_wkt))   AS dest_distance_m,
    EXTRACT(EPOCH FROM (
        LEAST(b.departure_latest, :a_departure_latest) -
        GREATEST(b.departure_earliest, :a_departure_earliest)
    )) AS overlap_seconds
FROM ride_requests b
JOIN profiles p ON b.user_id = p.id
WHERE
    b.status = 'ACTIVE'
    AND b.id      != :a_id
    AND b.user_id != :a_user_id
    AND b.departure_latest > NOW()
    AND (b.expires_at IS NULL OR b.expires_at > NOW())
    AND (b.seats_requested + :a_seats) <= :max_capacity
    AND b.departure_earliest <= :a_departure_latest
    AND b.departure_latest   >= :a_departure_earliest
    AND ST_DWithin(b.pickup_location, ST_GeogFromText(:a_pickup_wkt), :radius_m)
ORDER BY pickup_distance_m ASC
LIMIT :limit
""")


async def discover_candidates(
    db: AsyncSession,
    *,
    request_id: uuid.UUID,
    user_id: uuid.UUID,
    pickup_lat: float,
    pickup_lon: float,
    dest_lat: float,
    dest_lon: float,
    departure_earliest: datetime,
    departure_latest: datetime,
    seats_requested: int,
) -> list[dict[str, Any]]:
    """
    Execute the Stage 1 PostGIS candidate discovery query.
    Returns a list of raw candidate dicts from the database.
    """
    # Ensure UTC-aware timestamps for PostgreSQL
    if departure_earliest.tzinfo is None:
        departure_earliest = departure_earliest.replace(tzinfo=UTC)
    if departure_latest.tzinfo is None:
        departure_latest = departure_latest.replace(tzinfo=UTC)

    pickup_wkt = f"POINT({pickup_lon} {pickup_lat})"
    dest_wkt = f"POINT({dest_lon} {dest_lat})"

    result = await db.execute(
        CANDIDATE_QUERY,
        {
            "a_id": request_id,
            "a_user_id": user_id,
            "a_pickup_wkt": pickup_wkt,
            "a_dest_wkt": dest_wkt,
            "a_departure_earliest": departure_earliest,
            "a_departure_latest": departure_latest,
            "a_seats": seats_requested,
            "max_capacity": MAX_VEHICLE_CAPACITY,
            "radius_m": MAX_PICKUP_RADIUS_M,
            "limit": CANDIDATE_FETCH_LIMIT,
        },
    )
    rows = result.mappings().all()
    return [dict(row) for row in rows]
