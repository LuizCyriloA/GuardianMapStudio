from __future__ import annotations

from guardianmapstudio.domain.events import (
    BaseEvent,
    CrossroadCreatedEvent,
    CrossroadDeletedEvent,
    ExportCreatedEvent,
    RestrictedAreaCreatedEvent,
    RestrictedAreaDeletedEvent,
    RestrictedAreaUpdatedEvent,
    RoadCreatedEvent,
    RoadDeletedEvent,
    RoadUpdatedEvent,
    ValidationRunEvent,
    WaypointCreatedEvent,
    WaypointDeletedEvent,
    WaypointUpdatedEvent,
    WorkspaceCreatedEvent,
    WorkspacePublishedEvent,
)


def test_base_event_has_timestamp() -> None:
    e = BaseEvent()
    assert e.timestamp is not None


def test_workspace_created_event() -> None:
    e = WorkspaceCreatedEvent(workspace_id=1, project_id=2, base_version_id=None)
    assert e.workspace_id == 1
    assert e.project_id == 2
    assert e.base_version_id is None


def test_workspace_published_event() -> None:
    e = WorkspacePublishedEvent(workspace_id=1, version_id=5, project_id=2, version_number=3)
    assert e.version_id == 5
    assert e.version_number == 3


def test_validation_run_event() -> None:
    e = ValidationRunEvent(workspace_id=1, error_count=2, warning_count=1, duration_ms=42.5)
    assert e.error_count == 2
    assert e.duration_ms == 42.5


def test_export_created_event() -> None:
    e = ExportCreatedEvent(version_id=1, project_id=2, file_path="/tmp/f.json", file_size_bytes=1024)
    assert e.file_path == "/tmp/f.json"


def test_road_events() -> None:
    assert RoadCreatedEvent(workspace_id=1, road_id=2, road_name="R").road_name == "R"
    assert RoadUpdatedEvent(workspace_id=1, road_id=2).road_id == 2
    assert RoadDeletedEvent(workspace_id=1, road_id=2, road_name="R").road_id == 2


def test_waypoint_events() -> None:
    assert WaypointCreatedEvent(workspace_id=1, waypoint_id=3, waypoint_type="landmark").waypoint_id == 3
    assert WaypointUpdatedEvent(workspace_id=1, waypoint_id=3).waypoint_id == 3
    assert WaypointDeletedEvent(workspace_id=1, waypoint_id=3).waypoint_id == 3


def test_crossroad_events() -> None:
    assert CrossroadCreatedEvent(workspace_id=1, crossroad_id=4).crossroad_id == 4
    assert CrossroadDeletedEvent(workspace_id=1, crossroad_id=4).crossroad_id == 4


def test_area_events() -> None:
    assert RestrictedAreaCreatedEvent(workspace_id=1, area_id=5).area_id == 5
    assert RestrictedAreaUpdatedEvent(workspace_id=1, area_id=5).area_id == 5
    assert RestrictedAreaDeletedEvent(workspace_id=1, area_id=5).area_id == 5
