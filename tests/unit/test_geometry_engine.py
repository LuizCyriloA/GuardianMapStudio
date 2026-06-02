from __future__ import annotations

import math
from datetime import UTC, datetime

import pytest

from guardianmapstudio.domain.contracts import (
    GeoPoint,
    RestrictedArea,
    RestrictionType,
    Road,
    RoadDirection,
    Waypoint,
    WaypointType,
)
from guardianmapstudio.geometry.engine import EARTH_RADIUS_M, GeometryEngine

# Reference centroid: São José do Rio Preto, SP area
LAT = -20.81
LNG = -49.37

_NOW = datetime(2024, 1, 1, tzinfo=UTC)


def _make_road(coords: list[GeoPoint], name: str = "R") -> Road:
    return Road(
        id=1,
        workspace_id=1,
        name=name,
        coordinates=coords,
        speed_limit_kmh=30,
        direction=RoadDirection.TWO_WAY,
        width_meters=6.0,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _make_area(polygon: list[GeoPoint]) -> RestrictedArea:
    return RestrictedArea(
        id=1,
        workspace_id=1,
        name="Area",
        polygon=polygon,
        restriction_type=RestrictionType.NO_ENTRY,
        speed_limit_kmh=None,
        created_at=_NOW,
        updated_at=_NOW,
    )


@pytest.fixture
def engine() -> GeometryEngine:
    return GeometryEngine.from_centroid(LAT, LNG)


# ------------------------------------------------------------------
# Haversine
# ------------------------------------------------------------------


def test_haversine_known_distance(engine: GeometryEngine) -> None:
    # 0.0009° lat ≈ 100m at this location (EARTH_RADIUS_M * 0.0009 * π/180 ≈ 100m)
    a = GeoPoint(LAT, LNG)
    b = GeoPoint(LAT + 0.0009, LNG)
    dist = engine.haversine_distance(a, b)
    assert dist == pytest.approx(100.1, abs=2.0)


def test_haversine_matches_guardian(engine: GeometryEngine) -> None:
    a = GeoPoint(LAT, LNG)
    b = GeoPoint(LAT - 0.01, LNG + 0.01)
    dist = engine.haversine_distance(a, b)

    # Manual computation using the exact same formula as Guardian
    lat1 = math.radians(a.latitude)
    lat2 = math.radians(b.latitude)
    dlat = math.radians(b.latitude - a.latitude)
    dlng = math.radians(b.longitude - a.longitude)
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    expected = 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))

    assert dist == pytest.approx(expected, rel=1e-12)


def test_projected_distance_snap_scale(engine: GeometryEngine) -> None:
    base = GeoPoint(LAT, LNG)
    # ~0.3m north: 0.3 / 110_853 m/deg ≈ 2.71e-6 degrees
    near = GeoPoint(LAT + 2.71e-6, LNG)
    dist = engine.projected_distance(base, near)
    assert dist == pytest.approx(0.3, abs=0.05)
    assert dist < 0.5  # within snap tolerance


# ------------------------------------------------------------------
# Road intersection
# ------------------------------------------------------------------


def test_roads_intersect_crossing(engine: GeometryEngine) -> None:
    # Horizontal road at lat LAT, Vertical road at lng LNG — they cross
    road_h = _make_road([GeoPoint(LAT, LNG - 0.03), GeoPoint(LAT, LNG + 0.03)], "H")
    road_v = _make_road([GeoPoint(LAT - 0.03, LNG), GeoPoint(LAT + 0.03, LNG)], "V")
    assert engine.roads_intersect(road_h, road_v) is True


def test_roads_intersect_parallel(engine: GeometryEngine) -> None:
    # Two horizontal roads at different latitudes — they don't cross
    road_a = _make_road([GeoPoint(LAT, LNG - 0.03), GeoPoint(LAT, LNG + 0.03)], "A")
    road_b = _make_road([GeoPoint(LAT - 0.01, LNG - 0.03), GeoPoint(LAT - 0.01, LNG + 0.03)], "B")
    assert engine.roads_intersect(road_a, road_b) is False


