# GuardianMapStudio — Roadmap v2

## 1. Purpose

This roadmap defines the evolution of GuardianMapStudio from a basic human map
editor to an AI-assisted mapping platform.

Guiding principles:
- Human operator in control at every phase
- Integration correctness before feature richness
- Each MVP ships a working, tested, deployable version
- Guardian import must work end-to-end before advancing to next MVP

---

## 2. Completion Criteria

A MVP is complete only when:
- All acceptance criteria in the corresponding spec document are met
- Test suite passes with ≥ 80% coverage
- `ruff check` and `mypy --strict` pass with zero errors
- A complete authoring workflow (create → edit → validate → publish → export)
  completes without errors
- The exported JSON is successfully imported by Guardian on the same machine

---

## MVP01 — Human Map Editor

**Status**: In Development

**Objective**: Replace manual JSON editing with a visual browser-based tool.
The operator draws the map, validates it, publishes a version, and exports
a Guardian-compatible JSON file.

### Features included
- Project and Workspace management
- Road polyline drawing on Leaflet map
- Waypoint placement (stop_sign, speed_bump, gate, curve, landmark, stop_zone)
- Crossroad placement
- Restricted area polygon drawing
- Automatic validation with inline error/warning display on map
- Publish → create immutable Version
- Export Version to Guardian JSON format
- Export history
- Version history with read-only map preview

### Features excluded
- AI assistance of any kind
- OSM/GeoJSON import
- Undo/redo
- Multi-user editing
- Authentication
- Road-to-segment snap (only endpoint snap)
- Automatic crossroad detection

### Definition of Done
- All acceptance criteria in doc 04 checked
- Full WF-01 walkthrough (create → edit → validate → publish → export) completes
- Guardian starts and HUD shows correct road name from exported map
- Coverage ≥ 80%, ruff and mypy pass

---

## MVP02 — AI-Assisted Detection + Smart Snap

**Objective**: Let the AI suggest map entities from Guardian session footage.
The operator reviews and accepts or rejects each suggestion. Reduce manual
placement effort by 60–80%.

### Features included
- **CandidateEntity pipeline**: Guardian session video → AI detector → candidate markers on map
- **Review workflow**: operator sees candidate markers (dashed outline, distinct color),
  accepts or rejects each before publish
- **Road-to-segment snap**: snap endpoints to points along an existing road segment,
  not just to explicit vertices
- **Automatic crossroad detection**: CrossroadEngine detects all intersections and
  suggests crossroad placements
- **Undo/redo**: full undo/redo stack within the DRAFT Workspace
- **OSM import**: import road network from OpenStreetMap as a starting point
- **Tech debt**: rename `ValidationResult.affected_entity_type/affected_entity_id`
  to `target_type/target_id` for generic workspace and project-level validation rules
  (e.g. "project has no versions"). In MVP01, `affected_entity_id = 0` works as a
  workaround for workspace-level errors, but the naming is imprecise.

### Features excluded
- Real-time AI (runs on recorded sessions, not live)
- Multi-user editing
- Authentication

### Definition of Done
- CandidateEntity workflow end-to-end (Guardian session → suggestions → accepted → exported)
- Automatic crossroad detection reduces manual placement by ≥ 50% on test maps
- Road-to-segment snap working correctly
- Undo/redo works for all entity operations
- Coverage ≥ 80%

---

## MVP03 — Multi-User + Authentication

**Objective**: Allow multiple operators to use GuardianMapStudio safely, with
access control and audit trail.

### Features included
- **User accounts**: login with email + password
- **Role-based access**: Admin (can publish and export), Editor (can edit DRAFT only)
- **Audit log**: every edit linked to a user account
- **Multi-project isolation**: users see only their assigned projects
- **Concurrent edit protection**: last-write-wins with conflict notification
- **Session management**: JWT-based authentication

### Features excluded
- Real-time collaborative editing (Google Docs style)
- SSO / OAuth

### Definition of Done
- Login flow works end-to-end
- Role separation enforced at API level
- Audit trail records all operations with user identity
- Coverage ≥ 80%

---

## MVP04 — Simulation + Path Planning Preview

**Objective**: Allow the operator to simulate the Guardian vehicle path through
the map before deploying, catching configuration errors before going to hardware.

### Features included
- **Path simulator**: given a start and end waypoint, display the planned route
  the Guardian Planner would take
- **Speed profile overlay**: show speed limit transitions along the path
- **Obstacle preview**: simulate what the Localizer would report at each point
- **Restricted area impact**: show how restricted areas affect the path
- **Export with simulation report**: include simulation results in the export meta block

### Features excluded
- Real hardware integration (simulation only)
- Live path adjustment

### Definition of Done
- Path simulation runs on any published Version
- Speed profile correctly reflects road limits and restricted areas
- Simulation report included in export JSON meta block
- Coverage ≥ 80%

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Guardian JSON format changes | Low | High | Guardian and GuardianMapStudio share test: `test_export_passes_guardian_seed()` |
| Shapely/pyproj version incompatibility | Low | Medium | Pin exact versions in `pyproject.toml` |
| Browser Leaflet performance on large maps (500+ entities) | Medium | Medium | STRtree mandatory (ADR-008); test with synthetic 500-entity map |
| AI detection quality insufficient for MVP02 | Medium | Medium | Operator review is mandatory — bad suggestions are just rejected |
| SQLite write contention (future multi-user) | High (MVP03+) | Low (MVP01) | MVP01 is single-operator; migrate to PostgreSQL in MVP03 if needed |
