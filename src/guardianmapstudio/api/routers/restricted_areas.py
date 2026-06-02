from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException

from guardianmapstudio.api.deps import DbSession
from guardianmapstudio.api.errors import ErrorCode
from guardianmapstudio.api.routers._validation_helper import _run_validation_after_write
from guardianmapstudio.api.schemas import (
    GeoPointDTO,
    RestrictedAreaCreate,
    RestrictedAreaResponse,
    RestrictedAreaUpdate,
)
from guardianmapstudio.database.repository import MapRepository, WorkspaceRepository
from guardianmapstudio.domain.contracts import RestrictedArea

router = APIRouter()


def _area_to_response(area: RestrictedArea) -> RestrictedAreaResponse:
    return RestrictedAreaResponse(
        id=area.id,
        workspace_id=area.workspace_id,
        name=area.name,
        polygon=[GeoPointDTO(lat=p.latitude, lng=p.longitude) for p in area.polygon],
        restriction_type=area.restriction_type.value,
        speed_limit_kmh=area.speed_limit_kmh,
        active=area.active,
        created_at=area.created_at,
        updated_at=area.updated_at,
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


@router.get("/{workspace_id}/restricted-areas", response_model=list[RestrictedAreaResponse])
def list_areas(workspace_id: int, db: DbSession) -> list[RestrictedAreaResponse]:
    _require_draft(workspace_id, db)
    areas = MapRepository(db).get_areas(workspace_id)
    return [_area_to_response(a) for a in areas]


@router.post("/{workspace_id}/restricted-areas", response_model=RestrictedAreaResponse, status_code=201)
def create_area(workspace_id: int, body: RestrictedAreaCreate, db: DbSession) -> RestrictedAreaResponse:
    _require_draft(workspace_id, db)
    polygon_json = json.dumps(
        [{"lat": pt.lat, "lng": pt.lng} for pt in body.polygon],
        ensure_ascii=False,
    )
    area = MapRepository(db).create_area(
        workspace_id=workspace_id,
        name=body.name,
        polygon_json=polygon_json,
        restriction_type=body.restriction_type,
        speed_limit_kmh=body.speed_limit_kmh,
    )
    _run_validation_after_write(workspace_id, db)
    return _area_to_response(area)


@router.patch("/{workspace_id}/restricted-areas/{area_id}", response_model=RestrictedAreaResponse)
def update_area(workspace_id: int, area_id: int, body: RestrictedAreaUpdate, db: DbSession) -> RestrictedAreaResponse:
    _require_draft(workspace_id, db)
    repo = MapRepository(db)
    existing = repo.get_area(area_id)
    if existing is None or existing.workspace_id != workspace_id:
        raise HTTPException(
            status_code=404,
            detail={"error": ErrorCode.NOT_FOUND.value, "message": f"Restricted area {area_id} not found"},
        )
    updates: dict[str, Any] = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.polygon is not None:
        updates["polygon"] = json.dumps(
            [{"lat": pt.lat, "lng": pt.lng} for pt in body.polygon],
            ensure_ascii=False,
        )
    if body.restriction_type is not None:
        updates["restriction_type"] = body.restriction_type
    if body.speed_limit_kmh is not None:
        updates["speed_limit_kmh"] = body.speed_limit_kmh
    if body.active is not None:
        updates["active"] = body.active

    area = repo.update_area(area_id, **updates)
    if area is None:
        raise HTTPException(status_code=404, detail={"error": ErrorCode.NOT_FOUND.value, "message": "Area not found"})
    _run_validation_after_write(workspace_id, db)
    return _area_to_response(area)


@router.delete("/{workspace_id}/restricted-areas/{area_id}", status_code=204, response_model=None)
def delete_area(workspace_id: int, area_id: int, db: DbSession) -> None:
    _require_draft(workspace_id, db)
    repo = MapRepository(db)
    area = repo.get_area(area_id)
    if area is None or area.workspace_id != workspace_id:
        raise HTTPException(
            status_code=404,
            detail={"error": ErrorCode.NOT_FOUND.value, "message": f"Restricted area {area_id} not found"},
        )
    repo.delete_area(area_id)
    _run_validation_after_write(workspace_id, db)
