# GuardianMapStudio — Validation & Geometry Engine v2

This document defines the implementation of the four engines in
`src/guardianmapstudio/geometry/`. Each engine has a single responsibility.
The spatial standards (CRS, snap tolerance, STRtree) are defined in
doc 03 — Spatial Accuracy. This document defines the code structure,
interfaces, and rule implementations.

---

## 1. Engine Overview

```
src/guardianmapstudio/geometry/
├── __init__.py
├── engine.py         → GeometryEngine   (projections, distances, STRtree lifecycle)
├── snap.py           → SnapEngine        (snap candidates, snap algorithm)
├── crossroad.py      → CrossroadEngine   (road intersection detection)
└── validation.py     → ValidationEngine  (all validation rules, returns ValidationResult list)
```

Dependency direction:
```
ValidationEngine → GeometryEngine
SnapEngine       → GeometryEngine
CrossroadEngine  → GeometryEngine
```

No engine depends on another engine. Only `GeometryEngine` is shared.

---

## 2. GeometryEngine

File: `src/guardianmapstudio/geometry/engine.py`

**Responsibility**: projections, distances, polygon containment, STRtree
management. All other engines receive a `GeometryEngine` instance via
dependency injection.

```python
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import pyproj
from pyproj import Transformer
from shapely.geometry import LineString, Point, Polygon
from shapely.strtree import STRtree

from guardianmapstudio.domain.contracts import GeoPoint, Road, Waypoint, Crossroad, RestrictedArea

EARTH_RADIUS_M = 6_371_000   # must match Guardian's geo_utils.EARTH_RADIUS_M exactly


class GeometryEngine:
    """Spatial computation engine.

    Holds the projected CRS transformer and STRtree indices for a workspace.
    STRtrees are built lazily and invalidated on every edit operation.

    Usage:
        engine = GeometryEngine.from_centroid(lat=-20.81, lng=-49.38)
        dist = engine.haversine_distance(a, b)
        snapped = engine.snap_point(new_point, candidates)
    """

    def __init__(self, epsg_projected: int) -> None:
        self._transformer = Transformer.from_crs(
            "EPSG:4326",
            f"EPSG:{epsg_projected}",
            always_xy=True,   # input: (longitude, latitude)
        )
        self._epsg = epsg_projected
        # STRtree caches — rebuilt lazily after invalidation
        self._waypoint_tree: STRtree | None = None
        self._road_tree: STRtree | None = None
        self._area_tree: STRtree | None = None
        self._waypoint_index: list[Waypoint] = []
        self._road_index: list[Road] = []
        self._area_index: list[RestrictedArea] = []

    @classmethod
    def from_centroid(cls, lat: float, lng: float) -> "GeometryEngine":
        """Create engine with UTM projection appropriate for the given location.

        Current implementation: SIRGAS 2000 / UTM Southern Hemisphere only.
        This covers 100% of Brazilian territory (the target deployment environment).

        For global support (future): replace with pyproj.database.query_utm_crs_info()
        which auto-detects the correct UTM zone and hemisphere for any coordinate.
        """
        zone = int((lng + 180) / 6) + 1
        if lat >= 0:
            # Northern hemisphere — WGS 84 / UTM Zone Nk (EPSG: 32600 + zone)
            # Untested: no Brazilian condominium is in the Northern hemisphere.
            epsg = 32600 + zone
        else:
            # Southern hemisphere — SIRGAS 2000 / UTM Zone Sk (EPSG: 31960 + zone)
            epsg = 31960 + zone
        return cls(epsg)

    # ------------------------------------------------------------------
    # Projection
    # ------------------------------------------------------------------

    def project(self, point: GeoPoint) -> tuple[float, float]:
        """Project EPSG:4326 → UTM. Returns (x_meters, y_meters)."""
        x, y = self._transformer.transform(point.longitude, point.latitude)
        return x, y

    def project_all(self, points: list[GeoPoint]) -> list[tuple[float, float]]:
        """Project a list of GeoPoints to UTM."""
        return [self.project(p) for p in points]

    # ------------------------------------------------------------------
    # Distances
    # ------------------------------------------------------------------

    def haversine_distance(self, a: GeoPoint, b: GeoPoint) -> float:
        """Great-circle distance in meters. Same formula as Guardian geo_utils."""
        lat1 = math.radians(a.latitude)
        lat2 = math.radians(b.latitude)
        dlat = math.radians(b.latitude - a.latitude)
        dlng = math.radians(b.longitude - a.longitude)
        h = (math.sin(dlat / 2) ** 2
             + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2)
        return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))

    def projected_distance(self, a: GeoPoint, b: GeoPoint) -> float:
        """Euclidean distance in projected meters. More accurate than haversine
        for very short distances (< 100m) such as snap tolerance checks."""
        ax, ay = self.project(a)
        bx, by = self.project(b)
        return math.sqrt((ax - bx) ** 2 + (ay - by) ** 2)

    def point_to_segment_distance(
        self, point: GeoPoint, seg_start: GeoPoint, seg_end: GeoPoint
    ) -> float:
        """Minimum distance in meters from point to a line segment.
        Uses flat local projection (same as Guardian geo_utils._to_local)."""
        px, py = self._to_local(point, seg_start)
        ex, ey = self._to_local(seg_end, seg_start)
        seg_len_sq = ex * ex + ey * ey
        if seg_len_sq == 0:
            return math.sqrt(px * px + py * py)
        t = max(0.0, min(1.0, (px * ex + py * ey) / seg_len_sq))
        nx, ny = t * ex, t * ey
        return math.sqrt((px - nx) ** 2 + (py - ny) ** 2)

    def _to_local(self, point: GeoPoint, origin: GeoPoint) -> tuple[float, float]:
        """Local flat metric coordinates relative to origin (same as Guardian)."""
        dlat = math.radians(point.latitude - origin.latitude)
        dlng = math.radians(point.longitude - origin.longitude)
        avg_lat = math.radians((point.latitude + origin.latitude) / 2)
        x = dlng * math.cos(avg_lat) * EARTH_RADIUS_M
        y = dlat * EARTH_RADIUS_M
        return x, y

    # ------------------------------------------------------------------
    # Geometry checks
    # ------------------------------------------------------------------

    def roads_intersect(self, road_a: Road, road_b: Road) -> bool:
        """Check if two road polylines geometrically intersect."""
        coords_a = [(p.longitude, p.latitude) for p in road_a.coordinates]
        coords_b = [(p.longitude, p.latitude) for p in road_b.coordinates]
        if len(coords_a) < 2 or len(coords_b) < 2:
            return False
        return LineString(coords_a).intersects(LineString(coords_b))

    def point_inside_polygon(self, point: GeoPoint, area: RestrictedArea) -> bool:
        """Ray-casting containment test."""
        poly_coords = [(p.longitude, p.latitude) for p in area.polygon]
        return Polygon(poly_coords).contains(Point(point.longitude, point.latitude))

    # ------------------------------------------------------------------
    # STRtree management
    # ------------------------------------------------------------------

    def build_waypoint_tree(self, waypoints: list[Waypoint]) -> None:
        """Build (or rebuild) the waypoint spatial index."""
        self._waypoint_index = waypoints
        points = [Point(w.position.longitude, w.position.latitude) for w in waypoints]
        self._waypoint_tree = STRtree(points)

    def build_road_tree(self, roads: list[Road]) -> None:
        """Build (or rebuild) the road spatial index (uses bounding boxes)."""
        self._road_index = roads
        lines = [
            LineString([(p.longitude, p.latitude) for p in r.coordinates])
            for r in roads
        ]
        self._road_tree = STRtree(lines)

    def build_area_tree(self, areas: list[RestrictedArea]) -> None:
        """Build (or rebuild) the restricted area spatial index."""
        self._area_index = areas
        polys = [
            Polygon([(p.longitude, p.latitude) for p in a.polygon])
            for a in areas
        ]
        self._area_tree = STRtree(polys)

    def invalidate_all(self) -> None:
        """Invalidate all STRtree caches. Call after any workspace edit."""
        self._waypoint_tree = None
        self._road_tree = None
        self._area_tree = None
        self._waypoint_index = []
        self._road_index = []
        self._area_index = []
```

