from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import uuid as uuid_lib
import logging

logger = logging.getLogger(__name__)

from server.core.db import get_db
from server.core.security import get_current_user
from server.models.user import User
from server.models.company import Company
from server.models.simulation_run import SimulationRun
from server.models.decision import Decision
from server.models.company_decision import CompanyDecision
from server.models.truth_scan import TruthScan
from server.models.financial import FinancialRecord
from server.decision.decision_engine import generate_recommendations
from server.simulate.simulation_engine import SimulationInputs
from server.api.simulations import extract_metric_value

router = APIRouter(tags=["decisions"])


class DecisionOption(BaseModel):
    name: str
    description: str
    pros: List[str] = []
    cons: List[str] = []
    cost: Optional[str] = None
    risk: str = "medium"


class DecisionRecommendation(BaseModel):
    option: str
    rationale: str
    next_steps: List[str] = []


class CreateDecisionRequest(BaseModel):
    title: str
    context: Optional[str] = None
    options: List[DecisionOption] = []
    recommendation: Optional[DecisionRecommendation] = None
    status: str = "proposed"
    owner: Optional[str] = None
    tags: List[str] = []
    confidence: str = "medium"
    sources: List[str] = []


class UpdateDecisionRequest(BaseModel):
    title: Optional[str] = None
    context: Optional[str] = None
    options: Optional[List[DecisionOption]] = None
    recommendation: Optional[DecisionRecommendation] = None
    status: Optional[str] = None
    owner: Optional[str] = None
    tags: Optional[List[str]] = None
    confidence: Optional[str] = None

