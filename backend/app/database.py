"""
Database & In-Memory Spatial Repository for Zero-Dependency Local Execution.
Contains accurate geographic seed data for North-East India landslide zones.
"""
from typing import Dict, List, Any, Optional
import datetime

# Seed GeoJSON FeatureCollection of Landslide Hazard Zones
SEED_RISK_ZONES: Dict[str, Any] = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "zone_id": "Z-SHL-01",
                "name": "Shillong East Ridge & Upper Shillong",
                "district": "East Khasi Hills",
                "elevation_m": 1496,
                "risk_level": "severe",
                "probability": 0.88,
                "mean_slope_deg": 38.4,
                "rainfall_24h_mm": 142.5,
                "critical_infrastructure": "NH-40 Expressway, NEIGRIHMS Link",
                "soil_type": "Clayey Loam on Weathered Quartzite"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [91.865, 25.545],
                        [91.925, 25.548],
                        [91.938, 25.595],
                        [91.882, 25.602],
                        [91.865, 25.545]
                    ]
                ]
            }
        },
        {
            "type": "Feature",
            "properties": {
                "zone_id": "Z-CHR-02",
                "name": "Sohra (Cherrapunji) Plateau Escarpment",
                "district": "East Khasi Hills",
                "elevation_m": 1430,
                "risk_level": "high",
                "probability": 0.76,
                "mean_slope_deg": 35.8,
                "rainfall_24h_mm": 210.0,
                "critical_infrastructure": "SH-5 Sohra-Shella Border Route",
                "soil_type": "Limestone Karst & Fractured Sandstone"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [91.685, 25.245],
                        [91.758, 25.252],
                        [91.765, 25.315],
                        [91.678, 25.302],
                        [91.685, 25.245]
                    ]
                ]
            }
        },
        {
            "type": "Feature",
            "properties": {
                "zone_id": "Z-MAW-03",
                "name": "Mawsynram Valley Deep Canyons",
                "district": "East Khasi Hills",
                "elevation_m": 1400,
                "risk_level": "severe",
                "probability": 0.93,
                "mean_slope_deg": 42.1,
                "rainfall_24h_mm": 265.0,
                "critical_infrastructure": "Mawsynram-Balat Link Road",
                "soil_type": "Highly Saturated Colluvium"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [91.545, 25.265],
                        [91.622, 25.272],
                        [91.635, 25.335],
                        [91.538, 25.328],
                        [91.545, 25.265]
                    ]
                ]
            }
        },
        {
            "type": "Feature",
            "properties": {
                "zone_id": "Z-JOW-04",
                "name": "Jowai Cut-Slope Bypass Corridor",
                "district": "West Jaintia Hills",
                "elevation_m": 1380,
                "risk_level": "moderate",
                "probability": 0.54,
                "mean_slope_deg": 27.2,
                "rainfall_24h_mm": 88.0,
                "critical_infrastructure": "NH-6 National Highway",
                "soil_type": "Shale and Coal-bearing Sandstone"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [92.165, 25.405],
                        [92.245, 25.412],
                        [92.258, 25.475],
                        [92.158, 25.468],
                        [92.165, 25.405]
                    ]
                ]
            }
        },
        {
            "type": "Feature",
            "properties": {
                "zone_id": "Z-NONG-05",
                "name": "Nongpoh Lowland Corridor",
                "district": "Ri-Bhoi",
                "elevation_m": 485,
                "risk_level": "low",
                "probability": 0.19,
                "mean_slope_deg": 14.2,
                "rainfall_24h_mm": 42.0,
                "critical_infrastructure": "GS Road Highway Sector",
                "soil_type": "Alluvial Valley Fill"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [91.835, 25.865],
                        [91.925, 25.872],
                        [91.938, 25.935],
                        [91.828, 25.928],
                        [91.835, 25.865]
                    ]
                ]
            }
        },
        {
            "type": "Feature",
            "properties": {
                "zone_id": "Z-TURA-06",
                "name": "Tura Peak Forest Slope",
                "district": "West Garo Hills",
                "elevation_m": 872,
                "risk_level": "moderate",
                "probability": 0.48,
                "mean_slope_deg": 31.5,
                "rainfall_24h_mm": 95.0,
                "critical_infrastructure": "NH-217 Tura-Dalu Route",
                "soil_type": "Archaean Gneiss Complex"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [90.185, 25.485],
                        [90.255, 25.492],
                        [90.268, 25.555],
                        [90.178, 25.548],
                        [90.185, 25.485]
                    ]
                ]
            }
        }
    ]
}

