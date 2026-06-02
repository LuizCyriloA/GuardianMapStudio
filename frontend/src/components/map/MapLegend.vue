<template>
  <div style="background:#fff;border-top:1px solid #e2e8f0;padding:10px 12px;">
    <div style="font-size:11px;font-weight:600;color:#64748b;margin-bottom:6px;text-transform:uppercase;letter-spacing:.05em;">Legenda</div>
    <div style="display:flex;flex-wrap:wrap;gap:6px;">
      <div v-for="item in items" :key="item.label" style="display:flex;align-items:center;gap:4px;font-size:11px;">
        <div :style="{ width: '14px', height: '14px', borderRadius: '50%', background: item.color, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: '9px', fontWeight: '700' }">
          {{ item.letter }}
        </div>
        <span style="color:#475569;">{{ item.label }}</span>
      </div>
      <div style="display:flex;align-items:center;gap:4px;font-size:11px;">
        <div style="width:20px;height:3px;background:#378ADD;border-radius:2px;"></div>
        <span style="color:#475569;">Mão dupla</span>
      </div>
      <div style="display:flex;align-items:center;gap:4px;font-size:11px;">
        <div style="width:20px;height:3px;background:#ff7800;border-radius:2px;"></div>
        <span style="color:#475569;">Mão única</span>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue'

export default defineComponent({
  name: 'MapLegend',
  data() {
    return {
      items: [
        { letter: 'P', color: '#E24B4A', label: 'Parada' },
        { letter: 'L', color: '#EF9F27', label: 'Lombada' },
        { letter: 'G', color: '#1D9E75', label: 'Portão' },
        { letter: 'C', color: '#888780', label: 'Curva' },
        { letter: 'M', color: '#534AB7', label: 'Marco' },
        { letter: 'S', color: '#378ADD', label: 'Zona' },
      ],
    }
  },
})
</script>
