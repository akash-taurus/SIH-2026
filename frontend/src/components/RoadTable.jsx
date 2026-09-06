import React from 'react';
import { translations } from '../utils/translations';

/**
 * RoadTable: Critical Highway & Corridor Status Matrix
 * Uses distinct monochrome icons (●, /, ) for color-blind accessibility.
 */
export default function RoadTable({ roads = [], language = 'en', onSelectRoad = null }) {
  const t = translations[language] || translations.en;

  const getStatusBadge = (status) => {
    switch (status?.toLowerCase()) {
      case 'blocked':
        return (
          <span className="inline-flex items-center gap-1.5 bg-black text-white px-2 py-0.5 text-[10px] font-black uppercase tracking-wider font-mono">
            <span></span>
            <span>{t.road_blocked || "Blocked"}</span>
          </span>
        );
      case 'at_risk':
        return (
          <span className="inline-flex items-center gap-1.5 border-2 border-black text-black px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider font-mono">
            <span>/</span>
            <span>{t.road_at_risk || "t Risk"}</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 bg-gray-100 border border-gray-400 text-gray-800 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider font-mono">
            <span>●</span>
            <span>{t.road_open || "Open"}</span>
          </span>
        );
    }
  };

  return (
    <div className="bg-white border-2 border-black p-4">
      {/* Header */}
      <div className="flex items-center justify-between pb-2 mb-3 border-b-2 border-black">
        <div>
          <h3 className="text-base font-bold text-black tracking-tight">
            {t.road_status_title || "Highway Connectivity Status"}
          </h3>
          <p className="text-xs text-gray-600 font-mono">
            NH-40, NH-6, SH-5 rterial Highway Network
          </p>
        </div>
        <span className="bg-gray-100 text-black border border-black text-xs px-2 py-0.5 font-mono font-bold">
          {roads.length} Corridors
        </span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto max-h-[290px] overflow-y-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead className="sticky top-0 z-10">
            <tr className="border-b-2 border-black bg-gray-50 text-[11px] font-bold uppercase tracking-wider text-black">
              <th className="py-2.5 px-3">{t.road_name || "Corridor"}</th>
              <th className="py-2.5 px-3">{t.road_status || "Status"}</th>
              <th className="py-2.5 px-3">{t.road_reason || "Condition / Impasse"}</th>
              <th className="py-2.5 px-3 text-right">{t.road_updated || "Updated"}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {roads.map((road) => (
              <tr
                key={road.road_id}
                onClick={() => onSelectRoad && onSelectRoad(road)}
                className="hover:bg-gray-50 transition-colors cursor-pointer"
              >
                <td className="py-2.5 px-3">
                  <div className="font-bold text-black font-mono">{road.road_id}</div>
                  <div className="text-xs text-gray-700">{road.name}</div>
                </td>
                <td className="py-2.5 px-3 whitespace-nowrap">
                  {getStatusBadge(road.status)}
                </td>
                <td className="py-2.5 px-3 max-w-xs text-gray-800">
                  {road.blockage_reason ? (
                    <div>
                      <p className="font-medium text-black">{road.blockage_reason}</p>
                      {road.traffic_diversion && (
                        <p className="text-[10px] text-gray-500 font-mono mt-0.5">
                          ↳ Diversion: {road.traffic_diversion}
                        </p>
                      )}
                    </div>
                  ) : (
                    <span className="text-gray-500 font-mono">Clear transit corridor</span>
                  )}
                </td>
                <td className="py-2.5 px-3 text-right font-mono text-gray-500 whitespace-nowrap">
                  {road.last_updated}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
