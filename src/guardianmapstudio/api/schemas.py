from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class GeoPointDTO(BaseModel):
    lat: float
    lng: float


# --- Project ---


class ProjectCreate(BaseModel):
    name: str
    description: str = ""


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int


# --- Version ---


class VersionResponse(BaseModel):
    id: int
    project_id: int
    version_number: int
    name: str
    published_at: datetime
    road_count: int
    waypoint_count: int
    crossroad_count: int
    restricted_area_count: int
    model_config = ConfigDict(from_attributes=True)


class VersionListResponse(BaseModel):
    items: list[VersionResponse]
    total: int


# --- Workspace ---


class WorkspaceResponse(BaseModel):
    id: int
    project_id: int
    state: Literal["draft", "published"]
    base_version_id: int | None
    created_at: datetime
    updated_at: datetime
    last_validated_at: datetime | None
    has_validation_errors: bool
    model_config = ConfigDict(from_attributes=True)


class PublishRequest(BaseModel):
    version_name: str


# --- Road ---


class RoadCreate(BaseModel):
    name: str
    coordinates: list[GeoPointDTO]
    speed_limit_kmh: int = 20
    direction: str = "two_way"
    width_meters: float = 6.0


class RoadUpdate(BaseModel):
    name: str | None = None
    coordinates: list[GeoPointDTO] | None = None
    speed_limit_kmh: int | None = None
    direction: str | None = None
    width_meters: float | None = None


class RoadResponse(BaseModel):
    id: int
    workspace_id: int
    name: str
    coordinates: list[GeoPointDTO]
    speed_limit_kmh: int
    direction: str
    width_meters: float
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Waypoint ---


class WaypointCreate(BaseModel):
    name: str
    waypoint_type: str
    lat: float
    lng: float
    road_name: str | None = None
    heading_degrees: float | None = None
    extra_data: dict[str, Any] = {}
    active: bool = True


class WaypointUpdate(BaseModel):
    name: str | None = None
    waypoint_type: str | None = None
    lat: float | None = None
    lng: float | None = None
    road_name: str | None = None
    heading_degrees: float | None = None
    extra_data: dict[str, Any] | None = None
    active: bool | None = None


class WaypointResponse(BaseModel):
    id: int
    workspace_id: int
    name: str
    waypoint_type: str
    lat: float
    lng: float
    road_name: str | None
    heading_degrees: float | None
    extra_data: dict[str, Any]
    active: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Crossroad ---


class CrossroadCreate(BaseModel):
    road_a_name: str
    road_b_name: str
    lat: float
    lng: float


class CrossroadResponse(BaseModel):
    id: int
    workspace_id: int
    road_a_name: str
    road_b_name: str
    lat: float
    lng: float
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Restricted Area ---


class RestrictedAreaCreate(BaseModel):
    name: str
    polygon: list[GeoPointDTO]
    restriction_type: str
    speed_limit_kmh: int | None = None
    active: bool = True


class RestrictedAreaUpdate(BaseModel):
    name: str | None = None
    polygon: list[GeoPointDTO] | None = None
    restriction_type: str | None = None
    speed_limit_kmh: int | None = None
    active: bool | None = None


class RestrictedAreaResponse(BaseModel):
    id: int
    workspace_id: int
    name: str
    polygon: list[GeoPointDTO]
    restriction_type: str
    speed_limit_kmh: int | None
    active: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Validation ---


class ValidationResultResponse(BaseModel):
    id: int
    severity: str
    rule_id: str
    message: str
    affected_entity_type: str
    affected_entity_id: int


class ValidationSummaryResponse(BaseModel):
    workspace_id: int
    error_count: int
    warning_count: int
    can_publish: bool
    results: list[ValidationResultResponse]
    validated_at: datetime


# --- Map (bulk load) ---


class MapResponse(BaseModel):
    roads: list[RoadResponse]
    waypoints: list[WaypointResponse]
    crossroads: list[CrossroadResponse]
    restricted_areas: list[RestrictedAreaResponse]


# --- Snap ---


class SnapRequest(BaseModel):
    lat: float
    lng: float


class SnapResponse(BaseModel):
    original: GeoPointDTO
    snapped_to: GeoPointDTO
    snapped: bool
    distance_meters: float


# --- Export ---


class ExportResponse(BaseModel):
    export_id: int
    version_id: int
    file_path: str
    file_size_bytes: int
    exported_at: datetime


class ExportHistoryResponse(BaseModel):
    items: list[ExportResponse]
    total: int


# --- Error ---


class ErrorResponse(BaseModel):
    error: str
    message: str
    detail: dict[str, Any] = {}


# --- OSM Import (appended) ---


class ParsedRoadDTO(BaseModel):
    osm_way_id: int
    name: str
    coordinates: list[GeoPointDTO]
    direction: str           # "two_way" | "one_way"
    speed_limit_kmh: int
    width_meters: float
    highway_tag: str         # e.g. "residential"
    had_name: bool
    osm_warnings: list[str]


class OsmPreviewResponse(BaseModel):
    """Returned by POST /osm/preview. The frontend uses osm_way_id to
    correlate the operator's selection in the subsequent /osm/import call."""
    roads: list[ParsedRoadDTO]
    total_ways_in_file: int
    skipped_ways: int
    skipped_reasons: dict[str, int]


class OsmImportRequest(BaseModel):
    """Payload for POST /osm/import — sent after the operator confirms preview."""
    roads: list[ParsedRoadDTO]
    replace_existing: bool = False


class OsmImportResponse(BaseModel):
    workspace_id: int
    created_count: int
    deleted_existing: int
    renamed: list[dict[str, str]]   # [{"from": "...", "to": "..."}, ...]
