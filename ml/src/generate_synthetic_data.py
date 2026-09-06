"""
generate_synthetic_data.py

Hackathon fallback data generator (per SIH26001 role plan, Section 2 & 9).

Produces a synthetic grid-cell dataset for a demo NER region (default: mimics
Mizoram/Meghalaya terrain) with physics-informed correlations:
  - higher slope + high cumulative rainfall + low NDVI -> higher landslide probability
  - soil saturation proxy built from antecedent rainfall

Swap this out for real NASA GLC + SRTM DEM + IMD rainfall when available.
Output: data/raw/synthetic_grid_dataset.csv
"""

import numpy as np
import pandas as pd
from pathlib import Path

RNG = np.random.default_rng(42)

# Demo region bounding box (rough Mizoram/Meghalaya area) — swap for your real AOI
LAT_MIN, LAT_MAX = 23.0, 25.5
LON_MIN, LON_MAX = 91.0, 93.5

N_CELLS = 4000          # grid cells (spatial samples)
N_DAYS = 60              # days of history per cell (for rainfall accumulation)


def make_grid(n_cells: int) -> pd.DataFrame:
    lats = RNG.uniform(LAT_MIN, LAT_MAX, n_cells)
    lons = RNG.uniform(LON_MIN, LON_MAX, n_cells)
    cell_id = [f"cell_{i:05d}" for i in range(n_cells)]

    # Terrain: slope (deg), elevation (m), aspect (deg), NDVI (-1 to 1)
    slope = np.clip(RNG.gamma(shape=3.0, scale=8.0, size=n_cells), 0, 70)  # skewed, mostly moderate
    elevation = RNG.uniform(50, 2200, n_cells)
    aspect = RNG.uniform(0, 360, n_cells)
    ndvi = np.clip(RNG.normal(0.55, 0.2, n_cells), -0.1, 0.95)

    df = pd.DataFrame({
        "cell_id": cell_id,
        "lat": lats,
        "lon": lons,
        "slope_deg": slope,
        "elevation_m": elevation,
        "aspect_deg": aspect,
        "ndvi": ndvi,
    })
    return df


def simulate_rainfall_series(n_cells: int, n_days: int) -> np.ndarray:
    """Daily rainfall (mm) per cell over n_days, monsoon-like with occasional bursts."""
    base = RNG.gamma(shape=1.2, scale=8.0, size=(n_cells, n_days))
    # inject storm bursts on random days for random subset of cells
    burst_mask = RNG.random((n_cells, n_days)) < 0.06
    base[burst_mask] += RNG.uniform(40, 120, size=base[burst_mask].shape)
    return base  # mm/day


def compute_rainfall_features(rain: np.ndarray) -> pd.DataFrame:
    """From a (n_cells, n_days) rainfall matrix, compute cumulative + antecedent features
    using the most recent day as 'today'."""
    r24 = rain[:, -1]
    r3d = rain[:, -3:].sum(axis=1)
    r7d = rain[:, -7:].sum(axis=1)
    r30d = rain[:, -30:].sum(axis=1)

    # Antecedent Precipitation Index (API) — exponentially decayed sum, common
    # soil-moisture proxy when no sensor data is available (decay k=0.9)
    k = 0.9
    weights = k ** np.arange(rain.shape[1])[::-1]
    api = (rain * weights).sum(axis=1) / weights.sum()

    return pd.DataFrame({
        "rain_24h_mm": r24,
        "rain_3d_mm": r3d,
        "rain_7d_mm": r7d,
        "rain_30d_mm": r30d,
        "soil_saturation_proxy": api,  # antecedent precipitation index
    })


def label_landslide(df: pd.DataFrame) -> np.ndarray:
    """Physics-informed synthetic label: logistic function of slope, rainfall,
    soil saturation, and vegetation loss (low NDVI). Landslides are RARE by design
    (class imbalance), matching real-world base rates.
    """
    z = (
        -8.5
        + 0.055 * df["slope_deg"]
        + 0.010 * df["rain_7d_mm"]
        + 0.004 * df["soil_saturation_proxy"]
        + 1.8 * (1 - df["ndvi"])          # low NDVI (deforested) raises risk
        + 0.0009 * df["elevation_m"]
        + RNG.normal(0, 0.6, len(df))      # noise
    )
    prob = 1 / (1 + np.exp(-z))
    label = (RNG.random(len(df)) < prob).astype(int)
    return label, prob


def main(out_path: str = "data/raw/synthetic_grid_dataset.csv"):
    terrain = make_grid(N_CELLS)
    rain_matrix = simulate_rainfall_series(N_CELLS, N_DAYS)
    rain_feats = compute_rainfall_features(rain_matrix)

    df = pd.concat([terrain, rain_feats], axis=1)
    df["landslide_occurred"], df["_true_prob"] = label_landslide(df)

    print(f"Generated {len(df)} grid cells")
    print(f"Positive rate (landslide_occurred=1): {df['landslide_occurred'].mean():.3%}")

    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    df.drop(columns=["_true_prob"]).to_csv(out_file, index=False)
    print(f"Saved to {out_file.resolve()}")


if __name__ == "__main__":
    main()
