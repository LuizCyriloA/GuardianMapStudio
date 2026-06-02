from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class BaseEvent:
    timestamp: dt.datetime = field(default_factory=lambda: dt.datetime.now(dt.UTC))


@dataclass(frozen=True, slots=True)
class WorkspaceCreatedEvent(BaseEvent):
    workspace_id: int = 0
    project_id: int = 0
    base_version_id: int | None = None


@dataclass(frozen=True, slots=True)
class WorkspacePublishedEvent(BaseEvent):
    workspace_id: int = 0
    version_id: int = 0
    project_id: int = 0
    version_number: int = 0


@dataclass(frozen=True, slots=True)
class ValidationRunEvent(BaseEvent):
    workspace_id: int = 0
    error_count: int = 0
    warning_count: int = 0
    duration_ms: float = 0.0


@dataclass(frozen=True, slots=True)
class ExportCreatedEvent(BaseEvent):
    version_id: int = 0
    project_id: int = 0
    file_path: str = ""
    file_size_bytes: int = 0


@dataclass(frozen=True, slots=True)
class RoadCreatedEvent(BaseEvent):
    workspace_id: int = 0
    road_id: int = 0
    road_name: str = ""


@dataclass(frozen=True, slots=True)
class RoadUpdatedEvent(BaseEvent):
    workspace_id: int = 0
    road_id: int = 0


@dataclass(frozen=True, slots=True)
class RoadDeletedEvent(BaseEvent):
    workspace_id: int = 0
    road_id: int = 0
    road_name: str = ""


@dataclass(frozen=True, slots=True)
class WaypointCreatedEvent(BaseEvent):
    workspace_id: int = 0
    waypoint_id: int = 0
    waypoint_type: str = ""


@dataclass(frozen=True, slots=True)
class WaypointUpdatedEvent(BaseEvent):
    workspace_id: int = 0
    waypoint_id: int = 0


@dataclass(frozen=True, slots=True)
class WaypointDeletedEvent(BaseEvent):
    workspace_id: int = 0
    waypoint_id: int = 0


@dataclass(frozen=True, slots=True)
class CrossroadCreatedEvent(BaseEvent):
    workspace_id: int = 0
    crossroad_id: int = 0


@dataclass(frozen=True, slots=True)
class CrossroadDeletedEvent(BaseEvent):
    workspace_id: int = 0
    crossroad_id: int = 0


@dataclass(frozen=True, slots=True)
class RestrictedAreaCreatedEvent(BaseEvent):
    workspace_id: int = 0
    area_id: int = 0


@dataclass(frozen=True, slots=True)
class RestrictedAreaUpdatedEvent(BaseEvent):
    workspace_id: int = 0
    area_id: int = 0


@dataclass(frozen=True, slots=True)
class RestrictedAreaDeletedEvent(BaseEvent):
    workspace_id: int = 0
    area_id: int = 0
