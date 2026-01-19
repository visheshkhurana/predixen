from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from server.core.db import get_db
from server.core.security import get_current_user
from server.models.user import User
from server.models.scenario import Scenario, ScenarioComment
from server.models.company import Company

router = APIRouter(prefix="/comments", tags=["comments"])


class CommentCreate(BaseModel):
    content: str
    parent_id: Optional[int] = None


class CommentUpdate(BaseModel):
    content: str


class CommentResponse(BaseModel):
    id: int
    scenario_id: int
    user_id: int
    user_email: str
    content: str
    created_at: str
    updated_at: Optional[str] = None
    parent_id: Optional[int] = None


def check_scenario_access(scenario_id: int, user: User, db: Session) -> Scenario:
    """Check if user has access to the scenario"""
    from server.models.workspace import WorkspaceMember
    
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    company = db.query(Company).filter(Company.id == scenario.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Check ownership
    if company.user_id == user.id:
        return scenario
    
    # Check workspace membership
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.company_id == company.id,
        WorkspaceMember.user_id == user.id,
        WorkspaceMember.status == "active"
    ).first()
    
    if not member:
        raise HTTPException(status_code=403, detail="No access to this scenario")
    
    return scenario


@router.get("/scenarios/{scenario_id}", response_model=List[CommentResponse])
def list_comments(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all comments for a scenario"""
    check_scenario_access(scenario_id, current_user, db)
    
    comments = db.query(ScenarioComment).filter(
        ScenarioComment.scenario_id == scenario_id
    ).order_by(ScenarioComment.created_at.asc()).all()
    
    result = []
    for comment in comments:
        user = db.query(User).filter(User.id == comment.user_id).first()
        result.append(CommentResponse(
            id=comment.id,
            scenario_id=comment.scenario_id,
            user_id=comment.user_id,
            user_email=user.email if user else "unknown",
            content=comment.content,
            created_at=comment.created_at.isoformat(),
            updated_at=comment.updated_at.isoformat() if comment.updated_at else None,
            parent_id=comment.parent_id
        ))
    
    return result


@router.post("/scenarios/{scenario_id}", response_model=CommentResponse)
def create_comment(
    scenario_id: int,
    request: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new comment on a scenario"""
    check_scenario_access(scenario_id, current_user, db)
    
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="Comment content cannot be empty")
    
    # Verify parent comment exists if specified
    if request.parent_id:
        parent = db.query(ScenarioComment).filter(
            ScenarioComment.id == request.parent_id,
            ScenarioComment.scenario_id == scenario_id
        ).first()
        if not parent:
            raise HTTPException(status_code=400, detail="Parent comment not found")
    
    comment = ScenarioComment(
        scenario_id=scenario_id,
        user_id=current_user.id,
        content=request.content.strip(),
        parent_id=request.parent_id
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    
    return CommentResponse(
        id=comment.id,
        scenario_id=comment.scenario_id,
        user_id=comment.user_id,
        user_email=current_user.email,
        content=comment.content,
        created_at=comment.created_at.isoformat(),
        updated_at=None,
        parent_id=comment.parent_id
    )


@router.patch("/{comment_id}", response_model=CommentResponse)
def update_comment(
    comment_id: int,
    request: CommentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a comment (only by owner)"""
    comment = db.query(ScenarioComment).filter(ScenarioComment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Can only edit your own comments")
    
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="Comment content cannot be empty")
    
    comment.content = request.content.strip()
    comment.updated_at = datetime.utcnow()
    db.commit()
    
    return CommentResponse(
        id=comment.id,
        scenario_id=comment.scenario_id,
        user_id=comment.user_id,
        user_email=current_user.email,
        content=comment.content,
        created_at=comment.created_at.isoformat(),
        updated_at=comment.updated_at.isoformat() if comment.updated_at else None,
        parent_id=comment.parent_id
    )


@router.delete("/{comment_id}")
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a comment (only by owner)"""
    comment = db.query(ScenarioComment).filter(ScenarioComment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Can only delete your own comments")
    
    # Delete replies first
    db.query(ScenarioComment).filter(ScenarioComment.parent_id == comment_id).delete()
    db.delete(comment)
    db.commit()
    
    return {"status": "deleted"}
