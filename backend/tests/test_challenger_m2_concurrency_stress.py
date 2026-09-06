"""
Adversarial Concurrency & Worker Polling Race Condition Stress Test Suite
Milestone 2 Challenger 2 (Lifecycle Concurrency Challenger)

Evaluates:
1. Concurrency on Acknowledge & Resolve:
   - 50 concurrent acknowledge requests on a single alert (API & thread safety).
   - 50 concurrent resolve requests on a single alert (exactly 1 succeeds, 49 get 404, 0 duplicates).
   - Competing threads and HTTP races between acknowledge and resolve.
2. Worker Polling vs. Acknowledged State Race:
   - 50ms fast background worker polling vs mid-poll and continuous alert acknowledgement.
   - Verification across >= 10 worker polling cycles that alert NEVER reverts to "active".
   - Multi-zone acknowledgement preservation across worker polling cycles.
3. Delivery Audit Store Pagination Stress:
   - Flooding store with 500+ records.
   - Boundary condition pagination (offset 0, 499, 500, 1000) verifying zero IndexError.
   - 100 concurrent paginated queries with mixed filters.
   - Heavy concurrent writes (inserts) interleaved with concurrent paginated reads.
   - Historical alert pagination concurrency and X-Total-Count header consistency.
"""
import pytest
import asyncio
import random
import concurrent.futures
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.alert_service import alert_service, AlertService
from app.database import (
    clear_delivery_audit_records,
    add_delivery_audit_record,
    get_delivery_audit_records,
    _DELIVERY_AUDIT_STORE
)


@pytest.fixture(autouse=True)
def clean_system_state():
    """Ensures test isolation across each stress test execution."""
    clear_delivery_audit_records()
    alert_service._active_alerts.clear()
    alert_service._historical_alerts.clear()
    alert_service._sector_cooldowns.clear()
    yield
    clear_delivery_audit_records()
    alert_service._active_alerts.clear()
    alert_service._historical_alerts.clear()
    alert_service._sector_cooldowns.clear()


