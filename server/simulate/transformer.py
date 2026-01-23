"""
Transformation Layer: Converts AssumptionSet to EnhancedSimulationInputs.

This module bridges the gap between high-level assumption sets (user-friendly)
and low-level simulation inputs (engine-ready).
"""

import logging
from typing import Dict, Any, Optional, List
from server.simulate.assumptions import (
    AssumptionSet,
    Distribution,
    RevenueGrowthAssumption,
    ChurnAssumption,
    PriceChangeAssumption,
    BurnReductionAssumption,
    HeadcountPlan,
    FundraiseAssumption,
    DistributionType,
)
from server.simulate.enhanced_monte_carlo import (
    EnhancedSimulationInputs,
    DistributionParams,
    ScenarioEvent,
)

logger = logging.getLogger(__name__)


def distribution_to_params(dist: Distribution) -> DistributionParams:
    """Convert an AssumptionSet Distribution to a Monte Carlo DistributionParams."""
    dist_type_map = {
        DistributionType.FIXED: "fixed",
        DistributionType.NORMAL: "normal",
        DistributionType.LOGNORMAL: "lognormal",
        DistributionType.UNIFORM: "uniform",
        DistributionType.TRIANGULAR: "triangular",
        DistributionType.BETA: "beta",
    }
    
    return DistributionParams(
        type=dist_type_map.get(dist.type, "fixed"),
        value=dist.value,
        mean=dist.mean,
        std_dev=dist.std,
        min_val=dist.min,
        max_val=dist.max,
        mode=dist.mode,
        values=None,
    )


def get_distribution_mean(dist: Distribution) -> float:
    """Extract the expected mean value from a distribution."""
    if dist.type == DistributionType.FIXED:
        return dist.value or 0.0
    elif dist.type in (DistributionType.NORMAL, DistributionType.LOGNORMAL):
        return dist.mean or 0.0
    elif dist.type == DistributionType.UNIFORM:
        min_v = dist.min or 0.0
        max_v = dist.max or 0.0
        return (min_v + max_v) / 2.0
    elif dist.type == DistributionType.TRIANGULAR:
        min_v = dist.min or 0.0
        max_v = dist.max or 0.0
        mode_v = dist.mode or (min_v + max_v) / 2.0
        return (min_v + mode_v + max_v) / 3.0
    elif dist.type == DistributionType.BETA:
        a = dist.alpha or 2.0
        b = dist.beta or 2.0
        return a / (a + b)
    return 0.0


def get_distribution_std(dist: Distribution) -> float:
    """Extract the standard deviation from a distribution."""
    if dist.type == DistributionType.FIXED:
        return 0.0
    elif dist.type in (DistributionType.NORMAL, DistributionType.LOGNORMAL):
        return dist.std or 0.0
    elif dist.type == DistributionType.UNIFORM:
        min_v = dist.min or 0.0
        max_v = dist.max or 0.0
        return (max_v - min_v) / 3.46
    elif dist.type == DistributionType.TRIANGULAR:
        min_v = dist.min or 0.0
        max_v = dist.max or 0.0
        mode_v = dist.mode or (min_v + max_v) / 2.0
        variance = (min_v**2 + max_v**2 + mode_v**2 - min_v*max_v - min_v*mode_v - max_v*mode_v) / 18
        return variance ** 0.5
    elif dist.type == DistributionType.BETA:
        a = dist.alpha or 2.0
        b = dist.beta or 2.0
        variance = (a * b) / ((a + b)**2 * (a + b + 1))
        return variance ** 0.5
    return 1.0


def build_events_from_assumptions(assumptions: AssumptionSet) -> List[ScenarioEvent]:
    """Build scenario events from assumption set (e.g., fundraise, headcount changes)."""
    events = []
    
    if assumptions.fundraise and assumptions.fundraise.amount > 0:
        prob_dist = assumptions.fundraise.probability
        probability = get_distribution_mean(prob_dist)
        if probability > 0:
            fundraise_event = ScenarioEvent(
                id="fundraise_event",
                type="fundraise",
                name="Fundraise Round",
                month=assumptions.fundraise.timing_month,
                probability=probability,
                impact={},
                description=f"Raise ${assumptions.fundraise.amount:,.0f}",
            )
            events.append(fundraise_event)
    
    if assumptions.headcount_plan and assumptions.headcount_plan.monthly_hires:
        for month, hires in enumerate(assumptions.headcount_plan.monthly_hires):
            if hires > 0:
                hire_event = ScenarioEvent(
                    id=f"hire_month_{month + 1}",
                    type="headcount",
                    name=f"Month {month + 1} Hiring",
                    month=month + 1,
                    probability=1.0,
                    impact={},
                    description=f"Add {hires} employees",
                )
                events.append(hire_event)
    
    return events


