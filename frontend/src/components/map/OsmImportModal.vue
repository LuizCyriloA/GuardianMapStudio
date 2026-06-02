<template>
  <div
    style="position:fixed;inset:0;z-index:9000;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center;"
    @click.self="onBackdropClick"
  >
    <div style="background:#1e293b;border-radius:8px;width:680px;max-width:95vw;max-height:90vh;display:flex;flex-direction:column;box-shadow:0 8px 32px rgba(0,0,0,.5);">

      <!-- Header -->
      <div style="padding:16px 20px;border-bottom:1px solid #334155;display:flex;justify-content:space-between;align-items:center;">
        <h3 style="margin:0;color:#f1f5f9;font-size:16px;">Importar ruas do OpenStreetMap</h3>
        <button @click="$emit('close')" style="background:none;border:none;color:#94a3b8;cursor:pointer;font-size:20px;">✕</button>
      </div>

      <!-- Body -->
      <div style="flex:1;overflow-y:auto;padding:20px;">

        <!-- IDLE state -->
        <div v-if="state === 'idle'">
          <p style="color:#94a3b8;font-size:13px;margin:0 0 16px;">
            Selecione um arquivo <code>.osm</code> ou <code>.xml</code> exportado do openstreetmap.org.
          </p>
          <input
            ref="fileInput"
            type="file"
            accept=".osm,.xml"
            style="display:none;"
            @change="onFileChange"
          />
          <div style="display:flex;gap:10px;align-items:center;margin-bottom:16px;">
            <button @click="triggerFileInput" :style="btnSecondary()">Escolher arquivo</button>
            <span style="color:#94a3b8;font-size:13px;">{{ selectedFile ? selectedFile.name : 'Nenhum arquivo selecionado' }}</span>
          </div>
          <div v-if="fileError" style="color:#f87171;font-size:13px;margin-bottom:12px;">{{ fileError }}</div>
          <button :disabled="!selectedFile || !!fileError" :style="btnPrimary(!!selectedFile && !fileError)" @click="startPreview">
            Pré-visualizar
          </button>
        </div>

        <!-- PARSING state -->
        <div v-else-if="state === 'parsing'" style="text-align:center;padding:32px;">
          <div style="color:#94a3b8;font-size:14px;">Analisando arquivo...</div>
        </div>

        <!-- PREVIEW state -->
        <div v-else-if="state === 'preview'">
          <!-- Options -->
          <div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:16px;">
            <label style="display:flex;align-items:center;gap:6px;color:#94a3b8;font-size:13px;cursor:pointer;">
              <input type="checkbox" v-model="replaceExisting" style="cursor:pointer;" />
              Substituir ruas existentes
            </label>
            <label style="display:flex;align-items:center;gap:6px;color:#94a3b8;font-size:13px;cursor:pointer;">
              <input type="checkbox" v-model="includePedestrian" @change="onOptionChange" style="cursor:pointer;" />
              Incluir vias de pedestre
            </label>
            <label style="display:flex;align-items:center;gap:6px;color:#94a3b8;font-size:13px;cursor:pointer;">
              <input type="checkbox" v-model="includeUnnamed" @change="onOptionChange" style="cursor:pointer;" />
              Incluir vias sem nome
            </label>
          </div>

          <div v-if="optionsChanged" style="margin-bottom:12px;">
            <button :style="btnSecondary()" @click="reParse">Re-analisar</button>
          </div>

          <div style="color:#94a3b8;font-size:12px;margin-bottom:10px;">
            {{ previewRoads.length }} ruas detectadas
            ({{ totalWaysInFile }} ways no arquivo, {{ skippedWays }} ignoradas)
          </div>

          <!-- Road table -->
          <div style="overflow-y:auto;max-height:280px;border:1px solid #334155;border-radius:4px;">
            <table style="width:100%;border-collapse:collapse;font-size:12px;">
              <thead>
                <tr style="background:#0f172a;color:#94a3b8;">
                  <th style="padding:6px 8px;text-align:left;width:32px;">
                    <input type="checkbox" :checked="allSelected" @change="toggleAll" />
                  </th>
                  <th style="padding:6px 8px;text-align:left;">Nome</th>
                  <th style="padding:6px 8px;text-align:left;">Tipo</th>
                  <th style="padding:6px 8px;text-align:left;">Direção</th>
                  <th style="padding:6px 8px;text-align:right;">Pontos</th>
                  <th style="padding:6px 8px;text-align:center;">Avisos</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(road, idx) in previewRoads"
                  :key="road.osm_way_id"
                  :style="{ background: idx % 2 === 0 ? '#1e293b' : '#263348' }"
                >
                  <td style="padding:5px 8px;">
                    <input type="checkbox" :checked="selectedOsmIds.has(road.osm_way_id)" @change="toggleRoad(road.osm_way_id)" />
                  </td>
                  <td style="padding:5px 8px;color:#e2e8f0;">{{ road.name }}</td>
                  <td style="padding:5px 8px;color:#94a3b8;">{{ road.highway_tag }}</td>
                  <td style="padding:5px 8px;color:#94a3b8;">{{ road.direction === 'one_way' ? 'Mão única' : 'Mão dupla' }}</td>
                  <td style="padding:5px 8px;text-align:right;color:#94a3b8;">{{ road.coordinates.length }}</td>
                  <td style="padding:5px 8px;text-align:center;">
                    <span v-if="road.osm_warnings.length > 0"
                      style="background:#92400e;color:#fef3c7;border-radius:4px;padding:1px 6px;font-size:11px;"
                      :title="road.osm_warnings.join('; ')">
                      {{ road.osm_warnings.length }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div style="display:flex;gap:10px;margin-top:16px;">
            <button :style="btnPrimary(selectedOsmIds.size > 0)" :disabled="selectedOsmIds.size === 0" @click="startImport">
              Importar {{ selectedOsmIds.size }} selecionada(s)
            </button>
            <button :style="btnSecondary()" @click="reset">Cancelar</button>
          </div>
        </div>

        <!-- IMPORTING state -->
        <div v-else-if="state === 'importing'" style="text-align:center;padding:32px;">
          <div style="color:#94a3b8;font-size:14px;">Importando {{ selectedOsmIds.size }} ruas...</div>
        </div>

        <!-- DONE state -->
        <div v-else-if="state === 'done'">
          <div style="color:#4ade80;font-size:14px;margin-bottom:12px;">✔ Importação concluída</div>
          <div style="color:#e2e8f0;font-size:13px;line-height:1.8;">
            <div>Ruas criadas: <strong>{{ importResult?.created_count }}</strong></div>
            <div v-if="importResult && importResult.deleted_existing > 0">Ruas removidas: <strong>{{ importResult.deleted_existing }}</strong></div>
            <div v-if="importResult && importResult.renamed.length > 0">
              Renomeadas: <strong>{{ importResult.renamed.length }}</strong>
              <ul style="margin:4px 0 0 16px;color:#94a3b8;">
                <li v-for="r in importResult.renamed" :key="r.from">{{ r.from }} → {{ r.to }}</li>
              </ul>
            </div>
          </div>
          <button :style="btnPrimary(true)" style="margin-top:16px;" @click="$emit('close')">Fechar</button>
        </div>

        <!-- ERROR state -->
        <div v-else-if="state === 'error'">
          <div style="color:#f87171;font-size:13px;margin-bottom:12px;">{{ errorMessage }}</div>
          <div style="display:flex;gap:10px;">
            <button :style="btnSecondary()" @click="reset">Tentar novamente</button>
            <button :style="btnSecondary()" @click="$emit('close')">Fechar</button>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue'
import { useMapStore } from '../../stores/map'
import type { ParsedRoadDTO, OsmImportResponse } from '../../api/client'

type ModalState = 'idle' | 'parsing' | 'preview' | 'importing' | 'done' | 'error'

const MAX_FILE_SIZE = 10 * 1024 * 1024  // 10 MB

export default defineComponent({
  name: 'OsmImportModal',

  props: {
    workspaceId: { type: Number, required: true },
    visible: { type: Boolean, default: false },
  },

  emits: ['close', 'imported'],

  data() {
    return {
      state: 'idle' as ModalState,
      selectedFile: null as File | null,
      fileError: '',
      previewRoads: [] as ParsedRoadDTO[],
      selectedOsmIds: new Set<number>(),
      totalWaysInFile: 0,
      skippedWays: 0,
      replaceExisting: false,
      includePedestrian: false,
      includeUnnamed: false,
      optionsChanged: false,
      importResult: null as OsmImportResponse | null,
      errorMessage: '',
    }
  },

  computed: {
    allSelected(): boolean {
      if (this.previewRoads.length === 0) return false
      return this.previewRoads.every(r => this.selectedOsmIds.has(r.osm_way_id))
    },
  },

  methods: {
    triggerFileInput() {
      (this.$refs.fileInput as HTMLInputElement).click()
    },

    onBackdropClick() {
      if (this.state === 'idle' || this.state === 'preview' || this.state === 'error') {
        this.$emit('close')
      }
    },

    onFileChange(event: Event) {
      const input = event.target as HTMLInputElement
      const file = input.files?.[0] ?? null
      this.fileError = ''
      this.selectedFile = null

      if (!file) return

      if (!file.name.endsWith('.osm') && !file.name.endsWith('.xml')) {
        this.fileError = 'Apenas arquivos .osm ou .xml são aceitos.'
        return
      }
      if (file.size > MAX_FILE_SIZE) {
        this.fileError = `Arquivo muito grande (${(file.size / 1024 / 1024).toFixed(1)} MB). Máximo: 10 MB.`
        return
      }
      this.selectedFile = file
    },

    async startPreview() {
      if (!this.selectedFile) return
      this.state = 'parsing'
      this.optionsChanged = false
      try {
        const mapStore = useMapStore()
        const result = await mapStore.previewOsmImport(this.selectedFile, {
          includePedestrian: this.includePedestrian,
          includeUnnamed: this.includeUnnamed,
        })
        this.previewRoads = result.roads
        this.totalWaysInFile = result.total_ways_in_file
        this.skippedWays = result.skipped_ways
        this.selectedOsmIds = new Set(result.roads.map(r => r.osm_way_id))
        this.state = 'preview'
      } catch (err: unknown) {
        const e = err as { detail?: { message?: string } }
        this.errorMessage = e?.detail?.message ?? 'Erro ao analisar o arquivo.'
        this.state = 'error'
      }
    },

    onOptionChange() {
      this.optionsChanged = true
    },

    async reParse() {
      await this.startPreview()
    },

    toggleAll(event: Event) {
      const checked = (event.target as HTMLInputElement).checked
      if (checked) {
        this.selectedOsmIds = new Set(this.previewRoads.map(r => r.osm_way_id))
      } else {
        this.selectedOsmIds = new Set()
      }
    },

    toggleRoad(osmWayId: number) {
      const next = new Set(this.selectedOsmIds)
      if (next.has(osmWayId)) {
        next.delete(osmWayId)
      } else {
        next.add(osmWayId)
      }
      this.selectedOsmIds = next
    },

    async startImport() {
      const selected = this.previewRoads.filter(r => this.selectedOsmIds.has(r.osm_way_id))
      if (selected.length === 0) return
      this.state = 'importing'
      try {
        const mapStore = useMapStore()
        const result = await mapStore.commitOsmImport(selected, this.replaceExisting)
        this.importResult = result
        this.state = 'done'
        this.$emit('imported', result)
      } catch (err: unknown) {
        const e = err as { detail?: { message?: string } }
        this.errorMessage = e?.detail?.message ?? 'Erro ao importar ruas.'
        this.state = 'error'
      }
    },

    reset() {
      this.state = 'idle'
      this.selectedFile = null
      this.fileError = ''
      this.previewRoads = []
      this.selectedOsmIds = new Set()
      this.optionsChanged = false
      this.errorMessage = ''
      this.importResult = null
    },

    btnPrimary(enabled: boolean): Record<string, string> {
      return {
        padding: '8px 18px',
        background: enabled ? '#1d4ed8' : '#334155',
        color: '#fff',
        border: 'none',
        borderRadius: '4px',
        cursor: enabled ? 'pointer' : 'not-allowed',
        fontSize: '13px',
        opacity: enabled ? '1' : '0.6',
      }
    },

    btnSecondary(): Record<string, string> {
      return {
        padding: '8px 18px',
        background: '#334155',
        color: '#e2e8f0',
        border: 'none',
        borderRadius: '4px',
        cursor: 'pointer',
        fontSize: '13px',
      }
    },
  },
})
</script>
