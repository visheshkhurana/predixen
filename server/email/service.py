"""
Email service using Resend for transactional emails.
Handles invite emails, welcome emails, and other platform notifications.
Uses Replit Connectors API to fetch Resend credentials.
"""
import os
import resend
import asyncio
import httpx
from typing import Optional, Tuple
from datetime import datetime


# Cache for credentials (short-lived, refreshed each request cycle)
_cached_credentials: Optional[dict] = None


def _get_replit_token() -> Optional[str]:
    """Get the Replit authentication token for connector API."""
    repl_identity = os.getenv("REPL_IDENTITY")
    web_repl_renewal = os.getenv("WEB_REPL_RENEWAL")
    
    if repl_identity:
        return f"repl {repl_identity}"
    elif web_repl_renewal:
        return f"depl {web_repl_renewal}"
    return None


def _fetch_resend_credentials_sync() -> Optional[dict]:
    """
    Synchronously fetch Resend credentials from Replit Connectors API.
    Returns dict with api_key and from_email, or None if not configured.
    """
    global _cached_credentials
    
    # First check for direct environment variables (fallback)
    direct_api_key = os.getenv("RESEND_API_KEY")
    if direct_api_key:
        return {
            "api_key": direct_api_key,
            "from_email": os.getenv("RESEND_FROM_EMAIL", "noreply@predixen.ai")
        }
    
    # Try Replit Connectors API
    hostname = os.getenv("REPLIT_CONNECTORS_HOSTNAME")
    token = _get_replit_token()
    
    if not hostname or not token:
        return None
    
    try:
        import requests
        response = requests.get(
            f"https://{hostname}/api/v2/connection?include_secrets=true&connector_names=resend",
            headers={
                "Accept": "application/json",
                "X_REPLIT_TOKEN": token
            },
            timeout=10
        )
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        items = data.get("items", [])
        
        if not items:
            return None
        
        connection = items[0]
        settings = connection.get("settings", {})
        api_key = settings.get("api_key")
        from_email = settings.get("from_email", "noreply@predixen.ai")
        
        if not api_key:
            return None
        
        _cached_credentials = {
            "api_key": api_key,
            "from_email": from_email
        }
        return _cached_credentials
        
    except Exception as e:
        print(f"Error fetching Resend credentials: {e}")
        return None


def get_resend_credentials() -> Optional[dict]:
    """Get Resend API credentials (api_key and from_email)."""
    return _fetch_resend_credentials_sync()


def get_resend_api_key() -> Optional[str]:
    """Get Resend API key."""
    creds = get_resend_credentials()
    return creds.get("api_key") if creds else None


def get_from_email() -> str:
    """Get the default from email address for updates and notifications."""
    return "Nikita from Predixen <nikita@predixen.app>"


def get_transactional_from_email() -> str:
    """Get the transactional from email address for user-triggered emails (invites, shares, resets)."""
    env_override = os.getenv("RESEND_TRANSACTIONAL_FROM")
    return env_override or "Nikita from Predixen <nikita@predixen.app>"


def is_email_configured() -> bool:
    """Check if email service is properly configured."""
    creds = get_resend_credentials()
    return creds is not None and creds.get("api_key") is not None


def _send_email_sync(
    to: str,
    subject: str,
    html_content: str,
    from_email: Optional[str] = None,
    recipient_id: Optional[str] = None,
    campaign: Optional[str] = None,
    utm_params: Optional[dict] = None,
    headers: Optional[dict] = None,
    text_content: Optional[str] = None
) -> dict:
    """
    Synchronously send an email using Resend.
    This is run in a thread pool to avoid blocking the event loop.
    Automatically stores sent email in DB for tracking.
    """
    creds = get_resend_credentials()
    if not creds or not creds.get("api_key"):
        return {
            "success": False,
            "error": "Email service not configured. Please connect Resend integration."
        }
    
    resend.api_key = creds["api_key"]
    sender_email = from_email or "Predixen <kavibe8@predixen.app>"
    
    try:
        params = {
            "from": sender_email,
            "to": [to],
            "subject": subject,
            "html": html_content
        }
        if headers:
            params["headers"] = headers
        if text_content:
            params["text"] = text_content
        
        result = resend.Emails.send(params)
        email_id = result.get("id") if isinstance(result, dict) else getattr(result, "id", None)
        
        if email_id:
            try:
                from server.api.email_tracking import store_sent_email
                utm = utm_params or {}
                store_sent_email(
                    email_id=email_id,
                    to_email=to,
                    subject=subject,
                    from_email=sender_email,
                    recipient_id=recipient_id,
                    campaign=campaign,
                    utm_source=utm.get("utm_source"),
                    utm_medium=utm.get("utm_medium"),
                    utm_campaign=utm.get("utm_campaign"),
                    utm_content=utm.get("utm_content"),
                    utm_term=utm.get("utm_term")
                )
            except Exception as track_err:
                print(f"Tracking store warning: {track_err}")
        
        return {
            "success": True,
            "message_id": email_id,
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
    from_email: Optional[str] = None,
    recipient_id: Optional[str] = None,
    campaign: Optional[str] = None,
    utm_params: Optional[dict] = None
) -> dict:
    """
    Send an email using Resend (async wrapper).
    Runs the synchronous Resend SDK call in a thread pool to avoid blocking.
    
    Args:
        to: Recipient email address
        subject: Email subject
        html_content: HTML content of the email
        from_email: Optional sender email (defaults to configured from email)
        recipient_id: Optional unique ID for the recipient
        campaign: Optional campaign name for tracking
        utm_params: Optional dict with utm_source, utm_medium, utm_campaign, utm_content, utm_term
    
    Returns:
        dict with success status and message/error
    """
    return await asyncio.to_thread(
        _send_email_sync, to, subject, html_content, from_email,
        recipient_id, campaign, utm_params
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
    
    base_url = os.getenv("APP_BASE_URL", "https://predixen.app")
    invite_url = f"{base_url}/auth?invite={invite_token}"
    
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


async def send_platform_update_email(
    to_email: str,
    updates: list,
    app_url: str,
    template_html: Optional[str] = None
) -> dict:
    """
    Send a platform update email with recent changes.
    
    Args:
        to_email: Recipient email address
        updates: List of update items with title and description
        app_url: URL to the application
        template_html: Optional custom HTML template
    
    Returns:
        dict with success status and message/error
    """
    from server.email.templates import render_platform_update_template
    
    html_content = template_html or render_platform_update_template(
        updates=updates,
        app_url=app_url
    )
    
    subject = "Predixen Intelligence OS - New Features & Updates"
    
    return await send_email(to_email, subject, html_content)
