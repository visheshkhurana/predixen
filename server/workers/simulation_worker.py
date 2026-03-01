"""
Simulation Worker — Isolated process for CPU-bound Monte Carlo simulations.

Runs as a separate process from the API server to prevent simulation CPU usage
from starving API request handling. Polls the simulation_jobs table for PENDING
jobs, processes them with concurrency control, and broadcasts results via WebSocket.

On startup, marks any stale RUNNING jobs as FAILED (crash recovery).
"""

import os
import sys
import time
import signal
import logging
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("simulation_worker")

MAX_CONCURRENT = int(os.environ.get("SIM_WORKER_MAX_CONCURRENT", "3"))
POLL_INTERVAL = float(os.environ.get("SIM_WORKER_POLL_INTERVAL", "2.0"))
STALE_TIMEOUT_MINUTES = int(os.environ.get("SIM_WORKER_STALE_TIMEOUT", "30"))
NODE_SERVER_URL = os.environ.get("NODE_SERVER_URL", "http://localhost:5000")

_shutdown = threading.Event()


def _init_db():
    from server.core.db import SessionLocal
    return SessionLocal


def _recover_stale_jobs(SessionLocal):
    from server.models.simulation_job import SimulationJob, SimulationJobStatus

    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(minutes=STALE_TIMEOUT_MINUTES)
        stale = db.query(SimulationJob).filter(
            SimulationJob.status == SimulationJobStatus.RUNNING.value,
            SimulationJob.started_at < cutoff,
        ).all()

        if stale:
            logger.warning(f"Recovering {len(stale)} stale RUNNING jobs")
            for job in stale:
                job.status = SimulationJobStatus.FAILED.value
                job.error_message = "Worker crashed or restarted during execution"
                job.completed_at = datetime.utcnow()
            db.commit()
            logger.info(f"Marked {len(stale)} stale jobs as FAILED")

        orphaned = db.query(SimulationJob).filter(
            SimulationJob.status == SimulationJobStatus.RUNNING.value,
            SimulationJob.started_at == None,
        ).all()
        if orphaned:
            for job in orphaned:
                job.status = SimulationJobStatus.FAILED.value
                job.error_message = "Job was in RUNNING state without start time"
                job.completed_at = datetime.utcnow()
            db.commit()
            logger.info(f"Recovered {len(orphaned)} orphaned RUNNING jobs")
    except Exception as e:
        logger.error(f"Error during crash recovery: {e}")
        db.rollback()
    finally:
        db.close()


def _claim_next_job(SessionLocal) -> Optional[str]:
    from server.models.simulation_job import SimulationJob, SimulationJobStatus
    from sqlalchemy import text

    db = SessionLocal()
    try:
        result = db.execute(
            text("""
                UPDATE simulation_jobs
                SET status = :running, started_at = :now
                WHERE id = (
                    SELECT id FROM simulation_jobs
                    WHERE status = :pending
                    ORDER BY created_at ASC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                )
                RETURNING id
            """),
            {
                "running": SimulationJobStatus.RUNNING.value,
                "pending": SimulationJobStatus.PENDING.value,
                "now": datetime.utcnow(),
            }
        )
        row = result.fetchone()
        db.commit()
        if row:
            return row[0]
        return None
    except Exception as e:
        logger.error(f"Error claiming job: {e}")
        db.rollback()
        return None
    finally:
        db.close()


