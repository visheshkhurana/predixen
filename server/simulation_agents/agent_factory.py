"""
Agent Factory — creates and initializes agents from company data.
"""

import json
import logging
from typing import Dict, Any, List

from server.simulation_agents.agent_models import (
    BaseAgent, FounderAgent, InvestorAgent, CustomerAgent, TeamAgent, MarketAgent
)

logger = logging.getLogger(__name__)


def _num(value, default=0.0) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    return v if v == v else default


def gross_margin_pct_or_none(company_data: Dict[str, Any]):
    """Gross margin as a percentage, from a fraction or a percentage; None if unknown."""
    raw = company_data.get("gross_margin", company_data.get("grossMargin"))
    if raw is None:
        return None
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    if v != v:
        return None
    return v * 100.0 if abs(v) <= 1.0 else v


def resolve_burn(company_data: Dict[str, Any], gross_margin_pct: float) -> Dict[str, float]:
    """Split the company's burn into the pieces the agent simulation needs.

    ``monthly_burn`` is the canonical NET burn (total costs incl. COGS minus
    revenue -- CompanyState.monthly_burn, the dashboard's burnRate).
    ``expenses_monthly``, when present, is total costs incl. COGS.

    The monthly loop does ``cash += revenue * gross_margin - operating_costs``,
    so operating_costs must EXCLUDE COGS: total costs - revenue * (1 - gm).
    Month one then moves cash by exactly -net_burn whatever the margin. The old
    code fed net burn in as if it were gross spend, so any company with revenue
    above its net burn showed runway 999.
    """
    revenue = max(0.0, _num(company_data.get("monthly_revenue")))
    net_burn = max(0.0, _num(company_data.get("monthly_burn")))
    expenses = max(0.0, _num(company_data.get("expenses_monthly")))
    if net_burn > 0:
        total_costs = net_burn + revenue
    elif expenses > 0:
        total_costs = expenses
    else:
        total_costs = revenue  # breakeven: net burn 0 and no cost detail
    cogs = revenue * (1 - gross_margin_pct / 100.0)
    operating_costs = max(0.0, total_costs - cogs)
    return {
        "net_burn": max(0.0, total_costs - revenue),
        "total_costs": total_costs,
        "operating_costs": operating_costs,
    }


def create_agents(company_data: Dict[str, Any], scenario_config: Dict[str, Any] = None) -> List[BaseAgent]:
    scenario = scenario_config or {}

    cash = company_data.get("cash_balance", 0) or 0
    churn = company_data.get("churn_rate", 0.05)

    # monthly_burn is already NET burn; subtracting revenue again zeroed it.
    gm = gross_margin_pct_or_none(company_data)
    net_burn = resolve_burn(company_data, gm if gm is not None else 70.0)["net_burn"]
    runway = cash / net_burn if net_burn > 0 else 999

    confidence = 0.7
    if runway < 6:
        confidence = 0.3
    elif runway < 12:
        confidence = 0.5
    elif runway > 24:
        confidence = 0.85

    founder = FounderAgent({
        "risk_tolerance": scenario.get("founder_risk_tolerance", 0.6),
        "confidence": confidence,
        "hiring_bias": scenario.get("hiring_aggressiveness", 0.5),
    })

    investor = InvestorAgent({
        "investment_threshold": scenario.get("investor_threshold", 0.6),
        "risk_tolerance": scenario.get("investor_risk_tolerance", 0.4),
    })

    customer = CustomerAgent({
        "churn_rate": churn if churn > 0 else 0.05,
        "acquisition_rate": scenario.get("customer_acquisition_rate", 0.1),
        "satisfaction": scenario.get("customer_satisfaction", 0.7),
        "price_sensitivity": scenario.get("price_sensitivity", 0.5),
    })

    team = TeamAgent({
        "morale": 0.8 if runway > 12 else 0.6 if runway > 6 else 0.4,
        "productivity": 0.7,
    })

    market = MarketAgent({
        "tam_growth": scenario.get("market_growth", 0.15),
        "volatility": scenario.get("market_volatility", 0.2),
    })

    return [founder, investor, customer, team, market]


def build_initial_company_state(company_data: Dict[str, Any]) -> Dict[str, Any]:
    cash = company_data.get("cash_balance", 0) or 0
    revenue = company_data.get("monthly_revenue", 0) or 0
    growth = company_data.get("growth_rate", 5)

    gm = gross_margin_pct_or_none(company_data)
    gm_assumed = gm is None
    if gm is None:
        gm = 70.0
    burn = resolve_burn(company_data, gm)
    net_burn = burn["net_burn"]
    runway = cash / net_burn if net_burn > 0 else 999

    return {
        "cash_balance": cash,
        # Operating costs EXCLUDING COGS (COGS scales with revenue through the
        # gross margin in _advance_financials). Agent events scale this figure.
        "monthly_burn": burn["operating_costs"],
        "net_burn": net_burn,
        "monthly_revenue": revenue,
        "growth_rate": growth,
        "gross_margin": gm,
        "gross_margin_assumed": gm_assumed,
        "runway_months": min(runway, 999),
        "headcount": company_data.get("headcount", 10),
        "customers": company_data.get("customers", 100),
        "churn_rate": company_data.get("churn_rate", 0.05),
        "burn_multiple": net_burn / max(revenue, 1) if revenue > 0 else 10,
        "arpu": company_data.get("arpu", 100),
        "product_quality": 0.7,
        "recent_layoffs": False,
        "pricing_change": 0,
    }
