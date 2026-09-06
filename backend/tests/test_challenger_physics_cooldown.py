"""
M1 Challenger 1: Physics & Cooldown Adversarial Test Suite.

Adversarially stress-tests:
1. Geotechnical physics boundary conditions:
   - FS = 1.10001 vs 1.09999 (Incipient instability boundary)
   - FS = 1.00001 vs 0.99999 (Active limit-equilibrium shear failure boundary)
   - Slope = 24.9° vs 25.0° (Caine & Guzzetti empirical hillslope threshold boundary)
   - Slope-invariance of acute cloudburst downpours (>= 35 mm/h on gentle 24.9° slope)
   - Extreme inputs: negative rainfall (-15 mm/h, -100 mm 24h), extreme deluge (500 mm/h), 
     zero/negative duration (0.0h, -5.0h), 0% and 100% soil saturation.
2. Cooldown deduplication & rapid repeated triggers:
   - 100 consecutive rapid triggers in a tight loop (exactly 1 dispatched, 99 suppressed)
   - Audit trail verification: exactly 99 suppressed_cooldown audit records with cycle count and remaining seconds
   - Escalation override: High (FS=1.05) -> Severe (FS=0.85) immediately bypasses cooldown
   - Post-escalation suppression: subsequent Severe or High triggers suppressed
   - Cooldown expiration: advancing time by 901s permits new dispatch
   - Multi-sector independence: cooldowns are strictly isolated per zone
   - Sector stabilization: recovery to FS >= 1.30 clears cooldown
"""
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import pytest

from app.services.ml.physics import PhysicsSafetyShield
from app.services.alert_service import AlertService
from app.database import (
    clear_delivery_audit_records,
    get_delivery_audit_records,
)


@pytest.fixture(autouse=True)
def clean_audit_store():
    """Ensures each test starts and ends with a pristine delivery audit store."""
    clear_delivery_audit_records()
    yield
    clear_delivery_audit_records()


# ==============================================================================
# 1. Geotechnical Physics Limit-Equilibrium & Boundary Tests
# ==============================================================================

