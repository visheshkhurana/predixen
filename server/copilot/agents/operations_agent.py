"""
Operations Agent for FounderConsole Copilot.

Converts strategy and recommendations into concrete operational tasks
with timelines, owners, budgets, and success metrics.
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

OPERATIONS_SYSTEM_PROMPT = """You are FounderConsole Operations Agent: a COO-level execution partner.
Your job: convert strategic recommendations into concrete, executable operational plans.

Rules:
- Every output must be actionable with clear owners, timelines, and success metrics.
- Break big initiatives into weekly/monthly milestones.
- Ground all budget estimates in the company's actual financial data.
- Consider team capacity (headcount) when planning.
- Provide hiring plans with role, department, location, salary range, and start date.
- Suggest marketing experiments with budgets, channels, and expected outcomes.
- Recommend pricing adjustments with revenue impact projections.
- Generate OKRs tied to strategic goals.

Deliverables:
1) Operational Tasks (prioritized, with owners and deadlines)
2) Hiring Plan (roles, timing, budget impact)
3) Marketing Experiments (channels, budget, expected ROI)
4) Pricing Recommendations (changes, revenue impact)
5) OKRs (quarterly objectives with key results)
6) Resource Requirements and Budget
7) Risk Mitigation Steps
""" + get_grounding_prompt_addition()


@dataclass
class OperationalTask:
    title: str
    description: str
    priority: str
    owner_role: str
    deadline_weeks: int
    effort_hours: int
    dependencies: List[str] = field(default_factory=list)
    success_criteria: str = ""
    budget_usd: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "owner_role": self.owner_role,
            "deadline_weeks": self.deadline_weeks,
            "effort_hours": self.effort_hours,
            "dependencies": self.dependencies,
            "success_criteria": self.success_criteria,
            "budget_usd": self.budget_usd,
        }


@dataclass
class HiringPlan:
    role: str
    department: str
    seniority: str
    salary_range_min: int
    salary_range_max: int
    start_month: int
    justification: str
    impact_on_burn: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "department": self.department,
            "seniority": self.seniority,
            "salary_range": {"min": self.salary_range_min, "max": self.salary_range_max},
            "start_month": self.start_month,
            "justification": self.justification,
            "impact_on_burn": self.impact_on_burn,
        }


@dataclass
class MarketingExperiment:
    name: str
    channel: str
    budget_usd: float
    duration_weeks: int
    expected_leads: int
    expected_cac: float
    hypothesis: str
    success_metric: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "channel": self.channel,
            "budget_usd": self.budget_usd,
            "duration_weeks": self.duration_weeks,
            "expected_leads": self.expected_leads,
            "expected_cac": self.expected_cac,
            "hypothesis": self.hypothesis,
            "success_metric": self.success_metric,
        }


@dataclass
class OKR:
    objective: str
    key_results: List[Dict[str, Any]] = field(default_factory=list)
    quarter: str = "Q1"
    owner_role: str = "CEO"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "objective": self.objective,
            "key_results": self.key_results,
            "quarter": self.quarter,
            "owner_role": self.owner_role,
        }


@dataclass
class OperationsOutput:
    tasks: List[OperationalTask] = field(default_factory=list)
    hiring_plan: List[HiringPlan] = field(default_factory=list)
    marketing_experiments: List[MarketingExperiment] = field(default_factory=list)
    pricing_recommendations: List[Dict[str, Any]] = field(default_factory=list)
    okrs: List[OKR] = field(default_factory=list)
    total_budget: float = 0.0
    timeline_months: int = 3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tasks": [t.to_dict() for t in self.tasks],
            "hiring_plan": [h.to_dict() for h in self.hiring_plan],
            "marketing_experiments": [m.to_dict() for m in self.marketing_experiments],
            "pricing_recommendations": self.pricing_recommendations,
            "okrs": [o.to_dict() for o in self.okrs],
            "total_budget": self.total_budget,
            "timeline_months": self.timeline_months,
        }


class OperationsAgent(BaseAgent):
    """
    Operations Agent that converts strategy into actionable execution plans.

    Uses Claude Sonnet via LLM Router for operational planning.
    """

    OPERATIONS_KEYWORDS = [
        "execute", "implement", "operationalize", "action plan", "tasks",
        "hiring plan", "who should", "when should", "timeline",
        "okr", "objectives", "milestones", "sprint", "roadmap",
        "marketing plan", "campaign", "experiment", "budget",
        "pricing change", "price adjustment", "rollout",
        "team structure", "org chart", "resource allocation",
    ]

    def __init__(self, llm_router=None):
        super().__init__(AgentType.OPERATIONS, llm_router)

    async def process(
        self,
        query: str,
        ckb: CompanyKnowledgeBase,
        context: Dict[str, Any],
    ) -> AgentResponse:
        output = OperationsOutput()
        findings = []

        financials = self._get_financial_context(ckb, context)

        output.tasks = self._generate_tasks(query, ckb, financials, context)
        findings.append(f"Generated {len(output.tasks)} operational tasks")

        output.hiring_plan = self._generate_hiring_plan(query, ckb, financials)
        if output.hiring_plan:
            total_hire_cost = sum(h.salary_range_max for h in output.hiring_plan)
            findings.append(
                f"Hiring plan: {len(output.hiring_plan)} roles, "
                f"max annual cost ${total_hire_cost:,}"
            )

        output.marketing_experiments = self._generate_experiments(query, ckb, financials)
        if output.marketing_experiments:
            total_mkt = sum(e.budget_usd for e in output.marketing_experiments)
            findings.append(f"Marketing experiments: ${total_mkt:,.0f} total budget")

        output.pricing_recommendations = self._generate_pricing_recs(query, ckb, financials)

        output.okrs = self._generate_okrs(query, ckb, output)
        if output.okrs:
            findings.append(f"Generated {len(output.okrs)} OKRs")

        output.total_budget = self._calculate_total_budget(output)

        assumptions = [
            "Operational plan assumes current team capacity and no major disruptions",
            "Budget estimates based on market-rate salaries and typical SaaS benchmarks",
            "Timeline assumes immediate executive alignment and resource allocation",
        ]

        risks = self._identify_execution_risks(output, financials)

        llm_insights = await self._generate_llm_insights(query, output, ckb, context)
        if llm_insights:
            findings.append(llm_insights)

        confidence = self._assess_confidence(ckb, context)

        return AgentResponse(
            agent_type=AgentType.OPERATIONS,
            findings=findings,
            structured_output={"operations": output.to_dict()},
            assumptions=assumptions,
            risks=risks,
            next_questions=self._generate_questions(output, ckb),
            confidence=confidence,
            raw_response=llm_insights or "",
        )

    def _get_financial_context(
        self, ckb: CompanyKnowledgeBase, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        fin = ckb.financials or {}
        truth = context.get("truth_scan", {})
        return {
            "revenue": fin.get("revenue", truth.get("revenue", 0)),
            "monthly_burn": fin.get("monthly_burn", truth.get("monthly_burn", 50000)),
            "cash_balance": fin.get("cash_balance", truth.get("cash_balance", 500000)),
            "runway_months": fin.get("runway_months", truth.get("runway_months", 12)),
            "headcount": fin.get("headcount", truth.get("headcount", 10)),
            "payroll": fin.get("payroll", truth.get("payroll_expense", 30000)),
            "growth_rate": fin.get("growth_rate", truth.get("revenue_growth_pct", 10)),
            "cac": fin.get("cac", truth.get("cac", 500)),
            "arpu": fin.get("arpu", truth.get("arpu", 100)),
        }

    def _generate_tasks(
        self,
        query: str,
        ckb: CompanyKnowledgeBase,
        financials: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[OperationalTask]:
        tasks = []
        query_lower = query.lower()
        runway = financials.get("runway_months", 12)

        if runway and isinstance(runway, (int, float)) and runway < 12:
            tasks.append(OperationalTask(
                title="Emergency Cost Audit",
                description="Review all recurring expenses and identify 20-30% savings opportunities",
                priority="P0",
                owner_role="CFO / Finance Lead",
                deadline_weeks=1,
                effort_hours=16,
                success_criteria="Identified $X/mo in savings; cuts approved by leadership",
            ))
            tasks.append(OperationalTask(
                title="Vendor Renegotiation Sprint",
                description="Renegotiate top 5 vendor contracts for better terms or cancellation",
                priority="P0",
                owner_role="Operations Lead",
                deadline_weeks=2,
                effort_hours=20,
                dependencies=["Emergency Cost Audit"],
                success_criteria="Reduced vendor spend by 15%+",
            ))

        if any(kw in query_lower for kw in ["hire", "team", "headcount", "recruit"]):
            tasks.append(OperationalTask(
                title="Write Job Descriptions",
                description="Draft JDs for approved roles with clear requirements and comp ranges",
                priority="P1",
                owner_role="Hiring Manager",
                deadline_weeks=1,
                effort_hours=8,
                success_criteria="JDs approved and posted on 3+ channels",
            ))
            tasks.append(OperationalTask(
                title="Set Up Interview Pipeline",
                description="Define interview stages, rubrics, and assign interviewers",
                priority="P1",
                owner_role="HR / People Ops",
                deadline_weeks=2,
                effort_hours=12,
                dependencies=["Write Job Descriptions"],
                success_criteria="Pipeline configured; first candidates screened",
            ))

        if any(kw in query_lower for kw in ["growth", "revenue", "sales", "marketing", "gtm"]):
            tasks.append(OperationalTask(
                title="Define Growth Metrics Dashboard",
                description="Set up tracking for funnel metrics: visitors → leads → trials → customers",
                priority="P1",
                owner_role="Growth Lead",
                deadline_weeks=2,
                effort_hours=16,
                success_criteria="Dashboard live with real-time funnel data",
            ))
            tasks.append(OperationalTask(
                title="Launch First Growth Experiment",
                description="Run a 2-week paid experiment on the highest-potential channel",
                priority="P1",
                owner_role="Marketing Lead",
                deadline_weeks=3,
                effort_hours=20,
                dependencies=["Define Growth Metrics Dashboard"],
                success_criteria="Experiment complete with CAC and conversion data",
                budget_usd=2000,
            ))

        if any(kw in query_lower for kw in ["price", "pricing", "monetiz"]):
            tasks.append(OperationalTask(
                title="Pricing Analysis",
                description="Analyze current pricing vs. value delivered and competitor pricing",
                priority="P1",
                owner_role="Product / Strategy Lead",
                deadline_weeks=2,
                effort_hours=16,
                success_criteria="Pricing report with 2-3 pricing model options",
            ))
            tasks.append(OperationalTask(
                title="Price Change Communication Plan",
                description="Draft customer communication for any pricing changes",
                priority="P2",
                owner_role="Customer Success Lead",
                deadline_weeks=3,
                effort_hours=8,
                dependencies=["Pricing Analysis"],
                success_criteria="Communication plan approved; FAQ prepared",
            ))

        if not tasks:
            tasks.append(OperationalTask(
                title="Strategic Alignment Meeting",
                description="Align leadership team on priorities and resource allocation",
                priority="P0",
                owner_role="CEO",
                deadline_weeks=1,
                effort_hours=4,
                success_criteria="Top 3 priorities agreed with owners and deadlines",
            ))
            tasks.append(OperationalTask(
                title="Metrics Review Cadence",
                description="Establish weekly metrics review with all department leads",
                priority="P1",
                owner_role="CEO / COO",
                deadline_weeks=1,
                effort_hours=2,
                success_criteria="Weekly review scheduled; dashboard shared",
            ))

        return tasks

    def _generate_hiring_plan(
        self,
        query: str,
        ckb: CompanyKnowledgeBase,
        financials: Dict[str, Any],
    ) -> List[HiringPlan]:
        query_lower = query.lower()
        if not any(kw in query_lower for kw in ["hire", "team", "headcount", "recruit", "staff", "engineer", "sales"]):
            return []

        plans = []
        headcount = financials.get("headcount", 10)
        runway = financials.get("runway_months", 12)
        revenue = financials.get("revenue", 0)

        if any(kw in query_lower for kw in ["engineer", "developer", "tech"]):
            plans.append(HiringPlan(
                role="Senior Software Engineer",
                department="Engineering",
                seniority="Senior",
                salary_range_min=120000,
                salary_range_max=180000,
                start_month=2,
                justification="Accelerate product development for growth features",
                impact_on_burn=15000,
            ))

        if any(kw in query_lower for kw in ["sales", "revenue", "growth"]):
            plans.append(HiringPlan(
                role="Account Executive",
                department="Sales",
                seniority="Mid",
                salary_range_min=80000,
                salary_range_max=120000,
                start_month=1,
                justification="Drive revenue growth through outbound sales",
                impact_on_burn=10000,
            ))

        if not plans and headcount < 15:
            plans.append(HiringPlan(
                role="Full-Stack Engineer",
                department="Engineering",
                seniority="Mid",
                salary_range_min=100000,
                salary_range_max=150000,
                start_month=2,
                justification="Core team scaling for product development",
                impact_on_burn=12500,
            ))

        if runway and isinstance(runway, (int, float)) and runway < 12:
            for plan in plans:
                plan.start_month = max(plan.start_month, 3)
                plan.justification += " (delayed due to runway constraints)"

        return plans

    def _generate_experiments(
        self,
        query: str,
        ckb: CompanyKnowledgeBase,
        financials: Dict[str, Any],
    ) -> List[MarketingExperiment]:
        query_lower = query.lower()
        if not any(kw in query_lower for kw in ["market", "growth", "acquisition", "leads", "campaign", "gtm"]):
            return []

        cac = financials.get("cac", 500)
        experiments = []

        experiments.append(MarketingExperiment(
            name="LinkedIn Outbound Campaign",
            channel="LinkedIn Ads + Sales Nav",
            budget_usd=3000,
            duration_weeks=4,
            expected_leads=30,
            expected_cac=cac * 0.8,
            hypothesis="Targeted LinkedIn outreach to ICP converts better than broad campaigns",
            success_metric="Cost per qualified lead < $100; 3+ demos booked",
        ))

        experiments.append(MarketingExperiment(
            name="Content-Led SEO Sprint",
            channel="Blog + SEO",
            budget_usd=2000,
            duration_weeks=8,
            expected_leads=50,
            expected_cac=cac * 0.5,
            hypothesis="Problem-aware content captures high-intent organic traffic",
            success_metric="5+ articles ranking page 1; 50+ organic leads/month",
        ))

        experiments.append(MarketingExperiment(
            name="Product Hunt Launch",
            channel="Product Hunt",
            budget_usd=500,
            duration_weeks=2,
            expected_leads=100,
            expected_cac=5,
            hypothesis="Community launch drives awareness and early adopter signups",
            success_metric="Top 5 of the day; 100+ signups in 48 hours",
        ))

        return experiments

    def _generate_pricing_recs(
        self,
        query: str,
        ckb: CompanyKnowledgeBase,
        financials: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        query_lower = query.lower()
        if not any(kw in query_lower for kw in ["price", "pricing", "monetiz", "revenue"]):
            return []

        arpu = financials.get("arpu", 100)
        revenue = financials.get("revenue", 0)

        recs = []
        recs.append({
            "action": "Introduce Annual Plan Discount",
            "description": f"Offer 15-20% discount for annual commitment (current ARPU: ${arpu:,.0f})",
            "expected_impact": "Improve cash flow by 2-3 months; reduce churn 10-15%",
            "risk": "Lower effective ARPU per month",
            "timeline": "2-3 weeks to implement",
        })

        if arpu < 200:
            recs.append({
                "action": "Price Increase (10-20%)",
                "description": f"Raise base price from ${arpu:,.0f} to ${arpu * 1.15:,.0f}",
                "expected_impact": f"Increase MRR by ${revenue * 0.15:,.0f}/mo with <5% churn impact",
                "risk": "Potential churn increase; customer pushback",
                "timeline": "4-6 weeks (30-day notice to customers)",
            })

        return recs

    def _generate_okrs(
        self,
        query: str,
        ckb: CompanyKnowledgeBase,
        output: OperationsOutput,
    ) -> List[OKR]:
        okrs = []

        okrs.append(OKR(
            objective="Achieve sustainable growth with capital efficiency",
            key_results=[
                {"result": "Grow MRR by 15% month-over-month", "owner": "Sales Lead", "metric": "mrr_growth"},
                {"result": "Reduce burn multiple below 2x", "owner": "CFO", "metric": "burn_multiple"},
                {"result": "Maintain runway above 18 months", "owner": "CEO", "metric": "runway_months"},
            ],
            quarter="Q1",
            owner_role="CEO",
        ))

        if output.hiring_plan:
            okrs.append(OKR(
                objective="Build and scale the team effectively",
                key_results=[
                    {"result": f"Hire {len(output.hiring_plan)} key roles", "owner": "People Ops", "metric": "hires_completed"},
                    {"result": "Achieve 90-day new hire retention of 100%", "owner": "Managers", "metric": "retention_rate"},
                    {"result": "Complete onboarding within 2 weeks per hire", "owner": "People Ops", "metric": "onboarding_time"},
                ],
                quarter="Q1",
                owner_role="VP People",
            ))

        if output.marketing_experiments:
            okrs.append(OKR(
                objective="Validate scalable acquisition channels",
                key_results=[
                    {"result": "Run 3+ growth experiments", "owner": "Growth Lead", "metric": "experiments_run"},
                    {"result": "Identify 1 channel with CAC below $300", "owner": "Marketing Lead", "metric": "cac"},
                    {"result": "Generate 100+ qualified leads", "owner": "Marketing Lead", "metric": "qualified_leads"},
                ],
                quarter="Q1",
                owner_role="VP Marketing",
            ))

        return okrs

    def _calculate_total_budget(self, output: OperationsOutput) -> float:
        task_budget = sum(t.budget_usd for t in output.tasks)
        mkt_budget = sum(e.budget_usd for e in output.marketing_experiments)
        hire_budget = sum(h.salary_range_max / 12 for h in output.hiring_plan)
        return task_budget + mkt_budget + hire_budget

    def _identify_execution_risks(
        self, output: OperationsOutput, financials: Dict[str, Any]
    ) -> List[str]:
        risks = []
        runway = financials.get("runway_months", 12)

        if output.total_budget > financials.get("cash_balance", 500000) * 0.1:
            risks.append("Total execution budget exceeds 10% of cash — monitor spend carefully")

        if len(output.hiring_plan) > 3:
            risks.append("Multiple concurrent hires may strain management capacity")

        if runway and isinstance(runway, (int, float)) and runway < 12 and output.hiring_plan:
            risks.append("Hiring with limited runway increases burn — consider contractors first")

        risks.append("Execution plan assumes team alignment — misalignment is the #1 startup risk")

        return risks

    def _generate_questions(
        self, output: OperationsOutput, ckb: CompanyKnowledgeBase
    ) -> List[str]:
        questions = []
        if not ckb.financials.get("headcount"):
            questions.append("What is your current team size and composition?")
        if not output.hiring_plan:
            questions.append("Are there any immediate hiring needs?")
        if not ckb.strategy.get("moat"):
            questions.append("What is your key competitive advantage to protect during execution?")
        return questions[:3]

    def _assess_confidence(
        self, ckb: CompanyKnowledgeBase, context: Dict[str, Any]
    ) -> ConfidenceLevel:
        data_points = 0
        if ckb.financials:
            data_points += 2
        if ckb.financials.get("headcount"):
            data_points += 1
        if context.get("truth_scan"):
            data_points += 2
        if ckb.strategy:
            data_points += 1

        if data_points >= 4:
            return ConfidenceLevel.HIGH
        elif data_points >= 2:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW

    async def _generate_llm_insights(
        self,
        query: str,
        output: OperationsOutput,
        ckb: CompanyKnowledgeBase,
        context: Dict[str, Any],
    ) -> Optional[str]:
        if not self.llm_router:
            return None

        summary_parts = []
        if output.tasks:
            task_names = [t.title for t in output.tasks[:4]]
            summary_parts.append(f"Tasks: {', '.join(task_names)}")
        if output.hiring_plan:
            roles = [h.role for h in output.hiring_plan]
            summary_parts.append(f"Hiring: {', '.join(roles)}")
        if output.marketing_experiments:
            exps = [e.name for e in output.marketing_experiments[:3]]
            summary_parts.append(f"Experiments: {', '.join(exps)}")
        if output.okrs:
            summary_parts.append(f"OKRs: {len(output.okrs)} objectives")

        if not summary_parts:
            return None

        prompt = f"""Based on the following operational plan for {ckb.company_name}:

{chr(10).join(summary_parts)}

Total budget: ${output.total_budget:,.0f}
Timeline: {output.timeline_months} months

User question: {query}

Provide a concise execution briefing (3-4 sentences): what to prioritize first, biggest execution risk, and the one metric to watch most closely."""

        try:
            response = self._call_llm(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=OPERATIONS_SYSTEM_PROMPT,
                task_type="strategy",
                temperature=0.5,
            )
            return response
        except Exception as e:
            self.logger.warning(f"LLM insight generation failed: {e}")
            return None
