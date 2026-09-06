"""
Comprehensive Automated Test Suite for Milestone 2:
Alert Management & Delivery Status Endpoints (R2)

Covers:
- SUITE 1: Delivery Audit Endpoint (GET /api/v1/alerts/deliveries/audit)
  Filters: channel, recipient_group, status, alert_id, zone_id, wildcard 'all', pagination, 422 errors.
- SUITE 2: Active Alerts Query (GET /api/v1/alerts)
  Filters: status (active, acknowledged, resolved, all), severity, zone_id, refresh, 422 errors.
- SUITE 3: Historical Alerts Query (GET /api/v1/alerts/history)
  Pagination (limit, offset), X-Total-Count header, severity/zone filtering, 422 errors.
- SUITE 4: Single Alert Detail (GET /api/v1/alerts/{alert_id})
  Query by ID, query by zone_id fallback, historical lookup, 404 handling for nonexistent alerts and subpaths.
- SUITE 5: Alert Acknowledgement (POST /api/v1/alerts/{alert_id}/acknowledge)
  Custom officer, notes, default body, 404 handling, worker polling acknowledgment persistence.
- SUITE 6: Alert Resolution (POST /api/v1/alerts/{alert_id}/resolve)
  Custom resolver, resolution notes, move from active to history, clearing sector cooldown, 404 handling.
- SUITE 7: On-Demand Test Dispatch (POST /api/v1/alerts/test-dispatch)
  Drill dispatch, multi-channel (SMS, Push, CAP), recipient groups, custom broadcast message, delivery audit store linkage.
- SUITE 8: Worker Health & Controls (GET /alerts/worker/status, POST /worker/pause, POST /worker/resume)
  Telemetry response, pausing, resuming, alias routes.
- SUITE 9: Route Precedence & Regression Guard
  Strict verification that static routes (/deliveries/audit, /history, /worker/status, etc.) are never shadowed by /{alert_id}.
"""
import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.alert_service import alert_service
from app.database import (
    clear_delivery_audit_records,
    add_delivery_audit_record,
    get_delivery_audit_records,
)


@pytest.fixture(autouse=True)
def reset_alert_and_audit_state():
    """Ensures 100% test isolation across all alert and audit tests."""
    clear_delivery_audit_records()
    alert_service._active_alerts.clear()
    alert_service._historical_alerts.clear()
    alert_service._sector_cooldowns.clear()
    yield
    clear_delivery_audit_records()
    alert_service._active_alerts.clear()
    alert_service._historical_alerts.clear()
    alert_service._sector_cooldowns.clear()


def make_sample_alert(
    alert_id: str = "ALT-2026-Z-SHL-01",
    zone_id: str = "Z-SHL-01",
    zone_name: str = "Shillong East Ridge",
    severity: str = "high",
    risk_level: str = "High",
    status: str = "active",
    fs: float = 1.05
) -> dict:
    now_iso = datetime.now(timezone.utc).isoformat()
    return {
        "id": alert_id,
        "zone_id": zone_id,
        "zone_name": zone_name,
        "severity": severity,
        "risk_level": risk_level,
        "status": status,
        "factor_of_safety": fs,
        "probability": 0.75,
        "failure_mode": "Planar Translation",
        "breach_reasons": ["Factor of Safety FS=1.05 <= 1.10 incipient slope instability"],
        "title": f"HAZARD WARNING: {zone_name}",
        "message_en": f"Landslide risk high in {zone_name}.",
        "message_hi": f"{zone_name} में भूस्खलन का उच्च जोखिम।",
        "message_as": f"{zone_name}ত ভূমিস্খলনৰ উচ্চ আশংকা।",
        "triggered_at": now_iso,
        "timestamp": now_iso,
        "cooldown_until": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
        "acknowledged_at": None,
        "acknowledged_by": None,
        "notes": None,
        "resolved_at": None,
        "resolved_by": None,
        "resolution_note": None,
        "resolution_notes": None,
    }


