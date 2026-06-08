import { defineStore } from 'pinia'
import { api } from '../api/client'
import { useWorkspaceStore } from './workspace'
import type { ParsedRoadDTO, OsmImportResponse } from '../api/client'
import type {
  CrossroadResponse,
  RestrictedAreaResponse,
  RoadResponse,
  WaypointResponse,
} from '../api/types'

export type EntityType = 'road' | 'waypoint' | 'crossroad' | 'restricted_area'

interface MapState {
  roads: RoadResponse[]
  waypoints: WaypointResponse[]
  crossroads: CrossroadResponse[]
  restrictedAreas: RestrictedAreaResponse[]
  selectedEntityId: number | null
  selectedEntityType: EntityType | null
  selectedRoadIds: number[]
  loading: boolean
  workspaceId: number | null
  recenterSignal: number
}

export const useMapStore = defineStore('map', {
  state: (): MapState => ({
    roads: [],
    waypoints: [],
    crossroads: [],
    restrictedAreas: [],
    selectedEntityId: null,
    selectedEntityType: null,
    selectedRoadIds: [],
    loading: false,
    workspaceId: null,
    recenterSignal: 0,
  }),

  getters: {
    roadByName: (state) => (name: string) =>
      state.roads.find(r => r.name === name),

    waypointsByType: (state) => (type: string) =>
      state.waypoints.filter(w => w.waypoint_type === type),

    isRoadSelected: (state) => (id: number) =>
      state.selectedRoadIds.includes(id),
  },

  actions: {
    async fetchMap(workspaceId: number) {
      this.loading = true
      this.workspaceId = workspaceId
      try {
        const map = await api.getMap(workspaceId)
        this.roads = map.roads
        this.waypoints = map.waypoints
        this.crossroads = map.crossroads
        this.restrictedAreas = map.restricted_areas
      } finally {
        this.loading = false
      }
    },

    // Road selection (for select mode + delete key workflow)
    selectRoad(roadId: number) {
      this.selectedRoadIds = [roadId]
    },
    selectRoads(roadIds: number[]) {
      this.selectedRoadIds = [...roadIds]
    },
    clearRoadSelection() {
      this.selectedRoadIds = []
    },

    // Signal MapEditor to re-fit bounds (after import, merge, initial load)
    triggerRecenter() {
      this.recenterSignal++
    },

    // Roads
    async createRoad(data: object) {
      if (!this.workspaceId) return
      const road = await api.createRoad(this.workspaceId, data)
      this.roads.push(road)
      return road
    },

    async updateRoad(roadId: number, data: object) {
      if (!this.workspaceId) return
      const road = await api.updateRoad(this.workspaceId, roadId, data)
      const idx = this.roads.findIndex(r => r.id === roadId)
      if (idx >= 0) this.roads[idx] = road
      return road
    },

    async deleteRoad(roadId: number) {
      if (!this.workspaceId) return
      await api.deleteRoad(this.workspaceId, roadId)
      this.roads = this.roads.filter(r => r.id !== roadId)
    },

    // Waypoints
    async createWaypoint(data: object) {
      if (!this.workspaceId) return
      const wp = await api.createWaypoint(this.workspaceId, data)
      this.waypoints.push(wp)
      return wp
    },

    async updateWaypoint(waypointId: number, data: object) {
      if (!this.workspaceId) return
      const wp = await api.updateWaypoint(this.workspaceId, waypointId, data)
      const idx = this.waypoints.findIndex(w => w.id === waypointId)
      if (idx >= 0) this.waypoints[idx] = wp
      return wp
    },

    async deleteWaypoint(waypointId: number) {
      if (!this.workspaceId) return
      await api.deleteWaypoint(this.workspaceId, waypointId)
      this.waypoints = this.waypoints.filter(w => w.id !== waypointId)
    },

    // Crossroads
    async createCrossroad(data: object) {
      if (!this.workspaceId) return
      const cr = await api.createCrossroad(this.workspaceId, data)
      this.crossroads.push(cr)
      return cr
    },

    async deleteCrossroad(crossroadId: number) {
      if (!this.workspaceId) return
      await api.deleteCrossroad(this.workspaceId, crossroadId)
      this.crossroads = this.crossroads.filter(c => c.id !== crossroadId)
    },

    async detectCrossroads() {
      if (!this.workspaceId) return []
      const detected = await api.detectCrossroads(this.workspaceId)
      for (const cr of detected) {
        if (!this.crossroads.find(c => c.id === cr.id)) this.crossroads.push(cr)
      }
      return detected
    },

    // Restricted areas
    async createArea(data: object) {
      if (!this.workspaceId) return
      const area = await api.createArea(this.workspaceId, data)
      this.restrictedAreas.push(area)
      return area
    },

    async updateArea(areaId: number, data: object) {
      if (!this.workspaceId) return
      const area = await api.updateArea(this.workspaceId, areaId, data)
      const idx = this.restrictedAreas.findIndex(a => a.id === areaId)
      if (idx >= 0) this.restrictedAreas[idx] = area
      return area
    },

    async deleteArea(areaId: number) {
      if (!this.workspaceId) return
      await api.deleteArea(this.workspaceId, areaId)
      this.restrictedAreas = this.restrictedAreas.filter(a => a.id !== areaId)
    },

    // OSM Import
    async previewOsmImport(
      file: File,
      opts: { includePedestrian?: boolean; includeUnnamed?: boolean } = {},
    ) {
      const wsId = this.workspaceId
      if (!wsId) throw new Error('No active workspace')
      return await api.previewOsm(wsId, file, opts)
    },

    async commitOsmImport(
      roads: ParsedRoadDTO[],
      replaceExisting: boolean,
    ): Promise<OsmImportResponse> {
      const wsId = this.workspaceId
      if (!wsId) throw new Error('No active workspace')
      const result = await api.importOsm(wsId, { roads, replace_existing: replaceExisting })
      // Reload the full map so the new roads appear
      await this.fetchMap(wsId)
      // Refresh validation (the server already re-ran it; this syncs the store)
      await useWorkspaceStore().runValidation()
      // Signal MapEditor to re-fit bounds on the new roads
      this.triggerRecenter()
      return result
    },

    selectEntity(type: EntityType, id: number) {
      this.selectedEntityId = id
      this.selectedEntityType = type
    },

    clearSelection() {
      this.selectedEntityId = null
      this.selectedEntityType = null
    },

    clear() {
      this.roads = []
      this.waypoints = []
      this.crossroads = []
      this.restrictedAreas = []
      this.selectedEntityId = null
      this.selectedEntityType = null
      this.selectedRoadIds = []
      this.workspaceId = null
    },
  },
})
