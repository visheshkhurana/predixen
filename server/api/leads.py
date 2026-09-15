"""Lead capture for the public marketing tools.

Two things about this file are load-bearing and easy to get wrong again.

PREFIX. Express proxies /api/* to this app with pathRewrite {"^/api": ""}
(server/index.ts). A router prefix that itself contains /api is therefore
looked up here as "/api/leads" while the request actually arrives as "/leads",
and every caller gets a 404. This router was written with prefix="/api/leads"
and had never served a single request in production.

AUTH. POST is deliberately public — it is the conversion step on a free tool,
and demanding a login first would defeat the purpose. GET is emails, so it is
behind the platform-admin check. Before this file was fixed the listing was
open to anyone; it was unreachable, so nothing leaked, but restoring the route
without also restoring the lock would have turned a dead endpoint into a live
disclosure of every address collected.
"""

import hashlib
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from server.api.admin import require_platform_admin
from server.core.db import get_db
from server.models.lead import Lead
from server.services.posthog import capture as posthog_capture

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/leads", tags=["leads"])


class LeadCreate(BaseModel):
    email: EmailStr
    company: str = ""
    plan: str = ""
    # Where the address came from, so a calculator lead is distinguishable from
    # a hand-entered one. Free text on the model, constrained here.
    source: str = Field(default="website", max_length=50)
    # Whatever context the capturing surface wants to keep — for the runway
    # calculator this is the numbers the visitor actually entered, which is the
    # difference between "an email" and "a person with 4 months of runway".
    notes: Optional[str] = Field(default=None, max_length=2000)
    # Present when the capturing surface has a result worth sending back.
    # Absent for a plain address capture, in which case no email goes out.
    runway_months: Optional[str] = Field(default=None, max_length=20)
    runway_date: Optional[str] = Field(default=None, max_length=40)
    monthly_burn: Optional[str] = Field(default=None, max_length=40)


def _runway_email_html(data: LeadCreate) -> str:
    return f"""
    <div style="font:15px/1.6 -apple-system,Segoe UI,Roboto,sans-serif;color:#1a1d24;max-width:520px">
      <h2 style="margin:0 0 4px;font-size:20px">Your runway</h2>
      <p style="margin:0 0 20px;color:#5b6472">From the FounderConsole runway calculator.</p>
      <table style="border-collapse:collapse;width:100%;margin-bottom:20px">
        <tr><td style="padding:8px 0;color:#5b6472">Months of runway</td>
            <td style="padding:8px 0;text-align:right;font-weight:600">{data.runway_months}</td></tr>
        <tr><td style="padding:8px 0;color:#5b6472">Cash runs out</td>
            <td style="padding:8px 0;text-align:right;font-weight:600">{data.runway_date}</td></tr>
        <tr><td style="padding:8px 0;color:#5b6472">Monthly net burn</td>
            <td style="padding:8px 0;text-align:right;font-weight:600">{data.monthly_burn}</td></tr>
      </table>
      <p style="margin:0 0 8px;color:#5b6472">This uses a simple linear model: cash divided by net burn,
      with revenue growing at the rate you entered. It assumes burn stays flat, which it rarely does.</p>
      <p style="margin:0"><a href="https://founderconsole.ai/tools/runway-calculator"
         style="color:#2563eb">Adjust the numbers</a></p>
    </div>
    """


async def _send_runway_email(data: LeadCreate) -> None:
    """Best-effort. A failure here must never surface to the visitor.

    The lead is already committed by the time this runs, so a bounced send costs
    us the email, not the contact.
    """
    try:
        from server.email.service import send_email

        await send_email(
            to=str(data.email),
            subject=f"Your runway: {data.runway_months} months",
            html_content=_runway_email_html(data),
            campaign="runway-calculator",
        )
    except Exception:
        logger.exception("[leads] could not email the runway result")


def _lead_distinct_id(email: str) -> str:
    digest = hashlib.sha256(email.lower().strip().encode("utf-8")).hexdigest()[:32]
    return f"lead:{digest}"


def _emit_lead_captured(data: LeadCreate, created: bool) -> None:
    """Server-side conversion event. Client trackFunnel after fetch is unproven.

    PostHog project 522965 has calculator_used / cta_click / signup_view but
    zero lead_captured over 90d, even though the calculator chunk still calls
    trackFunnel("lead_captured") after a 2xx. Fire here after the row is
    committed so a successful POST always emits, independent of the browser.
    Does not identify or reset anyone.
    """
    try:
        location = (data.source or "website").strip() or "website"
        properties = {
            "location": location,
            "source": location,
            "created": created,
        }
        if data.runway_months:
            properties["runway_months"] = data.runway_months
        if data.plan:
            properties["plan"] = data.plan
        posthog_capture(
            "lead_captured",
            _lead_distinct_id(str(data.email)),
            properties,
        )
    except Exception:
        logger.exception("[leads] could not emit lead_captured")


@router.post("")
def create_lead(
    data: LeadCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Capture an address. Idempotent on email.

    `Lead.email` is unique, so the previous version raised IntegrityError and
    returned a 500 the second time anyone submitted the same address — which is
    exactly what a person does when they are not sure the first click worked.
    A repeat submission now updates the existing row and reports success,
    because from the visitor's point of view it did succeed.
    """
    email = data.email.lower().strip()
    try:
        lead = db.query(Lead).filter(Lead.email == email).one_or_none()
        if lead is None:
            lead = Lead(email=email, created_at=datetime.utcnow())
            db.add(lead)
            created = True
        else:
            created = False

        # Only overwrite with something non-empty; a later bare submission must
        # not wipe context captured earlier.
        if data.company:
            lead.company = data.company
        if data.plan:
            lead.plan = data.plan
        if data.source:
            lead.source = data.source
        if data.notes:
            lead.notes = data.notes
        lead.updated_at = datetime.utcnow()

        db.commit()
    except SQLAlchemyError:
        db.rollback()
        # Never surface a database error to a marketing page. The visitor can do
        # nothing with it, and a stack trace on a lead form is its own problem.
        raise HTTPException(status_code=503, detail="Could not save that right now")

    # Queued, not awaited: the visitor's request must not wait on Resend or
    # PostHog, and a provider outage must not turn a captured lead into a
    # visible failure.
    background.add_task(_emit_lead_captured, data, created)
    if data.runway_months and data.runway_date:
        background.add_task(_send_runway_email, data)

    return {"status": "ok", "created": created}


@router.get("")
def list_leads(
    limit: int = 50,
    db: Session = Depends(get_db),
    _admin=Depends(require_platform_admin),
):
    """List recent leads. Platform admin only — this returns email addresses."""
    limit = max(1, min(limit, 500))
    leads = db.query(Lead).order_by(Lead.created_at.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "email": l.email,
            "company": l.company,
            "plan": l.plan,
            "source": l.source,
            "notes": l.notes,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in leads
    ]
