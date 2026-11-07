"""Spatial utility functions for PostGIS SRID 4326 geography points."""

import re
from typing import Any

from geoalchemy2.elements import WKBElement, WKTElement
from shapely import from_wkb, from_wkt

# Regular expression fallback for WKT or EWKT POINT strings: POINT(lon lat) or SRID=4326;POINT(lon lat)
POINT_WKT_REGEX = re.compile(
    r"^(?:SRID=\d+;\s*)?POINT\s*\(\s*([+-]?\d+(?:\.\d+)?)\s+([+-]?\d+(?:\.\d+)?)\s*\)$",
    re.IGNORECASE,
)


def validate_coordinates(latitude: float, longitude: float) -> None:
    """Validate latitude and longitude against WGS 84 spatial boundaries.

    Raises:
        ValueError: If latitude is not in [-90, 90] or longitude is not in [-180, 180].
    """
    if not (-90.0 <= latitude <= 90.0):
        raise ValueError(
            f"Latitude must be between -90.0 and 90.0 degrees. Received: {latitude}"
        )
    if not (-180.0 <= longitude <= 180.0):
        raise ValueError(
            f"Longitude must be between -180.0 and 180.0 degrees. Received: {longitude}"
        )


def to_point_wkt(latitude: float, longitude: float) -> str:
    """Format latitude and longitude into PostGIS WKT Point string.

    CRITICAL CONVENTION: PostGIS WKT points require LONGITUDE as X and LATITUDE as Y.
    Example: POINT(longitude latitude)
    """
    validate_coordinates(latitude, longitude)
    return f"POINT({longitude} {latitude})"


def to_geography_point(latitude: float, longitude: float) -> WKTElement:
    """Create a GeoAlchemy2 WKTElement with SRID 4326 (WGS 84).

    CRITICAL CONVENTION: Longitude is X, Latitude is Y.
    """
    wkt = to_point_wkt(latitude=latitude, longitude=longitude)
    return WKTElement(wkt, srid=4326)


def parse_point_coordinates(point_geom: Any) -> tuple[float, float]:
    """Extract (latitude, longitude) from GeoAlchemy2 WKBElement, WKTElement, or WKT/EWKB string/bytes.

    Returns:
        tuple[float, float]: (latitude, longitude)
    """
    if isinstance(point_geom, (bytes, bytearray, memoryview)):
        try:
            shapely_point = from_wkb(bytes(point_geom))
            validate_coordinates(
                latitude=float(shapely_point.y), longitude=float(shapely_point.x)
            )
            return float(shapely_point.y), float(shapely_point.x)
        except Exception as exc:
            raise ValueError(
                f"Unable to parse spatial point coordinates from binary WKB: {point_geom!r}"
            ) from exc

    if isinstance(point_geom, WKBElement):
        if isinstance(point_geom.data, (bytes, bytearray, memoryview)):
            shapely_point = from_wkb(bytes(point_geom.data))
            validate_coordinates(
                latitude=float(shapely_point.y), longitude=float(shapely_point.x)
            )
            return float(shapely_point.y), float(shapely_point.x)
        wkt_str = str(point_geom.data)
    elif isinstance(point_geom, WKTElement):
        wkt_str = str(point_geom.data)
    else:
        wkt_str = str(point_geom)

    match = POINT_WKT_REGEX.match(wkt_str.strip())
    if match:
        lon, lat = float(match.group(1)), float(match.group(2))
        validate_coordinates(latitude=lat, longitude=lon)
        return lat, lon

    clean_str = re.sub(r"^SRID=\d+;\s*", "", wkt_str.strip(), flags=re.IGNORECASE)
    try:
        shapely_point = from_wkt(clean_str)
        validate_coordinates(
            latitude=float(shapely_point.y), longitude=float(shapely_point.x)
        )
        return float(shapely_point.y), float(shapely_point.x)
    except Exception:
        pass

    try:
        shapely_point = from_wkb(clean_str)
        validate_coordinates(
            latitude=float(shapely_point.y), longitude=float(shapely_point.x)
        )
        return float(shapely_point.y), float(shapely_point.x)
    except Exception as exc:
        raise ValueError(
            f"Unable to parse spatial point coordinates from: {point_geom}"
        ) from exc


def are_coordinates_identical(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    epsilon: float = 1e-6,
) -> bool:
    """Check if two coordinate pairs are identical within an epsilon threshold."""
    return abs(lat1 - lat2) < epsilon and abs(lon1 - lon2) < epsilon
