import numpy as np
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

DEFAULT_SCENARIOS = {
    "baseline": {
        "name": "Baseline",
        "description": "Current trajectory with no changes",
        "pricing_change_pct": 0,
        "growth_uplift_pct": 0,
        "burn_reduction_pct": 0,
        "fundraise_amount": 0,
        "gross_margin_delta_pct": 0,
    },
    "conservative": {
        "name": "Conservative Cut",
        "description": "Cut costs aggressively, accept slower growth to extend runway",
        "pricing_change_pct": 0,
        "growth_uplift_pct": -5,
        "burn_reduction_pct": 20,
        "fundraise_amount": 0,
        "gross_margin_delta_pct": 2,
    },
    "moderate_growth": {
        "name": "Moderate Growth",
        "description": "Moderate revenue improvements through pricing and growth levers",
        "pricing_change_pct": 10,
        "growth_uplift_pct": 10,
        "burn_reduction_pct": 0,
        "fundraise_amount": 0,
        "gross_margin_delta_pct": 0,
    },
    "aggressive_growth": {
        "name": "Aggressive Growth",
        "description": "Invest heavily in growth at the cost of higher burn rate",
        "pricing_change_pct": 20,
        "growth_uplift_pct": 25,
        "burn_reduction_pct": -15,
        "fundraise_amount": 0,
        "gross_margin_delta_pct": -5,
    },
    "cost_cutting": {
        "name": "Cost Cutting",
        "description": "Aggressive expense reduction with slight price concessions",
        "pricing_change_pct": -5,
        "growth_uplift_pct": -5,
        "burn_reduction_pct": 30,
        "fundraise_amount": 0,
        "gross_margin_delta_pct": 5,
    },
}

@dataclass
class SimulationInputs:
    baseline_revenue: float
    baseline_growth_rate: float
    gross_margin: float
    opex: float
    payroll: float
    other_costs: float
    cash_balance: float
    
    pricing_change_pct: float = 0
    growth_uplift_pct: float = 0
    burn_reduction_pct: float = 0
    hiring_plan: Optional[List[Dict]] = None
    fundraise_month: Optional[int] = None
    fundraise_amount: float = 0
    gross_margin_delta_pct: float = 0
    
    horizon_months: int = 24
    n_simulations: int = 1000
    growth_sigma: float = 5.0
    margin_sigma: float = 3.5

