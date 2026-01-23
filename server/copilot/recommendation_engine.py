"""
Recommendation Engine for Adaptive Guidance.

Analyzes simulation outcomes vs user goals and benchmarks to propose
proactive next-step suggestions after each simulation.
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class RecommendationType(str, Enum):
    REDUCE_BURN = "reduce_burn"
    INCREASE_REVENUE = "increase_revenue"
    DELAY_HIRING = "delay_hiring"
    ADJUST_PRICING = "adjust_pricing"
    FUNDRAISE = "fundraise"
    REDUCE_CHURN = "reduce_churn"
    EXTEND_RUNWAY = "extend_runway"
    IMPROVE_MARGINS = "improve_margins"
    ACCELERATE_GROWTH = "accelerate_growth"
    OPTIMIZE_CAC = "optimize_cac"


@dataclass
class UserGoals:
    """User's target goals for simulation outcomes."""
    target_runway_months: int = 18
    target_survival_rate: float = 80.0
    target_growth_rate: float = 10.0
    min_cash_buffer: float = 500000.0
    max_dilution_pct: float = 25.0


@dataclass
class Recommendation:
    """A single recommendation with context."""
    rec_type: RecommendationType
    priority: int
    text: str
    rationale: str
    action_prompt: str
    estimated_impact: Dict[str, Any]
    context_data: Dict[str, Any]


