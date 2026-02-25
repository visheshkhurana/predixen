from server.lib.lazy_imports import np
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


@dataclass
class DistributionParams:
    type: str
    value: Optional[float] = None
    mean: Optional[float] = None
    std_dev: Optional[float] = None
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    mode: Optional[float] = None
    values: Optional[List[Dict[str, float]]] = None


def sample_distribution(params: DistributionParams, size: int = 1, rng: Optional[np.random.Generator] = None) -> np.ndarray:
    if rng is None:
        rng = np.random.default_rng()
    if params.type == "fixed":
        return np.full(size, params.value or 0)
    elif params.type == "normal":
        return rng.normal(params.mean or 0, params.std_dev or 1, size)
    elif params.type == "lognormal":
        mu = np.log((params.mean or 1) ** 2 / np.sqrt((params.std_dev or 0.1) ** 2 + (params.mean or 1) ** 2))
        sigma = np.sqrt(np.log(1 + (params.std_dev or 0.1) ** 2 / (params.mean or 1) ** 2))
        return rng.lognormal(mu, sigma, size)
    elif params.type == "uniform":
        return rng.uniform(params.min_val or 0, params.max_val or 1, size)
    elif params.type == "triangular":
        min_v = params.min_val if params.min_val is not None else 0
        max_v = params.max_val if params.max_val is not None else 1
        mode_v = params.mode if params.mode is not None else (min_v + max_v) / 2
        return rng.triangular(min_v, mode_v, max_v, size)
    elif params.type == "discrete":
        if params.values:
            vals = [v["value"] for v in params.values]
            probs = [v["probability"] for v in params.values]
            probs = np.array(probs) / sum(probs)
            return rng.choice(vals, size=size, p=probs)
        return np.zeros(size)
    else:
        return np.full(size, params.value or 0)


@dataclass
class ScenarioEvent:
    id: str
    type: str
    name: str
    month: int
    probability: float = 1.0
    duration: Optional[DistributionParams] = None
    impact: Dict[str, Optional[DistributionParams]] = field(default_factory=dict)
    description: str = ""
    conditions: List[Dict] = field(default_factory=list)


@dataclass
class SimulationConfig:
    iterations: int = 1000
    horizon_months: int = 24
    seed: Optional[int] = None
    confidence_intervals: List[int] = field(default_factory=lambda: [10, 25, 50, 75, 90])
    parallel_workers: int = 4


@dataclass
class EnhancedSimulationInputs:
    baseline_revenue: float
    baseline_growth_rate: float
    gross_margin: float
    opex: float
    payroll: float
    other_costs: float
    cash_balance: float
    churn_rate: float = 5.0
    cac: float = 0
    ltv: float = 0
    
    pricing_change_pct: float = 0
    growth_uplift_pct: float = 0
    burn_reduction_pct: float = 0
    fundraise_month: Optional[int] = None
    fundraise_amount: float = 0
    gross_margin_delta_pct: float = 0
    churn_change_pct: float = 0
    cac_change_pct: float = 0
    
    events: List[ScenarioEvent] = field(default_factory=list)
    
    growth_sigma: float = 3.0
    margin_sigma: float = 2.0
    churn_sigma: float = 1.0


