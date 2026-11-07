"""
Geometric compatibility calculations for the matching engine.
All functions operate on plain Python floats — no DB calls.
"""

import math

EARTH_RADIUS_M = 6_371_000.0
MAX_PICKUP_RADIUS_M = 2_000.0
MAX_DEST_RADIUS_M = 5_000.0
MAX_DIRECTIONAL_DELTA_DEG = 90.0
DEST_PROXIMITY_BYPASS_M = 3_000.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Geodesic distance in metres between two WGS-84 coordinate pairs."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Forward geodesic bearing from point 1 to point 2 in degrees [0, 360).
    Returns 0.0 if both points are identical.
    """
    if abs(lat1 - lat2) < 1e-9 and abs(lon1 - lon2) < 1e-9:
        return 0.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


def angular_delta(bearing_a: float, bearing_b: float) -> float:
    """Minimum angular difference between two bearings, in [0, 180]."""
    diff = abs(bearing_a - bearing_b) % 360.0
    return min(diff, 360.0 - diff)


def is_directionally_compatible(
    bearing_a: float,
    bearing_b: float,
    dest_distance_m: float,
) -> bool:
    """
    Return True if the two travel vectors are directionally compatible.

    Rules (resolved from Phase 4A design validation):
    - delta ≤ 45°               → always compatible (preferred corridor)
    - 45° < delta ≤ 90°        → compatible only if dest_distance ≤ 3000m
    - delta > 90°               → hard reject regardless of dest proximity
      (anti-parallel; one passenger would backtrack severely)
    """
    delta = angular_delta(bearing_a, bearing_b)
    if delta <= 45.0:
        return True
    if delta <= 90.0:
        return dest_distance_m <= DEST_PROXIMITY_BYPASS_M
    return False


def road_distance_estimate(geodesic_m: float) -> float:
    """Calibrated tortuosity estimate: road ≈ 1.4 × straight-line distance."""
    return geodesic_m * 1.40


def road_duration_estimate_seconds(road_distance_m: float) -> float:
    """
    Estimate travel duration using conservative Mumbai daytime speed of 22 km/h.
    Returns seconds.
    """
    speed_ms = 22_000.0 / 3600.0  # 6.111 m/s
    return road_distance_m / speed_ms
