"""
Optimization Module for Goal-Seeking Simulations.

Provides grid search, random search, and gradient-free optimization
to find assumption set configurations that achieve target metrics.
"""

import logging
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from copy import deepcopy
import uuid
from datetime import datetime

from server.simulate.assumptions import (
    AssumptionSet,
    Distribution,
    DistributionType,
    RevenueGrowthAssumption,
    ChurnAssumption,
    BurnReductionAssumption,
)
from server.simulate.transformer import transform_assumptions_to_inputs, get_distribution_mean
from server.simulate.enhanced_monte_carlo import run_enhanced_monte_carlo, SimulationConfig

logger = logging.getLogger(__name__)


@dataclass
class Constraint:
    """Constraint on a metric during optimization."""
    metric: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    weight: float = 1.0


@dataclass
class OptimizationConfig:
    target_metric: str = "runway"
    target_value: float = 18.0
    direction: str = "maximize"
    optimize_fields: List[str] = field(default_factory=lambda: ["burn_reduction", "revenue_growth"])
    max_iterations: int = 100
    simulation_iterations: int = 200
    search_method: str = "random"
    tolerance: float = 0.5
    seed: Optional[int] = None
    constraints: List[Constraint] = field(default_factory=list)
    multi_objective: bool = False
    objective_weights: Dict[str, float] = field(default_factory=dict)


@dataclass
class OptimizationResult:
    job_id: str
    status: str
    best_assumptions: Optional[Dict[str, Any]] = None
    best_metric_value: Optional[float] = None
    iterations_run: int = 0
    convergence_history: List[Dict[str, float]] = field(default_factory=list)
    search_space: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    elapsed_time_ms: int = 0


PARAMETER_BOUNDS = {
    "revenue_growth": (0.0, 0.20),
    "churn_rate": (0.01, 0.15),
    "burn_reduction": (0.0, 0.25),
    "price_change": (-0.10, 0.20),
}


def get_nested_field_value(assumptions: AssumptionSet, field_name: str) -> float:
    """Extract the mean value from a nested assumption field."""
    if field_name == "revenue_growth":
        return get_distribution_mean(assumptions.revenue_growth.monthly_growth_rate)
    elif field_name == "churn_rate":
        return get_distribution_mean(assumptions.churn_rate.monthly_churn_rate)
    elif field_name == "burn_reduction":
        return get_distribution_mean(assumptions.burn_reduction.monthly_reduction_rate)
    elif field_name == "price_change":
        return get_distribution_mean(assumptions.price_change.annual_price_increase)
    return 0.0


def set_nested_field_value(assumptions: AssumptionSet, field_name: str, value: float) -> AssumptionSet:
    """Set a nested field to a fixed distribution value."""
    data = assumptions.model_dump()
    
    fixed_dist = {"type": "fixed", "value": value}
    
    if field_name == "revenue_growth":
        data["revenue_growth"]["monthly_growth_rate"] = fixed_dist
    elif field_name == "churn_rate":
        data["churn_rate"]["monthly_churn_rate"] = fixed_dist
    elif field_name == "burn_reduction":
        data["burn_reduction"]["monthly_reduction_rate"] = fixed_dist
    elif field_name == "price_change":
        data["price_change"]["annual_price_increase"] = fixed_dist
    
    return AssumptionSet(**data)


def evaluate_assumptions(
    assumptions: AssumptionSet,
    baseline_metrics: Dict[str, float],
    target_metric: str,
    sim_iterations: int = 200,
    seed: Optional[int] = None
) -> float:
    """Run a quick simulation and return the target metric value."""
    inputs = transform_assumptions_to_inputs(assumptions, baseline_metrics)
    
    config = SimulationConfig(
        iterations=sim_iterations,
        horizon_months=24,
        seed=seed,
        confidence_intervals=[10, 50, 90]
    )
    
    results = run_enhanced_monte_carlo(inputs, config)
    summary = results.get("summary", {})
    
    metric_map = {
        "runway": "mean_runway_months",
        "survival": "survival_rate",
        "cash": "mean_final_cash",
        "revenue": "mean_final_revenue",
        "growth": "mean_final_growth"
    }
    
    metric_key = metric_map.get(target_metric, target_metric)
    return float(summary.get(metric_key, 0.0) or 0.0)


