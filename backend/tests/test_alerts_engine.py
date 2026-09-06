"""
Comprehensive Automated Test Suite for Milestone 1:
- Physics & Rainfall Risk Triggers (FS <= 1.10, Caine/Guzzetti I-D curves, cloudbursts, extreme 24h downpours)
- Pluggable Notification Dispatch Engine & Zero-Key Simulator
- Delivery Audit Record Storage & Querying
- Cooldown Deduplication State Machine & Escalation Override
- Background Monitoring Worker Lifecycle, Non-Blocking Polling, and Resilient Recovery
- FastAPI Lifespan Startup & Shutdown Integration
"""
import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport

from app.main import app, lifespan
from app.services.ml.physics import PhysicsSafetyShield
from app.services.alert_service import AlertService, alert_service
from app.services.notification_service import (
    ZeroKeySimulatedProvider,
    TwilioSMSProvider,
    CDACCAPProvider,
    NotificationDispatcher,
    notification_dispatcher,
)
from app.database import (
    get_delivery_audit_records,
    clear_delivery_audit_records,
    add_delivery_audit_record,
)


@pytest.fixture(autouse=True)
def clean_audit_store():
    clear_delivery_audit_records()
    yield
    clear_delivery_audit_records()


# =====================================================================
# 1. Physics & Geotechnical Safety Threshold Tests
# =====================================================================

def test_fs_threshold_incipient_failure():
    """
    Verifies that Factor of Safety between 1.00 and 1.10 triggers
    incipient slope instability alert with structured breach reasons.
    """
    # Infinite slope evaluation: slope 27 deg, soil_saturation 0.80, 24h rain 140mm
    stability = PhysicsSafetyShield.calculate_factor_of_safety(
        slope_deg=27.0,
        soil_type="Highly Saturated Colluvium",
        soil_saturation_pct=0.80,
        rainfall_24h_mm=140.0
    )
    fs = stability["factor_of_safety"]
    # Verify FS is in the incipient failure range [1.00, 1.10]
    assert 1.00 <= fs <= 1.10, f"Expected FS in [1.00, 1.10], got {fs}"
    assert stability["is_slope_unstable"] is False  # Only True if FS < 1.0

    # Evaluate geotechnical threshold
    eval_result = PhysicsSafetyShield.evaluate_geotechnical_threshold(
        rain_intensity_1h=5.0,  # Below Caine threshold
        duration_hours=1.0,
        slope_deg=27.0,
        soil_saturation_pct=0.80,
        soil_type="Highly Saturated Colluvium",
        rainfall_24h_mm=140.0
    )
    assert eval_result["fs_breached"] is True
    assert eval_result["physics_threshold_breached"] is True
    assert any("Incipient Slope Instability" in r for r in eval_result["breach_reasons"])
    assert any("FS=" in r and "<= 1.10" in r for r in eval_result["breach_reasons"])


def test_caine_and_guzzetti_breaches():
    """
    Verifies Caine (1980) and Guzzetti (2008) empirical I-D threshold breaches.
    """
    # For D = 1.0h, Caine = 14.82 mm/h, Guzzetti = 19.50 mm/h
    # Test rain intensity 16.0 mm/h: breaches Caine, but below Guzzetti
    eval_caine = PhysicsSafetyShield.evaluate_geotechnical_threshold(
        rain_intensity_1h=16.0,
        duration_hours=1.0,
        slope_deg=30.0,  # Critical slope >= 25 deg
        soil_saturation_pct=0.50,
        rainfall_24h_mm=20.0
    )
    assert eval_caine["caine_breached"] is True
    assert eval_caine["guzzetti_breached"] is False
    assert eval_caine["physics_threshold_breached"] is True
    assert any("Caine (1980) I-D threshold breached" in r for r in eval_caine["breach_reasons"])

    # Test rain intensity 22.0 mm/h: breaches both Caine and Guzzetti
    eval_both = PhysicsSafetyShield.evaluate_geotechnical_threshold(
        rain_intensity_1h=22.0,
        duration_hours=1.0,
        slope_deg=30.0,
        soil_saturation_pct=0.50,
        rainfall_24h_mm=20.0
    )
    assert eval_both["caine_breached"] is True
    assert eval_both["guzzetti_breached"] is True
    assert any("Guzzetti (2008)" in r for r in eval_both["breach_reasons"])


