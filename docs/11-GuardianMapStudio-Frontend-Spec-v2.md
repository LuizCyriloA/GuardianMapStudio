# GuardianMapStudio — Frontend Specification v2

## 1. Technology Stack

| Technology | Version | Notes |
|---|---|---|
| Vue 3 | 3.4.x | Options API — consistent with Guardian dashboard |
| TypeScript | 5.x | Strict mode |
| Pinia | 2.x | State management |
| Leaflet.js | 1.9.4 | Map rendering — same version as Guardian |
| Vite | 5.x | Build tool |
| Axios | 1.x | HTTP client |

**Build output**: `frontend/dist/` — served as static files by FastAPI at `/`.

---

## 2. Application Structure

```
frontend/src/
├── main.ts                     ← createApp, mount, Pinia setup
├── App.vue                     ← root: sidebar nav + router-view
├── api/
│   ├── client.ts               ← all API calls, typed responses
│   └── types.ts                ← TypeScript interfaces matching API schemas
├── stores/
│   ├── project.ts              ← current project, version list
│   ├── workspace.ts            ← current workspace, validation state
│   └── map.ts                  ← roads, waypoints, crossroads, areas
├── components/
│   ├── layout/
│   │   ├── AppSidebar.vue      ← project selector, nav links
│   │   └── ValidationPanel.vue ← error/warning list, click-to-navigate
│   ├── map/
│   │   ├── MapEditor.vue       ← Leaflet map, entity drawing, snap indicator
│   │   ├── EntityForm.vue      ← create/edit form for any entity type
│   │   └── MapLegend.vue       ← color legend for entity types
│   ├── workspace/
│   │   ├── WorkspaceHeader.vue ← state badge, publish button, export button
│   │   └── PublishModal.vue    ← version name input + confirmation
│   └── version/
│       ├── VersionList.vue     ← published versions per project
│       └── VersionPreview.vue  ← read-only Leaflet map for a past version
└── views/
    ├── ProjectList.vue         ← list all projects, create new
    ├── EditorView.vue          ← main editing view (MapEditor + panels)
    └── VersionHistoryView.vue  ← version list + preview
```

---

## 3. Pinia Stores

### 3.1 Project Store (`stores/project.ts`)

```typescript
interface ProjectState {
  projects: ProjectResponse[]
  currentProject: ProjectResponse | null
  versions: VersionResponse[]
  loading: boolean
  error: string | null
}

actions:
  fetchProjects()                    → GET /api/v1/projects
  createProject(name, description)   → POST /api/v1/projects
  selectProject(id)                  → sets currentProject, fetches versions
  fetchVersions(projectId)           → GET /api/v1/projects/{id}/versions
```

### 3.2 Workspace Store (`stores/workspace.ts`)

```typescript
interface WorkspaceState {
  workspace: WorkspaceResponse | null
  validation: ValidationSummaryResponse | null
  publishing: boolean
  exporting: boolean
}

actions:
  fetchWorkspace(projectId)          → GET /api/v1/projects/{id}/workspace
  runValidation()                    → POST /api/v1/workspaces/{id}/validate
  publish(versionName)               → POST /api/v1/workspaces/{id}/publish
  exportVersion(versionId)           → POST /api/v1/versions/{id}/export
  downloadExport(versionId)          → GET /api/v1/versions/{id}/export/download

getters:
  canPublish                         → validation.error_count === 0
  isDraft                            → workspace.state === 'draft'
  errorCount                         → validation?.error_count ?? 0
  warningCount                       → validation?.warning_count ?? 0
```

### 3.3 Map Store (`stores/map.ts`)

