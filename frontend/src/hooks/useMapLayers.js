// frontend/src/hooks/useMapLayers.js
//
// Convenience hook for the map's layer visibility toggles
// (hazard zones, roads, settlements, rainfall indicator).

import { useAppContext } from '../contexts/AppContext';

export default function useMapLayers() {
  const { layers, toggleLayer, settlements } = useAppContext();

  return { layers, toggleLayer, settlements };
}
