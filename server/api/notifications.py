"""
API endpoints for notification management.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from server.services.notifications import (
    send_feature_notification, 
    send_publish_notification,
    send_early_member_invite,
    parse_changelog,
    NOTIFICATION_RECIPIENTS
)

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
