# GuardianMapStudio — Glossary v1

This glossary defines every domain term used across all GuardianMapStudio documents.
Terms are listed alphabetically. When a term has a direct equivalent in the Guardian
platform, the relationship is noted explicitly.

---

## A

**Active Workspace**
The single Workspace in DRAFT state associated with a Project at any given time.
A Project always has exactly one active Workspace. When a Workspace is Published,
a new DRAFT Workspace is automatically created from that Version so editing can continue.

---

## C

**Candidate Entity** *(MVP02+)*
An entity suggested by the AI pipeline, not yet confirmed by a human operator.
Candidate Entities are visible on the map with a distinct visual style (dashed outline)
and must be explicitly Accepted or Rejected before a Workspace can be Published.
Not present in MVP01.

**Coordinate**
A geographic point expressed as `{latitude, longitude}` in EPSG:4326 (WGS84).
Stored as two `Double` fields (7 decimal places, ~1 cm precision).
See also: *GeoPoint*, *EPSG:4326*.

**Crossroad**
An intersection between exactly two Roads at a specific geographic point.
Defined by: `road_a` (name), `road_b` (name), `lat`, `lng`.
In Guardian, crossroads trigger the SLOW AND VERIFY behavior (ADR-015).
In the export JSON, referenced by road name — both names must exist in the `roads` array.

**CrossroadEngine**
The engine responsible for geometric crossroad analysis.

In **MVP01**: validates that manually placed crossroad markers are near
the actual geometric intersection of the two named road polylines (within
1 meter). Does NOT auto-detect intersections — crossroads are placed
manually by the operator.

In **MVP02**: extended to auto-detect all road intersections and suggest
crossroad placement to the operator.

Part of the GeometryEngine subsystem. See also: *GeometryEngine*, *Crossroad*.

**CRS (Coordinate Reference System)**
The mathematical framework used to express geographic positions.
GuardianMapStudio uses two CRSs:
- **Storage CRS**: EPSG:4326 (WGS84) — for all persistent coordinates.
- **Calculation CRS**: SIRGAS 2000 / UTM (projected) — for metric calculations
  (distances, areas, snap tolerance, intersection detection).
See also: *EPSG:4326*, *SIRGAS 2000*.

---

## D

**Draft**
The state of a Workspace that is being actively edited. A Draft can have
validation errors. A Draft cannot be exported to Guardian directly —
it must first be Published to create a Version.
See also: *Workspace*, *Published*.

---

## E

**Entity**
Any named map object that is not a Road or a Crossroad. In GuardianMapStudio,
Entity is the collective term for: Waypoints and Restricted Areas.
In the export JSON, Entities are split into `waypoints` and `restricted_areas` arrays.
Guardian uses Entity data to trigger proximity warnings and speed adjustments.

**EPSG:4326 (WGS84)**
The geographic coordinate system used by all GPS devices and by both
GuardianMapStudio and Guardian for storing coordinates.
Latitude range: -90 to +90. Longitude range: -180 to +180.
Precision stored: 7 decimal places (~1 cm at equatorial scale).

**Export**
The action of converting a Published Version into a JSON file in the
Guardian canonical format. Only a Version (not a Workspace) can be exported.
The export file includes a `meta` block with provenance information and
a `schema_version` field. Guardian imports the file via `guardian-seed-map --from-json`.
See also: *Version*, *Guardian Export Format*, *schema_version*.

**Export History**
The record of every Export action: which Version was exported, when, and to what file path.
Stored in the `export_history` table. Provides a full audit trail.

**extra_data**
A JSON object attached to a Waypoint that stores type-specific attributes.
The valid keys depend on waypoint type:
- `speed_bump`: `{"height_cm": <integer>}` — bump height in centimeters
- `gate`: `{"gate_type": "<GateType>"}` — see *GateType*
- `stop_sign`: `{}` — no extra data (heading stored in `heading_degrees` field)
- `curve`, `landmark`, `crossroad`, `stop_zone`: `{}` — no extra data

---

## G

**GateType**
Enumeration of gate subtypes. Values (match Guardian exactly):
- `"entry"` — vehicles may enter but not exit
- `"exit"` — vehicles may exit but not enter
- `"entry_exit"` — bidirectional gate (most common)
- `"internal"` — internal gate within the condominium

**GeometryEngine**
The subsystem that handles all spatial computations: coordinate projection,
distance calculation, polyline intersection, polygon containment, STRtree indexing.
All proximity queries and snap operations go through the GeometryEngine.
Direct coordinate arithmetic outside this engine is prohibited (ADR-008).

**GeoPoint**
A value object representing a single geographic coordinate: `{latitude: float, longitude: float}`.
Used internally in domain contracts. In the export JSON, serialized as `{"lat": ..., "lng": ...}`.

