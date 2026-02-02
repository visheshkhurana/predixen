"""
Response Formatter for Natural Copilot Conversations.

Enforces consistent output formatting based on response mode.
"""
from typing import Dict, Any, List, Optional
from enum import Enum


class ResponseMode(Enum):
    EXPLAIN = "explain"
    COMPARE = "compare"
    PLAN = "plan"
    TEACH = "teach"
    JSON = "json"


def format_response_by_mode(
    output: Dict[str, Any],
    mode: str,
    provenance: Optional[Dict[str, Any]] = None,
    session_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Format agent output according to the specified response mode.
    
    Args:
        output: Raw agent output
        mode: Response mode (explain, compare, plan, teach, json)
        provenance: Provenance information for citations
        session_context: Session context for debugging
        
    Returns:
        Formatted output with mode-specific structure
    """
    formatted = output.copy()
    
    if mode == "json":
        formatted = format_json_mode(output, provenance)
    elif mode == "compare":
        formatted = format_compare_mode(output, provenance)
    elif mode == "plan":
        formatted = format_plan_mode(output, provenance)
    elif mode == "teach":
        formatted = format_teach_mode(output)
    else:
        formatted = format_explain_mode(output, provenance)
    
    return formatted


def format_explain_mode(output: Dict[str, Any], provenance: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Format output for EXPLAIN mode - natural language with citations."""
    formatted = output.copy()
    
    if provenance and output.get("executive_summary"):
        summary = output["executive_summary"]
        if isinstance(summary, list) and len(summary) > 0:
            citation = f" (Run #{provenance.get('runId', 'N/A')}, {provenance.get('runTimestamp', 'N/A')[:10] if provenance.get('runTimestamp') else 'N/A'})"
            summary_with_cite = [s + citation if i == 0 else s for i, s in enumerate(summary)]
            formatted["executive_summary"] = summary_with_cite
    
    return formatted


def format_compare_mode(output: Dict[str, Any], provenance: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Format output for COMPARE mode - side-by-side comparison."""
    formatted = output.copy()
    
    if not formatted.get("comparison_table"):
        formatted["comparison_table"] = []
    
    if formatted.get("strategy_options"):
        comparison_rows = []
        for i, option in enumerate(formatted["strategy_options"][:2]):
            comparison_rows.append({
                "metric": option.get("title", f"Option {i+1}"),
                "description": option.get("description", ""),
                "impact": option.get("impact", "")
            })
        formatted["comparison_table"] = comparison_rows
    
    return formatted


def format_plan_mode(output: Dict[str, Any], provenance: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Format output for PLAN mode - actionable recommendations."""
    formatted = output.copy()
    
    if formatted.get("recommendations"):
        prioritized = []
        for i, rec in enumerate(formatted["recommendations"][:5]):
            prioritized.append({
                "priority": i + 1,
                "action": rec.get("action", ""),
                "expected_impact": rec.get("expected_impact", ""),
                "timeline": rec.get("timeline", ""),
                "feasibility": rec.get("feasibility", "Medium")
            })
        formatted["action_plan"] = prioritized
    
    return formatted


def format_teach_mode(output: Dict[str, Any]) -> Dict[str, Any]:
    """Format output for TEACH mode - educational explanations."""
    formatted = output.copy()
    
    formatted["teaching_elements"] = {
        "definitions": [],
        "examples": [],
        "metaphors": []
    }
    
    return formatted


def format_json_mode(output: Dict[str, Any], provenance: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Format output for JSON mode - structured API-friendly output."""
    json_output = {
        "data": {
            "executive_summary": output.get("executive_summary", []),
            "financials": output.get("financials"),
            "recommendations": output.get("recommendations"),
            "strategy_options": output.get("strategy_options"),
        },
        "provenance": provenance,
        "metadata": {
            "response_mode": "json",
            "generated_at": None
        }
    }
    
    return json_output


def ensure_citations(
    output: Dict[str, Any],
    provenance: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Ensure all numeric values in the output have proper citations.
    
    This adds provenance references to numeric claims when not already present.
    """
    if not provenance:
        return output
    
    citation_suffix = f" [Run #{provenance.get('runId', 'N/A')}]"
    
    if output.get("financials"):
        financials = output["financials"]
        if financials.get("runway") and not str(financials.get("runway", "")).endswith("]"):
            financials["runway_citation"] = citation_suffix
        if financials.get("survival_rate") and not str(financials.get("survival_rate", "")).endswith("]"):
            financials["survival_rate_citation"] = citation_suffix
    
    return output


def extract_causal_drivers(
    output: Dict[str, Any],
    simulation_result: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Extract causal drivers from agent output or simulation results.
    
    Returns top 3 drivers ranked by impact.
    """
    drivers = []
    
    if simulation_result and simulation_result.get("sensitivity"):
        sensitivity = simulation_result["sensitivity"]
        sorted_factors = sorted(
            sensitivity.items(),
            key=lambda x: abs(x[1]) if isinstance(x[1], (int, float)) else 0,
            reverse=True
        )
        for name, impact in sorted_factors[:3]:
            drivers.append({
                "name": name,
                "impact": f"{impact:+.1f}" if isinstance(impact, (int, float)) else str(impact),
                "direction": "positive" if isinstance(impact, (int, float)) and impact > 0 else "negative"
            })
    
    if not drivers and output.get("recommendations"):
        for rec in output["recommendations"][:3]:
            drivers.append({
                "name": rec.get("action", "Unknown"),
                "impact": rec.get("expected_impact", "N/A"),
                "direction": "recommendation"
            })
    
    return drivers
