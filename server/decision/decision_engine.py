import json
import os
from typing import Dict, Any, List
from server.simulate.simulation_engine import SimulationInputs, run_monte_carlo

def load_action_library() -> List[Dict]:
    lib_path = os.path.join(os.path.dirname(__file__), "action_library.json")
    with open(lib_path, "r") as f:
        return json.load(f)

def select_candidates(truth_metrics: Dict, confidence: int) -> List[Dict]:
    actions = load_action_library()
    candidates = []
    
    runway_p50 = truth_metrics.get("runway_p50", 12)
    concentration = truth_metrics.get("concentration_top5") or 0
    retention = truth_metrics.get("logo_retention_12m") or 80
    gross_margin = truth_metrics.get("gross_margin", 70)
    
    for action in actions:
        applicability = action.get("applicability", [])
        bucket = action.get("bucket", "")
        
        if confidence < 60:
            if bucket == "growth" and "all" not in applicability:
                continue
            if "growth_marketing_push" == action["id"]:
                continue
        
        if runway_p50 >= 12 and "low_runway" in applicability and "all" not in applicability:
            continue
        
        if runway_p50 >= 6 and "critical_runway" in applicability:
            continue
        
        if concentration > 50 and action["id"] == "growth_marketing_push":
            continue
        
        if retention < 70 and action["id"] == "growth_marketing_push":
            continue
        
        if "low_margin" in applicability and gross_margin >= 60:
            continue
        
        if "strong_retention" in applicability and retention < 85:
            if "all" not in applicability:
                continue
        
        if "high_confidence" in applicability and confidence < 75:
            if "all" not in applicability:
                continue
        
        candidates.append(action)
    
    return candidates[:12]

def score_action(
    action: Dict,
    simulation_outputs: Dict,
    baseline_outputs: Dict,
    truth_metrics: Dict,
    confidence: int
) -> Dict[str, Any]:
    survival_18m = simulation_outputs.get("survival", {}).get("18m", 0) / 100
    survival_score = survival_18m
    
    runway_p50 = simulation_outputs.get("runway", {}).get("p50", 0)
    runway_score = min(1.0, runway_p50 / 24)
    
    baseline_rev_18m = baseline_outputs.get("summary", {}).get("revenue_18m_median", 1)
    sim_rev_18m = simulation_outputs.get("summary", {}).get("revenue_18m_median", 1)
    growth_score = min(1.0, max(0, (sim_rev_18m / max(1, baseline_rev_18m)) - 0.5))
    
    baseline_burn = baseline_outputs.get("summary", {}).get("avg_burn_p50", 1)
    sim_burn = simulation_outputs.get("summary", {}).get("avg_burn_p50", 1)
    if baseline_burn > 0 and sim_burn > 0:
        burn_improvement = (baseline_burn - sim_burn) / baseline_burn
        efficiency_score = min(1.0, max(0, burn_improvement + 0.5))
    else:
        efficiency_score = 0.5
    
    risk_penalty = 0
    bucket = action.get("bucket", "")
    scenario_deltas = action.get("scenario_deltas", {})
    
    if confidence < 60 and bucket == "growth":
        risk_penalty += 0.15
    
    if runway_p50 < 9 and len(scenario_deltas.get("hiring_plan", [])) > 0:
        risk_penalty += 0.10
    
    burn_change = scenario_deltas.get("burn_reduction_pct", 0)
    if burn_change > 25:
        risk_penalty += 0.05
    if burn_change < -30:
        risk_penalty += 0.12
    if burn_change < -50:
        risk_penalty += 0.20
    if burn_change < -75:
        risk_penalty += 0.15
    
    pricing_change = scenario_deltas.get("pricing_change_pct", 0)
    if pricing_change >= 8:
        if not (confidence > 75 and truth_metrics.get("logo_retention_12m", 0) > 85):
            risk_penalty += 0.05
    
    total_score = (
        0.45 * survival_score +
        0.20 * runway_score +
        0.15 * efficiency_score +
        0.20 * growth_score -
        risk_penalty
    )
    
    baseline_survival_18m = baseline_outputs.get("survival", {}).get("18m", 0)
    baseline_runway = baseline_outputs.get("runway", {}).get("p50", 0)
    
    delta_survival = simulation_outputs.get("survival", {}).get("18m", 0) - baseline_survival_18m
    delta_runway = runway_p50 - baseline_runway
    
    if abs(delta_survival) < 0.5 and baseline_survival_18m >= 95:
        baseline_cash = baseline_outputs.get("summary", {}).get("final_cash_p50", 1)
        sim_cash = simulation_outputs.get("summary", {}).get("final_cash_p50", 1)
        if abs(baseline_cash) > 0:
            cash_pct_change = ((sim_cash - baseline_cash) / max(abs(baseline_cash), 1)) * 100
            delta_survival = round(cash_pct_change * 0.15, 2)
    
    if abs(delta_runway) < 0.5:
        baseline_cash_end = baseline_outputs.get("summary", {}).get("final_cash_p50", 0)
        sim_cash_end = simulation_outputs.get("summary", {}).get("final_cash_p50", 0)
        cash_diff = sim_cash_end - baseline_cash_end
        avg_burn = max(baseline_outputs.get("summary", {}).get("avg_burn_p50", 0), 10000)
        delta_runway = round(min(max(cash_diff / avg_burn / 3, -12), 12), 1)
    
    return {
        "action": action,
        "total_score": round(total_score, 3),
        "survival_score": round(survival_score, 3),
        "runway_score": round(runway_score, 3),
        "efficiency_score": round(efficiency_score, 3),
        "growth_score": round(growth_score, 3),
        "risk_penalty": round(risk_penalty, 3),
        "delta_survival_18m": round(delta_survival, 2),
        "delta_runway_p50": round(delta_runway, 2),
        "simulation_summary": simulation_outputs.get("summary", {})
    }

