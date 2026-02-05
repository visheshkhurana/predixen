"""
Google Sheets / CSV suggestion rules.
Generates metrics based on detected column patterns.
"""

from typing import Dict, Any, List
from server.metrics.suggestions.rules.base import SuggestionRule, SuggestionOutput


class SheetsRevenueRule(SuggestionRule):
    """Suggest Revenue metric if revenue-like columns detected."""
    
    rule_id = "sheets_revenue"
    adapter_key = "google_sheets"
    
    REVENUE_COLUMNS = ["revenue", "sales", "income", "total_revenue", "gross_revenue", "net_revenue"]
    
    def applies(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> bool:
        columns = [c.lower() for c in capabilities.get("columns", [])]
        return any(col in columns for col in self.REVENUE_COLUMNS)
    
    def _find_column(self, capabilities: Dict[str, Any]) -> str:
        columns = capabilities.get("columns", [])
        for col in columns:
            if col.lower() in self.REVENUE_COLUMNS:
                return col
        return "revenue"
    
    def build(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> SuggestionOutput:
        value_column = self._find_column(capabilities)
        time_column = capabilities.get("time_column", "date")
        
        dsl_yaml = f'''meta:
  id: sheets_revenue
  name: Revenue (Sheets)
  grain: monthly
  unit: USD
  format: currency
  description: Revenue data imported from spreadsheet

dependencies:
  - data_source_type: google_sheets
    required: true

mapping:
  source_connector: google_sheets
  value_column: {value_column}
  time_column: {time_column}

logic:
  type: aggregate
  measures:
    - name: revenue
      agg: sum
      field: {value_column}
  time_bucket: monthly
'''
        
        return SuggestionOutput(
            suggestion_key="sheets_revenue",
            title="Revenue (Sheets)",
            description=f"Revenue from spreadsheet column '{value_column}'.",
            category="Finance",
            metric_dsl_yaml=dsl_yaml,
            dependencies=[{"data_source_type": "google_sheets", "required": True}],
            confidence=70,
            reason={
                "trigger": f"Detected revenue column: {value_column}",
                "fields_used": [value_column, time_column],
                "assumptions": ["Column contains numeric revenue values"]
            },
            adapter_key="google_sheets"
        )


class SheetsSpendRule(SuggestionRule):
    """Suggest Spend metric if spend-like columns detected."""
    
    rule_id = "sheets_spend"
    adapter_key = "google_sheets"
    
    SPEND_COLUMNS = ["spend", "cost", "expenses", "expense", "ad_spend", "marketing_spend"]
    
    def applies(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> bool:
        columns = [c.lower() for c in capabilities.get("columns", [])]
        return any(col in columns for col in self.SPEND_COLUMNS)
    
    def _find_column(self, capabilities: Dict[str, Any]) -> str:
        columns = capabilities.get("columns", [])
        for col in columns:
            if col.lower() in self.SPEND_COLUMNS:
                return col
        return "spend"
    
    def build(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> SuggestionOutput:
        value_column = self._find_column(capabilities)
        time_column = capabilities.get("time_column", "date")
        
        dsl_yaml = f'''meta:
  id: sheets_spend
  name: Spend (Sheets)
  grain: monthly
  unit: USD
  format: currency
  description: Spend/cost data imported from spreadsheet

dependencies:
  - data_source_type: google_sheets
    required: true

mapping:
  source_connector: google_sheets
  value_column: {value_column}
  time_column: {time_column}

logic:
  type: aggregate
  measures:
    - name: spend
      agg: sum
      field: {value_column}
  time_bucket: monthly
'''
        
        return SuggestionOutput(
            suggestion_key="sheets_spend",
            title="Spend (Sheets)",
            description=f"Spend from spreadsheet column '{value_column}'.",
            category="Finance",
            metric_dsl_yaml=dsl_yaml,
            dependencies=[{"data_source_type": "google_sheets", "required": True}],
            confidence=70,
            reason={
                "trigger": f"Detected spend column: {value_column}",
                "fields_used": [value_column, time_column],
                "assumptions": ["Column contains numeric spend values"]
            },
            adapter_key="google_sheets"
        )


class SheetsHeadcountRule(SuggestionRule):
    """Suggest Headcount metric if employee-like columns detected."""
    
    rule_id = "sheets_headcount"
    adapter_key = "google_sheets"
    
    HEADCOUNT_COLUMNS = ["headcount", "employees", "team_size", "hires", "staff"]
    
    def applies(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> bool:
        columns = [c.lower() for c in capabilities.get("columns", [])]
        return any(col in columns for col in self.HEADCOUNT_COLUMNS)
    
    def _find_column(self, capabilities: Dict[str, Any]) -> str:
        columns = capabilities.get("columns", [])
        for col in columns:
            if col.lower() in self.HEADCOUNT_COLUMNS:
                return col
        return "headcount"
    
    def build(self, capabilities: Dict[str, Any], org_context: Dict[str, Any]) -> SuggestionOutput:
        value_column = self._find_column(capabilities)
        time_column = capabilities.get("time_column", "date")
        
        dsl_yaml = f'''meta:
  id: sheets_headcount
  name: Headcount (Sheets)
  grain: monthly
  unit: count
  format: number
  description: Team size data imported from spreadsheet

dependencies:
  - data_source_type: google_sheets
    required: true

mapping:
  source_connector: google_sheets
  value_column: {value_column}
  time_column: {time_column}

logic:
  type: aggregate
  measures:
    - name: headcount
      agg: max
      field: {value_column}
  time_bucket: monthly
'''
        
        return SuggestionOutput(
            suggestion_key="sheets_headcount",
            title="Headcount (Sheets)",
            description=f"Team size from spreadsheet column '{value_column}'.",
            category="Finance",
            metric_dsl_yaml=dsl_yaml,
            dependencies=[{"data_source_type": "google_sheets", "required": True}],
            confidence=65,
            reason={
                "trigger": f"Detected headcount column: {value_column}",
                "fields_used": [value_column, time_column],
                "assumptions": ["Uses max value per period (point-in-time snapshot)"]
            },
            adapter_key="google_sheets"
        )


SHEETS_RULES: List[SuggestionRule] = [
    SheetsRevenueRule(),
    SheetsSpendRule(),
    SheetsHeadcountRule(),
]
