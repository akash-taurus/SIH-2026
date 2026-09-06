import React, { useEffect, useMemo, useState, useRef } from 'react';
import { MapContainer, TileLayer, GeoJSON, Polyline, CircleMarker, Popup, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import Legend from './Legend';
import ThreeDMapHeatmap from './ThreeDMapHeatmap';
import { fetchLiveRadarFrames, fetchInSARDeformation } from '../services/api';

// Fix default leaflet icon paths if needed
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

// Green -> Yellow -> Orange -> Red Heatmap Palette
const RISK_COLORS = {
  low: '#22C55E',       // Green
  moderate: '#EB308',  // Yellow
  high: '#F97316',      // Orange
  severe: '#EF4444'     // Red
};

// Component to handle smooth pan to selected zone
function MapController({ selectedZone }) {
  const map = useMap();
  useEffect(() => {
    if (selectedZone && selectedZone.lat && selectedZone.lon) {
      map.flyTo([selectedZone.lat, selectedZone.lon], 10, { duration: 0.8 });
    }
  }, [selectedZone, map]);
  return null;
}

/**
 * MapView: Unified GIS Component with 3D Topography, 2D Tactical Heatmap,
 * Live DoAppler Weather Radar Loops, and Sentinel-1 InSAR Ground Motion.
 */
export default function MapView({
  riskZonesGeoJSON,
  roads = [],
  settlements = [],
  selectedZone = null,
  language = 'en',
  isSimulating = false,
  onSelectZone
}) {
  const [mapMode, setMapMode] = useState('3d'); // '3d' | '2d' | 'radar' | 'insar'
  const defaultCenter = useMemo(() => [25.5788, 91.8933], []);

  // DoAppler Radar Loop State
  const [radarFrames, setRadarFrames] = useState([]);
  const [currentFrameIndex, setCurrentFrameIndex] = useState(0);
  const [isPlayingRadar, setIsPlayingRadar] = useState(true);
  const [radarOpacity, setRadarOpacity] = useState(0.75);
  const radarTimerRef = useRef(null);

  // Sentinel-1 InSAR Ground Motion State
  const [insarData, setInsarData] = useState(null);

  // Fetch Radar & InSAR data
  useEffect(() => {
    fetchLiveRadarFrames().then((data) => {
      if (data && Array.isArray(data.frames) && data.frames.length > 0) {
        setRadarFrames(data.frames);
        setCurrentFrameIndex(data.frames.length - 1);
      }
    });

    fetchInSARDeformation().then((data) => {
      if (data) setInsarData(data);
    });
  }, []);

  // DoAppler Radar nimation Loop
  useEffect(() => {
    if (mapMode === 'radar' && isPlayingRadar && radarFrames.length > 0) {
      radarTimerRef.current = setInterval(() => {
        setCurrentFrameIndex((prev) => (prev + 1) % radarFrames.length);
      }, 1000);
    } else {
      if (radarTimerRef.current) clearInterval(radarTimerRef.current);
    }
    return () => {
      if (radarTimerRef.current) clearInterval(radarTimerRef.current);
    };
  }, [mapMode, isPlayingRadar, radarFrames]);

  const currentRadarTileUrl = useMemo(() => {
    if (!radarFrames || radarFrames.length === 0 || !radarFrames[currentFrameIndex]) {
      return null;
    }
    return radarFrames[currentFrameIndex].tile_url;
  }, [radarFrames, currentFrameIndex]);

  const currentFrameTimestamp = useMemo(() => {
    if (!radarFrames || !radarFrames[currentFrameIndex]) return 'Live Radar';
    const ts = radarFrames[currentFrameIndex].time;
    if (!ts) return 'Live Telemetry';
    const d = new Date(ts * 1000);
    return `${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} IST (${radarFrames[currentFrameIndex].type === 'nowcast_forecast' ? 'Nowcast' : 'Past'})`;
  }, [radarFrames, currentFrameIndex]);

  const styleZone = useMemo(() => {
    return (feature) => {
      const level = feature.properties.risk_level?.toLowerCase() || 'low';
      const isSelected = selectedZone?.zone_id === feature.properties.zone_id;
      const color = RISK_COLORS[level] || '#22C55E';
      return {
        fillColor: color,
        weight: isSelected ? 3.5 : 2,
        opacity: 1,
        color: isSelected ? '#000000' : color,
        dashArray: isSelected ? '4, 4' : null,
        fillOpacity: level === 'severe' ? 0.75 : level === 'high' ? 0.65 : level === 'moderate' ? 0.55 : 0.45
      };
    };
  }, [selectedZone]);

  const highwayGeometries = useMemo(() => ({
    'NH-40': [
      [26.115, 91.815], // Jorabat
      [25.901, 91.881], // Nongpoh
      [25.661, 91.902], // Umiam
      [25.578, 91.893]  // Shillong
    ],
    'NH-6': [
      [25.578, 91.893], // Shillong
      [25.441, 92.203], // Jowai
      [25.210, 92.420], // Khliehriat
      [24.830, 92.770]  // Silchar border
    ],
    'SH-5': [
      [25.578, 91.893], // Shillong
      [25.271, 91.731], // Sohra
      [25.180, 91.640]  // Shella
    ]
  }), []);

  const getRiskBadgeColor = (level) => {
    switch (level?.toLowerCase()) {
      case 'severe': return 'background: #EF4444; color: white;';
      case 'high': return 'background: #F97316; color: white;';
      case 'moderate': return 'background: #EB308; color: black;';
      default: return 'background: #22C55E; color: white;';
    }
  };

  return (
    <div className="space-y-2">
      {/* Map Mode Switcher Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 bg-white border-2 border-black p-2.5">
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            type="button"
            onClick={() => setMapMode('3d')}
            className={`text-xs font-medium px-4 py-1.5 border rounded-l-md transition-colors cursor-pointer ${
              mapMode === '3d'
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
            }`}
          >
            3D Topo-Heatmap & Heights
          </button>
          <button
            type="button"
            onClick={() => setMapMode('2d')}
            className={`text-xs font-medium px-4 py-1.5 border-t border-b border-r transition-colors cursor-pointer ${
              mapMode === '2d'
                 ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
            }`}
          >
            2D Tactical Heatmap
          </button>

          <button
            type="button"
            onClick={() => setMapMode('insar')}
            className={`text-xs font-medium px-4 py-1.5 border-t border-b border-r rounded-r-md transition-colors cursor-pointer ${
              mapMode === 'insar'
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
            }`}
          >
            ️ Sentinel-1 InSAR Ground Motion
          </button>
        </div>

        <div className="hidden md:flex items-center gap-2 text-xs text-gray-600">
          <span>Active Sector:</span>
          <span className="font-medium text-gray-800 bg-gray-100 px-2.5 py-1 rounded-md border border-gray-200">
            {selectedZone?.name || 'Shillong Peak Ridge'} ({selectedZone?.elevation_m || 1496}m MSL)
          </span>
        </div>
      </div>

      {/* 3D Topographic Heatmap Mode */}
      {mapMode === '3d' ? (
        <ThreeDMapHeatmap
          riskZonesGeoJSON={riskZonesGeoJSON}
          selectedZone={selectedZone}
          language={language}
          isSimulating={isSimulating}
          onSelectZone={onSelectZone}
        />
      ) : (
        <div className="relative w-full h-[800px] border border-gray-200 rounded-xl shadow-sm overflow-hidden bg-[#FFF]">
          <MapContainer
            key={mapMode}
            center={defaultCenter}
            zoom={9}
            scrollWheelZoom={true}
            preferCanvas={true}
            className="w-full h-full"
          >
            <MapController selectedZone={selectedZone} />

            {/* Base OpenStreetMap Cartography */}
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              maxZoom={18}
            />

            {/* 2D Tactical Heatmap Polygons */}
            {mapMode === '2d' && riskZonesGeoJSON && (
              <GeoJSON
                data={riskZonesGeoJSON}
                style={styleZone}
                onEachFeature={(feature, layer) => {
                  layer.on({
                    click: () => onSelectZone && onSelectZone(feature.properties)
                  });
                  const badgeStyle = getRiskBadgeColor(feature.properties.risk_level);
                  layer.bindPopup(`
                    <div style="font-family: Inter, sans-serif; min-width: 210px; padding: 4px;">
                      <div style="font-weight: 800; font-size: 13px; text-transform: uppercase; border-bottom: 2px solid black; padding-bottom: 4px; margin-bottom: 6px;">
                        ${feature.properties.name}
                      </div>
                      <div style="font-size: 11px; margin-bottom: 3px;">
                        <b>Elevation Height:</b> ${feature.properties.elevation_m || 1400} m MSL
                      </div>
                      <div style="font-size: 11px; margin-bottom: 3px;">
                        <b>Risk Level:</b> <span style="${badgeStyle} padding: 1px 6px; font-weight: bold; font-family: monospace; border-radius: 2px;">${(feature.properties.risk_level || 'low').toUApperCase()}</span> (${Math.round((feature.properties.probability || 0.5) * 100)}%)
                      </div>
                      <div style="font-size: 11px; margin-bottom: 3px;">
                        <b>Mean Slope:</b> ${feature.properties.mean_slope_deg || 30.0}°
                      </div>
                      <div style="font-size: 11px; margin-bottom: 3px;">
                        <b>24h Rainfall:</b> ${feature.properties.rainfall_24h_mm || 0} mm
                      </div>
                    </div>
                  `);
                }}
              />
            )}

            {/* Sentinel-1 InSAR Ground Motion Scatter Markers */}
            {mapMode === 'insar' && insarData && Array.isArray(insarData.features) && (
              insarData.features.map((feat, idx) => {
                if (!feat || !feat.geometry || !Array.isArray(feat.geometry.coordinates)) return null;
                const coords = feat.geometry.coordinates;
                const lon = Number(coords[0]);
                const lat = Number(coords[1]);
                if (isNaN(lat) || isNaN(lon)) return null;
                const props = feat.properties || {};
                const markerColor = props.severity_color || '#EF4444';
                return (
                  <CircleMarker
                    key={props.id || `insar-${idx}`}
                    center={[lat, lon]}
                    radius={10}
                    pathOptions={{
                      color: '#000000',
                      weight: 2,
                      fillColor: markerColor,
                      fillOpacity: 0.9
                    }}
                  >
                    <Popup>
                      <div className="font-mono text-xs p-1 min-w-[240px] max-w-[320px] whitespace-normal break-words">
                        <h4 className="font-bold text-black border-b border-black pb-1 uppercase">{props.name || 'InSAR Telemetry Point'}</h4>
                        <div className="space-y-1 mt-1 text-[11px]">
                          <div><b>Satellite:</b> {props.satellite || 'Sentinel-1'}</div>
                          <div><b>LOS Velocity:</b> <span className="font-bold" style={{ color: markerColor }}>{props.los_velocity_mm_year} mm/yr</span></div>
                          <div><b>Cumulative Displacement:</b> {props.cumulative_displacement_mm} mm</div>
                          <div><b>Interferometric Coherence:</b> γ = {props.coherence}</div>
                          <div><b>Kinematic Trend:</b> <span className="font-bold">{props.displacement_trend}</span></div>
                          <div><b>Elevation:</b> {props.elevation_m}m MSL</div>
                        </div>
                      </div>
                    </Popup>
                  </CircleMarker>
                );
              })
            )}

            {/* Road Polylines */}
            {roads.map((road) => {
              if (!road || !road.road_id) return null;
              const positions = highwayGeometries[road.road_id];
              if (!positions || !Array.isArray(positions) || positions.length === 0) return null;

              const isBlocked = road.status === 'blocked';
              const isRestricted = road.status === 'restricted';
              const color = isBlocked ? '#000000' : isRestricted ? '#777777' : '#22C55E';
              const dashArray = isBlocked ? '6, 6' : isRestricted ? '3, 6' : null;

              return (
                <Polyline
                  key={road.road_id}
                  positions={positions}
                  pathOptions={{
                    color,
                    weight: isBlocked ? 5 : 4,
                    dashArray,
                    opacity: 0.95
                  }}
                >
                  <Popup>
                    <div style={{ fontFamily: 'monospace', fontSize: '11px', padding: '4px' }}>
                      <b style={{ textTransform: 'uppercase', fontSize: '12px' }}>{road.name}</b>
                      <div style={{ marginTop: '4px' }}>
                        <b>Status:</b>{' '}
                        <span style={{ textTransform: 'uppercase', fontWeight: 'bold' }}>
                          {road.status}
                        </span>
                      </div>
                      <div><b>Nearest Zone:</b> {road.nearest_zone_id}</div>
                      <div><b>Passability:</b> {road.passability_pct}%</div>
                    </div>
                  </Popup>
                </Polyline>
              );
            })}

            {/* Settlement evacuation markers */}
            {settlements.map((s, idx) => {
              if (!s || s.lat === undefined || s.lon === undefined || isNaN(Number(s.lat)) || isNaN(Number(s.lon))) {
                return null;
              }
              const lat = Number(s.lat);
              const lon = Number(s.lon);
              return (
                <CircleMarker
                  key={s.settlement_id || `settlement-${idx}`}
                  center={[lat, lon]}
                  radius={6}
                  pathOptions={{
                    color: '#000000',
                    weight: 1.5,
                    fillColor: RISK_COLORS[s.risk_level?.toLowerCase()] || '#22C55E',
                    fillOpacity: 0.95
                  }}
                >
                  <Popup>
                    <div style={{ fontFamily: 'monospace', fontSize: '11px', padding: '4px' }}>
                      <b style={{ textTransform: 'uppercase', fontSize: '12px' }}>{s.name || s.village}</b>
                      <div style={{ marginTop: '4px' }}><b>Population:</b> {s.population}</div>
                      <div><b>Risk Level:</b> {s.risk_level}</div>
                      <div><b>Distance to Slope:</b> {s.distance_km} km</div>
                    </div>
                  </Popup>
                </CircleMarker>
              );
            })}
          </MapContainer>



          {/* Sentinel-1 InSAR Legend Overlay */}
          {mapMode === 'insar' && (
            <div className="absolute bottom-3 right-3 z-[1000] bg-white/95 backdrop-blur-sm border border-gray-200 rounded-lg p-3 text-xs shadow-sm max-w-xs">
              <h5 className="font-semibold text-gray-800 border-b border-gray-200 pb-1.5 mb-2">
                ️ Sentinel-1 PS-InSAR Ground Displacement (LOS mm/yr)
              </h5>
              <div className="space-y-1 text-[10px]">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span className="w-3 h-3 bg-red-600 border border-black inline-block"></span>
                    <span>Severe Subsidence (&lt; -15 mm/yr)</span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span className="w-3 h-3 bg-orange-500 border border-black inline-block"></span>
                    <span>Active Downward Shear (-10 to -15 mm/yr)</span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span className="w-3 h-3 bg-yellow-500 border border-black inline-block"></span>
                    <span>Moderate Slope Creep (-4 to -10 mm/yr)</span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span className="w-3 h-3 bg-green-600 border border-black inline-block"></span>
                    <span>Geotechnically Stable (&gt; -4 mm/yr)</span>
                  </div>
                </div>
              </div>
              <p className="text-[9px] text-gray-500 mt-1.5 pt-1 border-t border-gray-200">
                Copernicus Sentinel-1 SR C-Band Persistent Scatterer Interferometry
              </p>
            </div>
          )}

          {/* Standard 2D Map Legend */}
          {mapMode === '2d' && <Legend language={language} />}
        </div>
      )}
    </div>
  );
}