# Critical Road Highway Network
SEED_ROADS: List[Dict[str, Any]] = [
    {
        "road_id": "NH-6",
        "name": "Jorabat – Shillong Expressway (GS Road)",
        "status": "blocked",
        "blockage_reason": "Mudslide & slope collapse near Umiam dam road-widening zone due to unscientific hill-cutting (Km 58-64, Ri-Bhoi District)",
        "last_updated": "8 mins ago",
        "affected_zone": "Z-SHL-01",
        "traffic_diversion": "Diverted via Umroi–Byrnihat alternate link"
    },
    {
        "road_id": "NH-6",
        "name": "Shillong – Jowai – Silchar (old NH-44 extension)",
        "status": "at_risk",
        "blockage_reason": "Road cave-in & debris accumulation in East Jaintia Hills stretch (Jowai–Ratacherra section)",
        "last_updated": "22 mins ago",
        "affected_zone": "Z-JOW-04",
        "traffic_diversion": "Heavy vehicles restricted to single lane; light vehicles proceed with caution"
    },
    {
        "road_id": "SH-5",
        "name": "Sohra (Cherrapunji) – Shella Border Road",
        "status": "at_risk",
        "blockage_reason": "Intermittent rockfalls & boulder drops on descent to Shella due to saturated limestone karst escarpment",
        "last_updated": "45 mins ago",
        "affected_zone": "Z-CHR-02",
        "traffic_diversion": "Proceed with caution; night travel not advised"
    },
    {
        "road_id": "NH-106",
        "name": "Shillong – Mairang – Nongstoin Highway",
        "status": "at_risk",
        "blockage_reason": "Slope instability & minor debris fall near Mairang–Nongstoin section due to road-widening excavation",
        "last_updated": "1 hour ago",
        "affected_zone": "Z-MAW-03",
        "traffic_diversion": "Speed restriction 20 km/h at Km 32-38; avoid during heavy rain"
    },
    {
        "road_id": "NH-40",
        "name": "Shillong – Pynursla – Dawki Border Highway",
        "status": "blocked",
        "blockage_reason": "Major landslide at Laitlyngkot–Lyngkyrdem (Km 24-37); road restoration ongoing, night closure 10 PM – 5 AM",
        "last_updated": "35 mins ago",
        "affected_zone": "Z-SHL-01",
        "traffic_diversion": "Alt route: Shillong–Jowai–Amlarem–Dawki or Shillong–Sohra–Sohbar–Dawki"
    }
]

# Emergency Settlement Prioritization
SEED_SETTLEMENTS: List[Dict[str, Any]] = [
    {
        "village": "Mawsynram Valley Sector",
        "district": "East Khasi Hills",
        "population": 1337,
        "risk_level": "severe",
        "distance_km": 3.4,
        "nearest_hospital": "Mawsynram Community Health Centre",
        "priority_rank": 1,
        "evacuation_status": "Immediate Evacuation Alert"
    },
    {
        "village": "Cherrapunji (Sohra Rim)",
        "district": "East Khasi Hills",
        "population": 2450,
        "risk_level": "high",
        "distance_km": 5.8,
        "nearest_hospital": "Sohra Community Health Centre",
        "priority_rank": 2,
        "evacuation_status": "Stage 2 Standby Alert"
    },
    {
        "village": "Laitlyngkot Slope Dwellings",
        "district": "East Khasi Hills",
        "population": 1480,
        "risk_level": "high",
        "distance_km": 8.5,
        "nearest_hospital": "Pynursla Community Health Centre",
        "priority_rank": 3,
        "evacuation_status": "Stage 1 Advisory"
    },
    {
        "village": "Ialong Cut-Slope Hamlet",
        "district": "West Jaintia Hills",
        "population": 1820,
        "risk_level": "moderate",
        "distance_km": 4.2,
        "nearest_hospital": "Jowai Civil Hospital (Ialong)",
        "priority_rank": 4,
        "evacuation_status": "Watch & Monitor"
    },
    {
        "village": "Nongpoh Valley Corridor",
        "district": "Ri-Bhoi",
        "population": 17055,
        "risk_level": "low",
        "distance_km": 1.5,
        "nearest_hospital": "Nongpoh District Civil Hospital",
        "priority_rank": 5,
        "evacuation_status": "Normal Operations"
    }
]

