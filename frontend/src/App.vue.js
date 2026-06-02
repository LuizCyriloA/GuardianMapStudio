/// <reference types="../node_modules/.vue-global-types/vue_3.4_false.d.ts" />
import { defineComponent } from 'vue';
import AppSidebar from './components/layout/AppSidebar.vue';
import ProjectList from './views/ProjectList.vue';
import EditorView from './views/EditorView.vue';
import VersionHistoryView from './views/VersionHistoryView.vue';
import { useProjectStore } from './stores/project';
import { useWorkspaceStore } from './stores/workspace';
import { useMapStore } from './stores/map';
export default defineComponent({
    name: 'App',
    components: { AppSidebar, ProjectList, EditorView, VersionHistoryView },
    data() {
        return {
            currentView: 'projects',
            editorMounted: false,
        };
    },
    methods: {
        navigate(view) {
            this.currentView = view;
            if (view === 'editor') {
                this.editorMounted = true;
                // Let Leaflet re-measure after potential display change
                this.$nextTick(() => {
                    const editorView = this.$refs.editorView;
                    if (editorView) {
                        const mapEl = editorView.$el?.querySelector('#guardian-map');
                        if (mapEl) {
                            // Trigger invalidateSize via the MapEditor ref
                            const mapEditorRef = editorView.$refs?.mapEditor;
                            mapEditorRef?.invalidateSize();
                        }
                    }
                });
            }
        },
        async onProjectSelected(projectId) {
            const proj = useProjectStore();
            await proj.selectProject(projectId);
            const ws = useWorkspaceStore();
            await ws.fetchWorkspace(projectId);
            if (ws.workspace) {
                const map = useMapStore();
                await map.fetchMap(ws.workspace.id);
                await ws.loadValidation();
            }
            this.editorMounted = true;
            this.currentView = 'editor';
        },
    },
    // Expose delete entity for Leaflet popup buttons
    mounted() {
        // deleteEntity is exposed via main.ts window.guardianApp
    },
}); /* PartiallyEnd: #3632/script.vue */
function __VLS_template() {
    const __VLS_ctx = {};
    const __VLS_localComponents = {
        ...{ AppSidebar, ProjectList, EditorView, VersionHistoryView },
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
    const __VLS_0 = __VLS_resolvedLocalAndGlobalComponents.AppSidebar;
    /** @type { [typeof __VLS_components.AppSidebar, ] } */
    // @ts-ignore
    const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({ ...{ 'onNavigate': {} }, currentView: ((__VLS_ctx.currentView)), }));
    const __VLS_2 = __VLS_1({ ...{ 'onNavigate': {} }, currentView: ((__VLS_ctx.currentView)), }, ...__VLS_functionalComponentArgsRest(__VLS_1));
    let __VLS_6;
    const __VLS_7 = {
        onNavigate: (__VLS_ctx.navigate)
    };
    let __VLS_3;
    let __VLS_4;
    var __VLS_5;
    __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
    if (__VLS_ctx.currentView === 'projects') {
        const __VLS_8 = __VLS_resolvedLocalAndGlobalComponents.ProjectList;
        /** @type { [typeof __VLS_components.ProjectList, ] } */
        // @ts-ignore
        const __VLS_9 = __VLS_asFunctionalComponent(__VLS_8, new __VLS_8({ ...{ 'onProjectSelected': {} }, }));
        const __VLS_10 = __VLS_9({ ...{ 'onProjectSelected': {} }, }, ...__VLS_functionalComponentArgsRest(__VLS_9));
        let __VLS_14;
        const __VLS_15 = {
            onProjectSelected: (__VLS_ctx.onProjectSelected)
        };
        let __VLS_11;
        let __VLS_12;
        var __VLS_13;
    }
    if (__VLS_ctx.editorMounted) {
        const __VLS_16 = __VLS_resolvedLocalAndGlobalComponents.EditorView;
        /** @type { [typeof __VLS_components.EditorView, ] } */
        // @ts-ignore
        const __VLS_17 = __VLS_asFunctionalComponent(__VLS_16, new __VLS_16({ ref: ("editorView"), }));
        const __VLS_18 = __VLS_17({ ref: ("editorView"), }, ...__VLS_functionalComponentArgsRest(__VLS_17));
        __VLS_asFunctionalDirective(__VLS_directives.vShow)(null, { ...__VLS_directiveBindingRestFields, value: (__VLS_ctx.currentView === 'editor') }, null, null);
        // @ts-ignore navigation for `const editorView = ref()`
        __VLS_ctx.editorView;
        var __VLS_22 = {};
        var __VLS_21;
    }
    if (__VLS_ctx.currentView === 'history') {
        const __VLS_23 = __VLS_resolvedLocalAndGlobalComponents.VersionHistoryView;
        /** @type { [typeof __VLS_components.VersionHistoryView, ] } */
        // @ts-ignore
        const __VLS_24 = __VLS_asFunctionalComponent(__VLS_23, new __VLS_23({}));
        const __VLS_25 = __VLS_24({}, ...__VLS_functionalComponentArgsRest(__VLS_24));
    }
    var __VLS_slots;
    var __VLS_inheritedAttrs;
    const __VLS_refs = {
        "editorView": __VLS_22,
    };
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
