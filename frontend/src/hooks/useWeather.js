// frontend/src/hooks/useWeather.js
//
// Convenience hook for the 72h precipitation forecast tied to the currently
// selected hazard zone, plus the judge-demo cloudburst simulation toggle.

import { useAppContext } from '../contexts/AppContext';

export default function useWeather() {
  const {
    weatherData,
    loading,
    error,
    refreshWeather,
    isSimulating,
    toggleSimulation,
    selectedZone
  } = useAppContext();

  return {
    weatherData,
    isLoading: !!loading.weather,
    error: error.weather || null,
    refreshWeather,
    isSimulating,
    toggleSimulation,
    selectedZone
  };
}
