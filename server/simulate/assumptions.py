"""
Assumption Sets Module for Probabilistic Simulation.

Defines the JSON schema and Pydantic models for assumption sets used in
Monte Carlo simulations. Supports distributions for stochastic modeling.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
from datetime import datetime


class DistributionType(str, Enum):
    FIXED = "fixed"
    NORMAL = "normal"
    LOGNORMAL = "lognormal"
    UNIFORM = "uniform"
    TRIANGULAR = "triangular"
    BETA = "beta"


class Distribution(BaseModel):
    """Base distribution model for stochastic variables."""
    type: DistributionType = DistributionType.FIXED
    value: Optional[float] = None
    mean: Optional[float] = None
    std: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    mode: Optional[float] = None
    alpha: Optional[float] = None
    beta: Optional[float] = None

    @validator('type', pre=True)
    def validate_type(cls, v):
        if isinstance(v, str):
            return DistributionType(v.lower())
        return v

    def sample(self, rng=None) -> float:
        """Sample a value from this distribution."""
        import numpy as np
        if rng is None:
            rng = np.random.default_rng()
        
        if self.type == DistributionType.FIXED:
            return self.value or 0.0
        elif self.type == DistributionType.NORMAL:
            return rng.normal(self.mean or 0, self.std or 1)
        elif self.type == DistributionType.LOGNORMAL:
            return rng.lognormal(self.mean or 0, self.std or 1)
        elif self.type == DistributionType.UNIFORM:
            return rng.uniform(self.min or 0, self.max or 1)
        elif self.type == DistributionType.TRIANGULAR:
            return rng.triangular(self.min or 0, self.mode or 0.5, self.max or 1)
        elif self.type == DistributionType.BETA:
            return rng.beta(self.alpha or 2, self.beta or 2)
        return self.value or 0.0


class RevenueGrowthAssumption(BaseModel):
    """Revenue growth assumptions with distribution support."""
    monthly_growth_rate: Distribution = Field(
        default_factory=lambda: Distribution(type=DistributionType.NORMAL, mean=0.05, std=0.02),
        description="Monthly revenue growth rate (e.g., 0.05 = 5%)"
    )
    seasonality_factor: Optional[Dict[int, float]] = Field(
        default=None,
        description="Monthly seasonality multipliers (1-12)"
    )


class ChurnAssumption(BaseModel):
    """Customer churn assumptions."""
    monthly_churn_rate: Distribution = Field(
        default_factory=lambda: Distribution(type=DistributionType.BETA, alpha=2, beta=20),
        description="Monthly churn rate (0-1)"
    )
    logo_churn_rate: Optional[Distribution] = Field(
        default=None,
        description="Logo churn rate if different from revenue churn"
    )


class PriceChangeAssumption(BaseModel):
    """Pricing change assumptions."""
    annual_price_increase: Distribution = Field(
        default_factory=lambda: Distribution(type=DistributionType.FIXED, value=0.0),
        description="Annual price increase rate"
    )
    timing_month: int = Field(
        default=12,
        description="Month when price change takes effect (1-12)",
        ge=1,
        le=12
    )


class BurnReductionAssumption(BaseModel):
    """Cost/burn reduction assumptions."""
    monthly_reduction_rate: Distribution = Field(
        default_factory=lambda: Distribution(type=DistributionType.FIXED, value=0.0),
        description="Monthly burn reduction target rate"
    )
    categories: Optional[Dict[str, float]] = Field(
        default=None,
        description="Reduction targets by category (opex, payroll, etc.)"
    )


class HeadcountPlan(BaseModel):
    """Hiring/headcount assumptions."""
    current_headcount: int = Field(default=10, ge=0)
    monthly_hires: List[int] = Field(
        default_factory=lambda: [0] * 24,
        description="Planned hires per month for projection horizon"
    )
    avg_salary: Distribution = Field(
        default_factory=lambda: Distribution(type=DistributionType.NORMAL, mean=100000, std=20000),
        description="Average fully-loaded salary per employee"
    )
    ramp_months: int = Field(
        default=3,
        description="Months for new hire to reach full productivity",
        ge=0
    )


class FundraiseAssumption(BaseModel):
    """Fundraising assumptions."""
    amount: float = Field(default=0, description="Target raise amount", ge=0)
    timing_month: int = Field(
        default=6,
        description="Expected close month from now",
        ge=1
    )
    pre_money_valuation: Optional[float] = Field(
        default=None,
        description="Pre-money valuation"
    )
    probability: Distribution = Field(
        default_factory=lambda: Distribution(type=DistributionType.FIXED, value=0.7),
        description="Probability of successful close (0-1)"
    )
    instrument: Literal["equity", "safe", "note"] = Field(
        default="equity",
        description="Financing instrument type"
    )


class CapexAssumption(BaseModel):
    """Capital expenditure assumptions."""
    one_time_expenses: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of {month, amount, description} for one-time capex"
    )
    recurring_monthly: Distribution = Field(
        default_factory=lambda: Distribution(type=DistributionType.FIXED, value=0),
        description="Recurring monthly capex"
    )


class AssumptionSet(BaseModel):
    """
    Complete assumption set for probabilistic simulation.
    
    This is the core input schema for the Monte Carlo simulation engine.
    Each field can be a fixed value or a distribution for stochastic modeling.
    """
    id: Optional[str] = None
    name: str = Field(description="Name of this assumption set")
    description: Optional[str] = None
    template_id: Optional[str] = Field(
        default=None,
        description="ID of template this was derived from"
    )
    
    revenue_growth: RevenueGrowthAssumption = Field(
        default_factory=RevenueGrowthAssumption
    )
    churn_rate: ChurnAssumption = Field(
        default_factory=ChurnAssumption
    )
    price_change: PriceChangeAssumption = Field(
        default_factory=PriceChangeAssumption
    )
    burn_reduction: BurnReductionAssumption = Field(
        default_factory=BurnReductionAssumption
    )
    headcount_plan: HeadcountPlan = Field(
        default_factory=HeadcountPlan
    )
    fundraise: FundraiseAssumption = Field(
        default_factory=FundraiseAssumption
    )
    capex: Optional[CapexAssumption] = None
    
    custom_fields: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional custom assumption fields"
    )
    
    simulation_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Simulation configuration overrides"
    )
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Base Case Scenario",
                "description": "Conservative growth with moderate churn",
                "revenue_growth": {
                    "monthly_growth_rate": {
                        "type": "normal",
                        "mean": 0.05,
                        "std": 0.02
                    }
                },
                "churn_rate": {
                    "monthly_churn_rate": {
                        "type": "beta",
                        "alpha": 2,
                        "beta": 20
                    }
                },
                "headcount_plan": {
                    "current_headcount": 15,
                    "monthly_hires": [1, 1, 2, 1, 1, 2, 1, 1, 2, 1, 1, 2],
                    "avg_salary": {
                        "type": "normal",
                        "mean": 120000,
                        "std": 25000
                    }
                },
                "fundraise": {
                    "amount": 5000000,
                    "timing_month": 6,
                    "probability": {
                        "type": "fixed",
                        "value": 0.7
                    }
                }
            }
        }


class AssumptionSetCreate(BaseModel):
    """Request model for creating an assumption set."""
    name: str
    description: Optional[str] = None
    template_id: Optional[str] = None
    revenue_growth: Optional[RevenueGrowthAssumption] = None
    churn_rate: Optional[ChurnAssumption] = None
    price_change: Optional[PriceChangeAssumption] = None
    burn_reduction: Optional[BurnReductionAssumption] = None
    headcount_plan: Optional[HeadcountPlan] = None
    fundraise: Optional[FundraiseAssumption] = None
    capex: Optional[CapexAssumption] = None
    custom_fields: Optional[Dict[str, Any]] = None
    simulation_config: Optional[Dict[str, Any]] = None


class AssumptionSetUpdate(BaseModel):
    """Request model for updating an assumption set."""
    name: Optional[str] = None
    description: Optional[str] = None
    revenue_growth: Optional[RevenueGrowthAssumption] = None
    churn_rate: Optional[ChurnAssumption] = None
    price_change: Optional[PriceChangeAssumption] = None
    burn_reduction: Optional[BurnReductionAssumption] = None
    headcount_plan: Optional[HeadcountPlan] = None
    fundraise: Optional[FundraiseAssumption] = None
    capex: Optional[CapexAssumption] = None
    custom_fields: Optional[Dict[str, Any]] = None
    simulation_config: Optional[Dict[str, Any]] = None


def validate_assumption_set(assumption_set: AssumptionSet) -> List[str]:
    """
    Validate an assumption set for consistency and range checks.
    
    Returns a list of validation errors (empty if valid).
    """
    errors = []
    
    if assumption_set.churn_rate:
        churn = assumption_set.churn_rate.monthly_churn_rate
        if churn.type == DistributionType.FIXED:
            if churn.value is not None and (churn.value < 0 or churn.value > 1):
                errors.append("Churn rate must be between 0 and 1")
    
    if assumption_set.headcount_plan:
        hp = assumption_set.headcount_plan
        cumulative = hp.current_headcount
        for i, hires in enumerate(hp.monthly_hires):
            cumulative += hires
            if cumulative < 0:
                errors.append(f"Headcount cannot go negative in month {i+1}")
    
    if assumption_set.fundraise:
        fr = assumption_set.fundraise
        if fr.amount < 0:
            errors.append("Fundraise amount cannot be negative")
        if fr.probability.type == DistributionType.FIXED:
            if fr.probability.value is not None and (fr.probability.value < 0 or fr.probability.value > 1):
                errors.append("Fundraise probability must be between 0 and 1")
    
    return errors
