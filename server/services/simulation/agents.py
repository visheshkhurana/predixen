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

RECENT EVENTS:
{recent_events}

YOUR MEMORIES:
{memory_text}

AVAILABLE ACTIONS: {json.dumps(available)}

Decide your ONE action this month. Respond with JSON:
{{
  "action": "<one of your available actions>",
  "reasoning": "<2-3 sentence chain-of-thought explaining your decision>",
  "description": "<1 sentence human-readable description of what you did>",
  "sentiment": "<very_positive|positive|neutral|negative|very_negative>",
  "impact": {{
    "mrr_delta": <number>,
    "burn_rate_delta": <number>,
    "cash_delta": <number>,
    "customers_delta": <number>,
    "churn_rate_delta": <number>,
    "team_size_delta": <number>,
    "team_morale_delta": <number>,
    "product_quality_delta": <number>,
    "market_fit_delta": <number>,
    "investor_confidence_delta": <number>,
    "growth_rate_delta": <number>
  }}
}}

Only include non-zero deltas. Be realistic — single actions cause small incremental changes, not dramatic swings. A single customer churning reduces customers by 1, not 50."""


async def agent_decide(
    agent: AgentPersona,
    company_state: CompanyState,
    recent_actions: List[AgentAction],
    round_num: int,
    total_rounds: int,
    memory: List[str],
    llm_client,
    model: str = "gpt-4o-mini",
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
