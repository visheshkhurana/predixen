"""
Intent Parser for Conversational Co-Pilot.

Parses natural language commands into structured simulation actions.
"""
import re
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CopilotIntent(str, Enum):
    RUN_SIMULATION = "run_simulation"
    COMPARE_SCENARIOS = "compare_scenarios"
    SAVE_SCENARIO = "save_scenario"
    LOAD_SCENARIO = "load_scenario"
    MODIFY_PREVIOUS = "modify_previous"
    EXPLAIN_RESULTS = "explain_results"
    GENERAL_QUERY = "general_query"


@dataclass
class SimulationParameters:
    """Extracted parameters for a simulation command."""
    burn_reduction_pct: Optional[float] = None
    price_change_pct: Optional[float] = None
    revenue_growth_pct: Optional[float] = None
    hiring_freeze_months: Optional[int] = None
    headcount_change: Optional[int] = None
    fundraise_amount: Optional[float] = None
    fundraise_month: Optional[int] = None
    churn_reduction_pct: Optional[float] = None
    horizon_months: int = 24
    scenario_name: Optional[str] = None
    compare_scenarios: List[str] = field(default_factory=list)


@dataclass
class ClarificationQuestion:
    """Question to ask when command is ambiguous."""
    field: str
    question: str
    options: Optional[List[str]] = None
    example: Optional[str] = None


@dataclass
class ParsedIntent:
    """Result of intent parsing."""
    intent: CopilotIntent
    parameters: SimulationParameters
    confidence: float
    clarifications_needed: List[ClarificationQuestion] = field(default_factory=list)
    original_message: str = ""
    is_complete: bool = True


INTENT_PATTERNS = {
    CopilotIntent.RUN_SIMULATION: [
        r'\b(simulate|simulating|run\s+simulation|run\s+a?\s*sim|model|project|forecast)\b',
        r'\bwhat\s+(if|happens\s+if|would\s+happen)\b',
        r'\b(scenario|test|try)\b.*\b(with|where|assuming)\b',
        r'\b(raise|fundraise|raising)\s*\$?\d+',
        r'\b(cut|cuts?|reduce|reduces?|reducing|lower|lowering|decrease|decreasing|slash|slashing)\s*(the\s+)?(burn|costs?|expenses?|spending|opex|overhead)\b',
        r'\b(increase|increasing|raise|raising|bump|bumping|grow|growing)\s*(the\s+)?(price|prices|revenue|pricing|mrr)\b',
        r'\b(freeze|freezing|stop|stopping|pause|pausing|halt|halting)\s*(the\s+)?hir(ing|es?)\b',
        r'\b(hire|hiring|add|adding|lay\s*off|laying\s*off)\s*\d+\s*(people|employees?)\b',
    ],
    CopilotIntent.COMPARE_SCENARIOS: [
        r'\b(compare|versus|vs\.?|against)\b',
        r'\bside[\s-]by[\s-]side\b',
        r'\bdifference\s+between\b',
    ],
    CopilotIntent.SAVE_SCENARIO: [
        r'\b(save|store|keep|remember)\b.*\b(scenario|plan|simulation|this)\b',
        r'\bsave\s+(this\s+)?as\b',
        r'\bname\s+this\b',
    ],
    CopilotIntent.LOAD_SCENARIO: [
        r'\b(load|open|show|use|retrieve)\b.*\b(scenario|plan)\b',
        r'\bswitch\s+to\b.*\b(scenario|plan)\b',
    ],
    CopilotIntent.MODIFY_PREVIOUS: [
        r'\b(now|also|and|then)\b.*\b(add|change|modify|adjust|reduce|increase)\b',
        r'\b(what\s+if\s+we)\b.*\b(also|additionally)\b',
        r'\b(on\s+top\s+of\s+that|in\s+addition)\b',
    ],
    CopilotIntent.EXPLAIN_RESULTS: [
        r'\b(why|explain|how\s+come|what\s+caused)\b',
        r'\b(break\s*down|detail|elaborate)\b',
    ],
}

