// frontend/src/components/LayerControl.jsx
//
// Floating layer-toggle control overlaid on the top-right of MapView.
// Lets the user show/hide hazard zones, roads, settlements, and the
// rainfall intensity indicator independently.

import React from 'react';
import { translations } from '../utils/translations';

export default function LayerControl({ layers, onToggle, language = 'en' }) {
  const t = translations[language] || translations.en;

  const rows = [
    { key: 'hazardZones', label: t.map_layer_zones || 'Hazard Zones' },
    { key: 'roads', label: t.map_layer_roads || 'Roads' },
    { key: 'settlements', label: t.map_layer_settlements || 'Settlements' },
    { key: 'rainfall', label: t.map_layer_rainfall || 'Rainfall (24h)' }
  ];

  return (
    <div className="ner-map-layer-control">
      {rows.map((row) => (
        <label key={row.key}>
          <input
            type="checkbox"
            checked={!!layers[row.key]}
            onChange={() => onToggle(row.key)}
          />
          {row.label}
        </label>
      ))}
    </div>
  );
}
