"""
Evaluation Runner - Runs evaluation suites to measure Copilot quality.
Provides scoring functions for citation coverage, structure compliance, hallucination risk, and PII leak detection.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session
import re

from server.lib.privacy.pii_redactor import detect_pii


@dataclass
class EvalScore:
    name: str
    score: float
    max_score: float
    details: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "score": self.score,
            "max_score": self.max_score,
            "percentage": round((self.score / self.max_score) * 100, 2) if self.max_score > 0 else 0,
            "details": self.details
        }


def calculate_citation_coverage(output: Dict[str, Any], citations: List[Dict[str, Any]]) -> EvalScore:
    """
    Calculate what percentage of claims have supporting citations.
    
    Args:
        output: The copilot response output
        citations: List of citations provided
    
    Returns:
        EvalScore with citation coverage percentage
    """
    claims = []
    
    for summary in output.get("executive_summary", []):
        claims.append(summary)
    
    for rec in output.get("recommendations", []):
        if "action" in rec:
            claims.append(rec["action"])
        if "rationale" in rec:
            claims.append(rec["rationale"])
    
    for assumption in output.get("assumptions", []):
        claims.append(assumption)
    
    if not claims:
        return EvalScore(
            name="citation_coverage",
            score=100,
            max_score=100,
            details={"total_claims": 0, "cited_claims": 0, "message": "No claims to evaluate"}
        )
    
    citation_texts = set()
    for citation in citations:
        if "snippet" in citation:
            citation_texts.add(citation["snippet"].lower()[:50])
    
    cited_claims = 0
    for claim in claims:
        claim_words = set(claim.lower().split())
        for cite_text in citation_texts:
            cite_words = set(cite_text.split())
            if len(claim_words & cite_words) >= 3:
                cited_claims += 1
                break
    
    coverage = (cited_claims / len(claims)) * 100 if claims else 100
    
    return EvalScore(
        name="citation_coverage",
        score=round(coverage, 2),
        max_score=100,
        details={
            "total_claims": len(claims),
            "cited_claims": cited_claims,
            "uncited_claims": len(claims) - cited_claims
        }
    )


def calculate_structure_compliance(output: Dict[str, Any]) -> EvalScore:
    """
    Check if the output contains all required sections.
    
    Required sections: executive_summary, recommendations, assumptions, risks
    Optional sections: financials, market_and_customers, strategy_options
    """
    required_sections = ["executive_summary", "recommendations", "assumptions", "risks"]
    optional_sections = ["financials", "market_and_customers", "strategy_options"]
    
    present_required = []
    missing_required = []
    present_optional = []
    
    for section in required_sections:
        value = output.get(section)
        if value and (isinstance(value, list) and len(value) > 0):
            present_required.append(section)
        elif value and isinstance(value, dict):
            present_required.append(section)
        else:
            missing_required.append(section)
    
    for section in optional_sections:
        if output.get(section):
            present_optional.append(section)
    
    required_score = len(present_required) / len(required_sections) * 70
    optional_score = len(present_optional) / len(optional_sections) * 30
    
    total_score = required_score + optional_score
    
    return EvalScore(
        name="structure_compliance",
        score=round(total_score, 2),
        max_score=100,
        details={
            "required_present": present_required,
            "required_missing": missing_required,
            "optional_present": present_optional,
            "required_score": round(required_score, 2),
            "optional_score": round(optional_score, 2)
        }
    )


def calculate_hallucination_risk(output: Dict[str, Any], citations: List[Dict[str, Any]]) -> EvalScore:
    """
    Identify potential hallucination risks - numbers or specific claims without citations.
    Lower score = higher risk.
    """
    number_pattern = re.compile(r'\$[\d,]+(?:\.\d+)?[KMB]?|\d+(?:\.\d+)?%|\d{4,}')
    
    all_text = []
    for summary in output.get("executive_summary", []):
        all_text.append(summary)
    for rec in output.get("recommendations", []):
        all_text.append(str(rec))
    
    combined_text = " ".join(all_text)
    numbers_found = number_pattern.findall(combined_text)
    
    citation_numbers = set()
    for citation in citations:
        snippet = citation.get("snippet", "")
        for num in number_pattern.findall(snippet):
            citation_numbers.add(num)
    
    uncited_numbers = []
    for num in numbers_found:
        if num not in citation_numbers:
            uncited_numbers.append(num)
    
    if not numbers_found:
        score = 100
    else:
        cited_ratio = (len(numbers_found) - len(uncited_numbers)) / len(numbers_found)
        score = cited_ratio * 100
    
    return EvalScore(
        name="hallucination_risk",
        score=round(score, 2),
        max_score=100,
        details={
            "total_numbers_found": len(numbers_found),
            "uncited_numbers": uncited_numbers[:10],
            "risk_level": "low" if score >= 80 else "medium" if score >= 50 else "high"
        }
    )


def check_pii_leak(output: Dict[str, Any]) -> EvalScore:
    """
    Check if any PII was leaked in the output.
    Score of 100 means no PII found.
    """
    all_text = []
    
    def extract_text(obj, depth=0):
        if depth > 10:
            return
        if isinstance(obj, str):
            all_text.append(obj)
        elif isinstance(obj, list):
            for item in obj:
                extract_text(item, depth + 1)
        elif isinstance(obj, dict):
            for value in obj.values():
                extract_text(value, depth + 1)
    
    extract_text(output)
    combined_text = " ".join(all_text)
    
    pii_findings = detect_pii(combined_text)
    
    if not pii_findings:
        score = 100
        risk_level = "none"
    else:
        total_pii = sum(f.get("count", 0) for f in pii_findings)
        if total_pii <= 2:
            score = 80
            risk_level = "low"
        elif total_pii <= 5:
            score = 50
            risk_level = "medium"
        else:
            score = 20
            risk_level = "high"
    
    return EvalScore(
        name="pii_leak_check",
        score=score,
        max_score=100,
        details={
            "pii_findings": pii_findings,
            "risk_level": risk_level
        }
    )


async def run_copilot_quality_eval(inputs: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """Run the copilot quality evaluation suite."""
    output = inputs.get("output", {})
    citations = inputs.get("citations", [])
    
    scores = [
        calculate_citation_coverage(output, citations),
        calculate_structure_compliance(output),
        calculate_hallucination_risk(output, citations),
        check_pii_leak(output)
    ]
    
    total_score = sum(s.score for s in scores)
    max_score = sum(s.max_score for s in scores)
    overall = (total_score / max_score) * 100 if max_score > 0 else 0
    
    return {
        "outputs": {
            "evaluated_output_preview": str(output)[:500]
        },
        "scores": {s.name: s.to_dict() for s in scores},
        "overall_score": round(overall, 2)
    }


async def run_extraction_accuracy_eval(inputs: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """Run the extraction accuracy evaluation suite."""
    extracted = inputs.get("extracted", {})
    expected = inputs.get("expected", {})
    tolerance = inputs.get("tolerance", 0.05)
    
    scores = []
    field_results = {}
    
    for field, expected_value in expected.items():
        actual_value = extracted.get(field)
        
        if actual_value is None:
            field_results[field] = {"status": "missing", "expected": expected_value, "actual": None}
            scores.append(0)
        elif isinstance(expected_value, (int, float)) and isinstance(actual_value, (int, float)):
            if expected_value == 0:
                match = actual_value == 0
            else:
                diff = abs(actual_value - expected_value) / abs(expected_value)
                match = diff <= tolerance
            
            field_results[field] = {
                "status": "match" if match else "mismatch",
                "expected": expected_value,
                "actual": actual_value,
                "within_tolerance": match
            }
            scores.append(100 if match else 0)
        else:
            match = str(actual_value).lower() == str(expected_value).lower()
            field_results[field] = {
                "status": "match" if match else "mismatch",
                "expected": expected_value,
                "actual": actual_value
            }
            scores.append(100 if match else 0)
    
    overall = sum(scores) / len(scores) if scores else 0
    
    return {
        "outputs": field_results,
        "scores": {
            "field_accuracy": {
                "score": overall,
                "max_score": 100,
                "percentage": overall,
                "details": field_results
            }
        },
        "overall_score": round(overall, 2)
    }


async def run_pii_redaction_eval(inputs: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """Run the PII redaction effectiveness evaluation suite."""
    from server.lib.privacy.pii_redactor import redact_text
    
    test_cases = inputs.get("test_cases", [
        {"text": "Contact john.doe@example.com for details", "expected_type": "email"},
        {"text": "Call me at 555-123-4567", "expected_type": "phone"},
        {"text": "Card: 4111111111111111", "expected_type": "card"},
        {"text": "API key: sk_test_abcdefghijklmnopqrstuvwxyz", "expected_type": "token"},
    ])
    
    results = []
    for test in test_cases:
        text = test.get("text", "")
        expected_type = test.get("expected_type")
        
        result = redact_text(text, mode="standard")
        
        found_type = None
        for finding in result.findings:
            if finding.get("type") == expected_type:
                found_type = expected_type
                break
        
        redacted = "[REDACTED_" in result.redacted_text
        
        results.append({
            "input": text[:50],
            "expected_type": expected_type,
            "found_type": found_type,
            "redacted": redacted,
            "success": found_type == expected_type and redacted
        })
    
    successful = sum(1 for r in results if r["success"])
    overall = (successful / len(results)) * 100 if results else 0
    
    return {
        "outputs": {"test_results": results},
        "scores": {
            "redaction_accuracy": {
                "score": overall,
                "max_score": 100,
                "percentage": overall,
                "details": {"successful": successful, "total": len(results)}
            }
        },
        "overall_score": round(overall, 2)
    }


async def run_evaluation_suite(suite_name: str, inputs: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """
    Run a specific evaluation suite.
    
    Args:
        suite_name: Name of the evaluation suite to run
        inputs: Input parameters for the evaluation
        db: Database session
    
    Returns:
        Dictionary with outputs, scores, and overall_score
    """
    suite_runners = {
        "copilot_quality": run_copilot_quality_eval,
        "extraction_accuracy": run_extraction_accuracy_eval,
        "pii_redaction": run_pii_redaction_eval
    }
    
    runner = suite_runners.get(suite_name)
    if not runner:
        raise ValueError(f"Unknown evaluation suite: {suite_name}")
    
    return await runner(inputs, db)
