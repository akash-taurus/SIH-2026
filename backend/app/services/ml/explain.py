"""Human-readable SHAP explanations for the SIH dashboard."""
from pathlib import Path
import logging
import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger("ner_lews.ml.explain")

DEFAULT_MODEL_PATH = Path(__file__).resolve().parent / "models" / "xgb_landslide_v2.pkl"

FRIENDLY = {
    "slope_deg":"High slope angle", "elevation_m":"Elevation", "aspect_deg":"Slope orientation (Aspect)", "ndvi":"Vegetation (NDVI)",
    "rain_1h_mm":"Recent 1-hour rainfall", "rain_6h_mm":"Recent 6-hour rainfall", "rain_12h_mm":"Recent 12-hour rainfall",
    "rain_24h_mm":"24-hour rainfall", "rain_3d_mm":"3-day rainfall", "rain_7d_mm":"7-day rainfall",
    "rain_14d_mm":"14-day rainfall", "rain_30d_mm":"30-day rainfall", "soil_saturation_proxy":"Antecedent soil wetness",
    "curvature":"Terrain curvature", "twi":"Topographic wetness", "distance_to_drainage_m":"Distance to drainage",
    "rain_intensity_ratio":"Recent rainfall intensity", "rain_7d_change_ratio":"Rainfall accumulation", "north_facing":"North-facing slope", "low_vegetation":"Low vegetation", "high_slope":"High-slope flag"
}

class LandslideExplainer:
    def __init__(self, model_path=None):
        self.model_path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
        self.model = None
        self.feature_columns = []
        self.explainer = None
        self._init_explainer()

    def _init_explainer(self):
        if not self.model_path.exists():
            logger.info("Model path %s not found. Explainer disabled.", self.model_path)
            return
        try:
            import shap
            bundle = joblib.load(str(self.model_path))
            self.model = bundle["model"]
            self.feature_columns = bundle.get("feature_columns", [])
            self.explainer = shap.TreeExplainer(self.model)
        except Exception as e:
            logger.warning("Failed to initialize SHAP TreeExplainer: %s", e)
            self.explainer = None

    def explain_row(self, X_row, top_k=5):
        if self.explainer is None:
            return []
        try:
            vals = np.asarray(self.explainer.shap_values(X_row)).reshape(-1)
            out = []
            for feat, val, sv in zip(self.feature_columns, X_row.iloc[0].values, vals):
                if abs(float(sv)) < 1e-6:
                    continue
                increases = float(sv) > 0
                label = FRIENDLY.get(feat, feat.replace('_', ' ').title())
                out.append({
                    "feature": feat,
                    "label": label,
                    "value": round(float(val), 3),
                    "shap_value": round(float(sv), 4),
                    "direction": "increases_risk" if increases else "decreases_risk",
                    "explanation": f"{label} ({float(val):.1f}) is contributing to {'higher' if increases else 'lower'} landslide risk."
                })
            return sorted(out, key=lambda x: abs(x["shap_value"]), reverse=True)[:top_k]
        except Exception as e:
            logger.warning("SHAP explanation failed: %s", e)
            return []
