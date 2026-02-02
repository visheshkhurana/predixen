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
    active_scenario_id: Optional[int] = None
    active_run_id: Optional[int] = None
    last_run_id: Optional[int] = None
    baseline_run_id: Optional[int] = None
    response_mode: str = "explain"
    
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
    
    def set_active_context(
        self,
        scenario_id: Optional[int] = None,
        run_id: Optional[int] = None,
        baseline_run_id: Optional[int] = None
    ):
        """Set the active context for natural conversations."""
        if scenario_id is not None:
            self.active_scenario_id = scenario_id
        if run_id is not None:
            if self.active_run_id is not None:
                self.last_run_id = self.active_run_id
            self.active_run_id = run_id
        if baseline_run_id is not None:
            self.baseline_run_id = baseline_run_id
        self.updated_at = datetime.utcnow()
    
    def set_response_mode(self, mode: str):
        """Set the response mode: explain, compare, plan, teach, json."""
        valid_modes = ["explain", "compare", "plan", "teach", "json"]
        if mode.lower() in valid_modes:
            self.response_mode = mode.lower()
        self.updated_at = datetime.utcnow()
    
    def get_session_context(self) -> Dict[str, Any]:
        """Get the full session context for copilot requests."""
        return {
            "companyId": self.company_id,
            "userId": self.user_id,
            "activeScenarioId": self.active_scenario_id or self.last_scenario_id,
            "activeScenarioName": self.last_scenario_name,
            "activeRunId": self.active_run_id or self.last_simulation_id,
            "lastRunId": self.last_run_id,
            "baselineRunId": self.baseline_run_id,
            "responseMode": self.response_mode,
            "hasPendingClarification": self.pending_clarification is not None
        }
    
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
        self._conversation_ids: Dict[str, int] = {}
    
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
        if key in self._conversation_ids:
            del self._conversation_ids[key]
    
    def get_or_create_conversation(self, db, company_id: int, user_id: int) -> int:
        """Get or create a Conversation record and return its ID."""
        from server.models.conversation import Conversation
        
        key = self._key(company_id, user_id)
        if key in self._conversation_ids:
            return self._conversation_ids[key]
        
        conversation = db.query(Conversation).filter(
            Conversation.company_id == company_id,
            Conversation.user_id == user_id,
            Conversation.is_active == True
        ).order_by(Conversation.updated_at.desc()).first()
        
        if not conversation:
            conversation = Conversation(
                company_id=company_id,
                user_id=user_id,
                title="Chat Session",
                is_active=True
            )
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
        
        self._conversation_ids[key] = conversation.id
        return conversation.id
    
    def add_message_to_conversation(
        self, 
        db, 
        company_id: int, 
        user_id: int, 
        role: str, 
        content: str,
        intent_type: Optional[str] = None,
        scenario_id: Optional[int] = None,
        simulation_id: Optional[int] = None,
        chart_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Add a message to the Conversation record."""
        from server.models.conversation import ConversationMessage, Conversation
        
        conversation_id = self.get_or_create_conversation(db, company_id, user_id)
        
        message = ConversationMessage(
            conversation_id=conversation_id,
            role=role,
            content=content[:10000] if content else "",
            intent_type=intent_type,
            scenario_id=scenario_id,
            simulation_id=simulation_id,
            chart_data=chart_data,
            message_metadata=metadata or {}
        )
        db.add(message)
        
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conversation:
            conversation.updated_at = datetime.utcnow()
            if scenario_id:
                conversation.last_scenario_id = scenario_id
            state = self.get(company_id, user_id)
            conversation.context_metadata = {
                'last_simulation_params': state.last_simulation_params,
                'last_scenario_name': state.last_scenario_name,
            }
        
        db.commit()
    
    def add_recommendation(
        self,
        db,
        company_id: int,
        user_id: int,
        recommendation_type: str,
        recommendation_text: str,
        priority: int = 0,
        context_data: Optional[Dict[str, Any]] = None
    ) -> int:
        """Add a recommendation to the current conversation."""
        from server.models.conversation import ConversationRecommendation
        
        conversation_id = self.get_or_create_conversation(db, company_id, user_id)
        
        recommendation = ConversationRecommendation(
            conversation_id=conversation_id,
            recommendation_type=recommendation_type,
            recommendation_text=recommendation_text,
            priority=priority,
            context_data=context_data
        )
        db.add(recommendation)
        db.commit()
        db.refresh(recommendation)
        return recommendation.id
    
    def persist_to_db(self, db, company_id: int, user_id: int):
        """Persist state to company's metadata_json (legacy) and Conversation model."""
        from server.models.company import Company
        from server.models.conversation import Conversation
        
        state = self.get(company_id, user_id)
        
        company = db.query(Company).filter(Company.id == company_id).first()
        if company:
            metadata = company.metadata_json or {}
            metadata['copilot_state'] = state.to_dict()
            company.metadata_json = metadata
        
        conversation_id = self.get_or_create_conversation(db, company_id, user_id)
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conversation:
            conversation.context_metadata = {
                'last_simulation_params': state.last_simulation_params,
                'last_scenario_name': state.last_scenario_name,
            }
            if state.last_scenario_id:
                conversation.last_scenario_id = state.last_scenario_id
        
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
