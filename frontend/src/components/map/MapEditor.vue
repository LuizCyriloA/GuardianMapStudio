<template>
  <div style="flex:1;position:relative;display:flex;flex-direction:column;min-height:0;">
    <!-- Toolbar -->
    <div style="background:#1e293b;padding:6px 12px;display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
      <button @click="setMode('select')" :style="toolBtn(drawingMode === 'select')">▶ Selecionar</button>
      <button @click="setMode('waypoint')" :style="toolBtn(drawingMode === 'waypoint')">📍 Waypoint</button>
      <button
        :style="draftBtnStyle('#0f6bb5')"
        :disabled="!isDraft"
        :title="isDraft ? 'Detectar cruzamentos em X e T automaticamente' : 'Disponível apenas em rascunho'"
        @click="onDetectCrossroads"
      >🔍 Detectar cruzamentos</button>
      <button
        :style="draftBtnStyle('#0f766e')"
        :disabled="!isDraft"
        :title="isDraft ? 'Importar ruas do OpenStreetMap' : 'Disponível apenas em rascunho'"
        @click="osmImportOpen = true"
      >📥 Importar OSM</button>
      <button
        :style="draftBtnStyle('#7c3aed')"
        :disabled="!isDraft"
        :title="isDraft ? 'Mesclar ruas duplicadas' : 'Disponível apenas em rascunho'"
        @click="mergeOpen = true"
      >⤢ Mesclar duplicadas</button>
      <button
        :style="toolBtn(false)"
        title="Centralizar mapa nas entidades"
        @click="recenterOnEntities"
      >🎯 Centralizar</button>
      <RoadQuickSelect
        @road-selected="onRoadFromQuickSelect"
        @selection-cleared="onQuickSelectCleared"
      />
      <button
        :style="undoBtnStyle"
        :disabled="!canUndo"
        :title="canUndo ? undoLabel : 'Nada para desfazer'"
        @click="triggerUndo"
      >⟲ Desfazer</button>
    </div>

    <!-- Select-mode hint (Stage 8.B — shown only in select mode) -->
    <div v-if="drawingMode === 'select'" class="select-mode-hint">
      💡 Clique numa rua para selecionar.
      Mantenha <kbd>CTRL</kbd> e arraste para selecionar várias.
    </div>

    <!-- Waypoint-mode hint -->
    <div v-if="drawingMode === 'waypoint'" class="select-mode-hint">
      📍 Clique no mapa para posicionar o waypoint.
    </div>

    <!-- Bulk selection status bar -->
    <div v-if="bulkStatus"
      style="background:#1e3a5f;color:#93c5fd;font-size:12px;padding:4px 12px;border-bottom:1px solid #1d4ed8;">
      {{ bulkStatus }}
    </div>

    <!-- Map container — NEVER v-if, always present -->
    <div id="guardian-map" style="flex:1;min-height:0;"></div>

    <!-- Road info footer — shown when a single road is selected in select mode -->
    <transition name="slide-footer">
      <div v-if="selectedRoad && drawingMode === 'select'" class="road-footer">
        <div class="road-footer-info">
          <span class="road-footer-name">{{ selectedRoad.name }}</span>
          <span class="road-footer-detail">{{ selectedRoad.speed_limit_kmh }} km/h</span>
          <span class="road-footer-detail">{{ selectedRoad.direction === 'two_way' ? 'Mão dupla' : 'Mão única' }}</span>
          <span class="road-footer-detail">{{ selectedRoad.width_meters }}m</span>
        </div>
        <div class="road-footer-shortcuts">
          <kbd>P</kbd>
          <span class="road-footer-shortcut-label">{{ pareStateLabel }}</span>
        </div>
        <button class="road-footer-delete" @click="onFooterDelete">🗑 Excluir rua</button>
      </div>
    </transition>

    <!-- Snap indicator tooltip -->
    <div v-if="snapMsg" style="position:absolute;bottom:8px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,.7);color:#fff;padding:4px 12px;border-radius:12px;font-size:12px;pointer-events:none;z-index:1000;">
      {{ snapMsg }}
    </div>

    <!-- OSM Import Modal -->
    <OsmImportModal
      v-if="osmImportOpen && workspaceId !== null"
      :workspace-id="workspaceId"
      :visible="osmImportOpen"
      @close="osmImportOpen = false"
      @imported="onOsmImported"
    />

    <!-- Merge Roads Modal -->
    <MergeRoadsModal
      v-if="mergeOpen && workspaceId !== null"
      :workspace-id="workspaceId"
      :visible="mergeOpen"
      @close="mergeOpen = false"
      @merged="onMerged"
    />

    <!-- Confirm delete modal -->
    <ConfirmModal
      :visible="confirmModal.visible"
      :title="confirmModal.title"
      :message="confirmModal.message"
      :items="confirmModal.items"
      @confirm="confirmModal.onConfirm()"
      @cancel="confirmModal.visible = false"
    />
  </div>
</template>

<script lang="ts">
import { defineComponent, watch } from 'vue'
import L from 'leaflet'
import { useMapStore } from '../../stores/map'
import { useWorkspaceStore } from '../../stores/workspace'
import { useUndoStore } from '../../stores/undo'
import { api } from '../../api/client'
import OsmImportModal from './OsmImportModal.vue'
import MergeRoadsModal from './MergeRoadsModal.vue'
import ConfirmModal from '../common/ConfirmModal.vue'
import RoadQuickSelect from './RoadQuickSelect.vue'
import { CompassControl } from './CompassControl'
import { attachRectangleSelector } from './RectangleSelector'
import type { RoadResponse, GeoPoint } from '../../api/types'

