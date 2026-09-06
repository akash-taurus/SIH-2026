from fastapi import APIRouter, Query
from typing import List, Dict, Any
from app.services.ingestion.weather_poller import fetch_live_meteorology, fetch_all_live_sectors
from app.services.ml.physics import PhysicsSafetyShield
from app.services.ml.risk_scorer import LandslideRiskEngine

router = APIRouter(tags=["Weather"])
risk_engine = LandslideRiskEngine()

@router.get("/weather/live-sectors")
async def get_all_live_sectors() -> List[Dict[str, Any]]:
    """
    Returns live real-time meteorological conditions and coupled physics risk evaluations
    for all 6 active mountain observation sectors across Meghalaya / NER.
    """
    sectors_weather = await fetch_all_live_sectors()
    results = []

    for sector in sectors_weather:
        # Run physics and geotechnical risk inference with live atmospheric data
        risk_eval = risk_engine.predict_risk({
            "slope_deg": sector["mean_slope_deg"],
            "elevation_m": sector["elevation_m"],
            "rain_1h": max(sector["current_rain_mm_h"], 0.0),
            "rain_24h": sector["rain_24h_mm"],
            "rain_7d": sector["rain_24h_mm"] * 2.5,
            "soil_saturation_pct": sector["soil_saturation_pct"],
            "soil_type": sector["soil_type"],
            "dist_to_road_m": 35.0
        })

        results.append({
            **sector,
            "risk_level": risk_eval["risk_level"],
            "probability": risk_eval["probability"],
            "factor_of_safety": risk_eval["factor_of_safety"],
            "failure_mode": risk_eval["failure_mode"],
            "physics_threshold_breached": risk_eval["physics_threshold_breached"]
        })

    return results

@router.get("/weather/forecast")
async def get_weather_forecast(
    lat: float = Query(25.5788, description="Latitude"),
    lon: float = Query(91.8933, description="Longitude")
) -> List[Dict[str, Any]]:
    """
    Returns 72-hour precipitation and soil moisture forecast with Caine safety thresholds.
    """
    raw = await fetch_live_meteorology(lat, lon)
    hourly = raw.get("hourly", {})
    times = hourly.get("time", [])
    precip = hourly.get("precipitation", [])
    soil0 = hourly.get("soil_moisture_0_to_1cm", [])
    soil1 = hourly.get("soil_moisture_1_to_3cm", [])

    results = []
    step = 3
    for i in range(0, len(times), step):
        t_str = times[i]
        r_val = float(precip[i]) if i < len(precip) and precip[i] is not None else 0.0
        
        s0 = float(soil0[i]) if i < len(soil0) and soil0[i] is not None else 0.35
        s1 = float(soil1[i]) if i < len(soil1) and soil1[i] is not None else 0.35
        soil_pct = min(round(((s0 + s1) / 2.0) * 100 * 2.2), 100)

        duration_hours = max(i + 1, 1)
        caine_thresh = PhysicsSafetyShield.calculate_critical_intensity(duration_hours)

        day_num = (i // 24) + 1
        hour_part = t_str.split("T")[-1][:5] if "T" in t_str else f"{i%24:02d}:00"
        time_label = f"Day {day_num} {hour_part}"

        results.append({
            "time": time_label,
            "hourOffset": i,
            "rainfall": round(r_val, 1),
            "soilMoisture": soil_pct,
            "caineThreshold": caine_thresh,
            "isBreach": (r_val >= caine_thresh or r_val >= 35.0)
        })

    return results
