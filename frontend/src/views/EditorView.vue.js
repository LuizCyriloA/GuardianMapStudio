/// <reference types="../../node_modules/.vue-global-types/vue_3.4_false.d.ts" />
import { defineComponent } from 'vue';
import WorkspaceHeader from '../components/workspace/WorkspaceHeader.vue';
import MapEditor from '../components/map/MapEditor.vue';
import EntityForm from '../components/map/EntityForm.vue';
import ValidationPanel from '../components/layout/ValidationPanel.vue';
import MapLegend from '../components/map/MapLegend.vue';
import { useProjectStore } from '../stores/project';
import { useWorkspaceStore } from '../stores/workspace';
import { useMapStore } from '../stores/map';
export default defineComponent({
    name: 'EditorView',
    components: { WorkspaceHeader, MapEditor, EntityForm, ValidationPanel, MapLegend },
    data() {
        return {
            showEntityForm: false,
            entityFormMode: 'create',
            entityFormType: '',
            entityFormData: {},
        };
    },
    async mounted() {
        const ws = useWorkspaceStore();
        const proj = useProjectStore();
        const map = useMapStore();
        if (!ws.workspace && proj.currentProject) {
            await ws.fetchWorkspace(proj.currentProject.id);
        }
        if (ws.workspace) {
            await map.fetchMap(ws.workspace.id);
            await ws.loadValidation();
        }
    },
    methods: {
        onEntityForm({ entityType, initialData }) {
            this.entityFormType = entityType;
            this.entityFormData = initialData;
            this.entityFormMode = 'create';
            this.showEntityForm = true;
        },
        onEntitySelected({ type, id }) {
            const mapStore = useMapStore();
            mapStore.selectEntity(type, id);
        },
        closeEntityForm() {
            this.showEntityForm = false;
        },
        async onEntitySaved() {
            this.showEntityForm = false;
            await this.runValidation();
        },
        async runValidation() {
            await useWorkspaceStore().runValidation();
            const editor = this.$refs.mapEditor;
            editor?.renderValidation();
        },
        async onPublished(version) {
            const proj = useProjectStore();
            const ws = useWorkspaceStore();
            const map = useMapStore();
            // Reload workspace (new DRAFT was created by backend)
            if (proj.currentProject) {
                await proj.fetchVersions(proj.currentProject.id);
                await ws.fetchWorkspace(proj.currentProject.id);
            }
            if (ws.workspace) {
                await map.fetchMap(ws.workspace.id);
            }
            ws.validation = null;
        },
        async onExport() {
            const proj = useProjectStore();
            const latestVersion = proj.latestVersion;
            if (!latestVersion)
                return;
            await useWorkspaceStore().exportVersion(latestVersion.id);
        },
    },
}); /* PartiallyEnd: #3632/script.vue */
function __VLS_template() {
    const __VLS_ctx = {};
    const __VLS_localComponents = {
        ...{ WorkspaceHeader, MapEditor, EntityForm, ValidationPanel, MapLegend },
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
    const __VLS_0 = __VLS_resolvedLocalAndGlobalComponents.WorkspaceHeader;
    /** @type { [typeof __VLS_components.WorkspaceHeader, ] } */
    // @ts-ignore
    const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({ ...{ 'onValidate': {} }, ...{ 'onExport': {} }, ...{ 'onPublished': {} }, }));
    const __VLS_2 = __VLS_1({ ...{ 'onValidate': {} }, ...{ 'onExport': {} }, ...{ 'onPublished': {} }, }, ...__VLS_functionalComponentArgsRest(__VLS_1));
    let __VLS_6;
    const __VLS_7 = {
        onValidate: (__VLS_ctx.runValidation)
    };
    const __VLS_8 = {
        onExport: (__VLS_ctx.onExport)
    };
    const __VLS_9 = {
        onPublished: (__VLS_ctx.onPublished)
    };
    let __VLS_3;
    let __VLS_4;
    var __VLS_5;
    __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
    const __VLS_10 = __VLS_resolvedLocalAndGlobalComponents.MapEditor;
    /** @type { [typeof __VLS_components.MapEditor, ] } */
    // @ts-ignore
    const __VLS_11 = __VLS_asFunctionalComponent(__VLS_10, new __VLS_10({ ...{ 'onEntityForm': {} }, ...{ 'onEntitySelected': {} }, ref: ("mapEditor"), ...{ style: ({}) }, }));
    const __VLS_12 = __VLS_11({ ...{ 'onEntityForm': {} }, ...{ 'onEntitySelected': {} }, ref: ("mapEditor"), ...{ style: ({}) }, }, ...__VLS_functionalComponentArgsRest(__VLS_11));
    // @ts-ignore navigation for `const mapEditor = ref()`
    __VLS_ctx.mapEditor;
    var __VLS_16 = {};
    let __VLS_17;
    const __VLS_18 = {
        onEntityForm: (__VLS_ctx.onEntityForm)
    };
    const __VLS_19 = {
        onEntitySelected: (__VLS_ctx.onEntitySelected)
    };
    let __VLS_13;
    let __VLS_14;
    var __VLS_15;
    __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
    if (__VLS_ctx.showEntityForm) {
        const __VLS_20 = __VLS_resolvedLocalAndGlobalComponents.EntityForm;
        /** @type { [typeof __VLS_components.EntityForm, ] } */
        // @ts-ignore
        const __VLS_21 = __VLS_asFunctionalComponent(__VLS_20, new __VLS_20({ ...{ 'onSaved': {} }, ...{ 'onCancel': {} }, mode: ((__VLS_ctx.entityFormMode)), entityType: ((__VLS_ctx.entityFormType)), initialData: ((__VLS_ctx.entityFormData)), }));
        const __VLS_22 = __VLS_21({ ...{ 'onSaved': {} }, ...{ 'onCancel': {} }, mode: ((__VLS_ctx.entityFormMode)), entityType: ((__VLS_ctx.entityFormType)), initialData: ((__VLS_ctx.entityFormData)), }, ...__VLS_functionalComponentArgsRest(__VLS_21));
        let __VLS_26;
        const __VLS_27 = {
            onSaved: (__VLS_ctx.onEntitySaved)
        };
        const __VLS_28 = {
            onCancel: (__VLS_ctx.closeEntityForm)
        };
        let __VLS_23;
        let __VLS_24;
        var __VLS_25;
    }
    const __VLS_29 = __VLS_resolvedLocalAndGlobalComponents.ValidationPanel;
    /** @type { [typeof __VLS_components.ValidationPanel, ] } */
    // @ts-ignore
    const __VLS_30 = __VLS_asFunctionalComponent(__VLS_29, new __VLS_29({ ...{ style: ({}) }, }));
    const __VLS_31 = __VLS_30({ ...{ style: ({}) }, }, ...__VLS_functionalComponentArgsRest(__VLS_30));
    const __VLS_35 = __VLS_resolvedLocalAndGlobalComponents.MapLegend;
    /** @type { [typeof __VLS_components.MapLegend, ] } */
    // @ts-ignore
    const __VLS_36 = __VLS_asFunctionalComponent(__VLS_35, new __VLS_35({}));
    const __VLS_37 = __VLS_36({}, ...__VLS_functionalComponentArgsRest(__VLS_36));
    var __VLS_slots;
    var __VLS_inheritedAttrs;
    const __VLS_refs = {
        "mapEditor": __VLS_16,
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
