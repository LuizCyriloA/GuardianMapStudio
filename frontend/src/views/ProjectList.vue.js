/// <reference types="../../node_modules/.vue-global-types/vue_3.4_false.d.ts" />
import { defineComponent } from 'vue';
import { useProjectStore } from '../stores/project';
import { mapState } from 'pinia';
export default defineComponent({
    name: 'ProjectList',
    emits: ['project-selected'],
    data() {
        return {
            newName: '',
            newDesc: '',
            creating: false,
            createError: '',
        };
    },
    computed: {
        ...mapState(useProjectStore, ['projects', 'loading']),
    },
    async created() {
        await useProjectStore().fetchProjects();
    },
    methods: {
        async createProject() {
            if (!this.newName.trim())
                return;
            this.creating = true;
            this.createError = '';
            try {
                const project = await useProjectStore().createProject(this.newName.trim(), this.newDesc.trim());
                this.newName = '';
                this.newDesc = '';
                this.$emit('project-selected', project.id);
            }
            catch (e) {
                this.createError = 'Erro ao criar projeto';
            }
            finally {
                this.creating = false;
            }
        },
        async openProject(id) {
            await useProjectStore().selectProject(id);
            this.$emit('project-selected', id);
        },
    },
}); /* PartiallyEnd: #3632/script.vue */
function __VLS_template() {
    const __VLS_ctx = {};
    const __VLS_localComponents = {
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
    __VLS_elementAsFunction(__VLS_intrinsicElements.h1, __VLS_intrinsicElements.h1)({ ...{ style: ({}) }, });
    __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
    __VLS_elementAsFunction(__VLS_intrinsicElements.h2, __VLS_intrinsicElements.h2)({ ...{ style: ({}) }, });
    __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
    __VLS_elementAsFunction(__VLS_intrinsicElements.input)({ ...{ onKeydown: (__VLS_ctx.createProject) }, placeholder: ("Nome do projeto"), ...{ style: ({}) }, });
    (__VLS_ctx.newName);
    __VLS_elementAsFunction(__VLS_intrinsicElements.input)({ placeholder: ("Descrição (opcional)"), ...{ style: ({}) }, });
    (__VLS_ctx.newDesc);
    __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (__VLS_ctx.createProject) }, disabled: ((!__VLS_ctx.newName.trim() || __VLS_ctx.creating)), ...{ style: ({}) }, });
    (__VLS_ctx.creating ? 'Criando…' : '+ Criar');
    if (__VLS_ctx.createError) {
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
        (__VLS_ctx.createError);
    }
    if (__VLS_ctx.loading) {
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
    }
    else if (__VLS_ctx.projects.length === 0) {
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
    }
    else {
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
        for (const [p] of __VLS_getVForSourceType((__VLS_ctx.projects))) {
            __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ onClick: (...[$event]) => {
                        if (!(!((__VLS_ctx.loading))))
                            return;
                        if (!(!((__VLS_ctx.projects.length === 0))))
                            return;
                        __VLS_ctx.openProject(p.id);
                    } }, ...{ onMouseover: (...[$event]) => {
                        if (!(!((__VLS_ctx.loading))))
                            return;
                        if (!(!((__VLS_ctx.projects.length === 0))))
                            return;
                        $event.currentTarget.style.borderColor = '#1d4ed8';
                    } }, ...{ onMouseleave: (...[$event]) => {
                        if (!(!((__VLS_ctx.loading))))
                            return;
                        if (!(!((__VLS_ctx.projects.length === 0))))
                            return;
                        $event.currentTarget.style.borderColor = '#e2e8f0';
                    } }, key: ((p.id)), ...{ style: ({}) }, });
            __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
            __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
            (p.name);
            if (p.description) {
                __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
                (p.description);
            }
            __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
            (new Date(p.created_at).toLocaleDateString('pt-BR'));
            __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
        }
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
