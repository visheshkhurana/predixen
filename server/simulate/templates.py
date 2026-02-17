"""
Strategy Templates Registry for FounderConsole Simulator.

Pre-defined assumption sets that map to common startup strategies.
Users can select a template and override specific parameters.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from server.simulate.assumptions import (
    AssumptionSet,
    Distribution,
    DistributionType,
    RevenueGrowthAssumption,
    ChurnAssumption,
    PriceChangeAssumption,
    BurnReductionAssumption,
    HeadcountPlan,
    FundraiseAssumption,
)


class StrategyTemplate(BaseModel):
    """A strategy template with preset assumptions."""
    id: str
    name: str
    description: str
    category: str = Field(description="Category: growth, efficiency, survival, balanced")
    tags: List[str] = Field(default_factory=list)
    assumptions: AssumptionSet
    recommended_for: Optional[str] = None


STRATEGY_TEMPLATES: Dict[str, StrategyTemplate] = {
    "extend_runway": StrategyTemplate(
        id="extend_runway",
        name="Extend Runway",
        description="Focus on extending runway through cost reduction and conservative growth. Ideal for uncertain markets or when fundraising is delayed.",
        category="survival",
        tags=["cost-cutting", "conservative", "runway"],
        recommended_for="Startups with <12 months runway or uncertain fundraising timeline",
        assumptions=AssumptionSet(
            name="Extend Runway",
            revenue_growth=RevenueGrowthAssumption(
                monthly_growth_rate=Distribution(
                    type=DistributionType.NORMAL,
                    mean=0.02,
                    std=0.01
                )
            ),
            churn_rate=ChurnAssumption(
                monthly_churn_rate=Distribution(
                    type=DistributionType.BETA,
                    alpha=2,
                    beta=25
                )
            ),
            price_change=PriceChangeAssumption(
                annual_price_increase=Distribution(type=DistributionType.FIXED, value=0.05),
                timing_month=6
            ),
            burn_reduction=BurnReductionAssumption(
                monthly_reduction_rate=Distribution(
                    type=DistributionType.FIXED,
                    value=0.05
                ),
                categories={"opex": 0.10, "payroll": 0.03, "marketing": 0.15}
            ),
            headcount_plan=HeadcountPlan(
                current_headcount=20,
                monthly_hires=[0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0] + [0] * 12,
                avg_salary=Distribution(type=DistributionType.FIXED, value=100000)
            ),
            fundraise=FundraiseAssumption(
                amount=0,
                timing_month=12,
                probability=Distribution(type=DistributionType.FIXED, value=0.3)
            )
        )
    ),
    
    "aggressive_growth": StrategyTemplate(
        id="aggressive_growth",
        name="Aggressive Growth",
        description="Maximize growth velocity with significant investment in team and go-to-market. Suitable when runway is secure and market opportunity is clear.",
        category="growth",
        tags=["high-growth", "investment", "scale"],
        recommended_for="Well-funded startups with product-market fit and >18 months runway",
        assumptions=AssumptionSet(
            name="Aggressive Growth",
            revenue_growth=RevenueGrowthAssumption(
                monthly_growth_rate=Distribution(
                    type=DistributionType.NORMAL,
                    mean=0.12,
                    std=0.04
                )
            ),
            churn_rate=ChurnAssumption(
                monthly_churn_rate=Distribution(
                    type=DistributionType.BETA,
                    alpha=3,
                    beta=30
                )
            ),
            price_change=PriceChangeAssumption(
                annual_price_increase=Distribution(type=DistributionType.FIXED, value=0.0),
                timing_month=12
            ),
            burn_reduction=BurnReductionAssumption(
                monthly_reduction_rate=Distribution(type=DistributionType.FIXED, value=0.0)
            ),
            headcount_plan=HeadcountPlan(
                current_headcount=25,
                monthly_hires=[2, 3, 3, 4, 3, 4, 3, 4, 3, 4, 3, 4] + [3] * 12,
                avg_salary=Distribution(type=DistributionType.NORMAL, mean=130000, std=30000)
            ),
            fundraise=FundraiseAssumption(
                amount=10000000,
                timing_month=9,
                pre_money_valuation=50000000,
                probability=Distribution(type=DistributionType.FIXED, value=0.6),
                instrument="equity"
            )
        )
    ),
    
    "balanced_growth": StrategyTemplate(
        id="balanced_growth",
        name="Balanced Growth",
        description="Moderate growth with focus on unit economics and sustainable scaling. Balance between velocity and efficiency.",
        category="balanced",
        tags=["sustainable", "unit-economics", "moderate"],
        recommended_for="Series A/B companies optimizing for efficient growth",
        assumptions=AssumptionSet(
            name="Balanced Growth",
            revenue_growth=RevenueGrowthAssumption(
                monthly_growth_rate=Distribution(
                    type=DistributionType.NORMAL,
                    mean=0.06,
                    std=0.02
                )
            ),
            churn_rate=ChurnAssumption(
                monthly_churn_rate=Distribution(
                    type=DistributionType.BETA,
                    alpha=2,
                    beta=30
                )
            ),
            price_change=PriceChangeAssumption(
                annual_price_increase=Distribution(type=DistributionType.FIXED, value=0.03),
                timing_month=1
            ),
            burn_reduction=BurnReductionAssumption(
                monthly_reduction_rate=Distribution(type=DistributionType.FIXED, value=0.02)
            ),
            headcount_plan=HeadcountPlan(
                current_headcount=30,
                monthly_hires=[1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2] + [1] * 12,
                avg_salary=Distribution(type=DistributionType.NORMAL, mean=115000, std=25000)
            ),
            fundraise=FundraiseAssumption(
                amount=5000000,
                timing_month=12,
                probability=Distribution(type=DistributionType.FIXED, value=0.5)
            )
        )
    ),
    
    "profitability_path": StrategyTemplate(
        id="profitability_path",
        name="Path to Profitability",
        description="Prioritize reaching profitability or cash-flow positive. Minimal external funding dependency.",
        category="efficiency",
        tags=["profitability", "bootstrapped", "sustainable"],
        recommended_for="Startups targeting default-alive status or limited fundraising options",
        assumptions=AssumptionSet(
            name="Path to Profitability",
            revenue_growth=RevenueGrowthAssumption(
                monthly_growth_rate=Distribution(
                    type=DistributionType.NORMAL,
                    mean=0.04,
                    std=0.015
                )
            ),
            churn_rate=ChurnAssumption(
                monthly_churn_rate=Distribution(
                    type=DistributionType.BETA,
                    alpha=2,
                    beta=35
                )
            ),
            price_change=PriceChangeAssumption(
                annual_price_increase=Distribution(type=DistributionType.FIXED, value=0.08),
                timing_month=3
            ),
            burn_reduction=BurnReductionAssumption(
                monthly_reduction_rate=Distribution(type=DistributionType.FIXED, value=0.08),
                categories={"opex": 0.15, "payroll": 0.05, "marketing": 0.10}
            ),
            headcount_plan=HeadcountPlan(
                current_headcount=15,
                monthly_hires=[0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0] + [0] * 12,
                avg_salary=Distribution(type=DistributionType.FIXED, value=95000)
            ),
            fundraise=FundraiseAssumption(
                amount=0,
                timing_month=24,
                probability=Distribution(type=DistributionType.FIXED, value=0.0)
            )
        )
    ),
    
    "fundraise_prep": StrategyTemplate(
        id="fundraise_prep",
        name="Fundraise Preparation",
        description="Optimize metrics for upcoming fundraise. Focus on growth acceleration and key metrics that investors value.",
        category="growth",
        tags=["fundraising", "metrics", "investor-ready"],
        recommended_for="Companies 3-6 months before planned fundraise",
        assumptions=AssumptionSet(
            name="Fundraise Preparation",
            revenue_growth=RevenueGrowthAssumption(
                monthly_growth_rate=Distribution(
                    type=DistributionType.NORMAL,
                    mean=0.10,
                    std=0.03
                )
            ),
            churn_rate=ChurnAssumption(
                monthly_churn_rate=Distribution(
                    type=DistributionType.BETA,
                    alpha=2,
                    beta=40
                )
            ),
            price_change=PriceChangeAssumption(
                annual_price_increase=Distribution(type=DistributionType.FIXED, value=0.0),
                timing_month=12
            ),
            burn_reduction=BurnReductionAssumption(
                monthly_reduction_rate=Distribution(type=DistributionType.FIXED, value=0.0)
            ),
            headcount_plan=HeadcountPlan(
                current_headcount=20,
                monthly_hires=[2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1] + [1] * 12,
                avg_salary=Distribution(type=DistributionType.NORMAL, mean=120000, std=25000)
            ),
            fundraise=FundraiseAssumption(
                amount=8000000,
                timing_month=6,
                pre_money_valuation=40000000,
                probability=Distribution(
                    type=DistributionType.TRIANGULAR,
                    min=0.3,
                    mode=0.6,
                    max=0.85
                ),
                instrument="equity"
            )
        )
    ),
    
    "market_downturn": StrategyTemplate(
        id="market_downturn",
        name="Market Downturn Response",
        description="Conservative planning for economic uncertainty. Prioritize survival and maintain optionality.",
        category="survival",
        tags=["recession", "conservative", "defensive"],
        recommended_for="During market downturns or economic uncertainty",
        assumptions=AssumptionSet(
            name="Market Downturn Response",
            revenue_growth=RevenueGrowthAssumption(
                monthly_growth_rate=Distribution(
                    type=DistributionType.NORMAL,
                    mean=0.01,
                    std=0.03
                )
            ),
            churn_rate=ChurnAssumption(
                monthly_churn_rate=Distribution(
                    type=DistributionType.BETA,
                    alpha=3,
                    beta=20
                )
            ),
            price_change=PriceChangeAssumption(
                annual_price_increase=Distribution(type=DistributionType.FIXED, value=0.0),
                timing_month=12
            ),
            burn_reduction=BurnReductionAssumption(
                monthly_reduction_rate=Distribution(type=DistributionType.FIXED, value=0.10),
                categories={"opex": 0.20, "payroll": 0.10, "marketing": 0.25}
            ),
            headcount_plan=HeadcountPlan(
                current_headcount=25,
                monthly_hires=[-1, -1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0] + [0] * 12,
                avg_salary=Distribution(type=DistributionType.FIXED, value=100000)
            ),
            fundraise=FundraiseAssumption(
                amount=3000000,
                timing_month=9,
                probability=Distribution(type=DistributionType.FIXED, value=0.25),
                instrument="safe"
            )
        )
    )
}


def get_template(template_id: str) -> Optional[StrategyTemplate]:
    """Get a strategy template by ID."""
    return STRATEGY_TEMPLATES.get(template_id)


def list_templates(category: Optional[str] = None) -> List[StrategyTemplate]:
    """List all available templates, optionally filtered by category."""
    templates = list(STRATEGY_TEMPLATES.values())
    if category:
        templates = [t for t in templates if t.category == category]
    return templates


def create_from_template(
    template_id: str,
    name: str,
    overrides: Optional[Dict] = None
) -> Optional[AssumptionSet]:
    """
    Create a new assumption set from a template with optional overrides.
    
    Args:
        template_id: ID of the template to use
        name: Name for the new assumption set
        overrides: Dictionary of fields to override
        
    Returns:
        New AssumptionSet or None if template not found
    """
    template = get_template(template_id)
    if not template:
        return None
    
    assumption_dict = template.assumptions.model_dump()
    assumption_dict["name"] = name
    assumption_dict["template_id"] = template_id
    
    if overrides:
        for key, value in overrides.items():
            if key in assumption_dict and isinstance(assumption_dict[key], dict):
                assumption_dict[key].update(value)
            else:
                assumption_dict[key] = value
    
    return AssumptionSet(**assumption_dict)
