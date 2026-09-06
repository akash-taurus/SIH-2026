"""
M1 Challenger 2: Concurrency, Lifespan, and Resiliency Adversarial Test Suite.

Adversarially tests:
1. 20 concurrent parallel starts: confirms race-condition immunity, idempotent rejection, single task spawn.
2. Rapid pause/resume toggling: 50 rapid cycles while actively polling, checking deadlock and crash immunity.
3. Rapid zero-delay start/stop cancellation: 20 rapid cycles, ensuring zero CancelledError leaks and zero orphaned pending tasks.
4. Synthetic unhandled exception injection: verifies fault tolerance, degraded health telemetry, error logging, and self-healing recovery.
5. Delivery audit store capping bound: verifies hard cap at 1,000 items with 1,500 inputs, strict FIFO eviction, and zero memory leaks.
"""
import asyncio
import sys
import time
import warnings
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.database import (
    _DELIVERY_AUDIT_STORE,
    add_delivery_audit_record,
    clear_delivery_audit_records,
    get_delivery_audit_records,
)
from app.services.alert_service import AlertService


@pytest.fixture(autouse=True)
def reset_audit_store():
    """Ensures each test starts and ends with a pristine audit store."""
    clear_delivery_audit_records()
    yield
    clear_delivery_audit_records()


# ==============================================================================
# CHALLENGE 1: Concurrency & Race Conditions
# ==============================================================================

