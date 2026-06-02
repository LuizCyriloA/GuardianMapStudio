# GuardianMapStudio — Editor UX Patch v1 (Complementary Spec — Doc 17)

> **Status**: Complementary patch on top of MVP01 + Doc 15 (OSM Import) + Doc 16 (Editor UX).
> **Type**: 3 small UI improvements (1 new control, 1 behavior fix, 1 bug fix).
> **Footprint**: Frontend only. Zero backend changes. Zero new dependencies.

---

## 1. Purpose & Scope

After running Doc 16 in production, three issues surfaced:

1. **Discoverability**: with 50+ roads on the map, finding a specific road by
   panning and clicking is tedious. A dropdown / search box that lists all
   roads is needed.
2. **Pan blocked in Select mode**: Doc 16 §5.8 disables `map.dragging` whenever
   a mousedown starts in Select mode. The operator can no longer pan the map
   while in this mode, which makes editing painful. Rectangle selection should
   require a modifier key (CTRL/Cmd); plain drag should pan as usual.
3. **Waypoint button is dead**: clicking "Waypoint" in the toolbar produces no
   reaction. The waypoint form never opens. This is a regression bug.

### 1.1 Relationship to other documents

| Doc | Relationship |
|---|---|
| 11 (Frontend Spec) | §4 (MapEditor) — adds one toolbar control, modifies the click-mode behavior, fixes waypoint mode handler. |
| 13 (Implementation Blueprint) | Add as small "Stage 8 — Editor UX Patch". Stages 1–7 unchanged. |
| 15 (OSM Import) | Unchanged. The new road dropdown lists OSM-imported roads alongside manually created ones. |
| 16 (Editor UX) | Modifies §5.8 (RectangleSelector behavior) and §5.4 (waypoint form handler). All other §5 sections (compass, undo, ConfirmModal, merge modal, etc.) are unchanged. |

### 1.2 What this is NOT

- Not a redesign. The toolbar layout from Doc 16 stays; one control is added.
- Not a new entity type, new endpoint, or new validation rule.
- Not a search across waypoints, crossroads, or areas — roads only.

---

## 2. Impact Analysis — What Stays, What Changes

### 2.1 What stays exactly the same

| Component | Status |
|---|---|
| All 11 database tables | **Unchanged** |
| All SQLAlchemy models | **Unchanged** |
| Domain contracts and enums | **Unchanged** |
| Geometry engines | **Unchanged** |
| All 37 existing API endpoints (35 + 2 merge from Doc 16) | **Unchanged** |
| GuardianExporter & export format | **Unchanged** |
| Validation rules | **Unchanged** |
| Publish & Export workflows | **Unchanged** |
| Test coverage threshold (80%) | **Unchanged** |
| Backend tests | **Unchanged** (no backend changes) |
| All other frontend behavior (compass, undo, merge modal, OSM modal, etc.) | **Unchanged** |

### 2.2 What changes

| Area | Change | Files touched |
|---|---|---|
| Backend | NOTHING | — |
| Frontend toolbar | New `RoadQuickSelect` control next to "Desfazer" | `MapEditor.vue` (template), new `components/map/RoadQuickSelect.vue` |
| Frontend map store | New `centerOnRoad(id)` action | `stores/map.ts` (additive) |
| Frontend rectangle selector | CTRL-gated rectangle, default drag = pan | `components/map/RectangleSelector.ts` (modified) |
| Frontend MapEditor | Waypoint click handler — investigate + fix | `MapEditor.vue` (bug fix) |
| Tests | None (no backend changes; existing frontend has no unit tests in MVP01) | — |

### 2.3 Why all changes are safe

- **No backend changes** — zero risk to API contracts, DB schema, or export format.
- **Road dropdown reuses existing state** (`mapStore.roads`) and existing actions
  (`selectRoad` from Doc 16 §5.5). No new store concepts.
- **CTRL gating is strictly less aggressive** than the current behavior:
  rectangle selection still works when CTRL is held; without CTRL the map
  simply pans (the natural Leaflet default). No path that previously worked
  becomes broken.
- **Waypoint fix is a bug fix**, not a refactor. The reference implementation
  in §5.3 is the spec; if the existing code matches it, only the missing piece
  needs to be added.

---

## 3. Architecture Decisions

### ADR-17-01 — Road dropdown uses `<input list>` + `<datalist>`, not `<select>`