PARAMETER_PATTERNS = {
    'burn_reduction': [
        (r'(reduc\w*|cut\w*|lower\w*|decrease\w*|slash\w*)\s*(?:the\s+)?(?:overall\s+)?(burn|costs?|expenses?|spending|opex|overhead)\s*(?:rate\s*)?(?:by\s*)?(\d+(?:\.\d+)?)\s*%', 3),
        (r'(\d+(?:\.\d+)?)\s*%\s*(?:burn|cost|expense|spending)\s*(reduction|cut|decrease)', 1),
        (r'(?:burn|cost|expense)\s*(reduction|cut)\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*%', 2),
        (r'(reduc\w*|cut\w*|lower\w*|slash\w*)\s+(\d+(?:\.\d+)?)\s*%\s*(?:of\s+)?(?:the\s+)?(?:burn|costs?|expenses?|spending)', 2),
        (r'(reduc\w*|cut\w*|lower\w*|decrease\w*|slash\w*)\s*(?:the\s+)?(?:marketing|payroll|salaries|rent|infra|infrastructure|cloud|aws|server)\s*(?:spend(?:ing)?|budget|costs?)?\s*(?:by\s*)?(\d+(?:\.\d+)?)\s*%', 2),
    ],
    'price_change': [
        (r'(increas\w*|rais\w*|bump\w*|grow\w*)\s*(?:the\s+)?price[s]?\s*(?:by\s*)?(\d+(?:\.\d+)?)\s*%', 2),
        (r'(\d+(?:\.\d+)?)\s*%\s*price\s*(increase|hike|raise)', 1),
        (r'price\s*(increase|change|hike)\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*%', 2),
        (r'(decreas\w*|lower\w*|reduc\w*|drop\w*)\s*(?:the\s+)?price[s]?\s*(?:by\s*)?(\d+(?:\.\d+)?)\s*%', 2, -1),
        (r'(increas\w*|rais\w*|bump\w*)\s+(\d+(?:\.\d+)?)\s*%\s*(?:on\s+)?(?:the\s+)?(?:price|pricing)', 2),
    ],
    'hiring_freeze': [
        (r'(freez\w*|stop\w*|paus\w*|halt\w*)\s*(?:the\s+)?hir(ing|es?)\s*(?:for\s*)?(\d+)\s*(month|mo)', 3),
        (r'hiring\s*freeze\s*(?:for\s*)?(\d+)\s*(month|mo)', 1),
        (r'no\s*(new\s*)?(hir(ing|es?))\s*(?:for\s*)?(\d+)\s*(month|mo)', 4),
        (r'(freez\w*|stop\w*|paus\w*|halt\w*)\s*(?:all\s+)?(?:new\s+)?hir(ing|es?)', None),
    ],
    'headcount': [
        (r'(hire|add)\s*(\d+)\s*(people|employees?|heads?|staff|engineers?|developers?|devs?|designers?|salespeople|reps?)', 2),
        (r'(reduce|cut|lay\s*off)\s*(\d+)\s*(people|employees?|heads?|staff|engineers?|developers?)', 2, -1),
        (r'(\d+)\s*(new\s*)?(hires?|employees?|engineers?|developers?)', 1),
    ],
    'fundraise': [
        (r'(raise|fundraise|get)\s*\$?(\d+(?:\.\d+)?)\s*(m|million|k|thousand)?', 2, 3),
        (r'\$(\d+(?:\.\d+)?)\s*(m|million|k|thousand)?\s*(fundraise|raise|round)', 1, 2),
        (r'fundraise\s*(?:of\s*)?\$?(\d+(?:\.\d+)?)\s*(m|million|k|thousand)?', 1, 2),
    ],
    'fundraise_timing': [
        (r'(delay|push|postpone)\s*(fundraise|raise|round)\s*(?:by\s*)?(\d+)\s*(month|mo)', 3),
        (r'fundraise\s*(?:in|at)\s*month\s*(\d+)', 1),
        (r'raise\s*(?:in|at)\s*(\d+)\s*(month|mo)', 1),
    ],
    'revenue_growth': [
        (r'(increase|boost|grow)\s*revenue\s*(?:by\s*)?(\d+(?:\.\d+)?)\s*%', 2),
        (r'(\d+(?:\.\d+)?)\s*%\s*revenue\s*(growth|increase)', 1),
        (r'revenue\s*(growth|increase)\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*%', 2),
        (r'(reduce|cut|lower|decrease|drop)\s*revenue\s*(?:by\s*)?(\d+(?:\.\d+)?)\s*%', 2, -1),
        (r'revenue\s*(decline|decrease|drop|reduction)\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*%', 2, -1),
    ],
    'churn_reduction': [
        (r'(reduce|cut|lower|decrease)\s*churn\s*(?:by\s*)?(\d+(?:\.\d+)?)\s*%', 2),
        (r'(\d+(?:\.\d+)?)\s*%\s*churn\s*(reduction|decrease)', 1),
    ],
    'horizon': [
        (r'(?:for|over|next)\s*(\d+)\s*(month|mo)', 1),
        (r'(\d+)[\s-]*(month|mo)\s*(simulation|forecast|projection|horizon)', 1),
    ],
    'scenario_name': [
        (r'(?:save|name|call)\s*(?:this|it)?\s*(?:as)?\s*["\']([^"\']+)["\']', 1),
        (r'(?:save|name|call)\s*(?:this|it)?\s*(?:as)?\s*(\w[\w\s]{2,20})', 1),
        (r'scenario\s*["\']([^"\']+)["\']', 1),
        (r'plan\s+(\w+)', 1),
    ],
    'compare_targets': [
        (r'compare\s*["\']?([^"\']+)["\']?\s*(?:and|vs\.?|versus|with|to)\s*["\']?([^"\']+)["\']?', 1, 2),
        (r'compare\s*(plan\s*\w+)\s*(?:and|vs\.?|to)\s*(plan\s*\w+)', 1, 2),
    ],
}


