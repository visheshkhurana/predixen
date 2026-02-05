"""
Multi-LLM Router - Classifier-based intelligent model selection.

Supported Providers:
- OpenAI: GPT-4o (via Replit AI Integrations)
- Anthropic: Claude Opus, Sonnet, Haiku (via Replit AI Integrations)
- Google: Gemini Pro, Flash (via Replit AI Integrations)
- Perplexity: Sonar models for web search with citations

Task Routing Logic:
- Web search, real-time data, news → Perplexity Sonar (web-grounded)
- Market research, competitor analysis → Perplexity (with citations)
- Financial analysis, metrics extraction → GPT-4o (best at structured data)
- Complex reasoning, coding → Claude Opus (deep reasoning)
- Strategy, planning → Claude Sonnet (balanced)
- Quick tasks, general chat → Gemini Flash (fastest, cost-effective)
- Vision/image analysis → GPT-4o (best vision model)

Classification:
- Uses Gemini Flash for fast intent classification
- Falls back to keyword-based classification if LLM unavailable
"""
import os
import time
import logging
from enum import Enum
from typing import Optional, Dict, Any, List, Literal, Tuple
from dataclasses import dataclass, field
from datetime import datetime

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
    WEB_SEARCH = "web_search"
    MARKET_RESEARCH = "market_research"
    COMPETITOR_ANALYSIS = "competitor_analysis"
    REAL_TIME_DATA = "real_time_data"
    NEWS_CURRENT_EVENTS = "news_current_events"