```typescript
interface MapState {
  roads: RoadResponse[]
  waypoints: WaypointResponse[]
  crossroads: CrossroadResponse[]
  restrictedAreas: RestrictedAreaResponse[]
  selectedEntityId: number | null
  selectedEntityType: EntityType | null
  loading: boolean
}

type EntityType = 'road' | 'waypoint' | 'crossroad' | 'restricted_area'

actions:
  // Bulk load
  fetchMap(workspaceId)              → GET /api/v1/workspaces/{id}/map

  // Roads
  createRoad(data)                   → POST /api/v1/workspaces/{id}/roads
  updateRoad(roadId, data)           → PATCH /api/v1/workspaces/{id}/roads/{id}
  deleteRoad(roadId)                 → DELETE /api/v1/workspaces/{id}/roads/{id}

  // Waypoints
  createWaypoint(data)               → POST /api/v1/workspaces/{id}/waypoints
  updateWaypoint(waypointId, data)   → PATCH /api/v1/workspaces/{id}/waypoints/{id}
  deleteWaypoint(waypointId)         → DELETE /api/v1/workspaces/{id}/waypoints/{id}

  // Crossroads
  createCrossroad(data)              → POST /api/v1/workspaces/{id}/crossroads
  deleteCrossroad(crossroadId)       → DELETE /api/v1/workspaces/{id}/crossroads/{id}

  // Restricted areas
  createArea(data)                   → POST /api/v1/workspaces/{id}/restricted-areas
  updateArea(areaId, data)           → PATCH /api/v1/workspaces/{id}/restricted-areas/{id}
  deleteArea(areaId)                 → DELETE /api/v1/workspaces/{id}/restricted-areas/{id}

  // Selection (pan map to entity)
  selectEntity(type, id)             → sets selectedEntityId + selectedEntityType

getters:
  roadByName(name)                   → RoadResponse | undefined
  waypointsByType(type)              → WaypointResponse[]
```

---

## 4. MapEditor Component

**File**: `src/components/map/MapEditor.vue`

The core editing component. Hosts the Leaflet map and handles all drawing interactions.

### 4.1 Leaflet initialization

```
mounted() {
  this.$nextTick(() => {
    this.initMap()
  })
}
```

**Critical**: Leaflet must always initialize in `mounted()` + `$nextTick()`.
Never in `created()` — the DOM element does not exist yet.

### 4.2 Map layers

One Leaflet layer group per entity type:
- `roadsLayer` — `L.Polyline` per road, color by direction
- `waypointsLayer` — `L.Marker` per waypoint, icon by type
- `crossroadsLayer` — `L.CircleMarker` per crossroad
- `areasLayer` — `L.Polygon` per restricted area
- `validationLayer` — error/warning markers overlaid on entities
- `snapIndicatorLayer` — temporary marker showing snap preview

### 4.3 Drawing modes

The editor has three modes, controlled by `drawingMode` data property:

| Mode | Value | User action |
|---|---|---|
| Select | `'select'` | Click entity to select, open edit panel |
| Draw road | `'road'` | Click to add vertices; double-click to finish |
| Place waypoint | `'waypoint'` | Single click places waypoint at cursor |
| Draw area | `'area'` | Click to add polygon vertices; double-click to finish |

Mode is toggled via toolbar buttons. Only one mode active at a time.

### 4.4 Snap indicator

While in `'waypoint'` or `'road'` mode, on every `mousemove`:
1. Call `POST /api/v1/workspaces/{id}/snap` with current cursor position
2. If `snapped: true` → show blue circle marker at `snapped_to` position
3. If `snapped: false` → hide snap indicator

The snap indicator is a visual preview only — it does not persist any data.
On click, the waypoint/vertex is created at the snapped position.

### 4.5 Entity markers

```typescript
const WAYPOINT_ICONS: Record<string, string> = {
  stop_sign:  '🛑',
  speed_bump: '🔶',
  gate:       '🏠',
  landmark:   '📍',
  curve:      '↩️',
  crossroad:  '✖️',
  stop_zone:  '🅿️',
}

const ROAD_COLORS: Record<string, string> = {
  two_way: '#3388ff',   // blue
  one_way: '#ff7800',   // orange
}

const AREA_COLORS: Record<string, string> = {
  speed_limit:     '#ffcc00',   // yellow fill
  no_entry:        '#ff4444',   // red fill
  pedestrian_only: '#44ff44',   // green fill
}
```

