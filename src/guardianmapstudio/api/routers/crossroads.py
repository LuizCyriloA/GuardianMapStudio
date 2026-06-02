from __future__ import annotations

from fastapi import APIRouter, HTTPException

from guardianmapstudio.api.deps import DbSession
from guardianmapstudio.api.errors import ErrorCode
from guardianmapstudio.api.routers._validation_helper import _run_validation_after_write
from guardianmapstudio.api.schemas import CrossroadCreate, CrossroadResponse
from guardianmapstudio.database.repository import MapRepository, WorkspaceRepository
from guardianmapstudio.domain.contracts import Crossroad

router = APIRouter()


def _crossroad_to_response(cr: Crossroad) -> CrossroadResponse:
    return CrossroadResponse(
        id=cr.id,
        workspace_id=cr.workspace_id,
        road_a_name=cr.road_a_name,
        road_b_name=cr.road_b_name,
        lat=cr.position.latitude,
        lng=cr.position.longitude,
        created_at=cr.created_at,
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


@router.get("/{workspace_id}/crossroads", response_model=list[CrossroadResponse])
def list_crossroads(workspace_id: int, db: DbSession) -> list[CrossroadResponse]:
    _require_draft(workspace_id, db)
    crossroads = MapRepository(db).get_crossroads(workspace_id)
    return [_crossroad_to_response(cr) for cr in crossroads]


@router.post("/{workspace_id}/crossroads", response_model=CrossroadResponse, status_code=201)
def create_crossroad(workspace_id: int, body: CrossroadCreate, db: DbSession) -> CrossroadResponse:
    _require_draft(workspace_id, db)
    cr = MapRepository(db).create_crossroad(
        workspace_id=workspace_id,
        road_a_name=body.road_a_name,
        road_b_name=body.road_b_name,
        latitude=body.lat,
        longitude=body.lng,
    )
    _run_validation_after_write(workspace_id, db)
    return _crossroad_to_response(cr)


@router.delete("/{workspace_id}/crossroads/{crossroad_id}", status_code=204, response_model=None)
def delete_crossroad(workspace_id: int, crossroad_id: int, db: DbSession) -> None:
    _require_draft(workspace_id, db)
    repo = MapRepository(db)
    cr = repo.get_crossroad(crossroad_id)
    if cr is None or cr.workspace_id != workspace_id:
        raise HTTPException(
            status_code=404,
            detail={"error": ErrorCode.NOT_FOUND.value, "message": f"Crossroad {crossroad_id} not found"},
        )
    repo.delete_crossroad(crossroad_id)
    _run_validation_after_write(workspace_id, db)
