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
import html
import logging
import re
import threading
import time
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from server.api.admin import require_platform_admin
from server.core.db import get_db
from server.middleware.rate_limiter import client_ip, socket_host
from server.models.lead import Lead
from server.services.posthog import capture as posthog_capture
from server.services.posthog import lead_distinct_id, sanitize_distinct_id

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
    # Explicit opt-in from a calculator. False is rejected; the server writes
    # its own consent timestamp and does not trust the client clock.
    consent: bool = False
    consent_at: Optional[datetime] = None
    source_page: str = Field(default="", max_length=200)
    # Browser PostHog distinct_id, when the page has one. Invalid values are
    # dropped so a bad client cannot 422 a real lead.
    distinct_id: Optional[str] = None

    @field_validator("distinct_id", mode="before")
    @classmethod
    def _drop_invalid_distinct_id(cls, value: object) -> Optional[str]:
        if not isinstance(value, str):
            return None
        return sanitize_distinct_id(value)


def _esc(value: object) -> str:
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


# ASCII digits only. A Unicode digit class would accept other numerals.
_NUMBER_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")
_ISO_DATE_RE = re.compile(
    r"^([0-9]{4})-([0-9]{2})-([0-9]{2})"
    r"(?:[T ]([0-9]{2}):([0-9]{2})(?::([0-9]{2})(?:\.[0-9]+)?)?(?:Z|[+-][0-9]{2}:[0-9]{2})?)?$"
)


def _is_iso_date(value: str) -> bool:
    match = _ISO_DATE_RE.fullmatch(value)
    if not match:
        return False
    year, month, day = (int(match.group(i)) for i in range(1, 4))
    hour = int(match.group(4) or 0)
    minute = int(match.group(5) or 0)
    second = int(match.group(6) or 0)
    if hour > 23 or minute > 59 or second > 59:
        return False
    try:
        datetime(year, month, day, hour, minute, second)
    except ValueError:
        return False
    return True


def _is_number_or_iso_date(value: str) -> bool:
    return _NUMBER_RE.fullmatch(value) is not None or _is_iso_date(value)


def _require_safe_result_fields(data: LeadCreate) -> None:
    """Reject runway fields that are not a number or an ISO date.

    These three values are interpolated into the result email. A tag, a
    currency string, or a prose date is a 400, and the row is not written.
    The template also escapes every interpolated value.
    """
    for field in ("runway_months", "runway_date", "monthly_burn"):
        raw = getattr(data, field)
        if raw is None:
            continue
        text = str(raw).strip()
        if not text:
            setattr(data, field, None)
            continue
        if not _is_number_or_iso_date(text):
            raise HTTPException(status_code=400, detail="Invalid result field")
        setattr(data, field, text)


def _result_email_footer() -> str:
    return """<p style="margin:0;color:#5b6472;font-size:13px">You asked for this result.
      Monthly founder finance tips are pending and are not sent until you confirm.
      Unsubscribe any time by emailing hello@founderconsole.ai.</p>"""


def _runway_email_html(data: LeadCreate) -> str:
    months = _esc(data.runway_months)
    when = _esc(data.runway_date)
    burn = _esc(data.monthly_burn)
    return f"""
    <div style="font:15px/1.6 -apple-system,Segoe UI,Roboto,sans-serif;color:#1a1d24;max-width:520px">
      <h2 style="margin:0 0 4px;font-size:20px">Your runway</h2>
      <p style="margin:0 0 20px;color:#5b6472">From the FounderConsole runway calculator.</p>
      <table style="border-collapse:collapse;width:100%;margin-bottom:20px">
        <tr><td style="padding:8px 0;color:#5b6472">Months of runway</td>
            <td style="padding:8px 0;text-align:right;font-weight:600">{months}</td></tr>
        <tr><td style="padding:8px 0;color:#5b6472">Cash runs out</td>
            <td style="padding:8px 0;text-align:right;font-weight:600">{when}</td></tr>
        <tr><td style="padding:8px 0;color:#5b6472">Monthly net burn</td>
            <td style="padding:8px 0;text-align:right;font-weight:600">{burn}</td></tr>
      </table>
      <p style="margin:0 0 8px;color:#5b6472">This uses a simple linear model: cash divided by net burn,
      with revenue growing at the rate you entered. It assumes burn stays flat, which it rarely does.</p>
      <p style="margin:0 0 8px"><a href="https://founderconsole.ai/tools/runway-calculator"
         style="color:#2563eb">Adjust the numbers</a></p>
      {_result_email_footer()}
    </div>
    """