---

## 3. SnapEngine

File: `src/guardianmapstudio/geometry/snap.py`

**Responsibility**: given a new point, find the nearest snap candidate
within tolerance and return a `SnapResult`. Full algorithm in doc 03.

```python
from __future__ import annotations

from shapely.geometry import Point

from guardianmapstudio.domain.contracts import GeoPoint, Road, Waypoint, SnapResult
from guardianmapstudio.geometry.engine import GeometryEngine


class SnapEngine:
    """Snaps new points to existing geometry within tolerance.

    Snap candidates (MVP01):
      - Road endpoints (first and last point of each road)
      - Existing waypoint positions

    Road midpoint vertices and road-to-segment snapping: MVP02.
    """

    def __init__(self, engine: GeometryEngine, tolerance_m: float = 0.5) -> None:
        self._engine = engine
        self._tolerance_m = tolerance_m

    def snap(
        self,
        new_point: GeoPoint,
        roads: list[Road],
        waypoints: list[Waypoint],
    ) -> SnapResult:
        """Find closest snap candidate within tolerance.

        Returns SnapResult with snapped=True if any candidate is within
        self._tolerance_m (projected meters).
        """
        candidates: list[GeoPoint] = []

        # Collect road endpoints
        for road in roads:
            if len(road.coordinates) >= 2:
                candidates.append(road.coordinates[0])
                candidates.append(road.coordinates[-1])

        # Collect waypoint positions
        for wp in waypoints:
            candidates.append(wp.position)

        if not candidates:
            return SnapResult(
                original=new_point,
                snapped_to=new_point,
                snapped=False,
                distance_meters=0.0,
            )

        # Find closest candidate in projected space
        best_candidate: GeoPoint | None = None
        best_dist = float("inf")

        for candidate in candidates:
            dist = self._engine.projected_distance(new_point, candidate)
            if dist < best_dist:
                best_dist = dist
                best_candidate = candidate

        if best_candidate is not None and best_dist <= self._tolerance_m:
            return SnapResult(
                original=new_point,
                snapped_to=best_candidate,
                snapped=True,
                distance_meters=best_dist,
            )

        return SnapResult(
            original=new_point,
            snapped_to=new_point,
            snapped=False,
            distance_meters=0.0,
        )
```

