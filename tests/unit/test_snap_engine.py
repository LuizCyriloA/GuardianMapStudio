from __future__ import annotations

from datetime import UTC, datetime

import pytest

from guardianmapstudio.domain.contracts import (
    GeoPoint,
    Road,
    RoadDirection,
    Waypoint,
    WaypointType,
)
from guardianmapstudio.geometry.engine import GeometryEngine
from guardianmapstudio.geometry.snap import SnapEngine

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


def _make_waypoint(pos: GeoPoint, wid: int = 1) -> Waypoint:
    return Waypoint(
        id=wid,
        workspace_id=1,
        name=f"WP{wid}",
        waypoint_type=WaypointType.LANDMARK,
        position=pos,
        road_name=None,
        heading_degrees=None,
        extra_data={},
        created_at=_NOW,
        updated_at=_NOW,
    )


@pytest.fixture
def engine() -> GeometryEngine:
    return GeometryEngine.from_centroid(LAT, LNG)


def test_snap_within_tolerance(engine: GeometryEngine) -> None:
    endpoint = GeoPoint(LAT, LNG)
    road = _make_road([endpoint, GeoPoint(LAT - 0.01, LNG)])
    # ~0.3m north of endpoint
    new_pt = GeoPoint(LAT + 2.71e-6, LNG)

    snap_engine = SnapEngine(engine, tolerance_m=0.5)
    result = snap_engine.snap(new_pt, [road], [])

    assert result.snapped is True
    assert result.snapped_to == endpoint
    assert result.distance_meters < 0.5


def test_snap_outside_tolerance(engine: GeometryEngine) -> None:
    endpoint = GeoPoint(LAT, LNG)
    road = _make_road([endpoint, GeoPoint(LAT - 0.01, LNG)])
    # ~0.7m north of endpoint — outside 0.5m tolerance
    new_pt = GeoPoint(LAT + 6.31e-6, LNG)

    snap_engine = SnapEngine(engine, tolerance_m=0.5)
    result = snap_engine.snap(new_pt, [road], [])

    assert result.snapped is False
    assert result.snapped_to == new_pt
    assert result.distance_meters == 0.0


def test_snap_exact_coincident(engine: GeometryEngine) -> None:
    endpoint = GeoPoint(LAT, LNG)
    road = _make_road([endpoint, GeoPoint(LAT - 0.01, LNG)])

    snap_engine = SnapEngine(engine, tolerance_m=0.5)
    result = snap_engine.snap(endpoint, [road], [])

    assert result.snapped is True
    assert result.snapped_to == endpoint
    assert result.distance_meters == pytest.approx(0.0, abs=1e-9)


def test_snap_no_candidates(engine: GeometryEngine) -> None:
    pt = GeoPoint(LAT, LNG)
    snap_engine = SnapEngine(engine, tolerance_m=0.5)
    result = snap_engine.snap(pt, [], [])

    assert result.snapped is False
    assert result.snapped_to == pt
    assert result.distance_meters == 0.0


def test_snap_returns_closest(engine: GeometryEngine) -> None:
    near = GeoPoint(LAT, LNG)
    far = GeoPoint(LAT + 0.001, LNG)  # ~111m away
    road_near = _make_road([near, GeoPoint(LAT - 0.01, LNG)], "Near")
    road_far = _make_road([far, GeoPoint(LAT + 0.011, LNG)], "Far")

    # New point very close to `near` endpoint
    new_pt = GeoPoint(LAT + 2.71e-6, LNG)
    snap_engine = SnapEngine(engine, tolerance_m=0.5)
    result = snap_engine.snap(new_pt, [road_near, road_far], [])

    assert result.snapped is True
    assert result.snapped_to == near


def test_snap_respects_custom_tolerance(engine: GeometryEngine) -> None:
    endpoint = GeoPoint(LAT, LNG)
    road = _make_road([endpoint, GeoPoint(LAT - 0.01, LNG)])
    # ~0.8m away from endpoint — beyond default 0.5m but within 1.0m
    new_pt = GeoPoint(LAT + 7.21e-6, LNG)

    snap_strict = SnapEngine(engine, tolerance_m=0.5)
    result_strict = snap_strict.snap(new_pt, [road], [])
    assert result_strict.snapped is False

    snap_wide = SnapEngine(engine, tolerance_m=1.0)
    result_wide = snap_wide.snap(new_pt, [road], [])
    assert result_wide.snapped is True
    assert result_wide.snapped_to == endpoint


def test_snap_waypoint_candidate(engine: GeometryEngine) -> None:
    wp_pos = GeoPoint(LAT, LNG)
    wp = _make_waypoint(wp_pos)

    new_pt = GeoPoint(LAT + 2.71e-6, LNG)
    snap_engine = SnapEngine(engine, tolerance_m=0.5)
    result = snap_engine.snap(new_pt, [], [wp])

    assert result.snapped is True
    assert result.snapped_to == wp_pos
