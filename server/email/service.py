"""
Email service using Resend for transactional emails.
Handles invite emails, welcome emails, and other platform notifications.
Uses Replit Connectors API to fetch Resend credentials.
Also includes Slack webhook notifications for signup events.

Platform/transactional emails use only founderconsole.* domains.
Outreach/update emails rotate across all verified domains (see send_update_emails.py).
"""
import os
import resend
import asyncio
import httpx
import logging
import random
from typing import Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


PLATFORM_DOMAINS = [
    "founderconsole.ai",
    "founderconsole.co",
    "founderconsole.com",
    "founderconsole.in",
    "founderconsole.info",
    "founderconsole.net",
    "founderconsole.shop",
    "updates.founderconsole.ai",
]

_platform_domain_counter = 0

_slack_logger = logging.getLogger("slack_notifications")


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
            "from_email": os.getenv("RESEND_FROM_EMAIL", "noreply@founderconsole.ai")
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
        from_email = settings.get("from_email", "noreply@founderconsole.ai")
        
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


def _get_next_platform_domain() -> str:
    """Get the next founderconsole domain in rotation for platform emails."""
    global _platform_domain_counter
    domain = PLATFORM_DOMAINS[_platform_domain_counter % len(PLATFORM_DOMAINS)]
    _platform_domain_counter += 1
    return domain


def get_from_email() -> str:
    """Get a from email address for platform notifications, rotating across founderconsole.* domains."""
    domain = _get_next_platform_domain()
    return f"FounderConsole <noreply@{domain}>"


def get_transactional_from_email() -> str:
    """Get a from email address for transactional emails (invites, resets, etc.), rotating across founderconsole.* domains."""
    env_override = os.getenv("RESEND_TRANSACTIONAL_FROM")
    if env_override:
        return env_override
    domain = _get_next_platform_domain()
    return f"FounderConsole <noreply@{domain}>"


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
    verified_from = creds.get("from_email", "noreply@founderconsole.ai")
    sender_email = from_email or f"FounderConsole <{verified_from}>"
    
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
    utm_params: Optional[dict] = None,
    headers: Optional[dict] = None,
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
        recipient_id, campaign, utm_params, headers
    )


def deliver_lifecycle_email(
    to: str,
    subject: str,
    html_content: str,
    *,
    category: str,
    template: str,
    campaign: Optional[str] = None,
    user_id: Optional[int] = None,
    from_email: Optional[str] = None,
    due_at: Optional[datetime] = None,
    db=None,
) -> dict:
    """Classified send. category is required; it is never inferred.

    transactional (password_reset, email_verification, receipt) skips the cap,
    opt-out, hold expiry, and List-Unsubscribe. lifecycle, digest, and briefing
    are covered by both the cap and RFC 8058. One token is signed per covered
    send and used for the footer link and the List-Unsubscribe header.
    LIFECYCLE_GUARDS=off skips opt-out, the cap, and expiry. Headers stay.
    """
    from server.core.db import SessionLocal
    from server.email.lifecycle_guard import (
        CATEGORY_TRANSACTIONAL,
        COVERED_CATEGORIES,
        assert_template,
        evaluate_for_user,
        guard_enabled,
        is_past_max_hold,
        list_unsubscribe_headers,
        record_lifecycle_event,
        stamp_unsubscribe_footer,
        unsubscribe_links,
        user_id_for_email,
    )

    assert_template(category, template)
    tracked_as = campaign or template

    if category == CATEGORY_TRANSACTIONAL:
        return _send_email_sync(
            to,
            subject,
            html_content,
            from_email=from_email,
            recipient_id=str(user_id) if user_id is not None else None,
            campaign=tracked_as,
        )

    if category not in COVERED_CATEGORIES:
        raise ValueError(f"unknown email category: {category}")

    owns_session = db is None
    if owns_session:
        db = SessionLocal()
    try:
        uid = user_id if user_id is not None else user_id_for_email(db, to)
        if uid is None:
            logger.info(
                "lifecycle email skipped reason=unknown_user category=%s template=%s",
                category,
                template,
            )
            return {"success": False, "skipped": True, "reason": "unknown_user"}

        effective_due = due_at or datetime.utcnow()
        try:
            if guard_enabled() and is_past_max_hold(template, effective_due):
                record_lifecycle_event(
                    db,
                    uid,
                    category,
                    tracked_as,
                    "dropped_expired",
                    "expired",
                )
                return {"success": False, "skipped": True, "dropped": True, "reason": "expired"}
            decision = evaluate_for_user(db, uid)
        except Exception:
            logger.exception(
                "lifecycle guard failed closed user_id=%s category=%s template=%s",
                uid,
                category,
                template,
            )
            return {"success": False, "skipped": True, "reason": "guard_error"}

        if not decision.allow:
            record_lifecycle_event(
                db,
                uid,
                category,
                tracked_as,
                f"skipped_{decision.reason}",
                decision.reason,
            )
            return {"success": False, "skipped": True, "reason": decision.reason}

        links = unsubscribe_links(uid)
        stamped = stamp_unsubscribe_footer(html_content, links.page_url)
        result = _send_email_sync(
            to,
            subject,
            stamped,
            from_email=from_email,
            recipient_id=str(uid),
            campaign=tracked_as,
            headers=list_unsubscribe_headers(links),
        )
        if result.get("success"):
            record_lifecycle_event(db, uid, category, tracked_as, "sent", None)
        else:
            record_lifecycle_event(
                db,
                uid,
                category,
                tracked_as,
                "failed",
                str(result.get("error") or "")[:120] or None,
            )
        return result
    finally:
        if owns_session:
            db.close()


