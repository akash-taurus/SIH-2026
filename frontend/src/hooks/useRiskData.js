// frontend/src/hooks/useRiskData.js
//
// Convenience hook for components that only care about hazard-zone data
// (the GeoJSON risk polygons, the regional summary, and zone selection).

import { useAppContext } from '../contexts/AppContext';

export default function useRiskData() {
  const {
    riskZonesGeoJSON,
    riskSummary,
    selectedZone,
    setSelectedZone,
    zoneCentroids,
    loading,
    error
  } = useAppContext();

  return {
    riskZonesGeoJSON,
    riskSummary,
    zoneCentroids,
    selectedZone,
    selectZone: setSelectedZone,
    isLoading: !!loading.zones,
    error: error.zones || error.summary || null
  };
}
