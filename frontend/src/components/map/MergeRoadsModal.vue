<template>
  <div
    style="position:fixed;inset:0;z-index:9000;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center;"
    @click.self="onBackdropClick"
  >
    <div style="background:#1e293b;border-radius:8px;width:600px;max-width:94vw;max-height:88vh;display:flex;flex-direction:column;box-shadow:0 8px 32px rgba(0,0,0,.5);">
      <!-- Header -->
      <div style="padding:16px 20px;border-bottom:1px solid #334155;display:flex;justify-content:space-between;align-items:center;">
        <h3 style="margin:0;color:#f1f5f9;font-size:16px;">Mesclar ruas duplicadas</h3>
        <button @click="$emit('close')" style="background:none;border:none;color:#94a3b8;cursor:pointer;font-size:20px;">✕</button>
      </div>

      <!-- Body -->
      <div style="flex:1;overflow-y:auto;padding:20px;">

        <!-- LOADING -->
        <div v-if="state === 'loading'" style="text-align:center;padding:32px;color:#94a3b8;font-size:14px;">
          Buscando grupos duplicados...
        </div>

        <!-- EMPTY -->
        <div v-else-if="state === 'empty'" style="text-align:center;padding:32px;">
          <div style="color:#4ade80;font-size:14px;margin-bottom:8px;">✔ Nenhuma rua duplicada encontrada</div>
          <div style="color:#94a3b8;font-size:13px;">Todas as ruas têm nomes únicos.</div>
          <button :style="btnSecondary()" style="margin-top:16px;" @click="$emit('close')">Fechar</button>
        </div>

        <!-- PREVIEW -->
        <div v-else-if="state === 'preview'">
          <div style="color:#94a3b8;font-size:12px;margin-bottom:4px;">
            ⚠️ Mesclar é irreversível nesta sessão.
          </div>
          <div v-for="(grp, idx) in groups" :key="idx"
            style="border:1px solid #334155;border-radius:6px;padding:12px;margin-bottom:12px;">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
              <input type="checkbox" :checked="selectedGroups.has(idx)" @change="toggleGroup(idx)" style="cursor:pointer;width:16px;height:16px;" />
              <input
                v-model="grp.editedName"
                :style="nameInputStyle"
                style="flex:1;"
                :placeholder="grp.base_name"
              />
              <span style="color:#94a3b8;font-size:12px;">{{ grp.road_ids.length }} segmentos</span>
            </div>
            <ul style="margin:0;padding-left:20px;color:#94a3b8;font-size:12px;">
              <li v-for="(rname, ri) in grp.road_names" :key="ri">
                {{ rname }} <span style="color:#64748b;">({{ grp.road_points[ri] }} pts)</span>
              </li>
            </ul>
          </div>

          <button :style="btnPrimary(selectedGroups.size > 0)" :disabled="selectedGroups.size === 0"
            style="margin-right:8px;" @click="startMerge">
            Mesclar {{ selectedGroups.size }} grupo(s)
          </button>
          <button :style="btnSecondary()" @click="$emit('close')">Cancelar</button>
        </div>

        <!-- MERGING -->
        <div v-else-if="state === 'merging'" style="text-align:center;padding:32px;color:#94a3b8;font-size:14px;">
          Mesclando {{ selectedGroups.size }} grupo(s)...
        </div>

        <!-- DONE -->
        <div v-else-if="state === 'done'">
          <div style="color:#4ade80;font-size:14px;margin-bottom:12px;">✔ Mesclagem concluída</div>
          <div style="color:#e2e8f0;font-size:13px;line-height:1.8;">
            <div>Grupos mesclados: <strong>{{ mergeResults.length }}</strong></div>
            <div>Segmentos removidos: <strong>{{ totalDeleted }}</strong></div>
            <div v-if="totalGaps > 0" style="color:#fbbf24;">
              Lacunas detectadas: <strong>{{ totalGaps }}</strong> (verifique a geometria)
            </div>
          </div>
          <button :style="btnPrimary(true)" style="margin-top:16px;" @click="$emit('close')">Fechar</button>
        </div>

        <!-- ERROR -->
        <div v-else-if="state === 'error'">
          <div style="color:#f87171;font-size:13px;margin-bottom:12px;">{{ errorMessage }}</div>
          <div style="display:flex;gap:8px;">
            <button :style="btnSecondary()" @click="loadGroups">Tentar novamente</button>
            <button :style="btnSecondary()" @click="$emit('close')">Fechar</button>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue'
