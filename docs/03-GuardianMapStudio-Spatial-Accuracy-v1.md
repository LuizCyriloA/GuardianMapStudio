# GuardianMapStudio — Spatial Accuracy v1

This document defines all spatial standards: coordinate systems, numerical
precision, snap tolerance, geometry algorithms, and performance requirements.
These standards are authoritative — no code in the geometry subsystem may
deviate from them without updating this document first.

---

## 1. Coordinate Reference Systems

### 1.1 Storage CRS — EPSG:4326 (WGS84)

All coordinates are stored in EPSG:4326 (WGS84 geographic coordinates).

- **Latitude**: `-90.0` to `+90.0` degrees
- **Longitude**: `-180.0` to `+180.0` degrees
- **Column type**: `REAL` in SQLite via SQLAlchemy `Double` (64-bit IEEE 754)
- **Precision**: 7 decimal places

**Rationale**: EPSG:4326 is the native format of all GPS devices, phone browsers
(`navigator.geolocation`), and the Guardian platform. Storing in any other CRS
would require a fixed regional assumption and a conversion step on every read.

**Coordinate precision — why 7 decimal places:**

| Decimal places | Resolution | Practical meaning |
|---|---|---|
| 5 | ~1.1 m | Distinguishes buildings |
| 6 | ~11 cm | Distinguishes people |
| **7** | **~1.1 cm** | **Sufficient for vehicle-scale mapping** |
| 8 | ~1.1 mm | Unnecessary for this application |

At latitude -20° (typical Brazilian condominium):
- `1e-7°` latitude = **1.11 cm**
- `1e-7°` longitude = **1.05 cm**

The snap tolerance of 0.5 m is represented as `~4.5e-6°` — well within 7 decimal
place precision. No spatial operation in GuardianMapStudio requires sub-centimeter
precision.

---

### 1.2 Calculation CRS — SIRGAS 2000 / UTM (Projected)

All metric calculations (distances, snap, polygon area, line intersection) are
performed in a **projected CRS** — never directly in EPSG:4326.

**Why projection is necessary**: EPSG:4326 is an angular coordinate system.
Arithmetic on angular coordinates produces incorrect metric results. For example,
computing Euclidean distance in degrees and multiplying by 111,320 m/degree
gives a correct latitude distance but an incorrect longitude distance because
longitude degrees vary in metric length with latitude.

**Projection used**: SIRGAS 2000 / UTM, zone determined dynamically from
the centroid of the map being processed.

| Region | Zone | EPSG |
|---|---|---|
| Most of São Paulo, Rio de Janeiro, Brasília | 23S | 31983 |
| Curitiba, Porto Alegre, west SP | 22S | 31982 |
| Recife, Salvador, eastern NE | 25S | 31985 |
| Manaus, Belém | 20S–21S | 31980–31981 |

**Implementation**: Use `pyproj.Transformer` with `always_xy=True`.
The zone is determined at `GeometryEngine` construction time from the map centroid.

```python
from pyproj import Transformer, CRS

def _utm_epsg_from_centroid(lat: float, lng: float) -> int:
    """Determine UTM EPSG code for a given centroid.

    Southern hemisphere: SIRGAS 2000 / UTM (EPSG 31960 + zone) — covers all of Brazil.
    Northern hemisphere: WGS 84 / UTM (EPSG 32600 + zone) — untested fallback.

    For full global support (future): use pyproj.database.query_utm_crs_info().
    """
    zone = int((lng + 180) / 6) + 1
    if lat >= 0:
        return 32600 + zone   # WGS 84 / UTM Northern Hemisphere
    return 31960 + zone       # SIRGAS 2000 / UTM Southern Hemisphere

transformer = Transformer.from_crs(
    CRS.from_epsg(4326),
    CRS.from_epsg(_utm_epsg_from_centroid(centroid_lat, centroid_lng)),
    always_xy=True,  # (longitude, latitude) input order
)
```

**Scope of projection**: The projected CRS is used only for within-request
calculations. Coordinates are always projected before calculation and the
result (if a distance) is returned in meters. Projected coordinates are never
stored in the database.

---

## 2. Snap Engine

### 2.1 Snap Tolerance

**Value**: `0.5 meters` (projected distance)

**Configurable via**: `STUDIO_SNAP_TOLERANCE_M` in `.env` (default: 0.5)

**Meaning**: When a new point is placed within 0.5 m (projected) of an
existing candidate, it is automatically moved to coincide exactly with
that candidate.

**In angular terms** (at latitude -20°, for reference only):
- `0.5 m ≈ 4.49e-6°` latitude
- `0.5 m ≈ 4.81e-6°` longitude

These values are not used directly — all snap calculations are done in
projected meters via `pyproj`.

### 2.2 Snap Candidates

Snap candidates are geometric objects that a new point may snap to:

