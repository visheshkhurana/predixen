"""
Review/Reflection Agent for FounderConsole Copilot.

Validates other agents' outputs before presenting to the user.
Detects hallucinations, verifies calculations, checks assumptions
against Truth Scan data, and flags inconsistencies.
"""
import logging
import re
from typing import Dict, Any, List, Optional

from .base import (
    BaseAgent, AgentResponse, AgentType,
    CompanyKnowledgeBase, ConfidenceLevel
)

logger = logging.getLogger(__name__)


REVIEW_SYSTEM_PROMPT = """You are FounderConsole Review Agent: a rigorous quality-assurance layer.
Your job: verify other agents' outputs for accuracy, consistency, and groundedness.

Rules:
- Check every numeric claim against the provided truth_scan data.
- Flag any number that cannot be traced to verified company data or simulation results.
- Detect contradictions between different agents' outputs.
- Verify that recommendations are consistent with the company's financial reality.
- Check mathematical calculations (e.g., runway = cash / burn).
- Flag overly optimistic projections without supporting evidence.
- Ensure all currency values use consistent formatting.
- Mark each finding as VERIFIED, WARNING, or ERROR.

Output a structured review with:
1) Verification results for each major claim
2) Inconsistencies detected
3) Hallucination flags
4) Overall confidence assessment
5) Suggested corrections
"""


