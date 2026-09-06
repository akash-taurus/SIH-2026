"""SIH26001 production-oriented FastAPI service: prediction, batch, risk map and alerts."""
import sys, json, logging
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"src"))
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pandas as pd
from predict import LandslidePredictor, to_geojson, to_frontend_zones, risk_summary_from_scores
from explain import LandslideExplainer
from features import build_feature_matrix, add_derived_features
from db import init_db, save_prediction, save_alert

logging.basicConfig(level=logging.INFO); log=logging.getLogger("sih26001")
ROOT=Path(__file__).resolve().parent.parent; MODEL_PATH=str(ROOT/"models"/"xgb_landslide_v2.pkl")
DATA_PATH=ROOT/"data/raw/synthetic_grid_dataset.csv"
app=FastAPI(title="SIH26001 Landslide Risk API",version="2.0.0",description="Explainable landslide risk prediction, batch scoring, GeoJSON and alerts.")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
predictor=None; explainer=None; DB_ENABLED=False

class PredictRequest(BaseModel):
    lat:float; lon:float; slope_deg:float=Field(...,ge=0,le=90); elevation_m:float=Field(...,ge=-500); aspect_deg:float=Field(...,ge=0,le=360); ndvi:float=Field(...,ge=-1,le=1)
    # Sub-daily rain fields default to None (not 0) so "not provided" is distinguishable from
    # "confirmed zero". None values are dropped before feature-building so features.py can derive
    # sensible estimates from rain_24h_mm/rain_7d_mm instead of silently assuming no recent rain.
    rain_1h_mm:float|None=None; rain_6h_mm:float|None=None; rain_12h_mm:float|None=None
    rain_24h_mm:float; rain_3d_mm:float; rain_7d_mm:float; rain_14d_mm:float|None=None; rain_30d_mm:float
    soil_saturation_proxy:float; curvature:float=0; twi:float=5; distance_to_drainage_m:float=500
class BatchRequest(BaseModel): cells:list[PredictRequest]
class Factor(BaseModel): feature:str; label:str; value:float; shap_value:float; direction:str; explanation:str
class PredictResponse(BaseModel): lat:float; lon:float; risk_score:float; risk_level:str; model_version:str; confidence:float; top_contributing_factors:list[Factor]

@app.on_event("startup")
def load():
 global predictor,explainer,DB_ENABLED
 if not Path(MODEL_PATH).exists(): raise RuntimeError("Model missing. Run: python src/train.py")
 predictor=LandslidePredictor(MODEL_PATH); explainer=LandslideExplainer(MODEL_PATH); DB_ENABLED=init_db(); log.info("Loaded model %s; database=%s",predictor.model_version,DB_ENABLED)
@app.get("/")
def root(): return {"status":"ok","service":"SIH26001","version":"2.0.0"}
@app.get("/health")
def health(): return {"model_loaded":predictor is not None,"model_version":getattr(predictor,"model_version",None)}

def _prepare_rows(cells):
 """Turn request cells into row dicts, deriving sub-daily rainfall fallbacks per-row
 BEFORE any batching. This must happen per-row (not on the assembled DataFrame) because
 different cells in the same batch can be missing different fields; assembling first and
 deriving after would leave real NaNs where a fallback should have been computed."""
 rows=[]
 for c in cells:
  raw=c.model_dump(exclude_none=True) if hasattr(c,"model_dump") else c.dict(exclude_none=True)
  feats={k:v for k,v in raw.items() if k not in ('lat','lon')}
  derived=add_derived_features(pd.DataFrame([feats])).iloc[0].to_dict()
  rows.append({**raw,**derived})
 return rows

def single(req):
 row=_prepare_rows([req])[0]; feats={k:v for k,v in row.items() if k not in ('lat','lon')}
 X,_=build_feature_matrix(pd.DataFrame([feats]))
 result=predictor.predict_row(feats); factors=explainer.explain_row(X[explainer.feature_columns].iloc[[0]],top_k=5)
 score=result['risk_score']; return {**result,"lat":req.lat,"lon":req.lon,"confidence":round(max(score,1-score),4),"top_contributing_factors":factors}
@app.post("/predict",response_model=PredictResponse)
def predict(req:PredictRequest):
 if predictor is None: raise HTTPException(503,"Model not loaded")
 result=single(req)
 if DB_ENABLED: save_prediction({"lat":result["lat"],"lon":result["lon"],"score":result["risk_score"],"level":result["risk_level"],"version":result["model_version"]})
 return result
