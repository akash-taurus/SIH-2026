from typing import Dict, Any, List
import math
from .physics import SOIL_GEOTECHNICAL_PROPERTIES

def _num(payload: Dict[str, Any], key: str, default: float, alt_key: Optional[str] = None) -> float:
    v = payload.get(key)
    if v is None and alt_key:
        v = payload.get(alt_key)
    if v is None:
        return default
    try:
        return float(v)
    except (ValueError, TypeError):
        return default

class FeatureExtractor:
    """
    14-Dimensional Geotechnical & Hydrological Feature Engineering Matrix.
    Extracts, normalizes, and validates topographical, geotechnical, and meteorology signals.
    All vector values are standardized as numeric floats for model consumption.
    """

    FEATURE_NAMES = [
        "slope_deg",
        "aspect_deg",
        "elevation_m",
        "twi",
        "dist_to_road_m",
        "rain_1h",
        "rain_24h",
        "rain_7d",
        "api_15_mm",
        "soil_saturation_pct",
        "forecast_48h_rain",
        "historical_slide_density",
        "soil_cohesion_kpa",
        "friction_angle_deg"
    ]

    @staticmethod
    def extract_vector(payload: Dict[str, Any]) -> Dict[str, float]:
        """
        Converts raw sensor / zone dictionary to standardized high-precision numeric feature vector.
        """
        slope = _num(payload, "slope_deg", 28.0, "mean_slope_deg")
        aspect = _num(payload, "aspect_deg", 180.0)
        elevation = _num(payload, "elevation_m", 1496.0)
        twi = _num(payload, "twi", 6.8)
        dist_to_road = _num(payload, "dist_to_road_m", 45.0)

        rain_1h = _num(payload, "rain_1h", 12.0, "rainfall_1h_mm")
        rain_24h = _num(payload, "rain_24h", 65.0, "rainfall_24h_mm")
        rain_7d = _num(payload, "rain_7d", 180.0, "rainfall_7d_mm")
        soil_sat = _num(payload, "soil_saturation_pct", 0.65, "soil_moisture")
        forecast_48h = _num(payload, "forecast_48h_rain", 110.0)
        hist_density = _num(payload, "historical_slide_density", 3.2)
        soil_type = str(payload.get("soil_type") or "Clayey Loam on Weathered Quartzite")

        soil_props = SOIL_GEOTECHNICAL_PROPERTIES.get(soil_type, SOIL_GEOTECHNICAL_PROPERTIES["default"])
        cohesion = float(soil_props["cohesion_kpa"])
        friction_angle = float(soil_props["friction_angle_deg"])

        if soil_sat > 1.0:
            soil_sat = soil_sat / 100.0

        # Calculate 15-Day Antecedent Precipitation Index (API-15) with decay constant k=0.85
        api_15 = rain_1h + (rain_24h * 0.85) + (rain_7d * 0.32)

        return {
            "slope_deg": slope,
            "aspect_deg": aspect,
            "elevation_m": elevation,
            "twi": twi,
            "dist_to_road_m": dist_to_road,
            "rain_1h": rain_1h,
            "rain_24h": rain_24h,
            "rain_7d": rain_7d,
            "api_15_mm": round(api_15, 2),
            "soil_saturation_pct": soil_sat,
            "forecast_48h_rain": forecast_48h,
            "historical_slide_density": hist_density,
            "soil_cohesion_kpa": cohesion,
            "friction_angle_deg": friction_angle
        }

    XGB_FEATURE_COLUMNS = [
        "slope_deg", "elevation_m", "aspect_deg", "ndvi",
        "rain_1h_mm", "rain_6h_mm", "rain_12h_mm", "rain_24h_mm",
        "rain_3d_mm", "rain_7d_mm", "rain_14d_mm", "rain_30d_mm",
        "soil_saturation_proxy", "curvature", "twi", "distance_to_drainage_m",
        "rain_intensity_ratio", "rain_7d_change_ratio", "north_facing", "low_vegetation", "high_slope"
    ]

    @classmethod
    def extract_xgb_dataframe(cls, payload: Dict[str, Any]):
        """
        Builds a 21-dimensional DataFrame aligned with the trained XGBoost model bundle.
        """
        import pandas as pd
        slope = _num(payload, "slope_deg", 28.0, "mean_slope_deg")
        elevation = _num(payload, "elevation_m", 1496.0)
        aspect = _num(payload, "aspect_deg", 180.0)
        ndvi = _num(payload, "ndvi", 0.55)

        rain_24h = _num(payload, "rain_24h_mm", _num(payload, "rain_24h", 65.0, "rainfall_24h_mm"))
        rain_1h = _num(payload, "rain_1h_mm", _num(payload, "rain_1h", rain_24h / 24.0, "rainfall_1h_mm"))
        rain_6h = _num(payload, "rain_6h_mm", rain_24h / 4.0)
        rain_12h = _num(payload, "rain_12h_mm", rain_24h / 2.0)
        rain_3d = _num(payload, "rain_3d_mm", rain_24h * 2.2)
        rain_7d = _num(payload, "rain_7d_mm", _num(payload, "rain_7d", 180.0, "rainfall_7d_mm"))
        rain_14d = _num(payload, "rain_14d_mm", rain_7d * 1.7)
        rain_30d = _num(payload, "rain_30d_mm", rain_7d * 3.5)

        soil_sat = _num(payload, "soil_saturation_pct", 0.65, "soil_moisture")
        raw_proxy = payload.get("soil_saturation_proxy")
        soil_proxy = float(raw_proxy) if raw_proxy is not None else (soil_sat * 100.0 if soil_sat <= 1.0 else soil_sat)
        curvature = _num(payload, "curvature", 0.0)
        twi = _num(payload, "twi", 6.8)
        dist_drainage = _num(payload, "distance_to_drainage_m", _num(payload, "dist_to_road_m", 45.0))

        row = {
            "slope_deg": slope,
            "elevation_m": elevation,
            "aspect_deg": aspect,
            "ndvi": ndvi,
            "rain_1h_mm": rain_1h,
            "rain_6h_mm": rain_6h,
            "rain_12h_mm": rain_12h,
            "rain_24h_mm": rain_24h,
            "rain_3d_mm": rain_3d,
            "rain_7d_mm": rain_7d,
            "rain_14d_mm": rain_14d,
            "rain_30d_mm": rain_30d,
            "soil_saturation_proxy": soil_proxy,
            "curvature": curvature,
            "twi": twi,
            "distance_to_drainage_m": dist_drainage,
            "rain_intensity_ratio": (rain_3d + 1e-3) / (rain_30d / 10 + 1e-3),
            "rain_7d_change_ratio": (rain_7d + 1e-3) / (rain_30d / 4 + 1e-3),
            "north_facing": 1.0 if (aspect > 315 or aspect < 45) else 0.0,
            "low_vegetation": 1.0 if ndvi < 0.3 else 0.0,
            "high_slope": 1.0 if slope >= 30.0 else 0.0,
        }
        return pd.DataFrame([row])[cls.XGB_FEATURE_COLUMNS]
