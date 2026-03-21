import asyncio
import json
import logging
import traceback
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from server.core.db import get_db
from server.core.security import get_current_user
from server.core.company_access import get_user_company
from server.models import User
from server.lib.llm.openai_client import get_openai_client
from server.services.simulation.engine import SimulationEngine
from server.services.simulation.types import CompanyState, AgentAction

logger = logging.getLogger(__name__)
router = APIRouter(tags=["simulation-v2"])

_results_store: dict = {}


class SimulationV2Request(BaseModel):
    total_rounds: int = Field(default=24, ge=6, le=60)
    monthly_revenue: float = Field(default=50000, ge=0)
    monthly_burn: float = Field(default=80000, ge=0)
    cash_balance: float = Field(default=500000, ge=0)
    customers: int = Field(default=50, ge=0)
    team_size: int = Field(default=10, ge=1)
    growth_rate: float = Field(default=0.05, ge=-0.5, le=1.0)
    churn_rate: float = Field(default=0.03, ge=0.0, le=0.5)
    funding_climate: float = Field(default=0.6, ge=0.0, le=1.0)
    market_growth: float = Field(default=0.5, ge=0.0, le=1.0)
    market_volatility: float = Field(default=0.1, ge=0.0, le=0.5)


def _sse_event(event_type: str, data: dict) -> str:
    payload = json.dumps({"type": event_type, **data}, default=str)
    return f"data: {payload}\n\n"


@router.post("/simulation/v2/run")
async def run_simulation_v2_sse(
    request: SimulationV2Request,
    current_user: User = Depends(get_current_user),
):
    client = get_openai_client()
    if not client:
        raise HTTPException(status_code=503, detail="LLM service not configured")

    initial_state = CompanyState(
        mrr=request.monthly_revenue,
        arr=request.monthly_revenue * 12,
        burn_rate=request.monthly_burn,
        cash=request.cash_balance,
        runway_months=request.cash_balance / request.monthly_burn if request.monthly_burn > 0 else 999,
        customers=request.customers,
        churn_rate=request.churn_rate,
        team_size=request.team_size,
        team_morale=0.7,
        product_quality=0.5,
        market_fit=0.5,
        brand_reputation=0.5,
        investor_confidence=0.5,
        growth_rate=request.growth_rate,
    )

    scenario_params = {
        "funding_climate": request.funding_climate,
        "market_growth": request.market_growth,
        "market_volatility": request.market_volatility,
    }

    engine = SimulationEngine(llm_client=client, model="gpt-4o-mini")

    event_queue: asyncio.Queue = asyncio.Queue()

    async def progress_callback(step: str, pct: int, msg: str):
        await event_queue.put(_sse_event("progress", {"step": step, "pct": pct, "msg": msg}))

    async def event_callback(action: AgentAction):
        await event_queue.put(_sse_event("agent_event", {"data": action.to_dict()}))

    async def run_engine():
        try:
            result = await engine.run_simulation(
                initial_state=initial_state,
                scenario_params=scenario_params,
                total_rounds=request.total_rounds,
                progress_callback=progress_callback,
                event_callback=event_callback,
            )

            for rnd in result.rounds:
                await event_queue.put(_sse_event("round_complete", {
                    "round": rnd["round"],
                    "state": rnd["state"],
                    "action_count": len(rnd["actions"]),
                }))

            agents_data = [a.to_dict() for a in result.config.agents]
            await event_queue.put(_sse_event("agents_generated", {"agents": agents_data}))

            complete_data = {
                "simulation_id": result.simulation_id,
                "status": result.status.value,
                "total_rounds": result.config.total_rounds,
                "total_actions": len(result.all_actions),
                "initial_state": result.config.initial_state.to_dict(),
                "final_state": result.final_state.to_dict(),
                "report": result.report,
                "rounds": result.rounds,
                "all_actions": [a.to_dict() for a in result.all_actions],
                "agents": agents_data,
            }

            _results_store[result.simulation_id] = complete_data

            await event_queue.put(_sse_event("complete", {"result": complete_data}))
        except Exception as e:
            logger.error(f"Simulation engine error: {e}\n{traceback.format_exc()}")
            await event_queue.put(_sse_event("error", {"message": str(e)}))
        finally:
            await event_queue.put(None)

    async def event_generator():
        task = asyncio.create_task(run_engine())
        try:
            while True:
                event = await event_queue.get()
                if event is None:
                    break
                yield event
        except asyncio.CancelledError:
            task.cancel()
            raise
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/simulation/v2/{simulation_id}")
async def get_simulation_v2_result(
    simulation_id: str,
    current_user: User = Depends(get_current_user),
):
    result = _results_store.get(simulation_id)
    if not result:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return result