def _execute_job(job_id: str, SessionLocal):
    from server.models.simulation_job import SimulationJob, SimulationJobStatus
    from server.models.scenario import Scenario
    from server.simulate.enhanced_monte_carlo import (
        run_enhanced_monte_carlo,
        EnhancedSimulationInputs,
        SimulationConfig,
        ScenarioEvent,
        DistributionParams,
    )

    db = SessionLocal()
    try:
        job = db.query(SimulationJob).filter(SimulationJob.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        scenario = db.query(Scenario).filter(Scenario.id == job.scenario_id).first()
        if not scenario:
            job.status = SimulationJobStatus.FAILED.value
            job.error_message = "Scenario not found"
            job.completed_at = datetime.utcnow()
            db.commit()
            return

        inputs_json = scenario.inputs_json or {}
        events_json = inputs_json.get("events", [])

        config = SimulationConfig(
            iterations=job.config_json.get("iterations", 1000),
            horizon_months=job.config_json.get("horizon_months", 24),
            seed=job.seed,
            confidence_intervals=job.config_json.get("confidence_intervals", [10, 25, 50, 75, 90]),
        )

        events = _parse_events(events_json)

        inputs = EnhancedSimulationInputs(
            baseline_revenue=inputs_json.get("baseline_revenue", 100000),
            baseline_growth_rate=inputs_json.get("baseline_growth_rate", 5),
            gross_margin=inputs_json.get("gross_margin", 70),
            opex=inputs_json.get("opex", 20000),
            payroll=inputs_json.get("payroll", 50000),
            other_costs=inputs_json.get("other_costs", 10000),
            cash_balance=inputs_json.get("cash_balance", 500000),
            churn_rate=inputs_json.get("churn_rate", 5),
            pricing_change_pct=inputs_json.get("pricing_change_pct", 0),
            growth_uplift_pct=inputs_json.get("growth_uplift_pct", 0),
            burn_reduction_pct=inputs_json.get("burn_reduction_pct", 0),
            fundraise_month=inputs_json.get("fundraise_month"),
            fundraise_amount=inputs_json.get("fundraise_amount", 0),
            gross_margin_delta_pct=inputs_json.get("gross_margin_delta_pct", 0),
            events=events,
        )

        start_time = time.time()
        result = run_enhanced_monte_carlo(inputs, config)
        elapsed_ms = int((time.time() - start_time) * 1000)

        result["scenarioId"] = scenario.id
        result["jobId"] = job_id

        job.results_json = result
        job.status = SimulationJobStatus.COMPLETED.value
        job.completed_at = datetime.utcnow()
        job.execution_time_ms = elapsed_ms
        job.progress = 100
        db.commit()

        logger.info(f"Job {job_id} completed in {elapsed_ms}ms (scenario {scenario.id})")

        _broadcast_completion(scenario.id, result)

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        try:
            job = db.query(SimulationJob).filter(SimulationJob.id == job_id).first()
            if job:
                job.status = SimulationJobStatus.FAILED.value
                job.error_message = str(e)[:500]
                job.completed_at = datetime.utcnow()
                db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()


def _parse_events(events_data):
    from server.simulate.enhanced_monte_carlo import ScenarioEvent, DistributionParams
    import uuid

    parsed = []
    for e in events_data:
        impact = {}
        if e.get("impact"):
            for key, val in e["impact"].items():
                if val:
                    impact[key] = DistributionParams(
                        type=val.get("type", "fixed"),
                        value=val.get("value"),
                        mean=val.get("mean"),
                        std_dev=val.get("stdDev"),
                        min_val=val.get("min"),
                        max_val=val.get("max"),
                        mode=val.get("mode"),
                        values=val.get("values"),
                    )

        duration = None
        if e.get("duration"):
            d = e["duration"]
            duration = DistributionParams(
                type=d.get("type", "fixed"),
                value=d.get("value", 1),
                mean=d.get("mean"),
                std_dev=d.get("stdDev"),
                min_val=d.get("min"),
                max_val=d.get("max"),
            )

        parsed.append(ScenarioEvent(
            id=e.get("id", str(uuid.uuid4())),
            type=e.get("type", "custom"),
            name=e.get("name", "Event"),
            month=e.get("month", 1),
            probability=e.get("probability", 1.0),
            duration=duration,
            impact=impact,
            description=e.get("description", ""),
        ))
    return parsed


def _broadcast_completion(scenario_id: int, results: Dict):
    try:
        import httpx

        with httpx.Client(timeout=5.0) as client:
            client.post(
                f"{NODE_SERVER_URL}/internal/broadcast/simulation",
                json={
                    "scenarioId": scenario_id,
                    "status": "completed",
                    "progress": 100,
                    "results": results,
                },
            )
    except Exception as e:
        logger.warning(f"Failed to broadcast completion for scenario {scenario_id}: {e}")


def run_worker():
    logger.info("=" * 60)
    logger.info("Simulation Worker starting")
    logger.info(f"  Max concurrent jobs: {MAX_CONCURRENT}")
    logger.info(f"  Poll interval: {POLL_INTERVAL}s")
    logger.info(f"  Stale timeout: {STALE_TIMEOUT_MINUTES}min")
    logger.info("=" * 60)

    SessionLocal = _init_db()

    _recover_stale_jobs(SessionLocal)

    executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT, thread_name_prefix="sim")
    active_futures: Dict[str, Future] = {}

    def _cleanup_completed():
        done = [jid for jid, f in active_futures.items() if f.done()]
        for jid in done:
            future = active_futures.pop(jid)
            exc = future.exception()
            if exc:
                logger.error(f"Job {jid} thread raised: {exc}")

    try:
        while not _shutdown.is_set():
            _cleanup_completed()

            if len(active_futures) < MAX_CONCURRENT:
                job_id = _claim_next_job(SessionLocal)
                if job_id:
                    logger.info(f"Claimed job {job_id} ({len(active_futures) + 1}/{MAX_CONCURRENT} active)")
                    future = executor.submit(_execute_job, job_id, SessionLocal)
                    active_futures[job_id] = future
                    continue

            _shutdown.wait(timeout=POLL_INTERVAL)
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("Worker shutting down, waiting for active jobs...")
        executor.shutdown(wait=True, cancel_futures=False)
        logger.info("Simulation Worker stopped")


def _handle_signal(signum, frame):
    logger.info(f"Received signal {signum}, initiating shutdown...")
    _shutdown.set()


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    run_worker()
