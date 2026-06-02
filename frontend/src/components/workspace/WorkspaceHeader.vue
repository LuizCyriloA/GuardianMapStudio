<template>
  <div style="background:#fff;border-bottom:1px solid #e2e8f0;padding:10px 16px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
    <div style="flex:1;min-width:0;">
      <div style="font-weight:700;font-size:15px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
        {{ projectName }}
      </div>
      <div style="font-size:12px;color:#64748b;display:flex;align-items:center;gap:8px;margin-top:2px;">
        <span :style="stateBadgeStyle">{{ stateLabel }}</span>
        <span v-if="lastValidated" style="color:#94a3b8;">Validado: {{ lastValidated }}</span>
        <span v-if="errorCount > 0" style="color:#dc2626;">● {{ errorCount }} erro(s)</span>
        <span v-if="warningCount > 0" style="color:#d97706;">○ {{ warningCount }} aviso(s)</span>
      </div>
    </div>

    <div style="display:flex;gap:8px;align-items:center;">
      <button @click="$emit('validate')" :disabled="validating"
        style="padding:6px 14px;background:#e2e8f0;border:none;border-radius:6px;cursor:pointer;font-size:13px;font-weight:500;">
        {{ validating ? 'Validando…' : 'Validar' }}
      </button>

      <div style="position:relative;">
        <button
          @click="onPublishClick"
          :disabled="!canPublish || publishing"
          :title="!canPublish ? `Corrija ${errorCount} erro(s) antes de publicar` : 'Publicar nova versão'"
          :style="publishBtnStyle">
          {{ publishing ? 'Publicando…' : 'Publicar' }}
        </button>
      </div>

      <button v-if="latestVersion" @click="$emit('export')" :disabled="exporting"
        style="padding:6px 14px;background:#0d9488;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:13px;font-weight:500;">
        {{ exporting ? 'Exportando…' : `Exportar v${latestVersion.version_number}` }}
      </button>
    </div>

    <PublishModal
      v-if="showPublishModal"
      @publish="onPublish"
      @cancel="showPublishModal = false"
    />
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue'
import { useProjectStore } from '../../stores/project'
import { useWorkspaceStore } from '../../stores/workspace'
import { mapState } from 'pinia'
import PublishModal from './PublishModal.vue'

export default defineComponent({
  name: 'WorkspaceHeader',
  components: { PublishModal },
  emits: ['validate', 'export', 'published'],
  data() {
    return { showPublishModal: false, validating: false }
  },
  computed: {
    ...mapState(useProjectStore, ['currentProject', 'latestVersion']),
    ...mapState(useWorkspaceStore, ['workspace', 'canPublish', 'publishing', 'exporting', 'errorCount', 'warningCount']),
    projectName(): string {
      return this.currentProject?.name ?? 'Nenhum projeto'
    },
    stateLabel(): string {
      return this.workspace?.state === 'draft' ? 'DRAFT' : 'PUBLICADO'
    },
    stateBadgeStyle() {
      const isDraft = this.workspace?.state === 'draft'
      return {
        background: isDraft ? '#dbeafe' : '#d1fae5',
        color: isDraft ? '#1d4ed8' : '#065f46',
        padding: '1px 8px',
        borderRadius: '9999px',
        fontSize: '11px',
        fontWeight: '600',
      }
    },
    publishBtnStyle() {
      const ok = this.canPublish && !this.publishing
      return {
        padding: '6px 14px',
        background: ok ? '#16a34a' : '#94a3b8',
        color: '#fff',
        border: 'none',
        borderRadius: '6px',
        cursor: ok ? 'pointer' : 'not-allowed',
        fontSize: '13px',
        fontWeight: '500',
      }
    },
    lastValidated(): string {
      const ws = this.workspace
      if (!ws?.last_validated_at) return ''
      const d = new Date(ws.last_validated_at)
      return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
    },
  },
  methods: {
    onPublishClick() {
      if (!this.canPublish) return
      this.showPublishModal = true
    },
    async onPublish(versionName: string) {
      this.showPublishModal = false
      const ws = useWorkspaceStore()
      const version = await ws.publish(versionName)
      if (version) this.$emit('published', version)
    },
  },
})
</script>
