"""
Cross-source suggestion rules.
Generates composed metrics that require multiple data sources (CAC, LTV, ROAS).
"""

from typing import Dict, Any, List
from server.metrics.suggestions.rules.base import SuggestionRule, SuggestionOutput


class CACRule(SuggestionRule):
    """Suggest Customer Acquisition Cost (requires ads + customers)."""
    
    rule_id = "cross_cac"
    adapter_key = "cross_source"
    
    def applies(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> bool:
        available_adapters = org_context.get("available_adapters", [])
        has_ads = any(a in available_adapters for a in ["google_ads", "meta_ads", "google_sheets"])
        has_customers = any(a in available_adapters for a in ["stripe", "hubspot", "salesforce"])
        return has_ads and has_customers
    
    def build(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> SuggestionOutput:
        available_adapters = org_context.get("available_adapters", [])
        
        spend_metric = "google_ads_spend" if "google_ads" in available_adapters else "sheets_spend"
        customers_metric = "stripe_new_customers" if "stripe" in available_adapters else "crm_new_customers"
        
        dsl_yaml = f'''meta:
  id: cross_cac
  name: Customer Acquisition Cost (CAC)
  grain: monthly
  unit: USD
  format: currency
  description: Cost to acquire one new customer (Ad Spend / New Customers)

dependencies:
  - metric: {spend_metric}
    required: true
  - metric: {customers_metric}
    required: true

logic:
  type: compose
  expression: {spend_metric} / {customers_metric}

postprocess:
  round: 2
'''
        
        return SuggestionOutput(
            suggestion_key="cross_cac",
            title="Customer Acquisition Cost (CAC)",
            description="Average cost to acquire one new customer.",
            category="Growth",
            metric_dsl_yaml=dsl_yaml,
            dependencies=[
                {"metric": spend_metric, "required": True},
                {"metric": customers_metric, "required": True}
            ],
            confidence=80,
            reason={
                "trigger": "Both ad spend and customer data sources available",
                "fields_used": [],
                "assumptions": [f"Uses {spend_metric} for spend", f"Uses {customers_metric} for customers"]
            },
            adapter_key="cross_source"
        )


class LTVRule(SuggestionRule):
    """Suggest Lifetime Value (requires revenue + churn data)."""
    
    rule_id = "cross_ltv"
    adapter_key = "cross_source"
    
    def applies(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> bool:
        available_adapters = org_context.get("available_adapters", [])
        has_revenue = "stripe" in available_adapters
        return has_revenue
    
    def build(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> SuggestionOutput:
        dsl_yaml = '''meta:
  id: cross_ltv
  name: Customer Lifetime Value (LTV)
  grain: monthly
  unit: USD
  format: currency
  description: Average revenue per customer over their lifetime (ARPU / Churn Rate)

dependencies:
  - metric: stripe_mrr
    required: true
  - metric: stripe_new_customers
    required: true

logic:
  type: compose
  expression: (stripe_mrr / stripe_new_customers) * 24

postprocess:
  round: 0
'''
        
        return SuggestionOutput(
            suggestion_key="cross_ltv",
            title="Customer Lifetime Value (LTV)",
            description="Estimated lifetime value of a customer (assumes 24-month average lifetime).",
            category="Growth",
            metric_dsl_yaml=dsl_yaml,
            dependencies=[
                {"metric": "stripe_mrr", "required": True},
                {"metric": "stripe_new_customers", "required": True}
            ],
            confidence=65,
            reason={
                "trigger": "Revenue data available for LTV calculation",
                "fields_used": [],
                "assumptions": ["Assumes 24-month average customer lifetime", "Uses ARPU approximation"]
            },
            adapter_key="cross_source"
        )


class LTVCACRatioRule(SuggestionRule):
    """Suggest LTV:CAC Ratio."""
    
    rule_id = "cross_ltv_cac_ratio"
    adapter_key = "cross_source"
    
    def applies(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> bool:
        available_adapters = org_context.get("available_adapters", [])
        has_revenue = "stripe" in available_adapters
        has_ads = any(a in available_adapters for a in ["google_ads", "meta_ads", "google_sheets"])
        return has_revenue and has_ads
    
    def build(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> SuggestionOutput:
        dsl_yaml = '''meta:
  id: cross_ltv_cac_ratio
  name: LTV:CAC Ratio
  grain: monthly
  unit: ratio
  format: number
  description: Ratio of customer lifetime value to acquisition cost

dependencies:
  - metric: cross_ltv
    required: true
  - metric: cross_cac
    required: true

logic:
  type: compose
  expression: cross_ltv / cross_cac

postprocess:
  round: 1
'''
        
        return SuggestionOutput(
            suggestion_key="cross_ltv_cac_ratio",
            title="LTV:CAC Ratio",
            description="How many times LTV exceeds CAC (healthy = 3x+).",
            category="Growth",
            metric_dsl_yaml=dsl_yaml,
            dependencies=[
                {"metric": "cross_ltv", "required": True},
                {"metric": "cross_cac", "required": True}
            ],
            confidence=70,
            reason={
                "trigger": "Both LTV and CAC metrics can be computed",
                "fields_used": [],
                "assumptions": ["Requires LTV and CAC metrics to exist"]
            },
            adapter_key="cross_source"
        )


class ROASRule(SuggestionRule):
    """Suggest Return on Ad Spend (requires revenue + ad spend)."""
    
    rule_id = "cross_roas"
    adapter_key = "cross_source"
    
    def applies(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> bool:
        available_adapters = org_context.get("available_adapters", [])
        has_revenue = "stripe" in available_adapters
        has_ads = any(a in available_adapters for a in ["google_ads", "meta_ads", "google_sheets"])
        return has_revenue and has_ads
    
    def build(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> SuggestionOutput:
        available_adapters = org_context.get("available_adapters", [])
        spend_metric = "google_ads_spend" if "google_ads" in available_adapters else "sheets_spend"
        
        dsl_yaml = f'''meta:
  id: cross_roas
  name: Return on Ad Spend (ROAS)
  grain: monthly
  unit: ratio
  format: number
  description: Revenue generated per dollar spent on advertising

dependencies:
  - metric: stripe_revenue_paid
    required: true
  - metric: {spend_metric}
    required: true

logic:
  type: compose
  expression: stripe_revenue_paid / {spend_metric}

postprocess:
  round: 2
'''
        
        return SuggestionOutput(
            suggestion_key="cross_roas",
            title="Return on Ad Spend (ROAS)",
            description="Revenue generated per dollar of ad spend.",
            category="Growth",
            metric_dsl_yaml=dsl_yaml,
            dependencies=[
                {"metric": "stripe_revenue_paid", "required": True},
                {"metric": spend_metric, "required": True}
            ],
            confidence=75,
            reason={
                "trigger": "Both revenue and ad spend data available",
                "fields_used": [],
                "assumptions": [f"Uses {spend_metric} for ad spend"]
            },
            adapter_key="cross_source"
        )


class RunwayRule(SuggestionRule):
    """Suggest Runway metric (cash / burn rate)."""
    
    rule_id = "cross_runway"
    adapter_key = "cross_source"
    
    def applies(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> bool:
        available_adapters = org_context.get("available_adapters", [])
        has_accounting = "quickbooks" in available_adapters
        return has_accounting
    
    def build(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> SuggestionOutput:
        dsl_yaml = '''meta:
  id: cross_runway
  name: Runway (Months)
  grain: monthly
  unit: months
  format: number
  description: Months of runway remaining (Cash Balance / Monthly Burn)

dependencies:
  - metric: quickbooks_burn_rate
    required: true

config:
  cash_balance_source: manual

logic:
  type: formula
  expression: cash_balance / quickbooks_burn_rate

postprocess:
  round: 1
'''
        
        return SuggestionOutput(
            suggestion_key="cross_runway",
            title="Runway (Months)",
            description="Estimated months of runway based on current burn rate.",
            category="Finance",
            metric_dsl_yaml=dsl_yaml,
            dependencies=[
                {"metric": "quickbooks_burn_rate", "required": True},
                {"config": "cash_balance", "required": True}
            ],
            confidence=60,
            reason={
                "trigger": "Burn rate data available",
                "fields_used": [],
                "assumptions": ["Requires manual cash balance input or bank connection"]
            },
            adapter_key="cross_source"
        )


CROSS_SOURCE_RULES: List[SuggestionRule] = [
    CACRule(),
    LTVRule(),
    LTVCACRatioRule(),
    ROASRule(),
    RunwayRule(),
]