// ── Waypoint icon config ────────────────────────────────────────────────────
const WAYPOINT_ICON_CFG: Record<string, { letter: string; color: string }> = {
  stop_sign:  { letter: 'P', color: '#E24B4A' },
  speed_bump: { letter: 'L', color: '#EF9F27' },
  gate:       { letter: 'G', color: '#1D9E75' },
  curve:      { letter: 'C', color: '#888780' },
  landmark:   { letter: 'M', color: '#534AB7' },
  stop_zone:  { letter: 'S', color: '#378ADD' },
  crossroad:  { letter: 'X', color: '#888780' },
}

const ROAD_COLORS: Record<string, string> = {
  two_way: '#378ADD',
  one_way: '#ff7800',
}

const SELECTED_ROAD_COLOR = '#FFB400'
const SELECTED_ROAD_WEIGHT = 6

const AREA_COLORS: Record<string, string> = {
  speed_limit:     '#ffcc00',
  no_entry:        '#ff4444',
  pedestrian_only: '#44ff44',
}

// Scale factor relative to zoom 18 (the typical editing zoom).
// Each Leaflet zoom step doubles the map scale; we apply a dampened factor (0.7)
// so icons grow/shrink more gradually than the map tiles.
function iconZoomScale(zoom: number): number {
  return Math.min(2.0, Math.max(0.4, Math.pow(2, (zoom - 18) * 0.7)))
}

function makeWaypointIcon(type: string, heading?: number | null, zoom = 18): L.DivIcon {
  const s = iconZoomScale(zoom)
  const cfg = WAYPOINT_ICON_CFG[type] ?? { letter: '?', color: '#888' }
  const sz = Math.round(24 * s)
  const fs = Math.round(13 * s)
  const circle = `<div style="width:${sz}px;height:${sz}px;border-radius:50%;background:${cfg.color};color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:${fs}px;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.4);">${cfg.letter}</div>`
  if (type === 'stop_sign' && heading != null) {
    // Unrotated icon coordinate system (anchor = center-top = road endpoint):
    //   x < cx  → left lane   (no marking)
    //   x > cx  → right lane  (rectangle) and curb (P circle, outside road)
    //   y > 0   → into the road (anti-heading direction on map after rotation)
    //
    // KEY: the rectangle must be TALLER than it is wide so that after rotating
    // by heading its LONG axis aligns WITH the road direction (parallel to road).
    //   rH (tall) = along-road dimension  → parallel to road after rotation ✓
    //   rW (narrow) = cross-road dimension → half-lane width after rotation ✓
    //
    // CSS rotation formula (CW, y-down screen):
    //   new_screen_dx = dx·cos(θ) − dy·sin(θ)
    //   new_screen_dy = dx·sin(θ) + dy·cos(θ)
    // So "down in icon" (dy>0) → anti-heading on map ✓
    //    "right in icon" (dx>0) → right-of-road on map ✓
    const W   = Math.round(40 * s)   // container width
    const H   = Math.round(20 * s)   // container height
    const cx  = Math.round(20 * s)   // anchor x = road centreline
    const cSz = Math.round(17 * s)   // P circle diameter
    const cFs = Math.round(10 * s)   // P circle font
    const pL  = Math.round(22 * s)   // P left  (right of road centre)
    const pT  = 0                    // P top   (at anchor/endpoint level)
    const rW  = Math.round(6  * s)   // rectangle narrow side (cross-road, ≈ half lane)
    const rH  = Math.round(16 * s)   // rectangle tall  side  (along-road → parallel)
    const rT  = Math.round(2  * s)   // rectangle top offset  (slight depth into road)
    return L.divIcon({
      html: `<div style="position:relative;width:${W}px;height:${H}px;transform:rotate(${heading}deg);transform-origin:${cx}px 0;overflow:visible;"><div style="position:absolute;left:${pL}px;top:${pT}px;width:${cSz}px;height:${cSz}px;border-radius:50%;background:${cfg.color};color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:${cFs}px;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.4);transform:rotate(${-heading}deg);">P</div><div style="position:absolute;left:${cx}px;top:${rT}px;width:${rW}px;height:${rH}px;background:${cfg.color};border-radius:2px;"></div></div>`,
      className: '',
      iconSize: [W, H],
      iconAnchor: [cx, 0],
      popupAnchor: [Math.round(8 * s), Math.round(10 * s)],
    })
  }
  return L.divIcon({
    html: circle,
    className: '',
    iconSize: [sz, sz],
    iconAnchor: [Math.round(sz / 2), Math.round(sz / 2)],
    popupAnchor: [0, -14],
  })
}

