"""
Agent Models — defines the five core simulation agents.

Each agent has state, memory, goals, and decision rules.
Agents observe the environment and act each simulation round.
"""

import random
import math
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class AgentType(str, Enum):
    FOUNDER = "founder"
    INVESTOR = "investor"
    CUSTOMER = "customer"
    TEAM = "team"
    MARKET = "market"


class Sentiment(str, Enum):
    VERY_NEGATIVE = "very_negative"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    POSITIVE = "positive"
    VERY_POSITIVE = "very_positive"


@dataclass
class AgentEvent:
    month: int
    agent_type: str
    event_type: str
    description: str
    impact: Dict[str, float] = field(default_factory=dict)
    severity: str = "info"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "month": self.month,
            "agentType": self.agent_type,
            "eventType": self.event_type,
            "description": self.description,
            "impact": self.impact,
            "severity": self.severity,
            "metadata": self.metadata,
        }


@dataclass
class AgentState:
    sentiment: Sentiment = Sentiment.NEUTRAL
    confidence: float = 0.5
    risk_tolerance: float = 0.5
    activity_level: float = 0.5
    custom: Dict[str, Any] = field(default_factory=dict)


class BaseAgent:
    def __init__(self, agent_type: AgentType, config: Dict[str, Any] = None):
        self.agent_type = agent_type
        self.config = config or {}
        self.state = AgentState()
        self.memory: List[Dict[str, Any]] = []
        self.events: List[AgentEvent] = []

    def observe(self, environment: Dict[str, Any], company: Dict[str, Any], month: int):
        raise NotImplementedError

    def act(self, environment: Dict[str, Any], company: Dict[str, Any], month: int) -> List[AgentEvent]:
        raise NotImplementedError

    def remember(self, key: str, value: Any):
        self.memory.append({"key": key, "value": value, "timestamp": len(self.memory)})

    def recall(self, key: str) -> Optional[Any]:
        for item in reversed(self.memory):
            if item["key"] == key:
                return item["value"]
        return None

    def get_state_summary(self) -> Dict[str, Any]:
        return {
            "agentType": self.agent_type.value,
            "sentiment": self.state.sentiment.value,
            "confidence": round(self.state.confidence, 2),
            "riskTolerance": round(self.state.risk_tolerance, 2),
            "activityLevel": round(self.state.activity_level, 2),
            "custom": self.state.custom,
        }


class FounderAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(AgentType.FOUNDER, config)
        self.state.risk_tolerance = config.get("risk_tolerance", 0.6) if config else 0.6
        self.state.confidence = config.get("confidence", 0.7) if config else 0.7
        self.hiring_bias = config.get("hiring_bias", 0.5) if config else 0.5
        self.fundraising_urgency = 0.0

    def observe(self, environment: Dict[str, Any], company: Dict[str, Any], month: int):
        runway = company.get("runway_months", 18)
        burn = company.get("monthly_burn", 0)
        revenue = company.get("monthly_revenue", 0)
        growth = company.get("growth_rate", 0)

        if runway < 6:
            self.fundraising_urgency = min(1.0, self.fundraising_urgency + 0.3)
            self.state.confidence = max(0.1, self.state.confidence - 0.1)
        elif runway < 12:
            self.fundraising_urgency = min(1.0, self.fundraising_urgency + 0.1)
        else:
            self.fundraising_urgency = max(0.0, self.fundraising_urgency - 0.05)

        if growth > 10:
            self.state.confidence = min(1.0, self.state.confidence + 0.05)
        elif growth < 0:
            self.state.confidence = max(0.1, self.state.confidence - 0.05)

        if revenue > burn * 1.1:
            self.state.sentiment = Sentiment.VERY_POSITIVE
        elif revenue > burn * 0.8:
            self.state.sentiment = Sentiment.POSITIVE
        elif revenue > burn * 0.5:
            self.state.sentiment = Sentiment.NEUTRAL
        else:
            self.state.sentiment = Sentiment.NEGATIVE

    def act(self, environment: Dict[str, Any], company: Dict[str, Any], month: int) -> List[AgentEvent]:
        events = []
        runway = company.get("runway_months", 18)

        if self.fundraising_urgency > 0.7 and runway < 9:
            events.append(AgentEvent(
                month=month,
                agent_type=self.agent_type.value,
                event_type="fundraising_initiated",
                description=f"Founder begins fundraising — runway is {runway:.0f} months",
                impact={"burn_multiplier": 1.1, "founder_focus": -0.2},
                severity="warning",
            ))
            self.remember("fundraising_started", month)

        if self.state.confidence > 0.7 and self.hiring_bias > 0.5 and runway > 12:
            hire_prob = self.hiring_bias * self.state.confidence * 0.3
            if random.random() < hire_prob:
                events.append(AgentEvent(
                    month=month,
                    agent_type=self.agent_type.value,
                    event_type="hiring_decision",
                    description="Founder decides to accelerate hiring",
                    impact={"headcount_change": random.randint(1, 3), "burn_increase": random.uniform(5000, 15000)},
                    severity="info",
                ))

        if self.state.confidence < 0.3 and runway < 8:
            if random.random() < 0.4:
                cut_pct = random.uniform(0.1, 0.25)
                events.append(AgentEvent(
                    month=month,
                    agent_type=self.agent_type.value,
                    event_type="cost_cutting",
                    description=f"Founder initiates {cut_pct*100:.0f}% cost reduction",
                    impact={"burn_reduction_pct": cut_pct, "team_morale": -0.15},
                    severity="warning",
                ))

        return events


class InvestorAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(AgentType.INVESTOR, config)
        self.investment_threshold = config.get("investment_threshold", 0.6) if config else 0.6
        self.state.risk_tolerance = config.get("risk_tolerance", 0.4) if config else 0.4
        self.interest_level = 0.5
        self.last_evaluation_month = -1

    def observe(self, environment: Dict[str, Any], company: Dict[str, Any], month: int):
        growth = company.get("growth_rate", 0)
        burn_multiple = company.get("burn_multiple", 5)
        runway = company.get("runway_months", 18)
        market_sentiment = environment.get("funding_climate", 0.5)

        growth_score = min(1.0, max(0.0, growth / 20))
        efficiency_score = min(1.0, max(0.0, 1.0 - (burn_multiple - 1) / 4))
        runway_score = min(1.0, max(0.0, runway / 18))

        self.interest_level = (
            growth_score * 0.4 +
            efficiency_score * 0.25 +
            runway_score * 0.15 +
            market_sentiment * 0.2
        )

        if self.interest_level > 0.7:
            self.state.sentiment = Sentiment.POSITIVE
        elif self.interest_level > 0.4:
            self.state.sentiment = Sentiment.NEUTRAL
        else:
            self.state.sentiment = Sentiment.NEGATIVE

    def act(self, environment: Dict[str, Any], company: Dict[str, Any], month: int) -> List[AgentEvent]:
        events = []
        if month - self.last_evaluation_month < 3:
            return events
        self.last_evaluation_month = month

        funding_climate = environment.get("funding_climate", 0.5)

        if self.interest_level > self.investment_threshold and funding_climate > 0.4:
            invest_prob = self.interest_level * funding_climate
            if random.random() < invest_prob * 0.3:
                raise_amount = company.get("monthly_burn", 50000) * random.randint(12, 24)
                events.append(AgentEvent(
                    month=month,
                    agent_type=self.agent_type.value,
                    event_type="investment_interest",
                    description=f"Investor shows strong interest — potential ${raise_amount/1e6:.1f}M round",
                    impact={"funding_probability": invest_prob, "potential_raise": raise_amount},
                    severity="info",
                    metadata={"interest_level": round(self.interest_level, 2)},
                ))
        elif self.interest_level < 0.3:
            events.append(AgentEvent(
                month=month,
                agent_type=self.agent_type.value,
                event_type="investment_pass",
                description=f"Investor passes — growth insufficient at {company.get('growth_rate', 0):.1f}%",
                impact={"funding_probability": -0.1},
                severity="warning",
                metadata={"interest_level": round(self.interest_level, 2)},
            ))

        return events


class CustomerAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(AgentType.CUSTOMER, config)
        self.base_churn_rate = config.get("churn_rate", 0.05) if config else 0.05
        self.base_acquisition_rate = config.get("acquisition_rate", 0.1) if config else 0.1
        self.satisfaction = config.get("satisfaction", 0.7) if config else 0.7
        self.price_sensitivity = config.get("price_sensitivity", 0.5) if config else 0.5

    def observe(self, environment: Dict[str, Any], company: Dict[str, Any], month: int):
        product_quality = company.get("product_quality", 0.7)
        pricing_change = company.get("pricing_change", 0)
        market_competition = environment.get("competition_intensity", 0.5)

        self.satisfaction = max(0.1, min(1.0,
            self.satisfaction +
            product_quality * 0.05 -
            market_competition * 0.03 -
            abs(pricing_change) * self.price_sensitivity * 0.1
        ))

        if self.satisfaction > 0.7:
            self.state.sentiment = Sentiment.POSITIVE
        elif self.satisfaction > 0.4:
            self.state.sentiment = Sentiment.NEUTRAL
        else:
            self.state.sentiment = Sentiment.NEGATIVE

    def act(self, environment: Dict[str, Any], company: Dict[str, Any], month: int) -> List[AgentEvent]:
        events = []
        customers = company.get("customers", 100)
        if customers <= 0:
            customers = 100

        churn_modifier = (1 - self.satisfaction) * 0.5
        effective_churn = self.base_churn_rate + churn_modifier
        effective_churn = max(0.01, min(0.3, effective_churn + random.gauss(0, 0.01)))

        churned = int(customers * effective_churn)
        if churned > 0 and effective_churn > self.base_churn_rate * 1.5:
            events.append(AgentEvent(
                month=month,
                agent_type=self.agent_type.value,
                event_type="churn_spike",
                description=f"Customer churn elevated — {churned} customers lost ({effective_churn*100:.1f}% rate)",
                impact={"customers_lost": churned, "revenue_impact": -churned * company.get("arpu", 100)},
                severity="warning" if effective_churn > 0.1 else "info",
            ))

        growth_modifier = self.satisfaction * 0.3 + environment.get("market_growth", 0.5) * 0.2
        effective_acquisition = self.base_acquisition_rate * (1 + growth_modifier)
        new_customers = int(customers * effective_acquisition * random.uniform(0.7, 1.3))

        if new_customers > customers * 0.15:
            events.append(AgentEvent(
                month=month,
                agent_type=self.agent_type.value,
                event_type="acquisition_surge",
                description=f"Strong customer acquisition — {new_customers} new customers added",
                impact={"customers_gained": new_customers, "revenue_impact": new_customers * company.get("arpu", 100)},
                severity="info",
            ))

        company["customers"] = max(1, customers - churned + new_customers)
        company["churn_rate"] = effective_churn
        return events


class TeamAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(AgentType.TEAM, config)
        self.morale = config.get("morale", 0.7) if config else 0.7
        self.productivity = config.get("productivity", 0.7) if config else 0.7
        self.attrition_risk = 0.05

    def observe(self, environment: Dict[str, Any], company: Dict[str, Any], month: int):
        runway = company.get("runway_months", 18)
        recent_layoffs = company.get("recent_layoffs", False)
        growth = company.get("growth_rate", 0)
        hiring_market = environment.get("hiring_market_tightness", 0.5)

        if runway < 6:
            self.morale = max(0.1, self.morale - 0.1)
            self.attrition_risk = min(0.3, self.attrition_risk + 0.05)
        elif runway < 12:
            self.morale = max(0.2, self.morale - 0.03)
        else:
            self.morale = min(0.9, self.morale + 0.02)

        if recent_layoffs:
            self.morale = max(0.1, self.morale - 0.15)
            self.attrition_risk = min(0.4, self.attrition_risk + 0.1)

        if growth > 10:
            self.morale = min(0.95, self.morale + 0.03)

        self.productivity = self.morale * 0.6 + (1 - self.attrition_risk) * 0.4

        if self.morale > 0.6:
            self.state.sentiment = Sentiment.POSITIVE
        elif self.morale > 0.4:
            self.state.sentiment = Sentiment.NEUTRAL
        else:
            self.state.sentiment = Sentiment.NEGATIVE

    def act(self, environment: Dict[str, Any], company: Dict[str, Any], month: int) -> List[AgentEvent]:
        events = []
        headcount = company.get("headcount", 10)

        if self.attrition_risk > 0.15 and random.random() < self.attrition_risk:
            departures = max(1, int(headcount * random.uniform(0.05, 0.15)))
            events.append(AgentEvent(
                month=month,
                agent_type=self.agent_type.value,
                event_type="attrition",
                description=f"Team attrition — {departures} team members departing (morale: {self.morale*100:.0f}%)",
                impact={"headcount_change": -departures, "productivity_impact": -0.1},
                severity="warning",
            ))
            company["headcount"] = max(1, headcount - departures)

        if self.morale < 0.3:
            events.append(AgentEvent(
                month=month,
                agent_type=self.agent_type.value,
                event_type="morale_crisis",
                description=f"Team morale critically low at {self.morale*100:.0f}% — productivity declining",
                impact={"productivity_multiplier": 0.7, "innovation_impact": -0.3},
                severity="danger",
            ))

        company["product_quality"] = min(1.0, self.productivity * 0.8 + random.uniform(0, 0.2))
        return events


class MarketAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(AgentType.MARKET, config)
        self.base_tam_growth = config.get("tam_growth", 0.15) if config else 0.15
        self.volatility = config.get("volatility", 0.2) if config else 0.2
        self.current_cycle = "expansion"

    def observe(self, environment: Dict[str, Any], company: Dict[str, Any], month: int):
        cycle_shift = random.gauss(0, self.volatility * 0.1)

        if self.current_cycle == "expansion" and random.random() < 0.05:
            self.current_cycle = "contraction"
        elif self.current_cycle == "contraction" and random.random() < 0.1:
            self.current_cycle = "expansion"

        if self.current_cycle == "expansion":
            self.state.sentiment = Sentiment.POSITIVE
            self.state.confidence = min(1.0, self.state.confidence + 0.02)
        else:
            self.state.sentiment = Sentiment.NEGATIVE
            self.state.confidence = max(0.1, self.state.confidence - 0.03)

    def act(self, environment: Dict[str, Any], company: Dict[str, Any], month: int) -> List[AgentEvent]:
        events = []

        if self.current_cycle == "contraction" and random.random() < 0.15:
            impact_severity = random.uniform(0.05, 0.2)
            events.append(AgentEvent(
                month=month,
                agent_type=self.agent_type.value,
                event_type="market_downturn",
                description=f"Market downturn — {impact_severity*100:.0f}% reduction in available funding",
                impact={"funding_climate_change": -impact_severity, "market_growth_change": -impact_severity * 0.5},
                severity="warning",
            ))

        if self.current_cycle == "expansion" and random.random() < 0.1:
            events.append(AgentEvent(
                month=month,
                agent_type=self.agent_type.value,
                event_type="market_opportunity",
                description="New market opportunity detected — increased growth potential",
                impact={"market_growth_change": random.uniform(0.05, 0.15), "tam_expansion": random.uniform(0.1, 0.3)},
                severity="info",
            ))

        if random.random() < 0.08:
            events.append(AgentEvent(
                month=month,
                agent_type=self.agent_type.value,
                event_type="competitor_move",
                description="Competitor raises funding or launches competing product",
                impact={"competition_intensity_change": random.uniform(0.05, 0.2)},
                severity="info",
            ))

        return events
