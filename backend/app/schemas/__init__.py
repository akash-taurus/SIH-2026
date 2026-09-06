from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class RiskSummaryItem(BaseModel):
    level: str
    count: int
    percentage: int
    color: str

class RoadItem(BaseModel):
    road_id: str
    name: str
    status: str
    blockage_reason: Optional[str] = None
    last_updated: str
    affected_zone: Optional[str] = None
    traffic_diversion: Optional[str] = None

class SettlementItem(BaseModel):
    village: str
    district: str
    population: int
    risk_level: str
    distance_km: float
    nearest_hospital: str
    priority_rank: int
    evacuation_status: str
    vulnerability_score: Optional[float] = None

class ReportCreate(BaseModel):
    note: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    severity: Optional[str] = "high"
    reporter: Optional[str] = "Citizen Responder"

class ReportResponse(BaseModel):
    id: str
    reporter: str
    location_name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    note: str
    severity: str
    status: str
    timestamp: str
    photo_url: Optional[str] = None

class WeatherForecastPoint(BaseModel):
    time: str
    rainfall: float
    soilMoisture: Optional[float] = None
    caineThreshold: Optional[float] = None
    isBreach: Optional[bool] = False

class Factor(BaseModel):
    feature: str
    label: str
    value: float
    shap_value: float
    direction: str
    explanation: str

class PredictRequest(BaseModel):
    slope_deg: float = 35.0
    rain_1h: float = 25.0
    rain_24h: float = 120.0
    rain_7d: float = 240.0
    soil_saturation_pct: float = 0.80
    dist_to_road_m: float = 30.0
    historical_slide_density: float = 3.0
    storm_duration_hours: float = 1.0
    # Optional fields for geographic ML grid cells
    lat: Optional[float] = None
    lon: Optional[float] = None
    elevation_m: Optional[float] = None
    aspect_deg: Optional[float] = None
    ndvi: Optional[float] = None
    rain_1h_mm: Optional[float] = None
    rain_6h_mm: Optional[float] = None
    rain_12h_mm: Optional[float] = None
    rain_24h_mm: Optional[float] = None
    rain_3d_mm: Optional[float] = None
    rain_7d_mm: Optional[float] = None
    rain_14d_mm: Optional[float] = None
    rain_30d_mm: Optional[float] = None
    soil_saturation_proxy: Optional[float] = None
    curvature: Optional[float] = None
    twi: Optional[float] = None
    distance_to_drainage_m: Optional[float] = None

class BatchPredictRequest(BaseModel):
    cells: List[PredictRequest]

class PredictResponse(BaseModel):
    risk_level: str
    probability: float
    factor_of_safety: Optional[float] = None
    failure_mode: Optional[str] = None
    pore_pressure_kpa: Optional[float] = None
    physics_threshold_breached: bool
    geotechnical_safety: Dict[str, Any]
    features_used: Dict[str, float]
    confidence_score: float
    probability_bounds: Optional[Dict[str, float]] = None
    model_version: Optional[str] = "v2.0"
    top_contributing_factors: Optional[List[Factor]] = None

from app.schemas.alerts import (
    AlertResponse,
    DeliveryAuditRecord,
    TestDispatchRequest,
    TestDispatchResponse,
    AlertAcknowledgeRequest,
    AlertResolveRequest,
    WorkerStatusResponse,
)

