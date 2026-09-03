// frontend/src/contexts/AppContext.jsx
//
// Global application state for NER-LEWS.
// Owns: language selection, selected hazard zone, all fetched dashboard data
// (risk zones, roads, settlements, emergency list, weather, citizen reports),
// map layer visibility toggles, and the citizen "Report Hazard" modal flow.
//
// Every component (MapView, WeatherChart, RoadTable, EmergencyPrioritizationCard,
// ReportModal, RecentReportsTable, Navbar, AlertBanner ...) should read/write
// state through useAppContext() instead of fetching data or holding it locally,
// so the whole dashboard stays in sync (e.g. selecting a zone on the map updates
// the weather chart and the alert banner at the same time).

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState
} from 'react';
import {
  fetchRiskZones,
  fetchRiskSummary,
  fetchRoads,
  fetchEmergencyList,
  fetchWeatherForecast,
  fetchRecentReports,
  submitHazardReport,
  toggleCloudburstSimulation,
  getSimulationState,
  ZONE_COORDINATES
} from '../services/api';
import settlementsData from '../mockData/settlements.json';
import roadPathsData from '../mockData/roadPaths.json';

const AppContext = createContext(null);

const DEFAULT_ZONE_ID = 'Z-SHL-01';

/** Computes a rough centroid for a GeoJSON Polygon's outer ring. */
function getPolygonCentroid(coordinates) {
  const ring = coordinates?.[0] || [];
  if (ring.length === 0) return null;
  let sumLat = 0;
  let sumLon = 0;
  ring.forEach(([lon, lat]) => {
    sumLat += lat;
    sumLon += lon;
  });
  return { lat: sumLat / ring.length, lon: sumLon / ring.length };
}

