import L from 'leaflet'

export interface RectangleSelectorOptions {
  /** Called with the geographic bounds of the drawn rectangle. */
  onSelect: (bounds: L.LatLngBounds) => void
  /** Visual style for the in-progress rectangle. */
  style?: L.PathOptions
}

const DEFAULT_STYLE: L.PathOptions = {
  color: '#FFB400',
  weight: 1.5,
  fillColor: '#FFB400',
  fillOpacity: 0.18,
  dashArray: '4 4',
}

/**
 * Attaches a click-drag rectangle selection handler to a Leaflet map.
 *
 * Behavior:
 *  - Plain drag → map pans (Leaflet default — we do NOT interfere).
 *  - CTRL+drag (or Cmd+drag on macOS) → draws a selection rectangle.
 *
 * Returns a teardown function that detaches all handlers and restores
 * any temporarily-disabled map behavior.
 */
export function attachRectangleSelector(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  map: any,
  opts: RectangleSelectorOptions,
): () => void {
  const style = { ...DEFAULT_STYLE, ...(opts.style ?? {}) }
  let startLatLng: L.LatLng | null = null
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let rectLayer: any = null
  let active = false   // True only when a CTRL-modified drag is in progress

  const isModified = (e: L.LeafletMouseEvent): boolean => {
    return e.originalEvent.ctrlKey || e.originalEvent.metaKey
  }

  const onMouseDown = (e: L.LeafletMouseEvent) => {
    // Without modifier → let Leaflet pan the map. Do nothing.
    if (!isModified(e)) return

    // Don't start a rectangle on a marker (let marker click pass through).
    const target = e.originalEvent.target as HTMLElement | null
    if (target?.closest?.('.leaflet-marker-icon')) return

    active = true
    startLatLng = e.latlng
    map.dragging.disable()        // ONLY now — not on every mousedown
    map.getContainer().style.cursor = 'crosshair'
  }

  const onMouseMove = (e: L.LeafletMouseEvent) => {
    if (!active || !startLatLng) return
    const bounds = L.latLngBounds(startLatLng, e.latlng)
    if (!rectLayer) {
      rectLayer = L.rectangle(bounds, style).addTo(map)
    } else {
      rectLayer.setBounds(bounds)
    }
  }

  const onMouseUp = (e: L.LeafletMouseEvent) => {
    if (!active || !startLatLng) {
      return
    }
    const bounds = L.latLngBounds(startLatLng, e.latlng)
    const moved = startLatLng.distanceTo(e.latlng)
    if (moved > 5) {
      opts.onSelect(bounds)
    }
    if (rectLayer) {
      map.removeLayer(rectLayer)
      rectLayer = null
    }
    startLatLng = null
    active = false
    map.dragging.enable()
    map.getContainer().style.cursor = ''
  }

  // Safety: if the user releases CTRL mid-drag, abort the rectangle cleanly.
  const onKeyUp = (e: KeyboardEvent) => {
    if (!active) return
    if (e.key === 'Control' || e.key === 'Meta') {
      if (rectLayer) {
        map.removeLayer(rectLayer)
        rectLayer = null
      }
      startLatLng = null
      active = false
      map.dragging.enable()
      map.getContainer().style.cursor = ''
    }
  }

  map.on('mousedown', onMouseDown)
  map.on('mousemove', onMouseMove)
  map.on('mouseup', onMouseUp)
  document.addEventListener('keyup', onKeyUp)

  return () => {
    map.off('mousedown', onMouseDown)
    map.off('mousemove', onMouseMove)
    map.off('mouseup', onMouseUp)
    document.removeEventListener('keyup', onKeyUp)
    if (rectLayer) map.removeLayer(rectLayer)
    map.dragging.enable()
    map.getContainer().style.cursor = ''
  }
}
