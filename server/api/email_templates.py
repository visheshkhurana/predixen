"""
API endpoints for email template management.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from server.core.db import get_db
from server.core.security import get_current_user
from server.models import User, UserRole
from server.email.templates import TEMPLATE_CONFIGS, get_template_preview
from server.email.service import is_email_configured, send_email
from server.services.notifications import send_ai_copilot_feature_update, NOTIFICATION_RECIPIENTS

router = APIRouter(prefix="/email-templates", tags=["email-templates"])


def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.OWNER.value, UserRole.ADMIN.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


class TemplateInfo(BaseModel):
    id: str
    name: str
    description: str
    variables: List[str]
    subject: str


class TemplatePreviewRequest(BaseModel):
    template_type: str


class TestEmailRequest(BaseModel):
    template_type: str
    to_email: str


class EmailStatusResponse(BaseModel):
    configured: bool
    from_email: Optional[str] = None


@router.get("/status")
def get_email_status(
    current_user: User = Depends(require_admin)
) -> EmailStatusResponse:
    """Check if email service is configured."""
    import os
    configured = is_email_configured()
    from_email = os.getenv("RESEND_FROM_EMAIL") if configured else None
    
    return EmailStatusResponse(
        configured=configured,
        from_email=from_email
    )


@router.get("/templates")
def list_templates(
    current_user: User = Depends(require_admin)
) -> List[TemplateInfo]:
    """List all available email templates."""
    templates = []
    for template_id, config in TEMPLATE_CONFIGS.items():
        templates.append(TemplateInfo(
            id=template_id,
            name=config["name"],
            description=config["description"],
            variables=config["variables"],
            subject=config["subject"]
        ))
    return templates


@router.get("/templates/{template_type}/preview")
def preview_template(
    template_type: str,
    current_user: User = Depends(require_admin)
) -> dict:
    """Get a preview of an email template with sample data."""
    if template_type not in TEMPLATE_CONFIGS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_type}' not found"
        )
    
    preview_html = get_template_preview(template_type)
    if not preview_html:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate template preview"
        )
    
    config = TEMPLATE_CONFIGS[template_type]
    
    return {
        "template_type": template_type,
        "name": config["name"],
        "subject": config["subject"],
        "html": preview_html,
        "variables": config["variables"]
    }


@router.post("/test")
async def send_test_email(
    request: TestEmailRequest,
    current_user: User = Depends(require_admin)
) -> dict:
    """Send a test email using a specific template."""
    if not is_email_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email service is not configured. Please set RESEND_API_KEY."
        )
    
    if request.template_type not in TEMPLATE_CONFIGS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{request.template_type}' not found"
        )
    
    preview_html = get_template_preview(request.template_type)
    if not preview_html:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate template"
        )
    
    config = TEMPLATE_CONFIGS[request.template_type]
    subject = f"[TEST] {config['subject']}"
    
    result = await send_email(
        to=request.to_email,
        subject=subject,
        html_content=preview_html
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Failed to send email")
        )
    
    return {
        "success": True,
        "message": f"Test email sent to {request.to_email}",
        "template_type": request.template_type
    }


class FeatureUpdateRequest(BaseModel):
    emails: Optional[List[str]] = None
    author: str = "Predixen Team"


@router.post("/send-ai-copilot-update")
async def send_ai_copilot_update_emails(
    request: Optional[FeatureUpdateRequest] = None,
    current_user: User = Depends(require_admin)
) -> dict:
    """Send AI Copilot feature update emails to specified recipients or all notification recipients."""
    req = request if request else FeatureUpdateRequest()
    
    result = await send_ai_copilot_feature_update(
        to_emails=req.emails,
        author=req.author
    )
    
    if not result["success"] and "error" in result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["error"]
        )
    
    return {
        "success": result["success"],
        "sent_to": result["sent"],
        "failed": result["failed"],
        "message": result["message"]
    }
