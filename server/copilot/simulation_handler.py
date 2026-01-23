"""
Simulation Handler for Conversational Co-Pilot.

Executes simulations based on parsed intents and manages scenarios.
"""
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from server.copilot.intent_parser import (
    ParsedIntent, CopilotIntent, SimulationParameters,
    format_parameters_summary
)
from server.copilot.conversation_state import ConversationState, conversation_store
from server.copilot.recommendation_engine import (
    RecommendationEngine, UserGoals, Recommendation
)

logger = logging.getLogger(__name__)


class SimulationHandler:
    """Handles simulation execution and scenario management."""
    
    def __init__(self, db: Session, company_id: int, user_id: int):
        self.db = db
        self.company_id = company_id
        self.user_id = user_id
        self.state = conversation_store.get(company_id, user_id)
    
    def handle_intent(self, parsed: ParsedIntent) -> Dict[str, Any]:
        """Route intent to appropriate handler."""
        handlers = {
            CopilotIntent.RUN_SIMULATION: self.run_simulation,
            CopilotIntent.COMPARE_SCENARIOS: self.compare_scenarios,
            CopilotIntent.SAVE_SCENARIO: self.save_scenario,
            CopilotIntent.LOAD_SCENARIO: self.load_scenario,
            CopilotIntent.MODIFY_PREVIOUS: self.modify_previous,
            CopilotIntent.EXPLAIN_RESULTS: self.explain_results,
            CopilotIntent.GENERAL_QUERY: self.general_query,
        }
        
        handler = handlers.get(parsed.intent, self.general_query)
        
        if not parsed.is_complete:
            return self._build_clarification_response(parsed)
        
        try:
            result = handler(parsed)
            self.state.add_message('user', parsed.original_message)
            self.state.add_message('assistant', result.get('summary', ''), {
                'intent': parsed.intent.value,
                'action': result.get('action')
            })
            conversation_store.save(self.state)
            return result
        except Exception as e:
            logger.error(f"Error handling intent {parsed.intent}: {e}")
            return {
                'success': False,
                'error': str(e),
                'summary': f"I encountered an error: {str(e)}. Please try again.",
                'intent': parsed.intent.value
            }
    
    def run_simulation(self, parsed: ParsedIntent) -> Dict[str, Any]:
        """Run a simulation with extracted parameters."""
        from server.models.truth_scan import TruthScan
        from server.simulate.enhanced_monte_carlo import (
            EnhancedSimulationInputs, SimulationConfig, run_enhanced_monte_carlo
        )
        from server.models.scenario import Scenario
        from server.models.simulation_run import SimulationRun
        
        truth_scan = self.db.query(TruthScan).filter(
            TruthScan.company_id == self.company_id
        ).order_by(TruthScan.created_at.desc()).first()
        
        if not truth_scan:
            return {
                'success': False,
                'error': 'No financial data available',
                'summary': "I need financial data to run a simulation. Please upload your financial documents first.",
                'intent': parsed.intent.value
            }
        
        metrics = truth_scan.outputs_json.get("metrics", {})
        params = parsed.parameters
        
        baseline_revenue = metrics.get("monthly_revenue", 50000)
        if isinstance(baseline_revenue, dict):
            baseline_revenue = baseline_revenue.get("value", 50000)
        
        baseline_growth = metrics.get("revenue_growth_mom", 5)
        if isinstance(baseline_growth, dict):
            baseline_growth = baseline_growth.get("value", 5)
        
        burn_rate = metrics.get("burn_rate", 60000)
        if isinstance(burn_rate, dict):
            burn_rate = burn_rate.get("value", 60000)
        
        cash_balance = metrics.get("cash_balance", 500000)
        if isinstance(cash_balance, dict):
            cash_balance = cash_balance.get("value", 500000)
        
        gross_margin = metrics.get("gross_margin", 70)
        if isinstance(gross_margin, dict):
            gross_margin = gross_margin.get("value", 70)
        
        churn_rate = metrics.get("churn_rate", 5)
        if isinstance(churn_rate, dict):
            churn_rate = churn_rate.get("value", 5)
        
        opex = burn_rate * 0.3
        payroll = burn_rate * 0.5
        other_costs = burn_rate * 0.2
        
        burn_reduction_pct = params.burn_reduction_pct or 0
        if burn_reduction_pct:
            opex = opex * (1 - burn_reduction_pct / 100)
            other_costs = other_costs * (1 - burn_reduction_pct / 100)
        
        growth_uplift_pct = params.revenue_growth_pct or 0
        pricing_change_pct = params.price_change_pct or 0
        
        fundraise_amount = params.fundraise_amount or 0
        fundraise_month = params.fundraise_month
        
        inputs = EnhancedSimulationInputs(
            baseline_revenue=baseline_revenue,
            baseline_growth_rate=baseline_growth / 100,
            gross_margin=gross_margin / 100,
            opex=opex,
            payroll=payroll,
            other_costs=other_costs,
            cash_balance=cash_balance,
            churn_rate=churn_rate,
            pricing_change_pct=pricing_change_pct,
            growth_uplift_pct=growth_uplift_pct,
            burn_reduction_pct=burn_reduction_pct,
            fundraise_amount=fundraise_amount,
            fundraise_month=fundraise_month,
        )
        
        config = SimulationConfig(
            iterations=500,
            horizon_months=params.horizon_months,
            seed=42,
            confidence_intervals=[10, 25, 50, 75, 90]
        )
        
        results = run_enhanced_monte_carlo(inputs, config)
        
        scenario_name = params.scenario_name or f"Simulation {datetime.now().strftime('%Y%m%d_%H%M')}"
        scenario = Scenario(
            company_id=self.company_id,
            name=scenario_name,
            inputs_json={
                'parameters': {
                    'burn_reduction_pct': params.burn_reduction_pct,
                    'price_change_pct': params.price_change_pct,
                    'revenue_growth_pct': params.revenue_growth_pct,
                    'hiring_freeze_months': params.hiring_freeze_months,
                    'headcount_change': params.headcount_change,
                    'fundraise_amount': params.fundraise_amount,
                    'fundraise_month': params.fundraise_month,
                    'horizon_months': params.horizon_months,
                },
                'original_message': parsed.original_message
            }
        )
        self.db.add(scenario)
        self.db.commit()
        self.db.refresh(scenario)
        
        sim_run = SimulationRun(
            scenario_id=scenario.id,
            n_sims=config.iterations,
            seed=config.seed,
            outputs_json=results
        )
        self.db.add(sim_run)
        self.db.commit()
        self.db.refresh(sim_run)
        
        self.state.set_last_simulation(
            scenario_id=int(scenario.id),
            scenario_name=scenario_name,
            simulation_id=int(sim_run.id),
            params=dict(scenario.inputs_json) if scenario.inputs_json else {},
            results=results
        )
        
        summary = results.get('summary', {})
        runway = summary.get('mean_runway_months', 0)
        survival = summary.get('survival_rate', 0)
        final_cash = summary.get('mean_final_cash', 0)
        
        param_summary = format_parameters_summary(params)
        
        rec_engine = RecommendationEngine(industry="saas")
        sim_results_for_recs = {
            'runway_months': runway,
            'survival_rate': survival * 100 if survival <= 1 else survival,
            'final_cash': final_cash,
        }
        current_financials = {
            'burn_multiple': burn_rate / max(baseline_revenue, 1) if baseline_revenue else 3.0,
            'gross_margin': gross_margin / 100,
            'churn_rate': churn_rate / 100,
            'growth_rate': baseline_growth / 100,
        }
        sim_params_for_recs = {
            'burn_reduction_pct': params.burn_reduction_pct,
            'price_change_pct': params.price_change_pct,
            'fundraise_amount': params.fundraise_amount,
        }
        recommendations = rec_engine.analyze(
            sim_results_for_recs,
            current_financials,
            UserGoals(),
            sim_params_for_recs
        )
        
        rec_text = rec_engine.format_recommendations_for_chat(recommendations)
        
        recommendation_ids = {}
        for rec in recommendations:
            try:
                rec_id = conversation_store.add_recommendation(
                    self.db,
                    self.company_id,
                    self.user_id,
                    recommendation_type=rec.rec_type.value,
                    recommendation_text=rec.text,
                    priority=rec.priority,
                    context_data={
                        'action_prompt': rec.action_prompt,
                        'rationale': rec.rationale,
                        'estimated_impact': rec.estimated_impact,
                        'scenario_id': scenario.id,
                        'simulation_id': sim_run.id,
                    }
                )
                recommendation_ids[rec.rec_type.value] = rec_id
            except Exception as e:
                logger.warning(f"Failed to persist recommendation: {e}")
        
        chart_data = self._generate_chart_data(results, scenario_name)
        
        response_text = f"""**Simulation Results: {scenario_name}**

I ran a {params.horizon_months}-month simulation with {param_summary}.

**Key Outcomes:**
- **Runway**: {runway:.1f} months (P50)
- **Survival Rate**: {survival*100:.0f}%
- **Final Cash**: ${final_cash/1000:.0f}K

The simulation ran {config.iterations} Monte Carlo iterations to account for uncertainty.

{rec_text}"""
        
        return {
            'success': True,
            'intent': parsed.intent.value,
            'action': 'simulation_completed',
            'summary': response_text,
            'scenario_id': scenario.id,
            'scenario_name': scenario_name,
            'simulation_id': sim_run.id,
            'results': {
                'runway_months': runway,
                'survival_rate': survival,
                'final_cash': final_cash,
                'confidence_intervals': summary.get('percentiles', {}),
            },
            'parameters': {
                'burn_reduction_pct': params.burn_reduction_pct,
                'price_change_pct': params.price_change_pct,
                'revenue_growth_pct': params.revenue_growth_pct,
                'hiring_freeze_months': params.hiring_freeze_months,
                'fundraise_amount': params.fundraise_amount,
                'horizon_months': params.horizon_months,
            },
            'chart_data': chart_data,
            'recommendations': [
                {
                    'id': recommendation_ids.get(r.rec_type.value),
                    'type': r.rec_type.value,
                    'priority': r.priority,
                    'text': r.text,
                    'action_prompt': r.action_prompt,
                }
                for r in recommendations
            ],
            'follow_up_actions': [
                {'label': 'Save as Plan', 'action': 'save_scenario'},
                {'label': 'Compare Scenarios', 'action': 'compare_scenarios'},
                {'label': 'Tweak Parameters', 'action': 'modify_previous'},
            ]
        }
    
    def modify_previous(self, parsed: ParsedIntent) -> Dict[str, Any]:
        """Modify the previous simulation with new parameters."""
        if not self.state.last_simulation_params:
            return {
                'success': False,
                'error': 'No previous simulation to modify',
                'summary': "I don't have a previous simulation to modify. Let's start fresh - what scenario would you like to simulate?",
                'intent': parsed.intent.value
            }
        
        prev_params = self.state.last_simulation_params.get('parameters', {})
        
        new_params = SimulationParameters(
            burn_reduction_pct=parsed.parameters.burn_reduction_pct or prev_params.get('burn_reduction_pct'),
            price_change_pct=parsed.parameters.price_change_pct or prev_params.get('price_change_pct'),
            revenue_growth_pct=parsed.parameters.revenue_growth_pct or prev_params.get('revenue_growth_pct'),
            hiring_freeze_months=parsed.parameters.hiring_freeze_months or prev_params.get('hiring_freeze_months'),
            headcount_change=parsed.parameters.headcount_change or prev_params.get('headcount_change'),
            fundraise_amount=parsed.parameters.fundraise_amount or prev_params.get('fundraise_amount'),
            fundraise_month=parsed.parameters.fundraise_month or prev_params.get('fundraise_month'),
            horizon_months=parsed.parameters.horizon_months or prev_params.get('horizon_months', 24),
        )
        
        modified_parsed = ParsedIntent(
            intent=CopilotIntent.RUN_SIMULATION,
            parameters=new_params,
            confidence=parsed.confidence,
            original_message=parsed.original_message,
            is_complete=True
        )
        
        return self.run_simulation(modified_parsed)
    
    def save_scenario(self, parsed: ParsedIntent) -> Dict[str, Any]:
        """Save the current scenario with a name."""
        from server.models.scenario import Scenario
        
        if not self.state.last_scenario_id:
            return {
                'success': False,
                'error': 'No scenario to save',
                'summary': "I don't have a scenario to save. Run a simulation first, then I can save it.",
                'intent': parsed.intent.value
            }
        
        name = parsed.parameters.scenario_name
        if not name:
            return self._build_clarification_response(parsed)
        
        scenario = self.db.query(Scenario).filter(
            Scenario.id == self.state.last_scenario_id
        ).first()
        
        if scenario:
            scenario.name = name
            self.db.commit()
            self.state.last_scenario_name = name
            
            return {
                'success': True,
                'intent': parsed.intent.value,
                'action': 'scenario_saved',
                'summary': f"Saved the scenario as **'{name}'**. You can load it later with 'Load {name}' or compare it with other scenarios.",
                'scenario_id': scenario.id,
                'scenario_name': name
            }
        
        return {
            'success': False,
            'error': 'Scenario not found',
            'summary': "I couldn't find the scenario to save. Please run a new simulation.",
            'intent': parsed.intent.value
        }
    
    def load_scenario(self, parsed: ParsedIntent) -> Dict[str, Any]:
        """Load a saved scenario."""
        from server.models.scenario import Scenario
        from server.models.simulation_run import SimulationRun
        
        name = parsed.parameters.scenario_name
        if not name:
            scenarios = self.db.query(Scenario).filter(
                Scenario.company_id == self.company_id
            ).order_by(Scenario.created_at.desc()).limit(5).all()
            
            if not scenarios:
                return {
                    'success': False,
                    'error': 'No saved scenarios',
                    'summary': "You don't have any saved scenarios yet. Run a simulation first.",
                    'intent': parsed.intent.value
                }
            
            scenario_list = "\n".join([f"- {s.name}" for s in scenarios])
            return {
                'success': False,
                'error': 'No scenario name provided',
                'summary': f"Which scenario would you like to load?\n\n{scenario_list}",
                'intent': parsed.intent.value,
                'available_scenarios': [{'id': s.id, 'name': s.name} for s in scenarios]
            }
        
        scenario = self.db.query(Scenario).filter(
            Scenario.company_id == self.company_id,
            Scenario.name.ilike(f"%{name}%")
        ).first()
        
        if not scenario:
            return {
                'success': False,
                'error': f'Scenario "{name}" not found',
                'summary': f"I couldn't find a scenario called '{name}'. Check the name and try again.",
                'intent': parsed.intent.value
            }
        
        sim_run = self.db.query(SimulationRun).filter(
            SimulationRun.scenario_id == scenario.id
        ).order_by(SimulationRun.created_at.desc()).first()
        
        results = sim_run.outputs_json if sim_run else {}
        
        self.state.set_last_simulation(
            scenario_id=int(scenario.id),
            scenario_name=str(scenario.name),
            simulation_id=int(sim_run.id) if sim_run else None,
            params=dict(scenario.inputs_json) if scenario.inputs_json else {},
            results=dict(results) if results else {}
        )
        
        summary = results.get('summary', {}) if isinstance(results, dict) else {}
        runway = summary.get('mean_runway_months', 0)
        survival = summary.get('survival_rate', 0)
        
        scenario_name_str = str(scenario.name)
        
        return {
            'success': True,
            'intent': parsed.intent.value,
            'action': 'scenario_loaded',
            'summary': f"""Loaded scenario **'{scenario_name_str}'**

**Results:**
- Runway: {runway:.1f} months
- Survival Rate: {survival*100:.0f}%

You can now modify this scenario or compare it with others.""",
            'scenario_id': int(scenario.id),
            'scenario_name': scenario_name_str,
            'results': {
                'runway_months': runway,
                'survival_rate': survival,
            }
        }
    
    def compare_scenarios(self, parsed: ParsedIntent) -> Dict[str, Any]:
        """Compare two or more scenarios."""
        from server.models.scenario import Scenario
        from server.models.simulation_run import SimulationRun
        
        scenario_names = parsed.parameters.compare_scenarios
        
        if len(scenario_names) < 2:
            scenarios = self.db.query(Scenario).filter(
                Scenario.company_id == self.company_id
            ).order_by(Scenario.created_at.desc()).limit(5).all()
            
            if len(scenarios) < 2:
                return {
                    'success': False,
                    'error': 'Not enough scenarios to compare',
                    'summary': "You need at least 2 saved scenarios to compare. Run more simulations and save them first.",
                    'intent': parsed.intent.value
                }
            
            scenario_list = "\n".join([f"- {s.name}" for s in scenarios])
            return {
                'success': False,
                'error': 'Need two scenario names',
                'summary': f"Which two scenarios would you like to compare?\n\nAvailable scenarios:\n{scenario_list}",
                'intent': parsed.intent.value,
                'available_scenarios': [{'id': s.id, 'name': s.name} for s in scenarios]
            }
        
        scenarios_data = []
        for name in scenario_names[:2]:
            scenario = self.db.query(Scenario).filter(
                Scenario.company_id == self.company_id,
                Scenario.name.ilike(f"%{name.strip()}%")
            ).first()
            
            if scenario:
                sim_run = self.db.query(SimulationRun).filter(
                    SimulationRun.scenario_id == scenario.id
                ).order_by(SimulationRun.created_at.desc()).first()
                
                scenarios_data.append({
                    'name': scenario.name,
                    'id': scenario.id,
                    'results': sim_run.outputs_json if sim_run else {}
                })
        
        if len(scenarios_data) < 2:
            return {
                'success': False,
                'error': 'Could not find all scenarios',
                'summary': f"I couldn't find all the scenarios you mentioned. Please check the names.",
                'intent': parsed.intent.value
            }
        
        s1, s2 = scenarios_data[0], scenarios_data[1]
        s1_summary = s1['results'].get('summary', {})
        s2_summary = s2['results'].get('summary', {})
        
        runway_diff = (s1_summary.get('mean_runway_months', 0) - s2_summary.get('mean_runway_months', 0))
        survival_diff = (s1_summary.get('survival_rate', 0) - s2_summary.get('survival_rate', 0)) * 100
        
        comparison_text = f"""**Comparison: {s1['name']} vs {s2['name']}**

| Metric | {s1['name']} | {s2['name']} | Difference |
|--------|------------|------------|------------|
| Runway | {s1_summary.get('mean_runway_months', 0):.1f} mo | {s2_summary.get('mean_runway_months', 0):.1f} mo | {runway_diff:+.1f} mo |
| Survival | {s1_summary.get('survival_rate', 0)*100:.0f}% | {s2_summary.get('survival_rate', 0)*100:.0f}% | {survival_diff:+.0f}% |
| Final Cash | ${s1_summary.get('mean_final_cash', 0)/1000:.0f}K | ${s2_summary.get('mean_final_cash', 0)/1000:.0f}K | - |

"""
        
        if runway_diff > 0:
            comparison_text += f"**{s1['name']}** extends runway by {runway_diff:.1f} months compared to {s2['name']}."
        elif runway_diff < 0:
            comparison_text += f"**{s2['name']}** extends runway by {abs(runway_diff):.1f} months compared to {s1['name']}."
        else:
            comparison_text += "Both scenarios have similar runway projections."
        
        return {
            'success': True,
            'intent': parsed.intent.value,
            'action': 'scenarios_compared',
            'summary': comparison_text,
            'comparison': {
                'scenario_1': {
                    'name': s1['name'],
                    'runway': s1_summary.get('mean_runway_months', 0),
                    'survival': s1_summary.get('survival_rate', 0),
                },
                'scenario_2': {
                    'name': s2['name'],
                    'runway': s2_summary.get('mean_runway_months', 0),
                    'survival': s2_summary.get('survival_rate', 0),
                },
                'differences': {
                    'runway_months': runway_diff,
                    'survival_rate': survival_diff,
                }
            }
        }
    
    def explain_results(self, parsed: ParsedIntent) -> Dict[str, Any]:
        """Explain the results of the last simulation."""
        if not self.state.last_simulation_results:
            return {
                'success': False,
                'error': 'No results to explain',
                'summary': "I don't have any simulation results to explain. Run a simulation first.",
                'intent': parsed.intent.value
            }
        
        results = self.state.last_simulation_results
        params = self.state.last_simulation_params or {}
        summary = results.get('summary', {})
        
        runway = summary.get('mean_runway_months', 0)
        survival = summary.get('survival_rate', 0)
        
        explanation = f"""**Explanation of Results**

Your simulation projected a **{runway:.1f} month runway** with a **{survival*100:.0f}% survival rate**. Here's why:

"""
        
        param_info = params.get('parameters', {})
        if param_info.get('burn_reduction_pct'):
            explanation += f"- **Burn Reduction ({param_info['burn_reduction_pct']}%)**: This directly extends runway by reducing monthly cash outflow.\n"
        if param_info.get('price_change_pct'):
            explanation += f"- **Price Change ({param_info['price_change_pct']:+}%)**: Impacts revenue and margins.\n"
        if param_info.get('hiring_freeze_months'):
            explanation += f"- **Hiring Freeze ({param_info['hiring_freeze_months']} months)**: Reduces headcount costs during freeze period.\n"
        if param_info.get('fundraise_amount'):
            amt = param_info['fundraise_amount']
            amt_str = f"${amt/1_000_000:.1f}M" if amt >= 1_000_000 else f"${amt/1000:.0f}K"
            explanation += f"- **Fundraise ({amt_str})**: Injects cash, extending runway significantly.\n"
        
        explanation += """
The simulation accounts for uncertainty through Monte Carlo modeling, running hundreds of iterations with varying assumptions."""
        
        return {
            'success': True,
            'intent': parsed.intent.value,
            'action': 'results_explained',
            'summary': explanation
        }
    
    def general_query(self, parsed: ParsedIntent) -> Dict[str, Any]:
        """Handle general queries that don't match specific intents."""
        return {
            'success': True,
            'intent': parsed.intent.value,
            'action': 'general_response',
            'summary': None,
            'pass_to_agents': True
        }
    
    def _build_clarification_response(self, parsed: ParsedIntent) -> Dict[str, Any]:
        """Build a response requesting clarification."""
        clarifications = parsed.clarifications_needed
        
        if not clarifications:
            return self.general_query(parsed)
        
        questions = []
        for c in clarifications:
            q = {'field': c.field, 'question': c.question}
            if c.options:
                q['options'] = c.options
            if c.example:
                q['example'] = c.example
            questions.append(q)
        
        self.state.set_pending_clarification({
            'intent': parsed.intent.value,
            'questions': questions,
            'partial_params': {
                k: v for k, v in parsed.parameters.__dict__.items() 
                if v is not None and k != 'compare_scenarios'
            }
        })
        
        summary = clarifications[0].question
        if clarifications[0].options:
            summary += "\n\nSuggestions:\n" + "\n".join([f"- {o}" for o in clarifications[0].options])
        if clarifications[0].example:
            summary += f"\n\nExample: \"{clarifications[0].example}\""
        
        return {
            'success': False,
            'intent': parsed.intent.value,
            'action': 'clarification_needed',
            'summary': summary,
            'clarifications': questions
        }
    
    def _generate_chart_data(
        self, 
        results: Dict[str, Any], 
        scenario_name: str
    ) -> Dict[str, Any]:
        """Generate chart-ready data for inline visualization in chat."""
        summary = results.get('summary', {})
        trajectories = results.get('trajectories', {})
        
        runway_data = {
            'type': 'runway_band',
            'scenario_name': scenario_name,
            'metrics': {
                'p10': summary.get('percentiles', {}).get('p10_runway', 0),
                'p25': summary.get('percentiles', {}).get('p25_runway', 0),
                'p50': summary.get('mean_runway_months', 0),
                'p75': summary.get('percentiles', {}).get('p75_runway', 0),
                'p90': summary.get('percentiles', {}).get('p90_runway', 0),
            }
        }
        
        cash_trajectory = []
        if trajectories.get('mean_cash'):
            for i, cash in enumerate(trajectories['mean_cash'][:24]):
                month_data = {'month': i}
                month_data['mean'] = cash
                if trajectories.get('p10_cash') and i < len(trajectories['p10_cash']):
                    month_data['p10'] = trajectories['p10_cash'][i]
                if trajectories.get('p90_cash') and i < len(trajectories['p90_cash']):
                    month_data['p90'] = trajectories['p90_cash'][i]
                cash_trajectory.append(month_data)
        
        survival_trajectory = []
        if trajectories.get('survival_rate'):
            for i, rate in enumerate(trajectories['survival_rate'][:24]):
                survival_trajectory.append({
                    'month': i,
                    'survival_rate': rate * 100
                })
        
        return {
            'runway': runway_data,
            'cash_trajectory': cash_trajectory,
            'survival_trajectory': survival_trajectory,
        }
