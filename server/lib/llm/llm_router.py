"""
Multi-LLM Router - Automatically selects the best model for each task type.

Supported Providers:
- OpenAI: GPT-4o (via Replit AI Integrations)
- Anthropic: Claude Opus, Sonnet, Haiku (via Replit AI Integrations)
- Google: Gemini Pro, Flash (via Replit AI Integrations)

Task Routing Logic:
- Financial analysis, metrics extraction → GPT-4o (best at structured data)
- Complex reasoning, coding → Claude Opus (deep reasoning)
- Strategy, planning, general chat → Claude Sonnet (balanced)
- Quick extraction, simple tasks → Gemini Flash (fastest)
- High-volume processing → Gemini Flash (cost-effective)
- Vision/image analysis → GPT-4o (best vision model)
"""
import os
import logging
from enum import Enum
from typing import Optional, Dict, Any, List, Literal
from dataclasses import dataclass

from server.lib.llm.openai_client import AuditedOpenAIClient, get_audited_client as get_openai_client
from server.lib.llm.anthropic_client import AuditedAnthropicClient, get_audited_anthropic_client

logger = logging.getLogger(__name__)


class TaskType(str, Enum):
    """Task types for intelligent model routing."""
    FINANCIAL_ANALYSIS = "financial_analysis"
    METRICS_EXTRACTION = "metrics_extraction"
    COMPLEX_REASONING = "complex_reasoning"
    CODING = "coding"
    STRATEGY = "strategy"
    PLANNING = "planning"
    GENERAL_CHAT = "general_chat"
    QUICK_EXTRACTION = "quick_extraction"
    SIMPLE_TASK = "simple_task"
    VISION = "vision"
    DATA_PROCESSING = "data_processing"


