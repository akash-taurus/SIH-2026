"""Prediction, batch scoring and dynamic GeoJSON generation."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import joblib
import pandas as pd
from features import build_feature_matrix, risk_level_from_score

# Canonical tiers shared with frontend MapView/Legend (PLAN 05):
# Low / Moderate / High / Severe. Older bundles may carry
# medium/critical thresholds — normalized on load (see __init__).
CANONICAL_THRESHOLDS = {"moderate": .30, "high": .60, "severe": .80}

def _normalize_thresholds(stored):
    if not isinstance(stored, dict):
        return dict(CANONICAL_THRESHOLDS)
    out = dict(CANONICAL_THRESHOLDS)
    if "medium" in stored and "moderate" not in stored:
        out["moderate"] = stored["medium"]
    if "critical" in stored and "severe" not in stored:
        out["severe"] = stored["critical"]
    for k in ("moderate", "high", "severe"):
        if k in stored:
            out[k] = stored[k]
    return out


def _normalize_level(level):
    mapping = {"medium": "Moderate", "critical": "Severe",
               "moderate": "Moderate", "severe": "Severe",
               "low": "Low", "high": "High",
               "Low": "Low", "Medium": "Moderate", "High": "High",
               "Critical": "Severe", "Moderate": "Moderate", "Severe": "Severe"}
    return mapping.get(level, level)

class LandslidePredictor:
    def __init__(self, model_path="models/xgb_landslide_v2.pkl"):
        bundle = joblib.load(model_path)
        self.model = bundle["model"]
        self.feature_columns = bundle["feature_columns"]
        self.model_version = bundle.get("model_version", "v2.0")
        self.thresholds = _normalize_thresholds(bundle.get("thresholds"))
        self.calibrator = bundle.get("calibrator")

    def _probability(self, X):
        raw = self.model.predict_proba(X)[:, 1]
        return self.calibrator.predict_proba(raw.reshape(-1, 1))[:, 1] if self.calibrator else raw

    def predict_row(self, row):
        X, _ = build_feature_matrix(pd.DataFrame([row]))
        score = float(self._probability(X)[0])
        return {"risk_score": round(score, 4), "risk_level": _normalize_level(risk_level_from_score(score)), "model_version": self.model_version}

    def predict_batch(self, df):
        X, _ = build_feature_matrix(df)
        scores = self._probability(X)
        out = df.copy()
        out["risk_score"] = scores
        out["risk_level"] = [_normalize_level(risk_level_from_score(s)) for s in scores]
        out["model_version"] = self.model_version
        return out


def to_geojson(scored):
    features = []
    for _, row in scored.iterrows():
        features.append({"type":"Feature", "geometry":{"type":"Point","coordinates":[float(row["lon"]),float(row["lat"])]},
            "properties":{"cell_id":row.get("cell_id"),"risk_score":round(float(row["risk_score"]),4),"risk_level":_normalize_level(row["risk_level"]),"model_version":row["model_version"]}})
    return {"type":"FeatureCollection","features":features}


def to_frontend_zones(scored, half_deg=0.02):
    """Convert scored grid cells to frontend-compatible Polygon zones.

    Frontend MapView expects GeoJSON Polygons with properties:
    zone_id, name, district, risk_level (low/moderate/high/severe),
    probability, mean_slope_deg, rainfall_24h_mm.
    Each grid cell becomes a small square polygon so live mode works
    without the static mock file.
    """
    features = []
    for _, row in scored.iterrows():
        lon, lat = float(row["lon"]), float(row["lat"])
        level = str(_normalize_level(row.get("risk_level", "Low"))).lower()
        ring = [[lon - half_deg, lat - half_deg], [lon + half_deg, lat - half_deg],
                [lon + half_deg, lat + half_deg], [lon - half_deg, lat + half_deg],
                [lon - half_deg, lat - half_deg]]
        features.append({"type": "Feature",
            "properties": {
                "zone_id": str(row.get("cell_id", f"Z-{lat:.2f}-{lon:.2f}")),
                "name": str(row.get("cell_id", f"Cell {lat:.2f}, {lon:.2f}")),
                "district": "Live ML grid",
                "risk_level": level,
                "probability": round(float(row["risk_score"]), 4),
                "mean_slope_deg": round(float(row.get("slope_deg", 0.0)), 1),
                "rainfall_24h_mm": round(float(row.get("rain_24h_mm", 0.0)), 1),
            },
            "geometry": {"type": "Polygon", "coordinates": [ring]}})
    return {"type": "FeatureCollection", "features": features}


def risk_summary_from_scores(scored):
    """Aggregate scored cells into frontend riskSummary.json shape."""
    levels = [str(_normalize_level(v)).lower() for v in scored["risk_level"].tolist()]
    total = max(len(levels), 1)
    colors = {"low": "#EBEBEB", "moderate": "#AAAAAA", "high": "#444444", "severe": "#000000"}
    out = []
    for key, label in (("low", "Low"), ("moderate", "Moderate"), ("high", "High"), ("severe", "Severe")):
        count = sum(1 for lv in levels if lv == key)
        out.append({"level": label, "count": count,
                    "percentage": round(count / total * 100), "color": colors[key]})
    return out


def precompute_heatmap(data_path="data/raw/synthetic_grid_dataset.csv", model_path="models/xgb_landslide_v2.pkl", out_path="data/processed/risk_heatmap.geojson"):
    predictor = LandslidePredictor(model_path)
    scored = predictor.predict_batch(pd.read_csv(data_path))
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(to_geojson(scored)))
    print(f"Wrote {len(scored)} features to {Path(out_path).resolve()}")

if __name__ == "__main__": precompute_heatmap()
