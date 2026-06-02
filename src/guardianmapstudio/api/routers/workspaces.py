from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from guardianmapstudio.api.deps import DbSession, SettingsDep
from guardianmapstudio.api.errors import ErrorCode
from guardianmapstudio.api.schemas import (
    CrossroadResponse,
    GeoPointDTO,
    MapResponse,
    PublishRequest,
    RestrictedAreaResponse,
    RoadResponse,
    SnapRequest,
    SnapResponse,
    VersionResponse,
    WaypointResponse,
)
from guardianmapstudio.database.models import EntityVersionModel, RoadVersionModel
from guardianmapstudio.database.repository import (
    MapRepository,
    VersionRepository,
    WorkspaceRepository,
)
from guardianmapstudio.domain.contracts import (
    GeoPoint,
    Road,
    Version,
    WorkspaceState,
)
from guardianmapstudio.geometry.engine import GeometryEngine
from guardianmapstudio.geometry.snap import SnapEngine
from guardianmapstudio.geometry.validation import ValidationEngine

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


@router.get("/{workspace_id}/map", response_model=MapResponse)
def get_map(workspace_id: int, db: DbSession) -> MapResponse:
    ws = WorkspaceRepository(db).get_by_id(workspace_id)
    if ws is None:
        raise HTTPException(
            status_code=404,
            detail={"error": ErrorCode.NOT_FOUND.value, "message": f"Workspace {workspace_id} not found"},
        )
    repo = MapRepository(db)
    roads = repo.get_roads(workspace_id)
    waypoints = repo.get_waypoints(workspace_id)
    crossroads = repo.get_crossroads(workspace_id)
    areas = repo.get_areas(workspace_id)
    return MapResponse(
        roads=[_road_to_response(r) for r in roads],
        waypoints=[
            WaypointResponse(
                id=w.id, workspace_id=w.workspace_id, name=w.name,
                waypoint_type=w.waypoint_type.value,
                lat=w.position.latitude, lng=w.position.longitude,
                road_name=w.road_name, heading_degrees=w.heading_degrees,
                extra_data=w.extra_data, active=w.active,
                created_at=w.created_at, updated_at=w.updated_at,
            )
            for w in waypoints
        ],
        crossroads=[
            CrossroadResponse(
                id=cr.id, workspace_id=cr.workspace_id,
                road_a_name=cr.road_a_name, road_b_name=cr.road_b_name,
                lat=cr.position.latitude, lng=cr.position.longitude,
                created_at=cr.created_at,
            )
            for cr in crossroads
        ],
        restricted_areas=[
            RestrictedAreaResponse(
                id=a.id, workspace_id=a.workspace_id, name=a.name,
                polygon=[GeoPointDTO(lat=p.latitude, lng=p.longitude) for p in a.polygon],
                restriction_type=a.restriction_type.value,
                speed_limit_kmh=a.speed_limit_kmh, active=a.active,
                created_at=a.created_at, updated_at=a.updated_at,
            )
            for a in areas
        ],
    )


@router.post("/{workspace_id}/publish", response_model=VersionResponse, status_code=201)
def publish_workspace(workspace_id: int, body: PublishRequest, db: DbSession) -> VersionResponse:
    ws_repo = WorkspaceRepository(db)
    ws = ws_repo.get_by_id(workspace_id)
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

    # Run validation
    map_repo = MapRepository(db)
    roads = map_repo.get_roads(workspace_id)
    waypoints = map_repo.get_waypoints(workspace_id)
    crossroads = map_repo.get_crossroads(workspace_id)
    areas = map_repo.get_areas(workspace_id)

    all_points = [p for r in roads for p in r.coordinates]
    avg_lat = sum(p.latitude for p in all_points) / len(all_points) if all_points else -23.5
    avg_lng = sum(p.longitude for p in all_points) / len(all_points) if all_points else -46.6

    geo = GeometryEngine.from_centroid(avg_lat, avg_lng)
    val_results = ValidationEngine(geo).validate(roads, waypoints, crossroads, areas)
    if any(r.is_blocking for r in val_results):
        raise HTTPException(
            status_code=422,
            detail={"error": ErrorCode.VALIDATION_ERRORS_BLOCKING.value, "message": "Blocking validation errors exist"},
        )

    # Create version record
    ver_repo = VersionRepository(db)
    version = ver_repo.create(
        project_id=ws.project_id,
        name=body.version_name,
        road_count=len(roads),
        waypoint_count=len([w for w in waypoints if w.active]),
        crossroad_count=len(crossroads),
        restricted_area_count=len([a for a in areas if a.active]),
    )

    # Snapshot roads
    _snapshot_entities(db, version.id, roads, waypoints, crossroads, areas)

    # Mark workspace as published
    ws_repo.set_published(workspace_id)

    # Create new DRAFT workspace from this version
    ws_repo.create(project_id=ws.project_id, base_version_id=version.id)

    return _version_to_response(version)


