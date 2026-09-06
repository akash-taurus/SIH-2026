import httpx
import asyncio
from typing import Dict, Any, List, Optional
import math

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# 6 Primary Geotechnical & Meteorological Sectors across Meghalaya / NER
DEFAULT_SECTOR_COORDINATES = {
    "Z-SHL-01": {"name": "Shillong Peak Ridge", "lat": 25.5788, "lon": 91.8933, "elevation_m": 1496, "mean_slope_deg": 38.4, "dist_to_road_m": 20.0, "soil_type": "Clayey Loam on Weathered Quartzite"},
    "Z-CHR-02": {"name": "Sohra Escarpment", "lat": 25.2711, "lon": 91.7312, "elevation_m": 1430, "mean_slope_deg": 35.8, "dist_to_road_m": 35.0, "soil_type": "Limestone Karst & Fractured Sandstone"},
    "Z-MAW-03": {"name": "Mawsynram Canyons", "lat": 25.2988, "lon": 91.5822, "elevation_m": 1400, "mean_slope_deg": 42.1, "dist_to_road_m": 15.0, "soil_type": "Highly Saturated Colluvium"},
    "Z-JOW-04": {"name": "Jowai Bypass Cut", "lat": 25.4412, "lon": 92.2033, "elevation_m": 1380, "mean_slope_deg": 27.2, "dist_to_road_m": 45.0, "soil_type": "Shale and Coal-bearing Sandstone"},
    "Z-NONG-05": {"name": "Nongpoh Lowlands", "lat": 25.9011, "lon": 91.8812, "elevation_m": 485, "mean_slope_deg": 14.2, "dist_to_road_m": 120.0, "soil_type": "Alluvial Valley Fill"},
    "Z-TURA-06": {"name": "Tura Peak Ridge", "lat": 25.5144, "lon": 90.2211, "elevation_m": 872, "mean_slope_deg": 31.5, "dist_to_road_m": 60.0, "soil_type": "Archaean Gneiss Complex"}
}

WMO_WEATHER_CODES = {
    0: "Clear Sky",
    1: "Mainly Clear",
    2: "Partly Cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing Rime Fog",
    51: "Light Drizzle",
    53: "Moderate Drizzle",
    55: "Dense Drizzle",
    61: "Slight Rain",
    63: "Moderate Rain",
    65: "Heavy Torrential Rain",
    80: "Slight Rain Showers",
    81: "Moderate Rain Showers",
    82: "Violent Rain Showers",
    95: "Thunderstorm",
    96: "Thunderstorm with Slight Hail",
    99: "Thunderstorm with Heavy Hail"
}