**Decision**: Render the road quick-select as an HTML5 `<input list>` paired
with a `<datalist>` of all road names. The operator can type to filter, or
click the field and pick from the dropdown.

**Rationale**:
- A native `<select>` becomes unusable with > 50 options (no search, long
  scroll). Brazilian condominium maps regularly exceed this.
- `<input list>` + `<datalist>` is **standard HTML5**, zero JavaScript, zero
  dependencies, works in every modern browser. Filtering as the operator
  types is free.
- Alternative considered: a custom autocomplete component (e.g. PrimeVue
  AutoComplete). Rejected because it would add a UI library dependency for
  a single control.

**Trade-off**: minor browser inconsistency in how the dropdown chrome renders
(Safari shows a slightly different style). Acceptable — function is identical.

### ADR-17-02 — Rectangle selection requires CTRL (or Cmd on macOS); plain drag pans

**Decision**: In Select mode, dragging the mouse **without** a modifier key
pans the map (the Leaflet default). Holding **CTRL** (or **Cmd** on macOS)
while dragging draws the selection rectangle.

**Rationale**:
- Today's behavior (Doc 16) makes the map unpannable in Select mode, which
  is the most-used mode (clicking roads to inspect/delete them).
- CTRL+drag for rectangle selection is the convention in many editors
  (Figma, Photoshop selection tools).
- Pure drag = pan matches the default Leaflet experience the operator
  already knows from non-Select modes.

**Trade-off**: operators must learn one modifier key. Mitigated by a status
hint shown in Select mode: "CTRL+arrastar para selecionar várias ruas".

**Alternative considered**: a separate "Retângulo" toolbar button that puts
the editor into an exclusive rectangle-draw mode. Rejected because it adds
a click for every multi-select operation.

### ADR-17-03 — Waypoint click handler: investigate first, then apply reference implementation

**Decision**: Before changing any waypoint-mode code, the implementation must
first **read the current MapEditor.vue and identify which link in the chain
is broken**. The reference implementation in §5.3 is the target state; the
fix is whatever is needed to reach that state.

**Rationale**:
- The bug "nothing happens when I click Waypoint" can have at least 6 distinct
  root causes (button click handler missing, `drawingMode` not updated,
  `onMapClick` not branching on waypoint mode, `entityFormOpen` not being set,
  EntityForm v-if condition wrong, EntityForm import missing, or a JavaScript
  error in the console blocking everything).
- A blind rewrite risks fixing the wrong issue or introducing regressions in
  the road/area flows that share the same handler.
- The reference implementation gives a clear target; the diff is what gets
  applied.

---

## 4. Backend Changes

**None.** This patch is frontend-only.

---

## 5. Frontend Changes

### 5.1 New component: `RoadQuickSelect.vue`

**File**: `frontend/src/components/map/RoadQuickSelect.vue`

A small toolbar control that lists every road in the active workspace,
sorted alphabetically. Selecting a road from the list:
1. Selects the road in the map store (highlights it amber per Doc 16 §5.5).
2. Centers the map on that road's bounding box.
3. Opens the entity panel showing the road's data (same as click-to-select).