def run_monte_carlo(inputs: SimulationInputs, seed: Optional[int] = None) -> Dict[str, Any]:
    rng = np.random.default_rng(seed)
    
    n = inputs.n_simulations
    horizon = inputs.horizon_months
    
    adjusted_growth = inputs.baseline_growth_rate + inputs.growth_uplift_pct
    adjusted_margin = inputs.gross_margin + inputs.gross_margin_delta_pct
    
    burn_reduction_mult = 1 - (inputs.burn_reduction_pct / 100)
    adjusted_opex = inputs.opex * burn_reduction_mult
    adjusted_payroll = inputs.payroll * burn_reduction_mult
    adjusted_other = inputs.other_costs * burn_reduction_mult
    
    adjusted_revenue = inputs.baseline_revenue * (1 + inputs.pricing_change_pct / 100)
    
    revenue_paths = np.zeros((n, horizon))
    cash_paths = np.zeros((n, horizon))
    burn_paths = np.zeros((n, horizon))
    runway_months = np.zeros(n)
    
    for sim in range(n):
        revenue = adjusted_revenue
        cash = inputs.cash_balance
        payroll = adjusted_payroll
        
        for month in range(horizon):
            growth_rate = rng.normal(adjusted_growth, inputs.growth_sigma) / 100
            growth_rate = np.clip(growth_rate, -0.5, 0.5)
            margin = np.clip(
                rng.normal(adjusted_margin, inputs.margin_sigma),
                10, 95
            ) / 100
            
            revenue = revenue * (1 + growth_rate)
            revenue = min(revenue, inputs.baseline_revenue * 1000)
            
            if inputs.hiring_plan:
                for hire in inputs.hiring_plan:
                    if hire.get("start_month", 0) == month + 1:
                        payroll += hire.get("monthly_cost", 0)
            
            if inputs.fundraise_month and month + 1 == inputs.fundraise_month:
                cash += inputs.fundraise_amount
            
            gross_profit = revenue * margin
            net_cashflow = gross_profit - adjusted_opex - payroll - adjusted_other
            
            cash = cash + net_cashflow
            burn = max(0, -net_cashflow) if net_cashflow < 0 else 0
            
            revenue_paths[sim, month] = revenue
            cash_paths[sim, month] = cash
            burn_paths[sim, month] = burn
            
            if cash <= 0 and runway_months[sim] == 0:
                runway_months[sim] = month + 1
        
        if runway_months[sim] == 0:
            ending_cash = cash_paths[sim, -1]
            last_burns = burn_paths[sim, -3:]
            avg_burn = np.mean(last_burns) if np.any(last_burns > 0) else 0
            if avg_burn > 0:
                extra_months = ending_cash / avg_burn
                runway_months[sim] = horizon + min(extra_months, 36)
            else:
                last_net = 0
                for m_idx in range(max(0, horizon - 3), horizon):
                    rev_m = revenue_paths[sim, m_idx]
                    cash_diff = cash_paths[sim, m_idx] - (cash_paths[sim, m_idx - 1] if m_idx > 0 else inputs.cash_balance)
                    last_net = cash_diff
                if last_net > 0:
                    runway_months[sim] = horizon + 36
                else:
                    runway_months[sim] = horizon + 12
    
    survival_6m = np.sum(runway_months > 6) / n
    survival_12m = np.sum(runway_months > 12) / n
    survival_18m = np.sum(runway_months > 18) / n
    survival_24m = np.sum(runway_months > 24) / n
    
    runway_p10 = np.percentile(runway_months, 10)
    runway_p50 = np.percentile(runway_months, 50)
    runway_p90 = np.percentile(runway_months, 90)
    
    revenue_p10 = np.percentile(revenue_paths, 10, axis=0).tolist()
    revenue_p50 = np.percentile(revenue_paths, 50, axis=0).tolist()
    revenue_p90 = np.percentile(revenue_paths, 90, axis=0).tolist()
    
    cash_p10 = np.percentile(cash_paths, 10, axis=0).tolist()
    cash_p50 = np.percentile(cash_paths, 50, axis=0).tolist()
    cash_p90 = np.percentile(cash_paths, 90, axis=0).tolist()
    
    burn_p10 = np.percentile(burn_paths, 10, axis=0).tolist()
    burn_p50 = np.percentile(burn_paths, 50, axis=0).tolist()
    burn_p90 = np.percentile(burn_paths, 90, axis=0).tolist()
    
    survival_curve = []
    for m in range(1, horizon + 1):
        survival_curve.append({
            "month": m,
            "survival_rate": float(np.sum(runway_months > m) / n)
        })
    
    return {
        "runway": {
            "p10": round(runway_p10, 1),
            "p50": round(runway_p50, 1),
            "p90": round(runway_p90, 1),
            "distribution": runway_months.tolist()[:100]
        },
        "survival": {
            "6m": round(survival_6m * 100, 1),
            "12m": round(survival_12m * 100, 1),
            "18m": round(survival_18m * 100, 1),
            "24m": round(survival_24m * 100, 1),
            "curve": survival_curve
        },
        "bands": {
            "revenue": {
                "p10": revenue_p10,
                "p50": revenue_p50,
                "p90": revenue_p90
            },
            "cash": {
                "p10": cash_p10,
                "p50": cash_p50,
                "p90": cash_p90
            },
            "burn": {
                "p10": burn_p10,
                "p50": burn_p50,
                "p90": burn_p90
            }
        },
        "summary": {
            "revenue_18m_median": round(revenue_p50[17] if len(revenue_p50) > 17 else revenue_p50[-1], 0),
            "final_cash_p50": round(cash_p50[-1], 0),
            "avg_burn_p50": round(np.mean(burn_p50), 0)
        },
        "n_simulations": n,
        "horizon_months": horizon
    }