def test_fs_boundary_1_10001_vs_1_09999():
    """
    Adversarial boundary test around Factor of Safety FS = 1.10:
    - FS = 1.10001: Slope is marginally stable; FS threshold must NOT breach.
    - FS = 1.09999: Incipient slope instability; FS threshold MUST breach.
    - FS = 1.10000: Exact boundary; FS threshold MUST breach (FS <= 1.10).
    """
    service = AlertService()
    zone = {
        "properties": {
            "zone_id": "Z-BOUNDARY-01",
            "name": "Boundary Test Ridge",
            "critical_infrastructure": "National Highway NH-40",
        }
    }

    # Case A: FS = 1.10001 (Above 1.10 threshold)
    with patch.object(PhysicsSafetyShield, "calculate_factor_of_safety") as mock_fs:
        mock_fs.return_value = {
            "factor_of_safety": 1.10001,
            "is_slope_unstable": False,
            "failure_mode": "Marginally Stable (Creep & Tension Cracks Likely)",
            "pore_water_pressure_kpa": 12.0,
            "driving_stress_kpa": 15.0,
            "resisting_strength_kpa": 16.5,
            "perched_water_table_m": 1.0,
        }
        res_above = PhysicsSafetyShield.evaluate_geotechnical_threshold(
            rain_intensity_1h=5.0,
            duration_hours=1.0,
            slope_deg=20.0,
            soil_saturation_pct=0.5,
            rainfall_24h_mm=20.0,
        )
        assert res_above["fs_breached"] is False
        assert res_above["physics_threshold_breached"] is False
        assert len(res_above["breach_reasons"]) == 0

        # Verify AlertService does not generate false positive alert
        risk_above = {
            "factor_of_safety": 1.10001,
            "probability": 0.25,
            "risk_level": "Low",
            "physics_threshold_breached": False,
            "geotechnical_safety": res_above,
        }
        alert_above = service._generate_zone_alert(zone, risk_above)
        assert alert_above is None

    # Case B: FS = 1.09999 (Below 1.10 threshold - Incipient Instability)
    with patch.object(PhysicsSafetyShield, "calculate_factor_of_safety") as mock_fs:
        mock_fs.return_value = {
            "factor_of_safety": 1.09999,
            "is_slope_unstable": False,
            "failure_mode": "Marginally Stable (Creep & Tension Cracks Likely)",
            "pore_water_pressure_kpa": 12.5,
            "driving_stress_kpa": 15.0,
            "resisting_strength_kpa": 16.49,
            "perched_water_table_m": 1.0,
        }
        res_below = PhysicsSafetyShield.evaluate_geotechnical_threshold(
            rain_intensity_1h=5.0,
            duration_hours=1.0,
            slope_deg=20.0,
            soil_saturation_pct=0.5,
            rainfall_24h_mm=20.0,
        )
        assert res_below["fs_breached"] is True
        assert res_below["physics_threshold_breached"] is True
        assert any("FS=1.10 <= 1.10" in r and "Incipient Slope Instability" in r for r in res_below["breach_reasons"])

        # Verify AlertService triggers High alert with breach reasons
        risk_below = {
            "factor_of_safety": 1.09999,
            "probability": 0.45,
            "risk_level": "Moderate",
            "physics_threshold_breached": True,
            "geotechnical_safety": res_below,
        }
        alert_below = service._generate_zone_alert(zone, risk_below)
        assert alert_below is not None
        assert alert_below["severity"] == "high"
        assert alert_below["factor_of_safety"] == 1.100  # round(1.09999, 3)

    # Case C: Exact boundary FS = 1.10000
    with patch.object(PhysicsSafetyShield, "calculate_factor_of_safety") as mock_fs:
        mock_fs.return_value = {
            "factor_of_safety": 1.10000,
            "is_slope_unstable": False,
            "failure_mode": "Marginally Stable",
            "pore_water_pressure_kpa": 12.0,
            "driving_stress_kpa": 15.0,
            "resisting_strength_kpa": 16.5,
            "perched_water_table_m": 1.0,
        }
        res_exact = PhysicsSafetyShield.evaluate_geotechnical_threshold(
            rain_intensity_1h=5.0, duration_hours=1.0, slope_deg=20.0
        )
        assert res_exact["fs_breached"] is True
        assert res_exact["physics_threshold_breached"] is True


