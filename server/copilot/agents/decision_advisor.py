"""
Decision Advisor Agent - Decision-first, probability-driven financial advisor.

This agent transforms user questions into actionable, simulation-backed recommendations.
It extracts core decisions, maps them to financial levers, runs simulations automatically,
and provides opinionated recommendations with confidence levels.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import logging
import re

from .base import BaseAgent, AgentType, AgentResponse, ConfidenceLevel, CompanyKnowledgeBase

logger = logging.getLogger(__name__)


class DecisionType(Enum):
    """Types of strategic decisions the advisor can handle."""
    EXTEND_RUNWAY = "extend_runway"
    FUNDRAISE_TIMING = "fundraise_timing"
    REDUCE_BURN = "reduce_burn"
    INCREASE_REVENUE = "increase_revenue"
    HIRING = "hiring"
    PRICING = "pricing"
    MARKET_EXPANSION = "market_expansion"
    COST_OPTIMIZATION = "cost_optimization"
    GENERAL = "general"


@dataclass
class DecisionContext:
    """Extracted decision context from user query."""
    decision_type: DecisionType
    core_decision: str
    target_outcome: Optional[str] = None
    timeframe_months: int = 12
    constraints: List[str] = field(default_factory=list)
    levers_available: List[str] = field(default_factory=list)


@dataclass
class FinancialLever:
    """A quantitative financial adjustment lever."""
    name: str
    current_value: float
    adjusted_value: float
    change_percent: float
    impact_description: str
    feasibility: str  # "easy", "moderate", "difficult"
    time_to_implement_months: int


@dataclass
class SimulationOutcome:
    """Outcome from running a simulation with specific levers."""
    lever_combination: List[str]
    runway_p10: float
    runway_p50: float
    runway_p90: float
    survival_12m: float
    survival_18m: float
    survival_24m: float
    cash_at_horizon: Dict[str, float]
    risk_factors: List[str]


@dataclass
class RiskAnalysis:
    """Risk and sensitivity analysis results."""
    riskiest_assumptions: List[Dict[str, Any]]
    sensitivity_analysis: List[Dict[str, Any]]
    failure_cascade: str
    confidence_blockers: List[str]


@dataclass
class ActionRecommendation:
    """Final recommendation with confidence level."""
    primary_action: str
    action_details: str
    expected_impact: str
    confidence: ConfidenceLevel
    confidence_reasoning: str
    what_would_change_recommendation: str
    alternative_actions: List[str]


def _metric_number(value) -> Optional[float]:
    """A truth-scan / CKB metric as a float: raw number, numeric string, or {value: ...}."""
    if isinstance(value, dict):
        value = value.get("value")
    if isinstance(value, bool) or value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


class DecisionAdvisorAgent(BaseAgent):
    """
    Decision Advisor Agent that provides decision-first, probability-driven advice.
    
    Key capabilities:
    1. Extracts and restates user decisions in plain English
    2. Maps decisions to quantitative financial levers
    3. Runs simulations automatically when context is clear
    4. Surfaces risks with sensitivity analysis
    5. Provides opinionated recommendations with confidence levels
    """
    
    DECISION_PATTERNS = {
        DecisionType.EXTEND_RUNWAY: [
            r"extend.*runway", r"runway.*extend", r"more.*runway",
            r"stretch.*cash", r"survive.*longer", r"last.*longer",
            r"how.*long.*survive", r"increase.*runway"
        ],
        DecisionType.FUNDRAISE_TIMING: [
            r"fundrais(e|ing).*delay", r"delay.*fundrais", r"postpone.*round",
            r"push.*back.*round", r"raise.*later", r"when.*raise",
            r"timing.*fundrais", r"slip.*fundrais", r"fundrais.*slip"
        ],
        DecisionType.REDUCE_BURN: [
            r"cut.*burn", r"reduce.*burn", r"lower.*expenses",
            r"cut.*costs?", r"reduce.*costs?", r"save.*money",
            r"decrease.*burn", r"burn.*reduction"
        ],
        DecisionType.INCREASE_REVENUE: [
            r"increase.*revenue", r"grow.*revenue", r"more.*sales",
            r"boost.*revenue", r"revenue.*growth", r"scale.*revenue"
        ],
        DecisionType.HIRING: [
            r"hiring.*freeze", r"stop.*hiring", r"pause.*hiring",
            r"delay.*hires?", r"slow.*hiring", r"team.*size",
            r"headcount", r"layoff", r"restructur"
        ],
        DecisionType.PRICING: [
            r"raise.*price", r"increase.*price", r"pricing.*change",
            r"price.*increase", r"charge.*more", r"premium.*pricing"
        ],
        DecisionType.COST_OPTIMIZATION: [
            r"optimi[sz]e.*costs?", r"efficient", r"streamline",
            r"cost.*saving", r"reduce.*overhead"
        ]
    }
    
    LEVER_DEFINITIONS = {
        "burn_reduction": {
            "name": "Burn Rate Reduction",
            "description": "Reduce monthly operating expenses",
            "typical_range": (10, 40),
            "implementation_time": 1,
            "feasibility": "moderate"
        },
        "hiring_freeze": {
            "name": "Hiring Freeze/Delay",
            "description": "Pause or slow new hires",
            "typical_range": (50, 100),
            "implementation_time": 0,
            "feasibility": "easy"
        },
        "pricing_increase": {
            "name": "Price Increase",
            "description": "Raise prices on products/services",
            "typical_range": (5, 25),
            "implementation_time": 2,
            "feasibility": "moderate"
        },
        "revenue_acceleration": {
            "name": "Revenue Acceleration",
            "description": "Increase sales velocity and conversion",
            "typical_range": (10, 30),
            "implementation_time": 3,
            "feasibility": "difficult"
        },
        "fundraise_timing": {
            "name": "Fundraise Timing",
            "description": "Adjust when to raise next round",
            "typical_range": (-6, 6),
            "implementation_time": 0,
            "feasibility": "moderate"
        },
        "margin_improvement": {
            "name": "Gross Margin Improvement",
            "description": "Improve unit economics",
            "typical_range": (2, 10),
            "implementation_time": 3,
            "feasibility": "difficult"
        }
    }

    def __init__(self, llm_router=None):
        super().__init__(AgentType.CFO, llm_router)
        self.logger = logging.getLogger("copilot.decision_advisor")
        self.simulation_status: Dict[str, Any] = {"ran": False, "reason": None}
    
    async def process(
        self,
        query: str,
        ckb: CompanyKnowledgeBase,
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Process a decision-oriented query and return structured advice."""
        
        decision_context = self.clarify_decision(query, ckb)
        
        financials = self._get_financial_snapshot(ckb, context)
        
        levers = self.map_decision_to_levers(decision_context, financials)
        
        simulation_results = await self._run_decision_simulations(
            decision_context, levers, financials, context
        )
        
        risk_analysis = self.identify_risks(simulation_results, financials)
        
        recommendation = self.recommend_action(
            decision_context, simulation_results, risk_analysis, financials
        )
        
        return self._format_response(
            decision_context, levers, simulation_results,
            risk_analysis, recommendation, ckb
        )
    
    def clarify_decision(
        self,
        query: str,
        ckb: CompanyKnowledgeBase
    ) -> DecisionContext:
        """
        Extract and clarify the core decision from user's query.
        Returns a structured DecisionContext.
        """
        query_lower = query.lower()
        
        decision_type = self._detect_decision_type(query_lower)
        
        core_decision = self._extract_core_decision(query_lower, decision_type, ckb)
        
        timeframe = self._extract_timeframe(query_lower)
        
        target = self._extract_target_outcome(query_lower, decision_type)
        
        levers = self._get_available_levers(decision_type)
        
        constraints = self._extract_constraints(query_lower)
        
        return DecisionContext(
            decision_type=decision_type,
            core_decision=core_decision,
            target_outcome=target,
            timeframe_months=timeframe,
            constraints=constraints,
            levers_available=levers
        )
    
    def _detect_decision_type(self, query: str) -> DecisionType:
        """Detect the type of decision from query patterns."""
        for dtype, patterns in self.DECISION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    return dtype
        return DecisionType.GENERAL
    
    def _extract_core_decision(
        self,
        query: str,
        decision_type: DecisionType,
        ckb: CompanyKnowledgeBase
    ) -> str:
        """Extract and restate the core decision in plain English."""
        runway = ckb.financials.get("runway_months", 12)
        burn = ckb.financials.get("monthly_burn", 0)
        
        templates = {
            DecisionType.EXTEND_RUNWAY: f"Extend runway beyond current {runway:.0f} months",
            DecisionType.FUNDRAISE_TIMING: "Determine optimal timing for next fundraising round",
            DecisionType.REDUCE_BURN: f"Reduce monthly burn rate from ${burn:,.0f}",
            DecisionType.INCREASE_REVENUE: "Accelerate revenue growth to improve unit economics",
            DecisionType.HIRING: "Optimize headcount and hiring pace",
            DecisionType.PRICING: "Adjust pricing strategy to improve margins",
            DecisionType.COST_OPTIMIZATION: "Optimize cost structure for efficiency",
            DecisionType.GENERAL: "Improve financial position and extend runway"
        }
        
        return templates.get(decision_type, templates[DecisionType.GENERAL])
    
    def _extract_timeframe(self, query: str) -> int:
        """Extract timeframe in months from query."""
        month_patterns = [
            (r"(\d+)\s*months?", lambda m: int(m.group(1))),
            (r"(\d+)\s*years?", lambda m: int(m.group(1)) * 12),
            (r"next\s*quarter", lambda m: 3),
            (r"next\s*year", lambda m: 12),
            (r"6\s*months?", lambda m: 6),
        ]
        
        for pattern, extractor in month_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return extractor(match)
        
        return 12
    
    def _extract_target_outcome(
        self,
        query: str,
        decision_type: DecisionType
    ) -> Optional[str]:
        """Extract specific target outcome if mentioned."""
        if decision_type == DecisionType.EXTEND_RUNWAY:
            match = re.search(r"(\d+)\s*months?.*runway", query)
            if match:
                return f"{match.group(1)} months of runway"
        
        return None
    
    def _get_available_levers(self, decision_type: DecisionType) -> List[str]:
        """Get available financial levers for this decision type."""
        lever_mapping = {
            DecisionType.EXTEND_RUNWAY: [
                "burn_reduction", "hiring_freeze", "pricing_increase",
                "revenue_acceleration", "margin_improvement"
            ],
            DecisionType.FUNDRAISE_TIMING: [
                "fundraise_timing", "burn_reduction", "revenue_acceleration"
            ],
            DecisionType.REDUCE_BURN: [
                "burn_reduction", "hiring_freeze"
            ],
            DecisionType.INCREASE_REVENUE: [
                "pricing_increase", "revenue_acceleration"
            ],
            DecisionType.HIRING: [
                "hiring_freeze", "burn_reduction"
            ],
            DecisionType.PRICING: [
                "pricing_increase", "margin_improvement"
            ],
            DecisionType.COST_OPTIMIZATION: [
                "burn_reduction", "margin_improvement"
            ],
            DecisionType.GENERAL: list(self.LEVER_DEFINITIONS.keys())
        }
        return lever_mapping.get(decision_type, lever_mapping[DecisionType.GENERAL])
    
    def _extract_constraints(self, query: str) -> List[str]:
        """Extract any constraints mentioned in the query."""
        constraints = []
        
        if re.search(r"without.*(layoff|firing|letting.*go)", query):
            constraints.append("No layoffs")
        if re.search(r"without.*(raise|fundrais)", query):
            constraints.append("No new fundraising")
        if re.search(r"maintain.*growth", query):
            constraints.append("Maintain growth rate")
        
        return constraints
    
    def _get_financial_snapshot(
        self,
        ckb: CompanyKnowledgeBase,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Current financials from the CKB, then the latest truth scan.

        context["truth_scan"] is the scan's whole outputs_json; its numbers live
        under ["metrics"] with the truth-scan keys (monthly_revenue, net_burn,
        cash_balance, runway_p50, gross_margin, revenue_growth_mom, ...). The
        old reader looked at the top level with other names (revenue,
        monthly_burn, gross_margin_pct, revenue_growth_pct, ...), never matched,
        and filled in invented defaults ($50k burn, $500k cash, 12 months,
        70% margin, 10% growth, 5% churn). Unknown values are now None.

        monthly_burn is the canonical NET burn (total costs incl. COGS minus
        revenue); negative means profitable.
        """
        fin = ckb.financials or {}
        truth = context.get("truth_scan") or {}
        metrics = truth.get("metrics") if isinstance(truth.get("metrics"), dict) else {}
        # Tolerate a flat legacy payload as a last resort.
        sources = [fin, metrics, truth]

        def pick(*keys):
            for src in sources:
                for k in keys:
                    v = _metric_number(src.get(k)) if isinstance(src, dict) else None
                    if v is not None:
                        return v
            return None

        revenue = pick("revenue", "monthly_revenue", "mrr")
        net_burn = pick("monthly_burn", "net_burn")
        cash = pick("cash_balance")
        runway = pick("runway_months", "runway_p50")
        if runway is None and cash is not None and net_burn is not None and net_burn > 0:
            runway = cash / net_burn
        gross_margin = pick("gross_margin")
        if gross_margin is not None and abs(gross_margin) <= 1:
            gross_margin *= 100

        return {
            "revenue": revenue,
            "monthly_burn": net_burn,
            "cash_balance": cash,
            "runway_months": runway,
            "gross_margin": gross_margin,
            "growth_rate": pick("growth_rate", "revenue_growth_mom"),
            "headcount": pick("headcount"),
            "payroll": pick("payroll"),
            "opex": pick("opex"),
            "other_costs": pick("other_costs"),
            "arpu": pick("arpu"),
            "churn_rate": pick("churn_rate", "gross_churn_rate"),
        }
    
    def map_decision_to_levers(
        self,
        decision: DecisionContext,
        financials: Dict[str, Any]
    ) -> List[FinancialLever]:
        """
        Map a high-level decision to quantitative financial levers.
        Returns prioritized list of levers with calculated impacts.
        """
        levers = []
        
        for lever_key in decision.levers_available:
            lever_def = self.LEVER_DEFINITIONS.get(lever_key)
            if not lever_def:
                continue
            
            lever = self._calculate_lever_impact(
                lever_key, lever_def, financials, decision
            )
            if lever:
                levers.append(lever)
        
        levers.sort(key=lambda l: abs(l.change_percent), reverse=True)
        
        return levers
    
    def _calculate_lever_impact(
        self,
        lever_key: str,
        lever_def: Dict[str, Any],
        financials: Dict[str, Any],
        decision: DecisionContext
    ) -> Optional[FinancialLever]:
        """Calculate the impact of a specific lever."""
        
        burn = financials.get("monthly_burn")
        runway = financials.get("runway_months")
        revenue = financials.get("revenue") or 0
        payroll = financials.get("payroll")

        # No invented baselines: a lever whose input is unknown is not offered.
        needs = {
            "burn_reduction": burn is not None and burn > 0 and runway is not None,
            "hiring_freeze": payroll is not None and payroll > 0,
            "pricing_increase": revenue > 0,
            "revenue_acceleration": financials.get("growth_rate") is not None,
            "margin_improvement": financials.get("gross_margin") is not None,
        }
        if lever_key in needs and not needs[lever_key]:
            return None

        if lever_key == "burn_reduction":
            current = burn
            reduction_pct = 20
            adjusted = burn * (1 - reduction_pct / 100)
            impact = f"Reduces burn by ${burn * reduction_pct / 100:,.0f}/mo, extends runway by ~{runway * reduction_pct / (100 - reduction_pct):.1f} months"
            
        elif lever_key == "hiring_freeze":
            current = payroll
            reduction_pct = 30
            adjusted = payroll
            impact = f"Saves ${payroll * 0.3:,.0f}/mo in avoided hiring costs"
            
        elif lever_key == "pricing_increase":
            current = revenue
            increase_pct = 15
            adjusted = revenue * (1 + increase_pct / 100) if revenue else 0
            impact = f"Increases revenue by ${revenue * increase_pct / 100:,.0f}/mo, improves margin contribution"
            reduction_pct = increase_pct
            
        elif lever_key == "revenue_acceleration":
            current = financials.get("growth_rate")
            boost_pct = 20
            adjusted = current * (1 + boost_pct / 100)
            impact = f"Accelerates growth from {current:.0f}% to {adjusted:.0f}%, compounds over time"
            reduction_pct = boost_pct
            
        elif lever_key == "margin_improvement":
            current = financials.get("gross_margin")
            improvement = 5
            adjusted = min(current + improvement, 95)
            impact = f"Improves gross margin from {current:.0f}% to {adjusted:.0f}%"
            reduction_pct = improvement
            
        elif lever_key == "fundraise_timing":
            current = 0
            delay_months = -3
            adjusted = delay_months
            impact = f"Delay fundraise by {abs(delay_months)} months to improve terms"
            reduction_pct = delay_months
            
        else:
            return None
        
        return FinancialLever(
            name=lever_def["name"],
            current_value=current,
            adjusted_value=adjusted,
            change_percent=reduction_pct,
            impact_description=impact,
            feasibility=lever_def["feasibility"],
            time_to_implement_months=lever_def["implementation_time"]
        )
    
    # Lever -> real engine parameter. Levers with no engine mapping (hiring
    # freeze without a hiring plan, fundraise timing without an amount) are
    # not simulated.
    LEVER_ENGINE_PARAMS = {
        "Burn Rate Reduction": lambda lever, fin: {"burn_reduction_pct": 20.0},
        "Price Increase": lambda lever, fin: {"pricing_change_pct": 15.0},
        "Revenue Acceleration": lambda lever, fin: {"growth_uplift_pct": (fin.get("growth_rate") or 0) * 0.2},
        "Gross Margin Improvement": lambda lever, fin: {"gross_margin_delta_pct": 5.0},
    }

    def simulation_inputs_missing(self, financials: Dict[str, Any]) -> List[str]:
        missing = []
        if financials.get("cash_balance") is None or financials.get("cash_balance") <= 0:
            missing.append("cash balance")
        if financials.get("monthly_burn") is None:
            missing.append("net burn")
        return missing

    def _engine_outcome(self, financials: Dict[str, Any], params: Dict[str, float], label: List[str], risks: List[str]):
        """One Monte Carlo run of the basic engine (server/simulate/simulation_engine)."""
        from server.api.simulations import resolve_baseline_financials
        from server.simulate.simulation_engine import SimulationInputs, run_monte_carlo

        metrics = {
            "monthly_revenue": financials.get("revenue") or 0,
            "cash_balance": financials.get("cash_balance") or 0,
            "gross_margin": financials.get("gross_margin") or 0,
            "revenue_growth_mom": financials.get("growth_rate") or 0,
            "opex": financials.get("opex") or 0,
            "payroll": financials.get("payroll") or 0,
            "other_costs": financials.get("other_costs") or 0,
            "net_burn": financials.get("monthly_burn") or 0,
        }
        base = resolve_baseline_financials(metrics, None)
        inputs = SimulationInputs(
            baseline_revenue=base["revenue"],
            baseline_growth_rate=base["growth"],
            gross_margin=base["gross_margin"],
            opex=base["opex"],
            payroll=base["payroll"],
            other_costs=base["other_costs"],
            cash_balance=base["cash"],
            n_simulations=self.SIMULATION_RUNS,
            horizon_months=24,
            **params,
        )
        out = run_monte_carlo(inputs, seed=42)
        cash_p50 = out.get("bands", {}).get("cash", {}).get("p50") or []

        def cash_at(month):
            return float(cash_p50[month - 1]) if len(cash_p50) >= month else 0.0

        return SimulationOutcome(
            lever_combination=label,
            runway_p10=float(out["runway"]["p10"]),
            runway_p50=float(out["runway"]["p50"]),
            runway_p90=float(out["runway"]["p90"]),
            survival_12m=float(out["survival"]["12m"]),
            survival_18m=float(out["survival"]["18m"]),
            survival_24m=float(out["survival"]["24m"]),
            cash_at_horizon={"12m": cash_at(12), "18m": cash_at(18), "24m": cash_at(24)},
            risk_factors=risks,
        )

    SIMULATION_RUNS = 500

    async def _run_decision_simulations(
        self,
        decision: DecisionContext,
        levers: List[FinancialLever],
        financials: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[SimulationOutcome]:
        """Run the real Monte Carlo engine for baseline and each mapped lever.

        The old version fabricated every number: baseline survival 70/50/30%,
        P10/P90 as 0.7x/1.3x of a runway, "boosts" of change_percent / 5. With
        the inputs missing, or the engine failing, it now returns no outcomes
        and the response says no simulation was run.
        """
        import asyncio

        self.simulation_status = {"ran": False, "reason": None, "engine": "simulation_engine.run_monte_carlo"}
        missing = self.simulation_inputs_missing(financials)
        if missing:
            self.simulation_status["reason"] = "Missing " + " and ".join(missing)
            return []

        plans = [(["Baseline (no changes)"], {}, ["Current trajectory"])]
        mapped = [l for l in levers if l.name in self.LEVER_ENGINE_PARAMS]
        for lever in mapped[:3]:
            plans.append((
                [lever.name],
                self.LEVER_ENGINE_PARAMS[lever.name](lever, financials),
                [f"Assumes {lever.feasibility} implementation of {lever.name}"],
            ))
        if len(mapped) >= 2:
            combined: Dict[str, float] = {}
            for lever in mapped[:2]:
                combined.update(self.LEVER_ENGINE_PARAMS[lever.name](lever, financials))
            plans.append((
                [l.name for l in mapped[:2]],
                combined,
                ["Execution complexity of multiple initiatives"],
            ))

        def run_all():
            return [self._engine_outcome(financials, params, label, risks) for label, params, risks in plans]

        try:
            outcomes = await asyncio.to_thread(run_all)
        except Exception as e:  # never fall back to invented numbers
            self.logger.warning(f"Decision simulation failed: {e}")
            self.simulation_status["reason"] = "The simulation engine failed"
            return []

        self.simulation_status["ran"] = True
        self.simulation_status["runs_per_scenario"] = self.SIMULATION_RUNS
        return outcomes
    
    def identify_risks(
        self,
        simulation_results: List[SimulationOutcome],
        financials: Dict[str, Any]
    ) -> RiskAnalysis:
        """Identify risks; sensitivity is computed from the real numbers or omitted."""

        riskiest = []
        cash = financials.get("cash_balance")
        net = financials.get("monthly_burn")
        revenue = financials.get("revenue") or 0
        gross_margin = financials.get("gross_margin")
        growth = financials.get("growth_rate")
        churn = financials.get("churn_rate")

        def runway_for(net_burn):
            if cash is None or cash <= 0 or net_burn is None:
                return None
            return cash / net_burn if net_burn > 0 else None

        base_runway = runway_for(net)

        def runway_delta(new_net):
            new = runway_for(new_net)
            if base_runway is None or new is None:
                return "not available"
            return f"{new - base_runway:+.1f} months"

        margin_drop_net = (net + revenue * 0.05) if net is not None else None

        if gross_margin is not None and gross_margin > 75:
            riskiest.append({
                "assumption": f"Gross margin of {gross_margin:.1f}%",
                "risk_level": "High" if gross_margin > 80 else "Medium",
                "impact": f"A 5-point margin drop changes runway by {runway_delta(margin_drop_net)}",
                "mitigation": "Diversify revenue streams, negotiate supplier costs"
            })

        if growth is not None and growth > 20:
            riskiest.append({
                "assumption": f"Growth rate of {growth:.0f}%",
                "risk_level": "Medium",
                "impact": "Growth above 20%/mo rarely persists; re-run the simulation at a lower rate",
                "mitigation": "Build sales pipeline, diversify channels"
            })

        if churn is not None and churn > 3:
            riskiest.append({
                "assumption": f"Churn rate of {churn:.1f}%",
                "risk_level": "Medium",
                "impact": "Each point of monthly churn compounds into lost revenue",
                "mitigation": "Customer success investment, NPS monitoring"
            })

        sensitivity = []
        if gross_margin is not None and net is not None:
            sensitivity.append({
                "variable": "Gross Margin",
                "current": gross_margin,
                "sensitivity": "-5 pts",
                "runway_impact": runway_delta(margin_drop_net),
                "survival_impact": "not simulated",
            })
        if net is not None and net > 0:
            sensitivity.append({
                "variable": "Net Burn",
                "current": net,
                "sensitivity": "+15%",
                "runway_impact": runway_delta(net * 1.15),
                "survival_impact": "not simulated",
            })

        cascade = self._generate_failure_cascade(financials)

        blockers = []
        if not revenue:
            blockers.append("No revenue data - projections are estimates only")
        if cash is None or cash <= 0:
            blockers.append("Missing cash balance - runway calculations uncertain")
        if net is None:
            blockers.append("Missing net burn - no simulation was run")

        return RiskAnalysis(
            riskiest_assumptions=riskiest,
            sensitivity_analysis=sensitivity,
            failure_cascade=cascade,
            confidence_blockers=blockers
        )
    
    def _generate_failure_cascade(self, financials: Dict[str, Any]) -> str:
        """Generate a failure cascade narrative."""
        runway = financials.get("runway_months")
        burn = financials.get("monthly_burn")
        if runway is None or burn is None or burn <= 0:
            return ""

        return (
            f"If revenue growth lags by 20%, monthly burn stays at ${burn:,.0f}, "
            f"runway compresses from {runway:.0f} to {runway * 0.7:.0f} months. "
            f"This forces an emergency raise at worse terms (20-30% more dilution) "
            f"or requires immediate 25% cost cuts to stabilize."
        )
    
    def recommend_action(
        self,
        decision: DecisionContext,
        simulation_results: List[SimulationOutcome],
        risk_analysis: RiskAnalysis,
        financials: Dict[str, Any]
    ) -> ActionRecommendation:
        """Generate the primary recommendation with confidence level."""
        
        if len(simulation_results) <= 1:
            status = getattr(self, "simulation_status", None) or {}
            reason = status.get("reason")
            if status.get("ran"):
                details = "Only the baseline could be simulated; none of the levers map to the simulation engine."
            else:
                details = "No simulation was run" + (f": {reason}." if reason else ".")
            return ActionRecommendation(
                primary_action="Gather more data",
                action_details=details,
                expected_impact="N/A",
                confidence=ConfidenceLevel.LOW,
                confidence_reasoning="Missing critical financial inputs",
                what_would_change_recommendation="Provide revenue, burn, and cash balance data",
                alternative_actions=["Upload financial statements", "Enter baseline metrics manually"]
            )
        
        best_outcome = max(
            simulation_results[1:],
            key=lambda o: o.survival_18m
        )
        
        primary_lever = best_outcome.lever_combination[0]
        survival_improvement = best_outcome.survival_18m - simulation_results[0].survival_18m
        runway_improvement = best_outcome.runway_p50 - simulation_results[0].runway_p50
        
        confidence = ConfidenceLevel.HIGH
        if risk_analysis.confidence_blockers:
            confidence = ConfidenceLevel.LOW
        elif len(risk_analysis.riskiest_assumptions) >= 2:
            confidence = ConfidenceLevel.MEDIUM
        
        confidence_reasons = []
        if confidence == ConfidenceLevel.HIGH:
            confidence_reasons.append("Complete financial data available")
            confidence_reasons.append("Assumptions within normal ranges")
        elif confidence == ConfidenceLevel.MEDIUM:
            confidence_reasons.append("Some assumptions at risk")
            confidence_reasons.append(f"{len(risk_analysis.riskiest_assumptions)} risky assumptions identified")
        else:
            confidence_reasons.extend(risk_analysis.confidence_blockers)
        
        alternatives = [
            o.lever_combination[0] for o in simulation_results[1:4]
            if o.lever_combination[0] != primary_lever
        ]
        
        what_changes = "Recommendation would change if: "
        if risk_analysis.riskiest_assumptions:
            assumption = risk_analysis.riskiest_assumptions[0]
            what_changes += assumption.get("impact", "key assumptions change significantly")
        else:
            what_changes += "growth rate drops below 5% or burn increases by 20%+"
        
        return ActionRecommendation(
            primary_action=f"Implement {primary_lever}",
            action_details=f"This lever provides the best risk-adjusted improvement for your situation. "
                          f"Start implementation immediately for maximum impact.",
            expected_impact=f"{survival_improvement:+.0f} pts simulated survival at 18 months, "
                          f"{runway_improvement:+.1f} months runway (P50)",
            confidence=confidence,
            confidence_reasoning="; ".join(confidence_reasons),
            what_would_change_recommendation=what_changes,
            alternative_actions=alternatives[:2]
        )
    
    def _format_response(
        self,
        decision: DecisionContext,
        levers: List[FinancialLever],
        simulations: List[SimulationOutcome],
        risks: RiskAnalysis,
        recommendation: ActionRecommendation,
        ckb: CompanyKnowledgeBase
    ) -> AgentResponse:
        """Format the complete response for the user."""
        
        findings = [
            f"Decision: {decision.core_decision}",
            f"Analysis timeframe: {decision.timeframe_months} months",
        ]
        
        if simulations and len(simulations) > 1:
            baseline = simulations[0]
            best = max(simulations[1:], key=lambda s: s.survival_18m)
            findings.append(
                f"Baseline survival (18m): {baseline.survival_18m:.0f}% → "
                f"With {best.lever_combination[0]}: {best.survival_18m:.0f}%"
            )
        
        else:
            status = getattr(self, "simulation_status", None) or {}
            if not status.get("ran"):
                findings.append(
                    "No simulation was run"
                    + (f" ({status['reason']})" if status.get("reason") else "")
                )

        findings.append(f"Recommendation: {recommendation.primary_action}")
        findings.append(f"Confidence: {recommendation.confidence.value.upper()}")
        
        assumptions = [
            f"Assumes {r['assumption']}" for r in risks.riskiest_assumptions[:3]
        ]
        
        risk_list = [
            f"{r['assumption']}: {r['risk_level']} risk"
            for r in risks.riskiest_assumptions
        ]
        if risks.failure_cascade:
            risk_list.append(f"Cascade risk: {risks.failure_cascade[:100]}...")
        
        next_questions = [
            "Would you like me to run a more detailed simulation with different assumptions?",
            "Should I create a scenario comparing multiple lever combinations?",
            "Do you want to see the sensitivity analysis in more detail?"
        ]
        
        decision_advisor_output = {
            "decision_context": {
                "type": decision.decision_type.value,
                "core_decision": decision.core_decision,
                "target": decision.target_outcome,
                "timeframe_months": decision.timeframe_months,
                "constraints": decision.constraints
            },
            "levers": [
                {
                    "name": lever.name,
                    "current_value": lever.current_value,
                    "adjusted_value": lever.adjusted_value,
                    "change_percent": lever.change_percent,
                    "impact": lever.impact_description,
                    "feasibility": lever.feasibility,
                    "time_to_implement": lever.time_to_implement_months
                }
                for lever in levers
            ],
            "simulations": [
                {
                    "scenario": f"Scenario {i+1}",
                    "levers_applied": sim.lever_combination,
                    "runway": {
                        "p10": sim.runway_p10,
                        "p50": sim.runway_p50,
                        "p90": sim.runway_p90
                    },
                    "survival": {
                        "12m": sim.survival_12m,
                        "18m": sim.survival_18m,
                        "24m": sim.survival_24m
                    },
                    "risks": sim.risk_factors
                }
                for i, sim in enumerate(simulations)
            ],
            "simulation_status": getattr(self, "simulation_status", None) or {"ran": False, "reason": None},
            "risk_analysis": {
                "riskiest_assumptions": risks.riskiest_assumptions,
                "sensitivity": risks.sensitivity_analysis,
                "failure_cascade": risks.failure_cascade
            },
            "recommendation": {
                "primary_action": recommendation.primary_action,
                "details": recommendation.action_details,
                "expected_impact": recommendation.expected_impact,
                "confidence": recommendation.confidence.value,
                "confidence_reasoning": recommendation.confidence_reasoning,
                "alternatives": recommendation.alternative_actions,
                "what_changes": recommendation.what_would_change_recommendation
            }
        }
        
        return AgentResponse(
            agent_type=AgentType.DECISION_ADVISOR,
            findings=findings,
            structured_output=decision_advisor_output,
            assumptions=assumptions,
            risks=risk_list,
            next_questions=next_questions,
            confidence=recommendation.confidence,
            decision_advisor_output=decision_advisor_output
        )


def is_decision_query(query: str) -> bool:
    """Check if a query is decision-oriented and should use the Decision Advisor."""
    decision_indicators = [
        r"how.*can.*i", r"what.*should.*i", r"how.*do.*i",
        r"extend.*runway", r"reduce.*burn", r"increase.*revenue",
        r"delay.*fundrais", r"when.*should", r"what.*if",
        r"should.*i", r"is.*it.*worth", r"compare.*options",
        r"what.*happens", r"simulate", r"scenario",
        r"survive", r"last.*longer", r"improve.*position"
    ]
    
    query_lower = query.lower()
    for pattern in decision_indicators:
        if re.search(pattern, query_lower):
            return True
    return False