def transform_assumptions_to_inputs(
    assumptions: AssumptionSet,
    baseline_metrics: Dict[str, float],
) -> EnhancedSimulationInputs:
    """
    Transform an AssumptionSet into EnhancedSimulationInputs.
    
    Args:
        assumptions: The user-defined assumption set (nested structure)
        baseline_metrics: Current financial metrics from the company's latest data
            Expected keys: revenue, growth_rate, gross_margin, opex, payroll,
                          other_costs, cash, churn_rate, cac, ltv
    
    Returns:
        EnhancedSimulationInputs ready for Monte Carlo simulation
    """
    revenue_growth_dist = assumptions.revenue_growth.monthly_growth_rate
    revenue_growth_mean = get_distribution_mean(revenue_growth_dist) * 100
    revenue_growth_std = get_distribution_std(revenue_growth_dist) * 100
    
    churn_dist = assumptions.churn_rate.monthly_churn_rate
    churn_mean = get_distribution_mean(churn_dist) * 100
    churn_std = get_distribution_std(churn_dist) * 100
    
    price_change_dist = assumptions.price_change.annual_price_increase
    price_change_mean = get_distribution_mean(price_change_dist) * 100
    
    burn_reduction_dist = assumptions.burn_reduction.monthly_reduction_rate
    burn_reduction_mean = get_distribution_mean(burn_reduction_dist) * 100
    
    gross_margin_change = 0.0
    
    fundraise_month = None
    fundraise_amount = 0.0
    if assumptions.fundraise and assumptions.fundraise.amount > 0:
        prob = get_distribution_mean(assumptions.fundraise.probability)
        if prob > 0.5:
            fundraise_month = assumptions.fundraise.timing_month
            fundraise_amount = assumptions.fundraise.amount
    
    events = build_events_from_assumptions(assumptions)
    
    inputs = EnhancedSimulationInputs(
        baseline_revenue=baseline_metrics.get("revenue", 100000),
        baseline_growth_rate=baseline_metrics.get("growth_rate", 5.0),
        gross_margin=baseline_metrics.get("gross_margin", 70.0),
        opex=baseline_metrics.get("opex", 50000),
        payroll=baseline_metrics.get("payroll", 100000),
        other_costs=baseline_metrics.get("other_costs", 20000),
        cash_balance=baseline_metrics.get("cash", 1000000),
        churn_rate=churn_mean if churn_mean > 0 else baseline_metrics.get("churn_rate", 5.0),
        cac=baseline_metrics.get("cac", 0),
        ltv=baseline_metrics.get("ltv", 0),
        pricing_change_pct=price_change_mean,
        growth_uplift_pct=revenue_growth_mean,
        burn_reduction_pct=burn_reduction_mean,
        fundraise_month=fundraise_month,
        fundraise_amount=fundraise_amount,
        gross_margin_delta_pct=gross_margin_change,
        events=events,
        growth_sigma=revenue_growth_std if revenue_growth_std > 0 else 3.0,
        margin_sigma=2.0,
        churn_sigma=churn_std if churn_std > 0 else 1.0,
    )
    
    return inputs


def extract_baseline_from_truth_scan(truth_scan_data: Dict[str, Any]) -> Dict[str, float]:
    """
    Extract baseline metrics from a truth scan result.
    
    Args:
        truth_scan_data: Output from the truth scan engine
    
    Returns:
        Dictionary of baseline metrics for simulation
    """
    metrics = truth_scan_data.get("metrics", {})
    
    return {
        "revenue": float(metrics.get("arr", 0) or metrics.get("mrr", 0) * 12 or 100000),
        "growth_rate": float(metrics.get("revenue_growth_rate", 5.0) or 5.0),
        "gross_margin": float(metrics.get("gross_margin", 70.0) or 70.0),
        "opex": float(metrics.get("opex", 50000) or 50000),
        "payroll": float(metrics.get("payroll", 100000) or 100000),
        "other_costs": float(metrics.get("other_costs", 20000) or 20000),
        "cash": float(metrics.get("cash_balance", 1000000) or 1000000),
        "churn_rate": float(metrics.get("churn_rate", 5.0) or 5.0),
        "cac": float(metrics.get("cac", 0) or 0),
        "ltv": float(metrics.get("ltv", 0) or 0),
    }


def extract_baseline_from_financials(financials: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Extract baseline metrics from raw financial records.
    
    Args:
        financials: List of financial record dictionaries
    
    Returns:
        Dictionary of baseline metrics for simulation
    """
    if not financials:
        return {
            "revenue": 100000,
            "growth_rate": 5.0,
            "gross_margin": 70.0,
            "opex": 50000,
            "payroll": 100000,
            "other_costs": 20000,
            "cash": 1000000,
            "churn_rate": 5.0,
            "cac": 0,
            "ltv": 0,
        }
    
    sorted_records = sorted(financials, key=lambda x: x.get("period_end") or "", reverse=True)
    latest = sorted_records[0] if sorted_records else {}
    
    revenue = float(latest.get("revenue", 0) or 0)
    cogs = float(latest.get("cogs", 0) or 0)
    gross_margin = ((revenue - cogs) / revenue * 100) if revenue > 0 else 70.0
    
    opex = float(latest.get("sales_marketing", 0) or 0) + float(latest.get("general_admin", 0) or 0)
    payroll = float(latest.get("payroll", 0) or latest.get("operating_expenses", 0) * 0.6 or 100000)
    other = float(latest.get("other_costs", 0) or latest.get("operating_expenses", 0) * 0.2 or 20000)
    
    growth_rate = 5.0
    if len(sorted_records) >= 2:
        prev = sorted_records[1]
        prev_rev = float(prev.get("revenue", 0) or 0)
        if prev_rev > 0:
            growth_rate = ((revenue - prev_rev) / prev_rev * 100)
    
    return {
        "revenue": revenue if revenue > 0 else 100000,
        "growth_rate": growth_rate,
        "gross_margin": gross_margin,
        "opex": opex if opex > 0 else 50000,
        "payroll": payroll if payroll > 0 else 100000,
        "other_costs": other if other > 0 else 20000,
        "cash": float(latest.get("cash", 1000000) or 1000000),
        "churn_rate": float(latest.get("churn_rate", 5.0) or 5.0),
        "cac": float(latest.get("cac", 0) or 0),
        "ltv": float(latest.get("ltv", 0) or 0),
    }