def test_fs_boundary_1_00001_vs_0_99999():
    """
    Adversarial boundary test around Limit-Equilibrium Failure FS = 1.00:
    - FS = 1.00001: Incipient instability (High severity, FS <= 1.10).
    - FS = 0.99999: Active shear failure (Severe severity, FS <= 1.00).
    - FS = 1.00000: Exact limit-equilibrium boundary (Severe severity, FS <= 1.00).
    """
    service = AlertService()
    zone = {
        "properties": {
            "zone_id": "Z-BOUNDARY-02",
            "name": "Limit-Equilibrium Zone",
            "critical_infrastructure": "State Highway SH-5",
        }
    }

    # Case A: FS = 1.00001 (Incipient Instability, High severity)
    with patch.object(PhysicsSafetyShield, "calculate_factor_of_safety") as mock_fs:
        mock_fs.return_value = {
            "factor_of_safety": 1.00001,
            "is_slope_unstable": False,
            "failure_mode": "Marginally Stable (Creep & Tension Cracks Likely)",
            "pore_water_pressure_kpa": 14.0,
            "driving_stress_kpa": 15.0,
            "resisting_strength_kpa": 15.0,
            "perched_water_table_m": 1.1,
        }
        res_incipient = PhysicsSafetyShield.evaluate_geotechnical_threshold(
            rain_intensity_1h=5.0, duration_hours=1.0, slope_deg=22.0
        )
        assert res_incipient["fs_breached"] is True
        assert any("Incipient Slope Instability" in r for r in res_incipient["breach_reasons"])
        assert not any("Active Limit-Equilibrium Shear Failure" in r for r in res_incipient["breach_reasons"])

        risk_incipient = {
            "factor_of_safety": 1.00001,
            "probability": 0.55,
            "risk_level": "Moderate",
            "physics_threshold_breached": True,
            "geotechnical_safety": res_incipient,
        }
        alert_incipient = service._generate_zone_alert(zone, risk_incipient)
        assert alert_incipient is not None
        assert alert_incipient["severity"] == "high"

    # Case B: FS = 0.99999 (Active Failure, Severe severity)
    with patch.object(PhysicsSafetyShield, "calculate_factor_of_safety") as mock_fs:
        mock_fs.return_value = {
            "factor_of_safety": 0.99999,
            "is_slope_unstable": True,
            "failure_mode": "Rotational Slump along Bedding Plane",
            "pore_water_pressure_kpa": 16.0,
            "driving_stress_kpa": 15.0,
            "resisting_strength_kpa": 14.99,
            "perched_water_table_m": 1.3,
        }
        res_active = PhysicsSafetyShield.evaluate_geotechnical_threshold(
            rain_intensity_1h=5.0, duration_hours=1.0, slope_deg=22.0
        )
        assert res_active["fs_breached"] is True
        assert res_active["physics_threshold_breached"] is True
        assert any("Active Limit-Equilibrium Shear Failure" in r for r in res_active["breach_reasons"])

        risk_active = {
            "factor_of_safety": 0.99999,
            "probability": 0.55,
            "risk_level": "Moderate",
            "physics_threshold_breached": True,
            "geotechnical_safety": res_active,
        }
        alert_active = service._generate_zone_alert(zone, risk_active)
        assert alert_active is not None
        assert alert_active["severity"] == "severe"  # Elevated to severe because FS <= 1.00

    # Case C: Exact boundary FS = 1.00000
    with patch.object(PhysicsSafetyShield, "calculate_factor_of_safety") as mock_fs:
        mock_fs.return_value = {
            "factor_of_safety": 1.00000,
            "is_slope_unstable": False,
            "failure_mode": "Critical Limit Equilibrium",
            "pore_water_pressure_kpa": 15.0,
            "driving_stress_kpa": 15.0,
            "resisting_strength_kpa": 15.0,
            "perched_water_table_m": 1.2,
        }
        res_exact = PhysicsSafetyShield.evaluate_geotechnical_threshold(
            rain_intensity_1h=5.0, duration_hours=1.0, slope_deg=22.0
        )
        assert any("FS=1.00 <= 1.00" in r and "Active Limit-Equilibrium" in r for r in res_exact["breach_reasons"])


def test_slope_critical_boundary_24_9_vs_25_0():
    """
    Adversarial boundary test around critical hillslope threshold (slope = 25.0°):
    - Slope = 24.9°: Below critical threshold. Caine & Guzzetti I-D curves must NOT trigger.
    - Slope = 25.0°: Critical threshold met. Caine & Guzzetti I-D curves MUST trigger.
    - Acute cloudburst (35 mm/h): Slope-invariant; must trigger at slope = 24.9°.
    """
    # Case A: Slope = 24.9° with heavy rain (20 mm/h)
    eval_24_9 = PhysicsSafetyShield.evaluate_geotechnical_threshold(
        rain_intensity_1h=20.0,  # Exceeds Caine (14.82) and Guzzetti (19.50)
        duration_hours=1.0,
        slope_deg=24.9,
        soil_saturation_pct=0.50,
        rainfall_24h_mm=30.0,
    )
    assert eval_24_9["is_slope_critical"] is False
    assert eval_24_9["caine_breached"] is False
    assert eval_24_9["guzzetti_breached"] is False
    assert eval_24_9["sat_caine_breached"] is False
    assert not any("Caine (1980)" in r for r in eval_24_9["breach_reasons"])
    assert not any("Guzzetti (2008)" in r for r in eval_24_9["breach_reasons"])

    # Case B: Slope = 25.0° with identical heavy rain (20 mm/h)
    eval_25_0 = PhysicsSafetyShield.evaluate_geotechnical_threshold(
        rain_intensity_1h=20.0,
        duration_hours=1.0,
        slope_deg=25.0,
        soil_saturation_pct=0.50,
        rainfall_24h_mm=30.0,
    )
    assert eval_25_0["is_slope_critical"] is True
    assert eval_25_0["caine_breached"] is True
    assert eval_25_0["guzzetti_breached"] is True
    assert eval_25_0["physics_threshold_breached"] is True
    assert any("Caine (1980)" in r for r in eval_25_0["breach_reasons"])
    assert any("Guzzetti (2008)" in r for r in eval_25_0["breach_reasons"])

    # Case C: Acute Cloudburst Downpour (>= 35 mm/h) is slope-invariant
    eval_cloudburst_gentle = PhysicsSafetyShield.evaluate_geotechnical_threshold(
        rain_intensity_1h=36.0,
        duration_hours=1.0,
        slope_deg=24.9,  # Non-critical gentle slope
        soil_saturation_pct=0.40,
        rainfall_24h_mm=25.0,
    )
    assert eval_cloudburst_gentle["is_slope_critical"] is False
    assert eval_cloudburst_gentle["acute_1h_breached"] is True
    assert eval_cloudburst_gentle["physics_threshold_breached"] is True
    assert any("Acute cloudburst downpour" in r for r in eval_cloudburst_gentle["breach_reasons"])


