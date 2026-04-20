"""
Lead-gen admin API routes for FounderConsole (predixen).

Place at: server/api/lead_gen.py
Register in server/main.py by adding to _register_remaining_routers():
    from server.api.lead_gen import router as lead_gen_router
    app.include_router(lead_gen_router)

Endpoints (all under /api/admin/lead-gen, platform-admin gated):
  GET    /leads                    - paginated list with filters
  GET    /leads/{id}               - detail + recent events
  POST   /leads                    - manual create (tries to upsert on email)
  PATCH  /leads/{id}               - update fields (status, notes, tags)
  DELETE /leads/{id}               - hard delete (audit-logged)
  POST   /leads/{id}/actions       - manual trigger: send_email, pause, resume, mark_replied

  GET    /campaigns                - list campaigns
  POST   /campaigns                - create
  PATCH  /campaigns/{id}           - edit
  GET    /campaigns/{id}/leads     - leads in a campaign

  GET    /templates                - list templates
  PATCH  /templates/{id}           - edit prompt/subject

  GET    /stats                    - funnel counts + recent events
  GET    /settings                 - n8n connection + toggles
  PATCH  /settings                 - update

Webhook receivers (mounted separately, unauthenticated + HMAC-signed):
  POST /webhooks/lead-gen/ingest      - n8n pushes a newly-scraped lead
  POST /webhooks/lead-gen/event       - n8n pushes an event (email_sent, reply, etc.)
  POST /webhooks/lead-gen/simulation  - predixen itself calls this on first-sim-complete
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.orm import Session

# Follow the existing import style in server/api/admin.py + server/api/leads.py
from server.core.database import get_db
from server.core.security import get_current_user, require_platform_admin
from server.models.user import User
from server.models.lead import Lead  # existing — extended with new columns
from server.models.lead_gen import LeadCampaign, LeadEvent, LeadTemplate, LeadGenSettings
from server.services.audit import log_audit
from server.services.credentials import CredentialEncryption  # re-use existing encryption

router = APIRouter(prefix="/api/admin/lead-gen", tags=["admin", "lead-gen"])

# ============================================================
# Pydantic schemas
# ============================================================

class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    linkedin_url: Optional[str] = None
    website: Optional[str] = None
    source: str
    sector: Optional[str] = None
    stage: Optional[str] = None
    status: str
    hunter_status: Optional[str] = None
    plan: Optional[str] = None
    summary: Optional[str] = None
    hook: Optional[str] = None
    last_email_at: Optional[datetime] = None
    reply_category: Optional[str] = None
    trial_signed_up_at: Optional[datetime] = None
    has_simulated: bool
    p50_survival: Optional[int] = None
    tags: list[str] = []
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class LeadCreateIn(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    linkedin_url: Optional[str] = None
    website: Optional[str] = None
    source: str = "manual"
    stage: Optional[str] = None
    sector: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    notes: Optional[str] = None


class LeadPatchIn(BaseModel):
    status: Optional[str] = None
    stage: Optional[str] = None
    sector: Optional[str] = None
    plan: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[list[str]] = None
    reply_category: Optional[str] = None


class LeadActionIn(BaseModel):
    action: str  # send_email | pause | resume | mark_replied | mark_unsubscribed
    template_key: Optional[str] = None
    campaign_id: Optional[int] = None
    custom_subject: Optional[str] = None
    custom_body: Optional[str] = None


class LeadEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    lead_id: int
    campaign_id: Optional[int] = None
    kind: str
    email_subject: Optional[str] = None
    email_body_preview: Optional[str] = None
    reply_category: Optional[str] = None
    metadata: dict = {}
    source_system: str
    created_at: datetime


class LeadDetailOut(LeadOut):
    recent_events: list[LeadEventOut] = []


class CampaignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: Optional[str] = None
    target_segment: dict = {}
    n8n_workflow_id: Optional[str] = None
    n8n_webhook_path: Optional[str] = None
    cadence_days: list[int] = []
    goal_metric: str
    status: str
    created_at: datetime


class CampaignIn(BaseModel):
    name: str
    description: Optional[str] = None
    target_segment: dict = Field(default_factory=dict)
    n8n_workflow_id: Optional[str] = None
    n8n_webhook_path: Optional[str] = None
    cadence_days: list[int] = Field(default_factory=lambda: [0, 2, 5, 9])
    goal_metric: str = "trial_signup"
    status: str = "draft"


class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    key: str
    label: str
    category: str
    system_prompt: str
    sample_subject: Optional[str] = None
    sample_body: Optional[str] = None
    model: Optional[str] = None
    is_active: bool
    updated_at: datetime


class TemplatePatchIn(BaseModel):
    label: Optional[str] = None
    system_prompt: Optional[str] = None
    sample_subject: Optional[str] = None
    sample_body: Optional[str] = None
    model: Optional[str] = None
    is_active: Optional[bool] = None


class StatsOut(BaseModel):
    totals: dict[str, int]           # by status
    sources: dict[str, int]           # by source
    last_7d_sends: int
    last_7d_replies: int
    reply_rate_7d: float              # 0..1
    trial_signups_7d: int
    active_campaigns: int
    recent_events: list[LeadEventOut]


class SettingsOut(BaseModel):
    n8n_base_url: Optional[str] = None
    n8n_api_key_set: bool  # boolean so we never leak the key
    outbound_webhook_url: Optional[str] = None
    activation_webhook_url: Optional[str] = None
    sending_domain: Optional[str] = None
    daily_send_limit: int
    is_enabled: bool
    updated_at: Optional[datetime] = None


class SettingsPatchIn(BaseModel):
    n8n_base_url: Optional[str] = None
    n8n_api_key: Optional[str] = None  # plaintext in; we encrypt on the way to the DB
    outbound_webhook_url: Optional[str] = None
    activation_webhook_url: Optional[str] = None
    sending_domain: Optional[str] = None
    daily_send_limit: Optional[int] = None
    is_enabled: Optional[bool] = None


# ============================================================
# Leads
# ============================================================

@router.get("/leads", response_model=dict)
def list_leads(
    search: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    source: Optional[str] = None,
    stage: Optional[str] = None,
    has_replied: Optional[bool] = None,
    page: int = 1,
    page_size: int = 25,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    """Paginated list with filters."""
    page_size = min(max(page_size, 1), 100)
    offset = (page - 1) * page_size

    stmt = select(Lead)
    count_stmt = select(func.count()).select_from(Lead)

    conditions = []
    if search:
        like = f"%{search}%"
        conditions.append(or_(
            Lead.email.ilike(like),
            Lead.company.ilike(like),
            Lead.first_name.ilike(like),
            Lead.last_name.ilike(like),
        ))
    if status_filter:
        conditions.append(Lead.status == status_filter)
    if source:
        conditions.append(Lead.source == source)
    if stage:
        conditions.append(Lead.stage == stage)
    if has_replied is True:
        conditions.append(Lead.reply_category.is_not(None))
    elif has_replied is False:
        conditions.append(Lead.reply_category.is_(None))

    if conditions:
        stmt = stmt.where(and_(*conditions))
        count_stmt = count_stmt.where(and_(*conditions))

    total = db.execute(count_stmt).scalar() or 0
    stmt = stmt.order_by(desc(Lead.created_at)).offset(offset).limit(page_size)
    rows = db.execute(stmt).scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [LeadOut.model_validate(r).model_dump() for r in rows],
    }


@router.get("/leads/{lead_id}", response_model=LeadDetailOut)
def get_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    events = db.execute(
        select(LeadEvent)
        .where(LeadEvent.lead_id == lead_id)
        .order_by(desc(LeadEvent.created_at))
        .limit(50)
    ).scalars().all()

    detail = LeadDetailOut.model_validate(lead).model_copy(update={
        "recent_events": [LeadEventOut.model_validate(e).model_dump() for e in events],
    })
    return detail


@router.post("/leads", response_model=LeadOut, status_code=status.HTTP_201_CREATED)
def create_lead(
    data: LeadCreateIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    existing = db.execute(select(Lead).where(Lead.email == data.email)).scalar_one_or_none()
    if existing:
        # upsert: patch existing fields
        for k, v in data.model_dump(exclude_unset=True, exclude={"email"}).items():
            if v is not None:
                setattr(existing, k, v)
        existing.updated_at = datetime.utcnow()
        lead = existing
    else:
        lead = Lead(**data.model_dump(exclude_unset=True), status="new")
        db.add(lead)
    db.commit()
    db.refresh(lead)

    log_audit(db, admin, "lead.created" if not existing else "lead.updated", {"email": data.email, "lead_id": lead.id})
    return lead


@router.patch("/leads/{lead_id}", response_model=LeadOut)
def patch_lead(
    lead_id: int,
    data: LeadPatchIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    before = {k: getattr(lead, k) for k in data.model_dump(exclude_unset=True).keys()}
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(lead, k, v)
    lead.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(lead)

    log_audit(db, admin, "lead.patched", {"lead_id": lead_id, "changes": data.model_dump(exclude_unset=True), "before": before})
    return lead


@router.delete("/leads/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    email = lead.email
    db.delete(lead)
    db.commit()
    log_audit(db, admin, "lead.deleted", {"lead_id": lead_id, "email": email})


@router.post("/leads/{lead_id}/actions", response_model=dict)
async def lead_action(
    lead_id: int,
    body: LeadActionIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    """
    Manual trigger dispatched from the admin UI.
    Delegates to n8n via webhook for sends, or updates local state for pauses/marks.
    """
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    settings = _get_settings_or_default(db)

    if body.action == "send_email":
        if not settings.outbound_webhook_url:
            raise HTTPException(status_code=400, detail="outbound_webhook_url not configured. Set it in /admin/lead-gen/settings.")
        payload = {
            "email": lead.email,
            "first_name": lead.first_name,
            "last_name": lead.last_name,
            "company_name": lead.company,
            "linkedin_url": lead.linkedin_url,
            "source": lead.source,
            "campaign_id": body.campaign_id,
            "template_key": body.template_key,
            "custom_subject": body.custom_subject,
            "custom_body": body.custom_body,
            "triggered_by": admin.email,
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(settings.outbound_webhook_url, json=payload)
                r.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"n8n webhook failed: {e}")

        db.add(LeadEvent(
            lead_id=lead_id, campaign_id=body.campaign_id, kind="email_queued",
            source_system="predixen",
            metadata={"triggered_by": admin.email, "template_key": body.template_key},
        ))
        lead.status = "queued"
        lead.updated_at = datetime.utcnow()
        db.commit()
        log_audit(db, admin, "lead.email_queued", {"lead_id": lead_id, "template_key": body.template_key})
        return {"status": "queued"}

    elif body.action == "pause":
        lead.status = "paused"
    elif body.action == "resume":
        lead.status = "queued"
    elif body.action == "mark_replied":
        lead.status = "replied"
        lead.reply_category = body.template_key or "manual"  # reuse field for category tag
        db.add(LeadEvent(
            lead_id=lead_id, kind="reply_received", source_system="manual",
            reply_category=lead.reply_category,
            metadata={"marked_by": admin.email},
        ))
    elif body.action == "mark_unsubscribed":
        lead.status = "unsubscribed"
        db.add(LeadEvent(lead_id=lead_id, kind="unsubscribed", source_system="manual",
                         metadata={"marked_by": admin.email}))
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {body.action}")

    lead.updated_at = datetime.utcnow()
    db.commit()
    log_audit(db, admin, f"lead.{body.action}", {"lead_id": lead_id})
    return {"status": lead.status}


# ============================================================
# Campaigns
# ============================================================

@router.get("/campaigns", response_model=list[CampaignOut])
def list_campaigns(db: Session = Depends(get_db), admin: User = Depends(require_platform_admin)):
    rows = db.execute(select(LeadCampaign).order_by(desc(LeadCampaign.created_at))).scalars().all()
    return [CampaignOut.model_validate(r) for r in rows]


@router.post("/campaigns", response_model=CampaignOut, status_code=201)
def create_campaign(
    data: CampaignIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    camp = LeadCampaign(**data.model_dump(), created_by=admin.id)
    db.add(camp)
    db.commit()
    db.refresh(camp)
    log_audit(db, admin, "campaign.created", {"campaign_id": camp.id, "name": camp.name})
    return camp


@router.patch("/campaigns/{campaign_id}", response_model=CampaignOut)
def patch_campaign(
    campaign_id: int,
    data: CampaignIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    camp = db.get(LeadCampaign, campaign_id)
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(camp, k, v)
    camp.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(camp)
    log_audit(db, admin, "campaign.patched", {"campaign_id": campaign_id})
    return camp


@router.get("/campaigns/{campaign_id}/leads", response_model=list[LeadOut])
def list_campaign_leads(
    campaign_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    """Leads that have at least one event tied to this campaign."""
    stmt = (
        select(Lead)
        .join(LeadEvent, LeadEvent.lead_id == Lead.id)
        .where(LeadEvent.campaign_id == campaign_id)
        .distinct()
        .order_by(desc(Lead.last_email_at))
    )
    return [LeadOut.model_validate(r) for r in db.execute(stmt).scalars().all()]


# ============================================================
# Templates
# ============================================================

@router.get("/templates", response_model=list[TemplateOut])
def list_templates(db: Session = Depends(get_db), admin: User = Depends(require_platform_admin)):
    rows = db.execute(select(LeadTemplate).order_by(LeadTemplate.category, LeadTemplate.key)).scalars().all()
    return [TemplateOut.model_validate(r) for r in rows]


@router.patch("/templates/{template_id}", response_model=TemplateOut)
def patch_template(
    template_id: int,
    data: TemplatePatchIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    tpl = db.get(LeadTemplate, template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(tpl, k, v)
    tpl.updated_by = admin.id
    tpl.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(tpl)
    log_audit(db, admin, "template.patched", {"template_id": template_id, "key": tpl.key})
    return tpl


# ============================================================
# Stats + settings
# ============================================================

@router.get("/stats", response_model=StatsOut)
def stats(db: Session = Depends(get_db), admin: User = Depends(require_platform_admin)):
    # Totals by status
    totals_rows = db.execute(
        select(Lead.status, func.count()).group_by(Lead.status)
    ).all()
    totals = {k or "unknown": int(v) for k, v in totals_rows}

    sources_rows = db.execute(
        select(Lead.source, func.count()).group_by(Lead.source)
    ).all()
    sources = {k or "unknown": int(v) for k, v in sources_rows}

    week_ago = datetime.utcnow() - timedelta(days=7)
    sends_7d = db.execute(
        select(func.count()).select_from(LeadEvent)
        .where(LeadEvent.kind == "email_sent", LeadEvent.created_at >= week_ago)
    ).scalar() or 0
    replies_7d = db.execute(
        select(func.count()).select_from(LeadEvent)
        .where(LeadEvent.kind == "reply_received", LeadEvent.created_at >= week_ago)
    ).scalar() or 0
    signups_7d = db.execute(
        select(func.count()).select_from(Lead)
        .where(Lead.trial_signed_up_at >= week_ago)
    ).scalar() or 0

    reply_rate = (replies_7d / sends_7d) if sends_7d else 0.0

    active_campaigns = db.execute(
        select(func.count()).select_from(LeadCampaign).where(LeadCampaign.status == "active")
    ).scalar() or 0

    recent = db.execute(
        select(LeadEvent).order_by(desc(LeadEvent.created_at)).limit(20)
    ).scalars().all()

    return StatsOut(
        totals=totals,
        sources=sources,
        last_7d_sends=int(sends_7d),
        last_7d_replies=int(replies_7d),
        reply_rate_7d=round(reply_rate, 4),
        trial_signups_7d=int(signups_7d),
        active_campaigns=int(active_campaigns),
        recent_events=[LeadEventOut.model_validate(e) for e in recent],
    )


def _get_settings_or_default(db: Session) -> LeadGenSettings:
    s = db.get(LeadGenSettings, 1)
    if not s:
        s = LeadGenSettings(id=1)
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


@router.get("/settings", response_model=SettingsOut)
def get_settings(db: Session = Depends(get_db), admin: User = Depends(require_platform_admin)):
    s = _get_settings_or_default(db)
    return SettingsOut(
        n8n_base_url=s.n8n_base_url,
        n8n_api_key_set=bool(s.n8n_api_key_encrypted),
        outbound_webhook_url=s.outbound_webhook_url,
        activation_webhook_url=s.activation_webhook_url,
        sending_domain=s.sending_domain,
        daily_send_limit=s.daily_send_limit,
        is_enabled=s.is_enabled,
        updated_at=s.updated_at,
    )


@router.patch("/settings", response_model=SettingsOut)
def patch_settings(
    data: SettingsPatchIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    s = _get_settings_or_default(db)
    patch = data.model_dump(exclude_unset=True)
    if "n8n_api_key" in patch:
        api_key = patch.pop("n8n_api_key")
        if api_key:
            s.n8n_api_key_encrypted = CredentialEncryption.encrypt(api_key)
        else:
            s.n8n_api_key_encrypted = None
    for k, v in patch.items():
        setattr(s, k, v)
    s.updated_by = admin.id
    s.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(s)
    log_audit(db, admin, "lead_gen.settings_patched", {"keys": list(patch.keys())})
    return get_settings(db, admin)  # reuse for response shape


# ============================================================
# Convenience: fetch a template by key (used by the n8n workflow)
# ============================================================
@router.get("/templates/by-key/{key}", response_model=TemplateOut)
def get_template_by_key(
    key: str,
    db: Session = Depends(get_db),
    # Intentionally not admin-gated — n8n needs to fetch templates at send time.
    # Protect via a shared secret header if exposed publicly; see SETUP.md.
    current_user: User = Depends(get_current_user),
):
    tpl = db.execute(select(LeadTemplate).where(LeadTemplate.key == key, LeadTemplate.is_active == True)).scalar_one_or_none()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return tpl
