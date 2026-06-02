from __future__ import annotations

from guardianmapstudio.domain.contracts import (
    Crossroad,
    GateType,
    RestrictedArea,
    Road,
    ValidationResult,
    ValidationSeverity,
    Waypoint,
    WaypointType,
)
from guardianmapstudio.geometry.crossroad import CrossroadEngine
from guardianmapstudio.geometry.engine import GeometryEngine


class ValidationEngine:
    """Applies all validation rules to a workspace.

    Usage:
        engine = ValidationEngine(geometry_engine)
        results = engine.validate(roads, waypoints, crossroads, areas)
        errors = [r for r in results if r.is_blocking]
    """

    DUPLICATE_POSITION_M = 0.5  # matches snap tolerance (doc 03)
    CROSSROAD_PROXIMITY_M = 1.0  # matches CrossroadEngine.INTERSECTION_PROXIMITY_M

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
            results.append(
                ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    rule_id="workspace.min_roads",
                    message="The workspace has no roads. Add at least one road before publishing.",
                    affected_entity_type="workspace",
                    affected_entity_id=0,
                )
            )
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
                results.append(
                    ValidationResult(
                        severity=ValidationSeverity.ERROR,
                        rule_id="road.min_points",
                        message=(
                            f"Road '{road.name}' has only {len(road.coordinates)} point(s)."
                            " Minimum is 2."
                        ),
                        affected_entity_type="road",
                        affected_entity_id=road.id,
                    )
                )

            # road.name_unique
            if road.name in road_names:
                results.append(
                    ValidationResult(
                        severity=ValidationSeverity.ERROR,
                        rule_id="road.name_unique",
                        message=(
                            f"Road name '{road.name}' is already used by another road"
                            " in this workspace."
                        ),
                        affected_entity_type="road",
                        affected_entity_id=road.id,
                    )
                )
            else:
                road_names[road.name] = road.id

            # road.speed_limit_positive
            if road.speed_limit_kmh <= 0:
                results.append(
                    ValidationResult(
                        severity=ValidationSeverity.ERROR,
                        rule_id="road.speed_limit_positive",
                        message=(
                            f"Road '{road.name}' has invalid speed limit:"
                            f" {road.speed_limit_kmh} km/h. Must be > 0."
                        ),
                        affected_entity_type="road",
                        affected_entity_id=road.id,
                    )
                )

            # road.width_positive
            if road.width_meters <= 0:
                results.append(
                    ValidationResult(
                        severity=ValidationSeverity.ERROR,
                        rule_id="road.width_positive",
                        message=(
                            f"Road '{road.name}' has invalid width:"
                            f" {road.width_meters} m. Must be > 0."
                        ),
                        affected_entity_type="road",
                        affected_entity_id=road.id,
                    )
                )

        # road.no_waypoints is checked in _validate_waypoints() because it
        # needs both the roads list and the waypoints list simultaneously.

        return results

    def _validate_roads_waypoint_coverage(
        self, roads: list[Road], waypoints: list[Waypoint]
    ) -> list[ValidationResult]:
        """road.no_waypoints — separate method because it needs waypoints."""
        results = []
        roads_with_waypoints = {w.road_name for w in waypoints if w.road_name is not None}
        for road in roads:
            if road.name not in roads_with_waypoints:
                results.append(
                    ValidationResult(
                        severity=ValidationSeverity.WARNING,
                        rule_id="road.no_waypoints",
                        message=(
                            f"Road '{road.name}' has no waypoints. Consider adding"
                            " stop signs, speed bumps, or other markers."
                        ),
                        affected_entity_type="road",
                        affected_entity_id=road.id,
                    )
                )
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
                results.append(
                    ValidationResult(
                        severity=ValidationSeverity.ERROR,
                        rule_id="waypoint.name_not_empty",
                        message=(
                            "A waypoint has an empty name."
                            " All waypoints must have a non-blank name."
                        ),
                        affected_entity_type="waypoint",
                        affected_entity_id=wp.id,
                    )
                )

            # waypoint.road_exists
            if wp.road_name is not None and wp.road_name not in road_names:
                results.append(
                    ValidationResult(
                        severity=ValidationSeverity.ERROR,
                        rule_id="waypoint.road_exists",
                        message=(
                            f"Waypoint '{wp.name}' references road '{wp.road_name}'"
                            " which does not exist in this workspace."
                        ),
                        affected_entity_type="waypoint",
                        affected_entity_id=wp.id,
                    )
                )

            # waypoint.heading_range
            if wp.heading_degrees is not None:
                if not (0.0 <= wp.heading_degrees <= 360.0):
                    results.append(
                        ValidationResult(
                            severity=ValidationSeverity.ERROR,
                            rule_id="waypoint.heading_range",
                            message=(
                                f"Waypoint '{wp.name}' heading {wp.heading_degrees}°"
                                " is outside valid range 0–360."
                            ),
                            affected_entity_type="waypoint",
                            affected_entity_id=wp.id,
                        )
                    )

            # waypoint.speed_bump_height
            if wp.waypoint_type == WaypointType.SPEED_BUMP:
                height = wp.extra_data.get("height_cm")
                if height is None or not isinstance(height, int | float) or height <= 0:
                    results.append(
                        ValidationResult(
                            severity=ValidationSeverity.ERROR,
                            rule_id="waypoint.speed_bump_height",
                            message=f"Speed bump '{wp.name}' must have extra_data.height_cm > 0.",
                            affected_entity_type="waypoint",
                            affected_entity_id=wp.id,
                        )
                    )

            # waypoint.gate_type_valid
            if wp.waypoint_type == WaypointType.GATE:
                gate_type = wp.extra_data.get("gate_type")
                valid_gate_types = {gt.value for gt in GateType}
                if gate_type not in valid_gate_types:
                    results.append(
                        ValidationResult(
                            severity=ValidationSeverity.ERROR,
                            rule_id="waypoint.gate_type_valid",
                            message=(
                                f"Gate '{wp.name}' must have extra_data.gate_type"
                                f" set to one of: {sorted(valid_gate_types)}."
                            ),
                            affected_entity_type="waypoint",
                            affected_entity_id=wp.id,
                        )
                    )

        # waypoint.duplicate_position: WARNING for pairs within 0.5m
        # Complexity: O(n²) where n = number of waypoints.
        # Acceptable for MVP01 (max ~80 waypoints per condominium map).
        # For n=80: 3,160 comparisons per validation run — negligible.
        # If maps grow beyond 500 waypoints, replace with STRtree nearest-neighbor.
        for i, wp_a in enumerate(waypoints):
            for wp_b in waypoints[i + 1 :]:
                dist = self._geo.haversine_distance(wp_a.position, wp_b.position)
                if dist < self.DUPLICATE_POSITION_M:
                    results.append(
                        ValidationResult(
                            severity=ValidationSeverity.WARNING,
                            rule_id="waypoint.duplicate_position",
                            message=(
                                f"Waypoints '{wp_a.name}' and '{wp_b.name}'"
                                f" are {dist:.2f}m apart"
                                f" (less than snap tolerance of {self.DUPLICATE_POSITION_M}m)."
                                " They may be duplicates."
                            ),
                            affected_entity_type="waypoint",
                            affected_entity_id=wp_a.id,
                        )
                    )

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
                results.append(
                    ValidationResult(
                        severity=ValidationSeverity.ERROR,
                        rule_id="crossroad.road_a_exists",
                        message=(
                            f"Crossroad references road '{cr.road_a_name}'"
                            " which does not exist in this workspace."
                        ),
                        affected_entity_type="crossroad",
                        affected_entity_id=cr.id,
                    )
                )

            # crossroad.road_b_exists
            if road_b is None:
                results.append(
                    ValidationResult(
                        severity=ValidationSeverity.ERROR,
                        rule_id="crossroad.road_b_exists",
                        message=(
                            f"Crossroad references road '{cr.road_b_name}'"
                            " which does not exist in this workspace."
                        ),
                        affected_entity_type="crossroad",
                        affected_entity_id=cr.id,
                    )
                )

            # crossroad.roads_distinct
            if cr.road_a_name == cr.road_b_name:
                results.append(
                    ValidationResult(
                        severity=ValidationSeverity.ERROR,
                        rule_id="crossroad.roads_distinct",
                        message=(
                            f"Crossroad has road_a and road_b both set to '{cr.road_a_name}'."
                            " They must be different roads."
                        ),
                        affected_entity_type="crossroad",
                        affected_entity_id=cr.id,
                    )
                )

            # crossroad.roads_intersect (WARNING — only if both roads exist)
            if road_a is not None and road_b is not None:
                near = self._crossroad_engine.crossroad_is_near_intersection(cr, road_a, road_b)
                if not near:
                    results.append(
                        ValidationResult(
                            severity=ValidationSeverity.WARNING,
                            rule_id="crossroad.roads_intersect",
                            message=(
                                f"Crossroad between '{cr.road_a_name}' and '{cr.road_b_name}'"
                                " is not near a geometric intersection of those roads"
                                f" (within {self.CROSSROAD_PROXIMITY_M}m)."
                                " Check that the roads actually cross at this point."
                            ),
                            affected_entity_type="crossroad",
                            affected_entity_id=cr.id,
                        )
                    )

        return results

    # ------------------------------------------------------------------
    # Restricted area rules
    # ------------------------------------------------------------------

    def _validate_areas(self, areas: list[RestrictedArea]) -> list[ValidationResult]:
        results = []

        for area in areas:
            # area.min_points
            if len(area.polygon) < 3:
                results.append(
                    ValidationResult(
                        severity=ValidationSeverity.ERROR,
                        rule_id="area.min_points",
                        message=(
                            f"Restricted area '{area.name}' has only {len(area.polygon)}"
                            " point(s). Polygon requires at least 3."
                        ),
                        affected_entity_type="restricted_area",
                        affected_entity_id=area.id,
                    )
                )

            # area.name_not_empty
            if not area.name or not area.name.strip():
                results.append(
                    ValidationResult(
                        severity=ValidationSeverity.ERROR,
                        rule_id="area.name_not_empty",
                        message=(
                            "A restricted area has an empty name."
                            " All areas must have a non-blank name."
                        ),
                        affected_entity_type="restricted_area",
                        affected_entity_id=area.id,
                    )
                )

            # area.speed_limit_required
            if area.restriction_type.value == "speed_limit" and area.speed_limit_kmh is None:
                results.append(
                    ValidationResult(
                        severity=ValidationSeverity.ERROR,
                        rule_id="area.speed_limit_required",
                        message=(
                            f"Restricted area '{area.name}' has restriction type 'speed_limit'"
                            " but no speed_limit_kmh set."
                        ),
                        affected_entity_type="restricted_area",
                        affected_entity_id=area.id,
                    )
                )

            # area.speed_limit_positive
            if area.speed_limit_kmh is not None and area.speed_limit_kmh <= 0:
                results.append(
                    ValidationResult(
                        severity=ValidationSeverity.ERROR,
                        rule_id="area.speed_limit_positive",
                        message=(
                            f"Restricted area '{area.name}' has"
                            f" speed_limit_kmh={area.speed_limit_kmh}. Must be > 0."
                        ),
                        affected_entity_type="restricted_area",
                        affected_entity_id=area.id,
                    )
                )

        return results
