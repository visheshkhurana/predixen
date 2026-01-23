"""
Conversation API endpoints for enhanced copilot memory and shortcuts.

Provides endpoints for:
- Listing past conversations
- Loading conversation details with messages
- Conversation shortcuts (revisit last session, use scenario assumptions)
- Recommendation feedback tracking
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from server.core.db import get_db
from server.core.security import get_current_user
from server.models.user import User
from server.models.company import Company
from server.models.conversation import Conversation, ConversationMessage, ConversationRecommendation
from server.models.scenario import Scenario

router = APIRouter(prefix="/companies", tags=["conversations"])


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    intent_type: Optional[str] = None
    scenario_id: Optional[int] = None
    simulation_id: Optional[int] = None
    chart_data: Optional[dict] = None
    message_metadata: Optional[dict] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ConversationSummaryResponse(BaseModel):
    id: int
    title: Optional[str] = None
    last_scenario_id: Optional[int] = None
    is_active: bool
    message_count: int
    created_at: datetime
    updated_at: datetime
    last_message_preview: Optional[str] = None
    
    class Config:
        from_attributes = True


class ConversationDetailResponse(BaseModel):
    id: int
    title: Optional[str] = None
    last_scenario_id: Optional[int] = None
    context_metadata: Optional[dict] = None
    is_active: bool
    messages: List[MessageResponse]
    recommendations: List[dict] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CreateConversationRequest(BaseModel):
    title: Optional[str] = None


class RecommendationFeedbackRequest(BaseModel):
    feedback: str


class UseShortcutRequest(BaseModel):
    shortcut_type: str
    conversation_id: Optional[int] = None
    scenario_name: Optional[str] = None


class ShortcutResponse(BaseModel):
    success: bool
    context_restored: bool
    message: str
    restored_params: Optional[dict] = None
    restored_scenario_id: Optional[int] = None


@router.get("/{company_id}/conversations", response_model=List[ConversationSummaryResponse])
async def list_conversations(
    company_id: int,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all conversations for a company with pagination."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    conversations = db.query(Conversation).filter(
        Conversation.company_id == company_id,
        Conversation.user_id == current_user.id
    ).order_by(desc(Conversation.updated_at)).offset(offset).limit(limit).all()
    
    results = []
    for conv in conversations:
        message_count = db.query(ConversationMessage).filter(
            ConversationMessage.conversation_id == conv.id
        ).count()
        
        last_message = db.query(ConversationMessage).filter(
            ConversationMessage.conversation_id == conv.id
        ).order_by(desc(ConversationMessage.created_at)).first()
        
        preview = None
        if last_message:
            preview = last_message.content[:100] + "..." if len(last_message.content) > 100 else last_message.content
        
        results.append(ConversationSummaryResponse(
            id=conv.id,
            title=conv.title,
            last_scenario_id=conv.last_scenario_id,
            is_active=conv.is_active,
            message_count=message_count,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            last_message_preview=preview
        ))
    
    return results


@router.get("/{company_id}/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    company_id: int,
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed conversation with all messages and recommendations."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.company_id == company_id,
        Conversation.user_id == current_user.id
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = db.query(ConversationMessage).filter(
        ConversationMessage.conversation_id == conversation_id
    ).order_by(ConversationMessage.created_at).all()
    
    recommendations = db.query(ConversationRecommendation).filter(
        ConversationRecommendation.conversation_id == conversation_id
    ).all()
    
    return ConversationDetailResponse(
        id=conversation.id,
        title=conversation.title,
        last_scenario_id=conversation.last_scenario_id,
        context_metadata=conversation.context_metadata,
        is_active=conversation.is_active,
        messages=[MessageResponse.model_validate(m) for m in messages],
        recommendations=[
            {
                "id": r.id,
                "type": r.recommendation_type,
                "text": r.recommendation_text,
                "priority": r.priority,
                "feedback": r.feedback,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in recommendations
        ],
        created_at=conversation.created_at,
        updated_at=conversation.updated_at
    )


@router.post("/{company_id}/conversations", response_model=ConversationDetailResponse)
async def create_conversation(
    company_id: int,
    request: CreateConversationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new conversation for a company."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    conversation = Conversation(
        company_id=company_id,
        user_id=current_user.id,
        title=request.title,
        is_active=True
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    
    return ConversationDetailResponse(
        id=conversation.id,
        title=conversation.title,
        last_scenario_id=conversation.last_scenario_id,
        context_metadata=conversation.context_metadata,
        is_active=conversation.is_active,
        messages=[],
        recommendations=[],
        created_at=conversation.created_at,
        updated_at=conversation.updated_at
    )


@router.post("/{company_id}/conversations/shortcut", response_model=ShortcutResponse)
async def use_conversation_shortcut(
    company_id: int,
    request: UseShortcutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Use a conversation shortcut to restore context.
    
    Shortcut types:
    - revisit_last_session: Restore the most recent conversation context
    - use_scenario_assumptions: Load assumptions from a named scenario
    """
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    if request.shortcut_type == "revisit_last_session":
        last_conversation = db.query(Conversation).filter(
            Conversation.company_id == company_id,
            Conversation.user_id == current_user.id
        ).order_by(desc(Conversation.updated_at)).first()
        
        if not last_conversation:
            return ShortcutResponse(
                success=False,
                context_restored=False,
                message="No previous conversation found"
            )
        
        restored_params = None
        if last_conversation.context_metadata:
            restored_params = last_conversation.context_metadata.get("last_simulation_params")
        
        return ShortcutResponse(
            success=True,
            context_restored=True,
            message=f"Restored context from conversation: {last_conversation.title or 'Untitled'}",
            restored_params=restored_params,
            restored_scenario_id=last_conversation.last_scenario_id
        )
    
    elif request.shortcut_type == "use_scenario_assumptions":
        if not request.scenario_name:
            raise HTTPException(status_code=400, detail="scenario_name required for this shortcut type")
        
        scenario = db.query(Scenario).filter(
            Scenario.company_id == company_id,
            Scenario.name.ilike(f"%{request.scenario_name}%")
        ).first()
        
        if not scenario:
            return ShortcutResponse(
                success=False,
                context_restored=False,
                message=f"No scenario found matching '{request.scenario_name}'"
            )
        
        restored_params = scenario.inputs if hasattr(scenario, 'inputs') else None
        
        return ShortcutResponse(
            success=True,
            context_restored=True,
            message=f"Loaded assumptions from scenario: {scenario.name}",
            restored_params=restored_params,
            restored_scenario_id=scenario.id
        )
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown shortcut type: {request.shortcut_type}")