| Candidate type | Snaps to | Used when |
|---|---|---|
| Road endpoint | Start or end point of any Road polyline | Placing any point |
| Waypoint position | Existing Waypoint coordinate | Placing a Waypoint |
| Road midpoint vertex | Any intermediate vertex of a Road | Moving a vertex |

**Note**: Road-to-road snapping (connecting one road's endpoint to another road's
segment) is **MVP02**. In MVP01, snap only applies to existing explicit points,
not to points along a segment.

### 2.3 Snap Algorithm

```
Input:  new_point (GeoPoint), workspace_id
Output: SnapResult

1. Project new_point to UTM → (x_new, y_new)
2. Build STRtree of all snap candidate points in workspace
3. Query STRtree for all candidates within snap_tolerance_m (bounding box)
4. For each candidate in result:
     projected_dist = euclidean_distance((x_new, y_new), projected(candidate))
     if projected_dist < snap_tolerance_m:
         keep as snap target if closest so far
5. If a snap target was found:
     return SnapResult(original=new_point, snapped_to=target,
                       snapped=True, distance_meters=projected_dist)
6. Else:
     return SnapResult(original=new_point, snapped_to=new_point,
                       snapped=False, distance_meters=0.0)
```

### 2.4 Snap is applied at create time, not at query time

Snap is applied when the operator places or moves a point (POST/PATCH).
The snapped coordinate is what gets stored in the database.
The `SnapResult` is returned in the API response so the frontend can
show feedback ("position adjusted by 0.28m").

---

## 3. STRtree — Mandatory Spatial Index

### 3.1 Rule

All proximity queries, snap candidate lookups, and polygon containment checks
**must** use Shapely's `STRtree`. Linear iteration over coordinate lists is
prohibited in production code (ADR-008).

### 3.2 What STRtree replaces

| Query | Without STRtree | With STRtree |
|---|---|---|
| Find snap candidates | O(n) iterate all points | O(log n) bounding box query |
| Find nearest waypoint | O(n) compute all distances | O(log n) nearest neighbor |
| Check polygon containment | O(n) test each polygon | O(log n) candidate filter |
| Validate crossroad proximity | O(n×m) all road pairs | O(log n) per road |

### 3.3 Construction pattern

STRtree must be rebuilt after any workspace edit. The `GeometryEngine` holds
one STRtree per entity type and rebuilds lazily (on next query after invalidation).

```python
from shapely.geometry import Point
from shapely.strtree import STRtree

# Build once from all waypoint positions
waypoint_points = [Point(w.position.longitude, w.position.latitude)
                   for w in waypoints]
tree = STRtree(waypoint_points)

# Shapely 2.x: query() returns a numpy.ndarray of INTEGER INDICES
# into the original list — NOT geometry objects.
# Use int() to convert numpy.int64 before indexing.
candidate_indices = tree.query(point.buffer(snap_tolerance_deg))

for idx in candidate_indices:
    candidate = waypoints[int(idx)]
    dist = projected_distance(new_point, candidate.position)
    # ... precise distance check in projected meters

# WRONG (Shapely 1.x pattern — breaks on Shapely 2.x):
# for geom in tree.query(point.buffer(snap_tolerance_deg)):
#     geom.distance(...)   # geom is an index, not a geometry
```

**Important**: STRtree queries use EPSG:4326 bounding boxes for the initial
spatial filter, then projected distance for the precise check. This two-step
approach avoids projecting all entities for every query.

### 3.4 STRtree lifecycle

| Event | Action |
|---|---|
| Road created/updated/deleted | Invalidate road STRtree |
| Waypoint created/updated/deleted | Invalidate waypoint STRtree |
| Crossroad created/deleted | Invalidate crossroad STRtree |
| Restricted area created/updated/deleted | Invalidate area STRtree |
| Next spatial query after invalidation | Rebuild from database |

---

## 4. Geometry Algorithms

### 4.1 Haversine distance (point-to-point)

Used for: distance between two GeoPoints (e.g. waypoint proximity check,
validation rule `waypoint.duplicate_position`).

```python
EARTH_RADIUS_M = 6_371_000  # meters — same constant as Guardian

def haversine_distance(a: GeoPoint, b: GeoPoint) -> float:
    """Distance in meters between two EPSG:4326 points."""
    lat1 = math.radians(a.latitude)
    lat2 = math.radians(b.latitude)
    dlat = math.radians(b.latitude - a.latitude)
    dlng = math.radians(b.longitude - a.longitude)
    h = (math.sin(dlat / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2)
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))
```

**This is the same formula used by Guardian's `geo_utils.haversine_distance()`.**
The constant `EARTH_RADIUS_M = 6_371_000` must be identical in both projects.
Do not use `math.atan2` — the formula above uses `math.asin(math.sqrt(h))`.

### 4.2 Point-to-segment distance (for road proximity)

