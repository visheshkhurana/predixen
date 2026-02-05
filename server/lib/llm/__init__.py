"""
LLM Module - Unified interface for multiple LLM providers with intelligent routing.

Features:
- Classifier-based routing to optimal LLMs (OpenAI, Anthropic, Gemini, Perplexity)
- Perplexity integration for web search with citations
- PII redaction and audit logging
- Cost/latency tracking

Usage:
    from server.lib.llm import get_llm_router, TaskType
    
    router = get_llm_router(db_session=db, company_id=1)
    
    # Intelligent routing with automatic intent classification
    result = router.smart_chat("What's the current market cap of Apple?")
    # -> Routes to Perplexity for real-time web data
    
    # Auto-select best model for specific task
    result = router.chat(
        messages=[{"role": "user", "content": "Analyze this financial data..."}],
        task_type=TaskType.FINANCIAL_ANALYSIS
    )
    # -> Routes to GPT-4o for financial analysis
    
    # Web search with citations
    result = router.web_search("Latest SaaS funding trends in 2025")
    # -> Returns content with authoritative citations
    
    # Quick single-turn chat
    response = router.quick_chat("Summarize this text...", TaskType.SIMPLE_TASK)
"""

from server.lib.llm.llm_router import (
    LLMRouter,
    get_llm_router,
    TaskType,
    Provider,
    ModelConfig,
    MODELS,
    AVAILABLE_MODELS,
    TASK_TO_MODEL,
    TASK_DESCRIPTIONS,
    WEB_SEARCH_TASKS,
    RoutingMetrics,
)

from server.lib.llm.openai_client import (
    AuditedOpenAIClient,
    get_audited_client as get_openai_client,
)

from server.lib.llm.anthropic_client import (
    AuditedAnthropicClient,
    get_audited_anthropic_client,
)

from server.lib.llm.gemini_client import GeminiClient

try:
    from server.lib.llm.perplexity_client import PerplexityClient
except ImportError:
    PerplexityClient = None

try:
    from server.lib.llm.intent_classifier import IntentClassifier, IntentType, ClassificationResult
except ImportError:
    IntentClassifier = None
    IntentType = None
    ClassificationResult = None

__all__ = [
    "LLMRouter",
    "get_llm_router",
    "TaskType",
    "Provider",
    "ModelConfig",
    "MODELS",
    "AVAILABLE_MODELS",
    "TASK_TO_MODEL",
    "TASK_DESCRIPTIONS",
    "WEB_SEARCH_TASKS",
    "RoutingMetrics",
    "AuditedOpenAIClient",
    "get_openai_client",
    "AuditedAnthropicClient",
    "get_audited_anthropic_client",
    "GeminiClient",
    "PerplexityClient",
    "IntentClassifier",
    "IntentType",
    "ClassificationResult",
]