### 4.6 Validation overlay

After every validation run:
- Remove all existing `validationLayer` markers
- For each `ValidationResult`:
  - ERROR → red `L.CircleMarker` at entity position
  - WARNING → yellow `L.CircleMarker` at entity position
  - Popup shows: `rule_id` + `message`
  - Clicking the marker also selects the entity in the panel

### 4.7 Popup delete buttons

Leaflet popups are HTML strings — Vue directives do not work inside them.
Delete buttons in popups must use `window.guardianApp.deleteEntity(type, id)`.

The app instance must be exposed:
```typescript
const app = createApp(App).mount('#app')
window.guardianApp = app
```

---

## 5. EntityForm Component

**File**: `src/components/map/EntityForm.vue`

Shown in a side panel when an entity is selected (select mode) or being created.

### 5.1 Waypoint form fields

Always shown:
- `name` (text input, required)
- `waypoint_type` (select: all WaypointType values)
- `road_name` (select: all road names in workspace, or "None")
- `lat`, `lng` (read-only display, updated by map click)

Conditional fields (shown based on `waypoint_type`):

| Type | Extra field |
|---|---|
| `speed_bump` | `height_cm` (number input, default 10, min 1) |
| `gate` | `gate_type` (select: entry/exit/entry_exit/internal) |
| `stop_sign` | `heading_degrees` (number input, 0–360, optional) |

### 5.2 Road form fields

- `name` (text input, required)
- `speed_limit_kmh` (number input, default 20, min 1)
- `direction` (select: two_way / one_way)
- `width_meters` (number input, default 6.0, min 0.1)

### 5.3 Restricted area form fields

- `name` (text input, required)
- `restriction_type` (select: speed_limit / no_entry / pedestrian_only)
- `speed_limit_kmh` (number input — shown only when restriction_type == speed_limit)
- `active` (toggle)

---

## 6. ValidationPanel Component

**File**: `src/components/layout/ValidationPanel.vue`

Always visible in the right panel. Updates automatically after every save.

### 6.1 Layout

```
┌─────────────────────────────────┐
│ Validation                      │
│ ● 2 errors   ○ 1 warning        │
├─────────────────────────────────┤
│ ● [road] road.min_points        │
│   "Road 'Rua X' has only 1..."  │  ← click to pan map
│                                 │
│ ● [waypoint] waypoint.road_exists│
│   "Waypoint 'PARE' references..." │
│                                 │
│ ○ [road] road.no_waypoints      │
│   "Road 'Rua Y' has no..."      │
└─────────────────────────────────┘
```

- Red dot (●) = ERROR
- Yellow dot (○) = WARNING
- Clicking any result calls `mapStore.selectEntity(type, id)` which pans the Leaflet map

### 6.2 Publish button state

The `Publish` button in `WorkspaceHeader.vue`:
- Disabled + gray when `workspaceStore.errorCount > 0`
- Enabled + green when `workspaceStore.canPublish`
- Tooltip when disabled: "Fix {n} error(s) before publishing"

---

## 7. WorkspaceHeader Component

**File**: `src/components/workspace/WorkspaceHeader.vue`

Shown above the map editor. Contains the workspace state badge and action buttons.

```
┌───────────────────────────────────────────────────────────────┐
│ Condomínio Parque das Flores   [DRAFT]                        │
│ Last validated: 2 minutes ago  ● 1 error  ○ 2 warnings        │
│                           [Validar]  [Publicar]  [Exportar v3]│
└───────────────────────────────────────────────────────────────┘
```