def consent_is_recorded(email: str) -> bool:
    """True only when the committed row has consent and a server timestamp.

    The result email calls this before Resend. A missing row, a false consent
    flag, or a database error all refuse the send.
    """
    from server.core.db import SessionLocal

    db = SessionLocal()
    try:
        lead = db.query(Lead).filter(Lead.email == email.lower().strip()).one_or_none()
        return bool(lead and lead.consent is True and lead.consent_at)
    except Exception:
        logger.exception("[leads] could not confirm consent before email")
        return False
    finally:
        db.close()


async def _send_runway_email(data: LeadCreate) -> None:
    """Best-effort. A failure here must never surface to the visitor.

    Consent has to be on the committed row before this talks to Resend. The
    message is the calculator result, not an LLM prompt, and its links do not
    carry the address.
    """
    if not consent_is_recorded(str(data.email)):
        logger.warning("[leads] not sending the result email; consent is not recorded")
        return
    try:
        from server.email.service import send_email

        subject = f"Your runway: {data.runway_months} months".replace("\r", "").replace("\n", "")
        await send_email(
            to=str(data.email),
            subject=subject,
            html_content=_runway_email_html(data),
            campaign="runway-calculator",
        )
    except Exception:
        logger.exception("[leads] could not email the runway result")


def _lead_distinct_id(email: str) -> str:
    return lead_distinct_id(email)


# Fixed window for POST /leads. Hardcoded so this does not add an env var.
# The middleware applies the same cap; this one does not fail open when the
# database is down, and it never keys the bucket on the address.
LEAD_RATE_LIMIT = 8
LEAD_RATE_WINDOW_SECONDS = 60
_LEAD_HITS: dict[str, list[float]] = {}
_LEAD_LOCK = threading.Lock()


def lead_client_key(request: Optional[Request]) -> str:
    """Client address for the lead bucket. Never an email.

    Delegates to client_ip. X-Real-IP counts only when the TCP peer is
    loopback (Express on 127.0.0.1 or ::ffff:127.0.0.1). Express forwards
    the edge-supplied header unchanged. Otherwise the bucket is the
    X-Forwarded-For entry in front of exactly two trusted hops. This store
    is separate from the middleware window so a request is not counted twice.
    """
    if request is None:
        return "unknown"
    headers = getattr(request, "headers", None)
    key = client_ip(headers, socket_host(request))
    if not key or "@" in key:
        return "unknown"
    return key[:200]


def lead_rate_limited(
    key: str,
    *,
    now: Optional[float] = None,
    limit: int = LEAD_RATE_LIMIT,
    window: float = LEAD_RATE_WINDOW_SECONDS,
    store: Optional[dict[str, list[float]]] = None,
) -> bool:
    """True when this key is over the window. A blocked call does not count."""
    bucket = _LEAD_HITS if store is None else store
    stamp = time.monotonic() if now is None else now
    with _LEAD_LOCK:
        hits = [seen for seen in bucket.get(key, []) if stamp - seen < window]
        if len(hits) >= limit:
            bucket[key] = hits
            return True
        hits.append(stamp)
        bucket[key] = hits
        return False


def _email_markers(email: str) -> tuple[str, ...]:
    """The address and every hash form we must not send to PostHog or a URL."""
    raw = (email or "").lower().strip()
    if not raw:
        return ()
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    short = digest[:32]
    return (raw, digest, short, f"lead:{short}")


def _mentions_email(value: object, markers: tuple[str, ...]) -> bool:
    if value is None or not markers:
        return False
    text = str(value).lower()
    return any(marker and marker in text for marker in markers)


def _event_distinct_id(data: LeadCreate) -> tuple[str, str]:
    """Browser id when it is safe. Never the address and never a hash of it.

    A missing or rejected browser id becomes a random opt-in id. That id is
    not derived from the email, so PostHog cannot be joined back to the address.
    """
    markers = _email_markers(str(data.email))
    client_id = sanitize_distinct_id(data.distinct_id)
    if client_id and not _mentions_email(client_id, markers):
        return client_id, "browser"
    return f"optin:{uuid.uuid4().hex}", "anonymous"


def _scrub_email(value: object, markers: tuple[str, ...], fallback: str = "") -> str:
    text = "" if value is None else str(value)
    if _mentions_email(text, markers):
        return fallback
    return text


# Resend here is a transactional sender (send_email). There is no
# Contacts/Audiences double opt-in, and account verification tokens belong to
# logged-in users, not calculator leads. Opt-ins are stored pending. Monthly
# tips must not go out until consent_status is confirmed.
MARKETING_OPT_IN_PENDING = "pending"
MARKETING_OPT_IN_CONFIRMED = "confirmed"


