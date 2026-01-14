from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import numpy as np


class Regime(str, Enum):
    BASE = "base"
    DOWNTURN = "downturn"
    BREAKOUT = "breakout"


class DistributionType(str, Enum):
    NORMAL = "normal"
    TRIANGULAR = "triangular"
    UNIFORM = "uniform"
    LOGNORMAL = "lognormal"


@dataclass
class DriverConfig:
    mean: float
    sigma: float
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    distribution: DistributionType = DistributionType.NORMAL
    mode: Optional[float] = None


@dataclass
class RegimeConfig:
    name: str
    description: str
    driver_adjustments: Dict[str, DriverConfig] = field(default_factory=dict)
    fundraising_success_prob: float = 0.5
    transition_probs: Dict[str, float] = field(default_factory=dict)


DEFAULT_REGIMES: Dict[str, RegimeConfig] = {
    "base": RegimeConfig(
        name="Base Case",
        description="Normal market conditions with moderate uncertainty",
        driver_adjustments={
            "growth_rate": DriverConfig(mean=0, sigma=3.0, min_val=-20, max_val=50),
            "churn_rate": DriverConfig(mean=0, sigma=0.5, min_val=0, max_val=15),
            "gross_margin": DriverConfig(mean=0, sigma=2.0, min_val=10, max_val=95),
            "cac": DriverConfig(mean=0, sigma=5.0, min_val=0, max_val=None),
            "dso": DriverConfig(mean=0, sigma=5.0, min_val=15, max_val=120),
            "conversion_rate": DriverConfig(mean=0, sigma=2.0, min_val=0, max_val=100),
        },
        fundraising_success_prob=0.6,
        transition_probs={"base": 0.85, "downturn": 0.10, "breakout": 0.05}
    ),
    "downturn": RegimeConfig(
        name="Downturn",
        description="Challenging market with reduced growth and higher churn",
        driver_adjustments={
            "growth_rate": DriverConfig(mean=-5, sigma=5.0, min_val=-30, max_val=20),
            "churn_rate": DriverConfig(mean=2, sigma=1.0, min_val=0, max_val=25),
            "gross_margin": DriverConfig(mean=-3, sigma=3.0, min_val=5, max_val=90),
            "cac": DriverConfig(mean=15, sigma=8.0, min_val=0, max_val=None),
            "dso": DriverConfig(mean=15, sigma=10.0, min_val=20, max_val=150),
            "conversion_rate": DriverConfig(mean=-5, sigma=3.0, min_val=0, max_val=100),
        },
        fundraising_success_prob=0.25,
        transition_probs={"base": 0.20, "downturn": 0.75, "breakout": 0.05}
    ),
    "breakout": RegimeConfig(
        name="Breakout",
        description="Strong tailwinds with accelerated growth",
        driver_adjustments={
            "growth_rate": DriverConfig(mean=8, sigma=4.0, min_val=0, max_val=80),
            "churn_rate": DriverConfig(mean=-1, sigma=0.3, min_val=0, max_val=10),
            "gross_margin": DriverConfig(mean=5, sigma=2.0, min_val=20, max_val=98),
            "cac": DriverConfig(mean=-10, sigma=5.0, min_val=0, max_val=None),
            "dso": DriverConfig(mean=-5, sigma=3.0, min_val=10, max_val=90),
            "conversion_rate": DriverConfig(mean=5, sigma=2.0, min_val=0, max_val=100),
        },
        fundraising_success_prob=0.85,
        transition_probs={"base": 0.25, "downturn": 0.02, "breakout": 0.73}
    ),
}


DRIVER_CORRELATION_MATRIX = {
    "growth_rate": {"growth_rate": 1.0, "churn_rate": -0.3, "gross_margin": 0.2, "cac": 0.4, "dso": 0.1, "conversion_rate": 0.5},
    "churn_rate": {"growth_rate": -0.3, "churn_rate": 1.0, "gross_margin": -0.2, "cac": 0.2, "dso": 0.3, "conversion_rate": -0.4},
    "gross_margin": {"growth_rate": 0.2, "churn_rate": -0.2, "gross_margin": 1.0, "cac": -0.3, "dso": -0.1, "conversion_rate": 0.2},
    "cac": {"growth_rate": 0.4, "churn_rate": 0.2, "gross_margin": -0.3, "cac": 1.0, "dso": 0.2, "conversion_rate": 0.3},
    "dso": {"growth_rate": 0.1, "churn_rate": 0.3, "gross_margin": -0.1, "cac": 0.2, "dso": 1.0, "conversion_rate": 0.0},
    "conversion_rate": {"growth_rate": 0.5, "churn_rate": -0.4, "gross_margin": 0.2, "cac": 0.3, "dso": 0.0, "conversion_rate": 1.0},
}


@dataclass
class CustomerCohort:
    acquisition_month: int
    initial_customers: int
    current_customers: int
    mrr_per_customer: float
    gross_retention_rate: float
    net_retention_rate: float
    expansion_rate: float
    acquisition_channel: str = "organic"


@dataclass
class WorkingCapital:
    accounts_receivable: float = 0.0
    accounts_payable: float = 0.0
    inventory: float = 0.0
    deferred_revenue: float = 0.0
    prepaid_expenses: float = 0.0
    
    @property
    def net_working_capital(self) -> float:
        return self.accounts_receivable + self.inventory + self.prepaid_expenses - self.accounts_payable - self.deferred_revenue