def run_enhanced_monte_carlo(
    inputs: EnhancedSimulationInputs,
    config: SimulationConfig
) -> Dict[str, Any]:
    start_time = datetime.utcnow()
    
    rng = np.random.default_rng(config.seed)
    
    n = config.iterations
    horizon = config.horizon_months
    
    adjusted_growth = inputs.baseline_growth_rate + inputs.growth_uplift_pct
    adjusted_margin = inputs.gross_margin + inputs.gross_margin_delta_pct
    clamped_burn_reduction = max(0, min(100, inputs.burn_reduction_pct))
    burn_reduction_mult = 1 - (clamped_burn_reduction / 100)
    adjusted_revenue = inputs.baseline_revenue * (1 + inputs.pricing_change_pct / 100)
    adjusted_churn = inputs.churn_rate + inputs.churn_change_pct
    adjusted_cac = inputs.cac * (1 + inputs.cac_change_pct / 100) if inputs.cac > 0 else 0
    fundraise_amount = max(0, inputs.fundraise_amount)
    fundraise_month = inputs.fundraise_month
    if fundraise_month is not None and fundraise_month < 1:
        fundraise_month = 1
    
    revenue_paths = np.zeros((n, horizon))
    cash_paths = np.zeros((n, horizon))
    burn_paths = np.zeros((n, horizon))
    runway_months = np.zeros(n)
    breakeven_months = np.full(n, horizon + 1, dtype=float)
    
    event_occurrences = {event.id: 0 for event in inputs.events}
    event_runway_impacts = {event.id: [] for event in inputs.events}
    event_cash_impacts = {event.id: [] for event in inputs.events}
    
    for sim in range(n):
        revenue = adjusted_revenue
        cash = inputs.cash_balance
        payroll = inputs.payroll
        current_growth = adjusted_growth
        current_margin = adjusted_margin
        current_churn = adjusted_churn
        found_breakeven = False
        
        active_events = {}
        base_runway_estimate = 0
        
        for month in range(horizon):
            growth_rate = rng.normal(current_growth, inputs.growth_sigma) / 100
            growth_rate = np.clip(growth_rate, -0.5, 0.5)
            margin = np.clip(
                rng.normal(current_margin, inputs.margin_sigma),
                10, 95
            ) / 100
            churn = np.clip(
                rng.normal(current_churn, inputs.churn_sigma),
                0, 50
            ) / 100
            
            for event in inputs.events:
                if month + 1 == event.month:
                    if rng.random() < event.probability:
                        event_occurrences[event.id] += 1
                        pre_event_cash = cash
                        
                        duration = 1
                        if event.duration:
                            duration = int(sample_distribution(event.duration, 1, rng=rng)[0])
                        
                        active_events[event.id] = {
                            "remaining": duration,
                            "event": event
                        }
                        
                        cash_dist = event.impact.get("cash")
                        if cash_dist is not None:
                            cash_impact = sample_distribution(cash_dist, 1, rng=rng)[0]
                            cash += cash_impact
                            event_cash_impacts[event.id].append(cash_impact)
                        
                        rev_dist = event.impact.get("revenue")
                        if rev_dist is not None:
                            rev_impact = sample_distribution(rev_dist, 1, rng=rng)[0]
                            revenue *= (1 + rev_impact / 100)
                        
                        growth_dist = event.impact.get("growth")
                        if growth_dist is not None:
                            growth_impact = sample_distribution(growth_dist, 1, rng=rng)[0]
                            current_growth += growth_impact
                        
                        margin_dist = event.impact.get("margin")
                        if margin_dist is not None:
                            margin_impact = sample_distribution(margin_dist, 1, rng=rng)[0]
                            current_margin += margin_impact
                        
                        churn_dist = event.impact.get("churn")
                        if churn_dist is not None:
                            churn_impact = sample_distribution(churn_dist, 1, rng=rng)[0]
                            current_churn += churn_impact
                        
                        headcount_dist = event.impact.get("headcount")
                        if headcount_dist is not None:
                            headcount_impact = sample_distribution(headcount_dist, 1, rng=rng)[0]
                            payroll *= (1 + headcount_impact / 100)
                        
                        costs_dist = event.impact.get("costs")
                        if costs_dist is not None:
                            cost_impact = sample_distribution(costs_dist, 1, rng=rng)[0]
                            payroll *= (1 + cost_impact / 100)
            
            to_remove = []
            for eid, edata in active_events.items():
                edata["remaining"] -= 1
                if edata["remaining"] <= 0:
                    to_remove.append(eid)
            for eid in to_remove:
                del active_events[eid]
            
            revenue = revenue * (1 + growth_rate)
            revenue = revenue * (1 - churn)
            revenue = min(revenue, inputs.baseline_revenue * 1000)
            
            if fundraise_month and month + 1 == fundraise_month:
                cash += fundraise_amount
            
            gross_profit = revenue * margin
            total_opex = inputs.opex * burn_reduction_mult
            total_other = inputs.other_costs * burn_reduction_mult
            net_cashflow = gross_profit - total_opex - payroll - total_other
            
            cash = cash + net_cashflow
            burn = max(0, -net_cashflow) if net_cashflow < 0 else 0
            
            revenue_paths[sim, month] = revenue
            cash_paths[sim, month] = cash
            burn_paths[sim, month] = burn
            
            if not found_breakeven and net_cashflow >= 0:
                breakeven_months[sim] = month + 1
                found_breakeven = True
            
            if cash <= 0 and runway_months[sim] == 0:
                runway_months[sim] = month + 1
        
        if runway_months[sim] == 0:
            max_cap = 48
            final_cash = cash_paths[sim, horizon - 1]
            final_revenue = revenue_paths[sim, horizon - 1]
            
            net_cf = final_revenue * (adjusted_margin / 100) - inputs.opex * burn_reduction_mult - payroll - inputs.other_costs * burn_reduction_mult
            if net_cf >= 0:
                runway_months[sim] = max_cap
            else:
                extra = final_cash / abs(net_cf) if abs(net_cf) > 0 else max_cap
                runway_months[sim] = min(horizon + extra, max_cap)
        
        for event in inputs.events:
            if event.id in event_occurrences and event_occurrences[event.id] > 0:
                event_runway_impacts[event.id].append(runway_months[sim])
    
    survival_6m = np.sum(runway_months > 6) / n
    survival_12m = np.sum(runway_months > 12) / n
    survival_18m = np.sum(runway_months > 18) / n
    survival_24m = np.sum(runway_months > 24) / n
    
    def compute_percentiles(data: np.ndarray, axis: Optional[int] = None) -> Dict[str, Any]:
        percentiles = {}
        for p in config.confidence_intervals:
            percentiles[f"p{p}"] = np.percentile(data, p, axis=axis)
        percentiles["mean"] = np.mean(data, axis=axis)
        percentiles["std_dev"] = np.std(data, axis=axis)
        percentiles["min"] = np.min(data, axis=axis)
        percentiles["max"] = np.max(data, axis=axis)
        return percentiles
    
    runway_stats = compute_percentiles(runway_months)
    breakeven_stats = compute_percentiles(breakeven_months)
    
    revenue_percentiles = []
    cash_percentiles = []
    burn_percentiles = []
    
    for m in range(horizon):
        revenue_percentiles.append({
            "month": m + 1,
            **{f"p{p}": float(np.percentile(revenue_paths[:, m], p)) for p in config.confidence_intervals}
        })
        cash_percentiles.append({
            "month": m + 1,
            **{f"p{p}": float(np.percentile(cash_paths[:, m], p)) for p in config.confidence_intervals}
        })
        burn_percentiles.append({
            "month": m + 1,
            **{f"p{p}": float(np.percentile(burn_paths[:, m], p)) for p in config.confidence_intervals}
        })
    
    survival_curve = []
    for m in range(1, horizon + 1):
        survival_curve.append({
            "month": m,
            "survival_rate": float(np.sum(runway_months > m) / n)
        })
    
    event_impacts = []
    for event in inputs.events:
        if event_occurrences[event.id] > 0:
            avg_runway = np.mean(event_runway_impacts[event.id]) if event_runway_impacts[event.id] else 0
            avg_cash = np.mean(event_cash_impacts[event.id]) if event_cash_impacts[event.id] else 0
            event_impacts.append({
                "eventId": event.id,
                "eventName": event.name,
                "occurrenceRate": event_occurrences[event.id] / n,
                "avgRunwayImpact": round(avg_runway, 1),
                "avgCashImpact": round(avg_cash, 0)
            })
    
    end_time = datetime.utcnow()
    execution_time = (end_time - start_time).total_seconds() * 1000
    
    return {
        "jobId": str(uuid.uuid4()),
        "scenarioId": 0,
        "config": {
            "iterations": config.iterations,
            "horizonMonths": config.horizon_months,
            "seed": config.seed,
            "confidenceIntervals": config.confidence_intervals
        },
        "runway": {
            "p10": round(float(runway_stats["p10"]), 1),
            "p25": round(float(runway_stats.get("p25", runway_stats["p10"])), 1),
            "p50": round(float(runway_stats["p50"]), 1),
            "p75": round(float(runway_stats.get("p75", runway_stats["p90"])), 1),
            "p90": round(float(runway_stats["p90"]), 1),
            "mean": round(float(runway_stats["mean"]), 1),
            "stdDev": round(float(runway_stats["std_dev"]), 1),
            "min": round(float(runway_stats["min"]), 1),
            "max": round(float(runway_stats["max"]), 1)
        },
        "survivalProbability": {
            "6m": round(survival_6m * 100, 1),
            "12m": round(survival_12m * 100, 1),
            "18m": round(survival_18m * 100, 1),
            "24m": round(survival_24m * 100, 1)
        },
        "survivalCurve": survival_curve,
        "breakEvenMonth": {
            "p10": round(float(breakeven_stats["p10"]), 1),
            "p50": round(float(breakeven_stats["p50"]), 1),
            "p90": round(float(breakeven_stats["p90"]), 1),
            "mean": round(float(breakeven_stats["mean"]), 1),
        },
        "metrics": {
            "revenue": revenue_percentiles,
            "cash": cash_percentiles,
            "burn": burn_percentiles
        },
        "distributions": {
            "runway": runway_months.tolist()[:500],
            "finalCash": cash_paths[:, -1].tolist()[:500],
            "finalRevenue": revenue_paths[:, -1].tolist()[:500]
        },
        "eventImpacts": event_impacts,
        "executionTime": round(execution_time, 0),
        "timestamp": datetime.utcnow().isoformat()
    }


