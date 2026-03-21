import json
import logging
from typing import List, Dict, Any

from .types import AgentPersona, AgentType, ActionType, CompanyState

logger = logging.getLogger(__name__)

AGENT_TEMPLATES = {
    AgentType.FOUNDER: {
        "available_actions": [
            ActionType.HIRE, ActionType.FIRE, ActionType.PIVOT_PRODUCT,
            ActionType.RAISE_PRICES, ActionType.CUT_PRICES, ActionType.LAUNCH_FEATURE,
            ActionType.CUT_BURN, ActionType.INCREASE_MARKETING, ActionType.SEEK_FUNDING,
        ]
    },
    AgentType.INVESTOR: {
        "available_actions": [
            ActionType.OFFER_TERM_SHEET, ActionType.PASS_ON_DEAL,
            ActionType.REQUEST_METRICS, ActionType.FOLLOW_ON_INVEST, ActionType.MARK_DOWN,
        ]
    },
    AgentType.CUSTOMER: {
        "available_actions": [
            ActionType.SIGN_CONTRACT, ActionType.CHURN, ActionType.UPGRADE,
            ActionType.REFER_OTHERS, ActionType.COMPLAIN, ActionType.REQUEST_FEATURE,
        ]
    },
    AgentType.TEAM_MEMBER: {
        "available_actions": [
            ActionType.QUIT, ActionType.REQUEST_RAISE, ActionType.SHIP_FEATURE,
            ActionType.MISS_DEADLINE, ActionType.PROPOSE_IDEA,
        ]
    },
    AgentType.MARKET: {
        "available_actions": [
            ActionType.RECESSION, ActionType.BOOM, ActionType.NEW_REGULATION,
            ActionType.COMPETITOR_LAUNCH, ActionType.VIRAL_MOMENT, ActionType.MARKET_SHIFT,
        ]
    },
    AgentType.COMPETITOR: {
        "available_actions": [
            ActionType.COMPETITOR_LAUNCH, ActionType.CUT_PRICES,
            ActionType.INCREASE_MARKETING, ActionType.MARKET_SHIFT,
        ]
    },
    AgentType.ADVISOR: {
        "available_actions": [
            ActionType.PROPOSE_IDEA, ActionType.REQUEST_METRICS,
            ActionType.SEEK_FUNDING, ActionType.LAUNCH_FEATURE,
        ]
    },
}


async def generate_agent_personas(
    company_state: CompanyState,
    scenario_params: Dict[str, Any],
    llm_client,
    model: str = "gpt-4o-mini",
) -> List[AgentPersona]:
    prompt = f"""Generate realistic agent personas for a startup simulation.

COMPANY CONTEXT:
- MRR: ${company_state.mrr:,.0f}, Burn: ${company_state.burn_rate:,.0f}/mo
- Cash: ${company_state.cash:,.0f}, Runway: {company_state.runway_months:.1f}mo
- {company_state.customers} customers, {company_state.churn_rate:.1%} churn
- Team of {company_state.team_size}, morale at {company_state.team_morale:.0%}

SCENARIO: {json.dumps(scenario_params)}

Generate exactly 7 agents as a JSON object with an "agents" key containing an array. Each agent needs:
- "name": A realistic name (e.g. "Sarah Chen, Series A VC" not just "Investor")
- "agent_type": one of [founder, investor, customer, team, market, competitor, advisor]
- "bio": 2-3 sentences describing their background, motivations, and how they relate to this company
- "personality_traits": array of 3-4 traits like "data-driven", "impatient", "risk-averse", "growth-obsessed"
- "goals": array of 2-3 specific goals
- "emotional_tendency": float -1.0 to 1.0
- "activity_level": float 0.0 to 1.0
- "influence": float 0.5 to 3.0
- "risk_tolerance": float 0.0 to 1.0

REQUIRED MIX: 1 founder, 2 investors (1 bullish, 1 cautious), 1 key customer, 1 team lead, 1 market force, 1 competitor/advisor.

Respond with a JSON object: {{"agents": [...]}}"""

    try:
        response = llm_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=3000,
            response_format={"type": "json_object"},
        )

        data = json.loads(response.choices[0].message.content)
        agents_data = data if isinstance(data, list) else data.get("agents", [])

        personas = []
        for i, a in enumerate(agents_data):
            try:
                agent_type = AgentType(a["agent_type"])
            except (ValueError, KeyError):
                agent_type = AgentType.MARKET
            template = AGENT_TEMPLATES.get(agent_type, AGENT_TEMPLATES[AgentType.MARKET])

            personas.append(AgentPersona(
                id=f"agent_{i}",
                name=a.get("name", f"Agent {i}"),
                agent_type=agent_type,
                bio=a.get("bio", ""),
                personality_traits=a.get("personality_traits", []),
                goals=a.get("goals", []),
                emotional_tendency=float(a.get("emotional_tendency", 0)),
                activity_level=float(a.get("activity_level", 0.5)),
                influence=float(a.get("influence", 1.0)),
                risk_tolerance=float(a.get("risk_tolerance", 0.5)),
                available_actions=template["available_actions"],
            ))

        return personas

    except Exception as e:
        logger.error(f"Failed to generate agent personas via LLM: {e}")
        return _fallback_personas()


