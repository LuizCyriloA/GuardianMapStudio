<template>
  <nav style="width:220px;background:#1e293b;color:#fff;display:flex;flex-direction:column;height:100%;">
    <div style="padding:16px 20px;border-bottom:1px solid #334155;">
      <div style="font-size:18px;font-weight:700;color:#60a5fa;">🗺 GMS</div>
      <div style="font-size:11px;color:#94a3b8;margin-top:2px;">GuardianMapStudio</div>
    </div>

    <div v-if="currentProject" style="padding:12px 20px;border-bottom:1px solid #334155;">
      <div style="font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;">Projeto</div>
      <div style="font-size:13px;font-weight:600;margin-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
        {{ currentProject.name }}
      </div>
    </div>

    <ul style="list-style:none;padding:8px 0;flex:1;">
      <li>
        <button @click="$emit('navigate', 'projects')"
          :style="navStyle(currentView === 'projects')">
          📋 Projetos
        </button>
      </li>
      <li v-if="currentProject">
        <button @click="$emit('navigate', 'editor')"
          :style="navStyle(currentView === 'editor')">
          ✏️ Editor de Mapa
        </button>
      </li>
      <li v-if="currentProject">
        <button @click="$emit('navigate', 'history')"
          :style="navStyle(currentView === 'history')">
          🕓 Histórico de Versões
        </button>
      </li>
    </ul>

    <div style="padding:12px 20px;border-top:1px solid #334155;">
      <div style="font-size:11px;color:#475569;">MVP01 — Guardian Platform</div>
    </div>
  </nav>
</template>

<script lang="ts">
import { defineComponent } from 'vue'
import { useProjectStore } from '../../stores/project'
import { mapState } from 'pinia'

export default defineComponent({
  name: 'AppSidebar',
  props: {
    currentView: { type: String, required: true },
  },
  emits: ['navigate'],
  computed: {
    ...mapState(useProjectStore, ['currentProject']),
  },
  methods: {
    navStyle(active: boolean) {
      return {
        display: 'block',
        width: '100%',
        textAlign: 'left' as const,
        padding: '10px 20px',
        background: active ? '#1d4ed8' : 'transparent',
        color: active ? '#fff' : '#cbd5e1',
        border: 'none',
        cursor: 'pointer',
        fontSize: '14px',
        transition: 'background .15s',
      }
    },
  },
})
</script>
