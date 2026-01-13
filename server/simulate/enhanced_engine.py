import numpy as np
from scipy.linalg import cholesky
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import asdict
from .models import (
    EnrichedSimulationInputs, 
    MonthlyState, 
    ScenarioEvent,
    ScenarioDefinition,
    DecisionScore,
    SensitivityResult,
    WhatMustBeTrueReport,
    EnrichedSimulationResult,
    RegimeConfig,
    DriverConfig,
    DEFAULT_REGIMES,
    DRIVER_CORRELATION_MATRIX,
    Regime
)


class EnhancedSimulationEngine:
    
    def __init__(self, inputs: EnrichedSimulationInputs, seed: Optional[int] = None):
        self.inputs = inputs
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.regimes = DEFAULT_REGIMES
        self.driver_names = ["growth_rate", "churn_rate", "gross_margin", "cac", "dso", "conversion_rate"]
        self.correlation_matrix = self._build_correlation_matrix()
        self.cholesky_L = self._compute_cholesky()
        
    def _build_correlation_matrix(self) -> np.ndarray:
        n = len(self.driver_names)
        matrix = np.zeros((n, n))
        for i, d1 in enumerate(self.driver_names):
            for j, d2 in enumerate(self.driver_names):
                matrix[i, j] = DRIVER_CORRELATION_MATRIX.get(d1, {}).get(d2, 0.0)
        return matrix
    
    def _compute_cholesky(self) -> np.ndarray:
        try:
            return cholesky(self.correlation_matrix, lower=True)
        except:
            return np.eye(len(self.driver_names))
    
    def _sample_correlated_drivers(self, regime: str, n_samples: int = 1) -> Dict[str, np.ndarray]:
        regime_config = self.regimes.get(regime, self.regimes["base"])
        
        independent_samples = self.rng.standard_normal((n_samples, len(self.driver_names)))
        correlated_samples = independent_samples @ self.cholesky_L.T
        
        drivers = {}
        for i, driver_name in enumerate(self.driver_names):
            adj = regime_config.driver_adjustments.get(driver_name, DriverConfig(mean=0, sigma=1.0))
            
            base_values = getattr(self.inputs, driver_name, 0) if hasattr(self.inputs, driver_name) else 0
            if driver_name == "growth_rate":
                base_values = self.inputs.baseline_growth_rate + self.inputs.growth_uplift_pct
            elif driver_name == "gross_margin":
                base_values = self.inputs.gross_margin + self.inputs.gross_margin_delta_pct
            
            sampled = base_values + adj.mean + correlated_samples[:, i] * adj.sigma
            
            if adj.min_val is not None:
                sampled = np.maximum(sampled, adj.min_val)
            if adj.max_val is not None:
                sampled = np.minimum(sampled, adj.max_val)
            
            drivers[driver_name] = sampled
        
        return drivers
    
    def _transition_regime(self, current_regime: str) -> str:
        if not self.inputs.enable_regime_transitions:
            return current_regime
        
        regime_config = self.regimes.get(current_regime, self.regimes["base"])
        probs = regime_config.transition_probs
        
        regimes_list = list(probs.keys())
        prob_values = [probs[r] for r in regimes_list]
        
        prob_values = np.array(prob_values) / sum(prob_values)
        
        return self.rng.choice(regimes_list, p=prob_values)
    
    def _apply_scenario_events(
        self, 
        state: MonthlyState, 
        events: List[ScenarioEvent],
        drivers: Dict[str, float]
    ) -> Tuple[MonthlyState, Dict[str, float], List[str]]:
        active_events = []
        modified_drivers = drivers.copy()
        
        for event in events:
            if event.start_month <= state.month:
                if event.end_month is None or event.end_month >= state.month:
                    active_events.append(event.event_type)
                    
                    if event.event_type == "pricing_change":
                        change = event.params.get("change_pct", 0) / 100
                        state.mrr = state.mrr * (1 + change)
                        state.arr = state.mrr * 12
                    
                    elif event.event_type == "cost_cut":
                        opex_cut = event.params.get("opex_reduction_pct", 0) / 100
                        payroll_cut = event.params.get("payroll_reduction_pct", 0) / 100
                        state.opex = state.opex * (1 - opex_cut)
                        state.payroll = state.payroll * (1 - payroll_cut)
                        if payroll_cut > 0 and state.headcount > 1:
                            state.headcount = max(1, int(state.headcount * (1 - payroll_cut * 0.8)))
                    
                    elif event.event_type == "hiring_freeze":
                        pass
                    
                    elif event.event_type == "hiring_plan":
                        if event.start_month == state.month:
                            new_hires = event.params.get("new_hires", 0)
                            avg_salary = event.params.get("avg_salary", self.inputs.avg_salary)
                            state.headcount += new_hires
                            state.payroll += new_hires * avg_salary
                    
                    elif event.event_type == "fundraise":
                        if event.start_month == state.month:
                            amount = event.params.get("amount", 0)
                            success_prob = event.params.get("success_probability")
                            if success_prob is None:
                                regime_config = self.regimes.get(state.regime, self.regimes["base"])
                                success_prob = regime_config.fundraising_success_prob
                            
                            if self.rng.random() < success_prob:
                                state.cash += amount
                    
                    elif event.event_type == "marketing_spend_change":
                        change = event.params.get("change_pct", 0) / 100
                        marketing_portion = state.opex * 0.3
                        state.opex = state.opex + (marketing_portion * change)
                        modified_drivers["cac"] = modified_drivers.get("cac", self.inputs.cac) * (1 - change * 0.3)
                    
                    elif event.event_type == "churn_initiative":
                        reduction = event.params.get("churn_reduction_pct", 0) / 100
                        modified_drivers["churn_rate"] = modified_drivers.get("churn_rate", self.inputs.churn_rate) * (1 - reduction)
                    
                    elif event.event_type == "expansion_revenue":
                        expansion = event.params.get("expansion_rate_pct", 0) / 100
                        state.mrr = state.mrr * (1 + expansion / 12)
                        state.arr = state.mrr * 12
        
        return state, modified_drivers, active_events
    
    def _step_month(
        self,
        prev_state: MonthlyState,
        drivers: Dict[str, float],
        events: List[ScenarioEvent]
    ) -> MonthlyState:
        month = prev_state.month + 1
        
        new_regime = self._transition_regime(prev_state.regime)
        
        growth_rate = drivers["growth_rate"] / 100
        churn_rate = drivers["churn_rate"] / 100 / 12
        gross_margin = drivers["gross_margin"] / 100
        cac = drivers["cac"]
        dso = drivers["dso"]
        conversion_rate = drivers["conversion_rate"] / 100
        
        churned_customers = int(prev_state.total_customers * churn_rate)
        churn_amount = churned_customers * (prev_state.mrr / max(1, prev_state.total_customers))
        
        pipeline_converted = prev_state.pipeline_value * conversion_rate
        new_customers = int(pipeline_converted / self.inputs.arpu) if self.inputs.arpu > 0 else 0
        new_mrr = new_customers * self.inputs.arpu
        cac_total = new_customers * cac
        
        new_pipeline = prev_state.pipeline_value * 0.9 + (prev_state.mrr * 0.3)
        
        mrr = prev_state.mrr * (1 + growth_rate / 12) - churn_amount + new_mrr
        mrr = max(0, mrr)
        arr = mrr * 12
        
        total_customers = prev_state.total_customers - churned_customers + new_customers
        total_customers = max(1, total_customers)
        
        revenue = mrr
        cogs = revenue * (1 - gross_margin)
        gross_profit = revenue * gross_margin
        
        burn_reduction = 1 - (self.inputs.burn_reduction_pct / 100)
        opex = prev_state.opex * burn_reduction
        payroll = prev_state.payroll
        other_costs = self.inputs.other_costs * burn_reduction
        
        ebitda = gross_profit - opex - payroll - other_costs - cac_total
        
        dso_months = dso / 30
        collections = prev_state.revenue * (1 - (1 / max(1, dso_months + 1)))
        
        debt_payment = 0
        debt_balance = prev_state.debt_balance
        if debt_balance > 0 and self.inputs.debt_term_months > 0:
            monthly_principal = debt_balance / max(1, self.inputs.debt_term_months - month + 1)
            monthly_interest = debt_balance * (self.inputs.debt_interest_rate / 100 / 12)
            debt_payment = monthly_principal + monthly_interest
            debt_balance = max(0, debt_balance - monthly_principal)
        
        net_cashflow = collections - opex - payroll - other_costs - cac_total - debt_payment
        cash = prev_state.cash + net_cashflow
        
        burn_rate = max(0, -net_cashflow) if net_cashflow < 0 else 0
        
        state = MonthlyState(
            month=month,
            cash=cash,
            arr=arr,
            mrr=mrr,
            revenue=revenue,
            cogs=cogs,
            gross_profit=gross_profit,
            opex=opex,
            payroll=payroll,
            other_costs=other_costs,
            ebitda=ebitda,
            net_cashflow=net_cashflow,
            burn_rate=burn_rate,
            headcount=prev_state.headcount,
            pipeline_value=new_pipeline,
            bookings=new_mrr,
            churn_amount=churn_amount,
            cac_total=cac_total,
            new_customers=new_customers,
            churned_customers=churned_customers,
            total_customers=total_customers,
            dso_actual=dso,
            collections=collections,
            debt_balance=debt_balance,
            debt_payment=debt_payment,
            regime=new_regime,
            events_active=[]
        )
        
        state, _, active_events = self._apply_scenario_events(state, events, drivers)
        state.events_active = active_events
        
        return state
    
    def _create_initial_state(self) -> MonthlyState:
        return MonthlyState(
            month=0,
            cash=self.inputs.cash_balance,
            arr=self.inputs.baseline_mrr * 12,
            mrr=self.inputs.baseline_mrr,
            revenue=self.inputs.baseline_mrr,
            cogs=self.inputs.baseline_mrr * (1 - self.inputs.gross_margin / 100),
            gross_profit=self.inputs.baseline_mrr * (self.inputs.gross_margin / 100),
            opex=self.inputs.opex,
            payroll=self.inputs.payroll,
            other_costs=self.inputs.other_costs,
            ebitda=0,
            net_cashflow=0,
            burn_rate=0,
            headcount=self.inputs.headcount,
            pipeline_value=self.inputs.pipeline_value,
            bookings=0,
            churn_amount=0,
            cac_total=0,
            new_customers=0,
            churned_customers=0,
            total_customers=self.inputs.total_customers,
            dso_actual=self.inputs.dso,
            collections=0,
            debt_balance=self.inputs.debt_balance,
            debt_payment=0,
            regime=self.inputs.starting_regime,
            events_active=[]
        )
    
    def run_single_simulation(self, events: Optional[List[ScenarioEvent]] = None) -> List[MonthlyState]:
        if events is None:
            events = []
        
        states = [self._create_initial_state()]
        
        for month in range(self.inputs.horizon_months):
            drivers_sample = self._sample_correlated_drivers(states[-1].regime, n_samples=1)
            drivers = {k: v[0] for k, v in drivers_sample.items()}
            
            _, modified_drivers, _ = self._apply_scenario_events(states[-1], events, drivers)
            
            new_state = self._step_month(states[-1], modified_drivers, events)
            states.append(new_state)
        
        return states[1:]
    
    def run_monte_carlo(
        self, 
        scenario: Optional[ScenarioDefinition] = None
    ) -> EnrichedSimulationResult:
        n = self.inputs.n_simulations
        horizon = self.inputs.horizon_months
        
        events: List[ScenarioEvent] = scenario.events if scenario else []
        scenario_key = scenario.name.lower().replace(" ", "_") if scenario else "baseline"
        scenario_name = scenario.name if scenario else "Baseline"
        
        if scenario and scenario.regime_override:
            self.inputs.starting_regime = scenario.regime_override
        
        all_states: List[List[MonthlyState]] = []
        runway_months = np.zeros(n)
        regime_counts = {"base": 0, "downturn": 0, "breakout": 0}
        
        for sim in range(n):
            states = self.run_single_simulation(events)
            all_states.append(states)
            
            for state in states:
                regime_counts[state.regime] = regime_counts.get(state.regime, 0) + 1
            
            ran_out = False
            for m, state in enumerate(states):
                if state.cash <= 0:
                    runway_months[sim] = m + 1
                    ran_out = True
                    break
            
            if not ran_out:
                runway_months[sim] = horizon + 12
        
        total_regime_months = sum(regime_counts.values())
        regime_distribution = {k: v / total_regime_months for k, v in regime_counts.items()}
        
        survival_6m = np.sum(runway_months > 6) / n
        survival_12m = np.sum(runway_months > 12) / n
        survival_18m = np.sum(runway_months > 18) / n
        survival_24m = np.sum(runway_months > 24) / n
        
        runway_p10 = np.percentile(runway_months, 10)
        runway_p50 = np.percentile(runway_months, 50)
        runway_p90 = np.percentile(runway_months, 90)
        
        cash_matrix = np.zeros((n, horizon))
        revenue_matrix = np.zeros((n, horizon))
        burn_matrix = np.zeros((n, horizon))
        arr_matrix = np.zeros((n, horizon))
        
        for sim_idx, states in enumerate(all_states):
            for m, state in enumerate(states):
                cash_matrix[sim_idx, m] = state.cash
                revenue_matrix[sim_idx, m] = state.revenue
                burn_matrix[sim_idx, m] = state.burn_rate
                arr_matrix[sim_idx, m] = state.arr
        
        bands = {
            "cash": {
                "p10": np.percentile(cash_matrix, 10, axis=0).tolist(),
                "p50": np.percentile(cash_matrix, 50, axis=0).tolist(),
                "p90": np.percentile(cash_matrix, 90, axis=0).tolist()
            },
            "revenue": {
                "p10": np.percentile(revenue_matrix, 10, axis=0).tolist(),
                "p50": np.percentile(revenue_matrix, 50, axis=0).tolist(),
                "p90": np.percentile(revenue_matrix, 90, axis=0).tolist()
            },
            "burn": {
                "p10": np.percentile(burn_matrix, 10, axis=0).tolist(),
                "p50": np.percentile(burn_matrix, 50, axis=0).tolist(),
                "p90": np.percentile(burn_matrix, 90, axis=0).tolist()
            },
            "arr": {
                "p10": np.percentile(arr_matrix, 10, axis=0).tolist(),
                "p50": np.percentile(arr_matrix, 50, axis=0).tolist(),
                "p90": np.percentile(arr_matrix, 90, axis=0).tolist()
            }
        }
        
        monthly_states = []
        for m in range(horizon):
            monthly_states.append({
                "month": m + 1,
                "cash_p10": round(bands["cash"]["p10"][m], 0),
                "cash_p50": round(bands["cash"]["p50"][m], 0),
                "cash_p90": round(bands["cash"]["p90"][m], 0),
                "revenue_p10": round(bands["revenue"]["p10"][m], 0),
                "revenue_p50": round(bands["revenue"]["p50"][m], 0),
                "revenue_p90": round(bands["revenue"]["p90"][m], 0),
                "arr_p10": round(bands["arr"]["p10"][m], 0),
                "arr_p50": round(bands["arr"]["p50"][m], 0),
                "arr_p90": round(bands["arr"]["p90"][m], 0),
                "burn_p10": round(bands["burn"]["p10"][m], 0),
                "burn_p50": round(bands["burn"]["p50"][m], 0),
                "burn_p90": round(bands["burn"]["p90"][m], 0),
                "survival_rate": float(np.sum(runway_months > m + 1) / n)
            })
        
        survival_curve = [{"month": m + 1, "survival_rate": float(np.sum(runway_months > m + 1) / n)} for m in range(horizon)]
        
        return EnrichedSimulationResult(
            scenario_key=scenario_key,
            scenario_name=scenario_name,
            runway={
                "p10": round(float(runway_p10), 1),
                "p50": round(float(runway_p50), 1),
                "p90": round(float(runway_p90), 1)
            },
            survival={
                "6m": round(float(survival_6m * 100), 1),
                "12m": round(float(survival_12m * 100), 1),
                "18m": round(float(survival_18m * 100), 1),
                "24m": round(float(survival_24m * 100), 1),
            },
            bands=bands,
            monthly_states=monthly_states,
            regime_distribution=regime_distribution,
            decision_score=None,
            survival_curve=survival_curve,
            sensitivity=None,
            n_simulations=n,
            horizon_months=horizon
        )
    
    def compute_sensitivity(
        self,
        baseline_result: EnrichedSimulationResult,
        target_runway: int = 18,
        target_probability: float = 0.7
    ) -> WhatMustBeTrueReport:
        current_prob = baseline_result.survival.get(f"{target_runway}m", 0) / 100
        
        sensitivity_results = []
        
        perturbation_pct = 0.1
        
        for driver in ["growth_rate", "churn_rate", "gross_margin", "cac"]:
            original_value = getattr(self.inputs, driver, None)
            if original_value is None:
                if driver == "growth_rate":
                    original_value = self.inputs.baseline_growth_rate
                elif driver == "gross_margin":
                    original_value = self.inputs.gross_margin
                else:
                    continue
            
            perturbed_value = original_value
            
            if driver == "growth_rate":
                perturbed_value = original_value * 1.2
                self.inputs.baseline_growth_rate = perturbed_value
            elif driver == "gross_margin":
                perturbed_value = min(95, original_value * 1.1)
                self.inputs.gross_margin = perturbed_value
            elif driver == "churn_rate":
                perturbed_value = original_value * 0.7
                setattr(self.inputs, driver, perturbed_value)
            elif driver == "cac":
                perturbed_value = original_value * 0.8
                setattr(self.inputs, driver, perturbed_value)
            
            perturbed_result = self.run_monte_carlo()
            perturbed_prob = perturbed_result.survival.get(f"{target_runway}m", 0) / 100
            
            if driver == "growth_rate":
                self.inputs.baseline_growth_rate = original_value
            elif driver == "gross_margin":
                self.inputs.gross_margin = original_value
            else:
                setattr(self.inputs, driver, original_value)
            
            impact = perturbed_prob - current_prob
            
            direction = "increase" if impact > 0 else "decrease"
            if driver in ["churn_rate", "cac"]:
                direction = "decrease" if impact > 0 else "increase"
            
            sensitivity_results.append(SensitivityResult(
                driver=driver,
                impact_direction=direction,
                impact_magnitude=abs(impact),
                threshold_value=perturbed_value,
                explanation=f"{direction.title()}ing {driver.replace('_', ' ')} improves survival by {abs(impact)*100:.1f}%"
            ))
        
        sensitivity_results.sort(key=lambda x: x.impact_magnitude, reverse=True)
        
        recommendations = []
        for sr in sensitivity_results[:3]:
            if sr.driver == "growth_rate":
                recommendations.append(f"Increase monthly growth rate above {sr.threshold_value:.1f}% to improve runway")
            elif sr.driver == "churn_rate":
                recommendations.append(f"Reduce monthly churn below {sr.threshold_value:.1f}% to extend runway")
            elif sr.driver == "gross_margin":
                recommendations.append(f"Improve gross margin above {sr.threshold_value:.1f}% to boost cash generation")
            elif sr.driver == "cac":
                recommendations.append(f"Reduce CAC below ${sr.threshold_value:.0f} to improve unit economics")
        
        return WhatMustBeTrueReport(
            target_runway_months=target_runway,
            target_probability=target_probability,
            achievable=current_prob >= target_probability,
            current_probability=current_prob,
            key_drivers=sensitivity_results,
            recommendations=recommendations
        )


