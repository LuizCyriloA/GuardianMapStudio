from __future__ import annotations

from shapely.geometry import LineString

from guardianmapstudio.domain.contracts import Crossroad, GeoPoint, Road
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

    def find_intersection_point(self, road_a: Road, road_b: Road) -> GeoPoint | None:
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