def run_multi_scenario_simulation(
    base_inputs: SimulationInputs,
    scenarios: Optional[Dict[str, Dict]] = None,
    seed: Optional[int] = None
) -> Dict[str, Any]:
    """
    Run Monte Carlo simulation for multiple scenarios and return month-indexed results.
    
    Args:
        base_inputs: Base financial metrics from truth scan
        scenarios: Dictionary of scenario definitions. Uses DEFAULT_SCENARIOS if None.
        seed: Random seed for reproducibility
    
    Returns:
        Dictionary with scenario results containing month-indexed P10/P50/P90 metrics
    """
    if scenarios is None:
        scenarios = DEFAULT_SCENARIOS
    
    results = {}
    
    for idx, (scenario_key, scenario_params) in enumerate(scenarios.items()):
        scenario_inputs = SimulationInputs(
            baseline_revenue=base_inputs.baseline_revenue,
            baseline_growth_rate=base_inputs.baseline_growth_rate,
            gross_margin=base_inputs.gross_margin + scenario_params.get("gross_margin_delta_pct", 0),
            opex=base_inputs.opex,
            payroll=base_inputs.payroll,
            other_costs=base_inputs.other_costs,
            cash_balance=base_inputs.cash_balance,
            pricing_change_pct=scenario_params.get("pricing_change_pct", 0),
            growth_uplift_pct=scenario_params.get("growth_uplift_pct", 0),
            burn_reduction_pct=scenario_params.get("burn_reduction_pct", 0),
            fundraise_month=scenario_params.get("fundraise_month"),
            fundraise_amount=scenario_params.get("fundraise_amount", 0),
            n_simulations=base_inputs.n_simulations,
            horizon_months=base_inputs.horizon_months
        )
        
        scenario_seed = (seed + idx + 1) if seed is not None else None
        sim_result = run_monte_carlo(scenario_inputs, scenario_seed)
        
        month_data = []
        horizon = base_inputs.horizon_months
        for m in range(horizon):
            month_data.append({
                "month": m + 1,
                "revenue_p10": round(sim_result["bands"]["revenue"]["p10"][m], 0),
                "revenue_p50": round(sim_result["bands"]["revenue"]["p50"][m], 0),
                "revenue_p90": round(sim_result["bands"]["revenue"]["p90"][m], 0),
                "cash_p10": round(sim_result["bands"]["cash"]["p10"][m], 0),
                "cash_p50": round(sim_result["bands"]["cash"]["p50"][m], 0),
                "cash_p90": round(sim_result["bands"]["cash"]["p90"][m], 0),
                "burn_p10": round(sim_result["bands"]["burn"]["p10"][m], 0),
                "burn_p50": round(sim_result["bands"]["burn"]["p50"][m], 0),
                "burn_p90": round(sim_result["bands"]["burn"]["p90"][m], 0),
                "survival_rate": sim_result["survival"]["curve"][m]["survival_rate"] if m < len(sim_result["survival"]["curve"]) else 0
            })
        
        results[scenario_key] = {
            "name": scenario_params.get("name", scenario_key),
            "description": scenario_params.get("description", ""),
            "params": {
                "pricing_change_pct": scenario_params.get("pricing_change_pct", 0),
                "growth_uplift_pct": scenario_params.get("growth_uplift_pct", 0),
                "burn_reduction_pct": scenario_params.get("burn_reduction_pct", 0),
                "fundraise_amount": scenario_params.get("fundraise_amount", 0),
                "gross_margin_delta_pct": scenario_params.get("gross_margin_delta_pct", 0),
            },
            "summary": {
                "runway_p10": sim_result["runway"]["p10"],
                "runway_p50": sim_result["runway"]["p50"],
                "runway_p90": sim_result["runway"]["p90"],
                "survival_12m": sim_result["survival"]["12m"],
                "survival_18m": sim_result["survival"]["18m"],
                "survival_24m": sim_result["survival"]["24m"],
                "final_cash_p50": sim_result["summary"]["final_cash_p50"],
            },
            "month_data": month_data,
            "bands": sim_result["bands"],
            "survival_curve": sim_result["survival"]["curve"]
        }
    
    scenario_summaries = [
        {
            "key": key,
            "name": results[key]["name"],
            "runway_p50": results[key]["summary"]["runway_p50"],
            "survival_18m": results[key]["summary"]["survival_18m"],
            "final_cash_p50": results[key]["summary"]["final_cash_p50"],
        }
        for key in results
    ]
    scenario_summaries.sort(key=lambda x: x["runway_p50"], reverse=True)
    
    return {
        "scenarios": results,
        "comparison": scenario_summaries,
        "n_simulations": base_inputs.n_simulations,
        "horizon_months": base_inputs.horizon_months
    }
