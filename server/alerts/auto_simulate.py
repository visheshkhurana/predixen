"""
Auto-Trigger Simulations — automatically queue Monte Carlo simulations
when critical smart alerts fire (churn spike, burn spike, runway warning).
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from sqlalchemy.orm import Session

from server.core.company_metadata import save_metadata_value

logger = logging.getLogger(__name__)


ALERT_SCENARIO_MAP = {
    "burn_spike": {
        "scenario_name": "Burn Reduction Response",
        "description": "Auto-triggered: explore burn reduction scenarios after burn spike alert",
        "adjustments": {
            "burn_reduction_pct": 20,
            "hiring_freeze": True,
        },
    },
    "mrr_drop": {
        "scenario_name": "Revenue Recovery",
        "description": "Auto-triggered: model revenue recovery paths after MRR drop",
        "adjustments": {
            "revenue_growth_boost_pct": 5,
            "churn_reduction_pct": 10,
        },
    },
    "churn_spike": {
        "scenario_name": "Churn Mitigation Impact",
        "description": "Auto-triggered: simulate churn reduction impact after churn spike",
        "adjustments": {
            "churn_reduction_pct": 30,
            "retention_investment_pct": 5,
        },
    },
    "runway_warning": {
        "scenario_name": "Emergency Runway Extension",
        "description": "Auto-triggered: model runway extension scenarios after critical warning",
        "adjustments": {
            "burn_reduction_pct": 25,
            "hiring_freeze": True,
            "revenue_growth_boost_pct": 3,
        },
    },
    "runway_caution": {
        "scenario_name": "Proactive Runway Planning",
        "description": "Auto-triggered: model proactive cost optimization for runway extension",
        "adjustments": {
            "burn_reduction_pct": 10,
            "revenue_growth_boost_pct": 2,
        },
    },
    "growth_slowdown": {
        "scenario_name": "Growth Acceleration",
        "description": "Auto-triggered: model growth recovery strategies after slowdown",
        "adjustments": {
            "marketing_spend_increase_pct": 15,
            "revenue_growth_boost_pct": 5,
        },
    },
}


def should_auto_simulate(alert: Dict[str, Any]) -> bool:
    """Determine if an alert should trigger an automatic simulation."""
    alert_type = alert.get("type", "")
    severity = alert.get("severity", "")

    if alert_type in ALERT_SCENARIO_MAP:
        if severity in ("critical", "warning"):
            return True
    return False


def get_simulation_config(
    alert: Dict[str, Any],
    company_id: int,
    financials: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Build a simulation configuration based on the alert type.
    Returns a config dict that can be passed to the simulation engine.
    """
    alert_type = alert.get("type", "")
    scenario = ALERT_SCENARIO_MAP.get(alert_type)
    if not scenario:
        return None

    fin = financials or {}
    revenue = fin.get("revenue", 50000)
    burn = fin.get("monthly_burn", 80000)
    cash = fin.get("cash_balance", 500000)
    growth_rate = fin.get("growth_rate", 10)
    churn_rate = fin.get("churn_rate", 5)

    adjustments = scenario["adjustments"]

    adjusted_burn = burn
    if adjustments.get("burn_reduction_pct"):
        adjusted_burn = burn * (1 - adjustments["burn_reduction_pct"] / 100)

    adjusted_growth = growth_rate
    if adjustments.get("revenue_growth_boost_pct"):
        adjusted_growth = growth_rate + adjustments["revenue_growth_boost_pct"]

    adjusted_churn = churn_rate
    if adjustments.get("churn_reduction_pct"):
        adjusted_churn = churn_rate * (1 - adjustments["churn_reduction_pct"] / 100)

    config = {
        "simulation_id": str(uuid.uuid4()),
        "company_id": company_id,
        "trigger": "auto_alert",
        "alert_id": alert.get("id"),
        "alert_type": alert_type,
        "scenario_name": scenario["scenario_name"],
        "description": scenario["description"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "parameters": {
            "initial_revenue": revenue,
            "initial_burn": adjusted_burn,
            "initial_cash": cash,
            "growth_rate": adjusted_growth / 100,
            "churn_rate": adjusted_churn / 100,
            "horizon_months": 24,
            "num_simulations": 500,
            "adjustments_applied": adjustments,
        },
        "baseline_parameters": {
            "initial_revenue": revenue,
            "initial_burn": burn,
            "initial_cash": cash,
            "growth_rate": growth_rate / 100,
            "churn_rate": churn_rate / 100,
        },
    }

    return config


def create_auto_simulation_job(
    db: Session,
    company_id: int,
    alert: Dict[str, Any],
    financials: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Create an auto-triggered simulation job stored in company metadata.
    Returns the job record dict or None if not applicable.
    """
    if not should_auto_simulate(alert):
        return None

    config = get_simulation_config(alert, company_id, financials)
    if not config:
        return None

    try:
        from server.models.company import Company

        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            return None

        metadata = company.metadata_json or {}
        auto_sims = metadata.get("auto_simulations", [])

        sim_record = {
            "simulation_id": config["simulation_id"],
            "scenario_name": config["scenario_name"],
            "description": config["description"],
            "status": "QUEUED",
            "created_at": config["created_at"],
            "alert_id": alert.get("id"),
            "alert_type": alert.get("type"),
            "alert_severity": alert.get("severity"),
            "parameters": config["parameters"],
            "baseline_parameters": config["baseline_parameters"],
        }

        auto_sims.append(sim_record)
        auto_sims = auto_sims[-20:]
        save_metadata_value(db, company, "auto_simulations", auto_sims)

        logger.info(
            f"Auto-triggered simulation {config['simulation_id']} for company {company_id} "
            f"(alert: {alert.get('type')})"
        )

        return {
            "simulation_id": config["simulation_id"],
            "scenario_name": config["scenario_name"],
            "status": "QUEUED",
            "alert_type": alert.get("type"),
            "parameters": config["parameters"],
        }

    except Exception as e:
        logger.error(f"Failed to create auto-simulation job: {e}")
        db.rollback()

        return {
            "simulation_id": config["simulation_id"],
            "scenario_name": config["scenario_name"],
            "status": "QUEUED_IN_MEMORY",
            "alert_type": alert.get("type"),
            "parameters": config["parameters"],
            "note": "Stored in alert metadata (DB job creation failed)",
        }


def process_alerts_for_simulation(
    db: Session,
    company_id: int,
    alerts: List[Dict[str, Any]],
    financials: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Process a list of alerts and create auto-simulation jobs for qualifying ones.
    Returns list of created simulation job summaries.
    """
    created_jobs = []

    for alert in alerts:
        if not should_auto_simulate(alert):
            continue

        if alert.get("auto_simulation_triggered"):
            continue

        job = create_auto_simulation_job(db, company_id, alert, financials)
        if job:
            alert["auto_simulation_triggered"] = True
            alert["auto_simulation_id"] = job.get("simulation_id") or job.get("job_id")
            created_jobs.append(job)

    if created_jobs:
        logger.info(
            f"Auto-triggered {len(created_jobs)} simulations for company {company_id}"
        )

    return created_jobs