class Provider(str, Enum):
    """LLM Providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"


@dataclass
class ModelConfig:
    """Configuration for a model."""
    provider: Provider
    model_id: str
    max_tokens: int = 8192
    temperature: float = 0.7
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    description: str = ""


MODELS = {
    "gpt-4o": ModelConfig(
        provider=Provider.OPENAI,
        model_id="gpt-4o",
        max_tokens=16384,
        description="Best for structured data, financial analysis, vision tasks"
    ),
    "claude-opus-4-5": ModelConfig(
        provider=Provider.ANTHROPIC,
        model_id="claude-opus-4-5",
        max_tokens=8192,
        description="Most capable, best for complex reasoning and coding"
    ),
    "claude-sonnet-4-5": ModelConfig(
        provider=Provider.ANTHROPIC,
        model_id="claude-sonnet-4-5",
        max_tokens=8192,
        description="Balanced performance, recommended for most use cases"
    ),
    "claude-haiku-4-5": ModelConfig(
        provider=Provider.ANTHROPIC,
        model_id="claude-haiku-4-5",
        max_tokens=8192,
        description="Fastest Anthropic model, ideal for simple tasks"
    ),
    "gemini-2.5-flash": ModelConfig(
        provider=Provider.GEMINI,
        model_id="gemini-2.5-flash",
        max_tokens=8192,
        description="Fast and cost-effective, great for high-volume tasks"
    ),
    "gemini-2.5-pro": ModelConfig(
        provider=Provider.GEMINI,
        model_id="gemini-2.5-pro",
        max_tokens=8192,
        description="Advanced reasoning and coding capabilities"
    ),
    "gemini-3-flash-preview": ModelConfig(
        provider=Provider.GEMINI,
        model_id="gemini-3-flash-preview",
        max_tokens=8192,
        description="Latest hybrid reasoning model for daily use"
    ),
    "gemini-3-pro-preview": ModelConfig(
        provider=Provider.GEMINI,
        model_id="gemini-3-pro-preview",
        max_tokens=8192,
        description="Most powerful Gemini for agentic workflows"
    ),
}


TASK_TO_MODEL: Dict[TaskType, str] = {
    TaskType.FINANCIAL_ANALYSIS: "gpt-4o",
    TaskType.METRICS_EXTRACTION: "gpt-4o",
    TaskType.COMPLEX_REASONING: "claude-opus-4-5",
    TaskType.CODING: "claude-opus-4-5",
    TaskType.STRATEGY: "claude-sonnet-4-5",
    TaskType.PLANNING: "claude-sonnet-4-5",
    TaskType.GENERAL_CHAT: "gemini-2.5-flash",
    TaskType.QUICK_EXTRACTION: "gemini-2.5-flash",
    TaskType.SIMPLE_TASK: "gemini-2.5-flash",
    TaskType.VISION: "gpt-4o",
    TaskType.DATA_PROCESSING: "gemini-2.5-pro",
}


class LLMRouter:
    """
    Unified LLM Router that automatically selects the best model for each task.
    Supports OpenAI, Anthropic, and Gemini with PII redaction and audit logging.
    """
    
    def __init__(
        self,
        db_session=None,
        company_id: Optional[int] = None,
        user_id: Optional[int] = None,
        pii_mode: Literal["off", "standard", "strict"] = "standard",
        default_provider: Provider = Provider.GEMINI
    ):
        self.db_session = db_session
        self.company_id = company_id
        self.user_id = user_id
        self.pii_mode = pii_mode
        self.default_provider = default_provider
        
        self._openai_client: Optional[AuditedOpenAIClient] = None
        self._anthropic_client: Optional[AuditedAnthropicClient] = None
        self._gemini_client = None
    
    @property
    def openai_client(self) -> Optional[AuditedOpenAIClient]:
        """Lazy-load OpenAI client. Returns None if not configured."""
        if self._openai_client is None:
            try:
                self._openai_client = get_openai_client(
                    db_session=self.db_session,
                    company_id=self.company_id,
                    user_id=self.user_id,
                    pii_mode=self.pii_mode
                )
            except ValueError:
                return None
        return self._openai_client
    
    @property
    def openai_available(self) -> bool:
        """Check if OpenAI is available."""
        return self.openai_client is not None
    
    @property
    def anthropic_client(self) -> AuditedAnthropicClient:
        """Lazy-load Anthropic client."""
        if self._anthropic_client is None:
            self._anthropic_client = get_audited_anthropic_client(
                db_session=self.db_session,
                company_id=self.company_id,
                user_id=self.user_id,
                pii_mode=self.pii_mode
            )
        return self._anthropic_client
    
    @property
    def gemini_client(self):
        """Lazy-load Gemini client. Returns None if not configured."""
        if self._gemini_client is None:
            try:
                from server.lib.llm.gemini_client import GeminiClient
                self._gemini_client = GeminiClient(
                    db_session=self.db_session,
                    company_id=self.company_id,
                    user_id=self.user_id,
                    pii_mode=self.pii_mode
                )
            except (ValueError, ImportError) as e:
                logger.warning(f"Gemini client not available: {e}")
                return None
        return self._gemini_client
    
    @property
    def gemini_available(self) -> bool:
        """Check if Gemini is available."""
        return self.gemini_client is not None
    
    def get_model_for_task(self, task_type: TaskType) -> str:
        """Get the recommended model for a task type."""
        return TASK_TO_MODEL.get(task_type, "claude-sonnet-4-5")
    
    def get_model_info(self, model_id: str) -> Optional[ModelConfig]:
        """Get information about a model."""
        return MODELS.get(model_id)
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        task_type: Optional[TaskType] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        system: Optional[str] = None,
        response_format: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make a chat completion request, automatically routing to the best model.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            task_type: Optional task type for automatic model selection
            model: Optional explicit model override
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            system: System prompt (for Anthropic)
            response_format: Response format (for OpenAI JSON mode)
            **kwargs: Additional provider-specific arguments
        
        Returns:
            Dict with 'content', 'usage', 'model', 'provider', 'audit_log_id', 'pii_findings'
        """
        if model is None:
            if task_type:
                model = self.get_model_for_task(task_type)
            else:
                model = "gemini-2.5-flash"
        
        model_config = MODELS.get(model)
        if model_config is None:
            model_config = MODELS["gemini-2.5-flash"]
            model = "gemini-2.5-flash"
        
        if max_tokens is None:
            max_tokens = model_config.max_tokens
        
        if response_format and model_config.provider != Provider.OPENAI:
            if self.openai_available:
                model = "gpt-4o"
                model_config = MODELS[model]
        
        if model_config.provider == Provider.OPENAI:
            if self.openai_available:
                if system:
                    messages = [{"role": "system", "content": system}] + messages
                
                result = self.openai_client.chat_completion(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                    **kwargs
                )
                result["provider"] = "openai"
                return result
            else:
                model = "gemini-2.5-flash"
                model_config = MODELS[model]
        
        if model_config.provider == Provider.GEMINI:
            if self.gemini_available:
                if system:
                    messages = [{"role": "system", "content": system}] + messages
                
                result = self.gemini_client.chat_completion(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    company_id=self.company_id,
                    user_id=self.user_id,
                    **kwargs
                )
                return result
            else:
                model = "claude-sonnet-4-5"
                model_config = MODELS[model]
        
        result = self.anthropic_client.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens or model_config.max_tokens,
            system=system,
            **kwargs
        )
        return result
    
    def vision(
        self,
        messages: List[Dict[str, Any]],
        model: str = "gpt-4o",
        max_tokens: int = 4096,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make a vision completion request (currently OpenAI only).
        
        Args:
            messages: List of message dicts with multimodal content
            model: Model to use (default: gpt-4o)
            max_tokens: Maximum tokens in response
            **kwargs: Additional arguments
        
        Returns:
            Dict with 'content', 'usage', 'model', 'provider', 'audit_log_id', 'pii_findings'
        """
        if not self.openai_available:
            raise ValueError("Vision requires OpenAI. Configure AI_INTEGRATIONS_OPENAI_API_KEY.")
        
        result = self.openai_client.vision_completion(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            **kwargs
        )
        result["provider"] = "openai"
        return result
    
    def quick_chat(
        self,
        prompt: str,
        task_type: TaskType = TaskType.SIMPLE_TASK,
        system: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Convenience method for quick single-turn chat.
        
        Args:
            prompt: User prompt
            task_type: Task type for model selection
            system: Optional system prompt
            **kwargs: Additional arguments
        
        Returns:
            Response content as string
        """
        messages = [{"role": "user", "content": prompt}]
        result = self.chat(
            messages=messages,
            task_type=task_type,
            system=system,
            **kwargs
        )
        return result.get("content", "")


def get_llm_router(
    db_session=None,
    company_id: Optional[int] = None,
    user_id: Optional[int] = None,
    pii_mode: Literal["off", "standard", "strict"] = "standard"
) -> LLMRouter:
    """Factory function to create an LLM router."""
    return LLMRouter(
        db_session=db_session,
        company_id=company_id,
        user_id=user_id,
        pii_mode=pii_mode
    )


AVAILABLE_MODELS = list(MODELS.keys())

TASK_DESCRIPTIONS = {
    TaskType.FINANCIAL_ANALYSIS: "Analysis of financial data, metrics, KPIs",
    TaskType.METRICS_EXTRACTION: "Extracting structured data from documents",
    TaskType.COMPLEX_REASONING: "Deep analysis requiring multi-step reasoning",
    TaskType.CODING: "Code generation, debugging, refactoring",
    TaskType.STRATEGY: "Business strategy, market analysis, planning",
    TaskType.PLANNING: "Project planning, roadmaps, timelines",
    TaskType.GENERAL_CHAT: "General conversation, Q&A, explanations",
    TaskType.QUICK_EXTRACTION: "Simple data extraction, parsing",
    TaskType.SIMPLE_TASK: "Basic tasks, formatting, summaries",
    TaskType.VISION: "Image analysis, document OCR",
    TaskType.DATA_PROCESSING: "Data transformation, aggregation",
}