def run_sensitivity_analysis(
    inputs: EnhancedSimulationInputs,
    config: SimulationConfig,
    parameters: List[Dict[str, Any]],
    target_metric: str = "runway"
) -> Dict[str, Any]:
    start_time = datetime.utcnow()
    
    reduced_config = SimulationConfig(
        iterations=min(config.iterations, 500),
        horizon_months=config.horizon_months,
        seed=config.seed
    )
    
    baseline_result = run_enhanced_monte_carlo(inputs, reduced_config)
    baseline_value = baseline_result["runway"]["p50"]
    
    sensitivity_results = []
    
    for param in parameters:
        param_name = param["name"]
        label = param.get("label", param_name)
        baseline_param_value = param["baselineValue"]
        min_value = param["minValue"]
        max_value = param["maxValue"]
        
        low_inputs = EnhancedSimulationInputs(
            baseline_revenue=inputs.baseline_revenue,
            baseline_growth_rate=inputs.baseline_growth_rate,
            gross_margin=inputs.gross_margin,
            opex=inputs.opex,
            payroll=inputs.payroll,
            other_costs=inputs.other_costs,
            cash_balance=inputs.cash_balance,
            churn_rate=inputs.churn_rate,
            pricing_change_pct=inputs.pricing_change_pct,
            growth_uplift_pct=inputs.growth_uplift_pct,
            burn_reduction_pct=inputs.burn_reduction_pct,
            fundraise_month=inputs.fundraise_month,
            fundraise_amount=inputs.fundraise_amount,
            gross_margin_delta_pct=inputs.gross_margin_delta_pct,
            events=inputs.events
        )
        
        high_inputs = EnhancedSimulationInputs(
            baseline_revenue=inputs.baseline_revenue,
            baseline_growth_rate=inputs.baseline_growth_rate,
            gross_margin=inputs.gross_margin,
            opex=inputs.opex,
            payroll=inputs.payroll,
            other_costs=inputs.other_costs,
            cash_balance=inputs.cash_balance,
            churn_rate=inputs.churn_rate,
            pricing_change_pct=inputs.pricing_change_pct,
            growth_uplift_pct=inputs.growth_uplift_pct,
            burn_reduction_pct=inputs.burn_reduction_pct,
            fundraise_month=inputs.fundraise_month,
            fundraise_amount=inputs.fundraise_amount,
            gross_margin_delta_pct=inputs.gross_margin_delta_pct,
            events=inputs.events
        )
        
        if param_name == "baseline_growth_rate":
            low_inputs.baseline_growth_rate = min_value
            high_inputs.baseline_growth_rate = max_value
        elif param_name == "gross_margin":
            low_inputs.gross_margin = min_value
            high_inputs.gross_margin = max_value
        elif param_name == "churn_rate":
            low_inputs.churn_rate = min_value
            high_inputs.churn_rate = max_value
        elif param_name == "opex":
            low_inputs.opex = min_value
            high_inputs.opex = max_value
        elif param_name == "payroll":
            low_inputs.payroll = min_value
            high_inputs.payroll = max_value
        elif param_name == "pricing_change_pct":
            low_inputs.pricing_change_pct = min_value
            high_inputs.pricing_change_pct = max_value
        elif param_name == "burn_reduction_pct":
            low_inputs.burn_reduction_pct = min_value
            high_inputs.burn_reduction_pct = max_value
        elif param_name == "fundraise_amount":
            low_inputs.fundraise_amount = min_value
            high_inputs.fundraise_amount = max_value
        elif param_name == "cash_balance":
            low_inputs.cash_balance = min_value
            high_inputs.cash_balance = max_value
        
        low_result = run_enhanced_monte_carlo(low_inputs, reduced_config)
        high_result = run_enhanced_monte_carlo(high_inputs, reduced_config)
        
        runway_at_low = low_result["runway"]["p50"]
        runway_at_high = high_result["runway"]["p50"]
        
        impact = abs(runway_at_high - runway_at_low)
        
        if runway_at_high > runway_at_low:
            direction = "positive"
        elif runway_at_high < runway_at_low:
            direction = "negative"
        else:
            direction = "mixed"
        
        sensitivity_results.append({
            "parameter": param_name,
            "label": label,
            "baselineValue": baseline_param_value,
            "lowValue": min_value,
            "highValue": max_value,
            "runwayAtLow": runway_at_low,
            "runwayAtHigh": runway_at_high,
            "runwayAtBaseline": baseline_value,
            "impact": round(impact, 1),
            "direction": direction
        })
    
    sensitivity_results.sort(key=lambda x: x["impact"], reverse=True)
    
    end_time = datetime.utcnow()
    execution_time = (end_time - start_time).total_seconds() * 1000
    
    return {
        "scenarioId": 0,
        "targetMetric": target_metric,
        "baselineValue": baseline_value,
        "parameters": sensitivity_results,
        "executionTime": round(execution_time, 0),
        "timestamp": datetime.utcnow().isoformat()
    }


