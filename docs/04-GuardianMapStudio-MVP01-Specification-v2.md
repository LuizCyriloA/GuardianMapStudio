# GuardianMapStudio — MVP01 Specification v2

## 1. Purpose

MVP01 delivers a functional web-based map editor that allows a human operator
to create, edit, validate, version, and export a condominium map for use with
the Guardian autonomous vehicle platform.

**The objective is NOT to replace Guardian.**
The objective is to give the operator a proper authoring environment instead
of editing a JSON file by hand.

After MVP01, the operator can:
- Create a condominium map visually on an interactive Leaflet map
- Place roads, stop signs, speed bumps, gates, curves, and restricted areas
- Validate the map before publishing
- Export a Guardian-compatible JSON file with one click
- Keep a history of every published version

---

## 2. MVP01 Scope

### Map Authoring
- Create and manage Projects (one per condominium)
- Edit maps in a Workspace (mutable draft)
- Roads: draw polylines, set speed limit, direction, width
- Waypoints: place stop signs, speed bumps, gates, curves, landmarks, stop zones
- Crossroads: mark intersections between roads
- Restricted Areas: draw polygonal zones with restriction type

### Versioning
- Publish Workspace → creates immutable Version
- Full history of published Versions per Project
- New DRAFT Workspace automatically created after each Publish

### Validation
- Automatic validation on every save
- Inline error/warning display on the Leaflet map
- Publish blocked when any ERROR exists
- Warnings visible but non-blocking

### Export
- Export any published Version to Guardian JSON format
- Download file directly from browser
- Export history with file path and size
- `meta` block with provenance in every export

### Infrastructure
- FastAPI backend (Python 3.12)
- SQLite database (`guardianmapstudio.db`, 11 tables)
- Vue 3 + Leaflet frontend (served from FastAPI)
- Single-page application, no separate frontend server

---

## 3. Explicitly Out of Scope (MVP01)

| Feature | Target |
|---|---|
| AI-assisted entity detection from images/video | MVP02 |
| Import from OpenStreetMap or GeoJSON | MVP02 |
| Undo/redo (beyond reverting to last published version) | MVP02 |
| Live sync with Guardian while it is running | Never — by design |
| Multi-user editing or conflict resolution | MVP03 |
| Authentication or user accounts | MVP03 |
| Mobile or touch interface | MVP03 |
| Map simulation or path planning | MVP04 |
| Road snapping (snap endpoint to endpoint) | MVP02 |
| Automatic crossroad detection from polyline intersection | MVP02 |

---

## 4. User Workflows (MVP01)

### WF-01 — Create first map for a new condominium

```
1. Operator opens http://localhost:8000
2. Clicks "Novo Projeto"
3. Enters project name (e.g. "Condomínio Parque das Flores")
4. GuardianMapStudio creates Project + empty DRAFT Workspace
5. Map Editor opens with empty Leaflet map
6. Operator draws roads by clicking on the map
7. Operator places waypoints, crossroads, restricted areas
8. Operator reviews validation panel — fixes all ERRORs
9. Operator clicks "Publicar" → enters version name → confirms
10. GuardianMapStudio creates Version v1
11. Operator clicks "Exportar para Guardian"
12. JSON file is downloaded
13. Operator runs: uv run guardian-seed-map --from-json <file>
14. Guardian starts with the new map
```

### WF-02 — Update existing map

```
1. Operator opens project
2. Active DRAFT Workspace opens automatically
3. Operator makes changes (adds lombada, moves portaria, etc.)
4. Validation runs automatically — errors shown inline on map
5. Operator fixes errors
6. Operator publishes → Version v2 created
7. Operator exports and applies to Guardian as in WF-01
```

### WF-03 — Review previous version

```
1. Operator opens project → navigates to "Versões"
2. Selects a past version from the list
3. Reads-only map view shows the state at that point in time
4. Can export any previous version for Guardian if needed
```

### WF-04 — Fix validation error mid-edit

```
1. Operator draws a road with only 1 point
2. Red error marker appears on the map immediately
3. Validation panel shows: "Road 'Rua X' has only 1 point. Minimum is 2."
4. "Publicar" button is disabled
5. Operator extends the road to 2+ points
6. Error clears automatically
7. "Publicar" becomes enabled
```

---

## 5. Functional Requirements

### FR-01 — Project management
- The system must support creating multiple Projects
- Each Project has a name (required) and description (optional)
- Project name need not be globally unique but should be descriptive

### FR-02 — Workspace lifecycle
- Every Project always has exactly one DRAFT Workspace
- A DRAFT Workspace may be saved in any state, including invalid
- Publishing requires zero validation ERRORs
- After publishing, a new DRAFT Workspace is created automatically
  from the published Version, allowing immediate continuation of editing
- A published Workspace is permanently read-only

