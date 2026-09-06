import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import {
  fetchRiskZones,
  fetchRiskSummary,
  fetchWeatherForecast,
  fetchRoads,
  fetchEmergencyList,
  fetchRecentReports,
  submitHazardReport,
  ZONE_COORDINATES
} from '../services/api';
import {
  getQueuedCount,
  flushQueue,
  subscribeToQueue
} from '../services/offlineQueue';

const AppContext = createContext();

export function AppProvider({ children }) {
  const [language, setLanguage] = useState('en');
  const [selectedZone, setSelectedZone] = useState({
    zone_id: 'Z-SHL-01',
    name: 'Shillong East Ridge & Upper Shillong',
    district: 'East Khasi Hills',
    risk_level: 'severe',
    probability: 0.88,
    mean_slope_deg: 38.4,
    lat: 25.5788,
    lon: 91.8933,
    criticalRainThreshold: 35.0
  });

  const [riskZones, setRiskZones] = useState(null);
  const [riskSummary, setRiskSummary] = useState([]);
  const [roads, setRoads] = useState([]);
  const [settlements, setSettlements] = useState([]);
  const [weatherData, setWeatherData] = useState([]);
  const [reports, setReports] = useState([]);
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  // Milestone 3 Offline-First Field Hazard Reporting Synchronization State
  const [queuedReportsCount, setQueuedReportsCount] = useState(() => {
    try {
      return getQueuedCount();
    } catch {
      return 0;
    }
  });
  const [isOnline, setIsOnline] = useState(() => {
    return typeof navigator !== 'undefined' ? navigator.onLine : true;
  });
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncToast, setSyncToast] = useState(null);

  // Load all initial state
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [zonesData, summaryData, roadsData, emergencyData, reportsData] = await Promise.all([
        fetchRiskZones(),
        fetchRiskSummary(),
        fetchRoads(),
        fetchEmergencyList(),
        fetchRecentReports()
      ]);

      setRiskZones(zonesData);
      setRiskSummary(summaryData);
      setRoads(roadsData);
      setSettlements(emergencyData);
      setReports(reportsData);

      const zoneMeta = ZONE_COORDINATES[selectedZone?.zone_id || 'Z-SHL-01'] || { lat: 25.5788, lon: 91.8933 };
      const weather = await fetchWeatherForecast(zoneMeta.lat, zoneMeta.lon, selectedZone?.zone_id || 'Z-SHL-01');
      setWeatherData(weather);
    } catch (err) {
      console.error('[AppContext] Failed to load data:', err);
    } finally {
      setLoading(false);
    }
  }, [selectedZone?.zone_id]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Synchronize pending offline reports to backend API
  const syncPendingReports = useCallback(async () => {
    if (isSyncing) return null;
    setIsSyncing(true);
    try {
      const summary = await flushQueue(async () => {
        try {
          const freshReports = await fetchRecentReports();
          setReports(freshReports);
        } catch {
          // ignore
        }
      });

      if (summary && summary.synced > 0) {
        setSyncToast({
          message: `Successfully synchronized ${summary.synced} offline report${summary.synced > 1 ? 's' : ''} to central command.`,
          type: 'success'
        });
        setTimeout(() => setSyncToast(null), 5000);
        try {
          const freshReports = await fetchRecentReports();
          setReports(freshReports);
        } catch {
          // ignore
        }
      }
      return summary;
    } catch (err) {
      console.warn('[AppContext] Failed to sync offline reports:', err);
      return null;
    } finally {
      setIsSyncing(false);
    }
  }, [isSyncing]);

  // Listen to network transitions & offline queue mutations
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      console.log('[AppContext] Network restored. Triggering auto-sync...');
      syncPendingReports();
    };

    const handleOffline = () => {
      setIsOnline(false);
      console.log('[AppContext] Network severed. Operating in offline mode.');
    };

    if (typeof window !== 'undefined') {
      window.addEventListener('online', handleOnline);
      window.addEventListener('offline', handleOffline);
    }

    const unsubQueue = subscribeToQueue(({ count }) => {
      setQueuedReportsCount(count);
    });

    return () => {
      if (typeof window !== 'undefined') {
        window.removeEventListener('online', handleOnline);
        window.removeEventListener('offline', handleOffline);
      }
      unsubQueue();
    };
  }, [syncPendingReports]);

  // Handle zone selection change
  const handleSelectZone = async (zoneProps) => {
    const zoneId = zoneProps.zone_id || 'Z-SHL-01';
    const meta = ZONE_COORDINATES[zoneId] || { lat: 25.5788, lon: 91.8933, criticalRainThreshold: 35.0 };
    const fullZone = {
      ...zoneProps,
      lat: meta.lat,
      lon: meta.lon,
      criticalRainThreshold: meta.criticalRainThreshold
    };
    setSelectedZone(fullZone);

    try {
      const weather = await fetchWeatherForecast(meta.lat, meta.lon, zoneId);
      setWeatherData(weather);
    } catch (e) {
      console.warn('Weather refresh failed:', e);
    }
  };

  // Handle report submission
  const handleSubmitReport = async (reportData) => {
    const res = await submitHazardReport(reportData);
    if (res && res.success) {
      const updatedReports = await fetchRecentReports();
      setReports(updatedReports);
    }
    return res;
  };

  const handleRefreshWeather = async () => {
    const meta = ZONE_COORDINATES[selectedZone?.zone_id || 'Z-SHL-01'] || { lat: 25.5788, lon: 91.8933 };
    const weather = await fetchWeatherForecast(meta.lat, meta.lon, selectedZone?.zone_id || 'Z-SHL-01');
    setWeatherData(weather);
  };

  const value = {
    language,
    setLanguage,
    selectedZone,
    setSelectedZone: handleSelectZone,
    riskZones,
    riskSummary,
    roads,
    settlements,
    weatherData,
    reports,
    loading,
    isReportModalOpen,
    setIsReportModalOpen,
    submitReport: handleSubmitReport,
    refreshWeather: handleRefreshWeather,
    refreshAll: loadData,
    state: { language, selectedZone },
    // Milestone 3 Offline-First Field Hazard Reporting Synchronization Contracts
    queuedReportsCount,
    queuedCount: queuedReportsCount,
    isOnline,
    isSyncing,
    syncToast,
    setSyncToast,
    syncPendingReports,
    syncOfflineReports: syncPendingReports
  };

  return (
    <AppContext.Provider value={value}>
      {children}
      {/* Dynamic Sync Confirmation Toast */}
      {syncToast && (
        <div
          role="status"
          aria-live="polite"
          data-testid="sync-confirmation-toast"
          className="fixed bottom-4 right-4 z-50 p-3 bg-emerald-800 text-white font-mono text-xs border-2 border-black shadow-2xl flex items-center gap-2 animate-in fade-in"
        >
          <span className="text-base">✅</span>
          <span className="flex-1 font-semibold">{syncToast.message}</span>
          <button
            type="button"
            onClick={() => setSyncToast(null)}
            className="text-white hover:text-gray-200 font-bold ml-2 cursor-pointer"
          >
            ✕
          </button>
        </div>
      )}
    </AppContext.Provider>
  );
}

export function useAppState() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useAppState must be used within an AppProvider');
  }
  return context;
}

export default AppContext;