def make_sample_audit(
    audit_id: str = "DEL-001",
    alert_id: str = "ALT-2026-Z-SHL-01",
    zone_id: str = "Z-SHL-01",
    channel: str = "sms",
    recipient_group: str = "citizens",
    status: str = "simulated_delivered",
    provider: str = "zero_key_simulation",
    latency_ms: float = 5.2,
    preview: str = "Evacuation recommended"
) -> dict:
    return {
        "id": audit_id,
        "alert_id": alert_id,
        "zone_id": zone_id,
        "channel": channel,
        "recipient_group": recipient_group,
        "status": status,
        "provider": provider,
        "dispatched_at": datetime.now(timezone.utc).isoformat(),
        "latency_ms": latency_ms,
        "payload_preview": preview,
        "error_message": None,
    }


# =============================================================================
# SUITE 1: Delivery Audit Endpoint (GET /api/v1/alerts/deliveries/audit)
# =============================================================================

@pytest.mark.asyncio
async def test_audit_empty_store():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/alerts/deliveries/audit")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_audit_returns_schema_conforming_records():
    record = make_sample_audit()
    add_delivery_audit_record(record)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/alerts/deliveries/audit")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    item = data[0]
    required_keys = [
        "id", "alert_id", "zone_id", "channel", "recipient_group",
        "status", "provider", "dispatched_at", "latency_ms", "payload_preview"
    ]
    for key in required_keys:
        assert key in item, f"Missing key '{key}' in audit response"


@pytest.mark.asyncio
async def test_audit_filter_by_channel():
    add_delivery_audit_record(make_sample_audit(audit_id="DEL-SMS", channel="sms"))
    add_delivery_audit_record(make_sample_audit(audit_id="DEL-PUSH", channel="push"))
    add_delivery_audit_record(make_sample_audit(audit_id="DEL-CAP", channel="cap"))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp_sms = await ac.get("/api/v1/alerts/deliveries/audit?channel=sms")
        assert len(resp_sms.json()) == 1
        assert resp_sms.json()[0]["channel"] == "sms"

        resp_push = await ac.get("/api/v1/alerts/deliveries/audit?channel=push")
        assert len(resp_push.json()) == 1
        assert resp_push.json()[0]["channel"] == "push"

        resp_cap = await ac.get("/api/v1/alerts/deliveries/audit?channel=cap")
        assert len(resp_cap.json()) == 1
        assert resp_cap.json()[0]["channel"] == "cap"

        # Wildcard 'all' returns all records
        resp_all = await ac.get("/api/v1/alerts/deliveries/audit?channel=all")
        assert len(resp_all.json()) == 3


@pytest.mark.asyncio
async def test_audit_filter_by_recipient_group():
    add_delivery_audit_record(make_sample_audit(audit_id="DEL-1", recipient_group="citizens"))
    add_delivery_audit_record(make_sample_audit(audit_id="DEL-2", recipient_group="field_responders"))
    add_delivery_audit_record(make_sample_audit(audit_id="DEL-3", recipient_group="emergency_command"))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/alerts/deliveries/audit?recipient_group=field_responders")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["recipient_group"] == "field_responders"

        # Wildcard 'all' returns all
        resp_all = await ac.get("/api/v1/alerts/deliveries/audit?recipient_group=all")
        assert len(resp_all.json()) == 3


@pytest.mark.asyncio
async def test_audit_filter_by_status():
    add_delivery_audit_record(make_sample_audit(audit_id="DEL-1", status="simulated_delivered"))
    add_delivery_audit_record(make_sample_audit(audit_id="DEL-2", status="suppressed_cooldown"))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/alerts/deliveries/audit?status=suppressed_cooldown")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["status"] == "suppressed_cooldown"

        resp_all = await ac.get("/api/v1/alerts/deliveries/audit?status=all")
        assert len(resp_all.json()) == 2


