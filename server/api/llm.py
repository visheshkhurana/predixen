"""
LLM Router API - Endpoints for multi-LLM chat with intelligent model selection.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from server.core.db import get_db
from server.core.auth import get_current_user
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