def test_pre_saturated_caine_breach():
    """
    Verifies that high soil saturation (>= 85%) lowers Caine threshold to 75%.
    """
    caine_1h = PhysicsSafetyShield.calculate_critical_intensity(1.0)  # 14.82
    # 75% of Caine = 11.115 mm/h. Rain = 12.0 mm/h (below 14.82, but >= 11.12)
    eval_result = PhysicsSafetyShield.evaluate_geotechnical_threshold(
        rain_intensity_1h=12.0,
        duration_hours=1.0,
        slope_deg=30.0,
        soil_saturation_pct=0.90,  # >= 85%
        rainfall_24h_mm=40.0
    )
    assert eval_result["sat_caine_breached"] is True
    assert eval_result["physics_threshold_breached"] is True
    assert any("pre-saturation" in r.lower() for r in eval_result["breach_reasons"])


def test_acute_cloudburst_downpour():
    """
    Verifies acute torrential cloudburst trigger (P_1h >= 35.0 mm/h)
    even on non-critical gentle slopes (< 25 deg).
    """
    eval_result = PhysicsSafetyShield.evaluate_geotechnical_threshold(
        rain_intensity_1h=42.0,  # >= 35 mm/h
        duration_hours=1.0,
        slope_deg=15.0,  # Non-critical slope
        soil_saturation_pct=0.40,
        rainfall_24h_mm=30.0
    )
    assert eval_result["acute_1h_breached"] is True
    assert eval_result["physics_threshold_breached"] is True
    assert any("cloudburst downpour" in r.lower() for r in eval_result["breach_reasons"])


def test_extreme_24h_saturated_downpour():
    """
    Verifies extreme 24h cumulative loading under high saturation (P_24h >= 150mm and Sat >= 85%).
    """
    eval_result = PhysicsSafetyShield.evaluate_geotechnical_threshold(
        rain_intensity_1h=5.0,
        duration_hours=1.0,
        slope_deg=18.0,
        soil_saturation_pct=0.88,  # >= 85%
        rainfall_24h_mm=175.0      # >= 150 mm
    )
    assert eval_result["extreme_24h_sat_breached"] is True
    assert eval_result["physics_threshold_breached"] is True
    assert any("extreme 24h cumulative loading" in r.lower() for r in eval_result["breach_reasons"])


# =====================================================================
# 2. Notification Dispatch & Zero-Key Delivery Tests
# =====================================================================

@pytest.mark.asyncio
async def test_zero_key_simulated_sms_dispatch():
    """
    Verifies zero-key simulated SMS formatting (<= 160 chars),
    audit record creation, and latency tracking.
    """
    provider = ZeroKeySimulatedProvider()
    alert = {
        "id": "ALT-2026-Z-SHL-01",
        "zone_id": "Z-SHL-01",
        "zone_name": "Shillong East Ridge",
        "severity": "severe",
        "factor_of_safety": 0.88,
        "title": "CRITICAL HAZARD WARNING: Shillong East Ridge"
    }
    record = await provider.dispatch(alert, channel="sms", recipient_group="citizens")
    assert record["status"] == "simulated_delivered"
    assert record["provider"] == "zero_key_simulation"
    assert record["channel"] == "sms"
    assert record["recipient_group"] == "citizens"
    assert record["latency_ms"] >= 0.0
    assert len(record["payload_preview"]) <= 160
    assert "Shillong East Ridge" in record["payload_preview"]

    # Verify audit store persistence in database
    stored = get_delivery_audit_records(zone_id="Z-SHL-01")
    assert len(stored) == 1
    assert stored[0]["id"] == record["id"]