def test_extreme_inputs_physics_resilience():
    """
    Adversarially tests extreme and pathological inputs:
    - Negative rainfall (-15 mm/h, -100 mm 24h): no exceptions, no false alerts.
    - Extreme deluge (500 mm/h, 500 mm 24h): triggers all meteorological breaches safely.
    - Zero and negative storm duration (0.0h, -5.0h): safely clamped to 0.5h.
    - Soil saturation boundaries: 0.0 (0%) and 1.0 (100%).
    """
    # 1. Negative rainfall
    eval_neg = PhysicsSafetyShield.evaluate_geotechnical_threshold(
        rain_intensity_1h=-15.0,
        duration_hours=1.0,
        slope_deg=30.0,
        soil_saturation_pct=0.50,
        rainfall_24h_mm=-100.0,
    )
    assert eval_neg["actual_intensity_mm_h"] == -15.0
    assert eval_neg["safety_factor"] >= 0.0  # Safe clamp max(rain_intensity, 0.1)
    assert eval_neg["acute_1h_breached"] is False
    assert eval_neg["caine_breached"] is False
    assert eval_neg["guzzetti_breached"] is False

    # 2. Extreme deluge (500 mm/h)
    eval_deluge = PhysicsSafetyShield.evaluate_geotechnical_threshold(
        rain_intensity_1h=500.0,
        duration_hours=1.0,
        slope_deg=32.0,
        soil_saturation_pct=1.0,
        rainfall_24h_mm=500.0,
    )
    assert eval_deluge["physics_threshold_breached"] is True
    assert eval_deluge["acute_1h_breached"] is True
    assert eval_deluge["extreme_24h_sat_breached"] is True
    assert eval_deluge["caine_breached"] is True
    assert eval_deluge["guzzetti_breached"] is True
    assert eval_deluge["safety_factor"] == 0.03  # 14.82 / 500.0
    assert len(eval_deluge["breach_reasons"]) >= 4

    # 3. Zero and negative storm duration
    caine_zero = PhysicsSafetyShield.calculate_critical_intensity(0.0)
    caine_neg = PhysicsSafetyShield.calculate_critical_intensity(-5.0)
    caine_min = PhysicsSafetyShield.calculate_critical_intensity(0.5)
    assert caine_zero == caine_min == 19.42  # 14.82 * (0.5 ^ -0.39)
    assert caine_neg == caine_min == 19.42

    guzzetti_zero = PhysicsSafetyShield.calculate_guzzetti_intensity(0.0)
    guzzetti_neg = PhysicsSafetyShield.calculate_guzzetti_intensity(-5.0)
    guzzetti_min = PhysicsSafetyShield.calculate_guzzetti_intensity(0.5)
    assert guzzetti_zero == guzzetti_min == 26.45  # 19.50 * (0.5 ^ -0.44)
    assert guzzetti_neg == guzzetti_min == 26.45

    # 4. Soil saturation boundaries: 0.0 vs 1.0
    eval_dry = PhysicsSafetyShield.evaluate_geotechnical_threshold(
        rain_intensity_1h=12.0,
        duration_hours=1.0,
        slope_deg=30.0,
        soil_saturation_pct=0.0,
        rainfall_24h_mm=10.0,
    )
    assert eval_dry["sat_caine_breached"] is False
    assert eval_dry["extreme_24h_sat_breached"] is False

    eval_saturated = PhysicsSafetyShield.evaluate_geotechnical_threshold(
        rain_intensity_1h=12.0,  # >= 75% of Caine (11.12)
        duration_hours=1.0,
        slope_deg=30.0,
        soil_saturation_pct=1.0,  # >= 85%
        rainfall_24h_mm=160.0,    # >= 150mm
    )
    assert eval_saturated["sat_caine_breached"] is True
    assert eval_saturated["extreme_24h_sat_breached"] is True
    assert eval_saturated["physics_threshold_breached"] is True