---

## 4. CrossroadEngine

File: `src/guardianmapstudio/geometry/crossroad.py`

**Responsibility**: detect whether two roads geometrically intersect,
and find approximate intersection coordinates. Used by the validation
rule `crossroad.roads_intersect` and future auto-detection (MVP02).

```python
from __future__ import annotations

from shapely.geometry import LineString

from guardianmapstudio.domain.contracts import GeoPoint, Road, Crossroad
from guardianmapstudio.geometry.engine import GeometryEngine


class CrossroadEngine:
    """Geometric crossroad analysis.

    MVP01: validates that manually placed crossroads are near actual intersections.
    MVP02: auto-detects intersections and suggests crossroad placement.
    """

    # Crossroad marker must be within this many meters of the actual
    # road intersection to pass the crossroad.roads_intersect WARNING check.
    INTERSECTION_PROXIMITY_M = 1.0

    def __init__(self, engine: GeometryEngine) -> None:
        self._engine = engine

    def roads_intersect(self, road_a: Road, road_b: Road) -> bool:
        """Return True if the two road polylines geometrically cross."""
        return self._engine.roads_intersect(road_a, road_b)

    def find_intersection_point(
        self, road_a: Road, road_b: Road
    ) -> GeoPoint | None:
        """Return the approximate intersection GeoPoint, or None if roads don't cross.

        Uses Shapely's intersection() which returns the exact crossing point
        in EPSG:4326. Only returns a point (not a line — parallel roads
        that overlap return None).
        """
        coords_a = [(p.longitude, p.latitude) for p in road_a.coordinates]
        coords_b = [(p.longitude, p.latitude) for p in road_b.coordinates]
        if len(coords_a) < 2 or len(coords_b) < 2:
            return None

        intersection = LineString(coords_a).intersection(LineString(coords_b))
        if intersection.is_empty or intersection.geom_type != "Point":
            return None

        return GeoPoint(latitude=intersection.y, longitude=intersection.x)

    def crossroad_is_near_intersection(
        self, crossroad: Crossroad, road_a: Road, road_b: Road
    ) -> bool:
        """Check if a crossroad marker is placed near the actual road intersection.

        Returns True (valid) if:
          - The two roads geometrically intersect, AND
          - The crossroad position is within INTERSECTION_PROXIMITY_M of
            the intersection point.

        Returns False (warning) if the roads don't intersect or the marker
        is placed too far from the actual crossing.
        """
        intersection_point = self.find_intersection_point(road_a, road_b)
        if intersection_point is None:
            return False

        dist = self._engine.projected_distance(crossroad.position, intersection_point)
        return dist <= self.INTERSECTION_PROXIMITY_M
```