def make_test_alert(
    alert_id: str = "ALT-STRESS-01",
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
        "probability": 0.80,
        "failure_mode": "Planar Translation Stress",
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


# =============================================================================
# SUITE 1: Concurrency on Acknowledge & Resolve
# =============================================================================

@pytest.mark.asyncio
async def test_adversarial_50_concurrent_acknowledges_single_alert():
    """
    Stress-tests sending 50 concurrent acknowledge requests for the same alert via HTTP API.
    Verifies:
    - Zero crashes (0 500 errors).
    - Status transitions cleanly to 'acknowledged'.
    - Active store contains exactly 1 alert (zero duplicate allocations).
    - Consistent, valid ISO 8601 UTC timestamp.
    """
    alert = make_test_alert(alert_id="ALT-50-ACK", zone_id="Z-SHL-01")
    alert_service._active_alerts = [alert]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        tasks = [
            ac.post(
                "/api/v1/alerts/ALT-50-ACK/acknowledge",
                json={"acknowledged_by": f"Field Officer {i}", "notes": f"Patrol unit {i} dispatched"}
            )
            for i in range(50)
        ]
        responses = await asyncio.gather(*tasks)

    status_codes = [r.status_code for r in responses]
    assert all(code == 200 for code in status_codes), f"Unexpected status codes: {set(status_codes)}"

    # In-memory alert store integrity check
    active_alerts = alert_service.get_active_alerts()
    assert len(active_alerts) == 1, f"Expected 1 active alert, found {len(active_alerts)}"
    final = active_alerts[0]
    assert final["status"] == "acknowledged"
    assert final["acknowledged_at"] is not None
    # Validate timestamp parses as valid ISO datetime
    ack_dt = datetime.fromisoformat(final["acknowledged_at"])
    assert ack_dt.tzinfo is not None, "Timestamp must be timezone-aware"


def test_adversarial_50_concurrent_threads_acknowledging():
    """
    Directly tests thread safety of alert_service.acknowledge_alert() across 50 OS threads
    competing on the same alert record.
    """
    service = AlertService()
    service._active_alerts = [make_test_alert(alert_id="ALT-THREAD-ACK")]

    def ack_call(idx: int):
        return service.acknowledge_alert(
            alert_id="ALT-THREAD-ACK",
            acknowledged_by=f"ThreadOfficer-{idx}",
            notes=f"Thread note {idx}"
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(ack_call, i) for i in range(50)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == 50
    assert all(r is not None for r in results)
    assert len(service.get_active_alerts()) == 1
    assert service.get_active_alerts()[0]["status"] == "acknowledged"


def test_adversarial_competing_threads_ack_vs_resolve():
    """
    Simultaneously executes acknowledge and resolve from competing OS threads across 100 iterations.
    Verifies:
    - Alert always cleanly resolves and moves into history.
    - Zero active alerts remain after resolve completes.
    - Historical store contains exactly 1 record with status 'resolved'.
    - Zero orphaned state or list corruption.
    """
    for iteration in range(100):
        service = AlertService()
        test_id = f"ALT-RACE-{iteration}"
        service._active_alerts = [make_test_alert(alert_id=test_id)]

        def do_ack():
            return service.acknowledge_alert(test_id, acknowledged_by="RacerAck")

        def do_res():
            return service.resolve_alert(test_id, resolved_by="RacerRes", note="Stabilized")

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(do_ack)
            f2 = executor.submit(do_res)
            concurrent.futures.wait([f1, f2])

        active = service.get_active_alerts()
        history = service.get_historical_alerts()

        assert len(active) == 0, f"Iteration {iteration}: Active store must be empty, had {len(active)}"
        assert len(history) == 1, f"Iteration {iteration}: History store must have 1, had {len(history)}"
        assert history[0]["status"] == "resolved"


@pytest.mark.asyncio
async def test_adversarial_50_concurrent_resolves_single_alert():
    """
    Stress-tests 50 concurrent resolve requests for the exact same alert.
    Verifies:
    - Exactly 1 request succeeds with 200 OK.
    - Exactly 49 requests return 404 Not Found ('Alert not found or already resolved').
    - Historical store contains exactly 1 resolved entry (0 duplicate insertions).
    """
    alert = make_test_alert(alert_id="ALT-RESOLVE-STRESS", zone_id="Z-SHL-01")
    alert_service._active_alerts = [alert]
    alert_service._sector_cooldowns["Z-SHL-01"] = {"last_severity": "high"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        tasks = [
            ac.post(
                "/api/v1/alerts/ALT-RESOLVE-STRESS/resolve",
                json={"resolved_by": f"Admin-{i}", "resolution_note": f"Closure {i}"}
            )
            for i in range(50)
        ]
        responses = await asyncio.gather(*tasks)

    status_codes = [r.status_code for r in responses]
    assert status_codes.count(200) == 1, f"Expected exactly 1 200 OK, got {status_codes.count(200)}"
    assert status_codes.count(404) == 49, f"Expected 49 404 Not Found, got {status_codes.count(404)}"
    assert len(alert_service.get_active_alerts()) == 0
    assert len(alert_service.get_historical_alerts()) == 1
    assert "Z-SHL-01" not in alert_service._sector_cooldowns


@pytest.mark.asyncio
async def test_adversarial_http_race_50_acks_vs_1_resolve():
    """
    Races 50 concurrent HTTP acknowledge requests against 1 HTTP resolve request.
    Verifies:
    - Resolve completes cleanly.
    - Historical store has 1 resolved alert.
    - Active store has 0 alerts.
    - Acknowledges arriving after resolve cleanly return 404 with no 500 internal errors.
    """
    alert = make_test_alert(alert_id="ALT-HTTP-RACE-50", zone_id="Z-SHL-01")
    alert_service._active_alerts = [alert]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ack_tasks = [
            ac.post(
                "/api/v1/alerts/ALT-HTTP-RACE-50/acknowledge",
                json={"acknowledged_by": f"Officer-{i}"}
            )
            for i in range(50)
        ]
        resolve_task = ac.post(
            "/api/v1/alerts/ALT-HTTP-RACE-50/resolve",
            json={"resolved_by": "Senior Commander", "resolution_note": "Risk cleared"}
        )

        all_tasks = ack_tasks + [resolve_task]
        random.shuffle(all_tasks)
        responses = await asyncio.gather(*all_tasks)

    codes = [r.status_code for r in responses]
    assert all(c in (200, 404) for c in codes), f"Unexpected status codes: {set(codes)}"
    assert len(alert_service.get_active_alerts()) == 0
    assert len(alert_service.get_historical_alerts()) == 1
    assert alert_service.get_historical_alerts()[0]["status"] == "resolved"


# =============================================================================
# SUITE 2: Worker Polling vs. Acknowledged State Race
# =============================================================================

@pytest.mark.asyncio
async def test_adversarial_worker_50ms_polling_vs_acknowledged_state_10_cycles():
    """
    R1/R2 Critical Race Condition Test:
    - Starts background monitoring worker with high-frequency 50ms polling interval.
    - Acknowledges an active alert via HTTP API while the worker is actively polling.
    - Lets the worker poll for at least 10 consecutive cycles.
    - Verifies the alert REMAINS status='acknowledged' and NEVER reverts to 'active'.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Populate initial alerts via on-demand evaluation
        eval_resp = await ac.post("/api/v1/alerts/evaluate")
        assert eval_resp.status_code == 200
        alerts = eval_resp.json()["alerts"]
        assert len(alerts) > 0
        target = alerts[0]
        target_id = target["id"]
        target_zone = target["zone_id"]

        # Start worker at 50ms (0.05s) interval
        started = await alert_service.start_monitoring_worker(interval_seconds=0.05)
        assert started is True

        try:
            # Let worker execute 2 initial polling cycles
            await asyncio.sleep(0.12)
            polls_before = alert_service._poll_count

            # Acknowledge the alert via HTTP endpoint
            ack_resp = await ac.post(
                f"/api/v1/alerts/{target_id}/acknowledge",
                json={"acknowledged_by": "Incident Commander", "notes": "Active field deployment"}
            )
            assert ack_resp.status_code == 200
            assert ack_resp.json()["status"] == "acknowledged"

            # Wait for worker to complete at least 10 subsequent polling cycles
            target_polls = alert_service._poll_count + 10
            wait_iterations = 0
            while alert_service._poll_count < target_polls and wait_iterations < 100:
                await asyncio.sleep(0.02)
                wait_iterations += 1

            assert alert_service._poll_count >= target_polls, (
                f"Worker only reached {alert_service._poll_count} polls, wanted {target_polls}"
            )
        finally:
            await alert_service.stop_monitoring_worker()

        # Empirical Verification 1: Single Alert API
        detail_resp = await ac.get(f"/api/v1/alerts/{target_id}")
        assert detail_resp.status_code == 200
        detail_data = detail_resp.json()
        assert detail_data["status"] == "acknowledged", (
            f"Alert reverted to '{detail_data['status']}' after 10 worker polling cycles!"
        )
        assert detail_data["acknowledged_by"] == "Incident Commander"
        assert detail_data["notes"] == "Active field deployment"

        # Empirical Verification 2: Active Alerts Filter
        active_resp = await ac.get("/api/v1/alerts?status=active")
        assert active_resp.status_code == 200
        active_ids = [a["id"] for a in active_resp.json()]
        assert target_id not in active_ids, f"Target alert {target_id} mistakenly appeared in status=active pool"

        # Empirical Verification 3: Acknowledged Alerts Filter
        acked_resp = await ac.get("/api/v1/alerts?status=acknowledged")
        assert acked_resp.status_code == 200
        acked_ids = [a["id"] for a in acked_resp.json()]
        assert target_id in acked_ids, f"Target alert {target_id} missing from status=acknowledged pool"


@pytest.mark.asyncio
async def test_adversarial_mid_evaluation_ack_injection_10_cycles():
    """
    Adversarially injects an acknowledgement call precisely during the CPU-bound
    risk_engine.predict_risk() execution inside evaluate_and_dispatch_alerts().
    Verifies that the alert maintains status='acknowledged' over 10 worker polling cycles.
    """
    service = alert_service
    eval_resp = await service.evaluate_and_dispatch_alerts()
    assert len(eval_resp) > 0
    target_alert = eval_resp[0]
    target_id = target_alert["id"]

    original_predict = service.risk_engine.predict_risk
    injected = False

    def wrapped_predict(payload):
        nonlocal injected
        res = original_predict(payload)
        if not injected:
            injected = True
            # Mid-evaluation race injection
            service.acknowledge_alert(
                target_id,
                acknowledged_by="MidEvaluationInterrupter",
                notes="Mid-eval race injection"
            )
        return res

    with patch.object(service.risk_engine, "predict_risk", side_effect=wrapped_predict):
        await service.start_monitoring_worker(interval_seconds=0.05)
        try:
            start_polls = service._poll_count
            while service._poll_count < start_polls + 10:
                await asyncio.sleep(0.02)
        finally:
            await service.stop_monitoring_worker()

    final = service.get_alert_by_id(target_id)
    assert final is not None
    assert final.get("status") == "acknowledged", f"Alert reverted to {final.get('status')}"
    assert final.get("acknowledged_by") == "MidEvaluationInterrupter"
    assert final.get("notes") == "Mid-eval race injection"


@pytest.mark.asyncio
async def test_adversarial_all_sectors_acknowledged_during_continuous_worker_polling():
    """
    Evaluates system behavior when ALL active monitored sectors are acknowledged
    simultaneously during continuous 50ms worker polling.
    Verifies across 10 subsequent cycles that:
    - All monitored sectors retain status='acknowledged'.
    - Zero sectors revert to 'active'.
    - Querying GET /api/v1/alerts?status=active returns empty list.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        eval_resp = await ac.post("/api/v1/alerts/evaluate")
        alerts = eval_resp.json()["alerts"]
        assert len(alerts) >= 6

        await alert_service.start_monitoring_worker(interval_seconds=0.05)
        try:
            await asyncio.sleep(0.1)
            # Concurrently acknowledge all active alerts
            ack_tasks = [
                ac.post(
                    f"/api/v1/alerts/{a['id']}/acknowledge",
                    json={"acknowledged_by": "MultiZoneOperator", "notes": f"Observed {a['zone_id']}"}
                )
                for a in alerts
            ]
            ack_resps = await asyncio.gather(*ack_tasks)
            assert all(r.status_code == 200 for r in ack_resps)

            # Wait 10 polling cycles
            start_polls = alert_service._poll_count
            while alert_service._poll_count < start_polls + 10:
                await asyncio.sleep(0.02)
        finally:
            await alert_service.stop_monitoring_worker()

        # Verify active pool is completely empty
        pure_active = await ac.get("/api/v1/alerts?status=active")
        assert pure_active.status_code == 200
        assert len(pure_active.json()) == 0, f"Expected 0 active alerts, got {len(pure_active.json())}"

        # Verify all alerts in acknowledged pool
        acked_pool = await ac.get("/api/v1/alerts?status=acknowledged")
        assert acked_pool.status_code == 200
        assert len(acked_pool.json()) >= 6
        for alert_item in acked_pool.json():
            assert alert_item["status"] == "acknowledged"
            assert alert_item["acknowledged_by"] == "MultiZoneOperator"


@pytest.mark.asyncio
async def test_adversarial_resolve_during_active_worker_polling():
    """
    Verifies that resolving an alert while the worker is actively polling
    cleanly moves the alert to history without race conditions or deadlock.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        eval_resp = await ac.post("/api/v1/alerts/evaluate")
        alerts = eval_resp.json()["alerts"]
        target_id = alerts[0]["id"]

        await alert_service.start_monitoring_worker(interval_seconds=0.05)
        try:
            await asyncio.sleep(0.08)
            res_resp = await ac.post(
                f"/api/v1/alerts/{target_id}/resolve",
                json={"resolved_by": "Chief Geologist", "resolution_note": "Slope stabilized by drainage"}
            )
            assert res_resp.status_code == 200

            # Let worker poll 5 more times
            await asyncio.sleep(0.25)
        finally:
            await alert_service.stop_monitoring_worker()

        # Verify target_id is preserved in history
        hist_resp = await ac.get("/api/v1/alerts/history")
        assert hist_resp.status_code == 200
        hist_ids = [h["id"] for h in hist_resp.json()]
        assert target_id in hist_ids


# =============================================================================
# SUITE 3: Delivery Audit Store Pagination Stress
# =============================================================================

@pytest.mark.asyncio
async def test_adversarial_delivery_audit_500_records_flood_and_boundary_pagination():
    """
    Floods the in-memory delivery audit store with 500 records and tests exact
    boundary conditions:
    - offset=0, limit=500 -> 500 records
    - offset=499, limit=10 -> exactly 1 record
    - offset=500, limit=50 -> 0 records (empty list, zero IndexError)
    - offset=1000, limit=50 -> 0 records (empty list, zero IndexError)
    - offset=200, limit=50 -> exactly 50 records
    """
    clear_delivery_audit_records()
    zones = ["Z-SHL-01", "Z-SHL-02", "Z-CHR-01", "Z-CHR-02", "Z-MWS-01", "Z-MWS-02"]
    channels = ["sms", "push", "cap"]

    for i in range(500):
        add_delivery_audit_record({
            "id": f"DEL-{i:04d}",
            "alert_id": f"ALT-{i % 20}",
            "zone_id": zones[i % len(zones)],
            "channel": channels[i % len(channels)],
            "recipient_group": "citizens",
            "status": "simulated_delivered",
            "provider": "zero_key_simulation",
            "dispatched_at": "2026-09-03T12:00:00Z",
            "latency_ms": 5.0,
            "payload_preview": f"Stress test audit message {i}"
        })

    assert len(_DELIVERY_AUDIT_STORE) == 500

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Boundary 1: offset=0, limit=500
        r_all = await ac.get("/api/v1/alerts/deliveries/audit?limit=500&offset=0")
        assert r_all.status_code == 200
        assert len(r_all.json()) == 500

        # Boundary 2: offset=499, limit=10 (last single record)
        r_last = await ac.get("/api/v1/alerts/deliveries/audit?limit=10&offset=499")
        assert r_last.status_code == 200
        assert len(r_last.json()) == 1

        # Boundary 3: offset=500, limit=50 (exact end of list)
        r_exact_end = await ac.get("/api/v1/alerts/deliveries/audit?limit=50&offset=500")
        assert r_exact_end.status_code == 200
        assert len(r_exact_end.json()) == 0

        # Boundary 4: offset=1000, limit=50 (beyond list length)
        r_beyond = await ac.get("/api/v1/alerts/deliveries/audit?limit=50&offset=1000")
        assert r_beyond.status_code == 200
        assert len(r_beyond.json()) == 0

        # Boundary 5: offset=200, limit=50
        r_mid = await ac.get("/api/v1/alerts/deliveries/audit?limit=50&offset=200")
        assert r_mid.status_code == 200
        assert len(r_mid.json()) == 50


@pytest.mark.asyncio
async def test_adversarial_delivery_audit_100_concurrent_paginated_queries():
    """
    Executes 100 concurrent asynchronous paginated queries against a 500-record store
    with random limits, offsets, and multi-field filters.
    Verifies:
    - Zero unhandled exceptions or IndexErrors.
    - All return HTTP 200.
    - All return valid DeliveryAuditRecord schemas within limit bounds.
    """
    clear_delivery_audit_records()
    channels = ["sms", "push", "cap"]
    recipients = ["citizens", "field_responders", "emergency_command"]
    statuses = ["simulated_delivered", "delivered", "failed", "suppressed_cooldown"]
    zones = ["Z-SHL-01", "Z-SHL-02", "Z-CHR-01", "Z-CHR-02", "Z-MWS-01", "Z-MWS-02"]

    for i in range(500):
        add_delivery_audit_record({
            "id": f"DEL-{i:04d}",
            "alert_id": f"ALT-{i % 25}",
            "zone_id": zones[i % len(zones)],
            "channel": channels[i % len(channels)],
            "recipient_group": recipients[i % len(recipients)],
            "status": statuses[i % len(statuses)],
            "provider": "zero_key_simulation",
            "dispatched_at": "2026-09-03T12:00:00Z",
            "latency_ms": 4.5,
            "payload_preview": f"Concurrent query audit payload {i}"
        })

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        async def run_query(worker_id: int):
            limit = random.choice([10, 25, 50, 100, 500])
            offset = random.choice([0, 10, 50, 150, 300, 450, 499, 500, 600])
            chan = random.choice(["sms", "push", "cap", "all", None])
            group = random.choice(["citizens", "field_responders", "all", None])
            stat = random.choice(["simulated_delivered", "delivered", "all", None])

            params = [f"limit={limit}", f"offset={offset}"]
            if chan:
                params.append(f"channel={chan}")
            if group:
                params.append(f"recipient_group={group}")
            if stat:
                params.append(f"status={stat}")

            query_url = f"/api/v1/alerts/deliveries/audit?{'&'.join(params)}"
            resp = await ac.get(query_url)
            assert resp.status_code == 200, f"Query {worker_id} failed: {resp.status_code}"
            data = resp.json()
            assert isinstance(data, list)
            assert len(data) <= limit
            return len(data)

        results = await asyncio.gather(*[run_query(i) for i in range(100)])
        assert len(results) == 100


@pytest.mark.asyncio
async def test_adversarial_concurrent_audit_writes_during_paginated_reads():
    """
    Floods 500 baseline records and then executes 100 concurrent asynchronous inserts
    while simultaneously executing 100 concurrent paginated queries.
    Verifies list mutation safety, zero crash, zero memory corruption.
    """
    clear_delivery_audit_records()
    for i in range(500):
        add_delivery_audit_record({
            "id": f"DEL-BASE-{i:04d}",
            "alert_id": "ALT-BASE",
            "zone_id": "Z-SHL-01",
            "channel": "sms",
            "recipient_group": "citizens",
            "status": "simulated_delivered",
            "provider": "zero_key_simulation",
            "dispatched_at": "2026-09-03T12:00:00Z",
            "latency_ms": 3.0,
            "payload_preview": f"Base record {i}"
        })

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        async def insert_worker():
            for j in range(100):
                add_delivery_audit_record({
                    "id": f"DEL-INJECT-{j}",
                    "alert_id": "ALT-INJECT",
                    "zone_id": "Z-CHR-02",
                    "channel": "push",
                    "recipient_group": "field_responders",
                    "status": "simulated_delivered",
                    "provider": "zero_key_simulation",
                    "dispatched_at": "2026-09-03T12:00:00Z",
                    "latency_ms": 2.5,
                    "payload_preview": f"Injected record {j}"
                })
                await asyncio.sleep(0.001)

        async def read_worker(idx: int):
            limit = random.choice([20, 50, 100])
            offset = random.choice([0, 50, 200, 450, 500, 550])
            resp = await ac.get(f"/api/v1/alerts/deliveries/audit?limit={limit}&offset={offset}")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) <= limit
            return len(data)

        insert_task = asyncio.create_task(insert_worker())
        read_tasks = [read_worker(i) for i in range(100)]
        results = await asyncio.gather(*read_tasks)
        await insert_task

        assert len(results) == 100
        # 500 initial + 100 injected = 600 records total
        assert len(_DELIVERY_AUDIT_STORE) == 600


@pytest.mark.asyncio
async def test_adversarial_alert_history_pagination_concurrency():
    """
    Populates 100 historical alerts and executes 50 concurrent paginated requests
    with varying limits and offsets, verifying the X-Total-Count header and pagination slicing.
    """
    for i in range(100):
        alert_service._historical_alerts.append(
            make_test_alert(
                alert_id=f"ALT-HIST-{i:03d}",
                zone_id="Z-SHL-01" if i % 2 == 0 else "Z-CHR-02",
                status="resolved"
            )
        )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        async def page_query(idx: int):
            limit = random.choice([10, 25, 50])
            offset = random.choice([0, 20, 50, 75, 95, 100, 150])
            resp = await ac.get(f"/api/v1/alerts/history?limit={limit}&offset={offset}&status=all")
            assert resp.status_code == 200
            assert resp.headers.get("X-Total-Count") == "100"
            data = resp.json()
            assert len(data) <= limit
            return len(data)

        results = await asyncio.gather(*[page_query(i) for i in range(50)])
        assert len(results) == 50
