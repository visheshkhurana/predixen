"""
Recommendations Engine.

Generates actionable recommendations based on simulation results
and health check thresholds.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class RecommendationType(str, Enum):
    REDUCE_BURN = "reduce_burn"
    INCREASE_REVENUE = "increase_revenue"
    DELAY_HIRING = "delay_hiring"
    ADJUST_PRICING = "adjust_pricing"
    FUNDRAISE = "fundraise"
    REDUCE_CHURN = "reduce_churn"
    EXTEND_RUNWAY = "extend_runway"
    IMPROVE_MARGINS = "improve_margins"


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Recommendation:
    """A specific action recommendation."""
    type: RecommendationType
    title: str
    description: str
    priority: Priority
    impact: Dict[str, Any]
    action_details: Dict[str, Any]


HEALTH_THRESHOLDS = {
    "runway_months": {
        "critical": 6,
        "warning": 9,
        "healthy": 12
    },
    "survival_probability": {
        "critical": 0.50,
        "warning": 0.70,
        "healthy": 0.85
    },
    "burn_multiple": {
        "critical": 3.0,
        "warning": 2.0,
        "healthy": 1.5
    },
    "gross_margin": {
        "critical": 0.40,
        "warning": 0.55,
        "healthy": 0.70
    },
    "churn_rate": {
        "critical": 0.10,
        "warning": 0.07,
        "healthy": 0.05
    }
}


def generate_recommendations(
    simulation_results: Dict[str, Any],
    baseline_metrics: Optional[Dict[str, float]] = None,
    assumptions_json: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate recommendations based on simulation results and health checks.
    
    Args:
        simulation_results: Output from Monte Carlo simulation
        baseline_metrics: Current financial state
        assumptions_json: Current assumption configuration
    
    Returns:
        Dictionary with recommendations, health scores, and action items
    """
    summary = simulation_results.get("summary", {})
    
    runway = _get_p50(summary.get("runway_months", {}))
    survival_prob = _get_p50(summary.get("survival_probability", {}))
    ending_cash = _get_p50(summary.get("ending_cash", {}))
    
    baseline = baseline_metrics or {}
    burn_rate = baseline.get("burn_rate", 50000)
    monthly_revenue = baseline.get("monthly_revenue", 0)
    churn_rate = baseline.get("churn_rate", 0.05)
    gross_margin = baseline.get("gross_margin", 0.70)
    
    if burn_rate > 0 and monthly_revenue > 0:
        burn_multiple = burn_rate / monthly_revenue
    else:
        burn_multiple = 2.0
    
    health_scores = _calculate_health_scores(
        runway=runway,
        survival_prob=survival_prob,
        burn_multiple=burn_multiple,
        gross_margin=gross_margin,
        churn_rate=churn_rate
    )
    
    recommendations: List[Recommendation] = []
    
    if runway < HEALTH_THRESHOLDS["runway_months"]["critical"]:
        recommendations.extend(_generate_runway_critical_recommendations(
            runway, burn_rate, monthly_revenue, ending_cash
        ))
    elif runway < HEALTH_THRESHOLDS["runway_months"]["warning"]:
        recommendations.extend(_generate_runway_warning_recommendations(
            runway, burn_rate, monthly_revenue
        ))
    
    if survival_prob < HEALTH_THRESHOLDS["survival_probability"]["critical"]:
        recommendations.append(Recommendation(
            type=RecommendationType.FUNDRAISE,
            title="Consider Emergency Fundraising",
            description=f"With {survival_prob:.0%} survival probability, consider raising bridge funding to extend runway.",
            priority=Priority.CRITICAL,
            impact={"survival_improvement": "20-40%", "runway_extension": "6-12 months"},
            action_details={
                "suggested_raise": min(burn_rate * 12, 2000000),
                "urgency": "immediate"
            }
        ))
    
    if burn_multiple > HEALTH_THRESHOLDS["burn_multiple"]["critical"]:
        burn_reduction_needed = ((burn_multiple - 1.5) / burn_multiple) * 100
        recommendations.append(Recommendation(
            type=RecommendationType.REDUCE_BURN,
            title=f"Reduce Burn Rate by {burn_reduction_needed:.0f}%",
            description=f"Burn multiple of {burn_multiple:.1f}x is unsustainable. Target <1.5x.",
            priority=Priority.HIGH,
            impact={
                "runway_extension": f"{burn_reduction_needed * 0.3:.0f} months",
                "burn_reduction": f"${burn_rate * burn_reduction_needed / 100:,.0f}/month"
            },
            action_details={
                "current_burn": burn_rate,
                "target_burn": burn_rate * (1 - burn_reduction_needed / 100),
                "areas_to_review": ["marketing spend", "tool subscriptions", "contractor costs"]
            }
        ))
    
    if churn_rate > HEALTH_THRESHOLDS["churn_rate"]["critical"]:
        recommendations.append(Recommendation(
            type=RecommendationType.REDUCE_CHURN,
            title="Reduce Customer Churn",
            description=f"Monthly churn of {churn_rate:.1%} is high. Focus on retention.",
            priority=Priority.HIGH,
            impact={
                "ltv_improvement": f"{(1 / (churn_rate - 0.05)) / (1 / churn_rate) - 1:.0%}",
                "revenue_retention": "significant"
            },
            action_details={
                "current_churn": churn_rate,
                "target_churn": 0.05,
                "tactics": ["customer success outreach", "feature adoption campaigns", "pricing optimization"]
            }
        ))
    
    if gross_margin < HEALTH_THRESHOLDS["gross_margin"]["warning"]:
        recommendations.append(Recommendation(
            type=RecommendationType.IMPROVE_MARGINS,
            title="Improve Gross Margins",
            description=f"Gross margin of {gross_margin:.0%} is below healthy levels.",
            priority=Priority.MEDIUM,
            impact={
                "margin_improvement": f"{(0.70 - gross_margin):.0%}",
                "profitability": "improved unit economics"
            },
            action_details={
                "current_margin": gross_margin,
                "target_margin": 0.70,
                "levers": ["pricing increase", "COGS reduction", "operational efficiency"]
            }
        ))
    
    if monthly_revenue > 0 and monthly_revenue < burn_rate * 0.5:
        recommendations.append(Recommendation(
            type=RecommendationType.INCREASE_REVENUE,
            title="Accelerate Revenue Growth",
            description="Revenue covers less than 50% of burn. Focus on growth.",
            priority=Priority.HIGH,
            impact={
                "revenue_target": f"${burn_rate * 0.8:,.0f}/month",
                "timeline": "6-12 months"
            },
            action_details={
                "current_revenue": monthly_revenue,
                "revenue_gap": burn_rate * 0.8 - monthly_revenue,
                "growth_tactics": ["expand sales capacity", "increase pricing", "upsell existing customers"]
            }
        ))
    
    recommendations.sort(key=lambda x: _priority_to_int(x.priority))
    
    top_recommendations = [
        {
            "type": r.type.value,
            "title": r.title,
            "description": r.description,
            "priority": r.priority.value,
            "impact": r.impact,
            "action_details": r.action_details
        }
        for r in recommendations[:5]
    ]
    
    return {
        "health_scores": health_scores,
        "overall_health": _calculate_overall_health(health_scores),
        "recommendations": top_recommendations,
        "total_recommendations": len(recommendations),
        "metrics_analyzed": {
            "runway_months": runway,
            "survival_probability": survival_prob,
            "burn_multiple": burn_multiple,
            "gross_margin": gross_margin,
            "churn_rate": churn_rate
        }
    }


