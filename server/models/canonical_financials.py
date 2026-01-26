"""
Canonical Financial Model - Single source of truth for all financial data.

This module defines the NormalizedMonthlyFinancials schema with:
- Consistent sign conventions (expenses positive, netBurn = expenses - revenue)
- Full traceability via sources mapping
- Validation warnings and errors
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ValidationSeverity(str, Enum):
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


@dataclass
class ValidationWarning:
    code: str
    message: str
    fields: List[str]
    severity: ValidationSeverity = ValidationSeverity.WARN


@dataclass
class ValidationError:
    code: str
    message: str
    fields: List[str]
    severity: ValidationSeverity = ValidationSeverity.ERROR


@dataclass
class SourceReference:
    sheet: Optional[str] = None
    row_labels: Optional[List[str]] = None
    column: Optional[str] = None
    cell_range: Optional[str] = None
    raw_value: Optional[float] = None
    currency_converted: bool = False


@dataclass
class Period:
    year: int
    month: int
    label: str


@dataclass
class ExpenseBreakdown:
    cogs: Optional[float] = None
    marketing: Optional[float] = None
    payroll: Optional[float] = None
    operating: Optional[float] = None
    other: Optional[float] = None


@dataclass
class NormalizedMonthlyFinancials:
    """
    Canonical financial model representing a single month's financials.
    
    Sign Conventions:
    - All expense values are stored as POSITIVE numbers
    - revenue is positive
    - netBurn = totalExpenses - revenue
      - netBurn > 0 means burning cash
      - netBurn < 0 means profitable (net positive cash flow)
    - runwayMonths = cashOnHand / netBurn when netBurn > 0, else None
    """
    period: Period
    
    revenue: float = 0.0
    cash_on_hand: Optional[float] = None
    
    expenses: ExpenseBreakdown = field(default_factory=ExpenseBreakdown)
    total_expenses: float = 0.0
    
    net_burn: float = 0.0
    runway_months: Optional[float] = None
    is_profitable: bool = False
    
    sources: Dict[str, SourceReference] = field(default_factory=dict)
    validation: Dict[str, List] = field(default_factory=lambda: {"warnings": [], "errors": []})
    
    currency: str = "USD"
    fx_rate_used: Optional[float] = None
    detected_currency: Optional[str] = None
    
    def compute_derived_metrics(self):
        """Compute totalExpenses, netBurn, runway, isProfitable from components."""
        exp = self.expenses
        self.total_expenses = (
            (exp.cogs or 0) +
            (exp.marketing or 0) +
            (exp.payroll or 0) +
            (exp.operating or 0) +
            (exp.other or 0)
        )
        
        self.net_burn = self.total_expenses - self.revenue
        self.is_profitable = self.net_burn < 0
        
        if self.net_burn > 0 and self.cash_on_hand and self.cash_on_hand > 0:
            self.runway_months = self.cash_on_hand / self.net_burn
        else:
            self.runway_months = None
    
    def add_warning(self, code: str, message: str, fields: List[str], severity: str = "warn"):
        warning = {
            "code": code,
            "message": message,
            "fields": fields,
            "severity": severity
        }
        self.validation["warnings"].append(warning)
    
    def add_error(self, code: str, message: str, fields: List[str]):
        error = {
            "code": code,
            "message": message,
            "fields": fields,
            "severity": "error"
        }
        self.validation["errors"].append(error)
    
    def has_errors(self) -> bool:
        return len(self.validation.get("errors", [])) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        sources_dict = {}
        for key, ref in self.sources.items():
            sources_dict[key] = {
                "sheet": ref.sheet,
                "row_labels": ref.row_labels,
                "column": ref.column,
                "cell_range": ref.cell_range,
                "raw_value": ref.raw_value,
                "currency_converted": ref.currency_converted
            } if isinstance(ref, SourceReference) else ref
        
        return {
            "period": {
                "year": self.period.year,
                "month": self.period.month,
                "label": self.period.label
            },
            "revenue": self.revenue,
            "cash_on_hand": self.cash_on_hand,
            "expenses": {
                "cogs": self.expenses.cogs,
                "marketing": self.expenses.marketing,
                "payroll": self.expenses.payroll,
                "operating": self.expenses.operating,
                "other": self.expenses.other
            },
            "total_expenses": self.total_expenses,
            "net_burn": self.net_burn,
            "runway_months": self.runway_months,
            "is_profitable": self.is_profitable,
            "sources": sources_dict,
            "validation": self.validation,
            "currency": self.currency,
            "fx_rate_used": self.fx_rate_used,
            "detected_currency": self.detected_currency
        }


MARKETING_KEYWORDS = [
    "marketing",
    "sales & marketing",
    "sales and marketing",
    "user acquisition",
    "brand",
    "performance marketing",
    "digital marketing",
    "india marketing",
    "international marketing",
    "advertising",
    "ads",
    "media spend",
    "growth marketing",
    "content marketing",
    "social media",
    "influencer",
    "paid media",
    "customer acquisition",
]

PAYROLL_KEYWORDS = [
    "payroll",
    "salaries",
    "salary",
    "wages",
    "employee costs",
    "personnel",
    "compensation",
    "staff costs",
    "headcount costs",
]

COGS_KEYWORDS = [
    "cogs",
    "cost of goods sold",
    "cost of goods",
    "cost of revenue",
    "cost of sales",
    "direct costs",
    "direct expenses",
]

OPERATING_KEYWORDS = [
    "operating",
    "operating expenses",
    "g&a",
    "general & admin",
    "general and admin",
    "administration",
    "office",
    "rent",
    "utilities",
    "insurance",
    "legal",
    "professional fees",
]

OTHER_OPEX_KEYWORDS = [
    "other opex",
    "other operating",
    "other expenses",
    "miscellaneous",
    "misc",
    "sundry",
]

REVENUE_KEYWORDS = [
    "total revenue",
    "revenue",
    "net revenue",
    "sales",
    "total sales",
    "gross revenue",
    "income",
    "turnover",
]


def run_validation(financials: NormalizedMonthlyFinancials) -> NormalizedMonthlyFinancials:
    """
    Run validation and anomaly detection on normalized financials.
    Adds warnings/errors to the financials object.
    """
    exp = financials.expenses
    revenue = financials.revenue
    
    if financials.revenue < 0:
        financials.add_error(
            "NEGATIVE_REVENUE",
            "Revenue cannot be negative",
            ["revenue"]
        )
    
    if exp.cogs is not None and exp.cogs < 0:
        financials.add_error("NEGATIVE_COGS", "COGS cannot be negative", ["cogs"])
    
    if exp.marketing is not None and exp.marketing < 0:
        financials.add_error("NEGATIVE_MARKETING", "Marketing cannot be negative", ["marketing"])
    
    if exp.payroll is None:
        financials.add_warning(
            "PAYROLL_NOT_FOUND",
            "Payroll expenses not detected in the data. Consider adding manually if applicable.",
            ["payroll"],
            "warn"
        )
    
    if revenue > 1_000_000:
        if exp.marketing is not None and exp.marketing < revenue * 0.001:
            financials.add_warning(
                "MARKETING_SUSPICIOUSLY_LOW",
                f"Marketing (${exp.marketing:,.0f}) is less than 0.1% of revenue - may be missing marketing line items",
                ["marketing"],
                "warn"
            )
        
        if exp.marketing is not None and exp.marketing > revenue * 0.8:
            financials.add_warning(
                "MARKETING_SUSPICIOUSLY_HIGH",
                f"Marketing (${exp.marketing:,.0f}) is more than 80% of revenue - possible mapping issue",
                ["marketing"],
                "warn"
            )
    
    if revenue > 0 and abs(financials.net_burn) > revenue * 2:
        financials.add_warning(
            "NET_BURN_UNUSUAL",
            f"Net burn magnitude (${abs(financials.net_burn):,.0f}) is more than 2x revenue",
            ["net_burn"],
            "warn"
        )
    
    computed_total = (
        (exp.cogs or 0) +
        (exp.marketing or 0) +
        (exp.payroll or 0) +
        (exp.operating or 0) +
        (exp.other or 0)
    )
    if financials.total_expenses > 0:
        diff = abs(computed_total - financials.total_expenses)
        if diff > financials.total_expenses * 0.02:
            financials.add_warning(
                "EXPENSE_SUM_MISMATCH",
                f"Computed expense sum (${computed_total:,.0f}) differs from total (${financials.total_expenses:,.0f})",
                ["total_expenses"],
                "warn"
            )
    
    return financials