@pytest.mark.asyncio
async def test_adversarial_20_parallel_starts_concurrency():
    """
    Stress Test: 20 concurrent asyncio tasks simultaneously invoke start_monitoring_worker().
    Requirement:
    - Exactly 1 task successfully starts the worker (returns True).
    - Exactly 19 tasks are idempotently rejected (return False).
    - Exactly 1 underlying asyncio.Task is created and running.
    - Zero race conditions or duplicate loop instances.
    """
    service = AlertService()
    assert service.get_worker_status()["is_running"] is False

    # Launch 20 concurrent start coroutines
    tasks = [
        asyncio.create_task(service.start_monitoring_worker(interval_seconds=0.03))
        for _ in range(20)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Validate no exceptions were raised
    exceptions = [r for r in results if isinstance(r, Exception)]
    assert len(exceptions) == 0, f"Encountered unexpected exceptions during concurrent starts: {exceptions}"

    # Validate exact return values
    true_count = sum(1 for r in results if r is True)
    false_count = sum(1 for r in results if r is False)
    assert true_count == 1, f"Expected exactly 1 start to succeed, but got {true_count}"
    assert false_count == 19, f"Expected exactly 19 starts to be rejected, but got {false_count}"

    # Validate worker state
    status = service.get_worker_status()
    assert status["is_running"] is True
    assert status["task_name"] == "ner_lews_alert_monitoring_worker"
    assert service._worker_task is not None
    assert not service._worker_task.done()

    # Clean shutdown
    stopped = await service.stop_monitoring_worker()
    assert stopped is True
    assert service.get_worker_status()["is_running"] is False


@pytest.mark.asyncio
async def test_adversarial_rapid_pause_resume_50_cycles():
    """
    Stress Test: Rapidly toggles pause_monitoring() and resume_monitoring() 50 times
    while the worker is actively polling in the background.
    Requirement:
    - Worker does NOT crash.
    - Worker does NOT deadlock or hang the event loop.
    - Poll count continues to increment during resumed phases.
    - Status transitions accurately between 'running' and 'paused'.
    """
    service = AlertService()
    # Fast polling interval (10ms)
    await service.start_monitoring_worker(interval_seconds=0.01)
    await asyncio.sleep(0.03)

    initial_status = service.get_worker_status()
    assert initial_status["is_running"] is True
    initial_polls = initial_status["poll_count"]

    # Rapid toggle harness: 50 cycles
    for i in range(50):
        service.pause_monitoring()
        assert service.get_worker_status()["is_paused"] is True
        # Micro-sleep to allow loop to observe paused state
        await asyncio.sleep(0.001)

        service.resume_monitoring()
        assert service.get_worker_status()["is_paused"] is False
        # Micro-sleep to allow loop to execute evaluations
        await asyncio.sleep(0.001)

    # Verify worker remains fully operational after 50 rapid toggle cycles
    await asyncio.sleep(0.05)
    final_status = service.get_worker_status()

    assert final_status["is_running"] is True
    assert final_status["status"] == "running"
    assert final_status["poll_count"] > initial_polls, (
        f"Expected poll count to advance past {initial_polls}, got {final_status['poll_count']}"
    )

    stopped = await service.stop_monitoring_worker()
    assert stopped is True


# ==============================================================================
# CHALLENGE 2: Lifespan & Rapid Start/Stop Cancellation
# ==============================================================================

@pytest.mark.asyncio
async def test_adversarial_rapid_start_stop_cancellation_20_cycles():
    """
    Stress Test: 20 rapid start/stop cancellation cycles with zero delay between start and stop.
    Requirement:
    - Zero asyncio.CancelledError leaks to caller.
    - Zero 'Task was destroyed but it is pending!' warnings.
    - Worker task is completely terminated and reset to None on every cycle.
    - Final state is cleanly stopped.
    """
    service = AlertService()

    with warnings.catch_warnings(record=True) as captured_warnings:
        warnings.simplefilter("always")

        for cycle in range(20):
            # Immediate start
            start_ok = await service.start_monitoring_worker(interval_seconds=0.01)
            assert start_ok is True, f"Failed to start worker on cycle {cycle}"
            assert service._worker_task is not None

            # Immediate stop with ZERO delay (tests cancellation before/during initial sleep)
            try:
                stop_ok = await service.stop_monitoring_worker()
                assert stop_ok is True, f"Failed to stop worker on cycle {cycle}"
            except asyncio.CancelledError:
                pytest.fail(f"CancelledError leaked during stop_monitoring_worker on cycle {cycle}")

            # Verify complete teardown
            assert service._worker_task is None, f"Worker task was not reset to None on cycle {cycle}"
            status = service.get_worker_status()
            assert status["is_running"] is False, f"Worker still reported running on cycle {cycle}"
            assert status["status"] == "stopped", f"Worker status not stopped on cycle {cycle}"

    # Check for any leaked pending task warnings
    pending_task_warnings = [
        w for w in captured_warnings
        if "Task was destroyed but it is pending" in str(w.message)
    ]
    assert len(pending_task_warnings) == 0, (
        f"Detected leaked pending task warnings: {[str(w.message) for w in pending_task_warnings]}"
    )


@pytest.mark.asyncio
async def test_adversarial_synthetic_sensor_exception_resilience():
    """
    Stress Test: Inject synthetic unhandled exceptions into evaluate_and_dispatch_alerts().
    Requirement:
    - Background worker does NOT terminate or crash.
    - Telemetry transitions to 'degraded' health state.
    - consecutive_failures counter increments.
    - Error details and timestamps are logged and captured.
    - Worker self-heals when normal evaluation is restored, resetting failures to 0.
    """
    service = AlertService()

    # 1. Fault injection: evaluate_and_dispatch_alerts raises fatal hardware exception
    fault_message = "Simulated Hardware Failure: Geotechnical Sensor Bus Timeout (I2C 0x48)"
    with patch.object(
        service,
        "evaluate_and_dispatch_alerts",
        side_effect=RuntimeError(fault_message)
    ) as mock_eval:
        await service.start_monitoring_worker(interval_seconds=0.02)
        # Allow worker loop to encounter at least 3 failure iterations
        await asyncio.sleep(0.12)

        status_degraded = service.get_worker_status()
        assert status_degraded["is_running"] is True, "Worker terminated unexpectedly upon exception!"
        assert status_degraded["status"] == "degraded", (
            f"Expected status 'degraded', got '{status_degraded['status']}'"
        )
        assert status_degraded["consecutive_failures"] >= 2, (
            f"Expected consecutive_failures >= 2, got {status_degraded['consecutive_failures']}"
        )
        assert fault_message in status_degraded["last_error"]
        assert status_degraded["last_error_at"] is not None
        assert mock_eval.call_count >= 2

    # 2. Self-Healing: restore unmocked evaluation
    # Allow 2 normal cycles
    await asyncio.sleep(0.10)

    status_recovered = service.get_worker_status()
    assert status_recovered["is_running"] is True
    assert status_recovered["status"] == "running", (
        f"Expected recovered status 'running', got '{status_recovered['status']}'"
    )
    assert status_recovered["consecutive_failures"] == 0, (
        f"Expected consecutive_failures to reset to 0, got {status_recovered['consecutive_failures']}"
    )
    assert status_recovered["last_error"] is None

    await service.stop_monitoring_worker()


# ==============================================================================
# CHALLENGE 3: Delivery Audit Store Stress & Capping Bounds
# ==============================================================================

def test_adversarial_delivery_audit_store_1500_records_capping():
    """
    Stress Test: Ingest 1,500 delivery audit records into _DELIVERY_AUDIT_STORE.
    Requirement:
    - Hard cap strictly maintained at exactly 1,000 items (no unbounded memory growth).
    - Eviction follows strict FIFO order (oldest records 0..499 evicted, 500..1499 retained).
    - Latest inserted record is at index 0 (LIFO query display order).
    - Query filters and pagination (limit/offset) operate deterministically on capped store.
    - Memory footprint remains stable.
    """
    clear_delivery_audit_records()
    assert len(_DELIVERY_AUDIT_STORE) == 0

    # Ingest 1,500 records
    total_records_to_generate = 1500
    for idx in range(total_records_to_generate):
        record = {
            "id": f"DEL-STRESS-{idx:04d}",
            "alert_id": f"ALT-TEST-{idx % 10}",
            "zone_id": f"Z-TEST-{(idx % 6) + 1:02d}",
            "channel": "sms" if idx % 2 == 0 else "push",
            "recipient_group": "incident_command" if idx % 3 == 0 else "general_public",
            "status": "simulated_delivered",
            "provider": "zero_key_simulator",
            "dispatched_at": datetime.now(timezone.utc).isoformat(),
            "latency_ms": 5.0 + (idx % 10),
            "payload_preview": f"Adversarial Stress Record payload sample #{idx}",
            "error_message": None,
        }
        add_delivery_audit_record(record)

    # 1. Verify strict bound
    current_count = len(_DELIVERY_AUDIT_STORE)
    assert current_count == 1000, f"Audit store size exceeded cap: expected 1000, got {current_count}"

    # 2. Verify FIFO eviction and ordering
    # Index 0 must be the most recently added record: index 1499
    assert _DELIVERY_AUDIT_STORE[0]["id"] == f"DEL-STRESS-{1499:04d}"

    # Index 999 (oldest retained) must be index 500
    assert _DELIVERY_AUDIT_STORE[999]["id"] == f"DEL-STRESS-{500:04d}"

    # Verify evicted records (0 through 499) are completely absent
    store_ids = {r["id"] for r in _DELIVERY_AUDIT_STORE}
    assert "DEL-STRESS-0000" not in store_ids, "Oldest record was not evicted!"
    assert "DEL-STRESS-0499" not in store_ids, "Record 499 was not evicted!"
    assert "DEL-STRESS-0500" in store_ids, "Record 500 should be preserved!"
    assert "DEL-STRESS-1499" in store_ids, "Newest record must be preserved!"

    # 3. Query & pagination validation on 1,000 capped records
    page_1 = get_delivery_audit_records(limit=50, offset=0)
    assert len(page_1) == 50
    assert page_1[0]["id"] == "DEL-STRESS-1499"

    page_last = get_delivery_audit_records(limit=50, offset=980)
    assert len(page_last) == 20
    assert page_last[-1]["id"] == "DEL-STRESS-0500"

    page_out_of_bounds = get_delivery_audit_records(limit=50, offset=1000)
    assert len(page_out_of_bounds) == 0

    # 4. Memory footprint verification
    list_mem_bytes = sys.getsizeof(_DELIVERY_AUDIT_STORE)
    # 1000 reference pointers in Python list is ~8KB to ~10KB
    assert list_mem_bytes < 100_000, f"Memory footprint unusually large: {list_mem_bytes} bytes"


@pytest.mark.asyncio
async def test_adversarial_concurrent_delivery_audit_insertion_stress():
    """
    Stress Test: 15 concurrent asyncio workers concurrently write 100 records each (1500 total).
    Requirement:
    - Store remains strictly capped at 1,000 items.
    - Zero exceptions, corruption, or size overflow.
    """
    clear_delivery_audit_records()

    async def worker_writer(worker_id: int):
        for seq in range(100):
            idx = worker_id * 100 + seq
            record = {
                "id": f"CONC-AUDIT-W{worker_id}-{seq:03d}",
                "alert_id": f"ALT-CONC-{worker_id}",
                "zone_id": f"Z-TEST-{worker_id % 6}",
                "channel": "sms",
                "recipient_group": "all",
                "status": "simulated_delivered",
                "provider": "zero_key_simulator",
                "dispatched_at": datetime.now(timezone.utc).isoformat(),
                "latency_ms": 4.2,
                "payload_preview": f"Worker {worker_id} seq {seq}",
            }
            add_delivery_audit_record(record)
            if seq % 20 == 0:
                await asyncio.sleep(0.001)

    workers = [asyncio.create_task(worker_writer(w)) for w in range(15)]
    await asyncio.gather(*workers)

    assert len(_DELIVERY_AUDIT_STORE) == 1000, (
        f"Concurrent insertions violated cap: {len(_DELIVERY_AUDIT_STORE)}"
    )


# ==============================================================================
# ADDITIONAL ADVERSARIAL STRESS CHALLENGES
# ==============================================================================

@pytest.mark.asyncio
async def test_adversarial_20_parallel_stops():
    """
    Stress Test: 20 concurrent asyncio tasks simultaneously invoke stop_monitoring_worker().
    Requirement:
    - All 20 calls return True.
    - Zero CancelledError leaks.
    - Worker task is cleanly terminated without duplicate cancellation errors.
    """
    service = AlertService()
    await service.start_monitoring_worker(interval_seconds=0.02)
    assert service.get_worker_status()["is_running"] is True

    # Concurrent 20 stops
    stop_tasks = [
        asyncio.create_task(service.stop_monitoring_worker())
        for _ in range(20)
    ]
    stop_results = await asyncio.gather(*stop_tasks, return_exceptions=True)

    exceptions = [r for r in stop_results if isinstance(r, Exception)]
    assert len(exceptions) == 0, f"Exceptions in concurrent stop: {exceptions}"
    assert all(r is True for r in stop_results), f"Not all stops returned True: {stop_results}"
    assert service.get_worker_status()["is_running"] is False


@pytest.mark.asyncio
async def test_adversarial_repeated_lifespan_cycles_10x():
    """
    Stress Test: Rapidly cycles the FastAPI lifespan context manager 10 consecutive times.
    Requirement:
    - Background worker starts and terminates cleanly every iteration.
    - No task leakage or zombie loops across lifespan cycles.
    """
    from app.main import app, lifespan
    from app.services.alert_service import alert_service

    for i in range(10):
        async with lifespan(app):
            status_during = alert_service.get_worker_status()
            assert status_during["is_running"] is True
            assert status_during["status"] in ["running", "degraded"]

        status_after = alert_service.get_worker_status()
        assert status_after["is_running"] is False
        assert status_after["status"] == "stopped"


def test_adversarial_invalid_interval_clamping():
    """
    Stress Test: Edge-case intervals (negative, zero, minute fractions).
    Requirement:
    - Service clamps intervals to a safe minimum of 0.01s without crashing.
    """
    service = AlertService()
    asyncio.run(service.start_monitoring_worker(interval_seconds=-50.0))
    assert service._interval_seconds == 0.01
    asyncio.run(service.stop_monitoring_worker())

    asyncio.run(service.start_monitoring_worker(interval_seconds=0.0))
    assert service._interval_seconds == 0.01
    asyncio.run(service.stop_monitoring_worker())

