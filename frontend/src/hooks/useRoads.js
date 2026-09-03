// frontend/src/hooks/useRoads.js
//
// Convenience hook for highway connectivity status, merged with the GIS
// polyline geometry needed to draw roads on the map.

import { useAppContext } from '../contexts/AppContext';

export default function useRoads() {
  const { roads, roadsWithGeometry, loading, error } = useAppContext();

  return {
    roads,
    roadsWithGeometry,
    isLoading: !!loading.roads,
    error: error.roads || null
  };
}
