from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query

from guardianmapstudio.api.deps import DbSession, SettingsDep
from guardianmapstudio.api.errors import ErrorCode
from guardianmapstudio.api.routers._validation_helper import _run_validation_after_write
from guardianmapstudio.api.schemas import WaypointCreate, WaypointResponse, WaypointUpdate
from guardianmapstudio.database.repository import MapRepository, WorkspaceRepository
from guardianmapstudio.domain.contracts import GateType, GeoPoint, Waypoint, WaypointType
from guardianmapstudio.geometry.engine import GeometryEngine
from guardianmapstudio.geometry.snap import SnapEngine

router = APIRouter()


def _waypoint_to_response(wp: Waypoint) -> WaypointResponse:
    return WaypointResponse(
        id=wp.id,
        workspace_id=wp.workspace_id,
        name=wp.name,
        waypoint_type=wp.waypoint_type.value,
        lat=wp.position.latitude,
        lng=wp.position.longitude,
        road_name=wp.road_name,
        heading_degrees=wp.heading_degrees,
        extra_data=wp.extra_data,
        active=wp.active,
        created_at=wp.created_at,
        updated_at=wp.updated_at,
    )


def _require_draft(workspace_id: int, db: DbSession) -> None:
    from guardianmapstudio.domain.contracts import WorkspaceState
    ws = WorkspaceRepository(db).get_by_id(workspace_id)
    if ws is None:
        raise HTTPException(
            status_code=404,
            detail={"error": ErrorCode.NOT_FOUND.value, "message": f"Workspace {workspace_id} not found"},
        )
    if ws.state != WorkspaceState.DRAFT:
        raise HTTPException(
            status_code=409,
            detail={"error": ErrorCode.WORKSPACE_NOT_DRAFT.value, "message": "Workspace is not in DRAFT state"},
        )


def _validate_waypoint_type_rules(wtype: str, extra_data: dict) -> None:  # type: ignore[type-arg]
    """Validate type-specific business rules before saving. Raises 422 on failure."""
    if wtype == WaypointType.SPEED_BUMP.value:
        height = extra_data.get("height_cm")
        if height is None or not isinstance(height, int | float) or height <= 0:
            raise HTTPException(
                status_code=422,
                detail={"error": ErrorCode.VALIDATION_ERRORS_BLOCKING.value,
                        "message": "Speed bump must have extra_data.height_cm > 0"},
            )
    if wtype == WaypointType.GATE.value:
        gate_type = extra_data.get("gate_type")
        valid_gate_types = {gt.value for gt in GateType}
        if gate_type not in valid_gate_types:
            raise HTTPException(
                status_code=422,
                detail={"error": ErrorCode.VALIDATION_ERRORS_BLOCKING.value,
                        "message": f"Gate must have extra_data.gate_type in {sorted(valid_gate_types)}"},
            )


@router.get("/{workspace_id}/waypoints", response_model=list[WaypointResponse])
def list_waypoints(
    workspace_id: int,
    db: DbSession,
    waypoint_type: Annotated[str | None, Query(alias="type")] = None,
) -> list[WaypointResponse]:
    _require_draft(workspace_id, db)
    waypoints = MapRepository(db).get_waypoints(workspace_id)
    if waypoint_type is not None:
        waypoints = [w for w in waypoints if w.waypoint_type.value == waypoint_type]
    return [_waypoint_to_response(w) for w in waypoints]


