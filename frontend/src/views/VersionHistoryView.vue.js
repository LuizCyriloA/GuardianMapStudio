/// <reference types="../../node_modules/.vue-global-types/vue_3.4_false.d.ts" />
import { defineComponent } from 'vue';
import VersionList from '../components/version/VersionList.vue';
import VersionPreview from '../components/version/VersionPreview.vue';
import { useProjectStore } from '../stores/project';
import { mapState } from 'pinia';
export default defineComponent({
    name: 'VersionHistoryView',
    components: { VersionList, VersionPreview },
    data() {
        return { previewingVersion: null };
    },
    computed: {
        ...mapState(useProjectStore, ['currentProject', 'versions']),
    },
    async created() {
        const store = useProjectStore();
        if (store.currentProject) {
            await store.fetchVersions(store.currentProject.id);
        }
    },
    methods: {
        showPreview(version) {
            this.previewingVersion = version;
        },
    },
}); /* PartiallyEnd: #3632/script.vue */
function __VLS_template() {
    const __VLS_ctx = {};
    const __VLS_localComponents = {
        ...{ VersionList, VersionPreview },
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
    __VLS_elementAsFunction(__VLS_intrinsicElements.h1, __VLS_intrinsicElements.h1)({ ...{ style: ({}) }, });
    (__VLS_ctx.currentProject?.name ?? '');
    if (__VLS_ctx.previewingVersion) {
        __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (...[$event]) => {
                    if (!((__VLS_ctx.previewingVersion)))
                        return;
                    __VLS_ctx.previewingVersion = null;
                } }, ...{ style: ({}) }, });
    }
    if (!__VLS_ctx.previewingVersion) {
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
        const __VLS_0 = __VLS_resolvedLocalAndGlobalComponents.VersionList;
        /** @type { [typeof __VLS_components.VersionList, ] } */
        // @ts-ignore
        const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({ ...{ 'onPreview': {} }, versions: ((__VLS_ctx.versions)), }));
        const __VLS_2 = __VLS_1({ ...{ 'onPreview': {} }, versions: ((__VLS_ctx.versions)), }, ...__VLS_functionalComponentArgsRest(__VLS_1));
        let __VLS_6;
        const __VLS_7 = {
            onPreview: (__VLS_ctx.showPreview)
        };
        let __VLS_3;
        let __VLS_4;
        var __VLS_5;
    }
    if (__VLS_ctx.previewingVersion) {
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
        const __VLS_8 = __VLS_resolvedLocalAndGlobalComponents.VersionPreview;
        /** @type { [typeof __VLS_components.VersionPreview, ] } */
        // @ts-ignore
        const __VLS_9 = __VLS_asFunctionalComponent(__VLS_8, new __VLS_8({ version: ((__VLS_ctx.previewingVersion)), }));
        const __VLS_10 = __VLS_9({ version: ((__VLS_ctx.previewingVersion)), }, ...__VLS_functionalComponentArgsRest(__VLS_9));
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
