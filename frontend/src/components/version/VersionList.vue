<template>
  <div>
    <div v-if="versions.length === 0" style="text-align:center;color:#94a3b8;padding:24px;">
      Nenhuma versão publicada ainda.
    </div>
    <table v-else style="width:100%;border-collapse:collapse;font-size:13px;">
      <thead>
        <tr style="background:#f1f5f9;">
          <th style="padding:8px 12px;text-align:left;font-weight:600;color:#475569;">Versão</th>
          <th style="padding:8px 12px;text-align:left;font-weight:600;color:#475569;">Nome</th>
          <th style="padding:8px 12px;text-align:left;font-weight:600;color:#475569;">Data</th>
          <th style="padding:8px 12px;text-align:left;font-weight:600;color:#475569;">Entidades</th>
          <th style="padding:8px 12px;text-align:center;font-weight:600;color:#475569;">Ações</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="v in sortedVersions" :key="v.id" style="border-top:1px solid #e2e8f0;">
          <td style="padding:10px 12px;font-weight:600;color:#1d4ed8;">v{{ v.version_number }}</td>
          <td style="padding:10px 12px;color:#374151;">{{ v.name }}</td>
          <td style="padding:10px 12px;color:#64748b;">{{ formatDate(v.published_at) }}</td>
          <td style="padding:10px 12px;color:#64748b;">
            {{ v.road_count }} estradas · {{ v.waypoint_count }} waypoints
          </td>
          <td style="padding:10px 12px;text-align:center;display:flex;gap:6px;justify-content:center;">
            <button @click="$emit('preview', v)"
              style="padding:4px 12px;background:#e0e7ff;color:#1d4ed8;border:none;border-radius:5px;cursor:pointer;font-size:12px;font-weight:500;">
              Ver
            </button>
            <a :href="downloadUrl(v.id)" download
              style="padding:4px 12px;background:#d1fae5;color:#065f46;border:none;border-radius:5px;cursor:pointer;font-size:12px;font-weight:500;text-decoration:none;">
              Baixar
            </a>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue'
import { api } from '../../api/client'
import type { VersionResponse } from '../../api/types'

export default defineComponent({
  name: 'VersionList',
  props: {
    versions: { type: Array as () => VersionResponse[], default: () => [] },
  },
  emits: ['preview'],
  computed: {
    sortedVersions(): VersionResponse[] {
      return [...this.versions].sort((a, b) => b.version_number - a.version_number)
    },
  },
  methods: {
    formatDate(iso: string) {
      return new Date(iso).toLocaleDateString('pt-BR')
    },
    downloadUrl(versionId: number) {
      return api.downloadExportUrl(versionId)
    },
  },
})
</script>
