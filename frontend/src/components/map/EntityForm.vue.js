import { defineComponent } from 'vue';
import { useMapStore } from '../../stores/map';
import { mapState } from 'pinia';
export default defineComponent({
    name: 'EntityForm',
    props: {
        mode: { type: String, default: 'create' },
        entityType: { type: String, required: true },
        initialData: { type: Object, default: () => ({}) },
    },
    emits: ['saved', 'cancel'],
    data() {
        return {
            form: {
                name: '',
                speed_limit_kmh: 20,
                direction: 'two_way',
                width_meters: 6.0,
                waypoint_type: 'landmark',
                road_name: '',
                lat: 0,
                lng: 0,
                height_cm: 10,
                gate_type: 'entry',
                heading_degrees: null,
                road_a_name: '',
                road_b_name: '',
                restriction_type: 'no_entry',
            },
            saving: false,
            error: '',
        };
    },
    computed: {
        ...mapState(useMapStore, ['roads']),
        entityTypeLabel() {
            const labels = {
                road: 'Estrada',
                waypoint: 'Waypoint',
                crossroad: 'Cruzamento',
                restricted_area: 'Área Restrita',
            };
            return labels[this.entityType] ?? this.entityType;
        },
        inputStyle() {
            return {
                width: '100%',
                padding: '6px 10px',
                border: '1px solid #d1d5db',
                borderRadius: '5px',
                fontSize: '13px',
                background: '#fff',
            };
        },
    },
    created() {
        Object.assign(this.form, this.initialData);
    },
    methods: {
        async onSubmit() {
            this.error = '';
            this.saving = true;
            const mapStore = useMapStore();
            try {
                let result;
                if (this.entityType === 'road') {
                    // coordinates come from MapEditor via initialData
                    const data = {
                        name: this.form.name,
                        coordinates: this.initialData.coordinates ?? [],
                        speed_limit_kmh: this.form.speed_limit_kmh,
                        direction: this.form.direction,
                        width_meters: this.form.width_meters,
                    };
                    if (this.mode === 'create')
                        result = await mapStore.createRoad(data);
                    else
                        result = await mapStore.updateRoad(this.initialData.id, data);
                }
                else if (this.entityType === 'waypoint') {
                    const extra = {};
                    if (this.form.waypoint_type === 'speed_bump')
                        extra.height_cm = this.form.height_cm;
                    if (this.form.waypoint_type === 'gate')
                        extra.gate_type = this.form.gate_type;
                    const data = {
                        name: this.form.name,
                        waypoint_type: this.form.waypoint_type,
                        lat: this.form.lat,
                        lng: this.form.lng,
                        road_name: this.form.road_name || null,
                        heading_degrees: this.form.waypoint_type === 'stop_sign' ? this.form.heading_degrees : null,
                        extra_data: extra,
                    };
                    if (this.mode === 'create')
                        result = await mapStore.createWaypoint(data);
                    else
                        result = await mapStore.updateWaypoint(this.initialData.id, data);
                }
                else if (this.entityType === 'crossroad') {
                    const data = {
                        road_a_name: this.form.road_a_name,
                        road_b_name: this.form.road_b_name,
                        lat: this.form.lat,
                        lng: this.form.lng,
                    };
                    result = await mapStore.createCrossroad(data);
                }
                else if (this.entityType === 'restricted_area') {
                    const data = {
                        name: this.form.name,
                        polygon: this.initialData.polygon ?? [],
                        restriction_type: this.form.restriction_type,
                        speed_limit_kmh: this.form.restriction_type === 'speed_limit' ? this.form.speed_limit_kmh : null,
                    };
                    if (this.mode === 'create')
                        result = await mapStore.createArea(data);
                    else
                        result = await mapStore.updateArea(this.initialData.id, data);
                }
                this.$emit('saved', result);
            }
            catch (e) {
                const err = e;
                this.error = err?.message ?? 'Erro ao salvar';
            }
            finally {
                this.saving = false;
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
    __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
    (__VLS_ctx.mode === 'create' ? 'Criar' : 'Editar');
    (__VLS_ctx.entityTypeLabel);
    __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (...[$event]) => {
                __VLS_ctx.$emit('cancel');
            } }, ...{ style: ({}) }, });
    if (__VLS_ctx.entityType === 'road') {
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
        __VLS_elementAsFunction(__VLS_intrinsicElements.label, __VLS_intrinsicElements.label)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.input)({ placeholder: ("Rua Principal"), ...{ style: ((__VLS_ctx.inputStyle)) }, });
        (__VLS_ctx.form.name);
        __VLS_elementAsFunction(__VLS_intrinsicElements.label, __VLS_intrinsicElements.label)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.input)({ type: ("number"), min: ("1"), ...{ style: ((__VLS_ctx.inputStyle)) }, });
        (__VLS_ctx.form.speed_limit_kmh);
        __VLS_elementAsFunction(__VLS_intrinsicElements.label, __VLS_intrinsicElements.label)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.select, __VLS_intrinsicElements.select)({ value: ((__VLS_ctx.form.direction)), ...{ style: ((__VLS_ctx.inputStyle)) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.option, __VLS_intrinsicElements.option)({ value: ("two_way"), });
        __VLS_elementAsFunction(__VLS_intrinsicElements.option, __VLS_intrinsicElements.option)({ value: ("one_way"), });
        __VLS_elementAsFunction(__VLS_intrinsicElements.label, __VLS_intrinsicElements.label)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.input)({ type: ("number"), min: ("0.1"), step: ("0.1"), ...{ style: ((__VLS_ctx.inputStyle)) }, });
        (__VLS_ctx.form.width_meters);
    }
    else if (__VLS_ctx.entityType === 'waypoint') {
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
        __VLS_elementAsFunction(__VLS_intrinsicElements.label, __VLS_intrinsicElements.label)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.input)({ placeholder: ("Nome do ponto"), ...{ style: ((__VLS_ctx.inputStyle)) }, });
        (__VLS_ctx.form.name);
        __VLS_elementAsFunction(__VLS_intrinsicElements.label, __VLS_intrinsicElements.label)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.select, __VLS_intrinsicElements.select)({ value: ((__VLS_ctx.form.waypoint_type)), ...{ style: ((__VLS_ctx.inputStyle)) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.option, __VLS_intrinsicElements.option)({ value: ("stop_sign"), });
        __VLS_elementAsFunction(__VLS_intrinsicElements.option, __VLS_intrinsicElements.option)({ value: ("speed_bump"), });
        __VLS_elementAsFunction(__VLS_intrinsicElements.option, __VLS_intrinsicElements.option)({ value: ("gate"), });
        __VLS_elementAsFunction(__VLS_intrinsicElements.option, __VLS_intrinsicElements.option)({ value: ("landmark"), });
        __VLS_elementAsFunction(__VLS_intrinsicElements.option, __VLS_intrinsicElements.option)({ value: ("curve"), });
        __VLS_elementAsFunction(__VLS_intrinsicElements.option, __VLS_intrinsicElements.option)({ value: ("crossroad"), });
        __VLS_elementAsFunction(__VLS_intrinsicElements.option, __VLS_intrinsicElements.option)({ value: ("stop_zone"), });
        __VLS_elementAsFunction(__VLS_intrinsicElements.label, __VLS_intrinsicElements.label)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.select, __VLS_intrinsicElements.select)({ value: ((__VLS_ctx.form.road_name)), ...{ style: ((__VLS_ctx.inputStyle)) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.option, __VLS_intrinsicElements.option)({ value: (""), });
        for (const [r] of __VLS_getVForSourceType((__VLS_ctx.roads))) {
            __VLS_elementAsFunction(__VLS_intrinsicElements.option, __VLS_intrinsicElements.option)({ key: ((r.id)), value: ((r.name)), });
            (r.name);
        }
        if (__VLS_ctx.form.waypoint_type === 'speed_bump') {
            __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
            __VLS_elementAsFunction(__VLS_intrinsicElements.label, __VLS_intrinsicElements.label)({ ...{ style: ({}) }, });
            __VLS_elementAsFunction(__VLS_intrinsicElements.input)({ type: ("number"), min: ("1"), ...{ style: ((__VLS_ctx.inputStyle)) }, });
            (__VLS_ctx.form.height_cm);
        }
        if (__VLS_ctx.form.waypoint_type === 'gate') {
            __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
            __VLS_elementAsFunction(__VLS_intrinsicElements.label, __VLS_intrinsicElements.label)({ ...{ style: ({}) }, });
            __VLS_elementAsFunction(__VLS_intrinsicElements.select, __VLS_intrinsicElements.select)({ value: ((__VLS_ctx.form.gate_type)), ...{ style: ((__VLS_ctx.inputStyle)) }, });
            __VLS_elementAsFunction(__VLS_intrinsicElements.option, __VLS_intrinsicElements.option)({ value: ("entry"), });
            __VLS_elementAsFunction(__VLS_intrinsicElements.option, __VLS_intrinsicElements.option)({ value: ("exit"), });
            __VLS_elementAsFunction(__VLS_intrinsicElements.option, __VLS_intrinsicElements.option)({ value: ("entry_exit"), });
            __VLS_elementAsFunction(__VLS_intrinsicElements.option, __VLS_intrinsicElements.option)({ value: ("internal"), });
        }
        if (__VLS_ctx.form.waypoint_type === 'stop_sign') {
            __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
            __VLS_elementAsFunction(__VLS_intrinsicElements.label, __VLS_intrinsicElements.label)({ ...{ style: ({}) }, });
            __VLS_elementAsFunction(__VLS_intrinsicElements.input)({ type: ("number"), min: ("0"), max: ("360"), ...{ style: ((__VLS_ctx.inputStyle)) }, });
            (__VLS_ctx.form.heading_degrees);
        }
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
        (__VLS_ctx.form.lat?.toFixed(7));
        (__VLS_ctx.form.lng?.toFixed(7));
    }
    else if (__VLS_ctx.entityType === 'crossroad') {
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
        __VLS_elementAsFunction(__VLS_intrinsicElements.label, __VLS_intrinsicElements.label)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.select, __VLS_intrinsicElements.select)({ value: ((__VLS_ctx.form.road_a_name)), ...{ style: ((__VLS_ctx.inputStyle)) }, });
        for (const [r] of __VLS_getVForSourceType((__VLS_ctx.roads))) {
            __VLS_elementAsFunction(__VLS_intrinsicElements.option, __VLS_intrinsicElements.option)({ key: ((r.id)), value: ((r.name)), });
            (r.name);
        }
        __VLS_elementAsFunction(__VLS_intrinsicElements.label, __VLS_intrinsicElements.label)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.select, __VLS_intrinsicElements.select)({ value: ((__VLS_ctx.form.road_b_name)), ...{ style: ((__VLS_ctx.inputStyle)) }, });
        for (const [r] of __VLS_getVForSourceType((__VLS_ctx.roads))) {
            __VLS_elementAsFunction(__VLS_intrinsicElements.option, __VLS_intrinsicElements.option)({ key: ((r.id)), value: ((r.name)), });
            (r.name);
        }
    }
    else if (__VLS_ctx.entityType === 'restricted_area') {
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
        __VLS_elementAsFunction(__VLS_intrinsicElements.label, __VLS_intrinsicElements.label)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.input)({ placeholder: ("Zona restrita"), ...{ style: ((__VLS_ctx.inputStyle)) }, });
        (__VLS_ctx.form.name);
        __VLS_elementAsFunction(__VLS_intrinsicElements.label, __VLS_intrinsicElements.label)({ ...{ style: ({}) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.select, __VLS_intrinsicElements.select)({ value: ((__VLS_ctx.form.restriction_type)), ...{ style: ((__VLS_ctx.inputStyle)) }, });
        __VLS_elementAsFunction(__VLS_intrinsicElements.option, __VLS_intrinsicElements.option)({ value: ("no_entry"), });
        __VLS_elementAsFunction(__VLS_intrinsicElements.option, __VLS_intrinsicElements.option)({ value: ("speed_limit"), });
        __VLS_elementAsFunction(__VLS_intrinsicElements.option, __VLS_intrinsicElements.option)({ value: ("pedestrian_only"), });
        if (__VLS_ctx.form.restriction_type === 'speed_limit') {
            __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
            __VLS_elementAsFunction(__VLS_intrinsicElements.label, __VLS_intrinsicElements.label)({ ...{ style: ({}) }, });
            __VLS_elementAsFunction(__VLS_intrinsicElements.input)({ type: ("number"), min: ("1"), ...{ style: ((__VLS_ctx.inputStyle)) }, });
            (__VLS_ctx.form.speed_limit_kmh);
        }
    }
    if (__VLS_ctx.error) {
        __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
        (__VLS_ctx.error);
    }
    __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ ...{ style: ({}) }, });
    __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (__VLS_ctx.onSubmit) }, disabled: ((__VLS_ctx.saving)), ...{ style: ({}) }, });
    (__VLS_ctx.saving ? 'Salvando…' : (__VLS_ctx.mode === 'create' ? 'Criar' : 'Salvar'));
    __VLS_elementAsFunction(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({ ...{ onClick: (...[$event]) => {
                __VLS_ctx.$emit('cancel');
            } }, ...{ style: ({}) }, });
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
