import { defineComponent } from 'vue';
import { useProjectStore } from '../../stores/project';
import { mapState } from 'pinia';
export default defineComponent({
    name: 'AppSidebar',
    props: {
        currentView: { type: String, required: true },
    },
    emits: ['navigate'],
    computed: {
        ...mapState(useProjectStore, ['currentProject']),
    },
    methods: {
        navStyle(active) {
            return {
                display: 'block',
                width: '100%',
                textAlign: 'left',
                padding: '10px 20px',
                background: active ? '#1d4ed8' : 'transparent',
                color: active ? '#fff' : '#cbd5e1',
                border: 'none',
                cursor: 'pointer',
                fontSize: '14px',
                transition: 'background .15s',
            };
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
    __VLS_elementAsFunction(__VLS_intrinsicElements.nav, __VLS_intrinsicElements.nav)({ ...{ style: ({}) }, });
    __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
    __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
    __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
    if (__VLS_ctx.currentProject) {
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
        (__VLS_ctx.currentProject.name);
    }
    __VLS_elementAsFunction(__VLS_intrinsicElements.ul, __VLS_intrinsicElements.ul)({ ...{ style: ({}) }, });
    __VLS_elementAsFunction(__VLS_intrinsicElements.li, __VLS_intrinsicElements.li)({});
    __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (...[$event]) => {
                __VLS_ctx.$emit('navigate', 'projects');
            } }, ...{ style: ((__VLS_ctx.navStyle(__VLS_ctx.currentView === 'projects'))) }, });
    if (__VLS_ctx.currentProject) {
        __VLS_elementAsFunction(__VLS_intrinsicElements.li, __VLS_intrinsicElements.li)({});
        __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (...[$event]) => {
                    if (!((__VLS_ctx.currentProject)))
                        return;
                    __VLS_ctx.$emit('navigate', 'editor');
                } }, ...{ style: ((__VLS_ctx.navStyle(__VLS_ctx.currentView === 'editor'))) }, });
    }
    if (__VLS_ctx.currentProject) {
        __VLS_elementAsFunction(__VLS_intrinsicElements.li, __VLS_intrinsicElements.li)({});
        __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (...[$event]) => {
                    if (!((__VLS_ctx.currentProject)))
                        return;
                    __VLS_ctx.$emit('navigate', 'history');
                } }, ...{ style: ((__VLS_ctx.navStyle(__VLS_ctx.currentView === 'history'))) }, });
    }
    __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
    __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
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