SUPPORTED_METRICS = {"runway", "survival", "cash", "revenue", "growth", "dilution", "gross_margin", "burn_multiple"}


def evaluate_with_constraints(
    assumptions: AssumptionSet,
    baseline_metrics: Dict[str, float],
    config: OptimizationConfig,
    sim_iterations: int = 200,
    seed: Optional[int] = None
) -> Tuple[float, Dict[str, float], bool]:
    """
    Evaluate assumptions and check constraints.
    
    Returns:
        - Primary metric value
        - Dictionary of all metric values
        - Whether all constraints are satisfied
    """
    inputs = transform_assumptions_to_inputs(assumptions, baseline_metrics)
    
    sim_config = SimulationConfig(
        iterations=sim_iterations,
        horizon_months=24,
        seed=seed,
        confidence_intervals=[10, 50, 90]
    )
    
    results = run_enhanced_monte_carlo(inputs, sim_config)
    summary = results.get("summary", {})
    
    metric_map = {
        "runway": "mean_runway_months",
        "survival": "survival_rate",
        "cash": "mean_final_cash",
        "revenue": "mean_final_revenue",
        "growth": "mean_final_growth",
        "dilution": "dilution",
        "gross_margin": "gross_margin",
        "burn_multiple": "burn_multiple"
    }
    
    all_metrics = {}
    available_metrics = set()
    
    for name, key in metric_map.items():
        value = summary.get(key)
        if value is not None:
            all_metrics[name] = float(value)
            available_metrics.add(name)
        else:
            all_metrics[name] = None
    
    if all_metrics.get("dilution") is None:
        fundraise = assumptions.fundraise
        if fundraise and fundraise.raise_probability > 0:
            raise_amount = fundraise.raise_amount or 500000
            valuation = raise_amount / 0.20
            all_metrics["dilution"] = raise_amount / valuation
        else:
            all_metrics["dilution"] = 0.0
        available_metrics.add("dilution")
    
    if all_metrics.get("gross_margin") is None:
        all_metrics["gross_margin"] = baseline_metrics.get("gross_margin", 0.70)
        available_metrics.add("gross_margin")
    
    for name in ["runway", "survival", "cash", "revenue", "growth"]:
        if all_metrics.get(name) is None:
            if name == "runway":
                all_metrics[name] = 12.0
            elif name == "survival":
                all_metrics[name] = 0.5
            else:
                all_metrics[name] = 0.0
            available_metrics.add(name)
    
    primary_value = all_metrics.get(config.target_metric, 0.0) or 0.0
    
    constraints_satisfied = True
    for constraint in config.constraints:
        if constraint.metric not in SUPPORTED_METRICS:
            constraints_satisfied = False
            break
        
        metric_value = all_metrics.get(constraint.metric)
        if metric_value is None:
            constraints_satisfied = False
            break
        
        if constraint.min_value is not None and metric_value < constraint.min_value:
            constraints_satisfied = False
            break
        
        if constraint.max_value is not None and metric_value > constraint.max_value:
            constraints_satisfied = False
            break
    
    final_metrics = {k: v if v is not None else 0.0 for k, v in all_metrics.items()}
    return primary_value, final_metrics, constraints_satisfied


def compute_multi_objective_score(
    metrics: Dict[str, float],
    objective_weights: Dict[str, float],
    directions: Dict[str, str] = None
) -> float:
    """
    Compute a weighted multi-objective score.
    
    Args:
        metrics: Dictionary of metric values
        objective_weights: Weight for each metric (higher = more important)
        directions: Whether to maximize or minimize each metric
    
    Returns:
        Combined weighted score
    """
    if directions is None:
        directions = {
            "runway": "maximize",
            "survival": "maximize",
            "cash": "maximize",
            "revenue": "maximize",
            "growth": "maximize",
            "dilution": "minimize",
            "burn_multiple": "minimize"
        }
    
    normalizers = {
        "runway": 24.0,
        "survival": 1.0,
        "cash": 1000000.0,
        "revenue": 500000.0,
        "growth": 0.50,
        "dilution": 0.50,
        "burn_multiple": 5.0,
        "gross_margin": 1.0
    }
    
    total_weight = sum(objective_weights.values())
    if total_weight == 0:
        return 0.0
    
    score = 0.0
    for metric, weight in objective_weights.items():
        value = metrics.get(metric, 0.0)
        normalizer = normalizers.get(metric, 1.0)
        normalized_value = value / normalizer if normalizer else 0.0
        
        direction = directions.get(metric, "maximize")
        if direction == "minimize":
            normalized_value = 1.0 - min(normalized_value, 1.0)
        else:
            normalized_value = min(normalized_value, 1.0)
        
        score += (weight / total_weight) * normalized_value
    
    return score


