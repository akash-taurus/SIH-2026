from fastapi import APIRouter
from typing import Dict, Any, List
from app.database import get_risk_zones
from app.schemas import RiskSummaryItem, PredictRequest, PredictResponse, BatchPredictRequest
from app.services.ml.risk_scorer import LandslideRiskEngine

router = APIRouter(tags=["Risk Zones"])
risk_engine = LandslideRiskEngine()

@router.get("/risk-zones")
async def get_all_risk_zones() -> Dict[str, Any]:
    """
    Returns GeoJSON FeatureCollection of all landslide hazard zones
    with dynamic probability and static slope characteristics.
    """
    return get_risk_zones()

@router.get("/risk-summary", response_model=List[RiskSummaryItem])
async def get_regional_risk_summary():
    """
    Returns aggregated risk counts and percentages across all monitored sectors.
    """
    zones_geojson = get_risk_zones()
    features = zones_geojson.get("features", [])
    
    counts = {"low": 0, "moderate": 0, "high": 0, "severe": 0}
    for f in features:
        level = f.get("properties", {}).get("risk_level", "low").lower()
        if level in counts:
            counts[level] += 1
            
    total = max(len(features), 1)
    
    return [
        {"level": "Low", "count": counts["low"], "percentage": round((counts["low"] / total) * 100), "color": "#EBEBEB"},
        {"level": "Moderate", "count": counts["moderate"], "percentage": round((counts["moderate"] / total) * 100), "color": "#AAAAAA"},
        {"level": "High", "count": counts["high"], "percentage": round((counts["high"] / total) * 100), "color": "#444444"},
        {"level": "Severe", "count": counts["severe"], "percentage": round((counts["severe"] / total) * 100), "color": "#000000"}
    ]

@router.post("/predict-risk", response_model=PredictResponse)
@router.post("/predict", response_model=PredictResponse)
async def predict_landslide_risk(payload: PredictRequest):
    """
    Evaluates terrain and rainfall vectors against the hybrid Physics-Guided AI engine (XGBoost + Geotechnical Physics + SHAP).
    """
    data = payload.model_dump() if hasattr(payload, 'model_dump') else payload.dict()
    result = risk_engine.predict_risk(data, include_shap=True)
    return result

@router.post("/predict-risk/batch")
@router.post("/predict/batch")
async def predict_landslide_risk_batch(payload: BatchPredictRequest):
    """
    Evaluates multiple terrain cells in batch against the hybrid Physics-Guided AI engine.
    """
    results = []
    counts = {"Low": 0, "Moderate": 0, "High": 0, "Severe": 0}
    for cell in payload.cells:
        data = cell.model_dump() if hasattr(cell, 'model_dump') else cell.dict()
        res = risk_engine.predict_risk(data, include_shap=False)
        level = res["risk_level"]
        counts[level] = counts.get(level, 0) + 1
        results.append({
            "lat": cell.lat,
            "lon": cell.lon,
            "risk_score": res["probability"],
            "risk_level": level,
            "factor_of_safety": res["factor_of_safety"],
            "model_version": res.get("model_version", "v2.0")
        })
    return {
        "total_cells": len(results),
        "risk_counts": counts,
        "results": results
    }

@router.get("/risk-zones/evaluated")
async def get_evaluated_risk_zones():
    """
    Returns all risk zones with fresh ML-based risk evaluations and generates alerts.
    Use this instead of /risk-zones when you need current risk predictions.
    """
    from app.services.alert_service import alert_service
    zones_data = get_risk_zones()
    features = zones_data.get("features", [])
    
    async def evaluate_zone(zone):
        props = zone.get("properties", {})
        payload = {
            "slope_deg": props.get("mean_slope_deg", 30.0),
            "rain_1h": props.get("rainfall_1h_mm", 10.0),
            "rain_24h": props.get("rainfall_24h_mm", 50.0),
            "soil_saturation_pct": props.get("soil_saturation_pct", 0.65),
            "storm_duration_hours": 6.0,
            "soil_type": props.get("soil_type", "Clayey Loam on Weathered Quartzite"),
            "dist_to_road_m": props.get("dist_to_road_m", 45.0),
            "elevation_m": props.get("elevation_m", 1400),
            "twi": props.get("twi", 6.8),
            "historical_slide_density": props.get("historical_slide_density", 3.0),
            "api_15_mm": props.get("rainfall_7d_mm", 100.0),
        }
        result = risk_engine.predict_risk(payload)
        zone["properties"]["ml_risk_level"] = result.get("risk_level")
        zone["properties"]["ml_probability"] = result.get("probability")
        zone["properties"]["ml_factor_of_safety"] = result.get("factor_of_safety")
        zone["properties"]["ml_confidence"] = result.get("confidence_score")
        return zone
    
    import asyncio
    evaluated_features = await asyncio.gather(*[evaluate_zone(z) for z in features])
    zones_data["features"] = list(evaluated_features)
    
    alerts = await alert_service.evaluate_all_zones_and_generate_alerts()
    
    return {
        "zones": zones_data,
        "active_alerts": alerts,
        "alerts_count": len(alerts)
    }
