"""
Digital Twin API — unified endpoints for the Founder Digital Twin system.
Provides real-time company modeling, simulation, decision memory, and event tracking.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, Field

from server.core.db import get_db
from server.core.security import get_current_user
from server.core.company_access import get_user_company
from server.models.user import User
from server.services.digital_twin import (
    get_twin_state,
    emit_twin_event,
    get_twin_events,
    get_twin_history,
    get_decision_memory,
    run_twin_simulation,
)

router = APIRouter(prefix="", tags=["Digital Twin"])


ALLOWED_EVENT_TYPES = {
    "state_update", "revenue_update", "expense_update", "simulation_run",
    "decision_made", "decision_outcome", "alert_triggered", "connector_sync",
    "truth_scan_complete", "fundraising_update", "headcount_change",
    "data_ingestion",
}


class TwinEventRequest(BaseModel):
    event_type: str = Field(..., description="Type of event", max_length=100)
    source: str = Field(default="manual", description="Event source", max_length=100)
    payload: Optional[dict] = Field(default=None, description="Event payload")


class TwinSimulationRequest(BaseModel):
    scenario_name: str = Field(default="Custom Scenario", description="Name for this scenario")
    pricing_change_pct: float = Field(default=0, ge=-50, le=100)
    growth_uplift_pct: float = Field(default=0, ge=-50, le=200)
    burn_reduction_pct: float = Field(default=0, ge=0, le=80)
    fundraise_month: Optional[int] = Field(default=None, ge=1, le=24)
    fundraise_amount: Optional[int] = Field(default=None, ge=0)
    hiring_plan: list = Field(default_factory=list)


@router.get("/companies/{company_id}/twin/state")
def api_get_twin_state(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_user_company(db, company_id, current_user)
    state = get_twin_state(db, company_id)
    if "error" in state:
        raise HTTPException(status_code=404, detail=state["error"])
    return state


@router.get("/companies/{company_id}/twin/events")
def api_get_twin_events(
    company_id: int,
    event_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_user_company(db, company_id, current_user)
    events = get_twin_events(db, company_id, event_type=event_type, limit=limit, offset=offset)
    return {"events": events, "count": len(events)}


@router.post("/companies/{company_id}/twin/events")
def api_emit_twin_event(
    company_id: int,
    request: TwinEventRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_user_company(db, company_id, current_user)
    if request.event_type not in ALLOWED_EVENT_TYPES:
        raise HTTPException(status_code=422, detail=f"Invalid event_type. Must be one of: {', '.join(sorted(ALLOWED_EVENT_TYPES))}")
    try:
        event = emit_twin_event(db, company_id, request.event_type, request.source, request.payload)
        return event.to_dict()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to emit twin event")


@router.post("/companies/{company_id}/twin/simulate")
def api_run_twin_simulation(
    company_id: int,
    request: TwinSimulationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = get_user_company(db, company_id, current_user)
    scenario_config = {
        "scenario_name": request.scenario_name,
        "pricing_change_pct": request.pricing_change_pct,
        "growth_uplift_pct": request.growth_uplift_pct,
        "burn_reduction_pct": request.burn_reduction_pct,
        "fundraise_month": request.fundraise_month,
        "fundraise_amount": request.fundraise_amount,
        "hiring_plan": request.hiring_plan,
    }
    result = run_twin_simulation(db, company_id, scenario_config)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/companies/{company_id}/twin/decisions")
def api_get_decision_memory(
    company_id: int,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_user_company(db, company_id, current_user)
    decisions = get_decision_memory(db, company_id, limit=limit)
    return {"decisions": decisions, "count": len(decisions)}


@router.get("/companies/{company_id}/twin/history")
def api_get_twin_history(
    company_id: int,
    months: int = Query(12, ge=1, le=60),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_user_company(db, company_id, current_user)
    history = get_twin_history(db, company_id, months=months)
    return history