@pytest.mark.asyncio
async def test_zero_key_push_and_cap_formatting():
    """Verifies Push notification and CAP XML formatting in simulation mode."""
    provider = ZeroKeySimulatedProvider()
    alert = {
        "id": "ALT-2026-Z-CHR-02",
        "zone_id": "Z-CHR-02",
        "zone_name": "Sohra Escarpment",
        "severity": "high",
        "factor_of_safety": 1.05,
        "title": "ELEVATED HAZARD WARNING: Sohra Escarpment"
    }
    push_record = await provider.dispatch(alert, channel="push", recipient_group="field_responders")
    assert push_record["channel"] == "push"
    assert "🚨 HIGH ALERT" in push_record["payload_preview"]

    cap_record = await provider.dispatch(alert, channel="cap", recipient_group="emergency_command")
    assert cap_record["channel"] == "cap"
    assert "<CAP:Alert" in cap_record["payload_preview"]
    assert "zone='Z-CHR-02'" in cap_record["payload_preview"]


@pytest.mark.asyncio
async def test_notification_dispatcher_multi_channel():
    """Verifies concurrent dispatch across multiple channels and recipient groups."""
    dispatcher = NotificationDispatcher()
    alert = {
        "id": "ALT-2026-Z-MAW-03",
        "zone_id": "Z-MAW-03",
        "zone_name": "Mawsynram Canyons",
        "severity": "severe",
        "factor_of_safety": 0.72,
        "title": "CRITICAL HAZARD WARNING: Mawsynram Canyons"
    }
    records = await dispatcher.dispatch_alert(
        alert=alert,
        channels=["sms", "push"],
        recipient_groups=["citizens", "field_responders"]
    )
    assert len(records) == 4  # 2 channels * 2 groups = 4 dispatches
    assert all(r["status"] == "simulated_delivered" for r in records)

    stored = get_delivery_audit_records(zone_id="Z-MAW-03")
    assert len(stored) == 4


@pytest.mark.asyncio
async def test_twilio_and_cdac_fallback_to_simulation():
    """Verifies that Twilio and CDAC providers safely fall back to simulation when keys are absent."""
    twilio_provider = TwilioSMSProvider()
    cdac_provider = CDACCAPProvider()

    alert = {"id": "ALT-TEST", "zone_id": "Z-TEST", "zone_name": "Test Zone", "severity": "high", "factor_of_safety": 1.02}

    tw_record = await twilio_provider.dispatch(alert, "sms", "citizens")
    assert "twilio" in tw_record["provider"]
    assert tw_record["status"] == "simulated_delivered"

    cdac_record = await cdac_provider.dispatch(alert, "cap", "emergency_command")
    assert "cdac_cap" in cdac_record["provider"]
    assert cdac_record["status"] == "simulated_delivered"


# =====================================================================
# 3. Cooldown Deduplication & Escalation Override Tests
# =====================================================================

@pytest.mark.asyncio
async def test_cooldown_deduplication_suppresses_duplicate_alerts():
    """
    Verifies that rapid consecutive breaches within the cooldown window (15m)
    suppress notification dispatch and log a suppression audit record.
    """
    service = AlertService(cooldown_window_seconds=900)
    candidate_high = {
        "id": "ALT-2026-Z-SHL-01",
        "zone_id": "Z-SHL-01",
        "zone_name": "Shillong Peak Ridge",
        "severity": "high",
        "risk_level": "High",
        "factor_of_safety": 1.08,
        "title": "ELEVATED HAZARD WARNING: Shillong Peak Ridge"
    }

    # 1. First trigger: must dispatch
    outcome1 = await service.process_alert_dispatch(candidate_high)
    assert outcome1 == "dispatched_new"
    assert "Z-SHL-01" in service._sector_cooldowns

    dispatched_audits = get_delivery_audit_records(zone_id="Z-SHL-01", status="simulated_delivered")
    assert len(dispatched_audits) >= 1

    # 2. Immediate second trigger (same severity): MUST BE SUPPRESSED
    outcome2 = await service.process_alert_dispatch(candidate_high)
    assert outcome2 == "suppressed_cooldown"

    suppressed_audits = get_delivery_audit_records(zone_id="Z-SHL-01", status="suppressed_cooldown")
    assert len(suppressed_audits) == 1
    assert "Suppressed duplicate" in suppressed_audits[0]["payload_preview"]
    assert service._sector_cooldowns["Z-SHL-01"]["suppressed_count"] == 1


