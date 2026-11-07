"""Unit and contract tests for Phase 5A routing provider adapters."""

from __future__ import annotations

import httpx
import pytest

from app.routing.base import (
    DistanceSource,
    RoutingCapability,
)
from app.routing.fallback import FallbackRoutingProvider
from app.routing.ors_provider import ORSRoutingProvider
from app.routing.osrm_provider import OSRMRoutingProvider


@pytest.mark.asyncio
async def test_fallback_provider_capabilities_and_matrices() -> None:
    """Verify fallback provider capabilities, matrix calculation and approximation flags."""
    provider = FallbackRoutingProvider()
    assert RoutingCapability.DURATION_MATRIX in provider.capabilities
    assert RoutingCapability.DISTANCE_MATRIX in provider.capabilities
    assert RoutingCapability.MULTI_WAYPOINT_ROUTE in provider.capabilities
    assert RoutingCapability.ROUTE_GEOMETRY in provider.capabilities
    assert provider.provider_name == "fallback"

    # 3 Mumbai points: BKC, Kurla, Powai
    points = [
        (19.0657, 72.8687),
        (19.0688, 72.8790),
        (19.1176, 72.9060),
    ]
    matrix_res = await provider.get_route_matrix(points)
    assert matrix_res.is_approximate
    assert matrix_res.provider_name == "fallback"
    assert len(matrix_res.durations) == 3
    assert len(matrix_res.distances) == 3

    # Diagonal is zero
    for i in range(3):
        assert matrix_res.durations[i][i] == 0.0
        assert matrix_res.distances[i][i] == 0.0

    # Off-diagonal positive
    assert matrix_res.durations[0][1] > 0.0
    assert matrix_res.distances[0][1] > 0.0


@pytest.mark.asyncio
async def test_fallback_provider_multi_waypoint_route_synthesis() -> None:
    """Verify fallback synthesizes RFC 7946 GeoJSON LineString and per-leg metrics."""
    provider = FallbackRoutingProvider()
    waypoints = [
        (19.0657, 72.8687),
        (19.0688, 72.8790),
        (19.1176, 72.9060),
    ]
    route = await provider.get_multi_waypoint_route(
        waypoints,
        stop_ids=["stop-1", "stop-2", "stop-3"],
        stop_labels=["BKC", "Kurla", "Powai"],
    )

    assert route.total_distance.is_approximate
    assert route.total_distance.source == DistanceSource.CALIBRATED_TORTUOSITY_FALLBACK
    assert route.total_distance.distance_meters > 0
    assert route.total_duration_seconds > 0
    assert len(route.legs) == 2

    # Check legs
    leg1 = route.legs[0]
    assert leg1.sequence == 1
    assert leg1.start_stop_id == "stop-1"
    assert leg1.end_stop_id == "stop-2"
    assert leg1.start_label == "BKC"
    assert leg1.end_label == "Kurla"

    # Check GeoJSON LineString structure and RFC 7946 coordinate ordering [lon, lat]
    geom = route.full_geometry_geojson
    assert geom["type"] == "LineString"
    assert len(geom["coordinates"]) == 3
    assert geom["coordinates"][0] == [72.8687, 19.0657]
    assert geom["coordinates"][1] == [72.8790, 19.0688]
    assert geom["coordinates"][2] == [72.9060, 19.1176]


@pytest.mark.asyncio
async def test_osrm_provider_capabilities_and_configuration() -> None:
    """Verify OSRM provider capability flags and configurable candidate limit."""
    provider = OSRMRoutingProvider(max_routed_candidates=3)
    assert RoutingCapability.DURATION_MATRIX in provider.capabilities
    assert RoutingCapability.DISTANCE_MATRIX in provider.capabilities
    assert RoutingCapability.MULTI_WAYPOINT_ROUTE in provider.capabilities
    assert RoutingCapability.ROUTE_GEOMETRY in provider.capabilities
    assert provider.provider_name == "osrm"
    assert provider.max_routed_candidates == 3