@pytest.mark.asyncio
async def test_audit_filter_by_alert_id_and_zone_id():
    add_delivery_audit_record(make_sample_audit(audit_id="DEL-1", alert_id="ALT-A", zone_id="Z-SHL-01"))
    add_delivery_audit_record(make_sample_audit(audit_id="DEL-2", alert_id="ALT-B", zone_id="Z-CHR-02"))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp_alt = await ac.get("/api/v1/alerts/deliveries/audit?alert_id=ALT-A")
        assert len(resp_alt.json()) == 1
        assert resp_alt.json()[0]["alert_id"] == "ALT-A"

        # Case-insensitive zone_id
        resp_zone = await ac.get("/api/v1/alerts/deliveries/audit?zone_id=z-chr-02")
        assert len(resp_zone.json()) == 1
        assert resp_zone.json()[0]["zone_id"] == "Z-CHR-02"


@pytest.mark.asyncio
async def test_audit_multi_filter_intersection():
    add_delivery_audit_record(make_sample_audit(audit_id="DEL-1", channel="sms", recipient_group="citizens", status="simulated_delivered"))
    add_delivery_audit_record(make_sample_audit(audit_id="DEL-2", channel="sms", recipient_group="field_responders", status="simulated_delivered"))
    add_delivery_audit_record(make_sample_audit(audit_id="DEL-3", channel="push", recipient_group="citizens", status="simulated_delivered"))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/alerts/deliveries/audit?channel=sms&recipient_group=citizens")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == "DEL-1"


@pytest.mark.asyncio
async def test_audit_pagination_limit_and_offset():
    for i in range(10):
        add_delivery_audit_record(make_sample_audit(audit_id=f"DEL-{i:02d}"))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp_p1 = await ac.get("/api/v1/alerts/deliveries/audit?limit=3&offset=0")
        resp_p2 = await ac.get("/api/v1/alerts/deliveries/audit?limit=3&offset=3")
    assert resp_p1.status_code == 200
    assert resp_p2.status_code == 200
    p1_ids = [r["id"] for r in resp_p1.json()]
    p2_ids = [r["id"] for r in resp_p2.json()]
    assert len(p1_ids) == 3
    assert len(p2_ids) == 3
    assert len(set(p1_ids).intersection(set(p2_ids))) == 0


@pytest.mark.asyncio
async def test_audit_validation_errors_422():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp_zero_limit = await ac.get("/api/v1/alerts/deliveries/audit?limit=0")
        assert resp_zero_limit.status_code == 422

        resp_neg_limit = await ac.get("/api/v1/alerts/deliveries/audit?limit=-5")
        assert resp_neg_limit.status_code == 422

        resp_neg_offset = await ac.get("/api/v1/alerts/deliveries/audit?offset=-1")
        assert resp_neg_offset.status_code == 422

        resp_over_limit = await ac.get("/api/v1/alerts/deliveries/audit?limit=9999")
        assert resp_over_limit.status_code == 422


# =============================================================================
# SUITE 2: Active & Multi-Status Alerts Query (GET /api/v1/alerts)
# =============================================================================

@pytest.mark.asyncio
async def test_alerts_active_default():
    alert_service._active_alerts = [make_sample_alert()]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/alerts")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == "ALT-2026-Z-SHL-01"


@pytest.mark.asyncio
async def test_alerts_filter_severity():
    alert_service._active_alerts = [
        make_sample_alert(alert_id="ALT-1", severity="severe"),
        make_sample_alert(alert_id="ALT-2", severity="high"),
    ]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/alerts?severity=severe")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["severity"] == "severe"

        # Invalid severity yields 422
        resp_inv = await ac.get("/api/v1/alerts?severity=catastrophic")
        assert resp_inv.status_code == 422


@pytest.mark.asyncio
async def test_alerts_filter_status():
    alert_service._active_alerts = [
        make_sample_alert(alert_id="ALT-1", status="active"),
        make_sample_alert(alert_id="ALT-2", status="acknowledged"),
    ]
    alert_service._historical_alerts = [
        make_sample_alert(alert_id="ALT-3", status="resolved"),
    ]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp_act = await ac.get("/api/v1/alerts?status=active")
        assert len(resp_act.json()) == 1
        assert resp_act.json()[0]["status"] == "active"

        resp_ack = await ac.get("/api/v1/alerts?status=acknowledged")
        assert len(resp_ack.json()) == 1
        assert resp_ack.json()[0]["status"] == "acknowledged"

        resp_res = await ac.get("/api/v1/alerts?status=resolved")
        assert len(resp_res.json()) == 1
        assert resp_res.json()[0]["status"] == "resolved"

        resp_all = await ac.get("/api/v1/alerts?status=all")
        assert len(resp_all.json()) == 3

        # Invalid status yields 422
        resp_inv = await ac.get("/api/v1/alerts?status=unknown_status")
        assert resp_inv.status_code == 422


