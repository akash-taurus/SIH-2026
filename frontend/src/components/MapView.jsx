// frontend/src/components/MapView.jsx
//
// Zero-key GIS map: grayscale OSM basemap + dynamic GeoJSON hazard-zone
// polygons + road-status polylines + settlement markers + an optional
// rainfall-intensity indicator layer. Reads/writes global state through
// AppContext (via the useRiskData / useRoads / useMapLayers hooks) so the
// rest of the dashboard (WeatherChart, AlertBanner, RoadTable, ...) stays
// in sync with whatever the user selects on the map.

import React, { useEffect, useMemo } from 'react';
import {
  MapContainer,
  TileLayer,
  GeoJSON,
  Polyline,
  CircleMarker,
  Popup,
  Tooltip,
  useMap
} from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import '../styles/mapStyles.css';

import { translations } from '../utils/translations';
import useRiskData from '../hooks/useRiskData';
import useRoads from '../hooks/useRoads';
import useMapLayers from '../hooks/useMapLayers';
import Legend from './Legend';
import LayerControl from './LayerControl';

const RISK_COLORS = {
  low: '#EBEBEB',
  moderate: '#AAAAAA',
  high: '#444444',
  severe: '#000000'
};

const ROAD_STYLE = {
  open: { color: '#000000', weight: 2.5, opacity: 1, dashArray: null },
  at_risk: { color: '#000000', weight: 2.5, opacity: 1, dashArray: '8, 6' },
  blocked: { color: '#000000', weight: 4, opacity: 1, dashArray: '2, 6' }
};

const DEFAULT_CENTER = [25.5788, 91.8933]; // Shillong, Meghalaya
const DEFAULT_ZOOM = 9;

/** Keeps the Leaflet map correctly sized when its container is resized
 *  (e.g. sidebar collapse, responsive breakpoints, tab switches). */
function MapResizeHandler() {
  const map = useMap();

  useEffect(() => {
    const handleResize = () => map.invalidateSize();
    window.addEventListener('resize', handleResize);

    // Also fix sizing once right after mount, since the container may not
    // have its final layout dimensions on first paint (e.g. inside a
    // flex/grid dashboard column).
    const timeout = setTimeout(handleResize, 200);

    return () => {
      window.removeEventListener('resize', handleResize);
      clearTimeout(timeout);
    };
  }, [map]);

  return null;
}

function zoneStyle(feature) {
  const level = feature.properties?.risk_level || 'low';
  const isSevereOrHigh = level === 'severe' || level === 'high';

  return {
    fillColor: RISK_COLORS[level] || RISK_COLORS.low,
    weight: isSevereOrHigh ? 2 : 1,
    opacity: 1,
    color: '#000000',
    fillOpacity: level === 'severe' ? 0.85 : 0.6
  };
}

export default function MapView({ language = 'en' }) {
  const { riskZonesGeoJSON, zoneCentroids, selectZone, isLoading } = useRiskData();
  const { roadsWithGeometry } = useRoads();
  const { layers, toggleLayer, settlements } = useMapLayers();

  const t = translations[language] || translations.en;

  // GeoJSON layer must be re-keyed when the underlying data changes, since
  // react-leaflet's <GeoJSON> does not diff its `data` prop internally. The
  // key must stay STABLE across re-renders that don't change the data, or
  // the layer gets force-remounted every render (stacking duplicate SVG
  // paths and breaking click/popup handling).
  const geoJsonKey = useMemo(() => {
    const features = riskZonesGeoJSON?.features || [];
    return `zones-${features.length}-${features.map((f) => f.properties?.zone_id).join(',')}`;
  }, [riskZonesGeoJSON]);

  const onEachZoneFeature = (feature, layer) => {
    const props = feature.properties;
    layer.on({
      click: () => selectZone(props)
    });
    layer.bindPopup(
      `<div class="ner-map-popup">
        <h4>${props.name}</h4>
        <p class="ner-popup-risk">${props.risk_level?.toUpperCase()} &middot; ${Math.round((props.probability || 0) * 100)}%</p>
        <p>Slope: ${props.mean_slope_deg}&deg;</p>
        <p>24h Rainfall: ${props.rainfall_24h_mm} mm</p>
      </div>`
    );
  };

  return (
    <div className="ner-map-shell">
      <MapContainer center={DEFAULT_CENTER} zoom={DEFAULT_ZOOM} scrollWheelZoom>
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        />

        <MapResizeHandler />

        {layers.hazardZones && riskZonesGeoJSON && (
          <GeoJSON
            key={geoJsonKey}
            data={riskZonesGeoJSON}
            style={zoneStyle}
            onEachFeature={onEachZoneFeature}
          />
        )}

        {layers.roads && roadsWithGeometry.map((road) =>
          road.path ? (
            <Polyline
              key={road.road_id}
              positions={road.path}
              pathOptions={ROAD_STYLE[road.status] || ROAD_STYLE.open}
            >
              <Tooltip sticky>
                <strong>{road.road_id}</strong> &mdash; {road.name}
                <br />
                {t[`road_${road.status}`] || road.status}
                {road.blockage_reason ? <><br />{road.blockage_reason}</> : null}
              </Tooltip>
            </Polyline>
          ) : null
        )}

        {layers.settlements && settlements.map((settlement) => (
          <CircleMarker
            key={settlement.id}
            center={[settlement.latitude, settlement.longitude]}
            radius={settlement.type === 'town' ? 7 : 5}
            pathOptions={{
              color: '#ffffff',
              weight: 1,
              fillColor: '#000000',
              fillOpacity: 1
            }}
          >
            <Tooltip>
              <strong>{settlement.name}</strong>
              <br />
              {t.pop_label || 'Population'}: {settlement.population.toLocaleString()}
            </Tooltip>
          </CircleMarker>
        ))}

        {layers.rainfall && zoneCentroids.map((zone) => (
          <CircleMarker
            key={`rain-${zone.zone_id}`}
            center={[zone.lat, zone.lon]}
            radius={Math.max(6, Math.min(30, (zone.rainfall_24h_mm || 0) / 8))}
            pathOptions={{
              color: '#000000',
              weight: 1,
              fillColor: '#AAAAAA',
              fillOpacity: 0.35
            }}
          >
            <Popup>
              <div className="ner-map-popup">
                <h4>{zone.name}</h4>
                <p>24h Rainfall: {zone.rainfall_24h_mm} mm</p>
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>

      <Legend language={language} />
      <LayerControl layers={layers} onToggle={toggleLayer} language={language} />

      {isLoading && (
        <div
          className="ner-map-legend"
          style={{ bottom: 12, top: 'auto', left: 12 }}
        >
          {t.map_loading || 'Loading hazard zones\u2026'}
        </div>
      )}
    </div>
  );
}
