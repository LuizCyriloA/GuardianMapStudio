<template>
  <div style="background:#f8fafc;border-bottom:1px solid #e2e8f0;padding:12px;">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
      <div style="font-size:13px;font-weight:600;color:#1e293b;">
        {{ mode === 'create' ? 'Criar' : 'Editar' }} {{ entityTypeLabel }}
      </div>
      <button @click="$emit('cancel')" style="background:none;border:none;cursor:pointer;color:#94a3b8;font-size:16px;">✕</button>
    </div>

    <!-- Road form -->
    <div v-if="entityType === 'road'">
      <label style="display:block;font-size:12px;font-weight:500;margin-bottom:4px;">Nome *</label>
      <input v-model="form.name" placeholder="Rua Principal" :style="inputStyle" />

      <label style="display:block;font-size:12px;font-weight:500;margin:8px 0 4px;">Velocidade (km/h)</label>
      <input v-model.number="form.speed_limit_kmh" type="number" min="1" :style="inputStyle" />

      <label style="display:block;font-size:12px;font-weight:500;margin:8px 0 4px;">Direção</label>
      <select v-model="form.direction" :style="inputStyle">
        <option value="two_way">Mão dupla</option>
        <option value="one_way">Mão única</option>
      </select>

      <label style="display:block;font-size:12px;font-weight:500;margin:8px 0 4px;">Largura (m)</label>
      <input v-model.number="form.width_meters" type="number" min="0.1" step="0.1" :style="inputStyle" />
    </div>

    <!-- Waypoint form -->
    <div v-else-if="entityType === 'waypoint'">
      <label style="display:block;font-size:12px;font-weight:500;margin-bottom:4px;">Nome *</label>
      <input v-model="form.name" placeholder="Nome do ponto" :style="inputStyle" />

      <label style="display:block;font-size:12px;font-weight:500;margin:8px 0 4px;">Tipo</label>
      <select v-model="form.waypoint_type" :style="inputStyle">
        <option value="stop_sign">Parada (stop_sign)</option>
        <option value="speed_bump">Lombada (speed_bump)</option>
        <option value="gate">Portão (gate)</option>
        <option value="landmark">Marco (landmark)</option>
        <option value="curve">Curva (curve)</option>
        <option value="crossroad">Cruzamento (crossroad)</option>
        <option value="stop_zone">Zona de parada (stop_zone)</option>
      </select>

      <label style="display:block;font-size:12px;font-weight:500;margin:8px 0 4px;">Estrada associada</label>
      <select v-model="form.road_name" :style="inputStyle">
        <option value="">Nenhuma</option>
        <option v-for="r in roads" :key="r.id" :value="r.name">{{ r.name }}</option>
      </select>

      <!-- speed_bump extras -->
      <div v-if="form.waypoint_type === 'speed_bump'">
        <label style="display:block;font-size:12px;font-weight:500;margin:8px 0 4px;">Altura (cm) *</label>
        <input v-model.number="form.height_cm" type="number" min="1" :style="inputStyle" />
      </div>

      <!-- gate extras -->
      <div v-if="form.waypoint_type === 'gate'">
        <label style="display:block;font-size:12px;font-weight:500;margin:8px 0 4px;">Tipo de portão *</label>
        <select v-model="form.gate_type" :style="inputStyle">
          <option value="entry">Entrada</option>
          <option value="exit">Saída</option>
          <option value="entry_exit">Entrada/Saída</option>
          <option value="internal">Interno</option>
        </select>
      </div>

      <!-- stop_sign heading -->
      <div v-if="form.waypoint_type === 'stop_sign'">
        <label style="display:block;font-size:12px;font-weight:500;margin:8px 0 4px;">Ângulo (0–360°)</label>
        <input v-model.number="form.heading_degrees" type="number" min="0" max="360" :style="inputStyle" />
      </div>

      <div style="font-size:11px;color:#94a3b8;margin-top:6px;">
        Lat: {{ form.lat?.toFixed(7) }} / Lng: {{ form.lng?.toFixed(7) }}
      </div>
    </div>

    <!-- Crossroad form -->
    <div v-else-if="entityType === 'crossroad'">
      <label style="display:block;font-size:12px;font-weight:500;margin-bottom:4px;">Estrada A *</label>
      <select v-model="form.road_a_name" :style="inputStyle">
        <option v-for="r in roads" :key="r.id" :value="r.name">{{ r.name }}</option>
      </select>

      <label style="display:block;font-size:12px;font-weight:500;margin:8px 0 4px;">Estrada B *</label>
      <select v-model="form.road_b_name" :style="inputStyle">
        <option v-for="r in roads" :key="r.id" :value="r.name">{{ r.name }}</option>
      </select>
    </div>

    <!-- Area form -->
    <div v-else-if="entityType === 'restricted_area'">
      <label style="display:block;font-size:12px;font-weight:500;margin-bottom:4px;">Nome *</label>
      <input v-model="form.name" placeholder="Zona restrita" :style="inputStyle" />

      <label style="display:block;font-size:12px;font-weight:500;margin:8px 0 4px;">Tipo de restrição</label>
      <select v-model="form.restriction_type" :style="inputStyle">
        <option value="no_entry">Sem entrada</option>
        <option value="speed_limit">Limite de velocidade</option>
        <option value="pedestrian_only">Pedestres</option>
      </select>

      <div v-if="form.restriction_type === 'speed_limit'">
        <label style="display:block;font-size:12px;font-weight:500;margin:8px 0 4px;">Velocidade (km/h) *</label>
        <input v-model.number="form.speed_limit_kmh" type="number" min="1" :style="inputStyle" />
      </div>
    </div>

    <div v-if="error" style="color:#dc2626;font-size:12px;margin-top:6px;">{{ error }}</div>

    <div style="display:flex;gap:6px;margin-top:10px;">
      <button @click="onSubmit" :disabled="saving"
        style="flex:1;padding:8px;background:#1d4ed8;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:13px;font-weight:500;">
        {{ saving ? 'Salvando…' : (mode === 'create' ? 'Criar' : 'Salvar') }}
      </button>
      <button @click="$emit('cancel')"
        style="padding:8px 12px;background:#f1f5f9;border:none;border-radius:6px;cursor:pointer;font-size:13px;">
        Cancelar
      </button>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue'