export default defineComponent({
  name: 'MapEditor',
  components: { OsmImportModal, MergeRoadsModal, ConfirmModal, RoadQuickSelect },
  emits: ['entity-form', 'entity-selected'],

  data() {
    return {
      osmImportOpen: false,
      mergeOpen: false,
      // Leaflet objects typed as any — Vue's reactive proxy breaks L.* types
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      map: null as any,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      roadsLayer: null as any,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      waypointsLayer: null as any,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      crossroadsLayer: null as any,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      areasLayer: null as any,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      validationLayer: null as any,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      drawLayer: null as any,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      previewPolyline: null as any,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      snapIndicator: null as any,
      // Road id → Leaflet polyline (for in-place style updates without re-render)
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      roadLayerIndex: {} as Record<number, any>,

      drawingMode: 'select' as 'select' | 'road' | 'waypoint' | 'area',
      vertices: [] as L.LatLng[],
      snapMsg: '',
      bulkStatus: '',

      pendingRoadCoords: [] as GeoPoint[],
      pendingAreaCoords: [] as GeoPoint[],

      rectangleTeardown: null as (() => void) | null,

      // Road footer + P-key state
      selectedRoad: null as RoadResponse | null,
      pareState: 0 as 0 | 1 | 2 | 3,  // 0=none, 1=both, 2=start-only, 3=end-only

      confirmModal: {
        visible: false,
        title: '',
        message: '',
        items: [] as string[],
        onConfirm: () => {},
      },
    }
  },

  computed: {
    isDraft(): boolean {
      return useWorkspaceStore().isDraft ?? false
    },
    workspaceId(): number | null {
      return useWorkspaceStore().workspace?.id ?? null
    },
    canUndo(): boolean {
      return useUndoStore().canUndo
    },
    undoLabel(): string {
      return useUndoStore().lastActionLabel
    },
    pareStateLabel(): string {
      const isOneWay = this.selectedRoad?.direction === 'one_way'
      const labels: Record<number, string> = isOneWay
        ? { 0: 'Adicionar PARE', 3: '✓ PARE no fim  →  P: remover' }
        : {
            0: 'Adicionar PARE',
            1: '✓ PARE em ambas  →  P: só início',
            2: '✓ PARE no início  →  P: só fim',
            3: '✓ PARE no fim  →  P: remover',
          }
      return labels[this.pareState] ?? 'Adicionar PARE'
    },
    undoBtnStyle(): Record<string, string> {
      const can = this.canUndo
      return {
        padding: '4px 12px',
        background: can ? '#374151' : '#334155',
        color: can ? '#e2e8f0' : '#6b7280',
        border: can ? '1px solid #4b5563' : 'none',
        borderRadius: '4px',
        cursor: can ? 'pointer' : 'not-allowed',
        fontSize: '12px',
      }
    },
  },

  watch: {
    drawingMode(newMode: string, oldMode: string) {
      if (oldMode === 'select' && this.rectangleTeardown) {
        this.rectangleTeardown()
        this.rectangleTeardown = null
      }
      if (newMode === 'select' && this.map) {
        this.rectangleTeardown = attachRectangleSelector(this.map, {
          onSelect: (bounds) => this.selectRoadsInBounds(bounds),
        })
      }
    },
  },

  mounted() {
    this.$nextTick(() => { this.initMap() })
    document.addEventListener('keydown', this.onKeyDown)
  },

  beforeUnmount() {
    document.removeEventListener('keydown', this.onKeyDown)
    if (this.rectangleTeardown) this.rectangleTeardown()
    if (this.map) { this.map.remove(); this.map = null }
  },

  methods: {
    // ── Map initialization ─────────────────────────────────────────────────

    initMap() {
      const mapStore = useMapStore()
      const centerLat = mapStore.roads[0]?.coordinates[0]?.lat ?? -15.78
      const centerLng = mapStore.roads[0]?.coordinates[0]?.lng ?? -47.93

      this.map = L.map('guardian-map', {
        center: [centerLat, centerLng],
        zoom: mapStore.roads.length > 0 ? 18 : 5,
        doubleClickZoom: false,
      })

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 22,
      }).addTo(this.map)

      new CompassControl().addTo(this.map)

      this.roadsLayer      = L.layerGroup().addTo(this.map)
      this.waypointsLayer  = L.layerGroup().addTo(this.map)
      this.crossroadsLayer = L.layerGroup().addTo(this.map)
      this.areasLayer      = L.layerGroup().addTo(this.map)
      this.validationLayer = L.layerGroup().addTo(this.map)
      this.drawLayer       = L.layerGroup().addTo(this.map)

      this.map.on('click', this.onMapClick)
      this.map.on('dblclick', this.onMapDblClick)
      this.map.on('mousemove', this.onMapMouseMove)
      this.map.on('zoomend', () => this.renderWaypoints())

      this.renderAll()
      this.$nextTick(() => this.recenterOnEntities())

      this.rectangleTeardown = attachRectangleSelector(this.map, {
        onSelect: (bounds) => this.selectRoadsInBounds(bounds),
      })

      const store = useMapStore()
      watch(() => store.roads, () => this.renderRoads(), { deep: true })
      watch(() => store.waypoints, () => this.renderWaypoints(), { deep: true })
      watch(() => store.crossroads, () => this.renderCrossroads(), { deep: true })
      watch(() => store.restrictedAreas, () => this.renderAreas(), { deep: true })
      watch(() => useWorkspaceStore().validation, () => this.renderValidation(), { deep: true })
      watch(() => store.selectedEntityId, () => this.panToSelected())
      watch(() => store.recenterSignal, () => this.recenterOnEntities())
    },

    invalidateSize() {
      this.map?.invalidateSize()
    },

    // ── Re-center (§5.2) ──────────────────────────────────────────────────

    recenterOnEntities() {
      if (!this.map) return
      const store = useMapStore()
      const bounds = L.latLngBounds([])
      for (const road of store.roads) {
        for (const pt of road.coordinates) bounds.extend([pt.lat, pt.lng])
      }
      for (const wp of store.waypoints) bounds.extend([wp.lat, wp.lng])
      for (const cr of store.crossroads) bounds.extend([cr.lat, cr.lng])
      for (const area of store.restrictedAreas) {
        for (const pt of area.polygon) bounds.extend([pt.lat, pt.lng])
      }
      if (bounds.isValid()) {
        this.map.fitBounds(bounds, { padding: [40, 40], maxZoom: 19 })
      } else {
        this.map.setView([-15.78, -47.93], 5)
      }
    },

    // ── Mode & drawing ────────────────────────────────────────────────────

    setMode(mode: 'select' | 'road' | 'waypoint' | 'area') {
      this.cancelDrawing()
      this.drawingMode = mode
      if (this.map) {
        const container = this.map.getContainer()
        if (mode === 'select') {
          container.classList.remove('gms-drawing-mode')
          container.style.removeProperty('cursor')
        } else {
          // Leaflet applies `cursor: grab !important` via `.leaflet-grab`.
          // Inline style setProperty with 'important' is silently ignored for
          // inline styles per spec. Instead we add a class whose rule in the
          // stylesheet wins by being declared later (both !important, last wins).
          container.classList.add('gms-drawing-mode')
        }
      }
    },

    cancelDrawing() {
      this.vertices = []
      this.pendingRoadCoords = []
      this.pendingAreaCoords = []
      if (this.previewPolyline) { this.previewPolyline.remove(); this.previewPolyline = null }
      if (this.snapIndicator)  { this.snapIndicator.remove();  this.snapIndicator = null }
      this.drawLayer?.clearLayers()
    },

    onMapClick(e: L.LeafletMouseEvent) {
      const { lat, lng } = e.latlng

      if (this.drawingMode === 'select') {
        useMapStore().clearRoadSelection()
        this.refreshRoadStyles()
        this.bulkStatus = ''
        this.selectedRoad = null
        this.pareState = 0
        this.$emit('entity-form', { entityType: '', initialData: {} })
        return
      }

      if (this.drawingMode === 'road') {
        this.vertices.push(e.latlng)
        this.updatePreviewPolyline()
      } else if (this.drawingMode === 'waypoint') {
        this.openWaypointForm(e.latlng)
      } else if (this.drawingMode === 'area') {
        this.vertices.push(e.latlng)
        this.updatePreviewPolygon()
      }
    },

    onMapDblClick(e: L.LeafletMouseEvent) {
      if (this.drawingMode === 'road' && this.vertices.length >= 2) {
        const coords: GeoPoint[] = this.vertices.map(v => ({ lat: v.lat, lng: v.lng }))
        this.cancelDrawing()
        this.setMode('select')
        this.$emit('entity-form', {
          entityType: 'road',
          initialData: {
            name: `Rua ${Date.now().toString().slice(-4)}`,
            coordinates: coords,
            speed_limit_kmh: 20,
            direction: 'two_way',
            width_meters: 6.0,
          },
        })
      } else if (this.drawingMode === 'area' && this.vertices.length >= 3) {
        const polygon: GeoPoint[] = this.vertices.map(v => ({ lat: v.lat, lng: v.lng }))
        this.cancelDrawing()
        this.setMode('select')
        this.$emit('entity-form', {
          entityType: 'restricted_area',
          initialData: {
            name: `Área ${Date.now().toString().slice(-4)}`,
            polygon,
            restriction_type: 'no_entry',
          },
        })
      }
    },

    async onMapMouseMove(e: L.LeafletMouseEvent) {
      if (this.drawingMode !== 'waypoint' && this.drawingMode !== 'road') {
        this.snapMsg = ''
        return
      }
      const wsStore = useWorkspaceStore()
      if (!wsStore.workspace) return
      try {
        const res = await api.snap(wsStore.workspace.id, e.latlng.lat, e.latlng.lng)
        if (res.snapped) {
          this.snapMsg = `Snap: ${res.distance_meters.toFixed(2)}m`
          if (!this.snapIndicator) {
            this.snapIndicator = L.circleMarker(
              [res.snapped_to.lat, res.snapped_to.lng],
              { radius: 8, color: '#2563eb', fillColor: '#2563eb', fillOpacity: 0.5 }
            ).addTo(this.map!)
          } else {
            this.snapIndicator.setLatLng([res.snapped_to.lat, res.snapped_to.lng])
          }
        } else {
          this.snapMsg = ''
          if (this.snapIndicator) { this.snapIndicator.remove(); this.snapIndicator = null }
        }
      } catch { /* Snap errors are non-critical */ }
    },

    updatePreviewPolyline() {
      if (!this.map) return
      if (this.previewPolyline) this.previewPolyline.remove()
      if (this.vertices.length < 2) return
      this.previewPolyline = L.polyline(this.vertices, {
        color: '#378ADD', weight: 3, dashArray: '6 4', opacity: 0.7,
      }).addTo(this.map)
    },

    updatePreviewPolygon() {
      if (!this.map) return
      this.drawLayer?.clearLayers()
      if (this.vertices.length < 2) return
      L.polyline([...this.vertices, this.vertices[0]], {
        color: '#EF9F27', weight: 2, dashArray: '6 4',
      }).addTo(this.drawLayer!)
    },

    // ── Road selection (§5.5) ──────────────────────────────────────────────

    onRoadClick(road: RoadResponse) {
      if (this.drawingMode !== 'select') return
      if (this.selectedRoad?.id !== road.id) this.pareState = 0
      this.selectedRoad = road
      useMapStore().selectRoad(road.id)
      this.refreshRoadStyles()
      this.bulkStatus = ''
      this.$emit('entity-form', { entityType: 'road', initialData: { ...road } })
    },

    refreshRoadStyles() {
      const store = useMapStore()
      for (const [idStr, layer] of Object.entries(this.roadLayerIndex)) {
        const id = Number(idStr)
        const road = store.roads.find(r => r.id === id)
        if (!road) continue
        const selected = store.isRoadSelected(id)
        layer.setStyle({
          color: selected ? SELECTED_ROAD_COLOR : (ROAD_COLORS[road.direction] ?? '#378ADD'),
          weight: selected ? SELECTED_ROAD_WEIGHT : 4,
        })
      }
    },

    selectRoadsInBounds(bounds: L.LatLngBounds) {
      const store = useMapStore()
      const selectedIds: number[] = []
      for (const road of store.roads) {
        const hit = road.coordinates.some(p =>
          bounds.contains([p.lat, p.lng] as L.LatLngExpression)
        )
        if (hit) selectedIds.push(road.id)
      }
      store.selectRoads(selectedIds)
      this.refreshRoadStyles()

      if (selectedIds.length > 1) {
        this.bulkStatus = `${selectedIds.length} ruas selecionadas. Pressione Delete para excluir todas.`
        this.$emit('entity-form', { entityType: '', initialData: {} })
      } else if (selectedIds.length === 1) {
        this.bulkStatus = ''
        const road = store.roads.find(r => r.id === selectedIds[0])
        if (road) this.$emit('entity-form', { entityType: 'road', initialData: { ...road } })
      } else {
        this.bulkStatus = ''
      }
    },

    // ── Keyboard (§5.7 + §5.9) ─────────────────────────────────────────────

    async onKeyDown(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement).tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
      if ((e.key === 'p' || e.key === 'P') && !e.ctrlKey && !e.metaKey) {
        if (this.selectedRoad && useMapStore().selectedRoadIds.length === 1) {
          e.preventDefault()
          await this.cyclePareState()
        }
      }
      if (e.key === 'Delete' || e.key === 'Backspace') {
        if (useMapStore().selectedRoadIds.length > 0) {
          e.preventDefault()
          this.openDeleteConfirm()
        }
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
        e.preventDefault()
        useUndoStore().undoLast()
      }
    },

    openDeleteConfirm() {
      const store = useMapStore()
      const ids = store.selectedRoadIds
      const names = ids
        .map(id => store.roads.find(r => r.id === id)?.name)
        .filter(Boolean) as string[]
      this.confirmModal = {
        visible: true,
        title: ids.length === 1 ? 'Excluir rua?' : `Excluir ${ids.length} ruas?`,
        message: ids.length === 1
          ? 'Esta ação removerá a rua selecionada do rascunho.'
          : `Esta ação removerá ${ids.length} ruas do rascunho.`,
        items: names,
        onConfirm: () => this.performDelete([...ids]),
      }
    },

    async performDelete(ids: number[]) {
      this.confirmModal.visible = false
      const store = useMapStore()
      const restoreEntries: RoadResponse[] = ids
        .map(id => store.roads.find(r => r.id === id))
        .filter(Boolean) as RoadResponse[]
      try {
        for (const id of ids) await store.deleteRoad(id)
        useUndoStore().push({ type: 'delete_roads', roads: restoreEntries, timestamp: Date.now() })
        store.clearRoadSelection()
        this.bulkStatus = ''
        this.refreshRoadStyles()
      } catch (e: unknown) {
        alert(e instanceof Error ? e.message : 'Falha ao excluir')
      }
    },

    triggerUndo() {
      useUndoStore().undoLast()
    },

    // ── OSM / Merge events ──────────────────────────────────────────────────

    onOsmImported() {
      this.osmImportOpen = false
    },

    onMerged() {
      this.mergeOpen = false
    },

    // ── Render ─────────────────────────────────────────────────────────────

    renderAll() {
      this.renderRoads()
      this.renderWaypoints()
      this.renderCrossroads()
      this.renderAreas()
      this.renderValidation()
    },

    renderRoads() {
      if (!this.roadsLayer) return
      this.roadsLayer.clearLayers()
      this.roadLayerIndex = {}
      const store = useMapStore()
      for (const road of store.roads) {
        if (road.coordinates.length < 2) continue
        const lls = road.coordinates.map(c => [c.lat, c.lng] as [number, number])
        const selected = store.isRoadSelected(road.id)
        const color = selected ? SELECTED_ROAD_COLOR : (ROAD_COLORS[road.direction] ?? '#378ADD')
        const weight = selected ? SELECTED_ROAD_WEIGHT : 4
        const line = L.polyline(lls, { color, weight, opacity: 0.9 })
        line.on('click', (e) => {
          // In non-select modes (e.g. waypoint) let the event bubble to the
          // map so onMapClick can handle it for the active mode.
          if (this.drawingMode !== 'select') return
          L.DomEvent.stopPropagation(e)
          this.onRoadClick(road)
        })
        line.addTo(this.roadsLayer)
        this.roadLayerIndex[road.id] = line
      }
    },

    renderWaypoints() {
      if (!this.waypointsLayer) return
      this.waypointsLayer.clearLayers()
      const store = useMapStore()
      for (const wp of store.waypoints) {
        if (!wp.active) continue
        const icon = makeWaypointIcon(wp.waypoint_type, wp.heading_degrees, this.map?.getZoom() ?? 18)
        const m = L.marker([wp.lat, wp.lng], { icon })
        m.bindPopup(`
          <b>${wp.name}</b><br>
          <span style="color:#64748b;font-size:12px;">${wp.waypoint_type}</span>
          ${wp.road_name ? `<br>📍 ${wp.road_name}` : ''}<br>
          <button onclick="window.guardianApp.deleteEntity('waypoint', ${wp.id})"
            style="margin-top:6px;padding:3px 10px;background:#dc2626;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px;">
            Excluir
          </button>
        `)
        m.addTo(this.waypointsLayer)
      }
    },

    renderCrossroads() {
      if (!this.crossroadsLayer) return
      this.crossroadsLayer.clearLayers()
      const store = useMapStore()
      for (const cr of store.crossroads) {
        const m = L.circleMarker([cr.lat, cr.lng], {
          radius: 8, color: '#334155', fillColor: '#fff', fillOpacity: 1, weight: 2,
        })
        m.bindPopup(`
          <b>Cruzamento</b><br>
          ${cr.road_a_name} × ${cr.road_b_name}<br>
          <button onclick="window.guardianApp.deleteEntity('crossroad', ${cr.id})"
            style="margin-top:6px;padding:3px 10px;background:#dc2626;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px;">
            Excluir
          </button>
        `)
        m.addTo(this.crossroadsLayer)
      }
    },

    renderAreas() {
      if (!this.areasLayer) return
      this.areasLayer.clearLayers()
      const store = useMapStore()
      for (const area of store.restrictedAreas) {
        if (area.polygon.length < 3) continue
        const lls = area.polygon.map(p => [p.lat, p.lng] as [number, number])
        const fillColor = AREA_COLORS[area.restriction_type] ?? '#888888'
        const poly = L.polygon(lls, { color: fillColor, fillColor, fillOpacity: 0.2, weight: 2 })
        poly.bindPopup(`
          <b>${area.name}</b><br>
          ${area.restriction_type}
          ${area.speed_limit_kmh ? ` · ${area.speed_limit_kmh} km/h` : ''}<br>
          <button onclick="window.guardianApp.deleteEntity('restricted_area', ${area.id})"
            style="margin-top:6px;padding:3px 10px;background:#dc2626;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px;">
            Excluir
          </button>
        `)
        poly.addTo(this.areasLayer)
      }
    },

    renderValidation() {
      if (!this.validationLayer) return
      this.validationLayer.clearLayers()
      const ws = useWorkspaceStore()
      const store = useMapStore()
      if (!ws.validation) return

      const entityPos = (type: string, id: number): [number, number] | null => {
        if (type === 'road') {
          const r = store.roads.find(r => r.id === id)
          if (r?.coordinates[0]) return [r.coordinates[0].lat, r.coordinates[0].lng]
        } else if (type === 'waypoint') {
          const w = store.waypoints.find(w => w.id === id)
          if (w) return [w.lat, w.lng]
        } else if (type === 'crossroad') {
          const c = store.crossroads.find(c => c.id === id)
          if (c) return [c.lat, c.lng]
        } else if (type === 'restricted_area') {
          const a = store.restrictedAreas.find(a => a.id === id)
          if (a?.polygon[0]) return [a.polygon[0].lat, a.polygon[0].lng]
        }
        return null
      }

      for (const r of ws.validation.results) {
        const pos = entityPos(r.affected_entity_type, r.affected_entity_id)
        if (!pos) continue
        const color = r.severity === 'error' ? '#dc2626' : '#d97706'
        const m = L.circleMarker(pos, { radius: 10, color, fillColor: color, fillOpacity: 0.35, weight: 2 })
        m.bindPopup(`<b style="color:${color}">${r.severity.toUpperCase()}</b><br><small>${r.rule_id}</small><br>${r.message}`)
        m.addTo(this.validationLayer!)
      }
    },

    panToSelected() {
      const store = useMapStore()
      if (!store.selectedEntityId || !store.selectedEntityType || !this.map) return
      const { selectedEntityId: id, selectedEntityType: type } = store
      let pos: [number, number] | null = null
      if (type === 'road') {
        const r = store.roads.find(r => r.id === id)
        if (r?.coordinates[0]) pos = [r.coordinates[0].lat, r.coordinates[0].lng]
      } else if (type === 'waypoint') {
        const w = store.waypoints.find(w => w.id === id)
        if (w) pos = [w.lat, w.lng]
      } else if (type === 'crossroad') {
        const c = store.crossroads.find(c => c.id === id)
        if (c) pos = [c.lat, c.lng]
      } else if (type === 'restricted_area') {
        const a = store.restrictedAreas.find(a => a.id === id)
        if (a?.polygon[0]) pos = [a.polygon[0].lat, a.polygon[0].lng]
      }
      if (pos) this.map.panTo(pos)
    },

    // ── Waypoint form (Stage 8.C §5.5.2) ──────────────────────────────────

    openWaypointForm(latlng: L.LatLng) {
      // Force EntityForm to re-mount even if already open with stale data
      // (race-condition fix: false → nextTick → true re-triggers v-if).
      this.$emit('entity-form', { entityType: '', initialData: {} })
      this.$nextTick(() => {
        this.$emit('entity-form', {
          entityType: 'waypoint',
          initialData: {
            lat: latlng.lat,
            lng: latlng.lng,
            waypoint_type: '',
            name: '',
            road_name: this.guessNearestRoadName(latlng) ?? '',
            heading_degrees: null,
          },
        })
      })
    },

    guessNearestRoadName(latlng: L.LatLng): string | null {
      // O(N*M) nearest-vertex scan. Acceptable for ≤500 entities in MVP.
      // Returns null if no road vertex is within ~30 m of the click.
      let nearest: { name: string; dist: number } | null = null
      for (const road of useMapStore().roads) {
        for (const pt of road.coordinates) {
          const d = latlng.distanceTo([pt.lat, pt.lng])
          if (!nearest || d < nearest.dist) {
            nearest = { name: road.name, dist: d }
          }
        }
      }
      return nearest && nearest.dist <= 30 ? nearest.name : null
    },

    // ── P key — stop sign cycling ──────────────────────────────────────────

    calcBearing(from: GeoPoint, to: GeoPoint): number {
      const toRad = (d: number) => d * Math.PI / 180
      const φ1 = toRad(from.lat), φ2 = toRad(to.lat)
      const Δλ = toRad(to.lng - from.lng)
      const y = Math.sin(Δλ) * Math.cos(φ2)
      const x = Math.cos(φ1) * Math.sin(φ2) - Math.sin(φ1) * Math.cos(φ2) * Math.cos(Δλ)
      return (Math.atan2(y, x) * 180 / Math.PI + 360) % 360
    },

    offsetAlongBearing(pt: { lat: number; lng: number }, bearingDeg: number, meters: number): { lat: number; lng: number } {
      const R = 6371000
      const δ = meters / R
      const θ = bearingDeg * Math.PI / 180
      const φ1 = pt.lat * Math.PI / 180
      const λ1 = pt.lng * Math.PI / 180
      const φ2 = Math.asin(Math.sin(φ1) * Math.cos(δ) + Math.cos(φ1) * Math.sin(δ) * Math.cos(θ))
      const λ2 = λ1 + Math.atan2(Math.sin(θ) * Math.sin(δ) * Math.cos(φ1), Math.cos(δ) - Math.sin(φ1) * Math.sin(φ2))
      return { lat: φ2 * 180 / Math.PI, lng: λ2 * 180 / Math.PI }
    },

    async cyclePareState() {
      if (!this.selectedRoad) return
      const road = this.selectedRoad
      const coords = road.coordinates
      const mapStore = useMapStore()
      const wsStore = useWorkspaceStore()

      const isOneWay = road.direction === 'one_way'
      const nextState: Record<number, number> = isOneWay
        ? { 0: 3, 3: 0 }
        : { 0: 1, 1: 2, 2: 3, 3: 0 }
      const newState = (nextState[this.pareState] ?? 0) as 0 | 1 | 2 | 3

      // Delete all stop_sign waypoints associated with this road
      const existing = mapStore.waypoints.filter(
        w => w.waypoint_type === 'stop_sign' && w.road_name === road.name,
      )
      for (const wp of existing) await mapStore.deleteWaypoint(wp.id)

      const n = coords.length
      if (n >= 2 && newState !== 0) {
        const startHeading = Math.round(this.calcBearing(coords[1], coords[0]) * 10) / 10
        const endHeading   = Math.round(this.calcBearing(coords[n - 2], coords[n - 1]) * 10) / 10

        const create = async (pt: GeoPoint, heading: number, label: string) => {
          await mapStore.createWaypoint({
            name: `PARE – ${road.name} (${label})`,
            waypoint_type: 'stop_sign',
            lat: pt.lat,
            lng: pt.lng,
            road_name: road.name,
            heading_degrees: heading,
            extra_data: {},
          })
        }

        if (newState === 1) {
          await create(coords[0], startHeading, 'início')
          await create(coords[n - 1], endHeading, 'fim')
        } else if (newState === 2) {
          await create(coords[0], startHeading, 'início')
        } else if (newState === 3) {
          await create(coords[n - 1], endHeading, 'fim')
        }

        // Geometric crossings through the middle of this road (X and T intersections).
        // Rule: if the crossing road already has a stop_sign within 15m of the crossing
        // point (added when P was pressed on that road), skip — the intersection already
        // has PARE coverage. Maximum 2 PARE signs per X-crossing (never 4).
        //
        // createdThisRun tracks offset positions created in THIS cyclePareState call.
        // Multiple crossings at the same geographic point (e.g. a 3-way intersection
        // where two other roads meet Rua X at the same location) would otherwise produce
        // duplicate PAREs at identical offset positions → duplicate_position warning.
        const createdThisRun: L.LatLng[] = []

        for (const crossing of this.findGeometricCrossings(road)) {
          const crossingLatLng = L.latLng(crossing.lat, crossing.lng)
          const crossingAlreadyCovered = mapStore.waypoints.some(wp => {
            if (wp.waypoint_type !== 'stop_sign') return false
            if (wp.road_name === road.name) return false  // ignore own road's signs
            return L.latLng(wp.lat, wp.lng).distanceTo(crossingLatLng) <= 15
          })
          if (crossingAlreadyCovered) continue

          const { fromStart, fromEnd } = this.nearestSegmentBearings(coords, crossing)
          // Offset each PARE 3m to its respective side of the crossing so they don't
          // land at the exact same coordinate (which triggers the duplicate-position warning).
          const ptStart = this.offsetAlongBearing(crossing, (fromStart + 180) % 360, 3)
          const ptEnd   = this.offsetAlongBearing(crossing, (fromEnd   + 180) % 360, 3)
          const llStart = L.latLng(ptStart.lat, ptStart.lng)
          const llEnd   = L.latLng(ptEnd.lat,   ptEnd.lng)

          // Skip if this run already placed a PARE at essentially the same offset
          // (happens when 2+ roads share the same crossing point on the selected road).
          const tooClose = (ll: L.LatLng) => createdThisRun.some(p => p.distanceTo(ll) < 1)

          if (newState === 1) {
            if (!tooClose(llStart)) { await create(ptStart, fromStart, `× ${crossing.otherRoadName} (início→fim)`); createdThisRun.push(llStart) }
            if (!tooClose(llEnd))   { await create(ptEnd,   fromEnd,   `× ${crossing.otherRoadName} (fim→início)`); createdThisRun.push(llEnd) }
          } else if (newState === 2) {
            if (!tooClose(llStart)) { await create(ptStart, fromStart, `× ${crossing.otherRoadName} (início→fim)`); createdThisRun.push(llStart) }
          } else if (newState === 3) {
            if (!tooClose(llEnd))   { await create(ptEnd,   fromEnd,   `× ${crossing.otherRoadName} (fim→início)`); createdThisRun.push(llEnd) }
          }
        }
      }

      await wsStore.runValidation()
      this.pareState = newState
    },

    segmentsIntersect(
      p1: GeoPoint, p2: GeoPoint,
      p3: GeoPoint, p4: GeoPoint,
    ): GeoPoint | null {
      const dx12 = p2.lng - p1.lng, dy12 = p2.lat - p1.lat
      const dx34 = p4.lng - p3.lng, dy34 = p4.lat - p3.lat
      const denom = dx12 * dy34 - dy12 * dx34
      if (Math.abs(denom) < 1e-12) return null  // parallel
      const t = ((p3.lng - p1.lng) * dy34 - (p3.lat - p1.lat) * dx34) / denom
      const u = ((p3.lng - p1.lng) * dy12 - (p3.lat - p1.lat) * dx12) / denom
      if (t >= 0 && t <= 1 && u >= 0 && u <= 1) {
        return { lat: p1.lat + t * dy12, lng: p1.lng + t * dx12 }
      }
      return null
    },

    findGeometricCrossings(road: RoadResponse): Array<{ lat: number; lng: number; otherRoadName: string }> {
      const coords = road.coordinates
      const n = coords.length
      if (n < 2) return []
      const startPt = L.latLng(coords[0].lat, coords[0].lng)
      const endPt   = L.latLng(coords[n - 1].lat, coords[n - 1].lng)
      const results: Array<{ lat: number; lng: number; otherRoadName: string }> = []
      const seen = new Set<string>()

      for (const other of useMapStore().roads) {
        if (other.id === road.id) continue
        for (let i = 0; i < n - 1; i++) {
          for (let j = 0; j < other.coordinates.length - 1; j++) {
            const pt = this.segmentsIntersect(
              coords[i], coords[i + 1], other.coordinates[j], other.coordinates[j + 1],
            )
            if (!pt) continue
            const ll = L.latLng(pt.lat, pt.lng)
            if (ll.distanceTo(startPt) < 5 || ll.distanceTo(endPt) < 5) continue
            const key = `${other.name}|${pt.lat.toFixed(6)}|${pt.lng.toFixed(6)}`
            if (seen.has(key)) continue
            seen.add(key)
            results.push({ lat: pt.lat, lng: pt.lng, otherRoadName: other.name })
          }
        }
      }
      return results
    },

    async onDetectCrossroads() {
      const detected = await useMapStore().detectCrossroads()
      await useWorkspaceStore().runValidation()
      this.bulkStatus = `${detected?.length ?? 0} novo(s) cruzamento(s) detectado(s).`
    },

    nearestSegmentBearings(coords: GeoPoint[], pt: { lat: number; lng: number }) {
      let minD = Infinity, idx = 0
      for (let i = 0; i < coords.length - 1; i++) {
        const mid = L.latLng(
          (coords[i].lat + coords[i + 1].lat) / 2,
          (coords[i].lng + coords[i + 1].lng) / 2,
        )
        const d = mid.distanceTo(L.latLng(pt.lat, pt.lng))
        if (d < minD) { minD = d; idx = i }
      }
      return {
        fromStart: Math.round(this.calcBearing(coords[idx], coords[idx + 1]) * 10) / 10,
        fromEnd:   Math.round(this.calcBearing(coords[idx + 1], coords[idx]) * 10) / 10,
      }
    },

    onFooterDelete() {
      if (!this.selectedRoad) return
      useMapStore().selectRoad(this.selectedRoad.id)
      this.openDeleteConfirm()
    },

    // ── Road Quick Select handlers (Stage 8.A §5.3.2) ─────────────────────

    onRoadFromQuickSelect(roadId: number) {
      this.refreshRoadStyles()
      this.centerMapOnRoad(roadId)
      this.openRoadPanel(roadId)
    },

    onQuickSelectCleared() {
      this.refreshRoadStyles()
      this.$emit('entity-form', { entityType: '', initialData: {} })
    },

    centerMapOnRoad(roadId: number) {
      const store = useMapStore()
      const road = store.roads.find((r: RoadResponse) => r.id === roadId)
      if (!road || road.coordinates.length === 0) return
      const bounds = L.latLngBounds(
        road.coordinates.map((p: GeoPoint) => [p.lat, p.lng] as L.LatLngExpression),
      )
      if (bounds.isValid()) {
        this.map.fitBounds(bounds, { padding: [60, 60], maxZoom: 19 })
      }
    },

    openRoadPanel(roadId: number) {
      const store = useMapStore()
      const road = store.roads.find((r: RoadResponse) => r.id === roadId)
      if (!road) return
      this.$emit('entity-form', { entityType: 'road', initialData: { ...road } })
    },

    // ── Style helpers ──────────────────────────────────────────────────────

    toolBtn(active: boolean): Record<string, string> {
      return {
        padding: '4px 12px',
        background: active ? '#1d4ed8' : '#334155',
        color: '#fff',
        border: 'none',
        borderRadius: '4px',
        cursor: 'pointer',
        fontSize: '12px',
        fontWeight: active ? '600' : '400',
      }
    },

    draftBtnStyle(activeColor: string): Record<string, string> {
      const draft = this.isDraft
      return {
        padding: '4px 12px',
        background: draft ? activeColor : '#334155',
        color: '#fff',
        border: 'none',
        borderRadius: '4px',
        cursor: draft ? 'pointer' : 'not-allowed',
        fontSize: '12px',
        opacity: draft ? '1' : '0.5',
      }
    },
  },
})
</script>

