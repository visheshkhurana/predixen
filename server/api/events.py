"""Internal analytics event log.

SECURITY NOTE — read before changing the prefix or the dependencies.

This router's prefix deliberately excludes /api. Express proxies /api/* to this
app with pathRewrite {"^/api": ""} (server/index.ts), so a prefix of
"/api/events" is registered here as "/api/events" while the request actually
arrives as "/events" — a guaranteed 404 for every caller. That 404 is why this
router sat dormant for months.

When the prefix was corrected the routes became reachable, and both verbs were
open to the world:

  GET  /api/events  returned internal rows including user_id, company_id and a
                    free-form `meta` object, to anyone who asked.
  POST /api/events  accepted unauthenticated writes with a caller-chosen
                    user_id and company_id — arbitrary rows attributed to real
                    users, and unbounded table growth.

Nothing in the codebase calls either verb, so both are now authenticated: reads
require the platform admin (they expose other tenants' identifiers), writes
require a signed-in user and ignore any caller-supplied identity in favour of
the authenticated one. If a public, anonymous ingest endpoint is ever genuinely
needed, add a separate route with its own rate limit and no identity fields —
do not reopen these.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from server.api.admin import require_platform_admin
from server.core.db import get_db
from server.core.security import get_current_user
from server.models.analytics_event import AnalyticsEvent
from server.models import User

router = APIRouter(prefix="/events", tags=["events"])


class EventCreate(BaseModel):
    event_name: str = Field(max_length=120)
    company_id: Optional[int] = None
    meta: Optional[dict] = None
    # user_id is deliberately absent. It used to be caller-supplied, which let
    # anyone attribute an event to any user. It now comes from the session.


@router.post("")
def track_event(
    data: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    event = AnalyticsEvent(
        event_name=data.event_name,
        user_id=current_user.id,
        company_id=data.company_id,
        meta_json=data.meta or {},
        created_at=datetime.utcnow(),
    )
    db.add(event)
    db.commit()
    return {"status": "ok", "event_id": event.id}


@router.get("")
def list_events(
    limit: int = 50,
    db: Session = Depends(get_db),
    _admin=Depends(require_platform_admin),
):
    """Platform admin only — these rows carry user and company identifiers."""
    limit = max(1, min(limit, 500))
    events = db.query(AnalyticsEvent).order_by(AnalyticsEvent.created_at.desc()).limit(limit).all()
    return [
        {
            "id": e.id,
            "event_name": e.event_name,
            "user_id": e.user_id,
            "company_id": e.company_id,
            "meta": e.meta_json,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in events
    ]