# ==============================================================================
# 2. Cooldown Deduplication & 100 Rapid Cycles Stress
# ==============================================================================

@pytest.mark.asyncio
async def test_cooldown_100_rapid_cycles_stress():
    """
    Stress-tests cooldown deduplication under 100 consecutive rapid triggers:
    - Cycle 1: Dispatched (dispatched_new), recording delivery audit logs.
    - Cycles 2..100: Suppressed (suppressed_cooldown), recording 99 suppression audits.
    - Verifies suppression counter reaches exactly 99.
    - Verifies exactly 4 simulated delivery audits (2 channels x 2 groups).
    - Verifies exactly 99 suppressed delivery audits with exact cycle count tracking.
    """
    service = AlertService(cooldown_window_seconds=900)
    candidate = {
        "id": "ALT-STRESS-100",
        "zone_id": "Z-STRESS-01",
        "zone_name": "Mawsynram Rapid Stress Ridge",
        "severity": "high",
        "risk_level": "High",
        "factor_of_safety": 1.06,
        "title": "ELEVATED HAZARD WARNING: Mawsynram",
    }

    outcomes = []
    for i in range(100):
        res = await service.process_alert_dispatch(dict(candidate))
        outcomes.append(res)

    # 1. Verify dispatch distribution
    assert outcomes[0] == "dispatched_new"
    assert all(o == "suppressed_cooldown" for o in outcomes[1:])
    assert outcomes.count("dispatched_new") == 1
    assert outcomes.count("suppressed_cooldown") == 99

    # 2. Verify sector cooldown state tracking
    cooldown_state = service._sector_cooldowns["Z-STRESS-01"]
    assert cooldown_state["suppressed_count"] == 99
    assert cooldown_state["last_severity"] == "high"

    # 3. Verify delivery audit store records
    dispatched_audits = get_delivery_audit_records(zone_id="Z-STRESS-01", status="simulated_delivered")
    assert len(dispatched_audits) == 4  # (SMS + Push) x (citizens + field_responders)

    suppressed_audits = get_delivery_audit_records(
        zone_id="Z-STRESS-01", status="suppressed_cooldown", limit=200
    )
    assert len(suppressed_audits) == 99

    # Check that latest suppression audit has cycle count 99
    latest_suppression = suppressed_audits[0]  # Store is LIFO
    assert "Suppression cycle count: 99." in latest_suppression["payload_preview"]
    assert "Suppressed duplicate high alert for Z-STRESS-01" in latest_suppression["payload_preview"]


