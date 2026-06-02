# GuardianMapStudio — Architecture v2

## 1. Purpose

GuardianMapStudio is the map authoring tool for the Guardian autonomous vehicle platform.
It allows a human operator to create, edit, validate and version the condominium map —
roads, waypoints (stop signs, speed bumps, gates, landmarks, curves), crossroads and
restricted areas — and export it as a JSON file that Guardian imports at startup.

GuardianMapStudio and Guardian are **separate processes** that share no live connection.
The integration contract is a single JSON file on disk.

---

## 2. Context and Constraints

| Item | Decision | Rationale |
|---|---|---|
| Deployment | Same machine as Guardian | Reduces infrastructure; condominium environment |
| Database | SQLite (`guardianmapstudio.db`) | Same machine as Guardian; no concurrent writes from multiple clients |
| Guardian DB | `guardian.db` (separate file) | GuardianMapStudio never reads or writes guardian.db directly |
| Interface | Web application (browser on local network) | No installation required on operator device |
| Authentication | None in MVP01 | Closed local network; single operator |
| AI assistance | MVP02+ | MVP01 is human-only editing |
| Live editing | Not supported | Guardian stops → map is edited → Guardian restarts with new map |
| Integration | JSON file export → Guardian `guardian-seed-map --from-json` | Decoupled, auditable, reproducible |

---

## 3. Architecture Decision Records

### ADR-001 — Separate database from Guardian

**Decision**: GuardianMapStudio uses its own SQLite file (`guardianmapstudio.db`).
It never reads or writes `guardian.db`.

**Rationale**: Guardian's database stores runtime data (sessions, events, GPS positions).
GuardianMapStudio's database stores authoring data (projects, versions, workspaces).
Mixing them would create a brittle coupling where a GuardianMapStudio migration could
corrupt Guardian's runtime tables or vice versa.

**Consequence**: Integration happens exclusively through the JSON export file.
The Guardian operator runs `guardian-seed-map --from-json <file>` to apply the map.

---

### ADR-002 — JSON export format is Guardian's canonical import format

**Decision**: The export file produced by GuardianMapStudio is exactly the format
expected by Guardian's `seed_from_json()` function. No conversion layer exists.

**The canonical format is:**

```json
{
  "roads": [
    {
      "name": "Rua Principal",
      "coordinates": [{"lat": -20.8100, "lng": -49.3756}, {"lat": -20.8110, "lng": -49.3756}],
      "speed_limit_kmh": 20,
      "direction": "two_way",
      "width_meters": 6.0
    }
  ],
  "waypoints": [
    {"name": "Lombada 1",          "type": "speed_bump", "lat": -20.8103, "lng": -49.3756, "road": "Rua Principal",  "extra_data": {"height_cm": 10}},
    {"name": "PARE - Cruzamento",  "type": "stop_sign",  "lat": -20.8105, "lng": -49.3756, "road": "Rua Principal",  "heading_degrees": 90.0, "extra_data": {}},
    {"name": "Portaria Principal", "type": "gate",       "lat": -20.8100, "lng": -49.3756, "road": null,             "extra_data": {"gate_type": "entry_exit"}},
    {"name": "Curva Perigosa",     "type": "curve",      "lat": -20.8107, "lng": -49.3754, "road": "Rua Principal",  "extra_data": {}}
  ],
  "crossroads": [
    {"road_a": "Rua Principal", "road_b": "Rua Secundária", "lat": -20.8105, "lng": -49.3756}
  ],
  "restricted_areas": [
    {
      "name": "Playground",
      "polygon": [{"lat": -20.8106, "lng": -49.3758}, {"lat": -20.8106, "lng": -49.3754}, {"lat": -20.8108, "lng": -49.3754}, {"lat": -20.8108, "lng": -49.3758}],
      "restriction_type": "speed_limit",
      "speed_limit_kmh": 10,
      "active": true
    }
  ]
}
```