---

## 5. ValidationEngine

File: `src/guardianmapstudio/geometry/validation.py`

**Responsibility**: apply all validation rules to a workspace and return
a complete list of `ValidationResult` objects. Each rule is a private method.
Rules are grouped by entity type and run in order.

```python
from __future__ import annotations

from guardianmapstudio.domain.contracts import (
    ValidationResult, ValidationSeverity,
    Road, Waypoint, Crossroad, RestrictedArea,
    GateType, WaypointType,
)
from guardianmapstudio.geometry.engine import GeometryEngine
from guardianmapstudio.geometry.crossroad import CrossroadEngine


class ValidationEngine:
    """Applies all validation rules to a workspace.

    Usage:
        engine = ValidationEngine(geometry_engine)
        results = engine.validate(roads, waypoints, crossroads, areas)
        errors = [r for r in results if r.is_blocking]
    """

    DUPLICATE_POSITION_M = 0.5      # matches snap tolerance (doc 03)
    CROSSROAD_PROXIMITY_M = 1.0     # matches CrossroadEngine.INTERSECTION_PROXIMITY_M

    def __init__(self, geometry_engine: GeometryEngine) -> None:
        self._geo = geometry_engine
        self._crossroad_engine = CrossroadEngine(geometry_engine)

    def validate(
        self,
        roads: list[Road],
        waypoints: list[Waypoint],
        crossroads: list[Crossroad],
        areas: list[RestrictedArea],
    ) -> list[ValidationResult]:
        """Run all rules. Returns complete list of errors and warnings."""
        results: list[ValidationResult] = []

        results.extend(self._validate_workspace(roads))
        results.extend(self._validate_roads(roads))
        results.extend(self._validate_waypoints(waypoints, roads))
        results.extend(self._validate_crossroads(crossroads, roads))
        results.extend(self._validate_areas(areas))

        return results

    # ------------------------------------------------------------------
    # Workspace-level rules
    # ------------------------------------------------------------------

    def _validate_workspace(self, roads: list[Road]) -> list[ValidationResult]:
        results = []
        # workspace.min_roads: ERROR if no roads at all
        if len(roads) == 0:
            results.append(ValidationResult(
                severity=ValidationSeverity.ERROR,
                rule_id="workspace.min_roads",
                message="The workspace has no roads. Add at least one road before publishing.",
                affected_entity_type="workspace",
                affected_entity_id=0,
            ))
        return results

    # ------------------------------------------------------------------
    # Road rules
    # ------------------------------------------------------------------

    def _validate_roads(self, roads: list[Road]) -> list[ValidationResult]:
        results = []
        road_names: dict[str, int] = {}

        for road in roads:
            # road.min_points
            if len(road.coordinates) < 2:
                results.append(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    rule_id="road.min_points",
                    message=f"Road '{road.name}' has only {len(road.coordinates)} point(s). Minimum is 2.",
                    affected_entity_type="road",
                    affected_entity_id=road.id,
                ))

            # road.name_unique
            if road.name in road_names:
                results.append(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    rule_id="road.name_unique",
                    message=f"Road name '{road.name}' is already used by another road in this workspace.",
                    affected_entity_type="road",
                    affected_entity_id=road.id,
                ))
            else:
                road_names[road.name] = road.id

            # road.speed_limit_positive
            if road.speed_limit_kmh <= 0:
                results.append(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    rule_id="road.speed_limit_positive",
                    message=f"Road '{road.name}' has invalid speed limit: {road.speed_limit_kmh} km/h. Must be > 0.",
                    affected_entity_type="road",
                    affected_entity_id=road.id,
                ))

            # road.width_positive
            if road.width_meters <= 0:
                results.append(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    rule_id="road.width_positive",
                    message=f"Road '{road.name}' has invalid width: {road.width_meters} m. Must be > 0.",
                    affected_entity_type="road",
                    affected_entity_id=road.id,
                ))

        # road.no_waypoints is checked in _validate_waypoints() because it
        # needs both the roads list and the waypoints list simultaneously.
        # It is NOT checked here to avoid requiring waypoints as a parameter
        # of _validate_roads().

        return results

    def _validate_roads_waypoint_coverage(
        self, roads: list[Road], waypoints: list[Waypoint]
    ) -> list[ValidationResult]:
        """road.no_waypoints — separate method because it needs waypoints."""
        results = []
        roads_with_waypoints = {w.road_name for w in waypoints if w.road_name is not None}
        for road in roads:
            if road.name not in roads_with_waypoints:
                results.append(ValidationResult(
                    severity=ValidationSeverity.WARNING,
                    rule_id="road.no_waypoints",
                    message=f"Road '{road.name}' has no waypoints. Consider adding stop signs, speed bumps, or other markers.",
                    affected_entity_type="road",
                    affected_entity_id=road.id,
                ))
        return results

    # ------------------------------------------------------------------
    # Waypoint rules
    # ------------------------------------------------------------------

    def _validate_waypoints(
        self, waypoints: list[Waypoint], roads: list[Road]
    ) -> list[ValidationResult]:
        results = []
        road_names = {r.name for r in roads}

        for wp in waypoints:
            # waypoint.name_not_empty
            if not wp.name or not wp.name.strip():
                results.append(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    rule_id="waypoint.name_not_empty",
                    message="A waypoint has an empty name. All waypoints must have a non-blank name.",
                    affected_entity_type="waypoint",
                    affected_entity_id=wp.id,
                ))

            # waypoint.road_exists
            if wp.road_name is not None and wp.road_name not in road_names:
                results.append(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    rule_id="waypoint.road_exists",
                    message=f"Waypoint '{wp.name}' references road '{wp.road_name}' which does not exist in this workspace.",
                    affected_entity_type="waypoint",
                    affected_entity_id=wp.id,
                ))

            # waypoint.heading_range
            if wp.heading_degrees is not None:
                if not (0.0 <= wp.heading_degrees <= 360.0):
                    results.append(ValidationResult(
                        severity=ValidationSeverity.ERROR,
                        rule_id="waypoint.heading_range",
                        message=f"Waypoint '{wp.name}' heading {wp.heading_degrees}° is outside valid range 0–360.",
                        affected_entity_type="waypoint",
                        affected_entity_id=wp.id,
                    ))

            # waypoint.speed_bump_height
            if wp.waypoint_type == WaypointType.SPEED_BUMP:
                height = wp.extra_data.get("height_cm")
                if height is None or not isinstance(height, (int, float)) or height <= 0:
                    results.append(ValidationResult(
                        severity=ValidationSeverity.ERROR,
                        rule_id="waypoint.speed_bump_height",
                        message=f"Speed bump '{wp.name}' must have extra_data.height_cm > 0.",
                        affected_entity_type="waypoint",
                        affected_entity_id=wp.id,
                    ))

            # waypoint.gate_type_valid
            if wp.waypoint_type == WaypointType.GATE:
                gate_type = wp.extra_data.get("gate_type")
                valid_gate_types = {gt.value for gt in GateType}
                if gate_type not in valid_gate_types:
                    results.append(ValidationResult(
                        severity=ValidationSeverity.ERROR,
                        rule_id="waypoint.gate_type_valid",
                        message=f"Gate '{wp.name}' must have extra_data.gate_type set to one of: {sorted(valid_gate_types)}.",
                        affected_entity_type="waypoint",
                        affected_entity_id=wp.id,
                    ))

        # waypoint.duplicate_position: WARNING for pairs within 0.5m
        # Complexity: O(n²) where n = number of waypoints.
        # Acceptable for MVP01 (max ~80 waypoints per condominium map).
        # For n=80: 3,160 comparisons per validation run — negligible.
        # If maps grow beyond 500 waypoints, replace with STRtree nearest-neighbor.
        for i, wp_a in enumerate(waypoints):
            for wp_b in waypoints[i + 1:]:
                dist = self._geo.haversine_distance(wp_a.position, wp_b.position)
                if dist < self.DUPLICATE_POSITION_M:
                    results.append(ValidationResult(
                        severity=ValidationSeverity.WARNING,
                        rule_id="waypoint.duplicate_position",
                        message=(
                            f"Waypoints '{wp_a.name}' and '{wp_b.name}' are {dist:.2f}m apart "
                            f"(less than snap tolerance of {self.DUPLICATE_POSITION_M}m). "
                            "They may be duplicates."
                        ),
                        affected_entity_type="waypoint",
                        affected_entity_id=wp_a.id,
                    ))

        # road.no_waypoints: WARNING for each road with no associated waypoints
        # Placed here because it needs both roads and waypoints lists
        results.extend(self._validate_roads_waypoint_coverage(roads, waypoints))

        return results

    # ------------------------------------------------------------------
    # Crossroad rules
    # ------------------------------------------------------------------

    def _validate_crossroads(
        self, crossroads: list[Crossroad], roads: list[Road]
    ) -> list[ValidationResult]:
        results = []
        road_map: dict[str, Road] = {r.name: r for r in roads}

        for cr in crossroads:
            road_a = road_map.get(cr.road_a_name)
            road_b = road_map.get(cr.road_b_name)

            # crossroad.road_a_exists
            if road_a is None:
                results.append(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    rule_id="crossroad.road_a_exists",
                    message=f"Crossroad references road '{cr.road_a_name}' which does not exist in this workspace.",
                    affected_entity_type="crossroad",
                    affected_entity_id=cr.id,
                ))

            # crossroad.road_b_exists
            if road_b is None:
                results.append(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    rule_id="crossroad.road_b_exists",
                    message=f"Crossroad references road '{cr.road_b_name}' which does not exist in this workspace.",
                    affected_entity_type="crossroad",
                    affected_entity_id=cr.id,
                ))

            # crossroad.roads_distinct
            if cr.road_a_name == cr.road_b_name:
                results.append(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    rule_id="crossroad.roads_distinct",
                    message=f"Crossroad has road_a and road_b both set to '{cr.road_a_name}'. They must be different roads.",
                    affected_entity_type="crossroad",
                    affected_entity_id=cr.id,
                ))

            # crossroad.roads_intersect (WARNING — only if both roads exist)
            if road_a is not None and road_b is not None:
                near = self._crossroad_engine.crossroad_is_near_intersection(cr, road_a, road_b)
                if not near:
                    results.append(ValidationResult(
                        severity=ValidationSeverity.WARNING,
                        rule_id="crossroad.roads_intersect",
                        message=(
                            f"Crossroad between '{cr.road_a_name}' and '{cr.road_b_name}' is not "
                            f"near a geometric intersection of those roads "
                            f"(within {self.CROSSROAD_PROXIMITY_M}m). "
                            "Check that the roads actually cross at this point."
                        ),
                        affected_entity_type="crossroad",
                        affected_entity_id=cr.id,
                    ))

        return results

    # ------------------------------------------------------------------
    # Restricted area rules
    # ------------------------------------------------------------------

    def _validate_areas(self, areas: list[RestrictedArea]) -> list[ValidationResult]:
        results = []

        for area in areas:
            # area.min_points
            if len(area.polygon) < 3:
                results.append(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    rule_id="area.min_points",
                    message=f"Restricted area '{area.name}' has only {len(area.polygon)} point(s). Polygon requires at least 3.",
                    affected_entity_type="restricted_area",
                    affected_entity_id=area.id,
                ))

            # area.name_not_empty
            if not area.name or not area.name.strip():
                results.append(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    rule_id="area.name_not_empty",
                    message="A restricted area has an empty name. All areas must have a non-blank name.",
                    affected_entity_type="restricted_area",
                    affected_entity_id=area.id,
                ))

            # area.speed_limit_required
            if area.restriction_type.value == "speed_limit" and area.speed_limit_kmh is None:
                results.append(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    rule_id="area.speed_limit_required",
                    message=f"Restricted area '{area.name}' has restriction type 'speed_limit' but no speed_limit_kmh set.",
                    affected_entity_type="restricted_area",
                    affected_entity_id=area.id,
                ))

            # area.speed_limit_positive
            if area.speed_limit_kmh is not None and area.speed_limit_kmh <= 0:
                results.append(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    rule_id="area.speed_limit_positive",
                    message=f"Restricted area '{area.name}' has speed_limit_kmh={area.speed_limit_kmh}. Must be > 0.",
                    affected_entity_type="restricted_area",
                    affected_entity_id=area.id,
                ))

        return results
```

