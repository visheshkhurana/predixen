"""Natural language explanation generator for simulation results."""
from typing import Dict, Any, List, Optional


def generate_runway_explanation(
    runway_p50: float,
    survival_12m: float,
    survival_18m: float,
    scenario_name: str = "current scenario"
) -> str:
    """Generate a plain-English explanation of runway projections."""
    
    if runway_p50 >= 24:
        runway_status = "excellent"
        runway_detail = f"Your projected runway of {runway_p50:.0f} months puts you in a strong position with over 2 years of operational buffer."
    elif runway_p50 >= 18:
        runway_status = "healthy"
        runway_detail = f"With {runway_p50:.0f} months of runway, you have solid time to execute on your growth plans before needing additional capital."
    elif runway_p50 >= 12:
        runway_status = "adequate"
        runway_detail = f"Your {runway_p50:.0f} month runway provides reasonable time, but consider fundraising or cost optimization within the next 6 months."
    elif runway_p50 >= 6:
        runway_status = "concerning"
        runway_detail = f"At {runway_p50:.0f} months, you should prioritize either securing funding or implementing significant cost reductions immediately."
    else:
        runway_status = "critical"
        runway_detail = f"With only {runway_p50:.0f} months of runway remaining, urgent action is required to extend your runway or secure emergency funding."
    
    survival_context = ""
    if survival_18m >= 80:
        survival_context = f"There's a {survival_18m:.0f}% probability of remaining cash-positive at 18 months, indicating strong financial resilience."
    elif survival_18m >= 60:
        survival_context = f"Your {survival_18m:.0f}% survival probability at 18 months suggests moderate risk. Consider scenario planning for downside cases."
    elif survival_18m >= 40:
        survival_context = f"A {survival_18m:.0f}% survival probability at 18 months indicates significant uncertainty. Focus on improving key metrics."
    else:
        survival_context = f"The {survival_18m:.0f}% survival probability at 18 months represents material risk that should be addressed through strategic changes."
    
    return f"**Runway Assessment: {runway_status.title()}**\n\n{runway_detail}\n\n{survival_context}"


def generate_scenario_comparison(
    scenarios: List[Dict[str, Any]],
    best_scenario: str
) -> str:
    """Generate explanation comparing multiple scenarios."""
    
    if not scenarios:
        return "No scenarios available for comparison."
    
    lines = [f"**Scenario Comparison Summary**\n"]
    lines.append(f"Based on analysis across {len(scenarios)} scenarios, **{best_scenario}** emerges as the recommended path forward.\n")
    
    for s in scenarios[:3]:
        name = s.get("name", "Unknown")
        runway = s.get("runway_p50", 0)
        survival = s.get("survival_18m", 0)
        lines.append(f"- **{name}**: {runway:.0f} months runway, {survival:.0f}% survival probability")
    
    return "\n".join(lines)


def generate_driver_impact_explanation(
    sensitivity_results: List[Dict[str, Any]],
    target_runway: int = 18
) -> str:
    """Explain which drivers have the biggest impact on achieving target runway."""
    
    if not sensitivity_results:
        return "Sensitivity analysis not yet performed."
    
    lines = [f"**What Must Be True to Achieve {target_runway} Month Runway**\n"]
    
    for i, result in enumerate(sensitivity_results[:5], 1):
        driver = result.get("driver", "Unknown")
        impact = result.get("impact_magnitude", 0)
        direction = result.get("impact_direction", "positive")
        threshold = result.get("threshold_value")
        
        driver_label = driver.replace("_", " ").title()
        
        if threshold:
            lines.append(f"{i}. **{driver_label}** needs to reach {threshold:.1f}% (impact: {impact:.0f} months)")
        else:
            change = "increase" if direction == "positive" else "decrease"
            lines.append(f"{i}. A {change} in **{driver_label}** would add approximately {abs(impact):.1f} months of runway")
    
    return "\n".join(lines)


