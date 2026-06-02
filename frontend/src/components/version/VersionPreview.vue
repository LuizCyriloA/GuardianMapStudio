<template>
  <div style="height:100%;display:flex;flex-direction:column;">
    <!-- Banner -->
    <div style="background:#fef9c3;border-bottom:1px solid #fde68a;padding:8px 16px;font-size:13px;color:#92400e;flex-shrink:0;">
      📌 Versão v{{ version.version_number }} — <strong>{{ version.name }}</strong>
      (publicada em {{ formatDate(version.published_at) }}) — somente leitura
    </div>
    <!-- Map -->
    <div :id="mapId" style="flex:1;min-height:0;"></div>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue'
import L from 'leaflet'
import { api } from '../../api/client'
import type { VersionResponse } from '../../api/types'

export default defineComponent({
  name: 'VersionPreview',
  props: {
    version: { type: Object as () => VersionResponse, required: true },
  },
  data() {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return { map: null as any }
  },
  computed: {
    mapId(): string {
      return `version-map-${this.version.id}`
    },
  },
  mounted() {
    this.$nextTick(() => { this.initMap() })
  },
  beforeUnmount() {
    this.map?.remove()
  },
  methods: {
    async initMap() {
      await this.$nextTick()
      const el = document.getElementById(this.mapId)
      if (!el) return

      this.map = L.map(el, { zoom: 18, center: [-23.55, -46.63], zoomControl: true })
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
      }).addTo(this.map)

      // Load version map data
      try {
        const data = await fetch(`/api/v1/versions/${this.version.id}/map`).then(r => r.json()) as {
          roads: Array<{ name: string; coordinates: Array<{ lat: number; lng: number }> }>
          waypoints: Array<{ name: string; waypoint_type: string; latitude: number; longitude: number }>
          crossroads: Array<{ latitude: number; longitude: number; road_a_name: string; road_b_name: string }>
          restricted_areas: Array<{ name: string; polygon: Array<{ lat: number; lng: number }> }>
        }
        const bounds: L.LatLng[] = []

        for (const road of data.roads ?? []) {
          if (road.coordinates?.length >= 2) {
            const lls = road.coordinates.map((c) => L.latLng(c.lat, c.lng))
            L.polyline(lls, { color: '#378ADD', weight: 3 })
              .bindPopup(`<b>${road.name}</b>`)
              .addTo(this.map!)
            bounds.push(...lls)
          }
        }

        for (const wp of data.waypoints ?? []) {
          if (wp.latitude && wp.longitude) {
            const ll = L.latLng(wp.latitude, wp.longitude)
            L.circleMarker(ll, { radius: 6, color: '#534AB7' })
              .bindPopup(`<b>${wp.name}</b><br>${wp.waypoint_type}`)
              .addTo(this.map!)
            bounds.push(ll)
          }
        }

        if (bounds.length > 0 && this.map) {
          this.map.fitBounds(L.latLngBounds(bounds).pad(0.1))
        }
      } catch {
        // Version map load failed — continue with empty map
      }
    },

    formatDate(iso: string) {
      return new Date(iso).toLocaleDateString('pt-BR')
    },
  },
})
</script>
