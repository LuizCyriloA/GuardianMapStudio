/// <reference types="../../../node_modules/.vue-global-types/vue_3.4_false.d.ts" />
import { defineComponent } from 'vue';
import { useWorkspaceStore } from '../../stores/workspace';
import { useMapStore } from '../../stores/map';
import { mapState } from 'pinia';
export default defineComponent({
    name: 'ValidationPanel',
    computed: {
        ...mapState(useWorkspaceStore, ['validation']),
    },
    methods: {
        resultStyle(severity) {
            return {
                padding: '8px',
                marginBottom: '6px',
                borderRadius: '4px',
                cursor: 'pointer',
                background: severity === 'error' ? '#fef2f2' : '#fffbeb',
                borderLeft: `3px solid ${severity === 'error' ? '#dc2626' : '#d97706'}`,
                transition: 'opacity .15s',
            };
        },
        onClickResult(r) {
            const mapStore = useMapStore();
            const typeMap = {
                road: 'road',
                waypoint: 'waypoint',
                crossroad: 'crossroad',
                restricted_area: 'restricted_area',
                workspace: 'road',
            };
            const type = typeMap[r.affected_entity_type] ?? 'road';
            if (r.affected_entity_id > 0) {
                mapStore.selectEntity(type, r.affected_entity_id);
            }
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
    __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
    if (__VLS_ctx.validation) {
        __VLS_elementAsFunction(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({ ...{ style: ({}) }, });
        if (__VLS_ctx.validation.error_count > 0) {
            __VLS_elementAsFunction(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({ ...{ style: ({}) }, });
            (__VLS_ctx.validation.error_count);
        }
        if (__VLS_ctx.validation.warning_count > 0) {
            __VLS_elementAsFunction(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({ ...{ style: ({}) }, });
            (__VLS_ctx.validation.warning_count);
        }
        if (__VLS_ctx.validation.error_count === 0 && __VLS_ctx.validation.warning_count === 0) {
            __VLS_elementAsFunction(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({ ...{ style: ({}) }, });
        }
    }
    else {
        __VLS_elementAsFunction(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({ ...{ style: ({}) }, });
    }
    if (__VLS_ctx.validation && __VLS_ctx.validation.results.length) {
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
        for (const [r] of __VLS_getVForSourceType((__VLS_ctx.validation.results))) {
            __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ onClick: (...[$event]) => {
                        if (!((__VLS_ctx.validation && __VLS_ctx.validation.results.length)))
                            return;
                        __VLS_ctx.onClickResult(r);
                    } }, key: ((r.id)), ...{ style: ((__VLS_ctx.resultStyle(r.severity))) }, });
            __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
            __VLS_elementAsFunction(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({ ...{ style: (({ color: r.severity === 'error' ? '#dc2626' : '#d97706', fontSize: '16px' })) }, });
            (r.severity === 'error' ? '●' : '○');
            __VLS_elementAsFunction(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({ ...{ style: ({}) }, });
            (r.affected_entity_type);
            __VLS_elementAsFunction(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({ ...{ style: ({}) }, });
            (r.rule_id);
            __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
            (r.message);
        }
    }
    else if (__VLS_ctx.validation && __VLS_ctx.validation.results.length === 0) {
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
    }
    else {
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
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