def generate_decision_recommendation(
    ranked_scenarios: List[Dict[str, Any]],
    company_stage: str = "growth"
) -> str:
    """Generate strategic recommendation based on decision ranking."""
    
    if not ranked_scenarios:
        return "Run enhanced simulation to generate recommendations."
    
    top = ranked_scenarios[0] if ranked_scenarios else None
    if not top:
        return "No scenarios available."
    
    name = top.get("scenario_name", "Top scenario")
    score = top.get("composite_score", 0)
    survival = top.get("survival_18m_prob", 0)
    
    lines = [f"**Strategic Recommendation**\n"]
    lines.append(f"We recommend **{name}** with a composite score of {score:.1f}/100.\n")
    
    if survival >= 70:
        lines.append("This path offers strong survival probability while balancing growth potential and manageable complexity.")
    elif survival >= 50:
        lines.append("This option balances acceptable risk with upside potential. Consider hedging with contingency plans.")
    else:
        lines.append("While this is the best available option, the moderate survival probability suggests exploring additional risk mitigation strategies.")
    
    if len(ranked_scenarios) > 1:
        runner_up = ranked_scenarios[1]
        runner_name = runner_up.get("scenario_name", "Alternative")
        lines.append(f"\n**Alternative consideration**: {runner_name} offers a different risk-reward profile worth evaluating.")
    
    return "\n".join(lines)


def generate_cohort_insights(
    gross_retention: float,
    net_retention: float,
    industry_avg_gross: float = 85,
    industry_avg_net: float = 100
) -> str:
    """Generate insights about cohort retention metrics."""
    
    lines = ["**Customer Retention Analysis**\n"]
    
    gross_vs_avg = gross_retention - industry_avg_gross
    net_vs_avg = net_retention - industry_avg_net
    
    if gross_retention >= 90:
        lines.append(f"Your gross retention of {gross_retention:.0f}% is excellent, indicating strong product-market fit and customer satisfaction.")
    elif gross_retention >= 80:
        lines.append(f"Gross retention at {gross_retention:.0f}% is healthy but there's room for improvement through enhanced customer success initiatives.")
    else:
        lines.append(f"At {gross_retention:.0f}%, gross retention is below industry benchmarks. Consider investing in customer success and churn prevention.")
    
    if net_retention >= 110:
        lines.append(f"Net retention of {net_retention:.0f}% shows strong expansion revenue, with existing customers growing their spend over time.")
    elif net_retention >= 100:
        lines.append(f"Net retention at {net_retention:.0f}% means expansion revenue is offsetting churn, maintaining stable cohort value.")
    else:
        lines.append(f"Net retention below 100% ({net_retention:.0f}%) indicates cohorts are shrinking over time. Focus on upsell and cross-sell opportunities.")
    
    return "\n".join(lines)


def generate_full_explanation(
    simulation_result: Dict[str, Any],
    scenario_name: str = "Current Scenario",
    include_recommendations: bool = True
) -> Dict[str, str]:
    """Generate comprehensive explanations for all aspects of simulation results."""
    
    runway = simulation_result.get("runway", {})
    survival = simulation_result.get("survival", {})
    
    explanations = {
        "summary": generate_runway_explanation(
            runway_p50=runway.get("p50", 12),
            survival_12m=survival.get("12m", 50) * 100 if survival.get("12m", 50) <= 1 else survival.get("12m", 50),
            survival_18m=survival.get("18m", 40) * 100 if survival.get("18m", 40) <= 1 else survival.get("18m", 40),
            scenario_name=scenario_name
        ),
    }
    
    if "sensitivity" in simulation_result and simulation_result["sensitivity"]:
        explanations["drivers"] = generate_driver_impact_explanation(
            simulation_result["sensitivity"]
        )
    
    if "decision_ranking" in simulation_result and simulation_result["decision_ranking"]:
        explanations["recommendation"] = generate_decision_recommendation(
            simulation_result["decision_ranking"]
        )
    
    return explanations