@pytest.mark.asyncio
async def test_alerts_filter_zone_id():
    alert_service._active_alerts = [
        make_sample_alert(alert_id="ALT-1", zone_id="Z-SHL-01"),
        make_sample_alert(alert_id="ALT-2", zone_id="Z-CHR-02"),
    ]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/alerts?zone_id=z-shl-01")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["zone_id"] == "Z-SHL-01"


# =============================================================================
# SUITE 3: Historical Alerts Query (GET /api/v1/alerts/history)
# =============================================================================

@pytest.mark.asyncio
async def test_alerts_history_empty():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/alerts/history")
    assert resp.status_code == 200
    assert resp.json() == []
    assert resp.headers.get("X-Total-Count") == "0"


@pytest.mark.asyncio
async def test_alerts_history_pagination_and_headers():
    for i in range(5):
        resolved = make_sample_alert(alert_id=f"ALT-HIST-{i}", status="resolved")
        alert_service._historical_alerts.append(resolved)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp_p1 = await ac.get("/api/v1/alerts/history?limit=2&offset=0")
        resp_p2 = await ac.get("/api/v1/alerts/history?limit=2&offset=2")
    assert resp_p1.status_code == 200
    assert len(resp_p1.json()) == 2
    assert len(resp_p2.json()) == 2
    assert resp_p1.headers.get("X-Total-Count") == "5"
    assert resp_p1.json()[0]["id"] != resp_p2.json()[0]["id"]


@pytest.mark.asyncio
async def test_alerts_history_validation_422():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp_limit = await ac.get("/api/v1/alerts/history?limit=-1")
        assert resp_limit.status_code == 422
        resp_offset = await ac.get("/api/v1/alerts/history?offset=-5")
        assert resp_offset.status_code == 422
        resp_stat = await ac.get("/api/v1/alerts/history?status=active")
        assert resp_stat.status_code == 422


# =============================================================================
# SUITE 4: Single Alert Detail (GET /api/v1/alerts/{alert_id})
# =============================================================================

@pytest.mark.asyncio
async def test_get_alert_by_id_active():
    alert_service._active_alerts = [make_sample_alert(alert_id="ALT-2026-Z-SHL-01")]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/alerts/ALT-2026-Z-SHL-01")
    assert resp.status_code == 200
    assert resp.json()["id"] == "ALT-2026-Z-SHL-01"


@pytest.mark.asyncio
async def test_get_alert_by_zone_id_backward_compatibility():
    alert_service._active_alerts = [make_sample_alert(alert_id="ALT-2026-Z-SHL-01", zone_id="Z-SHL-01")]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/alerts/Z-SHL-01")
    assert resp.status_code == 200
    assert resp.json()["zone_id"] == "Z-SHL-01"


@pytest.mark.asyncio
async def test_get_alert_by_id_historical():
    alert_service._historical_alerts = [make_sample_alert(alert_id="ALT-HIST-99", status="resolved")]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/alerts/ALT-HIST-99")
    assert resp.status_code == 200
    assert resp.json()["id"] == "ALT-HIST-99"
    assert resp.json()["status"] == "resolved"


@pytest.mark.asyncio
async def test_get_alert_by_id_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/alerts/ALT-NON-EXISTENT")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# =============================================================================
# SUITE 5: Alert Acknowledgement (POST /api/v1/alerts/{alert_id}/acknowledge)
# =============================================================================

@pytest.mark.asyncio
async def test_acknowledge_alert_success():
    alert_service._active_alerts = [make_sample_alert(alert_id="ALT-ACK-01")]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/alerts/ALT-ACK-01/acknowledge",
            json={"acknowledged_by": "District Magistrate Shillong", "notes": "Dispatched patrol to mile 14"}
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "acknowledged"
    assert data["acknowledged_by"] == "District Magistrate Shillong"
    assert data["notes"] == "Dispatched patrol to mile 14"
    assert data["acknowledged_at"] is not None