```vue
<template>
  <div class="road-quick-select">
    <label class="rqs-label" for="rqs-input">Ir para rua:</label>
    <input
      id="rqs-input"
      ref="input"
      v-model="query"
      list="rqs-roads-list"
      type="text"
      :placeholder="placeholder"
      class="rqs-input"
      :disabled="!hasRoads"
      autocomplete="off"
      @change="onChange"
      @keydown.enter.prevent="onChange"
    />
    <datalist id="rqs-roads-list">
      <option v-for="road in sortedRoads" :key="road.id" :value="road.name" />
    </datalist>
    <button
      v-if="query"
      class="rqs-clear"
      type="button"
      title="Limpar busca"
      @click="onClear"
    >
      ×
    </button>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue'
import { useMapStore } from '../../stores/map'

export default defineComponent({
  name: 'RoadQuickSelect',

  data() {
    return {
      query: '' as string,
    }
  },

  computed: {
    mapStore() {
      return useMapStore()
    },
    sortedRoads() {
      // Cloned + sorted alphabetically (case-insensitive, locale-aware
      // so "São" sorts naturally for the operator).
      return [...this.mapStore.roads].sort((a, b) =>
        a.name.localeCompare(b.name, 'pt-BR', { sensitivity: 'base' }),
      )
    },
    hasRoads(): boolean {
      return this.mapStore.roads.length > 0
    },
    placeholder(): string {
      if (!this.hasRoads) return 'Nenhuma rua cadastrada'
      return `Digite ou escolha (${this.mapStore.roads.length} ruas)`
    },
  },

  methods: {
    onChange() {
      const name = this.query.trim()
      if (!name) return
      const road = this.mapStore.roads.find(
        r => r.name.toLowerCase() === name.toLowerCase(),
      )
      if (!road) {
        // The user typed something that isn't a road name. Do nothing —
        // datalist filtering will guide them. Don't show an alert.
        return
      }
      this.mapStore.selectRoad(road.id)
      // Centering and panel-opening are delegated to MapEditor via event,
      // because RoadQuickSelect must not depend on the Leaflet map instance.
      this.$emit('road-selected', road.id)
    },
    onClear() {
      this.query = ''
      this.mapStore.clearSelection()
      this.$refs.input && (this.$refs.input as HTMLInputElement).focus()
      this.$emit('selection-cleared')
    },
  },

  emits: ['road-selected', 'selection-cleared'],
})
</script>

<style scoped>
.road-quick-select {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 0 8px;
}
.rqs-label {
  font-size: 0.85rem;
  color: #444;
  white-space: nowrap;
}
.rqs-input {
  width: 220px;
  padding: 4px 8px;
  font-size: 0.9rem;
  border: 1px solid #bbb;
  border-radius: 4px;
}
.rqs-input:disabled {
  background: #f3f3f3;
  color: #999;
}
.rqs-clear {
  background: none;
  border: 1px solid #bbb;
  border-radius: 50%;
  width: 22px;
  height: 22px;
  font-size: 0.9rem;
  cursor: pointer;
  color: #666;
}
.rqs-clear:hover { background: #eee; }
</style>
```

### 5.2 New `centerOnRoad` action in map store

**File**: `frontend/src/stores/map.ts` — append to actions.

```typescript
actions: {
  // ... existing actions ...

  /**
   * Center the map view on a specific road's bounding box.
   * Used by RoadQuickSelect after selection.
   * The actual Leaflet call lives in MapEditor; this action computes
   * the bounds and exposes them via a transient state field that
   * MapEditor watches.
   *
   * Implementation note: we DON'T store a reference to the Leaflet map
   * in Pinia (the map is a Leaflet object that should not be reactive).
   * Instead, MapEditor watches `pendingFocusRoadId` and reacts.
   */
  focusRoad(roadId: number) {
    this.pendingFocusRoadId = roadId
  },

  consumeFocusRoad() {
    this.pendingFocusRoadId = null
  },
},

state: () => ({
  // ... existing fields ...
  pendingFocusRoadId: null as number | null,
}),
```

### 5.3 Wire the dropdown into `MapEditor.vue`

#### 5.3.1 Toolbar slot

