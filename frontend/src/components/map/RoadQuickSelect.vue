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

  emits: ['road-selected', 'selection-cleared'],

  data() {
    return {
      query: '' as string,
    }
  },

  computed: {
    sortedRoads() {
      const store = useMapStore()
      // Cloned + sorted alphabetically (case-insensitive, locale-aware
      // so "São" sorts naturally for the operator).
      return [...store.roads].sort((a, b) =>
        a.name.localeCompare(b.name, 'pt-BR', { sensitivity: 'base' }),
      )
    },
    hasRoads(): boolean {
      return useMapStore().roads.length > 0
    },
    placeholder(): string {
      const count = useMapStore().roads.length
      if (count === 0) return 'Nenhuma rua cadastrada'
      return `Digite ou escolha (${count} ruas)`
    },
  },

  methods: {
    onChange() {
      const name = this.query.trim()
      if (!name) return
      const store = useMapStore()
      const road = store.roads.find(
        r => r.name.toLowerCase() === name.toLowerCase(),
      )
      if (!road) {
        // The user typed something that isn't a road name. Do nothing —
        // datalist filtering will guide them. Don't show an alert.
        return
      }
      store.selectRoad(road.id)
      // Centering and panel-opening are delegated to MapEditor via event,
      // because RoadQuickSelect must not depend on the Leaflet map instance.
      this.$emit('road-selected', road.id)
    },

    onClear() {
      this.query = ''
      useMapStore().clearRoadSelection()
      const inp = this.$refs.input as HTMLInputElement | null
      if (inp) inp.focus()
      this.$emit('selection-cleared')
    },
  },
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
  color: #cbd5e1;
  white-space: nowrap;
}
.rqs-input {
  width: 200px;
  padding: 4px 8px;
  font-size: 0.85rem;
  border: 1px solid #475569;
  border-radius: 4px;
  background: #0f172a;
  color: #e2e8f0;
}
.rqs-input:disabled {
  background: #1e293b;
  color: #6b7280;
  border-color: #334155;
}
.rqs-input::placeholder {
  color: #6b7280;
}
.rqs-clear {
  background: none;
  border: 1px solid #475569;
  border-radius: 50%;
  width: 22px;
  height: 22px;
  font-size: 0.9rem;
  cursor: pointer;
  color: #94a3b8;
  display: flex;
  align-items: center;
  justify-content: center;
}
.rqs-clear:hover { background: #334155; color: #e2e8f0; }
</style>
