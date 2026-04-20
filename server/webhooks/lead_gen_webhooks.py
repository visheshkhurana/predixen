"""
Webhook receivers for n8n → predixen.

All endpoints under /webhooks/lead-gen/* require a valid HMAC-SHA256
signature in the X-Predixen-Signature header computed from the raw
request body and the LEAD_GEN_WEBHOOK_SECRET env var.

The n8n workflow computes this via a Function node before each POST:
    signature = hex(hmac_sha256(process.env.LEAD_GEN_WEBHOOK_SECRET, JSON.stringify(body)))
"""

from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from server.core.db import get_db
from server.models.lead import Lead
from server.models.lead_gen import LeadEvent

router = APIRouter(prefix="/webhooks/lead-gen", tags=["webhooks", "lead-gen"])


def _get_secret() -> str:
    secret = os.environ.get("LEAD_GEN_WEBHOOK_SECRET", "")
    if not secret:
        raise HTTPException(
            status_code=500,
            detail="LEAD_GEN_WEBHOOK_SECRET not set — refusing to accept unsigned webhooks",
        )
    return secret


async def verify_signature(
    request: Request,
    x_predixen_signature: Optional[str] = Header(None),
) -> bytes:
    secret = _get_secret()
    if not x_predixen_signature:
        raise HTTPException(401, "Missing X-Predixen-Signature header")
    body = await request.body()
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, x_predixen_signature):
        raise HTTPException(401, "Invalid signature")
    return body


# ============================================================
# /ingest — new lead from scraper / CSV import / external source
# ============================================================

class IngestIn(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    linkedin_url: Optional[str] = None
    website: Optional[str] = None
    source: str = "scraper"
    stage: Optional[str] = None
    sector: Optional[str] = None
    summary: Optional[str] = None
    hook: Optional[str] = None
    hunter_status: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


@router.post("/ingest", status_code=status.HTTP_201_CREATED)
async def ingest_lead(
    data: IngestIn,
    request: Request,
    db: Session = Depends(get_db),
    _sig: bytes = Depends(verify_signature),
):
    existing = db.execute(select(Lead).where(Lead.email == data.email)).scalar_one_or_none()
    if existing:
        for k, v in data.model_dump(exclude_unset=True, exclude={"email"}).items():
            if v is not None and not getattr(existing, k, None):
                setattr(existing, k, v)
        existing.updated_at = datetime.utcnow()
        if data.summary or data.hook:
            existing.enriched_at = datetime.utcnow()
        lead_id = existing.id
        action = "updated"
    else:
        lead = Lead(**data.model_dump(exclude_unset=True), status="new")
        if data.summary or data.hook:
            lead.enriched_at = datetime.utcnow()
        db.add(lead)
        db.flush()
        lead_id = lead.id
        action = "created"
    db.add(LeadEvent(lead_id=lead_id, kind=f"ingest_{action}", source_system="n8n"))
    db.commit()
    return {"lead_id": lead_id, "action": action}


# ============================================================
# /event — generic event (email_sent, reply, open, etc.)
# ============================================================

class EventIn(BaseModel):
    email: EmailStr
    kind: str
    campaign_id: Optional[int] = None
    email_subject: Optional[str] = None
    email_body_preview: Optional[str] = None
    gmail_thread_id: Optional[str] = None
    gmail_message_id: Optional[str] = None
    reply_category: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


@router.post("/event", status_code=status.HTTP_201_CREATED)
async def record_event(
    data: EventIn,
    db: Session = Depends(get_db),
    _sig: bytes = Depends(verify_signature),
):
    lead = db.execute(select(Lead).where(Lead.email == data.email)).scalar_one_or_none()
    if not lead:
        raise HTTPException(404, f"No lead with email {data.email}")

    db.add(LeadEvent(
        lead_id=lead.id,
        campaign_id=data.campaign_id,
        kind=data.kind,
        email_subject=data.email_subject,
        email_body_preview=(data.email_body_preview or "")[:500] or None,
        gmail_thread_id=data.gmail_thread_id,
        gmail_message_id=data.gmail_message_id,
        reply_category=data.reply_category,
        event_metadata=data.metadata,
        source_system="n8n",
    ))

    # Denormalize into Lead for fast UI queries
    if data.kind == "email_sent":
        lead.last_email_at = datetime.utcnow()
        if lead.status in ("new", "queued"):
            lead.status = "contacted"
    elif data.kind == "reply_received":
        lead.status = "replied"
        if data.reply_category:
            lead.reply_category = data.reply_category
    elif data.kind == "unsubscribed":
        lead.status = "unsubscribed"
    elif data.kind == "bounced":
        lead.status = "bounced"

    lead.updated_at = datetime.utcnow()
    db.commit()
    return {"ok": True, "lead_id": lead.id}


# ============================================================
# /simulation — predixen's own simulation handler calls this on first run
# ============================================================

class SimulationIn(BaseModel):
    email: EmailStr
    p50_survival: Optional[int] = None


@router.post("/simulation")
async def record_simulation(
    data: SimulationIn,
    db: Session = Depends(get_db),
    _sig: bytes = Depends(verify_signature),
):
    lead = db.execute(select(Lead).where(Lead.email == data.email)).scalar_one_or_none()
    if not lead:
        lead = Lead(
            email=data.email,
            source="signup",
            status="new",
            has_simulated=True,
            p50_survival=data.p50_survival,
            trial_signed_up_at=datetime.utcnow(),
        )
        db.add(lead)
        db.flush()
    else:
        lead.has_simulated = True
        if data.p50_survival is not None:
            lead.p50_survival = data.p50_survival
        if not lead.trial_signed_up_at:
            lead.trial_signed_up_at = datetime.utcnow()
        lead.updated_at = datetime.utcnow()

    db.add(LeadEvent(
        lead_id=lead.id, kind="simulation_completed",
        source_system="predixen",
        event_metadata={"p50_survival": data.p50_survival},
    ))
    db.commit()
    return {"ok": True, "lead_id": lead.id}
