"""
Base class for suggestion rules.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional


@dataclass
class SuggestionOutput:
    """Output from a suggestion rule."""
    suggestion_key: str
    title: str
    description: str
    category: str
    metric_dsl_yaml: str
    dependencies: List[Dict[str, Any]]
    confidence: int
    reason: Dict[str, Any]
    adapter_key: str


class SuggestionRule(ABC):
    """
    Base class for deterministic metric suggestion rules.
    Each rule checks if it applies to given capabilities and builds a suggestion.
    """
    
    rule_id: str = "base"
    adapter_key: str = "generic"
    
    @abstractmethod
    def applies(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> bool:
        """Check if this rule applies to the given capabilities."""
        pass
    
    @abstractmethod
    def build(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> SuggestionOutput:
        """Build the suggestion output if the rule applies."""
        pass
    
    def has_entity(self, capabilities: Dict[str, Any], entity: str) -> bool:
        """Helper to check if an entity exists in capabilities."""
        entities = capabilities.get("entities", [])
        return entity in entities
    
    def has_field(self, capabilities: Dict[str, Any], field: str) -> bool:
        """Helper to check if a field exists in capabilities."""
        fields = capabilities.get("fields", {})
        return field in fields and fields[field] == "present"
    
    def get_time_field(self, capabilities: Dict[str, Any]) -> str:
        """Get the time field from capabilities, default to 'created'."""
        return capabilities.get("time_field", "created")
