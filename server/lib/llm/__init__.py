"""
LLM Module - Unified interface for multiple LLM providers.

Usage:
    from server.lib.llm import get_llm_router, TaskType
    
    router = get_llm_router(db_session=db, company_id=1)
    
    # Auto-select best model for task
    result = router.chat(
        messages=[{"role": "user", "content": "Analyze this financial data..."}],
        task_type=TaskType.FINANCIAL_ANALYSIS
    )
    
    # Or specify model explicitly
    result = router.chat(
        messages=[{"role": "user", "content": "Write code to..."}],
        model="claude-opus-4-5"
    )
    
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
    "AuditedOpenAIClient",
    "get_openai_client",
    "AuditedAnthropicClient",
    "get_audited_anthropic_client",
    "GeminiClient",
]
