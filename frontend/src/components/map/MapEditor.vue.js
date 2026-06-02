/// <reference types="../../../node_modules/.vue-global-types/vue_3.4_false.d.ts" />
import { defineComponent, watch } from 'vue';
import L from 'leaflet';
import { useMapStore } from '../../stores/map';
import { useWorkspaceStore } from '../../stores/workspace';
import { useUndoStore } from '../../stores/undo';
import { api } from '../../api/client';
import OsmImportModal from './OsmImportModal.vue';
import MergeRoadsModal from './MergeRoadsModal.vue';
import ConfirmModal from '../common/ConfirmModal.vue';
import { CompassControl } from './CompassControl';
import { attachRectangleSelector } from './RectangleSelector';
// ── Waypoint icon config ────────────────────────────────────────────────────
const WAYPOINT_ICON_CFG = {
    stop_sign: { letter: 'P', color: '#E24B4A' },
    speed_bump: { letter: 'L', color: '#EF9F27' },
    gate: { letter: 'G', color: '#1D9E75' },
    curve: { letter: 'C', color: '#888780' },
    landmark: { letter: 'M', color: '#534AB7' },
    stop_zone: { letter: 'S', color: '#378ADD' },
    crossroad: { letter: 'X', color: '#888780' },
};
const ROAD_COLORS = {
    two_way: '#378ADD',
    one_way: '#ff7800',
};
const SELECTED_ROAD_COLOR = '#FFB400';
const SELECTED_ROAD_WEIGHT = 6;
const AREA_COLORS = {
    speed_limit: '#ffcc00',
    no_entry: '#ff4444',
    pedestrian_only: '#44ff44',
};
function makeWaypointIcon(type) {
    const cfg = WAYPOINT_ICON_CFG[type] ?? { letter: '?', color: '#888' };
    return L.divIcon({
        html: `<div style="width:24px;height:24px;border-radius:50%;background:${cfg.color};color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.4);">${cfg.letter}</div>`,
        className: '',
        iconSize: [24, 24],
        iconAnchor: [12, 12],
        popupAnchor: [0, -14],
    });
}
export default defineComponent({
    name: 'MapEditor',
    components: { OsmImportModal, MergeRoadsModal, ConfirmModal },
    emits: ['entity-form', 'entity-selected'],
    data() {
        return {
            osmImportOpen: false,
            mergeOpen: false,
            // Leaflet objects typed as any — Vue's reactive proxy breaks L.* types
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            map: null,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            roadsLayer: null,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            waypointsLayer: null,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            crossroadsLayer: null,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            areasLayer: null,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            validationLayer: null,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            drawLayer: null,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            previewPolyline: null,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            snapIndicator: null,
            // Road id → Leaflet polyline (for in-place style updates without re-render)
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            roadLayerIndex: {},
            drawingMode: 'select',
            vertices: [],
            snapMsg: '',
            bulkStatus: '',
            pendingRoadCoords: [],
            pendingAreaCoords: [],
            rectangleTeardown: null,
            confirmModal: {
                visible: false,
                title: '',
                message: '',
                items: [],
                onConfirm: () => { },
            },
        };
    },
    computed: {
        isDraft() {
            return useWorkspaceStore().isDraft ?? false;
        },
        workspaceId() {
            return useWorkspaceStore().workspace?.id ?? null;
        },
        canUndo() {
            return useUndoStore().canUndo;
        },
        undoLabel() {
            return useUndoStore().lastActionLabel;
        },
        undoBtnStyle() {
            const can = this.canUndo;
            return {
                padding: '4px 12px',
                background: can ? '#374151' : '#334155',
                color: can ? '#e2e8f0' : '#6b7280',
                border: can ? '1px solid #4b5563' : 'none',
                borderRadius: '4px',
                cursor: can ? 'pointer' : 'not-allowed',
                fontSize: '12px',
            };
        },
    },
    watch: {
        drawingMode(newMode, oldMode) {
            if (oldMode === 'select' && this.rectangleTeardown) {
                this.rectangleTeardown();
                this.rectangleTeardown = null;
            }
            if (newMode === 'select' && this.map) {
                this.rectangleTeardown = attachRectangleSelector(this.map, {
                    onSelect: (bounds) => this.selectRoadsInBounds(bounds),
                });
            }
        },
    },
    mounted() {
        this.$nextTick(() => { this.initMap(); });
        document.addEventListener('keydown', this.onKeyDown);
    },
    beforeUnmount() {
        document.removeEventListener('keydown', this.onKeyDown);
        if (this.rectangleTeardown)
            this.rectangleTeardown();
        if (this.map) {
            this.map.remove();
            this.map = null;
        }
    },
    methods: {
        // ── Map initialization ─────────────────────────────────────────────────
        initMap() {
            const mapStore = useMapStore();
            const centerLat = mapStore.roads[0]?.coordinates[0]?.lat ?? -15.78;
            const centerLng = mapStore.roads[0]?.coordinates[0]?.lng ?? -47.93;
            this.map = L.map('guardian-map', {
                center: [centerLat, centerLng],
                zoom: mapStore.roads.length > 0 ? 18 : 5,
                doubleClickZoom: false,
            });
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors',
                maxZoom: 22,
            }).addTo(this.map);
            new CompassControl().addTo(this.map);
            this.roadsLayer = L.layerGroup().addTo(this.map);
            this.waypointsLayer = L.layerGroup().addTo(this.map);
            this.crossroadsLayer = L.layerGroup().addTo(this.map);
            this.areasLayer = L.layerGroup().addTo(this.map);
            this.validationLayer = L.layerGroup().addTo(this.map);
            this.drawLayer = L.layerGroup().addTo(this.map);
            this.map.on('click', this.onMapClick);
            this.map.on('dblclick', this.onMapDblClick);
            this.map.on('mousemove', this.onMapMouseMove);
            this.renderAll();
            this.$nextTick(() => this.recenterOnEntities());
            this.rectangleTeardown = attachRectangleSelector(this.map, {
                onSelect: (bounds) => this.selectRoadsInBounds(bounds),
            });
            const store = useMapStore();
            watch(() => store.roads, () => this.renderRoads(), { deep: true });
            watch(() => store.waypoints, () => this.renderWaypoints(), { deep: true });
            watch(() => store.crossroads, () => this.renderCrossroads(), { deep: true });
            watch(() => store.restrictedAreas, () => this.renderAreas(), { deep: true });
            watch(() => useWorkspaceStore().validation, () => this.renderValidation(), { deep: true });
            watch(() => store.selectedEntityId, () => this.panToSelected());
            watch(() => store.recenterSignal, () => this.recenterOnEntities());
        },
        invalidateSize() {
            this.map?.invalidateSize();
        },
        // ── Re-center (§5.2) ──────────────────────────────────────────────────
        recenterOnEntities() {
            if (!this.map)
                return;
            const store = useMapStore();
            const bounds = L.latLngBounds([]);
            for (const road of store.roads) {
                for (const pt of road.coordinates)
                    bounds.extend([pt.lat, pt.lng]);
            }
            for (const wp of store.waypoints)
                bounds.extend([wp.lat, wp.lng]);
            for (const cr of store.crossroads)
                bounds.extend([cr.lat, cr.lng]);
            for (const area of store.restrictedAreas) {
                for (const pt of area.polygon)
                    bounds.extend([pt.lat, pt.lng]);
            }
            if (bounds.isValid()) {
                this.map.fitBounds(bounds, { padding: [40, 40], maxZoom: 19 });
            }
            else {
                this.map.setView([-15.78, -47.93], 5);
            }
        },
        // ── Mode & drawing ────────────────────────────────────────────────────
        setMode(mode) {
            this.cancelDrawing();
            this.drawingMode = mode;
            if (this.map) {
                this.map.getContainer().style.cursor = mode === 'select' ? '' : 'crosshair';
            }
        },
        cancelDrawing() {
            this.vertices = [];
            this.pendingRoadCoords = [];
            this.pendingAreaCoords = [];
            if (this.previewPolyline) {
                this.previewPolyline.remove();
                this.previewPolyline = null;
            }
            if (this.snapIndicator) {
                this.snapIndicator.remove();
                this.snapIndicator = null;
            }
            this.drawLayer?.clearLayers();
        },
        onMapClick(e) {
            const { lat, lng } = e.latlng;
            if (this.drawingMode === 'select') {
                useMapStore().clearRoadSelection();
                this.refreshRoadStyles();
                this.bulkStatus = '';
                this.$emit('entity-form', { entityType: '', initialData: {} });
                return;
            }
            if (this.drawingMode === 'road') {
                this.vertices.push(e.latlng);
                this.updatePreviewPolyline();
            }
            else if (this.drawingMode === 'waypoint') {
                this.$emit('entity-form', { entityType: '', initialData: {} });
                this.$nextTick(() => {
                    this.$emit('entity-form', {
                        entityType: 'waypoint',
                        initialData: { lat, lng, waypoint_type: '', road_name: '' },
                    });
                });
            }
            else if (this.drawingMode === 'area') {
                this.vertices.push(e.latlng);
                this.updatePreviewPolygon();
            }
        },
        onMapDblClick(e) {
            if (this.drawingMode === 'road' && this.vertices.length >= 2) {
                const coords = this.vertices.map(v => ({ lat: v.lat, lng: v.lng }));
                this.cancelDrawing();
                this.setMode('select');
                this.$emit('entity-form', {
                    entityType: 'road',
                    initialData: {
                        name: `Rua ${Date.now().toString().slice(-4)}`,
                        coordinates: coords,
                        speed_limit_kmh: 20,
                        direction: 'two_way',
                        width_meters: 6.0,
                    },
                });
            }
            else if (this.drawingMode === 'area' && this.vertices.length >= 3) {
                const polygon = this.vertices.map(v => ({ lat: v.lat, lng: v.lng }));
                this.cancelDrawing();
                this.setMode('select');
                this.$emit('entity-form', {
                    entityType: 'restricted_area',
                    initialData: {
                        name: `Área ${Date.now().toString().slice(-4)}`,
                        polygon,
                        restriction_type: 'no_entry',
                    },
                });
            }
        },
        async onMapMouseMove(e) {
            if (this.drawingMode !== 'waypoint' && this.drawingMode !== 'road') {
                this.snapMsg = '';
                return;
            }
            const wsStore = useWorkspaceStore();
            if (!wsStore.workspace)
                return;
            try {
                const res = await api.snap(wsStore.workspace.id, e.latlng.lat, e.latlng.lng);
                if (res.snapped) {
                    this.snapMsg = `Snap: ${res.distance_meters.toFixed(2)}m`;
                    if (!this.snapIndicator) {
                        this.snapIndicator = L.circleMarker([res.snapped_to.lat, res.snapped_to.lng], { radius: 8, color: '#2563eb', fillColor: '#2563eb', fillOpacity: 0.5 }).addTo(this.map);
                    }
                    else {
                        this.snapIndicator.setLatLng([res.snapped_to.lat, res.snapped_to.lng]);
                    }
                }
                else {
                    this.snapMsg = '';
                    if (this.snapIndicator) {
                        this.snapIndicator.remove();
                        this.snapIndicator = null;
                    }
                }
            }
            catch { /* Snap errors are non-critical */ }
        },
        updatePreviewPolyline() {
            if (!this.map)
                return;
            if (this.previewPolyline)
                this.previewPolyline.remove();
            if (this.vertices.length < 2)
                return;
            this.previewPolyline = L.polyline(this.vertices, {
                color: '#378ADD', weight: 3, dashArray: '6 4', opacity: 0.7,
            }).addTo(this.map);
        },
        updatePreviewPolygon() {
            if (!this.map)
                return;
            this.drawLayer?.clearLayers();
            if (this.vertices.length < 2)
                return;
            L.polyline([...this.vertices, this.vertices[0]], {
                color: '#EF9F27', weight: 2, dashArray: '6 4',
            }).addTo(this.drawLayer);
        },
        // ── Road selection (§5.5) ──────────────────────────────────────────────
        onRoadClick(road) {
            if (this.drawingMode !== 'select')
                return;
            useMapStore().selectRoad(road.id);
            this.refreshRoadStyles();
            this.bulkStatus = '';
            this.$emit('entity-form', { entityType: 'road', initialData: { ...road } });
        },
        refreshRoadStyles() {
            const store = useMapStore();
            for (const [idStr, layer] of Object.entries(this.roadLayerIndex)) {
                const id = Number(idStr);
                const road = store.roads.find(r => r.id === id);
                if (!road)
                    continue;
                const selected = store.isRoadSelected(id);
                layer.setStyle({
                    color: selected ? SELECTED_ROAD_COLOR : (ROAD_COLORS[road.direction] ?? '#378ADD'),
                    weight: selected ? SELECTED_ROAD_WEIGHT : 4,
                });
            }
        },
        selectRoadsInBounds(bounds) {
            const store = useMapStore();
            const selectedIds = [];
            for (const road of store.roads) {
                const hit = road.coordinates.some(p => bounds.contains([p.lat, p.lng]));
                if (hit)
                    selectedIds.push(road.id);
            }
            store.selectRoads(selectedIds);
            this.refreshRoadStyles();
            if (selectedIds.length > 1) {
                this.bulkStatus = `${selectedIds.length} ruas selecionadas. Pressione Delete para excluir todas.`;
                this.$emit('entity-form', { entityType: '', initialData: {} });
            }
            else if (selectedIds.length === 1) {
                this.bulkStatus = '';
                const road = store.roads.find(r => r.id === selectedIds[0]);
                if (road)
                    this.$emit('entity-form', { entityType: 'road', initialData: { ...road } });
            }
            else {
                this.bulkStatus = '';
            }
        },
        // ── Keyboard (§5.7 + §5.9) ─────────────────────────────────────────────
        onKeyDown(e) {
            const tag = e.target.tagName;
            if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT')
                return;
            if (e.key === 'Delete' || e.key === 'Backspace') {
                if (useMapStore().selectedRoadIds.length > 0) {
                    e.preventDefault();
                    this.openDeleteConfirm();
                }
            }
            if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
                e.preventDefault();
                useUndoStore().undoLast();
            }
        },
        openDeleteConfirm() {
            const store = useMapStore();
            const ids = store.selectedRoadIds;
            const names = ids
                .map(id => store.roads.find(r => r.id === id)?.name)
                .filter(Boolean);
            this.confirmModal = {
                visible: true,
                title: ids.length === 1 ? 'Excluir rua?' : `Excluir ${ids.length} ruas?`,
                message: ids.length === 1
                    ? 'Esta ação removerá a rua selecionada do rascunho.'
                    : `Esta ação removerá ${ids.length} ruas do rascunho.`,
                items: names,
                onConfirm: () => this.performDelete([...ids]),
            };
        },
        async performDelete(ids) {
            this.confirmModal.visible = false;
            const store = useMapStore();
            const restoreEntries = ids
                .map(id => store.roads.find(r => r.id === id))
                .filter(Boolean);
            try {
                for (const id of ids)
                    await store.deleteRoad(id);
                useUndoStore().push({ type: 'delete_roads', roads: restoreEntries, timestamp: Date.now() });
                store.clearRoadSelection();
                this.bulkStatus = '';
                this.refreshRoadStyles();
            }
            catch (e) {
                alert(e instanceof Error ? e.message : 'Falha ao excluir');
            }
        },
        triggerUndo() {
            useUndoStore().undoLast();
        },
        // ── OSM / Merge events ──────────────────────────────────────────────────
        onOsmImported() {
            this.osmImportOpen = false;
        },
        onMerged() {
            this.mergeOpen = false;
        },
        // ── Render ─────────────────────────────────────────────────────────────
        renderAll() {
            this.renderRoads();
            this.renderWaypoints();
            this.renderCrossroads();
            this.renderAreas();
            this.renderValidation();
        },
        renderRoads() {
            if (!this.roadsLayer)
                return;
            this.roadsLayer.clearLayers();
            this.roadLayerIndex = {};
            const store = useMapStore();
            for (const road of store.roads) {
                if (road.coordinates.length < 2)
                    continue;
                const lls = road.coordinates.map(c => [c.lat, c.lng]);
                const selected = store.isRoadSelected(road.id);
                const color = selected ? SELECTED_ROAD_COLOR : (ROAD_COLORS[road.direction] ?? '#378ADD');
                const weight = selected ? SELECTED_ROAD_WEIGHT : 4;
                const line = L.polyline(lls, { color, weight, opacity: 0.9 });
                line.on('click', (e) => {
                    L.DomEvent.stopPropagation(e);
                    this.onRoadClick(road);
                });
                line.bindPopup(`
          <b>${road.name}</b><br>
          ${road.speed_limit_kmh} km/h · ${road.direction === 'two_way' ? 'mão dupla' : 'mão única'}<br>
          <button onclick="window.guardianApp.deleteEntity('road', ${road.id})"
            style="margin-top:6px;padding:3px 10px;background:#dc2626;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px;">
            Excluir
          </button>
        `);
                line.addTo(this.roadsLayer);
                this.roadLayerIndex[road.id] = line;
            }
        },
        renderWaypoints() {
            if (!this.waypointsLayer)
                return;
            this.waypointsLayer.clearLayers();
            const store = useMapStore();
            for (const wp of store.waypoints) {
                if (!wp.active)
                    continue;
                const icon = makeWaypointIcon(wp.waypoint_type);
                const m = L.marker([wp.lat, wp.lng], { icon });
                m.bindPopup(`
          <b>${wp.name}</b><br>
          <span style="color:#64748b;font-size:12px;">${wp.waypoint_type}</span>
          ${wp.road_name ? `<br>📍 ${wp.road_name}` : ''}<br>
          <button onclick="window.guardianApp.deleteEntity('waypoint', ${wp.id})"
            style="margin-top:6px;padding:3px 10px;background:#dc2626;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px;">
            Excluir
          </button>
        `);
                m.addTo(this.waypointsLayer);
            }
        },
        renderCrossroads() {
            if (!this.crossroadsLayer)
                return;
            this.crossroadsLayer.clearLayers();
            const store = useMapStore();
            for (const cr of store.crossroads) {
                const m = L.circleMarker([cr.lat, cr.lng], {
                    radius: 8, color: '#334155', fillColor: '#fff', fillOpacity: 1, weight: 2,
                });
                m.bindPopup(`
          <b>Cruzamento</b><br>
          ${cr.road_a_name} × ${cr.road_b_name}<br>
          <button onclick="window.guardianApp.deleteEntity('crossroad', ${cr.id})"
            style="margin-top:6px;padding:3px 10px;background:#dc2626;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px;">
            Excluir
          </button>
        `);
                m.addTo(this.crossroadsLayer);
            }
        },
        renderAreas() {
            if (!this.areasLayer)
                return;
            this.areasLayer.clearLayers();
            const store = useMapStore();
            for (const area of store.restrictedAreas) {
                if (area.polygon.length < 3)
                    continue;
                const lls = area.polygon.map(p => [p.lat, p.lng]);
                const fillColor = AREA_COLORS[area.restriction_type] ?? '#888888';
                const poly = L.polygon(lls, { color: fillColor, fillColor, fillOpacity: 0.2, weight: 2 });
                poly.bindPopup(`
          <b>${area.name}</b><br>
          ${area.restriction_type}
          ${area.speed_limit_kmh ? ` · ${area.speed_limit_kmh} km/h` : ''}<br>
          <button onclick="window.guardianApp.deleteEntity('restricted_area', ${area.id})"
            style="margin-top:6px;padding:3px 10px;background:#dc2626;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px;">
            Excluir
          </button>
        `);
                poly.addTo(this.areasLayer);
            }
        },
        renderValidation() {
            if (!this.validationLayer)
                return;
            this.validationLayer.clearLayers();
            const ws = useWorkspaceStore();
            const store = useMapStore();
            if (!ws.validation)
                return;
            const entityPos = (type, id) => {
                if (type === 'road') {
                    const r = store.roads.find(r => r.id === id);
                    if (r?.coordinates[0])
                        return [r.coordinates[0].lat, r.coordinates[0].lng];
                }
                else if (type === 'waypoint') {
                    const w = store.waypoints.find(w => w.id === id);
                    if (w)
                        return [w.lat, w.lng];
                }
                else if (type === 'crossroad') {
                    const c = store.crossroads.find(c => c.id === id);
                    if (c)
                        return [c.lat, c.lng];
                }
                else if (type === 'restricted_area') {
                    const a = store.restrictedAreas.find(a => a.id === id);
                    if (a?.polygon[0])
                        return [a.polygon[0].lat, a.polygon[0].lng];
                }
                return null;
            };
            for (const r of ws.validation.results) {
                const pos = entityPos(r.affected_entity_type, r.affected_entity_id);
                if (!pos)
                    continue;
                const color = r.severity === 'error' ? '#dc2626' : '#d97706';
                const m = L.circleMarker(pos, { radius: 10, color, fillColor: color, fillOpacity: 0.35, weight: 2 });
                m.bindPopup(`<b style="color:${color}">${r.severity.toUpperCase()}</b><br><small>${r.rule_id}</small><br>${r.message}`);
                m.addTo(this.validationLayer);
            }
        },
        panToSelected() {
            const store = useMapStore();
            if (!store.selectedEntityId || !store.selectedEntityType || !this.map)
                return;
            const { selectedEntityId: id, selectedEntityType: type } = store;
            let pos = null;
            if (type === 'road') {
                const r = store.roads.find(r => r.id === id);
                if (r?.coordinates[0])
                    pos = [r.coordinates[0].lat, r.coordinates[0].lng];
            }
            else if (type === 'waypoint') {
                const w = store.waypoints.find(w => w.id === id);
                if (w)
                    pos = [w.lat, w.lng];
            }
            else if (type === 'crossroad') {
                const c = store.crossroads.find(c => c.id === id);
                if (c)
                    pos = [c.lat, c.lng];
            }
            else if (type === 'restricted_area') {
                const a = store.restrictedAreas.find(a => a.id === id);
                if (a?.polygon[0])
                    pos = [a.polygon[0].lat, a.polygon[0].lng];
            }
            if (pos)
                this.map.panTo(pos);
        },
        // ── Style helpers ──────────────────────────────────────────────────────
        toolBtn(active) {
            return {
                padding: '4px 12px',
                background: active ? '#1d4ed8' : '#334155',
                color: '#fff',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '12px',
                fontWeight: active ? '600' : '400',
            };
        },
        draftBtnStyle(activeColor) {
            const draft = this.isDraft;
            return {
                padding: '4px 12px',
                background: draft ? activeColor : '#334155',
                color: '#fff',
                border: 'none',
                borderRadius: '4px',
                cursor: draft ? 'pointer' : 'not-allowed',
                fontSize: '12px',
                opacity: draft ? '1' : '0.5',
            };
        },
    },
}); /* PartiallyEnd: #3632/script.vue */
function __VLS_template() {
    const __VLS_ctx = {};
    const __VLS_localComponents = {
        ...{ OsmImportModal, MergeRoadsModal, ConfirmModal },
        ...{},
        ...{},
        ...__VLS_ctx,
    };
    let __VLS_components;
    const __VLS_localDirectives = {
        ...{},
        ...__VLS_ctx,
    };
    let __VLS_directives;
    let __VLS_styleScopedClasses;
    let __VLS_resolvedLocalAndGlobalComponents;
    __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
    __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
    __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (...[$event]) => {
                __VLS_ctx.setMode('select');
            } }, ...{ style: ((__VLS_ctx.toolBtn(__VLS_ctx.drawingMode === 'select'))) }, });
    __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (...[$event]) => {
                __VLS_ctx.setMode('waypoint');
            } }, ...{ style: ((__VLS_ctx.toolBtn(__VLS_ctx.drawingMode === 'waypoint'))) }, });
    __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (...[$event]) => {
                __VLS_ctx.osmImportOpen = true;
            } }, ...{ style: ((__VLS_ctx.draftBtnStyle('#0f766e'))) }, disabled: ((!__VLS_ctx.isDraft)), title: ((__VLS_ctx.isDraft ? 'Importar ruas do OpenStreetMap' : 'Disponível apenas em rascunho')), });
    __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (...[$event]) => {
                __VLS_ctx.mergeOpen = true;
            } }, ...{ style: ((__VLS_ctx.draftBtnStyle('#7c3aed'))) }, disabled: ((!__VLS_ctx.isDraft)), title: ((__VLS_ctx.isDraft ? 'Mesclar ruas duplicadas' : 'Disponível apenas em rascunho')), });
    __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (__VLS_ctx.recenterOnEntities) }, ...{ style: ((__VLS_ctx.toolBtn(false))) }, title: ("Centralizar mapa nas entidades"), });
    __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (__VLS_ctx.triggerUndo) }, ...{ style: ((__VLS_ctx.undoBtnStyle)) }, disabled: ((!__VLS_ctx.canUndo)), title: ((__VLS_ctx.canUndo ? __VLS_ctx.undoLabel : 'Nada para desfazer')), });
    if (__VLS_ctx.bulkStatus) {
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
        (__VLS_ctx.bulkStatus);
    }
    __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ id: ("guardian-map"), ...{ style: ({}) }, });
    if (__VLS_ctx.snapMsg) {
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
        (__VLS_ctx.snapMsg);
    }
    if (__VLS_ctx.osmImportOpen && __VLS_ctx.workspaceId !== null) {
        const __VLS_0 = __VLS_resolvedLocalAndGlobalComponents.OsmImportModal;
        /** @type { [typeof __VLS_components.OsmImportModal, ] } */
        // @ts-ignore
        const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({ ...{ 'onClose': {} }, ...{ 'onImported': {} }, workspaceId: ((__VLS_ctx.workspaceId)), visible: ((__VLS_ctx.osmImportOpen)), }));
        const __VLS_2 = __VLS_1({ ...{ 'onClose': {} }, ...{ 'onImported': {} }, workspaceId: ((__VLS_ctx.workspaceId)), visible: ((__VLS_ctx.osmImportOpen)), }, ...__VLS_functionalComponentArgsRest(__VLS_1));
        let __VLS_6;
        const __VLS_7 = {
            onClose: (...[$event]) => {
                if (!((__VLS_ctx.osmImportOpen && __VLS_ctx.workspaceId !== null)))
                    return;
                __VLS_ctx.osmImportOpen = false;
            }
        };
        const __VLS_8 = {
            onImported: (__VLS_ctx.onOsmImported)
        };
        let __VLS_3;
        let __VLS_4;
        var __VLS_5;
    }
    if (__VLS_ctx.mergeOpen && __VLS_ctx.workspaceId !== null) {
        const __VLS_9 = __VLS_resolvedLocalAndGlobalComponents.MergeRoadsModal;
        /** @type { [typeof __VLS_components.MergeRoadsModal, ] } */
        // @ts-ignore
        const __VLS_10 = __VLS_asFunctionalComponent(__VLS_9, new __VLS_9({ ...{ 'onClose': {} }, ...{ 'onMerged': {} }, workspaceId: ((__VLS_ctx.workspaceId)), visible: ((__VLS_ctx.mergeOpen)), }));
        const __VLS_11 = __VLS_10({ ...{ 'onClose': {} }, ...{ 'onMerged': {} }, workspaceId: ((__VLS_ctx.workspaceId)), visible: ((__VLS_ctx.mergeOpen)), }, ...__VLS_functionalComponentArgsRest(__VLS_10));
        let __VLS_15;
        const __VLS_16 = {
            onClose: (...[$event]) => {
                if (!((__VLS_ctx.mergeOpen && __VLS_ctx.workspaceId !== null)))
                    return;
                __VLS_ctx.mergeOpen = false;
            }
        };
        const __VLS_17 = {
            onMerged: (__VLS_ctx.onMerged)
        };
        let __VLS_12;
        let __VLS_13;
        var __VLS_14;
    }
    const __VLS_18 = __VLS_resolvedLocalAndGlobalComponents.ConfirmModal;
    /** @type { [typeof __VLS_components.ConfirmModal, ] } */
    // @ts-ignore
    const __VLS_19 = __VLS_asFunctionalComponent(__VLS_18, new __VLS_18({ ...{ 'onConfirm': {} }, ...{ 'onCancel': {} }, visible: ((__VLS_ctx.confirmModal.visible)), title: ((__VLS_ctx.confirmModal.title)), message: ((__VLS_ctx.confirmModal.message)), items: ((__VLS_ctx.confirmModal.items)), }));
    const __VLS_20 = __VLS_19({ ...{ 'onConfirm': {} }, ...{ 'onCancel': {} }, visible: ((__VLS_ctx.confirmModal.visible)), title: ((__VLS_ctx.confirmModal.title)), message: ((__VLS_ctx.confirmModal.message)), items: ((__VLS_ctx.confirmModal.items)), }, ...__VLS_functionalComponentArgsRest(__VLS_19));
    let __VLS_24;
    const __VLS_25 = {
        onConfirm: (...[$event]) => {
            __VLS_ctx.confirmModal.onConfirm();
        }
    };
    const __VLS_26 = {
        onCancel: (...[$event]) => {
            __VLS_ctx.confirmModal.visible = false;
        }
    };
    let __VLS_21;
    let __VLS_22;
    var __VLS_23;
    var __VLS_slots;
    var __VLS_inheritedAttrs;
    const __VLS_refs = {};
    var $refs;
    var $el;
    return {
        attrs: {},
        slots: __VLS_slots,
        refs: $refs,
        rootEl: $el,
    };
}
;
let __VLS_self;
