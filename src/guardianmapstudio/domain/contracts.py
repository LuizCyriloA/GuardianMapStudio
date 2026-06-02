from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

# ---------------------------------------------------------------------------
# Enums — string values MUST match Guardian's enums exactly
# ---------------------------------------------------------------------------

class WorkspaceState(str, Enum):
    DRAFT     = "draft"
    PUBLISHED = "published"


class ValidationSeverity(str, Enum):
    ERROR   = "error"
    WARNING = "warning"


class WaypointType(str, Enum):
    STOP_SIGN  = "stop_sign"
    SPEED_BUMP = "speed_bump"
    GATE       = "gate"
    LANDMARK   = "landmark"
    CURVE      = "curve"
    CROSSROAD  = "crossroad"
    STOP_ZONE  = "stop_zone"


class GateType(str, Enum):
    ENTRY       = "entry"
    EXIT        = "exit"
    ENTRY_EXIT  = "entry_exit"
    INTERNAL    = "internal"


class RestrictionType(str, Enum):
    SPEED_LIMIT      = "speed_limit"
    NO_ENTRY         = "no_entry"
    PEDESTRIAN_ONLY  = "pedestrian_only"


class RoadDirection(str, Enum):
    TWO_WAY = "two_way"
    ONE_WAY = "one_way"


# ---------------------------------------------------------------------------
# Value Objects — immutable, no identity
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class GeoPoint:
    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not (-90.0 <= self.latitude <= 90.0):
            raise ValueError(f"Invalid latitude: {self.latitude}")
        if not (-180.0 <= self.longitude <= 180.0):
            raise ValueError(f"Invalid longitude: {self.longitude}")

    def to_export(self) -> dict[str, float]:
        return {"lat": self.latitude, "lng": self.longitude}


@dataclass(frozen=True, slots=True)
class ValidationResult:
    severity: ValidationSeverity
    rule_id: str
    message: str
    affected_entity_type: str
    affected_entity_id: int

    @property
    def is_blocking(self) -> bool:
        return self.severity == ValidationSeverity.ERROR


@dataclass(frozen=True, slots=True)
class ExportMeta:
    exported_by: str
    version_id: int
    version_name: str
    project_name: str
    exported_at: str
    schema_version: str


@dataclass(frozen=True, slots=True)
class SnapResult:
    original: GeoPoint
    snapped_to: GeoPoint
    snapped: bool
    distance_meters: float


# ---------------------------------------------------------------------------
# Aggregates — have identity (id field), correspond to database tables
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Project:
    id: int
    name: str
    description: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class Version:
    id: int
    project_id: int
    version_number: int
    name: str
    published_at: datetime
    road_count: int
    waypoint_count: int
    crossroad_count: int
    restricted_area_count: int


@dataclass(frozen=True, slots=True)
class Workspace:
    id: int
    project_id: int
    state: WorkspaceState
    base_version_id: int | None
    created_at: datetime
    updated_at: datetime
    last_validated_at: datetime | None
    has_validation_errors: bool


@dataclass(frozen=True, slots=True)
class Road:
    id: int
    workspace_id: int
    name: str
    coordinates: list[GeoPoint]    # TREAT AS READ-ONLY (frozen protects ref, not contents)
    speed_limit_kmh: int
    direction: RoadDirection
    width_meters: float
    created_at: datetime
    updated_at: datetime

    @property
    def point_count(self) -> int:
        return len(self.coordinates)

    @property
    def is_valid_geometry(self) -> bool:
        return len(self.coordinates) >= 2


@dataclass(frozen=True, slots=True)
class Waypoint:
    id: int
    workspace_id: int
    name: str
    waypoint_type: WaypointType
    position: GeoPoint
    road_name: str | None
    heading_degrees: float | None
    extra_data: dict[str, Any]     # TREAT AS READ-ONLY
    created_at: datetime
    updated_at: datetime
    active: bool = True


@dataclass(frozen=True, slots=True)
class Crossroad:
    id: int
    workspace_id: int
    road_a_name: str
    road_b_name: str
    position: GeoPoint
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RestrictedArea:
    id: int
    workspace_id: int
    name: str
    polygon: list[GeoPoint]        # TREAT AS READ-ONLY
    restriction_type: RestrictionType
    speed_limit_kmh: int | None
    created_at: datetime
    updated_at: datetime
    active: bool = True

    @property
    def is_valid_geometry(self) -> bool:
        return len(self.polygon) >= 3


@dataclass(frozen=True, slots=True)
class ExportRecord:
    id: int
    version_id: int
    project_id: int
    exported_at: datetime
    file_path: str
    file_size_bytes: int
