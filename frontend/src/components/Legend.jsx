import React from 'react';
import { translations } from '../utils/translations';

/**
 * Legend: Map Heatmap Legend Overlay
 * Displays Green -> Yellow -> Orange -> Red severity tiers and highway line symbols.
 */
export default function Legend({ language = 'en' }) {
  const t = translations[language] || translations.en;

  const legendItems = [
    { label: t.risk_severe || 'Severe (>80%)', color: 'bg-red-600', border: 'border border-black' },
    { label: t.risk_high || 'High (60–80%)', color: 'bg-orange-500', border: 'border border-black' },
    { label: t.risk_moderate || 'Moderate (30–60%)', color: 'bg-yellow-500', border: 'border border-black' },
    { label: t.risk_low || 'Low (<30%)', color: 'bg-green-600', border: 'border border-black' }
  ];

  return (
    <div className="absolute bottom-4 left-4 z-[1000] bg-white/95 backdrop-blur-xs border-2 border-black p-3 text-xs font-mono shadow-md max-w-[220px]">
      <h5 className="font-bold text-black border-b border-black pb-1 mb-2 uppercase tracking-tight text-[11px]">
        {t.nav_map || "Hazard Risk Heatmap"}
      </h5>

      {/* Continuous Gradient Indicator */}
      <div className="mb-2.5">
        <div className="w-full h-2 rounded-xs bg-gradient-to-r from-[#22c55e] via-[#eab308] via-[#f97316] to-[#ef4444] border border-black"></div>
      </div>

      <div className="space-y-1.5">
        {legendItems.map((item, idx) => (
          <div key={`legend-${idx}`} className="flex items-center gap-2">
            <span className={`w-3.5 h-3.5 inline-block ${item.color} ${item.border} shrink-0`}></span>
            <span className="text-[11px] font-semibold text-black leading-none">{item.label}</span>
          </div>
        ))}
      </div>

      <div className="mt-2.5 pt-2 border-t border-gray-300 text-[10px] space-y-1 text-gray-700">
        <div className="flex items-center gap-2">
          <span className="w-4 h-0.5 bg-black inline-block"></span>
          <span>Open Highway</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-4 h-0.5 bg-red-600 border-b border-dashed inline-block"></span>
          <span>At Risk / Blocked</span>
        </div>
      </div>
    </div>
  );
}