@router.get("/{company_id}/conversations/active")
async def get_active_conversation(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get or create the active conversation for current chat session."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    active_conversation = db.query(Conversation).filter(
        Conversation.company_id == company_id,
        Conversation.user_id == current_user.id,
        Conversation.is_active == True
    ).order_by(desc(Conversation.updated_at)).first()
    
    if not active_conversation:
        active_conversation = Conversation(
            company_id=company_id,
            user_id=current_user.id,
            title="New Conversation",
            is_active=True
        )
        db.add(active_conversation)
        db.commit()
        db.refresh(active_conversation)
    
    return {
        "id": active_conversation.id,
        "title": active_conversation.title,
        "created_at": active_conversation.created_at.isoformat(),
        "updated_at": active_conversation.updated_at.isoformat()
    }


@router.post("/{company_id}/conversations/{conversation_id}/recommendations/{recommendation_id}/feedback")
async def submit_recommendation_feedback(
    company_id: int,
    conversation_id: int,
    recommendation_id: int,
    request: RecommendationFeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit feedback for a recommendation (accepted, ignored, later)."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    recommendation = db.query(ConversationRecommendation).filter(
        ConversationRecommendation.id == recommendation_id,
        ConversationRecommendation.conversation_id == conversation_id
    ).first()
    
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    valid_feedback = ["accepted", "ignored", "later", "helpful", "not_helpful"]
    if request.feedback not in valid_feedback:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid feedback. Must be one of: {', '.join(valid_feedback)}"
        )
    
    recommendation.feedback = request.feedback
    recommendation.feedback_at = datetime.utcnow()
    db.commit()
    
    return {
        "success": True,
        "recommendation_id": recommendation_id,
        "feedback": request.feedback,
        "feedback_at": recommendation.feedback_at.isoformat()
    }


@router.get("/{company_id}/conversations/{conversation_id}/recommendations")
async def get_conversation_recommendations(
    company_id: int,
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all recommendations for a conversation with feedback status."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.company_id == company_id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    recommendations = db.query(ConversationRecommendation).filter(
        ConversationRecommendation.conversation_id == conversation_id
    ).order_by(desc(ConversationRecommendation.priority)).all()
    
    return [
        {
            "id": rec.id,
            "type": rec.recommendation_type,
            "text": rec.recommendation_text,
            "priority": rec.priority,
            "feedback": rec.feedback,
            "feedback_at": rec.feedback_at.isoformat() if rec.feedback_at else None,
            "created_at": rec.created_at.isoformat()
        }
        for rec in recommendations
    ]
