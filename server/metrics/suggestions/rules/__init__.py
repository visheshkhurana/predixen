"""
Suggestion Rules Package
Contains deterministic rules for generating metric suggestions.
"""

from server.metrics.suggestions.rules.base import SuggestionRule
from server.metrics.suggestions.rules.stripe import STRIPE_RULES
from server.metrics.suggestions.rules.ga4 import GA4_RULES
from server.metrics.suggestions.rules.quickbooks import QUICKBOOKS_RULES
from server.metrics.suggestions.rules.sheets import SHEETS_RULES
from server.metrics.suggestions.rules.cross_source import CROSS_SOURCE_RULES

ALL_RULES = STRIPE_RULES + GA4_RULES + QUICKBOOKS_RULES + SHEETS_RULES + CROSS_SOURCE_RULES

__all__ = [
    "SuggestionRule",
    "STRIPE_RULES",
    "GA4_RULES", 
    "QUICKBOOKS_RULES",
    "SHEETS_RULES",
    "CROSS_SOURCE_RULES",
    "ALL_RULES",
]