### FR-03 — Road editing
- Operator can draw a road by placing a polyline on the map
- Road name must be unique within the Workspace
- Minimum 2 points required
- Speed limit, direction (two_way/one_way), and width are configurable
- Deleting a road that has dependent waypoints or crossroads is rejected
  with a message listing the dependents

### FR-04 — Waypoint editing
- Operator can place waypoints by clicking the map
- Available types: stop_sign, speed_bump, gate, curve, landmark,
  crossroad (marker), stop_zone
- Speed bump requires height_cm > 0
- Gate requires gate_type (entry/exit/entry_exit/internal)
- Stop sign accepts optional heading_degrees (0–360°)
- Waypoint can be associated with a road by name (optional for gates)
- Snap is applied automatically within 0.5m tolerance

### FR-05 — Crossroad editing
- Operator can place a crossroad marker at an intersection
- Both road names must exist in the Workspace
- The two road names must be different

### FR-06 — Restricted area editing
- Operator can draw polygonal zones
- Available restriction types: speed_limit, no_entry, pedestrian_only
- speed_limit type requires speed_limit_kmh > 0

### FR-07 — Validation
- Validation runs after every create, update, or delete operation
- Results are cached in `validation_results` table
- Results are displayed inline on the map (red pin = ERROR, yellow pin = WARNING)
- Validation panel lists all results with entity type and message
- Clicking a result pans the map to the affected entity

### FR-08 — Publish
- Publish converts the DRAFT Workspace to an immutable Version
- Operator provides a version name at publish time
- Version number is auto-incremented (1, 2, 3...)
- Version stores a snapshot of all roads and entities
- Publish is atomic: either all data is versioned or nothing is

### FR-09 — Export
- Any published Version can be exported to Guardian JSON format
- Export produces a file with `meta` block + `roads` + `waypoints`
  + `crossroads` + `restricted_areas`
- File is named: `<project_name>_v<version_number>.json`
- File is written to `STUDIO_EXPORT_DIR` and downloadable from browser
- Every export is recorded in `export_history`

### FR-10 — Version history
- Operator can view all published versions for a project
- Each version shows: number, name, date, entity counts
- Read-only map preview available for any version

---

## 6. Non-Functional Requirements

### NFR-01 — Performance
- API responses (read): ≤ 200ms for maps with up to 500 entities
- Validation run: ≤ 500ms for maps with up to 500 entities
- Export generation: ≤ 1 second for any valid map
- Frontend initial load: ≤ 3 seconds on local network

### NFR-02 — Reliability
- No data loss: every save is immediately persisted to SQLite
- Publish is atomic: partial versions must never be created
- Export file must be identical to what `seed_from_json()` accepts —
  tested automatically in the test suite

### NFR-03 — Correctness
- All enum values in the export JSON must match Guardian exactly
- `road` field in waypoint export must match a road name in `roads` array
  or be `null` — never reference a non-existent road
- Coordinate precision: 7 decimal places in all exported coordinates

### NFR-04 — Usability
- The tool must run entirely in a standard desktop browser
  (Chrome, Firefox, Edge — no plugins required)
- No installation required on the operator's device beyond the browser
- The Leaflet map must load within 2 seconds on the local network
- All error messages must identify the specific entity affected

### NFR-05 — Maintainability
- Backend test coverage ≥ 80%
- `ruff check` passes with zero warnings
- `mypy --strict` passes on all source files
- All database migrations use Alembic (MVP02+; MVP01 uses `create_all()`)

---

## 7. Business Rules

| ID | Rule |
|---|---|
| BR-01 | A Project always has exactly one DRAFT Workspace |
| BR-02 | Publish requires zero validation ERRORs |
| BR-03 | A published Workspace is permanently read-only |
| BR-04 | Version numbers are sequential per project and never reused |
| BR-05 | Road names are unique within a Workspace (case-sensitive) |
| BR-06 | Deleting a road with dependents (waypoints or crossroads) is rejected |
| BR-07 | Crossroad road_a_name and road_b_name must be different |
| BR-08 | speed_limit Restricted Area must have speed_limit_kmh > 0 |
| BR-09 | speed_bump Waypoint must have extra_data.height_cm > 0 |
| BR-10 | gate Waypoint must have extra_data.gate_type set to a valid GateType |
| BR-11 | Export is only available for published Versions, not DRAFT Workspaces |
| BR-12 | A new DRAFT Workspace is created automatically after every Publish |
| BR-13 | Validation results are replaced entirely on each validation run |
| BR-14 | Snap tolerance is 0.5m (projected). Points within this distance are snapped |
| BR-15 | GuardianMapStudio never reads or writes guardian.db |

---

## 8. Validation Rules

All rules are evaluated by `ValidationEngine`. ERRORs block Publish.

### Roads