async def send_lifecycle_email(
    to: str,
    subject: str,
    html_content: str,
    *,
    category: str,
    template: str,
    campaign: Optional[str] = None,
    user_id: Optional[int] = None,
    from_email: Optional[str] = None,
    due_at: Optional[datetime] = None,
) -> dict:
    """Async wrapper around the classified choke point."""
    return await asyncio.to_thread(
        lambda: deliver_lifecycle_email(
            to,
            subject,
            html_content,
            category=category,
            template=template,
            campaign=campaign,
            user_id=user_id,
            from_email=from_email,
            due_at=due_at,
        )
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
    
    base_url = os.getenv("APP_BASE_URL", "https://founderconsole.ai")
    invite_url = f"{base_url}/auth?invite={invite_token}"
    
    html_content = template_html or render_invite_template(
        invite_url=invite_url,
        role=role,
        invited_by_email=invited_by_email,
        expires_at=expires_at,
        early_access=early_access
    )
    
    subject = "You're invited to FounderConsole Early Access" if early_access else "You've been invited to join FounderConsole"
    
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
    
    base_url = os.getenv("APP_BASE_URL", "https://founderconsole.ai")
    
    html_content = template_html or render_welcome_template(
        user_name=user_name,
        login_url=f"{base_url}/login"
    )
    
    subject = "Welcome to FounderConsole"
    
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
    
    base_url = os.getenv("APP_BASE_URL", "https://founderconsole.ai")
    reset_url = f"{base_url}/reset-password?token={reset_token}"
    
    html_content = template_html or render_password_reset_template(
        reset_url=reset_url
    )
    
    subject = "Reset Your FounderConsole Password"

    return await send_lifecycle_email(
        to_email,
        subject,
        html_content,
        category="transactional",
        template="password_reset",
    )


async def send_email_verification(
    to_email: str,
    verification_token: str,
    template_html: Optional[str] = None
) -> dict:
    from server.email.templates import render_email_verification_template
    
    base_url = os.getenv("APP_BASE_URL", "https://founderconsole.ai")
    verify_url = f"{base_url}/verify-email?token={verification_token}"
    
    html_content = template_html or render_email_verification_template(
        verify_url=verify_url
    )
    
    subject = "Verify Your FounderConsole Email"

    return await send_lifecycle_email(
        to_email,
        subject,
        html_content,
        category="transactional",
        template="email_verification",
    )


async def send_receipt_email(
    to_email: str,
    html_content: str,
    *,
    subject: str = "Your FounderConsole receipt",
) -> dict:
    """Payment receipt. Transactional: skips the cap and unsubscribe."""
    return await send_lifecycle_email(
        to_email,
        subject,
        html_content,
        category="transactional",
        template="receipt",
        campaign="receipt",
    )


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
    
    subject = "FounderConsole - New Features & Updates"

    from server.core.db import SessionLocal
    from server.email.lifecycle_guard import prepare_bulk_send

    db = SessionLocal()
    try:
        prepared = prepare_bulk_send(db, to_email, html_content)
    finally:
        db.close()
    if prepared is None:
        return {"success": False, "skipped": True, "error": "Recipient opted out of email"}

    return await send_email(to_email, subject, prepared.html, headers=prepared.headers or None)


async def send_slack_signup_notification(
    email: str,
    name: Optional[str] = None,
    signup_method: str = "Email",
    user_id: Optional[int] = None,
):
    webhook_url = os.getenv("SLACK_SIGNUP_WEBHOOK_URL")
    if not webhook_url:
        _slack_logger.debug("SLACK_SIGNUP_WEBHOOK_URL not set, skipping notification")
        return

    timestamp = datetime.utcnow().strftime("%B %d, %Y at %H:%M UTC")
    display_name = name or "Not provided"
    profile_link = f"https://founderconsole.ai/admin/users/{user_id}" if user_id else "N/A"

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "\U0001f389 New Signup on FounderConsole!", "emoji": True},
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Email:*\n{email}"},
                {"type": "mrkdwn", "text": f"*Name:*\n{display_name}"},
                {"type": "mrkdwn", "text": f"*Method:*\n{signup_method}"},
                {"type": "mrkdwn", "text": f"*Time:*\n{timestamp}"},
            ],
        },
    ]

    if user_id:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Profile:* <{profile_link}|View in Admin Panel>"},
        })

    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": "Sent from FounderConsole Signup Tracker"}],
    })

    payload = {"blocks": blocks, "text": f"New signup: {email} via {signup_method}"}

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(webhook_url, json=payload)
            resp.raise_for_status()
        _slack_logger.info(f"Slack signup notification sent for {email}")
    except Exception as exc:
        _slack_logger.warning(f"Failed to send Slack signup notification: {exc}")
