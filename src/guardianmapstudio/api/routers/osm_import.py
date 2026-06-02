from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from guardianmapstudio.api.deps import DbSession, get_settings
from guardianmapstudio.api.errors import ErrorCode
from guardianmapstudio.api.routers._validation_helper import _run_validation_after_write
from guardianmapstudio.api.schemas import (
    GeoPointDTO,
    OsmImportRequest,
    OsmImportResponse,
    OsmPreviewResponse,
    ParsedRoadDTO,
)
from guardianmapstudio.config.settings import GuardianMapStudioSettings
from guardianmapstudio.database.repository import WorkspaceRepository
from guardianmapstudio.domain.contracts import (
    GeoPoint,
    RoadDirection,
    WorkspaceState,
)
from guardianmapstudio.osm.importer import OsmImporter
from guardianmapstudio.osm.parser import OsmParser, ParsedRoad

router = APIRouter()


# Helper: ParsedRoad ⇄ ParsedRoadDTO
def _parsed_road_to_dto(pr: ParsedRoad) -> ParsedRoadDTO:
    return ParsedRoadDTO(
        osm_way_id=pr.osm_way_id,
        name=pr.name,
        coordinates=[GeoPointDTO(lat=p.latitude, lng=p.longitude)
                     for p in pr.coordinates],
        direction=pr.direction.value,
        speed_limit_kmh=pr.speed_limit_kmh,
        width_meters=pr.width_meters,
        highway_tag=pr.highway_tag,
        had_name=pr.had_name,
        osm_warnings=list(pr.osm_warnings),
    )


def _dto_to_parsed_road(dto: ParsedRoadDTO) -> ParsedRoad:
    return ParsedRoad(
        osm_way_id=dto.osm_way_id,
        name=dto.name,
        coordinates=[GeoPoint(latitude=p.lat, longitude=p.lng)
                     for p in dto.coordinates],
        direction=RoadDirection(dto.direction),
        speed_limit_kmh=dto.speed_limit_kmh,
        width_meters=dto.width_meters,
        highway_tag=dto.highway_tag,
        had_name=dto.had_name,
        osm_warnings=list(dto.osm_warnings),
    )


def _require_draft(workspace_id: int, db: Session) -> None:
    ws_repo = WorkspaceRepository(db)
    ws = ws_repo.get_by_id(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail={
            "error": ErrorCode.NOT_FOUND.value,
            "message": f"Workspace {workspace_id} not found",
            "detail": {},
        })
    if ws.state != WorkspaceState.DRAFT:
        raise HTTPException(status_code=409, detail={
            "error": ErrorCode.WORKSPACE_NOT_DRAFT.value,
            "message": "OSM import requires a DRAFT workspace",
            "detail": {"current_state": ws.state.value},
        })


@router.post(
    "/{workspace_id}/osm/preview",
    response_model=OsmPreviewResponse,
    status_code=status.HTTP_200_OK,
)
async def preview_osm(
    workspace_id: int,
    request: Request,
    db: DbSession,
    settings: Annotated[GuardianMapStudioSettings, Depends(get_settings)],
    include_pedestrian: bool = False,
    include_unnamed: bool = False,
) -> OsmPreviewResponse:
    """Parse an OSM XML upload and return the detected roads.

    Accepts raw OSM XML bytes as the request body
    (Content-Type: application/octet-stream or application/xml).
    Does NOT write to the database. The frontend uses this response to
    show a preview; the operator confirms with POST /osm/import.
    """
    _require_draft(workspace_id, db)

    max_bytes = settings.osm_max_file_size_mb * 1024 * 1024
    # Read up to max_bytes+1 so we can detect oversized payloads
    payload = await request.body()
    if len(payload) > max_bytes:
        raise HTTPException(status_code=413, detail={
            "error": ErrorCode.PAYLOAD_TOO_LARGE.value,
            "message": f"File exceeds {settings.osm_max_file_size_mb} MB limit",
            "detail": {"max_mb": settings.osm_max_file_size_mb},
        })

    try:
        result = OsmParser().parse(
            payload,
            include_pedestrian=include_pedestrian,
            include_unnamed=include_unnamed,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail={
            "error": ErrorCode.OSM_PARSE_ERROR.value,
            "message": str(e),
            "detail": {},
        }) from e

    if len(result.roads) > settings.osm_max_ways:
        raise HTTPException(status_code=422, detail={
            "error": ErrorCode.OSM_TOO_MANY_WAYS.value,
            "message": (
                f"File contains {len(result.roads)} drivable ways; "
                f"limit is {settings.osm_max_ways}. "
                "Trim the OSM export bounding box."
            ),
            "detail": {
                "ways_found": len(result.roads),
                "max_allowed": settings.osm_max_ways,
            },
        })

    return OsmPreviewResponse(
        roads=[_parsed_road_to_dto(r) for r in result.roads],
        total_ways_in_file=result.total_ways_in_file,
        skipped_ways=result.skipped_ways,
        skipped_reasons=result.skipped_reasons,
    )


@router.post(
    "/{workspace_id}/osm/import",
    response_model=OsmImportResponse,
    status_code=status.HTTP_201_CREATED,
)
def import_osm(
    workspace_id: int,
    payload: OsmImportRequest,
    db: DbSession,
) -> OsmImportResponse:
    """Commit the operator-confirmed OSM roads into the workspace.

    Reuses MapRepository.create_road for each road, so all existing
    invariants (BR-05 unique name via suffix, JSON ensure_ascii=False,
    Double precision) apply automatically.
    """
    _require_draft(workspace_id, db)

    parsed = [_dto_to_parsed_road(d) for d in payload.roads]

    try:
        summary = OsmImporter(db).import_roads(
            workspace_id, parsed,
            replace_existing=payload.replace_existing,
        )
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail={
            "error": ErrorCode.ROAD_HAS_DEPENDENTS.value,
            "message": str(e),
            "detail": {},
        }) from e
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail={
            "error": ErrorCode.DATABASE_ERROR.value,
            "message": "Database error during OSM import",
            "detail": {},
        }) from e

    # Re-run validation so has_validation_errors reflects the import
    _run_validation_after_write(workspace_id, db)
    db.commit()

    return OsmImportResponse(
        workspace_id=workspace_id,
        created_count=summary.created_count,
        deleted_existing=summary.deleted_existing,
        renamed=[{"from": a, "to": b} for (a, b) in summary.renamed],
    )
