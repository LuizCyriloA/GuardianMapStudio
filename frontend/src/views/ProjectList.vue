<template>
  <div style="max-width:700px;margin:0 auto;padding:32px 24px;">
    <h1 style="font-size:24px;font-weight:700;margin-bottom:24px;">Projetos</h1>

    <!-- Create form -->
    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:20px;margin-bottom:24px;">
      <h2 style="font-size:16px;font-weight:600;margin-bottom:16px;">Novo Projeto</h2>
      <div style="display:flex;gap:10px;flex-wrap:wrap;">
        <input v-model="newName" placeholder="Nome do projeto" @keydown.enter="createProject"
          style="flex:1;min-width:200px;padding:8px 12px;border:1px solid #d1d5db;border-radius:6px;font-size:14px;" />
        <input v-model="newDesc" placeholder="Descrição (opcional)"
          style="flex:1;min-width:200px;padding:8px 12px;border:1px solid #d1d5db;border-radius:6px;font-size:14px;" />
        <button @click="createProject" :disabled="!newName.trim() || creating"
          style="padding:8px 20px;background:#1d4ed8;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:14px;font-weight:500;white-space:nowrap;">
          {{ creating ? 'Criando…' : '+ Criar' }}
        </button>
      </div>
      <div v-if="createError" style="color:#dc2626;font-size:13px;margin-top:8px;">{{ createError }}</div>
    </div>

    <!-- Projects list -->
    <div v-if="loading" style="text-align:center;color:#94a3b8;padding:32px;">Carregando…</div>

    <div v-else-if="projects.length === 0"
      style="text-align:center;color:#94a3b8;padding:32px;background:#f8fafc;border-radius:8px;border:2px dashed #e2e8f0;">
      Nenhum projeto ainda. Crie o primeiro acima.
    </div>

    <div v-else style="display:flex;flex-direction:column;gap:10px;">
      <div v-for="p in projects" :key="p.id"
        style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:16px;display:flex;align-items:center;justify-content:space-between;cursor:pointer;transition:border-color .15s;"
        @click="openProject(p.id)"
        @mouseover="($event.currentTarget as HTMLElement).style.borderColor = '#1d4ed8'"
        @mouseleave="($event.currentTarget as HTMLElement).style.borderColor = '#e2e8f0'">
        <div>
          <div style="font-weight:600;font-size:15px;">{{ p.name }}</div>
          <div v-if="p.description" style="font-size:13px;color:#64748b;margin-top:2px;">{{ p.description }}</div>
          <div style="font-size:12px;color:#94a3b8;margin-top:4px;">
            Criado: {{ new Date(p.created_at).toLocaleDateString('pt-BR') }}
          </div>
        </div>
        <div style="color:#1d4ed8;font-size:13px;font-weight:500;white-space:nowrap;">
          Abrir →
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue'
import { useProjectStore } from '../stores/project'
import { mapState } from 'pinia'

export default defineComponent({
  name: 'ProjectList',
  emits: ['project-selected'],
  data() {
    return {
      newName: '',
      newDesc: '',
      creating: false,
      createError: '',
    }
  },
  computed: {
    ...mapState(useProjectStore, ['projects', 'loading']),
  },
  async created() {
    await useProjectStore().fetchProjects()
  },
  methods: {
    async createProject() {
      if (!this.newName.trim()) return
      this.creating = true
      this.createError = ''
      try {
        const project = await useProjectStore().createProject(this.newName.trim(), this.newDesc.trim())
        this.newName = ''
        this.newDesc = ''
        this.$emit('project-selected', project.id)
      } catch (e: unknown) {
        this.createError = 'Erro ao criar projeto'
      } finally {
        this.creating = false
      }
    },
    async openProject(id: number) {
      await useProjectStore().selectProject(id)
      this.$emit('project-selected', id)
    },
  },
})
</script>
