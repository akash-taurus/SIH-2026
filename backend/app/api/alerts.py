"""
API Endpoints for Regional Landslide Emergency Alerts, Lifecycle Operations,
Delivery Audit Logs, and Background Worker Telemetry.
"""
from fastapi import APIRouter, Query, HTTPException, Response, status
from typing import List, Dict, Any, Optional
import time
from datetime import datetime, timezone, timedelta

from app.services.alert_service import alert_service
from app.services.notification_service import notification_dispatcher
from app.database import get_risk_zones, get_delivery_audit_records
from app.schemas.alerts import (
    AlertResponse,
    DeliveryAuditRecord,
    TestDispatchRequest,
    TestDispatchResponse,
    AlertAcknowledgeRequest,
    AlertResolveRequest,
    WorkerStatusResponse,
)

router = APIRouter(tags=["Alerts"])

VALID_STATUSES = {"active", "acknowledged", "resolved", "all"}
VALID_SEVERITIES = {"severe", "high", "moderate", "low", "all"}


# =============================================================================
# 1. Active & Multi-Status Alerts Query (GET /alerts)
# =============================================================================
@router.get(
    "/alerts",
    response_model=List[AlertResponse],
    summary="Query emergency alerts",
    description="Returns regional emergency alerts filtered by status, severity, and zone. Defaults to active alerts."
)
async def get_active_alerts(
    status: Optional[str] = Query("active", description="Filter by status: active, acknowledged, resolved, or all"),
    severity: Optional[str] = Query(None, description="Filter by severity: severe, high, moderate, low"),
    zone_id: Optional[str] = Query(None, description="Filter by sector code, e.g. Z-SHL-01"),
    refresh: bool = Query(False, description="Force re-evaluation of all zone risks"),
    max_age_minutes: int = Query(30, description="Cache TTL in minutes before auto-refresh")
) -> List[Dict[str, Any]]:
    norm_status = status.strip().lower() if status else "active"
    if norm_status not in VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{status}'. Must be one of: {', '.join(sorted(VALID_STATUSES))}"
        )
    if severity and severity.strip().lower() not in VALID_SEVERITIES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid severity '{severity}'. Must be one of: {', '.join(sorted(VALID_SEVERITIES))}"
        )

    if refresh or not alert_service.get_active_alerts():
        await alert_service.evaluate_all_zones_and_generate_alerts()

    alert_service.clear_expired_alerts(max_age_minutes)

    if norm_status == "all":
        pool = alert_service.get_active_alerts() + alert_service.get_historical_alerts()
    elif norm_status == "resolved":
        pool = alert_service.get_historical_alerts()
    elif norm_status == "acknowledged":
        pool = [a for a in alert_service.get_active_alerts() if a.get("status", "").lower() == "acknowledged"]
    else:
        # Default 'active'
        pool = [a for a in alert_service.get_active_alerts() if a.get("status", "").lower() == "active"]

    return alert_service.filter_alerts(pool, severity=severity, zone_id=zone_id)


# =============================================================================
# 2. Historical Alerts Query (GET /alerts/history — static subpath before /{alert_id})
# =============================================================================
@router.get(
    "/alerts/history",
    response_model=List[AlertResponse],
    summary="Query historical emergency alerts",
    description="Returns paginated historical and resolved emergency alerts with optional severity and zone filters."
)
async def get_alert_history(
    response: Response,
    limit: int = Query(50, ge=1, le=500, description="Max historical records to return"),
    offset: int = Query(0, ge=0, description="Pagination offset index"),
    severity: Optional[str] = Query(None, description="Filter by severity: severe, high, moderate, low"),
    zone_id: Optional[str] = Query(None, description="Filter by sector code, e.g. Z-SHL-01"),
    status: Optional[str] = Query("resolved", description="Filter by status: resolved, all")
) -> List[Dict[str, Any]]:
    norm_status = status.strip().lower() if status else "resolved"
    if norm_status not in {"resolved", "all"}:
        raise HTTPException(
            status_code=422,
            detail=f"History status filter must be 'resolved' or 'all', got '{status}'"
        )
    if severity and severity.strip().lower() not in VALID_SEVERITIES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid severity '{severity}'. Must be one of: {', '.join(sorted(VALID_SEVERITIES))}"
        )

    pool = alert_service.get_historical_alerts()
    if norm_status == "all":
        pool = alert_service.get_active_alerts() + pool

    filtered = alert_service.filter_alerts(pool, severity=severity, zone_id=zone_id)
    response.headers["X-Total-Count"] = str(len(filtered))
    return filtered[offset : offset + limit]


