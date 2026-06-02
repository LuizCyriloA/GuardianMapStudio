import { defineStore } from 'pinia';
import { api } from '../api/client';
const STACK_LIMIT = 20;
export const useUndoStore = defineStore('undo', {
    state: () => ({
        stack: [],
        busy: false,
        lastError: '',
    }),
    getters: {
        canUndo: (state) => state.stack.length > 0 && !state.busy,
        lastActionLabel(state) {
            const top = state.stack[state.stack.length - 1];
            if (!top)
                return '';
            switch (top.type) {
                case 'delete_roads':
                    return top.roads.length === 1
                        ? `Desfazer exclusão de rua "${top.roads[0].name}"`
                        : `Desfazer exclusão de ${top.roads.length} ruas`;
                case 'delete_waypoint':
                    return `Desfazer exclusão de waypoint "${top.waypoint.name}"`;
                case 'delete_crossroad':
                    return `Desfazer exclusão de cruzamento`;
            }
        },
    },
    actions: {
        push(entry) {
            this.stack.push(entry);
            while (this.stack.length > STACK_LIMIT)
                this.stack.shift();
            this.lastError = '';
        },
        clear() {
            this.stack = [];
            this.lastError = '';
        },
        async undoLast() {
            if (!this.canUndo)
                return;
            const entry = this.stack.pop();
            this.busy = true;
            this.lastError = '';
            try {
                // Get workspace id from workspace store
                const { useWorkspaceStore } = await import('./workspace');
                const wsId = useWorkspaceStore().workspace?.id;
                if (!wsId)
                    throw new Error('No active workspace');
                switch (entry.type) {
                    case 'delete_roads':
                        for (const road of entry.roads) {
                            await api.createRoad(wsId, {
                                name: road.name,
                                coordinates: road.coordinates,
                                speed_limit_kmh: road.speed_limit_kmh,
                                direction: road.direction,
                                width_meters: road.width_meters,
                            });
                        }
                        break;
                    case 'delete_waypoint':
                        await api.createWaypoint(wsId, {
                            name: entry.waypoint.name,
                            waypoint_type: entry.waypoint.waypoint_type,
                            lat: entry.waypoint.lat,
                            lng: entry.waypoint.lng,
                            road_name: entry.waypoint.road_name,
                            heading_degrees: entry.waypoint.heading_degrees,
                            extra_data: entry.waypoint.extra_data,
                            active: entry.waypoint.active,
                        });
                        break;
                    case 'delete_crossroad':
                        await api.createCrossroad(wsId, {
                            road_a_name: entry.crossroad.road_a_name,
                            road_b_name: entry.crossroad.road_b_name,
                            lat: entry.crossroad.lat,
                            lng: entry.crossroad.lng,
                        });
                        break;
                }
                // Reload map and validation to reflect the restoration
                const { useMapStore } = await import('./map');
                const { useWorkspaceStore: useWsStore } = await import('./workspace');
                await useMapStore().fetchMap(wsId);
                await useWsStore().runValidation();
            }
            catch (e) {
                // Push back on failure so the operator can try again
                this.stack.push(entry);
                const msg = e instanceof Error ? e.message : 'Erro ao desfazer';
                this.lastError = msg;
                throw e;
            }
            finally {
                this.busy = false;
            }
        },
    },
});
