from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from guardianmapstudio.database.models import Base
from guardianmapstudio.database.repository import (
    ExportRepository,
    MapRepository,
    ProjectRepository,
    ValidationRepository,
    VersionRepository,
    WorkspaceRepository,
)
from guardianmapstudio.domain.contracts import (
    GeoPoint,
    Project,
    ValidationResult,
    ValidationSeverity,
    WorkspaceState,
)


@pytest.fixture
def session():  # type: ignore[no-untyped-def]
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as s:
        yield s
    engine.dispose()


def test_create_project(session):  # type: ignore[no-untyped-def]
    repo = ProjectRepository(session)
    project = repo.create("Condomínio A", "Descrição")
    assert project.id > 0
    assert project.name == "Condomínio A"
    assert project.description == "Descrição"


def test_get_project_returns_domain(session):  # type: ignore[no-untyped-def]
    repo = ProjectRepository(session)
    created = repo.create("Projeto B")
    fetched = repo.get_by_id(created.id)
    assert isinstance(fetched, Project)
    assert fetched is not None
    assert fetched.id == created.id


def test_create_workspace_from_project(session):  # type: ignore[no-untyped-def]
    proj_repo = ProjectRepository(session)
    ws_repo = WorkspaceRepository(session)
    project = proj_repo.create("Projeto C")
    # BR-01: create() auto-creates DRAFT workspace
    ws = ws_repo.get_active_draft(project.id)
    assert ws is not None
    assert ws.state == WorkspaceState.DRAFT
    assert ws.project_id == project.id


def test_get_active_draft(session):  # type: ignore[no-untyped-def]
    proj_repo = ProjectRepository(session)
    ws_repo = WorkspaceRepository(session)
    project = proj_repo.create("Projeto D")
    draft = ws_repo.get_active_draft(project.id)
    assert draft is not None
    assert draft.state == WorkspaceState.DRAFT


def test_create_road_returns_domain(session):  # type: ignore[no-untyped-def]
    proj_repo = ProjectRepository(session)
    ws_repo = WorkspaceRepository(session)
    map_repo = MapRepository(session)

    project = proj_repo.create("Projeto E")
    ws = ws_repo.get_active_draft(project.id)
    assert ws is not None

    coords = json.dumps([{"lat": -20.81, "lng": -49.37}, {"lat": -20.82, "lng": -49.38}],
                        ensure_ascii=False)
    road = map_repo.create_road(ws.id, "Rua Principal", coords, 30, "two_way", 6.0)
    assert road.id > 0
    assert road.name == "Rua Principal"
    assert len(road.coordinates) == 2


def test_road_coordinates_are_geopoints(session):  # type: ignore[no-untyped-def]
    proj_repo = ProjectRepository(session)
    ws_repo = WorkspaceRepository(session)
    map_repo = MapRepository(session)

    project = proj_repo.create("Projeto F")
    ws = ws_repo.get_active_draft(project.id)
    assert ws is not None

    coords = json.dumps([{"lat": -20.81, "lng": -49.37}, {"lat": -20.82, "lng": -49.38}],
                        ensure_ascii=False)
    road = map_repo.create_road(ws.id, "Rua Coords", coords, 20, "two_way", 5.0)
    for pt in road.coordinates:
        assert isinstance(pt, GeoPoint)


def test_waypoint_position_is_geopoint(session):  # type: ignore[no-untyped-def]
    proj_repo = ProjectRepository(session)
    ws_repo = WorkspaceRepository(session)
    map_repo = MapRepository(session)

    project = proj_repo.create("Projeto G")
    ws = ws_repo.get_active_draft(project.id)
    assert ws is not None

    wp = map_repo.create_waypoint(
        ws.id, "Parada", "stop_sign", -20.81, -49.37, None, None, "{}"
    )
    assert isinstance(wp.position, GeoPoint)
    assert wp.position.latitude == pytest.approx(-20.81)
    assert wp.position.longitude == pytest.approx(-49.37)


def test_waypoint_extra_data_is_dict(session):  # type: ignore[no-untyped-def]
    proj_repo = ProjectRepository(session)
    ws_repo = WorkspaceRepository(session)
    map_repo = MapRepository(session)

    project = proj_repo.create("Projeto H")
    ws = ws_repo.get_active_draft(project.id)
    assert ws is not None

    extra = json.dumps({"height_cm": 5}, ensure_ascii=False)
    wp = map_repo.create_waypoint(
        ws.id, "Lombada", "speed_bump", -20.81, -49.37, None, None, extra
    )
    assert isinstance(wp.extra_data, dict)
    assert wp.extra_data["height_cm"] == 5


def test_version_number_increments(session):  # type: ignore[no-untyped-def]
    proj_repo = ProjectRepository(session)
    ver_repo = VersionRepository(session)

    project = proj_repo.create("Projeto I")
    v1 = ver_repo.create(project.id, "v1", 1, 0, 0, 0)
    v2 = ver_repo.create(project.id, "v2", 2, 1, 0, 0)
    v3 = ver_repo.create(project.id, "v3", 3, 2, 1, 0)

    assert v1.version_number == 1
    assert v2.version_number == 2
    assert v3.version_number == 3


def test_validation_replace_results(session):  # type: ignore[no-untyped-def]
    proj_repo = ProjectRepository(session)
    ws_repo = WorkspaceRepository(session)
    val_repo = ValidationRepository(session)

    project = proj_repo.create("Projeto J")
    ws = ws_repo.get_active_draft(project.id)
    assert ws is not None

    first_batch = [
        ValidationResult(
            severity=ValidationSeverity.ERROR,
            rule_id="road.min_points",
            message="msg1",
            affected_entity_type="road",
            affected_entity_id=1,
        )
    ]
    val_repo.replace_results(ws.id, first_batch)
    assert val_repo.count_errors(ws.id) == 1

    second_batch = [
        ValidationResult(
            severity=ValidationSeverity.WARNING,
            rule_id="road.no_waypoints",
            message="msg2",
            affected_entity_type="road",
            affected_entity_id=1,
        ),
        ValidationResult(
            severity=ValidationSeverity.WARNING,
            rule_id="road.no_waypoints",
            message="msg3",
            affected_entity_type="road",
            affected_entity_id=2,
        ),
    ]
    val_repo.replace_results(ws.id, second_batch)
    assert val_repo.count_errors(ws.id) == 0
    assert len(val_repo.get_results(ws.id)) == 2


def test_export_record_created(session):  # type: ignore[no-untyped-def]
    proj_repo = ProjectRepository(session)
    ver_repo = VersionRepository(session)
    exp_repo = ExportRepository(session)

    project = proj_repo.create("Projeto K")
    version = ver_repo.create(project.id, "v1", 1, 0, 0, 0)

    record = exp_repo.create_record(version.id, project.id, "/exports/map.json", 1024)
    assert record.id > 0
    assert record.file_size_bytes == 1024

    history = exp_repo.get_history(project.id)
    assert len(history) == 1
    assert history[0].file_path == "/exports/map.json"
