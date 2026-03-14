import time
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def handle_simulation(payload: Dict[str, Any]) -> Dict[str, Any]:
    from server.core.db import SessionLocal
    from server.models.simulation_job import SimulationJob, SimulationJobStatus
    from server.models.scenario import Scenario
    from server.simulate.enhanced_monte_carlo import (
        run_enhanced_monte_carlo,
        EnhancedSimulationInputs,
        SimulationConfig,
        ScenarioEvent,
        DistributionParams,
    )
    from server.core.cache import cache_delete, cache_key
    from datetime import datetime
    import uuid

    job_id = payload.get("job_id")
    scenario_id = payload.get("scenario_id")
    config_json = payload.get("config", {})

    db = SessionLocal()
    try:
        if job_id:
            job = db.query(SimulationJob).filter(SimulationJob.id == job_id).first()
            if job:
                job.status = SimulationJobStatus.RUNNING.value
                job.started_at = datetime.utcnow()
                db.commit()

        scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
        if not scenario:
            raise ValueError(f"Scenario {scenario_id} not found")

        inputs_json = scenario.inputs_json or {}
        events_json = inputs_json.get("events", [])

        config = SimulationConfig(
            iterations=config_json.get("iterations", 1000),
            horizon_months=config_json.get("horizon_months", 24),
            seed=config_json.get("seed"),
            confidence_intervals=config_json.get("confidence_intervals", [10, 25, 50, 75, 90]),
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
        result["executionTimeMs"] = elapsed_ms

        if job_id:
            job = db.query(SimulationJob).filter(SimulationJob.id == job_id).first()
            if job:
                job.results_json = result
                job.status = SimulationJobStatus.COMPLETED.value
                job.completed_at = datetime.utcnow()
                job.execution_time_ms = elapsed_ms
                job.progress = 100
                db.commit()

        cache_delete(cache_key("twin_state", str(scenario.company_id)))
        cache_delete(cache_key("kpis", str(scenario.company_id)))

        logger.info(f"Simulation completed for scenario {scenario_id} in {elapsed_ms}ms")
        return {"scenario_id": scenario_id, "execution_time_ms": elapsed_ms, "status": "completed"}

    except Exception as e:
        if job_id:
            try:
                job = db.query(SimulationJob).filter(SimulationJob.id == job_id).first()
                if job:
                    job.status = SimulationJobStatus.FAILED.value
                    job.error_message = str(e)[:500]
                    job.completed_at = datetime.utcnow()
                    db.commit()
            except Exception:
                db.rollback()
        raise
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
