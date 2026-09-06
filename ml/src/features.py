"""Feature engineering for SIH26001 landslide risk prediction."""
import numpy as np
import pandas as pd

BASE_FEATURE_COLUMNS = [
    "slope_deg", "elevation_m", "aspect_deg", "ndvi",
    "rain_1h_mm", "rain_6h_mm", "rain_12h_mm", "rain_24h_mm",
    "rain_3d_mm", "rain_7d_mm", "rain_14d_mm", "rain_30d_mm",
    "soil_saturation_proxy", "curvature", "twi", "distance_to_drainage_m",
]
LEGACY_COLUMNS = ["rain_24h_mm", "rain_3d_mm", "rain_7d_mm", "rain_30d_mm", "soil_saturation_proxy"]
LABEL_COLUMN = "landslide_occurred"


def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Backward-compatible rainfall defaults for the starter/demo dataset.
    if "rain_1h_mm" not in df: df["rain_1h_mm"] = df["rain_24h_mm"] / 24.0
    if "rain_6h_mm" not in df: df["rain_6h_mm"] = df["rain_24h_mm"] / 4.0
    if "rain_12h_mm" not in df: df["rain_12h_mm"] = df["rain_24h_mm"] / 2.0
    if "rain_14d_mm" not in df: df["rain_14d_mm"] = df["rain_7d_mm"] * 1.7
    if "curvature" not in df: df["curvature"] = 0.0
    if "twi" not in df: df["twi"] = 5.0
    if "distance_to_drainage_m" not in df: df["distance_to_drainage_m"] = 500.0

    df["rain_intensity_ratio"] = (df["rain_3d_mm"] + 1e-3) / (df["rain_30d_mm"] / 10 + 1e-3)
    df["rain_7d_change_ratio"] = (df["rain_7d_mm"] + 1e-3) / (df["rain_30d_mm"] / 4 + 1e-3)
    df["north_facing"] = ((df["aspect_deg"] > 315) | (df["aspect_deg"] < 45)).astype(int)
    df["low_vegetation"] = (df["ndvi"] < 0.3).astype(int)
    df["high_slope"] = (df["slope_deg"] >= 30).astype(int)
    return df

ALL_FEATURE_COLUMNS = BASE_FEATURE_COLUMNS + [
    "rain_intensity_ratio", "rain_7d_change_ratio", "north_facing", "low_vegetation", "high_slope"
]


def build_feature_matrix(df: pd.DataFrame):
    df = add_derived_features(df)
    missing = [c for c in BASE_FEATURE_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required features: {missing}")
    X = df[ALL_FEATURE_COLUMNS].astype(float)
    y = df[LABEL_COLUMN] if LABEL_COLUMN in df.columns else None
    return X, y


def spatial_train_test_split(df, test_size=0.2, n_bins=8, seed=42):
    rng = np.random.default_rng(seed)
    df = df.copy()
    df["lat_bin"] = pd.cut(df["lat"], bins=n_bins, labels=False)
    df["lon_bin"] = pd.cut(df["lon"], bins=n_bins, labels=False)
    df["block_id"] = df["lat_bin"].astype(str) + "_" + df["lon_bin"].astype(str)
    blocks = np.array(df["block_id"].unique(), dtype=object)
    rng.shuffle(blocks)
    test_blocks = set(blocks[:max(1, int(len(blocks) * test_size))])
    is_test = df["block_id"].isin(test_blocks)
    return (df[~is_test].drop(columns=["lat_bin", "lon_bin", "block_id"]),
            df[is_test].drop(columns=["lat_bin", "lon_bin", "block_id"]))


def risk_level_from_score(score: float) -> str:
    # Canonical tiers shared with frontend Legend (PLAN 05):
    # Low <30%, Moderate 30-60%, High 60-80%, Severe >80%.
    if score < 0.30: return "Low"
    if score < 0.60: return "Moderate"
    if score < 0.80: return "High"
    return "Severe"
