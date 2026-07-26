import json
import logging
from typing import List, Optional

from .types import (
    AgentPersona, AgentAction, AgentType, ActionType,
    CompanyState, Sentiment,
)

logger = logging.getLogger(__name__)


def build_agent_system_prompt(agent: AgentPersona, company_state: CompanyState) -> str:
    return f"""You are {agent.name}, a {agent.agent_type.value} in a startup simulation.

PERSONA:
{agent.bio}

PERSONALITY TRAITS: {', '.join(agent.personality_traits)}
GOALS: {', '.join(agent.goals)}
EMOTIONAL TENDENCY: {agent.emotional_tendency} (-1=very pessimistic, 1=very optimistic)
RISK TOLERANCE: {agent.risk_tolerance} (0=risk-averse, 1=risk-seeking)

You must decide your next action based on the current company state and recent events.
You MUST respond with valid JSON only."""


def build_agent_decision_prompt(
    agent: AgentPersona,
    company_state: CompanyState,
    recent_actions: List[AgentAction],
    round_num: int,
    total_rounds: int,
    memory: List[str],
) -> str:
    recent_events = "\n".join([
        f"- [Month {a.round_num}] {a.agent_name} ({a.agent_type.value}): {a.description}"
        for a in recent_actions[-10:]
    ]) or "No recent events."

    memory_text = "\n".join([f"- {m}" for m in memory[-5:]]) or "No prior memories."
    available = [a.value for a in agent.available_actions]

    own_recent = [
        a for a in recent_actions if a.agent_type == agent.agent_type
    ][-3:]
    own_actions_text = "\n".join([
        f"- Month {a.round_num}: {a.action.value} — {a.description}"
        for a in own_recent
    ]) or "None yet."

    return f"""CURRENT MONTH: {round_num} of {total_rounds}

COMPANY STATE:
- MRR: ${company_state.mrr:,.0f} | ARR: ${company_state.arr:,.0f}
- Burn Rate: ${company_state.burn_rate:,.0f}/mo | Cash: ${company_state.cash:,.0f}
- Runway: {company_state.runway_months:.1f} months
- Customers: {company_state.customers} | Churn: {company_state.churn_rate:.1%}
- Team Size: {company_state.team_size} | Morale: {company_state.team_morale:.0%}
- Product Quality: {company_state.product_quality:.0%}
- Market Fit: {company_state.market_fit:.0%}
- Growth Rate: {company_state.growth_rate:.1%}/mo
- Investor Confidence: {company_state.investor_confidence:.0%}

RECENT EVENTS (all agents):
{recent_events}

YOUR LAST 3 ACTIONS:
{own_actions_text}

YOUR MEMORIES:
{memory_text}

AVAILABLE ACTIONS: {json.dumps(available)}

IMPORTANT RULES:
- Do NOT repeat the same action you took last round. Vary your decisions across rounds.
- Consider the outcomes of your previous actions before deciding.
- If your last action had little impact, try a different approach.

Decide your ONE action this month. Respond with JSON:
{{
  "action": "<one of your available actions>",
  "reasoning": "<2-3 sentence chain-of-thought explaining your decision>",
  "description": "<1 sentence human-readable description of what you did>",
  "sentiment": "<very_positive|positive|neutral|negative|very_negative>",
  "impact": {{
    "mrr_delta": <number, max ±5000>,
    "burn_rate_delta": <number, max ±5000>,
    "cash_delta": <number, max ±50000>,
    "customers_delta": <number, max ±20>,
    "churn_rate_delta": <number, max ±0.02>,
    "team_size_delta": <number, max ±3>,
    "team_morale_delta": <number, max ±0.1>,
    "product_quality_delta": <number, max ±0.1>,
    "market_fit_delta": <number, max ±0.1>,
    "investor_confidence_delta": <number, max ±0.1>,
    "growth_rate_delta": <number, max ±0.03>
  }}
}}

Only include non-zero deltas. Be realistic — this is a SINGLE MONTH of a startup. Single actions cause small incremental changes, not dramatic swings. A typical monthly MRR change is $500-$5000, not $50,000. Customer changes are 1-20 per month, not hundreds."""


async def agent_decide(
    agent: AgentPersona,
    company_state: CompanyState,
    recent_actions: List[AgentAction],
    round_num: int,
    total_rounds: int,
    memory: List[str],
    llm_client,
    model: str = "gpt-5.6-luna",
) -> Optional[AgentAction]:
    system_prompt = build_agent_system_prompt(agent, company_state)
    user_prompt = build_agent_decision_prompt(
        agent, company_state, recent_actions, round_num, total_rounds, memory
    )

    try:
        response = llm_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7 + (agent.emotional_tendency * 0.2),
            max_tokens=500,
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)

        action_str = result.get("action", "observe")
        try:
            action_type = ActionType(action_str)
        except ValueError:
            action_type = ActionType.OBSERVE

        sentiment_str = result.get("sentiment", "neutral")
        try:
            sentiment = Sentiment(sentiment_str)
        except ValueError:
            sentiment = Sentiment.NEUTRAL

        return AgentAction(
            round_num=round_num,
            month_label=f"Month {round_num}",
            agent_id=agent.id,
            agent_name=agent.name,
            agent_type=agent.agent_type,
            action=action_type,
            reasoning=result.get("reasoning", ""),
            description=result.get("description", ""),
            impact=result.get("impact", {}),
            sentiment=sentiment,
        )
    except Exception as e:
        logger.warning(f"Agent {agent.name} decision failed: {e}")
        return AgentAction(
            round_num=round_num,
            month_label=f"Month {round_num}",
            agent_id=agent.id,
            agent_name=agent.name,
            agent_type=agent.agent_type,
            action=ActionType.OBSERVE,
            reasoning=f"Agent could not decide: {str(e)}",
            description=f"{agent.name} observes the situation.",
            impact={},
            sentiment=Sentiment.NEUTRAL,
        )
