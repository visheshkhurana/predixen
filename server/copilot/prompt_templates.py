"""
Prompt Templates for Natural Copilot Conversations.

Provides structured templates for common copilot interactions that are:
- Natural and founder-friendly
- Grounded in verified data
- Actionable and clear
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class ResponseMode(Enum):
    EXPLAIN = "explain"
    COMPARE = "compare"
    PLAN = "plan"
    TEACH = "teach"
    JSON = "json"


@dataclass
class PromptTemplate:
    name: str
    description: str
    system_prompt: str
    output_format: str


RESPONSE_MODE_INSTRUCTIONS = {
    ResponseMode.EXPLAIN: """
Response Mode: EXPLAIN
- Use natural language with numeric summaries
- Provide a one-paragraph summary first
- List key values with provenance citations
- Explain what drives the metrics
- Keep tone conversational but precise
""",
    ResponseMode.COMPARE: """
Response Mode: COMPARE
- Present a side-by-side comparison
- Highlight key differences between scenarios/runs
- Use a structured format: Metric | Scenario A | Scenario B | Delta
- Explain which scenario performs better and why
- Cite both run IDs for each comparison point
""",
    ResponseMode.PLAN: """
Response Mode: PLAN
- Focus on actionable recommendations
- List top 3-5 levers that would improve outcomes
- For each lever: expected impact direction and magnitude
- Prioritize by impact and feasibility
- Ground recommendations in simulation data
""",
    ResponseMode.TEACH: """
Response Mode: TEACH
- Explain concepts with definitions and examples
- Use visual metaphors where helpful
- Relate concepts to the user's specific context
- Include glossary-style explanations
- Make complex ideas accessible
""",
    ResponseMode.JSON: """
Response Mode: JSON
- Return structured, API-friendly output
- Use consistent field names
- Include all numeric values with full precision
- Include provenance metadata
- No narrative text, pure data
"""
}


PROMPT_TEMPLATES: Dict[str, PromptTemplate] = {
    "metric_summary": PromptTemplate(
        name="Metric Summary",
        description="Summarize metrics for a scenario from a specific run",
        system_prompt="""You are summarizing financial metrics for a startup founder.

Context:
- Company: {company_name}
- Scenario: {scenario_name} (scenarioId: {scenario_id})
- Run: {run_id} (timestamp: {run_timestamp})
- Data Snapshot: {snapshot_id}

Present a clear summary with:
1. One-sentence headline (e.g., "Runway P50 is 15.0 months with 68% survival probability")
2. Key metrics table with exact values
3. Top 3 drivers affecting these metrics
4. One actionable insight

CRITICAL: Every number must match the run data exactly. Cite runId with every metric.""",
        output_format="narrative_with_citations"
    ),
    
    "comparison": PromptTemplate(
        name="Scenario Comparison",
        description="Compare two scenarios or runs side-by-side",
        system_prompt="""You are comparing two scenarios/runs for a startup founder.

Context:
- Company: {company_name}
- Scenario A: {scenario_a_name} (runId: {run_id_a})
- Scenario B: {scenario_b_name} (runId: {run_id_b})

Present a clear comparison with:
1. Executive summary of which scenario performs better overall
2. Side-by-side metric comparison (use table format)
3. Key differences and what drives them
4. Recommendation on which path to pursue

CRITICAL: Every number must be from verified runs. Cite both runIds.""",
        output_format="comparison_table"
    ),
    
    "why_explanation": PromptTemplate(
        name="Why Explanation",
        description="Explain why a metric changed between runs",
        system_prompt="""You are explaining why metrics changed between two runs.

Context:
- Company: {company_name}
- Previous Run: {run_id_prev} (timestamp: {prev_timestamp})
- Current Run: {run_id_curr} (timestamp: {curr_timestamp})
- Metric of Interest: {metric_name}

Explain:
1. What changed: "{metric_name} went from X to Y"
2. Top 3 contributing factors ranked by impact
3. Which assumptions or inputs drove the change
4. Whether this is expected or surprising

Use causal language: "because", "due to", "as a result of".""",
        output_format="causal_explanation"
    ),
    
    "decision_advice": PromptTemplate(
        name="Decision Advice",
        description="Recommend actions to achieve a specific goal",
        system_prompt="""You are advising a founder on how to achieve a specific goal.