def generate_recommendations(
    truth_metrics: Dict,
    confidence: int,
    baseline_sim_inputs: SimulationInputs
) -> List[Dict[str, Any]]:
    candidates = select_candidates(truth_metrics, confidence)
    
    baseline_outputs = run_monte_carlo(baseline_sim_inputs, seed=42)
    
    scored_actions = []
    
    for action in candidates:
        deltas = action.get("scenario_deltas", {})
        
        action_inputs = SimulationInputs(
            baseline_revenue=baseline_sim_inputs.baseline_revenue,
            baseline_growth_rate=baseline_sim_inputs.baseline_growth_rate,
            gross_margin=baseline_sim_inputs.gross_margin + deltas.get("gross_margin_delta_pct", 0),
            opex=baseline_sim_inputs.opex,
            payroll=baseline_sim_inputs.payroll,
            other_costs=baseline_sim_inputs.other_costs,
            cash_balance=baseline_sim_inputs.cash_balance,
            pricing_change_pct=deltas.get("pricing_change_pct", 0),
            growth_uplift_pct=deltas.get("growth_uplift_pct", 0),
            burn_reduction_pct=deltas.get("burn_reduction_pct", 0),
            hiring_plan=deltas.get("hiring_plan", []),
            fundraise_month=deltas.get("fundraise_month"),
            fundraise_amount=deltas.get("fundraise_amount", 0),
            n_simulations=500
        )
        
        sim_outputs = run_monte_carlo(action_inputs, seed=42)
        
        scored = score_action(
            action=action,
            simulation_outputs=sim_outputs,
            baseline_outputs=baseline_outputs,
            truth_metrics=truth_metrics,
            confidence=confidence
        )
        scored_actions.append(scored)
    
    scored_actions.sort(key=lambda x: x["total_score"], reverse=True)
    
    top_3 = scored_actions[:3]
    
    recommendations = []
    for i, scored in enumerate(top_3):
        action = scored["action"]
        recommendations.append({
            "rank": i + 1,
            "id": action["id"],
            "title": action["title"],
            "rationale": action["description"],
            "expected_impact": {
                "delta_survival_18m": scored["delta_survival_18m"],
                "delta_runway_p50": scored["delta_runway_p50"],
            },
            "risks": generate_risk_text(action, scored),
            "key_assumption": generate_assumption_text(action),
            "next_validation": action.get("scenario_deltas", {}),
            "scores": {
                "total": scored["total_score"],
                "survival": scored["survival_score"],
                "runway": scored["runway_score"],
                "efficiency": scored["efficiency_score"],
                "growth": scored["growth_score"],
                "risk_penalty": scored["risk_penalty"]
            }
        })
    
    return recommendations

def generate_risk_text(action: Dict, scored: Dict) -> List[str]:
    risks = []
    deltas = action.get("scenario_deltas", {})
    
    if deltas.get("burn_reduction_pct", 0) >= 20:
        risks.append("Aggressive cost cuts may impact team morale and velocity")
    
    burn_pct = deltas.get("burn_reduction_pct", 0)
    if burn_pct < -50:
        risks.append(f"Burn increases by {abs(burn_pct)}% — consider phased hiring to validate growth assumptions before full commitment")
    elif burn_pct < -30:
        risks.append(f"Significant burn increase ({abs(burn_pct)}%) will accelerate cash depletion and shorten runway")
    
    if deltas.get("pricing_change_pct", 0) >= 10:
        risks.append("Price increase may lead to customer churn")
    
    if deltas.get("fundraise_amount", 0) > 0:
        risks.append("Fundraising outcome is uncertain in current market")
    
    if deltas.get("growth_uplift_pct", 0) >= 5:
        risks.append("Growth acceleration requires execution excellence")
    
    if not risks:
        risks.append("Moderate execution risk with this approach")
    
    return risks

def generate_assumption_text(action: Dict) -> str:
    deltas = action.get("scenario_deltas", {})
    
    if deltas.get("fundraise_amount", 0) > 0:
        return "Assumes successful fundraise at target terms"
    
    if deltas.get("burn_reduction_pct", 0) >= 20:
        return "Assumes team can maintain productivity with reduced resources"
    
    if deltas.get("pricing_change_pct", 0) >= 5:
        return "Assumes customer retention remains stable despite price change"
    
    return "Assumes current market conditions persist"
