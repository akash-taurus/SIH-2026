// frontend/src/components/Legend.jsx
//
// Floating monochrome legend overlaid on the top-left of MapView, explaining
// the risk-zone fill scale and the road-status line styles.

import React from 'react';
import { translations } from '../utils/translations';

const RISK_ROWS = [
  { key: 'risk_low', swatchClass: 'low' },
  { key: 'risk_moderate', swatchClass: 'moderate' },
  { key: 'risk_high', swatchClass: 'high' },
  { key: 'risk_severe', swatchClass: 'severe' }
];

const SWATCH_COLORS = {
  low: '#EBEBEB',
  moderate: '#AAAAAA',
  high: '#444444',
  severe: '#000000'
};

export default function Legend({ language = 'en' }) {
  const t = translations[language] || translations.en;

  return (
    <div className="ner-map-legend">
      <div className="ner-map-legend-title">{t.map_legend_title || 'Legend'}</div>

      {RISK_ROWS.map((row) => (
        <div className="ner-map-legend-row" key={row.key}>
          <span
            className="ner-map-legend-swatch"
            style={{ background: SWATCH_COLORS[row.swatchClass] }}
          />
          <span>{t[row.key]}</span>
        </div>
      ))}

      <div className="ner-map-legend-row" style={{ marginTop: 6 }}>
        <span className="ner-map-legend-line" />
        <span>{t.road_open || 'Open Road'}</span>
      </div>
      <div className="ner-map-legend-row">
        <span className="ner-map-legend-line dashed" />
        <span>{t.road_at_risk || 'At-Risk Road'}</span>
      </div>
      <div className="ner-map-legend-row">
        <span className="ner-map-legend-line hashed" />
        <span>{t.road_blocked || 'Blocked Road'}</span>
      </div>
    </div>
  );
}
