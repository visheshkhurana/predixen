"""
Sensitivity Analysis Engine.

Implements One-At-a-Time (OAT) sensitivity analysis to determine which
assumptions have the greatest impact on simulation outcomes.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from copy import deepcopy
from server.lib.lazy_imports import np

from server.simulate.transformer import (
    transform_assumptions_to_inputs,
    get_nested_field_value,
    set_nested_field_value
)
from server.simulate.enhanced_monte_carlo import run_enhanced_monte_carlo


@dataclass
class SensitivityResult:
    """Result of sensitivity analysis for a single parameter."""
    parameter: str
    display_name: str
    base_value: float
    low_value: float
    high_value: float
    base_outcome: float
    low_outcome: float
    high_outcome: float
    impact_low: float
    impact_high: float
    total_impact: float
    sensitivity_score: float


SENSITIVITY_PARAMETERS = [
    {
        "path": "revenue_growth.monthly_growth_rate",
        "display_name": "Revenue Growth Rate",
        "default": 0.05,
        "min": 0.0,
        "max": 0.20
    },
    {
        "path": "churn.monthly_churn_rate",
        "display_name": "Monthly Churn Rate",
        "default": 0.03,
        "min": 0.01,
        "max": 0.15
    },
    {
        "path": "burn_reduction.monthly_reduction_rate",
        "display_name": "Burn Reduction Rate",
        "default": 0.02,
        "min": 0.0,
        "max": 0.10
    },
    {
        "path": "price_change.price_change_pct",
        "display_name": "Price Change %",
        "default": 0.0,
        "min": -0.15,
        "max": 0.25
    },
    {
        "path": "headcount_plan.monthly_hires",
        "display_name": "Monthly Hires",
        "default": 1,
        "min": 0,
        "max": 5
    },
    {
        "path": "fundraise.raise_amount",
        "display_name": "Fundraise Amount",
        "default": 0,
        "min": 0,
        "max": 5000000
    }
]


def run_sensitivity_analysis(
    assumptions_json: Dict[str, Any],
    baseline_metrics: Dict[str, float],
    target_metric: str = "runway_months",
    perturbation_pct: float = 0.10,
    iterations: int = 500,
    horizon_months: int = 24
) -> Dict[str, Any]:
    """
    Run sensitivity analysis on a set of assumptions.
    
    Uses OAT (One-At-a-Time) method:
    1. Run baseline simulation
    2. For each parameter, perturb by ±perturbation_pct
    3. Measure impact on target metric
    4. Rank parameters by total impact
    
    Args:
        assumptions_json: The assumption set configuration
        baseline_metrics: Current financial metrics
        target_metric: Which output to measure ("runway_months", "survival_probability", "cash_balance")
        perturbation_pct: How much to vary each parameter (0.10 = ±10%)
        iterations: Number of Monte Carlo iterations per run
        horizon_months: Simulation horizon
    
    Returns:
        Dictionary with sensitivity results including tornado chart data
    """
    base_inputs = transform_assumptions_to_inputs(assumptions_json, baseline_metrics)
    base_result = run_enhanced_monte_carlo(
        inputs=base_inputs,
        iterations=iterations,
        horizon_months=horizon_months
    )
    base_outcome = _extract_metric(base_result, target_metric)
    
    results: List[SensitivityResult] = []
    
    for param_config in SENSITIVITY_PARAMETERS:
        param_path = param_config["path"]
        display_name = param_config["display_name"]
        default_val = param_config["default"]
        param_min = param_config["min"]
        param_max = param_config["max"]
        
        base_value = get_nested_field_value(assumptions_json, param_path, default_val)
        if base_value is None or base_value == 0:
            base_value = default_val
        
        if isinstance(base_value, (int, float)):
            low_value = base_value * (1 - perturbation_pct)
            high_value = base_value * (1 + perturbation_pct)
            
            low_value = max(param_min, low_value)
            high_value = min(param_max, high_value)
        else:
            continue
        
        low_assumptions = deepcopy(assumptions_json)
        set_nested_field_value(low_assumptions, param_path, low_value)
        low_inputs = transform_assumptions_to_inputs(low_assumptions, baseline_metrics)
        low_result = run_enhanced_monte_carlo(
            inputs=low_inputs,
            iterations=iterations,
            horizon_months=horizon_months
        )
        low_outcome = _extract_metric(low_result, target_metric)
        
        high_assumptions = deepcopy(assumptions_json)
        set_nested_field_value(high_assumptions, param_path, high_value)
        high_inputs = transform_assumptions_to_inputs(high_assumptions, baseline_metrics)
        high_result = run_enhanced_monte_carlo(
            inputs=high_inputs,
            iterations=iterations,
            horizon_months=horizon_months
        )
        high_outcome = _extract_metric(high_result, target_metric)
        
        impact_low = low_outcome - base_outcome
        impact_high = high_outcome - base_outcome
        total_impact = abs(impact_high - impact_low)
        
        if base_outcome != 0:
            sensitivity_score = total_impact / abs(base_outcome) * 100
        else:
            sensitivity_score = total_impact * 100
        
        results.append(SensitivityResult(
            parameter=param_path,
            display_name=display_name,
            base_value=base_value,
            low_value=low_value,
            high_value=high_value,
            base_outcome=base_outcome,
            low_outcome=low_outcome,
            high_outcome=high_outcome,
            impact_low=impact_low,
            impact_high=impact_high,
            total_impact=total_impact,
            sensitivity_score=sensitivity_score
        ))
    
    results.sort(key=lambda x: x.total_impact, reverse=True)
    
    tornado_data = []
    for r in results:
        tornado_data.append({
            "parameter": r.display_name,
            "parameter_path": r.parameter,
            "low_impact": r.impact_low,
            "high_impact": r.impact_high,
            "total_impact": r.total_impact,
            "base_value": r.base_value,
            "low_value": r.low_value,
            "high_value": r.high_value
        })
    
    return {
        "target_metric": target_metric,
        "base_outcome": base_outcome,
        "perturbation_pct": perturbation_pct,
        "iterations": iterations,
        "horizon_months": horizon_months,
        "tornado_chart_data": tornado_data,
        "ranked_drivers": [
            {
                "rank": i + 1,
                "parameter": r.display_name,
                "sensitivity_score": round(r.sensitivity_score, 2),
                "total_impact": round(r.total_impact, 2)
            }
            for i, r in enumerate(results)
        ],
        "summary": {
            "most_influential": results[0].display_name if results else None,
            "least_influential": results[-1].display_name if results else None,
            "total_parameters_analyzed": len(results)
        }
    }


def _extract_metric(simulation_result: Dict[str, Any], metric: str) -> float:
    """Extract a specific metric from simulation results."""
    if metric == "runway_months":
        return simulation_result.get("summary", {}).get("runway_months", {}).get("p50", 12)
    elif metric == "survival_probability":
        return simulation_result.get("summary", {}).get("survival_probability", {}).get("p50", 0.5)
    elif metric == "cash_balance":
        return simulation_result.get("summary", {}).get("ending_cash", {}).get("p50", 0)
    elif metric == "revenue":
        monthly = simulation_result.get("monthly_projections", [])
        if monthly:
            return monthly[-1].get("revenue", {}).get("p50", 0)
        return 0
    else:
        return simulation_result.get("summary", {}).get(metric, {}).get("p50", 0)


def compute_elasticity(
    assumptions_json: Dict[str, Any],
    baseline_metrics: Dict[str, float],
    parameter_path: str,
    target_metric: str = "runway_months",
    delta_pct: float = 0.01,
    iterations: int = 500,
    horizon_months: int = 24
) -> Dict[str, Any]:
    """
    Compute the elasticity of a target metric with respect to a parameter.
    
    Elasticity = (% change in output) / (% change in input)
    
    Args:
        parameter_path: Which assumption to perturb
        target_metric: Which output to measure
        delta_pct: Small perturbation for derivative estimation
    
    Returns:
        Elasticity coefficient and interpretation
    """
    base_inputs = transform_assumptions_to_inputs(assumptions_json, baseline_metrics)
    base_result = run_enhanced_monte_carlo(
        inputs=base_inputs,
        iterations=iterations,
        horizon_months=horizon_months
    )
    base_outcome = _extract_metric(base_result, target_metric)
    
    base_value = get_nested_field_value(assumptions_json, parameter_path, 0.05)
    if base_value == 0:
        base_value = 0.01
    
    perturbed_value = base_value * (1 + delta_pct)
    perturbed_assumptions = deepcopy(assumptions_json)
    set_nested_field_value(perturbed_assumptions, parameter_path, perturbed_value)
    
    perturbed_inputs = transform_assumptions_to_inputs(perturbed_assumptions, baseline_metrics)
    perturbed_result = run_enhanced_monte_carlo(
        inputs=perturbed_inputs,
        iterations=iterations,
        horizon_months=horizon_months
    )
    perturbed_outcome = _extract_metric(perturbed_result, target_metric)
    
    if base_outcome != 0 and base_value != 0:
        pct_change_output = (perturbed_outcome - base_outcome) / base_outcome
        pct_change_input = delta_pct
        elasticity = pct_change_output / pct_change_input
    else:
        elasticity = 0
    
    if abs(elasticity) > 1:
        interpretation = "elastic (highly responsive)"
    elif abs(elasticity) == 1:
        interpretation = "unit elastic"
    else:
        interpretation = "inelastic (less responsive)"
    
    return {
        "parameter": parameter_path,
        "target_metric": target_metric,
        "elasticity": round(elasticity, 3),
        "interpretation": interpretation,
        "base_value": base_value,
        "base_outcome": base_outcome,
        "perturbed_value": perturbed_value,
        "perturbed_outcome": perturbed_outcome
    }