def _get_p50(metric: Dict[str, Any] | float) -> float:
    """Extract P50 value from metric."""
    if isinstance(metric, dict):
        return metric.get("p50", 0)
    return metric


def _calculate_health_scores(
    runway: float,
    survival_prob: float,
    burn_multiple: float,
    gross_margin: float,
    churn_rate: float
) -> Dict[str, Dict[str, Any]]:
    """Calculate health scores for each metric."""
    scores = {}
    
    scores["runway"] = _score_metric(
        runway,
        HEALTH_THRESHOLDS["runway_months"],
        higher_is_better=True
    )
    
    scores["survival_probability"] = _score_metric(
        survival_prob,
        HEALTH_THRESHOLDS["survival_probability"],
        higher_is_better=True
    )
    
    scores["burn_multiple"] = _score_metric(
        burn_multiple,
        HEALTH_THRESHOLDS["burn_multiple"],
        higher_is_better=False
    )
    
    scores["gross_margin"] = _score_metric(
        gross_margin,
        HEALTH_THRESHOLDS["gross_margin"],
        higher_is_better=True
    )
    
    scores["churn_rate"] = _score_metric(
        churn_rate,
        HEALTH_THRESHOLDS["churn_rate"],
        higher_is_better=False
    )
    
    return scores


def _score_metric(
    value: float,
    thresholds: Dict[str, float],
    higher_is_better: bool = True
) -> Dict[str, Any]:
    """Score a metric against thresholds."""
    if higher_is_better:
        if value >= thresholds["healthy"]:
            status = "healthy"
            score = 100
        elif value >= thresholds["warning"]:
            status = "warning"
            score = 60
        elif value >= thresholds["critical"]:
            status = "critical"
            score = 30
        else:
            status = "critical"
            score = 10
    else:
        if value <= thresholds["healthy"]:
            status = "healthy"
            score = 100
        elif value <= thresholds["warning"]:
            status = "warning"
            score = 60
        elif value <= thresholds["critical"]:
            status = "critical"
            score = 30
        else:
            status = "critical"
            score = 10
    
    return {
        "value": value,
        "status": status,
        "score": score,
        "threshold_healthy": thresholds["healthy"],
        "threshold_warning": thresholds["warning"],
        "threshold_critical": thresholds["critical"]
    }


