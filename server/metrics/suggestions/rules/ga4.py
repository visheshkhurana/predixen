"""
Google Analytics 4 suggestion rules.
Generates metrics for sessions, users, conversions, and conversion rate.
"""

from typing import Dict, Any, List
from server.metrics.suggestions.rules.base import SuggestionRule, SuggestionOutput


class GA4SessionsRule(SuggestionRule):
    """Suggest Sessions metric from GA4."""
    
    rule_id = "ga4_sessions"
    adapter_key = "ga4"
    
    def applies(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> bool:
        metrics = capabilities.get("metrics", [])
        return "sessions" in metrics or self.has_entity(capabilities, "sessions")
    
    def build(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> SuggestionOutput:
        dsl_yaml = '''meta:
  id: ga4_sessions
  name: Sessions (GA4)
  grain: daily
  unit: count
  format: number
  description: Total website sessions from Google Analytics 4

dependencies:
  - data_source_type: ga4
    event_type: session
    required: true

mapping:
  source_connector: ga4
  event_type: session

logic:
  type: aggregate
  measures:
    - name: sessions
      agg: sum
      field: session_count
  time_bucket: daily
'''
        
        return SuggestionOutput(
            suggestion_key="ga4_sessions",
            title="Sessions (GA4)",
            description="Total website sessions tracked by Google Analytics 4.",
            category="Product",
            metric_dsl_yaml=dsl_yaml,
            dependencies=[{"data_source_type": "ga4", "event_type": "session", "required": True}],
            confidence=95,
            reason={
                "trigger": "GA4 sessions metric available",
                "fields_used": ["session_count", "date"],
                "assumptions": []
            },
            adapter_key="ga4"
        )


class GA4UsersRule(SuggestionRule):
    """Suggest Active Users metric from GA4."""
    
    rule_id = "ga4_users"
    adapter_key = "ga4"
    
    def applies(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> bool:
        metrics = capabilities.get("metrics", [])
        return "activeUsers" in metrics or "users" in metrics or self.has_entity(capabilities, "users")
    
    def build(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> SuggestionOutput:
        dsl_yaml = '''meta:
  id: ga4_users
  name: Active Users (GA4)
  grain: daily
  unit: count
  format: number
  description: Daily active users from Google Analytics 4

dependencies:
  - data_source_type: ga4
    event_type: user
    required: true

mapping:
  source_connector: ga4
  event_type: user

logic:
  type: aggregate
  measures:
    - name: active_users
      agg: sum
      field: user_count
  time_bucket: daily
'''
        
        return SuggestionOutput(
            suggestion_key="ga4_users",
            title="Active Users (GA4)",
            description="Daily active users tracked by Google Analytics 4.",
            category="Product",
            metric_dsl_yaml=dsl_yaml,
            dependencies=[{"data_source_type": "ga4", "event_type": "user", "required": True}],
            confidence=95,
            reason={
                "trigger": "GA4 users metric available",
                "fields_used": ["user_count", "date"],
                "assumptions": []
            },
            adapter_key="ga4"
        )


class GA4ConversionsRule(SuggestionRule):
    """Suggest Conversions metric from GA4."""
    
    rule_id = "ga4_conversions"
    adapter_key = "ga4"
    
    def applies(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> bool:
        metrics = capabilities.get("metrics", [])
        return "conversions" in metrics or self.has_entity(capabilities, "conversions")
    
    def build(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> SuggestionOutput:
        dsl_yaml = '''meta:
  id: ga4_conversions
  name: Conversions (GA4)
  grain: daily
  unit: count
  format: number
  description: Total conversion events from Google Analytics 4

dependencies:
  - data_source_type: ga4
    event_type: conversion
    required: true

mapping:
  source_connector: ga4
  event_type: conversion

logic:
  type: aggregate
  measures:
    - name: conversions
      agg: sum
      field: conversion_count
  time_bucket: daily
'''
        
        return SuggestionOutput(
            suggestion_key="ga4_conversions",
            title="Conversions (GA4)",
            description="Total conversion events tracked by Google Analytics 4.",
            category="Growth",
            metric_dsl_yaml=dsl_yaml,
            dependencies=[{"data_source_type": "ga4", "event_type": "conversion", "required": True}],
            confidence=90,
            reason={
                "trigger": "GA4 conversions metric available",
                "fields_used": ["conversion_count", "date"],
                "assumptions": ["Includes all conversion event types"]
            },
            adapter_key="ga4"
        )


class GA4ConversionRateRule(SuggestionRule):
    """Suggest Conversion Rate as composed metric."""
    
    rule_id = "ga4_conversion_rate"
    adapter_key = "ga4"
    
    def applies(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> bool:
        metrics = capabilities.get("metrics", [])
        has_conversions = "conversions" in metrics or self.has_entity(capabilities, "conversions")
        has_sessions = "sessions" in metrics or self.has_entity(capabilities, "sessions")
        return has_conversions and has_sessions
    
    def build(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> SuggestionOutput:
        dsl_yaml = '''meta:
  id: ga4_conversion_rate
  name: Conversion Rate (GA4)
  grain: daily
  unit: "%"
  format: percentage
  description: Conversion rate (conversions / sessions * 100)

dependencies:
  - metric: ga4_conversions
    required: true
  - metric: ga4_sessions
    required: true

logic:
  type: compose
  expression: (ga4_conversions / ga4_sessions) * 100

postprocess:
  round: 2
'''
        
        return SuggestionOutput(
            suggestion_key="ga4_conversion_rate",
            title="Conversion Rate (GA4)",
            description="Percentage of sessions that resulted in a conversion.",
            category="Growth",
            metric_dsl_yaml=dsl_yaml,
            dependencies=[
                {"metric": "ga4_conversions", "required": True},
                {"metric": "ga4_sessions", "required": True}
            ],
            confidence=90,
            reason={
                "trigger": "Both conversions and sessions metrics available",
                "fields_used": [],
                "assumptions": ["Requires both ga4_conversions and ga4_sessions metrics"]
            },
            adapter_key="ga4"
        )


GA4_RULES: List[SuggestionRule] = [
    GA4SessionsRule(),
    GA4UsersRule(),
    GA4ConversionsRule(),
    GA4ConversionRateRule(),
]