@pytest.mark.asyncio
async def test_osrm_provider_route_matrix_parsing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify OSRM Table API adapter extracts both duration and distance matrices."""
    provider = OSRMRoutingProvider()

    async def fake_matrix(points: list[tuple[float, float]]) -> dict:
        return {
            "code": "Ok",
            "durations": [
                [0.0, 310.5, 740.0],
                [320.0, 0.0, 680.0],
                [750.0, 690.0, 0.0],
            ],
            "distances": [
                [0.0, 3200.0, 9100.0],
                [3300.0, 0.0, 8500.0],
                [9200.0, 8600.0, 0.0],
            ],
        }

    monkeypatch.setattr(provider, "_get_matrix", fake_matrix)

    pts = [(19.0657, 72.8687), (19.0688, 72.8790), (19.1176, 72.9060)]
    matrix_res = await provider.get_route_matrix(pts)
    assert not matrix_res.is_approximate
    assert matrix_res.provider_name == "osrm"
    assert matrix_res.durations[0][2] == 740.0
    assert matrix_res.distances[0][2] == 9100.0


@pytest.mark.asyncio
async def test_osrm_provider_multi_waypoint_route_parsing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify OSRM Route API response parsing into MultiWaypointRoute and GeoJSON."""
    provider = OSRMRoutingProvider()

    fake_osrm_response = {
        "code": "Ok",
        "routes": [
            {
                "distance": 9107.7,
                "duration": 743.9,
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [72.868700, 19.065700],
                        [72.868820, 19.065810],
                        [72.871200, 19.069500],
                        [72.906000, 19.117600],
                    ],
                },
                "legs": [
                    {"distance": 356.5, "duration": 45.2},
                    {"distance": 8751.2, "duration": 698.7},
                ],
            }
        ],
    }

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url: str, params: dict | None = None):
            request = httpx.Request("GET", url)
            return httpx.Response(200, json=fake_osrm_response, request=request)

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    waypoints = [
        (19.0657, 72.8687),
        (19.0688, 72.8790),
        (19.1176, 72.9060),
    ]
    route = await provider.get_multi_waypoint_route(
        waypoints,
        stop_ids=["p1", "p2", "d1"],
        stop_labels=["BKC", "Kurla", "Powai"],
    )

    assert route.total_distance.distance_meters == 9107.7
    assert route.total_distance.distance_km == 9.108
    assert route.total_distance.source == DistanceSource.PROVIDER_ROAD_NETWORK_ROUTE
    assert not route.total_distance.is_approximate
    assert route.total_duration_seconds == 743.9

    assert len(route.legs) == 2
    assert route.legs[0].distance_meters == 356.5
    assert route.legs[1].distance_meters == 8751.2

    geom = route.full_geometry_geojson
    assert geom["type"] == "LineString"
    assert len(geom["coordinates"]) == 4
    assert geom["coordinates"][0] == [72.8687, 19.0657]


@pytest.mark.asyncio
async def test_ors_provider_matrix_and_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify ORS provider requests duration & distance, and falls back gracefully on error."""
    provider = ORSRoutingProvider(api_key="test-key")
    assert provider.provider_name == "openrouteservice"

    # Simulate ORS network failure
    class FailingAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url: str, **kwargs):
            request = httpx.Request("POST", url)
            raise httpx.ConnectTimeout("Connection timeout to ORS", request=request)

    monkeypatch.setattr(httpx, "AsyncClient", FailingAsyncClient)

    # Calling get_multi_waypoint_route should degrade to fallback without raising
    waypoints = [(19.0657, 72.8687), (19.1176, 72.9060)]
    route = await provider.get_multi_waypoint_route(waypoints)
    assert route.total_distance.is_approximate
    assert route.total_distance.source == DistanceSource.CALIBRATED_TORTUOSITY_FALLBACK


@pytest.mark.asyncio
async def test_ors_provider_directions_geojson_successful_parsing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify ORS Directions API successful response parsing into GeoJSON LineString and legs."""
    provider = ORSRoutingProvider(api_key="test-key")

    fake_ors_geojson_response = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [72.868700, 19.065700],
                        [72.875000, 19.075000],
                        [72.906000, 19.117600],
                    ],
                },
                "properties": {
                    "summary": {
                        "distance": 9107.7,
                        "duration": 743.9,
                    },
                    "segments": [
                        {"distance": 450.0, "duration": 60.0},
                        {"distance": 8657.7, "duration": 683.9},
                    ],
                },
            }
        ],
    }

    class MockORSClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url: str, **kwargs):
            request = httpx.Request("POST", url)
            return httpx.Response(200, json=fake_ors_geojson_response, request=request)

    monkeypatch.setattr(httpx, "AsyncClient", MockORSClient)

    waypoints = [
        (19.0657, 72.8687),
        (19.0750, 72.8750),
        (19.1176, 72.9060),
    ]
    route = await provider.get_multi_waypoint_route(
        waypoints,
        stop_ids=["s1", "s2", "s3"],
        stop_labels=["BKC", "Kurla", "Powai"],
    )

    assert not route.total_distance.is_approximate
    assert route.total_distance.source == DistanceSource.PROVIDER_ROAD_NETWORK_ROUTE
    assert route.total_distance.distance_meters == 9107.7
    assert route.total_duration_seconds == 743.9
    assert len(route.legs) == 2
    assert route.legs[0].distance_meters == 450.0
    assert route.legs[0].duration_seconds == 60.0
    assert route.legs[1].distance_meters == 8657.7
    assert route.legs[1].duration_seconds == 683.9

    # RFC 7946 coordinate ordering: [longitude, latitude]
    coords = route.full_geometry_geojson["coordinates"]
    assert len(coords) == 3
    assert coords[0] == [72.868700, 19.065700]
    assert coords[1] == [72.875000, 19.075000]
    assert coords[2] == [72.906000, 19.117600]


