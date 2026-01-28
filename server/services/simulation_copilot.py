"""
AI-powered simulation copilot service.

Provides context-aware prompts and narrative summaries for simulations.
"""

import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class ImpactLevel(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class AssumptionImpact:
    """Describes the impact of changing an assumption."""
    assumption_name: str
    old_value: float
    new_value: float
    impact_level: ImpactLevel
    primary_effects: List[str]
    secondary_effects: List[str]
    recommendation: str
    warning: Optional[str] = None


ASSUMPTION_RELATIONSHIPS = {
    "pricing_change_pct": {
        "affects": ["revenue", "cac", "churn", "ltv"],
        "positive_effects": {
            "revenue": "Increases revenue per customer",
            "ltv": "Improves lifetime value"
        },
        "negative_effects": {
            "cac": "May increase acquisition costs as value proposition changes",
            "churn": "Higher prices can increase customer churn"
        },
        "thresholds": {
            "warning_high": 15,
            "warning_low": -10
        }
    },
    "growth_uplift_pct": {
        "affects": ["revenue", "burn", "cac", "headcount"],
        "positive_effects": {
            "revenue": "Accelerates revenue growth"
        },
        "negative_effects": {
            "burn": "Faster growth requires more spending",
            "cac": "Scaling quickly can increase customer acquisition costs",
            "headcount": "May require hiring to support growth"
        },
        "thresholds": {
            "warning_high": 20,
            "warning_low": -15
        }
    },
    "burn_reduction_pct": {
        "affects": ["runway", "growth", "headcount", "product_velocity"],
        "positive_effects": {
            "runway": "Extends cash runway significantly"
        },
        "negative_effects": {
            "growth": "Cutting spend may slow growth",
            "headcount": "May require layoffs or hiring freezes",
            "product_velocity": "Less investment in product development"
        },
        "thresholds": {
            "warning_high": 30,
            "warning_low": -20
        }
    },
    "gross_margin_delta_pct": {
        "affects": ["profitability", "pricing_power", "unit_economics"],
        "positive_effects": {
            "profitability": "Improves path to profitability",
            "unit_economics": "Better unit economics"
        },
        "negative_effects": {},
        "thresholds": {
            "warning_high": 20,
            "warning_low": -10
        }
    },
    "churn_change_pct": {
        "affects": ["ltv", "revenue", "cac_efficiency"],
        "positive_effects": {},
        "negative_effects": {
            "ltv": "Higher churn reduces lifetime value",
            "revenue": "Lost customers mean lost revenue"
        },
        "thresholds": {
            "warning_high": 5,
            "warning_low": -5
        }
    },
    "cac_change_pct": {
        "affects": ["ltv_cac_ratio", "burn", "growth_efficiency"],
        "positive_effects": {},
        "negative_effects": {
            "ltv_cac_ratio": "Higher CAC worsens LTV/CAC ratio",
            "burn": "More expensive to acquire customers increases burn"
        },
        "thresholds": {
            "warning_high": 15,
            "warning_low": -30
        }
    }
}


def get_context_aware_prompt(
    assumption: str,
    old_value: float,
    new_value: float,
    current_metrics: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate a context-aware prompt explaining the impact of an assumption change.
    
    Args:
        assumption: The assumption being changed (e.g., "pricing_change_pct")
        old_value: The previous value
        new_value: The new value
        current_metrics: Current company metrics for context
        
    Returns:
        Dict with prompt, effects, and recommendations
    """
    delta = new_value - old_value
    relationship = ASSUMPTION_RELATIONSHIPS.get(assumption, {})
    
    if not relationship:
        return {
            "prompt": f"Changed from {old_value}% to {new_value}%",
            "effects": [],
            "recommendation": None,
            "warning": None
        }
    
    effects = []
    primary_metric = ""
    
    affected = relationship.get("affects", [])
    
    if delta > 0:
        for metric, effect in relationship.get("positive_effects", {}).items():
            effects.append({"metric": metric, "effect": effect, "direction": "positive"})
        for metric, effect in relationship.get("negative_effects", {}).items():
            if _is_negative_when_increasing(assumption, metric):
                effects.append({"metric": metric, "effect": effect, "direction": "negative"})
    else:
        for metric, effect in relationship.get("negative_effects", {}).items():
            if _is_positive_when_decreasing(assumption, metric):
                effects.append({"metric": metric, "effect": effect, "direction": "positive"})
    
    thresholds = relationship.get("thresholds", {})
    warning = None
    if new_value > thresholds.get("warning_high", float('inf')):
        warning = _generate_high_value_warning(assumption, new_value)
    elif new_value < thresholds.get("warning_low", float('-inf')):
        warning = _generate_low_value_warning(assumption, new_value)
    
    prompt = _generate_natural_language_prompt(
        assumption, old_value, new_value, delta, effects, current_metrics
    )
    
    recommendation = _generate_recommendation(
        assumption, new_value, effects, current_metrics
    )
    
    return {
        "prompt": prompt,
        "effects": effects,
        "recommendation": recommendation,
        "warning": warning,
        "delta": delta,
        "impact_level": _calculate_impact_level(assumption, abs(delta))
    }


def _is_negative_when_increasing(assumption: str, metric: str) -> bool:
    """Check if increasing this assumption has negative effect on metric."""
    negative_relationships = {
        "pricing_change_pct": ["cac", "churn"],
        "growth_uplift_pct": ["burn", "cac"],
        "burn_reduction_pct": ["growth", "headcount", "product_velocity"],
        "churn_change_pct": ["ltv", "revenue"],
        "cac_change_pct": ["ltv_cac_ratio", "burn"]
    }
    return metric in negative_relationships.get(assumption, [])


def _is_positive_when_decreasing(assumption: str, metric: str) -> bool:
    """Check if decreasing this assumption has positive effect on metric."""
    positive_when_decreasing = {
        "churn_change_pct": ["ltv", "revenue"],
        "cac_change_pct": ["ltv_cac_ratio", "burn"],
        "burn_reduction_pct": []
    }
    return metric in positive_when_decreasing.get(assumption, [])


def _generate_high_value_warning(assumption: str, value: float) -> str:
    """Generate warning for high assumption values."""
    warnings = {
        "pricing_change_pct": f"A {value:.0f}% price increase is aggressive and may significantly impact customer acquisition and retention.",
        "growth_uplift_pct": f"A {value:.0f}% growth target requires substantial investment and may not be sustainable.",
        "burn_reduction_pct": f"Cutting burn by {value:.0f}% is dramatic and may require significant layoffs or restructuring.",
        "gross_margin_delta_pct": f"A {value:.0f}% margin improvement is ambitious - verify operational feasibility.",
        "churn_change_pct": f"Assuming {value:.0f}% higher churn significantly impacts revenue projections.",
        "cac_change_pct": f"A {value:.0f}% CAC increase will substantially impact unit economics."
    }
    return warnings.get(assumption, f"Value of {value}% is higher than typical ranges.")


def _generate_low_value_warning(assumption: str, value: float) -> str:
    """Generate warning for low assumption values."""
    warnings = {
        "pricing_change_pct": f"A {abs(value):.0f}% price cut may hurt margins significantly.",
        "growth_uplift_pct": f"A {abs(value):.0f}% growth decline indicates a conservative or declining scenario.",
        "burn_reduction_pct": f"Increasing burn by {abs(value):.0f}% will shorten runway.",
        "churn_change_pct": f"A {abs(value):.0f}% churn reduction is optimistic - validate with retention data."
    }
    return warnings.get(assumption)


def _generate_natural_language_prompt(
    assumption: str,
    old_value: float,
    new_value: float,
    delta: float,
    effects: List[Dict],
    metrics: Dict[str, Any]
) -> str:
    """Generate a natural language explanation of the change."""
    assumption_names = {
        "pricing_change_pct": "pricing",
        "growth_uplift_pct": "growth rate",
        "burn_reduction_pct": "burn rate",
        "gross_margin_delta_pct": "gross margin",
        "churn_change_pct": "churn rate",
        "cac_change_pct": "customer acquisition cost"
    }
    
    name = assumption_names.get(assumption, assumption)
    direction = "increasing" if delta > 0 else "decreasing"
    
    runway = metrics.get("runway_months", 12)
    burn = metrics.get("monthly_burn", 0)
    revenue = metrics.get("monthly_revenue", 0)
    
    if assumption == "pricing_change_pct":
        if delta > 0:
            return f"Increasing prices by {new_value:.0f}% will boost revenue per customer, but may slow acquisition if you don't add value to justify the increase."
        else:
            return f"Lowering prices by {abs(new_value):.0f}% may accelerate growth but will reduce margins. Consider if volume will offset the per-unit revenue loss."
    
    elif assumption == "growth_uplift_pct":
        if delta > 0:
            return f"Targeting {new_value:.0f}% faster growth will require additional marketing spend and potentially more hires to support increased demand."
        else:
            return f"A {abs(new_value):.0f}% slower growth assumption is more conservative. This may extend runway but delays reaching scale."
    
    elif assumption == "burn_reduction_pct":
        if delta > 0:
            est_runway_gain = (new_value / 100) * runway * 0.7
            return f"Cutting burn by {new_value:.0f}% could extend runway by roughly {est_runway_gain:.0f} months, but may require reducing headcount or slowing product development."
        else:
            return f"Increasing burn by {abs(new_value):.0f}% will shorten runway. Ensure the additional spend drives proportional value."
    
    elif assumption == "gross_margin_delta_pct":
        if delta > 0:
            return f"Improving gross margin by {new_value:.0f}% means better unit economics. This could come from pricing power, lower COGS, or operational efficiency."
        else:
            return f"A {abs(new_value):.0f}% margin decline signals higher costs or pricing pressure. Monitor the impact on path to profitability."
    
    elif assumption == "churn_change_pct":
        if delta > 0:
            return f"A {new_value:.0f}% increase in churn will reduce lifetime value and require more new customers to maintain revenue."
        else:
            return f"Reducing churn by {abs(new_value):.0f}% significantly improves LTV. This is often the most efficient way to grow revenue."
    
    elif assumption == "cac_change_pct":
        if delta > 0:
            return f"A {new_value:.0f}% increase in CAC means customers are more expensive to acquire. This often happens when scaling paid channels."
        else:
            return f"Lowering CAC by {abs(new_value):.0f}% improves unit economics. This could come from better conversion rates or more efficient channels."
    
    return f"{name.title()} changed from {old_value:.0f}% to {new_value:.0f}%."


def _generate_recommendation(
    assumption: str,
    value: float,
    effects: List[Dict],
    metrics: Dict[str, Any]
) -> Optional[str]:
    """Generate a recommendation based on the assumption change."""
    runway = metrics.get("runway_months", 12)
    
    if assumption == "burn_reduction_pct" and value > 20 and runway < 12:
        return "With limited runway, significant cost cuts may be necessary. Consider reducing hiring rather than cutting existing team."
    
    if assumption == "growth_uplift_pct" and value > 15:
        return "High growth targets require proportional investment. Ensure you have the capital and team to support this trajectory."
    
    if assumption == "pricing_change_pct" and value > 10:
        return "Large price increases work best when paired with value-adding features. Consider a phased rollout."
    
    if assumption == "churn_change_pct" and value > 3:
        return "Higher churn is concerning. Consider investing in customer success or product improvements."
    
    return None


def _calculate_impact_level(assumption: str, delta: float) -> str:
    """Calculate the impact level of a change."""
    high_impact_thresholds = {
        "pricing_change_pct": 10,
        "growth_uplift_pct": 10,
        "burn_reduction_pct": 15,
        "gross_margin_delta_pct": 10,
        "churn_change_pct": 3,
        "cac_change_pct": 15
    }
    
    medium_impact_thresholds = {
        "pricing_change_pct": 5,
        "growth_uplift_pct": 5,
        "burn_reduction_pct": 8,
        "gross_margin_delta_pct": 5,
        "churn_change_pct": 1.5,
        "cac_change_pct": 8
    }
    
    high_threshold = high_impact_thresholds.get(assumption, 10)
    medium_threshold = medium_impact_thresholds.get(assumption, 5)
    
    if delta >= high_threshold:
        return "high"
    elif delta >= medium_threshold:
        return "medium"
    return "low"


def generate_simulation_narrative(
    simulation_results: Dict[str, Any],
    scenario_params: Dict[str, Any],
    company_metrics: Dict[str, Any],
    scenario_name: str = "Custom Scenario"
) -> Dict[str, Any]:
    """
    Generate a narrative summary of simulation results.
    
    Args:
        simulation_results: Results from Monte Carlo simulation
        scenario_params: The scenario parameters used
        company_metrics: Current company metrics
        scenario_name: Name of the scenario
        
    Returns:
        Dict with summary, insights, drivers, and recommendations
    """
    runway = simulation_results.get("runway", {})
    survival = simulation_results.get("survival", {})
    summary = simulation_results.get("summary", {})
    
    runway_p50 = runway.get("p50", 12)
    runway_p10 = runway.get("p10", 6)
    runway_p90 = runway.get("p90", 18)
    
    survival_12m = survival.get("12m", 80)
    survival_18m = survival.get("18m", 60)
    survival_24m = survival.get("24m", 40)
    
    end_cash = summary.get("end_cash", 0)
    monthly_burn = summary.get("monthly_burn", 0) or summary.get("monthly_burn_p50", 0)
    
    is_healthy = survival_18m >= 75
    is_warning = survival_18m >= 50 and survival_18m < 75
    is_critical = survival_18m < 50
    
    narrative_parts = []
    
    if is_healthy:
        narrative_parts.append(
            f"Under the {scenario_name} scenario, the company shows a healthy financial outlook "
            f"with a median runway of {runway_p50:.1f} months and an {survival_18m:.0f}% probability "
            f"of surviving 18 months."
        )
    elif is_warning:
        narrative_parts.append(
            f"The {scenario_name} scenario shows moderate financial risk. "
            f"With a median runway of {runway_p50:.1f} months and a {survival_18m:.0f}% chance of "
            f"surviving 18 months, the company should monitor cash carefully and consider contingency plans."
        )
    else:
        narrative_parts.append(
            f"The {scenario_name} scenario indicates elevated financial risk. "
            f"With only {runway_p50:.1f} months of median runway and a {survival_18m:.0f}% survival probability "
            f"at 18 months, immediate action is recommended to extend runway or secure funding."
        )
    
    if runway_p90 - runway_p10 > 6:
        narrative_parts.append(
            f"There is significant uncertainty in the projections, with runway ranging from "
            f"{runway_p10:.0f} months (pessimistic) to {runway_p90:.0f} months (optimistic)."
        )
    
    if end_cash and monthly_burn:
        months_at_current = end_cash / monthly_burn if monthly_burn > 0 else 0
        if months_at_current < 6 and is_critical:
            narrative_parts.append(
                f"At the projected monthly burn of ${monthly_burn:,.0f}, "
                f"cash reserves may be exhausted within {months_at_current:.0f} months."
            )
    
    drivers = _identify_key_drivers(scenario_params, simulation_results)
    
    insights = _generate_comparative_insights(simulation_results, scenario_params)
    
    recommendations = _generate_narrative_recommendations(
        is_healthy, is_warning, is_critical,
        runway_p50, survival_18m, drivers, scenario_params
    )
    
    return {
        "summary": " ".join(narrative_parts),
        "health_status": "healthy" if is_healthy else ("warning" if is_warning else "critical"),
        "key_metrics": {
            "runway_p50": runway_p50,
            "runway_range": f"{runway_p10:.0f} - {runway_p90:.0f} months",
            "survival_18m": survival_18m,
            "survival_24m": survival_24m,
            "end_cash": end_cash,
            "monthly_burn": monthly_burn
        },
        "drivers": drivers,
        "insights": insights,
        "recommendations": recommendations
    }


def _identify_key_drivers(
    scenario_params: Dict[str, Any],
    simulation_results: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Identify the key drivers impacting the simulation results."""
    drivers = []
    
    driver_impact = {
        "burn_reduction_pct": {"name": "Burn Reduction", "impact": "runway", "weight": 1.5},
        "growth_uplift_pct": {"name": "Growth Rate", "impact": "revenue", "weight": 1.2},
        "pricing_change_pct": {"name": "Pricing Change", "impact": "revenue", "weight": 1.0},
        "churn_change_pct": {"name": "Churn Rate", "impact": "ltv", "weight": 1.3},
        "gross_margin_delta_pct": {"name": "Gross Margin", "impact": "profitability", "weight": 0.8},
        "cac_change_pct": {"name": "CAC Change", "impact": "efficiency", "weight": 0.9}
    }
    
    for param, info in driver_impact.items():
        value = scenario_params.get(param, 0)
        if value != 0:
            impact_score = abs(value) * info["weight"]
            drivers.append({
                "name": info["name"],
                "value": value,
                "impact_area": info["impact"],
                "impact_score": impact_score,
                "description": _get_driver_description(param, value)
            })
    
    if scenario_params.get("fundraise_amount", 0) > 0:
        drivers.append({
            "name": "Fundraising",
            "value": scenario_params.get("fundraise_amount", 0),
            "impact_area": "runway",
            "impact_score": 100,
            "description": f"Raising ${scenario_params.get('fundraise_amount', 0):,.0f} in month {scenario_params.get('fundraise_month', 1)}"
        })
    
    drivers.sort(key=lambda x: x["impact_score"], reverse=True)
    return drivers[:5]


def _get_driver_description(param: str, value: float) -> str:
    """Get a description for a driver."""
    descriptions = {
        "burn_reduction_pct": f"{'Reducing' if value > 0 else 'Increasing'} burn by {abs(value):.0f}%",
        "growth_uplift_pct": f"{'Accelerating' if value > 0 else 'Slowing'} growth by {abs(value):.0f}%",
        "pricing_change_pct": f"{'Increasing' if value > 0 else 'Decreasing'} prices by {abs(value):.0f}%",
        "churn_change_pct": f"Churn {'increasing' if value > 0 else 'decreasing'} by {abs(value):.0f}%",
        "gross_margin_delta_pct": f"Margin {'improving' if value > 0 else 'declining'} by {abs(value):.0f}%",
        "cac_change_pct": f"CAC {'increasing' if value > 0 else 'decreasing'} by {abs(value):.0f}%"
    }
    return descriptions.get(param, f"{param} = {value}%")


def _generate_comparative_insights(
    simulation_results: Dict[str, Any],
    scenario_params: Dict[str, Any]
) -> List[str]:
    """Generate comparative insights about the scenario."""
    insights = []
    
    runway_p50 = simulation_results.get("runway", {}).get("p50", 12)
    survival_18m = simulation_results.get("survival", {}).get("18m", 60)
    
    burn_reduction = scenario_params.get("burn_reduction_pct", 0)
    if burn_reduction > 0:
        est_runway_gain = burn_reduction * 0.15
        insights.append(
            f"The {burn_reduction:.0f}% burn reduction is the primary driver extending runway by approximately {est_runway_gain:.1f} months."
        )
    
    growth = scenario_params.get("growth_uplift_pct", 0)
    if growth > 10:
        insights.append(
            f"The {growth:.0f}% growth target is aggressive and will require increased investment in sales and marketing."
        )
    elif growth < -5:
        insights.append(
            f"The {abs(growth):.0f}% growth decline assumption reflects a conservative or downturn scenario."
        )
    
    fundraise = scenario_params.get("fundraise_amount", 0)
    if fundraise > 0:
        insights.append(
            f"The planned ${fundraise:,.0f} fundraise significantly impacts the projections and is critical for the runway forecast."
        )
    
    pricing = scenario_params.get("pricing_change_pct", 0)
    churn = scenario_params.get("churn_change_pct", 0)
    if pricing > 10 and churn > 0:
        insights.append(
            "Note: Price increases combined with higher churn may compound negatively. Monitor customer feedback closely."
        )
    
    return insights[:4]


def _generate_narrative_recommendations(
    is_healthy: bool,
    is_warning: bool,
    is_critical: bool,
    runway: float,
    survival: float,
    drivers: List[Dict],
    params: Dict[str, Any]
) -> List[str]:
    """Generate actionable recommendations based on the scenario."""
    recommendations = []
    
    if is_critical:
        recommendations.append(
            "Consider immediate actions to extend runway: reduce non-essential spending, "
            "accelerate fundraising timeline, or explore revenue acceleration opportunities."
        )
        if runway < 6:
            recommendations.append(
                "With less than 6 months runway, begin fundraising or bridge financing discussions immediately."
            )
    elif is_warning:
        recommendations.append(
            "Monitor cash position closely and maintain multiple scenarios for contingency planning."
        )
        if params.get("burn_reduction_pct", 0) == 0:
            recommendations.append(
                "Consider modeling a cost reduction scenario to understand runway extension options."
            )
    else:
        recommendations.append(
            "Financial position is healthy. Consider investing in growth initiatives while maintaining discipline."
        )
    
    if params.get("fundraise_amount", 0) == 0 and runway < 18:
        recommendations.append(
            "Model a fundraising scenario to understand the impact of additional capital on growth options."
        )
    
    top_driver = drivers[0] if drivers else None
    if top_driver and top_driver["impact_area"] == "runway":
        recommendations.append(
            f"The most impactful lever is {top_driver['name']}. "
            f"Consider running sensitivity analysis on this assumption."
        )
    
    return recommendations[:4]


def validate_assumption_value(
    assumption: str,
    value: float
) -> Dict[str, Any]:
    """
    Validate an assumption value and return any warnings.
    
    Args:
        assumption: The assumption name
        value: The proposed value
        
    Returns:
        Dict with is_valid, warning, and suggested_range
    """
    ranges = {
        "pricing_change_pct": (-20, 30),
        "growth_uplift_pct": (-20, 50),
        "burn_reduction_pct": (-30, 50),
        "gross_margin_delta_pct": (-15, 25),
        "churn_change_pct": (-10, 15),
        "cac_change_pct": (-40, 40)
    }
    
    typical_ranges = {
        "pricing_change_pct": (-5, 15),
        "growth_uplift_pct": (-5, 20),
        "burn_reduction_pct": (0, 25),
        "gross_margin_delta_pct": (-5, 10),
        "churn_change_pct": (-3, 3),
        "cac_change_pct": (-20, 20)
    }
    
    valid_range = ranges.get(assumption, (-100, 100))
    typical = typical_ranges.get(assumption, (-50, 50))
    
    is_valid = valid_range[0] <= value <= valid_range[1]
    is_typical = typical[0] <= value <= typical[1]
    
    warning = None
    if not is_valid:
        warning = f"Value {value}% is outside valid range ({valid_range[0]}% to {valid_range[1]}%)"
    elif not is_typical:
        warning = f"Value {value}% is outside typical range ({typical[0]}% to {typical[1]}%)"
    
    return {
        "is_valid": is_valid,
        "is_typical": is_typical,
        "warning": warning,
        "valid_range": valid_range,
        "typical_range": typical
    }