@pytest.mark.asyncio
async def test_escalation_override_immediate_bypass():
    """
    Adversarially tests escalation override:
    - Initial trigger at High severity -> dispatched.
    - 5 duplicate High triggers -> suppressed.
    - Hazard escalates to Severe (FS = 0.85) -> immediately bypasses cooldown!
    - Verifies outcome is 'escalated_dispatched' and title updated.
    - Subsequent Severe trigger -> suppressed (no double-escalation).
    - Subsequent High trigger -> suppressed (no de-escalation bypass).
    """
    service = AlertService(cooldown_window_seconds=900)
    alert_high = {
        "id": "ALT-ESC-01",
        "zone_id": "Z-ESC-01",
        "zone_name": "Sohra Escarpment",
        "severity": "high",
        "risk_level": "High",
        "factor_of_safety": 1.05,
        "title": "ELEVATED HAZARD WARNING: Sohra",
    }
    alert_severe = {
        "id": "ALT-ESC-01",
        "zone_id": "Z-ESC-01",
        "zone_name": "Sohra Escarpment",
        "severity": "severe",
        "risk_level": "Severe",
        "factor_of_safety": 0.85,
        "title": "CRITICAL HAZARD WARNING: Sohra",
    }

    # 1. Initial High trigger
    out1 = await service.process_alert_dispatch(dict(alert_high))
    assert out1 == "dispatched_new"

    # 2. Duplicate High triggers are suppressed
    for _ in range(5):
        out_supp = await service.process_alert_dispatch(dict(alert_high))
        assert out_supp == "suppressed_cooldown"
    assert service._sector_cooldowns["Z-ESC-01"]["suppressed_count"] == 5

    # 3. Severe Escalation: MUST BYPASS COOLDOWN
    out_esc = await service.process_alert_dispatch(alert_severe)
    assert out_esc == "escalated_dispatched"
    assert service._sector_cooldowns["Z-ESC-01"]["last_severity"] == "severe"
    assert service._sector_cooldowns["Z-ESC-01"]["suppressed_count"] == 0

    # Verify escalated title modification
    assert "CRITICAL ESCALATED HAZARD WARNING" in alert_severe["title"]

    # Verify additional delivery audits were generated for the escalation
    dispatched_audits = get_delivery_audit_records(zone_id="Z-ESC-01", status="simulated_delivered")
    assert len(dispatched_audits) == 8  # 4 initial + 4 escalated

    # 4. Subsequent Severe trigger: MUST BE SUPPRESSED (cannot escalate to same tier)
    out_severe_dup = await service.process_alert_dispatch(alert_severe)
    assert out_severe_dup == "suppressed_cooldown"

    # 5. Subsequent High trigger: MUST BE SUPPRESSED (de-escalation does not bypass)
    out_high_downgrade = await service.process_alert_dispatch(alert_high)
    assert out_high_downgrade == "suppressed_cooldown"


@pytest.mark.asyncio
async def test_cooldown_expiration_after_901_seconds():
    """
    Verifies temporal cooldown expiration:
    - Alert triggers at t=0 -> dispatched_new.
    - Alert triggers at t=899s (< 900s) -> suppressed_cooldown.
    - Alert triggers at t=901s (> 900s) -> dispatched_new.
    """
    service = AlertService(cooldown_window_seconds=900)
    alert = {
        "id": "ALT-TIME-01",
        "zone_id": "Z-TIME-01",
        "zone_name": "Jowai Corridor",
        "severity": "high",
        "risk_level": "High",
        "factor_of_safety": 1.05,
        "title": "ELEVATED HAZARD WARNING: Jowai",
    }

    # 1. Initial trigger at t=0
    out1 = await service.process_alert_dispatch(dict(alert))
    assert out1 == "dispatched_new"

    # 2. Advance time by 899 seconds (still within 900s window)
    service._sector_cooldowns["Z-TIME-01"]["cooldown_until"] -= timedelta(seconds=899)
    out_supp = await service.process_alert_dispatch(dict(alert))
    assert out_supp == "suppressed_cooldown"

    # 3. Advance time past the 900s window (total 901s elapsed)
    service._sector_cooldowns["Z-TIME-01"]["cooldown_until"] -= timedelta(seconds=3)
    out_exp = await service.process_alert_dispatch(dict(alert))
    assert out_exp == "dispatched_new"