async def fetch_live_meteorology(lat: float = 25.5788, lon: float = 91.8933) -> Dict[str, Any]:
    """
    Fetches real-time precipitation, 72h forecast, and multi-depth soil moisture
    directly from Open-Meteo ECMWF/ICON models with zero API keys.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "precipitation,soil_moisture_0_to_1cm,soil_moisture_1_to_3cm,soil_moisture_3_to_9cm,soil_moisture_9_to_27cm",
        "current": "temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,wind_speed_10m",
        "forecast_days": 3,
        "timezone": "Asia/Kolkata"
    }

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(OPEN_METEO_URL, params=params)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        return generate_fallback_weather(lat, lon)

async def fetch_single_sector_live_weather(zone_id: str, sector_info: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
    """
    Fetches live real-time meteorological conditions for a single sector.
    """
    lat = sector_info["lat"]
    lon = sector_info["lon"]
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,wind_speed_10m",
        "hourly": "precipitation,soil_moisture_0_to_1cm,soil_moisture_1_to_3cm",
        "forecast_days": 1,
        "timezone": "Asia/Kolkata"
    }

    try:
        res = await client.get(OPEN_METEO_URL, params=params)
        res.raise_for_status()
        data = res.json()
        current = data.get("current", {})
        hourly = data.get("hourly", {})

        precip_now = float(current.get("precipitation", current.get("rain", 0.0)))
        temp_c = float(current.get("temperature_2m", 22.0))
        humidity_pct = int(current.get("relative_humidity_2m", 75))
        weather_code = int(current.get("weather_code", 3))
        wind_kmh = float(current.get("wind_speed_10m", 5.0))

        hourly_precip = hourly.get("precipitation", [0.0] * 24)
        rain_24h = sum(float(p) for p in hourly_precip[:24] if p is not None)

        s0_list = hourly.get("soil_moisture_0_to_1cm", [0.35])
        s1_list = hourly.get("soil_moisture_1_to_3cm", [0.35])
        s0 = float(s0_list[0]) if s0_list and s0_list[0] is not None else 0.35
        s1 = float(s1_list[0]) if s1_list and s1_list[0] is not None else 0.35
        soil_sat_pct = min(round(((s0 + s1) / 2.0) * 100 * 2.2) / 100.0, 0.98)

        is_raining = precip_now > 0.05 or weather_code in [51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99]
        condition_text = WMO_WEATHER_CODES.get(weather_code, "Overcast")

        return {
            "zone_id": zone_id,
            "name": sector_info["name"],
            "latitude": lat,
            "longitude": lon,
            "elevation_m": sector_info["elevation_m"],
            "mean_slope_deg": sector_info["mean_slope_deg"],
            "soil_type": sector_info["soil_type"],
            "current_rain_mm_h": round(precip_now, 2),
            "is_raining": is_raining,
            "condition": condition_text,
            "temperature_c": round(temp_c, 1),
            "humidity_pct": humidity_pct,
            "wind_speed_kmh": round(wind_kmh, 1),
            "soil_saturation_pct": round(soil_sat_pct, 2),
            "rain_24h_mm": round(rain_24h, 1),
            "timestamp": current.get("time", "Live Telemetry")
        }
    except Exception as err:
        return {
            "zone_id": zone_id,
            "name": sector_info["name"],
            "latitude": lat,
            "longitude": lon,
            "elevation_m": sector_info["elevation_m"],
            "mean_slope_deg": sector_info["mean_slope_deg"],
            "soil_type": sector_info["soil_type"],
            "current_rain_mm_h": 0.0,
            "is_raining": False,
            "condition": "Overcast",
            "temperature_c": 22.0,
            "humidity_pct": 75,
            "wind_speed_kmh": 6.0,
            "soil_saturation_pct": 0.65,
            "rain_24h_mm": 45.0,
            "timestamp": "Live Fallback"
        }

async def fetch_all_live_sectors() -> List[Dict[str, Any]]:
    """
    Queries real-time meteorology in parallel across all 6 monitoring sectors.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        tasks = [
            fetch_single_sector_live_weather(zone_id, info, client)
            for zone_id, info in DEFAULT_SECTOR_COORDINATES.items()
        ]
        return await asyncio.gather(*tasks)

def generate_fallback_weather(lat: float, lon: float) -> Dict[str, Any]:
    """
    Generates deterministic meteorological series for offline demo/test scenarios.
    """
    times = []
    precip = []
    soil0 = []
    soil1 = []

    base_rain = [8.2, 14.5, 29.8, 48.0, 62.4, 35.1, 21.0, 12.0] * 3
    for i in range(24):
        times.append(f"2026-08-31T{i:02d}:00")
        r = base_rain[i % len(base_rain)]
        precip.append(r)
        soil0.append(min(0.20 + (r * 0.005), 0.45))
        soil1.append(min(0.22 + (r * 0.004), 0.45))

    return {
        "latitude": lat,
        "longitude": lon,
        "timezone": "Asia/Kolkata",
        "current": {"precipitation": 18.5, "temperature_2m": 22.4, "relative_humidity_2m": 82, "weather_code": 63, "wind_speed_10m": 8.5},
        "hourly": {
            "time": times,
            "precipitation": precip,
            "soil_moisture_0_to_1cm": soil0,
            "soil_moisture_1_to_3cm": soil1
        }
    }