| Rule ID | Severity | Condition |
|---|---|---|
| `road.min_points` | ERROR | Road has fewer than 2 GeoPoints |
| `road.name_unique` | ERROR | Road name already exists in this Workspace |
| `road.speed_limit_positive` | ERROR | speed_limit_kmh ≤ 0 |
| `road.width_positive` | ERROR | width_meters ≤ 0 |
| `road.no_waypoints` | WARNING | Road has zero associated waypoints |

### Waypoints

| Rule ID | Severity | Condition |
|---|---|---|
| `waypoint.name_not_empty` | ERROR | name is blank or whitespace-only |
| `waypoint.road_exists` | ERROR | road_name is set but no Road with that name exists |
| `waypoint.heading_range` | ERROR | heading_degrees is set but not in [0, 360] |
| `waypoint.speed_bump_height` | ERROR | type is speed_bump and extra_data.height_cm ≤ 0 or missing |
| `waypoint.gate_type_valid` | ERROR | type is gate and extra_data.gate_type is missing or invalid |
| `waypoint.duplicate_position` | WARNING | Another waypoint exists within 0.5m |

### Crossroads

| Rule ID | Severity | Condition |
|---|---|---|
| `crossroad.road_a_exists` | ERROR | road_a_name does not match any Road in Workspace |
| `crossroad.road_b_exists` | ERROR | road_b_name does not match any Road in Workspace |
| `crossroad.roads_distinct` | ERROR | road_a_name == road_b_name |
| `crossroad.roads_intersect` | WARNING | The two roads do not geometrically intersect near the crossroad position |

### Restricted Areas

| Rule ID | Severity | Condition |
|---|---|---|
| `area.min_points` | ERROR | Polygon has fewer than 3 GeoPoints |
| `area.name_not_empty` | ERROR | name is blank or whitespace-only |
| `area.speed_limit_required` | ERROR | restriction_type is speed_limit but speed_limit_kmh is null |
| `area.speed_limit_positive` | ERROR | speed_limit_kmh is set but ≤ 0 |

### Workspace-level

| Rule ID | Severity | Condition |
|---|---|---|
| `workspace.min_roads` | ERROR | Workspace has zero Roads |

---

## 9. Acceptance Criteria

### Project & Workspace
- [ ] Create project → empty DRAFT Workspace created automatically
- [ ] Project appears in project list
- [ ] Active DRAFT Workspace loads when project is opened
- [ ] Workspace state is `draft` until published
- [ ] After publish, new `draft` Workspace created from new Version

### Map Editing
- [ ] Draw road on map → persisted immediately
- [ ] Road with < 2 points shows ERROR inline on map
- [ ] Two roads with same name → second shows ERROR
- [ ] Place stop_sign → persisted with correct type
- [ ] Place speed_bump without height_cm → ERROR shown
- [ ] Place gate without gate_type → ERROR shown
- [ ] Place crossroad with non-existent road → ERROR shown
- [ ] Draw restricted area with < 3 points → ERROR shown
- [ ] Delete road with dependent waypoints → rejected with message
- [ ] Snap moves point within 0.5m tolerance to nearest existing point

### Validation
- [ ] Validation runs after every create/update/delete
- [ ] ERROR count shown in validation panel
- [ ] WARNING count shown in validation panel
- [ ] Affected entities highlighted on map (red = ERROR, yellow = WARNING)
- [ ] Clicking validation result pans map to affected entity

### Publish
- [ ] Publish button disabled when error_count > 0
- [ ] Publish with errors → 422 response with error list
- [ ] Publish with zero errors → Version created
- [ ] Version number increments correctly (1, 2, 3…)
- [ ] New DRAFT Workspace created after publish
- [ ] Published Version appears in version history

### Export
- [ ] Export available only for published Versions
- [ ] Export button on DRAFT Workspace → disabled or hidden
- [ ] Export produces valid JSON file
- [ ] Export file passes `guardian-seed-map --from-json` without error
- [ ] `meta.schema_version` is `"1.0"` in export
- [ ] `meta.version_number` matches the Version
- [ ] All `waypoints[].type` values match Guardian's WaypointType exactly
- [ ] `waypoints[].road` references a road that exists in the same export file
- [ ] Export recorded in export history
- [ ] Download from browser works

### Non-Functional
- [ ] API responses ≤ 200ms for maps with ≤ 500 entities
- [ ] `ruff check` passes with zero warnings
- [ ] `mypy --strict` passes
- [ ] `pytest` passes with ≥ 80% coverage
- [ ] No runtime exceptions during a complete WF-01 walkthrough

---

## 10. Definition of Done

MVP01 is complete when:

1. All acceptance criteria above are checked
2. A complete WF-01 walkthrough (create → edit → validate → publish → export)
   completes without errors
3. The exported JSON file is successfully imported by Guardian via
   `guardian-seed-map --from-json` on the same machine
4. Guardian starts and the Localization HUD shows the correct road name
   for at least one road from the exported map
5. Test suite passes with ≥ 80% coverage
6. No `mypy` or `ruff` errors
