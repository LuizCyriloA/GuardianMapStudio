<template>
  <div style="position:fixed;inset:0;background:rgba(0,0,0,.5);display:flex;align-items:center;justify-content:center;z-index:9999;">
    <div style="background:#fff;border-radius:8px;padding:24px;width:380px;box-shadow:0 20px 60px rgba(0,0,0,.3);">
      <h3 style="margin-bottom:16px;font-size:16px;font-weight:600;">Publicar Nova Versão</h3>

      <div style="margin-bottom:16px;">
        <label style="display:block;font-size:13px;font-weight:500;margin-bottom:6px;">Nome da versão</label>
        <input
          v-model="versionName"
          placeholder="Ex: v1.0 - Mapa inicial"
          @keydown.enter="onPublish"
          style="width:100%;padding:8px 12px;border:1px solid #d1d5db;border-radius:6px;font-size:14px;"
        />
      </div>

      <div style="display:flex;gap:8px;justify-content:flex-end;">
        <button @click="$emit('cancel')"
          style="padding:8px 16px;background:#f1f5f9;border:none;border-radius:6px;cursor:pointer;font-size:13px;">
          Cancelar
        </button>
        <button @click="onPublish" :disabled="!versionName.trim()"
          style="padding:8px 16px;background:#16a34a;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:13px;font-weight:500;">
          Publicar
        </button>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue'

export default defineComponent({
  name: 'PublishModal',
  emits: ['publish', 'cancel'],
  data() {
    return { versionName: '' }
  },
  methods: {
    onPublish() {
      if (!this.versionName.trim()) return
      this.$emit('publish', this.versionName.trim())
    },
  },
})
</script>
