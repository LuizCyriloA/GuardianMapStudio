/// <reference types="../../../node_modules/.vue-global-types/vue_3.4_false.d.ts" />
import { defineComponent } from 'vue';
export default defineComponent({
    name: 'MapLegend',
    data() {
        return {
            items: [
                { letter: 'P', color: '#E24B4A', label: 'Parada' },
                { letter: 'L', color: '#EF9F27', label: 'Lombada' },
                { letter: 'G', color: '#1D9E75', label: 'Portão' },
                { letter: 'C', color: '#888780', label: 'Curva' },
                { letter: 'M', color: '#534AB7', label: 'Marco' },
                { letter: 'S', color: '#378ADD', label: 'Zona' },
            ],
        };
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
    __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
    for (const [item] of __VLS_getVForSourceType((__VLS_ctx.items))) {
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ key: ((item.label)), ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: (({ width: '14px', height: '14px', borderRadius: '50%', background: item.color, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: '9px', fontWeight: '700' })) }, });
        (item.letter);
        __VLS_elementAsFunction(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({ ...{ style: ({}) }, });
        (item.label);
    }
    __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
    __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
    __VLS_elementAsFunction(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({ ...{ style: ({}) }, });
    __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
    __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
    __VLS_elementAsFunction(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({ ...{ style: ({}) }, });
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