def _snapshot_entities(
    db: Session,
    version_id: int,
    roads: list,  # type: ignore[type-arg]
    waypoints: list,  # type: ignore[type-arg]
    crossroads: list,  # type: ignore[type-arg]
    areas: list,  # type: ignore[type-arg]
) -> None:
    for road in roads:
        rv = RoadVersionModel(
            version_id=version_id,
            name=road.name,
            coordinates=json.dumps(
                [{"lat": p.latitude, "lng": p.longitude} for p in road.coordinates],
                ensure_ascii=False,
            ),
            speed_limit_kmh=road.speed_limit_kmh,
            direction=road.direction.value,
            width_meters=road.width_meters,
        )
        db.add(rv)

    for wp in waypoints:
        payload = json.dumps({
            "name": wp.name,
            "waypoint_type": wp.waypoint_type.value,
            "latitude": wp.position.latitude,
            "longitude": wp.position.longitude,
            "road_name": wp.road_name,
            "heading_degrees": wp.heading_degrees,
            "extra_data": wp.extra_data,
            "active": wp.active,
            "created_at": wp.created_at.isoformat(),
            "updated_at": wp.updated_at.isoformat(),
        }, ensure_ascii=False)
        db.add(EntityVersionModel(version_id=version_id, entity_type="waypoint", name=wp.name, payload=payload))

    for cr in crossroads:
        payload = json.dumps({
            "road_a_name": cr.road_a_name,
            "road_b_name": cr.road_b_name,
            "latitude": cr.position.latitude,
            "longitude": cr.position.longitude,
            "created_at": cr.created_at.isoformat(),
        }, ensure_ascii=False)
        db.add(EntityVersionModel(
            version_id=version_id,
            entity_type="crossroad",
            name=f"{cr.road_a_name}x{cr.road_b_name}",
            payload=payload,
        ))

    for area in areas:
        payload = json.dumps({
            "name": area.name,
            "polygon": [{"lat": p.latitude, "lng": p.longitude} for p in area.polygon],
            "restriction_type": area.restriction_type.value,
            "speed_limit_kmh": area.speed_limit_kmh,
            "active": area.active,
            "created_at": area.created_at.isoformat(),
            "updated_at": area.updated_at.isoformat(),
        }, ensure_ascii=False)
        db.add(EntityVersionModel(
            version_id=version_id, entity_type="restricted_area", name=area.name, payload=payload
        ))

    db.commit()


@router.post("/{workspace_id}/snap", response_model=SnapResponse)
def snap_point(workspace_id: int, body: SnapRequest, db: DbSession, settings: SettingsDep) -> SnapResponse:
    ws = WorkspaceRepository(db).get_by_id(workspace_id)
    if ws is None:
        raise HTTPException(
            status_code=404,
            detail={"error": ErrorCode.NOT_FOUND.value, "message": f"Workspace {workspace_id} not found"},
        )
    repo = MapRepository(db)
    roads = repo.get_roads(workspace_id)
    waypoints = repo.get_waypoints(workspace_id)

    all_points = [p for r in roads for p in r.coordinates]
    avg_lat = sum(p.latitude for p in all_points) / len(all_points) if all_points else body.lat
    avg_lng = sum(p.longitude for p in all_points) / len(all_points) if all_points else body.lng

    geo = GeometryEngine.from_centroid(avg_lat, avg_lng)
    snap_engine = SnapEngine(geo, tolerance_m=settings.snap_tolerance_m)
    new_point = GeoPoint(latitude=body.lat, longitude=body.lng)
    result = snap_engine.snap(new_point, roads, waypoints)

    return SnapResponse(
        original=GeoPointDTO(lat=result.original.latitude, lng=result.original.longitude),
        snapped_to=GeoPointDTO(lat=result.snapped_to.latitude, lng=result.snapped_to.longitude),
        snapped=result.snapped,
        distance_meters=result.distance_meters,
    )