@pytest.mark.asyncio
async def test_multi_sector_independent_cooldowns():
    """
    Verifies that cooldown deduplication is strictly partitioned by zone_id.
    Suppression in Sector A must never suppress or interfere with Sector B.
    """
    service = AlertService(cooldown_window_seconds=900)
    zone_a = {
        "id": "ALT-A-01",
        "zone_id": "Z-SHL-01",
        "zone_name": "Shillong",
        "severity": "high",
        "risk_level": "High",
        "factor_of_safety": 1.05,
    }
    zone_b = {
        "id": "ALT-B-01",
        "zone_id": "Z-CHR-02",
        "zone_name": "Cherrapunji",
        "severity": "high",
        "risk_level": "High",
        "factor_of_safety": 1.05,
    }

    # Trigger Zone A
    res_a1 = await service.process_alert_dispatch(dict(zone_a))
    assert res_a1 == "dispatched_new"

    # Immediate second trigger for Zone A: suppressed
    res_a2 = await service.process_alert_dispatch(dict(zone_a))
    assert res_a2 == "suppressed_cooldown"

    # Immediate trigger for Zone B: MUST DISPATCH INDEPENDENTLY
    res_b1 = await service.process_alert_dispatch(dict(zone_b))
    assert res_b1 == "dispatched_new"

    # Immediate second trigger for Zone B: suppressed
    res_b2 = await service.process_alert_dispatch(dict(zone_b))
    assert res_b2 == "suppressed_cooldown"

    assert service._sector_cooldowns["Z-SHL-01"]["suppressed_count"] == 1
    assert service._sector_cooldowns["Z-CHR-02"]["suppressed_count"] == 1


@pytest.mark.asyncio
async def test_sector_stabilization_clears_cooldown():
    """
    Verifies that when a sector stabilizes (FS >= 1.30 and Low risk),
    its active cooldown is removed from the state machine so that any future
    flash storms can immediately trigger new emergency alerts.
    """
    service = AlertService(cooldown_window_seconds=900)

    # Monitored feature with high risk
    unstable_zone = {
        "type": "Feature",
        "properties": {
            "zone_id": "Z-RECOV-01",
            "name": "Recovery Zone",
            "mean_slope_deg": 35.0,
            "rainfall_1h_mm": 25.0,
            "rainfall_24h_mm": 180.0,
            "soil_saturation_pct": 0.90,
            "soil_type": "Highly Saturated Colluvium",
        },
    }

    # First evaluation cycle: triggers alert and enters cooldown
    alerts1 = await service.evaluate_and_dispatch_alerts([unstable_zone])
    assert len(alerts1) >= 1
    assert "Z-RECOV-01" in service._sector_cooldowns

    # Monitored feature stabilizes (sunny conditions, dry soil)
    stable_zone = {
        "type": "Feature",
        "properties": {
            "zone_id": "Z-RECOV-01",
            "name": "Recovery Zone",
            "mean_slope_deg": 10.0,
            "rainfall_1h_mm": 0.0,
            "rainfall_24h_mm": 0.0,
            "soil_saturation_pct": 0.15,
            "soil_type": "Clayey Loam on Weathered Quartzite",
        },
    }

    # Second evaluation cycle: detects stabilized sector
    alerts2 = await service.evaluate_and_dispatch_alerts([stable_zone])
    assert len(alerts2) == 0
    # Cooldown should be cleared
    assert "Z-RECOV-01" not in service._sector_cooldowns


# ==============================================================================
# 3. Pathological Edge Cases & Concurrency Stress
# ==============================================================================

def test_adversarial_pathological_slopes_and_durations():
    """
    Stress-tests physical boundary conditions with extreme inputs:
    - Negative and vertical slopes (-45°, 0°, 90°, 150°)
    - Micro-duration (0.0001h) and multi-month duration (10,000h)
    - Pathological soil saturation (-1.5, 5.0)
    - Unknown soil type fallback
    All evaluations must return finite numbers without exceptions or NaN values.
    """
    pathological_slopes = [-45.0, 0.0, 5.0, 24.9, 25.0, 38.0, 85.0, 90.0, 150.0]
    for s in pathological_slopes:
        stab = PhysicsSafetyShield.calculate_factor_of_safety(
            slope_deg=s,
            soil_type="Unknown Martian Regolith",
            soil_saturation_pct=0.60,
            rainfall_24h_mm=50.0
        )
        assert stab["factor_of_safety"] >= 0.05
        assert not any(v != v for v in [stab["factor_of_safety"], stab["driving_stress_kpa"], stab["resisting_strength_kpa"]])

    # Micro and macro durations
    c_micro = PhysicsSafetyShield.calculate_critical_intensity(0.0001)
    assert c_micro == 19.42  # clamped to 0.5h
    c_macro = PhysicsSafetyShield.calculate_critical_intensity(10000.0)
    assert 0.0 < c_macro < 1.0

    # Pathological saturation (-1.5 and 5.0)
    eval_neg_sat = PhysicsSafetyShield.evaluate_geotechnical_threshold(
        rain_intensity_1h=10.0,
        slope_deg=30.0,
        soil_saturation_pct=-1.5
    )
    assert eval_neg_sat["slope_stability"]["factor_of_safety"] >= 0.05

    eval_hyper_sat = PhysicsSafetyShield.evaluate_geotechnical_threshold(
        rain_intensity_1h=10.0,
        slope_deg=30.0,
        soil_saturation_pct=5.0
    )
    assert eval_hyper_sat["slope_stability"]["factor_of_safety"] >= 0.05


