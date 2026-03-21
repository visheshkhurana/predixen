from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime


class SimulationStatus(str, Enum):
    CREATED = "created"
    CONFIGURING = "configuring"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentType(str, Enum):
    FOUNDER = "founder"
    INVESTOR = "investor"
    CUSTOMER = "customer"
    TEAM_MEMBER = "team"
    MARKET = "market"
    COMPETITOR = "competitor"
    ADVISOR = "advisor"


class ActionType(str, Enum):
    HIRE = "hire"
    FIRE = "fire"
    PIVOT_PRODUCT = "pivot_product"
    RAISE_PRICES = "raise_prices"
    CUT_PRICES = "cut_prices"
    LAUNCH_FEATURE = "launch_feature"
    CUT_BURN = "cut_burn"
    INCREASE_MARKETING = "increase_marketing"
    SEEK_FUNDING = "seek_funding"

    OFFER_TERM_SHEET = "offer_term_sheet"
    PASS_ON_DEAL = "pass_on_deal"
    REQUEST_METRICS = "request_metrics"
    FOLLOW_ON_INVEST = "follow_on_invest"
    MARK_DOWN = "mark_down"

    SIGN_CONTRACT = "sign_contract"
    CHURN = "churn"
    UPGRADE = "upgrade"
    REFER_OTHERS = "refer_others"
    COMPLAIN = "complain"
    REQUEST_FEATURE = "request_feature"

    QUIT = "quit"
    REQUEST_RAISE = "request_raise"
    SHIP_FEATURE = "ship_feature"
    MISS_DEADLINE = "miss_deadline"
    PROPOSE_IDEA = "propose_idea"

    RECESSION = "recession"
    BOOM = "boom"
    NEW_REGULATION = "new_regulation"
    COMPETITOR_LAUNCH = "competitor_launch"
    VIRAL_MOMENT = "viral_moment"
    MARKET_SHIFT = "market_shift"

    OBSERVE = "observe"
    IDLE = "idle"


class Sentiment(str, Enum):
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


@dataclass
class AgentPersona:
    id: str
    name: str
    agent_type: AgentType
    bio: str
    personality_traits: List[str]
    goals: List[str]
    emotional_tendency: float
    activity_level: float
    influence: float
    risk_tolerance: float
    available_actions: List[ActionType] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "agent_type": self.agent_type.value,
            "bio": self.bio,
            "personality_traits": self.personality_traits,
            "goals": self.goals,
            "emotional_tendency": self.emotional_tendency,
            "activity_level": self.activity_level,
            "influence": self.influence,
            "risk_tolerance": self.risk_tolerance,
            "available_actions": [a.value for a in self.available_actions],
        }


@dataclass
class AgentAction:
    round_num: int
    month_label: str
    agent_id: str
    agent_name: str
    agent_type: AgentType
    action: ActionType
    reasoning: str
    description: str
    impact: Dict[str, float]
    sentiment: Sentiment
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "round": self.round_num,
            "month": self.month_label,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "agent_type": self.agent_type.value,
            "action": self.action.value,
            "reasoning": self.reasoning,
            "description": self.description,
            "impact": self.impact,
            "sentiment": self.sentiment.value,
        }


@dataclass
class CompanyState:
    mrr: float = 0.0
    arr: float = 0.0
    burn_rate: float = 0.0
    cash: float = 0.0
    runway_months: float = 0.0
    customers: int = 0
    churn_rate: float = 0.0
    team_size: int = 0
    team_morale: float = 0.7
    product_quality: float = 0.5
    market_fit: float = 0.5
    brand_reputation: float = 0.5
    investor_confidence: float = 0.5
    growth_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mrr": self.mrr,
            "arr": self.arr,
            "burn_rate": self.burn_rate,
            "cash": self.cash,
            "runway_months": self.runway_months,
            "customers": self.customers,
            "churn_rate": self.churn_rate,
            "team_size": self.team_size,
            "team_morale": self.team_morale,
            "product_quality": self.product_quality,
            "market_fit": self.market_fit,
            "brand_reputation": self.brand_reputation,
            "investor_confidence": self.investor_confidence,
            "growth_rate": self.growth_rate,
        }

    def apply_action_impact(self, impact: Dict[str, float]):
        for key, delta in impact.items():
            field_name = key.replace("_delta", "")
            if hasattr(self, field_name):
                current = getattr(self, field_name)
                if isinstance(current, int):
                    setattr(self, field_name, max(0, current + int(delta)))
                else:
                    setattr(self, field_name, max(0.0, current + delta))
        self.arr = self.mrr * 12
        self.runway_months = self.cash / self.burn_rate if self.burn_rate > 0 else 999


@dataclass
class SimulationConfig:
    simulation_id: str
    total_rounds: int = 24
    agents: List[AgentPersona] = field(default_factory=list)
    initial_state: CompanyState = field(default_factory=CompanyState)
    scenario_params: Dict[str, Any] = field(default_factory=dict)
    early_stage_multipliers: Dict[str, float] = field(default_factory=lambda: {
        "founder": 1.5, "investor": 0.3, "customer": 0.5, "team": 1.0, "market": 0.8
    })
    late_stage_multipliers: Dict[str, float] = field(default_factory=lambda: {
        "founder": 1.0, "investor": 1.5, "customer": 1.2, "team": 0.8, "market": 1.0
    })


@dataclass
class SimulationResult:
    simulation_id: str
    config: SimulationConfig
    rounds: List[Dict[str, Any]] = field(default_factory=list)
    all_actions: List[AgentAction] = field(default_factory=list)
    final_state: CompanyState = field(default_factory=CompanyState)
    status: SimulationStatus = SimulationStatus.CREATED
    report: Optional[Dict[str, Any]] = None
