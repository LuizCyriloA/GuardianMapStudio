from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select

from guardianmapstudio.api.deps import DbSession, SettingsDep
from guardianmapstudio.api.errors import ErrorCode
from guardianmapstudio.api.schemas import ExportHistoryResponse, ExportResponse
from guardianmapstudio.database.models import EntityVersionModel, RoadVersionModel
from guardianmapstudio.database.repository import (
    ExportRepository,
    ProjectRepository,
    VersionRepository,
)
from guardianmapstudio.domain.contracts import (
    Crossroad,
    GeoPoint,
    RestrictedArea,
    RestrictionType,
    Road,
    RoadDirection,
    Waypoint,
    WaypointType,
)
from guardianmapstudio.export.guardian_exporter import GuardianExporter

router = APIRouter()


def _reconstruct_road(rv: RoadVersionModel, rid: int) -> Road:
    raw = json.loads(rv.coordinates)
    return Road(
        id=rid,
        workspace_id=0,
        name=rv.name,
        coordinates=[GeoPoint(latitude=p["lat"], longitude=p["lng"]) for p in raw],
        speed_limit_kmh=rv.speed_limit_kmh,
        direction=RoadDirection(rv.direction),
        width_meters=rv.width_meters,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _reconstruct_waypoint(payload: str, eid: int) -> Waypoint:
    data = json.loads(payload)
    return Waypoint(
        id=eid,
        workspace_id=0,
        name=data["name"],
        waypoint_type=WaypointType(data["waypoint_type"]),
        position=GeoPoint(latitude=data["latitude"], longitude=data["longitude"]),
        road_name=data.get("road_name"),
        heading_degrees=data.get("heading_degrees"),
        extra_data=data.get("extra_data", {}),
        created_at=datetime.fromisoformat(data["created_at"]),
        updated_at=datetime.fromisoformat(data["updated_at"]),
        active=data.get("active", True),
    )


def _reconstruct_crossroad(payload: str, eid: int) -> Crossroad:
    data = json.loads(payload)
    return Crossroad(
        id=eid,
        workspace_id=0,
        road_a_name=data["road_a_name"],
        road_b_name=data["road_b_name"],
        position=GeoPoint(latitude=data["latitude"], longitude=data["longitude"]),
        created_at=datetime.fromisoformat(data["created_at"]),
    )


def _reconstruct_area(payload: str, eid: int) -> RestrictedArea:
    data = json.loads(payload)
    return RestrictedArea(
        id=eid,
        workspace_id=0,
        name=data["name"],
        polygon=[GeoPoint(latitude=p["lat"], longitude=p["lng"]) for p in data["polygon"]],
        restriction_type=RestrictionType(data["restriction_type"]),
        speed_limit_kmh=data.get("speed_limit_kmh"),
        created_at=datetime.fromisoformat(data["created_at"]),
        updated_at=datetime.fromisoformat(data["updated_at"]),
        active=data.get("active", True),
    )


@router.get("/projects/{project_id}/exports", response_model=ExportHistoryResponse)
def get_export_history(project_id: int, db: DbSession) -> ExportHistoryResponse:
    project = ProjectRepository(db).get_by_id(project_id)
    if project is None:
        raise HTTPException(
            status_code=404,
            detail={"error": ErrorCode.NOT_FOUND.value, "message": f"Project {project_id} not found"},
        )
    history = ExportRepository(db).get_history(project_id)
    return ExportHistoryResponse(
        items=[
            ExportResponse(
                export_id=r.id,
                version_id=r.version_id,
                file_path=r.file_path,
                file_size_bytes=r.file_size_bytes,
                exported_at=r.exported_at,
            )
            for r in history
        ],
        total=len(history),
    )


@router.post("/versions/{version_id}/export", response_model=ExportResponse, status_code=201)
def export_version(version_id: int, db: DbSession, settings: SettingsDep) -> ExportResponse:
    ver_repo = VersionRepository(db)
    version = ver_repo.get_by_id(version_id)
    if version is None:
        raise HTTPException(
            status_code=404,
            detail={"error": ErrorCode.NOT_FOUND.value, "message": f"Version {version_id} not found"},
        )

    project = ProjectRepository(db).get_by_id(version.project_id)
    project_name = project.name if project else "unknown"

    # Load road snapshots
    road_models = (
        db.execute(select(RoadVersionModel).where(RoadVersionModel.version_id == version_id))
        .scalars()
        .all()
    )
    roads = [_reconstruct_road(rv, i + 1) for i, rv in enumerate(road_models)]

    # Load entity snapshots
    entity_models = (
        db.execute(select(EntityVersionModel).where(EntityVersionModel.version_id == version_id))
        .scalars()
        .all()
    )
    waypoints = [_reconstruct_waypoint(ev.payload, ev.id) for ev in entity_models if ev.entity_type == "waypoint"]
    crossroads = [_reconstruct_crossroad(ev.payload, ev.id) for ev in entity_models if ev.entity_type == "crossroad"]
    areas = [_reconstruct_area(ev.payload, ev.id) for ev in entity_models if ev.entity_type == "restricted_area"]

    timestamp = int(datetime.now(UTC).timestamp())
    filename = f"v{version.version_number}_{version_id}_{timestamp}.json"
    export_dir = Path(settings.export_dir)
    export_dir.mkdir(parents=True, exist_ok=True)
    output_path = export_dir / filename

    try:
        file_size = GuardianExporter().export(
            version=version,
            project_name=project_name,
            roads=roads,
            waypoints=waypoints,
            crossroads=crossroads,
            areas=areas,
            output_path=output_path,
            coordinate_precision=settings.coordinate_precision,
        )
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": ErrorCode.EXPORT_WRITE_ERROR.value, "message": str(exc)},
        ) from exc

    record = ExportRepository(db).create_record(
        version_id=version_id,
        project_id=version.project_id,
        file_path=str(output_path),
        file_size_bytes=file_size,
    )

    return ExportResponse(
        export_id=record.id,
        version_id=record.version_id,
        file_path=record.file_path,
        file_size_bytes=record.file_size_bytes,
        exported_at=record.exported_at,
    )