Context:
- Company: {company_name}
- Current State: {current_metrics}
- Goal: {goal_description}
- Constraints: {constraints}

Provide:
1. Top 3 levers that would move toward the goal
2. For each lever: expected impact direction and confidence
3. Trade-offs and risks
4. Recommended sequence of actions

Be opinionated but cite data to support recommendations.""",
        output_format="action_plan"
    ),
    
    "assumption_drilldown": PromptTemplate(
        name="Assumption Drilldown",
        description="List and explain assumptions affecting a metric",
        system_prompt="""You are explaining the assumptions behind a metric.

Context:
- Company: {company_name}
- Scenario: {scenario_name}
- Metric: {metric_name}
- Run: {run_id}

Present:
1. All assumptions that feed into this metric
2. Current value of each assumption
3. Sensitivity: how much would the metric change if assumption changed by 10%
4. Which assumptions are most uncertain

Help the founder understand what to validate.""",
        output_format="assumption_table"
    )
}


def detect_response_mode(message: str) -> ResponseMode:
    """Detect the intended response mode from the user's message."""
    message_lower = message.lower()
    
    if any(kw in message_lower for kw in ["compare", "vs", "versus", "difference between", "which is better"]):
        return ResponseMode.COMPARE
    
    if any(kw in message_lower for kw in ["plan", "recommend", "should i", "what should", "how to improve", "how can i"]):
        return ResponseMode.PLAN
    
    if any(kw in message_lower for kw in ["what is", "define", "explain concept", "teach me", "help me understand"]):
        return ResponseMode.TEACH
    
    if any(kw in message_lower for kw in ["json", "api", "structured", "raw data"]):
        return ResponseMode.JSON
    
    return ResponseMode.EXPLAIN


def detect_clarification_needed(message: str, session_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Detect if clarification is needed before answering."""
    message_lower = message.lower()
    
    if any(kw in message_lower for kw in ["changed", "went up", "went down", "different"]):
        if not session_context.get("lastRunId") and not session_context.get("baselineRunId"):
            return {
                "type": "comparison_target",
                "question": "Are you asking relative to baseline or the last run?",
                "options": ["BASELINE", "LAST RUN"]
            }
    
    if "scenario" in message_lower and not session_context.get("activeScenarioId"):
        return {
            "type": "scenario_selection",
            "question": "Which scenario would you like me to analyze?",
            "options": None
        }
    
    return None


def get_mode_instructions(mode: ResponseMode) -> str:
    """Get the instruction block for a response mode."""
    return RESPONSE_MODE_INSTRUCTIONS.get(mode, RESPONSE_MODE_INSTRUCTIONS[ResponseMode.EXPLAIN])


def format_provenance_block(
    company_id: int,
    scenario_id: Optional[int] = None,
    scenario_name: Optional[str] = None,
    run_id: Optional[int] = None,
    run_timestamp: Optional[str] = None,
    snapshot_id: Optional[str] = None
) -> str:
    """Format a provenance block for inclusion in responses."""
    lines = [
        "---",
        "**Provenance:**"
    ]
    lines.append(f"- CompanyId: {company_id}")
    if scenario_id:
        lines.append(f"- ScenarioId: {scenario_id}")
    if scenario_name:
        lines.append(f"- Scenario: {scenario_name}")
    if run_id:
        lines.append(f"- RunId: {run_id}")
    if run_timestamp:
        lines.append(f"- Timestamp: {run_timestamp}")
    if snapshot_id:
        lines.append(f"- DataSnapshotId: {snapshot_id[:16]}...")
    
    return "\n".join(lines)


def format_causal_summary(
    metric_name: str,
    old_value: float,
    new_value: float,
    drivers: List[Dict[str, Any]]
) -> str:
    """Format a causal explanation of metric changes."""
    direction = "increased" if new_value > old_value else "decreased"
    delta = abs(new_value - old_value)
    
    lines = [
        f"**{metric_name}** {direction} from {old_value:.1f} to {new_value:.1f} (delta: {delta:.1f})",
        "",
        "**Drivers (ranked by impact):**"
    ]
    
    for i, driver in enumerate(drivers[:3], 1):
        lines.append(f"{i}. {driver.get('name', 'Unknown')}: {driver.get('impact', 'N/A')}")
    
    return "\n".join(lines)
