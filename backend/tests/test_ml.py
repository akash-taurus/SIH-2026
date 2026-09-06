import pytest
from app.services.ml.physics import PhysicsSafetyShield
from app.services.ml.features import FeatureExtractor
from app.services.ml.risk_scorer import LandslideRiskEngine

def test_caine_physics_threshold_calculation():
    # Test Caine formula: Ic = 14.82 * (D ^ -0.39)
    # For D = 1 hour, Ic = 14.82
    # For D = 24 hours, Ic = 14.82 * (24 ^ -0.39) ~ 4.29
    thresh_1h = PhysicsSafetyShield.calculate_critical_intensity(1.0)
    assert thresh_1h == 14.82

    thresh_24h = PhysicsSafetyShield.calculate_critical_intensity(24.0)
    assert 4.0 <= thresh_24h <= 4.5

def test_geotechnical_evaluation_breach():
    # 45 mm/h rain on 35 deg slope -> Critical breach
    eval_result = PhysicsSafetyShield.evaluate_geotechnical_threshold(
        rain_intensity_1h=45.0,
        duration_hours=1.0,
        slope_deg=35.0,
        soil_saturation_pct=0.90
    )
    assert eval_result["physics_threshold_breached"] is True
    assert eval_result["is_slope_critical"] is True
    assert eval_result["safety_factor"] < 1.0

def test_geotechnical_evaluation_safe():
    # 2 mm/h rain on 10 deg slope -> Safe
    eval_result = PhysicsSafetyShield.evaluate_geotechnical_threshold(
        rain_intensity_1h=2.0,
        duration_hours=1.0,
        slope_deg=10.0,
        soil_saturation_pct=0.30
    )
    assert eval_result["physics_threshold_breached"] is False
    assert eval_result["is_slope_critical"] is False
    assert eval_result["safety_factor"] > 1.0

def test_feature_extractor():
    raw_data = {
        "slope_deg": 38.4,
        "rainfall_1h_mm": 25.0,
        "rainfall_24h_mm": 142.5,
        "soil_moisture": 85.0
    }
    vec = FeatureExtractor.extract_vector(raw_data)
    assert vec["slope_deg"] == 38.4
    assert vec["rain_1h"] == 25.0
    assert vec["rain_24h"] == 142.5
    assert vec["soil_saturation_pct"] == 0.85

def test_landslide_risk_engine_severe_scenario():
    engine = LandslideRiskEngine()
    result = engine.predict_risk({
        "slope_deg": 40.0,
        "rain_1h": 50.0,
        "rain_24h": 220.0,
        "rain_7d": 400.0,
        "soil_saturation_pct": 0.95,
        "dist_to_road_m": 15.0
    })
    assert result["risk_level"] in ["High", "Severe"]
    assert result["physics_threshold_breached"] is True
    assert result["probability"] >= 0.75
    assert "geotechnical_safety" in result

def test_landslide_risk_engine_low_scenario():
    engine = LandslideRiskEngine()
    result = engine.predict_risk({
        "slope_deg": 12.0,
        "rain_1h": 1.0,
        "rain_24h": 10.0,
        "rain_7d": 25.0,
        "soil_saturation_pct": 0.25,
        "dist_to_road_m": 200.0
    })
    assert result["risk_level"] == "Low"
    assert result["physics_threshold_breached"] is False
    assert result["probability"] < 0.30

def test_xgboost_integration_and_shap_explainability():
    engine = LandslideRiskEngine()
    assert engine.xgb_model is not None, "XGBoost model should be loaded in backend"
    assert engine.model_version.startswith("v2.0")

    result = engine.predict_risk({
        "slope_deg": 42.0,
        "rain_1h": 35.0,
        "rain_24h": 180.0,
        "rain_7d": 350.0,
        "soil_saturation_pct": 0.88,
        "dist_to_road_m": 25.0
    }, include_shap=True)

    assert "top_contributing_factors" in result
    factors = result["top_contributing_factors"]
    assert isinstance(factors, list)
    assert len(factors) > 0
    for f in factors:
        assert "feature" in f
        assert "label" in f
        assert "shap_value" in f
        assert "direction" in f
        assert "explanation" in f

def test_extract_xgb_dataframe_robustness():
    minimal_payload = {"slope_deg": 25.0, "rain_24h": 50.0}
    df = FeatureExtractor.extract_xgb_dataframe(minimal_payload)
    assert len(df.columns) == 21
    assert "slope_deg" in df.columns
    assert "rain_intensity_ratio" in df.columns
    assert "high_slope" in df.columns

