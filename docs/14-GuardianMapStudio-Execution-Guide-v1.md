# GuardianMapStudio — Execution Guide v1

## Purpose

This document contains the exact prompts to send to Claude Code for each
implementation stage. Each prompt is self-contained — copy and paste directly.

**Prerequisites before starting Stage 1:**
1. Create the project directory: `mkdir guardianmapstudio && cd guardianmapstudio`
2. Initialize git: `git init`
3. Copy all docs to `docs/` directory
4. Run: `uv init` (creates basic pyproject.toml — will be overwritten by Stage 1)

**Workflow for each stage:**
1. Send the prompt below to Claude Code
2. Wait for Claude Code to complete
3. Run the quality gate commands shown at the end of each prompt
4. Fix any failures before advancing to the next stage
5. `git add -A && git commit -m "Stage N complete"`

---
---

## Stage 1 — Foundation

### Prompt for Claude Code

```
Read the file docs/13-GuardianMapStudio-Implementation-Blueprint-v3.md,
section STAGE 1.

Implement ONLY Stage 1 — Foundation.
Do not advance to Stage 2 until all quality gates pass.

RULES:

1. Create ALL files listed in "Files to create in Stage 1" — including
   every __init__.py for every package in the directory layout.

2. Copy pyproject.toml, settings.py, main.py, conftest.py EXACTLY from
   the Blueprint. Do not modify any version number, field name, or type.

3. contracts.py must contain ALL 6 enums, ALL 4 value objects, and ALL 8
   aggregates from the Blueprint section 1.7. Do not omit any field.
   CRITICAL: all dataclasses use @dataclass(frozen=True, slots=True).
   CRITICAL: all enums use (str, Enum).
   CRITICAL: GeoPoint must have __post_init__ with bounds validation.
   CRITICAL: Road, Waypoint, RestrictedArea have created_at and updated_at.

4. events.py must contain BaseEvent + ALL 15 concrete events from section 1.8.

5. The conftest.py must have the STAGE 2 and STAGE 4 blocks COMMENTED OUT.
   They will be uncommented in those stages. Do NOT uncomment them now.

6. .gitignore, .pre-commit-config.yaml, and .github/workflows/ci.yml must
   all be created with the content from the Blueprint.

QUALITY GATE — run in this order:

   uv sync
   uv sync --extra dev
   uv run ruff check src/ tests/
   uv run mypy src/
   uv run pytest tests/unit/test_contracts.py -v
   python3 -c "from guardianmapstudio.main import create_app; app = create_app(); print('OK')"

Fix ALL errors before reporting completion.
```

---
---

## Stage 2 — Database

### Prompt for Claude Code

```
Read the file docs/13-GuardianMapStudio-Implementation-Blueprint-v3.md,
section STAGE 2.

Implement ONLY Stage 2 — Database.
Do not advance to Stage 3 until all quality gates pass.

FIRST ACTION: Open tests/conftest.py and uncomment the block marked
"STAGE 2". This adds db_engine and db_session fixtures.
Do NOT uncomment the STAGE 4 block.

RULES:

1. models.py must contain ALL 11 SQLAlchemy models from section 2.2.
   Copy the code EXACTLY. Do not change column types, constraint names,
   or relationship configurations.
   CRITICAL: latitude and longitude columns use Double — NEVER Float.
   CRITICAL: all mutable tables have updated_at with onupdate lambda.
   CRITICAL: cascade="all, delete-orphan" on all workspace children.

2. connection.py must match section 2.1 exactly.
   CRITICAL: check_same_thread is CONDITIONAL on SQLite URL.
   CRITICAL: get_db() does NOT live here — it lives in api/deps.py (Stage 4).

3. repository.py must implement ALL 6 repositories with ALL 36 methods
   listed in section 2.3. Each repository receives a Session in __init__.
   CRITICAL: All methods return domain contracts (from contracts.py), never
   ORM models. Use explicit _to_domain() conversion methods.
   CRITICAL: coordinates JSON uses {lat, lng} keys → convert to
   GeoPoint(latitude=p["lat"], longitude=p["lng"]).
   CRITICAL: Waypoint position must be constructed from separate lat/lng columns:
   GeoPoint(latitude=model.latitude, longitude=model.longitude).
   CRITICAL: extra_data must be deserialized with json.loads() → dict, not str.
   CRITICAL: When WRITING JSON to the database (coordinates, polygon, extra_data),
   always use json.dumps(..., ensure_ascii=False). Without this, road names with
   accented characters (e.g. "Rua São José") are stored as escaped unicode
   ("Rua S\u00e3o Jos\u00e9"), which breaks readability in the export file.
   CRITICAL: enum strings must be converted: RoadDirection(model.direction).

4. ProjectRepository.create() must also create the first DRAFT Workspace
   for the project automatically (BR-01: a Project always has one DRAFT).

QUALITY GATE:

   uv run ruff check src/ tests/
   uv run mypy src/
   uv run pytest tests/unit/ tests/integration/test_database.py -v

   python3 -c "
   from sqlalchemy import create_engine, inspect
   from guardianmapstudio.database.connection import create_tables
   engine = create_engine('sqlite:///:memory:')
   create_tables(engine)
   tables = sorted(inspect(engine).get_table_names())
   assert len(tables) == 11, f'Expected 11, got {len(tables)}: {tables}'
   print('11 tables:', tables)
   "

Fix ALL errors before reporting completion.
```