class ReviewAgent(BaseAgent):
    """
    Review/Reflection Agent that validates other agents' outputs
    before presenting results to the user.

    Uses GPT-4o via LLM Router for analytical verification.
    """

    def __init__(self, llm_router=None):
        super().__init__(AgentType.REVIEW, llm_router)

    async def process(
        self,
        query: str,
        ckb: CompanyKnowledgeBase,
        context: Dict[str, Any],
    ) -> AgentResponse:
        """Not used directly — use review_outputs instead."""
        return AgentResponse(agent_type=AgentType.REVIEW)

    async def review_outputs(
        self,
        agent_responses: List[AgentResponse],
        ckb: CompanyKnowledgeBase,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Review and validate outputs from other agents.

        Returns a review report with verification results,
        inconsistencies, and suggested corrections.
        """
        truth_scan = context.get("truth_scan", {})
        truth_metrics = truth_scan.get("metrics", {}) if isinstance(truth_scan, dict) else {}

        review = {
            "verified_claims": [],
            "warnings": [],
            "errors": [],
            "inconsistencies": [],
            "hallucination_flags": [],
            "confidence_adjustment": None,
            "overall_status": "PASS",
            "learning_caveats": [],
        }

        learning_caveats = self._check_recommendation_quality(context)
        if learning_caveats:
            review["learning_caveats"] = learning_caveats
            review["warnings"].extend([
                {"type": "learning_caveat", "detail": c} for c in learning_caveats
            ])

        for response in agent_responses:
            agent_name = response.agent_type.value

            claim_checks = self._verify_claims(
                response.findings, response.structured_output,
                truth_metrics, ckb
            )
            review["verified_claims"].extend(claim_checks["verified"])
            review["warnings"].extend(claim_checks["warnings"])
            review["errors"].extend(claim_checks["errors"])

            hallucinations = self._detect_hallucinations(
                response.findings, response.raw_response,
                truth_metrics, ckb
            )
            for h in hallucinations:
                h["source_agent"] = agent_name
            review["hallucination_flags"].extend(hallucinations)

        if len(agent_responses) > 1:
            inconsistencies = self._check_cross_agent_consistency(agent_responses)
            review["inconsistencies"] = inconsistencies

        math_errors = self._verify_math(agent_responses, ckb, truth_metrics)
        review["errors"].extend(math_errors)

        if review["errors"] or review["hallucination_flags"]:
            review["overall_status"] = "FAIL"
            review["confidence_adjustment"] = "DOWNGRADE"
        elif review["warnings"]:
            review["overall_status"] = "PASS_WITH_WARNINGS"
            review["confidence_adjustment"] = "CAUTION"

        if self.llm_router and agent_responses:
            llm_review = await self._llm_deep_review(
                agent_responses, ckb, context
            )
            if llm_review:
                review["llm_review"] = llm_review

        return review

    def _verify_claims(
        self,
        findings: List[str],
        structured_output: Dict[str, Any],
        truth_metrics: Dict[str, Any],
        ckb: CompanyKnowledgeBase,
    ) -> Dict[str, List[Dict[str, Any]]]:
        result = {"verified": [], "warnings": [], "errors": []}

        known_values = {}
        for key, val in truth_metrics.items():
            if isinstance(val, (int, float)):
                known_values[key] = val
            elif isinstance(val, dict) and "value" in val:
                known_values[key] = val["value"]

        if ckb.financials:
            for k, v in ckb.financials.items():
                if isinstance(v, (int, float)):
                    known_values[k] = v

        for finding in findings:
            numbers = re.findall(r'\$[\d,]+(?:\.\d+)?|\d+\.?\d*%|\d{1,3}(?:,\d{3})+', finding)
            if numbers:
                verified = False
                for num_str in numbers:
                    clean = num_str.replace('$', '').replace(',', '').replace('%', '')
                    try:
                        num_val = float(clean)
                        for known_key, known_val in known_values.items():
                            if isinstance(known_val, (int, float)):
                                if abs(num_val - known_val) < known_val * 0.05 or num_val == known_val:
                                    result["verified"].append({
                                        "claim": finding,
                                        "matched_metric": known_key,
                                        "status": "VERIFIED",
                                    })
                                    verified = True
                                    break
                    except (ValueError, ZeroDivisionError):
                        continue

                if not verified and numbers:
                    result["warnings"].append({
                        "claim": finding,
                        "reason": "Numeric claim could not be matched to verified data",
                        "status": "UNVERIFIED",
                    })

        return result

    def _detect_hallucinations(
        self,
        findings: List[str],
        raw_response: str,
        truth_metrics: Dict[str, Any],
        ckb: CompanyKnowledgeBase,
    ) -> List[Dict[str, Any]]:
        flags = []
        text = raw_response or " ".join(findings)
        if not text:
            return flags

        specificity_patterns = [
            r'exactly \d+',
            r'precisely \d+',
            r'we found that \d+',
            r'data shows \d+',
        ]
        for pattern in specificity_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                nums = re.findall(r'\d+', match)
                for num in nums:
                    num_val = int(num)
                    matched = False
                    for val in truth_metrics.values():
                        if isinstance(val, (int, float)) and abs(num_val - val) < val * 0.1:
                            matched = True
                            break
                    if not matched and num_val > 100:
                        flags.append({
                            "text": match,
                            "reason": "Specific numeric claim not found in verified data",
                            "severity": "warning",
                        })

        return flags

    def _check_cross_agent_consistency(
        self, responses: List[AgentResponse]
    ) -> List[Dict[str, Any]]:
        inconsistencies = []

        runway_values = {}
        revenue_values = {}
        burn_values = {}

        for resp in responses:
            agent = resp.agent_type.value
            output = resp.structured_output

            for text in resp.findings:
                runway_match = re.search(r'(\d+\.?\d*)\s*months?\s*(?:of\s+)?runway', text, re.IGNORECASE)
                if runway_match:
                    runway_values[agent] = float(runway_match.group(1))

                rev_match = re.search(r'\$(\d+(?:,\d{3})*(?:\.\d+)?)[KMB]?\s*(?:revenue|mrr)', text, re.IGNORECASE)
                if rev_match:
                    revenue_values[agent] = float(rev_match.group(1).replace(',', ''))

        if len(runway_values) > 1:
            vals = list(runway_values.values())
            if max(vals) - min(vals) > 3:
                inconsistencies.append({
                    "metric": "runway_months",
                    "values": runway_values,
                    "severity": "high",
                    "note": f"Runway estimates differ by {max(vals) - min(vals):.1f} months across agents",
                })

        return inconsistencies

    def _verify_math(
        self,
        responses: List[AgentResponse],
        ckb: CompanyKnowledgeBase,
        truth_metrics: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        errors = []

        cash = None
        burn = None
        stated_runway = None

        for key in ["cash_balance", "cash_on_hand", "cash"]:
            if key in truth_metrics:
                val = truth_metrics[key]
                cash = val if isinstance(val, (int, float)) else val.get("value") if isinstance(val, dict) else None
                if cash:
                    break

        for key in ["monthly_burn", "net_burn", "burn_rate"]:
            if key in truth_metrics:
                val = truth_metrics[key]
                burn = val if isinstance(val, (int, float)) else val.get("value") if isinstance(val, dict) else None
                if burn:
                    break

        for key in ["runway_months", "runway"]:
            if key in truth_metrics:
                val = truth_metrics[key]
                stated_runway = val if isinstance(val, (int, float)) else val.get("value") if isinstance(val, dict) else None
                if stated_runway:
                    break

        if cash and burn and burn > 0 and stated_runway:
            calculated_runway = cash / burn
            if abs(calculated_runway - stated_runway) > 2:
                errors.append({
                    "type": "math_error",
                    "description": f"Runway mismatch: cash(${cash:,.0f}) / burn(${burn:,.0f}) = {calculated_runway:.1f}mo but stated as {stated_runway:.1f}mo",
                    "severity": "high",
                    "correction": f"Runway should be approximately {calculated_runway:.1f} months",
                })

        return errors

    def _check_recommendation_quality(self, context: Dict[str, Any]) -> List[str]:
        caveats = []
        learning = context.get("learning_context")
        if not learning:
            return caveats

        low_quality = learning.get("low_quality_categories", [])
        for lq in low_quality:
            cat = lq.get("category", "")
            score = lq.get("score", 0)
            caveats.append(
                f"Historical data shows '{cat}' advice has had below-average effectiveness "
                f"(quality score: {score:.0f}%). Consider alternative approaches or add caveats."
            )

        pitfalls = learning.get("common_pitfalls", [])
        for p in pitfalls:
            caveats.append(p.get("warning", ""))

        return caveats

    async def _llm_deep_review(
        self,
        responses: List[AgentResponse],
        ckb: CompanyKnowledgeBase,
        context: Dict[str, Any],
    ) -> Optional[str]:
        if not self.llm_router:
            return None

        findings_text = []
        for resp in responses:
            agent_name = resp.agent_type.value
            for f in resp.findings[:3]:
                findings_text.append(f"[{agent_name}] {f}")

        if not findings_text:
            return None

        truth_summary = ""
        truth_scan = context.get("truth_scan", {})
        if isinstance(truth_scan, dict):
            metrics = truth_scan.get("metrics", {})
            if metrics:
                truth_items = []
                for k, v in list(metrics.items())[:10]:
                    if isinstance(v, (int, float)):
                        truth_items.append(f"{k}: {v}")
                    elif isinstance(v, dict) and "value" in v:
                        truth_items.append(f"{k}: {v['value']}")
                truth_summary = "\n".join(truth_items)

        prompt = f"""Review the following agent findings for {ckb.company_name} and check for:
1. Any numbers that contradict the verified data
2. Overly optimistic claims without evidence
3. Missing important caveats or risks
4. Logical inconsistencies between agents

Agent findings:
{chr(10).join(findings_text)}

Verified company data:
{truth_summary if truth_summary else "No verified data available — flag all specific numbers as unverified."}

Provide a brief review (3-4 sentences): are the findings trustworthy? Any red flags?"""

        try:
            response = self._call_llm(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=REVIEW_SYSTEM_PROMPT,
                task_type="financial_analysis",
                temperature=0.3,
            )
            return response
        except Exception as e:
            self.logger.warning(f"LLM review failed: {e}")
            return None
