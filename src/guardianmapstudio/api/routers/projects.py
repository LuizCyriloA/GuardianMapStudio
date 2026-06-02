from __future__ import annotations

from fastapi import APIRouter, HTTPException

from guardianmapstudio.api.deps import DbSession
from guardianmapstudio.api.errors import ErrorCode
from guardianmapstudio.api.schemas import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    VersionListResponse,
    VersionResponse,
    WorkspaceResponse,
)
from guardianmapstudio.database.repository import (
    ProjectRepository,
    VersionRepository,
    WorkspaceRepository,
)
from guardianmapstudio.domain.contracts import Project, Version, Workspace

router = APIRouter()


def _project_to_response(p: Project) -> ProjectResponse:
    return ProjectResponse(
        id=p.id,
        name=p.name,
        description=p.description,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _version_to_response(v: Version) -> VersionResponse:
    return VersionResponse(
        id=v.id,
        project_id=v.project_id,
        version_number=v.version_number,
        name=v.name,
        published_at=v.published_at,
        road_count=v.road_count,
        waypoint_count=v.waypoint_count,
        crossroad_count=v.crossroad_count,
        restricted_area_count=v.restricted_area_count,
    )


def _workspace_to_response(ws: Workspace) -> WorkspaceResponse:
    return WorkspaceResponse(
        id=ws.id,
        project_id=ws.project_id,
        state=ws.state.value,
        base_version_id=ws.base_version_id,
        created_at=ws.created_at,
        updated_at=ws.updated_at,
        last_validated_at=ws.last_validated_at,
        has_validation_errors=ws.has_validation_errors,
    )


@router.get("", response_model=ProjectListResponse)
def list_projects(db: DbSession) -> ProjectListResponse:
    repo = ProjectRepository(db)
    projects = repo.get_all()
    return ProjectListResponse(
        items=[_project_to_response(p) for p in projects],
        total=len(projects),
    )


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(body: ProjectCreate, db: DbSession) -> ProjectResponse:
    repo = ProjectRepository(db)
    # ProjectRepository.create() automatically creates the first DRAFT workspace (BR-01)
    project = repo.create(name=body.name, description=body.description)
    return _project_to_response(project)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int, db: DbSession) -> ProjectResponse:
    repo = ProjectRepository(db)
    project = repo.get_by_id(project_id)
    if project is None:
        raise HTTPException(
            status_code=404,
            detail={"error": ErrorCode.NOT_FOUND.value, "message": f"Project {project_id} not found"},
        )
    return _project_to_response(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: int, body: ProjectCreate, db: DbSession) -> ProjectResponse:
    repo = ProjectRepository(db)
    project = repo.update(project_id, name=body.name, description=body.description)
    if project is None:
        raise HTTPException(
            status_code=404,
            detail={"error": ErrorCode.NOT_FOUND.value, "message": f"Project {project_id} not found"},
        )
    return _project_to_response(project)


@router.get("/{project_id}/versions", response_model=VersionListResponse)
def list_versions(project_id: int, db: DbSession) -> VersionListResponse:
    project = ProjectRepository(db).get_by_id(project_id)
    if project is None:
        raise HTTPException(
            status_code=404,
            detail={"error": ErrorCode.NOT_FOUND.value, "message": f"Project {project_id} not found"},
        )
    versions = VersionRepository(db).get_all_for_project(project_id)
    return VersionListResponse(
        items=[_version_to_response(v) for v in versions],
        total=len(versions),
    )


@router.get("/{project_id}/workspace", response_model=WorkspaceResponse)
def get_workspace(project_id: int, db: DbSession) -> WorkspaceResponse:
    project = ProjectRepository(db).get_by_id(project_id)
    if project is None:
        raise HTTPException(
            status_code=404,
            detail={"error": ErrorCode.NOT_FOUND.value, "message": f"Project {project_id} not found"},
        )
    ws = WorkspaceRepository(db).get_active_draft(project_id)
    if ws is None:
        raise HTTPException(
            status_code=404,
            detail={"error": ErrorCode.NOT_FOUND.value, "message": "No active draft workspace"},
        )
    return _workspace_to_response(ws)