def constrained_random_search(
    assumptions: AssumptionSet,
    baseline_metrics: Dict[str, float],
    config: OptimizationConfig
) -> OptimizationResult:
    """
    Random search with constraint handling.
    
    Uses penalty method: infeasible solutions get penalized score.
    When multi_objective is enabled, always maximizes the composite score.
    """
    start_time = datetime.utcnow()
    job_id = str(uuid.uuid4())
    
    if config.seed:
        np.random.seed(config.seed)
    
    effective_direction = "maximize" if config.multi_objective else config.direction
    
    best_value = None
    best_assumptions = None
    best_metrics = None
    best_is_feasible = False
    convergence_history = []
    feasible_count = 0
    
    for i in range(config.max_iterations):
        test_assumptions = deepcopy(assumptions)
        sample_values = {}
        
        for fld in config.optimize_fields:
            bounds = PARAMETER_BOUNDS.get(fld, (0.0, 0.20))
            value = np.random.uniform(bounds[0], bounds[1])
            sample_values[fld] = value
            test_assumptions = set_nested_field_value(test_assumptions, fld, value)
        
        primary_value, all_metrics, is_feasible = evaluate_with_constraints(
            test_assumptions,
            baseline_metrics,
            config,
            config.simulation_iterations,
            config.seed
        )
        
        if config.multi_objective and config.objective_weights:
            valid_weights = {k: v for k, v in config.objective_weights.items() if k in SUPPORTED_METRICS}
            objective_value = compute_multi_objective_score(
                all_metrics,
                valid_weights
            )
        else:
            objective_value = primary_value
        
        penalty = 1.0
        if not is_feasible:
            penalty = 0.5
            for constraint in config.constraints:
                if constraint.weight > 1.0:
                    penalty *= (0.5 ** (constraint.weight - 1))
            objective_value = objective_value * penalty
        else:
            feasible_count += 1
        
        convergence_history.append({
            "iteration": i + 1,
            "objective_value": objective_value,
            "primary_metric": primary_value,
            "is_feasible": is_feasible,
            **sample_values,
            **{f"metric_{k}": v for k, v in all_metrics.items()}
        })
        
        is_better = False
        if best_value is None:
            is_better = True
        elif is_feasible and not best_is_feasible:
            is_better = True
        elif is_feasible == best_is_feasible:
            if effective_direction == "maximize" and objective_value > best_value:
                is_better = True
            elif effective_direction == "minimize" and objective_value < best_value:
                is_better = True
        
        if is_better:
            best_value = objective_value
            best_assumptions = test_assumptions.model_dump()
            best_metrics = {**all_metrics, "is_feasible": is_feasible}
            best_is_feasible = is_feasible
    
    elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000
    
    result = OptimizationResult(
        job_id=job_id,
        status="completed",
        best_assumptions=best_assumptions,
        best_metric_value=best_value,
        iterations_run=len(convergence_history),
        convergence_history=convergence_history,
        search_space={f: PARAMETER_BOUNDS.get(f, (0.0, 0.20)) for f in config.optimize_fields},
        elapsed_time_ms=int(elapsed)
    )
    
    result.constraints_summary = {
        "total_iterations": len(convergence_history),
        "feasible_solutions": feasible_count,
        "feasibility_rate": feasible_count / len(convergence_history) if convergence_history else 0,
        "best_is_feasible": best_metrics.get("is_feasible", False) if best_metrics else False
    }
    
    return result