---

## 6. Engine Integration — How Engines Are Wired

The engines are constructed once per request via FastAPI dependency injection.
The `GeometryEngine` is initialized from the workspace's map centroid.

```python
# src/guardianmapstudio/api/deps.py

from guardianmapstudio.geometry.engine import GeometryEngine
from guardianmapstudio.geometry.snap import SnapEngine
from guardianmapstudio.geometry.crossroad import CrossroadEngine
from guardianmapstudio.geometry.validation import ValidationEngine
from guardianmapstudio.config.settings import GuardianMapStudioSettings


def get_geometry_engine(
    centroid_lat: float,
    centroid_lng: float,
    settings: GuardianMapStudioSettings,
) -> GeometryEngine:
    engine = GeometryEngine.from_centroid(centroid_lat, centroid_lng)
    return engine


def get_snap_engine(
    geo: GeometryEngine,
    settings: GuardianMapStudioSettings,
) -> SnapEngine:
    return SnapEngine(geo, tolerance_m=settings.snap_tolerance_m)


def get_validation_engine(geo: GeometryEngine) -> ValidationEngine:
    return ValidationEngine(geo)
```

**Map centroid**: computed from the average of all road endpoint coordinates
in the workspace. For an empty workspace, default to `lat=-23.5, lng=-46.6`
(São Paulo region). This default only affects UTM zone selection and has
no impact on correctness for the first road drawn.