@pytest.mark.asyncio
async def test_escalation_override_bypasses_cooldown():
    """
    Verifies that when risk escalates (High -> Severe) within the cooldown window,
    the cooldown is immediately bypassed and emergency notifications are dispatched.
    """
    service = AlertService(cooldown_window_seconds=900)
    alert_high = {
        "id": "ALT-2026-Z-CHR-02",
        "zone_id": "Z-CHR-02",
        "zone_name": "Sohra Escarpment",
        "severity": "high",
        "risk_level": "High",
        "factor_of_safety": 1.06,
        "title": "ELEVATED HAZARD WARNING: Sohra Escarpment"
    }
    outcome_high = await service.process_alert_dispatch(alert_high)
    assert outcome_high == "dispatched_new"

    # Severe escalation happens 10 seconds later
    alert_severe = {
        "id": "ALT-2026-Z-CHR-02",
        "zone_id": "Z-CHR-02",
        "zone_name": "Sohra Escarpment",
        "severity": "severe",
        "risk_level": "Severe",
        "factor_of_safety": 0.74,
        "title": "CRITICAL HAZARD WARNING: Sohra Escarpment"
    }
    outcome_severe = await service.process_alert_dispatch(alert_severe)
    assert outcome_severe == "escalated_dispatched"
    assert service._sector_cooldowns["Z-CHR-02"]["last_severity"] == "severe"
    assert "CRITICAL ESCALATED" in alert_severe["title"]


@pytest.mark.asyncio
async def test_cooldown_expiration_allows_redispatch():
    """Verifies that once the cooldown window expires, new alerts dispatch cleanly."""
    service = AlertService(cooldown_window_seconds=1)  # 1 second cooldown for fast test
    alert = {
        "id": "ALT-2026-Z-JOW-04",
        "zone_id": "Z-JOW-04",
        "zone_name": "Jowai Bypass Cut",
        "severity": "high",
        "risk_level": "High",
        "factor_of_safety": 1.05,
        "title": "ELEVATED HAZARD WARNING: Jowai"
    }
    outcome1 = await service.process_alert_dispatch(alert)
    assert outcome1 == "dispatched_new"

    # Wait for cooldown to expire
    await asyncio.sleep(1.05)

    outcome2 = await service.process_alert_dispatch(alert)
    assert outcome2 == "dispatched_new"


# =====================================================================
# 4. Background Monitoring Worker Lifecycle & Telemetry Tests
# =====================================================================

@pytest.mark.asyncio
async def test_worker_lifecycle_start_stop():
    """Verifies worker start, idempotent start, and clean stop."""
    service = AlertService()
    assert service.get_worker_status()["status"] == "stopped"
    assert service.get_worker_status()["is_running"] is False

    started = await service.start_monitoring_worker(interval_seconds=0.05)
    assert started is True
    status = service.get_worker_status()
    assert status["is_running"] is True
    assert status["status"] in ["running", "degraded"]

    # Duplicate start returns False
    duplicate = await service.start_monitoring_worker(interval_seconds=0.05)
    assert duplicate is False

    stopped = await service.stop_monitoring_worker()
    assert stopped is True
    assert service.get_worker_status()["status"] == "stopped"
    assert service.get_worker_status()["is_running"] is False


@pytest.mark.asyncio
async def test_worker_periodic_polling():
    """Verifies worker repeatedly executes inspection cycles in background."""
    service = AlertService()
    await service.start_monitoring_worker(interval_seconds=0.04)
    await asyncio.sleep(0.15)

    status = service.get_worker_status()
    await service.stop_monitoring_worker()

    assert status["poll_count"] >= 2
    assert status["last_run_at"] is not None
    assert status["last_duration_seconds"] >= 0.0
    assert status["monitored_sectors_count"] == 6


