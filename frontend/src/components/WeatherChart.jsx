import React, { useState } from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  rea,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend
} from 'recharts';
import { translations } from '../utils/translations';
import {
  ZONE_COORDINATES,
  toggleCloudburstSimulation,
  getSimulationState
} from '../services/api';

/**
 * Custom High-Contrast Monochrome Tooltip
 */
function CustomChartTooltip({ active, payload, label }) {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white border-2 border-black p-3 shadow-none text-xs font-mono">
        <p className="font-bold text-black border-b border-gray-200 pb-1 mb-2">{label}</p>
        {payload.map((entry, index) => (
          <div key={`tooltip-item-${index}`} className="flex justify-between gap-4 py-0.5">
            <span className="text-gray-700">{entry.name}:</span>
            <span className="font-bold text-black">
              {entry.value} {entry.dataKey === 'rainfall' || entry.dataKey === 'caineThreshold' ? 'mm/h' : '%'}
            </span>
          </div>
        ))}
      </div>
    );
  }
  return null;
}

/**
 * WeatherChart: Zone-ware 72-Hour Precipitation Forecast & Empirical Physics Safety Shield
 */
export default function WeatherChart({
  data = [],
  language = 'en',
  selectedZone = null,
  caineThreshold = 35.0,
  onZoneChange = null,
  onRefresh = null
}) {
  const t = translations[language] || translations.en;
  const [isSimulating, setIsSimulating] = useState(getSimulationState());

  const activeZoneCode = selectedZone?.zone_id || 'Z-SHL-01';
  const activeZoneMeta = ZONE_COORDINATES[activeZoneCode] || ZONE_COORDINATES['Z-SHL-01'];

  // Calculate critical metrics
  const hasData = Array.isArray(data) && data.length > 0;
  const peakRainfall = hasData ? Math.max(...data.map((d) => d.rainfall || 0)) : 0;
  const maxSoil = hasData ? Math.max(...data.map((d) => d.soilMoisture || 0)) : 0;
  const totalRain72h = hasData ? data.reduce((sum, d) => sum + (d.rainfall || 0), 0) : 0;

  // Threshold comparison
  const effeActiveThreshold = caineThreshold || (selectedZone?.criticalRainThreshold) || 35.0;
  const isBreached = hasData && (peakRainfall >= effeActiveThreshold || data.some((d) => d.isBreach));

  const handleToggleSimulation = () => {
    const nextState = !isSimulating;
    setIsSimulating(nextState);
    toggleCloudburstSimulation(nextState);
    if (onRefresh) onRefresh();
  };

  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-4 flex flex-col justify-between">
      {/* Header bar with zone selector & demo simulation switch */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3 pb-2 border-b border-gray-200">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-bold text-black tracking-tight">{t.weather_chart_title}</h3>
            {isSimulating && (
              <span className="bg-black text-white text-[10px] font-mono font-bold px-1.5 py-0.5 animate-pulse rounded-sm">
                CLOUDBURST SIMULTION AACTIVE
              </span>
            )}
          </div>
          <p className="text-xs text-gray-500 font-mono">
            {t.weather_chart_subtitle || "Physics Threshold: Caine I-D Critical Curve"} • {t.lead_time_tag || "24-72h Lead Time"} • {activeZoneMeta.name}
          </p>
        </div>

        {/* ction button for Hackathon Judge Demo Runbook */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleToggleSimulation}
            className={`text-[11px] font-medium px-2.5 py-1 border rounded-md transition-colors cursor-pointer ${
              isSimulating
                ? 'bg-blue-600 text-white border-blue-700 hover:bg-blue-700'
                : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
            }`}
          >
            {isSimulating ? 'Reset Real Stream' : 'Simulate Cloudburst'}
          </button>
        </div>
      </div>

      {/* Geotechnical & Early Warning Lead-Time Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4 bg-gray-50 rounded-lg p-2.5 border border-gray-200 text-xs">
        <div>
          <span className="text-gray-500 block text-[10px] uppercase font-semibold">Peak Rain Rate</span>
          <span className="text-sm font-black text-black tabular-nums">{peakRainfall.toFixed(1)} mm/h</span>
        </div>
        <div>
          <span className="text-gray-500 block text-[10px] uppercase font-semibold">Max Saturation</span>
          <span className="text-sm font-black text-black tabular-nums">{maxSoil.toFixed(1)}%</span>
        </div>
        <div>
          <span className="text-gray-500 block text-[10px] uppercase font-semibold">Cumulative 72h</span>
          <span className="text-sm font-black text-black tabular-nums">{totalRain72h.toFixed(1)} mm</span>
        </div>
        <div>
          <span className="text-gray-500 block text-[10px] uppercase font-semibold">Physics Early Warning</span>
          {isBreached ? (
            <span className="text-xs font-bold text-red-700 bg-red-100 px-1.5 py-0.5 inline-block mt-0.5 rounded-sm">
              Threshold Breached
            </span>
          ) : (
            <span className="text-xs font-bold text-black inline-block mt-0.5 font-mono">
               Below Critical
            </span>
          )}
        </div>
      </div>

      {/* Recharts Area & Dynamic Physics Line Curve */}
      {!hasData ? (
        <div className="w-full h-64 flex items-center justify-center border border-dashed border-gray-300 text-xs text-gray-500 font-mono">
          No forecast data available
        </div>
      ) : (
        <div className="w-full h-64">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="rainfallMonochromeFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#000000" stopOpacity={0.45} />
                  <stop offset="95%" stopColor="#000000" stopOpacity={0.05} />
                </linearGradient>
              </defs>

              <XAxis
                dataKey="time"
                stroke="#444444"
                tick={{ fontSize: 10, fill: '#222222' }}
                tickLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                yAxisId="rain"
                stroke="#444444"
                tick={{ fontSize: 10, fill: '#222222' }}
                tickLine={false}
                unit="mm"
              />
              <YAxis
                yAxisId="soil"
                orientation="right"
                stroke="#888888"
                tick={{ fontSize: 10, fill: '#888888' }}
                tickLine={false}
                unit="%"
                domain={[0, 100]}
                hide={true}
              />

              <Tooltip content={<CustomChartTooltip />} />

              <Legend
                verticalAlign="top"
                align="right"
                iconType="plainline"
                wrapperStyle={{ fontSize: '11px', paddingBottom: '6px' }}
              />

              {/* Empirical Caine Physics Safety Curve */}
              <Line
                yAxisId="rain"
                type="monotone"
                dataKey="caineThreshold"
                name="Caine I-D Threshold Curve"
                stroke="#000000"
                strokeWidth={2}
                strokeDasharray="4 4"
                dot={false}
              />

              {/* Precipitation Fill */}
              <rea
                yAxisId="rain"
                type="monotone"
                dataKey="rainfall"
                name={t.rainfall_label || "Precipitation (mm/h)"}
                fill="url(#rainfallMonochromeFill)"
                stroke="#000000"
                strokeWidth={2.5}
              />

              {/* Soil Moisture Saturation Curve */}
              <Line
                yAxisId="soil"
                type="monotone"
                dataKey="soilMoisture"
                name={t.soil_moisture_label || "Soil Saturation (%)"}
                stroke="#666666"
                strokeWidth={1.5}
                strokeDasharray="2 2"
                dot={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