Place the dropdown **immediately to the LEFT of the "⟲ Desfazer" button**
(per the user's request: "do lado do botão Desfazer"):

```vue
<div class="toolbar">
  <!-- ... existing buttons up to and including "🎯 Centralizar" ... -->

  <RoadQuickSelect
    @road-selected="onRoadFromQuickSelect"
    @selection-cleared="onQuickSelectCleared"
  />

  <button class="btn-undo" :disabled="!undoStore.canUndo" ...>
    ⟲ Desfazer
  </button>

  <!-- ... remaining buttons (Validar, Publicar, Exportar) ... -->
</div>
```

#### 5.3.2 Event handlers in MapEditor

```typescript
methods: {
  // ... existing methods ...

  onRoadFromQuickSelect(roadId: number) {
    // Selection in mapStore was already updated by RoadQuickSelect.
    // We handle: restyle, center the map, open the side panel.
    this.refreshRoadStyles()
    this.centerMapOnRoad(roadId)
    this.openRoadPanel(roadId)
  },

  onQuickSelectCleared() {
    this.refreshRoadStyles()
    this.entityFormOpen = false
  },

  centerMapOnRoad(roadId: number) {
    const road = this.mapStore.roads.find(r => r.id === roadId)
    if (!road || road.coordinates.length === 0) return
    const bounds = L.latLngBounds(
      road.coordinates.map(p => [p.lat, p.lng] as L.LatLngExpression),
    )
    if (bounds.isValid()) {
      this.map.fitBounds(bounds, {
        padding: [60, 60],
        maxZoom: 19,
      })
    }
  },

  openRoadPanel(roadId: number) {
    const road = this.mapStore.roads.find(r => r.id === roadId)
    if (!road) return
    this.entityFormType = 'road'
    this.entityFormData = { ...road }
    this.entityFormOpen = true
  },
},
```

### 5.4 RectangleSelector: CTRL/Cmd-gated rectangle, default drag pans

**File**: `frontend/src/components/map/RectangleSelector.ts` — replace the
implementation from Doc 16 §5.8 with the version below. The public API
(`attachRectangleSelector(map, opts) → teardown`) is unchanged.

```typescript
import L from 'leaflet'

export interface RectangleSelectorOptions {
  /** Called with the geographic bounds of the drawn rectangle. */
  onSelect: (bounds: L.LatLngBounds) => void
  /** Visual style for the in-progress rectangle. */
  style?: L.PathOptions
}

const DEFAULT_STYLE: L.PathOptions = {
  color: '#FFB400',
  weight: 1.5,
  fillColor: '#FFB400',
  fillOpacity: 0.18,
  dashArray: '4 4',
}

/**
 * Attaches a click-drag rectangle selection handler to a Leaflet map.
 *
 * Behavior:
 *  - Plain drag → map pans (Leaflet default — we do NOT interfere).
 *  - CTRL+drag (or Cmd+drag on macOS) → draws a selection rectangle.
 *
 * Returns a teardown function that detaches all handlers and restores
 * any temporarily-disabled map behavior.
 */
export function attachRectangleSelector(
  map: L.Map,
  opts: RectangleSelectorOptions,
): () => void {
  const style = { ...DEFAULT_STYLE, ...(opts.style ?? {}) }
  let startLatLng: L.LatLng | null = null
  let rectLayer: L.Rectangle | null = null
  let active = false   // True only when a CTRL-modified drag is in progress

  const isModified = (e: L.LeafletMouseEvent | MouseEvent): boolean => {
    const orig = 'originalEvent' in e ? e.originalEvent : (e as MouseEvent)
    return orig.ctrlKey || orig.metaKey
  }

  const onMouseDown = (e: L.LeafletMouseEvent) => {
    // Without modifier → let Leaflet pan the map. Do nothing.
    if (!isModified(e)) return

    // Don't start a rectangle on a marker (let marker click pass through).
    const target = e.originalEvent.target as HTMLElement | null
    if (target?.closest('.leaflet-marker-icon')) return

    active = true
    startLatLng = e.latlng
    map.dragging.disable()        // ONLY now — not on every mousedown
    map.getContainer().style.cursor = 'crosshair'
  }

  const onMouseMove = (e: L.LeafletMouseEvent) => {
    if (!active || !startLatLng) return
    const bounds = L.latLngBounds(startLatLng, e.latlng)
    if (!rectLayer) {
      rectLayer = L.rectangle(bounds, style).addTo(map)
    } else {
      rectLayer.setBounds(bounds)
    }
  }

  const onMouseUp = (e: L.LeafletMouseEvent) => {
    if (!active || !startLatLng) {
      return
    }
    const bounds = L.latLngBounds(startLatLng, e.latlng)
    const moved = startLatLng.distanceTo(e.latlng)
    if (moved > 5) {
      opts.onSelect(bounds)
    }
    if (rectLayer) {
      map.removeLayer(rectLayer)
      rectLayer = null
    }
    startLatLng = null
    active = false
    map.dragging.enable()
    map.getContainer().style.cursor = ''
  }

  // Safety: if the user releases CTRL mid-drag, abort cleanly.
  const onKeyUp = (e: KeyboardEvent) => {
    if (!active) return
    if (e.key === 'Control' || e.key === 'Meta') {
      if (rectLayer) {
        map.removeLayer(rectLayer)
        rectLayer = null
      }
      startLatLng = null
      active = false
      map.dragging.enable()
      map.getContainer().style.cursor = ''
    }
  }

  map.on('mousedown', onMouseDown)
  map.on('mousemove', onMouseMove)
  map.on('mouseup', onMouseUp)
  document.addEventListener('keyup', onKeyUp)

  return () => {
    map.off('mousedown', onMouseDown)
    map.off('mousemove', onMouseMove)
    map.off('mouseup', onMouseUp)
    document.removeEventListener('keyup', onKeyUp)
    if (rectLayer) map.removeLayer(rectLayer)
    map.dragging.enable()
    map.getContainer().style.cursor = ''
  }
}
```

#### 5.4.1 Status hint in Select mode

In `MapEditor.vue`, when `drawingMode === 'select'`, show a one-line status
hint below the toolbar (or as a small overlay in the top-left of the map):

```vue
<div v-if="drawingMode === 'select'" class="select-mode-hint">
  💡 Clique numa rua para selecionar.
  Mantenha <kbd>CTRL</kbd> e arraste para selecionar várias.
</div>
```

CSS:
```css
.select-mode-hint {
  background: #f8f8f8;
  border-left: 3px solid #FFB400;
  padding: 6px 12px;
  font-size: 0.85rem;
  color: #555;
}
.select-mode-hint kbd {
  background: #fff;
  border: 1px solid #ccc;
  border-radius: 3px;
  padding: 1px 5px;
  font-family: monospace;
}
```

### 5.5 Waypoint click handler — investigation + reference implementation

This is a **bug fix**. The current behavior is: clicking the "Waypoint"
toolbar button does nothing visible — the form never opens.

#### 5.5.1 Mandatory investigation (do this FIRST, before changing code)

Open `frontend/src/components/map/MapEditor.vue` and verify each link in
the chain. The chain should look like this end-to-end:

```
User clicks "Waypoint" toolbar button
   ↓ (button @click)
this.setMode('waypoint')
   ↓
this.drawingMode = 'waypoint'   (data property)
   ↓
(optional) cursor changes to crosshair
   ↓
User clicks on the map
   ↓ (map L.Map 'click' handler)
this.onMapClick(e)
   ↓ (branches on this.drawingMode)
if (this.drawingMode === 'waypoint') this.openWaypointForm(e.latlng)
   ↓
sets entityFormType = 'waypoint', entityFormData = {...}, entityFormOpen = true
   ↓
EntityForm component re-renders because v-if="entityFormOpen" becomes true
   ↓
Form is visible to the user with TIPO as the first field
```

**For each step, verify in the actual code**:

1. **Toolbar button**: does the "Waypoint" `<button>` have a `@click="setMode('waypoint')"` handler? If the button has no handler, or the handler is calling the wrong method name, this is the bug.

2. **setMode**: does the method exist and actually mutate `this.drawingMode`? Open the browser DevTools, click the button, and inspect the Vue component — `drawingMode` should change to `'waypoint'`.

3. **Map click handler**: is there a `this.map.on('click', this.onMapClick)` in `initMap()` (or equivalent)? If the handler is registered but does not branch on `drawingMode`, that is the bug.

4. **openWaypointForm exists**: search for any function that opens the waypoint form. If only `openRoadForm` exists and there's no waypoint equivalent, that's the bug.

5. **EntityForm v-if condition**: open the parent template and find `<EntityForm v-if="..." />`. The condition must include the waypoint case. A common bug: `v-if="entityFormOpen && entityFormType === 'road'"` (excludes waypoint).

6. **Browser console**: open DevTools console and click Waypoint, then click the map. **Any JavaScript error blocks the rest of the handler.** If you see "Cannot read properties of undefined", that's the bug.

Document which step is broken before applying the fix below.

#### 5.5.2 Reference implementation

Once the broken step is identified, the code below is the canonical
implementation. Apply only the parts that are missing or wrong; do not
rewrite the whole file.

```typescript
// In MapEditor.vue <script>

data() {
  return {
    drawingMode: 'select' as 'select' | 'road' | 'waypoint',
    entityFormOpen: false,
    entityFormType: null as 'road' | 'waypoint' | null,
    entityFormData: {} as Record<string, unknown>,
    // ... other data
  }
},

methods: {
  setMode(mode: 'select' | 'road' | 'waypoint') {
    this.drawingMode = mode

    // Visual cursor feedback
    if (this.map) {
      this.map.getContainer().style.cursor =
        mode === 'waypoint' ? 'crosshair' :
        mode === 'road' ? 'crosshair' :
        ''
    }

    // When LEAVING select mode, clear any selection so the operator
    // doesn't accidentally Delete a selected road by pressing Delete
    // in another context.
    if (mode !== 'select' && this.mapStore.selectedRoadIds.length > 0) {
      this.mapStore.clearSelection()
      this.refreshRoadStyles()
    }
  },

  initMap() {
    // ... existing init (tile layer, compass, layers) ...
    this.map.on('click', this.onMapClick)
  },

  onMapClick(e: L.LeafletMouseEvent) {
    // Branch on the active drawing mode
    if (this.drawingMode === 'waypoint') {
      this.openWaypointForm(e.latlng)
      return
    }
    if (this.drawingMode === 'select') {
      // Empty-map click in select mode → clear selection
      if (this.mapStore.selectedRoadIds.length > 0) {
        this.mapStore.clearSelection()
        this.refreshRoadStyles()
        this.entityFormOpen = false
      }
      return
    }
    // (road mode handler if any — covered by OSM import nowadays)
  },

  openWaypointForm(latlng: L.LatLng) {
    // Force the form to re-mount even if it was already open with
    // stale data. This is the fix for the Doc 16 §5.4 race condition.
    this.entityFormOpen = false
    this.$nextTick(() => {
      this.entityFormType = 'waypoint'
      this.entityFormData = {
        lat: latlng.lat,
        lng: latlng.lng,
        waypoint_type: '',                // empty → forces TIPO selection
        name: '',
        road_name: this.guessNearestRoadName(latlng) ?? null,
        heading_degrees: null,
        extra_data: {},
      }
      this.entityFormOpen = true
    })
  },

  guessNearestRoadName(latlng: L.LatLng): string | null {
    // Naive nearest-road lookup. Iterates all roads (O(N*M)).
    // For the MVP target of ≤500 entities this is < 5 ms.
    // Returns null if no road is within ~30 m of the click.
    let nearest: { name: string; dist: number } | null = null
    for (const road of this.mapStore.roads) {
      for (const pt of road.coordinates) {
        const d = latlng.distanceTo([pt.lat, pt.lng])
        if (!nearest || d < nearest.dist) {
          nearest = { name: road.name, dist: d }
        }
      }
    }
    return nearest && nearest.dist <= 30 ? nearest.name : null
  },
},
```

#### 5.5.3 EntityForm template guard

In the parent template (likely `MapEditor.vue` or a layout component),
the EntityForm render must include the waypoint case:

```vue
<EntityForm
  v-if="entityFormOpen && entityFormType"
  :open="entityFormOpen"
  :type="entityFormType"
  :data="entityFormData"
  @save="onEntitySave"
  @cancel="entityFormOpen = false"
/>
```

The `entityFormType` is `'waypoint'` when set by `openWaypointForm()`,
and the EntityForm internally renders the waypoint sub-form (per Doc 11
§5 — already implemented).

If the EntityForm uses internal branching like:

```vue
<RoadForm v-if="type === 'road'" ... />
<WaypointForm v-if="type === 'waypoint'" ... />
```

…verify that `WaypointForm` is imported in the EntityForm component AND
that `WaypointForm` follows the field order from Doc 16 §5.4.2 (TIPO first,
NOME second, auto-focus on TIPO select).

---

## 6. Updated Workflows

The existing workflows (WF-01..WF-08) are unaffected. Three small behavior
changes:

| Workflow | Before this patch | After this patch |
|---|---|---|
| Find a specific road | Pan the map looking for it | Type its name in the Quick Select dropdown |
| Pan in Select mode | Impossible (drag was blocked) | Plain drag pans; CTRL+drag selects |
| Place a waypoint | Broken (form never opened) | Click Waypoint → click map → form opens with TIPO first |

---

## 7. Implementation Sequence

Single Stage 8, three sub-stages. Frontend-only. Quick to ship.

### Stage 8.A — Road Quick Select dropdown

1. Add `pendingFocusRoadId` state and `focusRoad`/`consumeFocusRoad`
   actions to `mapStore` per §5.2. (Optional — only needed if you want
   to decouple the map from RoadQuickSelect via state. The simpler
   alternative is the event-emit pattern in §5.3, which is what the
   reference code uses.)
2. Create `frontend/src/components/map/RoadQuickSelect.vue` per §5.1.
3. Import and place the component in the MapEditor toolbar per §5.3.1.
4. Add the `onRoadFromQuickSelect`, `onQuickSelectCleared`,
   `centerMapOnRoad`, and `openRoadPanel` methods to `MapEditor.vue`
   per §5.3.2.

**Quality gate**:

```bash
cd frontend
npm run build           # zero TypeScript errors
cd ..
uv run guardianmapstudio
```

Manual checks:

- [ ] Dropdown shows next to "⟲ Desfazer"
- [ ] Empty workspace → dropdown is disabled, placeholder "Nenhuma rua cadastrada"
- [ ] Workspace with roads → typing filters the datalist
- [ ] Clicking a road name in the datalist selects it on the map
- [ ] Map centers on the selected road
- [ ] Side panel opens with the road's data
- [ ] "×" clear button resets selection

Commit: `git commit -m "Stage 8.A — road quick select dropdown"`

### Stage 8.B — Rectangle selection requires CTRL

1. Replace `frontend/src/components/map/RectangleSelector.ts` per §5.4.
2. Add the status hint per §5.4.1 in MapEditor.vue.

**Quality gate**:

```bash
cd frontend && npm run build && cd ..
uv run guardianmapstudio
```

Manual checks:

- [ ] In Select mode, plain drag pans the map (does NOT draw rectangle)
- [ ] In Select mode, CTRL+drag draws the amber rectangle
- [ ] CTRL+drag selects all roads with at least one vertex inside
- [ ] Releasing CTRL mid-drag aborts the rectangle cleanly
- [ ] After mouseup, map dragging is re-enabled (try a normal pan)
- [ ] Status hint about CTRL appears in Select mode
- [ ] Status hint does NOT appear in Waypoint mode

Commit: `git commit -m "Stage 8.B — CTRL-gated rectangle selection"`

### Stage 8.C — Fix Waypoint button

1. Read `frontend/src/components/map/MapEditor.vue` and follow the
   6-step investigation in §5.5.1. Identify the broken link.
2. Apply only the parts of §5.5.2 that are missing or wrong. Do NOT
   rewrite the whole component — minimal diffs only.
3. If EntityForm renders sub-forms internally, verify per §5.5.3 that
   the waypoint case is handled.

**Quality gate**:

```bash
cd frontend && npm run build && cd ..
uv run guardianmapstudio
```

Manual checks:

- [ ] Click "Waypoint" toolbar button → cursor changes to crosshair
- [ ] DevTools console shows NO errors
- [ ] Click anywhere on the map → form opens (no missed clicks)
- [ ] Form shows TIPO as the first field, auto-focused
- [ ] Form shows NOME as the second field
- [ ] Selecting a TIPO reveals conditional fields (e.g. `height_cm` for
      speed_bump, `gate_type` for gate)
- [ ] Saving creates the waypoint, which appears on the map
- [ ] Cancelling closes the form without creating anything
- [ ] After saving, clicking another spot on the map opens a NEW form
      (not stale data from the previous one)

Commit: `git commit -m "Stage 8.C — fix waypoint click handler"`

### Stage 8.D — Smoke regression

Run all prior workflows to confirm nothing broke:

```bash
uv run pytest tests/ -v --cov=guardianmapstudio --cov-fail-under=80
uv run ruff check src/ tests/
uv run mypy src/
```

(Backend tests should be 100% green and unchanged since no backend
files were touched.)

Manual end-to-end:

- [ ] WF-05 (OSM import) still works
- [ ] WF-06 (merge duplicates) still works
- [ ] WF-07 (rectangle delete) still works — now via CTRL+drag
- [ ] WF-08 (undo) still works
- [ ] Publish + Export still produces valid JSON
- [ ] `"restricted_areas": []` still present in exported JSON

---

## 8. Acceptance Criteria

### Road Quick Select

- [ ] Dropdown is positioned immediately LEFT of the "⟲ Desfazer" button
- [ ] Dropdown is disabled when workspace has zero roads
- [ ] Datalist contains every road in the workspace, alphabetically sorted
- [ ] Sorting respects Brazilian Portuguese locale (e.g. "São" sorts naturally)
- [ ] Selecting a road highlights it on the map (amber, same as click)
- [ ] Selecting a road centers the map on its bounding box with padding
- [ ] Selecting a road opens the side panel with that road's data
- [ ] "×" clear button resets the input AND clears map selection
- [ ] Typing a partial name filters the dropdown (native datalist behavior)
- [ ] Typing a name that does NOT exist does nothing (no error, no alert)
- [ ] Dropdown updates when roads are added (via OSM import or merge)
- [ ] Dropdown updates when roads are deleted

### Rectangle selection with CTRL

- [ ] In Select mode, plain drag pans the map
- [ ] In Select mode, CTRL+drag (or Cmd+drag on macOS) draws amber rectangle
- [ ] CTRL+drag selects all roads with at least one vertex inside bounds
- [ ] Multi-selection shows status text (not the form), per Doc 16 §5.8
- [ ] Pressing DELETE with multi-selection opens bulk confirmation modal
- [ ] Releasing CTRL mid-drag aborts the rectangle cleanly (no orphan layer)
- [ ] After any rectangle operation, map dragging is fully re-enabled
- [ ] Status hint "💡 Clique numa rua... CTRL+arrastar..." visible in Select mode
- [ ] Status hint disappears in other modes
- [ ] Switching away from Select mode tears down all rectangle handlers
- [ ] Clicking on a road (without CTRL) still selects it (existing behavior)

### Waypoint button fix

- [ ] Clicking "Waypoint" toolbar button visibly activates the mode (cursor change)
- [ ] DevTools console shows ZERO errors after clicking the button
- [ ] Clicking the map in Waypoint mode opens the form on EVERY click
- [ ] Form fields appear in order: Tipo, Nome, Conditional, Rua, Posição
- [ ] TIPO select is auto-focused on form open
- [ ] Selecting `speed_bump` reveals `height_cm` field with required validation
- [ ] Selecting `gate` reveals `gate_type` select with required validation
- [ ] Selecting `stop_sign` reveals `heading_degrees` field (optional)
- [ ] Submitting the form creates the waypoint via POST /waypoints
- [ ] The new waypoint marker appears on the map immediately
- [ ] Cancelling the form does not create a waypoint
- [ ] After saving, clicking another spot opens a NEW form with TIPO empty
      (not stale data)
- [ ] If `road_name` was guessed from a nearby road (<30m), it pre-fills
      the Rua select

### Regression

- [ ] All backend tests still pass (no backend code changed)
- [ ] `npm run build` produces zero TypeScript errors
- [ ] `ruff check` zero warnings
- [ ] `mypy --strict` zero errors
- [ ] All MVP01 + Doc 15 + Doc 16 workflows still complete end-to-end
- [ ] Export JSON unchanged in shape (`restricted_areas: []` still present)
- [ ] 11-tables database invariant still holds

---

## 9. Out of Scope (Future Work)

| Feature | Status | Why deferred |
|---|---|---|
| Quick Select for waypoints / crossroads / areas | MVP02 | User requested roads only; mixed-type search needs separate design |
| Fuzzy search (e.g. "rsao" matches "Rua São") | MVP02 | Native datalist does prefix-match; fuzzy needs a JS lib (fuse.js) |
| Recent roads history in the dropdown | MVP02 | Nice-to-have; not requested |
| Keyboard shortcut to focus the Quick Select (e.g. `/`) | MVP02 | Easy add but not requested |
| Visual rectangle handle / corner-drag to resize selection | MVP02 | Current rectangle is fire-and-forget; advanced UX |
| Shift+click for additive selection (add a road to current selection) | MVP02 (was noted as optional polish in Doc 16) | Not requested explicitly |
| Right-click context menu on roads | MVP03 | Bigger UX redesign |

---

## 10. Notes for Reviewers

1. **Why `<input list>` over a select**: see ADR-17-01. Native HTML5,
   zero deps, scales to hundreds of options, has search for free. A
   `<select>` works fine for ≤30 entries but degrades badly above that
   threshold — and OSM imports of medium condominiums regularly produce
   80–150 roads.

2. **Why CTRL not SHIFT**: SHIFT in many Leaflet plugins means
   "add-to-current-selection". CTRL is more idiomatic for "alternate
   mode of the drag gesture" (Figma marquee select, Photoshop selection
   tools). Also, SHIFT+click is reserved for the future additive-selection
   feature (Doc 16 §9, optional polish).

3. **Why the waypoint bug is fixed by investigation + reference, not by
   handing over a full diff**: I don't have access to the running
   MapEditor.vue, so I cannot know which specific link in the chain is
   broken. A blind rewrite risks breaking the road-mode handler or the
   click-to-select-road logic. The 6-step investigation in §5.5.1 makes
   the failure mode explicit so the fix is targeted.

4. **Why we don't add a unit test for the dropdown or rectangle**:
   the MVP01 codebase has no frontend test infrastructure (per Doc 06,
   only backend tests are required at 80% coverage). Setting up Vitest +
   Vue Test Utils for three small components would be a larger scope
   change than the patch itself. Manual checklists in §7 cover acceptance.