class RecommendationEngine:
    """
    Rule-based recommendation engine that analyzes simulation results
    and proposes next steps tailored to user goals.
    """
    
    BENCHMARKS = {
        "saas": {
            "typical_burn_multiple": 1.5,
            "typical_gross_margin": 0.75,
            "typical_churn_monthly": 0.03,
            "typical_growth_rate": 0.08,
            "typical_cac_payback_months": 12,
        },
        "marketplace": {
            "typical_burn_multiple": 2.0,
            "typical_gross_margin": 0.40,
            "typical_churn_monthly": 0.05,
            "typical_growth_rate": 0.10,
            "typical_cac_payback_months": 18,
        },
        "ecommerce": {
            "typical_burn_multiple": 1.8,
            "typical_gross_margin": 0.35,
            "typical_churn_monthly": 0.08,
            "typical_growth_rate": 0.06,
            "typical_cac_payback_months": 6,
        },
        "fintech": {
            "typical_burn_multiple": 2.5,
            "typical_gross_margin": 0.60,
            "typical_churn_monthly": 0.02,
            "typical_growth_rate": 0.12,
            "typical_cac_payback_months": 15,
        },
    }
    
    THRESHOLDS = {
        "critical_runway_months": 6,
        "warning_runway_months": 9,
        "healthy_runway_months": 12,
        "target_runway_months": 18,
        "critical_survival_rate": 50,
        "warning_survival_rate": 70,
        "healthy_survival_rate": 85,
        "high_burn_multiple": 3.0,
        "low_gross_margin": 0.50,
        "high_churn_rate": 0.05,
    }
    
    def __init__(self, industry: str = "saas"):
        self.industry = industry
        self.benchmarks = self.BENCHMARKS.get(industry.lower(), self.BENCHMARKS["saas"])
    
    def analyze(
        self,
        simulation_results: Dict[str, Any],
        current_financials: Optional[Dict[str, Any]] = None,
        user_goals: Optional[UserGoals] = None,
        simulation_params: Optional[Dict[str, Any]] = None,
    ) -> List[Recommendation]:
        """
        Analyze simulation outcomes and generate prioritized recommendations.
        
        Args:
            simulation_results: Output from Monte Carlo simulation
            current_financials: Current financial metrics if available
            user_goals: User's target goals (defaults to standard goals)
            simulation_params: Parameters used in the simulation
            
        Returns:
            List of prioritized recommendations
        """
        goals = user_goals or UserGoals()
        recommendations = []
        
        runway_months = simulation_results.get("runway_months", 0)
        survival_rate = simulation_results.get("survival_rate", 0)
        final_cash = simulation_results.get("final_cash", 0)
        confidence_intervals = simulation_results.get("confidence_intervals", {})
        
        runway_gap = goals.target_runway_months - runway_months
        survival_gap = goals.target_survival_rate - survival_rate
        
        if runway_months < self.THRESHOLDS["critical_runway_months"]:
            recommendations.append(self._critical_runway_recommendation(
                runway_months, goals.target_runway_months, simulation_params
            ))
            recommendations.append(self._fundraise_recommendation(
                runway_months, final_cash, "urgent"
            ))
        elif runway_months < self.THRESHOLDS["warning_runway_months"]:
            recommendations.append(self._warning_runway_recommendation(
                runway_months, goals.target_runway_months, simulation_params
            ))
        elif runway_gap > 0:
            recommendations.append(self._extend_runway_recommendation(
                runway_months, goals.target_runway_months, simulation_params
            ))
        
        if survival_rate < self.THRESHOLDS["critical_survival_rate"]:
            recommendations.append(self._critical_survival_recommendation(
                survival_rate, goals.target_survival_rate
            ))
        elif survival_rate < self.THRESHOLDS["warning_survival_rate"]:
            recommendations.append(self._warning_survival_recommendation(
                survival_rate, goals.target_survival_rate
            ))
        
        if current_financials:
            burn_multiple = current_financials.get("burn_multiple", 0)
            gross_margin = current_financials.get("gross_margin", 0)
            churn_rate = current_financials.get("churn_rate", 0)
            growth_rate = current_financials.get("growth_rate", 0)
            
            if burn_multiple > self.THRESHOLDS["high_burn_multiple"]:
                recommendations.append(self._high_burn_recommendation(burn_multiple))
            
            if gross_margin < self.THRESHOLDS["low_gross_margin"]:
                recommendations.append(self._low_margin_recommendation(gross_margin))
            
            if churn_rate > self.THRESHOLDS["high_churn_rate"]:
                recommendations.append(self._high_churn_recommendation(churn_rate))
            
            if growth_rate < self.benchmarks["typical_growth_rate"] * 0.5:
                recommendations.append(self._low_growth_recommendation(growth_rate))
        
        if simulation_params:
            recommendations.extend(self._suggest_alternative_scenarios(
                simulation_results, simulation_params, goals
            ))
        
        recommendations.sort(key=lambda r: r.priority, reverse=True)
        return recommendations[:5]
    
    def _critical_runway_recommendation(
        self, 
        current_runway: float, 
        target_runway: float,
        params: Optional[Dict[str, Any]]
    ) -> Recommendation:
        burn_cut_needed = ((target_runway - current_runway) / target_runway) * 100 if target_runway > 0 else 25
        burn_cut_pct = min(max(int(burn_cut_needed), 15), 40)
        
        return Recommendation(
            rec_type=RecommendationType.REDUCE_BURN,
            priority=100,
            text=f"Your runway is critically short at {current_runway:.0f} months. Consider cutting burn by {burn_cut_pct}% to reach your {target_runway}-month target.",
            rationale=f"With only {current_runway:.0f} months of runway, you have limited time to course-correct. Most investors want to see 12+ months runway before engaging.",
            action_prompt=f"Try: 'What if we cut burn by {burn_cut_pct}%?'",
            estimated_impact={"runway_increase_months": burn_cut_pct * 0.15 * current_runway},
            context_data={"current_runway": current_runway, "target_runway": target_runway}
        )
    
    def _warning_runway_recommendation(
        self,
        current_runway: float,
        target_runway: float,
        params: Optional[Dict[str, Any]]
    ) -> Recommendation:
        burn_cut_pct = 15
        
        return Recommendation(
            rec_type=RecommendationType.REDUCE_BURN,
            priority=80,
            text=f"Your runway of {current_runway:.0f} months is below the healthy threshold. Consider reducing burn or accelerating revenue.",
            rationale="A runway of 9-12 months leaves limited buffer for fundraising, which typically takes 4-6 months.",
            action_prompt="Try: 'What if we cut burn by 15%?' or 'What if we increase prices by 10%?'",
            estimated_impact={"runway_increase_months": 2},
            context_data={"current_runway": current_runway}
        )
    
    def _extend_runway_recommendation(
        self,
        current_runway: float,
        target_runway: float,
        params: Optional[Dict[str, Any]]
    ) -> Recommendation:
        gap = target_runway - current_runway
        
        return Recommendation(
            rec_type=RecommendationType.EXTEND_RUNWAY,
            priority=50,
            text=f"You're {gap:.0f} months short of your {target_runway}-month runway target. Consider a combination of burn reduction and revenue acceleration.",
            rationale=f"Current runway of {current_runway:.0f} months is reasonable but falls short of your stated goal.",
            action_prompt="Try: 'What if we cut burn by 10% and increase revenue growth by 5%?'",
            estimated_impact={"potential_runway_gain": gap},
            context_data={"current_runway": current_runway, "target_runway": target_runway}
        )
    
    def _critical_survival_recommendation(
        self,
        survival_rate: float,
        target_rate: float
    ) -> Recommendation:
        return Recommendation(
            rec_type=RecommendationType.FUNDRAISE,
            priority=95,
            text=f"Your survival probability of {survival_rate:.0f}% is critically low. Immediate action required.",
            rationale="A survival rate below 50% indicates high probability of running out of cash. This requires urgent intervention.",
            action_prompt="Try: 'What if we raise $2M now?' or 'What if we cut burn by 30%?'",
            estimated_impact={"survival_rate_improvement": 30},
            context_data={"current_survival": survival_rate}
        )
    
    def _warning_survival_recommendation(
        self,
        survival_rate: float,
        target_rate: float
    ) -> Recommendation:
        return Recommendation(
            rec_type=RecommendationType.EXTEND_RUNWAY,
            priority=70,
            text=f"Your survival probability of {survival_rate:.0f}% is below healthy levels. Consider risk mitigation strategies.",
            rationale="A survival rate between 50-70% indicates meaningful risk that should be addressed.",
            action_prompt="Try: 'What if we delay hiring by 3 months?' or 'Reduce burn by 20%'",
            estimated_impact={"survival_rate_improvement": 15},
            context_data={"current_survival": survival_rate}
        )
    
    def _fundraise_recommendation(
        self,
        runway: float,
        cash: float,
        urgency: str = "normal"
    ) -> Recommendation:
        priority = 90 if urgency == "urgent" else 60
        amount = max(1.0, cash * 2 / 1000000) if cash > 0 else 2.0
        
        return Recommendation(
            rec_type=RecommendationType.FUNDRAISE,
            priority=priority,
            text=f"Consider raising ${amount:.1f}M to extend runway and provide buffer for growth initiatives.",
            rationale=f"With {runway:.0f} months runway, fundraising now gives you negotiating leverage before you're in a distressed position.",
            action_prompt=f"Try: 'What if we raise ${amount:.1f}M in month 3?'",
            estimated_impact={"runway_increase_months": amount * 4},
            context_data={"suggested_raise": amount}
        )
    
    def _high_burn_recommendation(self, burn_multiple: float) -> Recommendation:
        return Recommendation(
            rec_type=RecommendationType.REDUCE_BURN,
            priority=75,
            text=f"Your burn multiple of {burn_multiple:.1f}x is high. Industry benchmark is {self.benchmarks['typical_burn_multiple']:.1f}x.",
            rationale="A high burn multiple means you're spending too much relative to new revenue generated. This signals inefficient growth.",
            action_prompt="Try: 'What if we cut marketing spend by 20%?' or 'Delay hiring by 3 months'",
            estimated_impact={"burn_multiple_reduction": burn_multiple - self.benchmarks['typical_burn_multiple']},
            context_data={"current_burn_multiple": burn_multiple}
        )
    
    def _low_margin_recommendation(self, gross_margin: float) -> Recommendation:
        return Recommendation(
            rec_type=RecommendationType.IMPROVE_MARGINS,
            priority=65,
            text=f"Your gross margin of {gross_margin*100:.0f}% is below industry average of {self.benchmarks['typical_gross_margin']*100:.0f}%.",
            rationale="Low gross margins limit your ability to invest in growth and extend runway. Consider pricing or cost structure changes.",
            action_prompt="Try: 'What if we increase prices by 15%?'",
            estimated_impact={"margin_improvement_pct": (self.benchmarks['typical_gross_margin'] - gross_margin) * 100},
            context_data={"current_margin": gross_margin}
        )
    
    def _high_churn_recommendation(self, churn_rate: float) -> Recommendation:
        return Recommendation(
            rec_type=RecommendationType.REDUCE_CHURN,
            priority=70,
            text=f"Your monthly churn of {churn_rate*100:.1f}% is above the industry average of {self.benchmarks['typical_churn_monthly']*100:.1f}%.",
            rationale="High churn erodes your revenue base and increases CAC payback. Focus on retention before scaling acquisition.",
            action_prompt="Try: 'What if we reduce churn by 2%?'",
            estimated_impact={"revenue_retention_improvement": (churn_rate - self.benchmarks['typical_churn_monthly']) * 12 * 100},
            context_data={"current_churn": churn_rate}
        )
    
    def _low_growth_recommendation(self, growth_rate: float) -> Recommendation:
        return Recommendation(
            rec_type=RecommendationType.ACCELERATE_GROWTH,
            priority=55,
            text=f"Your growth rate of {growth_rate*100:.1f}% is significantly below industry benchmark of {self.benchmarks['typical_growth_rate']*100:.0f}%.",
            rationale="Low growth makes it harder to outrun burn and reduces investor attractiveness.",
            action_prompt="Try: 'What if we increase growth rate by 5%?'",
            estimated_impact={"revenue_increase_pct": self.benchmarks['typical_growth_rate'] * 100},
            context_data={"current_growth": growth_rate}
        )
    
    def _suggest_alternative_scenarios(
        self,
        results: Dict[str, Any],
        params: Dict[str, Any],
        goals: UserGoals
    ) -> List[Recommendation]:
        """Suggest alternative scenarios based on what wasn't tried."""
        alternatives = []
        
        if not params.get("burn_reduction_pct"):
            alternatives.append(Recommendation(
                rec_type=RecommendationType.REDUCE_BURN,
                priority=40,
                text="You haven't explored burn reduction scenarios yet.",
                rationale="Burn reduction is often the fastest path to extending runway.",
                action_prompt="Try: 'What if we cut burn by 20%?'",
                estimated_impact={},
                context_data={}
            ))
        
        if not params.get("fundraise_amount"):
            alternatives.append(Recommendation(
                rec_type=RecommendationType.FUNDRAISE,
                priority=35,
                text="Consider exploring fundraising scenarios to understand your options.",
                rationale="Understanding the impact of different raise amounts helps with planning.",
                action_prompt="Try: 'What if we raise $1.5M in month 6?'",
                estimated_impact={},
                context_data={}
            ))
        
        if not params.get("price_change_pct"):
            alternatives.append(Recommendation(
                rec_type=RecommendationType.ADJUST_PRICING,
                priority=30,
                text="You haven't tested pricing changes yet.",
                rationale="Even small price increases can significantly impact unit economics.",
                action_prompt="Try: 'What if we increase prices by 10%?'",
                estimated_impact={},
                context_data={}
            ))
        
        return alternatives[:2]
    
    def format_recommendations_for_chat(
        self,
        recommendations: List[Recommendation]
    ) -> str:
        """Format recommendations as a chat-friendly message."""
        if not recommendations:
            return "Your scenario looks healthy! No immediate concerns detected."
        
        lines = ["**Suggested Next Steps:**\n"]
        
        for i, rec in enumerate(recommendations, 1):
            lines.append(f"{i}. {rec.text}")
            lines.append(f"   *{rec.action_prompt}*\n")
        
        return "\n".join(lines)
    
    def get_recommendation_chart_data(
        self,
        recommendations: List[Recommendation]
    ) -> Dict[str, Any]:
        """Generate chart data for visualizing recommendation impacts."""
        return {
            "type": "recommendation_impact",
            "data": [
                {
                    "type": rec.rec_type.value,
                    "priority": rec.priority,
                    "label": rec.rec_type.value.replace("_", " ").title(),
                    "impact": rec.estimated_impact,
                }
                for rec in recommendations
            ]
        }
