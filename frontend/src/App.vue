<template>
  <div style="display:flex;height:100vh;overflow:hidden;">
    <!-- Sidebar -->
    <AppSidebar :current-view="currentView" @navigate="navigate" />

    <!-- Main content area -->
    <div style="flex:1;display:flex;flex-direction:column;min-width:0;overflow:hidden;">
      <!-- Use v-show NOT v-if for EditorView to preserve Leaflet instance within the same session -->
      <ProjectList
        v-if="currentView === 'projects'"
        @project-selected="onProjectSelected"
      />
      <EditorView
        v-show="currentView === 'editor'"
        ref="editorView"
        v-if="editorMounted"
      />
      <VersionHistoryView
        v-if="currentView === 'history'"
      />
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue'
import AppSidebar from './components/layout/AppSidebar.vue'
import ProjectList from './views/ProjectList.vue'
import EditorView from './views/EditorView.vue'
import VersionHistoryView from './views/VersionHistoryView.vue'
import { useProjectStore } from './stores/project'
import { useWorkspaceStore } from './stores/workspace'
import { useMapStore } from './stores/map'

export default defineComponent({
  name: 'App',
  components: { AppSidebar, ProjectList, EditorView, VersionHistoryView },

  data() {
    return {
      currentView: 'projects' as 'projects' | 'editor' | 'history',
      editorMounted: false,
    }
  },

  methods: {
    navigate(view: 'projects' | 'editor' | 'history') {
      this.currentView = view
      if (view === 'editor') {
        this.editorMounted = true
        // Let Leaflet re-measure after potential display change
        this.$nextTick(() => {
          const editorView = this.$refs.editorView as { $el: HTMLElement } | undefined
          if (editorView) {
            const mapEl = editorView.$el?.querySelector('#guardian-map')
            if (mapEl) {
              // Trigger invalidateSize via the MapEditor ref
              const mapEditorRef = (editorView as { $refs?: { mapEditor?: { invalidateSize: () => void } } }).$refs?.mapEditor
              mapEditorRef?.invalidateSize()
            }
          }
        })
      }
    },

    async onProjectSelected(projectId: number) {
      const proj = useProjectStore()
      await proj.selectProject(projectId)

      const ws = useWorkspaceStore()
      await ws.fetchWorkspace(projectId)

      if (ws.workspace) {
        const map = useMapStore()
        await map.fetchMap(ws.workspace.id)
        await ws.loadValidation()
      }

      this.editorMounted = true
      this.currentView = 'editor'
    },
  },

  // Expose delete entity for Leaflet popup buttons
  mounted() {
    // deleteEntity is exposed via main.ts window.guardianApp
  },
})
</script>
