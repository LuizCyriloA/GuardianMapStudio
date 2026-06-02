from __future__ import annotations

from datetime import UTC, datetime

import pytest

from guardianmapstudio.domain.contracts import (
    Crossroad,
    GeoPoint,
    Road,
    RoadDirection,
)
from guardianmapstudio.geometry.crossroad import CrossroadEngine
from guardianmapstudio.geometry.engine import GeometryEngine

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


def _make_crossroad(pos: GeoPoint, a: str = "A", b: str = "B") -> Crossroad:
    return Crossroad(
        id=1,
        workspace_id=1,
        road_a_name=a,
        road_b_name=b,
        position=pos,
        created_at=_NOW,
    )


@pytest.fixture
def engine() -> GeometryEngine:
    return GeometryEngine.from_centroid(LAT, LNG)


@pytest.fixture
def crossroad_engine(engine: GeometryEngine) -> CrossroadEngine:
    return CrossroadEngine(engine)


# Perpendicular roads that cross exactly at (LAT, LNG)
@pytest.fixture
def crossing_roads() -> tuple[Road, Road]:
    road_h = _make_road([GeoPoint(LAT, LNG - 0.03), GeoPoint(LAT, LNG + 0.03)], "H")
    road_v = _make_road([GeoPoint(LAT - 0.03, LNG), GeoPoint(LAT + 0.03, LNG)], "V")
    return road_h, road_v


@pytest.fixture
def parallel_roads() -> tuple[Road, Road]:
    road_a = _make_road([GeoPoint(LAT, LNG - 0.03), GeoPoint(LAT, LNG + 0.03)], "A")
    road_b = _make_road([GeoPoint(LAT - 0.01, LNG - 0.03), GeoPoint(LAT - 0.01, LNG + 0.03)], "B")
    return road_a, road_b


def test_roads_intersect_crossing(
    crossroad_engine: CrossroadEngine, crossing_roads: tuple[Road, Road]
) -> None:
    road_h, road_v = crossing_roads
    assert crossroad_engine.roads_intersect(road_h, road_v) is True


def test_roads_intersect_parallel(
    crossroad_engine: CrossroadEngine, parallel_roads: tuple[Road, Road]
) -> None:
    road_a, road_b = parallel_roads
    assert crossroad_engine.roads_intersect(road_a, road_b) is False


def test_find_intersection_point(
    crossroad_engine: CrossroadEngine, crossing_roads: tuple[Road, Road]
) -> None:
    road_h, road_v = crossing_roads
    pt = crossroad_engine.find_intersection_point(road_h, road_v)
    assert pt is not None
    assert pt.latitude == pytest.approx(LAT, abs=1e-6)
    assert pt.longitude == pytest.approx(LNG, abs=1e-6)


def test_find_intersection_no_cross(
    crossroad_engine: CrossroadEngine, parallel_roads: tuple[Road, Road]
) -> None:
    road_a, road_b = parallel_roads
    pt = crossroad_engine.find_intersection_point(road_a, road_b)
    assert pt is None


def test_crossroad_near_intersection(
    crossroad_engine: CrossroadEngine, crossing_roads: tuple[Road, Road]
) -> None:
    road_h, road_v = crossing_roads
    cr = _make_crossroad(GeoPoint(LAT, LNG), "H", "V")
    assert crossroad_engine.crossroad_is_near_intersection(cr, road_h, road_v) is True


def test_crossroad_far_from_intersection(
    crossroad_engine: CrossroadEngine, crossing_roads: tuple[Road, Road]
) -> None:
    road_h, road_v = crossing_roads
    # 2e-5° lat ≈ 2.2m — beyond 1.0m proximity threshold
    cr = _make_crossroad(GeoPoint(LAT + 2e-5, LNG), "H", "V")
    assert crossroad_engine.crossroad_is_near_intersection(cr, road_h, road_v) is False


def test_single_point_road_no_intersection(crossroad_engine: CrossroadEngine) -> None:
    road_short = _make_road([GeoPoint(LAT, LNG)], "Short")  # only 1 point
    road_normal = _make_road([GeoPoint(LAT - 0.03, LNG), GeoPoint(LAT + 0.03, LNG)], "Normal")
    assert crossroad_engine.roads_intersect(road_short, road_normal) is False
    assert crossroad_engine.find_intersection_point(road_short, road_normal) is None
