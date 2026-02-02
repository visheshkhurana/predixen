"""
Strategy Agent for Fund Flow Copilot.

CEO advisor + product/GTM strategist that helps discuss business ideas,
propose new verticals, design GTM, and turn analysis into decisions.
"""
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from .base import (
    BaseAgent, AgentResponse, AgentType,
    CompanyKnowledgeBase, ConfidenceLevel
)

logger = logging.getLogger(__name__)


from server.copilot.grounding_rules import get_grounding_prompt_addition

STRATEGY_SYSTEM_PROMPT = """You are Fund Flow Strategy Agent: a CEO advisor + product/GTM strategist.
Your job: help the user discuss business ideas, propose new verticals, design GTM, and turn analysis into decisions.

Rules:
- Ground strategy in constraints (financial reality, product scope, market facts).
- Provide options and tradeoffs, not only one "answer".
- Be execution-oriented: milestones, first steps, risks, owner suggestions.
- Never hallucinate factual claims about the company; rely on CKB + tool outputs.

Deliverables:
1) Findings
2) Strategy Options (2–4) with pros/cons, effort, risk
3) Recommended plan (ranked) + 30/60/90 day actions
4) Vertical expansion ideas (with rationale)
5) Assumptions & Risks
6) Next Questions (≤3)
""" + get_grounding_prompt_addition()


@dataclass
class StrategyOption:
    """A strategic option with tradeoffs."""
    name: str
    description: str
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)
    effort: str = "medium"
    risk: str = "medium"
    timeline: str = ""
    first_steps: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "pros": self.pros,
            "cons": self.cons,
            "effort": self.effort,
            "risk": self.risk,
            "timeline": self.timeline,
            "first_steps": self.first_steps
        }


@dataclass
class VerticalOpportunity:
    """Vertical expansion opportunity."""
    name: str
    description: str
    icp_overlap: str = "medium"
    data_advantage: str = "low"
    distribution_reuse: str = "medium"
    compliance_cost: str = "low"
    market_size: str = ""
    why_now: str = ""
    score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "adjacency_score": {
                "icp_overlap": self.icp_overlap,
                "data_advantage": self.data_advantage,
                "distribution_reuse": self.distribution_reuse,
                "compliance_cost": self.compliance_cost
            },
            "market_size": self.market_size,
            "why_now": self.why_now,
            "score": self.score
        }


@dataclass
class ExecutionPlan:
    """30/60/90 day execution plan."""
    day_30: List[str] = field(default_factory=list)
    day_60: List[str] = field(default_factory=list)
    day_90: List[str] = field(default_factory=list)
    key_metrics: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "day_30": self.day_30,
            "day_60": self.day_60,
            "day_90": self.day_90,
            "key_metrics": self.key_metrics
        }


@dataclass
class StrategyOutput:
    """Complete strategy output."""
    business_diagnosis: Dict[str, Any] = field(default_factory=dict)
    options: List[StrategyOption] = field(default_factory=list)
    recommended: Optional[StrategyOption] = None
    verticals: List[VerticalOpportunity] = field(default_factory=list)
    execution_plan: Optional[ExecutionPlan] = None
    risks: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "business_diagnosis": self.business_diagnosis,
            "options": [o.to_dict() for o in self.options],
            "recommended": self.recommended.to_dict() if self.recommended else None,
            "verticals": [v.to_dict() for v in self.verticals],
            "execution_plan": self.execution_plan.to_dict() if self.execution_plan else None,
            "risks": self.risks
        }


