from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from guardianmapstudio.api.deps import DbSession
from guardianmapstudio.api.errors import ErrorCode
from guardianmapstudio.api.schemas import ValidationResultResponse, ValidationSummaryResponse
from guardianmapstudio.database.models import ValidationResultModel
from guardianmapstudio.database.repository import (
    MapRepository,
    ValidationRepository,
    WorkspaceRepository,
)
from guardianmapstudio.geometry.engine import GeometryEngine
from guardianmapstudio.geometry.validation import ValidationEngine

router = APIRouter()


@router.post("/{workspace_id}/validate", response_model=ValidationSummaryResponse)
def run_validation(workspace_id: int, db: DbSession) -> ValidationSummaryResponse:
    ws = WorkspaceRepository(db).get_by_id(workspace_id)
    if ws is None:
        raise HTTPException(
            status_code=404,
            detail={"error": ErrorCode.NOT_FOUND.value, "message": f"Workspace {workspace_id} not found"},
        )

    map_repo = MapRepository(db)
    roads = map_repo.get_roads(workspace_id)
    waypoints = map_repo.get_waypoints(workspace_id)
    crossroads = map_repo.get_crossroads(workspace_id)
    areas = map_repo.get_areas(workspace_id)

    all_points = [p for r in roads for p in r.coordinates]
    avg_lat = sum(p.latitude for p in all_points) / len(all_points) if all_points else -23.5
    avg_lng = sum(p.longitude for p in all_points) / len(all_points) if all_points else -46.6

    geo = GeometryEngine.from_centroid(avg_lat, avg_lng)
    engine = ValidationEngine(geo)
    results = engine.validate(roads, waypoints, crossroads, areas)

    val_repo = ValidationRepository(db)
    val_repo.replace_results(workspace_id, results)

    now = datetime.now(UTC)
    has_errors = any(r.is_blocking for r in results)
    WorkspaceRepository(db).update_validation_state(workspace_id, has_errors, now)

    # Load saved results with DB ids
    saved = (
        db.execute(
            select(ValidationResultModel).where(ValidationResultModel.workspace_id == workspace_id)
        )
        .scalars()
        .all()
    )

    error_count = sum(1 for r in results if r.is_blocking)
    warning_count = len(results) - error_count

    return ValidationSummaryResponse(
        workspace_id=workspace_id,
        error_count=error_count,
        warning_count=warning_count,
        can_publish=not has_errors,
        results=[
            ValidationResultResponse(
                id=row.id,
                severity=row.severity,
                rule_id=row.rule_id,
                message=row.message,
                affected_entity_type=row.affected_entity_type,
                affected_entity_id=row.affected_entity_id,
            )
            for row in saved
        ],
        validated_at=now,
    )


@router.get("/{workspace_id}/validation", response_model=ValidationSummaryResponse)
def get_validation(workspace_id: int, db: DbSession) -> ValidationSummaryResponse:
    ws = WorkspaceRepository(db).get_by_id(workspace_id)
    if ws is None:
        raise HTTPException(
            status_code=404,
            detail={"error": ErrorCode.NOT_FOUND.value, "message": f"Workspace {workspace_id} not found"},
        )

    saved = (
        db.execute(
            select(ValidationResultModel).where(ValidationResultModel.workspace_id == workspace_id)
        )
        .scalars()
        .all()
    )

    error_count = sum(1 for r in saved if r.severity == "error")
    warning_count = sum(1 for r in saved if r.severity == "warning")
    validated_at = ws.last_validated_at or datetime.now(UTC)

    return ValidationSummaryResponse(
        workspace_id=workspace_id,
        error_count=error_count,
        warning_count=warning_count,
        can_publish=not ws.has_validation_errors,
        results=[
            ValidationResultResponse(
                id=row.id,
                severity=row.severity,
                rule_id=row.rule_id,
                message=row.message,
                affected_entity_type=row.affected_entity_type,
                affected_entity_id=row.affected_entity_id,
            )
            for row in saved
        ],
        validated_at=validated_at,
    )