def grid_search(
    assumptions: AssumptionSet,
    baseline_metrics: Dict[str, float],
    config: OptimizationConfig
) -> OptimizationResult:
    """
    Grid search over the specified optimization fields.
    
    Divides each field's range into steps and evaluates all combinations.
    """
    start_time = datetime.utcnow()
    job_id = str(uuid.uuid4())
    
    grid_points = 5
    search_grids = {}
    
    for fld in config.optimize_fields:
        bounds = PARAMETER_BOUNDS.get(fld, (0.0, 0.20))
        search_grids[fld] = np.linspace(bounds[0], bounds[1], grid_points)
    
    from itertools import product
    all_combinations = list(product(*[
        [(fld, val) for val in search_grids[fld]]
        for fld in config.optimize_fields
    ]))
    
    if len(all_combinations) > config.max_iterations:
        np.random.seed(config.seed)
        indices = np.random.choice(len(all_combinations), config.max_iterations, replace=False)
        all_combinations = [all_combinations[i] for i in indices]
    
    best_value = None
    best_assumptions = None
    convergence_history = []
    
    for i, combo in enumerate(all_combinations):
        test_assumptions = deepcopy(assumptions)
        
        for fld, value in combo:
            test_assumptions = set_nested_field_value(test_assumptions, fld, value)
        
        metric_value = evaluate_assumptions(
            test_assumptions,
            baseline_metrics,
            config.target_metric,
            config.simulation_iterations,
            config.seed
        )
        
        convergence_history.append({
            "iteration": i + 1,
            "metric_value": metric_value,
            **{fld: value for fld, value in combo}
        })
        
        is_better = False
        if best_value is None:
            is_better = True
        elif config.direction == "maximize" and metric_value > best_value:
            is_better = True
        elif config.direction == "minimize" and metric_value < best_value:
            is_better = True
        
        if is_better:
            best_value = metric_value
            best_assumptions = test_assumptions.model_dump()
        
        if config.direction == "maximize" and best_value >= config.target_value:
            break
        if config.direction == "minimize" and best_value <= config.target_value:
            break
    
    elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000
    
    return OptimizationResult(
        job_id=job_id,
        status="completed",
        best_assumptions=best_assumptions,
        best_metric_value=best_value,
        iterations_run=len(convergence_history),
        convergence_history=convergence_history,
        search_space={f: PARAMETER_BOUNDS.get(f, (0.0, 0.20)) for f in config.optimize_fields},
        elapsed_time_ms=int(elapsed)
    )


def random_search(
    assumptions: AssumptionSet,
    baseline_metrics: Dict[str, float],
    config: OptimizationConfig
) -> OptimizationResult:
    """
    Random search over the specified optimization fields.
    
    Samples random points within each field's bounds.
    """
    start_time = datetime.utcnow()
    job_id = str(uuid.uuid4())
    
    if config.seed:
        np.random.seed(config.seed)
    
    best_value = None
    best_assumptions = None
    convergence_history = []
    
    for i in range(config.max_iterations):
        test_assumptions = deepcopy(assumptions)
        sample_values = {}
        
        for fld in config.optimize_fields:
            bounds = PARAMETER_BOUNDS.get(fld, (0.0, 0.20))
            value = np.random.uniform(bounds[0], bounds[1])
            sample_values[fld] = value
            test_assumptions = set_nested_field_value(test_assumptions, fld, value)
        
        metric_value = evaluate_assumptions(
            test_assumptions,
            baseline_metrics,
            config.target_metric,
            config.simulation_iterations,
            config.seed
        )
        
        convergence_history.append({
            "iteration": i + 1,
            "metric_value": metric_value,
            **sample_values
        })
        
        is_better = False
        if best_value is None:
            is_better = True
        elif config.direction == "maximize" and metric_value > best_value:
            is_better = True
        elif config.direction == "minimize" and metric_value < best_value:
            is_better = True
        
        if is_better:
            best_value = metric_value
            best_assumptions = test_assumptions.model_dump()
        
        if config.direction == "maximize" and best_value >= config.target_value:
            break
        if config.direction == "minimize" and best_value <= config.target_value:
            break
    
    elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000
    
    return OptimizationResult(
        job_id=job_id,
        status="completed",
        best_assumptions=best_assumptions,
        best_metric_value=best_value,
        iterations_run=len(convergence_history),
        convergence_history=convergence_history,
        search_space={f: PARAMETER_BOUNDS.get(f, (0.0, 0.20)) for f in config.optimize_fields},
        elapsed_time_ms=int(elapsed)
    )


