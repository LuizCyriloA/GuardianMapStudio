from __future__ import annotations

import math

from pyproj import Transformer
from shapely.geometry import LineString, Point, Polygon
from shapely.strtree import STRtree

from guardianmapstudio.domain.contracts import (
    GeoPoint,
    RestrictedArea,
    Road,
    Waypoint,
)

EARTH_RADIUS_M = 6_371_000  # must match Guardian's geo_utils.EARTH_RADIUS_M exactly


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
            always_xy=True,  # input: (longitude, latitude)
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
    def from_centroid(cls, lat: float, lng: float) -> GeometryEngine:
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
        h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
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
        return bool(LineString(coords_a).intersects(LineString(coords_b)))

    def point_inside_polygon(self, point: GeoPoint, area: RestrictedArea) -> bool:
        """Ray-casting containment test."""
        poly_coords = [(p.longitude, p.latitude) for p in area.polygon]
        return bool(Polygon(poly_coords).contains(Point(point.longitude, point.latitude)))

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
            LineString([(p.longitude, p.latitude) for p in r.coordinates]) for r in roads
        ]
        self._road_tree = STRtree(lines)

    def build_area_tree(self, areas: list[RestrictedArea]) -> None:
        """Build (or rebuild) the restricted area spatial index."""
        self._area_index = areas
        polys = [
            Polygon([(p.longitude, p.latitude) for p in a.polygon]) for a in areas
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