# In-Memory Citizen Field Reports Store
_REPORTS_STORE: List[Dict[str, Any]] = []

def get_risk_zones() -> Dict[str, Any]:
    return SEED_RISK_ZONES

def get_roads() -> List[Dict[str, Any]]:
    return SEED_ROADS

def get_settlements() -> List[Dict[str, Any]]:
    # Compute mathematical vulnerability score
    weights = {"severe": 4.0, "high": 2.5, "moderate": 1.5, "low": 1.0}
    settlements = []
    import math
    for s in SEED_SETTLEMENTS:
        w = weights.get(s["risk_level"].lower(), 1.0)
        pop = max(s["population"], 10)
        score = round(w * math.log10(pop) * s["distance_km"], 2)
        settlements.append({**s, "vulnerability_score": score})
    
    settlements.sort(key=lambda x: x["vulnerability_score"], reverse=True)
    for idx, item in enumerate(settlements):
        item["priority_rank"] = idx + 1
    return settlements

def get_reports() -> List[Dict[str, Any]]:
    return _REPORTS_STORE

def add_report(report_dict: Dict[str, Any]) -> Dict[str, Any]:
    new_id = f"REP-{datetime.datetime.now().year}-{len(_REPORTS_STORE) + 1:03d}"
    record = {
        "id": new_id,
        "reporter": report_dict.get("reporter", "Field Officer (Telemetry)"),
        "location_name": report_dict.get("location_name", "Field Coordinates"),
        "latitude": report_dict.get("latitude"),
        "longitude": report_dict.get("longitude"),
        "note": report_dict.get("note", ""),
        "severity": report_dict.get("severity", "high"),
        "status": "verified",
        "timestamp": "Just now",
        "photo_url": report_dict.get("photo_url")
    }
    _REPORTS_STORE.insert(0, record)
    return record


# In-Memory Alert Delivery Audit Store
_DELIVERY_AUDIT_STORE: List[Dict[str, Any]] = []

def add_delivery_audit_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Adds a delivery audit record to in-memory store (capped at 1000 items)."""
    _DELIVERY_AUDIT_STORE.insert(0, record)
    if len(_DELIVERY_AUDIT_STORE) > 1000:
        _DELIVERY_AUDIT_STORE.pop()
    return record

def get_delivery_audit_records(
    alert_id: Optional[str] = None,
    zone_id: Optional[str] = None,
    channel: Optional[str] = None,
    recipient_group: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """Retrieves delivery audit records matching query filters."""
    records = _DELIVERY_AUDIT_STORE
    if alert_id:
        clean_alert_id = alert_id.strip()
        records = [r for r in records if r.get("alert_id") == clean_alert_id]
    if zone_id:
        clean_zone = zone_id.strip().upper()
        records = [r for r in records if r.get("zone_id", "").upper() == clean_zone]
    if channel and channel.strip().lower() != "all":
        clean_chan = channel.strip().lower()
        records = [r for r in records if r.get("channel", "").lower() == clean_chan]
    if recipient_group and recipient_group.strip().lower() != "all":
        clean_recip = recipient_group.strip().lower()
        records = [r for r in records if r.get("recipient_group", "").lower() == clean_recip]
    if status and status.strip().lower() != "all":
        clean_stat = status.strip().lower()
        records = [r for r in records if r.get("status", "").lower() == clean_stat]
    return records[offset : offset + limit]

def clear_delivery_audit_records() -> None:
    """Clears all delivery audit records (useful for test isolation)."""
    _DELIVERY_AUDIT_STORE.clear()

