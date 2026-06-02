from __future__ import annotations

from guardianmapstudio.domain.contracts import GeoPoint, Road, SnapResult, Waypoint
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
