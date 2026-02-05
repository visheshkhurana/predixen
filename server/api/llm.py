"""
LLM Router API - Endpoints for multi-LLM chat with intelligent model selection.

Features:
- Classifier-based intelligent routing to optimal LLMs
- Perplexity integration for web search with citations
- Cost/latency tracking and routing statistics
- Multi-provider support: OpenAI, Anthropic, Gemini, Perplexity
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from server.core.db import get_db
from server.core.security import get_current_user
from server.models.user import User
from server.lib.llm import get_llm_router, TaskType, MODELS, TASK_TO_MODEL, TASK_DESCRIPTIONS

router = APIRouter(prefix="/llm", tags=["llm"])


class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., description="Chat messages")
    task_type: Optional[str] = Field(None, description="Task type for auto model selection")
    model: Optional[str] = Field(None, description="Explicit model override")
    system: Optional[str] = Field(None, description="System prompt")
    temperature: float = Field(0.7, ge=0, le=2, description="Sampling temperature")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens in response")


class ChatResponse(BaseModel):
    content: str
    model: str
    provider: str
    usage: Dict[str, int]
    task_type_used: Optional[str] = None
    pii_findings: List[Dict[str, Any]] = []


@router.get("/models")
async def list_models():
    """List all available LLM models and their capabilities."""
    models_info = {}
    for model_id, config in MODELS.items():
        models_info[model_id] = {
            "provider": config.provider.value,
            "max_tokens": config.max_tokens,
            "description": config.description,
        }
    return {
        "models": models_info,
        "default_model": "claude-sonnet-4-5"
    }


@router.get("/task-types")
async def list_task_types():
    """List all task types and their recommended models."""
    task_types = {}
    for task_type in TaskType:
        task_types[task_type.value] = {
            "description": TASK_DESCRIPTIONS.get(task_type, ""),
            "recommended_model": TASK_TO_MODEL.get(task_type, "claude-sonnet-4-5")
        }
    return {"task_types": task_types}


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Send a chat message with intelligent model routing.
    
    If task_type is provided, the best model for that task is automatically selected.
    If model is provided, it overrides the task-based selection.
    If neither is provided, claude-sonnet-4-5 is used as default.
    """
    try:
        llm_router = get_llm_router(
            db_session=db,
            user_id=current_user.id,
            pii_mode="standard"
        )
        
        task_type_enum = None
        if request.task_type:
            try:
                task_type_enum = TaskType(request.task_type)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid task_type. Valid options: {[t.value for t in TaskType]}"
                )
        
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        
        result = llm_router.chat(
            messages=messages,
            task_type=task_type_enum,
            model=request.model,
            system=request.system,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        return ChatResponse(
            content=result.get("content", ""),
            model=result.get("model", ""),
            provider=result.get("provider", ""),
            usage=result.get("usage", {}),
            task_type_used=request.task_type,
            pii_findings=result.get("pii_findings", [])
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick-chat")
async def quick_chat(
    prompt: str,
    task_type: str = "simple_task",
    system: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Quick single-turn chat with automatic model selection."""
    try:
        llm_router = get_llm_router(
            db_session=db,
            user_id=current_user.id,
            pii_mode="standard"
        )
        
        try:
            task_type_enum = TaskType(task_type)
        except ValueError:
            task_type_enum = TaskType.SIMPLE_TASK
        
        response = llm_router.quick_chat(
            prompt=prompt,
            task_type=task_type_enum,
            system=system
        )
        
        return {
            "response": response,
            "task_type": task_type_enum.value,
            "model": TASK_TO_MODEL.get(task_type_enum, "claude-sonnet-4-5")
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class SmartChatRequest(BaseModel):
    query: str = Field(..., description="User query for intelligent routing")
    context: Optional[str] = Field(None, description="Optional conversation context")
    system: Optional[str] = Field(None, description="Optional system prompt")
    temperature: float = Field(0.7, ge=0, le=2, description="Sampling temperature")


class SmartChatResponse(BaseModel):
    content: str
    model: str
    provider: str
    task_type: str
    usage: Dict[str, int]
    classification: Dict[str, Any]
    citations: Optional[List[Dict[str, Any]]] = None
    total_latency_ms: int


@router.post("/smart-chat", response_model=SmartChatResponse)
async def smart_chat(
    request: SmartChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Intelligent chat with automatic intent classification and model routing.
    
    Uses Gemini Flash to classify user intent, then routes to the optimal model:
    - OpenAI GPT-4o: Financial analysis, structured data, vision
    - Anthropic Claude: Complex reasoning, coding, strategy
    - Gemini: General chat, quick tasks, high-volume
    - Perplexity: Web search, market research, real-time data
    """
    try:
        llm_router = get_llm_router(
            db_session=db,
            user_id=current_user.id,
            pii_mode="standard",
            use_classifier=True
        )
        
        result = llm_router.smart_chat(
            query=request.query,
            context=request.context,
            system=request.system,
            temperature=request.temperature
        )
        
        return SmartChatResponse(
            content=result.get("content", ""),
            model=result.get("model", ""),
            provider=result.get("provider", ""),
            task_type=result.get("task_type", "general_chat"),
            usage=result.get("usage", {}),
            classification=result.get("classification", {}),
            citations=result.get("citations"),
            total_latency_ms=result.get("total_latency_ms", 0)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class WebSearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    model: str = Field("sonar-small", description="Perplexity model: sonar-small, sonar-large, sonar-huge")
    system_prompt: Optional[str] = Field(None, description="Optional system instruction")
    search_recency_filter: Optional[str] = Field(None, description="Recency filter: day, week, month, year")


class WebSearchResponse(BaseModel):
    content: str
    citations: List[Dict[str, Any]]
    model: str
    provider: str
    usage: Dict[str, int]


@router.post("/web-search", response_model=WebSearchResponse)
async def web_search(
    request: WebSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Perform a web search using Perplexity for real-time information.
    
    Returns structured content with inline citations from authoritative sources.
    Ideal for:
    - Market research and competitive analysis
    - Current pricing, statistics, and data
    - Recent news and industry developments
    """
    try:
        llm_router = get_llm_router(
            db_session=db,
            user_id=current_user.id,
            pii_mode="standard"
        )
        
        if not llm_router.perplexity_available:
            raise HTTPException(
                status_code=503,
                detail="Web search unavailable. Perplexity API key not configured."
            )
        
        result = llm_router.web_search(
            query=request.query,
            model=request.model,
            system_prompt=request.system_prompt,
            search_recency_filter=request.search_recency_filter
        )
        
        return WebSearchResponse(
            content=result.get("content", ""),
            citations=result.get("citations", []),
            model=result.get("model", ""),
            provider=result.get("provider", "perplexity"),
            usage=result.get("usage", {})
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/routing-stats")
async def get_routing_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get routing statistics for the current session.
    
    Returns aggregated metrics about model selection and performance.
    Note: Statistics are per-router instance, useful for debugging and optimization.
    """
    try:
        llm_router = get_llm_router(
            db_session=db,
            user_id=current_user.id,
            pii_mode="standard"
        )
        
        stats = llm_router.get_routing_stats()
        
        return {
            "stats": stats,
            "available_providers": {
                "openai": llm_router.openai_available,
                "anthropic": llm_router.anthropic_available,
                "gemini": llm_router.gemini_available,
                "perplexity": llm_router.perplexity_available
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
