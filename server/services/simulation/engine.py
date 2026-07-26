import asyncio
import json
import logging
import random
import uuid
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime

from .types import (
    AgentPersona, AgentAction, AgentType, ActionType,
    CompanyState, SimulationConfig, SimulationResult, SimulationStatus,
)
from .agents import agent_decide
from .agent_config import generate_agent_personas
from .memory import AgentMemoryManager
from .report_generator import generate_simulation_report

logger = logging.getLogger(__name__)


class SimulationEngine:
    def __init__(self, llm_client, model: str = "gpt-5.6-luna"):
        self.llm_client = llm_client
        self.model = model
        self.memory_manager = AgentMemoryManager()

    async def run_simulation(
        self,
        initial_state: CompanyState,
        scenario_params: Dict[str, Any],
        total_rounds: int = 24,
        progress_callback: Optional[Callable] = None,
        event_callback: Optional[Callable] = None,
    ) -> SimulationResult:
        simulation_id = f"sim_{uuid.uuid4().hex[:12]}"
        self.memory_manager.reset()

        if progress_callback:
            await self._call(progress_callback, "generating_agents", 0, "Generating agent personas...")

        agents = await generate_agent_personas(
            initial_state, scenario_params, self.llm_client, self.model
        )

        if progress_callback:
            await self._call(progress_callback, "generating_agents", 100,
                             f"Generated {len(agents)} agent personas")

        config = SimulationConfig(
            simulation_id=simulation_id,
            total_rounds=total_rounds,
            agents=agents,
            initial_state=CompanyState(**initial_state.to_dict()),
            scenario_params=scenario_params,
        )

        result = SimulationResult(
            simulation_id=simulation_id,
            config=config,
            status=SimulationStatus.RUNNING,
        )

        current_state = CompanyState(**initial_state.to_dict())
        all_actions: List[AgentAction] = []

        if progress_callback:
            await self._call(progress_callback, "simulating", 0, "Starting simulation...")

        for round_num in range(1, total_rounds + 1):
            active_agents = self._select_active_agents(agents, round_num, total_rounds)
            round_actions = []

            for agent in active_agents:
                memory = self.memory_manager.get_memory(agent.id)

                action = await agent_decide(
                    agent=agent,
                    company_state=current_state,
                    recent_actions=all_actions[-15:],
                    round_num=round_num,
                    total_rounds=total_rounds,
                    memory=memory,
                    llm_client=self.llm_client,
                    model=self.model,
                )

                if action:
                    current_state.apply_action_impact(action.impact)
                    self.memory_manager.add_memory(
                        agent.id,
                        f"Month {round_num}: I {action.description}. Result: {json.dumps(action.impact)}",
                    )
                    round_actions.append(action)
                    all_actions.append(action)

                    if event_callback:
                        await self._call_event(event_callback, action)

            self._apply_monthly_dynamics(current_state)

            result.rounds.append({
                "round": round_num,
                "month_label": f"Month {round_num}",
                "state": current_state.to_dict(),
                "actions": [a.to_dict() for a in round_actions],
                "active_agent_count": len(active_agents),
            })

            if progress_callback:
                pct = int((round_num / total_rounds) * 100)
                await self._call(
                    progress_callback, "simulating", pct,
                    f"Month {round_num}/{total_rounds} — {len(round_actions)} agent actions",
                )

        result.all_actions = all_actions
        result.final_state = current_state
        result.status = SimulationStatus.COMPLETED

        if progress_callback:
            await self._call(progress_callback, "generating_report", 0, "Compiling analysis report...")

        report = await generate_simulation_report(result, self.llm_client, self.model)
        result.report = report

        if progress_callback:
            await self._call(progress_callback, "generating_report", 100, "Report complete")

        return result

    def _select_active_agents(
        self, agents: List[AgentPersona], round_num: int, total_rounds: int,
    ) -> List[AgentPersona]:
        stage_progress = round_num / total_rounds

        if stage_progress < 0.33:
            stage_mult = {
                "founder": 1.5, "investor": 0.3, "customer": 0.5,
                "team": 1.2, "market": 0.6, "competitor": 0.4, "advisor": 0.8,
            }
        elif stage_progress < 0.66:
            stage_mult = {
                "founder": 1.0, "investor": 1.0, "customer": 1.0,
                "team": 1.0, "market": 1.0, "competitor": 1.0, "advisor": 1.0,
            }
        else:
            stage_mult = {
                "founder": 0.8, "investor": 1.5, "customer": 1.3,
                "team": 0.7, "market": 1.2, "competitor": 1.3, "advisor": 0.5,
            }

        active = []
        for agent in agents:
            prob = agent.activity_level
            mult = stage_mult.get(agent.agent_type.value, 1.0)
            final_prob = min(prob * mult, 0.95)
            if random.random() < final_prob:
                active.append(agent)

        founder_ids = [a.id for a in active if a.agent_type == AgentType.FOUNDER]
        if not founder_ids:
            founders = [a for a in agents if a.agent_type == AgentType.FOUNDER]
            if founders:
                active.append(founders[0])

        return active

    def _apply_monthly_dynamics(self, state: CompanyState):
        if state.growth_rate > 1:
            state.growth_rate = state.growth_rate / 100.0
        state.growth_rate = max(-0.1, min(0.5, state.growth_rate))
        state.churn_rate = max(0.0, min(0.2, state.churn_rate))

        state.cash += state.mrr - state.burn_rate

        if state.growth_rate > 0 and state.customers > 0:
            new_customers = max(1, int(state.customers * state.growth_rate))
            new_customers = min(new_customers, max(50, int(state.customers * 0.5)))
            avg_revenue = state.mrr / max(state.customers, 1)
            state.customers += new_customers
            state.mrr += new_customers * avg_revenue

        churned = int(state.customers * state.churn_rate)
        state.customers = max(0, state.customers - churned)
        if churned > 0 and state.customers > 0:
            avg_revenue = state.mrr / max(state.customers + churned, 1)
            state.mrr = max(0, state.mrr - churned * avg_revenue)

        state.mrr = min(state.mrr, 100_000_000)
        state.customers = min(state.customers, 1_000_000)

        state.arr = state.mrr * 12
        state.runway_months = state.cash / state.burn_rate if state.burn_rate > 0 else 999

    async def _call(self, callback, step, pct, msg):
        if asyncio.iscoroutinefunction(callback):
            await callback(step, pct, msg)
        else:
            callback(step, pct, msg)

    async def _call_event(self, callback, action):
        if asyncio.iscoroutinefunction(callback):
            await callback(action)
        else:
            callback(action)
