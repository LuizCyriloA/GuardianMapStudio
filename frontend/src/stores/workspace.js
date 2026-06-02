import { defineStore } from 'pinia';
import { api } from '../api/client';
export const useWorkspaceStore = defineStore('workspace', {
    state: () => ({
        workspace: null,
        validation: null,
        publishing: false,
        exporting: false,
        error: null,
    }),
    getters: {
        canPublish: (state) => state.validation !== null && state.validation.error_count === 0,
        isDraft: (state) => state.workspace?.state === 'draft',
        errorCount: (state) => state.validation?.error_count ?? 0,
        warningCount: (state) => state.validation?.warning_count ?? 0,
    },
    actions: {
        async fetchWorkspace(projectId) {
            this.error = null;
            try {
                this.workspace = await api.getWorkspace(projectId);
            }
            catch (e) {
                this.error = 'Workspace não encontrado';
            }
        },
        async runValidation() {
            if (!this.workspace)
                return;
            try {
                this.validation = await api.validate(this.workspace.id);
                // Refresh workspace state after validation
                this.workspace = {
                    ...this.workspace,
                    has_validation_errors: (this.validation?.error_count ?? 0) > 0,
                    last_validated_at: this.validation?.validated_at ?? null,
                };
            }
            catch (e) {
                this.error = 'Erro ao validar';
            }
        },
        async loadValidation() {
            if (!this.workspace)
                return;
            try {
                this.validation = await api.getValidation(this.workspace.id);
            }
            catch {
                // No cached validation yet — ignore
            }
        },
        async publish(versionName) {
            if (!this.workspace)
                return null;
            this.publishing = true;
            try {
                const version = await api.publish(this.workspace.id, versionName);
                return version;
            }
            finally {
                this.publishing = false;
            }
        },
        async exportVersion(versionId) {
            this.exporting = true;
            try {
                await api.exportVersion(versionId);
                // Trigger download
                const url = api.downloadExportUrl(versionId);
                const a = document.createElement('a');
                a.href = url;
                a.download = `version_${versionId}.json`;
                a.click();
            }
            finally {
                this.exporting = false;
            }
        },
        clear() {
            this.workspace = null;
            this.validation = null;
            this.error = null;
        },
    },
});