def _fallback_personas() -> List[AgentPersona]:
    defaults = [
        ("agent_0", "Alex Rivera, CEO", AgentType.FOUNDER,
         "First-time founder with a technical background. Obsessed with product-market fit.",
         ["visionary", "hands-on", "resilient"], ["achieve PMF", "reach $1M ARR"], 0.6, 0.9, 2.0, 0.7),
        ("agent_1", "Diana Park, Lead VC", AgentType.INVESTOR,
         "Partner at a Series A fund. Aggressive but metric-driven.",
         ["data-driven", "ambitious", "pattern-matching"], ["10x return", "board seat"], 0.4, 0.6, 2.5, 0.6),
        ("agent_2", "Marcus Webb, Angel Investor", AgentType.INVESTOR,
         "Former founder turned angel. Patient and empathetic.",
         ["patient", "supportive", "risk-tolerant"], ["help founders", "modest return"], 0.3, 0.4, 1.0, 0.8),
        ("agent_3", "Priya Sharma, Enterprise Buyer", AgentType.CUSTOMER,
         "VP of Engineering at a mid-market company evaluating the product.",
         ["pragmatic", "budget-conscious", "demanding"], ["solve pain point", "prove ROI"], 0.0, 0.5, 1.5, 0.3),
        ("agent_4", "Jordan Lee, Eng Lead", AgentType.TEAM_MEMBER,
         "Senior engineer and first hire. Core to product velocity.",
         ["perfectionist", "loyal", "opinionated"], ["ship great product", "grow career"], 0.2, 0.7, 1.5, 0.4),
        ("agent_5", "The Market", AgentType.MARKET,
         "External macroeconomic and industry forces affecting the company.",
         ["unpredictable", "cyclical", "impactful"], ["equilibrium"], 0.0, 0.5, 2.0, 0.5),
        ("agent_6", "NovaTech, Competitor", AgentType.COMPETITOR,
         "Well-funded competitor that recently raised a Series B.",
         ["aggressive", "well-resourced", "fast-moving"], ["market dominance", "crush rivals"], -0.3, 0.6, 1.5, 0.7),
    ]
    personas = []
    for d in defaults:
        agent_type = d[2]
        template = AGENT_TEMPLATES.get(agent_type, AGENT_TEMPLATES[AgentType.MARKET])
        personas.append(AgentPersona(
            id=d[0], name=d[1], agent_type=agent_type, bio=d[3],
            personality_traits=d[4], goals=d[5],
            emotional_tendency=d[6], activity_level=d[7],
            influence=d[8], risk_tolerance=d[9],
            available_actions=template["available_actions"],
        ))
    return personas