class Provider(str, Enum):
    """LLM Providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    PERPLEXITY = "perplexity"


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
    "perplexity-sonar-small": ModelConfig(
        provider=Provider.PERPLEXITY,
        model_id="llama-3.1-sonar-small-128k-online",
        max_tokens=4096,
        description="Fast web search with citations, cost-effective"
    ),
    "perplexity-sonar-large": ModelConfig(
        provider=Provider.PERPLEXITY,
        model_id="llama-3.1-sonar-large-128k-online",
        max_tokens=4096,
        description="Detailed web search with citations"
    ),
    "perplexity-sonar-huge": ModelConfig(
        provider=Provider.PERPLEXITY,
        model_id="llama-3.1-sonar-huge-128k-online",
        max_tokens=4096,
        description="Most capable web search for complex research"
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
    TaskType.WEB_SEARCH: "perplexity-sonar-small",
    TaskType.MARKET_RESEARCH: "perplexity-sonar-large",
    TaskType.COMPETITOR_ANALYSIS: "perplexity-sonar-large",
    TaskType.REAL_TIME_DATA: "perplexity-sonar-small",
    TaskType.NEWS_CURRENT_EVENTS: "perplexity-sonar-small",
}


FALLBACK_CHAIN: Dict[str, List[str]] = {
    "gpt-4o": ["claude-sonnet-4-5", "gemini-2.5-pro"],
    "claude-opus-4-5": ["gpt-4o", "gemini-2.5-pro"],
    "claude-sonnet-4-5": ["gpt-4o", "gemini-2.5-flash"],
    "claude-haiku-4-5": ["gemini-2.5-flash", "gpt-4o"],
    "gemini-2.5-flash": ["claude-haiku-4-5", "gpt-4o"],
    "gemini-2.5-pro": ["claude-sonnet-4-5", "gpt-4o"],
    "gemini-3-flash-preview": ["gemini-2.5-flash", "claude-sonnet-4-5"],
    "gemini-3-pro-preview": ["gemini-2.5-pro", "claude-opus-4-5"],
    "perplexity-sonar-small": ["perplexity-sonar-large", "gpt-4o"],
    "perplexity-sonar-large": ["perplexity-sonar-huge", "gpt-4o"],
    "perplexity-sonar-huge": ["perplexity-sonar-large", "claude-opus-4-5"],
}


@dataclass
class RoutingMetrics:
    """Metrics for a single routing decision."""
    query: str
    classified_intent: str
    selected_model: str
    selected_provider: str
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    classification_latency_ms: int = 0
    total_latency_ms: int = 0
    tokens_used: int = 0
    cost_estimate: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


class LLMRouter:
    """
    Classifier-based LLM Router that intelligently routes requests to optimal models.
    
    Supports:
    - OpenAI: GPT-4o for financial analysis, structured data, vision
    - Anthropic: Claude for complex reasoning, coding, strategy
    - Gemini: Fast classification, general chat, high-volume tasks
    - Perplexity: Web search with citations, real-time data, research
    
    Features:
    - Intent classification using Gemini Flash
    - Automatic fallback chains if primary model fails
    - Cost/latency tracking and audit logging
    - PII redaction across all providers
    """
    
    def __init__(
        self,
        db_session=None,
        company_id: Optional[int] = None,
        user_id: Optional[int] = None,
        pii_mode: Literal["off", "standard", "strict"] = "standard",
        default_provider: Provider = Provider.GEMINI,
        use_classifier: bool = True
    ):
        self.db_session = db_session
        self.company_id = company_id
        self.user_id = user_id
        self.pii_mode = pii_mode
        self.default_provider = default_provider
        self.use_classifier = use_classifier
        
        self._openai_client: Optional[AuditedOpenAIClient] = None
        self._anthropic_client: Optional[AuditedAnthropicClient] = None
        self._gemini_client = None
        self._perplexity_client = None
        self._intent_classifier = None
        
        self._routing_metrics: List[RoutingMetrics] = []
    
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
    
    @property
    def perplexity_client(self):
        """Lazy-load Perplexity client. Returns None if not configured."""
        if self._perplexity_client is None:
            try:
                from server.lib.llm.perplexity_client import PerplexityClient
                self._perplexity_client = PerplexityClient(
                    db_session=self.db_session,
                    company_id=self.company_id,
                    user_id=self.user_id,
                    pii_mode=self.pii_mode
                )
            except (ValueError, ImportError) as e:
                logger.warning(f"Perplexity client not available: {e}")
                return None
        return self._perplexity_client
    
    @property
    def perplexity_available(self) -> bool:
        """Check if Perplexity is available."""
        return self.perplexity_client is not None
    
    @property
    def intent_classifier(self):
        """Lazy-load intent classifier."""
        if self._intent_classifier is None:
            from server.lib.llm.intent_classifier import IntentClassifier
            self._intent_classifier = IntentClassifier(
                db_session=self.db_session,
                company_id=self.company_id,
                user_id=self.user_id
            )
        return self._intent_classifier
    
    def get_model_for_task(self, task_type: TaskType) -> str:
        """Get the recommended model for a task type."""
        return TASK_TO_MODEL.get(task_type, "claude-sonnet-4-5")
    
    def classify_and_route(
        self,
        query: str,
        context: Optional[str] = None
    ) -> Tuple[TaskType, str, Dict[str, Any]]:
        """
        Classify user intent and determine optimal model routing.
        
        Args:
            query: The user's query
            context: Optional context about the conversation
        
        Returns:
            Tuple of (task_type, model_id, classification_info)
        """
        start_time = time.time()
        
        if self.use_classifier:
            from server.lib.llm.intent_classifier import IntentType
            
            result = self.intent_classifier.classify(query, context)
            
            try:
                task_type = TaskType(result.primary_intent.value)
            except ValueError:
                task_type = TaskType.GENERAL_CHAT
            
            model = self.get_model_for_task(task_type)
            
            if result.requires_web_search and self.perplexity_available:
                if task_type not in [TaskType.WEB_SEARCH, TaskType.MARKET_RESEARCH, 
                                     TaskType.COMPETITOR_ANALYSIS, TaskType.REAL_TIME_DATA,
                                     TaskType.NEWS_CURRENT_EVENTS]:
                    task_type = TaskType.WEB_SEARCH
                    model = "perplexity-sonar-small"
            
            classification_latency = int((time.time() - start_time) * 1000)
            
            return task_type, model, {
                "primary_intent": result.primary_intent.value,
                "confidence": result.confidence,
                "requires_web_search": result.requires_web_search,
                "requires_real_time": result.requires_real_time,
                "complexity": result.complexity,
                "reasoning": result.reasoning,
                "classification_latency_ms": classification_latency
            }
        else:
            return TaskType.GENERAL_CHAT, "gemini-2.5-flash", {
                "primary_intent": "general_chat",
                "confidence": 0.5,
                "requires_web_search": False,
                "classification_latency_ms": 0
            }
    
    def web_search(
        self,
        query: str,
        model: str = "sonar-small",
        system_prompt: Optional[str] = None,
        search_recency_filter: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Perform a web search using Perplexity.
        
        Args:
            query: Search query
            model: Perplexity model (sonar-small, sonar-large, sonar-huge)
                   Also accepts prefixed names like perplexity-sonar-small
            system_prompt: Optional system instruction
            search_recency_filter: Recency filter (day, week, month, year)
            **kwargs: Additional arguments
        
        Returns:
            Dict with 'content', 'citations', 'usage', 'model', 'provider'
        """
        normalized_model = model.replace("perplexity-", "")
        
        perplexity = self.perplexity_client
        if perplexity is None:
            logger.warning("Perplexity not available, falling back to GPT-4o")
            fallback_result = self.chat(
                messages=[{"role": "user", "content": query}],
                model="gpt-4o",
                system=system_prompt or "You are a helpful assistant. Answer based on your knowledge.",
                **kwargs
            )
            fallback_result["citations"] = []
            return fallback_result
        
        return perplexity.search(
            query=query,
            model=normalized_model,
            system_prompt=system_prompt,
            search_recency_filter=search_recency_filter,
            **kwargs
        )
    
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
        
        if model_config.provider == Provider.PERPLEXITY:
            perplexity = self.perplexity_client
            if perplexity is not None:
                user_content = messages[-1].get("content", "") if messages else ""
                result = perplexity.search(
                    query=user_content,
                    model=model.replace("perplexity-", ""),
                    system_prompt=system,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                return result
            else:
                logger.info("Perplexity not available, falling back to GPT-4o")
                model = "gpt-4o"
                model_config = MODELS.get(model) or MODELS["gemini-2.5-flash"]
        
        if model_config.provider == Provider.OPENAI:
            openai = self.openai_client
            if openai is not None:
                if system:
                    messages = [{"role": "system", "content": system}] + messages
                
                result = openai.chat_completion(
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
                logger.info("OpenAI not available, falling back to Gemini")
                model = "gemini-2.5-flash"
                model_config = MODELS.get(model) or MODELS["claude-sonnet-4-5"]
        
        if model_config.provider == Provider.GEMINI:
            gemini = self.gemini_client
            if gemini is not None:
                if system:
                    messages = [{"role": "system", "content": system}] + messages
                
                result = gemini.chat_completion(
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
                logger.info("Gemini not available, falling back to Claude")
                model = "claude-sonnet-4-5"
                model_config = MODELS.get(model) or list(MODELS.values())[0]
        
        anthropic = self.anthropic_client
        if anthropic is None:
            raise ValueError(
                "No LLM provider available. Configure at least one of: "
                "AI_INTEGRATIONS_OPENAI_API_KEY, AI_INTEGRATIONS_ANTHROPIC_API_KEY, "
                "AI_INTEGRATIONS_GEMINI_API_KEY"
            )
        
        result = anthropic.chat_completion(
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
        openai = self.openai_client
        if openai is None:
            raise ValueError("Vision requires OpenAI. Configure AI_INTEGRATIONS_OPENAI_API_KEY.")
        
        result = openai.vision_completion(
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
    
    def smart_chat(
        self,
        query: str,
        context: Optional[str] = None,
        system: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Classifier-based intelligent chat that automatically routes to the best model.
        
        This is the primary entry point for intelligent routing. It:
        1. Classifies the user's intent using Gemini Flash
        2. Routes to the optimal model (including Perplexity for web search)
        3. Returns the response with routing metadata
        
        Args:
            query: The user's query
            context: Optional context about the conversation
            system: Optional system prompt
            **kwargs: Additional arguments
        
        Returns:
            Dict with 'content', 'citations' (if web search), 'usage', 'model', 
            'provider', 'task_type', 'classification'
        """
        start_time = time.time()
        
        task_type, model, classification = self.classify_and_route(query, context)
        
        messages = [{"role": "user", "content": query}]
        
        result = self.chat(
            messages=messages,
            task_type=task_type,
            model=model,
            system=system,
            **kwargs
        )
        
        total_latency = int((time.time() - start_time) * 1000)
        
        result["task_type"] = task_type.value
        result["classification"] = classification
        result["total_latency_ms"] = total_latency
        
        metrics = RoutingMetrics(
            query=query[:200],
            classified_intent=task_type.value,
            selected_model=model,
            selected_provider=result.get("provider", "unknown"),
            classification_latency_ms=classification.get("classification_latency_ms", 0),
            total_latency_ms=total_latency,
            tokens_used=result.get("usage", {}).get("total_tokens", 0)
        )
        self._routing_metrics.append(metrics)
        
        if len(self._routing_metrics) > 1000:
            self._routing_metrics = self._routing_metrics[-500:]
        
        return result
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """Get statistics about routing decisions."""
        if not self._routing_metrics:
            return {"total_requests": 0}
        
        total = len(self._routing_metrics)
        by_provider = {}
        by_intent = {}
        total_latency = 0
        
        for m in self._routing_metrics:
            by_provider[m.selected_provider] = by_provider.get(m.selected_provider, 0) + 1
            by_intent[m.classified_intent] = by_intent.get(m.classified_intent, 0) + 1
            total_latency += m.total_latency_ms
        
        return {
            "total_requests": total,
            "by_provider": by_provider,
            "by_intent": by_intent,
            "avg_latency_ms": total_latency // total if total > 0 else 0
        }


def get_llm_router(
    db_session=None,
    company_id: Optional[int] = None,
    user_id: Optional[int] = None,
    pii_mode: Literal["off", "standard", "strict"] = "standard",
    use_classifier: bool = True
) -> LLMRouter:
    """Factory function to create an LLM router."""
    return LLMRouter(
        db_session=db_session,
        company_id=company_id,
        user_id=user_id,
        pii_mode=pii_mode,
        use_classifier=use_classifier
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
    TaskType.WEB_SEARCH: "Web search for current information and facts",
    TaskType.MARKET_RESEARCH: "Industry trends, market sizing, research",
    TaskType.COMPETITOR_ANALYSIS: "Competitor analysis, competitive landscape",
    TaskType.REAL_TIME_DATA: "Current prices, live data, real-time statistics",
    TaskType.NEWS_CURRENT_EVENTS: "Recent news, announcements, current events",
}


WEB_SEARCH_TASKS = {
    TaskType.WEB_SEARCH,
    TaskType.MARKET_RESEARCH,
    TaskType.COMPETITOR_ANALYSIS,
    TaskType.REAL_TIME_DATA,
    TaskType.NEWS_CURRENT_EVENTS,
}