def compute_decision_scores(
    results: List[EnrichedSimulationResult],
    weights: Optional[Dict[str, float]] = None
) -> List[DecisionScore]:
    if weights is None:
        weights = {
            "survival": 0.30,
            "growth": 0.25,
            "downside_risk": 0.20,
            "dilution": 0.15,
            "complexity": 0.10
        }
    
    scores = []
    
    for result in results:
        survival_score = result.survival.get("18m", 0) / 100
        
        arr_18m = result.bands["arr"]["p50"][17] if len(result.bands["arr"]["p50"]) > 17 else result.bands["arr"]["p50"][-1]
        arr_start = result.bands["arr"]["p50"][0]
        growth_score = min(1.0, (arr_18m / max(1, arr_start) - 1) / 3)
        
        cash_p10_end = result.bands["cash"]["p10"][-1]
        downside_risk = max(0, -cash_p10_end) / 1000000
        downside_score = max(0, 1 - downside_risk)
        
        dilution_pct = 0
        dilution_score = 1.0 - (dilution_pct / 50)
        
        complexity_score = 0.8
        
        composite = (
            weights["survival"] * survival_score +
            weights["growth"] * growth_score +
            weights["downside_risk"] * downside_score +
            weights["dilution"] * dilution_score +
            weights["complexity"] * complexity_score
        )
        
        scores.append(DecisionScore(
            scenario_key=result.scenario_key,
            scenario_name=result.scenario_name,
            survival_12m_prob=result.survival.get("12m", 0),
            survival_18m_prob=result.survival.get("18m", 0),
            expected_arr_18m=arr_18m,
            downside_risk_cvar=cash_p10_end,
            dilution_pct=dilution_pct,
            complexity_score=complexity_score,
            composite_score=round(composite, 3),
            rank=0
        ))
    
    scores.sort(key=lambda x: x.composite_score, reverse=True)
    for i, score in enumerate(scores):
        score.rank = i + 1
    
    return scores
