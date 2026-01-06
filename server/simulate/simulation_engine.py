import numpy as np
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

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
    hiring_plan: List[Dict] = None
    fundraise_month: Optional[int] = None
    fundraise_amount: float = 0
    gross_margin_delta_pct: float = 0
    
    horizon_months: int = 24
    n_simulations: int = 1000
    growth_sigma: float = 3.0
    margin_sigma: float = 2.0

def run_monte_carlo(inputs: SimulationInputs, seed: Optional[int] = None) -> Dict[str, Any]:
    if seed is not None:
        np.random.seed(seed)
    
    n = inputs.n_simulations
    horizon = inputs.horizon_months
    
    adjusted_growth = inputs.baseline_growth_rate + inputs.growth_uplift_pct
    adjusted_margin = inputs.gross_margin + inputs.gross_margin_delta_pct
    
    burn_reduction_mult = 1 - (inputs.burn_reduction_pct / 100)
    adjusted_opex = inputs.opex * burn_reduction_mult
    adjusted_other = inputs.other_costs * burn_reduction_mult
    
    adjusted_revenue = inputs.baseline_revenue * (1 + inputs.pricing_change_pct / 100)
    
    revenue_paths = np.zeros((n, horizon))
    cash_paths = np.zeros((n, horizon))
    burn_paths = np.zeros((n, horizon))
    runway_months = np.zeros(n)
    
    for sim in range(n):
        revenue = adjusted_revenue
        cash = inputs.cash_balance
        payroll = inputs.payroll
        
        for month in range(horizon):
            growth_rate = np.random.normal(adjusted_growth, inputs.growth_sigma) / 100
            margin = np.clip(
                np.random.normal(adjusted_margin, inputs.margin_sigma),
                10, 95
            ) / 100
            
            revenue = revenue * (1 + growth_rate)
            
            if inputs.hiring_plan:
                for hire in inputs.hiring_plan:
                    if hire.get("start_month", 0) == month + 1:
                        payroll += hire.get("monthly_cost", 0)
            
            if inputs.fundraise_month and month + 1 == inputs.fundraise_month:
                cash += inputs.fundraise_amount
            
            gross_profit = revenue * margin
            total_costs = (inputs.opex * burn_reduction_mult) + payroll + (inputs.other_costs * burn_reduction_mult) + (revenue * (1 - margin))
            net_cashflow = gross_profit - adjusted_opex - payroll - adjusted_other
            
            cash = cash + net_cashflow
            burn = max(0, -net_cashflow) if net_cashflow < 0 else 0
            
            revenue_paths[sim, month] = revenue
            cash_paths[sim, month] = cash
            burn_paths[sim, month] = burn
            
            if cash <= 0 and runway_months[sim] == 0:
                runway_months[sim] = month + 1
        
        if runway_months[sim] == 0:
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