def lead_may_receive_founder_tips(lead) -> bool:
    """True only after an explicit confirm. Pending consent is not enough."""
    return bool(getattr(lead, "consent", False)) and (
        getattr(lead, "consent_status", None) == MARKETING_OPT_IN_CONFIRMED
    )


def _request_host(request: Optional[Request]) -> str:
    if request is None:
        return ""
    headers = getattr(request, "headers", None)
    raw = ""
    if headers is not None:
        getter = getattr(headers, "get", None)
        if getter is not None:
            raw = getter("x-forwarded-host") or getter("host") or ""
    host = str(raw).split(",")[0].strip()
    if host:
        return host
    url = getattr(request, "url", None)
    return str(getattr(url, "hostname", "") or "")


def _emit_lead_captured(data: LeadCreate, created: bool, host: str = "") -> None:
    """Server-side conversion event. Client trackFunnel after fetch is unproven.

    PostHog project 522965 has calculator_used / cta_click / signup_view but
    zero lead_captured over 90d, even though the calculator chunk still calls
    trackFunnel("lead_captured") after a 2xx. Fire here after the row is
    committed so a successful POST always emits, independent of the browser.
    The distinct_id is the browser one when the page sent a safe id. Otherwise
    it is a random opt-in id. The address and any hash of it are stripped from
    the id and from every property. Does not call identify or reset anyone.
    """
    try:
        markers = _email_markers(str(data.email))
        location = _scrub_email((data.source or "website").strip() or "website", markers, "website") or "website"
        distinct_id, distinct_id_source = _event_distinct_id(data)
        if _mentions_email(distinct_id, markers):
            distinct_id, distinct_id_source = f"optin:{uuid.uuid4().hex}", "anonymous"
        properties = {
            "location": location,
            "source": location,
            "created": created,
            "distinct_id_source": distinct_id_source,
            "host": _scrub_email(host, markers),
        }
        page = _scrub_email((data.source_page or "").strip(), markers)
        if page:
            properties["source_page"] = page
        runway = _scrub_email(data.runway_months, markers)
        if runway:
            properties["runway_months"] = runway
        plan = _scrub_email(data.plan, markers)
        if plan:
            properties["plan"] = plan
        posthog_capture(
            "lead_captured",
            distinct_id,
            properties,
        )
    except Exception:
        logger.exception("[leads] could not emit lead_captured")


@router.post("")
def create_lead(
    data: LeadCreate,
    background: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
):
    """Capture an address. Idempotent on email. Requires consent.

    `Lead.email` is unique, so the previous version raised IntegrityError and
    returned a 500 the second time anyone submitted the same address — which is
    exactly what a person does when they are not sure the first click worked.
    A repeat submission now updates the existing row and reports success,
    because from the visitor's point of view it did succeed.

    Consent has to be true and name the page. The row is stored
    consent_status=pending. No double opt-in email is sent: see
    MARKETING_OPT_IN_PENDING. The result email is the result they asked for,
    not the monthly tips. It is queued only when runway_months and runway_date
    are present, only after the consent row commits, and the sender checks
    that row again before Resend. Burn multiple, dilution, LTV/CAC, and
    default-alive do not queue a message. The public body is always
    {"status": "ok"}. The address is not sent to an LLM.
    """
    if lead_rate_limited(lead_client_key(request)):
        raise HTTPException(status_code=429, detail="Too many requests")
    if data.consent is not True:
        raise HTTPException(status_code=400, detail="Consent is required")
    source_page = (data.source_page or "").strip()
    if not source_page:
        raise HTTPException(status_code=400, detail="A source page is required")
    _require_safe_result_fields(data)

    email = data.email.lower().strip()
    host = _request_host(request)
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
        lead.consent = True
        # Server clock. The client sends consent_at so the payload is explicit;
        # a visitor's clock is not the record.
        lead.consent_at = datetime.utcnow()
        lead.source_page = source_page
        if lead.consent_status != MARKETING_OPT_IN_CONFIRMED:
            lead.consent_status = MARKETING_OPT_IN_PENDING
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
    background.add_task(_emit_lead_captured, data, created, host)
    if data.runway_months and data.runway_date:
        background.add_task(_send_runway_email, data)

    # One body for a new row, a pending row, and a confirmed row. created and
    # consent_status would tell a stranger whether this address is already
    # on the list, and whether the opt-in is still pending.
    return {"status": "ok"}


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
            "consent": bool(l.consent),
            "consent_at": l.consent_at.isoformat() if l.consent_at else None,
            "source_page": l.source_page,
            "consent_status": l.consent_status,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in leads
    ]