class StrategyAgent(BaseAgent):
    """
    Strategy Agent that provides business strategy,
    GTM planning, and vertical expansion recommendations.
    
    Uses Claude Sonnet via LLM Router for strategy and planning.
    """
    
    def __init__(self, llm_router=None):
        super().__init__(AgentType.STRATEGY, llm_router)
    
    async def process(
        self, 
        query: str, 
        ckb: CompanyKnowledgeBase,
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Process strategy request."""
        
        output = StrategyOutput()
        findings = []
        
        output.business_diagnosis = self._diagnose_business(ckb, context)
        findings.append(f"Business model: {output.business_diagnosis.get('business_model', 'Unknown')}")
        
        output.options = self._generate_strategy_options(ckb, context, query)
        findings.append(f"Generated {len(output.options)} strategic options")
        
        if output.options:
            output.recommended = self._rank_options(output.options, ckb)
            if output.recommended:
                findings.append(f"Recommended: {output.recommended.name}")
        
        output.verticals = self._identify_vertical_opportunities(ckb, context)
        if output.verticals:
            findings.append(f"Identified {len(output.verticals)} vertical expansion opportunities")
        
        output.execution_plan = self._create_execution_plan(output.recommended, ckb)
        
        output.risks = self._identify_strategic_risks(ckb, context)
        
        assumptions = self._identify_assumptions(output, context)
        
        next_questions = []
        if not ckb.financials.get("runway_months"):
            next_questions.append("What is your current runway?")
        if not ckb.strategy.get("moat"):
            next_questions.append("What is your key defensibility or moat?")
        if not output.business_diagnosis.get("revenue_model"):
            next_questions.append("How do you charge customers (subscription, usage, transaction)?")
        
        confidence = self._assess_confidence(ckb, context)
        
        llm_insights = await self._generate_llm_insights(query, output, ckb, context)
        if llm_insights:
            findings.append(llm_insights)
        
        return AgentResponse(
            agent_type=AgentType.STRATEGY,
            findings=findings,
            structured_output={
                "strategy": output.to_dict(),
                "recommendations": [output.recommended.to_dict()] if output.recommended else []
            },
            assumptions=assumptions,
            risks=output.risks,
            next_questions=next_questions[:3],
            confidence=confidence,
            raw_response=llm_insights or ""
        )
    
    def _diagnose_business(
        self, 
        ckb: CompanyKnowledgeBase, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Diagnose current business model."""
        
        diagnosis = {
            "company_name": ckb.company_name,
            "industry": ckb.industry or "Unknown",
            "stage": ckb.stage or "Unknown",
            "value_proposition": ckb.strategy.get("value_proposition", "To be defined"),
            "business_model": self._infer_business_model(ckb),
            "revenue_model": ckb.strategy.get("revenue_model", "To be defined"),
            "buyer_vs_user": ckb.strategy.get("buyer_user", "To be researched"),
            "moat": ckb.strategy.get("moat", "To be identified"),
            "defensibility": ckb.strategy.get("defensibility", [])
        }
        
        if ckb.financials:
            fin = ckb.financials
            revenue = (fin.get("pnl") or {}).get("revenue")
            if isinstance(revenue, (int, float)):
                diagnosis["current_revenue"] = self.format_currency(revenue, ckb.currency)
            gross_margin = (fin.get("pnl") or {}).get("gross_margin")
            if isinstance(gross_margin, (int, float)):
                diagnosis["gross_margin"] = f"{gross_margin:.1f}%"
            runway = (fin.get("cashflow") or {}).get("runway_months")
            if isinstance(runway, (int, float)):
                diagnosis["runway"] = f"{runway:.0f} months"
        
        return diagnosis
    
    def _infer_business_model(self, ckb: CompanyKnowledgeBase) -> str:
        """Infer business model from available data."""
        
        industry = (ckb.industry or "").lower()
        
        if any(kw in industry for kw in ["saas", "software", "platform"]):
            return "SaaS / Subscription"
        elif any(kw in industry for kw in ["marketplace", "network"]):
            return "Marketplace"
        elif any(kw in industry for kw in ["fintech", "payment"]):
            return "Fintech / Transaction-based"
        elif any(kw in industry for kw in ["ecommerce", "retail"]):
            return "E-commerce"
        elif any(kw in industry for kw in ["agtech", "agriculture"]):
            return "AgTech / B2B Platform"
        
        return "To be defined"
    
    def _generate_strategy_options(
        self, 
        ckb: CompanyKnowledgeBase, 
        context: Dict[str, Any],
        query: str
    ) -> List[StrategyOption]:
        """Generate strategic options based on context."""
        
        options = []
        
        runway_raw = ckb.financials.get("cashflow", {}).get("runway_months", 18)
        # Handle case where runway might be a dict (e.g., {"value": 18}) or numeric
        if isinstance(runway_raw, dict):
            runway = runway_raw.get("value", 18)
        else:
            runway = runway_raw
        
        # Ensure runway is numeric for comparison
        if runway and isinstance(runway, (int, float)) and runway < 12:
            options.append(StrategyOption(
                name="Focus & Extend Runway",
                description="Cut non-essential spend, focus on core product-market fit",
                pros=[
                    "Extends runway for more attempts at growth",
                    "Forces prioritization and focus",
                    "Demonstrates discipline to future investors"
                ],
                cons=[
                    "May slow growth and hurt morale",
                    "Could signal weakness to market",
                    "Risk of falling behind competitors"
                ],
                effort="low",
                risk="low",
                timeline="Immediate - 30 days",
                first_steps=[
                    "Audit all expenses, identify 20-30% cuts",
                    "Prioritize top 3 growth initiatives only",
                    "Communicate clearly with team"
                ]
            ))
        
        options.append(StrategyOption(
            name="Double Down on Core ICP",
            description="Concentrate resources on winning the ideal customer segment",
            pros=[
                "Faster path to product-market fit signals",
                "Better unit economics through specialization",
                "Stronger positioning and word-of-mouth"
            ],
            cons=[
                "Limits addressable market near-term",
                "Risk if ICP definition is wrong",
                "May miss adjacent opportunities"
            ],
            effort="medium",
            risk="medium",
            timeline="60-90 days to see results",
            first_steps=[
                "Define and document ICP precisely",
                "Align product roadmap to ICP needs",
                "Focus sales/marketing on ICP only"
            ]
        ))
        
        options.append(StrategyOption(
            name="Expand to Adjacent Vertical",
            description="Leverage existing capabilities in a related market",
            pros=[
                "Larger addressable market",
                "Diversifies revenue risk",
                "May have data/distribution advantages"
            ],
            cons=[
                "Divides focus and resources",
                "Requires learning new domain",
                "Execution risk"
            ],
            effort="high",
            risk="high",
            timeline="6-12 months to meaningful revenue",
            first_steps=[
                "Validate demand with 10 potential customers",
                "Assess product gap vs. adjacency needs",
                "Build minimal viable expansion"
            ]
        ))
        
        if "gtm" in query.lower() or "go to market" in query.lower():
            options.append(StrategyOption(
                name="Product-Led Growth (PLG)",
                description="Enable users to try and adopt product before sales engagement",
                pros=[
                    "Lower CAC through self-serve",
                    "Faster sales cycles",
                    "Viral/referral potential"
                ],
                cons=[
                    "Requires product investment",
                    "May not work for complex products",
                    "Need to balance with enterprise sales"
                ],
                effort="high",
                risk="medium",
                timeline="3-6 months to implement",
                first_steps=[
                    "Define free/trial experience",
                    "Instrument product analytics",
                    "Build onboarding flow"
                ]
            ))
        
        return options
    
    def _rank_options(
        self, 
        options: List[StrategyOption], 
        ckb: CompanyKnowledgeBase
    ) -> Optional[StrategyOption]:
        """Rank options and return recommended strategy."""
        
        runway_raw = ckb.financials.get("cashflow", {}).get("runway_months", 18)
        # Handle case where runway might be a dict
        if isinstance(runway_raw, dict):
            runway = runway_raw.get("value", 18)
        else:
            runway = runway_raw
        
        if runway and isinstance(runway, (int, float)) and runway < 12:
            for opt in options:
                if opt.effort == "low" and opt.risk == "low":
                    return opt
        
        for opt in options:
            if opt.effort == "medium" and opt.risk == "medium":
                return opt
        
        return options[0] if options else None
    
    def _identify_vertical_opportunities(
        self, 
        ckb: CompanyKnowledgeBase, 
        context: Dict[str, Any]
    ) -> List[VerticalOpportunity]:
        """Identify vertical expansion opportunities."""
        
        verticals = []
        industry = (ckb.industry or "").lower()
        
        if "agtech" in industry or "agriculture" in industry:
            verticals.append(VerticalOpportunity(
                name="Food Processing & Manufacturing",
                description="Extend supply chain visibility to processing facilities",
                icp_overlap="high",
                data_advantage="medium",
                distribution_reuse="high",
                compliance_cost="medium",
                market_size="Large - $50B+",
                why_now="Food safety regulations tightening, traceability demand",
                score=0.75
            ))
            
            verticals.append(VerticalOpportunity(
                name="Agricultural Lending / Trade Finance",
                description="Leverage transaction data for credit decisioning",
                icp_overlap="high",
                data_advantage="high",
                distribution_reuse="high",
                compliance_cost="high",
                market_size="Large - $100B+",
                why_now="Fintech disruption in agricultural finance",
                score=0.70
            ))
        
        if "fintech" in industry or "saas" in industry:
            verticals.append(VerticalOpportunity(
                name="Enterprise/Large Accounts",
                description="Move upmarket to larger customers",
                icp_overlap="medium",
                data_advantage="low",
                distribution_reuse="medium",
                compliance_cost="medium",
                market_size="Large",
                why_now="SMB/mid-market saturating, enterprise has budget",
                score=0.65
            ))
        
        verticals.sort(key=lambda x: x.score, reverse=True)
        
        return verticals[:3]
    
    def _create_execution_plan(
        self, 
        recommended: Optional[StrategyOption],
        ckb: CompanyKnowledgeBase
    ) -> ExecutionPlan:
        """Create 30/60/90 day execution plan."""
        
        plan = ExecutionPlan()
        
        if recommended:
            plan.day_30 = recommended.first_steps[:3] if recommended.first_steps else [
                "Align leadership on strategy",
                "Communicate to team",
                "Begin first initiative"
            ]
            
            plan.day_60 = [
                "Execute core initiatives",
                "Measure initial progress",
                "Iterate based on learnings"
            ]
            
            plan.day_90 = [
                "Assess results vs. targets",
                "Decide on next phase",
                "Report to stakeholders"
            ]
        else:
            plan.day_30 = ["Define strategy", "Set goals", "Align team"]
            plan.day_60 = ["Execute", "Measure", "Learn"]
            plan.day_90 = ["Assess", "Iterate", "Scale"]
        
        plan.key_metrics = [
            "Revenue growth rate",
            "Customer acquisition cost (CAC)",
            "Net revenue retention (NRR)",
            "Burn multiple"
        ]
        
        return plan
    
    def _identify_strategic_risks(
        self, 
        ckb: CompanyKnowledgeBase, 
        context: Dict[str, Any]
    ) -> List[str]:
        """Identify strategic risks."""
        
        risks = []
        
        if not ckb.strategy.get("moat"):
            risks.append("No clear moat/defensibility identified - risk of commoditization")
        
        runway_raw = ckb.financials.get("cashflow", {}).get("runway_months")
        # Handle case where runway might be a dict
        if isinstance(runway_raw, dict):
            runway = runway_raw.get("value")
        else:
            runway = runway_raw
        
        if runway and isinstance(runway, (int, float)) and runway < 18:
            risks.append(f"Limited runway ({runway:.0f} months) constrains strategic options")
        
        if not ckb.icp:
            risks.append("ICP not clearly defined - risk of unfocused go-to-market")
        
        risks.append("Strategy recommendations based on limited data - validate with customers")
        
        return risks
    
    def _identify_assumptions(
        self, 
        output: StrategyOutput, 
        context: Dict[str, Any]
    ) -> List[str]:
        """Identify assumptions made in strategy recommendations."""
        
        assumptions = []
        
        assumptions.append("Strategy based on available financial and market data")
        
        if not context.get("truth_scan"):
            assumptions.append("Financial metrics not validated through Truth Scan")
        
        assumptions.append("Market conditions and competitive landscape may change")
        
        if output.verticals:
            assumptions.append("Vertical opportunities require customer validation")
        
        return assumptions
    
    def _assess_confidence(
        self, 
        ckb: CompanyKnowledgeBase, 
        context: Dict[str, Any]
    ) -> ConfidenceLevel:
        """Assess confidence level in recommendations."""
        
        data_points = 0
        
        if ckb.financials:
            data_points += 2
        if ckb.icp:
            data_points += 1
        if ckb.competitors:
            data_points += 1
        if context.get("truth_scan"):
            data_points += 2
        
        if data_points >= 4:
            return ConfidenceLevel.HIGH
        elif data_points >= 2:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW
    
    async def _generate_llm_insights(
        self,
        query: str,
        output: "StrategyOutput",
        ckb: CompanyKnowledgeBase,
        context: Dict[str, Any]
    ) -> Optional[str]:
        """Generate LLM-powered strategic insights using Claude Sonnet."""
        if not self.llm_router:
            return None
        
        strategy_summary = []
        if output.business_diagnosis:
            diag = output.business_diagnosis
            if diag.get("stage"):
                strategy_summary.append(f"Stage: {diag.get('stage')}")
            if diag.get("revenue_model"):
                strategy_summary.append(f"Revenue Model: {diag.get('revenue_model')}")
            if diag.get("primary_focus"):
                strategy_summary.append(f"Focus: {diag.get('primary_focus')}")
        if output.recommended:
            strategy_summary.append(f"Recommended: {output.recommended.name}")
        if output.options:
            option_names = [o.name for o in output.options[:3]]
            strategy_summary.append(f"Options: {', '.join(option_names)}")
        if output.risks:
            strategy_summary.append(f"Key Risks: {', '.join(output.risks[:2])}")
        
        if not strategy_summary:
            return None
        
        prompt = f"""Based on the following strategic analysis for {ckb.company_name}:

{chr(10).join(strategy_summary)}

User question: {query}

Provide a brief, actionable strategic insight (2-3 sentences) focused on the most important strategic move the company should consider. Be specific about timing, priorities, and expected outcomes."""
        
        try:
            response = self._call_llm(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=STRATEGY_SYSTEM_PROMPT,
                task_type="strategy",
                temperature=0.6
            )
            return response
        except Exception as e:
            self.logger.warning(f"LLM insight generation failed: {e}")
            return None