<style>
/* Higher specificity (3 classes) beats Leaflet's .leaflet-container.leaflet-grab (2 classes),
   ensuring crosshair wins regardless of stylesheet load order. */
.leaflet-container.leaflet-container.gms-drawing-mode,
.leaflet-container.leaflet-container.gms-drawing-mode * {
  cursor: crosshair !important;
}
</style>

<style scoped>
.road-footer {
  position: absolute;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  padding: 10px 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  white-space: nowrap;
  pointer-events: all;
}
.road-footer-info { display: flex; align-items: center; gap: 10px; }
.road-footer-name { color: #0f172a; font-weight: 700; font-size: 14px; }
.road-footer-detail { color: #64748b; font-size: 13px; }
.road-footer-shortcuts { display: flex; align-items: center; gap: 6px; border-left: 1px solid #e2e8f0; padding-left: 14px; }
.road-footer-shortcut-label { color: #475569; font-size: 13px; }
.road-footer-delete {
  padding: 4px 12px;
  background: #dc2626;
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
}
.road-footer-delete:hover { background: #b91c1c; }
.slide-footer-enter-active, .slide-footer-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.slide-footer-enter-from, .slide-footer-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(10px);
}
.slide-footer-enter-to, .slide-footer-leave-from {
  opacity: 1;
  transform: translateX(-50%) translateY(0);
}

.select-mode-hint {
  background: #1e293b;
  border-left: 3px solid #FFB400;
  padding: 6px 12px;
  font-size: 0.85rem;
  color: #94a3b8;
}
.select-mode-hint kbd {
  background: #334155;
  border: 1px solid #475569;
  border-radius: 3px;
  padding: 1px 5px;
  font-family: monospace;
  color: #e2e8f0;
}
</style>
