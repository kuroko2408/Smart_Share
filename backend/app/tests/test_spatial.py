"""Tests for spatial utility functions and coordinate conventions."""

import pytest
from geoalchemy2.elements import WKTElement

from app.core.spatial import (
    are_coordinates_identical,
    parse_point_coordinates,
    to_geography_point,
    to_point_wkt,
    validate_coordinates,
)


def test_validate_coordinates_valid() -> None:
    """Verify validation passes for valid boundary and intermediate coordinates."""
    valid_coords = [
        (0.0, 0.0),
        (19.0760, 72.8777),  # Mumbai
        (90.0, 0.0),  # North Pole
        (-90.0, 0.0),  # South Pole
        (0.0, 180.0),  # Antimeridian East
        (0.0, -180.0),  # Antimeridian West
        (-33.8688, 151.2093),  # Sydney
    ]
    for lat, lon in valid_coords:
        validate_coordinates(latitude=lat, longitude=lon)


def test_validate_coordinates_invalid_latitude() -> None:
    """Verify invalid latitudes raise ValueError."""
    invalid_lats = [90.0001, -90.0001, 105.0, -120.0]
    for lat in invalid_lats:
        with pytest.raises(ValueError, match="Latitude must be between -90.0 and 90.0"):
            validate_coordinates(latitude=lat, longitude=0.0)


def test_validate_coordinates_invalid_longitude() -> None:
    """Verify invalid longitudes raise ValueError."""
    invalid_lons = [180.0001, -180.0001, 200.0, -250.0]
    for lon in invalid_lons:
        with pytest.raises(
            ValueError, match="Longitude must be between -180.0 and 180.0"
        ):
            validate_coordinates(latitude=0.0, longitude=lon)


def test_to_point_wkt_coordinate_order() -> None:
    """Verify PostGIS WKT ordering: Longitude as X, Latitude as Y."""
    # Mumbai: Lat=19.076, Lon=72.8777 -> POINT(72.8777 19.076)
    wkt = to_point_wkt(latitude=19.0760, longitude=72.8777)
    assert wkt == "POINT(72.8777 19.076)"
    assert wkt.startswith("POINT(72.8777")


def test_to_geography_point_srid() -> None:
    """Verify WKTElement creation sets SRID 4326."""
    elem = to_geography_point(latitude=19.0760, longitude=72.8777)
    assert isinstance(elem, WKTElement)
    assert elem.srid == 4326
    assert "POINT(72.8777 19.076)" in str(elem.data)


def test_parse_point_coordinates() -> None:
    """Verify parsing coordinates back from WKT and WKTElement."""
    wkt_string = "POINT(72.8777 19.0760)"
    lat, lon = parse_point_coordinates(wkt_string)
    assert pytest.approx(lat, abs=1e-4) == 19.0760
    assert pytest.approx(lon, abs=1e-4) == 72.8777

    elem = to_geography_point(latitude=28.6139, longitude=77.2090)  # Delhi
    lat_parsed, lon_parsed = parse_point_coordinates(elem)
    assert pytest.approx(lat_parsed, abs=1e-4) == 28.6139
    assert pytest.approx(lon_parsed, abs=1e-4) == 77.2090


def test_are_coordinates_identical() -> None:
    """Verify distinct endpoint detection."""
    # Identical
    assert are_coordinates_identical(19.076, 72.877, 19.076, 72.877) is True
    # Different
    assert are_coordinates_identical(19.076, 72.877, 19.077, 72.877) is False
    assert are_coordinates_identical(19.076, 72.877, 19.076, 72.878) is False
