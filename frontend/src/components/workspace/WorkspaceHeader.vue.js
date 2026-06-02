/// <reference types="../../../node_modules/.vue-global-types/vue_3.4_false.d.ts" />
import { defineComponent } from 'vue';
import { useProjectStore } from '../../stores/project';
import { useWorkspaceStore } from '../../stores/workspace';
import { mapState } from 'pinia';
import PublishModal from './PublishModal.vue';
export default defineComponent({
    name: 'WorkspaceHeader',
    components: { PublishModal },
    emits: ['validate', 'export', 'published'],
    data() {
        return { showPublishModal: false, validating: false };
    },
    computed: {
        ...mapState(useProjectStore, ['currentProject', 'latestVersion']),
        ...mapState(useWorkspaceStore, ['workspace', 'canPublish', 'publishing', 'exporting', 'errorCount', 'warningCount']),
        projectName() {
            return this.currentProject?.name ?? 'Nenhum projeto';
        },
        stateLabel() {
            return this.workspace?.state === 'draft' ? 'DRAFT' : 'PUBLICADO';
        },
        stateBadgeStyle() {
            const isDraft = this.workspace?.state === 'draft';
            return {
                background: isDraft ? '#dbeafe' : '#d1fae5',
                color: isDraft ? '#1d4ed8' : '#065f46',
                padding: '1px 8px',
                borderRadius: '9999px',
                fontSize: '11px',
                fontWeight: '600',
            };
        },
        publishBtnStyle() {
            const ok = this.canPublish && !this.publishing;
            return {
                padding: '6px 14px',
                background: ok ? '#16a34a' : '#94a3b8',
                color: '#fff',
                border: 'none',
                borderRadius: '6px',
                cursor: ok ? 'pointer' : 'not-allowed',
                fontSize: '13px',
                fontWeight: '500',
            };
        },
        lastValidated() {
            const ws = this.workspace;
            if (!ws?.last_validated_at)
                return '';
            const d = new Date(ws.last_validated_at);
            return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
        },
    },
    methods: {
        onPublishClick() {
            if (!this.canPublish)
                return;
            this.showPublishModal = true;
        },
        async onPublish(versionName) {
            this.showPublishModal = false;
            const ws = useWorkspaceStore();
            const version = await ws.publish(versionName);
            if (version)
                this.$emit('published', version);
        },
    },
}); /* PartiallyEnd: #3632/script.vue */
function __VLS_template() {
    const __VLS_ctx = {};
    const __VLS_localComponents = {
        ...{ PublishModal },
        ...{},
        ...{},
        ...__VLS_ctx,
    };
    let __VLS_components;
    const __VLS_localDirectives = {
        ...{},
        ...__VLS_ctx,
    };
    let __VLS_directives;
    let __VLS_styleScopedClasses;
    let __VLS_resolvedLocalAndGlobalComponents;
    __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
    __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
    __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
    (__VLS_ctx.projectName);
    __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
    __VLS_elementAsFunction(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({ ...{ style: ((__VLS_ctx.stateBadgeStyle)) }, });
    (__VLS_ctx.stateLabel);
    if (__VLS_ctx.lastValidated) {
        __VLS_elementAsFunction(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({ ...{ style: ({}) }, });
        (__VLS_ctx.lastValidated);
    }
    if (__VLS_ctx.errorCount > 0) {
        __VLS_elementAsFunction(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({ ...{ style: ({}) }, });
        (__VLS_ctx.errorCount);
    }
    if (__VLS_ctx.warningCount > 0) {
        __VLS_elementAsFunction(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({ ...{ style: ({}) }, });
        (__VLS_ctx.warningCount);
    }
    __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
    __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (...[$event]) => {
                __VLS_ctx.$emit('validate');
            } }, disabled: ((__VLS_ctx.validating)), ...{ style: ({}) }, });
    (__VLS_ctx.validating ? 'Validando…' : 'Validar');
    __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
    __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (__VLS_ctx.onPublishClick) }, disabled: ((!__VLS_ctx.canPublish || __VLS_ctx.publishing)), title: ((!__VLS_ctx.canPublish ? `Corrija ${__VLS_ctx.errorCount} erro(s) antes de publicar` : 'Publicar nova versão')), ...{ style: ((__VLS_ctx.publishBtnStyle)) }, });
    (__VLS_ctx.publishing ? 'Publicando…' : 'Publicar');
    if (__VLS_ctx.latestVersion) {
        __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (...[$event]) => {
                    if (!((__VLS_ctx.latestVersion)))
                        return;
                    __VLS_ctx.$emit('export');
                } }, disabled: ((__VLS_ctx.exporting)), ...{ style: ({}) }, });
        (__VLS_ctx.exporting ? 'Exportando…' : `Exportar v${__VLS_ctx.latestVersion.version_number}`);
    }
    if (__VLS_ctx.showPublishModal) {
        const __VLS_0 = __VLS_resolvedLocalAndGlobalComponents.PublishModal;
        /** @type { [typeof __VLS_components.PublishModal, ] } */
        // @ts-ignore
        const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({ ...{ 'onPublish': {} }, ...{ 'onCancel': {} }, }));
        const __VLS_2 = __VLS_1({ ...{ 'onPublish': {} }, ...{ 'onCancel': {} }, }, ...__VLS_functionalComponentArgsRest(__VLS_1));
        let __VLS_6;
        const __VLS_7 = {
            onPublish: (__VLS_ctx.onPublish)
        };
        const __VLS_8 = {
            onCancel: (...[$event]) => {
                if (!((__VLS_ctx.showPublishModal)))
                    return;
                __VLS_ctx.showPublishModal = false;
            }
        };
        let __VLS_3;
        let __VLS_4;
        var __VLS_5;
    }
    var __VLS_slots;
    var __VLS_inheritedAttrs;
    const __VLS_refs = {};
    var $refs;
    var $el;
    return {
        attrs: {},
        slots: __VLS_slots,
        refs: $refs,
        rootEl: $el,
    };
}
;
let __VLS_self;
