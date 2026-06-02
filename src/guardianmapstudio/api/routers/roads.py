from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from guardianmapstudio.api.deps import DbSession
from guardianmapstudio.api.errors import ErrorCode
from guardianmapstudio.api.routers._validation_helper import _run_validation_after_write
from guardianmapstudio.api.schemas import (
    DuplicateGroupResponse,
    DuplicateGroupsResponse,
    GeoPointDTO,
    RoadCreate,
    RoadMergeRequest,
    RoadMergeResponse,
    RoadMergeResultItem,
    RoadResponse,
    RoadUpdate,
)
from guardianmapstudio.database.repository import MapRepository, WorkspaceRepository
from guardianmapstudio.domain.contracts import Road
from guardianmapstudio.geometry.engine import GeometryEngine
from guardianmapstudio.geometry.road_merge import RoadMergeService

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


# ---------------------------------------------------------------------------
# Duplicate detection & merge (inserted before /{road_id} to avoid routing clash)
# ---------------------------------------------------------------------------

# Matches the OSM importer's suffix pattern: "Foo (2)", "Foo (3)", ...
_SUFFIX_RE = re.compile(r"^(.*) \((\d+)\)$")


def _strip_suffix(name: str) -> str:
    """Return the base name without the OSM dedup suffix."""
    m = _SUFFIX_RE.match(name)
    return m.group(1) if m else name


@router.get(
    "/{workspace_id}/roads/duplicate-groups",
    response_model=DuplicateGroupsResponse,
)
def list_duplicate_groups(
    workspace_id: int,
    db: DbSession,
) -> DuplicateGroupsResponse:
    """Detect groups of roads that share a base name (OSM suffix pattern)."""
    roads = MapRepository(db).get_roads(workspace_id)

    by_base: dict[str, list[Road]] = defaultdict(list)
    for r in roads:
        by_base[_strip_suffix(r.name)].append(r)

    groups: list[DuplicateGroupResponse] = []
    for base_name, group_roads in by_base.items():
        if len(group_roads) < 2:
            continue
        groups.append(DuplicateGroupResponse(
            base_name=base_name,
            road_ids=[r.id for r in group_roads],
            road_names=[r.name for r in group_roads],
            total_points=sum(len(r.coordinates) for r in group_roads),
        ))
    return DuplicateGroupsResponse(groups=groups)


@router.post(
    "/{workspace_id}/roads/merge",
    response_model=RoadMergeResponse,
    status_code=status.HTTP_200_OK,
)
def merge_roads(
    workspace_id: int,
    payload: RoadMergeRequest,
    db: DbSession,
) -> RoadMergeResponse:
    """Merge groups of roads into single roads (all groups in one transaction)."""
    _require_draft(workspace_id, db)

    map_repo = MapRepository(db)
    all_roads = {r.id: r for r in map_repo.get_roads(workspace_id)}

    # Validate the request before any write
    seen_ids: set[int] = set()
    for grp in payload.groups:
        if len(grp.source_road_ids) < 2:
            raise HTTPException(status_code=422, detail={
                "error": ErrorCode.MERGE_INSUFFICIENT_ROADS.value,
                "message": f"Group '{grp.target_name}' has fewer than 2 source roads",
                "detail": {"target_name": grp.target_name},
            })
        for rid in grp.source_road_ids:
            if rid not in all_roads:
                raise HTTPException(status_code=404, detail={
                    "error": ErrorCode.NOT_FOUND.value,
                    "message": f"Road id {rid} not found in workspace",
                    "detail": {"road_id": rid},
                })
            if rid in seen_ids:
                raise HTTPException(status_code=422, detail={
                    "error": ErrorCode.MERGE_DUPLICATE_SOURCE.value,
                    "message": f"Road id {rid} appears in multiple merge groups",
                    "detail": {"road_id": rid},
                })
            seen_ids.add(rid)

    # Build a GeometryEngine for the merge service
    all_points = [p for r in all_roads.values() for p in r.coordinates]
    if all_points:
        avg_lat = sum(p.latitude for p in all_points) / len(all_points)
        avg_lng = sum(p.longitude for p in all_points) / len(all_points)
    else:
        avg_lat, avg_lng = -23.5, -46.6
    geo = GeometryEngine.from_centroid(avg_lat, avg_lng)
    merge_service = RoadMergeService(geo)

    results: list[RoadMergeResultItem] = []
    try:
        for grp in payload.groups:
            roads_to_merge = [all_roads[rid] for rid in grp.source_road_ids]
            merged = merge_service.merge(roads_to_merge)

            # Update the first source road in place with merged geometry
            target_road = roads_to_merge[0]
            coords_json = json.dumps(
                [{"lat": p.latitude, "lng": p.longitude} for p in merged.coordinates],
                ensure_ascii=False,
            )
            map_repo.update_road(
                road_id=target_road.id,
                name=grp.target_name,
                coordinates=coords_json,
            )

            # Reassign waypoints: any whose road_name was one of the source roads
            old_names = {r.name for r in roads_to_merge[1:]}
            all_source_names = {target_road.name} | old_names
            wp_count = 0
            for wp in map_repo.get_waypoints(workspace_id):
                if wp.road_name in all_source_names and wp.road_name != grp.target_name:
                    map_repo.update_waypoint(waypoint_id=wp.id, road_name=grp.target_name)
                    wp_count += 1

            # Reassign crossroads
            cr_count = 0
            for cr in map_repo.get_crossroads(workspace_id):
                new_a = grp.target_name if cr.road_a_name in all_source_names else cr.road_a_name
                new_b = grp.target_name if cr.road_b_name in all_source_names else cr.road_b_name
                if new_a != cr.road_a_name or new_b != cr.road_b_name:
                    map_repo.update_crossroad(
                        crossroad_id=cr.id, road_a_name=new_a, road_b_name=new_b,
                    )
                    cr_count += 1

            # Delete the other source roads
            deleted_ids: list[int] = []
            for r in roads_to_merge[1:]:
                map_repo.delete_road(r.id)
                deleted_ids.append(r.id)

            results.append(RoadMergeResultItem(
                target_name=grp.target_name,
                merged_road_id=target_road.id,
                source_road_ids=list(grp.source_road_ids),
                deleted_road_ids=deleted_ids,
                total_coordinates=len(merged.coordinates),
                reversed_road_ids=list(merged.reversed_roads),
                gaps_meters=[g[1] for g in merged.gaps],
                reassigned_waypoints=wp_count,
                reassigned_crossroads=cr_count,
            ))
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail={
            "error": ErrorCode.MERGE_FAILED.value,
            "message": str(e),
            "detail": {},
        }) from e
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail={
            "error": ErrorCode.DATABASE_ERROR.value,
            "message": "Database error during merge",
            "detail": {},
        }) from e

    _run_validation_after_write(workspace_id, db)
    db.commit()

    return RoadMergeResponse(workspace_id=workspace_id, results=results)


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
