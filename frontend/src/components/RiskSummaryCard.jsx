import React from 'react';
import { translations } from '../utils/translations';

/**
 * RiskSummaryCard: Regional Hazard Severity Distribution Breakdown
 * Grayscale progress indicators with high contrast tabular metrics.
 */
export default function RiskSummaryCard({ summary = [], language = 'en', onSelectFilter = null }) {
  const t = translations[language] || translations.en;

  const totalCount = summary.reduce((sum, item) => sum + (item.count || 0), 0);

  const getTierDetails = (level) => {
    switch (level?.toLowerCase()) {
      case 'severe':
        return {
          label: t.risk_severe || "Severe Risk",
          barColor: 'bg-black',
          textColor: 'text-black',
          badge: 'bg-black text-white'
        };
      case 'high':
        return {
          label: t.risk_high || "High Risk",
          barColor: 'bg-[#444444]',
          textColor: 'text-black',
          badge: 'border-2 border-black text-black'
        };
      case 'moderate':
        return {
          label: t.risk_moderate || "Moderate Risk",
          barColor: 'bg-[#]',
          textColor: 'text-gray-800',
          badge: 'bg-gray-200 text-gray-800'
        };
      default:
        return {
          label: t.risk_low || "Low Risk",
          barColor: 'bg-[#EBEBEB]',
          textColor: 'text-gray-600',
          badge: 'border border-gray-300 text-gray-600'
        };
    }
  };

  return (
    <div className="bg-white border-2 border-black p-4">
      {/* Header bar with total monitored zone count */}
      <div className="flex items-center justify-between pb-2 mb-3 border-b-2 border-black">
        <div>
          <h3 className="text-base font-bold text-black tracking-tight">
            {t.risk_summary_title || "Regional Risk Distribution"}
          </h3>
          <p className="text-xs text-gray-600 font-mono">
            {t.total_zones || "Total Monitored Sectors"}: <span className="font-bold text-black">{totalCount}</span>
          </p>
        </div>
        <span className="bg-black text-white text-[10px] font-mono font-bold px-2 py-0.5 uppercase tracking-wider">
          LIVE I FUSION
        </span>
      </div>

      {/* Progress Bars List */}
      <div className="space-y-3">
        {summary.map((item, idx) => {
          const tier = getTierDetails(item.level);
          const percent = totalCount > 0 ? Math.round((item.count / totalCount) * 100) : (item.percentage || 0);

          return (
            <div
              key={`risk-tier-${idx}`}
              onClick={() => onSelectFilter && onSelectFilter(item.level)}
              className="cursor-pointer group p-1 hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-center justify-between text-xs mb-1">
                <div className="flex items-center gap-2">
                  <span className={`w-2.5 h-2.5 inline-block ${tier.barColor} border border-black`}></span>
                  <span className="font-bold text-black">{tier.label}</span>
                </div>
                <div className="flex items-center gap-2 font-mono">
                  <span className="text-gray-500">{percent}%</span>
                  <span className={`px-1.5 py-0.2 text-[10px] font-bold ${tier.badge}`}>
                    {item.count}
                  </span>
                </div>
              </div>

              {/* High-Contrast Grayscale Bar */}
              <div className="w-full h-3 bg-gray-100 border border-black overflow-hidden">
                <div
                  className={`h-full ${tier.barColor} transition-all duration-500`}
                  style={{ width: `${percent}%` }}
                ></div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