# ------------------------------------------------------------------
# Polygon containment
# ------------------------------------------------------------------


def test_point_inside_polygon(engine: GeometryEngine) -> None:
    # Square polygon around the reference centroid
    poly = [
        GeoPoint(LAT + 0.01, LNG - 0.01),
        GeoPoint(LAT + 0.01, LNG + 0.01),
        GeoPoint(LAT - 0.01, LNG + 0.01),
        GeoPoint(LAT - 0.01, LNG - 0.01),
    ]
    area = _make_area(poly)
    interior = GeoPoint(LAT, LNG)
    assert engine.point_inside_polygon(interior, area) is True


def test_point_outside_polygon(engine: GeometryEngine) -> None:
    poly = [
        GeoPoint(LAT + 0.01, LNG - 0.01),
        GeoPoint(LAT + 0.01, LNG + 0.01),
        GeoPoint(LAT - 0.01, LNG + 0.01),
        GeoPoint(LAT - 0.01, LNG - 0.01),
    ]
    area = _make_area(poly)
    exterior = GeoPoint(LAT + 0.5, LNG)  # far north of polygon
    assert engine.point_inside_polygon(exterior, area) is False


# ------------------------------------------------------------------
# from_centroid hemisphere branches
# ------------------------------------------------------------------


def test_from_centroid_southern_hemisphere() -> None:
    engine = GeometryEngine.from_centroid(lat=-20.81, lng=-49.37)
    # Zone 22, southern hemisphere → EPSG 31982
    assert engine._epsg == 31982


def test_from_centroid_northern_hemisphere() -> None:
    engine = GeometryEngine.from_centroid(lat=10.0, lng=-49.37)
    # Zone 22, northern hemisphere → EPSG 32622
    assert engine._epsg == 32622


# ------------------------------------------------------------------
# STRtree management + invalidation
# ------------------------------------------------------------------


def test_build_and_invalidate_trees(engine: GeometryEngine) -> None:
    now = datetime.now(UTC)
    wp = Waypoint(
        id=1,
        workspace_id=1,
        name="WP",
        waypoint_type=WaypointType.LANDMARK,
        position=GeoPoint(LAT, LNG),
        road_name=None,
        heading_degrees=None,
        extra_data={},
        created_at=now,
        updated_at=now,
    )
    road = _make_road([GeoPoint(LAT, LNG - 0.01), GeoPoint(LAT, LNG + 0.01)])
    area = _make_area([
        GeoPoint(LAT + 0.01, LNG - 0.01),
        GeoPoint(LAT + 0.01, LNG + 0.01),
        GeoPoint(LAT - 0.01, LNG + 0.01),
    ])

    engine.build_waypoint_tree([wp])
    engine.build_road_tree([road])
    engine.build_area_tree([area])

    assert engine._waypoint_tree is not None
    assert engine._road_tree is not None
    assert engine._area_tree is not None

    engine.invalidate_all()

    assert engine._waypoint_tree is None
    assert engine._road_tree is None
    assert engine._area_tree is None
    assert engine._waypoint_index == []
    assert engine._road_index == []
    assert engine._area_index == []


# ------------------------------------------------------------------
# point_to_segment_distance
# ------------------------------------------------------------------


def test_point_to_segment_distance_on_segment(engine: GeometryEngine) -> None:
    # Midpoint of a 200m horizontal segment — distance should be ~0m
    start = GeoPoint(LAT, LNG - 0.001)
    end = GeoPoint(LAT, LNG + 0.001)
    mid = GeoPoint(LAT, LNG)
    dist = engine.point_to_segment_distance(mid, start, end)
    assert dist == pytest.approx(0.0, abs=0.5)


def test_point_to_segment_zero_length(engine: GeometryEngine) -> None:
    # Zero-length segment → distance = distance to start point
    pt = GeoPoint(LAT + 5e-6, LNG)
    seg = GeoPoint(LAT, LNG)
    dist = engine.point_to_segment_distance(pt, seg, seg)
    # Should equal distance from pt to seg ≈ 0.56m
    direct = engine.haversine_distance(pt, seg)
    assert dist == pytest.approx(direct, abs=0.1)