export function AppProvider({ children }) {
  // ---- Localization -------------------------------------------------
  const [language, setLanguage] = useState('en');

  // ---- Selected hazard zone (drives map highlight + weather chart) --
  const [selectedZone, setSelectedZoneState] = useState(null);

  // ---- Server / mock data --------------------------------------------
  const [riskZonesGeoJSON, setRiskZonesGeoJSON] = useState(null);
  const [riskSummary, setRiskSummary] = useState([]);
  const [roads, setRoads] = useState([]);
  const [emergencyList, setEmergencyList] = useState([]);
  const [weatherData, setWeatherData] = useState([]);
  const [reports, setReports] = useState([]);
  const [settlements] = useState(settlementsData);

  const [loading, setLoading] = useState({
    zones: true,
    roads: true,
    emergency: true,
    weather: true,
    reports: true
  });
  const [error, setError] = useState({});

  // ---- Map layer visibility toggles ----------------------------------
  const [layers, setLayers] = useState({
    hazardZones: true,
    roads: true,
    settlements: true,
    rainfall: false
  });

  // ---- Citizen "Report Hazard" modal ----------------------------------
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [isSimulating, setIsSimulating] = useState(getSimulationState());

  const setError1 = useCallback((key, value) => {
    setError((prev) => ({ ...prev, [key]: value }));
  }, []);

  // ---- Initial data load (zones, summary, roads, emergency, reports) -
  useEffect(() => {
    let isMounted = true;

    (async () => {
      try {
        const zones = await fetchRiskZones();
        if (isMounted) setRiskZonesGeoJSON(zones);
      } catch (err) {
        if (isMounted) setError1('zones', err.message);
      } finally {
        if (isMounted) setLoading((l) => ({ ...l, zones: false }));
      }

      try {
        const summary = await fetchRiskSummary();
        if (isMounted) setRiskSummary(summary);
      } catch (err) {
        if (isMounted) setError1('summary', err.message);
      }

      try {
        const roadsData = await fetchRoads();
        if (isMounted) setRoads(roadsData);
      } catch (err) {
        if (isMounted) setError1('roads', err.message);
      } finally {
        if (isMounted) setLoading((l) => ({ ...l, roads: false }));
      }

      try {
        const emergency = await fetchEmergencyList();
        if (isMounted) setEmergencyList(emergency);
      } catch (err) {
        if (isMounted) setError1('emergency', err.message);
      } finally {
        if (isMounted) setLoading((l) => ({ ...l, emergency: false }));
      }

      try {
        const recentReports = await fetchRecentReports();
        if (isMounted) setReports(recentReports);
      } catch (err) {
        if (isMounted) setError1('reports', err.message);
      } finally {
        if (isMounted) setLoading((l) => ({ ...l, reports: false }));
      }
    })();

    return () => {
      isMounted = false;
    };
  }, [setError1]);

  // ---- Weather forecast: refetch whenever the selected zone changes --
  const refreshWeather = useCallback(async (zoneOverride) => {
    const targetZone = zoneOverride || selectedZone;
    const zoneId = targetZone?.zone_id || DEFAULT_ZONE_ID;
    const coords = ZONE_COORDINATES[zoneId] || ZONE_COORDINATES[DEFAULT_ZONE_ID];

    setLoading((l) => ({ ...l, weather: true }));
    try {
      const forecast = await fetchWeatherForecast(coords.lat, coords.lon, zoneId);
      setWeatherData(forecast);
    } catch (err) {
      setError1('weather', err.message);
    } finally {
      setLoading((l) => ({ ...l, weather: false }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedZone]);

  useEffect(() => {
    refreshWeather();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedZone]);

  const setSelectedZone = useCallback((zoneProperties) => {
    setSelectedZoneState(zoneProperties);
  }, []);

  const toggleSimulation = useCallback((enable) => {
    const next = toggleCloudburstSimulation(enable);
    setIsSimulating(next);
    refreshWeather();
    return next;
  }, [refreshWeather]);

  // ---- Map layer toggles -----------------------------------------------
  const toggleLayer = useCallback((key) => {
    setLayers((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  // ---- Citizen report modal flow ---------------------------------------
  const openReportModal = useCallback(() => setIsReportModalOpen(true), []);
  const closeReportModal = useCallback(() => setIsReportModalOpen(false), []);

  const handleSubmitReport = useCallback(async (reportData) => {
    const result = await submitHazardReport(reportData);
    const updatedReports = await fetchRecentReports();
    setReports(updatedReports);
    setIsReportModalOpen(false);
    return result;
  }, []);

  // ---- Derived data: zone centroids (for rainfall layer / popups) -----
  const zoneCentroids = useMemo(() => {
    const features = riskZonesGeoJSON?.features || [];
    return features
      .map((feature) => {
        const centroid = getPolygonCentroid(feature.geometry?.coordinates);
        if (!centroid) return null;
        return { ...feature.properties, ...centroid };
      })
      .filter(Boolean);
  }, [riskZonesGeoJSON]);

  // ---- Derived data: roads merged with GIS polyline geometry -----------
  const roadsWithGeometry = useMemo(() => {
    return roads.map((road) => ({
      ...road,
      path: roadPathsData[road.road_id]?.coordinates || null
    }));
  }, [roads]);

  const value = useMemo(() => ({
    // localization
    language,
    setLanguage,

    // selection
    selectedZone,
    setSelectedZone,

    // raw + derived data
    riskZonesGeoJSON,
    riskSummary,
    roads,
    roadsWithGeometry,
    settlements,
    emergencyList,
    weatherData,
    reports,
    zoneCentroids,

    // status
    loading,
    error,

    // map layers
    layers,
    toggleLayer,

    // weather / simulation
    refreshWeather,
    isSimulating,
    toggleSimulation,

    // citizen reports
    isReportModalOpen,
    openReportModal,
    closeReportModal,
    handleSubmitReport
  }), [
    language,
    selectedZone,
    setSelectedZone,
    riskZonesGeoJSON,
    riskSummary,
    roads,
    roadsWithGeometry,
    settlements,
    emergencyList,
    weatherData,
    reports,
    zoneCentroids,
    loading,
    error,
    layers,
    toggleLayer,
    refreshWeather,
    isSimulating,
    toggleSimulation,
    isReportModalOpen,
    openReportModal,
    closeReportModal,
    handleSubmitReport
  ]);

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useAppContext() {
  const ctx = useContext(AppContext);
  if (!ctx) {
    throw new Error('useAppContext must be used within an <AppProvider>');
  }
  return ctx;
}

export default AppContext;
