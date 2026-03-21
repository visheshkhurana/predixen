"""
Agent Simulation API — endpoints for running and retrieving agent-based simulations.
"""

import json
import secrets
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from server.core.db import get_db
from server.core.auth import get_current_user
from server.models import User
from server.models.agent_simulation import AgentSimulationRun
from server.simulation_agents.simulation_orchestrator import run_agent_simulation
from server.simulation_agents.simulation_report import generate_report

logger = logging.getLogger(__name__)
router = APIRouter(tags=["agent-simulation"])


class AgentSimulationRequest(BaseModel):
    num_rounds: int = Field(default=24, ge=6, le=60)
    seed: Optional[int] = None
    hiring_rate: float = Field(default=0, ge=0, le=20)
    pricing_change: float = Field(default=0, ge=-50, le=100)
    marketing_spend_multiplier: float = Field(default=1.0, ge=0.1, le=5.0)
    funding_climate: float = Field(default=0.6, ge=0.0, le=1.0)
    market_growth: float = Field(default=0.5, ge=0.0, le=1.0)
    market_trend: str = Field(default="neutral")
    market_volatility: float = Field(default=0.1, ge=0.0, le=0.5)
    founder_risk_tolerance: float = Field(default=0.6, ge=0.0, le=1.0)
    hiring_aggressiveness: float = Field(default=0.5, ge=0.0, le=1.0)
    monthly_revenue: Optional[float] = None
    monthly_burn: Optional[float] = None
    cash_balance: Optional[float] = None
    growth_rate: Optional[float] = None
    headcount: Optional[int] = None
    gross_margin: Optional[float] = None


@router.post("/companies/{company_id}/simulation/agent-run")
async def run_simulation(
    company_id: int,
    request: AgentSimulationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scenario_inputs = request.model_dump(exclude_none=True)

    try:
        result = run_agent_simulation(
            db=db,
            company_id=company_id,
            scenario_inputs=scenario_inputs,
            num_rounds=request.num_rounds,
            seed=request.seed,
        )

        report = generate_report(result)
        result["report"] = report

        share_token = secrets.token_urlsafe(32)

        sim_run = AgentSimulationRun(
            company_id=company_id,
            scenario_json=json.dumps(scenario_inputs),
            num_rounds=request.num_rounds,
            seed=request.seed,
            survival_probability=result["summary"]["survivalProbability"],
            funding_probability=result["summary"]["fundingProbability"],
            final_cash=result["summary"]["finalCash"],
            final_runway=result["summary"]["finalRunway"],
            results_json=json.dumps(result),
            events_json=json.dumps(result.get("events", [])),
            status="completed",
            completed_at=datetime.utcnow(),
            share_token=share_token,
        )
        db.add(sim_run)
        db.commit()
        db.refresh(sim_run)

        result["simulationId"] = sim_run.id
        result["shareToken"] = share_token

        return result

    except Exception as e:
        logger.error(f"Agent simulation failed for company {company_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")


@router.get("/companies/{company_id}/simulation/agent-runs")
async def list_simulations(
    company_id: int,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    runs = (
        db.query(AgentSimulationRun)
        .filter(AgentSimulationRun.company_id == company_id)
        .order_by(AgentSimulationRun.created_at.desc())
        .limit(limit)
        .all()
    )
    return {"runs": [r.to_dict() for r in runs]}


@router.get("/companies/{company_id}/simulation/agent-run/{run_id}")
async def get_simulation(
    company_id: int,
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    run = (
        db.query(AgentSimulationRun)
        .filter(AgentSimulationRun.id == run_id, AgentSimulationRun.company_id == company_id)
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="Simulation not found")

    try:
        results = json.loads(run.results_json) if run.results_json else {}
    except (json.JSONDecodeError, TypeError):
        results = {}

    return {**run.to_dict(), "results": results}


@router.get("/simulation/shared/{share_token}")
async def get_shared_simulation(
    share_token: str,
    db: Session = Depends(get_db),
):
    run = db.query(AgentSimulationRun).filter(AgentSimulationRun.share_token == share_token).first()
    if not run:
        raise HTTPException(status_code=404, detail="Shared simulation not found")

    try:
        results = json.loads(run.results_json) if run.results_json else {}
    except (json.JSONDecodeError, TypeError):
        results = {}

    report = results.get("report", {})
    return {
        "simulationId": run.id,
        "companyName": results.get("companyName", "Startup"),
        "summary": results.get("summary", {}),
        "report": report,
        "timeline": results.get("timeline", []),
        "events": results.get("events", []),
        "recommendations": results.get("recommendations", []),
        "keyRisks": results.get("keyRisks", []),
        "trajectories": results.get("trajectories", {}),
        "createdAt": run.created_at.isoformat() if run.created_at else None,
    }
