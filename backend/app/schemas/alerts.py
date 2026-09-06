"""
Pydantic Schemas for Regional Landslide Emergency Alerts,
Delivery Audit Logs, and Worker Status Telemetry.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AlertResponse(BaseModel):
    id: str = Field(..., description="Unique alert identifier, e.g. ALT-2026-Z-SHL-01")
    zone_id: str = Field(..., description="Monitored sector code, e.g. Z-SHL-01")
    zone_name: str = Field(..., description="Geographical name of the zone")
    severity: str = Field(..., description="Severity tier: severe, high, moderate, low")
    risk_level: str = Field(..., description="Risk tier: Severe, High, Moderate, Low")
    status: str = Field("active", description="Alert status: active, acknowledged, resolved")
    factor_of_safety: float = Field(..., description="Computed geotechnical Factor of Safety")
    probability: float = Field(..., description="Predicted landslide probability (0.0 to 1.0)")
    failure_mode: Optional[str] = Field(None, description="Physical slope failure mode classification")
    breach_reasons: List[str] = Field(default_factory=list, description="Structured quantitative breach explanations")
    title: str = Field(..., description="Headline hazard alert title")
    message_en: str = Field(..., description="Emergency advisory message in English")
    message_hi: Optional[str] = Field(None, description="Emergency advisory message in Hindi")
    message_as: Optional[str] = Field(None, description="Emergency advisory message in Assamese")
    triggered_at: Optional[str] = Field(None, description="ISO UTC timestamp when alert was triggered")
    timestamp: Optional[str] = Field(None, description="Timestamp for backward compatibility")
    cooldown_until: Optional[str] = Field(None, description="ISO UTC timestamp until which duplicates are suppressed")
    acknowledged_at: Optional[str] = Field(None, description="ISO UTC timestamp of acknowledgement")
    acknowledged_by: Optional[str] = Field(None, description="Identifier/name of acknowledging officer")
    notes: Optional[str] = Field(None, description="Operational notes recorded on alert acknowledgement")
    resolved_at: Optional[str] = Field(None, description="ISO UTC timestamp of resolution")
    resolved_by: Optional[str] = Field(None, description="Identifier/name of resolving officer")
    resolution_note: Optional[str] = Field(None, description="Operational notes recorded on alert resolution")
    resolution_notes: Optional[str] = Field(None, description="Operational notes recorded on alert resolution")


class DeliveryAuditRecord(BaseModel):
    id: str = Field(..., description="Unique delivery ID, e.g. DEL-1725350000-a1b2")
    alert_id: str = Field(..., description="Associated alert ID")
    zone_id: str = Field(..., description="Target monitored zone ID")
    channel: str = Field(..., description="Channel: sms, push, cap, webhook, suppressed")
    recipient_group: str = Field(..., description="Group: citizens, field_responders, emergency_command, all")
    status: str = Field(..., description="Delivery status: simulated_delivered, delivered, failed, suppressed_cooldown")
    provider: str = Field(..., description="Provider: zero_key_simulation, twilio, cdac_cap, cooldown_state_machine")
    dispatched_at: str = Field(..., description="ISO 8601 UTC timestamp of dispatch")
    latency_ms: float = Field(0.0, description="Round-trip transmission latency in milliseconds")
    payload_preview: str = Field(..., description="Text summary of dispatched message")
    error_message: Optional[str] = Field(None, description="Error detail if delivery failed")


class TestDispatchRequest(BaseModel):
    zone_id: str = Field("Z-SHL-01", description="Target zone ID for drill dispatch")
    severity: Optional[str] = Field("high", description="Simulated severity: severe, high")
    channels: Optional[List[str]] = Field(default_factory=lambda: ["sms", "push"], description="Channels to dispatch")
    recipient_group: Optional[str] = Field("citizens", description="Target recipient cohort")
    custom_message: Optional[str] = Field(None, description="Optional custom broadcast text override")


class TestDispatchResponse(BaseModel):
    status: str = Field("dispatched", description="Status of the test dispatch operation")
    test_alert_id: str = Field(..., description="Generated synthetic test alert ID")
    deliveries: List[DeliveryAuditRecord] = Field(default_factory=list, description="List of generated delivery audit records")


class AlertAcknowledgeRequest(BaseModel):
    acknowledged_by: Optional[str] = Field("Field Officer", description="Name/role acknowledging the alert")
    notes: Optional[str] = Field(None, description="Operational notes on alert acknowledgement")


class AlertResolveRequest(BaseModel):
    resolved_by: Optional[str] = Field("System Admin", description="Name/role resolving the alert")
    resolution_note: Optional[str] = Field(None, description="Operational notes on event resolution")
    resolution_notes: Optional[str] = Field(None, description="Operational notes on event resolution")


class WorkerStatusResponse(BaseModel):
    status: str = Field(..., description="Worker health status: running, paused, stopped, degraded")
    is_running: bool = Field(..., description="True if background monitoring task is alive")
    is_paused: bool = Field(False, description="True if evaluations are paused")
    task_name: Optional[str] = Field(None, description="Internal asyncio task name")
    interval_seconds: float = Field(30.0, description="Evaluation cadence interval in seconds")
    poll_count: int = Field(0, description="Total inspection cycles completed")
    started_at: Optional[str] = Field(None, description="ISO UTC timestamp of worker start")
    uptime_seconds: Optional[float] = Field(None, description="Total running uptime in seconds")
    last_run_at: Optional[str] = Field(None, description="ISO UTC timestamp of last evaluation cycle")
    last_duration_seconds: float = Field(0.0, description="Execution duration of last evaluation cycle in seconds")
    consecutive_failures: int = Field(0, description="Count of consecutive evaluation exceptions")
    last_error: Optional[str] = Field(None, description="Last exception description if any")
    last_error_at: Optional[str] = Field(None, description="ISO UTC timestamp of last exception")
    active_alerts_count: int = Field(0, description="Current number of active emergency alerts")
    monitored_sectors_count: int = Field(6, description="Total monitored sectors in the system")