---

## 7. GuardianExporter

File: `src/guardianmapstudio/export/guardian_exporter.py`

**Responsibility**: serialize a published Version into the canonical Guardian
JSON format (ADR-002 in Architecture).

```python
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from guardianmapstudio.domain.contracts import (
    Road, Waypoint, Crossroad, RestrictedArea,
    ExportMeta, ExportRecord, Version,
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
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "schema_version": self.SCHEMA_VERSION,
        }

        p = coordinate_precision

        data = {
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
                self._serialize_waypoint(w, p)
                for w in waypoints
                if w.active
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

    def _serialize_waypoint(self, w: Waypoint, precision: int) -> dict:
        """Serialize one Waypoint to Guardian export format.

        Key name is 'type' (NOT 'waypoint_type') — Guardian's seed_from_json()
        expects exactly this key name.
        """
        entry: dict = {
            "name": w.name,
            "type": w.waypoint_type.value,   # Guardian expects "type", not "waypoint_type"
            "lat": round(w.position.latitude, precision),
            "lng": round(w.position.longitude, precision),
            "road": w.road_name,             # string or null — never omit
            "extra_data": w.extra_data,      # always included, even when {}
        }
        # heading_degrees: only include key when not None
        if w.heading_degrees is not None:
            entry["heading_degrees"] = round(w.heading_degrees, 1)
        return entry
```

