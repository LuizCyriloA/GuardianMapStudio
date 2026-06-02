/// <reference types="../../../node_modules/.vue-global-types/vue_3.4_false.d.ts" />
import { defineComponent } from 'vue';
export default defineComponent({
    name: 'ConfirmModal',
    props: {
        visible: { type: Boolean, required: true },
        title: { type: String, required: true },
        message: { type: String, required: true },
        items: { type: Array, default: () => [] },
        confirmLabel: { type: String, default: 'Sim, excluir' },
        cancelLabel: { type: String, default: 'Cancelar' },
    },
    emits: ['confirm', 'cancel'],
    watch: {
        visible(v) {
            if (v) {
                // Cancel is the default focused action — protects against accidental Enter-key confirmations
                this.$nextTick(() => this.$refs.cancelBtn?.focus());
            }
        },
    },
    mounted() {
        document.addEventListener('keydown', this.onKey);
    },
    beforeUnmount() {
        document.removeEventListener('keydown', this.onKey);
    },
    methods: {
        onConfirm() { this.$emit('confirm'); },
        onCancel() { this.$emit('cancel'); },
        onKey(e) {
            if (this.visible && e.key === 'Escape') {
                e.preventDefault();
                this.onCancel();
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
    if (__VLS_ctx.visible) {
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ onClick: (__VLS_ctx.onCancel) }, ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ role: ("dialog"), "aria-modal": ("true"), ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.h3, __VLS_intrinsicElements.h3)({ ...{ style: ({}) }, });
        (__VLS_ctx.title);
        __VLS_elementAsFunction(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({ ...{ style: ({}) }, });
        (__VLS_ctx.message);
        if (__VLS_ctx.items.length) {
            __VLS_elementAsFunction(__VLS_intrinsicElements.ul, __VLS_intrinsicElements.ul)({ ...{ style: ({}) }, });
            for (const [item, idx] of __VLS_getVForSourceType((__VLS_ctx.items.slice(0, 10)))) {
                __VLS_elementAsFunction(__VLS_intrinsicElements.li, __VLS_intrinsicElements.li)({ key: ((idx)), });
                (item);
            }
            if (__VLS_ctx.items.length > 10) {
                __VLS_elementAsFunction(__VLS_intrinsicElements.li, __VLS_intrinsicElements.li)({ ...{ style: ({}) }, });
                (__VLS_ctx.items.length - 10);
            }
        }
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (__VLS_ctx.onCancel) }, ref: ("cancelBtn"), ...{ style: ({}) }, });
        // @ts-ignore navigation for `const cancelBtn = ref()`
        __VLS_ctx.cancelBtn;
        (__VLS_ctx.cancelLabel);
        __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (__VLS_ctx.onConfirm) }, ...{ style: ({}) }, });
        (__VLS_ctx.confirmLabel);
    }
    var __VLS_slots;
    var __VLS_inheritedAttrs;
    const __VLS_refs = {
        "cancelBtn": __VLS_nativeElements['button'],
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