@app.post("/predict/batch")
def batch(req:BatchRequest):
 if predictor is None: raise HTTPException(503,"Model not loaded")
 rows=_prepare_rows(req.cells); raw=pd.DataFrame([{k:v for k,v in r.items() if k not in ('lat','lon')} for r in rows]); scored=predictor.predict_batch(raw); counts=scored.risk_level.value_counts().to_dict()
 results=[]
 for r,s in zip(rows,scored.to_dict('records')): results.append({"lat":r['lat'],"lon":r['lon'],"risk_score":round(float(s['risk_score']),4),"risk_level":s['risk_level'],"model_version":s['model_version']})
 return {"total_cells":len(results),"risk_counts":counts,"results":results}
@app.get("/risk-map")
def risk_map():
 if predictor is None: raise HTTPException(503,"Model not loaded")
 if not DATA_PATH.exists(): raise HTTPException(404,"No grid dataset configured")
 return to_geojson(predictor.predict_batch(pd.read_csv(DATA_PATH)))
@app.post("/alerts/evaluate")
def alerts(req:BatchRequest):
 if predictor is None: raise HTTPException(503,"Model not loaded")
 rows=_prepare_rows(req.cells)
 scored=predictor.predict_batch(pd.DataFrame([{k:v for k,v in r.items() if k not in ('lat','lon')} for r in rows]))
 alerts=[]
 for r,s in zip(rows,scored.to_dict('records')):
  if s['risk_level'] in ('High','Severe'): alert={"lat":r['lat'],"lon":r['lon'],"risk_score":round(float(s['risk_score']),4),"risk_level":s['risk_level'],"severity":"EMERGENCY" if s['risk_level']=='Severe' else 'WARNING',"message":f"{s['risk_level']} landslide risk detected. Monitor and activate local response protocol."}; alerts.append(alert); save_alert({"lat":alert["lat"],"lon":alert["lon"],"score":alert["risk_score"],"level":alert["risk_level"],"severity":alert["severity"],"message":alert["message"]}) if DB_ENABLED else None
 return {"alert_count":len(alerts),"alerts":alerts}

def _scored_grid(limit: int = 500):
  if predictor is None: raise HTTPException(503,"Model not loaded")
  if not DATA_PATH.exists(): raise HTTPException(404,"No grid dataset configured")
  df = pd.read_csv(DATA_PATH)
  if limit and len(df) > limit:
    df = df.head(limit)
  return predictor.predict_batch(df)

# --- Frontend live-mode compat (PLAN 06): frontend calls /api/v1/* ---
@app.get("/risk-zones")
@app.get("/api/v1/risk-zones")
def risk_zones(limit: int = Query(500, ge=1, le=4000)):
  return to_frontend_zones(_scored_grid(limit))

@app.get("/risk-summary")
@app.get("/api/v1/risk-summary")
def risk_summary(limit: int = Query(4000, ge=1, le=4000)):
  return risk_summary_from_scores(_scored_grid(limit))

@app.get("/roads")
@app.get("/api/v1/roads")
def roads():
  # Placeholder until roads DB is owned by backend; shape matches frontend mockData/roads.json.
  return [{"road_id": "NH-40", "name": "Jorabat – Shillong Expressway (GS Road)", "status": "blocked", "blockage_reason": "See live risk-zones overlay", "last_updated": "live"},
          {"road_id": "NH-6", "name": "Shillong – Jowai – Silchar", "status": "at_risk", "blockage_reason": "See live risk-zones overlay", "last_updated": "live"},
          {"road_id": "SH-5", "name": "Cherrapunji – Shella Border Highway", "status": "open", "blockage_reason": None, "last_updated": "live"}]

@app.get("/emergency-prioritization")
@app.get("/api/v1/emergency-prioritization")
def emergency_prioritization():
  return []

@app.get("/reports")
@app.get("/api/v1/reports")
def list_reports():
  return []

@app.get("/weather/forecast")
@app.get("/api/v1/weather/forecast")
def weather_forecast(lat: float = 25.5788, lon: float = 91.8933):
  # Thin live proxy to Open-Meteo so REACT_APP_USE_MOCK=false works without
  # exposing the third-party URL to every client. Frontend still has its own
  # direct fetch + fallback; this is the backend-owned equivalent.
  import urllib.request, json as _json
  url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
         "&hourly=precipitation&forecast_days=3&timezone=Asia%2FKolkata")
  try:
    with urllib.request.urlopen(url, timeout=10) as resp:
      return {"source": "open-meteo", "lat": lat, "lon": lon, "payload": _json.loads(resp.read().decode())}
  except Exception as exc:
    raise HTTPException(502, f"Open-Meteo upstream failed: {exc}")
