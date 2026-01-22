"""
Base Agent class for the Fund Flow Copilot multi-agent system.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AgentType(Enum):
    ROUTER = "router"
    CFO = "cfo"
    MARKET = "market"
    STRATEGY = "strategy"


class ConfidenceLevel(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class AgentResponse:
    """Standard response format from all agents."""
    agent_type: AgentType
    findings: List[str] = field(default_factory=list)
    structured_output: Dict[str, Any] = field(default_factory=dict)
    assumptions: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    next_questions: List[str] = field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    raw_response: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_type": self.agent_type.value,
            "findings": self.findings,
            "structured_output": self.structured_output,
            "assumptions": self.assumptions,
            "risks": self.risks,
            "next_questions": self.next_questions,
            "confidence": self.confidence.value,
            "raw_response": self.raw_response
        }


@dataclass
class CompanyKnowledgeBase:
    """Company Knowledge Base (CKB) - shared context across agents."""
    company_id: int
    company_name: str
    industry: str = ""
    stage: str = ""
    currency: str = "USD"
    
    overview: Dict[str, Any] = field(default_factory=dict)
    financials: Dict[str, Any] = field(default_factory=dict)
    market: Dict[str, Any] = field(default_factory=dict)
    strategy: Dict[str, Any] = field(default_factory=dict)
    
    icp: Dict[str, Any] = field(default_factory=dict)
    competitors: List[Dict[str, Any]] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    decisions_made: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "company_id": self.company_id,
            "company_name": self.company_name,
            "industry": self.industry,
            "stage": self.stage,
            "currency": self.currency,
            "overview": self.overview,
            "financials": self.financials,
            "market": self.market,
            "strategy": self.strategy,
            "icp": self.icp,
            "competitors": self.competitors,
            "risks": self.risks,
            "decisions_made": self.decisions_made
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CompanyKnowledgeBase":
        return cls(
            company_id=data.get("company_id", 0),
            company_name=data.get("company_name", ""),
            industry=data.get("industry", ""),
            stage=data.get("stage", ""),
            currency=data.get("currency", "USD"),
            overview=data.get("overview", {}),
            financials=data.get("financials", {}),
            market=data.get("market", {}),
            strategy=data.get("strategy", {}),
            icp=data.get("icp", {}),
            competitors=data.get("competitors", []),
            risks=data.get("risks", []),
            decisions_made=data.get("decisions_made", [])
        )


class BaseAgent(ABC):
    """Base class for all specialist agents."""
    
    def __init__(self, agent_type: AgentType):
        self.agent_type = agent_type
        self.logger = logging.getLogger(f"copilot.{agent_type.value}")
    
    @abstractmethod
    async def process(
        self, 
        query: str, 
        ckb: CompanyKnowledgeBase,
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Process a query and return structured response."""
        pass
    
    def format_currency(self, value: float, currency: str = "USD") -> str:
        """Format currency in human-readable format (e.g., USD 14.5M)."""
        if value is None:
            return "N/A"
        
        abs_value = abs(value)
        sign = "-" if value < 0 else ""
        
        if abs_value >= 1_000_000_000:
            formatted = f"{abs_value / 1_000_000_000:.1f}B"
        elif abs_value >= 1_000_000:
            formatted = f"{abs_value / 1_000_000:.1f}M"
        elif abs_value >= 1_000:
            formatted = f"{abs_value / 1_000:.1f}K"
        else:
            formatted = f"{abs_value:.0f}"
        
        return f"{sign}{currency} {formatted}"
    
    def format_currency_words(self, value: float, currency: str = "USD") -> str:
        """Format currency with words (e.g., fourteen point five million dollars)."""
        if value is None:
            return "N/A"
        
        abs_value = abs(value)
        
        if abs_value >= 1_000_000_000:
            num = abs_value / 1_000_000_000
            unit = "billion"
        elif abs_value >= 1_000_000:
            num = abs_value / 1_000_000
            unit = "million"
        elif abs_value >= 1_000:
            num = abs_value / 1_000
            unit = "thousand"
        else:
            num = abs_value
            unit = ""
        
        currency_names = {
            "USD": "US dollars",
            "EUR": "euros",
            "GBP": "British pounds",
            "INR": "Indian rupees"
        }
        curr_name = currency_names.get(currency, currency)
        
        if unit:
            return f"{num:.1f} {unit} {curr_name}"
        return f"{num:.0f} {curr_name}"