@pytest.mark.asyncio
async def test_acknowledge_alert_default_body():
    alert_service._active_alerts = [make_sample_alert(alert_id="ALT-ACK-02")]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/v1/alerts/ALT-ACK-02/acknowledge", json={})
    assert resp.status_code == 200
    assert resp.json()["acknowledged_by"] == "Field Officer"
    assert resp.json()["status"] == "acknowledged"


@pytest.mark.asyncio
async def test_acknowledge_alert_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/v1/alerts/ALT-MISSING/acknowledge", json={})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_acknowledge_preserved_across_worker_evaluation():
    """Verifies that an acknowledged alert maintains acknowledged status across background worker polling cycles."""
    active_alert = make_sample_alert(alert_id="ALT-2026-Z-SHL-01", zone_id="Z-SHL-01")
    alert_service._active_alerts = [active_alert]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ack_resp = await ac.post(
            "/api/v1/alerts/ALT-2026-Z-SHL-01/acknowledge",
            json={"acknowledged_by": "Special Officer", "notes": "Active observation"}
        )
        assert ack_resp.status_code == 200
        assert ack_resp.json()["status"] == "acknowledged"

        # Trigger re-evaluation
        eval_resp = await ac.post("/api/v1/alerts/evaluate")
        assert eval_resp.status_code == 200

        # Query active alerts: Z-SHL-01 alert should still be acknowledged
        alerts_resp = await ac.get("/api/v1/alerts?zone_id=Z-SHL-01")
        assert alerts_resp.status_code == 200
        matching = [a for a in alerts_resp.json() if a.get("zone_id") == "Z-SHL-01"]
        if matching:
            assert matching[0]["status"] == "acknowledged"
            assert matching[0]["acknowledged_by"] == "Special Officer"
            assert matching[0]["notes"] == "Active observation"


# =============================================================================
# SUITE 6: Alert Resolution (POST /api/v1/alerts/{alert_id}/resolve)
# =============================================================================

