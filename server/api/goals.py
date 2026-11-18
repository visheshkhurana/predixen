"""Goals API: founders save their own targets (MRR, runway, a hire, a raise...).

Before this existed the Goals page had nowhere to save to, so "New goal" could
never work. Goals are per company and follow the usual company access rules
(get_user_company also blocks writes from view-only members).
"""
from datetime import date
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from server.core.company_access import get_user_company
from server.core.db import get_db
from server.core.security import get_current_user
from server.models.goal import CompanyGoal
from server.models.user import User

router = APIRouter(tags=["goals"])

Unit = Literal["currency", "months", "percent", "count", "none"]
Status = Literal["on_track", "at_risk", "off_track", "done"]


class GoalCreate(BaseModel):
    title: str = Field(..., max_length=200)
    unit: Unit = "none"
    target_value: Optional[float] = None
    current_value: Optional[float] = None
    deadline: Optional[date] = None
    status: Status = "on_track"
    notes: Optional[str] = Field(None, max_length=2000)

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("Give the goal a name")
        return v


class GoalUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    unit: Optional[Unit] = None
    target_value: Optional[float] = None
    current_value: Optional[float] = None
    deadline: Optional[date] = None
    status: Optional[Status] = None
    notes: Optional[str] = Field(None, max_length=2000)

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Give the goal a name")
        return v


def _goal_dict(g: CompanyGoal) -> Dict[str, Any]:
    return {
        "id": g.id,
        "title": g.title,
        "unit": g.unit,
        "target_value": g.target_value,
        "current_value": g.current_value,
        "deadline": g.deadline.isoformat() if g.deadline else None,
        "status": g.status,
        "notes": g.notes,
        "created_at": g.created_at.isoformat() if g.created_at else None,
        "updated_at": g.updated_at.isoformat() if g.updated_at else None,
    }


def _get_goal(db: Session, company_id: int, goal_id: int) -> CompanyGoal:
    goal = (
        db.query(CompanyGoal)
        .filter(CompanyGoal.id == goal_id, CompanyGoal.company_id == company_id)
        .first()
    )
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


@router.get("/companies/{company_id}/goals")
def list_goals(company_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    company = get_user_company(db, company_id, current_user)
    goals = (
        db.query(CompanyGoal)
        .filter(CompanyGoal.company_id == company.id)
        .order_by(CompanyGoal.created_at.desc(), CompanyGoal.id.desc())
        .all()
    )
    return {"goals": [_goal_dict(g) for g in goals]}


@router.post("/companies/{company_id}/goals", status_code=201)
def create_goal(company_id: int, req: GoalCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    company = get_user_company(db, company_id, current_user)
    goal = CompanyGoal(company_id=company.id, **req.model_dump())
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return _goal_dict(goal)


@router.patch("/companies/{company_id}/goals/{goal_id}")
def update_goal(company_id: int, goal_id: int, req: GoalUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    company = get_user_company(db, company_id, current_user)
    goal = _get_goal(db, company.id, goal_id)
    data = req.model_dump(exclude_unset=True)
    for required in ("title", "unit", "status"):
        if required in data and data[required] is None:
            data.pop(required)
    for k, v in data.items():
        setattr(goal, k, v)
    db.commit()
    db.refresh(goal)
    return _goal_dict(goal)


@router.delete("/companies/{company_id}/goals/{goal_id}")
def delete_goal(company_id: int, goal_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    company = get_user_company(db, company_id, current_user)
    goal = _get_goal(db, company.id, goal_id)
    db.delete(goal)
    db.commit()
    return {"deleted": True}
