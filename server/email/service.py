"""
Email service using Resend for transactional emails.
Handles invite emails, welcome emails, and other platform notifications.
"""
import os
import resend
import asyncio
from typing import Optional
from datetime import datetime


def get_resend_api_key() -> Optional[str]:
    """Get Resend API key from environment."""
    return os.getenv("RESEND_API_KEY")


def get_from_email() -> str:
    """Get the default from email address."""
    return os.getenv("RESEND_FROM_EMAIL", "noreply@predixen.ai")


def is_email_configured() -> bool:
    """Check if email service is properly configured."""
    api_key = get_resend_api_key()
    return api_key is not None and len(api_key) > 0


def _send_email_sync(
    to: str,
    subject: str,
    html_content: str,
    from_email: Optional[str] = None
) -> dict:
    """
    Synchronously send an email using Resend.
    This is run in a thread pool to avoid blocking the event loop.
    """
    api_key = get_resend_api_key()
    if not api_key:
        return {
            "success": False,
            "error": "Email service not configured. Please set RESEND_API_KEY."
        }
    
    resend.api_key = api_key
    
    try:
        params = {
            "from": from_email or get_from_email(),
            "to": [to],
            "subject": subject,
            "html": html_content
        }
        
        result = resend.Emails.send(params)
        
        return {
            "success": True,
            "message_id": result.get("id") if isinstance(result, dict) else getattr(result, "id", None),
            "message": f"Email sent successfully to {to}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


async def send_email(
    to: str,
    subject: str,
    html_content: str,
    from_email: Optional[str] = None
) -> dict:
    """
    Send an email using Resend (async wrapper).
    Runs the synchronous Resend SDK call in a thread pool to avoid blocking.
    
    Args:
        to: Recipient email address
        subject: Email subject
        html_content: HTML content of the email
        from_email: Optional sender email (defaults to configured from email)
    
    Returns:
        dict with success status and message/error
    """
    return await asyncio.to_thread(
        _send_email_sync, to, subject, html_content, from_email
    )


async def send_invite_email(
    to_email: str,
    invite_token: str,
    role: str,
    invited_by_email: str,
    expires_at: datetime,
    early_access: bool = True,
    template_html: Optional[str] = None
) -> dict:
    """
    Send an invitation email to a new user.
    
    Args:
        to_email: Recipient email address
        invite_token: Unique invite token for registration
        role: The role being offered (viewer, analyst, admin, owner)
        invited_by_email: Email of the person who sent the invite
        expires_at: When the invite expires
        early_access: Whether to use early access messaging (default True)
        template_html: Optional custom HTML template
    
    Returns:
        dict with success status and message/error
    """
    from server.email.templates import render_invite_template
    
    base_url = os.getenv("APP_BASE_URL", "https://predixen.ai")
    invite_url = f"{base_url}/register?token={invite_token}"
    
    html_content = template_html or render_invite_template(
        invite_url=invite_url,
        role=role,
        invited_by_email=invited_by_email,
        expires_at=expires_at,
        early_access=early_access
    )
    
    subject = "You're invited to Predixen Early Access" if early_access else "You've been invited to join Predixen Intelligence OS"
    
    return await send_email(to_email, subject, html_content)


async def send_welcome_email(
    to_email: str,
    user_name: Optional[str] = None,
    template_html: Optional[str] = None
) -> dict:
    """
    Send a welcome email to a newly registered user.
    
    Args:
        to_email: Recipient email address
        user_name: Optional user's name
        template_html: Optional custom HTML template
    
    Returns:
        dict with success status and message/error
    """
    from server.email.templates import render_welcome_template
    
    base_url = os.getenv("APP_BASE_URL", "https://predixen.ai")
    
    html_content = template_html or render_welcome_template(
        user_name=user_name,
        login_url=f"{base_url}/login"
    )
    
    subject = "Welcome to Predixen Intelligence OS"
    
    return await send_email(to_email, subject, html_content)


async def send_password_reset_email(
    to_email: str,
    reset_token: str,
    template_html: Optional[str] = None
) -> dict:
    """
    Send a password reset email.
    
    Args:
        to_email: Recipient email address
        reset_token: Password reset token
        template_html: Optional custom HTML template
    
    Returns:
        dict with success status and message/error
    """
    from server.email.templates import render_password_reset_template
    
    base_url = os.getenv("APP_BASE_URL", "https://predixen.ai")
    reset_url = f"{base_url}/reset-password?token={reset_token}"
    
    html_content = template_html or render_password_reset_template(
        reset_url=reset_url
    )
    
    subject = "Reset Your Predixen Password"
    
    return await send_email(to_email, subject, html_content)
