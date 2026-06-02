from __future__ import annotations

from datetime import UTC, datetime

import pytest

from guardianmapstudio.domain.contracts import (
    Crossroad,
    GeoPoint,
    RestrictedArea,
    RestrictionType,
    Road,
    RoadDirection,
    ValidationSeverity,
    Waypoint,
    WaypointType,
)
from guardianmapstudio.geometry.engine import GeometryEngine
from guardianmapstudio.geometry.validation import ValidationEngine

LAT = -20.81
LNG = -49.37
_NOW = datetime(2024, 1, 1, tzinfo=UTC)


# ------------------------------------------------------------------
# Factories
# ------------------------------------------------------------------


def _road(
    coords: list[GeoPoint],
    name: str = "Rua A",
    rid: int = 1,
    speed: int = 30,
    width: float = 6.0,
) -> Road:
    return Road(
        id=rid,
        workspace_id=1,
        name=name,
        coordinates=coords,
        speed_limit_kmh=speed,
        direction=RoadDirection.TWO_WAY,
        width_meters=width,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _waypoint(
    pos: GeoPoint,
    name: str = "WP",
    wtype: WaypointType = WaypointType.LANDMARK,
    road_name: str | None = "Rua A",
    heading: float | None = None,
    extra: dict | None = None,  # type: ignore[type-arg]
    wid: int = 1,
    active: bool = True,
) -> Waypoint:
    return Waypoint(
        id=wid,
        workspace_id=1,
        name=name,
        waypoint_type=wtype,
        position=pos,
        road_name=road_name,
        heading_degrees=heading,
        extra_data=extra or {},
        created_at=_NOW,
        updated_at=_NOW,
        active=active,
    )


def _crossroad(
    pos: GeoPoint,
    road_a: str = "Rua A",
    road_b: str = "Rua B",
    cid: int = 1,
) -> Crossroad:
    return Crossroad(
        id=cid,
        workspace_id=1,
        road_a_name=road_a,
        road_b_name=road_b,
        position=pos,
        created_at=_NOW,
    )


def _area(
    polygon: list[GeoPoint],
    name: str = "Area",
    rtype: RestrictionType = RestrictionType.NO_ENTRY,
    speed: int | None = None,
    aid: int = 1,
) -> RestrictedArea:
    return RestrictedArea(
        id=aid,
        workspace_id=1,
        name=name,
        polygon=polygon,
        restriction_type=rtype,
        speed_limit_kmh=speed,
        created_at=_NOW,
        updated_at=_NOW,
    )


@pytest.fixture
def val_engine() -> ValidationEngine:
    geo = GeometryEngine.from_centroid(LAT, LNG)
    return ValidationEngine(geo)


def _errors(results: list) -> list:  # type: ignore[type-arg]
    return [r for r in results if r.severity == ValidationSeverity.ERROR]


def _warnings(results: list) -> list:  # type: ignore[type-arg]
    return [r for r in results if r.severity == ValidationSeverity.WARNING]


# ------------------------------------------------------------------
# Workspace
# ------------------------------------------------------------------


def test_workspace_no_roads_error(val_engine: ValidationEngine) -> None:
    results = val_engine.validate([], [], [], [])
    ids = [r.rule_id for r in results]
    assert "workspace.min_roads" in ids
    assert any(r.severity == ValidationSeverity.ERROR for r in results)


# ------------------------------------------------------------------
# Road rules
# ------------------------------------------------------------------


def test_road_min_points_error(val_engine: ValidationEngine) -> None:
    bad_road = _road([GeoPoint(LAT, LNG)])  # only 1 point
    results = val_engine.validate([bad_road], [], [], [])
    ids = [r.rule_id for r in _errors(results)]
    assert "road.min_points" in ids


def test_road_name_unique_error(val_engine: ValidationEngine) -> None:
    road_a = _road([GeoPoint(LAT, LNG), GeoPoint(LAT - 0.01, LNG)], name="Dup", rid=1)
    road_b = _road([GeoPoint(LAT, LNG + 0.01), GeoPoint(LAT - 0.01, LNG + 0.01)], name="Dup", rid=2)
    results = val_engine.validate([road_a, road_b], [], [], [])
    ids = [r.rule_id for r in _errors(results)]
    assert "road.name_unique" in ids


def test_road_speed_limit_error(val_engine: ValidationEngine) -> None:
    bad_road = _road(
        [GeoPoint(LAT, LNG), GeoPoint(LAT - 0.01, LNG)], speed=0
    )
    results = val_engine.validate([bad_road], [], [], [])
    ids = [r.rule_id for r in _errors(results)]
    assert "road.speed_limit_positive" in ids


def test_road_width_positive_error(val_engine: ValidationEngine) -> None:
    bad_road = _road(
        [GeoPoint(LAT, LNG), GeoPoint(LAT - 0.01, LNG)], width=0.0
    )
    results = val_engine.validate([bad_road], [], [], [])
    ids = [r.rule_id for r in _errors(results)]
    assert "road.width_positive" in ids


def test_road_no_waypoints_warning(val_engine: ValidationEngine) -> None:
    road = _road([GeoPoint(LAT, LNG), GeoPoint(LAT - 0.01, LNG)])
    results = val_engine.validate([road], [], [], [])
    ids = [r.rule_id for r in _warnings(results)]
    assert "road.no_waypoints" in ids


# ------------------------------------------------------------------
# Waypoint rules
# ------------------------------------------------------------------


def test_waypoint_name_empty_error(val_engine: ValidationEngine) -> None:
    road = _road([GeoPoint(LAT, LNG), GeoPoint(LAT - 0.01, LNG)])
    wp = _waypoint(GeoPoint(LAT, LNG), name="   ")
    results = val_engine.validate([road], [wp], [], [])
    ids = [r.rule_id for r in _errors(results)]
    assert "waypoint.name_not_empty" in ids


def test_waypoint_road_exists_error(val_engine: ValidationEngine) -> None:
    road = _road([GeoPoint(LAT, LNG), GeoPoint(LAT - 0.01, LNG)], name="Rua A")
    wp = _waypoint(GeoPoint(LAT, LNG), road_name="Rua Inexistente")
    results = val_engine.validate([road], [wp], [], [])
    ids = [r.rule_id for r in _errors(results)]
    assert "waypoint.road_exists" in ids


def test_waypoint_speed_bump_no_height(val_engine: ValidationEngine) -> None:
    road = _road([GeoPoint(LAT, LNG), GeoPoint(LAT - 0.01, LNG)])
    wp = _waypoint(GeoPoint(LAT, LNG), wtype=WaypointType.SPEED_BUMP, extra={})
    results = val_engine.validate([road], [wp], [], [])
    ids = [r.rule_id for r in _errors(results)]
    assert "waypoint.speed_bump_height" in ids


def test_waypoint_gate_invalid_type(val_engine: ValidationEngine) -> None:
    road = _road([GeoPoint(LAT, LNG), GeoPoint(LAT - 0.01, LNG)])
    wp = _waypoint(
        GeoPoint(LAT, LNG),
        wtype=WaypointType.GATE,
        extra={"gate_type": "invalid"},
    )
    results = val_engine.validate([road], [wp], [], [])
    ids = [r.rule_id for r in _errors(results)]
    assert "waypoint.gate_type_valid" in ids


def test_waypoint_heading_out_of_range(val_engine: ValidationEngine) -> None:
    road = _road([GeoPoint(LAT, LNG), GeoPoint(LAT - 0.01, LNG)])
    wp = _waypoint(GeoPoint(LAT, LNG), heading=400.0)
    results = val_engine.validate([road], [wp], [], [])
    ids = [r.rule_id for r in _errors(results)]
    assert "waypoint.heading_range" in ids


def test_waypoint_duplicate_position(val_engine: ValidationEngine) -> None:
    road = _road([GeoPoint(LAT, LNG), GeoPoint(LAT - 0.01, LNG)])
    # Two waypoints only 0.3m apart (2.7e-6 deg lat offset)
    wp1 = _waypoint(GeoPoint(LAT, LNG), wid=1)
    wp2 = _waypoint(GeoPoint(LAT + 2.71e-6, LNG), wid=2)
    results = val_engine.validate([road], [wp1, wp2], [], [])
    ids = [r.rule_id for r in _warnings(results)]
    assert "waypoint.duplicate_position" in ids


# ------------------------------------------------------------------
# Crossroad rules
# ------------------------------------------------------------------


def test_crossroad_road_a_missing(val_engine: ValidationEngine) -> None:
    road = _road([GeoPoint(LAT, LNG - 0.01), GeoPoint(LAT, LNG + 0.01)], name="Rua B")
    cr = _crossroad(GeoPoint(LAT, LNG), road_a="Rua Fantasma", road_b="Rua B")
    results = val_engine.validate([road], [], [cr], [])
    ids = [r.rule_id for r in _errors(results)]
    assert "crossroad.road_a_exists" in ids


def test_crossroad_roads_identical(val_engine: ValidationEngine) -> None:
    road = _road([GeoPoint(LAT, LNG - 0.01), GeoPoint(LAT, LNG + 0.01)], name="Rua A")
    cr = _crossroad(GeoPoint(LAT, LNG), road_a="Rua A", road_b="Rua A")
    results = val_engine.validate([road], [], [cr], [])
    ids = [r.rule_id for r in _errors(results)]
    assert "crossroad.roads_distinct" in ids


def test_crossroad_not_near_intersection(val_engine: ValidationEngine) -> None:
    road_h = _road([GeoPoint(LAT, LNG - 0.03), GeoPoint(LAT, LNG + 0.03)], name="H", rid=1)
    road_v = _road([GeoPoint(LAT - 0.03, LNG), GeoPoint(LAT + 0.03, LNG)], name="V", rid=2)
    # Crossroad placed 5m away from actual intersection
    cr = _crossroad(GeoPoint(LAT + 5e-5, LNG), road_a="H", road_b="V")
    results = val_engine.validate([road_h, road_v], [], [cr], [])
    ids = [r.rule_id for r in _warnings(results)]
    assert "crossroad.roads_intersect" in ids


# ------------------------------------------------------------------
# Area rules
# ------------------------------------------------------------------


def test_area_min_points_error(val_engine: ValidationEngine) -> None:
    road = _road([GeoPoint(LAT, LNG), GeoPoint(LAT - 0.01, LNG)])
    area = _area([GeoPoint(LAT, LNG), GeoPoint(LAT + 0.01, LNG)])  # only 2 points
    results = val_engine.validate([road], [], [], [area])
    ids = [r.rule_id for r in _errors(results)]
    assert "area.min_points" in ids


def test_area_speed_limit_required(val_engine: ValidationEngine) -> None:
    road = _road([GeoPoint(LAT, LNG), GeoPoint(LAT - 0.01, LNG)])
    area = _area(
        [GeoPoint(LAT, LNG), GeoPoint(LAT + 0.01, LNG), GeoPoint(LAT, LNG + 0.01)],
        rtype=RestrictionType.SPEED_LIMIT,
        speed=None,
    )
    results = val_engine.validate([road], [], [], [area])
    ids = [r.rule_id for r in _errors(results)]
    assert "area.speed_limit_required" in ids


def test_area_speed_limit_positive_error(val_engine: ValidationEngine) -> None:
    road = _road([GeoPoint(LAT, LNG), GeoPoint(LAT - 0.01, LNG)])
    area = _area(
        [GeoPoint(LAT, LNG), GeoPoint(LAT + 0.01, LNG), GeoPoint(LAT, LNG + 0.01)],
        rtype=RestrictionType.SPEED_LIMIT,
        speed=0,
    )
    results = val_engine.validate([road], [], [], [area])
    ids = [r.rule_id for r in _errors(results)]
    assert "area.speed_limit_positive" in ids


# ------------------------------------------------------------------
# Happy path
# ------------------------------------------------------------------


def test_valid_workspace_no_results(val_engine: ValidationEngine) -> None:
    road = _road([GeoPoint(LAT, LNG), GeoPoint(LAT - 0.01, LNG)], name="Rua A")
    wp = _waypoint(GeoPoint(LAT - 0.005, LNG), road_name="Rua A")
    results = val_engine.validate([road], [wp], [], [])
    errors = _errors(results)
    assert len(errors) == 0


def test_can_publish_with_warnings(val_engine: ValidationEngine) -> None:
    # Road with no waypoints → WARNING (not ERROR) → can still publish
    road = _road([GeoPoint(LAT, LNG), GeoPoint(LAT - 0.01, LNG)])
    results = val_engine.validate([road], [], [], [])
    errors = _errors(results)
    warnings = _warnings(results)
    assert len(errors) == 0
    assert len(warnings) > 0  # road.no_waypoints warning
