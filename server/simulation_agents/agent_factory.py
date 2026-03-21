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


def create_agents(company_data: Dict[str, Any], scenario_config: Dict[str, Any] = None) -> List[BaseAgent]:
    scenario = scenario_config or {}

    cash = company_data.get("cash_balance", 0) or 0
    burn = company_data.get("monthly_burn", 0) or 0
    revenue = company_data.get("monthly_revenue", 0) or 0
    growth = company_data.get("growth_rate", 5)
    headcount = company_data.get("headcount", 10)
    churn = company_data.get("churn_rate", 0.05)
    customers = company_data.get("customers", 100)

    net_burn = max(0, burn - revenue)
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
    burn = company_data.get("monthly_burn", 0) or 0
    revenue = company_data.get("monthly_revenue", 0) or 0
    growth = company_data.get("growth_rate", 5)

    net_burn = max(0, burn - revenue)
    runway = cash / net_burn if net_burn > 0 else 999

    return {
        "cash_balance": cash,
        "monthly_burn": burn,
        "monthly_revenue": revenue,
        "growth_rate": growth,
        "gross_margin": company_data.get("gross_margin", 70),
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