def compute_scenario_diff(
    version_a: Dict[str, Any],
    version_b: Dict[str, Any]
) -> Dict[str, Any]:
    changes = []
    input_changes = 0
    event_changes = 0
    tag_changes = 0
    
    inputs_a = version_a.get("inputs_json", {})
    inputs_b = version_b.get("inputs_json", {})
    
    all_keys = set(inputs_a.keys()) | set(inputs_b.keys())
    for key in all_keys:
        val_a = inputs_a.get(key)
        val_b = inputs_b.get(key)
        if val_a != val_b:
            change_type = "modified"
            if val_a is None:
                change_type = "added"
            elif val_b is None:
                change_type = "removed"
            changes.append({
                "field": "inputs",
                "path": f"inputs.{key}",
                "oldValue": val_a,
                "newValue": val_b,
                "changeType": change_type
            })
            input_changes += 1
    
    events_a = version_a.get("events_json", [])
    events_b = version_b.get("events_json", [])
    
    events_a_ids = {e.get("id"): e for e in events_a}
    events_b_ids = {e.get("id"): e for e in events_b}
    
    for eid in set(events_a_ids.keys()) | set(events_b_ids.keys()):
        if eid not in events_a_ids:
            changes.append({
                "field": "events",
                "path": f"events.{eid}",
                "oldValue": None,
                "newValue": events_b_ids[eid],
                "changeType": "added"
            })
            event_changes += 1
        elif eid not in events_b_ids:
            changes.append({
                "field": "events",
                "path": f"events.{eid}",
                "oldValue": events_a_ids[eid],
                "newValue": None,
                "changeType": "removed"
            })
            event_changes += 1
        elif events_a_ids[eid] != events_b_ids[eid]:
            changes.append({
                "field": "events",
                "path": f"events.{eid}",
                "oldValue": events_a_ids[eid],
                "newValue": events_b_ids[eid],
                "changeType": "modified"
            })
            event_changes += 1
    
    tags_a = set(version_a.get("tags", []))
    tags_b = set(version_b.get("tags", []))
    
    for tag in tags_a - tags_b:
        changes.append({
            "field": "tags",
            "path": f"tags.{tag}",
            "oldValue": tag,
            "newValue": None,
            "changeType": "removed"
        })
        tag_changes += 1
    
    for tag in tags_b - tags_a:
        changes.append({
            "field": "tags",
            "path": f"tags.{tag}",
            "oldValue": None,
            "newValue": tag,
            "changeType": "added"
        })
        tag_changes += 1
    
    return {
        "versionA": version_a.get("version", 0),
        "versionB": version_b.get("version", 0),
        "changes": changes,
        "inputChanges": input_changes,
        "eventChanges": event_changes,
        "tagChanges": tag_changes
    }