@pytest.mark.asyncio
async def test_alert_lifecycle_cooldown_interaction():
    """
    Verifies interaction between Alert Lifecycle (acknowledge/resolve) and Cooldown State Machine:
    - Acknowledging an alert keeps cooldown ACTIVE (suppresses duplicate notifications).
    - Resolving an alert CLEARS sector cooldown (allows immediate emergency redispatch).
    """
    service = AlertService(cooldown_window_seconds=900)
    alert = {
        "id": "ALT-LIFE-01",
        "zone_id": "Z-LIFE-01",
        "zone_name": "Lifecycle Zone",
        "severity": "high",
        "risk_level": "High",
        "factor_of_safety": 1.05,
        "title": "ELEVATED HAZARD WARNING: Lifecycle Zone",
        "status": "active"
    }

    # 1. Initial trigger: enters cooldown
    out1 = await service.process_alert_dispatch(dict(alert))
    assert out1 == "dispatched_new"
    service._active_alerts = [dict(alert)]
    assert "Z-LIFE-01" in service._sector_cooldowns

    # 2. Acknowledge alert: cooldown must remain intact
    ack = service.acknowledge_alert("ALT-LIFE-01", acknowledged_by="Responder Team Alpha")
    assert ack is not None
    assert ack["status"] == "acknowledged"
    assert "Z-LIFE-01" in service._sector_cooldowns

    # Next trigger during cooldown remains suppressed
    out_ack_dup = await service.process_alert_dispatch(dict(alert))
    assert out_ack_dup == "suppressed_cooldown"

    # 3. Resolve alert: sector cooldown MUST BE CLEARED
    res = service.resolve_alert("ALT-LIFE-01", resolved_by="NDRF Incident Commander")
    assert res is not None
    assert res["status"] == "resolved"
    assert "Z-LIFE-01" not in service._sector_cooldowns

    # 4. Immediate subsequent trigger now dispatches as NEW
    out_fresh = await service.process_alert_dispatch(dict(alert))
    assert out_fresh == "dispatched_new"


@pytest.mark.asyncio
async def test_rapid_concurrency_100_simultaneous_triggers():
    """
    Adversarially tests concurrency safety under 100 simultaneous async tasks:
    - 100 concurrent tasks execute process_alert_dispatch() for the same sector.
    - Exactly 1 task dispatches (dispatched_new).
    - Exactly 99 tasks are suppressed (suppressed_cooldown).
    - Verifies zero unhandled exceptions and robust internal state.
    """
    service = AlertService(cooldown_window_seconds=900)
    candidate = {
        "id": "ALT-CONC-100",
        "zone_id": "Z-CONC-100",
        "zone_name": "Massive Concurrency Zone",
        "severity": "high",
        "risk_level": "High",
        "factor_of_safety": 1.05,
        "title": "ELEVATED HAZARD WARNING: Concurrency",
    }

    # Fire 100 simultaneous tasks
    tasks = [
        service.process_alert_dispatch(dict(candidate))
        for _ in range(100)
    ]
    outcomes = await asyncio.gather(*tasks)

    dispatched = [o for o in outcomes if o == "dispatched_new"]
    suppressed = [o for o in outcomes if o == "suppressed_cooldown"]

    assert len(dispatched) == 1
    assert len(suppressed) == 99
    assert service._sector_cooldowns["Z-CONC-100"]["suppressed_count"] == 99

