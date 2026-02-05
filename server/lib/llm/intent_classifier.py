"""
Intent Classifier - Uses Gemini Flash to classify user queries into task types.
This enables intelligent routing to the optimal LLM for each request.
"""
import os
import json
import logging
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    """Intent types for classifier-based routing."""
    WEB_SEARCH = "web_search"
    MARKET_RESEARCH = "market_research"
    COMPETITOR_ANALYSIS = "competitor_analysis"
    FINANCIAL_ANALYSIS = "financial_analysis"
    METRICS_EXTRACTION = "metrics_extraction"
    COMPLEX_REASONING = "complex_reasoning"
    CODING = "coding"
    STRATEGY = "strategy"
    PLANNING = "planning"
    GENERAL_CHAT = "general_chat"
    QUICK_TASK = "quick_task"
    VISION = "vision"
    DATA_PROCESSING = "data_processing"
    DOCUMENT_ANALYSIS = "document_analysis"
    REAL_TIME_DATA = "real_time_data"
    NEWS_CURRENT_EVENTS = "news_current_events"


@dataclass
class ClassificationResult:
    """Result of intent classification."""
    primary_intent: IntentType
    confidence: float
    secondary_intent: Optional[IntentType] = None
    requires_web_search: bool = False
    requires_real_time: bool = False
    complexity: str = "medium"
    reasoning: str = ""


INTENT_DESCRIPTIONS = {
    IntentType.WEB_SEARCH: "General web search for current information, facts, or data",
    IntentType.MARKET_RESEARCH: "Research on market trends, industry analysis, sizing",
    IntentType.COMPETITOR_ANALYSIS: "Analysis of competitors, competitive landscape",
    IntentType.FINANCIAL_ANALYSIS: "Analysis of financial data, metrics, KPIs, ratios",
    IntentType.METRICS_EXTRACTION: "Extracting structured data from documents or text",
    IntentType.COMPLEX_REASONING: "Multi-step reasoning, logical analysis, complex problems",
    IntentType.CODING: "Code generation, debugging, refactoring, technical implementation",
    IntentType.STRATEGY: "Business strategy, go-to-market, positioning, planning",
    IntentType.PLANNING: "Project planning, roadmaps, timelines, task breakdown",
    IntentType.GENERAL_CHAT: "General conversation, simple Q&A, explanations",
    IntentType.QUICK_TASK: "Simple formatting, summaries, quick responses",
    IntentType.VISION: "Image analysis, document OCR, visual understanding",
    IntentType.DATA_PROCESSING: "Data transformation, aggregation, calculations",
    IntentType.DOCUMENT_ANALYSIS: "Analyzing documents, contracts, reports",
    IntentType.REAL_TIME_DATA: "Current prices, stock data, live statistics",
    IntentType.NEWS_CURRENT_EVENTS: "Recent news, current events, recent announcements",
}

WEB_SEARCH_INTENTS = {
    IntentType.WEB_SEARCH,
    IntentType.MARKET_RESEARCH,
    IntentType.COMPETITOR_ANALYSIS,
    IntentType.REAL_TIME_DATA,
    IntentType.NEWS_CURRENT_EVENTS,
}

WEB_SEARCH_KEYWORDS = [
    "latest", "current", "today", "now", "recent", "news",
    "price", "stock", "market", "competitor", "compare",
    "trend", "forecast", "2024", "2025", "2026",
    "what is", "who is", "where is", "when did",
    "how much", "how many", "statistics", "data",
    "benchmark", "industry", "sector", "company",
    "funding", "raised", "valuation", "revenue",
    "search", "find", "look up", "research",
]