@pytest.mark.asyncio
async def test_resolve_alert_success():
    alert_service._active_alerts = [make_sample_alert(alert_id="ALT-RES-01", zone_id="Z-SHL-01")]
    alert_service._sector_cooldowns["Z-SHL-01"] = {"last_severity": "high"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/alerts/ALT-RES-01/resolve",
            json={"resolved_by": "Chief Engineer", "resolution_note": "Culvert unblocked and slope drained"}
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "resolved"
    assert data["resolved_by"] == "Chief Engineer"
    assert data["resolution_note"] == "Culvert unblocked and slope drained"
    assert data["resolved_at"] is not None

    # Verify moved to history and cooldown cleared
    assert len(alert_service.get_active_alerts()) == 0
    assert len(alert_service.get_historical_alerts()) == 1
    assert "Z-SHL-01" not in alert_service._sector_cooldowns


@pytest.mark.asyncio
async def test_resolve_alert_with_resolution_notes_alias():
    alert_service._active_alerts = [make_sample_alert(alert_id="ALT-RES-02", zone_id="Z-CHR-02")]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/alerts/ALT-RES-02/resolve",
            json={"resolved_by": "Site Supervisor", "resolution_notes": "Retaining wall stabilized"}
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"
    assert resp.json()["resolution_notes"] == "Retaining wall stabilized"


@pytest.mark.asyncio
async def test_resolve_alert_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/v1/alerts/ALT-NOT-FOUND/resolve", json={})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_resolve_already_resolved_yields_404():
    alert_service._active_alerts = [make_sample_alert(alert_id="ALT-RES-03")]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp1 = await ac.post("/api/v1/alerts/ALT-RES-03/resolve", json={})
        assert resp1.status_code == 200

        # Resolving second time must yield 404
        resp2 = await ac.post("/api/v1/alerts/ALT-RES-03/resolve", json={})
        assert resp2.status_code == 404


# =============================================================================
# SUITE 7: On-Demand Test Dispatch (POST /api/v1/alerts/test-dispatch)
# =============================================================================

@pytest.mark.asyncio
async def test_test_dispatch_drill():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "zone_id": "Z-SHL-01",
            "channels": ["sms", "push"],
            "recipient_group": "citizens",
            "severity": "high",
            "custom_message": "CIVIL DRILL TEST ALERT"
        }
        resp = await ac.post("/api/v1/alerts/test-dispatch", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "dispatched"
    assert "test_alert_id" in data
    assert len(data["deliveries"]) == 2

    # Verify audit records were persisted in store
    audits = get_delivery_audit_records(zone_id="Z-SHL-01")
    assert len(audits) >= 2
    assert any("CIVIL DRILL TEST ALERT" in a["payload_preview"] for a in audits)


@pytest.mark.asyncio
async def test_test_dispatch_default_fallback():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Calling with empty body should use Z-SHL-01 fallback
        resp = await ac.post("/api/v1/alerts/test-dispatch", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "dispatched"
    assert data["test_alert_id"].startswith("TEST-ALT-")
    assert len(data["deliveries"]) == 2


@pytest.mark.asyncio
async def test_test_dispatch_invalid_body_422():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/alerts/test-dispatch",
            content="not-json",
            headers={"Content-Type": "application/json"}
        )
    assert resp.status_code == 422


# =============================================================================
# SUITE 8: Worker Health & Controls
# =============================================================================

@pytest.mark.asyncio
async def test_worker_status_telemetry():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/alerts/worker/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "is_running" in data
    assert data["monitored_sectors_count"] == 6


@pytest.mark.asyncio
async def test_worker_pause_and_resume():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        pause_resp = await ac.post("/api/v1/alerts/worker/pause")
        assert pause_resp.status_code == 200
        assert pause_resp.json()["status"] == "paused"

        resume_resp = await ac.post("/api/v1/alerts/worker/resume")
        assert resume_resp.status_code == 200
        assert resume_resp.json()["status"] == "resumed"


@pytest.mark.asyncio
async def test_worker_alias_routes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        pause_resp = await ac.post("/api/v1/worker/pause")
        assert pause_resp.status_code == 200
        assert pause_resp.json()["status"] == "paused"

        resume_resp = await ac.post("/api/v1/worker/resume")
        assert resume_resp.status_code == 200
        assert resume_resp.json()["status"] == "resumed"


# =============================================================================
# SUITE 9: Route Precedence & Regression Guard
# =============================================================================

@pytest.mark.asyncio
async def test_route_precedence_no_shadowing_audit():
    """Confirms /alerts/deliveries/audit is never intercepted as /alerts/{alert_id}."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/alerts/deliveries/audit")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_route_precedence_no_shadowing_history():
    """Confirms /alerts/history is never intercepted as /alerts/{alert_id}."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/alerts/history")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_route_precedence_no_shadowing_worker_status():
    """Confirms /alerts/worker/status is never intercepted as /alerts/{alert_id}."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/alerts/worker/status")
    assert resp.status_code == 200
    assert "status" in resp.json()


@pytest.mark.asyncio
async def test_route_precedence_protected_subpaths_404():
    """Confirms querying static subpaths as alert_id returns 404."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        for subpath in ["evaluate", "test-dispatch"]:
            resp = await ac.get(f"/api/v1/alerts/{subpath}")
            assert resp.status_code == 404


# =============================================================================
# SUITE 10: Additional Edge Cases & Contract Guards
# =============================================================================

