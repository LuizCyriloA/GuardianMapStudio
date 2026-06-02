from __future__ import annotations

import time

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from guardianmapstudio.database.models import (
    ProjectModel,
    RoadModel,
    WaypointModel,
    WorkspaceModel,
)

EXPECTED_TABLES = {
    "crossroads",
    "entity_versions",
    "export_history",
    "projects",
    "restricted_areas",
    "road_versions",
    "roads",
    "validation_results",
    "versions",
    "waypoints",
    "workspaces",
}


def test_create_tables_all_11(db_engine):  # type: ignore[no-untyped-def]
    tables = set(inspect(db_engine).get_table_names())
    assert tables == EXPECTED_TABLES, f"Tables mismatch: {tables}"


def test_road_name_unique_constraint(db_session):  # type: ignore[no-untyped-def]
    project = ProjectModel(name="P1", description="")
    db_session.add(project)
    db_session.flush()

    ws = WorkspaceModel(project_id=project.id, state="draft")
    db_session.add(ws)
    db_session.flush()

    coords = '[{"lat": -20.81, "lng": -49.37}, {"lat": -20.82, "lng": -49.38}]'
    r1 = RoadModel(
        workspace_id=ws.id,
        name="Rua A",
        coordinates=coords,
        speed_limit_kmh=20,
        direction="two_way",
        width_meters=6.0,
    )
    db_session.add(r1)
    db_session.flush()

    r2 = RoadModel(
        workspace_id=ws.id,
        name="Rua A",
        coordinates=coords,
        speed_limit_kmh=20,
        direction="two_way",
        width_meters=6.0,
    )
    db_session.add(r2)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_waypoint_type_check_constraint(db_session):  # type: ignore[no-untyped-def]
    project = ProjectModel(name="P2", description="")
    db_session.add(project)
    db_session.flush()

    ws = WorkspaceModel(project_id=project.id, state="draft")
    db_session.add(ws)
    db_session.flush()

    wp = WaypointModel(
        workspace_id=ws.id,
        name="Bad",
        waypoint_type="invalid_type",
        latitude=-20.81,
        longitude=-49.37,
        extra_data="{}",
    )
    db_session.add(wp)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_workspace_state_check_constraint(db_session):  # type: ignore[no-untyped-def]
    project = ProjectModel(name="P3", description="")
    db_session.add(project)
    db_session.flush()

    ws = WorkspaceModel(project_id=project.id, state="invalid_state")
    db_session.add(ws)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_double_precision_preserved(db_session):  # type: ignore[no-untyped-def]
    project = ProjectModel(name="P4", description="")
    db_session.add(project)
    db_session.flush()

    ws = WorkspaceModel(project_id=project.id, state="draft")
    db_session.add(ws)
    db_session.flush()

    lat = -20.8123456
    lng = -49.3765432
    wp = WaypointModel(
        workspace_id=ws.id,
        name="Precision",
        waypoint_type="landmark",
        latitude=lat,
        longitude=lng,
        extra_data="{}",
    )
    db_session.add(wp)
    db_session.commit()
    db_session.expire(wp)

    fetched = db_session.get(WaypointModel, wp.id)
    assert fetched is not None
    assert abs(fetched.latitude - lat) < 1e-7
    assert abs(fetched.longitude - lng) < 1e-7


def test_updated_at_changes_on_update(db_session):  # type: ignore[no-untyped-def]
    project = ProjectModel(name="P5", description="")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    original_updated = project.updated_at
    time.sleep(0.01)

    project.name = "P5 updated"
    db_session.commit()
    db_session.refresh(project)

    assert project.updated_at >= original_updated


def test_cascade_delete_workspace(db_session):  # type: ignore[no-untyped-def]
    project = ProjectModel(name="P6", description="")
    db_session.add(project)
    db_session.flush()

    ws = WorkspaceModel(project_id=project.id, state="draft")
    db_session.add(ws)
    db_session.flush()

    coords = '[{"lat": -20.81, "lng": -49.37}, {"lat": -20.82, "lng": -49.38}]'
    road = RoadModel(
        workspace_id=ws.id,
        name="Rua Cascade",
        coordinates=coords,
        speed_limit_kmh=30,
        direction="two_way",
        width_meters=5.0,
    )
    db_session.add(road)
    db_session.commit()

    road_id = road.id
    db_session.delete(ws)
    db_session.commit()

    assert db_session.get(RoadModel, road_id) is None