def parse_intent(message: str) -> ParsedIntent:
    """
    Parse a natural language message to extract intent and parameters.
    
    Args:
        message: The user's chat message
        
    Returns:
        ParsedIntent with detected intent, extracted parameters, and any needed clarifications
    """
    message_lower = message.lower().strip()
    
    detected_intent = CopilotIntent.GENERAL_QUERY
    max_confidence = 0.0
    
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, message_lower, re.IGNORECASE):
                confidence = 0.8
                if detected_intent == CopilotIntent.GENERAL_QUERY or confidence > max_confidence:
                    detected_intent = intent
                    max_confidence = confidence
                break
    
    parameters = extract_parameters(message_lower)
    parameters.scenario_name = extract_scenario_name(message)
    
    clarifications = []
    is_complete = True
    
    if detected_intent == CopilotIntent.RUN_SIMULATION:
        if not has_any_simulation_params(parameters):
            clarifications.append(ClarificationQuestion(
                field="simulation_type",
                question="What would you like to simulate? You can specify changes like:",
                options=[
                    "Reduce burn by 20%",
                    "Increase prices by 10%",
                    "Freeze hiring for 6 months",
                    "Delay fundraise by 3 months"
                ],
                example="Simulate a 15% burn reduction and 5% price increase"
            ))
            is_complete = False
    
    elif detected_intent == CopilotIntent.SAVE_SCENARIO:
        if not parameters.scenario_name:
            clarifications.append(ClarificationQuestion(
                field="scenario_name",
                question="What would you like to name this scenario?",
                options=["Plan A", "Conservative Cut", "Aggressive Growth", "Bridge Scenario"],
                example="Save this as 'Plan B'"
            ))
            is_complete = False
    
    elif detected_intent == CopilotIntent.COMPARE_SCENARIOS:
        if len(parameters.compare_scenarios) < 2:
            clarifications.append(ClarificationQuestion(
                field="compare_scenarios",
                question="Which scenarios would you like to compare?",
                options=None,
                example="Compare Plan A vs Plan B"
            ))
            is_complete = False
    
    elif detected_intent == CopilotIntent.LOAD_SCENARIO:
        if not parameters.scenario_name:
            clarifications.append(ClarificationQuestion(
                field="scenario_name",
                question="Which scenario would you like to load?",
                options=None,
                example="Load Plan A"
            ))
            is_complete = False
    
    return ParsedIntent(
        intent=detected_intent,
        parameters=parameters,
        confidence=max_confidence if max_confidence > 0 else 0.5,
        clarifications_needed=clarifications,
        original_message=message,
        is_complete=is_complete
    )


