import L from 'leaflet';
/**
 * Static compass rose displayed in the top-right corner of the map.
 * Labels follow Brazilian Portuguese convention: N/S/L/O (Leste/Oeste, not E/W).
 * No rotation — Web Mercator tiles always have North up.
 */
export const CompassControl = L.Control.extend({
    options: { position: 'topright' },
    onAdd() {
        const div = L.DomUtil.create('div', 'gms-compass');
        div.style.cssText = 'pointer-events:none;user-select:none;';
        div.innerHTML = `
      <svg viewBox="0 0 60 60" width="60" height="60" aria-label="Bússola N S L O">
        <circle cx="30" cy="30" r="28" fill="white" stroke="#222" stroke-width="1.2" opacity="0.92"/>
        <!-- N pointer (red) -->
        <polygon points="30,6 26,30 30,26 34,30" fill="#E24B4A"/>
        <!-- S pointer (dark) -->
        <polygon points="30,54 26,30 30,34 34,30" fill="#222"/>
        <!-- L (Leste) tick -->
        <line x1="54" y1="30" x2="48" y2="30" stroke="#222" stroke-width="1.5"/>
        <!-- O (Oeste) tick -->
        <line x1="6"  y1="30" x2="12" y2="30" stroke="#222" stroke-width="1.5"/>
        <!-- Labels -->
        <text x="30" y="14" text-anchor="middle" font-family="sans-serif" font-size="10" font-weight="700" fill="#222">N</text>
        <text x="30" y="52" text-anchor="middle" font-family="sans-serif" font-size="9"  fill="#222">S</text>
        <text x="51" y="33" text-anchor="middle" font-family="sans-serif" font-size="9"  fill="#222">L</text>
        <text x="9"  y="33" text-anchor="middle" font-family="sans-serif" font-size="9"  fill="#222">O</text>
      </svg>
    `;
        L.DomEvent.disableClickPropagation(div);
        return div;
    },
});
