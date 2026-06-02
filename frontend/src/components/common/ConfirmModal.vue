<template>
  <div
    v-if="visible"
    style="position:fixed;inset:0;z-index:9100;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center;"
    @click.self="onCancel"
  >
    <div
      role="dialog"
      aria-modal="true"
      style="background:#1e293b;border-radius:8px;width:440px;max-width:92vw;padding:24px;box-shadow:0 8px 32px rgba(0,0,0,.5);"
    >
      <h3 style="margin:0 0 8px;color:#f1f5f9;font-size:16px;">{{ title }}</h3>
      <p style="margin:0 0 12px;color:#94a3b8;font-size:13px;">{{ message }}</p>
      <ul v-if="items.length" style="margin:0 0 16px;padding-left:20px;color:#cbd5e1;font-size:13px;">
        <li v-for="(item, idx) in items.slice(0, 10)" :key="idx">{{ item }}</li>
        <li v-if="items.length > 10" style="color:#94a3b8;">… e mais {{ items.length - 10 }} item(ns)</li>
      </ul>
      <div style="display:flex;gap:10px;justify-content:flex-end;">
        <button ref="cancelBtn" @click="onCancel"
          style="padding:8px 18px;background:#334155;color:#e2e8f0;border:none;border-radius:4px;cursor:pointer;font-size:13px;">
          {{ cancelLabel }}
        </button>
        <button @click="onConfirm"
          style="padding:8px 18px;background:#dc2626;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:13px;font-weight:600;">
          {{ confirmLabel }}
        </button>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue'

export default defineComponent({
  name: 'ConfirmModal',
  props: {
    visible: { type: Boolean, required: true },
    title: { type: String, required: true },
    message: { type: String, required: true },
    items: { type: Array as () => string[], default: () => [] },
    confirmLabel: { type: String, default: 'Sim, excluir' },
    cancelLabel: { type: String, default: 'Cancelar' },
  },
  emits: ['confirm', 'cancel'],
  watch: {
    visible(v: boolean) {
      if (v) {
        // Cancel is the default focused action — protects against accidental Enter-key confirmations
        this.$nextTick(() => (this.$refs.cancelBtn as HTMLButtonElement)?.focus())
      }
    },
  },
  mounted() {
    document.addEventListener('keydown', this.onKey)
  },
  beforeUnmount() {
    document.removeEventListener('keydown', this.onKey)
  },
  methods: {
    onConfirm() { this.$emit('confirm') },
    onCancel() { this.$emit('cancel') },
    onKey(e: KeyboardEvent) {
      if (this.visible && e.key === 'Escape') {
        e.preventDefault()
        this.onCancel()
      }
    },
  },
})
</script>