def extract_parameters(message: str) -> SimulationParameters:
    """Extract simulation parameters from message."""
    params = SimulationParameters()
    
    for pattern_tuple in PARAMETER_PATTERNS.get('burn_reduction', []):
        pattern = pattern_tuple[0]
        group_idx = pattern_tuple[1]
        multiplier = pattern_tuple[2] if len(pattern_tuple) > 2 else 1
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            try:
                params.burn_reduction_pct = float(match.group(group_idx)) * multiplier
                break
            except (ValueError, IndexError):
                pass
    
    for pattern_tuple in PARAMETER_PATTERNS.get('price_change', []):
        pattern = pattern_tuple[0]
        group_idx = pattern_tuple[1]
        multiplier = pattern_tuple[2] if len(pattern_tuple) > 2 else 1
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            try:
                params.price_change_pct = float(match.group(group_idx)) * multiplier
                break
            except (ValueError, IndexError):
                pass
    
    for pattern_tuple in PARAMETER_PATTERNS.get('hiring_freeze', []):
        pattern = pattern_tuple[0]
        group_idx = pattern_tuple[1]
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            if group_idx is None:
                params.hiring_freeze_months = 6
                break
            try:
                params.hiring_freeze_months = int(match.group(group_idx))
                break
            except (ValueError, IndexError):
                pass
    
    for pattern_tuple in PARAMETER_PATTERNS.get('headcount', []):
        pattern = pattern_tuple[0]
        group_idx = pattern_tuple[1]
        multiplier = pattern_tuple[2] if len(pattern_tuple) > 2 else 1
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            try:
                params.headcount_change = int(match.group(group_idx)) * multiplier
                break
            except (ValueError, IndexError):
                pass
    
    for pattern_tuple in PARAMETER_PATTERNS.get('fundraise', []):
        pattern = pattern_tuple[0]
        amount_idx = pattern_tuple[1]
        unit_idx = pattern_tuple[2] if len(pattern_tuple) > 2 else None
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            try:
                amount = float(match.group(amount_idx))
                if unit_idx:
                    unit = match.group(unit_idx).lower() if match.group(unit_idx) else ''
                    if unit in ('m', 'million'):
                        amount *= 1_000_000
                    elif unit in ('k', 'thousand'):
                        amount *= 1_000
                params.fundraise_amount = amount
                break
            except (ValueError, IndexError):
                pass
    
    for pattern_tuple in PARAMETER_PATTERNS.get('fundraise_timing', []):
        pattern = pattern_tuple[0]
        group_idx = pattern_tuple[1]
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            try:
                params.fundraise_month = int(match.group(group_idx))
                break
            except (ValueError, IndexError):
                pass
    
    for pattern_tuple in PARAMETER_PATTERNS.get('revenue_growth', []):
        pattern = pattern_tuple[0]
        group_idx = pattern_tuple[1]
        multiplier = pattern_tuple[2] if len(pattern_tuple) > 2 else 1
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            try:
                params.revenue_growth_pct = float(match.group(group_idx)) * multiplier
                break
            except (ValueError, IndexError):
                pass
    
    for pattern_tuple in PARAMETER_PATTERNS.get('churn_reduction', []):
        pattern = pattern_tuple[0]
        group_idx = pattern_tuple[1]
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            try:
                params.churn_reduction_pct = float(match.group(group_idx))
                break
            except (ValueError, IndexError):
                pass
    
    for pattern_tuple in PARAMETER_PATTERNS.get('horizon', []):
        pattern = pattern_tuple[0]
        group_idx = pattern_tuple[1]
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            try:
                params.horizon_months = int(match.group(group_idx))
                break
            except (ValueError, IndexError):
                pass
    
    for pattern_tuple in PARAMETER_PATTERNS.get('compare_targets', []):
        pattern = pattern_tuple[0]
        idx1 = pattern_tuple[1]
        idx2 = pattern_tuple[2] if len(pattern_tuple) > 2 else None
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            try:
                params.compare_scenarios = [
                    match.group(idx1).strip(),
                ]
                if idx2:
                    params.compare_scenarios.append(match.group(idx2).strip())
                break
            except (IndexError):
                pass
    
    return params


def extract_scenario_name(message: str) -> Optional[str]:
    """Extract scenario name from message."""
    for pattern_tuple in PARAMETER_PATTERNS.get('scenario_name', []):
        pattern = pattern_tuple[0]
        group_idx = pattern_tuple[1]
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            name = match.group(group_idx).strip()
            stop_words = {'as', 'this', 'it', 'the', 'a', 'an'}
            if name.lower() not in stop_words and len(name) > 1:
                return name
    return None


def has_any_simulation_params(params: SimulationParameters) -> bool:
    """Check if any simulation parameters were extracted."""
    return any([
        params.burn_reduction_pct is not None,
        params.price_change_pct is not None,
        params.revenue_growth_pct is not None,
        params.hiring_freeze_months is not None,
        params.headcount_change is not None,
        params.fundraise_amount is not None,
        params.fundraise_month is not None,
        params.churn_reduction_pct is not None,
    ])


def format_parameters_summary(params: SimulationParameters) -> str:
    """Format extracted parameters as a human-readable summary."""
    parts = []
    
    if params.burn_reduction_pct:
        parts.append(f"burn reduction of {abs(params.burn_reduction_pct):.0f}%")
    if params.price_change_pct:
        direction = "increase" if params.price_change_pct > 0 else "decrease"
        parts.append(f"price {direction} of {abs(params.price_change_pct):.0f}%")
    if params.revenue_growth_pct:
        parts.append(f"revenue growth boost of {params.revenue_growth_pct:.0f}%")
    if params.hiring_freeze_months:
        parts.append(f"hiring freeze for {params.hiring_freeze_months} months")
    if params.headcount_change:
        direction = "hiring" if params.headcount_change > 0 else "reducing"
        parts.append(f"{direction} {abs(params.headcount_change)} employees")
    if params.fundraise_amount:
        if params.fundraise_amount >= 1_000_000:
            amt_str = f"${params.fundraise_amount / 1_000_000:.1f}M"
        else:
            amt_str = f"${params.fundraise_amount / 1_000:.0f}K"
        parts.append(f"fundraise of {amt_str}")
    if params.fundraise_month:
        parts.append(f"fundraise in month {params.fundraise_month}")
    if params.churn_reduction_pct:
        parts.append(f"churn reduction of {params.churn_reduction_pct:.0f}%")
    
    if not parts:
        return "No specific parameters detected"
    
    return ", ".join(parts)
