import { defineStore } from 'pinia'
import { api } from '../api/client'
import type { ProjectResponse, VersionResponse } from '../api/types'

interface ProjectState {
  projects: ProjectResponse[]
  currentProject: ProjectResponse | null
  versions: VersionResponse[]
  loading: boolean
  error: string | null
}

export const useProjectStore = defineStore('project', {
  state: (): ProjectState => ({
    projects: [],
    currentProject: null,
    versions: [],
    loading: false,
    error: null,
  }),

  actions: {
    async fetchProjects() {
      this.loading = true
      this.error = null
      try {
        const res = await api.getProjects()
        this.projects = res.items
      } catch (e) {
        this.error = 'Erro ao carregar projetos'
      } finally {
        this.loading = false
      }
    },

    async createProject(name: string, description = '') {
      const project = await api.createProject(name, description)
      this.projects.push(project)
      return project
    },

    async selectProject(id: number) {
      const project = this.projects.find(p => p.id === id) ?? null
      this.currentProject = project
      if (project) {
        await this.fetchVersions(project.id)
      }
    },

    async fetchVersions(projectId: number) {
      const res = await api.getVersions(projectId)
      this.versions = res.items
    },
  },

  getters: {
    latestVersion: (state) =>
      state.versions.length > 0
        ? state.versions[state.versions.length - 1]
        : null,
  },
})