@pytest.mark.asyncio
async def test_osrm_table_api_timeout_triggers_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify OSRM Table API timeout triggers graceful fallback with approximate flags."""
    from app.matching.detour import evaluate_pairwise_detour

    provider = OSRMRoutingProvider()

    async def timeout_matrix(points):
        req = httpx.Request(
            "GET", "https://router.project-osrm.org/table/v1/driving/..."
        )
        raise httpx.TimeoutException("OSRM Table connection timed out", request=req)

    monkeypatch.setattr(provider, "_get_matrix", timeout_matrix)

    pts = [
        (19.0657, 72.8687),
        (19.0688, 72.8790),
        (19.1176, 72.9060),
        (19.1200, 72.9100),
    ]
    result = await evaluate_pairwise_detour(
        provider=provider,
        pickup_a=pts[0],
        pickup_b=pts[1],
        dest_a=pts[2],
        dest_b=pts[3],
        max_extra_a=30,
        max_extra_b=30,
    )

    assert result is not None
    assert result.is_approximate
    assert result.distance_source == DistanceSource.CALIBRATED_TORTUOSITY_FALLBACK
    assert "tortuosity factor 1.40" in result.notice


@pytest.mark.asyncio
async def test_osrm_table_api_http_429_triggers_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify OSRM Table API HTTP 429 rate limit triggers graceful fallback."""
    from app.matching.detour import evaluate_pairwise_detour

    provider = OSRMRoutingProvider()

    async def rate_limited_matrix(points):
        req = httpx.Request(
            "GET", "https://router.project-osrm.org/table/v1/driving/..."
        )
        resp = httpx.Response(429, request=req)
        raise httpx.HTTPStatusError("Too Many Requests", request=req, response=resp)

    monkeypatch.setattr(provider, "_get_matrix", rate_limited_matrix)

    pts = [
        (19.0657, 72.8687),
        (19.0688, 72.8790),
        (19.1176, 72.9060),
        (19.1200, 72.9100),
    ]
    result = await evaluate_pairwise_detour(
        provider=provider,
        pickup_a=pts[0],
        pickup_b=pts[1],
        dest_a=pts[2],
        dest_b=pts[3],
        max_extra_a=30,
        max_extra_b=30,
    )

    assert result is not None
    assert result.is_approximate
    assert result.distance_source == DistanceSource.CALIBRATED_TORTUOSITY_FALLBACK


@pytest.mark.asyncio
async def test_osrm_table_api_invalid_payload_triggers_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify invalid status code in OSRM payload triggers graceful fallback."""
    from app.matching.detour import evaluate_pairwise_detour

    provider = OSRMRoutingProvider()

    async def invalid_matrix(points):
        return {"code": "InvalidQuery", "message": "Could not find route"}

    monkeypatch.setattr(provider, "_get_matrix", invalid_matrix)

    pts = [
        (19.0657, 72.8687),
        (19.0688, 72.8790),
        (19.1176, 72.9060),
        (19.1200, 72.9100),
    ]
    result = await evaluate_pairwise_detour(
        provider=provider,
        pickup_a=pts[0],
        pickup_b=pts[1],
        dest_a=pts[2],
        dest_b=pts[3],
        max_extra_a=30,
        max_extra_b=30,
    )

    assert result is not None
    assert result.is_approximate
    assert result.distance_source == DistanceSource.CALIBRATED_TORTUOSITY_FALLBACK


@pytest.mark.asyncio
async def test_osrm_table_api_none_values_triggers_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify None matrix entries trigger graceful fallback."""
    from app.matching.detour import evaluate_pairwise_detour

    provider = OSRMRoutingProvider()

    async def none_matrix(points):
        return {
            "code": "Ok",
            "durations": [[0, None], [None, 0]],
            "distances": [[0, None], [None, 0]],
        }

    monkeypatch.setattr(provider, "_get_matrix", none_matrix)

    pts = [
        (19.0657, 72.8687),
        (19.0688, 72.8790),
        (19.1176, 72.9060),
        (19.1200, 72.9100),
    ]
    result = await evaluate_pairwise_detour(
        provider=provider,
        pickup_a=pts[0],
        pickup_b=pts[1],
        dest_a=pts[2],
        dest_b=pts[3],
        max_extra_a=30,
        max_extra_b=30,
    )

    assert result is not None
    assert result.is_approximate
    assert result.distance_source == DistanceSource.CALIBRATED_TORTUOSITY_FALLBACK
