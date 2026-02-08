import os
import uuid
import hmac
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Request, Query, HTTPException, Header, Depends
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy import func, case, and_

from server.core.db import get_db
from server.models.email_event import EmailEvent, EmailLinkClick, EmailFeedback

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/email-tracking", tags=["email-tracking"])

WEBHOOK_SECRET = os.getenv("RESEND_WEBHOOK_SECRET", "")
ANALYTICS_TOKEN = os.getenv("ANALYTICS_ACCESS_TOKEN", "predixen-analytics-2026")


def _verify_resend_signature(payload: bytes, signature: Optional[str]) -> bool:
    if not WEBHOOK_SECRET:
        return True
    if not signature:
        return False
    try:
        expected = hmac.new(
            WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
    except Exception:
        return False


class ResendWebhookPayload(BaseModel):
    type: str
    created_at: Optional[str] = None
    data: dict


@router.post("/webhooks/resend")
async def resend_webhook(request: Request):
    raw_body = await request.body()
    svix_signature = request.headers.get("svix-signature") or request.headers.get("webhook-signature")
    
    if WEBHOOK_SECRET and not svix_signature:
        raise HTTPException(status_code=401, detail="Missing webhook signature")
    
    body = await request.json()
    event_type = body.get("type", "")
    data = body.get("data", {})
    email_id = data.get("email_id") or data.get("id", "")
    timestamp = body.get("created_at") or datetime.utcnow().isoformat()

    try:
        ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        ts = datetime.utcnow()

    db = next(get_db())
    try:
        event_record = db.query(EmailEvent).filter(EmailEvent.email_id == email_id).first()

        if not event_record:
            event_record = EmailEvent(
                email_id=email_id,
                to_email=data.get("to", [None])[0] if isinstance(data.get("to"), list) else data.get("to"),
                subject=data.get("subject"),
                sent_at=ts,
                events_json=[]
            )
            db.add(event_record)
            db.flush()

        events_list = event_record.events_json or []
        events_list.append({
            "type": event_type,
            "timestamp": ts.isoformat(),
            "data": {k: v for k, v in data.items() if k not in ("html", "text")}
        })
        event_record.events_json = events_list
        event_record.updated_at = datetime.utcnow()

        if event_type == "email.delivered":
            event_record.delivered_at = ts
        elif event_type == "email.opened":
            is_bot = False
            seconds_since_sent = None
            if event_record.sent_at:
                seconds_since_sent = (ts - event_record.sent_at).total_seconds()

            ua = (data.get("user_agent") or data.get("userAgent") or "").lower()
            bot_ua_keywords = [
                "googleimageproxy", "mozilla/5.0 (windows nt 10.0; win64; x64)",
                "barracuda", "mimecast", "proofpoint", "fortiguard",
                "symantec", "fireeye", "trendmicro", "sophos",
                "messagelabs", "ironport", "mailguard", "spamhaus",
                "protection", "scanner", "crawler", "bot", "spider",
                "preview", "prefetch", "guard", "antivirus",
            ]

            if seconds_since_sent is not None and seconds_since_sent < 30:
                is_bot = True
            elif any(kw in ua for kw in bot_ua_keywords):
                is_bot = True
            elif not event_record.delivered_at:
                is_bot = True
            elif event_record.delivered_at and (ts - event_record.delivered_at).total_seconds() < 5:
                is_bot = True

            if is_bot:
                event_record.is_bot_open = True
                event_record.classification = "machine"
            else:
                if not event_record.classification or event_record.classification == "machine":
                    event_record.classification = "human"
                    event_record.is_bot_open = False

            event_record.open_count = (event_record.open_count or 0) + 1
            if is_bot:
                if not event_record.opened_at:
                    pass
            else:
                event_record.opened_at = ts
        elif event_type == "email.clicked":
            event_record.click_count = (event_record.click_count or 0) + 1
            if not event_record.clicked_at:
                event_record.clicked_at = ts
            clicked_url = data.get("click", {}).get("link") or data.get("url", "")
            if clicked_url:
                urls = event_record.clicked_urls or []
                urls.append({"url": clicked_url, "at": ts.isoformat()})
                event_record.clicked_urls = urls
        elif event_type == "email.bounced":
            event_record.bounced_at = ts
        elif event_type == "email.complained":
            event_record.complained_at = ts

        db.commit()
        logger.info(f"Webhook processed: {event_type} for {email_id}")
        return {"status": "ok"}

    except Exception as e:
        db.rollback()
        logger.error(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@router.get("/r/{tracking_id}")
async def track_link_click(tracking_id: str, request: Request):
    db = next(get_db())
    try:
        link = db.query(EmailLinkClick).filter(EmailLinkClick.tracking_id == tracking_id).first()
        if not link:
            return RedirectResponse(url="https://predixen.app", status_code=302)

        link.clicked = True
        link.click_count = (link.click_count or 0) + 1
        now = datetime.utcnow()
        if not link.first_clicked_at:
            link.first_clicked_at = now
        link.last_clicked_at = now
        link.user_agent = request.headers.get("user-agent", "")[:500]
        link.ip_address = request.client.host if request.client else None

        if link.email_id:
            event = db.query(EmailEvent).filter(EmailEvent.email_id == link.email_id).first()
            if event:
                event.click_count = (event.click_count or 0) + 1
                if not event.clicked_at:
                    event.clicked_at = now
                urls = event.clicked_urls or []
                urls.append({"url": link.destination_url, "label": link.link_label, "at": now.isoformat()})
                event.clicked_urls = urls

        db.commit()
        return RedirectResponse(url=link.destination_url, status_code=302)

    except Exception as e:
        db.rollback()
        logger.error(f"Link tracking error: {e}")
        return RedirectResponse(url="https://predixen.app", status_code=302)
    finally:
        db.close()


@router.get("/feedback")
async def email_feedback_page(
    email_id: Optional[str] = None,
    email: Optional[str] = None,
    campaign: Optional[str] = None,
    rating: Optional[str] = None
):
    submitted = False
    if rating:
        db = next(get_db())
        try:
            fb = EmailFeedback(
                email_id=email_id,
                recipient_email=email,
                rating=rating,
                campaign=campaign,
                created_at=datetime.utcnow()
            )
            db.add(fb)
            db.commit()
            submitted = True
        except Exception as e:
            db.rollback()
            logger.error(f"Feedback save error: {e}")
        finally:
            db.close()

    base_url = "/email-tracking/feedback"
    params = f"email_id={email_id or ''}&email={email or ''}&campaign={campaign or ''}"

    if submitted:
        html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
        <title>Thank You - Predixen</title>
        <style>body{{margin:0;padding:40px 20px;background:#f4f4f5;font-family:'Segoe UI',sans-serif;display:flex;justify-content:center;}}
        .card{{background:#fff;border-radius:12px;padding:48px;max-width:480px;width:100%;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,0.08);}}
        h2{{color:#1e293b;margin:0 0 12px;}} p{{color:#64748b;font-size:15px;line-height:1.6;}}
        .check{{font-size:48px;margin-bottom:16px;color:#22c55e;}}</style></head>
        <body><div class="card"><div class="check">&#10003;</div><h2>Thank you for your feedback!</h2>
        <p>Your response helps us improve Predixen for you.</p></div></body></html>"""
    else:
        html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
        <title>Feedback - Predixen</title>
        <style>body{{margin:0;padding:40px 20px;background:#f4f4f5;font-family:'Segoe UI',sans-serif;display:flex;justify-content:center;}}
        .card{{background:#fff;border-radius:12px;padding:48px;max-width:480px;width:100%;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,0.08);}}
        h2{{color:#1e293b;margin:0 0 8px;}} p{{color:#64748b;font-size:15px;margin:0 0 32px;}}
        .btns{{display:flex;gap:16px;justify-content:center;flex-wrap:wrap;}}
        a.btn{{display:inline-flex;align-items:center;gap:8px;padding:14px 28px;border-radius:8px;text-decoration:none;font-size:15px;font-weight:600;border:1px solid #e2e8f0;color:#334155;transition:all .15s;}}
        a.btn:hover{{background:#f8fafc;border-color:#94a3b8;}}
        a.yes{{background:#22c55e;color:#fff;border-color:#22c55e;}} a.yes:hover{{background:#16a34a;}}
        a.meh{{background:#f59e0b;color:#fff;border-color:#f59e0b;}} a.meh:hover{{background:#d97706;}}
        textarea{{width:100%;padding:12px;border:1px solid #e2e8f0;border-radius:8px;margin-top:24px;font-size:14px;resize:vertical;min-height:80px;font-family:inherit;}}
        </style></head>
        <body><div class="card"><h2>Was this email helpful?</h2>
        <p>Your feedback helps us send you more relevant updates.</p>
        <div class="btns">
        <a class="btn yes" href="{base_url}?{params}&rating=helpful">Yes, helpful</a>
        <a class="btn meh" href="{base_url}?{params}&rating=somewhat">Somewhat</a>
        <a class="btn" href="{base_url}?{params}&rating=not_helpful">Not really</a>
        </div></div></body></html>"""

    return HTMLResponse(content=html)


@router.post("/feedback")
async def submit_feedback_api(request: Request):
    body = await request.json()
    db = next(get_db())
    try:
        fb = EmailFeedback(
            email_id=body.get("email_id"),
            recipient_email=body.get("email"),
            rating=body.get("rating"),
            comment=body.get("comment"),
            campaign=body.get("campaign"),
            created_at=datetime.utcnow()
        )
        db.add(fb)
        db.commit()
        return {"status": "ok"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@router.get("/analytics")
async def email_analytics(
    request: Request,
    campaign: Optional[str] = None,
    days: int = Query(default=30, ge=1, le=365),
    token: Optional[str] = Query(default=None)
):
    auth_header = request.headers.get("authorization", "")
    provided_token = token or auth_header.replace("Bearer ", "")
    if ANALYTICS_TOKEN and provided_token != ANALYTICS_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    db = next(get_db())
    try:
        since = datetime.utcnow() - timedelta(days=days)
        q = db.query(EmailEvent).filter(EmailEvent.created_at >= since)
        if campaign:
            q = q.filter(EmailEvent.campaign == campaign)

        events = q.all()
        total = len(events)
        delivered = sum(1 for e in events if e.delivered_at)
        opened_human = sum(1 for e in events if e.opened_at and not e.is_bot_open)
        opened_bot = sum(1 for e in events if e.is_bot_open)
        clicked = sum(1 for e in events if e.clicked_at)
        bounced = sum(1 for e in events if e.bounced_at)
        complained = sum(1 for e in events if e.complained_at)

        open_rate = (opened_human / delivered * 100) if delivered > 0 else 0
        click_rate = (clicked / delivered * 100) if delivered > 0 else 0
        bounce_rate = (bounced / total * 100) if total > 0 else 0

        per_recipient = []
        for e in events:
            per_recipient.append({
                "email_id": e.email_id,
                "to": e.to_email,
                "recipient_id": e.recipient_id,
                "campaign": e.campaign,
                "sent_at": e.sent_at.isoformat() if e.sent_at else None,
                "delivered_at": e.delivered_at.isoformat() if e.delivered_at else None,
                "opened_at": e.opened_at.isoformat() if e.opened_at else None,
                "clicked_at": e.clicked_at.isoformat() if e.clicked_at else None,
                "bounced_at": e.bounced_at.isoformat() if e.bounced_at else None,
                "is_bot_open": e.is_bot_open,
                "classification": e.classification,
                "open_count": e.open_count,
                "click_count": e.click_count,
                "clicked_urls": e.clicked_urls
            })

        link_clicks = db.query(EmailLinkClick).filter(
            EmailLinkClick.created_at >= since
        ).all()
        
        top_links = {}
        for lc in link_clicks:
            key = lc.link_label or lc.destination_url
            if key not in top_links:
                top_links[key] = {"label": lc.link_label, "url": lc.destination_url, "clicks": 0, "unique_clickers": set()}
            top_links[key]["clicks"] += lc.click_count or 0
            if lc.recipient_email:
                top_links[key]["unique_clickers"].add(lc.recipient_email)

        top_links_list = [
            {"label": v["label"], "url": v["url"], "clicks": v["clicks"], "unique_clickers": len(v["unique_clickers"])}
            for v in sorted(top_links.values(), key=lambda x: x["clicks"], reverse=True)
        ]

        feedback_records = db.query(EmailFeedback).filter(
            EmailFeedback.created_at >= since
        ).all()
        feedback_summary = {"helpful": 0, "somewhat": 0, "not_helpful": 0, "total": len(feedback_records)}
        for fb in feedback_records:
            if fb.rating in feedback_summary:
                feedback_summary[fb.rating] += 1

        return {
            "period_days": days,
            "campaign_filter": campaign,
            "summary": {
                "total_sent": total,
                "delivered": delivered,
                "opened_human": opened_human,
                "opened_bot": opened_bot,
                "clicked": clicked,
                "bounced": bounced,
                "complained": complained,
                "open_rate_pct": round(open_rate, 1),
                "click_rate_pct": round(click_rate, 1),
                "bounce_rate_pct": round(bounce_rate, 1)
            },
            "per_recipient": per_recipient,
            "top_links": top_links_list,
            "feedback": feedback_summary
        }

    except Exception as e:
        logger.error(f"Analytics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/welcome")
async def welcome_redirect(
    request: Request,
    ref: Optional[str] = None,
    uid: Optional[str] = None,
    dest: str = Query(default="https://predixen.app")
):
    db = next(get_db())
    try:
        from server.models.email_event import EmailLinkClick
        visit = EmailLinkClick(
            tracking_id=f"welcome-{uuid.uuid4().hex[:12]}",
            recipient_email=uid,
            recipient_id=uid,
            destination_url=dest,
            link_label=f"welcome-redirect-{ref or 'direct'}",
            clicked=True,
            click_count=1,
            first_clicked_at=datetime.utcnow(),
            last_clicked_at=datetime.utcnow(),
            user_agent=request.headers.get("user-agent", "")[:500],
            ip_address=request.client.host if request.client else None,
            created_at=datetime.utcnow()
        )
        db.add(visit)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Welcome redirect tracking error: {e}")
    finally:
        db.close()

    return RedirectResponse(url=dest, status_code=302)


def _get_raw_conn():
    import os, psycopg2
    return psycopg2.connect(os.environ["DATABASE_URL"])


def create_tracked_link(
    destination_url: str,
    email_id: Optional[str] = None,
    recipient_email: Optional[str] = None,
    recipient_id: Optional[str] = None,
    link_label: Optional[str] = None,
    base_url: str = "https://predixen.app"
) -> str:
    tracking_id = uuid.uuid4().hex[:16]
    try:
        conn = _get_raw_conn()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO email_link_clicks 
               (email_id, tracking_id, recipient_email, recipient_id, destination_url, link_label, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (email_id, tracking_id, recipient_email, recipient_id, destination_url, link_label, datetime.utcnow())
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Tracked link creation error: {e}")
        return destination_url

    return f"{base_url}/email-tracking/r/{tracking_id}"


def store_sent_email(
    email_id: str,
    to_email: str,
    subject: str,
    from_email: Optional[str] = None,
    recipient_id: Optional[str] = None,
    campaign: Optional[str] = None,
    utm_source: Optional[str] = None,
    utm_medium: Optional[str] = None,
    utm_campaign: Optional[str] = None,
    utm_content: Optional[str] = None,
    utm_term: Optional[str] = None
):
    import json
    try:
        conn = _get_raw_conn()
        cur = conn.cursor()
        now = datetime.utcnow()
        events = json.dumps([{"type": "email.sent", "timestamp": now.isoformat()}])
        cur.execute(
            """INSERT INTO email_events 
               (email_id, to_email, subject, from_email, recipient_id, campaign, sent_at,
                utm_source, utm_medium, utm_campaign, utm_content, utm_term, events_json, created_at, updated_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (email_id) DO NOTHING""",
            (email_id, to_email, subject, from_email, recipient_id, campaign, now,
             utm_source, utm_medium, utm_campaign, utm_content, utm_term, events, now, now)
        )
        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"Stored sent email: {email_id} to {to_email}")
    except Exception as e:
        logger.error(f"Store sent email error: {e}")
