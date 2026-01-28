"""
Router/Orchestrator Agent for Fund Flow Copilot.

Routes work to specialist agents (CFO, Market, Strategy),
maintains Company Knowledge Base, and delivers final structured answers.
"""
import re
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .base import (
    BaseAgent, AgentResponse, AgentType, 
    CompanyKnowledgeBase, ConfidenceLevel
)

logger = logging.getLogger(__name__)


ROUTER_SYSTEM_PROMPT = """You are Fund Flow Copilot Orchestrator. Your job is to route work to specialist agents (CFO, Market, Strategy), maintain a shared Company Knowledge Base (CKB), and deliver a final, structured, decision-useful answer.

Core principles:
- Be accurate. Never invent numbers, customers, benchmarks, or citations.
- Separate facts (from docs/web/tools) from assumptions (clearly labeled).
- Prefer structured outputs: tables, bullet lists, checklists.
- Keep a running CKB: company overview, model, key financials, ICP, competitors, risks, decisions made.

Default base currency: USD.
Always display financial magnitudes in human format: 14,500,000 → USD 14.5M.

When documents are uploaded:
- Extract and normalize first, then advise.
- If extraction is partial/uncertain, say what is missing and what you assumed.

Output format (final answer):
- Executive Summary (5 bullets max)
- Company Snapshot (what we know; 6–10 bullets)
- Financials (table + key insights) [if available]
- Market & Customers (ICP + top target customers + competitors)
- Strategy Options (2–4 options with tradeoffs)
- Recommendations (ranked, with why + first steps)
- Assumptions & Data Gaps (explicit)
- Next Questions (max 5)

Data rules:
- Never hallucinate numbers or named customers. If unknown, say "Not in the provided documents".
- If web data conflicts with doc data, prioritize documents; note discrepancy.
"""


@dataclass
class RoutingDecision:
    """Decision about which agents to call."""
    call_cfo: bool = False
    call_market: bool = False
    call_strategy: bool = False
    call_decision_advisor: bool = False
    reasoning: str = ""