CLASSIFIER_SYSTEM_PROMPT = """You are an intent classifier for a financial intelligence platform. 
Classify user queries into the most appropriate task type for LLM routing.

TASK TYPES:
- web_search: Requires searching the web for current information
- market_research: Industry/market analysis, sizing, trends
- competitor_analysis: Analyzing specific competitors
- financial_analysis: Financial data analysis, KPIs, ratios, metrics
- metrics_extraction: Extracting structured data from text/documents
- complex_reasoning: Multi-step logical reasoning, complex analysis
- coding: Code generation, debugging, technical implementation
- strategy: Business strategy, GTM, positioning
- planning: Project planning, roadmaps, timelines
- general_chat: Simple Q&A, explanations, conversation
- quick_task: Simple formatting, summaries, quick responses
- vision: Image/document visual analysis
- data_processing: Data transformation, calculations
- document_analysis: Analyzing documents, contracts, reports
- real_time_data: Current prices, live statistics
- news_current_events: Recent news, announcements

ROUTING RULES:
1. If query asks about current/recent events, news, or real-time data → web_search/real_time_data
2. If query mentions competitors by name or asks to compare companies → competitor_analysis
3. If query asks about market size, industry trends → market_research
4. If query involves financial metrics, runway, burn rate → financial_analysis
5. If query requires step-by-step reasoning or complex analysis → complex_reasoning
6. If query is about code, implementation, or debugging → coding
7. If query is about business strategy, GTM, positioning → strategy
8. Simple questions or explanations → general_chat

Respond with JSON:
{
  "primary_intent": "<intent_type>",
  "confidence": <0.0-1.0>,
  "secondary_intent": "<intent_type or null>",
  "requires_web_search": <true/false>,
  "requires_real_time": <true/false>,
  "complexity": "<low/medium/high>",
  "reasoning": "<brief explanation>"
}"""


