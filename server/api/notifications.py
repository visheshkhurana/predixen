"""
API endpoints for notification management.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from server.services.notifications import (
    send_feature_notification, 
    send_publish_notification,
    send_early_member_invite,
    send_weekly_digest,
    parse_changelog,
    NOTIFICATION_RECIPIENTS
)
from server.core.db import get_db
from server.models.email_event import EmailEvent

router = APIRouter(prefix="/notifications", tags=["notifications"])


class FeatureNotificationRequest(BaseModel):
    feature_name: str
    description: str
    changes: List[str]
    category: str = "Feature Update"
    author: Optional[str] = None
    from_email: Optional[str] = None


class NotificationResponse(BaseModel):
    success: bool
    message: str
    recipients: List[str]


@router.post("/feature", response_model=NotificationResponse)
async def notify_feature_update(request: FeatureNotificationRequest):
    """
    Send email notification about a new feature or platform change.
    Sends to configured recipients: nikita@predixen.ai and vysheshk@gmail.com
    """
    kwargs = {
        "feature_name": request.feature_name,
        "description": request.description,
        "changes": request.changes,
        "category": request.category,
        "author": request.author
    }
    if request.from_email:
        kwargs["from_email"] = request.from_email
    
    success = await send_feature_notification(**kwargs)
    
    if success:
        return NotificationResponse(
            success=True,
            message=f"Feature notification sent successfully for: {request.feature_name}",
            recipients=NOTIFICATION_RECIPIENTS
        )
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to send feature notification. Check Resend configuration."
        )


@router.get("/recipients")
async def get_notification_recipients():
    """Get the list of notification recipients."""
    return {"recipients": NOTIFICATION_RECIPIENTS}


@router.post("/publish")
async def trigger_publish_notification() -> Dict[str, Any]:
    """
    Manually trigger a publish notification.
    This is automatically called on app startup in production.
    Reads from CHANGELOG.md and sends email about new features.
    """
    result = await send_publish_notification()
    
    if result.get("success"):
        return {
            "success": True,
            "message": f"Publish notification sent for version {result.get('version')}",
            "version": result.get("version"),
            "changes_count": result.get("changes_count"),
            "recipients": result.get("recipients")
        }
    else:
        return {
            "success": False,
            "message": result.get("reason", "Failed to send notification")
        }


@router.get("/changelog")
async def get_changelog() -> Dict[str, Any]:
    """
    Get the parsed changelog with latest version info.
    """
    return parse_changelog()


class EarlyMemberInviteRequest(BaseModel):
    to_emails: Optional[List[str]] = None
    invited_by: str = "Nikita Luther, Founder"


@router.post("/early-member-invite")
async def trigger_early_member_invite(request: EarlyMemberInviteRequest) -> Dict[str, Any]:
    """
    Send early member invitation emails individually to each recipient.
    If no emails provided, sends to default NOTIFICATION_RECIPIENTS.
    """
    result = await send_early_member_invite(
        to_emails=request.to_emails,
        invited_by=request.invited_by
    )
    return result


def classify_email_event(event: Dict[str, Any], db: Session) -> None:
    """
    Classify email opens as human or machine based on timing and click behavior.
    - Opens < 2 seconds after delivery with no clicks = machine (bot/scanner)
    - Opens with clicks = human
    - Opens > 2 seconds after delivery = human (tentative)
    Persists to database for durability.
    """
    event_type = event.get("type", "")
    data = event.get("data", {})
    email_id = data.get("email_id")
    
    if not email_id:
        return
    
    timestamp_str = data.get("timestamp") or data.get("created_at")
    if timestamp_str:
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except:
            timestamp = datetime.now(timezone.utc)
    else:
        timestamp = datetime.now(timezone.utc)
    
    record = db.query(EmailEvent).filter(EmailEvent.email_id == email_id).first()
    
    if not record:
        record = EmailEvent(
            email_id=email_id,
            to_email=data.get("to"),
            subject=data.get("subject"),
            events_json=[]
        )
        db.add(record)
    
    events = record.events_json or []
    events.append({
        "type": event_type,
        "timestamp": timestamp.isoformat(),
        "data": data
    })
    record.events_json = events
    
    if event_type == "email.delivered":
        record.delivered_at = timestamp
    
    elif event_type == "email.clicked":
        record.clicked_at = timestamp
        record.classification = "human"
    
    elif event_type == "email.opened":
        record.opened_at = timestamp
        if record.delivered_at:
            delta = (timestamp - record.delivered_at.replace(tzinfo=timezone.utc)).total_seconds()
            if record.classification != "human":
                record.classification = "machine" if delta < 2 else "human"
    
    db.commit()


@router.post("/resend-webhook")
async def handle_resend_webhook(event: Dict[str, Any], db: Session = Depends(get_db)) -> Dict[str, str]:
    """
    Receive Resend webhook events and classify email opens.
    Configure this endpoint in Resend dashboard:
    - Subscribe to: email.delivered, email.opened, email.clicked
    """
    try:
        classify_email_event(event, db)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/email-stats/{email_id}")
async def get_email_stats(email_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get classification and event info for a specific email."""
    record = db.query(EmailEvent).filter(EmailEvent.email_id == email_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Email not found")
    return {
        "email_id": record.email_id,
        "to": record.to_email,
        "subject": record.subject,
        "delivered_at": record.delivered_at.isoformat() if record.delivered_at else None,
        "opened_at": record.opened_at.isoformat() if record.opened_at else None,
        "clicked_at": record.clicked_at.isoformat() if record.clicked_at else None,
        "classification": record.classification,
        "events": record.events_json or []
    }


@router.get("/email-stats")
async def get_all_email_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get all tracked email events with classifications."""
    records = db.query(EmailEvent).order_by(EmailEvent.created_at.desc()).limit(100).all()
    
    total = len(records)
    delivered = sum(1 for r in records if r.delivered_at)
    opened = sum(1 for r in records if r.opened_at)
    clicked = sum(1 for r in records if r.clicked_at)
    human_opens = sum(1 for r in records if r.classification == "human")
    machine_opens = sum(1 for r in records if r.classification == "machine")
    
    emails = [{
        "email_id": r.email_id,
        "to": r.to_email,
        "subject": r.subject,
        "delivered_at": r.delivered_at.isoformat() if r.delivered_at else None,
        "opened_at": r.opened_at.isoformat() if r.opened_at else None,
        "clicked_at": r.clicked_at.isoformat() if r.clicked_at else None,
        "classification": r.classification,
        "created_at": r.created_at.isoformat() if r.created_at else None
    } for r in records]
    
    return {
        "total_emails": total,
        "delivered": delivered,
        "opened": opened,
        "clicked": clicked,
        "human_opens": human_opens,
        "machine_opens": machine_opens,
        "open_rate": round((opened / total * 100), 1) if total > 0 else 0,
        "click_rate": round((clicked / total * 100), 1) if total > 0 else 0,
        "emails": emails
    }


class DigestRequest(BaseModel):
    email: EmailStr
    company_name: str
    metrics: Dict[str, Any]
    alerts: List[Dict[str, Any]] = []
    recommendations: List[str] = []


class DigestSubscriptionRequest(BaseModel):
    email: EmailStr
    company_id: int
    frequency: str = "weekly"  # weekly, daily
    enabled: bool = True


@router.post("/digest/send")
async def send_digest(request: DigestRequest):
    """
    Send a weekly KPI digest email to a user.
    Contains key metrics summary, alerts, and recommendations.
    """
    success = await send_weekly_digest(
        to_email=request.email,
        company_name=request.company_name,
        metrics=request.metrics,
        alerts=request.alerts,
        recommendations=request.recommendations
    )
    
    if success:
        return {
            "success": True,
            "message": f"Weekly digest sent to {request.email}"
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to send digest email. Check Resend configuration."
        )


@router.post("/digest/test")
async def send_test_digest(email: EmailStr):
    """
    Send a test digest email with sample data.
    Useful for previewing the digest format.
    """
    test_metrics = {
        "mrr": 45000,
        "mrr_change_pct": 8.5,
        "runway_months": 14.2,
        "burn_rate": 32000,
        "survival_probability": 0.72,
        "cash_balance": 456000
    }
    
    test_alerts = [
        {"type": "runway", "message": "Runway is below 18-month target. Consider reducing burn or raising funds.", "severity": "warning"},
        {"type": "churn", "message": "Customer churn increased 2% this month. Review retention strategies.", "severity": "info"}
    ]
    
    test_recommendations = [
        "Focus on reducing CAC by 15% through organic marketing channels",
        "Consider extending runway to 18+ months before next fundraise",
        "Implement customer success program to reduce churn below 3%"
    ]
    
    success = await send_weekly_digest(
        to_email=email,
        company_name="Demo Company",
        metrics=test_metrics,
        alerts=test_alerts,
        recommendations=test_recommendations
    )
    
    if success:
        return {
            "success": True,
            "message": f"Test digest sent to {email}"
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to send test digest. Check Resend configuration."
        )