# =============================================================================
# 3. Delivery Audit Log Query (GET /alerts/deliveries/audit — static subpath)
# =============================================================================
@router.get(
    "/alerts/deliveries/audit",
    response_model=List[DeliveryAuditRecord],
    summary="Query emergency alert delivery audit logs",
    description="Returns delivery audit logs with filtering by channel, recipient group, dispatch status, alert ID, and zone ID with pagination."
)
async def get_delivery_audit_logs(
    channel: Optional[str] = Query(None, description="Channel: sms, push, cap, all"),
    recipient_group: Optional[str] = Query(None, description="Recipient group: citizens, field_responders, emergency_command, all"),
    status: Optional[str] = Query(None, description="Status: simulated_delivered, delivered, failed, suppressed_cooldown, all"),
    alert_id: Optional[str] = Query(None, description="Filter by unique alert identifier"),
    zone_id: Optional[str] = Query(None, description="Filter by monitored sector ID (e.g. Z-SHL-01)"),
    limit: int = Query(50, ge=1, le=500, description="Max audit entries to retrieve (1 to 500)"),
    offset: int = Query(0, ge=0, description="Offset index for pagination")
) -> List[Dict[str, Any]]:
    clean_channel = None if not channel or channel.strip().lower() == "all" else channel.strip().lower()
    clean_recipient = None if not recipient_group or recipient_group.strip().lower() == "all" else recipient_group.strip().lower()
    clean_status = None if not status or status.strip().lower() == "all" else status.strip().lower()
    clean_alert_id = alert_id.strip() if alert_id else None
    clean_zone_id = zone_id.strip().upper() if zone_id else None

    return get_delivery_audit_records(
        alert_id=clean_alert_id,
        zone_id=clean_zone_id,
        channel=clean_channel,
        recipient_group=clean_recipient,
        status=clean_status,
        limit=limit,
        offset=offset
    )


# =============================================================================
# 4. Worker Telemetry & Controls
# =============================================================================
@router.get(
    "/alerts/worker/status",
    response_model=WorkerStatusResponse,
    summary="Get background monitoring worker telemetry"
)
async def get_worker_status() -> Dict[str, Any]:
    return alert_service.get_worker_status()


@router.post("/alerts/worker/pause", summary="Pause worker evaluations")
@router.post("/worker/pause", summary="Pause worker evaluations (alias)")
async def pause_worker() -> Dict[str, Any]:
    alert_service.pause_monitoring()
    return {"status": "paused", "worker": alert_service.get_worker_status()}


@router.post("/alerts/worker/resume", summary="Resume worker evaluations")
@router.post("/worker/resume", summary="Resume worker evaluations (alias)")
async def resume_worker() -> Dict[str, Any]:
    alert_service.resume_monitoring()
    return {"status": "resumed", "worker": alert_service.get_worker_status()}


# =============================================================================
# 5. On-Demand Evaluation & Drill Test Dispatch
# =============================================================================
@router.post(
    "/alerts/evaluate",
    summary="Force immediate evaluation of all monitored zones"
)
async def force_evaluate_alerts() -> Dict[str, Any]:
    alerts = await alert_service.evaluate_all_zones_and_generate_alerts()
    return {
        "status": "evaluated",
        "alerts_count": len(alerts),
        "alerts": alerts,
        "evaluated_at": alert_service._last_evaluation.isoformat() if alert_service._last_evaluation else None
    }


