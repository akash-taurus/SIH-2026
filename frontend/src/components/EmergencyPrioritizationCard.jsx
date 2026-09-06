import React from 'react';
import { translations } from '../utils/translations';

/**
 * EmergencyPrioritizationCard: Ranked Village Evacuation Priority List
 * Implements mathematical vulnerability scoring:
 * Priority Score = Risk Weight * log10(Population) * Distance to Hospital
 */
export default function EmergencyPrioritizationCard({
  settlements = [],
  language = 'en',
  onSelectSettlement = null
}) {
  const t = translations[language] || translations.en;

  const getRankBadge = (rank) => {
    if (rank === 1) {
      return (
        <span className="bg-black text-white px-2 py-0.5 text-xs font-black font-mono">
          #1 PRIORITY
        </span>
      );
    }
    if (rank === 2) {
      return (
        <span className="border-2 border-black text-black px-2 py-0.5 text-xs font-bold font-mono">
          #2 PRIORITY
        </span>
      );
    }
    return (
      <span className="bg-gray-100 border border-gray-400 text-gray-800 px-2 py-0.5 text-xs font-bold font-mono">
        #{rank}
      </span>
    );
  };

  const getRiskTag = (riskLevel) => {
    switch (riskLevel?.toLowerCase()) {
      case 'severe':
        return <span className="bg-black text-white px-1.5 py-0.5 text-[10px] font-mono uppercase font-bold">Severe</span>;
      case 'high':
        return <span className="border border-black text-black px-1.5 py-0.5 text-[10px] font-mono uppercase font-bold">High</span>;
      case 'moderate':
        return <span className="bg-gray-200 text-gray-800 px-1.5 py-0.5 text-[10px] font-mono uppercase font-medium">Mod</span>;
      default:
        return <span className="border border-gray-300 text-gray-600 px-1.5 py-0.5 text-[10px] font-mono uppercase font-normal">Low</span>;
    }
  };

  return (
    <div className="bg-white border-2 border-black p-4">
      {/* Header */}
      <div className="flex items-center justify-between pb-2 mb-3 border-b-2 border-black">
        <div>
          <h3 className="text-base font-bold text-black tracking-tight">
            {t.emergency_title || "Emergency Evacuation Prioritization"}
          </h3>
          <p className="text-xs text-gray-600 font-mono">
            Vulnerability: Risk Weight × log10(Pop) × Hospital Dist
          </p>
        </div>
        <span className="bg-black text-white text-[10px] font-mono font-bold px-2 py-0.5 uppercase tracking-wider">
          NDRF / SDRF RNKING
        </span>
      </div>

      {/* List */}
      <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
        {settlements.map((item, idx) => (
          <div
            key={`settlement-${idx}`}
            onClick={() => onSelectSettlement && onSelectSettlement(item)}
            className="border border-gray-300 hover:border-black p-3 transition-colors cursor-pointer bg-gray-50/50 hover:bg-white"
          >
            <div className="flex items-start justify-between gap-2 mb-1.5">
              <div>
                <div className="flex items-center gap-2">
                  <h4 className="font-bold text-sm text-black">{item.village}</h4>
                  {getRiskTag(item.risk_level)}
                </div>
                <p className="text-xs text-gray-500 font-mono">
                  {item.district} • {item.nearest_hospital}
                </p>
              </div>
              {getRankBadge(item.priority_rank || idx + 1)}
            </div>

            <div className="grid grid-cols-3 gap-2 mt-2 pt-2 border-t border-gray-200 text-xs font-mono">
              <div>
                <span className="text-gray-500 block text-[10px] uppercase">{t.pop_label || "Population"}</span>
                <span className="font-bold text-black">{item.population?.toLocaleString()}</span>
              </div>
              <div>
                <span className="text-gray-500 block text-[10px] uppercase">{t.dist_label || "Hospital"}</span>
                <span className="font-bold text-black">{item.distance_km} km</span>
              </div>
              <div>
                <span className="text-gray-500 block text-[10px] uppercase">{t.evacuation_status || "ction"}</span>
                <span className="font-semibold text-black truncate block">
                  {item.evacuation_status || "Standard AAdvisory"}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
