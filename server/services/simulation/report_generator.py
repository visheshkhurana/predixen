import json
import logging
from typing import Dict, Any

from .types import SimulationResult

logger = logging.getLogger(__name__)


async def generate_simulation_report(
    result: "SimulationResult",
    llm_client,
    model: str,
) -> Dict[str, Any]:
    key_events = []
    for action in result.all_actions:
        if action.action.value not in ("observe", "idle"):
            key_events.append(
                f"Month {action.round_num}: {action.agent_name} — {action.description}"
            )

    initial = result.config.initial_state
    final = result.final_state

    plausibility_warnings = []
    if final.mrr > 100_000_000:
        plausibility_warnings.append(f"WARNING: Final MRR (${final.mrr:,.0f}) exceeds $100M — likely unrealistic for a startup simulation.")
    if final.customers > 1_000_000:
        plausibility_warnings.append(f"WARNING: Final customer count ({final.customers:,}) exceeds 1M — likely unrealistic for a {result.config.total_rounds}-month simulation.")
    if initial.mrr > 0 and final.mrr / initial.mrr > 100:
        plausibility_warnings.append(f"WARNING: MRR grew {final.mrr / initial.mrr:.0f}x in {result.config.total_rounds} months — extreme growth detected.")
    if initial.customers > 0 and final.customers / max(initial.customers, 1) > 100:
        plausibility_warnings.append(f"WARNING: Customers grew {final.customers / max(initial.customers, 1):.0f}x — extreme growth detected.")

    warnings_text = "\n".join(plausibility_warnings) if plausibility_warnings else ""

    prompt = f"""Analyze this startup simulation and produce a structured report.

INITIAL STATE: MRR ${initial.mrr:,.0f}, Cash ${initial.cash:,.0f}, {initial.customers} customers, {initial.team_size} team
FINAL STATE: MRR ${final.mrr:,.0f}, Cash ${final.cash:,.0f}, {final.customers} customers, {final.team_size} team
SIMULATION LENGTH: {result.config.total_rounds} months
TOTAL EVENTS: {len(result.all_actions)}
{f"PLAUSIBILITY WARNINGS:{chr(10)}{warnings_text}" if warnings_text else ""}

KEY EVENTS:
{chr(10).join(key_events[:40])}

If any plausibility warnings are present, factor them into your analysis and note unrealistic results in the executive summary.

Generate a JSON report with:
{{
  "title": "Executive summary title",
  "executive_summary": "2-3 paragraph executive summary",
  "key_findings": ["finding 1", "finding 2", ...],
  "risk_factors": ["risk 1", "risk 2", ...],
  "opportunities": ["opp 1", "opp 2", ...],
  "recommendation": "Final strategic recommendation paragraph",
  "outcome_score": 0-100,
  "term_sheet_probability": 0-100
}}"""

    try:
        response = llm_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        survived = final.cash > 0 and final.runway_months > 0
        return {
            "title": "Simulation Complete" if survived else "Runway Exhausted",
            "executive_summary": f"Over {result.config.total_rounds} months the company "
                                 f"{'survived' if survived else 'ran out of cash'} with "
                                 f"MRR moving from ${initial.mrr:,.0f} to ${final.mrr:,.0f}.",
            "key_findings": [f"Final MRR: ${final.mrr:,.0f}", f"Final cash: ${final.cash:,.0f}"],
            "risk_factors": ["Simulation report generation encountered an error"],
            "opportunities": [],
            "recommendation": "Review the timeline for detailed agent decisions.",
            "outcome_score": 50 if survived else 20,
            "term_sheet_probability": 40 if survived else 10,
        }
