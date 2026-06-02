import { defineStore } from 'pinia';
import { api } from '../api/client';
import { useWorkspaceStore } from './workspace';
export const useMapStore = defineStore('map', {
    state: () => ({
        roads: [],
        waypoints: [],
        crossroads: [],
        restrictedAreas: [],
        selectedEntityId: null,
        selectedEntityType: null,
        loading: false,
        workspaceId: null,
    }),
    getters: {
        roadByName: (state) => (name) => state.roads.find(r => r.name === name),
        waypointsByType: (state) => (type) => state.waypoints.filter(w => w.waypoint_type === type),
    },
    actions: {
        async fetchMap(workspaceId) {
            this.loading = true;
            this.workspaceId = workspaceId;
            try {
                const map = await api.getMap(workspaceId);
                this.roads = map.roads;
                this.waypoints = map.waypoints;
                this.crossroads = map.crossroads;
                this.restrictedAreas = map.restricted_areas;
            }
            finally {
                this.loading = false;
            }
        },
        // Roads
        async createRoad(data) {
            if (!this.workspaceId)
                return;
            const road = await api.createRoad(this.workspaceId, data);
            this.roads.push(road);
            return road;
        },
        async updateRoad(roadId, data) {
            if (!this.workspaceId)
                return;
            const road = await api.updateRoad(this.workspaceId, roadId, data);
            const idx = this.roads.findIndex(r => r.id === roadId);
            if (idx >= 0)
                this.roads[idx] = road;
            return road;
        },
        async deleteRoad(roadId) {
            if (!this.workspaceId)
                return;
            await api.deleteRoad(this.workspaceId, roadId);
            this.roads = this.roads.filter(r => r.id !== roadId);
        },
        // Waypoints
        async createWaypoint(data) {
            if (!this.workspaceId)
                return;
            const wp = await api.createWaypoint(this.workspaceId, data);
            this.waypoints.push(wp);
            return wp;
        },
        async updateWaypoint(waypointId, data) {
            if (!this.workspaceId)
                return;
            const wp = await api.updateWaypoint(this.workspaceId, waypointId, data);
            const idx = this.waypoints.findIndex(w => w.id === waypointId);
            if (idx >= 0)
                this.waypoints[idx] = wp;
            return wp;
        },
        async deleteWaypoint(waypointId) {
            if (!this.workspaceId)
                return;
            await api.deleteWaypoint(this.workspaceId, waypointId);
            this.waypoints = this.waypoints.filter(w => w.id !== waypointId);
        },
        // Crossroads
        async createCrossroad(data) {
            if (!this.workspaceId)
                return;
            const cr = await api.createCrossroad(this.workspaceId, data);
            this.crossroads.push(cr);
            return cr;
        },
        async deleteCrossroad(crossroadId) {
            if (!this.workspaceId)
                return;
            await api.deleteCrossroad(this.workspaceId, crossroadId);
            this.crossroads = this.crossroads.filter(c => c.id !== crossroadId);
        },
        // Restricted areas
        async createArea(data) {
            if (!this.workspaceId)
                return;
            const area = await api.createArea(this.workspaceId, data);
            this.restrictedAreas.push(area);
            return area;
        },
        async updateArea(areaId, data) {
            if (!this.workspaceId)
                return;
            const area = await api.updateArea(this.workspaceId, areaId, data);
            const idx = this.restrictedAreas.findIndex(a => a.id === areaId);
            if (idx >= 0)
                this.restrictedAreas[idx] = area;
            return area;
        },
        async deleteArea(areaId) {
            if (!this.workspaceId)
                return;
            await api.deleteArea(this.workspaceId, areaId);
            this.restrictedAreas = this.restrictedAreas.filter(a => a.id !== areaId);
        },
        // OSM Import
        async previewOsmImport(file, opts = {}) {
            const wsId = this.workspaceId;
            if (!wsId)
                throw new Error('No active workspace');
            return await api.previewOsm(wsId, file, opts);
        },
        async commitOsmImport(roads, replaceExisting) {
            const wsId = this.workspaceId;
            if (!wsId)
                throw new Error('No active workspace');
            const result = await api.importOsm(wsId, { roads, replace_existing: replaceExisting });
            // Reload the full map so the new roads appear
            await this.fetchMap(wsId);
            // Refresh validation (the server already re-ran it; this syncs the store)
            await useWorkspaceStore().runValidation();
            return result;
        },
        selectEntity(type, id) {
            this.selectedEntityId = id;
            this.selectedEntityType = type;
        },
        clearSelection() {
            this.selectedEntityId = null;
            this.selectedEntityType = null;
        },
        clear() {
            this.roads = [];
            this.waypoints = [];
            this.crossroads = [];
            this.restrictedAreas = [];
            this.selectedEntityId = null;
            this.selectedEntityType = null;
            this.workspaceId = null;
        },
    },
});