class RouterAgent(BaseAgent):
    """
    Router/Orchestrator that determines which specialist agents to call
    and merges their responses into a final structured output.
    
    Uses Gemini Flash via LLM Router for fast orchestration and response synthesis.
    Passes LLM Router to child agents for model-specific tasks:
    - CFO Agent → GPT-4o (financial analysis)
    - Market Agent → Claude Sonnet (market research)
    - Strategy Agent → Claude Sonnet (strategy/planning)
    """
    
    CFO_KEYWORDS = [
        "extract", "financials", "metrics", "run rate", "runway", "statements",
        "revenue", "burn", "margin", "p&l", "balance sheet", "cash flow",
        "arpu", "cac", "ltv", "churn", "mrr", "arr", "ebitda", "opex"
    ]
    
    MARKET_KEYWORDS = [
        "competitors", "customers", "icp", "benchmarks", "pricing", "tam",
        "trends", "market size", "industry", "segments", "target market",
        "buyer persona", "competition", "market research", "differentiate",
        "differentiation", "compete", "competitive advantage", "market position"
    ]
    
    STRATEGY_KEYWORDS = [
        "new verticals", "product strategy", "gtm", "expansion", "positioning",
        "business ideas", "growth strategy", "go to market", "roadmap",
        "pivot", "business model", "value proposition", "moat", "defensibility",
        "differentiate", "differentiation", "strategy", "strategic"
    ]
    
    DECISION_KEYWORDS = [
        "how can i", "what should i", "how do i", "should i",
        "extend runway", "reduce burn", "increase revenue", "cut costs",
        "delay fundrais", "postpone round", "when should", "what if",
        "survive longer", "last longer", "stretch cash", "hiring freeze",
        "layoff", "simulate", "scenario", "compare options", "what happens",
        "improve position", "is it worth", "trade-off", "tradeoff"
    ]
    
    def __init__(self, llm_router=None):
        super().__init__(AgentType.ROUTER, llm_router)
    
    def determine_routing(self, query: str, has_document: bool = False) -> RoutingDecision:
        """Determine which agents to call based on the query."""
        query_lower = query.lower()
        
        decision = RoutingDecision()
        reasons = []
        
        if any(kw in query_lower for kw in self.DECISION_KEYWORDS):
            decision.call_decision_advisor = True
            reasons.append("Decision-first analysis with simulations")
        
        if has_document or any(kw in query_lower for kw in self.CFO_KEYWORDS):
            decision.call_cfo = True
            reasons.append("Financial analysis needed")
        
        if any(kw in query_lower for kw in self.MARKET_KEYWORDS):
            decision.call_market = True
            reasons.append("Market research needed")
        
        if any(kw in query_lower for kw in self.STRATEGY_KEYWORDS):
            decision.call_strategy = True
            reasons.append("Strategy advice needed")
        
        if not any([decision.call_cfo, decision.call_market, decision.call_strategy, decision.call_decision_advisor]):
            decision.call_cfo = True
            decision.call_strategy = True
            reasons.append("General advisory - using CFO + Strategy")
        
        decision.reasoning = "; ".join(reasons)
        return decision
    
    async def process(
        self, 
        query: str, 
        ckb: CompanyKnowledgeBase,
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Process query by routing to appropriate agents and merging responses."""
        
        has_document = context.get("has_document", False)
        routing = self.determine_routing(query, has_document)
        
        self.logger.info(f"Routing decision: {routing}")
        
        agent_responses: List[AgentResponse] = []
        
        if routing.call_decision_advisor:
            from .decision_advisor import DecisionAdvisorAgent
            advisor = DecisionAdvisorAgent(llm_router=self.llm_router)
            advisor_response = await advisor.process(query, ckb, context)
            agent_responses.append(advisor_response)
            
            if advisor_response.structured_output.get("recommendation"):
                ckb.decisions_v2.append({
                    "query": query,
                    "recommendation": advisor_response.structured_output.get("recommendation"),
                    "simulations": advisor_response.structured_output.get("simulations", [])
                })
        
        if routing.call_cfo and not routing.call_decision_advisor:
            from .cfo_agent import CFOAgent
            cfo = CFOAgent(llm_router=self.llm_router)
            cfo_response = await cfo.process(query, ckb, context)
            agent_responses.append(cfo_response)
            
            if cfo_response.structured_output.get("financials"):
                ckb.financials.update(cfo_response.structured_output.get("financials", {}))
        
        if routing.call_market:
            from .market_agent import MarketAgent
            market = MarketAgent(llm_router=self.llm_router)
            market_response = await market.process(query, ckb, context)
            agent_responses.append(market_response)
            
            if market_response.structured_output.get("competitors"):
                ckb.competitors = market_response.structured_output.get("competitors", [])
            if market_response.structured_output.get("icp"):
                ckb.icp = market_response.structured_output.get("icp", {})
        
        if routing.call_strategy and not routing.call_decision_advisor:
            from .strategy_agent import StrategyAgent
            strategy = StrategyAgent(llm_router=self.llm_router)
            strategy_response = await strategy.process(query, ckb, context)
            agent_responses.append(strategy_response)
            
            if strategy_response.structured_output.get("strategy"):
                ckb.strategy.update(strategy_response.structured_output.get("strategy", {}))
        
        merged = self._merge_responses(agent_responses, ckb)
        
        return merged
    
    def _merge_responses(
        self, 
        responses: List[AgentResponse],
        ckb: CompanyKnowledgeBase
    ) -> AgentResponse:
        """Merge responses from multiple agents into a unified response."""
        
        all_findings = []
        all_assumptions = []
        all_risks = []
        all_questions = []
        merged_output = {}
        decision_advisor_output = None
        
        for resp in responses:
            all_findings.extend(resp.findings)
            all_assumptions.extend(resp.assumptions)
            all_risks.extend(resp.risks)
            all_questions.extend(resp.next_questions[:3])
            merged_output[resp.agent_type.value] = resp.structured_output
            
            if resp.decision_advisor_output:
                decision_advisor_output = resp.decision_advisor_output
        
        unique_findings = list(dict.fromkeys(all_findings))[:10]
        unique_assumptions = list(dict.fromkeys(all_assumptions))
        unique_risks = list(dict.fromkeys(all_risks))
        unique_questions = list(dict.fromkeys(all_questions))[:5]
        
        confidence_levels = [r.confidence for r in responses]
        if ConfidenceLevel.LOW in confidence_levels:
            overall_confidence = ConfidenceLevel.LOW
        elif ConfidenceLevel.MEDIUM in confidence_levels:
            overall_confidence = ConfidenceLevel.MEDIUM
        else:
            overall_confidence = ConfidenceLevel.HIGH
        
        final_output = self._structure_final_output(
            merged_output, ckb, unique_findings, unique_questions
        )
        
        synthesis = self._synthesize_response(unique_findings, unique_risks, ckb)
        
        return AgentResponse(
            agent_type=AgentType.ROUTER,
            findings=unique_findings,
            structured_output=final_output,
            assumptions=unique_assumptions,
            risks=unique_risks,
            next_questions=unique_questions,
            confidence=overall_confidence,
            raw_response=synthesis or "",
            decision_advisor_output=decision_advisor_output
        )
    
    def _structure_final_output(
        self,
        merged: Dict[str, Any],
        ckb: CompanyKnowledgeBase,
        findings: List[str],
        questions: List[str]
    ) -> Dict[str, Any]:
        """Structure the final output in the prescribed format."""
        
        executive_summary = findings[:5] if findings else ["No specific findings from analysis."]
        
        company_snapshot = [
            f"Company: {ckb.company_name}",
            f"Industry: {ckb.industry or 'Not specified'}",
            f"Stage: {ckb.stage or 'Not specified'}",
            f"Base Currency: {ckb.currency}"
        ]
        
        if ckb.financials:
            fin = ckb.financials
            if fin.get("revenue"):
                company_snapshot.append(f"Revenue: {self.format_currency(fin['revenue'], ckb.currency)}")
            if fin.get("burn_rate"):
                company_snapshot.append(f"Burn Rate: {self.format_currency(fin['burn_rate'], ckb.currency)}/mo")
            if fin.get("runway_months"):
                company_snapshot.append(f"Runway: {fin['runway_months']} months")
        
        return {
            "executive_summary": executive_summary,
            "company_snapshot": company_snapshot,
            "financials": merged.get("cfo", {}).get("financials"),
            "market_and_customers": {
                "icp": merged.get("market", {}).get("icp"),
                "target_customers": merged.get("market", {}).get("target_customers"),
                "competitors": merged.get("market", {}).get("competitors"),
                "differentiation": merged.get("market", {}).get("differentiation"),
                "benchmarks": merged.get("market", {}).get("benchmarks")
            },
            "strategy_options": merged.get("strategy", {}).get("options"),
            "recommendations": merged.get("strategy", {}).get("recommendations"),
            "assumptions_and_data_gaps": merged.get("cfo", {}).get("data_gaps", []),
            "next_questions": questions,
            "ckb": ckb.to_dict()
        }
    
    def _synthesize_response(
        self,
        findings: List[str],
        risks: List[str],
        ckb: CompanyKnowledgeBase
    ) -> Optional[str]:
        """
        Synthesize a cohesive executive summary from agent findings.
        Uses Gemini Flash for fast orchestration.
        """
        if not self.llm_router or not findings:
            return None
        
        findings_text = "\n".join([f"- {f}" for f in findings[:8]])
        risks_text = "\n".join([f"- {r}" for r in risks[:4]]) if risks else "No specific risks identified"
        
        prompt = f"""You are synthesizing insights from multiple financial analysis agents for {ckb.company_name}.

Key Findings:
{findings_text}

Key Risks:
{risks_text}

Provide a 2-3 sentence executive summary that captures the most important insights. Be direct, specific, and actionable."""
        
        try:
            response = self._call_llm(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are an expert financial analyst synthesizing insights for startup founders.",
                task_type="general_chat",
                temperature=0.5
            )
            return response if response else "Analysis complete. Review the detailed findings above for specific insights."
        except Exception as e:
            self.logger.warning(f"Synthesis generation failed: {e}")
            return "Analysis complete. Review the detailed findings above for specific insights."
