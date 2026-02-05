"""
Suggestion Engine - runs rules against capabilities to generate suggestions.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from server.metrics.suggestions.rules import ALL_RULES, SuggestionRule
from server.metrics.suggestions.rules.base import SuggestionOutput

logger = logging.getLogger(__name__)


class SuggestionEngine:
    """
    Runs deterministic rules against connector capabilities to generate metric suggestions.
    """
    
    def __init__(self):
        self.rules = ALL_RULES
    
    def run_for_adapter(
        self,
        adapter_key: str,
        capabilities: Dict[str, Any],
        org_context: Dict[str, Any]
    ) -> List[SuggestionOutput]:
        """
        Run all applicable rules for a specific adapter.
        
        Args:
            adapter_key: The connector type (stripe, ga4, quickbooks, etc.)
            capabilities: Discovered capabilities from the connector
            org_context: Organization context (available_adapters, etc.)
        
        Returns:
            List of suggestion outputs
        """
        suggestions = []
        
        for rule in self.rules:
            if rule.adapter_key != adapter_key and rule.adapter_key != "cross_source":
                continue
            
            try:
                if rule.applies(capabilities, org_context):
                    output = rule.build(capabilities, org_context)
                    suggestions.append(output)
                    logger.debug(f"Rule {rule.rule_id} matched, generated: {output.suggestion_key}")
            except Exception as e:
                logger.warning(f"Rule {rule.rule_id} failed: {e}")
        
        return suggestions
    
    def run_cross_source(
        self,
        all_capabilities: Dict[str, Dict[str, Any]],
        org_context: Dict[str, Any]
    ) -> List[SuggestionOutput]:
        """
        Run cross-source rules that require multiple data sources.
        
        Args:
            all_capabilities: Dict mapping adapter_key to capabilities
            org_context: Organization context with available_adapters list
        
        Returns:
            List of cross-source suggestion outputs
        """
        suggestions = []
        
        merged_capabilities = {}
        for adapter_key, caps in all_capabilities.items():
            for key, value in caps.items():
                if key not in merged_capabilities:
                    merged_capabilities[key] = value
                elif isinstance(value, list):
                    merged_capabilities[key] = list(set(merged_capabilities.get(key, []) + value))
                elif isinstance(value, dict):
                    merged_capabilities[key] = {**merged_capabilities.get(key, {}), **value}
        
        for rule in self.rules:
            if rule.adapter_key != "cross_source":
                continue
            
            try:
                if rule.applies(merged_capabilities, org_context):
                    output = rule.build(merged_capabilities, org_context)
                    suggestions.append(output)
                    logger.debug(f"Cross-source rule {rule.rule_id} matched: {output.suggestion_key}")
            except Exception as e:
                logger.warning(f"Cross-source rule {rule.rule_id} failed: {e}")
        
        return suggestions
    
    def run_all(
        self,
        all_capabilities: Dict[str, Dict[str, Any]],
        org_context: Dict[str, Any]
    ) -> List[SuggestionOutput]:
        """
        Run all rules (adapter-specific + cross-source).
        
        Args:
            all_capabilities: Dict mapping adapter_key to capabilities
            org_context: Organization context
        
        Returns:
            Combined list of all suggestion outputs
        """
        all_suggestions = []
        
        org_context["available_adapters"] = list(all_capabilities.keys())
        
        for adapter_key, capabilities in all_capabilities.items():
            adapter_suggestions = self.run_for_adapter(adapter_key, capabilities, org_context)
            all_suggestions.extend(adapter_suggestions)
        
        cross_suggestions = self.run_cross_source(all_capabilities, org_context)
        all_suggestions.extend(cross_suggestions)
        
        return all_suggestions
    
    def check_dependencies_satisfied(
        self,
        suggestion: SuggestionOutput,
        existing_metrics: List[str],
        available_adapters: List[str]
    ) -> tuple[bool, List[str]]:
        """
        Check if a suggestion's dependencies are satisfied.
        
        Returns:
            Tuple of (is_satisfied, list of missing dependencies)
        """
        missing = []
        
        for dep in suggestion.dependencies:
            if "metric" in dep:
                if dep["metric"] not in existing_metrics:
                    if dep.get("required", False):
                        missing.append(f"metric:{dep['metric']}")
            elif "data_source_type" in dep:
                if dep["data_source_type"] not in available_adapters:
                    if dep.get("required", False):
                        missing.append(f"adapter:{dep['data_source_type']}")
        
        return len(missing) == 0, missing
