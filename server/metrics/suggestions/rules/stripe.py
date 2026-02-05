"""
Stripe-specific suggestion rules.
Generates metrics for revenue, MRR, ARR, customers, and refunds.
"""

from typing import Dict, Any, List
from server.metrics.suggestions.rules.base import SuggestionRule, SuggestionOutput


class StripeRevenueRule(SuggestionRule):
    """Suggest Revenue metric from paid invoices."""
    
    rule_id = "stripe_revenue_paid"
    adapter_key = "stripe"
    
    def applies(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> bool:
        return (
            self.has_entity(capabilities, "invoices") and
            (self.has_field(capabilities, "invoice.amount") or 
             self.has_field(capabilities, "invoice.amount_paid"))
        )
    
    def build(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> SuggestionOutput:
        amount_field = "amount_paid" if self.has_field(capabilities, "invoice.amount_paid") else "amount"
        
        dsl_yaml = f'''meta:
  id: stripe_revenue
  name: Revenue (Stripe)
  grain: monthly
  unit: USD
  format: currency
  description: Total paid invoice amount from Stripe

dependencies:
  - data_source_type: stripe
    event_type: invoice
    required: true

mapping:
  source_connector: stripe
  event_type: invoice
  filters:
    - field: status
      operator: eq
      value: paid

logic:
  type: aggregate
  measures:
    - name: total_revenue
      agg: sum
      field: {amount_field}
  time_bucket: monthly
'''
        
        return SuggestionOutput(
            suggestion_key="stripe_revenue_paid",
            title="Revenue (Stripe)",
            description="Total revenue from paid Stripe invoices, aggregated monthly.",
            category="Finance",
            metric_dsl_yaml=dsl_yaml,
            dependencies=[{"data_source_type": "stripe", "event_type": "invoice", "required": True}],
            confidence=95,
            reason={
                "trigger": "Detected invoices entity with amount field",
                "fields_used": [f"invoice.{amount_field}", "invoice.status"],
                "assumptions": ["Filters to paid invoices only", "Amount is in cents, will be divided by 100"]
            },
            adapter_key="stripe"
        )


class StripeMRRRule(SuggestionRule):
    """Suggest MRR metric from active subscriptions."""
    
    rule_id = "stripe_mrr"
    adapter_key = "stripe"
    
    def applies(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> bool:
        return (
            self.has_entity(capabilities, "subscriptions") and
            (self.has_field(capabilities, "subscription.plan_amount") or
             self.has_field(capabilities, "subscription.items"))
        )
    
    def build(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> SuggestionOutput:
        dsl_yaml = '''meta:
  id: stripe_mrr
  name: MRR (Stripe)
  grain: monthly
  unit: USD
  format: currency
  description: Monthly Recurring Revenue from active Stripe subscriptions

dependencies:
  - data_source_type: stripe
    event_type: subscription
    required: true

mapping:
  source_connector: stripe
  event_type: subscription
  filters:
    - field: status
      operator: in
      value: ["active", "trialing"]

logic:
  type: aggregate
  measures:
    - name: mrr
      agg: sum
      field: plan_amount
      transform: divide_100
  time_bucket: monthly
'''
        
        return SuggestionOutput(
            suggestion_key="stripe_mrr",
            title="MRR (Stripe)",
            description="Monthly Recurring Revenue from active Stripe subscriptions.",
            category="Finance",
            metric_dsl_yaml=dsl_yaml,
            dependencies=[{"data_source_type": "stripe", "event_type": "subscription", "required": True}],
            confidence=90,
            reason={
                "trigger": "Detected subscriptions entity with plan_amount",
                "fields_used": ["subscription.plan_amount", "subscription.status"],
                "assumptions": ["Filters to active/trialing only", "Normalizes to monthly"]
            },
            adapter_key="stripe"
        )


class StripeARRRule(SuggestionRule):
    """Suggest ARR metric as composed metric (MRR * 12)."""
    
    rule_id = "stripe_arr"
    adapter_key = "stripe"
    
    def applies(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> bool:
        return self.has_entity(capabilities, "subscriptions")
    
    def build(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> SuggestionOutput:
        dsl_yaml = '''meta:
  id: stripe_arr
  name: ARR (Stripe)
  grain: monthly
  unit: USD
  format: currency
  description: Annual Recurring Revenue (MRR * 12)

dependencies:
  - metric: stripe_mrr
    required: true

logic:
  type: compose
  expression: stripe_mrr * 12
'''
        
        return SuggestionOutput(
            suggestion_key="stripe_arr",
            title="ARR (Stripe)",
            description="Annual Recurring Revenue, calculated as MRR * 12.",
            category="Finance",
            metric_dsl_yaml=dsl_yaml,
            dependencies=[{"metric": "stripe_mrr", "required": True}],
            confidence=95,
            reason={
                "trigger": "MRR metric is available for composition",
                "fields_used": [],
                "assumptions": ["Assumes MRR metric exists or will be created"]
            },
            adapter_key="stripe"
        )


class StripeNewCustomersRule(SuggestionRule):
    """Suggest New Customers metric."""
    
    rule_id = "stripe_new_customers"
    adapter_key = "stripe"
    
    def applies(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> bool:
        return self.has_entity(capabilities, "customers")
    
    def build(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> SuggestionOutput:
        dsl_yaml = '''meta:
  id: stripe_new_customers
  name: New Customers (Stripe)
  grain: monthly
  unit: count
  format: number
  description: Count of new customers created in Stripe

dependencies:
  - data_source_type: stripe
    event_type: customer
    required: true

mapping:
  source_connector: stripe
  event_type: customer

logic:
  type: aggregate
  measures:
    - name: new_customers
      agg: count_distinct
      field: id
  time_bucket: monthly
'''
        
        return SuggestionOutput(
            suggestion_key="stripe_new_customers",
            title="New Customers (Stripe)",
            description="Count of new customers created in Stripe each month.",
            category="Growth",
            metric_dsl_yaml=dsl_yaml,
            dependencies=[{"data_source_type": "stripe", "event_type": "customer", "required": True}],
            confidence=90,
            reason={
                "trigger": "Detected customers entity",
                "fields_used": ["customer.id", "customer.created"],
                "assumptions": ["Uses creation date for time bucketing"]
            },
            adapter_key="stripe"
        )


class StripeRefundsRule(SuggestionRule):
    """Suggest Refunds metric."""
    
    rule_id = "stripe_refunds"
    adapter_key = "stripe"
    
    def applies(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> bool:
        return self.has_entity(capabilities, "refunds") or self.has_entity(capabilities, "charges")
    
    def build(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> SuggestionOutput:
        dsl_yaml = '''meta:
  id: stripe_refunds
  name: Refunds (Stripe)
  grain: monthly
  unit: USD
  format: currency
  description: Total refunded amount from Stripe

dependencies:
  - data_source_type: stripe
    event_type: refund
    required: true

mapping:
  source_connector: stripe
  event_type: refund

logic:
  type: aggregate
  measures:
    - name: total_refunds
      agg: sum
      field: amount
      transform: divide_100
  time_bucket: monthly
'''
        
        return SuggestionOutput(
            suggestion_key="stripe_refunds",
            title="Refunds (Stripe)",
            description="Total refunded amount from Stripe each month.",
            category="Finance",
            metric_dsl_yaml=dsl_yaml,
            dependencies=[{"data_source_type": "stripe", "event_type": "refund", "required": True}],
            confidence=85,
            reason={
                "trigger": "Detected refunds or charges entity",
                "fields_used": ["refund.amount"],
                "assumptions": ["Amount is in cents"]
            },
            adapter_key="stripe"
        )


STRIPE_RULES: List[SuggestionRule] = [
    StripeRevenueRule(),
    StripeMRRRule(),
    StripeARRRule(),
    StripeNewCustomersRule(),
    StripeRefundsRule(),
]