@router.post("/simulation/{run_id}/decisions/generate", response_model=Dict[str, Any])
def generate_decisions(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sim_run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
    
    if not sim_run:
        raise HTTPException(status_code=404, detail="Simulation run not found")
    
    from server.models.scenario import Scenario
    scenario = db.query(Scenario).filter(Scenario.id == sim_run.scenario_id).first()
    
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    company = db.query(Company).filter(
        Company.id == scenario.company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=403, detail="Access denied")
    
    truth_scan = db.query(TruthScan).filter(
        TruthScan.company_id == company.id
    ).order_by(TruthScan.created_at.desc()).first()
    
    if not truth_scan:
        raise HTTPException(status_code=400, detail="Run a truth scan first")
    
    metrics = truth_scan.outputs_json.get("metrics", {})
    confidence = truth_scan.outputs_json.get("data_confidence_score", 50)
    
    latest_record = (
        db.query(FinancialRecord)
        .filter(FinancialRecord.company_id == company.id)
        .order_by(FinancialRecord.period_start.desc())
        .first()
    )
    
    def metric_or_record(metric_key, record_attr, default):
        val = extract_metric_value(metrics.get(metric_key), 0)
        if val and val > 0:
            return val
        if latest_record and getattr(latest_record, record_attr, None):
            return float(getattr(latest_record, record_attr))
        return default
    
    baseline_inputs = SimulationInputs(
        baseline_revenue=metric_or_record("monthly_revenue", "revenue", 50000),
        baseline_growth_rate=extract_metric_value(metrics.get("revenue_growth_mom"), 10),
        gross_margin=extract_metric_value(metrics.get("gross_margin"), 70),
        opex=metric_or_record("opex", "opex", 20000),
        payroll=metric_or_record("payroll", "payroll", 30000),
        other_costs=metric_or_record("other_costs", "other_costs", 5000),
        cash_balance=metric_or_record("cash_balance", "cash_balance", 500000),
        n_simulations=500
    )
    
    recommendations = generate_recommendations(metrics, confidence, baseline_inputs)
    
    decision = Decision(
        simulation_run_id=run_id,
        recommended_actions_json=recommendations
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)
    
    return {
        "id": decision.id,
        "simulation_run_id": run_id,
        "recommendations": recommendations
    }

def _build_fallback_key_risks(burn, revenue, cash, runway_months, net_burn, growth):
    risks = []
    if runway_months < 12:
        risks.append({
            "risk": f"Your net monthly burn of ${net_burn:,.0f} gives you approximately {runway_months:.0f} months before cash hits zero. If revenue growth does not accelerate or costs are not reduced, you will be unable to meet payroll and vendor obligations. The danger is not just insolvency — it is the cascading loss of leverage that begins 2-3 months before cash actually runs out, when employees start leaving, investors stop returning calls, and customers sense instability. At your current trajectory, this tipping point arrives in roughly {max(1, int(runway_months - 3)):.0f} months.",
            "likelihood": "High" if runway_months < 6 else "Medium",
            "contingency": f"Trigger an emergency cost reduction plan targeting a 25% burn reduction, which would save approximately ${burn * 0.25:,.0f}/month and extend runway by {runway_months * 0.25 / (1 - 0.25):.0f}+ months. Simultaneously initiate bridge financing conversations with existing investors — they are your fastest path to capital because they already know the business and can move in 2-3 weeks versus 2-3 months for new investors.",
            "pivot_deadline": f"If burn has not decreased by at least 15% within 6 weeks, pivot to a skeleton-crew operating model and begin acqui-hire or soft-landing conversations. Do not wait past {max(1, int(runway_months - 4)):.0f} months of remaining runway to make this call."
        })
    if revenue > 0 and growth <= 5:
        be_growth = ((burn / revenue) - 1) * 100
        risks.append({
            "risk": f"Your month-over-month revenue growth is {growth:.1f}%, but you need approximately {be_growth:.0f}% MoM growth to reach break-even at your current cost structure. At this rate, revenue will never catch up to expenses, leaving you permanently dependent on external capital to survive. Every month that passes without a step-change in growth trajectory makes the next fundraise harder — investors want to see acceleration, not linear crawl. The gap between your current growth and break-even growth is not something that closes gradually; it requires a deliberate, aggressive shift in go-to-market strategy.",
            "likelihood": "High" if growth <= 0 else "Medium",
            "contingency": f"Reassign 50% of engineering capacity from infrastructure to revenue-driving features immediately. Launch a pricing experiment targeting a 15-20% increase for new customers while grandfathering existing accounts. Aim for 3 high-value upsell conversations per week with existing accounts — expansion revenue is the fastest path to closing the growth gap.",
            "pivot_deadline": f"If MoM growth has not reached at least {max(5, int(be_growth * 0.3)):.0f}% within 90 days, pivot the go-to-market strategy entirely — either shift to a different customer segment, change the pricing model, or explore a fundamentally different distribution channel. Continuing the current approach past that point is burning cash without evidence of traction."
        })
    risks.append({
        "risk": "Critical knowledge and customer relationships are concentrated in 1-2 team members. If either leaves — whether for a competing offer, burnout, or personal reasons — you lose not just their output but months of institutional knowledge that cannot be quickly replaced. In an early-stage company, this kind of departure can stall the product roadmap by 2-3 months and damage customer confidence at the worst possible time. The risk is heightened during periods of uncertainty, which is exactly where you are now.",
        "likelihood": "Medium",
        "contingency": "Within the next 2 weeks, have each critical team member document their top 5 processes and decision frameworks. Cross-train at least one backup for each critical function. For your top 3 most essential people, implement retention packages — even modest equity refreshers or retention bonuses signal commitment and buy you stability.",
        "pivot_deadline": "If documentation and cross-training are not complete within 30 days, escalate to a board-level discussion about key-person risk and consider restructuring responsibilities even at the cost of short-term velocity. The window to mitigate this risk shrinks every week you delay."
    })
    if burn > 0 and revenue > 0:
        concentration_risk = min(revenue * 0.4, burn * 0.3)
        risks.append({
            "risk": f"If your revenue is concentrated in a small number of accounts, losing even one major customer could eliminate ${concentration_risk:,.0f}+/month overnight. At your current burn rate, that kind of revenue loss would cut your runway by {max(1, int(runway_months * 0.3)):.0f}+ months and force you into emergency mode. Customer concentration is an invisible risk — everything looks stable until a single contract non-renewal or budget cut changes the math completely. The problem is compounded if these accounts are on monthly contracts with short notice periods.",
            "likelihood": "Medium",
            "contingency": f"Target signing 5+ new accounts per quarter to reduce concentration below 30% for any single customer. Implement quarterly business reviews with your top 5 accounts to surface churn signals early. Push for annual contracts with 90-day notice periods — the upfront discount is worth the stability.",
            "pivot_deadline": "If no single customer accounts for less than 30% of revenue by end of next quarter, pivot to a product-led growth model with self-serve onboarding that removes dependency on large enterprise deals. The longer concentration persists, the more fragile the business becomes."
        })
    risks.append({
        "risk": f"Fundraising conditions are not static. If the macro environment shifts — rising interest rates, a market correction, or a sector-specific downturn — the capital available to startups at your stage could shrink significantly before you need to raise. When that happens, valuations compress, terms become more investor-favorable, and rounds that would have closed in 6 weeks take 6 months. With approximately {runway_months:.0f} months of runway, you do not have the luxury of assuming the fundraising window stays open indefinitely.",
        "likelihood": "Medium",
        "contingency": "Begin investor outreach 6 months before your projected cash need, not 3 months. Maintain a warm pipeline of at least 15 investors through regular updates and informal check-ins. Prepare a 'Plan B' operating model that shows a credible path to cash-flow breakeven without additional funding — this gives you leverage in negotiations and a real fallback if the market turns.",
        "pivot_deadline": f"If you have not received at least 2 term sheets by the time runway drops below {max(3, int(runway_months * 0.5)):.0f} months, immediately activate the Plan B operating model and shift to breakeven mode. Do not continue fundraising past 3 months of runway — at that point, survival takes priority over growth."
    })
    return risks[:5]


def _build_fallback_playbook(burn, revenue, cash, runway_months, net_burn, growth, weekly_burn, daily_burn):
    vendor_target = burn * 0.08
    playbook = []

    if runway_months < 12:
        playbook.append({
            "phase": "Phase 1: Preparation (Week 1-2)",
            "action": f"Pull a full vendor and subscription audit. List every recurring charge over $500/month. Cancel or renegotiate anything non-essential to immediate revenue generation.",
            "owner": "Head of Finance",
            "timeline": "Week 1",
            "definition_of_done": f"Spreadsheet of all recurring charges reviewed by CEO, with ${vendor_target:,.0f}+ in identified savings and cancellation/renegotiation initiated on each line item"
        })
        playbook.append({
            "phase": "Phase 1: Preparation (Week 1-2)",
            "action": f"Implement an immediate hiring freeze across all departments. Convert any open requisitions to contractor-based roles with 30-day termination clauses.",
            "owner": "CEO",
            "timeline": "Week 1",
            "definition_of_done": f"All open job postings paused, hiring managers notified in writing, contractor templates prepared for any critical roles"
        })
        playbook.append({
            "phase": "Phase 1: Preparation (Week 1-2)",
            "action": f"Reduce infrastructure costs by right-sizing cloud resources, eliminating unused environments, and consolidating dev/staging servers.",
            "owner": "VP Engineering / DevOps Lead",
            "timeline": "Week 1-2",
            "definition_of_done": f"Infrastructure audit complete, unused resources terminated, projected savings of ${burn * 0.04:,.0f}-${burn * 0.06:,.0f}/month confirmed in next billing cycle"
        })
        playbook.append({
            "phase": "Phase 2: Execution (Week 3-6)",
            "action": f"Identify your top 3 revenue-generating channels by conversion rate. Reallocate 80% of sales and marketing effort to those channels only. Pause all experimental campaigns.",
            "owner": "Head of Sales / Head of Marketing",
            "timeline": "Week 3",
            "definition_of_done": f"Channel performance report shared with leadership, budget reallocated, experimental campaigns paused with target of ${revenue * 0.2:,.0f}/month incremental revenue within 60 days"
        })
        playbook.append({
            "phase": "Phase 2: Execution (Week 3-6)",
            "action": f"Contact your top 10 customers and offer annual prepay discounts (15-20% off) in exchange for upfront cash. Prioritize accounts with monthly contracts over $1,000.",
            "owner": "Head of Sales / Account Management",
            "timeline": "Week 3-4",
            "definition_of_done": f"All 10 customers contacted, at least 3 prepay proposals sent, target ${cash * 0.05:,.0f}-${cash * 0.1:,.0f} in committed upfront cash"
        })
        playbook.append({
            "phase": "Phase 2: Execution (Week 3-6)",
            "action": f"Renegotiate payment terms with your 5 largest vendors to Net-60 or Net-90. Offer early payment discounts on future invoices as leverage.",
            "owner": "Head of Finance",
            "timeline": "Week 3",
            "definition_of_done": f"Renegotiation conversations initiated with all 5 vendors, at least 2 signed amendments in hand freeing ${burn * 0.1:,.0f}-${burn * 0.15:,.0f} in near-term cash"
        })
        playbook.append({
            "phase": "Phase 2: Execution (Week 3-6)",
            "action": f"Schedule a board/advisor call to discuss bridge financing options. Prepare a 90-day operating plan showing path to ${burn * 0.75:,.0f}/month burn rate.",
            "owner": "CEO",
            "timeline": "Week 4-5",
            "definition_of_done": "Board call completed, 90-day plan presented, bridge commitment or term sheet timeline agreed upon"
        })
        playbook.append({
            "phase": "Phase 3: Optimization (Week 7-8)",
            "action": f"Track weekly burn against the new target of ${burn * 0.75:,.0f}/month. Review progress every Friday with the leadership team and adjust levers as needed.",
            "owner": "CEO / Head of Finance",
            "timeline": "Week 7-8",
            "definition_of_done": f"4 consecutive weekly reviews completed, actual burn within 10% of ${burn * 0.75:,.0f}/month target, course corrections documented"
        })
    else:
        playbook.append({
            "phase": "Phase 1: Preparation (Week 1-2)",
            "action": f"Map your full customer acquisition funnel with conversion rates at each stage. Identify the single biggest drop-off point and assign a dedicated team to fix it.",
            "owner": "Head of Growth / Head of Product",
            "timeline": "Week 1-2",
            "definition_of_done": f"Funnel analysis document with conversion rates at each stage, drop-off point identified, 2-person team assigned with a 2-week sprint to fix it"
        })
        playbook.append({
            "phase": "Phase 1: Preparation (Week 1-2)",
            "action": f"Audit all non-revenue-critical engineering projects. Pause or descope any initiative that does not directly contribute to customer acquisition, retention, or monetization.",
            "owner": "VP Engineering / CTO",
            "timeline": "Week 1",
            "definition_of_done": "Project inventory reviewed, non-critical projects paused or descoped, 30-40% of engineering capacity redirected to revenue-driving features"
        })
        playbook.append({
            "phase": "Phase 1: Preparation (Week 1-2)",
            "action": f"Set up weekly cash flow monitoring with a dashboard visible to the leadership team. Track actual vs. projected burn every Friday.",
            "owner": "Head of Finance",
            "timeline": "Week 1",
            "definition_of_done": "Dashboard live and shared with leadership team, first weekly review completed with actual vs. projected comparison"
        })
        playbook.append({
            "phase": "Phase 2: Execution (Week 3-6)",
            "action": f"Launch a pricing experiment: test a 15-20% price increase on new customers while grandfathering existing accounts. Measure impact on conversion over 30 days.",
            "owner": "Head of Product / CEO",
            "timeline": "Week 3",
            "definition_of_done": f"New pricing live for new signups, A/B test instrumented, 30-day measurement window started with target of ${revenue * 0.15:,.0f}-${revenue * 0.2:,.0f}/month incremental revenue if conversion holds"
        })
        playbook.append({
            "phase": "Phase 2: Execution (Week 3-6)",
            "action": f"Identify your 5 highest-value customers and schedule executive-level check-ins. Understand their expansion needs and propose upsell packages.",
            "owner": "Head of Sales / CEO",
            "timeline": "Week 3-5",
            "definition_of_done": f"All 5 meetings completed, expansion proposals sent to at least 3 accounts, target ${revenue * 0.06:,.0f}-${revenue * 0.1:,.0f}/month in expansion revenue"
        })
        playbook.append({
            "phase": "Phase 2: Execution (Week 3-6)",
            "action": f"Build a 6-month financial model with three scenarios (base, optimistic, downside). Present to the board with specific asks for each scenario.",
            "owner": "CEO / Head of Finance",
            "timeline": "Week 5-6",
            "definition_of_done": "Model complete with all three scenarios, board presentation delivered, strategic alignment confirmed and next steps agreed"
        })
        playbook.append({
            "phase": "Phase 3: Optimization (Week 7-8)",
            "action": f"Review funnel fix results and pricing experiment data. Double down on what worked, kill what didn't. Set revised growth targets for the next quarter.",
            "owner": "Head of Growth / CEO",
            "timeline": "Week 7-8",
            "definition_of_done": f"Results report shared with leadership, revised quarterly growth targets set, resource allocation updated based on experiment outcomes"
        })

    return playbook


@router.get("/companies/{company_id}/strategic-diagnosis")
def generate_strategic_diagnosis(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    revenue = 0.0
    burn = 0.0
    cash = 0.0
    growth = 0.0
    runway_months = 24.0
    net_burn = 0.0
    exhaustion_date = "beyond 24 months"
    breakeven_growth_needed = 0.0
    confidence = 50
    survival_prob = None
    
    try:
        truth_scan = db.query(TruthScan).filter(
            TruthScan.company_id == company.id
        ).order_by(TruthScan.created_at.desc()).first()
        
        metrics = {}
        confidence = 50
        if truth_scan and truth_scan.outputs_json:
            metrics = truth_scan.outputs_json.get("metrics", {})
            confidence = truth_scan.outputs_json.get("data_confidence_score", 50)
        
        latest_record = (
            db.query(FinancialRecord)
            .filter(FinancialRecord.company_id == company.id)
            .order_by(FinancialRecord.period_start.desc())
            .first()
        )
        
        revenue = extract_metric_value(metrics.get("monthly_revenue"), 0)
        if not revenue and latest_record and latest_record.revenue:
            revenue = float(latest_record.revenue)
        burn = extract_metric_value(metrics.get("monthly_burn"), 0)
        if not burn and latest_record:
            opex = float(latest_record.opex or 0)
            payroll = float(latest_record.payroll or 0)
            burn = opex + payroll
        cash = extract_metric_value(metrics.get("cash_balance"), 0)
        if not cash and latest_record and latest_record.cash_balance:
            cash = float(latest_record.cash_balance)
        growth = extract_metric_value(metrics.get("revenue_growth_mom"), 0)
        runway_months = cash / burn if burn > 0 else 24
        
        from server.models.scenario import Scenario
        scenarios = db.query(Scenario).filter(Scenario.company_id == company_id).all()
        sim_data = None
        if scenarios:
            for scenario in scenarios:
                sim_run = db.query(SimulationRun).filter(
                    SimulationRun.scenario_id == scenario.id
                ).order_by(SimulationRun.created_at.desc()).first()
                if sim_run and sim_run.outputs_json:
                    sim_data = sim_run.outputs_json
                    break
        
        survival_prob = None
        if sim_data:
            survival = sim_data.get("survival", {})
            survival_prob = survival.get("probability_18m") or survival.get("probability_12m")
        
        net_burn = burn - revenue
        months_to_zero = cash / net_burn if net_burn > 0 else 99
        exhaustion_date = (datetime.utcnow() + timedelta(days=int(months_to_zero * 30))).strftime("%B %Y") if months_to_zero < 99 else "beyond 24 months"
        breakeven_growth_needed = ((burn / revenue) - 1) * 100 if revenue > 0 else 0
    except Exception as data_err:
        logger.warning(f"Error gathering financial data for diagnosis: {data_err}")
    
    company_context = f"""Company: {company.name}
Industry: {getattr(company, 'industry', 'Technology')}
Stage: {getattr(company, 'stage', 'Seed/Series A')}
Monthly Revenue: ${revenue:,.0f}
Monthly Burn: ${burn:,.0f}
Cash Balance: ${cash:,.0f}
Revenue Growth (MoM): {growth:.1f}%
Runway: {runway_months:.1f} months
Data Confidence: {confidence}%"""
    
    if survival_prob is not None:
        company_context += f"\n18-Month Survival Probability: {survival_prob:.1f}%"
    
    company_context += f"\nNet Monthly Burn (burn minus revenue): ${net_burn:,.0f}"
    company_context += f"\nProjected Cash Exhaustion: {exhaustion_date}"
    if revenue > 0:
        company_context += f"\nMoM Growth Needed to Reach Break-Even: {breakeven_growth_needed:.1f}%"

    system_prompt = """You are a McKinsey senior partner and a16z venture partner combined. You write brutally honest, data-backed strategic briefing memos for startup founders. Write all narrative sections in plain prose — no bullet points, no dashboards, no charts. The only exception is the execution_playbook field, which is a structured list of action items designed for the founder to forward directly to their team.

ABSOLUTE REQUIREMENTS:
1. recommendation_narrative MUST be 2-3 FULL PARAGRAPHS (each 3-5 sentences). A single sentence is UNACCEPTABLE. Write real reasoning, not summaries.
2. inaction_narrative MUST include the specific cash exhaustion date and the exact month-over-month growth rate needed to break even.
3. execution_playbook MUST contain 6-10 items, each with a clear task written as an instruction and an owner role.

Respond in valid JSON with this exact structure:
{
  "situation_narrative": "A 3-5 sentence paragraph in plain English describing the company's current financial state. Use specific numbers from the data (MRR, burn rate, runway, growth rate). Example tone: 'TechFlow Analytics is currently burning $143K/month against $15.4K in MRR. At this rate, you have approximately 2.9 months of runway remaining. Revenue growth has stalled at 0%, which means the gap between what you earn and what you spend is not closing. This puts you in a critical position where decisive action in the next 2-4 weeks will significantly impact your outcomes.'",
  "recommendation_headline": "A bold, specific action statement — e.g. 'Cut Monthly Burn by 30% and Launch Emergency Revenue Sprint'",
  "recommendation_narrative": "CRITICAL: This must be 2-3 FULL PARAGRAPHS of written reasoning — NOT a one-liner like 'Raise capital in Q1 to extend runway'. Each paragraph must be 3-5 sentences minimum. Write as if you are a senior advisor sitting across the table from the founder explaining your thinking in detail. Paragraph 1 (WHY THIS ACTION): Explain WHY this specific action is the highest-leverage move right now. Reference their exact revenue, burn, and runway numbers. What makes this the right play versus alternatives like cutting costs, raising a bridge, or pivoting? Be specific about what you considered and rejected. Paragraph 2 (WHY NOW / COST OF DELAY): Explain what happens if the founder waits — quantify the cost of delay using their burn rate (e.g., 'Every week you wait costs $X and reduces your negotiating leverage'). Describe the trade-offs honestly: what gets sacrificed, what risks are introduced, and why the trade-off is still worth it. Be concrete about the narrowing window. Paragraph 3 (MECHANICS): Describe the mechanics — what specifically to do first, who to talk to, what to deprioritize. This paragraph should read like the opening move of a chess game: precise and sequenced. Separate paragraphs with double newlines (\\n\\n). REMEMBER: Each paragraph MUST be multiple sentences. If your output is less than 150 words total for this field, you have failed.",
  "urgency_text": "A specific, time-bound urgency statement using the company's data — e.g. 'Act within the next 2 weeks. At your current burn of $X/month, each day of inaction costs $Y and your fundraising window closes by [date].' or 'This decision becomes materially less effective after 30 days because [specific reason].'",
  "inaction_narrative": "CRITICAL: This must be 2-3 FULL PARAGRAPHS painting a vivid, specific picture of what happens if the founder does nothing. Paragraph 1: State the math plainly — 'If no action is taken, at your current burn rate of $X/month, runway will be exhausted by [specific month/year]. Revenue would need to grow by Y% month-over-month to reach break-even, which is significantly above your current trajectory of Z%.' Include the EXACT exhaustion date and EXACT growth rate needed. Paragraph 2: Describe the cascade of consequences — when does the crisis become visible to employees, when do fundraising options narrow, when does the company lose leverage with investors/customers/partners? Use specific timeline markers. Paragraph 3 (optional): Describe the end state — forced fire sale, down round at punitive terms, talent exodus, etc. Make it concrete, not abstract. Separate paragraphs with double newlines (\\n\\n).",
  "company_stage_label": "One of: Pre-Revenue, Early Revenue, Growth, Scale, or Distressed",
  "health_score": 1-100,
  "health_label": "One of: Critical, Concerning, Stable, Healthy, Strong",
  "inaction_projection": {
    "months_to_crisis": integer,
    "crisis_description": "One-sentence summary",
    "probability": 0-100,
    "cash_at_crisis": number,
    "key_trigger": "Single trigger"
  },
  "execution_playbook": [
    {
      "phase": "Phase name — one of: 'Phase 1: Preparation (Week 1-2)', 'Phase 2: Execution (Week 3-6)', 'Phase 3: Optimization (Week 7-8)'",
      "action": "A clear task written as an instruction that a team member can execute without asking questions. Example: 'Update the pitch deck to include Q4 metrics and a clear use-of-funds breakdown'. NOT vague advice like 'improve sales' — write it as a specific directive using the company's actual numbers where possible.",
      "owner": "The role responsible — e.g. 'CEO', 'Head of Finance', 'CTO', 'VP Engineering', 'Head of Sales', 'Head of Product'",
      "timeline": "A specific deadline within the phase — e.g. 'Week 1', 'By end of Week 2', 'Within 48 hours'",
      "definition_of_done": "What 'complete' looks like — a clear, verifiable condition. e.g. 'Deck sent to 5 target investors with follow-up meetings scheduled', 'Vendor list reviewed and 3+ contracts renegotiated with signed amendments'"
    }
  ],
  "top_3_priorities": [
    {
      "priority": "Short action label",
      "why_now": "One sentence on urgency",
      "expected_impact": "Quantified expected outcome"
    }
  ],
  "blind_spots": ["2-3 things the founder probably isn't thinking about"],
  "key_risks": [
    {
      "risk": "A mini-paragraph (3-5 sentences) describing a specific risk scenario. Start with WHAT could go wrong in concrete terms, then describe WHY it is likely given the company's current data, and HOW SEVERE the consequences would be. Example: 'Your top 3 accounts represent over 60% of monthly revenue. If any one of them churns — due to budget cuts, competitive displacement, or contract non-renewal — you would lose approximately $9K/month in recurring revenue overnight. At your current burn rate, this would reduce runway from 9 months to under 5 months, pushing you into crisis territory where fundraising becomes a rescue operation rather than a growth round. The concentration risk is compounded by the fact that none of these accounts are on annual contracts, meaning they can leave with 30 days notice.'",
      "likelihood": "High, Medium, or Low",
      "contingency": "A specific, executable action plan written as 2-3 sentences. Example: 'Immediately initiate annual contract negotiations with all three accounts, offering a 15% discount for 12-month commitments. In parallel, activate your pipeline of 10 warm leads and target closing 2 new accounts within 60 days to reduce concentration below 40%.'",
      "pivot_deadline": "A specific, time-bound deadline by which the founder must make a decision or change course on this risk. Example: 'If customer concentration has not dropped below 40% by end of Q2, pivot to a self-serve product motion that does not depend on large accounts.' or 'Decide by March 15 whether to raise a bridge round or cut burn — waiting past that date means fundraising under duress.'"
    }
  ]
}

CRITICAL INSTRUCTION FOR key_risks: Generate 3-5 specific risks. Each "risk" field must be a MINI-PARAGRAPH (3-5 sentences) that tells a specific story: what could go wrong, why it is likely given the data, and what the impact would be. Do NOT write one-line risk labels — write a vivid scenario paragraph. Each "contingency" field must be 2-3 sentences of specific, executable actions — not vague advice. Each "pivot_deadline" field must be a specific, time-bound deadline stating WHEN the founder must decide or change course — not vague timing like 'soon' but a concrete date, milestone, or metric threshold that triggers a pivot. Write as if handing an emergency playbook to an operator. Reference the company's actual numbers.

CRITICAL INSTRUCTION FOR execution_playbook: Generate 6-10 SPECIFIC action items that the founder can forward directly to their team. Group them into phases:
- Phase 1: Preparation (Week 1-2) — what to get ready, audits, analysis, team alignment
- Phase 2: Execution (Week 3-6) — the core actions, launches, negotiations, outreach
- Phase 3: Optimization (Week 7-8) — measure results, iterate, course-correct
Each action must be a clear instruction — not vague advice like 'improve sales'. Write them as if you are handing a to-do list to an operator. Use the company's actual numbers to set targets. The playbook should be so specific that a team member could execute it without asking clarifying questions. Each item MUST include a 'definition_of_done' field describing the verifiable completion criteria."""
    
    try:
        from server.lib.llm.llm_router import get_llm_router, TaskType
        llm_router = get_llm_router(
            db_session=db,
            company_id=company_id,
            user_id=current_user.id
        )
        
        result = llm_router.chat(
            messages=[{"role": "user", "content": f"Provide a strategic diagnosis for this company:\n\n{company_context}"}],
            task_type=TaskType.FINANCIAL_ANALYSIS,
            model="gpt-4o",
            system=system_prompt,
            temperature=0.6,
            max_tokens=8000,
        )
        
        import json, re
        content = result.get("content", "{}")
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        content = re.sub(r',\s*}', '}', content)
        content = re.sub(r',\s*]', ']', content)
        
        try:
            diagnosis = json.loads(content)
        except json.JSONDecodeError:
            first_brace = content.find('{')
            last_brace = content.rfind('}')
            if first_brace != -1 and last_brace != -1:
                content = content[first_brace:last_brace + 1]
                content = re.sub(r',\s*}', '}', content)
                content = re.sub(r',\s*]', ']', content)
                diagnosis = json.loads(content)
            else:
                raise
        diagnosis["company_name"] = company.name
        diagnosis["generated_at"] = datetime.utcnow().isoformat()
        diagnosis["model_used"] = result.get("model", "unknown")
        
        return diagnosis
        
    except Exception as e:
        import traceback
        logger.error(f"Strategic diagnosis failed: {traceback.format_exc()}")
        growth_text = "Revenue growth is positive, which is encouraging, but it is not yet enough to close the gap between what you earn and what you spend." if growth > 0 else f"Revenue growth is at {growth:.1f}%, which means the gap between what you earn and what you spend is not closing."
        crisis_months = max(1, int(runway_months - 2))
        daily_burn = burn / 30
        weekly_burn = burn / 4
        cash_at_crisis = max(0, cash - burn * crisis_months)
        be_growth_text = f" Revenue would need to grow by {breakeven_growth_needed:.0f}% month-over-month to reach break-even, which is significantly above your current trajectory of {growth:.1f}%." if revenue > 0 and breakeven_growth_needed > 0 else ""

        if runway_months < 12:
            rec_headline = "Cut Monthly Burn by 25% and Launch an Emergency Revenue Sprint"
            rec_p1 = f"Your most urgent priority is survival. With ${cash:,.0f} in the bank and a net monthly burn of ${net_burn:,.0f}, you have roughly {runway_months:.0f} months before cash runs out. The single highest-leverage action right now is to reduce burn immediately. This means auditing every vendor contract, pausing all non-essential hiring, consolidating overlapping tools, and renegotiating payment terms where possible. A 25% burn reduction would extend your runway by approximately {runway_months * 0.25 / (1 - 0.25):.0f} months — time that could mean the difference between a strong fundraise and a fire sale."
            rec_p2 = f"If you wait even 30 days to act, you will have consumed another ${burn:,.0f}, and your negotiating position with investors, vendors, and partners weakens with every passing week. The trade-off is real: cutting costs may slow product development and strain team morale. But the alternative — running out of cash entirely — eliminates all options. Every week of delay costs you ${weekly_burn:,.0f} and makes each subsequent decision more constrained."
            rec_p3 = f"Start this week. Pull your team leads into a room, lay out the numbers, and identify the three largest non-essential cost lines. Simultaneously, identify your highest-conversion revenue channels and double down on them. The goal is not just to cut — it is to buy yourself the runway to execute a focused revenue sprint that changes the trajectory."
            rec_narrative = f"{rec_p1}\n\n{rec_p2}\n\n{rec_p3}"
        else:
            rec_headline = "Accelerate Revenue Growth While Maintaining Capital Efficiency"
            rec_p1 = f"With {runway_months:.0f} months of runway and ${cash:,.0f} in reserves, you are not in immediate danger — but you are also not in a position of strength. Your current revenue of ${revenue:,.0f}/month growing at {growth:.1f}% is not on a trajectory to reach profitability before your cash runs out. The highest-leverage move right now is to accelerate revenue growth while keeping burn flat. This means reallocating resources from infrastructure and internal tooling toward direct revenue-generating activities."
            rec_p2 = f"The trade-off is clear: investing aggressively in growth now means accepting some short-term inefficiency, but the compounding effect of even a few additional percentage points of monthly growth will dramatically extend your effective runway and strengthen your position for future fundraising. If you wait 2-3 months to make this shift, you will have spent ${burn * 2.5:,.0f} without meaningfully changing your trajectory, and your fundraising window will be narrower."
            rec_p3 = f"Start by identifying your top-performing acquisition channel and allocating 80% of marketing resources there. Simultaneously, have your product team audit which features drive the most upgrades and retention — then ruthlessly prioritize those on the roadmap. Schedule a board update within 2 weeks to align stakeholders on the growth-first strategy and secure any incremental budget needed for the push."
            rec_narrative = f"{rec_p1}\n\n{rec_p2}\n\n{rec_p3}"

        urgency = f"Act within the next {'2 weeks' if runway_months < 6 else '30 days'}. At your current burn of ${burn:,.0f}/month, each day of inaction costs ${daily_burn:,.0f}. {'Your fundraising window effectively closes when you drop below 3 months of runway, which happens in approximately ' + f'{max(1, int(runway_months - 3)):.0f}' + ' months.' if runway_months < 12 else 'This decision becomes materially less effective after 60 days as your runway shortens and fundraising leverage decreases.'}"

        inaction_p1 = f"If no action is taken, at your current burn rate of ${burn:,.0f}/month against revenue of ${revenue:,.0f}/month, runway will be exhausted by approximately {exhaustion_date}.{be_growth_text} The math is unforgiving: every month that passes without a change in trajectory consumes ${net_burn:,.0f} in net cash."
        inaction_p2 = f"The consequences begin well before cash actually hits zero. Within {max(1, crisis_months - 2)} months, your cash position will be visible to employees — expect your best people to start exploring other options. Within {crisis_months} months, you will have approximately ${cash_at_crisis:,.0f} remaining, which puts you below the threshold where investors consider you a viable investment. At that point, fundraising shifts from 'raising a round' to 'negotiating a rescue' — terms become punitive, dilution becomes severe, and board control may shift."
        inaction_p3 = f"By the time cash reserves approach zero, your options narrow to three: a distressed acquisition at a fraction of your peak valuation, a bridge round with onerous terms from existing investors, or an orderly wind-down. None of these outcomes are inevitable today — but they become increasingly likely with each month of inaction."

        return {
            "situation_narrative": f"{company.name} is currently burning ${burn:,.0f}/month against ${revenue:,.0f} in monthly revenue. At this rate, you have approximately {runway_months:.1f} months of runway remaining. {growth_text} This puts you in a {'critical' if runway_months < 6 else 'challenging'} position where decisive action in the next {'2-4 weeks' if runway_months < 6 else '1-2 months'} will significantly impact your outcomes.",
            "recommendation_headline": rec_headline,
            "recommendation_narrative": rec_narrative,
            "urgency_text": urgency,
            "inaction_narrative": f"{inaction_p1}\n\n{inaction_p2}\n\n{inaction_p3}",
            "diagnosis_narrative": f"Based on your current metrics, {company.name} has approximately {runway_months:.0f} months of runway at the current burn rate of ${burn:,.0f}/month. {growth_text} Focus on extending runway while pursuing growth opportunities.",
            "company_stage_label": "Early Revenue" if revenue > 0 else "Pre-Revenue",
            "health_score": min(100, max(10, int(runway_months * 5 + growth * 2))),
            "health_label": "Stable" if runway_months > 12 else ("Concerning" if runway_months > 6 else "Critical"),
            "inaction_projection": {
                "months_to_crisis": crisis_months,
                "crisis_description": f"Cash reserves depleted at current burn rate of ${burn:,.0f}/month",
                "probability": 70 if runway_months < 12 else 40,
                "cash_at_crisis": 0,
                "key_trigger": "Cash balance drops below 2 months of operating expenses"
            },
            "execution_playbook": _build_fallback_playbook(burn, revenue, cash, runway_months, net_burn, growth, weekly_burn, daily_burn),
            "top_3_priorities": [
                {"priority": "Extend runway", "why_now": "Current runway is limited", "expected_impact": "Add 3-6 months of operating time"},
                {"priority": "Accelerate revenue", "why_now": "Revenue growth compounds over time", "expected_impact": "Reduce dependency on external funding"},
                {"priority": "Optimize burn", "why_now": "Every dollar saved extends runway", "expected_impact": "10-20% burn reduction possible"}
            ],
            "blind_spots": [
                "Customer concentration risk if relying on few large accounts",
                "Team capacity constraints that could limit growth execution",
                "Market timing risk as conditions may shift"
            ],
            "key_risks": _build_fallback_key_risks(burn, revenue, cash, runway_months, net_burn, growth),
            "company_name": company.name,
            "generated_at": datetime.utcnow().isoformat(),
            "model_used": "fallback",
            "error": str(e)
        }


@router.get("/companies/{company_id}/decisions/latest", response_model=Dict[str, Any])
def get_latest_decisions(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    from server.models.scenario import Scenario
    scenarios = db.query(Scenario).filter(Scenario.company_id == company_id).all()
    
    if not scenarios:
        raise HTTPException(status_code=404, detail="No scenarios found")
    
    latest_decision = None
    for scenario in scenarios:
        sim_runs = db.query(SimulationRun).filter(
            SimulationRun.scenario_id == scenario.id
        ).all()
        
        for run in sim_runs:
            decision = db.query(Decision).filter(
                Decision.simulation_run_id == run.id
            ).order_by(Decision.created_at.desc()).first()
            
            if decision:
                if latest_decision is None or decision.created_at > latest_decision.created_at:
                    latest_decision = decision
    
    if not latest_decision:
        raise HTTPException(status_code=404, detail="No decisions found")
    
    return {
        "id": latest_decision.id,
        "recommendations": latest_decision.recommended_actions_json,
        "created_at": latest_decision.created_at.isoformat()
    }


@router.get("/companies/{company_id}/decisions")
def list_company_decisions(
    company_id: int,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    query = db.query(CompanyDecision).filter(CompanyDecision.company_id == company_id)
    
    if status:
        query = query.filter(CompanyDecision.status == status)
    
    decisions = query.order_by(CompanyDecision.created_at.desc()).all()
    
    return {
        "decisions": [d.to_dict() for d in decisions],
        "total": len(decisions)
    }


@router.get("/companies/{company_id}/decisions/{decision_id}")
def get_company_decision(
    company_id: int,
    decision_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    try:
        decision_uuid = uuid_lib.UUID(decision_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid decision ID format")
    
    decision = db.query(CompanyDecision).filter(
        CompanyDecision.id == decision_uuid,
        CompanyDecision.company_id == company_id
    ).first()
    
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    
    return decision.to_dict()


@router.post("/companies/{company_id}/decisions")
def create_company_decision(
    company_id: int,
    request: CreateDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    decision = CompanyDecision(
        company_id=company_id,
        title=request.title,
        context=request.context,
        options_json=[o.model_dump() for o in request.options],
        recommendation_json=request.recommendation.model_dump() if request.recommendation else {},
        status=request.status,
        owner=request.owner,
        tags=request.tags,
        confidence=request.confidence,
        sources_json=request.sources
    )
    
    db.add(decision)
    db.commit()
    db.refresh(decision)
    
    return decision.to_dict()


@router.patch("/companies/{company_id}/decisions/{decision_id}")
def update_company_decision(
    company_id: int,
    decision_id: str,
    request: UpdateDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    try:
        decision_uuid = uuid_lib.UUID(decision_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid decision ID format")
    
    decision = db.query(CompanyDecision).filter(
        CompanyDecision.id == decision_uuid,
        CompanyDecision.company_id == company_id
    ).first()
    
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    
    if request.title is not None:
        decision.title = request.title
    if request.context is not None:
        decision.context = request.context
    if request.options is not None:
        decision.options_json = [o.model_dump() for o in request.options]
    if request.recommendation is not None:
        decision.recommendation_json = request.recommendation.model_dump()
    if request.status is not None:
        decision.status = request.status
    if request.owner is not None:
        decision.owner = request.owner
    if request.tags is not None:
        decision.tags = request.tags
    if request.confidence is not None:
        decision.confidence = request.confidence
    
    decision.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(decision)
    
    return decision.to_dict()


@router.delete("/companies/{company_id}/decisions/{decision_id}")
def delete_company_decision(
    company_id: int,
    decision_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    try:
        decision_uuid = uuid_lib.UUID(decision_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid decision ID format")
    
    decision = db.query(CompanyDecision).filter(
        CompanyDecision.id == decision_uuid,
        CompanyDecision.company_id == company_id
    ).first()
    
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    
    db.delete(decision)
    db.commit()
    
    return {"success": True, "message": "Decision deleted"}
