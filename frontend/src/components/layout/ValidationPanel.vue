<template>
  <div style="background:#fff;border-left:1px solid #e2e8f0;padding:12px;overflow-y:auto;flex:1;">
    <div style="font-weight:600;font-size:14px;margin-bottom:8px;display:flex;align-items:center;gap:8px;">
      Validação
      <span v-if="validation" style="font-size:12px;font-weight:400;color:#64748b;">
        <span v-if="validation.error_count > 0" style="color:#dc2626;">
          ● {{ validation.error_count }} erro(s)
        </span>
        <span v-if="validation.warning_count > 0" style="color:#d97706;margin-left:6px;">
          ○ {{ validation.warning_count }} aviso(s)
        </span>
        <span v-if="validation.error_count === 0 && validation.warning_count === 0" style="color:#16a34a;">
          ✓ Sem problemas
        </span>
      </span>
      <span v-else style="font-size:12px;color:#94a3b8;">Não validado</span>
    </div>

    <div v-if="validation && validation.results.length">
      <div
        v-for="r in validation.results"
        :key="r.id"
        @click="onClickResult(r)"
        :style="resultStyle(r.severity)"
      >
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:2px;">
          <span :style="{ color: r.severity === 'error' ? '#dc2626' : '#d97706', fontSize: '16px' }">
            {{ r.severity === 'error' ? '●' : '○' }}
          </span>
          <span style="font-size:11px;background:#f1f5f9;padding:1px 5px;border-radius:3px;color:#475569;">
            {{ r.affected_entity_type }}
          </span>
          <span style="font-size:11px;color:#64748b;">{{ r.rule_id }}</span>
        </div>
        <div style="font-size:12px;color:#374151;padding-left:22px;line-height:1.4;">
          {{ r.message }}
        </div>
      </div>
    </div>

    <div v-else-if="validation && validation.results.length === 0"
      style="font-size:12px;color:#16a34a;padding:8px 0;">
      ✓ Workspace válido — pronto para publicar
    </div>

    <div v-else style="font-size:12px;color:#94a3b8;padding:8px 0;">
      Execute a validação para ver os resultados.
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue'
import { useWorkspaceStore } from '../../stores/workspace'
import { useMapStore } from '../../stores/map'
import { mapState } from 'pinia'
import type { ValidationResultResponse } from '../../api/types'

export default defineComponent({
  name: 'ValidationPanel',
  computed: {
    ...mapState(useWorkspaceStore, ['validation']),
  },
  methods: {
    resultStyle(severity: string) {
      return {
        padding: '8px',
        marginBottom: '6px',
        borderRadius: '4px',
        cursor: 'pointer',
        background: severity === 'error' ? '#fef2f2' : '#fffbeb',
        borderLeft: `3px solid ${severity === 'error' ? '#dc2626' : '#d97706'}`,
        transition: 'opacity .15s',
      }
    },
    onClickResult(r: ValidationResultResponse) {
      const mapStore = useMapStore()
      const typeMap: Record<string, 'road' | 'waypoint' | 'crossroad' | 'restricted_area'> = {
        road: 'road',
        waypoint: 'waypoint',
        crossroad: 'crossroad',
        restricted_area: 'restricted_area',
        workspace: 'road',
      }
      const type = typeMap[r.affected_entity_type] ?? 'road'
      if (r.affected_entity_id > 0) {
        mapStore.selectEntity(type, r.affected_entity_id)
      }
    },
  },
})
</script>