@dataclass
class DebtFacility:
    principal: float
    interest_rate: float
    term_months: int
    start_month: int
    monthly_payment: float = 0.0
    covenants: Dict[str, float] = field(default_factory=dict)
    
    def check_covenants(self, state: Any) -> Dict[str, bool]:
        results = {}
        if "min_cash" in self.covenants:
            results["min_cash"] = state.cash >= self.covenants["min_cash"]
        if "max_leverage" in self.covenants:
            leverage = self.principal / max(state.arr, 1)
            results["max_leverage"] = leverage <= self.covenants["max_leverage"]
        if "min_revenue_growth" in self.covenants:
            results["min_revenue_growth"] = True
        return results


@dataclass
class MonthlyState:
    month: int
    cash: float
    arr: float
    mrr: float
    revenue: float
    cogs: float
    gross_profit: float
    opex: float
    payroll: float
    other_costs: float
    ebitda: float
    net_cashflow: float
    burn_rate: float
    headcount: int
    pipeline_value: float
    bookings: float
    churn_amount: float
    cac_total: float
    new_customers: int
    churned_customers: int
    total_customers: int
    dso_actual: float
    collections: float
    debt_balance: float
    debt_payment: float
    regime: str = "base"
    events_active: List[str] = field(default_factory=list)
    accounts_receivable: float = 0.0
    accounts_payable: float = 0.0
    deferred_revenue: float = 0.0
    net_working_capital: float = 0.0
    interest_expense: float = 0.0
    covenant_status: Dict[str, bool] = field(default_factory=dict)
    gross_retention: float = 100.0
    net_retention: float = 100.0
    cohort_count: int = 0


@dataclass
class EnrichedSimulationInputs:
    baseline_mrr: float
    baseline_growth_rate: float
    gross_margin: float
    opex: float
    payroll: float
    other_costs: float
    cash_balance: float
    
    churn_rate: float = 3.0
    cac: float = 500.0
    dso: float = 45.0
    conversion_rate: float = 5.0
    headcount: int = 10
    avg_salary: float = 8000.0
    pipeline_value: float = 0.0
    arpu: float = 500.0
    total_customers: int = 100
    debt_balance: float = 0.0
    debt_interest_rate: float = 0.0
    debt_term_months: int = 0
    
    starting_regime: str = "base"
    enable_regime_transitions: bool = True
    
    pricing_change_pct: float = 0
    growth_uplift_pct: float = 0
    burn_reduction_pct: float = 0
    gross_margin_delta_pct: float = 0
    
    fundraise_month: Optional[int] = None
    fundraise_amount: float = 0
    fundraise_probability: Optional[float] = None
    
    horizon_months: int = 24
    n_simulations: int = 1000
    
    growth_sigma: float = 3.0
    margin_sigma: float = 2.0
    churn_sigma: float = 0.5
    cac_sigma: float = 5.0
    dso_sigma: float = 5.0
    conversion_sigma: float = 2.0


@dataclass
class ScenarioEvent:
    event_type: str
    start_month: int
    end_month: Optional[int] = None
    params: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    decay_rate: float = 0.0
    decay_type: str = "exponential"


EVENT_TYPES = {
    "pricing_change": {
        "description": "Adjust pricing by a percentage",
        "params": ["change_pct"],
        "affects": ["mrr", "arpu"]
    },
    "cost_cut": {
        "description": "Reduce operating expenses",
        "params": ["opex_reduction_pct", "payroll_reduction_pct"],
        "affects": ["opex", "payroll", "headcount"]
    },
    "hiring_freeze": {
        "description": "Pause all hiring",
        "params": [],
        "affects": ["headcount", "payroll"]
    },
    "hiring_plan": {
        "description": "Scheduled hiring over time",
        "params": ["new_hires", "avg_salary"],
        "affects": ["headcount", "payroll"]
    },
    "fundraise": {
        "description": "Raise capital",
        "params": ["amount", "success_probability"],
        "affects": ["cash"]
    },
    "marketing_spend_change": {
        "description": "Adjust marketing budget",
        "params": ["change_pct"],
        "affects": ["opex", "cac", "pipeline"]
    },
    "churn_initiative": {
        "description": "Customer success initiative to reduce churn",
        "params": ["churn_reduction_pct"],
        "affects": ["churn_rate"]
    },
    "expansion_revenue": {
        "description": "Launch expansion/upsell initiative",
        "params": ["expansion_rate_pct"],
        "affects": ["arpu", "mrr"]
    },
}


@dataclass
class ScenarioDefinition:
    name: str
    description: str = ""
    events: List[ScenarioEvent] = field(default_factory=list)
    starting_regime: str = "base"
    regime_override: Optional[str] = None


@dataclass 
class DecisionScore:
    scenario_key: str
    scenario_name: str
    survival_12m_prob: float
    survival_18m_prob: float
    expected_arr_18m: float
    downside_risk_cvar: float
    dilution_pct: float
    complexity_score: float
    composite_score: float
    rank: int
    survival_component: float = 0.0
    growth_component: float = 0.0
    risk_component: float = 0.0
    dilution_component: float = 0.0
    complexity_component: float = 0.0


@dataclass
class SensitivityResult:
    driver: str
    impact_direction: str
    impact_magnitude: float
    threshold_value: Optional[float]
    explanation: str


@dataclass
class WhatMustBeTrueReport:
    target_runway_months: int
    target_probability: float
    achievable: bool
    current_probability: float
    key_drivers: List[SensitivityResult]
    recommendations: List[str]


@dataclass
class EnrichedSimulationResult:
    scenario_key: str
    scenario_name: str
    runway: Dict[str, float]
    survival: Dict[str, Any]
    bands: Dict[str, Dict[str, List[float]]]
    monthly_states: List[Dict[str, Any]]
    regime_distribution: Dict[str, float]
    decision_score: Optional[DecisionScore]
    sensitivity: Optional[List[SensitivityResult]]
    n_simulations: int
    horizon_months: int
    survival_curve: List[Dict[str, Any]] = field(default_factory=list)
