"""
API endpoints for notification management.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from server.services.notifications import (
    send_feature_notification, 
    send_publish_notification,
    send_early_member_invite,
    parse_changelog,
    NOTIFICATION_RECIPIENTS
)

router = APIRouter(prefix="/notifications", tags=["notifications"])

email_events_store: Dict[str, Dict[str, Any]] = {}


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


def classify_email_event(event: Dict[str, Any]) -> None:
    """
    Classify email opens as human or machine based on timing and click behavior.
    - Opens < 2 seconds after delivery with no clicks = machine (bot/scanner)
    - Opens with clicks = human
    - Opens > 2 seconds after delivery = human (tentative)
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
    
    record = email_events_store.setdefault(email_id, {
        "email_id": email_id,
        "to": data.get("to"),
        "subject": data.get("subject"),
        "delivered_at": None,
        "opened_at": None,
        "clicked_at": None,
        "classification": None,
        "events": []
    })
    
    record["events"].append({
        "type": event_type,
        "timestamp": timestamp.isoformat(),
        "data": data
    })
    
    if event_type == "email.delivered":
        record["delivered_at"] = timestamp.isoformat()
    
    elif event_type == "email.clicked":
        record["clicked_at"] = timestamp.isoformat()
        record["classification"] = "human"
    
    elif event_type == "email.opened":
        record["opened_at"] = timestamp.isoformat()
        if record["delivered_at"]:
            delivered_dt = datetime.fromisoformat(record["delivered_at"])
            delta = (timestamp - delivered_dt).total_seconds()
            if record["classification"] != "human":
                record["classification"] = "machine" if delta < 2 else "human"
    
    email_events_store[email_id] = record


@router.post("/resend-webhook")
async def handle_resend_webhook(event: Dict[str, Any]) -> Dict[str, str]:
    """
    Receive Resend webhook events and classify email opens.
    Configure this endpoint in Resend dashboard:
    - Subscribe to: email.delivered, email.opened, email.clicked
    """
    try:
        classify_email_event(event)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/email-stats/{email_id}")
async def get_email_stats(email_id: str) -> Dict[str, Any]:
    """Get classification and event info for a specific email."""
    record = email_events_store.get(email_id)
    if not record:
        raise HTTPException(status_code=404, detail="Email not found")
    return record


@router.get("/email-stats")
async def get_all_email_stats() -> Dict[str, Any]:
    """Get all tracked email events with classifications."""
    total = len(email_events_store)
    human_opens = sum(1 for r in email_events_store.values() if r.get("classification") == "human")
    machine_opens = sum(1 for r in email_events_store.values() if r.get("classification") == "machine")
    
    return {
        "total_emails": total,
        "human_opens": human_opens,
        "machine_opens": machine_opens,
        "emails": list(email_events_store.values())
    }