import { useMapStore } from '../../stores/map'
import { mapState } from 'pinia'

export default defineComponent({
  name: 'EntityForm',
  props: {
    mode: { type: String as () => 'create' | 'edit', default: 'create' },
    entityType: { type: String, required: true },
    initialData: { type: Object, default: () => ({}) },
  },
  emits: ['saved', 'cancel'],
  data() {
    return {
      form: {
        name: '',
        speed_limit_kmh: 20,
        direction: 'two_way',
        width_meters: 6.0,
        waypoint_type: 'landmark',
        road_name: '',
        lat: 0,
        lng: 0,
        height_cm: 10,
        gate_type: 'entry',
        heading_degrees: null as number | null,
        road_a_name: '',
        road_b_name: '',
        restriction_type: 'no_entry',
      },
      saving: false,
      error: '',
    }
  },
  computed: {
    ...mapState(useMapStore, ['roads']),
    entityTypeLabel(): string {
      const labels: Record<string, string> = {
        road: 'Estrada',
        waypoint: 'Waypoint',
        crossroad: 'Cruzamento',
        restricted_area: 'Área Restrita',
      }
      return labels[this.entityType] ?? this.entityType
    },
    inputStyle() {
      return {
        width: '100%',
        padding: '6px 10px',
        border: '1px solid #d1d5db',
        borderRadius: '5px',
        fontSize: '13px',
        background: '#fff',
      }
    },
  },
  created() {
    Object.assign(this.form, this.initialData)
  },
  methods: {
    async onSubmit() {
      this.error = ''
      this.saving = true
      const mapStore = useMapStore()
      try {
        let result

        if (this.entityType === 'road') {
          // coordinates come from MapEditor via initialData
          const data = {
            name: this.form.name,
            coordinates: (this.initialData as { coordinates?: unknown }).coordinates ?? [],
            speed_limit_kmh: this.form.speed_limit_kmh,
            direction: this.form.direction,
            width_meters: this.form.width_meters,
          }
          if (this.mode === 'create') result = await mapStore.createRoad(data)
          else result = await mapStore.updateRoad((this.initialData as { id: number }).id, data)

        } else if (this.entityType === 'waypoint') {
          const extra: Record<string, unknown> = {}
          if (this.form.waypoint_type === 'speed_bump') extra.height_cm = this.form.height_cm
          if (this.form.waypoint_type === 'gate') extra.gate_type = this.form.gate_type
          const data = {
            name: this.form.name,
            waypoint_type: this.form.waypoint_type,
            lat: this.form.lat,
            lng: this.form.lng,
            road_name: this.form.road_name || null,
            heading_degrees: this.form.waypoint_type === 'stop_sign' ? this.form.heading_degrees : null,
            extra_data: extra,
          }
          if (this.mode === 'create') result = await mapStore.createWaypoint(data)
          else result = await mapStore.updateWaypoint((this.initialData as { id: number }).id, data)

        } else if (this.entityType === 'crossroad') {
          const data = {
            road_a_name: this.form.road_a_name,
            road_b_name: this.form.road_b_name,
            lat: this.form.lat,
            lng: this.form.lng,
          }
          result = await mapStore.createCrossroad(data)

        } else if (this.entityType === 'restricted_area') {
          const data = {
            name: this.form.name,
            polygon: (this.initialData as { polygon?: unknown }).polygon ?? [],
            restriction_type: this.form.restriction_type,
            speed_limit_kmh: this.form.restriction_type === 'speed_limit' ? this.form.speed_limit_kmh : null,
          }
          if (this.mode === 'create') result = await mapStore.createArea(data)
          else result = await mapStore.updateArea((this.initialData as { id: number }).id, data)
        }

        this.$emit('saved', result)
      } catch (e: unknown) {
        const err = e as Record<string, unknown>
        this.error = (err?.message as string) ?? 'Erro ao salvar'
      } finally {
        this.saving = false
      }
    },
  },
})
</script>