- `[Validar]` → calls `workspaceStore.runValidation()`
- `[Publicar]` → opens `PublishModal.vue`; disabled when errors exist
- `[Exportar v3]` → calls `workspaceStore.exportVersion(latestVersionId)`;
  only shown when at least one Version exists; shows latest version number

---

## 8. VersionHistoryView

**File**: `src/views/VersionHistoryView.vue`

Displays all published versions for the current project.

```
┌─────────────────────────────────────────────────────────────┐
│ Versões — Condomínio Parque das Flores                      │
├──────┬──────────────────────┬──────────────┬───────────────┤
│  v3  │ v3 - Adicionado play…│ 2026-06-01   │ [Ver] [Baixar]│
│  v2  │ v2 - Portaria ajust… │ 2026-05-28   │ [Ver] [Baixar]│
│  v1  │ v1 - Mapa inicial    │ 2026-05-20   │ [Ver] [Baixar]│
└──────┴──────────────────────┴──────────────┴───────────────┘
```

- `[Ver]` → opens `VersionPreview.vue` with read-only Leaflet map
- `[Baixar]` → GET /api/v1/versions/{id}/export/download

`VersionPreview.vue` shows the same visual as the editor but:
- No drawing mode toolbar
- All markers are non-editable
- No validation panel
- Banner: "Versão v3 (publicada em 2026-06-01) — somente leitura"

---

## 9. Leaflet Rules (Critical)

These rules apply to every Leaflet map instance in the application.

| Rule | Reason |
|---|---|
| Always init in `mounted()` + `$nextTick()` | DOM element does not exist in `created()` |
| Never use `v-if` on a map container | `v-if` destroys the Leaflet instance; use CSS `display: none` |
| Call `map.invalidateSize()` on tab switch | Leaflet loses dimensions when container is hidden |
| Popup buttons use `window.guardianApp.method()` | Vue directives don't work in Leaflet HTML strings |
| OSM tile URL: `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png` | Standard, no API key required |
| Default zoom for condominium: 18 | Sufficient detail for road-level editing |
| Attribution: `© OpenStreetMap contributors` | Required by OSM tile usage policy |

---

## 10. API Types (TypeScript)

**File**: `src/api/types.ts`

```typescript
export interface GeoPoint { lat: number; lng: number }

export interface RoadResponse {
  id: number; workspace_id: number; name: string
  coordinates: GeoPoint[]; speed_limit_kmh: number
  direction: 'two_way' | 'one_way'; width_meters: number
  created_at: string; updated_at: string
}

export interface WaypointResponse {
  id: number; workspace_id: number; name: string
  waypoint_type: string; lat: number; lng: number
  road_name: string | null; heading_degrees: number | null
  extra_data: Record<string, unknown>; active: boolean
  created_at: string; updated_at: string
}

export interface CrossroadResponse {
  id: number; workspace_id: number
  road_a_name: string; road_b_name: string
  lat: number; lng: number; created_at: string
}

export interface RestrictedAreaResponse {
  id: number; workspace_id: number; name: string
  polygon: GeoPoint[]; restriction_type: string
  speed_limit_kmh: number | null; active: boolean
  created_at: string; updated_at: string
}

export interface ValidationResultResponse {
  id: number; severity: 'error' | 'warning'
  rule_id: string; message: string
  affected_entity_type: string; affected_entity_id: number
}

export interface ValidationSummaryResponse {
  workspace_id: number; error_count: number; warning_count: number
  can_publish: boolean; results: ValidationResultResponse[]
  validated_at: string
}

export interface WorkspaceResponse {
  id: number; project_id: number; state: 'draft' | 'published'
  base_version_id: number | null
  has_validation_errors: boolean
  last_validated_at: string | null
  created_at: string; updated_at: string
}

export interface VersionResponse {
  id: number; project_id: number; version_number: number; name: string
  published_at: string
  road_count: number; waypoint_count: number
  crossroad_count: number; restricted_area_count: number
}
```