@pytest.mark.asyncio
async def test_worker_pause_resume():
    """Verifies worker evaluations pause and resume without task recreation."""
    service = AlertService()
    await service.start_monitoring_worker(interval_seconds=0.04)
    await asyncio.sleep(0.06)

    service.pause_monitoring()
    status_paused = service.get_worker_status()
    assert status_paused["is_paused"] is True
    assert status_paused["status"] == "paused"
    count_paused = status_paused["poll_count"]

    await asyncio.sleep(0.10)
    assert service.get_worker_status()["poll_count"] == count_paused

    service.resume_monitoring()
    await asyncio.sleep(0.10)
    assert service.get_worker_status()["poll_count"] > count_paused

    await service.stop_monitoring_worker()


@pytest.mark.asyncio
async def test_worker_resilient_error_recovery():
    """Verifies that unexpected evaluation exceptions do not crash the worker task."""
    service = AlertService()
    with patch.object(service, "evaluate_and_dispatch_alerts", side_effect=RuntimeError("Simulated Sensor Glitch")):
        await service.start_monitoring_worker(interval_seconds=0.04)
        await asyncio.sleep(0.10)

        status = service.get_worker_status()
        assert status["is_running"] is True  # Task must survive
        assert status["status"] == "degraded"
        assert status["consecutive_failures"] >= 1
        assert "Simulated Sensor Glitch" in status["last_error"]

        await service.stop_monitoring_worker()


@pytest.mark.asyncio
async def test_fastapi_lifespan_integration():
    """Verifies that FastAPI lifespan starts the worker on startup and cancels on shutdown."""
    async with lifespan(app):
        status = alert_service.get_worker_status()
        assert status["is_running"] is True

    # After lifespan exit, worker must be terminated
    status_after = alert_service.get_worker_status()
    assert status_after["is_running"] is False


@pytest.mark.asyncio
async def test_worker_status_endpoints():
    """Verifies REST API worker status and control endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # GET worker status
        resp = await ac.get("/api/v1/alerts/worker/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "is_running" in data
        assert data["monitored_sectors_count"] == 6

        # POST pause
        pause_resp = await ac.post("/api/v1/alerts/worker/pause")
        assert pause_resp.status_code == 200
        assert pause_resp.json()["status"] == "paused"

        # POST resume
        resume_resp = await ac.post("/api/v1/alerts/worker/resume")
        assert resume_resp.status_code == 200
        assert resume_resp.json()["status"] == "resumed"


@pytest.mark.asyncio
async def test_alert_acknowledgement_and_resolution():
    """Verifies acknowledge and resolve workflows in alert_service."""
    service = AlertService()
    # Create synthetic active alert
    test_alert = {
        "id": "ALT-2026-Z-TEST",
        "zone_id": "Z-TEST",
        "zone_name": "Test Sector",
        "severity": "high",
        "risk_level": "High",
        "status": "active",
        "factor_of_safety": 1.05,
        "probability": 0.70,
        "title": "TEST ALERT",
    }
    service._active_alerts = [test_alert]
    service._sector_cooldowns["Z-TEST"] = {"last_severity": "high", "suppressed_count": 0}

    # Acknowledge
    ack = service.acknowledge_alert("ALT-2026-Z-TEST", acknowledged_by="Officer Sangma")
    assert ack is not None
    assert ack["status"] == "acknowledged"
    assert ack["acknowledged_by"] == "Officer Sangma"
    assert ack["acknowledged_at"] is not None

    # Resolve
    res = service.resolve_alert("ALT-2026-Z-TEST", resolved_by="Admin Marak", note="Drain cleared")
    assert res is not None
    assert res["status"] == "resolved"
    assert res["resolution_note"] == "Drain cleared"
    assert len(service.get_active_alerts()) == 0
    assert len(service.get_historical_alerts()) == 1
    assert "Z-TEST" not in service._sector_cooldowns
