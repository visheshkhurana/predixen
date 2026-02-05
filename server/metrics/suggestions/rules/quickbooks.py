"""
QuickBooks suggestion rules.
Generates metrics for expenses, COGS, gross margin, and burn rate.
"""

from typing import Dict, Any, List
from server.metrics.suggestions.rules.base import SuggestionRule, SuggestionOutput


class QuickBooksExpensesRule(SuggestionRule):
    """Suggest Expenses metric from QuickBooks."""
    
    rule_id = "quickbooks_expenses"
    adapter_key = "quickbooks"
    
    def applies(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> bool:
        return (
            self.has_entity(capabilities, "expenses") or
            self.has_entity(capabilities, "transactions") or
            self.has_entity(capabilities, "accounts")
        )
    
    def build(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> SuggestionOutput:
        dsl_yaml = '''meta:
  id: quickbooks_expenses
  name: Total Expenses (QuickBooks)
  grain: monthly
  unit: USD
  format: currency
  description: Total expenses from QuickBooks

dependencies:
  - data_source_type: quickbooks
    event_type: expense
    required: true

mapping:
  source_connector: quickbooks
  event_type: expense
  filters:
    - field: account_type
      operator: eq
      value: Expense

logic:
  type: aggregate
  measures:
    - name: total_expenses
      agg: sum
      field: amount
  time_bucket: monthly
'''
        
        return SuggestionOutput(
            suggestion_key="quickbooks_expenses",
            title="Total Expenses (QuickBooks)",
            description="Total expenses aggregated from QuickBooks each month.",
            category="Finance",
            metric_dsl_yaml=dsl_yaml,
            dependencies=[{"data_source_type": "quickbooks", "event_type": "expense", "required": True}],
            confidence=85,
            reason={
                "trigger": "Detected expenses/transactions in QuickBooks",
                "fields_used": ["expense.amount", "expense.account_type"],
                "assumptions": ["Filters to Expense account type"]
            },
            adapter_key="quickbooks"
        )


class QuickBooksCOGSRule(SuggestionRule):
    """Suggest Cost of Goods Sold metric from QuickBooks."""
    
    rule_id = "quickbooks_cogs"
    adapter_key = "quickbooks"
    
    def applies(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> bool:
        accounts = capabilities.get("account_types", [])
        return "CostOfGoodsSold" in accounts or self.has_entity(capabilities, "accounts")
    
    def build(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> SuggestionOutput:
        dsl_yaml = '''meta:
  id: quickbooks_cogs
  name: COGS (QuickBooks)
  grain: monthly
  unit: USD
  format: currency
  description: Cost of Goods Sold from QuickBooks

dependencies:
  - data_source_type: quickbooks
    event_type: transaction
    required: true

mapping:
  source_connector: quickbooks
  event_type: transaction
  filters:
    - field: account_type
      operator: eq
      value: CostOfGoodsSold

logic:
  type: aggregate
  measures:
    - name: cogs
      agg: sum
      field: amount
  time_bucket: monthly
'''
        
        return SuggestionOutput(
            suggestion_key="quickbooks_cogs",
            title="COGS (QuickBooks)",
            description="Cost of Goods Sold from QuickBooks Cost accounts.",
            category="Finance",
            metric_dsl_yaml=dsl_yaml,
            dependencies=[{"data_source_type": "quickbooks", "event_type": "transaction", "required": True}],
            confidence=75,
            reason={
                "trigger": "QuickBooks account data available",
                "fields_used": ["transaction.amount", "transaction.account_type"],
                "assumptions": ["Requires CostOfGoodsSold account type mapping"]
            },
            adapter_key="quickbooks"
        )


class QuickBooksGrossMarginRule(SuggestionRule):
    """Suggest Gross Margin as composed metric."""
    
    rule_id = "quickbooks_gross_margin"
    adapter_key = "quickbooks"
    
    def applies(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> bool:
        return self.has_entity(capabilities, "accounts")
    
    def build(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> SuggestionOutput:
        dsl_yaml = '''meta:
  id: quickbooks_gross_margin
  name: Gross Margin (%)
  grain: monthly
  unit: "%"
  format: percentage
  description: Gross Margin percentage ((Revenue - COGS) / Revenue * 100)

dependencies:
  - metric: stripe_revenue_paid
    required: true
  - metric: quickbooks_cogs
    required: true

logic:
  type: compose
  expression: ((stripe_revenue_paid - quickbooks_cogs) / stripe_revenue_paid) * 100

postprocess:
  round: 1
'''
        
        return SuggestionOutput(
            suggestion_key="quickbooks_gross_margin",
            title="Gross Margin (%)",
            description="Gross margin percentage calculated from Revenue and COGS.",
            category="Finance",
            metric_dsl_yaml=dsl_yaml,
            dependencies=[
                {"metric": "stripe_revenue_paid", "required": True},
                {"metric": "quickbooks_cogs", "required": True}
            ],
            confidence=70,
            reason={
                "trigger": "QuickBooks COGS data available",
                "fields_used": [],
                "assumptions": ["Requires both Revenue (Stripe) and COGS (QuickBooks) metrics"]
            },
            adapter_key="quickbooks"
        )


class QuickBooksBurnRateRule(SuggestionRule):
    """Suggest Burn Rate metric."""
    
    rule_id = "quickbooks_burn_rate"
    adapter_key = "quickbooks"
    
    def applies(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> bool:
        return (
            self.has_entity(capabilities, "expenses") or
            self.has_entity(capabilities, "transactions")
        )
    
    def build(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> SuggestionOutput:
        dsl_yaml = '''meta:
  id: quickbooks_burn_rate
  name: Burn Rate (QuickBooks)
  grain: monthly
  unit: USD
  format: currency
  description: Monthly cash burn from operating expenses

dependencies:
  - data_source_type: quickbooks
    event_type: transaction
    required: true

mapping:
  source_connector: quickbooks
  event_type: transaction
  filters:
    - field: account_type
      operator: in
      value: ["Expense", "OtherExpense", "CostOfGoodsSold"]

logic:
  type: aggregate
  measures:
    - name: burn_rate
      agg: sum
      field: amount
  time_bucket: monthly
'''
        
        return SuggestionOutput(
            suggestion_key="quickbooks_burn_rate",
            title="Burn Rate (QuickBooks)",
            description="Monthly operating expenses (cash burn) from QuickBooks.",
            category="Finance",
            metric_dsl_yaml=dsl_yaml,
            dependencies=[{"data_source_type": "quickbooks", "event_type": "transaction", "required": True}],
            confidence=80,
            reason={
                "trigger": "Expense transactions available in QuickBooks",
                "fields_used": ["transaction.amount", "transaction.account_type"],
                "assumptions": ["Includes all expense account types"]
            },
            adapter_key="quickbooks"
        )


QUICKBOOKS_RULES: List[SuggestionRule] = [
    QuickBooksExpensesRule(),
    QuickBooksCOGSRule(),
    QuickBooksGrossMarginRule(),
    QuickBooksBurnRateRule(),
]