def _calculate_overall_health(health_scores: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate overall health grade."""
    scores = [s["score"] for s in health_scores.values()]
    avg_score = sum(scores) / len(scores) if scores else 0
    
    critical_count = sum(1 for s in health_scores.values() if s["status"] == "critical")
    warning_count = sum(1 for s in health_scores.values() if s["status"] == "warning")
    
    if critical_count >= 2:
        grade = "D"
    elif critical_count == 1:
        grade = "C"
    elif warning_count >= 2:
        grade = "B-"
    elif warning_count == 1:
        grade = "B"
    elif avg_score >= 90:
        grade = "A"
    else:
        grade = "B+"
    
    return {
        "score": round(avg_score, 1),
        "grade": grade,
        "critical_areas": critical_count,
        "warning_areas": warning_count
    }


def _generate_runway_critical_recommendations(
    runway: float,
    burn_rate: float,
    revenue: float,
    cash: float
) -> List[Recommendation]:
    """Generate recommendations for critical runway situation."""
    recs = []
    
    recs.append(Recommendation(
        type=RecommendationType.REDUCE_BURN,
        title="Emergency Cost Reduction",
        description=f"With only {runway:.1f} months runway, immediate cost cuts needed.",
        priority=Priority.CRITICAL,
        impact={
            "target_savings": f"${burn_rate * 0.25:,.0f}/month",
            "runway_extension": "2-3 months"
        },
        action_details={
            "immediate_actions": [
                "Freeze all non-essential hiring",
                "Renegotiate vendor contracts",
                "Pause discretionary spending"
            ],
            "timeline": "this week"
        }
    ))
    
    if revenue > 0:
        recs.append(Recommendation(
            type=RecommendationType.ADJUST_PRICING,
            title="Consider Price Increase",
            description="A 10-15% price increase could extend runway without volume loss.",
            priority=Priority.HIGH,
            impact={
                "revenue_increase": f"${revenue * 0.12:,.0f}/month",
                "runway_extension": "1-2 months"
            },
            action_details={
                "suggested_increase": "10-15%",
                "implementation": "grandfather existing customers for 60 days"
            }
        ))
    
    recs.append(Recommendation(
        type=RecommendationType.DELAY_HIRING,
        title="Delay All Hiring",
        description="Freeze hiring until runway exceeds 12 months.",
        priority=Priority.HIGH,
        impact={
            "savings_per_hire": "$120,000-180,000/year",
            "runway_extension": "1-3 months per hire avoided"
        },
        action_details={
            "affected_roles": "all open positions",
            "resume_threshold": "12+ months runway"
        }
    ))
    
    return recs


def _generate_runway_warning_recommendations(
    runway: float,
    burn_rate: float,
    revenue: float
) -> List[Recommendation]:
    """Generate recommendations for warning runway situation."""
    recs = []
    
    recs.append(Recommendation(
        type=RecommendationType.EXTEND_RUNWAY,
        title="Develop Runway Extension Plan",
        description=f"With {runway:.1f} months runway, build a plan to reach 12+ months.",
        priority=Priority.HIGH,
        impact={
            "target_runway": "12+ months",
            "planning_horizon": "next 90 days"
        },
        action_details={
            "options": [
                "Reduce burn by 15-20%",
                "Accelerate revenue 20-30%",
                "Raise bridge funding"
            ],
            "recommended_combo": "burn reduction + revenue focus"
        }
    ))
    
    if revenue > 0 and burn_rate > revenue * 1.5:
        recs.append(Recommendation(
            type=RecommendationType.REDUCE_BURN,
            title="Align Burn to Revenue",
            description="Reduce burn rate to achieve sustainable growth.",
            priority=Priority.MEDIUM,
            impact={
                "target_burn_multiple": "1.5x",
                "sustainable_burn": f"${revenue * 1.5:,.0f}/month"
            },
            action_details={
                "current_burn": burn_rate,
                "target_burn": revenue * 1.5,
                "reduction_needed": burn_rate - revenue * 1.5
            }
        ))
    
    return recs


def _priority_to_int(priority: Priority) -> int:
    """Convert priority to integer for sorting."""
    mapping = {
        Priority.CRITICAL: 0,
        Priority.HIGH: 1,
        Priority.MEDIUM: 2,
        Priority.LOW: 3
    }
    return mapping.get(priority, 4)