class IntentClassifier:
    """
    Classifies user intents using Gemini Flash for fast, cost-effective routing.
    Falls back to keyword-based classification if LLM is unavailable.
    """
    
    def __init__(
        self,
        db_session=None,
        company_id: Optional[int] = None,
        user_id: Optional[int] = None
    ):
        self.db = db_session
        self.company_id = company_id
        self.user_id = user_id
        self._gemini_client = None
    
    @property
    def gemini_client(self):
        """Lazy-load Gemini client."""
        if self._gemini_client is None:
            try:
                from server.lib.llm.gemini_client import GeminiClient
                self._gemini_client = GeminiClient(
                    db_session=self.db,
                    company_id=self.company_id,
                    user_id=self.user_id,
                    pii_mode="off"
                )
            except (ValueError, ImportError) as e:
                logger.warning(f"Gemini not available for classification: {e}")
                return None
        return self._gemini_client
    
    def _keyword_classify(self, query: str) -> ClassificationResult:
        """
        Fast keyword-based classification fallback.
        Used when LLM classification is unavailable or for quick pre-filtering.
        """
        query_lower = query.lower()
        
        requires_web = any(kw in query_lower for kw in WEB_SEARCH_KEYWORDS)
        
        if any(kw in query_lower for kw in ["competitor", "vs ", "versus", "compare to", "compared to"]):
            return ClassificationResult(
                primary_intent=IntentType.COMPETITOR_ANALYSIS,
                confidence=0.8,
                requires_web_search=True,
                complexity="medium",
                reasoning="Detected competitor-related keywords"
            )
        
        if any(kw in query_lower for kw in ["market size", "tam", "sam", "industry", "sector trend"]):
            return ClassificationResult(
                primary_intent=IntentType.MARKET_RESEARCH,
                confidence=0.8,
                requires_web_search=True,
                complexity="medium",
                reasoning="Detected market research keywords"
            )
        
        if any(kw in query_lower for kw in ["news", "recent", "today", "latest", "just announced"]):
            return ClassificationResult(
                primary_intent=IntentType.NEWS_CURRENT_EVENTS,
                confidence=0.8,
                requires_web_search=True,
                requires_real_time=True,
                complexity="low",
                reasoning="Detected news/current events keywords"
            )
        
        if any(kw in query_lower for kw in ["price", "stock", "valuation", "funding round"]):
            return ClassificationResult(
                primary_intent=IntentType.REAL_TIME_DATA,
                confidence=0.8,
                requires_web_search=True,
                requires_real_time=True,
                complexity="low",
                reasoning="Detected real-time data keywords"
            )
        
        if any(kw in query_lower for kw in ["runway", "burn rate", "mrr", "arr", "ltv", "cac", "churn"]):
            return ClassificationResult(
                primary_intent=IntentType.FINANCIAL_ANALYSIS,
                confidence=0.85,
                requires_web_search=False,
                complexity="medium",
                reasoning="Detected financial metrics keywords"
            )
        
        if any(kw in query_lower for kw in ["code", "function", "implement", "debug", "error", "bug", "api"]):
            return ClassificationResult(
                primary_intent=IntentType.CODING,
                confidence=0.85,
                requires_web_search=False,
                complexity="high",
                reasoning="Detected coding-related keywords"
            )
        
        if any(kw in query_lower for kw in ["strategy", "gtm", "go-to-market", "positioning", "differentiate"]):
            return ClassificationResult(
                primary_intent=IntentType.STRATEGY,
                confidence=0.8,
                requires_web_search=requires_web,
                complexity="high",
                reasoning="Detected strategy keywords"
            )
        
        if any(kw in query_lower for kw in ["analyze", "explain why", "reason", "because", "therefore"]):
            return ClassificationResult(
                primary_intent=IntentType.COMPLEX_REASONING,
                confidence=0.7,
                requires_web_search=requires_web,
                complexity="high",
                reasoning="Detected reasoning-related keywords"
            )
        
        if requires_web:
            return ClassificationResult(
                primary_intent=IntentType.WEB_SEARCH,
                confidence=0.7,
                requires_web_search=True,
                complexity="low",
                reasoning="Contains web search keywords"
            )
        
        return ClassificationResult(
            primary_intent=IntentType.GENERAL_CHAT,
            confidence=0.6,
            requires_web_search=False,
            complexity="low",
            reasoning="Default classification"
        )
    
    def classify(
        self,
        query: str,
        context: Optional[str] = None,
        use_llm: bool = True
    ) -> ClassificationResult:
        """
        Classify user intent using LLM (Gemini Flash) or keyword fallback.
        
        Args:
            query: The user's query to classify
            context: Optional context about the conversation
            use_llm: Whether to use LLM classification (default True)
        
        Returns:
            ClassificationResult with intent, confidence, and routing hints
        """
        if not use_llm or self.gemini_client is None:
            return self._keyword_classify(query)
        
        try:
            user_message = f"Query: {query}"
            if context:
                user_message = f"Context: {context}\n\nQuery: {query}"
            
            messages = [
                {"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ]
            
            result = self.gemini_client.chat_completion(
                messages=messages,
                model="gemini-2.5-flash",
                temperature=0.1,
                max_tokens=500
            )
            
            content = result.get("content", "")
            
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                parsed = json.loads(json_str)
                
                primary_intent_str = parsed.get("primary_intent", "general_chat")
                try:
                    primary_intent = IntentType(primary_intent_str)
                except ValueError:
                    primary_intent = IntentType.GENERAL_CHAT
                
                secondary_intent = None
                if parsed.get("secondary_intent"):
                    try:
                        secondary_intent = IntentType(parsed["secondary_intent"])
                    except ValueError:
                        pass
                
                return ClassificationResult(
                    primary_intent=primary_intent,
                    confidence=float(parsed.get("confidence", 0.7)),
                    secondary_intent=secondary_intent,
                    requires_web_search=bool(parsed.get("requires_web_search", False)),
                    requires_real_time=bool(parsed.get("requires_real_time", False)),
                    complexity=parsed.get("complexity", "medium"),
                    reasoning=parsed.get("reasoning", "")
                )
            
            return self._keyword_classify(query)
            
        except Exception as e:
            logger.warning(f"LLM classification failed, using keyword fallback: {e}")
            return self._keyword_classify(query)
    
    def should_use_web_search(self, result: ClassificationResult) -> bool:
        """Determine if query should be routed to Perplexity for web search."""
        if result.requires_web_search:
            return True
        if result.requires_real_time:
            return True
        if result.primary_intent in WEB_SEARCH_INTENTS:
            return True
        return False


def get_intent_classifier(
    db_session=None,
    company_id: Optional[int] = None,
    user_id: Optional[int] = None
) -> IntentClassifier:
    """Factory function to create an intent classifier."""
    return IntentClassifier(
        db_session=db_session,
        company_id=company_id,
        user_id=user_id
    )
