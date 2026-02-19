from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from server.core.db import get_db
from server.models.lead import Lead
from datetime import datetime

router = APIRouter(prefix="/api/leads", tags=["leads"])

class LeadCreate(BaseModel):
    email: str
    company: str = ""
    plan: str = ""

@router.post("")
def create_lead(data: LeadCreate, db: Session = Depends(get_db)):
    lead = Lead(email=data.email, company=data.company, plan=data.plan, created_at=datetime.utcnow())
    db.add(lead)
    db.commit()
    return {"status": "ok", "message": "Lead captured"}

@router.get("")
def list_leads(limit: int = 50, db: Session = Depends(get_db)):
    leads = db.query(Lead).order_by(Lead.created_at.desc()).limit(limit).all()
    return [{"id": l.id, "email": l.email, "company": l.company, "plan": l.plan, "created_at": l.created_at.isoformat() if l.created_at else None} for l in leads]
