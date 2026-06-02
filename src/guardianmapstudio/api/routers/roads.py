from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import IntegrityError

from guardianmapstudio.api.deps import DbSession
from guardianmapstudio.api.errors import ErrorCode
from guardianmapstudio.api.routers._validation_helper import _run_validation_after_write
from guardianmapstudio.api.schemas import GeoPointDTO, RoadCreate, RoadResponse, RoadUpdate
from guardianmapstudio.database.repository import MapRepository, WorkspaceRepository
from guardianmapstudio.domain.contracts import Road

router = APIRouter()


def _road_to_response(road: Road) -> RoadResponse:
    return RoadResponse(
        id=road.id,
        workspace_id=road.workspace_id,
        name=road.name,
        coordinates=[GeoPointDTO(lat=p.latitude, lng=p.longitude) for p in road.coordinates],
        speed_limit_kmh=road.speed_limit_kmh,
        direction=road.direction.value,
        width_meters=road.width_meters,
        created_at=road.created_at,
        updated_at=road.updated_at,
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


@router.get("/{workspace_id}/roads", response_model=list[RoadResponse])
def list_roads(workspace_id: int, db: DbSession) -> list[RoadResponse]:
    _require_draft(workspace_id, db)
    roads = MapRepository(db).get_roads(workspace_id)
    return [_road_to_response(r) for r in roads]


@router.post("/{workspace_id}/roads", response_model=RoadResponse, status_code=201)
def create_road(workspace_id: int, body: RoadCreate, db: DbSession) -> RoadResponse:
    _require_draft(workspace_id, db)
    coords_json = json.dumps(
        [{"lat": pt.lat, "lng": pt.lng} for pt in body.coordinates],
        ensure_ascii=False,
    )
    try:
        road = MapRepository(db).create_road(
            workspace_id=workspace_id,
            name=body.name,
            coordinates_json=coords_json,
            speed_limit_kmh=body.speed_limit_kmh,
            direction=body.direction,
            width_meters=body.width_meters,
        )
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail={"error": ErrorCode.ROAD_NAME_DUPLICATE.value, "message": f"Road '{body.name}' already exists"},
        ) from exc
    _run_validation_after_write(workspace_id, db)
    return _road_to_response(road)


@router.get("/{workspace_id}/roads/{road_id}", response_model=RoadResponse)
def get_road(workspace_id: int, road_id: int, db: DbSession) -> RoadResponse:
    road = MapRepository(db).get_road(road_id)
    if road is None or road.workspace_id != workspace_id:
        raise HTTPException(
            status_code=404,
            detail={"error": ErrorCode.NOT_FOUND.value, "message": f"Road {road_id} not found"},
        )
    return _road_to_response(road)


@router.patch("/{workspace_id}/roads/{road_id}", response_model=RoadResponse)
def update_road(workspace_id: int, road_id: int, body: RoadUpdate, db: DbSession) -> RoadResponse:
    _require_draft(workspace_id, db)
    repo = MapRepository(db)
    existing = repo.get_road(road_id)
    if existing is None or existing.workspace_id != workspace_id:
        raise HTTPException(
            status_code=404,
            detail={"error": ErrorCode.NOT_FOUND.value, "message": f"Road {road_id} not found"},
        )
    updates: dict[str, Any] = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.coordinates is not None:
        updates["coordinates"] = json.dumps(
            [{"lat": pt.lat, "lng": pt.lng} for pt in body.coordinates],
            ensure_ascii=False,
        )
    if body.speed_limit_kmh is not None:
        updates["speed_limit_kmh"] = body.speed_limit_kmh
    if body.direction is not None:
        updates["direction"] = body.direction
    if body.width_meters is not None:
        updates["width_meters"] = body.width_meters

    try:
        road = repo.update_road(road_id, **updates)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail={"error": ErrorCode.ROAD_NAME_DUPLICATE.value, "message": "Road name already exists"},
        ) from exc
    if road is None:
        raise HTTPException(status_code=404, detail={"error": ErrorCode.NOT_FOUND.value, "message": "Road not found"})
    _run_validation_after_write(workspace_id, db)
    return _road_to_response(road)


@router.delete("/{workspace_id}/roads/{road_id}", status_code=204, response_model=None)
def delete_road(workspace_id: int, road_id: int, db: DbSession) -> None:
    _require_draft(workspace_id, db)
    repo = MapRepository(db)
    road = repo.get_road(road_id)
    if road is None or road.workspace_id != workspace_id:
        raise HTTPException(
            status_code=404,
            detail={"error": ErrorCode.NOT_FOUND.value, "message": f"Road {road_id} not found"},
        )
    # Check for dependent waypoints
    waypoints = repo.get_waypoints(workspace_id)
    if any(w.road_name == road.name for w in waypoints):
        raise HTTPException(
            status_code=409,
            detail={"error": ErrorCode.ROAD_HAS_DEPENDENTS.value, "message": "Road has associated waypoints"},
        )
    repo.delete_road(road_id)
    _run_validation_after_write(workspace_id, db)