def bayesian_search(
    assumptions: AssumptionSet,
    baseline_metrics: Dict[str, float],
    config: OptimizationConfig
) -> OptimizationResult:
    """
    Simple Bayesian-style search with Latin Hypercube sampling.
    
    More intelligent than random search, samples more efficiently.
    """
    start_time = datetime.utcnow()
    job_id = str(uuid.uuid4())
    
    if config.seed:
        np.random.seed(config.seed)
    
    n_initial = min(10, config.max_iterations // 2)
    n_dims = len(config.optimize_fields)
    
    samples = np.zeros((n_initial, n_dims))
    for d in range(n_dims):
        perm = np.random.permutation(n_initial)
        for i in range(n_initial):
            samples[i, d] = (perm[i] + np.random.random()) / n_initial
    
    best_value = None
    best_assumptions = None
    convergence_history = []
    evaluated_points = []
    evaluated_values = []
    
    for i in range(n_initial):
        test_assumptions = deepcopy(assumptions)
        sample_values = {}
        
        for j, fld in enumerate(config.optimize_fields):
            bounds = PARAMETER_BOUNDS.get(fld, (0.0, 0.20))
            value = bounds[0] + samples[i, j] * (bounds[1] - bounds[0])
            sample_values[fld] = value
            test_assumptions = set_nested_field_value(test_assumptions, fld, value)
        
        metric_value = evaluate_assumptions(
            test_assumptions,
            baseline_metrics,
            config.target_metric,
            config.simulation_iterations,
            config.seed
        )
        
        evaluated_points.append(sample_values)
        evaluated_values.append(metric_value)
        
        convergence_history.append({
            "iteration": i + 1,
            "metric_value": metric_value,
            **sample_values
        })
        
        is_better = False
        if best_value is None:
            is_better = True
        elif config.direction == "maximize" and metric_value > best_value:
            is_better = True
        elif config.direction == "minimize" and metric_value < best_value:
            is_better = True
        
        if is_better:
            best_value = metric_value
            best_assumptions = test_assumptions.model_dump()
    
    for i in range(n_initial, config.max_iterations):
        if config.direction == "maximize":
            top_indices = np.argsort(evaluated_values)[-3:]
        else:
            top_indices = np.argsort(evaluated_values)[:3]
        
        center = {}
        for fld in config.optimize_fields:
            vals = [evaluated_points[idx][fld] for idx in top_indices]
            center[fld] = np.mean(vals)
        
        test_assumptions = deepcopy(assumptions)
        sample_values = {}
        
        for fld in config.optimize_fields:
            bounds = PARAMETER_BOUNDS.get(fld, (0.0, 0.20))
            range_size = (bounds[1] - bounds[0]) * 0.3
            value = center[fld] + np.random.uniform(-range_size, range_size)
            value = np.clip(value, bounds[0], bounds[1])
            sample_values[fld] = value
            test_assumptions = set_nested_field_value(test_assumptions, fld, value)
        
        metric_value = evaluate_assumptions(
            test_assumptions,
            baseline_metrics,
            config.target_metric,
            config.simulation_iterations,
            config.seed
        )
        
        evaluated_points.append(sample_values)
        evaluated_values.append(metric_value)
        
        convergence_history.append({
            "iteration": i + 1,
            "metric_value": metric_value,
            **sample_values
        })
        
        is_better = False
        if config.direction == "maximize" and metric_value > best_value:
            is_better = True
        elif config.direction == "minimize" and metric_value < best_value:
            is_better = True
        
        if is_better:
            best_value = metric_value
            best_assumptions = test_assumptions.model_dump()
        
        if config.direction == "maximize" and best_value >= config.target_value:
            break
        if config.direction == "minimize" and best_value <= config.target_value:
            break
    
    elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000
    
    return OptimizationResult(
        job_id=job_id,
        status="completed",
        best_assumptions=best_assumptions,
        best_metric_value=best_value,
        iterations_run=len(convergence_history),
        convergence_history=convergence_history,
        search_space={f: PARAMETER_BOUNDS.get(f, (0.0, 0.20)) for f in config.optimize_fields},
        elapsed_time_ms=int(elapsed)
    )


def run_optimization(
    assumptions: AssumptionSet,
    baseline_metrics: Dict[str, float],
    config: OptimizationConfig
) -> OptimizationResult:
    """
    Run optimization using the specified search method.
    """
    if config.search_method == "grid":
        return grid_search(assumptions, baseline_metrics, config)
    elif config.search_method == "bayesian":
        return bayesian_search(assumptions, baseline_metrics, config)
    else:
        return random_search(assumptions, baseline_metrics, config)
