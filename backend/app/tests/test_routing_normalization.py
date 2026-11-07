"""Unit tests for Phase 5A distance normalization, data models, and GeoJSON geometry."""

from __future__ import annotations

from app.routing.models import (
    DistanceMetric,
    DistanceSource,
    MultiWaypointRoute,
    PassengerJourneyMetrics,
    RouteLeg,
    RoutingMatrixResult,
)


def test_distance_source_enum_values() -> None:
    """Verify all explicit provenance categories defined in Phase 5A."""
    assert DistanceSource.GEODESIC_SPHEROID == "geodesic_spheroid"
    assert (
        DistanceSource.CALIBRATED_TORTUOSITY_FALLBACK
        == "calibrated_tortuosity_fallback"
    )
    assert DistanceSource.PROVIDER_MATRIX_TABLE == "provider_matrix_table"
    assert DistanceSource.PROVIDER_ROAD_NETWORK_ROUTE == "provider_road_network_route"
    assert DistanceSource.ACTUAL_TELEMETRY == "actual_telemetry"


def test_distance_metric_si_units_and_properties() -> None:
    """Verify SI-unit conversions and kilometer property precision."""
    metric = DistanceMetric(
        distance_meters=9107.7,
        source=DistanceSource.PROVIDER_ROAD_NETWORK_ROUTE,
        is_approximate=False,
        confidence_factor=1.0,
    )
    assert metric.distance_meters == 9107.7
    assert metric.distance_km == 9.108
    assert not metric.is_approximate
    assert metric.source == DistanceSource.PROVIDER_ROAD_NETWORK_ROUTE

    # Fallback distance metric
    fallback_metric = DistanceMetric(
        distance_meters=14500.0,
        source=DistanceSource.CALIBRATED_TORTUOSITY_FALLBACK,
        is_approximate=True,
        confidence_factor=0.7,
    )
    assert fallback_metric.distance_km == 14.5
    assert fallback_metric.is_approximate
    assert fallback_metric.confidence_factor == 0.7


def test_route_leg_conversions() -> None:
    """Verify RouteLeg units and calculated properties."""
    leg = RouteLeg(
        sequence=1,
        start_stop_id="stop-a",
        end_stop_id="stop-b",
        start_label="BKC One",
        end_label="Kurla Station",
        distance_meters=3450.0,
        duration_seconds=420.0,
    )
    assert leg.sequence == 1
    assert leg.distance_km == 3.45
    assert leg.duration_minutes == 7.0


def test_passenger_journey_metrics_and_detour() -> None:
    """Verify per-passenger journey metrics, solo direct vs pooled detour calculations."""
    metrics = PassengerJourneyMetrics(
        passenger_request_id="req-target-123",
        solo_direct_distance_meters=8500.0,
        solo_direct_duration_seconds=720.0,  # 12 minutes
        pooled_journey_distance_meters=9100.0,
        pooled_journey_duration_seconds=840.0,  # 14 minutes
        detour_distance_meters=600.0,
        detour_duration_minutes=2.0,
        distance_source=DistanceSource.PROVIDER_ROAD_NETWORK_ROUTE,
        is_approximate=False,
    )
    assert metrics.solo_direct_distance_km == 8.5
    assert metrics.solo_direct_duration_minutes == 12.0
    assert metrics.pooled_distance_km == 9.1
    assert metrics.pooled_duration_minutes == 14.0
    assert metrics.detour_distance_km == 0.6
    assert metrics.detour_duration_minutes == 2.0
    assert not metrics.is_approximate


def test_geojson_linestring_rfc7946_coordinate_order() -> None:
    """Verify RFC 7946 requirement: coordinates are ordered [longitude, latitude]."""
    # Mumbai coordinates: BKC to Powai
    bkc_lon, bkc_lat = 72.8687, 19.0657
    powai_lon, powai_lat = 72.9060, 19.1176

    route = MultiWaypointRoute(
        total_distance=DistanceMetric(
            distance_meters=9107.7,
            source=DistanceSource.PROVIDER_ROAD_NETWORK_ROUTE,
            is_approximate=False,
        ),
        total_duration_seconds=743.9,
        legs=[
            RouteLeg(
                sequence=1,
                start_stop_id="s1",
                end_stop_id="s2",
                distance_meters=9107.7,
                duration_seconds=743.9,
            )
        ],
        full_geometry_geojson={
            "type": "LineString",
            "coordinates": [
                [bkc_lon, bkc_lat],
                [powai_lon, powai_lat],
            ],
        },
        provider_name="osrm",
    )

    geom = route.full_geometry_geojson
    assert geom["type"] == "LineString"
    assert len(geom["coordinates"]) == 2
    # Verify [lon, lat] ordering: lon for Mumbai is ~72.8, lat is ~19.0
    first_pt = geom["coordinates"][0]
    assert 72.0 <= first_pt[0] <= 73.5  # Longitude Easting
    assert 18.5 <= first_pt[1] <= 19.5  # Latitude Northing


def test_routing_matrix_result_shape_and_types() -> None:
    """Verify RoutingMatrixResult structure holding durations and distances."""
    res = RoutingMatrixResult(
        durations=[[0.0, 300.0], [300.0, 0.0]],
        distances=[[0.0, 4200.0], [4200.0, 0.0]],
        is_approximate=False,
        provider_name="osrm",
        routing_accuracy="road_network_duration_road_network_distance",
        notice="OSRM public routing",
    )
    assert len(res.durations) == 2
    assert len(res.distances) == 2
    assert res.durations[0][1] == 300.0
    assert res.distances[0][1] == 4200.0
    assert not res.is_approximate
