"""
Base Agent class for the Fund Flow Copilot multi-agent system.

All agents use the Multi-LLM Router for intelligent model selection:
- CFO Agent → GPT-4o (best for financial analysis)
- Market Agent → Claude Sonnet (balanced for market research)
- Strategy Agent → Claude Sonnet (strategy and planning)
- Router Agent → Gemini Flash (fast orchestration)
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from enum import Enum
import logging

if TYPE_CHECKING:
    from server.lib.llm.llm_router import LLMRouter

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
class CKBLayer:
    """Base layer for structured CKB data."""
    items: List[Dict[str, Any]] = field(default_factory=list)
    
    def add(self, item: Dict[str, Any]) -> None:
        """Add an item to the layer."""
        from datetime import datetime
        item["added_at"] = datetime.utcnow().isoformat()
        self.items.append(item)
        if len(self.items) > 100:
            self.items = self.items[-100:]
    
    def to_dict(self) -> List[Dict[str, Any]]:
        return self.items


@dataclass
class CompanyKnowledgeBase:
    """
    Company Knowledge Base (CKB) v2 - shared context across agents.
    
    Organized into four layers:
    - facts: Verified data from documents, APIs, user confirmations
    - beliefs: Inferences and estimates with confidence levels
    - decisions: Tracked decisions with options and outcomes
    - outcomes: Results and learnings from past decisions
    """
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
    
    facts: List[Dict[str, Any]] = field(default_factory=list)
    beliefs: List[Dict[str, Any]] = field(default_factory=list)
    decisions_v2: List[Dict[str, Any]] = field(default_factory=list)
    outcomes: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_fact(self, category: str, key: str, value: Any, source: str, confidence: str = "high") -> None:
        """Add a verified fact to the CKB."""
        from datetime import datetime
        self.facts.append({
            "category": category,
            "key": key,
            "value": value,
            "source": source,
            "confidence": confidence,
            "added_at": datetime.utcnow().isoformat()
        })
        if len(self.facts) > 200:
            self.facts = self.facts[-200:]
    
    def add_belief(self, category: str, belief: str, reasoning: str, confidence: str = "medium") -> None:
        """Add an inference/belief to the CKB."""
        from datetime import datetime
        self.beliefs.append({
            "category": category,
            "belief": belief,
            "reasoning": reasoning,
            "confidence": confidence,
            "added_at": datetime.utcnow().isoformat()
        })
        if len(self.beliefs) > 100:
            self.beliefs = self.beliefs[-100:]
    
    def add_decision(self, decision_id: str, title: str, context: str, 
                     options: List[Dict], recommendation: Dict, status: str = "proposed") -> None:
        """Track a decision in the CKB."""
        from datetime import datetime
        self.decisions_v2.append({
            "decision_id": decision_id,
            "title": title,
            "context": context,
            "options": options,
            "recommendation": recommendation,
            "status": status,
            "created_at": datetime.utcnow().isoformat()
        })
        if len(self.decisions_v2) > 50:
            self.decisions_v2 = self.decisions_v2[-50:]
    
    def add_outcome(self, decision_id: str, result: str, metrics_impact: Dict[str, Any], 
                    learnings: List[str]) -> None:
        """Record the outcome of a decision."""
        from datetime import datetime
        self.outcomes.append({
            "decision_id": decision_id,
            "result": result,
            "metrics_impact": metrics_impact,
            "learnings": learnings,
            "recorded_at": datetime.utcnow().isoformat()
        })
        if len(self.outcomes) > 50:
            self.outcomes = self.outcomes[-50:]
    
    def get_facts_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get all facts for a specific category."""
        return [f for f in self.facts if f.get("category") == category]
    
    def get_high_confidence_beliefs(self) -> List[Dict[str, Any]]:
        """Get beliefs with high confidence."""
        return [b for b in self.beliefs if b.get("confidence") == "high"]
    
    def get_pending_decisions(self) -> List[Dict[str, Any]]:
        """Get decisions that are still pending."""
        return [d for d in self.decisions_v2 if d.get("status") in ["proposed", "pending"]]
    
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
            "decisions_made": self.decisions_made,
            "facts": self.facts,
            "beliefs": self.beliefs,
            "decisions_v2": self.decisions_v2,
            "outcomes": self.outcomes
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
            decisions_made=data.get("decisions_made", []),
            facts=data.get("facts", []),
            beliefs=data.get("beliefs", []),
            decisions_v2=data.get("decisions_v2", []),
            outcomes=data.get("outcomes", [])
        )


class BaseAgent(ABC):
    """Base class for all specialist agents."""
    
    def __init__(self, agent_type: AgentType, llm_router: Optional["LLMRouter"] = None):
        self.agent_type = agent_type
        self.llm_router = llm_router
        self.logger = logging.getLogger(f"copilot.{agent_type.value}")
    
    def set_llm_router(self, llm_router: "LLMRouter") -> None:
        """Set the LLM router for this agent."""
        self.llm_router = llm_router
    
    @abstractmethod
    async def process(
        self, 
        query: str, 
        ckb: CompanyKnowledgeBase,
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Process a query and return structured response."""
        pass
    
    def _call_llm(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        task_type: str = "general_chat",
        model: Optional[str] = None,
        temperature: float = 0.7
    ) -> Optional[str]:
        """
        Call the LLM router with the given messages.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: System prompt for the model
            task_type: Task type for model routing (e.g., 'financial_analysis', 'strategy')
            model: Optional explicit model override
            temperature: Sampling temperature
        
        Returns:
            Response content as string, or None if LLM not available
        """
        if not self.llm_router:
            self.logger.warning(f"LLM router not available for {self.agent_type.value} agent")
            return None
        
        try:
            from server.lib.llm.llm_router import TaskType
            task = TaskType(task_type) if task_type in [t.value for t in TaskType] else TaskType.GENERAL_CHAT
            
            result = self.llm_router.chat(
                messages=messages,
                task_type=task,
                model=model,
                system=system_prompt,
                temperature=temperature
            )
            
            return result.get("content", "")
        except Exception as e:
            self.logger.error(f"LLM call failed for {self.agent_type.value}: {e}")
            return None
    
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
