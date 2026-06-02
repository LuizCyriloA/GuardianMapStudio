from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from guardianmapstudio.database.repository import (
    MapRepository,
    ValidationRepository,
    WorkspaceRepository,
)
from guardianmapstudio.geometry.engine import GeometryEngine
from guardianmapstudio.geometry.validation import ValidationEngine


def _run_validation_after_write(workspace_id: int, db: Session) -> None:
    """Run the full validation pipeline and persist results. Called after every map write."""
    map_repo = MapRepository(db)
    roads = map_repo.get_roads(workspace_id)
    waypoints = map_repo.get_waypoints(workspace_id)
    crossroads = map_repo.get_crossroads(workspace_id)
    areas = map_repo.get_areas(workspace_id)

    all_points = [p for r in roads for p in r.coordinates]
    if all_points:
        avg_lat = sum(p.latitude for p in all_points) / len(all_points)
        avg_lng = sum(p.longitude for p in all_points) / len(all_points)
    else:
        avg_lat, avg_lng = -23.5, -46.6

    geo = GeometryEngine.from_centroid(avg_lat, avg_lng)
    engine = ValidationEngine(geo)
    results = engine.validate(roads, waypoints, crossroads, areas)

    val_repo = ValidationRepository(db)
    val_repo.replace_results(workspace_id, results)

    ws_repo = WorkspaceRepository(db)
    has_errors = any(r.is_blocking for r in results)
    ws_repo.update_validation_state(workspace_id, has_errors, datetime.now(UTC))
