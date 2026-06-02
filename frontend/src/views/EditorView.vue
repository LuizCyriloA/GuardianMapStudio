<template>
  <div style="display:flex;flex-direction:column;height:100%;min-height:0;">
    <!-- Header -->
    <WorkspaceHeader
      @validate="runValidation"
      @export="onExport"
      @published="onPublished"
    />

    <!-- Main area -->
    <div style="flex:1;display:flex;min-height:0;">
      <!-- Map + toolbar -->
      <MapEditor
        ref="mapEditor"
        style="flex:1;min-width:0;"
        @entity-form="onEntityForm"
        @entity-selected="onEntitySelected"
      />

      <!-- Right panel -->
      <div style="width:280px;display:flex;flex-direction:column;border-left:1px solid #e2e8f0;background:#f8fafc;overflow:hidden;">
        <!-- Entity form (takes priority over validation) -->
        <EntityForm
          v-if="showEntityForm"
          :mode="entityFormMode"
          :entity-type="entityFormType"
          :initial-data="entityFormData"
          @saved="onEntitySaved"
          @cancel="closeEntityForm"
        />

        <!-- Validation panel -->
        <ValidationPanel style="flex:1;overflow-y:auto;" />

        <!-- Legend -->
        <MapLegend />
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue'
import WorkspaceHeader from '../components/workspace/WorkspaceHeader.vue'
import MapEditor from '../components/map/MapEditor.vue'
import EntityForm from '../components/map/EntityForm.vue'
import ValidationPanel from '../components/layout/ValidationPanel.vue'
import MapLegend from '../components/map/MapLegend.vue'
import { useProjectStore } from '../stores/project'
import { useWorkspaceStore } from '../stores/workspace'
import { useMapStore } from '../stores/map'

export default defineComponent({
  name: 'EditorView',
  components: { WorkspaceHeader, MapEditor, EntityForm, ValidationPanel, MapLegend },

  data() {
    return {
      showEntityForm: false,
      entityFormMode: 'create' as 'create' | 'edit',
      entityFormType: '',
      entityFormData: {} as Record<string, unknown>,
    }
  },

  async mounted() {
    const ws = useWorkspaceStore()
    const proj = useProjectStore()
    const map = useMapStore()

    if (!ws.workspace && proj.currentProject) {
      await ws.fetchWorkspace(proj.currentProject.id)
    }
    if (ws.workspace) {
      await map.fetchMap(ws.workspace.id)
      await ws.loadValidation()
    }
  },

  methods: {
    onEntityForm({ entityType, initialData }: { entityType: string; initialData: Record<string, unknown> }) {
      this.entityFormType = entityType
      this.entityFormData = initialData
      this.entityFormMode = 'create'
      this.showEntityForm = true
    },

    onEntitySelected({ type, id }: { type: string; id: number }) {
      const mapStore = useMapStore()
      mapStore.selectEntity(type as 'road' | 'waypoint' | 'crossroad' | 'restricted_area', id)
    },

    closeEntityForm() {
      this.showEntityForm = false
    },

    async onEntitySaved() {
      this.showEntityForm = false
      await this.runValidation()
    },

    async runValidation() {
      await useWorkspaceStore().runValidation()
      const editor = this.$refs.mapEditor as InstanceType<typeof MapEditor>
      editor?.renderValidation()
    },

    async onPublished(version: { id: number }) {
      const proj = useProjectStore()
      const ws = useWorkspaceStore()
      const map = useMapStore()

      // Reload workspace (new DRAFT was created by backend)
      if (proj.currentProject) {
        await proj.fetchVersions(proj.currentProject.id)
        await ws.fetchWorkspace(proj.currentProject.id)
      }
      if (ws.workspace) {
        await map.fetchMap(ws.workspace.id)
      }
      ws.validation = null
    },

    async onExport() {
      const proj = useProjectStore()
      const latestVersion = proj.latestVersion
      if (!latestVersion) return
      await useWorkspaceStore().exportVersion(latestVersion.id)
    },
  },
})
</script>
