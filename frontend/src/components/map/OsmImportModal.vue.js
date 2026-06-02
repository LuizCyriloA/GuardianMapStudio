import { defineComponent } from 'vue';
import { useMapStore } from '../../stores/map';
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB
export default defineComponent({
    name: 'OsmImportModal',
    props: {
        workspaceId: { type: Number, required: true },
        visible: { type: Boolean, default: false },
    },
    emits: ['close', 'imported'],
    data() {
        return {
            state: 'idle',
            selectedFile: null,
            fileError: '',
            previewRoads: [],
            selectedOsmIds: new Set(),
            totalWaysInFile: 0,
            skippedWays: 0,
            replaceExisting: false,
            includePedestrian: false,
            includeUnnamed: false,
            optionsChanged: false,
            importResult: null,
            errorMessage: '',
        };
    },
    computed: {
        allSelected() {
            if (this.previewRoads.length === 0)
                return false;
            return this.previewRoads.every(r => this.selectedOsmIds.has(r.osm_way_id));
        },
    },
    methods: {
        triggerFileInput() {
            this.$refs.fileInput.click();
        },
        onBackdropClick() {
            if (this.state === 'idle' || this.state === 'preview' || this.state === 'error') {
                this.$emit('close');
            }
        },
        onFileChange(event) {
            const input = event.target;
            const file = input.files?.[0] ?? null;
            this.fileError = '';
            this.selectedFile = null;
            if (!file)
                return;
            if (!file.name.endsWith('.osm') && !file.name.endsWith('.xml')) {
                this.fileError = 'Apenas arquivos .osm ou .xml são aceitos.';
                return;
            }
            if (file.size > MAX_FILE_SIZE) {
                this.fileError = `Arquivo muito grande (${(file.size / 1024 / 1024).toFixed(1)} MB). Máximo: 10 MB.`;
                return;
            }
            this.selectedFile = file;
        },
        async startPreview() {
            if (!this.selectedFile)
                return;
            this.state = 'parsing';
            this.optionsChanged = false;
            try {
                const mapStore = useMapStore();
                const result = await mapStore.previewOsmImport(this.selectedFile, {
                    includePedestrian: this.includePedestrian,
                    includeUnnamed: this.includeUnnamed,
                });
                this.previewRoads = result.roads;
                this.totalWaysInFile = result.total_ways_in_file;
                this.skippedWays = result.skipped_ways;
                this.selectedOsmIds = new Set(result.roads.map(r => r.osm_way_id));
                this.state = 'preview';
            }
            catch (err) {
                const e = err;
                this.errorMessage = e?.detail?.message ?? 'Erro ao analisar o arquivo.';
                this.state = 'error';
            }
        },
        onOptionChange() {
            this.optionsChanged = true;
        },
        async reParse() {
            await this.startPreview();
        },
        toggleAll(event) {
            const checked = event.target.checked;
            if (checked) {
                this.selectedOsmIds = new Set(this.previewRoads.map(r => r.osm_way_id));
            }
            else {
                this.selectedOsmIds = new Set();
            }
        },
        toggleRoad(osmWayId) {
            const next = new Set(this.selectedOsmIds);
            if (next.has(osmWayId)) {
                next.delete(osmWayId);
            }
            else {
                next.add(osmWayId);
            }
            this.selectedOsmIds = next;
        },
        async startImport() {
            const selected = this.previewRoads.filter(r => this.selectedOsmIds.has(r.osm_way_id));
            if (selected.length === 0)
                return;
            this.state = 'importing';
            try {
                const mapStore = useMapStore();
                const result = await mapStore.commitOsmImport(selected, this.replaceExisting);
                this.importResult = result;
                this.state = 'done';
                this.$emit('imported', result);
            }
            catch (err) {
                const e = err;
                this.errorMessage = e?.detail?.message ?? 'Erro ao importar ruas.';
                this.state = 'error';
            }
        },
        reset() {
            this.state = 'idle';
            this.selectedFile = null;
            this.fileError = '';
            this.previewRoads = [];
            this.selectedOsmIds = new Set();
            this.optionsChanged = false;
            this.errorMessage = '';
            this.importResult = null;
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
    if (__VLS_ctx.state === 'idle') {
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
        __VLS_elementAsFunction(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.code, __VLS_intrinsicElements.code)({});
        __VLS_elementAsFunction(__VLS_intrinsicElements.code, __VLS_intrinsicElements.code)({});
        __VLS_elementAsFunction(__VLS_intrinsicElements.input)({ ...{ onChange: (__VLS_ctx.onFileChange) }, ref: ("fileInput"), type: ("file"), accept: (".osm,.xml"), ...{ style: ({}) }, });
        // @ts-ignore navigation for `const fileInput = ref()`
        __VLS_ctx.fileInput;
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (__VLS_ctx.triggerFileInput) }, ...{ style: ((__VLS_ctx.btnSecondary())) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({ ...{ style: ({}) }, });
        (__VLS_ctx.selectedFile ? __VLS_ctx.selectedFile.name : 'Nenhum arquivo selecionado');
        if (__VLS_ctx.fileError) {
            __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
            (__VLS_ctx.fileError);
        }
        __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (__VLS_ctx.startPreview) }, disabled: ((!__VLS_ctx.selectedFile || !!__VLS_ctx.fileError)), ...{ style: ((__VLS_ctx.btnPrimary(!!__VLS_ctx.selectedFile && !__VLS_ctx.fileError))) }, });
    }
    else if (__VLS_ctx.state === 'parsing') {
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
    }
    else if (__VLS_ctx.state === 'preview') {
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.label, __VLS_intrinsicElements.label)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.input)({ type: ("checkbox"), ...{ style: ({}) }, });
        (__VLS_ctx.replaceExisting);
        __VLS_elementAsFunction(__VLS_intrinsicElements.label, __VLS_intrinsicElements.label)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.input)({ ...{ onChange: (__VLS_ctx.onOptionChange) }, type: ("checkbox"), ...{ style: ({}) }, });
        (__VLS_ctx.includePedestrian);
        __VLS_elementAsFunction(__VLS_intrinsicElements.label, __VLS_intrinsicElements.label)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.input)({ ...{ onChange: (__VLS_ctx.onOptionChange) }, type: ("checkbox"), ...{ style: ({}) }, });
        (__VLS_ctx.includeUnnamed);
        if (__VLS_ctx.optionsChanged) {
            __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
            __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (__VLS_ctx.reParse) }, ...{ style: ((__VLS_ctx.btnSecondary())) }, });
        }
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
        (__VLS_ctx.previewRoads.length);
        (__VLS_ctx.totalWaysInFile);
        (__VLS_ctx.skippedWays);
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.table, __VLS_intrinsicElements.table)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.thead, __VLS_intrinsicElements.thead)({});
        __VLS_elementAsFunction(__VLS_intrinsicElements.tr, __VLS_intrinsicElements.tr)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.th, __VLS_intrinsicElements.th)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.input)({ ...{ onChange: (__VLS_ctx.toggleAll) }, type: ("checkbox"), checked: ((__VLS_ctx.allSelected)), });
        __VLS_elementAsFunction(__VLS_intrinsicElements.th, __VLS_intrinsicElements.th)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.th, __VLS_intrinsicElements.th)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.th, __VLS_intrinsicElements.th)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.th, __VLS_intrinsicElements.th)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.th, __VLS_intrinsicElements.th)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.tbody, __VLS_intrinsicElements.tbody)({});
        for (const [road, idx] of __VLS_getVForSourceType((__VLS_ctx.previewRoads))) {
            __VLS_elementAsFunction(__VLS_intrinsicElements.tr, __VLS_intrinsicElements.tr)({ key: ((road.osm_way_id)), ...{ style: (({ background: idx % 2 === 0 ? '#1e293b' : '#263348' })) }, });
            __VLS_elementAsFunction(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({ ...{ style: ({}) }, });
            __VLS_elementAsFunction(__VLS_intrinsicElements.input)({ ...{ onChange: (...[$event]) => {
                        if (!(!((__VLS_ctx.state === 'idle'))))
                            return;
                        if (!(!((__VLS_ctx.state === 'parsing'))))
                            return;
                        if (!((__VLS_ctx.state === 'preview')))
                            return;
                        __VLS_ctx.toggleRoad(road.osm_way_id);
                    } }, type: ("checkbox"), checked: ((__VLS_ctx.selectedOsmIds.has(road.osm_way_id))), });
            __VLS_elementAsFunction(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({ ...{ style: ({}) }, });
            (road.name);
            __VLS_elementAsFunction(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({ ...{ style: ({}) }, });
            (road.highway_tag);
            __VLS_elementAsFunction(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({ ...{ style: ({}) }, });
            (road.direction === 'one_way' ? 'Mão única' : 'Mão dupla');
            __VLS_elementAsFunction(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({ ...{ style: ({}) }, });
            (road.coordinates.length);
            __VLS_elementAsFunction(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({ ...{ style: ({}) }, });
            if (road.osm_warnings.length > 0) {
                __VLS_elementAsFunction(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({ ...{ style: ({}) }, title: ((road.osm_warnings.join('; '))), });
                (road.osm_warnings.length);
            }
        }
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (__VLS_ctx.startImport) }, ...{ style: ((__VLS_ctx.btnPrimary(__VLS_ctx.selectedOsmIds.size > 0))) }, disabled: ((__VLS_ctx.selectedOsmIds.size === 0)), });
        (__VLS_ctx.selectedOsmIds.size);
        __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (__VLS_ctx.reset) }, ...{ style: ((__VLS_ctx.btnSecondary())) }, });
    }
    else if (__VLS_ctx.state === 'importing') {
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
        (__VLS_ctx.selectedOsmIds.size);
    }
    else if (__VLS_ctx.state === 'done') {
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
        __VLS_elementAsFunction(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
        (__VLS_ctx.importResult?.created_count);
        if (__VLS_ctx.importResult && __VLS_ctx.importResult.deleted_existing > 0) {
            __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
            __VLS_elementAsFunction(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
            (__VLS_ctx.importResult.deleted_existing);
        }
        if (__VLS_ctx.importResult && __VLS_ctx.importResult.renamed.length > 0) {
            __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
            __VLS_elementAsFunction(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
            (__VLS_ctx.importResult.renamed.length);
            __VLS_elementAsFunction(__VLS_intrinsicElements.ul, __VLS_intrinsicElements.ul)({ ...{ style: ({}) }, });
            for (const [r] of __VLS_getVForSourceType((__VLS_ctx.importResult.renamed))) {
                __VLS_elementAsFunction(__VLS_intrinsicElements.li, __VLS_intrinsicElements.li)({ key: ((r.from)), });
                (r.from);
                (r.to);
            }
        }
        __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (...[$event]) => {
                    if (!(!((__VLS_ctx.state === 'idle'))))
                        return;
                    if (!(!((__VLS_ctx.state === 'parsing'))))
                        return;
                    if (!(!((__VLS_ctx.state === 'preview'))))
                        return;
                    if (!(!((__VLS_ctx.state === 'importing'))))
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
        __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (__VLS_ctx.reset) }, ...{ style: ((__VLS_ctx.btnSecondary())) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (...[$event]) => {
                    if (!(!((__VLS_ctx.state === 'idle'))))
                        return;
                    if (!(!((__VLS_ctx.state === 'parsing'))))
                        return;
                    if (!(!((__VLS_ctx.state === 'preview'))))
                        return;
                    if (!(!((__VLS_ctx.state === 'importing'))))
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
    const __VLS_refs = {
        "fileInput": __VLS_nativeElements['input'],
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
