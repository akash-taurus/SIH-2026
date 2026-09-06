# SIH26001 — Landslide Risk ML/Backend V2

Competition-ready starter architecture for the AI/ML + backend role:
**data contract → feature engineering → model comparison → calibrated risk → SHAP explanations → batch prediction → dynamic GeoJSON → alert engine → optional PostgreSQL → Docker**.

## Run locally

```bash
python -m venv venv
# Windows
venv\Scripts\activate
pip install -r requirements.txt

# Demo only: creates synthetic data. Do NOT present its metrics as real-world accuracy.
python src/generate_synthetic_data.py
python src/train.py
python src/predict.py
uvicorn api.main:app --reload --port 8000
```

Swagger: `http://127.0.0.1:8000/docs`

## Main endpoints

- `POST /predict` — single-cell risk + calibrated score + human-readable SHAP factors
- `POST /predict/batch` — score many cells for a dashboard/map
- `GET /risk-map` — dynamically generated GeoJSON from the configured grid
- `POST /alerts/evaluate` — High/Critical risk alert generation
- `GET /health` — service/model health

## Model V2 changes

1. Expanded rainfall windows: 1h/6h/12h/24h/3d/7d/14d/30d.
2. Terrain features: curvature, TWI and distance to drainage.
3. Derived rainfall/vegetation/slope features.
4. Spatial train/test split to reduce geographic leakage.
5. XGBoost vs Random Forest comparison using ROC-AUC and PR-AUC.
6. Probability calibration using a sigmoid calibration layer.
7. Versioned model bundle: `models/xgb_landslide_v2.pkl`.
8. Human-readable SHAP explanations.
9. Batch inference and GeoJSON output.
10. Alert engine for High/Critical risk.
11. Optional PostgreSQL persistence for predictions and alerts.
12. Docker + docker-compose deployment.
13. Structured logging and health endpoint.

## Real-data strategy

Use `data/README.md` as the data contract. The final SIH model should be trained/evaluated on a documented historical landslide inventory joined with terrain, satellite/vegetation and rainfall observations by location and date. Keep a separate temporal holdout for final validation. Synthetic data exists only to prove the software pipeline.

## PostgreSQL + Docker

```bash
docker compose up --build
```

This starts the API and PostgreSQL. The API automatically creates `risk_predictions` and `risk_alerts` tables when `DATABASE_URL` is present.

## Unified Production Architecture

For the active NER-LEWS application, runtime ML inference and SHAP explainability are consolidated into the core backend at [`backend/app/services/ml/`](file:///Z:/CodeBase/SIH/backend/app/services/ml):
- **Model Training & Evaluation:** Run `python src/train.py` in `ml/` to train XGBoost models and export to `backend/app/services/ml/models/xgb_landslide_v2.pkl`.
- **Hybrid Inference:** The core backend (`backend/app/main.py`) serves live predictions at `/api/v1/predict-risk` and `/api/v1/predict/batch`, coupling XGBoost probabilities with the Limit-Equilibrium Slope Stability physics engine (`PhysicsSafetyShield`).

## Remaining optional integrations

SMS/email, mobile UI, and advanced deep-learning models are intentionally left as integration layers. Add them only after the real-data baseline is stable; a well-validated gradient-boosting model is preferable to a deep model without sufficient labeled landslide data.
