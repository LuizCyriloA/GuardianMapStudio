from __future__ import annotations

import json
from dataclasses import dataclass

from loguru import logger
from sqlalchemy.orm import Session

from guardianmapstudio.database.repository import MapRepository
from guardianmapstudio.domain.contracts import Road
from guardianmapstudio.osm.parser import ParsedRoad


@dataclass(frozen=True, slots=True)
class ImportSummary:
    created_count: int
    skipped_count: int
    renamed: list[tuple[str, str]]  # (original_name, final_name)
    deleted_existing: int            # > 0 only when replace_existing=True


class OsmImporter:
    """Creates Road entities from ParsedRoad objects in a workspace.

    Reuses MapRepository.create_road() so all existing invariants apply:
    - workspace must be DRAFT (enforced by the router before calling this)
    - road names are unique per workspace (enforced here via suffix)
    - JSON coordinates persisted with ensure_ascii=False (repository handles it)
    """

    def __init__(self, db: Session) -> None:
        self._repo = MapRepository(db)

    def import_roads(
        self,
        workspace_id: int,
        parsed_roads: list[ParsedRoad],
        *,
        replace_existing: bool = False,
    ) -> ImportSummary:
        """Create Roads in the workspace from the given parsed roads.

        Args:
            workspace_id: the active DRAFT Workspace id.
            parsed_roads: roads selected by the operator for import.
            replace_existing: if True, delete all existing roads in the
                workspace first. Raises ValueError if any road has
                dependent waypoints or crossroads.

        Returns:
            ImportSummary with counts and renamed list.
        """
        deleted = 0
        if replace_existing:
            deleted = self._delete_all_roads(workspace_id)

        existing_names: set[str] = {
            r.name for r in self._repo.get_roads(workspace_id)
        }

        created = 0
        renamed: list[tuple[str, str]] = []

        for pr in parsed_roads:
            final_name = self._dedupe_name(pr.name, existing_names)
            if final_name != pr.name:
                renamed.append((pr.name, final_name))
            existing_names.add(final_name)

            coords_json = json.dumps(
                [{"lat": p.latitude, "lng": p.longitude} for p in pr.coordinates],
                ensure_ascii=False,
            )
            self._repo.create_road(
                workspace_id=workspace_id,
                name=final_name,
                coordinates_json=coords_json,
                speed_limit_kmh=pr.speed_limit_kmh,
                direction=pr.direction.value,
                width_meters=pr.width_meters,
            )
            created += 1

        logger.info(
            "OSM import: created={} renamed={} deleted_existing={}",
            created, len(renamed), deleted,
        )
        return ImportSummary(
            created_count=created,
            skipped_count=0,
            renamed=renamed,
            deleted_existing=deleted,
        )

    def _delete_all_roads(self, workspace_id: int) -> int:
        """Delete every Road in the workspace. Raises ValueError if any road
        has dependent waypoints or crossroads."""
        roads: list[Road] = self._repo.get_roads(workspace_id)
        if not roads:
            return 0

        # Check for dependents before deleting anything
        waypoints = self._repo.get_waypoints(workspace_id)
        road_names_with_waypoints = {w.road_name for w in waypoints if w.road_name}

        crossroads = self._repo.get_crossroads(workspace_id)
        road_names_with_crossroads = (
            {c.road_a_name for c in crossroads} | {c.road_b_name for c in crossroads}
        )

        for r in roads:
            if r.name in road_names_with_waypoints:
                raise ValueError(
                    f"Road '{r.name}' has associated waypoints and cannot be deleted"
                )
            if r.name in road_names_with_crossroads:
                raise ValueError(
                    f"Road '{r.name}' has associated crossroads and cannot be deleted"
                )

        for r in roads:
            self._repo.delete_road(r.id)
        return len(roads)

    @staticmethod
    def _dedupe_name(name: str, taken: set[str]) -> str:
        """Return `name` if free, else `name (N)` with smallest N >= 2."""
        if name not in taken:
            return name
        n = 2
        while f"{name} ({n})" in taken:
            n += 1
        return f"{name} ({n})"
