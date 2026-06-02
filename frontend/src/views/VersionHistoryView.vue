<template>
  <div style="padding:24px;height:100%;display:flex;flex-direction:column;min-height:0;">
    <div style="display:flex;align-items:center;gap:16px;margin-bottom:20px;flex-shrink:0;">
      <h1 style="font-size:20px;font-weight:700;">
        Versões — {{ currentProject?.name ?? '' }}
      </h1>
      <button v-if="previewingVersion" @click="previewingVersion = null"
        style="padding:6px 14px;background:#f1f5f9;border:1px solid #d1d5db;border-radius:6px;cursor:pointer;font-size:13px;">
        ← Voltar à lista
      </button>
    </div>

    <!-- Version list -->
    <div v-if="!previewingVersion" style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;flex:1;overflow-y:auto;">
      <VersionList :versions="versions" @preview="showPreview" />
    </div>

    <!-- Version preview -->
    <div v-if="previewingVersion" style="flex:1;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">
      <VersionPreview :version="previewingVersion" />
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue'
import VersionList from '../components/version/VersionList.vue'
import VersionPreview from '../components/version/VersionPreview.vue'
import { useProjectStore } from '../stores/project'
import { mapState } from 'pinia'
import type { VersionResponse } from '../api/types'

export default defineComponent({
  name: 'VersionHistoryView',
  components: { VersionList, VersionPreview },
  data() {
    return { previewingVersion: null as VersionResponse | null }
  },
  computed: {
    ...mapState(useProjectStore, ['currentProject', 'versions']),
  },
  async created() {
    const store = useProjectStore()
    if (store.currentProject) {
      await store.fetchVersions(store.currentProject.id)
    }
  },
  methods: {
    showPreview(version: VersionResponse) {
      this.previewingVersion = version
    },
  },
})
</script>
