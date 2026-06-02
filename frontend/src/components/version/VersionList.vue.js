/// <reference types="../../../node_modules/.vue-global-types/vue_3.4_false.d.ts" />
import { defineComponent } from 'vue';
import { api } from '../../api/client';
export default defineComponent({
    name: 'VersionList',
    props: {
        versions: { type: Array, default: () => [] },
    },
    emits: ['preview'],
    computed: {
        sortedVersions() {
            return [...this.versions].sort((a, b) => b.version_number - a.version_number);
        },
    },
    methods: {
        formatDate(iso) {
            return new Date(iso).toLocaleDateString('pt-BR');
        },
        downloadUrl(versionId) {
            return api.downloadExportUrl(versionId);
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
    __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
    if (__VLS_ctx.versions.length === 0) {
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
    }
    else {
        __VLS_elementAsFunction(__VLS_intrinsicElements.table, __VLS_intrinsicElements.table)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.thead, __VLS_intrinsicElements.thead)({});
        __VLS_elementAsFunction(__VLS_intrinsicElements.tr, __VLS_intrinsicElements.tr)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.th, __VLS_intrinsicElements.th)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.th, __VLS_intrinsicElements.th)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.th, __VLS_intrinsicElements.th)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.th, __VLS_intrinsicElements.th)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.th, __VLS_intrinsicElements.th)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.tbody, __VLS_intrinsicElements.tbody)({});
        for (const [v] of __VLS_getVForSourceType((__VLS_ctx.sortedVersions))) {
            __VLS_elementAsFunction(__VLS_intrinsicElements.tr, __VLS_intrinsicElements.tr)({ key: ((v.id)), ...{ style: ({}) }, });
            __VLS_elementAsFunction(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({ ...{ style: ({}) }, });
            (v.version_number);
            __VLS_elementAsFunction(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({ ...{ style: ({}) }, });
            (v.name);
            __VLS_elementAsFunction(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({ ...{ style: ({}) }, });
            (__VLS_ctx.formatDate(v.published_at));
            __VLS_elementAsFunction(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({ ...{ style: ({}) }, });
            (v.road_count);
            (v.waypoint_count);
            __VLS_elementAsFunction(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({ ...{ style: ({}) }, });
            __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (...[$event]) => {
                        if (!(!((__VLS_ctx.versions.length === 0))))
                            return;
                        __VLS_ctx.$emit('preview', v);
                    } }, ...{ style: ({}) }, });
            __VLS_elementAsFunction(__VLS_intrinsicElements.a, __VLS_intrinsicElements.a)({ href: ((__VLS_ctx.downloadUrl(v.id))), download: (true), ...{ style: ({}) }, });
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
