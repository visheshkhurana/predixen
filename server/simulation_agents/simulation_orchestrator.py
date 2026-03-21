"""
Simulation Orchestrator — runs multi-agent simulation loops.

Steps:
1. Load Digital Twin state
2. Build knowledge graph
3. Initialize agents
4. Run N rounds (each round = 1 month)
5. Collect events, update environment, track outcomes
"""

import json
import math
import random
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from server.simulation_agents.agent_models import BaseAgent, AgentEvent
from server.simulation_agents.agent_factory import create_agents, build_initial_company_state
from server.simulation_agents.agent_memory import AgentMemoryStore
from server.simulation_agents.environment_engine import EnvironmentEngine
from server.simulation_agents.knowledge_graph import build_company_graph

logger = logging.getLogger(__name__)


def run_agent_simulation(
    db,
    company_id: int,
    scenario_inputs: Dict[str, Any] = None,
    num_rounds: int = 24,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    if seed is not None:
        random.seed(seed)

    scenario = scenario_inputs or {}

    graph = build_company_graph(db, company_id)
    entities = graph.get("entities", {})
    company_financials = entities.get("financials", {})
    company_info = entities.get("company", {})

    override_map = {
        "monthly_revenue": "monthly_revenue",
        "monthly_burn": "monthly_burn",
        "cash_balance": "cash_balance",
        "growth_rate": "growth_rate",
        "headcount": "headcount",
        "gross_margin": "gross_margin",
    }
    for scenario_key, fin_key in override_map.items():
        if scenario_key in scenario:
            company_financials[fin_key] = scenario[scenario_key]

    for alt_key, real_key in [("revenue_monthly", "monthly_revenue"), ("expenses_monthly", "monthly_burn")]:
        if alt_key in company_financials and real_key not in company_financials:
            company_financials[real_key] = company_financials[alt_key]

    company_state = build_initial_company_state(company_financials)
    agents = create_agents(company_financials, scenario)
    memory = AgentMemoryStore()

    env_config = {
        "initial_funding_climate": scenario.get("funding_climate", 0.6),
        "initial_market_growth": scenario.get("market_growth", 0.5),
        "initial_competition": scenario.get("competition", 0.4),
        "volatility": scenario.get("market_volatility", 0.1),
        "market_trend": scenario.get("market_trend", "neutral"),
    }
    environment = EnvironmentEngine(env_config)

    all_events: List[Dict[str, Any]] = []
    monthly_snapshots: List[Dict[str, Any]] = []
    agent_states_history: List[Dict[str, Any]] = []

    growth_rate = company_state.get("growth_rate", 5) / 100
    gross_margin = company_state.get("gross_margin", 70) / 100

    hiring_rate = scenario.get("hiring_rate", 0)
    pricing_change = scenario.get("pricing_change", 0)
    marketing_multiplier = scenario.get("marketing_spend_multiplier", 1.0)

    for month in range(1, num_rounds + 1):
        env_state = environment.step(month)

        for agent in agents:
            agent.observe(env_state, company_state, month)

        round_events: List[AgentEvent] = []
        for agent in agents:
            events = agent.act(env_state, company_state, month)
            round_events.extend(events)

            memory.record(
                agent.agent_type.value, month,
                "state", agent.get_state_summary()
            )

        _apply_events_to_state(company_state, round_events, env_state)

        _advance_financials(
            company_state, month, growth_rate, gross_margin,
            hiring_rate, pricing_change, marketing_multiplier, env_state
        )

        for event in round_events:
            all_events.append(event.to_dict())

        monthly_snapshots.append({
            "month": month,
            "cash_balance": round(company_state["cash_balance"], 0),
            "monthly_revenue": round(company_state["monthly_revenue"], 0),
            "monthly_burn": round(company_state["monthly_burn"], 0),
            "runway_months": round(company_state["runway_months"], 1),
            "headcount": company_state.get("headcount", 0),
            "customers": company_state.get("customers", 0),
            "growth_rate": round(company_state.get("growth_rate", 0), 2),
            "survival": company_state["cash_balance"] > 0,
        })

        agent_states_history.append({
            "month": month,
            "agents": {a.agent_type.value: a.get_state_summary() for a in agents},
        })

    result = _compile_results(
        company_state, monthly_snapshots, all_events,
        agent_states_history, environment, company_info, scenario
    )
    result["knowledgeGraph"] = {"nodes": graph["nodes"][:20], "edges": graph["edges"][:30]}

    return result


def _apply_events_to_state(
    company: Dict[str, Any],
    events: List[AgentEvent],
    env_state: Dict[str, float],
):
    for event in events:
        impact = event.impact
        if "burn_increase" in impact:
            company["monthly_burn"] = company.get("monthly_burn", 0) + impact["burn_increase"]
        if "burn_reduction_pct" in impact:
            company["monthly_burn"] *= (1 - impact["burn_reduction_pct"])
            company["recent_layoffs"] = True
        if "headcount_change" in impact:
            company["headcount"] = max(1, company.get("headcount", 10) + impact["headcount_change"])
        if "burn_multiplier" in impact:
            company["monthly_burn"] *= impact["burn_multiplier"]
        if "revenue_impact" in impact:
            company["monthly_revenue"] = max(0, company.get("monthly_revenue", 0) + impact["revenue_impact"])
        if "productivity_multiplier" in impact:
            company["product_quality"] = company.get("product_quality", 0.7) * impact["productivity_multiplier"]
        if "funding_climate_change" in impact:
            env_state["funding_climate"] = max(0.05, min(0.95,
                env_state.get("funding_climate", 0.5) + impact["funding_climate_change"]))
        if "competition_intensity_change" in impact:
            env_state["competition_intensity"] = max(0.05, min(0.95,
                env_state.get("competition_intensity", 0.4) + impact["competition_intensity_change"]))
        if "team_morale" in impact:
            pass
        if "potential_raise" in impact and impact.get("funding_probability", 0) > 0.5:
            if random.random() < impact["funding_probability"] * 0.4:
                company["cash_balance"] += impact["potential_raise"]


def _advance_financials(
    company: Dict[str, Any],
    month: int,
    growth_rate: float,
    gross_margin: float,
    hiring_rate: float,
    pricing_change: float,
    marketing_multiplier: float,
    env_state: Dict[str, float],
):
    revenue = company.get("monthly_revenue", 0)
    burn = company.get("monthly_burn", 0)
    cash = company.get("cash_balance", 0)

    effective_growth = growth_rate * (1 + random.gauss(0, 0.02))
    effective_growth *= (0.8 + env_state.get("market_growth", 0.5) * 0.4)

    if pricing_change != 0:
        effective_growth += pricing_change / 100 * 0.3

    new_revenue = revenue * (1 + effective_growth)
    company["monthly_revenue"] = max(0, new_revenue)

    if hiring_rate > 0 and month % 3 == 0:
        new_hires = max(1, int(hiring_rate))
        company["headcount"] = company.get("headcount", 10) + new_hires
        company["monthly_burn"] += new_hires * random.uniform(8000, 15000)

    if marketing_multiplier != 1.0:
        marketing_cost_change = burn * 0.2 * (marketing_multiplier - 1.0)
        company["monthly_burn"] += marketing_cost_change

    burn = company["monthly_burn"]
    net_cashflow = new_revenue * gross_margin - burn
    company["cash_balance"] = cash + net_cashflow

    net_burn = max(0, burn - new_revenue * gross_margin)
    company["runway_months"] = company["cash_balance"] / net_burn if net_burn > 0 else 999

    company["growth_rate"] = effective_growth * 100
    company["burn_multiple"] = net_burn / max(new_revenue, 1) if new_revenue > 0 else 10


def _compile_results(
    final_state: Dict[str, Any],
    snapshots: List[Dict[str, Any]],
    events: List[Dict[str, Any]],
    agent_states: List[Dict[str, Any]],
    environment: EnvironmentEngine,
    company_info: Dict[str, Any],
    scenario: Dict[str, Any],
) -> Dict[str, Any]:
    survived_months = sum(1 for s in snapshots if s["survival"])
    total_months = len(snapshots)
    survival_probability = (survived_months / total_months * 100) if total_months > 0 else 0

    cash_trajectory = [s["cash_balance"] for s in snapshots]
    revenue_trajectory = [s["monthly_revenue"] for s in snapshots]
    runway_trajectory = [min(s["runway_months"], 999) for s in snapshots]

    cash_at_end = final_state.get("cash_balance", 0)
    runway_at_end = min(final_state.get("runway_months", 0), 999)

    funding_events = [e for e in events if e["eventType"] in ("investment_interest", "investment_pass")]
    funding_probability = 0
    if funding_events:
        interest = sum(1 for e in funding_events if e["eventType"] == "investment_interest")
        funding_probability = interest / len(funding_events) * 100

    risk_events = [e for e in events if e["severity"] in ("warning", "danger")]

    key_risks = []
    risk_types = {}
    for e in risk_events:
        rt = e["eventType"]
        risk_types[rt] = risk_types.get(rt, 0) + 1
    for rt, count in sorted(risk_types.items(), key=lambda x: -x[1])[:5]:
        sample = next((e for e in risk_events if e["eventType"] == rt), None)
        key_risks.append({
            "type": rt,
            "occurrences": count,
            "description": sample["description"] if sample else rt,
            "severity": sample["severity"] if sample else "warning",
        })

    recommendations = _generate_recommendations(final_state, snapshots, events, key_risks)

    return {
        "simulationId": None,
        "companyName": company_info.get("name", "Your Company"),
        "scenarioInputs": scenario,
        "numRounds": total_months,
        "summary": {
            "survivalProbability": round(survival_probability, 1),
            "fundingProbability": round(funding_probability, 1),
            "finalCash": round(cash_at_end, 0),
            "finalRunway": round(runway_at_end, 1),
            "finalRevenue": round(final_state.get("monthly_revenue", 0), 0),
            "finalHeadcount": final_state.get("headcount", 0),
            "finalCustomers": final_state.get("customers", 0),
            "totalEvents": len(events),
            "riskEvents": len(risk_events),
        },
        "timeline": snapshots,
        "events": events,
        "agentStates": agent_states,
        "environment": {
            "history": environment.get_history(),
            "shocks": environment.get_shocks(),
        },
        "keyRisks": key_risks,
        "recommendations": recommendations,
        "trajectories": {
            "cash": cash_trajectory,
            "revenue": revenue_trajectory,
            "runway": runway_trajectory,
        },
    }


def _generate_recommendations(
    state: Dict[str, Any],
    snapshots: List[Dict[str, Any]],
    events: List[Dict[str, Any]],
    risks: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    recs = []
    runway = state.get("runway_months", 999)
    burn = state.get("monthly_burn", 0)
    revenue = state.get("monthly_revenue", 0)

    if runway < 6:
        recs.append({
            "priority": "critical",
            "title": "Extend runway immediately",
            "description": f"Runway is critically low at {runway:.0f} months. Consider cutting burn by 20-30% or initiating emergency fundraising.",
            "impact": "Could extend runway by 3-6 months",
            "category": "survival",
        })

    if burn > revenue * 2 and revenue > 0:
        recs.append({
            "priority": "high",
            "title": "Reduce burn multiple",
            "description": f"Burn multiple is {burn/max(revenue,1):.1f}x — you're spending ${burn/max(revenue,1):.1f} for every $1 of revenue. Target below 2x.",
            "impact": "Improves investor attractiveness and extends runway",
            "category": "efficiency",
        })

    churn_events = sum(1 for e in events if e["eventType"] == "churn_spike")
    if churn_events > 3:
        recs.append({
            "priority": "high",
            "title": "Address customer retention",
            "description": f"Customer churn was flagged {churn_events} times during the simulation. Focus on retention before acquisition.",
            "impact": "Reducing churn by 1% could increase LTV by 5-10%",
            "category": "growth",
        })

    morale_events = sum(1 for e in events if e["eventType"] == "morale_crisis")
    if morale_events > 0:
        recs.append({
            "priority": "medium",
            "title": "Improve team morale",
            "description": "Team morale hit critical levels during the simulation, reducing productivity and increasing attrition risk.",
            "impact": "Higher morale = 20-30% better productivity",
            "category": "team",
        })

    if not any(e["eventType"] == "investment_interest" for e in events) and runway < 12:
        recs.append({
            "priority": "high",
            "title": "Improve fundraising readiness",
            "description": "No investor interest was generated during the simulation. Focus on improving growth metrics and unit economics.",
            "impact": "Strong metrics increase funding probability significantly",
            "category": "fundraising",
        })

    growth = state.get("growth_rate", 0)
    if growth > 15:
        recs.append({
            "priority": "medium",
            "title": "Double down on growth",
            "description": f"Growth rate of {growth:.1f}% is strong. Consider increasing marketing spend to capitalize on momentum.",
            "impact": "Accelerated growth improves fundraising position",
            "category": "growth",
        })

    if not recs:
        recs.append({
            "priority": "info",
            "title": "Company is on a healthy trajectory",
            "description": "The simulation shows stable growth with manageable risks. Continue monitoring key metrics.",
            "impact": "Stay the course",
            "category": "general",
        })

    return recs
