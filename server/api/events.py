from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from server.core.db import get_db
from server.models.analytics_event import AnalyticsEvent
from datetime import datetime
from typing import Optional

router = APIRouter(prefix="/api/events", tags=["events"])

class EventCreate(BaseModel):
    event_name: str
    user_id: Optional[int] = None
    company_id: Optional[int] = None
    meta: Optional[dict] = None

@router.post("")
def track_event(data: EventCreate, db: Session = Depends(get_db)):
    event = AnalyticsEvent(
        event_name=data.event_name,
        user_id=data.user_id,
        company_id=data.company_id,
        meta_json=data.meta or {},
        created_at=datetime.utcnow()
    )
    db.add(event)
    db.commit()
    return {"status": "ok", "event_id": event.id}

@router.get("")
def list_events(limit: int = 50, db: Session = Depends(get_db)):
    events = db.query(AnalyticsEvent).order_by(AnalyticsEvent.created_at.desc()).limit(limit).all()
    return [{"id": e.id, "event_name": e.event_name, "user_id": e.user_id, "company_id": e.company_id, "meta": e.meta_json, "created_at": e.created_at.isoformat() if e.created_at else None} for e in events]
