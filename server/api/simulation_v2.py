import asyncio
import json
import logging
import threading
import time
import traceback
from collections import OrderedDict
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from server.core.db import get_db
from server.core.security import get_current_user
from server.core.company_access import get_user_company
from server.core.plan_usage import PLAN_QUOTA_SIMULATION, reserve_monthly_quota
from server.models import User
from server.lib.llm.openai_client import get_openai_client
from server.services.simulation.engine import SimulationEngine
from server.services.simulation.input_normalization import inputs_for_simulation_request
from server.services.simulation.types import CompanyState, AgentAction, net_runway_months

logger = logging.getLogger(__name__)
router = APIRouter(tags=["simulation-v2"])

class _ResultStore:
    """Bounded, expiring, owner-scoped cache of finished runs.

    Process-local: with several workers a GET can land on a worker that did not
    run the simulation and answer 404. The full result is already streamed in
    the run's "complete" event, so this is only a short-lived convenience.
    """

    def __init__(self, max_items: int = 200, ttl_seconds: float = 6 * 3600):
        self.max_items = max_items
        self.ttl_seconds = ttl_seconds
        self._items: "OrderedDict[str, tuple[float, int, dict]]" = OrderedDict()
        self._lock = threading.Lock()

    def put(self, simulation_id: str, owner_user_id: int, result: dict) -> None:
        with self._lock:
            self._items[simulation_id] = (time.monotonic(), owner_user_id, result)
            self._items.move_to_end(simulation_id)
            self._evict()

    def get(self, simulation_id: str, owner_user_id: int) -> Optional[dict]:
        with self._lock:
            self._evict()
            entry = self._items.get(simulation_id)
            if entry is None or entry[1] != owner_user_id:
                return None
            return entry[2]

    def _evict(self) -> None:
        cutoff = time.monotonic() - self.ttl_seconds
        while self._items:
            key, (stored_at, _, _) = next(iter(self._items.items()))
            if stored_at >= cutoff and len(self._items) <= self.max_items:
                break
            self._items.popitem(last=False)

    def __len__(self) -> int:
        return len(self._items)


_results_store = _ResultStore()


class SimulationV2Request(BaseModel):
    total_rounds: int = Field(default=24, ge=6, le=60)
    monthly_revenue: float = Field(default=50000, ge=0)
    # GROSS monthly spend (all costs incl. COGS), NOT the dashboard's net burn:
    # the engine does cash += monthly_revenue - monthly_burn.
    monthly_burn: float = Field(default=80000)
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


def build_simulation_v2_state(normalized: dict) -> tuple[CompanyState, dict, int]:
    """Build the engine inputs from normalised values.

    The formulas match the historical inline construction: ARR is 12x revenue,
    and runway is cash / (burn - revenue) -- monthly_burn is gross spend -- or
    999 when revenue covers spend.
    """
    monthly_revenue = normalized["monthly_revenue"]
    monthly_burn = normalized["monthly_burn"]
    cash_balance = normalized["cash_balance"]
    initial_state = CompanyState(
        mrr=monthly_revenue,
        arr=monthly_revenue * 12,
        burn_rate=monthly_burn,
        cash=cash_balance,
        runway_months=net_runway_months(cash_balance, monthly_revenue, monthly_burn),
        customers=normalized["customers"],
        churn_rate=normalized["churn_rate"],
        team_size=normalized["team_size"],
        team_morale=normalized["team_morale"],
        product_quality=normalized["product_quality"],
        market_fit=normalized["market_fit"],
        brand_reputation=normalized["brand_reputation"],
        investor_confidence=normalized["investor_confidence"],
        growth_rate=normalized["growth_rate"],
    )
    scenario_params = {
        "funding_climate": normalized["funding_climate"],
        "market_growth": normalized["market_growth"],
        "market_volatility": normalized["market_volatility"],
    }
    return initial_state, scenario_params, normalized["total_rounds"]


@router.post("/simulation/v2/run")
async def run_simulation_v2_sse(
    request: SimulationV2Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    client = get_openai_client()
    if not client:
        raise HTTPException(status_code=503, detail="LLM service not configured")

    reserve_monthly_quota(db, current_user, PLAN_QUOTA_SIMULATION)

    normalized, input_provenance = inputs_for_simulation_request(request)
    initial_state, scenario_params, total_rounds = build_simulation_v2_state(normalized)

    engine = SimulationEngine(llm_client=client, model="gpt-5-mini")

    event_queue: asyncio.Queue = asyncio.Queue()

    async def progress_callback(step: str, pct: int, msg: str):
        await event_queue.put(_sse_event("progress", {"step": step, "pct": pct, "msg": msg}))

    async def event_callback(action: AgentAction):
        await event_queue.put(_sse_event("agent_event", {"data": action.to_dict()}))

    async def run_engine():
        try:
            result = await asyncio.wait_for(
                engine.run_simulation(
                    initial_state=initial_state,
                    scenario_params=scenario_params,
                    total_rounds=total_rounds,
                    progress_callback=progress_callback,
                    event_callback=event_callback,
                ),
                timeout=180.0,
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
                "input_provenance": input_provenance,
            }

            _results_store.put(result.simulation_id, current_user.id, complete_data)

            await event_queue.put(_sse_event("complete", {"result": complete_data}))
        except asyncio.TimeoutError:
            logger.warning("Flight Simulator timed out after 180s")
            await event_queue.put(_sse_event("error", {"message": "Simulation timed out after 3 minutes. Try reducing the number of rounds or try again."}))
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
    # Another user's id answers 404, same as an unknown one.
    result = _results_store.get(simulation_id, current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return result
