/// <reference types="../../../node_modules/.vue-global-types/vue_3.4_false.d.ts" />
import { defineComponent } from 'vue';
import { useMapStore } from '../../stores/map';
export default defineComponent({
    name: 'RoadQuickSelect',
    emits: ['road-selected', 'selection-cleared'],
    data() {
        return {
            query: '',
        };
    },
    computed: {
        sortedRoads() {
            const store = useMapStore();
            // Cloned + sorted alphabetically (case-insensitive, locale-aware
            // so "São" sorts naturally for the operator).
            return [...store.roads].sort((a, b) => a.name.localeCompare(b.name, 'pt-BR', { sensitivity: 'base' }));
        },
        hasRoads() {
            return useMapStore().roads.length > 0;
        },
        placeholder() {
            const count = useMapStore().roads.length;
            if (count === 0)
                return 'Nenhuma rua cadastrada';
            return `Digite ou escolha (${count} ruas)`;
        },
    },
    methods: {
        onChange() {
            const name = this.query.trim();
            if (!name)
                return;
            const store = useMapStore();
            const road = store.roads.find(r => r.name.toLowerCase() === name.toLowerCase());
            if (!road) {
                // The user typed something that isn't a road name. Do nothing —
                // datalist filtering will guide them. Don't show an alert.
                return;
            }
            store.selectRoad(road.id);
            // Centering and panel-opening are delegated to MapEditor via event,
            // because RoadQuickSelect must not depend on the Leaflet map instance.
            this.$emit('road-selected', road.id);
        },
        onClear() {
            this.query = '';
            useMapStore().clearRoadSelection();
            const inp = this.$refs.input;
            if (inp)
                inp.focus();
            this.$emit('selection-cleared');
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
    __VLS_styleScopedClasses['rqs-input'];
    __VLS_styleScopedClasses['rqs-input'];
    __VLS_styleScopedClasses['rqs-clear'];
    // CSS variable injection 
    // CSS variable injection end 
    let __VLS_resolvedLocalAndGlobalComponents;
    __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ class: ("road-quick-select") }, });
    __VLS_elementAsFunction(__VLS_intrinsicElements.label, __VLS_intrinsicElements.label)({ ...{ class: ("rqs-label") }, for: ("rqs-input"), });
    __VLS_elementAsFunction(__VLS_intrinsicElements.input)({ ...{ onChange: (__VLS_ctx.onChange) }, ...{ onKeydown: (__VLS_ctx.onChange) }, id: ("rqs-input"), ref: ("input"), value: ((__VLS_ctx.query)), list: ("rqs-roads-list"), type: ("text"), placeholder: ((__VLS_ctx.placeholder)), ...{ class: ("rqs-input") }, disabled: ((!__VLS_ctx.hasRoads)), autocomplete: ("off"), });
    // @ts-ignore navigation for `const input = ref()`
    __VLS_ctx.input;
    __VLS_elementAsFunction(__VLS_intrinsicElements.datalist, __VLS_intrinsicElements.datalist)({ id: ("rqs-roads-list"), });
    for (const [road] of __VLS_getVForSourceType((__VLS_ctx.sortedRoads))) {
        __VLS_elementAsFunction(__VLS_intrinsicElements.option)({ key: ((road.id)), value: ((road.name)), });
    }
    if (__VLS_ctx.query) {
        __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (__VLS_ctx.onClear) }, ...{ class: ("rqs-clear") }, type: ("button"), title: ("Limpar busca"), });
    }
    __VLS_styleScopedClasses['road-quick-select'];
    __VLS_styleScopedClasses['rqs-label'];
    __VLS_styleScopedClasses['rqs-input'];
    __VLS_styleScopedClasses['rqs-clear'];
    var __VLS_slots;
    var __VLS_inheritedAttrs;
    const __VLS_refs = {
        "input": __VLS_nativeElements['input'],
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