@router.post(
    "/alerts/test-dispatch",
    response_model=TestDispatchResponse,
    summary="Trigger drill test alert dispatch"
)
async def test_dispatch_endpoint(
    payload: TestDispatchRequest = TestDispatchRequest()
) -> Dict[str, Any]:
    zones_fc = get_risk_zones()
    features = zones_fc.get("features", [])
    valid_zones = {
        f.get("properties", {}).get("zone_id"): f.get("properties", {})
        for f in features
    }

    target_zone_id = payload.zone_id
    if not target_zone_id or target_zone_id not in valid_zones:
        target_zone_id = "Z-SHL-01"

    zone_meta = valid_zones.get(target_zone_id, {})
    zone_name = zone_meta.get("name", "Shillong East Ridge & Upper Shillong")

    severity = (payload.severity or "high").lower()
    if severity not in ["low", "moderate", "high", "severe"]:
        severity = "high"

    now_dt = datetime.now(timezone.utc)
    test_alert_id = f"TEST-ALT-{int(time.time() * 1000)}-{target_zone_id}"
    synthetic_alert = {
        "id": test_alert_id,
        "zone_id": target_zone_id,
        "zone_name": zone_name,
        "severity": severity,
        "risk_level": severity.capitalize(),
        "status": "active",
        "factor_of_safety": 1.05 if severity == "high" else (0.85 if severity == "severe" else 1.35),
        "probability": 0.75 if severity in ["high", "severe"] else 0.25,
        "failure_mode": "Simulated Drill Scenario",
        "breach_reasons": [f"Emergency Response Drill Test for {target_zone_id}"],
        "title": f"TEST DRILL WARNING: {zone_name}",
        "message_en": payload.custom_message or f"TEST DRILL ADVISORY: This is a simulated alert for {zone_name}.",
        "message_hi": f"परीक्षण अभ्यास: यह {zone_name} के लिए एक सिम्युलेटेड चेतावनी है।",
        "message_as": f"পৰীক্ষামূলক সতৰ্কবাণী: এইটো {zone_name}ৰ বাবে এটা কৃটিম সতৰ্কবাণী।",
        "triggered_at": now_dt.isoformat(),
        "timestamp": now_dt.isoformat(),
        "cooldown_until": (now_dt + timedelta(seconds=900)).isoformat(),
    }

    channels = payload.channels or ["sms", "push"]
    recipient_group = payload.recipient_group or "citizens"
    recipient_groups = [recipient_group] if recipient_group != "all" else ["citizens", "field_responders"]

    deliveries = await notification_dispatcher.dispatch_alert(
        alert=synthetic_alert,
        channels=channels,
        recipient_groups=recipient_groups,
        custom_message=payload.custom_message
    )

    return {
        "status": "dispatched",
        "test_alert_id": test_alert_id,
        "deliveries": deliveries
    }


# =============================================================================
# 6. Parameterized Sub-Resource Actions (/{alert_id}/acknowledge, /{alert_id}/resolve)
# =============================================================================
@router.post(
    "/alerts/{alert_id}/acknowledge",
    response_model=AlertResponse,
    summary="Acknowledge an active emergency alert"
)
async def acknowledge_alert_endpoint(
    alert_id: str,
    payload: AlertAcknowledgeRequest = AlertAcknowledgeRequest()
) -> Dict[str, Any]:
    if alert_id.lower() in {"history", "deliveries", "worker", "evaluate", "test-dispatch"}:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")

    updated = alert_service.acknowledge_alert(
        alert_id=alert_id,
        acknowledged_by=payload.acknowledged_by or "Field Officer",
        notes=payload.notes
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert '{alert_id}' not found or already resolved."
        )
    return updated


@router.post(
    "/alerts/{alert_id}/resolve",
    response_model=AlertResponse,
    summary="Resolve an active emergency alert"
)
async def resolve_alert_endpoint(
    alert_id: str,
    payload: AlertResolveRequest = AlertResolveRequest()
) -> Dict[str, Any]:
    if alert_id.lower() in {"history", "deliveries", "worker", "evaluate", "test-dispatch"}:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")

    note = payload.resolution_notes or payload.resolution_note
    resolved = alert_service.resolve_alert(
        alert_id=alert_id,
        resolved_by=payload.resolved_by or "System Admin",
        note=note
    )
    if not resolved:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert '{alert_id}' not found or already resolved."
        )
    return resolved


# =============================================================================
# 7. Parameterized Single Alert Query (MUST BE AT THE END to prevent path shadowing)
# =============================================================================
@router.get(
    "/alerts/{alert_id}",
    response_model=AlertResponse,
    summary="Get single alert telemetry by ID or Zone code"
)
async def get_single_alert(alert_id: str) -> Dict[str, Any]:
    if alert_id.lower() in {"history", "deliveries", "worker", "evaluate", "test-dispatch"}:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")

    alert = alert_service.get_alert_by_id(alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with ID or Zone '{alert_id}' not found"
        )
    return alert