Used for: finding distance from a point to the nearest segment of a road polyline
(validation rule `crossroad.roads_intersect`).

Uses the flat-projection approach with `_to_local()` (same as Guardian):

```python
def _to_local(point: GeoPoint, origin: GeoPoint) -> tuple[float, float]:
    """Convert GeoPoint to local flat metric coordinates relative to origin."""
    dlat = math.radians(point.latitude - origin.latitude)
    dlng = math.radians(point.longitude - origin.longitude)
    avg_lat = math.radians((point.latitude + origin.latitude) / 2)
    x = dlng * math.cos(avg_lat) * EARTH_RADIUS_M
    y = dlat * EARTH_RADIUS_M
    return x, y
```

### 4.3 Polygon containment (ray casting)

Used for: checking if a point is inside a RestrictedArea polygon
(future: validation rule `waypoint.inside_restricted_area`).

Uses the same ray-casting algorithm as Guardian's `is_point_inside_polygon()`.
Not required for MVP01 validation, but the implementation is shared.

### 4.4 Polyline intersection (for crossroad validation)

Used for: `crossroad.roads_intersect` WARNING — checks that the two roads
actually cross near the crossroad marker.

Algorithm: use Shapely `LineString.intersects()` after projecting both roads
to the calculation CRS. Distance from the crossroad marker to the intersection
point must be ≤ snap_tolerance_m × 2 (1 meter) to avoid false positives.

---

## 5. Floating-Point Storage

### 5.1 Latitude and longitude columns

- SQLite type: `REAL` (64-bit IEEE 754 double, ~15 significant decimal digits)
- SQLAlchemy type: `Double` (maps to `REAL` in SQLite)
- **Never use `Float` (32-bit) for coordinates** — error at lat -20° is ~1.8 cm

**Why `Double` and not `Float`:**

```
Float (32-bit) at lat -20.81234567:
  Stored value: -20.812345504760742
  Error: 0.000000165 degrees = 1.84 cm

Double (64-bit) at lat -20.81234567:
  Stored value: -20.81234567 (exact within 7 dp)
  Error: < 0.001 mm
```

A 1.84 cm error from Float32 is larger than the 1.1 cm resolution of
7 decimal places. Float32 is therefore inadequate as a coordinate type.

### 5.2 Coordinate rounding on export

When generating the Guardian export JSON, all coordinates are rounded to
`STUDIO_COORDINATE_PRECISION` decimal places (default: 7) using Python's
`round()` function. This prevents floating-point noise from propagating
into the export file (e.g. `-20.810000000000002` becomes `-20.81`).

```python
def round_coord(value: float, precision: int = 7) -> float:
    return round(value, precision)
```

### 5.3 Heading degrees

`heading_degrees` (0.0–360.0) is stored as `REAL` in SQLite.
Rounded to 1 decimal place in the export (`round(heading, 1)`).

---

## 6. Geometry Validation Thresholds

| Check | Threshold | Used in |
|---|---|---|
| Road minimum points | 2 | `road.min_points` ERROR |
| Polygon minimum points | 3 | `area.min_points` ERROR |
| Duplicate waypoint position | < 0.5 m (projected) | `waypoint.duplicate_position` WARNING |
| Crossroad proximity to intersection | ≤ 1.0 m (projected) | `crossroad.roads_intersect` WARNING |
| Snap tolerance | 0.5 m (projected, configurable) | SnapEngine |

---

## 7. Performance Requirements

| Operation | Max time | Condition |
|---|---|---|
| STRtree build | < 50 ms | Up to 500 entities |
| Snap query | < 10 ms | Up to 500 entities in STRtree |
| Full validation run | < 500 ms | Up to 500 entities |
| Export generation | < 1 s | Any valid map |

These requirements are enforced by integration tests using `pytest-benchmark`
or simple `time.perf_counter()` assertions.

---

## 8. Relationship to Guardian's Spatial Implementation

GuardianMapStudio and Guardian share the same spatial foundations:

| Item | GuardianMapStudio | Guardian |
|---|---|---|
| Storage CRS | EPSG:4326 | EPSG:4326 |
| `EARTH_RADIUS_M` | `6_371_000` | `6_371_000` (same constant) |
| Haversine formula | `math.asin(math.sqrt(h))` | Same |
| `_to_local()` projection | Same implementation | `geo_utils._to_local()` |
| `Double` for lat/lng columns | Yes | Yes |
| Point-to-segment algorithm | Same | `geo_utils.point_to_segment_distance()` |
| Polygon containment | Ray casting | Same |

**The constants and formulas must remain identical between the two projects.**
If Guardian updates `EARTH_RADIUS_M` or changes its haversine implementation,
GuardianMapStudio must be updated to match. Any divergence would cause the
distances computed by GuardianMapStudio's validation to differ from the
distances computed by Guardian's Localizer for the same map.