**Guardian**
The autonomous low-speed vehicle platform that consumes the map produced by
GuardianMapStudio. Guardian reads the map from its own database (`guardian.db`)
which is populated by running `guardian-seed-map --from-json <file>`.
GuardianMapStudio never reads or writes `guardian.db` directly.

**Guardian Export Format**
The canonical JSON structure that GuardianMapStudio produces and Guardian consumes.
Defined in ADR-002 of the Architecture document. Top-level keys: `meta`, `roads`,
`waypoints`, `crossroads`, `restricted_areas`.
The format is stable — any change must be reflected in both projects simultaneously.

---

## H

**heading_degrees**
The compass bearing (0–360°) indicating the direction a stop sign faces.
0° = North, 90° = East, 180° = South, 270° = West.
Used by Guardian to determine the approach direction for SLOW AND VERIFY behavior.
Only applicable to `stop_sign` waypoints. Optional field in the export JSON.

---

## L

**Landmark**
A Waypoint of type `"landmark"`. Used to mark notable but non-safety-critical
points on the map (e.g., building entrances, parking areas).
Guardian does not trigger any safety behavior for landmarks.
`extra_data`: `{}`

---

## P

**Polyline**
An ordered sequence of GeoPoints defining the shape of a Road.
Stored as a JSON array of `{lat, lng}` objects in the database.
Minimum 2 points required. Points are connected in order (index 0 → 1 → 2...).

**Project**
The top-level organizational unit. Represents one condominium.
A Project contains one or more Versions and one active Workspace.
Multiple Projects can coexist in the same `guardianmapstudio.db`.
Fields: `id`, `name`, `description`, `created_at`.

**Publish**
The action of converting the active Workspace (DRAFT) into an immutable Version.
Requires zero validation ERRORs. Warnings are allowed.
After publishing: the Workspace state changes to PUBLISHED, a new DRAFT Workspace
is created from that Version, and an entry is added to the Version history.
See also: *Version*, *Workspace*, *Validation*.

**Published**
The state of a Workspace that has been converted into a Version.
A Published Workspace is read-only. The map data is copied into the
`road_versions` and `entity_versions` tables with a `version_id` reference.
See also: *Publish*, *Version*.

---

## R

**Restricted Area**
A polygonal zone on the condominium map where special rules apply.
Defined by: `name`, `polygon` (array of GeoPoints, minimum 3), `restriction_type`, `speed_limit_kmh` (optional), `active`.
In Guardian, entering a Restricted Area adjusts the effective speed limit.
See also: *RestrictionType*.

**RestrictionType**
Enumeration of restricted area types. Values (match Guardian exactly):
- `"speed_limit"` — area has a specific speed limit lower than the road limit
- `"no_entry"` — area is off-limits to the vehicle
- `"pedestrian_only"` — area is reserved for pedestrians

**Road**
A named polyline representing a drivable path within the condominium.
Fields: `name` (unique within a Project), `coordinates` (Polyline), `speed_limit_kmh`,
`direction` (RoadDirection), `width_meters`.
Road names are used as foreign key references in Waypoints and Crossroads in the export JSON.
See also: *RoadDirection*, *Polyline*.

**RoadDirection**
Enumeration of road direction constraints. Values (match Guardian exactly):
- `"two_way"` — vehicles may travel in both directions (default)
- `"one_way"` — vehicles may travel in one direction only (direction implied by coordinate order)

---

## S

**schema_version**
A string field in the `meta` block of the export JSON that identifies the format version.
Current value: `"1.0"`. Guardian's ReplayEngine checks this field when loading sessions.
If the schema changes in a future version, this field enables backward compatibility detection.

**seed_from_json**
The Guardian CLI command entry point that reads a Guardian Export Format JSON file
and populates `guardian.db` with the map data. Invoked as:
`uv run guardian-seed-map --from-json <file>`
GuardianMapStudio is responsible for producing a file that this function accepts without error.

**SIRGAS 2000**
The official geodetic reference system for South America, used as the projected CRS
for metric calculations in GuardianMapStudio. Combined with UTM zone projection
(zone 22S or 23S depending on the condominium location) to convert
EPSG:4326 coordinates into metric coordinates for snap and distance operations.

**Snap**
The operation of automatically aligning a newly placed point to an existing
nearby point or line when it is within the snap tolerance (0.5 meters projected).
Prevents near-duplicate coordinates that would cause topology errors.
Example: placing the end of a Road segment 0.3m from the start of another Road
automatically joins them to the same coordinate.
See also: *SnapEngine*, *Snap Tolerance*.

**Snap Tolerance**
The maximum distance (in projected meters) within which two points are treated
as coincident during snap operations. Value: **0.5 meters**.
This tolerance applies to: Road endpoint connections, Waypoint placement on Roads,
Crossroad placement at intersections.

**SnapEngine**
The engine responsible for executing snap operations. Given a new point and the
existing geometry, SnapEngine finds the nearest candidate within snap tolerance
and returns the snapped coordinate. Uses STRtree for candidate lookup.