---
---

## Stage 3 — Geometry Engines + Exporter

### Prompt for Claude Code

```
Read the file docs/13-GuardianMapStudio-Implementation-Blueprint-v3.md,
section STAGE 3.

Implement ONLY Stage 3 — Geometry Engines + Exporter.
Do not advance to Stage 4 until all quality gates pass.

RULES:

1. GeometryEngine (engine.py): Copy the COMPLETE CODE from section 3.1.
   CRITICAL: EARTH_RADIUS_M = 6_371_000 — same as Guardian. Do not change.
   CRITICAL: haversine uses math.asin(math.sqrt(h)) — NOT math.atan2.
   CRITICAL: _to_local() is identical to Guardian's geo_utils._to_local().
   CRITICAL: from_centroid() handles BOTH hemispheres (31960+zone for south,
   32600+zone for north).
   CRITICAL: STRtree.query() returns numpy.ndarray of INTEGER INDICES,
   not geometry objects. Access: waypoints[int(idx)].

2. SnapEngine (snap.py): Copy from section 3.2.
   MVP01 candidates: road endpoints + waypoint positions ONLY.
   Road-to-segment snapping is MVP02 — do NOT implement.
   Always return SnapResult, even when snapped=False.

3. CrossroadEngine (crossroad.py): Copy from section 3.3.
   INTERSECTION_PROXIMITY_M = 1.0 — marker must be within 1m.

4. ValidationEngine (validation.py): Copy from section 3.4.
   ALL 19 RULES must be present. If any rule is missing, the validation
   is incomplete and publish will allow invalid maps.
   Rules: road(5) + waypoint(6) + crossroad(4) + area(4) + workspace(1) = 20
   CRITICAL: waypoint.duplicate_position uses O(n²) — this is intentional
   for MVP01 (max ~80 waypoints). Do NOT optimize.
   CRITICAL: _validate_roads_waypoint_coverage needs BOTH roads and waypoints
   as parameters. It is called from _validate_waypoints, not _validate_roads.

5. GuardianExporter (guardian_exporter.py): Copy from section 3.5.
   CRITICAL: waypoint key is "type" — NOT "waypoint_type".
   CRITICAL: "road" key always present even when null.
   CRITICAL: "heading_degrees" key OMITTED when null (not included with null value).
   CRITICAL: active=False waypoints EXCLUDED from export.
   CRITICAL: json.dumps(..., indent=2, ensure_ascii=False).

QUALITY GATE:

   uv run ruff check src/ tests/
   uv run mypy src/
   uv run pytest tests/unit/ -v --cov=guardianmapstudio.geometry \
     --cov=guardianmapstudio.export --cov-report=term-missing

Geometry coverage ≥ 90%. Exporter coverage = 100%.
Fix ALL errors before reporting completion.
```

---
---

## Stage 4 — REST API (Backend)

### Prompt for Claude Code