**Field rules (matching Guardian's `seed_from_json()`):**

| Field | Type | Notes |
|---|---|---|
| `roads[].name` | string | Used as foreign key reference by waypoints and crossroads |
| `roads[].coordinates` | array of `{lat, lng}` | Minimum 2 points |
| `roads[].speed_limit_kmh` | integer | km/h |
| `roads[].direction` | string | `"two_way"` or `"one_way"` |
| `roads[].width_meters` | float | Meters |
| `waypoints[].type` | string | `"stop_sign"`, `"speed_bump"`, `"gate"`, `"curve"`, `"landmark"`, `"crossroad"`, `"stop_zone"` |
| `waypoints[].road` | string or null | Must match a road name exactly, or null |
| `waypoints[].heading_degrees` | float, optional | Only for `stop_sign` |
| `waypoints[].extra_data.height_cm` | integer | Only for `speed_bump` |
| `waypoints[].extra_data.gate_type` | string | Only for `gate`: `"entry_exit"`, `"entry"`, `"exit"`, `"internal"` |
| `crossroads[].road_a` | string | Must match a road name exactly |
| `crossroads[].road_b` | string | Must match a road name exactly |
| `restricted_areas[].restriction_type` | string | `"speed_limit"`, `"no_entry"`, `"pedestrian_only"` |
| `restricted_areas[].polygon` | array of `{lat, lng}` | Minimum 3 points, must be closed (first == last or implicitly closed) |

**Rationale**: A single format eliminates the risk of drift between what GuardianMapStudio
exports and what Guardian imports. Any change to Guardian's import format must be
reflected in this document first.

---

### ADR-003 — Workspace is the unit of editing; Version is the unit of publishing

**Decision**: An operator works inside a Workspace. A Workspace is a mutable draft.
When the operator is satisfied and all validations pass, the Workspace is Published,
creating an immutable Version. Only a Version can be exported to Guardian.

**States:**

```
Workspace (DRAFT) → [validate + publish] → Version (PUBLISHED)
                                                ↓
                                         [export] → condominium_map.json
                                                         ↓
                                         [Guardian] → guardian-seed-map --from-json
```

**Rationale**: Prevents exporting a map with validation errors to Guardian.
Immutable versions provide a full audit trail — the operator can always see
which map version was active when a Guardian session was recorded.

---

### ADR-004 — Coordinates stored as EPSG:4326 (WGS84), calculations in projected CRS

**Decision**: All coordinates are stored as `latitude` (Double) and `longitude` (Double)
in EPSG:4326. Geometric calculations (distance, intersection, snap, area) are performed
in a projected CRS appropriate for the region (SIRGAS 2000 / UTM).

**Rationale**: EPSG:4326 is the native format of all GPS devices and the Guardian platform.
Storing in projected CRS would require a fixed region assumption. Projecting at query time
for calculations gives metric accuracy without storage coupling.

**Snap tolerance**: 0.5 meters (projected). Two points closer than 0.5m are treated as
the same point during snap operations.

**Coordinate precision**: 7 decimal places in EPSG:4326 (~1 cm precision at equatorial scale).

---

### ADR-005 — FastAPI serves both the REST API and the Vue 3 frontend

**Decision**: A single FastAPI process serves:
1. The REST API at `/api/v1/...`
2. The Vue 3 single-page application at `/` (static files from `frontend/dist/`)

**Rationale**: Single process, single port (default: 8000), no CORS configuration needed,
simpler deployment on the Guardian machine. The operator opens `http://localhost:8000`
in any browser on the local network.

**Port**: 8000 (configurable via `STUDIO_PORT` environment variable).
Guardian's Map Dashboard runs on port 5556. No conflict.

---

### ADR-006 — No authentication in MVP01

**Decision**: MVP01 has no login, no user accounts, no API keys.

**Rationale**: Single operator on a closed local network. Adding authentication in MVP01
would add complexity without security benefit in the target environment.

**Future**: MVP03+ may add basic authentication if the tool is accessed over a less
trusted network.

---

### ADR-007 — Validation is blocking for Publish, advisory for editing

**Decision**: Validation errors have two severity levels:

| Severity | Blocks Publish? | Shown during editing? |
|---|---|---|
| ERROR | Yes | Yes (inline on map) |
| WARNING | No | Yes (inline on map) |

The operator can save any workspace state, including invalid ones.
Publishing requires zero ERRORs. Warnings may exist in a published version.

**Rationale**: Blocking save would frustrate operators mid-edit. Blocking publish
protects Guardian from receiving a geometrically invalid map.

---

### ADR-008 — STRtree is mandatory for all spatial queries

**Decision**: All proximity queries (nearest waypoint, road containment, snap detection,
polygon intersection) use Shapely's STRtree. Linear scans over coordinate lists are
not permitted in production code.

**Rationale**: A condominium map may have 50–500 entities. STRtree provides O(log n)
query time vs O(n) for linear scan. More importantly, it makes the performance
characteristic explicit and consistent as the map grows.

---

### ADR-009 — Export file is human-readable and version-controlled

**Decision**: The exported JSON file:
1. Uses 2-space indentation (`json.dumps(..., indent=2)`)
2. Includes a `meta` block with export provenance
3. Is designed to be committed to a git repository alongside the Guardian project

**The `meta` block:**
```json
{
  "meta": {
    "exported_by": "GuardianMapStudio",
    "version_id": 3,
    "version_name": "v3 - Adicionado playground",
    "project_name": "Condomínio Exemplo",
    "exported_at": "2026-06-01T14:35:22+00:00",
    "schema_version": "1.0"
  },
  "roads": [...],
  "waypoints": [...],
  "crossroads": [...],
  "restricted_areas": [...]
}
```

**Rationale**: Guardian's `seed_from_json()` ignores unknown keys, so the `meta` block
does not break compatibility. The provenance data allows the Guardian operator to know
exactly which map version is currently loaded.

---

### ADR-010 — Project contains one map; one Project per condominium

**Decision**: A Project represents one condominium. It has exactly one active map
(its latest published Version). Multiple Projects can coexist in the same
`guardianmapstudio.db` (one DB file serves multiple condominiums if needed).

**Rationale**: Keeps the data model simple. A condominium has one layout.
If a section is redesigned, that is a new Version of the same Project,
not a new Project.

---

## 4. System Components

```
┌─────────────────────────────────────────────────────┐
│                  Guardian Machine                    │
│                                                      │
│  ┌─────────────────────────────────────────────┐    │
│  │         GuardianMapStudio (port 8000)        │    │
│  │                                              │    │
│  │  FastAPI ──► REST API (/api/v1/...)          │    │
│  │         ──► Static files (Vue 3 SPA)         │    │
│  │                                              │    │
│  │  SQLite: guardianmapstudio.db                │    │
│  │    └─ projects, versions, workspaces,        │    │
│  │       roads, waypoints, crossroads,          │    │
│  │       restricted_areas, export_history       │    │
│  └──────────────────┬──────────────────────────┘    │
│                     │ export JSON                    │
│                     ▼                               │
│           condominium_map.json                       │
│                     │                               │
│                     │ guardian-seed-map --from-json  │
│                     ▼                               │
│  ┌──────────────────────────────────────────────┐   │
│  │              Guardian (port 5555/5556)        │   │
│  │              SQLite: guardian.db              │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

---

## 5. Technology Stack

| Layer | Technology | Version | Notes |
|---|---|---|---|
| Backend | Python | 3.12 | Same as Guardian |
| API framework | FastAPI | 0.115.x | Async, OpenAPI auto-docs |
| ORM | SQLAlchemy | 2.0.x | Same as Guardian |
| Data validation | Pydantic v2 | 2.x | Request/response validation |
| Geometry | Shapely | 2.x | STRtree, projections |
| CRS projection | pyproj | 3.x | SIRGAS 2000 / UTM |
| Database | SQLite | (stdlib) | Same as Guardian |
| Frontend | Vue 3 | 3.4.x | Options API, CDN or bundled |
| Map rendering | Leaflet.js | 1.9.4 | Same as Guardian |
| State management | Pinia | 2.x | Vue 3 store |
| HTTP client | axios | 1.x | Frontend API calls |
| Linting | Ruff | 0.8.x | Same as Guardian |
| Type checking | mypy | 1.13.x | Same as Guardian |
| Testing | pytest | 8.x | Same as Guardian |
| Package manager | uv | latest | Same as Guardian |

---

## 6. Project Structure

```
guardianmapstudio/
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── docs/
│   └── (all architecture and spec documents)
├── src/
│   └── guardianmapstudio/
│       ├── __init__.py
│       ├── main.py                    ← FastAPI app + static file serving
│       ├── config/
│       │   └── settings.py            ← GuardianMapStudioSettings (pydantic-settings)
│       ├── domain/
│       │   ├── contracts.py           ← frozen dataclasses: Project, Version, Workspace, Road, Waypoint, Crossroad, RestrictedArea
│       │   └── events.py              ← domain events: WorkspacePublished, ExportCreated, ValidationFailed
│       ├── database/
│       │   ├── models.py              ← SQLAlchemy models (11 tables)
│       │   ├── connection.py          ← get_engine, get_session_factory, create_tables
│       │   └── repository.py         ← ProjectRepo, VersionRepo, WorkspaceRepo, MapRepo
│       ├── geometry/
│       │   ├── engine.py              ← GeometryEngine (Shapely + STRtree)
│       │   ├── snap.py                ← SnapEngine
│       │   ├── crossroad.py           ← CrossroadEngine
│       │   └── validation.py          ← ValidationEngine
│       ├── export/
│       │   └── guardian_exporter.py  ← GuardianExporter → produces canonical JSON
│       └── api/
│           ├── routers/
│           │   ├── projects.py
│           │   ├── workspaces.py
│           │   ├── roads.py
│           │   ├── waypoints.py
│           │   ├── crossroads.py
│           │   ├── restricted_areas.py
│           │   ├── validation.py
│           │   └── export.py
│           └── deps.py                ← FastAPI dependency injection
├── frontend/
│   ├── index.html
│   ├── src/
│   │   ├── main.ts
│   │   ├── App.vue
│   │   ├── stores/
│   │   │   ├── project.ts
│   │   │   ├── workspace.ts
│   │   │   └── map.ts
│   │   ├── components/
│   │   │   ├── MapEditor.vue
│   │   │   ├── EntityPanel.vue
│   │   │   ├── ValidationPanel.vue
│   │   │   └── ExportPanel.vue
│   │   └── api/
│   │       └── client.ts
│   └── package.json
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_geometry_engine.py
│   │   ├── test_snap_engine.py
│   │   ├── test_validation_engine.py
│   │   ├── test_guardian_exporter.py
│   │   └── test_repository.py
│   └── integration/
│       ├── test_api_projects.py
│       ├── test_api_workspaces.py
│       └── test_api_export.py
└── exports/                           ← default output directory for JSON exports
```

---

## 7. Database Tables (11)

### Authoring Tables (5)

| Table | Purpose |
|---|---|
| `projects` | One row per condominium. Contains name and metadata. |
| `versions` | Immutable published snapshots of a project map. |
| `workspaces` | Mutable editing drafts. One active workspace per project at a time. |
| `export_history` | Record of every JSON file exported, with version reference. |
| `validation_results` | Cached validation errors and warnings for a workspace. |

### Map Tables (6)

| Table | Purpose |
|---|---|
| `roads` | Road polylines. Scoped to a workspace or version. |
| `waypoints` | All POIs (stop signs, speed bumps, gates, landmarks, curves, stop zones). |
| `crossroads` | Intersections between two roads. |
| `restricted_areas` | Polygonal restricted zones. |
| `road_versions` | Immutable copy of roads when a version is published. |
| `entity_versions` | Immutable copy of all entities when a version is published. |

> **Note**: `road_versions` and `entity_versions` exist to make versions truly immutable.
> When a version is published, all map elements are copied into these tables with a
> `version_id` foreign key. The workspace tables remain mutable for the next edit cycle.

---

## 8. Integration with Guardian — Step by Step

The complete workflow for updating Guardian's map:

```
1. Operator opens GuardianMapStudio in browser (http://localhost:8000)
2. Operator selects project → opens workspace (DRAFT)
3. Operator edits map: adds/moves/deletes roads, waypoints, crossroads, areas
4. GuardianMapStudio validates automatically on each save
5. Operator reviews validation errors (red) and warnings (yellow) on map
6. Operator fixes all errors
7. Operator clicks "Publish" → Workspace becomes Version (PUBLISHED)
8. Operator clicks "Export for Guardian" → downloads / saves JSON file
9. Operator stops Guardian (Ctrl+C or systemctl stop guardian)
10. Operator runs: uv run guardian-seed-map --from-json <exported_file>
    (or: delete guardian.db and run guardian — it seeds automatically)
11. Operator starts Guardian
12. Guardian loads the new map from guardian.db
```

---

## 9. What GuardianMapStudio Does NOT Do (MVP01)

These are explicitly out of scope for MVP01 to keep the implementation focused:

- No AI-assisted entity detection (MVP02)
- No import from OSM or other GIS formats (MVP02)
- No live sync with Guardian while it is running
- No multi-user editing or conflict resolution
- No authentication or user accounts
- No map simulation or path planning
- No mobile / touch interface
- No undo/redo beyond workspace revert to last published version
