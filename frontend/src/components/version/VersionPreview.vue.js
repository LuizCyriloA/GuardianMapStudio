/// <reference types="../../../node_modules/.vue-global-types/vue_3.4_false.d.ts" />
import { defineComponent } from 'vue';
import L from 'leaflet';
export default defineComponent({
    name: 'VersionPreview',
    props: {
        version: { type: Object, required: true },
    },
    data() {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        return { map: null };
    },
    computed: {
        mapId() {
            return `version-map-${this.version.id}`;
        },
    },
    mounted() {
        this.$nextTick(() => { this.initMap(); });
    },
    beforeUnmount() {
        this.map?.remove();
    },
    methods: {
        async initMap() {
            await this.$nextTick();
            const el = document.getElementById(this.mapId);
            if (!el)
                return;
            this.map = L.map(el, { zoom: 18, center: [-23.55, -46.63], zoomControl: true });
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors',
            }).addTo(this.map);
            // Load version map data
            try {
                const data = await fetch(`/api/v1/versions/${this.version.id}/map`).then(r => r.json());
                const bounds = [];
                for (const road of data.roads ?? []) {
                    if (road.coordinates?.length >= 2) {
                        const lls = road.coordinates.map((c) => L.latLng(c.lat, c.lng));
                        L.polyline(lls, { color: '#378ADD', weight: 3 })
                            .bindPopup(`<b>${road.name}</b>`)
                            .addTo(this.map);
                        bounds.push(...lls);
                    }
                }
                for (const wp of data.waypoints ?? []) {
                    if (wp.latitude && wp.longitude) {
                        const ll = L.latLng(wp.latitude, wp.longitude);
                        L.circleMarker(ll, { radius: 6, color: '#534AB7' })
                            .bindPopup(`<b>${wp.name}</b><br>${wp.waypoint_type}`)
                            .addTo(this.map);
                        bounds.push(ll);
                    }
                }
                if (bounds.length > 0 && this.map) {
                    this.map.fitBounds(L.latLngBounds(bounds).pad(0.1));
                }
            }
            catch {
                // Version map load failed — continue with empty map
            }
        },
        formatDate(iso) {
            return new Date(iso).toLocaleDateString('pt-BR');
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
    (__VLS_ctx.version.version_number);
    __VLS_elementAsFunction(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
    (__VLS_ctx.version.name);
    (__VLS_ctx.formatDate(__VLS_ctx.version.published_at));
    __VLS_elementAsFunction(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({ id: ((__VLS_ctx.mapId)), ...{ style: ({}) }, });
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
