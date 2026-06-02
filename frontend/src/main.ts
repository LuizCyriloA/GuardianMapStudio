import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { useMapStore } from './stores/map'
import { useWorkspaceStore } from './stores/workspace'

// Declare window.guardianApp for Leaflet popup callbacks
declare global {
  interface Window {
    guardianApp: {
      deleteEntity: (type: string, id: number) => void
    }
  }
}

const pinia = createPinia()
const app = createApp(App)
app.use(pinia)

const mountedApp = app.mount('#app')

// Expose for Leaflet popup button callbacks
window.guardianApp = {
  async deleteEntity(type: string, id: number) {
    const mapStore = useMapStore()
    const wsStore = useWorkspaceStore()
    try {
      if (type === 'road')             await mapStore.deleteRoad(id)
      else if (type === 'waypoint')    await mapStore.deleteWaypoint(id)
      else if (type === 'crossroad')   await mapStore.deleteCrossroad(id)
      else if (type === 'restricted_area') await mapStore.deleteArea(id)
      // Auto-validate after delete
      await wsStore.runValidation()
    } catch (e) {
      alert('Erro ao excluir: ' + String(e))
    }
  },
}

export default mountedApp