import { api } from '../../api/client'
import { useMapStore } from '../../stores/map'
import { useWorkspaceStore } from '../../stores/workspace'
import { useUndoStore } from '../../stores/undo'

type ModalState = 'loading' | 'empty' | 'preview' | 'merging' | 'done' | 'error'

interface GroupEntry {
  base_name: string
  road_ids: number[]
  road_names: string[]
  road_points: number[]
  editedName: string
}

export default defineComponent({
  name: 'MergeRoadsModal',
  props: {
    workspaceId: { type: Number, required: true },
    visible: { type: Boolean, default: false },
  },
  emits: ['close', 'merged'],

  data() {
    return {
      state: 'loading' as ModalState,
      groups: [] as GroupEntry[],
      selectedGroups: new Set<number>(),
      mergeResults: [] as Array<{ deleted_road_ids: number[]; gaps_meters: number[] }>,
      errorMessage: '',
    }
  },

  computed: {
    totalDeleted(): number {
      return this.mergeResults.reduce(
        (s: number, r: { deleted_road_ids: number[] }) => s + r.deleted_road_ids.length, 0,
      )
    },
    totalGaps(): number {
      return this.mergeResults.reduce(
        (s: number, r: { gaps_meters: number[] }) => s + r.gaps_meters.length, 0,
      )
    },
    nameInputStyle(): Record<string, string> {
      return {
        background: '#0f172a',
        border: '1px solid #475569',
        borderRadius: '4px',
        color: '#e2e8f0',
        fontSize: '13px',
        padding: '4px 8px',
      }
    },
  },

  mounted() {
    this.loadGroups()
  },

  methods: {
    onBackdropClick() {
      if (this.state === 'preview' || this.state === 'empty' || this.state === 'error') {
        this.$emit('close')
      }
    },

    async loadGroups() {
      this.state = 'loading'
      try {
        const data = await api.getDuplicateGroups(this.workspaceId)
        if (data.groups.length === 0) {
          this.state = 'empty'
          return
        }
        this.groups = data.groups.map(g => ({
          base_name: g.base_name,
          road_ids: g.road_ids,
          road_names: g.road_names,
          road_points: this.estimatePoints(g.total_points, g.road_ids.length),
          editedName: g.base_name,
        }))
        this.selectedGroups = new Set(this.groups.map((_, i) => i))
        this.state = 'preview'
      } catch (err: unknown) {
        const e = err as { detail?: { message?: string } }
        this.errorMessage = e?.detail?.message ?? 'Erro ao buscar grupos duplicados.'
        this.state = 'error'
      }
    },

    estimatePoints(total: number, count: number): number[] {
      // Distribute total points evenly (exact counts come from road objects, approximated here)
      const per = Math.floor(total / count)
      return Array(count).fill(per)
    },

    toggleGroup(idx: number) {
      const next = new Set(this.selectedGroups)
      if (next.has(idx)) next.delete(idx)
      else next.add(idx)
      this.selectedGroups = next
    },

    async startMerge() {
      const groupsToMerge = [...this.selectedGroups].map(i => ({
        target_name: this.groups[i].editedName || this.groups[i].base_name,
        source_road_ids: this.groups[i].road_ids,
      }))
      this.state = 'merging'
      try {
        const result = await api.mergeRoads(this.workspaceId, groupsToMerge)
        this.mergeResults = result.results
        this.state = 'done'

        // Reload map + validation + recenter
        const mapStore = useMapStore()
        const wsStore = useWorkspaceStore()
        await mapStore.fetchMap(this.workspaceId)
        await wsStore.runValidation()
        mapStore.triggerRecenter()

        // Merge is NOT undoable — clear undo stack
        useUndoStore().clear()

        this.$emit('merged', result)
      } catch (err: unknown) {
        const e = err as { detail?: { message?: string } }
        this.errorMessage = e?.detail?.message ?? 'Erro ao mesclar ruas.'
        this.state = 'error'
      }
    },

    btnPrimary(enabled: boolean): Record<string, string> {
      return {
        padding: '8px 18px',
        background: enabled ? '#1d4ed8' : '#334155',
        color: '#fff',
        border: 'none',
        borderRadius: '4px',
        cursor: enabled ? 'pointer' : 'not-allowed',
        fontSize: '13px',
        opacity: enabled ? '1' : '0.6',
      }
    },

    btnSecondary(): Record<string, string> {
      return {
        padding: '8px 18px',
        background: '#334155',
        color: '#e2e8f0',
        border: 'none',
        borderRadius: '4px',
        cursor: 'pointer',
        fontSize: '13px',
      }
    },
  },
})
</script>
