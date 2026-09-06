"""Human-readable SHAP explanations for the SIH dashboard."""
import joblib, shap, numpy as np, pandas as pd

FRIENDLY = {
    "slope_deg":"High slope angle", "elevation_m":"Elevation", "ndvi":"Vegetation (NDVI)",
    "rain_1h_mm":"Recent 1-hour rainfall", "rain_6h_mm":"Recent 6-hour rainfall", "rain_12h_mm":"Recent 12-hour rainfall",
    "rain_24h_mm":"24-hour rainfall", "rain_3d_mm":"3-day rainfall", "rain_7d_mm":"7-day rainfall",
    "rain_14d_mm":"14-day rainfall", "rain_30d_mm":"30-day rainfall", "soil_saturation_proxy":"Antecedent soil wetness",
    "curvature":"Terrain curvature", "twi":"Topographic wetness", "distance_to_drainage_m":"Distance to drainage",
    "rain_intensity_ratio":"Recent rainfall intensity", "rain_7d_change_ratio":"Rainfall accumulation", "north_facing":"North-facing slope", "low_vegetation":"Low vegetation", "high_slope":"High-slope flag"
}

class LandslideExplainer:
    def __init__(self, model_path="models/xgb_landslide_v2.pkl"):
        bundle=joblib.load(model_path); self.model=bundle["model"]; self.feature_columns=bundle["feature_columns"]; self.explainer=shap.TreeExplainer(self.model)
    def explain_row(self, X_row, top_k=5):
        vals=np.asarray(self.explainer.shap_values(X_row)).reshape(-1); out=[]
        for feat,val,sv in zip(self.feature_columns,X_row.iloc[0].values,vals):
            if abs(float(sv)) < 1e-8: continue
            increases=float(sv)>0
            out.append({"feature":feat,"label":FRIENDLY.get(feat,feat.replace('_',' ').title()),"value":round(float(val),3),"shap_value":round(float(sv),4),"direction":"increases_risk" if increases else "decreases_risk","explanation":f"{FRIENDLY.get(feat,feat.replace('_',' ').title())} is contributing to {'higher' if increases else 'lower'} landslide risk."})
        return sorted(out,key=lambda x:abs(x["shap_value"]),reverse=True)[:top_k]