@router.post("/{workspace_id}/waypoints", response_model=WaypointResponse, status_code=201)
def create_waypoint(workspace_id: int, body: WaypointCreate, db: DbSession, settings: SettingsDep) -> WaypointResponse:
    _require_draft(workspace_id, db)
    _validate_waypoint_type_rules(body.waypoint_type, body.extra_data)

    # Snap the new position against existing roads and waypoints
    repo = MapRepository(db)
    roads = repo.get_roads(workspace_id)
    existing_waypoints = repo.get_waypoints(workspace_id)

    all_points = [p for r in roads for p in r.coordinates]
    avg_lat = sum(p.latitude for p in all_points) / len(all_points) if all_points else body.lat
    avg_lng = sum(p.longitude for p in all_points) / len(all_points) if all_points else body.lng

    geo = GeometryEngine.from_centroid(avg_lat, avg_lng)
    snap_engine = SnapEngine(geo, tolerance_m=settings.snap_tolerance_m)
    new_point = GeoPoint(latitude=body.lat, longitude=body.lng)
    snap_result = snap_engine.snap(new_point, roads, existing_waypoints)

    final_lat = snap_result.snapped_to.latitude
    final_lng = snap_result.snapped_to.longitude
    extra_json = json.dumps(body.extra_data, ensure_ascii=False)

    wp = repo.create_waypoint(
        workspace_id=workspace_id,
        name=body.name,
        waypoint_type=body.waypoint_type,
        latitude=final_lat,
        longitude=final_lng,
        road_name=body.road_name,
        heading_degrees=body.heading_degrees,
        extra_data_json=extra_json,
    )
    _run_validation_after_write(workspace_id, db)
    return _waypoint_to_response(wp)


@router.get("/{workspace_id}/waypoints/{waypoint_id}", response_model=WaypointResponse)
def get_waypoint(workspace_id: int, waypoint_id: int, db: DbSession) -> WaypointResponse:
    wp = MapRepository(db).get_waypoint(waypoint_id)
    if wp is None or wp.workspace_id != workspace_id:
        raise HTTPException(
            status_code=404,
            detail={"error": ErrorCode.NOT_FOUND.value, "message": f"Waypoint {waypoint_id} not found"},
        )
    return _waypoint_to_response(wp)


@router.patch("/{workspace_id}/waypoints/{waypoint_id}", response_model=WaypointResponse)
def update_waypoint(workspace_id: int, waypoint_id: int, body: WaypointUpdate, db: DbSession) -> WaypointResponse:
    _require_draft(workspace_id, db)
    repo = MapRepository(db)
    existing = repo.get_waypoint(waypoint_id)
    if existing is None or existing.workspace_id != workspace_id:
        raise HTTPException(
            status_code=404,
            detail={"error": ErrorCode.NOT_FOUND.value, "message": f"Waypoint {waypoint_id} not found"},
        )

    updates: dict[str, Any] = {}
    new_wtype = body.waypoint_type if body.waypoint_type is not None else existing.waypoint_type.value
    new_extra = body.extra_data if body.extra_data is not None else existing.extra_data
    _validate_waypoint_type_rules(new_wtype, new_extra)

    if body.name is not None:
        updates["name"] = body.name
    if body.waypoint_type is not None:
        updates["waypoint_type"] = body.waypoint_type
    if body.lat is not None:
        updates["latitude"] = body.lat
    if body.lng is not None:
        updates["longitude"] = body.lng
    if body.road_name is not None:
        updates["road_name"] = body.road_name
    if body.heading_degrees is not None:
        updates["heading_degrees"] = body.heading_degrees
    if body.extra_data is not None:
        updates["extra_data"] = json.dumps(body.extra_data, ensure_ascii=False)
    if body.active is not None:
        updates["active"] = body.active

    wp = repo.update_waypoint(waypoint_id, **updates)
    if wp is None:
        raise HTTPException(
            status_code=404,
            detail={"error": ErrorCode.NOT_FOUND.value, "message": "Waypoint not found"},
        )
    _run_validation_after_write(workspace_id, db)
    return _waypoint_to_response(wp)


@router.delete("/{workspace_id}/waypoints/{waypoint_id}", status_code=204, response_model=None)
def delete_waypoint(workspace_id: int, waypoint_id: int, db: DbSession) -> None:
    _require_draft(workspace_id, db)
    repo = MapRepository(db)
    wp = repo.get_waypoint(waypoint_id)
    if wp is None or wp.workspace_id != workspace_id:
        raise HTTPException(
            status_code=404,
            detail={"error": ErrorCode.NOT_FOUND.value, "message": f"Waypoint {waypoint_id} not found"},
        )
    repo.delete_waypoint(waypoint_id)
    _run_validation_after_write(workspace_id, db)
