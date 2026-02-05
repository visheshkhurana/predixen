"""
Metric Suggestion Engine
Generates metric recommendations based on connected data sources.
"""

from server.metrics.suggestions.engine import SuggestionEngine
from server.metrics.suggestions.service import SuggestionService

__all__ = ["SuggestionEngine", "SuggestionService"]
