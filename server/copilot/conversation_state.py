"""
Conversation State Management for Copilot.

Tracks the context of ongoing conversations to support follow-up commands.
"""
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConversationState:
    """State of an ongoing copilot conversation."""
    company_id: int
    user_id: int
    last_scenario_id: Optional[int] = None
    last_scenario_name: Optional[str] = None
    last_assumption_set_id: Optional[int] = None
    last_simulation_id: Optional[int] = None
    last_simulation_params: Optional[Dict[str, Any]] = None
    last_simulation_results: Optional[Dict[str, Any]] = None
    pending_clarification: Optional[Dict[str, Any]] = None
    message_history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationState':
        """Create from dictionary."""
        if isinstance(data.get('created_at'), str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if isinstance(data.get('updated_at'), str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a message to history."""
        self.message_history.append({
            'role': role,
            'content': content,
            'timestamp': datetime.utcnow().isoformat(),
            'metadata': metadata or {}
        })
        if len(self.message_history) > 20:
            self.message_history = self.message_history[-20:]
        self.updated_at = datetime.utcnow()
    
    def set_last_simulation(
        self,
        scenario_id: Optional[int] = None,
        scenario_name: Optional[str] = None,
        assumption_set_id: Optional[int] = None,
        simulation_id: Optional[int] = None,
        params: Optional[Dict[str, Any]] = None,
        results: Optional[Dict[str, Any]] = None
    ):
        """Update the last simulation context."""
        if scenario_id:
            self.last_scenario_id = scenario_id
        if scenario_name:
            self.last_scenario_name = scenario_name
        if assumption_set_id:
            self.last_assumption_set_id = assumption_set_id
        if simulation_id:
            self.last_simulation_id = simulation_id
        if params:
            self.last_simulation_params = params
        if results:
            self.last_simulation_results = results
        self.updated_at = datetime.utcnow()
    
    def set_pending_clarification(self, clarification: Dict[str, Any]):
        """Set a pending clarification question."""
        self.pending_clarification = clarification
        self.updated_at = datetime.utcnow()
    
    def clear_pending_clarification(self):
        """Clear pending clarification."""
        self.pending_clarification = None
        self.updated_at = datetime.utcnow()
    
    def get_context_summary(self) -> str:
        """Get a summary of current context for LLM prompts."""
        parts = []
        if self.last_scenario_name:
            parts.append(f"Current scenario: {self.last_scenario_name}")
        if self.last_simulation_results:
            summary = self.last_simulation_results.get('summary', {})
            if summary.get('mean_runway_months'):
                parts.append(f"Last runway: {summary['mean_runway_months']:.1f} months")
            if summary.get('survival_rate'):
                parts.append(f"Survival rate: {summary['survival_rate']*100:.0f}%")
        return " | ".join(parts) if parts else "No previous context"


class ConversationStateStore:
    """In-memory store for conversation states with DB persistence."""
    
    def __init__(self):
        self._states: Dict[str, ConversationState] = {}
    
    def _key(self, company_id: int, user_id: int) -> str:
        return f"{company_id}:{user_id}"
    
    def get(self, company_id: int, user_id: int) -> ConversationState:
        """Get or create conversation state."""
        key = self._key(company_id, user_id)
        if key not in self._states:
            self._states[key] = ConversationState(
                company_id=company_id,
                user_id=user_id
            )
        return self._states[key]
    
    def save(self, state: ConversationState):
        """Save conversation state."""
        key = self._key(state.company_id, state.user_id)
        self._states[key] = state
    
    def clear(self, company_id: int, user_id: int):
        """Clear conversation state."""
        key = self._key(company_id, user_id)
        if key in self._states:
            del self._states[key]
    
    def persist_to_db(self, db, company_id: int, user_id: int):
        """Persist state to company's metadata_json."""
        from server.models.company import Company
        
        state = self.get(company_id, user_id)
        company = db.query(Company).filter(Company.id == company_id).first()
        if company:
            metadata = company.metadata_json or {}
            metadata['copilot_state'] = state.to_dict()
            company.metadata_json = metadata
            db.commit()
    
    def load_from_db(self, db, company_id: int, user_id: int) -> ConversationState:
        """Load state from company's metadata_json."""
        from server.models.company import Company
        
        key = self._key(company_id, user_id)
        if key in self._states:
            return self._states[key]
        
        company = db.query(Company).filter(Company.id == company_id).first()
        if company and company.metadata_json:
            state_data = company.metadata_json.get('copilot_state')
            if state_data and state_data.get('user_id') == user_id:
                state = ConversationState.from_dict(state_data)
                self._states[key] = state
                return state
        
        return self.get(company_id, user_id)


conversation_store = ConversationStateStore()