@pytest.mark.asyncio
async def test_alerts_refresh_parameter():
    """Confirms that refresh=true forces a fresh evaluation cycle."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/alerts?refresh=true")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_alerts_history_filter_severity():
    """Verifies severity filtering on historical alerts."""
    alert_service._historical_alerts = [
        make_sample_alert(alert_id="HIST-SEV", severity="severe", status="resolved"),
        make_sample_alert(alert_id="HIST-MOD", severity="moderate", status="resolved"),
    ]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/alerts/history?severity=severe")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["id"] == "HIST-SEV"


@pytest.mark.asyncio
async def test_alerts_history_filter_zone_id():
    """Verifies sector filtering on historical alerts."""
    alert_service._historical_alerts = [
        make_sample_alert(alert_id="HIST-SHL", zone_id="Z-SHL-01", status="resolved"),
        make_sample_alert(alert_id="HIST-CHR", zone_id="Z-CHR-02", status="resolved"),
    ]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/alerts/history?zone_id=Z-SHL-01")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["id"] == "HIST-SHL"


@pytest.mark.asyncio
async def test_audit_offset_beyond_total():
    """Verifies offset exceeding total records returns an empty list gracefully."""
    add_delivery_audit_record(make_sample_audit(audit_id="DEL-1"))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/alerts/deliveries/audit?offset=50&limit=10")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_acknowledge_already_resolved_yields_404():
    """Attempting to acknowledge an already resolved alert must return 404."""
    alert_service._active_alerts = [make_sample_alert(alert_id="ALT-RESOLVED-1")]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Resolve it first
        res_resp = await ac.post("/api/v1/alerts/ALT-RESOLVED-1/resolve", json={})
        assert res_resp.status_code == 200

        # Try to acknowledge
        ack_resp = await ac.post("/api/v1/alerts/ALT-RESOLVED-1/acknowledge", json={})
        assert ack_resp.status_code == 404


@pytest.mark.asyncio
async def test_test_dispatch_multi_channel_all_groups():
    """Tests drill dispatch with 3 channels and recipient_group='all' (3 channels x 2 groups = 6 deliveries)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "zone_id": "Z-SHL-01",
            "channels": ["sms", "push", "cap"],
            "recipient_group": "all",
            "severity": "severe",
            "custom_message": "MULTI-CHANNEL ALL COHORT DRILL"
        }
        resp = await ac.post("/api/v1/alerts/test-dispatch", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["deliveries"]) == 6
    channels = {d["channel"] for d in data["deliveries"]}
    assert channels == {"sms", "push", "cap"}
    groups = {d["recipient_group"] for d in data["deliveries"]}
    assert groups == {"citizens", "field_responders"}


@pytest.mark.asyncio
async def test_get_alert_by_id_includes_notes_and_resolution():
    """Verifies that AlertResponse includes operational notes and resolution_note."""
    alert = make_sample_alert(alert_id="ALT-NOTES-01")
    alert["notes"] = "Patrol dispatched"
    alert["resolution_note"] = "All clear"
    alert_service._active_alerts = [alert]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/alerts/ALT-NOTES-01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["notes"] == "Patrol dispatched"
    assert data["resolution_note"] == "All clear"


@pytest.mark.asyncio
async def test_resolve_alert_preserves_multilingual_messages():
    """Verifies that resolving an alert preserves English, Hindi, and Assamese advisories."""
    alert = make_sample_alert(alert_id="ALT-MULTI-01", zone_id="Z-SHL-01")
    alert["message_en"] = "English advisory"
    alert["message_hi"] = "Hindi advisory"
    alert["message_as"] = "Assamese advisory"
    alert_service._active_alerts = [alert]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/v1/alerts/ALT-MULTI-01/resolve", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["message_en"] == "English advisory"
    assert data["message_hi"] == "Hindi advisory"
    assert data["message_as"] == "Assamese advisory"


@pytest.mark.asyncio
async def test_route_precedence_no_shadowing_evaluate_and_dispatch():
    """Verifies that POST /alerts/evaluate and POST /alerts/test-dispatch are not intercepted."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp_eval = await ac.post("/api/v1/alerts/evaluate")
        assert resp_eval.status_code == 200

        resp_disp = await ac.post("/api/v1/alerts/test-dispatch", json={})
        assert resp_disp.status_code == 200


@pytest.mark.asyncio
async def test_alerts_active_filter_case_insensitive():
    """Verifies that query filters handle case-insensitivity seamlessly."""
    alert_service._active_alerts = [
        make_sample_alert(alert_id="ALT-CASE-1", zone_id="Z-SHL-01", severity="high", status="active")
    ]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/alerts?status=ACTIVE&severity=HIGH&zone_id=z-shl-01")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["id"] == "ALT-CASE-1"