**speed_bump** *(Waypoint type)*
A Waypoint marking a physical speed bump on the road.
Guardian reduces speed and applies SLOW AND VERIFY behavior when approaching.
`extra_data`: `{"height_cm": <integer>}` — height of the bump in centimeters.

**stop_sign** *(Waypoint type)*
A Waypoint marking a PARE (stop) sign.
Guardian triggers SLOW AND VERIFY behavior when approaching and requires a full stop.
Optional field: `heading_degrees` (0–360°).
`extra_data`: `{}`

**stop_zone** *(Waypoint type)*
A Waypoint marking a safe position where the Guardian vehicle may halt.
Guardian only stops at designated stop zones (ADR-016 in Guardian architecture).
`extra_data`: `{}`

**STRtree**
Sort-Tile-Recursive tree. A spatial index provided by Shapely that enables
O(log n) nearest-neighbor and bounding-box intersection queries.
Required for all spatial queries in GuardianMapStudio (ADR-008).
Used by: GeometryEngine, SnapEngine, CrossroadEngine, ValidationEngine.

---

## V

**Validation**
The process of checking the map data for geometric and semantic correctness.
Runs automatically on every save. Results are classified as ERROR or WARNING:
- **ERROR**: blocks Publish. Example: Road with fewer than 2 points, Waypoint outside all Roads.
- **WARNING**: does not block Publish. Example: Road with no Waypoints, isolated Landmark.
See also: *ValidationEngine*, *ADR-007 in Architecture*.

**ValidationEngine**
The engine that applies all validation rules to the current Workspace and returns
a list of `ValidationResult` objects, each with: `severity` (ERROR|WARNING),
`rule_id`, `message`, `affected_entity_id`, `affected_entity_type`.
Results are stored in the `validation_results` table and displayed on the map.

**Version**
An immutable snapshot of a Project's map at a specific point in time.
Created by the Publish action. Can be exported to Guardian.
Fields: `id`, `project_id`, `version_number` (auto-incremented), `name`, `published_at`.
Map data is preserved in `road_versions` and `entity_versions` tables.
A Version can never be edited — to make changes, a new Workspace is created from it.
See also: *Publish*, *Workspace*, *Export*.

---

## W

**Waypoint**
A named point of interest on the condominium map. Guardian uses Waypoints
to trigger proximity warnings, speed adjustments, and safety behaviors.
Fields: `name`, `type` (WaypointType), `lat`, `lng`, `road` (Road name or null),
`heading_degrees` (optional), `extra_data` (type-specific JSON object).
See also: *WaypointType*, *extra_data*.

**WaypointType**
Enumeration of waypoint types. Values (match Guardian's `WaypointType` enum exactly):
- `"stop_sign"` — PARE sign; triggers SLOW AND VERIFY and full stop
- `"speed_bump"` — physical speed bump; triggers speed reduction
- `"gate"` — condominium gate (entry, exit, or both)
- `"landmark"` — informational marker; no Guardian safety behavior
- `"curve"` — road curve requiring reduced speed
- `"crossroad"` — intersection marker (distinct from the Crossroad entity)
- `"stop_zone"` — designated safe stopping position (ADR-016)

**width_meters**
The width of a Road in meters. Used by Guardian for path planning and obstacle
clearance calculations. Stored as a float. Typical values: 4.0–8.0 meters.

**Workspace**
A mutable editing environment associated with a Project.
A Workspace is in one of two states:
- **DRAFT**: actively being edited. May have validation errors.
- **PUBLISHED**: converted to an immutable Version. Read-only.
Only one DRAFT Workspace exists per Project at any time.
The Workspace is the unit of editing; the Version is the unit of publishing.
See also: *Project*, *Version*, *Draft*, *Published*.

---

## Relationship to Guardian Terms

The following table maps GuardianMapStudio terms to their Guardian equivalents:

| GuardianMapStudio | Guardian | Notes |
|---|---|---|
| `Waypoint` (in export) | `MapWaypoint` | Same data, different layer |
| `Road` (in export) | `MapRoad` | Same data, different layer |
| `Crossroad` (in export) | `MapCrossroad` | Same data, different layer |
| `Restricted Area` (in export) | `MapRestrictedArea` | Same data, different layer |
| `WaypointType` values | `WaypointType` enum | Must be identical strings |
| `RoadDirection` values | `RoadDirection` enum | Must be identical strings |
| `RestrictionType` values | `RestrictionType` enum | Must be identical strings |
| `GateType` values | `GateType` enum | Must be identical strings |
| `schema_version` in `meta` | Checked by `ReplayEngine` | Currently `"1.0"` |

> **Critical**: Any string value in these enums must match exactly between
> GuardianMapStudio and Guardian. A mismatch (e.g. `"Speed_Bump"` vs `"speed_bump"`)
> causes `ValueError` in Guardian's `seed_from_json()` and the map will not load.
