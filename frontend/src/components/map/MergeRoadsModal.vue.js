import { defineComponent } from 'vue';
import { api } from '../../api/client';
import { useMapStore } from '../../stores/map';
import { useWorkspaceStore } from '../../stores/workspace';
import { useUndoStore } from '../../stores/undo';
export default defineComponent({
    name: 'MergeRoadsModal',
    props: {
        workspaceId: { type: Number, required: true },
        visible: { type: Boolean, default: false },
    },
    emits: ['close', 'merged'],
    data() {
        return {
            state: 'loading',
            groups: [],
            selectedGroups: new Set(),
            mergeResults: [],
            errorMessage: '',
        };
    },
    computed: {
        totalDeleted() {
            return this.mergeResults.reduce((s, r) => s + r.deleted_road_ids.length, 0);
        },
        totalGaps() {
            return this.mergeResults.reduce((s, r) => s + r.gaps_meters.length, 0);
        },
        nameInputStyle() {
            return {
                background: '#0f172a',
                border: '1px solid #475569',
                borderRadius: '4px',
                color: '#e2e8f0',
                fontSize: '13px',
                padding: '4px 8px',
            };
        },
    },
    mounted() {
        this.loadGroups();
    },
    methods: {
        onBackdropClick() {
            if (this.state === 'preview' || this.state === 'empty' || this.state === 'error') {
                this.$emit('close');
            }
        },
        async loadGroups() {
            this.state = 'loading';
            try {
                const data = await api.getDuplicateGroups(this.workspaceId);
                if (data.groups.length === 0) {
                    this.state = 'empty';
                    return;
                }
                this.groups = data.groups.map(g => ({
                    base_name: g.base_name,
                    road_ids: g.road_ids,
                    road_names: g.road_names,
                    road_points: this.estimatePoints(g.total_points, g.road_ids.length),
                    editedName: g.base_name,
                }));
                this.selectedGroups = new Set(this.groups.map((_, i) => i));
                this.state = 'preview';
            }
            catch (err) {
                const e = err;
                this.errorMessage = e?.detail?.message ?? 'Erro ao buscar grupos duplicados.';
                this.state = 'error';
            }
        },
        estimatePoints(total, count) {
            // Distribute total points evenly (exact counts come from road objects, approximated here)
            const per = Math.floor(total / count);
            return Array(count).fill(per);
        },
        toggleGroup(idx) {
            const next = new Set(this.selectedGroups);
            if (next.has(idx))
                next.delete(idx);
            else
                next.add(idx);
            this.selectedGroups = next;
        },
        async startMerge() {
            const groupsToMerge = [...this.selectedGroups].map(i => ({
                target_name: this.groups[i].editedName || this.groups[i].base_name,
                source_road_ids: this.groups[i].road_ids,
            }));
            this.state = 'merging';
            try {
                const result = await api.mergeRoads(this.workspaceId, groupsToMerge);
                this.mergeResults = result.results;
                this.state = 'done';
                // Reload map + validation + recenter
                const mapStore = useMapStore();
                const wsStore = useWorkspaceStore();
                await mapStore.fetchMap(this.workspaceId);
                await wsStore.runValidation();
                mapStore.triggerRecenter();
                // Merge is NOT undoable — clear undo stack
                useUndoStore().clear();
                this.$emit('merged', result);
            }
            catch (err) {
                const e = err;
                this.errorMessage = e?.detail?.message ?? 'Erro ao mesclar ruas.';
                this.state = 'error';
            }
        },
        btnPrimary(enabled) {
            return {
                padding: '8px 18px',
                background: enabled ? '#1d4ed8' : '#334155',
                color: '#fff',
                border: 'none',
                borderRadius: '4px',
                cursor: enabled ? 'pointer' : 'not-allowed',
                fontSize: '13px',
                opacity: enabled ? '1' : '0.6',
            };
        },
        btnSecondary() {
            return {
                padding: '8px 18px',
                background: '#334155',
                color: '#e2e8f0',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '13px',
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
    __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ onClick: (__VLS_ctx.onBackdropClick) }, ...{ style: ({}) }, });
    __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
    __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
    __VLS_elementAsFunction(__VLS_intrinsicElements.h3, __VLS_intrinsicElements.h3)({ ...{ style: ({}) }, });
    __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (...[$event]) => {
                __VLS_ctx.$emit('close');
            } }, ...{ style: ({}) }, });
    __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
    if (__VLS_ctx.state === 'loading') {
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
    }
    else if (__VLS_ctx.state === 'empty') {
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (...[$event]) => {
                    if (!(!((__VLS_ctx.state === 'loading'))))
                        return;
                    if (!((__VLS_ctx.state === 'empty')))
                        return;
                    __VLS_ctx.$emit('close');
                } }, ...{ style: ((__VLS_ctx.btnSecondary())) }, ...{ style: ({}) }, });
    }
    else if (__VLS_ctx.state === 'preview') {
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
        for (const [grp, idx] of __VLS_getVForSourceType((__VLS_ctx.groups))) {
            __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ key: ((idx)), ...{ style: ({}) }, });
            __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
            __VLS_elementAsFunction(__VLS_intrinsicElements.input)({ ...{ onChange: (...[$event]) => {
                        if (!(!((__VLS_ctx.state === 'loading'))))
                            return;
                        if (!(!((__VLS_ctx.state === 'empty'))))
                            return;
                        if (!((__VLS_ctx.state === 'preview')))
                            return;
                        __VLS_ctx.toggleGroup(idx);
                    } }, type: ("checkbox"), checked: ((__VLS_ctx.selectedGroups.has(idx))), ...{ style: ({}) }, });
            __VLS_elementAsFunction(__VLS_intrinsicElements.input)({ ...{ style: ((__VLS_ctx.nameInputStyle)) }, ...{ style: ({}) }, placeholder: ((grp.base_name)), });
            (grp.editedName);
            __VLS_elementAsFunction(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({ ...{ style: ({}) }, });
            (grp.road_ids.length);
            __VLS_elementAsFunction(__VLS_intrinsicElements.ul, __VLS_intrinsicElements.ul)({ ...{ style: ({}) }, });
            for (const [rname, ri] of __VLS_getVForSourceType((grp.road_names))) {
                __VLS_elementAsFunction(__VLS_intrinsicElements.li, __VLS_intrinsicElements.li)({ key: ((ri)), });
                (rname);
                __VLS_elementAsFunction(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({ ...{ style: ({}) }, });
                (grp.road_points[ri]);
            }
        }
        __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (__VLS_ctx.startMerge) }, ...{ style: ((__VLS_ctx.btnPrimary(__VLS_ctx.selectedGroups.size > 0))) }, disabled: ((__VLS_ctx.selectedGroups.size === 0)), ...{ style: ({}) }, });
        (__VLS_ctx.selectedGroups.size);
        __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (...[$event]) => {
                    if (!(!((__VLS_ctx.state === 'loading'))))
                        return;
                    if (!(!((__VLS_ctx.state === 'empty'))))
                        return;
                    if (!((__VLS_ctx.state === 'preview')))
                        return;
                    __VLS_ctx.$emit('close');
                } }, ...{ style: ((__VLS_ctx.btnSecondary())) }, });
    }
    else if (__VLS_ctx.state === 'merging') {
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
        (__VLS_ctx.selectedGroups.size);
    }
    else if (__VLS_ctx.state === 'done') {
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
        __VLS_elementAsFunction(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
        (__VLS_ctx.mergeResults.length);
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
        __VLS_elementAsFunction(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
        (__VLS_ctx.totalDeleted);
        if (__VLS_ctx.totalGaps > 0) {
            __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
            __VLS_elementAsFunction(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
            (__VLS_ctx.totalGaps);
        }
        __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (...[$event]) => {
                    if (!(!((__VLS_ctx.state === 'loading'))))
                        return;
                    if (!(!((__VLS_ctx.state === 'empty'))))
                        return;
                    if (!(!((__VLS_ctx.state === 'preview'))))
                        return;
                    if (!(!((__VLS_ctx.state === 'merging'))))
                        return;
                    if (!((__VLS_ctx.state === 'done')))
                        return;
                    __VLS_ctx.$emit('close');
                } }, ...{ style: ((__VLS_ctx.btnPrimary(true))) }, ...{ style: ({}) }, });
    }
    else if (__VLS_ctx.state === 'error') {
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
        (__VLS_ctx.errorMessage);
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (__VLS_ctx.loadGroups) }, ...{ style: ((__VLS_ctx.btnSecondary())) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (...[$event]) => {
                    if (!(!((__VLS_ctx.state === 'loading'))))
                        return;
                    if (!(!((__VLS_ctx.state === 'empty'))))
                        return;
                    if (!(!((__VLS_ctx.state === 'preview'))))
                        return;
                    if (!(!((__VLS_ctx.state === 'merging'))))
                        return;
                    if (!(!((__VLS_ctx.state === 'done'))))
                        return;
                    if (!((__VLS_ctx.state === 'error')))
                        return;
                    __VLS_ctx.$emit('close');
                } }, ...{ style: ((__VLS_ctx.btnSecondary())) }, });
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
