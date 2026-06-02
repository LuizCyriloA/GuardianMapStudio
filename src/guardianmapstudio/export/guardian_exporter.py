from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from guardianmapstudio.domain.contracts import (
    Crossroad,
    RestrictedArea,
    Road,
    Version,
    Waypoint,
)


class GuardianExporter:
    """Produces the canonical Guardian JSON export file.

    The output must pass Guardian's seed_from_json() without error.
    Field names and structure match exactly what Guardian expects.
    """

    SCHEMA_VERSION = "1.0"

    def export(
        self,
        version: Version,
        project_name: str,
        roads: list[Road],
        waypoints: list[Waypoint],
        crossroads: list[Crossroad],
        areas: list[RestrictedArea],
        output_path: Path,
        coordinate_precision: int = 7,
    ) -> int:
        """Write the export JSON file. Returns file size in bytes."""
        meta = {
            "exported_by": "GuardianMapStudio",
            "version_id": version.id,
            "version_name": version.name,
            "project_name": project_name,
            "exported_at": datetime.now(UTC).isoformat(),
            "schema_version": self.SCHEMA_VERSION,
        }

        p = coordinate_precision

        data: dict[str, Any] = {
            "meta": meta,
            "roads": [
                {
                    "name": r.name,
                    "coordinates": [
                        {"lat": round(pt.latitude, p), "lng": round(pt.longitude, p)}
                        for pt in r.coordinates
                    ],
                    "speed_limit_kmh": r.speed_limit_kmh,
                    "direction": r.direction.value,
                    "width_meters": r.width_meters,
                }
                for r in roads
            ],
            "waypoints": [
                self._serialize_waypoint(w, p) for w in waypoints if w.active
            ],
            "crossroads": [
                {
                    "road_a": cr.road_a_name,
                    "road_b": cr.road_b_name,
                    "lat": round(cr.position.latitude, p),
                    "lng": round(cr.position.longitude, p),
                }
                for cr in crossroads
            ],
            "restricted_areas": [
                {
                    "name": a.name,
                    "polygon": [
                        {"lat": round(pt.latitude, p), "lng": round(pt.longitude, p)}
                        for pt in a.polygon
                    ],
                    "restriction_type": a.restriction_type.value,
                    "speed_limit_kmh": a.speed_limit_kmh,
                    "active": a.active,
                }
                for a in areas
            ],
        }

        content = json.dumps(data, indent=2, ensure_ascii=False)
        output_path.write_text(content, encoding="utf-8")
        return len(content.encode("utf-8"))

    def _serialize_waypoint(self, w: Waypoint, precision: int) -> dict[str, Any]:
        """Serialize one Waypoint to Guardian export format.

        Key name is 'type' (NOT 'waypoint_type') — Guardian's seed_from_json()
        expects exactly this key name.
        """
        entry: dict[str, Any] = {
            "name": w.name,
            "type": w.waypoint_type.value,  # Guardian expects "type", not "waypoint_type"
            "lat": round(w.position.latitude, precision),
            "lng": round(w.position.longitude, precision),
            "road": w.road_name,  # string or null — never omit
            "extra_data": w.extra_data,  # always included, even when {}
        }
        # heading_degrees: only include key when not None
        if w.heading_degrees is not None:
            entry["heading_degrees"] = round(w.heading_degrees, 1)
        return entry
