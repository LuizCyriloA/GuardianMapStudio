from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from guardianmapstudio.domain.contracts import (
    Crossroad,
    GeoPoint,
    RestrictedArea,
    RestrictionType,
    Road,
    RoadDirection,
    Version,
    Waypoint,
    WaypointType,
)
from guardianmapstudio.export.guardian_exporter import GuardianExporter

LAT = -20.81
LNG = -49.37
_NOW = datetime(2024, 1, 1, tzinfo=UTC)


def _version() -> Version:
    return Version(
        id=1,
        project_id=1,
        version_number=1,
        name="v1.0",
        published_at=_NOW,
        road_count=1,
        waypoint_count=1,
        crossroad_count=0,
        restricted_area_count=0,
    )


def _road(name: str = "Rua A") -> Road:
    return Road(
        id=1,
        workspace_id=1,
        name=name,
        coordinates=[GeoPoint(LAT, LNG), GeoPoint(LAT - 0.01, LNG)],
        speed_limit_kmh=30,
        direction=RoadDirection.TWO_WAY,
        width_meters=6.0,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _waypoint(
    name: str = "WP",
    heading: float | None = None,
    active: bool = True,
    road_name: str | None = "Rua A",
) -> Waypoint:
    return Waypoint(
        id=1,
        workspace_id=1,
        name=name,
        waypoint_type=WaypointType.LANDMARK,
        position=GeoPoint(LAT, LNG),
        road_name=road_name,
        heading_degrees=heading,
        extra_data={},
        created_at=_NOW,
        updated_at=_NOW,
        active=active,
    )


def _crossroad() -> Crossroad:
    return Crossroad(
        id=1,
        workspace_id=1,
        road_a_name="Rua A",
        road_b_name="Rua B",
        position=GeoPoint(LAT, LNG),
        created_at=_NOW,
    )


def _area() -> RestrictedArea:
    return RestrictedArea(
        id=1,
        workspace_id=1,
        name="Zona Restrita",
        polygon=[GeoPoint(LAT, LNG), GeoPoint(LAT + 0.01, LNG), GeoPoint(LAT, LNG + 0.01)],
        restriction_type=RestrictionType.NO_ENTRY,
        speed_limit_kmh=None,
        created_at=_NOW,
        updated_at=_NOW,
    )


@pytest.fixture
def exporter() -> GuardianExporter:
    return GuardianExporter()


@pytest.fixture
def tmp_path_file(tmp_path: Path) -> Path:
    return tmp_path / "export.json"


def _run_export(
    exporter: GuardianExporter,
    output: Path,
    roads: list[Road] | None = None,
    waypoints: list[Waypoint] | None = None,
    crossroads: list[Crossroad] | None = None,
    areas: list[RestrictedArea] | None = None,
) -> dict:  # type: ignore[type-arg]
    exporter.export(
        version=_version(),
        project_name="Condomínio Test",
        roads=roads or [_road()],
        waypoints=waypoints or [_waypoint()],
        crossroads=crossroads or [],
        areas=areas or [],
        output_path=output,
    )
    return json.loads(output.read_text(encoding="utf-8"))


# ------------------------------------------------------------------
# JSON validity
# ------------------------------------------------------------------


def test_export_produces_valid_json(
    exporter: GuardianExporter, tmp_path_file: Path
) -> None:
    size = exporter.export(
        version=_version(),
        project_name="Test",
        roads=[_road()],
        waypoints=[_waypoint()],
        crossroads=[],
        areas=[],
        output_path=tmp_path_file,
    )
    content = tmp_path_file.read_text(encoding="utf-8")
    data = json.loads(content)
    assert isinstance(data, dict)
    assert size == len(content.encode("utf-8"))


def test_export_meta_fields_present(
    exporter: GuardianExporter, tmp_path_file: Path
) -> None:
    data = _run_export(exporter, tmp_path_file)
    meta = data["meta"]
    assert "exported_by" in meta
    assert "version_id" in meta
    assert "version_name" in meta
    assert "project_name" in meta
    assert "exported_at" in meta
    assert "schema_version" in meta


def test_export_schema_version_1_0(
    exporter: GuardianExporter, tmp_path_file: Path
) -> None:
    data = _run_export(exporter, tmp_path_file)
    assert data["meta"]["schema_version"] == "1.0"


# ------------------------------------------------------------------
# Waypoint serialization
# ------------------------------------------------------------------


def test_waypoint_type_key_is_type(
    exporter: GuardianExporter, tmp_path_file: Path
) -> None:
    data = _run_export(exporter, tmp_path_file, waypoints=[_waypoint()])
    wp = data["waypoints"][0]
    assert "type" in wp
    assert "waypoint_type" not in wp


def test_waypoint_road_key_present(
    exporter: GuardianExporter, tmp_path_file: Path
) -> None:
    wp_no_road = _waypoint(road_name=None)
    data = _run_export(exporter, tmp_path_file, waypoints=[wp_no_road])
    wp = data["waypoints"][0]
    assert "road" in wp
    assert wp["road"] is None


def test_heading_omitted_when_null(
    exporter: GuardianExporter, tmp_path_file: Path
) -> None:
    data = _run_export(exporter, tmp_path_file, waypoints=[_waypoint(heading=None)])
    wp = data["waypoints"][0]
    assert "heading_degrees" not in wp


def test_heading_present_when_set(
    exporter: GuardianExporter, tmp_path_file: Path
) -> None:
    data = _run_export(exporter, tmp_path_file, waypoints=[_waypoint(heading=180.5)])
    wp = data["waypoints"][0]
    assert "heading_degrees" in wp
    assert wp["heading_degrees"] == pytest.approx(180.5, abs=0.1)


def test_extra_data_always_present(
    exporter: GuardianExporter, tmp_path_file: Path
) -> None:
    data = _run_export(exporter, tmp_path_file, waypoints=[_waypoint()])
    wp = data["waypoints"][0]
    assert "extra_data" in wp
    assert wp["extra_data"] == {}


def test_inactive_waypoints_excluded(
    exporter: GuardianExporter, tmp_path_file: Path
) -> None:
    active_wp = _waypoint(name="Active", active=True)
    inactive_wp = Waypoint(
        id=2,
        workspace_id=1,
        name="Inactive",
        waypoint_type=WaypointType.LANDMARK,
        position=GeoPoint(LAT + 0.001, LNG),
        road_name="Rua A",
        heading_degrees=None,
        extra_data={},
        created_at=_NOW,
        updated_at=_NOW,
        active=False,
    )
    data = _run_export(exporter, tmp_path_file, waypoints=[active_wp, inactive_wp])
    names = [w["name"] for w in data["waypoints"]]
    assert "Active" in names
    assert "Inactive" not in names


# ------------------------------------------------------------------
# Coordinate precision
# ------------------------------------------------------------------


def test_coordinate_precision_7dp(
    exporter: GuardianExporter, tmp_path_file: Path
) -> None:
    lat_precise = -20.8123456789
    lng_precise = -49.3765432109
    wp = Waypoint(
        id=1,
        workspace_id=1,
        name="Precise",
        waypoint_type=WaypointType.LANDMARK,
        position=GeoPoint(lat_precise, lng_precise),
        road_name=None,
        heading_degrees=None,
        extra_data={},
        created_at=_NOW,
        updated_at=_NOW,
    )
    data = _run_export(exporter, tmp_path_file, waypoints=[wp])
    w = data["waypoints"][0]
    # Must be rounded to 7 decimal places
    assert w["lat"] == round(lat_precise, 7)
    assert w["lng"] == round(lng_precise, 7)


def test_export_utf8_accented_names(
    exporter: GuardianExporter, tmp_path_file: Path
) -> None:
    road_accented = Road(
        id=1,
        workspace_id=1,
        name="Rua São José",
        coordinates=[GeoPoint(LAT, LNG), GeoPoint(LAT - 0.01, LNG)],
        speed_limit_kmh=20,
        direction=RoadDirection.TWO_WAY,
        width_meters=5.0,
        created_at=_NOW,
        updated_at=_NOW,
    )
    data = _run_export(exporter, tmp_path_file, roads=[road_accented], waypoints=[])
    road_names = [r["name"] for r in data["roads"]]
    assert "Rua São José" in road_names
    # Verify no unicode escape sequences in file
    raw = tmp_path_file.read_text(encoding="utf-8")
    assert "\\u00e3" not in raw  # ã must not be escaped