---

## 8. Unit Tests

**tests/unit/test_geometry_engine.py**
```
test_haversine_known_distance          → two points 100m apart return ~100m
test_haversine_matches_guardian        → same result as Guardian's geo_utils formula
test_projected_distance_snap_scale     → 0.5m in projection matches tolerance
test_roads_intersect_crossing          → perpendicular roads return True
test_roads_intersect_parallel          → parallel roads return False
test_point_inside_polygon              → known interior point returns True
test_point_outside_polygon             → known exterior point returns False
```

**tests/unit/test_snap_engine.py**
```
test_snap_within_tolerance             → point 0.3m from endpoint → snapped=True
test_snap_outside_tolerance            → point 0.6m from endpoint → snapped=False
test_snap_exact_coincident             → point at 0.0m → snapped=True, dist=0.0
test_snap_no_candidates                → empty workspace → snapped=False
test_snap_returns_closest              → two candidates, returns nearest
test_snap_respects_custom_tolerance    → tolerance=1.0m snaps at 0.8m
```

**tests/unit/test_validation_engine.py**
```
test_road_min_points_error             → road with 1 point → ERROR road.min_points
test_road_name_unique_error            → two roads same name → ERROR road.name_unique
test_road_speed_limit_error            → speed_limit=0 → ERROR road.speed_limit_positive
test_road_no_waypoints_warning         → road with no waypoints → WARNING road.no_waypoints
test_waypoint_name_empty_error         → blank name → ERROR waypoint.name_not_empty
test_waypoint_road_exists_error        → road_name missing → ERROR waypoint.road_exists
test_waypoint_speed_bump_no_height     → speed_bump without height_cm → ERROR
test_waypoint_gate_invalid_type        → gate with bad gate_type → ERROR
test_waypoint_heading_out_of_range     → heading=400 → ERROR waypoint.heading_range
test_waypoint_duplicate_position       → two waypoints 0.3m apart → WARNING
test_crossroad_road_a_missing          → road_a not in workspace → ERROR
test_crossroad_roads_identical         → road_a == road_b → ERROR
test_crossroad_not_near_intersection   → marker far from crossing → WARNING
test_area_min_points_error             → polygon 2 points → ERROR area.min_points
test_area_speed_limit_required         → speed_limit type, no value → ERROR
test_workspace_no_roads_error          → empty workspace → ERROR workspace.min_roads
test_valid_workspace_no_results        → correct map → empty results list
test_can_publish_with_warnings         → warnings only → error_count=0
```

**tests/unit/test_guardian_exporter.py**
```
test_export_produces_valid_json        → output is parseable JSON
test_export_meta_fields_present        → meta block has all required keys
test_export_schema_version_1_0         → meta.schema_version == "1.0"
test_waypoint_type_key_is_type         → key is "type" not "waypoint_type"
test_waypoint_road_key_present         → "road" key always present (even null)
test_heading_omitted_when_null         → no heading_degrees key when null
test_extra_data_always_present         → extra_data: {} for waypoints with no extras
test_inactive_waypoints_excluded       → active=False waypoints not in export
test_coordinate_precision_7dp          → lat/lng rounded to 7 decimal places
test_export_passes_guardian_seed       → exported file accepted by seed_from_json()
```