@router.get("/versions/{version_id}/export/download")
def download_export(version_id: int, db: DbSession) -> FileResponse:
    from sqlalchemy import select as sa_select  # noqa: PLC0415

    from guardianmapstudio.database.models import ExportHistoryModel  # noqa: PLC0415
    row = (
        db.execute(
            sa_select(ExportHistoryModel)
            .where(ExportHistoryModel.version_id == version_id)
            .order_by(ExportHistoryModel.exported_at.desc())
            .limit(1)
        )
        .scalars()
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=404,
            detail={"error": ErrorCode.NOT_FOUND.value, "message": "No export found for this version"},
        )
    file_path = Path(row.file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail={"error": ErrorCode.NOT_FOUND.value, "message": "Export file not found on disk"},
        )
    return FileResponse(path=str(file_path), filename=file_path.name, media_type="application/json")


@router.get("/versions/{version_id}/map")
def get_version_map(version_id: int, db: DbSession) -> dict:  # type: ignore[type-arg]
    """Return snapshot of the map as stored in the version tables."""
    road_models = (
        db.execute(select(RoadVersionModel).where(RoadVersionModel.version_id == version_id))
        .scalars()
        .all()
    )
    entity_models = (
        db.execute(select(EntityVersionModel).where(EntityVersionModel.version_id == version_id))
        .scalars()
        .all()
    )
    return {
        "roads": [{"name": r.name, "coordinates": json.loads(r.coordinates)} for r in road_models],
        "waypoints": [json.loads(e.payload) for e in entity_models if e.entity_type == "waypoint"],
        "crossroads": [json.loads(e.payload) for e in entity_models if e.entity_type == "crossroad"],
        "restricted_areas": [json.loads(e.payload) for e in entity_models if e.entity_type == "restricted_area"],
    }
