"""
Domain Router: /api/ai
Aggregates AI Copilot, governance, and agent endpoints.
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
from server.core.db import get_db
from server.core.security import get_current_user
from server.core.company_access import get_user_company

router = APIRouter(prefix="/ai", tags=["AI Domain"])


class AIFeedbackRequest(BaseModel):
    company_id: int
    conversation_id: Optional[str] = None
    message_index: Optional[int] = None
    message_id: Optional[str] = None
    rating: str
    feedback_text: Optional[str] = None
    response_type: Optional[str] = None
    tags: Optional[List[str]] = None
    context_snapshot: Optional[dict] = None


@router.get("/agents")
def list_agents():
    from server.copilot.ai_governance import get_all_permissions
    return {"agents": get_all_permissions()}


@router.get("/agents/stats")
def agent_stats(company_id: int = Query(...), days: int = 7, db: Session = Depends(get_db), user=Depends(get_current_user)):
    get_user_company(db, company_id, user)
    from server.copilot.ai_governance import get_agent_stats
    return get_agent_stats(company_id=company_id, days=days)


@router.get("/governance/budgets")
def get_budgets(company_id: int = Query(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    get_user_company(db, company_id, user)
    from sqlalchemy import text
    rows = db.execute(
        text("SELECT agent_name, monthly_budget, usage FROM ai_agent_budgets WHERE company_id = :cid"),
        {"cid": company_id},
    ).fetchall()
    return [{"agent": r[0], "budget": r[1], "usage": r[2]} for r in rows]


@router.get("/flags")
def get_feature_flags(company_id: int = Query(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    get_user_company(db, company_id, user)
    from server.core.feature_flags import get_company_flags
    return {"flags": get_company_flags(company_id)}


@router.post("/feedback")
def submit_ai_feedback(req: AIFeedbackRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    get_user_company(db, req.company_id, user)
    if req.rating not in ("helpful", "not_helpful"):
        raise HTTPException(status_code=400, detail="Rating must be 'helpful' or 'not_helpful'")

    from server.models.copilot_feedback import CopilotFeedback
    feedback = CopilotFeedback(
        company_id=req.company_id,
        user_id=user.id,
        conversation_id=req.conversation_id,
        message_index=req.message_index,
        message_id=req.message_id,
        rating=req.rating,
        feedback_text=req.feedback_text,
        response_type=req.response_type,
        tags=req.tags or [],
        context_snapshot_json=req.context_snapshot,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return {"status": "ok", "feedback_id": feedback.id}


@router.get("/feedback/stats")
def get_ai_feedback_stats(
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if company_id:
        get_user_company(db, company_id, user)
    else:
        if not getattr(user, 'is_platform_admin', False) and getattr(user, 'role', '') not in ('admin', 'owner'):
            raise HTTPException(status_code=403, detail="Admin access required for global feedback stats")
    from server.services.feedback_analyzer import get_feedback_stats
    return get_feedback_stats(db, company_id=company_id)


@router.get("/learning-context/{company_id}")
def get_learning_context(company_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    get_user_company(db, company_id, user)
    from server.services.learning_context import build_learning_context, format_learning_context_for_prompt
    ctx = build_learning_context(company_id, db)
    prompt_text = format_learning_context_for_prompt(ctx)
    return {
        "company_id": company_id,
        "learning_context": ctx,
        "prompt_preview": prompt_text,
    }
