import L from 'leaflet';
const DEFAULT_STYLE = {
    color: '#FFB400',
    weight: 1.5,
    fillColor: '#FFB400',
    fillOpacity: 0.18,
    dashArray: '4 4',
};
/**
 * Attaches a click-drag rectangle selection handler to a Leaflet map.
 * Returns a teardown function that removes all handlers.
 *
 * Only active while attached — call teardown() when leaving select mode.
 */
export function attachRectangleSelector(
// eslint-disable-next-line @typescript-eslint/no-explicit-any
map, opts) {
    const style = { ...DEFAULT_STYLE, ...(opts.style ?? {}) };
    let startLatLng = null;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let rectLayer = null;
    const onMouseDown = (e) => {
        if (e.originalEvent.target?.closest?.('.leaflet-marker-icon')) {
            return; // don't start a rectangle on a marker
        }
        startLatLng = e.latlng;
        map.dragging.disable();
        map.getContainer().style.cursor = 'crosshair';
    };
    const onMouseMove = (e) => {
        if (!startLatLng)
            return;
        const bounds = L.latLngBounds(startLatLng, e.latlng);
        if (!rectLayer) {
            rectLayer = L.rectangle(bounds, style).addTo(map);
        }
        else {
            rectLayer.setBounds(bounds);
        }
    };
    const onMouseUp = (e) => {
        if (!startLatLng)
            return;
        const bounds = L.latLngBounds(startLatLng, e.latlng);
        const moved = startLatLng.distanceTo(e.latlng);
        // Ignore tiny drags (< 5m) — treat as a click handled elsewhere
        if (moved > 5) {
            opts.onSelect(bounds);
        }
        if (rectLayer) {
            map.removeLayer(rectLayer);
            rectLayer = null;
        }
        startLatLng = null;
        map.dragging.enable();
        map.getContainer().style.cursor = '';
    };
    map.on('mousedown', onMouseDown);
    map.on('mousemove', onMouseMove);
    map.on('mouseup', onMouseUp);
    return () => {
        map.off('mousedown', onMouseDown);
        map.off('mousemove', onMouseMove);
        map.off('mouseup', onMouseUp);
        if (rectLayer)
            map.removeLayer(rectLayer);
        map.dragging.enable();
    };
}
