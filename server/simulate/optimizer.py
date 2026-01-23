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