```
Read the file docs/13-GuardianMapStudio-Implementation-Blueprint-v3.md,
section STAGE 4.

Implement ONLY Stage 4 — REST API.
Do not advance to Stage 5 until all quality gates pass.

FIRST ACTION: Open tests/conftest.py and uncomment the block marked
"STAGE 4". This adds the client fixture for API integration tests.

SECOND ACTION: Replace src/guardianmapstudio/main.py with the Stage 4
version from section 4.4. This registers all routers and sets up the
engine singleton in app.state via lifespan.

RULES:

1. schemas.py: Copy ALL DTOs from section 4.2 EXACTLY.
   CRITICAL: WorkspaceResponse.state is Literal["draft", "published"].
   CRITICAL: GeoPointDTO has lat/lng (NOT latitude/longitude).

2. errors.py: Copy ErrorCode enum from section 4.1.

3. deps.py: Copy from section 4.3.
   CRITICAL: get_settings() uses @lru_cache(maxsize=1).
   CRITICAL: get_db() reads from request.app.state.session_factory.

4. main.py: Copy Stage 4 version from section 4.4. This REPLACES the
   Stage 1 stub entirely.
   CRITICAL: lifespan creates engine ONCE and stores session_factory
   in app.state. Engine is disposed on shutdown.
   CRITICAL: StaticFiles mount is LAST (after all routers) and only
   if the static directory exists.

5. EVERY router must implement domain→response conversion EXPLICITLY.
   NEVER use road.__dict__ (slots=True removes it).
   NEVER use dataclasses.asdict() (converts GeoPoint to {latitude, longitude}
   but GeoPointDTO expects {lat, lng}).
   Each router file has its own <entity>_to_response() function.
   See the road_to_response() example in section 4.5.

6. EVERY router that writes a map entity (POST, PATCH, DELETE for roads,
   waypoints, crossroads, restricted_areas) MUST call
   _run_validation_after_write() at the end of the handler.
   Copy the helper function from section 4.5.

7. POST /api/v1/projects must also create a DRAFT Workspace automatically
   (delegate to ProjectRepository.create which already does this).

8. POST /api/v1/workspaces/{id}/publish must:
   a. Check workspace is DRAFT (else 409 WORKSPACE_NOT_DRAFT)
   b. Run validation (else 422 VALIDATION_ERRORS_BLOCKING if errors)
   c. Create Version with next_version_number
   d. Copy all roads → road_versions, all entities → entity_versions
   e. Set workspace state to PUBLISHED
   f. Create new DRAFT workspace from the new version
   g. Return 201 with the new VersionResponse

9. Use ErrorCode.VALUE.value for all error responses — never hardcode strings.

QUALITY GATE:

   uv run ruff check src/ tests/
   uv run mypy src/
   uv run pytest tests/ -v --cov=guardianmapstudio --cov-fail-under=80

Fix ALL errors before reporting completion.
```

---
---

## Stage 5 — Frontend (Vue 3 + TypeScript)

### Prompt for Claude Code

```
Read the file docs/13-GuardianMapStudio-Implementation-Blueprint-v3.md,
section STAGE 5.

Also read docs/11-GuardianMapStudio-Frontend-Spec-v2.md in its entirety
for component details, store interfaces, and Leaflet rules.

Implement ONLY Stage 5 — Frontend.
This is the final stage of MVP01.

RULES:

1. Copy package.json, tsconfig.json, vite.config.ts EXACTLY from section 5.1.
   CRITICAL: All dependency versions are PINNED (no ^ or ~ ranges).
   CRITICAL: vite build outputs to ../src/guardianmapstudio/static/.

2. Copy types.ts from section 5.2 and client.ts from section 5.3 EXACTLY.
   CRITICAL: API_BASE = '' (empty string — same origin).
   CRITICAL: All API calls go through the client.ts functions. No raw
   fetch() in components.

3. Implement ALL 3 Pinia stores matching the interfaces in doc 11 section 3:
   project.ts, workspace.ts, map.ts.

4. Implement ALL components from doc 11 sections 4–8.

5. LEAFLET RULES (section 5.4) — violating any one causes hard-to-debug errors:
   CRITICAL: Always init in mounted() + this.$nextTick() — NEVER created().
   CRITICAL: Tab/view switching uses CSS display:none — NEVER v-if on map.
   CRITICAL: Call map.invalidateSize() after container becomes visible.
   CRITICAL: Popup buttons use window.guardianApp.deleteEntity(type, id).
   CRITICAL: const app = createApp(App); window.guardianApp = app.mount('#app').

6. MARKERS (section 5.5): Use letter markers (P, L, G, C, M, S) with
   color-coded circles. NO EMOJIS. Professional GIS appearance.

7. The Publish button is DISABLED when has_validation_errors is true.
   Tooltip: "Corrija N erro(s) antes de publicar".

QUALITY GATE:

   cd frontend
   npm ci
   npm run build
   cd ..

   uv run ruff check src/ tests/
   uv run mypy src/
   uv run pytest tests/ -v --cov=guardianmapstudio --cov-fail-under=80

   uv run guardianmapstudio

Then open http://localhost:8000 and run the WF-01 checklist from the
Blueprint section 5.7.

Fix ALL errors before reporting completion.
This is the last stage — MVP01 is complete when all checks pass.
```

