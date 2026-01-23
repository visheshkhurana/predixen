"""
API endpoints for notification management.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from server.services.notifications import send_feature_notification, NOTIFICATION_RECIPIENTS

router = APIRouter(prefix="/notifications", tags=["notifications"])


class FeatureNotificationRequest(BaseModel):
    feature_name: str
    description: str
    changes: List[str]
    category: str = "Feature Update"
    author: Optional[str] = None


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
    success = await send_feature_notification(
        feature_name=request.feature_name,
        description=request.description,
        changes=request.changes,
        category=request.category,
        author=request.author
    )
    
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
