"""
Automated Alert Monitoring & Management Service for NER-LEWS.
Features:
- Periodic background worker task with non-blocking sector evaluations
- Multi-criteria geotechnical & hydrological safety thresholds (FS <= 1.10, I-D curves, cloudbursts)
- Cooldown deduplication state machine (15-minute window)
- Escalation override (bypasses cooldown when hazard severity increases)
- Pluggable notification dispatching via zero-key simulator and external hooks
- Real-time worker health, telemetry, and alert lifecycle management
"""
import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from app.config import settings
from app.database import get_risk_zones, add_delivery_audit_record
from app.services.ml.risk_scorer import LandslideRiskEngine
from app.services.notification_service import notification_dispatcher

logger = logging.getLogger("ner_lews.alert_service")

ALERT_SEVERITY_THRESHOLDS = {
    "Severe": 0.80,
    "High": 0.60,
    "Moderate": 0.30,
}

RISK_LEVEL_ORDER = {"Low": 0, "Moderate": 1, "High": 2, "Severe": 3}
SEVERITY_RANK = {"low": 0, "moderate": 1, "high": 2, "severe": 3}


class AlertService:
    def __init__(self, cooldown_window_seconds: Optional[int] = None):
        self.risk_engine = LandslideRiskEngine()
        self._active_alerts: List[Dict[str, Any]] = []
        self._historical_alerts: List[Dict[str, Any]] = []
        self._sector_cooldowns: Dict[str, Dict[str, Any]] = {}
        self._cooldown_window_seconds: int = (
            cooldown_window_seconds
            if cooldown_window_seconds is not None
            else int(getattr(settings, "ALERT_COOLDOWN_SECONDS", 900))
        )
        self._interval_seconds: float = float(getattr(settings, "MONITORING_INTERVAL_SECONDS", 30.0))
        self._last_evaluation: Optional[datetime] = None

        # Background Worker State
        self._worker_task: Optional[asyncio.Task] = None
        self._worker_running: bool = False
        self._worker_paused: bool = False
        self._poll_count: int = 0
        self._started_at: Optional[datetime] = None
        self._last_run_at: Optional[datetime] = None
        self._last_duration_seconds: float = 0.0
        self._consecutive_failures: int = 0
        self._last_error: Optional[str] = None
        self._last_error_at: Optional[datetime] = None

    def _get_zone_payload(self, zone: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts numerical features from zone properties or direct dictionaries."""
        props = zone.get("properties", zone)
        return {
            "slope_deg": float(props.get("mean_slope_deg", props.get("slope_deg", 30.0))),
            "rain_1h": float(props.get("rainfall_1h_mm", props.get("rain_1h", props.get("current_rain_mm_h", 10.0)))),
            "rain_24h": float(props.get("rainfall_24h_mm", props.get("rain_24h", props.get("rain_24h_mm", 50.0)))),
            "soil_saturation_pct": float(props.get("soil_saturation_pct", 0.65)),
            "storm_duration_hours": float(props.get("storm_duration_hours", 6.0)),
            "soil_type": str(props.get("soil_type", "Clayey Loam on Weathered Quartzite")),
            "dist_to_road_m": float(props.get("dist_to_road_m", 45.0)),
            "elevation_m": float(props.get("elevation_m", 1400.0)),
            "twi": float(props.get("twi", 6.8)),
            "historical_slide_density": float(props.get("historical_slide_density", 3.0)),
            "api_15_mm": float(props.get("rainfall_7d_mm", props.get("rain_7d", props.get("api_15_mm", 100.0)))),
        }

    def _generate_zone_alert(self, zone: Dict[str, Any], risk_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Evaluates geotechnical physics and ML inference outputs to determine if an
        emergency alert should be generated, formatted with structured breach reasons.
        """
        props = zone.get("properties", zone)
        zone_id = props.get("zone_id", "UNKNOWN")
        zone_name = props.get("name", "Unknown Zone")
        infrastructure = props.get("critical_infrastructure", "Local roads")

        geo_safety = risk_result.get("geotechnical_safety", {})
        fs = float(risk_result.get("factor_of_safety", 1.5))
        prob = float(risk_result.get("probability", 0.0))
        risk_level = risk_result.get("risk_level", "Unknown")
        failure_mode = risk_result.get("failure_mode", geo_safety.get("slope_stability", {}).get("failure_mode", "Stable"))

        # Collect structured breach reasons
        reasons = list(geo_safety.get("breach_reasons", []))
        if prob >= 0.60:
            ml_reason = (
                f"Machine Learning risk model predicted {risk_level} hazard: "
                f"probability {prob:.1%} >= 60.0% threshold"
            )
            if ml_reason not in reasons:
                reasons.append(ml_reason)

        is_fs_breach = fs <= 1.10
        is_physics_breach = risk_result.get("physics_threshold_breached", False)
        is_ml_breach = risk_level in ["Severe", "High"] or prob >= 0.60

        # Must breach at least one geotechnical/hydrological safety threshold or High/Severe risk tier
        if not (is_fs_breach or is_physics_breach or is_ml_breach):
            return None

        # Determine severity tier
        is_severe = (
            fs <= 1.00
            or geo_safety.get("acute_1h_breached", False)
            or geo_safety.get("extreme_24h_sat_breached", False)
            or prob >= 0.80
            or (is_fs_breach and (geo_safety.get("caine_breached", False) or geo_safety.get("guzzetti_breached", False)))
        )
        severity = "severe" if is_severe else "high"
        title = f"{'CRITICAL' if severity == 'severe' else 'ELEVATED'} HAZARD WARNING: {zone_name}"

        # Construct localized multilingual advisory text
        reasons_summary = "; ".join(reasons[:2]) if reasons else f"Risk elevated to {risk_level}"
        message_en = (
            f"{title}. {reasons_summary}. Factor of Safety = {fs:.2f}. "
            f"Immediate evacuation and extreme caution recommended near {infrastructure}."
        )
        message_hi = (
            f"चेतावनी: {zone_name} में भूस्खलन जोखिम ({severity.upper()})। "
            f"सुरक्षा कारक = {fs:.2f}। {infrastructure} के समीप सतर्क रहें।"
        )
        message_as = (
            f"সতৰ্কবাণী: {zone_name}ত ভূমিস্খলনৰ আশংকা ({severity.upper()})। "
            f"সুৰক্ষা গুণাঙ্ক = {fs:.2f}। {infrastructure}ৰ ওচৰত সতৰ্ক থাকক।"
        )

        now_dt = datetime.now(timezone.utc)
        cooldown_until_dt = now_dt + timedelta(seconds=self._cooldown_window_seconds)

        return {
            "id": f"ALT-{now_dt.year}-{zone_id}",
            "zone_id": zone_id,
            "zone_name": zone_name,
            "severity": severity,
            "risk_level": risk_level,
            "status": "active",
            "factor_of_safety": round(fs, 3),
            "probability": round(prob, 3),
            "failure_mode": failure_mode,
            "breach_reasons": reasons,
            "title": title,
            "message_en": message_en,
            "message_hi": message_hi,
            "message_as": message_as,
            "triggered_at": now_dt.isoformat(),
            "timestamp": now_dt.isoformat(),
            "cooldown_until": cooldown_until_dt.isoformat(),
            "acknowledged_at": None,
            "acknowledged_by": None,
            "notes": None,
            "resolved_at": None,
            "resolved_by": None,
            "resolution_note": None,
            "resolution_notes": None,
        }

    async def process_alert_dispatch(
        self,
        candidate: Dict[str, Any],
        channels: Optional[List[str]] = None,
        recipient_groups: Optional[List[str]] = None,
        custom_message: Optional[str] = None
    ) -> str:
        """
        Enforces cooldown deduplication state machine and escalation override.
        Returns dispatch outcome: 'dispatched_new', 'escalated_dispatched', or 'suppressed_cooldown'.
        """
        zone_id = candidate.get("zone_id", "UNKNOWN")
        now = datetime.now(timezone.utc)
        cooldown = self._sector_cooldowns.get(zone_id)

        should_dispatch = False
        dispatch_type = "dispatched_new"

        if not cooldown or now >= cooldown["cooldown_until"]:
            # Initial trigger or cooldown expired
            should_dispatch = True
            dispatch_type = "dispatched_new"
        else:
            current_rank = SEVERITY_RANK.get(candidate["severity"].lower(), 0)
            last_rank = SEVERITY_RANK.get(cooldown["last_severity"].lower(), 0)

            if current_rank > last_rank:
                # Escalation Override: High -> Severe bypasses cooldown window immediately!
                should_dispatch = True
                dispatch_type = "escalated_dispatched"
                candidate["title"] = f"CRITICAL ESCALATED HAZARD WARNING: {candidate['zone_name']}"
                logger.info(
                    "[ESCALATION OVERRIDE] Zone %s escalated from %s to %s; overriding cooldown.",
                    zone_id, cooldown["last_severity"], candidate["severity"]
                )
            else:
                # Deduplicated: suppress notification dispatch
                should_dispatch = False
                dispatch_type = "suppressed_cooldown"

        if should_dispatch:
            # Update cooldown tracker
            self._sector_cooldowns[zone_id] = {
                "last_alert_id": candidate["id"],
                "last_dispatched_at": now,
                "cooldown_until": now + timedelta(seconds=self._cooldown_window_seconds),
                "last_severity": candidate["severity"],
                "last_risk_level": candidate["risk_level"],
                "suppressed_count": 0,
            }
            # Multi-channel notification delivery via dispatcher
            await notification_dispatcher.dispatch_alert(
                alert=candidate,
                channels=channels,
                recipient_groups=recipient_groups,
                custom_message=custom_message,
            )
        else:
            # Increment suppression counter
            cooldown["suppressed_count"] = cooldown.get("suppressed_count", 0) + 1
            candidate["cooldown_until"] = cooldown["cooldown_until"].isoformat()

            # Record suppression audit entry
            remaining_secs = max(0, int((cooldown["cooldown_until"] - now).total_seconds()))
            add_delivery_audit_record({
                "id": f"DEL-SUPP-{int(time.time()*1000)}-{uuid.uuid4().hex[:4]}",
                "alert_id": cooldown["last_alert_id"],
                "zone_id": zone_id,
                "channel": "suppressed",
                "recipient_group": "all",
                "status": "suppressed_cooldown",
                "provider": "cooldown_state_machine",
                "dispatched_at": now.isoformat(),
                "latency_ms": 0.0,
                "payload_preview": (
                    f"Suppressed duplicate {candidate['severity']} alert for {zone_id}. "
                    f"{remaining_secs}s cooldown remaining. "
                    f"Suppression cycle count: {cooldown['suppressed_count']}."
                ),
                "error_message": None,
            })
            logger.debug(
                "[COOLDOWN SUPPRESSION] Zone %s suppressed (cycle %d, %ds remaining).",
                zone_id, cooldown["suppressed_count"], remaining_secs
            )

        return dispatch_type

    async def evaluate_and_dispatch_alerts(
        self,
        sectors: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Performs non-blocking inspection across all monitored sectors, applies
        cooldown deduplication rules, and dispatches emergency alerts.
        """
        if sectors is None:
            zones_data = get_risk_zones()
            features = zones_data.get("features", [])
        else:
            features = sectors

        # Offload CPU-bound ML risk calculations to thread pool concurrently
        payloads = [self._get_zone_payload(zone) for zone in features]
        results = await asyncio.gather(
            *[asyncio.to_thread(self.risk_engine.predict_risk, p) for p in payloads]
        )

        existing_status_map = {a.get("id"): a for a in self._active_alerts if a.get("id")}
        existing_zone_map = {a.get("zone_id"): a for a in self._active_alerts if a.get("zone_id")}

        new_active: List[Dict[str, Any]] = []
        dispatch_tasks = []
        for zone, risk_result in zip(features, results):
            candidate = self._generate_zone_alert(zone, risk_result)
            if candidate:
                existing = existing_status_map.get(candidate.get("id")) or existing_zone_map.get(candidate.get("zone_id"))
                if existing and existing.get("status") == "acknowledged":
                    candidate["status"] = "acknowledged"
                    candidate["acknowledged_at"] = existing.get("acknowledged_at")
                    candidate["acknowledged_by"] = existing.get("acknowledged_by")
                    candidate["notes"] = existing.get("notes")

                dispatch_tasks.append(self.process_alert_dispatch(candidate))
                new_active.append(candidate)
            else:
                # If sector is stable, remove active cooldown so future breaches can trigger immediately
                props = zone.get("properties", zone)
                z_id = props.get("zone_id")
                if z_id and z_id in self._sector_cooldowns:
                    # Clear cooldown if sector has stabilized (FS > 1.30 and Low risk)
                    fs = float(risk_result.get("factor_of_safety", 1.5))
                    prob = float(risk_result.get("probability", 0.0))
                    if fs >= 1.30 and prob < 0.30:
                        self._sector_cooldowns.pop(z_id, None)

        if dispatch_tasks:
            await asyncio.gather(*dispatch_tasks)

        self._active_alerts = sorted(
            new_active,
            key=lambda a: (
                RISK_LEVEL_ORDER.get(a.get("risk_level", "Low"), 0),
                a.get("probability", 0)
            ),
            reverse=True
        )
        self._last_evaluation = datetime.now(timezone.utc)
        return self._active_alerts

    async def evaluate_all_zones_and_generate_alerts(self) -> List[Dict[str, Any]]:
        """Backward-compatible wrapper for manual on-demand evaluations."""
        return await self.evaluate_and_dispatch_alerts()

    # --- Background Worker Coroutine & Lifecycle Controls ---

    async def start_monitoring_worker(self, interval_seconds: Optional[float] = None) -> bool:
        """
        Starts the periodic background monitoring loop.
        Idempotent: returns False if worker is already running.
        """
        if interval_seconds is not None:
            self._interval_seconds = max(0.01, float(interval_seconds))

        if self._worker_task is not None and not self._worker_task.done():
            logger.warning("Monitoring worker is already active (Task: %s).", self._worker_task.get_name())
            return False

        self._worker_running = True
        self._worker_paused = False
        self._started_at = datetime.now(timezone.utc)
        self._worker_task = asyncio.create_task(
            self._monitoring_loop(),
            name="ner_lews_alert_monitoring_worker"
        )
        logger.info(
            "Started NER-LEWS background monitoring worker (interval=%.2fs, task=%s)",
            self._interval_seconds,
            self._worker_task.get_name()
        )
        return True

    async def stop_monitoring_worker(self, timeout_seconds: float = 5.0) -> bool:
        """Gracefully cancels and awaits termination of the monitoring worker task."""
        self._worker_running = False
        if self._worker_task is None:
            return True

        if not self._worker_task.done():
            self._worker_task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(self._worker_task), timeout=timeout_seconds)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                logger.info("Worker task cancellation confirmed.")
            except Exception as e:
                logger.warning("Exception during worker task cancellation: %s", e)

        self._worker_task = None
        logger.info("NER-LEWS background monitoring worker stopped.")
        return True

    def pause_monitoring(self) -> None:
        """Pauses worker evaluation cycles without canceling the task."""
        self._worker_paused = True
        logger.info("Monitoring worker paused.")

    def resume_monitoring(self) -> None:
        """Resumes worker evaluation cycles."""
        self._worker_paused = False
        logger.info("Monitoring worker resumed.")

    async def _monitoring_loop(self) -> None:
        """
        Main worker loop coroutine. Evaluates sectors periodically without blocking
        the event loop, applies cooldown rules, and dispatches alerts.
        """
        logger.info("Entering background monitoring loop (interval=%.2fs)", self._interval_seconds)
        while self._worker_running:
            try:
                if not self._worker_paused:
                    start_time = time.monotonic()
                    await self.evaluate_and_dispatch_alerts()
                    if self._worker_paused:
                        continue
                    duration = time.monotonic() - start_time
                    self._poll_count += 1
                    self._last_run_at = datetime.now(timezone.utc)
                    self._last_duration_seconds = round(duration, 4)
                    self._consecutive_failures = 0
                    self._last_error = None

                await asyncio.sleep(self._interval_seconds)

            except asyncio.CancelledError:
                logger.info("Monitoring worker task received cancellation; shutting down loop.")
                break
            except Exception as exc:
                self._consecutive_failures += 1
                self._last_error = f"{type(exc).__name__}: {str(exc)}"
                self._last_error_at = datetime.now(timezone.utc)
                logger.exception("Error in background monitoring loop cycle: %s", exc)

                # Resilient recovery: backoff sleep before retry to prevent tight error spinning
                backoff = min(self._interval_seconds, 5.0)
                try:
                    await asyncio.sleep(backoff)
                except asyncio.CancelledError:
                    break

    def get_worker_status(self) -> Dict[str, Any]:
        """Returns real-time health telemetry and performance metrics of the worker."""
        is_alive = self._worker_task is not None and not self._worker_task.done() and self._worker_running

        if not is_alive:
            health_status = "stopped"
        elif self._worker_paused:
            health_status = "paused"
        elif self._consecutive_failures > 0:
            health_status = "degraded"
        else:
            health_status = "running"

        uptime_seconds = None
        if self._started_at and is_alive:
            uptime_seconds = round((datetime.now(timezone.utc) - self._started_at).total_seconds(), 1)

        return {
            "status": health_status,
            "is_running": is_alive,
            "is_paused": self._worker_paused,
            "task_name": self._worker_task.get_name() if self._worker_task else None,
            "interval_seconds": self._interval_seconds,
            "poll_count": self._poll_count,
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "uptime_seconds": uptime_seconds,
            "last_run_at": self._last_run_at.isoformat() if self._last_run_at else None,
            "last_duration_seconds": self._last_duration_seconds,
            "consecutive_failures": self._consecutive_failures,
            "last_error": self._last_error,
            "last_error_at": self._last_error_at.isoformat() if self._last_error_at else None,
            "active_alerts_count": len(self._active_alerts),
            "monitored_sectors_count": 6,
        }

    # --- Query & Management Handlers ---

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Returns list of currently active emergency alerts."""
        return self._active_alerts

    def get_historical_alerts(self) -> List[Dict[str, Any]]:
        """Returns list of resolved/archived historical alerts."""
        return self._historical_alerts

    def get_alert_by_id(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """
        Searches active and historical alerts by alert ID or zone ID.
        Returns the alert dictionary if found, else None.
        """
        if not alert_id:
            return None
        target_id = alert_id.strip()
        target_upper = target_id.upper()

        # 1. Search active alerts by exact ID
        for alert in self._active_alerts:
            if alert.get("id") == target_id:
                return alert
        # 2. Search active alerts by zone_id (backward compatibility)
        for alert in self._active_alerts:
            if alert.get("zone_id", "").upper() == target_upper:
                return alert
        # 3. Search historical alerts by exact ID
        for alert in self._historical_alerts:
            if alert.get("id") == target_id:
                return alert
        # 4. Search historical alerts by zone_id
        for alert in self._historical_alerts:
            if alert.get("zone_id", "").upper() == target_upper:
                return alert
        return None

    def filter_alerts(
        self,
        alerts: List[Dict[str, Any]],
        status: Optional[str] = None,
        severity: Optional[str] = None,
        zone_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Filters a list of alert dictionaries by status, severity, and zone_id."""
        filtered = list(alerts)
        if status and status.strip().lower() != "all":
            clean_status = status.strip().lower()
            filtered = [a for a in filtered if a.get("status", "").lower() == clean_status]
        if severity and severity.strip().lower() != "all":
            clean_sev = severity.strip().lower()
            filtered = [a for a in filtered if a.get("severity", "").lower() == clean_sev]
        if zone_id and zone_id.strip().lower() != "all":
            clean_zone = zone_id.strip().upper()
            filtered = [a for a in filtered if a.get("zone_id", "").upper() == clean_zone]
        return filtered

    def acknowledge_alert(
        self,
        alert_id: str,
        acknowledged_by: str = "Field Officer",
        notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Acknowledges an active alert."""
        for alert in self._active_alerts:
            if alert.get("id") == alert_id:
                alert["status"] = "acknowledged"
                alert["acknowledged_at"] = datetime.now(timezone.utc).isoformat()
                alert["acknowledged_by"] = acknowledged_by
                if notes is not None:
                    alert["notes"] = notes
                return alert
        return None

    def resolve_alert(
        self,
        alert_id: str,
        resolved_by: str = "System Admin",
        note: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Resolves an active alert, moving it to historical alerts."""
        for idx, alert in enumerate(self._active_alerts):
            if alert.get("id") == alert_id:
                resolved = self._active_alerts.pop(idx)
                resolved["status"] = "resolved"
                resolved["resolved_at"] = datetime.now(timezone.utc).isoformat()
                resolved["resolved_by"] = resolved_by
                if note is not None:
                    resolved["resolution_note"] = note
                    resolved["resolution_notes"] = note
                self._historical_alerts.insert(0, resolved)
                # Clear sector cooldown
                zone_id = resolved.get("zone_id")
                if zone_id and zone_id in self._sector_cooldowns:
                    self._sector_cooldowns.pop(zone_id, None)
                return resolved
        return None

    def clear_expired_alerts(self, max_age_minutes: int = 60):
        if not self._last_evaluation:
            return
        elapsed = (datetime.now(timezone.utc) - self._last_evaluation).total_seconds() / 60
        if elapsed > max_age_minutes:
            self._active_alerts = []


alert_service = AlertService()
