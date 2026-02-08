"""
Notification service for sending email updates about platform changes.
Uses Resend integration for email delivery.
"""

import os
import re
import asyncio
import httpx
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path


NOTIFICATION_RECIPIENTS = [
    "nikita@predixen.ai",
    "vysheshk@gmail.com",
    "nikita.luther@gmail.com",
    "nikitafl2024@gmail.com"
]

# Sender rotation counter (persisted in memory, resets on restart)
_sender_counter = {"value": 0}


def get_next_sender_email() -> str:
    """Get the next sender email in rotation (new1@, new2@, new3@, etc.)."""
    _sender_counter["value"] += 1
    return f"Predixen <new{_sender_counter['value']}@predixen.app>"


def get_current_sender_count() -> int:
    """Get the current sender counter value."""
    return _sender_counter["value"]


async def get_resend_credentials() -> dict:
    """Get Resend API credentials from Replit connector."""
    hostname = os.environ.get("REPLIT_CONNECTORS_HOSTNAME")
    repl_identity = os.environ.get("REPL_IDENTITY")
    web_repl_renewal = os.environ.get("WEB_REPL_RENEWAL")
    
    if repl_identity:
        x_replit_token = f"repl {repl_identity}"
    elif web_repl_renewal:
        x_replit_token = f"depl {web_repl_renewal}"
    else:
        raise ValueError("No Replit token found for authentication")
    
    if not hostname:
        raise ValueError("REPLIT_CONNECTORS_HOSTNAME not configured")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://{hostname}/api/v2/connection?include_secrets=true&connector_names=resend",
            headers={
                "Accept": "application/json",
                "X_REPLIT_TOKEN": x_replit_token
            }
        )
        data = response.json()
        
    connection = data.get("items", [None])[0]
    if not connection or not connection.get("settings", {}).get("api_key"):
        raise ValueError("Resend not connected")
    
    return {
        "api_key": connection["settings"]["api_key"],
        "from_email": connection["settings"].get("from_email", "noreply@predixen.ai")
    }


async def send_feature_notification(
    feature_name: str,
    description: str,
    changes: List[str],
    category: str = "Feature Update",
    author: Optional[str] = None,
    from_email: str = "Predixen Updates <new2@predixen.app>"
) -> bool:
    """
    Send email notification about a new feature or change.
    
    Args:
        feature_name: Name of the feature or change
        description: Detailed description of what was changed
        changes: List of specific changes made
        category: Type of update (Feature Update, Bug Fix, Enhancement, etc.)
        author: Who made the change (optional)
    
    Returns:
        True if email was sent successfully, False otherwise
    """
    try:
        credentials = await get_resend_credentials()
        
        timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        
        changes_html = "".join([f"<li style='margin-bottom: 8px;'>{change}</li>" for change in changes])
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f5f5f5; margin: 0; padding: 20px;">
    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); overflow: hidden;">
        <div style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); padding: 24px 32px;">
            <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 600;">Predixen Intelligence OS</h1>
            <p style="color: rgba(255,255,255,0.9); margin: 8px 0 0 0; font-size: 14px;">{category}</p>
        </div>
        
        <div style="padding: 32px;">
            <div style="background-color: #f0fdf4; border-left: 4px solid #22c55e; padding: 16px; margin-bottom: 24px; border-radius: 0 4px 4px 0;">
                <h2 style="color: #166534; margin: 0 0 8px 0; font-size: 18px;">{feature_name}</h2>
                <p style="color: #15803d; margin: 0; font-size: 14px;">Deployed on {timestamp}</p>
            </div>
            
            <h3 style="color: #1f2937; font-size: 16px; margin: 0 0 12px 0;">Description</h3>
            <p style="color: #4b5563; line-height: 1.6; margin: 0 0 24px 0;">{description}</p>
            
            <h3 style="color: #1f2937; font-size: 16px; margin: 0 0 12px 0;">Changes Made</h3>
            <ul style="color: #4b5563; line-height: 1.6; margin: 0 0 24px 0; padding-left: 20px;">
                {changes_html}
            </ul>
            
            {f'<p style="color: #6b7280; font-size: 13px; margin: 24px 0 0 0;"><strong>Author:</strong> {author}</p>' if author else ''}
        </div>
        
        <div style="background-color: #f9fafb; padding: 20px 32px; border-top: 1px solid #e5e7eb;">
            <p style="color: #6b7280; font-size: 12px; margin: 0; text-align: center;">
                This is an automated notification from Predixen Intelligence OS.<br>
                <a href="https://predixen.ai" style="color: #6366f1; text-decoration: none;">Visit Dashboard</a>
            </p>
        </div>
    </div>
</body>
</html>
"""
        
        text_content = f"""
{category}: {feature_name}
Deployed on {timestamp}

Description:
{description}

Changes Made:
{chr(10).join(['- ' + change for change in changes])}

{f'Author: {author}' if author else ''}

---
This is an automated notification from Predixen Intelligence OS.
"""
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {credentials['api_key']}",
                    "Content-Type": "application/json"
                },
                json={
                    "from": from_email,
                    "to": NOTIFICATION_RECIPIENTS,
                    "subject": f"[Predixen] {category}: {feature_name}",
                    "html": html_content,
                    "text": text_content
                }
            )
            
            if response.status_code in (200, 201):
                print(f"Feature notification sent successfully: {feature_name}")
                return True
            else:
                print(f"Failed to send notification: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        print(f"Error sending feature notification: {e}")
        return False


async def send_deployment_notification(
    environment: str = "Production",
    version: Optional[str] = None,
    changes_summary: Optional[str] = None
) -> bool:
    """Send notification about a deployment."""
    return await send_feature_notification(
        feature_name=f"Deployment to {environment}",
        description=changes_summary or "A new version has been deployed to the platform.",
        changes=[f"Version: {version}"] if version else ["Latest changes deployed"],
        category="Deployment"
    )


async def send_ai_copilot_feature_update(
    to_emails: Optional[List[str]] = None,
    author: str = "Predixen Team"
) -> dict:
    """
    Send feature update email about the new AI Copilot features with click-to-test button.
    
    Args:
        to_emails: List of email addresses (defaults to NOTIFICATION_RECIPIENTS)
        author: Name of the person sending the update
    
    Returns:
        Dict with success status and list of sent/failed emails
    """
    import os
    
    if to_emails is None:
        to_emails = NOTIFICATION_RECIPIENTS
    
    try:
        credentials = await get_resend_credentials()
        base_url = os.getenv("APP_BASE_URL", "https://predixen.app")
        timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #0f172a; margin: 0; padding: 40px 20px;">
    <div style="max-width: 640px; margin: 0 auto;">
        <div style="text-align: center; margin-bottom: 24px;">
            <div style="display: inline-block; width: 48px; height: 48px; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); border-radius: 12px; text-align: center; line-height: 48px; color: #ffffff; font-weight: 700; font-size: 24px;">P</div>
        </div>
        
        <div style="background-color: #1e293b; border-radius: 16px; overflow: hidden; border: 1px solid #334155;">
            <div style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); padding: 32px; text-align: center;">
                <div style="display: inline-block; background-color: rgba(255,255,255,0.2); padding: 6px 16px; border-radius: 20px; margin-bottom: 16px;">
                    <span style="color: #ffffff; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 1.5px;">New Feature Release</span>
                </div>
                <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 700; line-height: 1.2;">Real-Time AI Simulation Copilot</h1>
                <p style="color: rgba(255,255,255,0.8); margin: 12px 0 0 0; font-size: 14px;">Deployed on {timestamp}</p>
            </div>
            
            <div style="padding: 32px;">
                <p style="color: #e2e8f0; font-size: 16px; line-height: 1.7; margin: 0 0 24px 0;">
                    We've just shipped a major upgrade to the simulation experience. Now, as you adjust scenario parameters, an <strong style="color: #a5b4fc;">AI copilot provides real-time guidance</strong> explaining exactly how each change impacts your runway, survival probability, and cash position.
                </p>
                
                <div style="background-color: #0f172a; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
                    <h3 style="color: #22c55e; font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin: 0 0 16px 0;">What's New</h3>
                    
                    <div style="margin-bottom: 16px; padding-left: 24px; border-left: 3px solid #6366f1;">
                        <h4 style="color: #ffffff; font-size: 16px; font-weight: 600; margin: 0 0 6px 0;">Context-Aware AI Guidance</h4>
                        <p style="color: #94a3b8; font-size: 14px; line-height: 1.6; margin: 0;">
                            As you adjust pricing, growth, burn rate, margins, churn, or CAC sliders, the AI instantly explains the impact on your key metrics with high/medium/low severity indicators.
                        </p>
                    </div>
                    
                    <div style="margin-bottom: 16px; padding-left: 24px; border-left: 3px solid #8b5cf6;">
                        <h4 style="color: #ffffff; font-size: 16px; font-weight: 600; margin: 0 0 6px 0;">Narrative Result Summaries</h4>
                        <p style="color: #94a3b8; font-size: 14px; line-height: 1.6; margin: 0;">
                            After running simulations, get plain-language explanations of your results including health status, top 5 key drivers ranked by impact, and actionable recommendations.
                        </p>
                    </div>
                    
                    <div style="padding-left: 24px; border-left: 3px solid #0ea5e9;">
                        <h4 style="color: #ffffff; font-size: 16px; font-weight: 600; margin: 0 0 6px 0;">Smart Debouncing</h4>
                        <p style="color: #94a3b8; font-size: 14px; line-height: 1.6; margin: 0;">
                            AI calls are optimized with 300ms debounce so you get smooth slider interactions without API overload while still getting instant feedback.
                        </p>
                    </div>
                </div>
                
                <div style="text-align: center; margin: 32px 0;">
                    <a href="{base_url}/scenarios" style="display: inline-block; padding: 16px 48px; font-size: 16px; font-weight: 600; color: #ffffff; text-decoration: none; background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); border-radius: 10px; box-shadow: 0 4px 12px rgba(34, 197, 94, 0.3);">Test It Now</a>
                </div>
                
                <p style="text-align: center; color: #64748b; font-size: 13px; margin: 0;">
                    Click the button above to open the Scenarios page and try the new AI copilot.
                </p>
            </div>
            
            <div style="background-color: #0f172a; padding: 24px 32px; border-top: 1px solid #334155;">
                <h4 style="color: #94a3b8; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin: 0 0 12px 0;">How to Test</h4>
                <ol style="color: #e2e8f0; font-size: 14px; line-height: 1.8; margin: 0; padding-left: 20px;">
                    <li>Go to <strong>Scenarios</strong> page</li>
                    <li>Click <strong>"New Scenario"</strong> or edit an existing one</li>
                    <li>Adjust any parameter slider (pricing, growth, burn, etc.)</li>
                    <li>Watch the AI guidance panel update in real-time</li>
                    <li>Run a simulation and see the AI narrative summary</li>
                </ol>
            </div>
            
            <div style="padding: 20px 32px; border-top: 1px solid #334155; text-align: center;">
                <p style="color: #64748b; font-size: 12px; margin: 0;">
                    Questions or feedback? Reply directly to this email.<br>
                    <span style="color: #6366f1;">— {author}</span>
                </p>
            </div>
        </div>
        
        <div style="text-align: center; margin-top: 24px;">
            <p style="color: #475569; font-size: 11px; margin: 0;">
                Predixen Intelligence OS • Automated Feature Update
            </p>
        </div>
    </div>
</body>
</html>
"""
        
        text_content = f"""
REAL-TIME AI SIMULATION COPILOT
New Feature Release - Deployed on {timestamp}

We've just shipped a major upgrade to the simulation experience. Now, as you adjust scenario parameters, an AI copilot provides real-time guidance explaining exactly how each change impacts your runway, survival probability, and cash position.

WHAT'S NEW:

1. Context-Aware AI Guidance
   As you adjust pricing, growth, burn rate, margins, churn, or CAC sliders, the AI instantly explains the impact on your key metrics with high/medium/low severity indicators.

2. Narrative Result Summaries
   After running simulations, get plain-language explanations of your results including health status, top 5 key drivers ranked by impact, and actionable recommendations.

3. Smart Debouncing
   AI calls are optimized with 300ms debounce so you get smooth slider interactions without API overload while still getting instant feedback.

HOW TO TEST:
1. Go to Scenarios page
2. Click "New Scenario" or edit an existing one
3. Adjust any parameter slider (pricing, growth, burn, etc.)
4. Watch the AI guidance panel update in real-time
5. Run a simulation and see the AI narrative summary

Test it now: {base_url}/scenarios

Questions or feedback? Reply directly to this email.
— {author}

---
Predixen Intelligence OS • Automated Feature Update
"""
        
        sent = []
        failed = []
        
        async with httpx.AsyncClient() as client:
            for email in to_emails:
                response = await client.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {credentials['api_key']}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "from": "Predixen Updates <updates@predixen.app>",
                        "to": [email],
                        "subject": "[Predixen] New Feature: Real-Time AI Simulation Copilot",
                        "html": html_content,
                        "text": text_content
                    }
                )
                
                if response.status_code in (200, 201):
                    sent.append(email)
                    print(f"Feature update sent to: {email}")
                else:
                    failed.append(email)
                    print(f"Failed to send to {email}: {response.status_code} - {response.text}")
        
        return {
            "success": len(failed) == 0,
            "sent": sent,
            "failed": failed,
            "message": f"Sent {len(sent)} email(s), {len(failed)} failed"
        }
        
    except Exception as e:
        print(f"Error sending AI copilot feature update: {e}")
        return {
            "success": False,
            "sent": [],
            "failed": to_emails or [],
            "error": str(e)
        }


async def send_beta_invite_email(
    to_emails: List[str],
    invited_by: str = "Predixen Team"
) -> dict:
    """
    Send beta test invitation emails with click-to-join functionality.
    
    Args:
        to_emails: List of email addresses to invite
        invited_by: Name/email of the person sending the invite
    
    Returns:
        Dict with success status and list of sent/failed emails
    """
    import os
    
    try:
        credentials = await get_resend_credentials()
        base_url = os.getenv("APP_BASE_URL", "https://predixen.app")
        timestamp = datetime.now().strftime("%B %d, %Y")
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f5f5f5; margin: 0; padding: 20px;">
    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 16px rgba(0,0,0,0.1); overflow: hidden;">
        <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 32px; text-align: center;">
            <div style="display: inline-block; width: 48px; height: 48px; background-color: #0ea5e9; border-radius: 12px; text-align: center; line-height: 48px; color: #ffffff; font-weight: 700; font-size: 24px; margin-bottom: 16px;">P</div>
            <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 700;">Predixen Intelligence OS</h1>
            <p style="color: #94a3b8; margin: 8px 0 0 0; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Beta Test Invitation</p>
        </div>
        
        <div style="padding: 40px;">
            <div style="text-align: center; margin-bottom: 32px;">
                <span style="display: inline-block; background-color: #fef3c7; color: #b45309; padding: 6px 16px; border-radius: 20px; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">Exclusive Access</span>
            </div>
            
            <h2 style="color: #0f172a; margin: 0 0 16px 0; font-size: 24px; font-weight: 600; text-align: center;">You're Invited to Test Predixen</h2>
            
            <p style="font-size: 16px; color: #475569; line-height: 1.7; margin: 0 0 24px 0; text-align: center;">
                <strong style="color: #0ea5e9;">{invited_by}</strong> has invited you to experience the future of startup financial intelligence.
            </p>
            
            <div style="background-color: #f8fafc; border-radius: 8px; padding: 24px; margin-bottom: 32px;">
                <p style="margin: 0 0 12px 0; font-size: 12px; font-weight: 600; color: #0f172a; text-transform: uppercase; letter-spacing: 1px;">What You'll Get Access To:</p>
                <ul style="margin: 0; padding-left: 20px; color: #475569; font-size: 14px; line-height: 1.8;">
                    <li>AI-powered financial document extraction</li>
                    <li>Monte Carlo simulations for runway forecasting</li>
                    <li>Sensitivity analysis with tornado charts</li>
                    <li>Smart decision recommendations ranked by survival probability</li>
                    <li>Multi-LLM copilot for financial questions</li>
                </ul>
            </div>
            
            <div style="text-align: center; margin: 32px 0;">
                <a href="{base_url}/auth" style="display: inline-block; padding: 16px 48px; font-size: 16px; font-weight: 600; color: #ffffff; text-decoration: none; background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%); border-radius: 10px; box-shadow: 0 4px 12px rgba(14, 165, 233, 0.3);">Start Testing Now</a>
            </div>
            
            <p style="text-align: center; color: #94a3b8; font-size: 13px; margin: 24px 0 0 0;">
                Click the button above to create your account and start exploring.
            </p>
        </div>
        
        <div style="background-color: #f8fafc; padding: 24px; text-align: center; border-top: 1px solid #e2e8f0;">
            <p style="margin: 0 0 4px 0; font-size: 14px; font-weight: 600; color: #0f172a;">Predixen</p>
            <p style="margin: 0; font-size: 12px; color: #64748b;">AI-Powered Financial Intelligence for Startups</p>
            <p style="margin: 12px 0 0 0; font-size: 11px; color: #94a3b8;">Sent on {timestamp}</p>
        </div>
    </div>
</body>
</html>
"""
        
        sent = []
        failed = []
        
        async with httpx.AsyncClient() as client:
            for email in to_emails:
                response = await client.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {credentials['api_key']}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "from": "Predixen <hello@predixen.app>",
                        "to": [email],
                        "subject": "You're Invited to Test Predixen Intelligence OS",
                        "html": html_content
                    }
                )
                
                if response.status_code in (200, 201):
                    sent.append(email)
                else:
                    failed.append(email)
        
        return {
            "success": len(failed) == 0,
            "sent": sent,
            "failed": failed,
            "message": f"Sent {len(sent)} invite(s), {len(failed)} failed"
        }
        
    except Exception as e:
        print(f"Error sending beta invites: {e}")
        return {
            "success": False,
            "sent": [],
            "failed": to_emails,
            "error": str(e)
        }


async def send_early_member_invite(
    to_emails: Optional[List[str]] = None,
    invited_by: str = "Nikita Luther, Founder"
) -> dict:
    """
    Send early member invitation emails for exclusive platform access.
    
    Args:
        to_emails: List of email addresses to invite (defaults to NOTIFICATION_RECIPIENTS)
        invited_by: Name of the person sending the invite
    
    Returns:
        Dict with success status and list of sent/failed emails
    """
    import os
    
    if to_emails is None:
        to_emails = NOTIFICATION_RECIPIENTS
    
    try:
        credentials = await get_resend_credentials()
        base_url = os.getenv("APP_BASE_URL", "https://predixen.app")
        timestamp = datetime.now().strftime("%B %d, %Y")
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #0f172a; margin: 0; padding: 40px 20px;">
    <div style="max-width: 640px; margin: 0 auto;">
        <div style="text-align: center; margin-bottom: 32px;">
            <div style="display: inline-block; width: 56px; height: 56px; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); border-radius: 14px; text-align: center; line-height: 56px; color: #ffffff; font-weight: 700; font-size: 28px;">P</div>
        </div>
        
        <div style="background-color: #1e293b; border-radius: 16px; overflow: hidden; border: 1px solid #334155;">
            <div style="padding: 40px 32px; text-align: center;">
                <div style="display: inline-block; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); padding: 6px 16px; border-radius: 20px; margin-bottom: 24px;">
                    <span style="color: #ffffff; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 1.5px;">Early Access</span>
                </div>
                
                <h1 style="color: #ffffff; margin: 0 0 16px 0; font-size: 32px; font-weight: 700; line-height: 1.2;">You're One of the First</h1>
                
                <p style="color: #94a3b8; font-size: 18px; line-height: 1.6; margin: 0 0 16px 0;">
                    Welcome to the founding circle of <span style="color: #a5b4fc;">Predixen Intelligence OS</span>
                </p>
                
                <p style="color: #e2e8f0; font-size: 16px; line-height: 1.6; margin: 0 0 32px 0;">
                    The <strong>AI-powered decision simulator</strong> that helps startup founders make better choices by running thousands of "what-if" scenarios in seconds.
                </p>
            </div>
            
            <!-- Feature 1: Decision Advisor -->
            <div style="padding: 0 32px 32px 32px;">
                <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border-radius: 12px; overflow: hidden; border: 1px solid #334155;">
                    <div style="background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); padding: 32px; text-align: center;">
                        <div style="font-size: 48px; margin-bottom: 8px;">&#x1F9E0;</div>
                        <div style="color: #ffffff; font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">AI-Powered</div>
                    </div>
                    <div style="padding: 20px;">
                        <div style="display: inline-block; background-color: #22c55e; padding: 4px 10px; border-radius: 4px; margin-bottom: 12px;">
                            <span style="color: #ffffff; font-size: 10px; font-weight: 600; text-transform: uppercase;">NEW</span>
                        </div>
                        <h3 style="color: #ffffff; margin: 0 0 8px 0; font-size: 18px; font-weight: 600;">AI Decision Advisor</h3>
                        <p style="color: #94a3b8; font-size: 14px; line-height: 1.6; margin: 0;">
                            Ask questions like <em>"How can I extend my runway by 6 months?"</em> and get actionable recommendations backed by probability simulations. The AI analyzes your options, runs Monte Carlo scenarios, and tells you exactly what to do with confidence levels.
                        </p>
                    </div>
                </div>
            </div>
            
            <!-- Feature 2: Scenario Simulator -->
            <div style="padding: 0 32px 32px 32px;">
                <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border-radius: 12px; overflow: hidden; border: 1px solid #334155;">
                    <div style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); padding: 32px; text-align: center;">
                        <div style="font-size: 48px; margin-bottom: 8px;">&#x1F4CA;</div>
                        <div style="color: #ffffff; font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">10,000+ Simulations</div>
                    </div>
                    <div style="padding: 20px;">
                        <h3 style="color: #ffffff; margin: 0 0 8px 0; font-size: 18px; font-weight: 600;">Scenario Simulator</h3>
                        <p style="color: #94a3b8; font-size: 14px; line-height: 1.6; margin: 0;">
                            Run 10,000+ simulations to see P10/P50/P90 outcomes for runway, survival probability, and cash position. Compare "reduce burn by 20%" vs "raise a bridge round" vs "freeze hiring" — all in one view with sensitivity analysis.
                        </p>
                    </div>
                </div>
            </div>
            
            <!-- Feature 3: Multi-Agent Copilot -->
            <div style="padding: 0 32px 32px 32px;">
                <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border-radius: 12px; overflow: hidden; border: 1px solid #334155;">
                    <div style="background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%); padding: 32px; text-align: center;">
                        <div style="font-size: 48px; margin-bottom: 8px;">&#x1F916;</div>
                        <div style="color: #ffffff; font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">4 AI Agents</div>
                    </div>
                    <div style="padding: 20px;">
                        <h3 style="color: #ffffff; margin: 0 0 8px 0; font-size: 18px; font-weight: 600;">Multi-Agent AI Copilot</h3>
                        <p style="color: #94a3b8; font-size: 14px; line-height: 1.6; margin: 0;">
                            Four specialized AI agents work together: <strong>CFO Agent</strong> (financial analysis), <strong>Market Agent</strong> (competitive intelligence), <strong>Strategy Agent</strong> (growth planning), and <strong>Decision Advisor</strong> (actionable recommendations). Each uses the best AI model for its task.
                        </p>
                    </div>
                </div>
            </div>
            
            <!-- What You Get -->
            <div style="padding: 0 32px 32px 32px;">
                <div style="background-color: #0f172a; border-radius: 12px; padding: 24px; text-align: left;">
                    <p style="color: #6366f1; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin: 0 0 16px 0;">As an early member, you get:</p>
                    
                    <div style="margin-bottom: 12px;">
                        <span style="color: #22c55e; margin-right: 8px;">&#10003;</span>
                        <span style="color: #e2e8f0; font-size: 14px;"><strong>Full platform access</strong> — All AI features, unlimited simulations</span>
                    </div>
                    <div style="margin-bottom: 12px;">
                        <span style="color: #22c55e; margin-right: 8px;">&#10003;</span>
                        <span style="color: #e2e8f0; font-size: 14px;"><strong>Decision simulations</strong> — See outcomes before committing</span>
                    </div>
                    <div style="margin-bottom: 12px;">
                        <span style="color: #22c55e; margin-right: 8px;">&#10003;</span>
                        <span style="color: #e2e8f0; font-size: 14px;"><strong>AI document extraction</strong> — Upload financials, get insights instantly</span>
                    </div>
                    <div style="margin-bottom: 12px;">
                        <span style="color: #22c55e; margin-right: 8px;">&#10003;</span>
                        <span style="color: #e2e8f0; font-size: 14px;"><strong>Direct founder access</strong> — Shape the product with your feedback</span>
                    </div>
                    <div>
                        <span style="color: #22c55e; margin-right: 8px;">&#10003;</span>
                        <span style="color: #e2e8f0; font-size: 14px;"><strong>Priority features</strong> — First access to new capabilities</span>
                    </div>
                </div>
            </div>
            
            <!-- CTA -->
            <div style="padding: 0 32px 40px 32px; text-align: center;">
                <a href="{base_url}" style="display: inline-block; padding: 18px 56px; font-size: 16px; font-weight: 600; color: #ffffff; text-decoration: none; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); border-radius: 12px; box-shadow: 0 8px 24px rgba(99, 102, 241, 0.4);">Start Simulating Decisions</a>
                
                <p style="color: #64748b; font-size: 13px; margin: 24px 0 0 0;">
                    No credit card required. Just sign up and start exploring.
                </p>
            </div>
            
            <div style="background-color: #0f172a; padding: 24px 32px; border-top: 1px solid #334155;">
                <p style="color: #94a3b8; font-size: 14px; line-height: 1.6; margin: 0; text-align: center;">
                    "We built Predixen so every founder can see the future before making critical decisions. No more guessing — just simulate, compare, and act with confidence."
                </p>
                <p style="color: #6366f1; font-size: 14px; font-weight: 600; margin: 16px 0 0 0; text-align: center;">
                    — {invited_by}
                </p>
            </div>
        </div>
        
        <div style="text-align: center; margin-top: 32px;">
            <p style="color: #475569; font-size: 12px; margin: 0;">
                Predixen Intelligence OS • {timestamp}
            </p>
            <p style="color: #334155; font-size: 11px; margin: 8px 0 0 0;">
                You received this because you were invited to early access.
            </p>
        </div>
    </div>
</body>
</html>
"""
        
        text_content = f"""
You're One of the First

Welcome to the founding circle of Predixen Intelligence OS

The AI-powered decision simulator that helps startup founders make better choices by running thousands of "what-if" scenarios in seconds.

═══════════════════════════════════════════════════════

FEATURE: AI Decision Advisor [NEW]
Ask questions like "How can I extend my runway by 6 months?" and get actionable recommendations backed by probability simulations. The AI analyzes your options, runs Monte Carlo scenarios, and tells you exactly what to do with confidence levels.

FEATURE: Scenario Simulator
Run 10,000+ simulations to see P10/P50/P90 outcomes for runway, survival probability, and cash position. Compare "reduce burn by 20%" vs "raise a bridge round" vs "freeze hiring" — all in one view with sensitivity analysis.

FEATURE: Multi-Agent AI Copilot
Four specialized AI agents work together: CFO Agent (financial analysis), Market Agent (competitive intelligence), Strategy Agent (growth planning), and Decision Advisor (actionable recommendations). Each uses the best AI model for its task.

═══════════════════════════════════════════════════════

As an early member, you get:

✓ Full platform access — All AI features, unlimited simulations
✓ Decision simulations — See outcomes before committing
✓ AI document extraction — Upload financials, get insights instantly
✓ Direct founder access — Shape the product with your feedback
✓ Priority features — First access to new capabilities

═══════════════════════════════════════════════════════

Start Simulating Decisions: {base_url}

No credit card required. Just sign up and start exploring.

---

"We built Predixen so every founder can see the future before making critical decisions. No more guessing — just simulate, compare, and act with confidence."

— {invited_by}

---
Predixen Intelligence OS • {timestamp}
"""
        
        sent = []
        failed = []
        
        async with httpx.AsyncClient() as client:
            for email in to_emails:
                response = await client.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {credentials['api_key']}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "from": get_next_sender_email(),
                        "to": [email],
                        "subject": "You're One of the First - Early Access to Predixen",
                        "html": html_content,
                        "text": text_content
                    }
                )
                
                sender_used = f"new{get_current_sender_count()}@predixen.app"
                if response.status_code in (200, 201):
                    sent.append(email)
                    print(f"Early member invite sent to: {email} (from: {sender_used})")
                else:
                    failed.append(email)
                    print(f"Failed to send to {email}: {response.status_code}")
        
        return {
            "success": len(failed) == 0,
            "sent": sent,
            "failed": failed,
            "message": f"Sent {len(sent)} early member invite(s), {len(failed)} failed"
        }
        
    except Exception as e:
        print(f"Error sending early member invites: {e}")
        return {
            "success": False,
            "sent": [],
            "failed": to_emails or [],
            "error": str(e)
        }


def parse_changelog() -> Dict[str, Any]:
    """
    Parse CHANGELOG.md to extract the latest version's changes.
    
    Returns:
        Dict with version, date, and categorized changes (Added, Changed, Fixed, etc.)
    """
    changelog_path = Path(__file__).parent.parent.parent / "CHANGELOG.md"
    
    if not changelog_path.exists():
        return {"version": None, "changes": {}}
    
    content = changelog_path.read_text()
    
    version_pattern = r'## \[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})'
    version_matches = list(re.finditer(version_pattern, content))
    
    if not version_matches:
        return {"version": None, "changes": {}}
    
    latest_match = version_matches[0]
    version = latest_match.group(1)
    date = latest_match.group(2)
    
    start_pos = latest_match.end()
    end_pos = version_matches[1].start() if len(version_matches) > 1 else len(content)
    
    version_content = content[start_pos:end_pos]
    
    changes = {}
    section_pattern = r'### (Added|Changed|Fixed|Removed|Deprecated|Security)\n(.*?)(?=### |$)'
    for section_match in re.finditer(section_pattern, version_content, re.DOTALL):
        category = section_match.group(1)
        items_text = section_match.group(2).strip()
        
        items = []
        for line in items_text.split('\n'):
            line = line.strip()
            if line.startswith('- '):
                item = line[2:].strip()
                if item.startswith('**') and '**:' in item:
                    title_end = item.index('**:') + 3
                    title = item[2:title_end-3]
                    desc = item[title_end:].strip()
                    items.append({"title": title, "description": desc})
                else:
                    items.append({"title": item, "description": ""})
        
        if items:
            changes[category] = items
    
    return {
        "version": version,
        "date": date,
        "changes": changes
    }


def get_last_notified_version() -> Optional[str]:
    """Get the last version that was notified about."""
    try:
        version_file = Path(__file__).parent.parent.parent / ".last_notified_version"
        if version_file.exists():
            return version_file.read_text().strip()
    except Exception as e:
        print(f"Warning: Could not read last notified version: {e}")
    return None


def set_last_notified_version(version: str) -> None:
    """Set the last notified version. Fails gracefully if write is not possible."""
    try:
        version_file = Path(__file__).parent.parent.parent / ".last_notified_version"
        version_file.write_text(version)
    except Exception as e:
        print(f"Warning: Could not save last notified version: {e}")


async def send_publish_notification() -> Dict[str, Any]:
    """
    Send email notification about new features when app is published.
    Reads from CHANGELOG.md and only sends if there's a new version.
    
    Returns:
        Dict with success status and details
    """
    import os
    
    if os.getenv("ENVIRONMENT", "development") != "production":
        print("Skipping publish notification in non-production environment")
        return {"success": False, "reason": "Not in production environment"}
    
    changelog = parse_changelog()
    
    if not changelog.get("version"):
        return {"success": False, "reason": "No version found in changelog"}
    
    current_version = changelog["version"]
    last_notified = get_last_notified_version()
    
    if last_notified == current_version:
        print(f"Version {current_version} already notified, skipping")
        return {"success": False, "reason": f"Version {current_version} already notified"}
    
    changes = changelog.get("changes", {})
    if not changes:
        return {"success": False, "reason": "No changes found in changelog"}
    
    all_changes = []
    for category, items in changes.items():
        for item in items:
            if item.get("description"):
                all_changes.append(f"[{category}] {item['title']}: {item['description']}")
            else:
                all_changes.append(f"[{category}] {item['title']}")
    
    added_features = changes.get("Added", [])
    feature_highlights = []
    for feature in added_features[:3]:
        if feature.get("title"):
            feature_highlights.append(feature["title"])
    
    description = f"Version {current_version} has been deployed with the following updates."
    if feature_highlights:
        description += f" Key new features: {', '.join(feature_highlights)}."
    
    success = await send_feature_notification(
        feature_name=f"v{current_version} Released",
        description=description,
        changes=all_changes,
        category="New Release",
        author="Predixen Team"
    )
    
    if success:
        set_last_notified_version(current_version)
        print(f"Publish notification sent for version {current_version}")
        return {
            "success": True,
            "version": current_version,
            "changes_count": len(all_changes),
            "recipients": NOTIFICATION_RECIPIENTS
        }
    else:
        return {"success": False, "reason": "Failed to send email"}


async def check_and_send_publish_notification() -> None:
    """
    Check if a new version has been deployed and send notification.
    This is called on application startup in production.
    """
    try:
        result = await send_publish_notification()
        if result.get("success"):
            print(f"Publish notification sent successfully: {result}")
        else:
            print(f"Publish notification skipped: {result.get('reason', 'Unknown')}")
    except Exception as e:
        print(f"Error in publish notification check: {e}")


async def send_platform_update(
    to_emails: Optional[List[str]] = None,
    subject: str = "Predixen Platform Update - February 2026",
    author: str = "Predixen Team",
    from_email: str = "Predixen Updates <updates@predixen.app>"
) -> dict:
    """
    Send a multipart (HTML + text) platform update email to all specified recipients individually.
    Uses both HTML and plain text parts so Resend can add open tracking pixel to the HTML.
    
    Args:
        to_emails: List of email addresses (defaults to all active users from database)
        subject: Email subject line
        author: Name of the sender
    
    Returns:
        Dict with success status and list of sent/failed emails
    """
    import os
    from server.core.db import SessionLocal
    from server.models import User
    
    # Get emails from database if not provided
    if to_emails is None:
        try:
            db = SessionLocal()
            users = db.query(User).filter(User.is_active == True).all()
            to_emails = [user.email for user in users if user.email]
            db.close()
        except Exception as e:
            print(f"Error fetching users from database: {e}")
            to_emails = NOTIFICATION_RECIPIENTS
    
    if not to_emails:
        return {
            "success": False,
            "sent": [],
            "failed": [],
            "error": "No recipients specified"
        }
    
    try:
        credentials = await get_resend_credentials()
        timestamp = datetime.now().strftime("%B %d, %Y")
        
        text_content = f"""PREDIXEN INTELLIGENCE OS - PLATFORM UPDATE
{timestamp}

Hi there,

We've been shipping new features and squashing bugs to make Predixen even better. Here's what's new:

---

NEW FEATURES

- Instant Metric Tooltips: Hover over any metric on your dashboard and instantly see what it means, how it's calculated, where the data came from, and its confidence level. No more guessing.

- Smarter AI Copilot Errors: When the AI assistant can't connect, you'll now get clear, helpful messages that tell you exactly what to do instead of generic error pages.

- Improved Metric Catalog API: The Metric Catalog now handles edge cases more gracefully, returning clean results instead of errors when switching between companies.

---

BUG FIXES

- Sidebar Toggle: Fixed the collapse/expand button on the sidebar so it works reliably every time.

- KPI Board Flickering: Resolved the data flickering issue on the KPI Board. Trend charts now load smoothly from your historical data.

- Churn Rate Display: The churn rate KPI now correctly displays as a percentage.

- Simulation Rankings: Fixed decision ranking to use correct scenario mappings after simulation runs.

---

WHAT'S COMING NEXT

- WhatsApp/SMS messaging for customer communications
- Enhanced scenario comparison views
- More AI-powered financial insights

---

Questions or feedback? Reply directly to this email.

Best,
{author}
Predixen Intelligence OS

---
This is an automated notification from Predixen Intelligence OS.
Visit: https://predixen.app
"""
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f5f5f5; margin: 0; padding: 20px;">
    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); overflow: hidden;">
        <div style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); padding: 24px 32px;">
            <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 600;">Predixen Intelligence OS</h1>
            <p style="color: rgba(255,255,255,0.9); margin: 8px 0 0 0; font-size: 14px;">Platform Update - {timestamp}</p>
        </div>
        
        <div style="padding: 32px;">
            <p style="color: #4b5563; line-height: 1.6; margin: 0 0 24px 0;">Hi there,</p>
            <p style="color: #4b5563; line-height: 1.6; margin: 0 0 24px 0;">We've been shipping new features and squashing bugs to make Predixen even better. Here's what's new:</p>
            
            <div style="background-color: #f0fdf4; border-left: 4px solid #22c55e; padding: 16px; margin-bottom: 24px; border-radius: 0 4px 4px 0;">
                <h2 style="color: #166534; margin: 0 0 8px 0; font-size: 18px;">New Features</h2>
                <p style="color: #15803d; margin: 0; font-size: 14px;">Better insights, clearer guidance</p>
            </div>
            
            <ul style="color: #4b5563; line-height: 1.8; margin: 0 0 24px 0; padding-left: 20px;">
                <li style="margin-bottom: 8px;"><strong>Instant Metric Tooltips:</strong> Hover over any metric on your dashboard and instantly see what it means, how it's calculated, where the data came from, and its confidence level. No more guessing.</li>
                <li style="margin-bottom: 8px;"><strong>Smarter AI Copilot Errors:</strong> When the AI assistant can't connect, you'll now get clear, helpful messages that tell you exactly what to do instead of generic error pages.</li>
                <li style="margin-bottom: 8px;"><strong>Improved Metric Catalog API:</strong> The Metric Catalog now handles edge cases more gracefully, returning clean results instead of errors when switching between companies.</li>
            </ul>
            
            <div style="background-color: #eff6ff; border-left: 4px solid #3b82f6; padding: 16px; margin-bottom: 24px; border-radius: 0 4px 4px 0;">
                <h2 style="color: #1e40af; margin: 0 0 8px 0; font-size: 18px;">Bug Fixes</h2>
                <p style="color: #1d4ed8; margin: 0; font-size: 14px;">Smoother, more reliable experience</p>
            </div>
            
            <ul style="color: #4b5563; line-height: 1.8; margin: 0 0 24px 0; padding-left: 20px;">
                <li style="margin-bottom: 8px;"><strong>Sidebar Toggle:</strong> Fixed the collapse/expand button on the sidebar so it works reliably every time.</li>
                <li style="margin-bottom: 8px;"><strong>KPI Board Flickering:</strong> Resolved the data flickering issue on the KPI Board. Trend charts now load smoothly from your historical data.</li>
                <li style="margin-bottom: 8px;"><strong>Churn Rate Display:</strong> The churn rate KPI now correctly displays as a percentage.</li>
                <li style="margin-bottom: 8px;"><strong>Simulation Rankings:</strong> Fixed decision ranking to use correct scenario mappings after simulation runs.</li>
            </ul>
            
            <h3 style="color: #1f2937; font-size: 16px; margin: 0 0 12px 0;">What's Coming Next</h3>
            <ul style="color: #4b5563; line-height: 1.8; margin: 0 0 24px 0; padding-left: 20px;">
                <li style="margin-bottom: 8px;">WhatsApp/SMS messaging for customer communications</li>
                <li style="margin-bottom: 8px;">Enhanced scenario comparison views</li>
                <li style="margin-bottom: 8px;">More AI-powered financial insights</li>
            </ul>
            
            <p style="color: #4b5563; line-height: 1.6; margin: 0 0 8px 0;">Questions or feedback? Reply directly to this email.</p>
            <p style="color: #4b5563; line-height: 1.6; margin: 24px 0 0 0;">Best,<br><strong>{author}</strong><br>Predixen Intelligence OS</p>
        </div>
        
        <div style="background-color: #f9fafb; padding: 20px 32px; border-top: 1px solid #e5e7eb;">
            <p style="color: #6b7280; font-size: 12px; margin: 0; text-align: center;">
                This is an automated notification from Predixen Intelligence OS.<br>
                <a href="https://predixen.app" style="color: #6366f1; text-decoration: none;">Visit Dashboard</a>
            </p>
        </div>
    </div>
</body>
</html>"""
        
        sent = []
        failed = []
        
        async with httpx.AsyncClient() as client:
            for i, email in enumerate(to_emails):
                try:
                    # Rate limit: 2 requests per second, so wait 600ms between emails
                    if i > 0:
                        await asyncio.sleep(0.6)
                    
                    response = await client.post(
                        "https://api.resend.com/emails",
                        headers={
                            "Authorization": f"Bearer {credentials['api_key']}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "from": from_email,
                            "to": [email],
                            "subject": subject,
                            "html": html_content,
                            "text": text_content
                        },
                        timeout=30.0
                    )
                    
                    if response.status_code in (200, 201):
                        sent.append(email)
                        print(f"Platform update sent to: {email}")
                    else:
                        failed.append({"email": email, "error": response.text})
                        print(f"Failed to send to {email}: {response.status_code} - {response.text}")
                except Exception as e:
                    failed.append({"email": email, "error": str(e)})
                    print(f"Error sending to {email}: {e}")
        
        return {
            "success": len(failed) == 0,
            "sent": sent,
            "failed": failed,
            "total_recipients": len(to_emails),
            "message": f"Sent {len(sent)} email(s), {len(failed)} failed"
        }
        
    except Exception as e:
        print(f"Error sending platform update: {e}")
        return {
            "success": False,
            "sent": [],
            "failed": to_emails or [],
            "error": str(e)
        }


async def send_hybrid_feature_announcement(
    to_emails: Optional[List[str]] = None,
    author: str = "Predixen Team",
    from_email: str = "Predixen Updates <updates@predixen.app>"
) -> dict:
    """
    Send announcement email about the upcoming Hybrid Feature build.
    Sends individually to each recipient.
    """
    import os
    from server.core.db import SessionLocal
    from server.models import User
    
    if to_emails is None:
        try:
            db = SessionLocal()
            users = db.query(User).filter(User.is_active == True).all()
            to_emails = [user.email for user in users if user.email]
            db.close()
        except Exception as e:
            print(f"Error fetching users from database: {e}")
            to_emails = NOTIFICATION_RECIPIENTS
    
    if not to_emails:
        return {"success": False, "sent": [], "failed": [], "error": "No recipients"}
    
    try:
        credentials = await get_resend_credentials()
        timestamp = datetime.now().strftime("%B %d, %Y")
        base_url = os.getenv("APP_BASE_URL", "https://predixen.app")
        
        html_content = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0f172a; margin: 0; padding: 40px 20px;">
<div style="max-width: 640px; margin: 0 auto;">
<div style="text-align: center; margin-bottom: 24px;">
<div style="display: inline-block; width: 48px; height: 48px; background: linear-gradient(135deg, #6366f1, #8b5cf6); border-radius: 12px; line-height: 48px; color: #fff; font-weight: 700; font-size: 24px;">P</div>
</div>
<div style="background-color: #1e293b; border-radius: 16px; border: 1px solid #334155;">
<div style="background: linear-gradient(135deg, #f59e0b, #d97706); padding: 32px; text-align: center;">
<div style="display: inline-block; background: rgba(255,255,255,0.2); padding: 6px 16px; border-radius: 20px; margin-bottom: 16px;">
<span style="color: #fff; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 1.5px;">Coming Soon</span>
</div>
<h1 style="color: #fff; margin: 0; font-size: 28px; font-weight: 700;">Predixen Hybrid Feature</h1>
<p style="color: rgba(255,255,255,0.9); margin: 12px 0 0; font-size: 14px;">Major Platform Upgrade Announcement</p>
</div>
<div style="padding: 32px;">
<p style="color: #e2e8f0; font-size: 16px; line-height: 1.7; margin: 0 0 24px;">
We're building a comprehensive <strong style="color: #fbbf24;">Hybrid Feature</strong> that combines real-time KPI tracking, predictive simulations, and actionable recommendations.
</p>
<div style="background-color: #0f172a; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
<h3 style="color: #22c55e; font-size: 14px; font-weight: 600; text-transform: uppercase; margin: 0 0 16px;">What's Coming</h3>
<div style="margin-bottom: 16px; padding-left: 24px; border-left: 3px solid #6366f1;">
<h4 style="color: #fff; font-size: 16px; margin: 0 0 6px;">Real-Time KPI Dashboard</h4>
<p style="color: #94a3b8; font-size: 14px; margin: 0;">Live charts with WebSocket real-time updates.</p>
</div>
<div style="margin-bottom: 16px; padding-left: 24px; border-left: 3px solid #8b5cf6;">
<h4 style="color: #fff; font-size: 16px; margin: 0 0 6px;">Enhanced Scenario Wizard</h4>
<p style="color: #94a3b8; font-size: 14px; margin: 0;">Pricing, spend limits, hiring plans, growth rates.</p>
</div>
<div style="margin-bottom: 16px; padding-left: 24px; border-left: 3px solid #0ea5e9;">
<h4 style="color: #fff; font-size: 16px; margin: 0 0 6px;">Monte Carlo Simulations</h4>
<p style="color: #94a3b8; font-size: 14px; margin: 0;">Forecast with confidence intervals from 100+ runs.</p>
</div>
<div style="margin-bottom: 16px; padding-left: 24px; border-left: 3px solid #22c55e;">
<h4 style="color: #fff; font-size: 16px; margin: 0 0 6px;">Actionable Recommendations</h4>
<p style="color: #94a3b8; font-size: 14px; margin: 0;">Plain-language insights based on simulations.</p>
</div>
<div style="padding-left: 24px; border-left: 3px solid #f59e0b;">
<h4 style="color: #fff; font-size: 16px; margin: 0 0 6px;">Data Integrations</h4>
<p style="color: #94a3b8; font-size: 14px; margin: 0;">CSV upload, Stripe/QuickBooks connectors.</p>
</div>
</div>
<div style="text-align: center; margin: 32px 0;">
<a href="{base_url}" style="display: inline-block; padding: 16px 48px; font-size: 16px; font-weight: 600; color: #fff; background: linear-gradient(135deg, #6366f1, #8b5cf6); border-radius: 10px; text-decoration: none;">Visit Predixen</a>
</div>
</div>
<div style="padding: 20px 32px; border-top: 1px solid #334155; text-align: center;">
<p style="color: #64748b; font-size: 12px; margin: 0;">Reply to this email with questions. — <span style="color: #6366f1;">{author}</span></p>
</div>
</div>
<div style="text-align: center; margin-top: 24px;">
<p style="color: #475569; font-size: 11px; margin: 0;">Predixen Intelligence OS • {timestamp}</p>
</div>
</div>
</body></html>"""
        
        text_content = f"""PREDIXEN HYBRID FEATURE - COMING SOON
{timestamp}

We're building a comprehensive Hybrid Feature combining real-time KPI tracking, predictive simulations, and actionable recommendations.

WHAT'S COMING:
- Real-Time KPI Dashboard with WebSocket updates
- Enhanced Scenario Wizard (pricing, spend, hiring, growth)
- Monte Carlo Simulations with confidence intervals
- Actionable Recommendations from simulations
- Data Integrations (CSV, Stripe, QuickBooks)

Visit: {base_url}

— {author}
Predixen Intelligence OS"""
        
        sent = []
        failed = []
        
        async with httpx.AsyncClient() as client:
            for i, email in enumerate(to_emails):
                if i > 0:
                    await asyncio.sleep(0.6)
                try:
                    response = await client.post(
                        "https://api.resend.com/emails",
                        headers={
                            "Authorization": f"Bearer {credentials['api_key']}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "from": from_email,
                            "to": [email],
                            "subject": "[Predixen] Coming Soon: Major Hybrid Feature Update",
                            "html": html_content,
                            "text": text_content
                        },
                        timeout=30.0
                    )
                    
                    if response.status_code in (200, 201):
                        sent.append(email)
                        print(f"Hybrid feature announcement sent to: {email}")
                    else:
                        failed.append({"email": email, "error": response.text})
                except Exception as e:
                    failed.append({"email": email, "error": str(e)})
        
        return {
            "success": len(failed) == 0,
            "sent": sent,
            "failed": failed,
            "total_recipients": len(to_emails),
            "message": f"Sent {len(sent)} email(s), {len(failed)} failed"
        }
        
    except Exception as e:
        print(f"Error sending hybrid feature announcement: {e}")
        return {"success": False, "sent": [], "failed": to_emails or [], "error": str(e)}


async def send_weekly_digest(
    to_email: str,
    company_name: str,
    metrics: Dict[str, Any],
    alerts: List[Dict[str, Any]],
    recommendations: List[str],
    from_email: str = "Predixen <digest@predixen.app>"
) -> bool:
    """
    Send weekly KPI digest email to a user.
    
    Args:
        to_email: Recipient email address
        company_name: Name of the company
        metrics: Dictionary with key metrics (mrr, runway_months, burn_rate, survival_probability, etc.)
        alerts: List of alert dicts with 'type', 'message', 'severity' keys
        recommendations: List of actionable recommendations
        from_email: Sender email address
    
    Returns:
        True if email was sent successfully, False otherwise
    """
    try:
        credentials = await get_resend_credentials()
        
        # Format metrics
        mrr = metrics.get("mrr", 0)
        mrr_change = metrics.get("mrr_change_pct", 0)
        runway = metrics.get("runway_months", 0)
        burn_rate = metrics.get("burn_rate", 0)
        survival_prob = metrics.get("survival_probability", 0) * 100
        cash_balance = metrics.get("cash_balance", 0)
        
        # Determine health status
        if survival_prob >= 80 and runway >= 18:
            health_status = "Healthy"
            health_color = "#22c55e"
            health_bg = "#052e16"
        elif survival_prob >= 60 and runway >= 12:
            health_status = "Moderate"
            health_color = "#eab308"
            health_bg = "#422006"
        else:
            health_status = "At Risk"
            health_color = "#ef4444"
            health_bg = "#450a0a"
        
        # Format alerts HTML
        alerts_html = ""
        for alert in alerts[:5]:  # Max 5 alerts
            severity = alert.get("severity", "info")
            if severity == "critical":
                alert_color = "#ef4444"
                alert_icon = "!!!"
            elif severity == "warning":
                alert_color = "#eab308"
                alert_icon = "!!"
            else:
                alert_color = "#3b82f6"
                alert_icon = "i"
            alerts_html += f"""
            <div style="display: flex; align-items: start; gap: 12px; margin-bottom: 12px; padding: 12px; background-color: #0f172a; border-radius: 8px; border-left: 3px solid {alert_color};">
                <span style="color: {alert_color}; font-weight: 600; font-size: 12px;">{alert_icon}</span>
                <div>
                    <p style="color: #e2e8f0; font-size: 14px; margin: 0;">{alert.get('message', '')}</p>
                </div>
            </div>
            """
        
        # Format recommendations HTML
        recommendations_html = ""
        for i, rec in enumerate(recommendations[:3], 1):  # Max 3 recommendations
            recommendations_html += f"""
            <div style="display: flex; align-items: start; gap: 12px; margin-bottom: 12px;">
                <span style="display: inline-flex; align-items: center; justify-content: center; width: 24px; height: 24px; background-color: #6366f1; color: #ffffff; border-radius: 50%; font-size: 12px; font-weight: 600;">{i}</span>
                <p style="color: #e2e8f0; font-size: 14px; margin: 0; flex: 1;">{rec}</p>
            </div>
            """
        
        # Format change indicators
        mrr_arrow = "^" if mrr_change > 0 else "v" if mrr_change < 0 else "-"
        mrr_color = "#22c55e" if mrr_change > 0 else "#ef4444" if mrr_change < 0 else "#94a3b8"
        
        timestamp = datetime.now().strftime("%B %d, %Y")
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #0f172a; margin: 0; padding: 40px 20px;">
    <div style="max-width: 640px; margin: 0 auto;">
        <div style="text-align: center; margin-bottom: 24px;">
            <div style="display: inline-block; width: 48px; height: 48px; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); border-radius: 12px; text-align: center; line-height: 48px; color: #ffffff; font-weight: 700; font-size: 24px;">P</div>
        </div>
        
        <div style="background-color: #1e293b; border-radius: 16px; overflow: hidden; border: 1px solid #334155;">
            <div style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); padding: 24px 32px;">
                <p style="color: rgba(255,255,255,0.8); font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin: 0 0 8px 0;">Weekly Digest</p>
                <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 700;">{company_name}</h1>
                <p style="color: rgba(255,255,255,0.7); margin: 8px 0 0 0; font-size: 14px;">Week of {timestamp}</p>
            </div>
            
            <div style="padding: 24px 32px;">
                <div style="display: flex; align-items: center; justify-content: space-between; padding: 16px; background-color: {health_bg}; border-radius: 12px; margin-bottom: 24px;">
                    <span style="color: #94a3b8; font-size: 14px;">Financial Health Status</span>
                    <span style="color: {health_color}; font-weight: 700; font-size: 18px;">{health_status}</span>
                </div>
                
                <h3 style="color: #94a3b8; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin: 0 0 16px 0;">Key Metrics</h3>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px;">
                    <div style="background-color: #0f172a; padding: 16px; border-radius: 12px;">
                        <p style="color: #64748b; font-size: 12px; margin: 0 0 4px 0;">Monthly Recurring Revenue</p>
                        <p style="color: #ffffff; font-size: 20px; font-weight: 700; margin: 0;">${mrr:,.0f}</p>
                        <p style="color: {mrr_color}; font-size: 12px; margin: 4px 0 0 0;">{mrr_arrow} {abs(mrr_change):.1f}% vs last week</p>
                    </div>
                    <div style="background-color: #0f172a; padding: 16px; border-radius: 12px;">
                        <p style="color: #64748b; font-size: 12px; margin: 0 0 4px 0;">Runway</p>
                        <p style="color: #ffffff; font-size: 20px; font-weight: 700; margin: 0;">{runway:.1f} months</p>
                    </div>
                    <div style="background-color: #0f172a; padding: 16px; border-radius: 12px;">
                        <p style="color: #64748b; font-size: 12px; margin: 0 0 4px 0;">Monthly Burn Rate</p>
                        <p style="color: #ffffff; font-size: 20px; font-weight: 700; margin: 0;">${burn_rate:,.0f}</p>
                    </div>
                    <div style="background-color: #0f172a; padding: 16px; border-radius: 12px;">
                        <p style="color: #64748b; font-size: 12px; margin: 0 0 4px 0;">Survival Probability</p>
                        <p style="color: #ffffff; font-size: 20px; font-weight: 700; margin: 0;">{survival_prob:.0f}%</p>
                    </div>
                </div>
                
                {"<h3 style='color: #94a3b8; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin: 0 0 16px 0;'>Alerts</h3>" + alerts_html if alerts else ""}
                
                {"<h3 style='color: #94a3b8; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin: 24px 0 16px 0;'>Recommendations</h3>" + recommendations_html if recommendations else ""}
                
                <div style="text-align: center; margin: 32px 0 16px 0;">
                    <a href="https://predixen.app/dashboard" style="display: inline-block; padding: 14px 32px; font-size: 14px; font-weight: 600; color: #ffffff; text-decoration: none; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); border-radius: 10px;">View Full Dashboard</a>
                </div>
            </div>
            
            <div style="padding: 16px 32px; border-top: 1px solid #334155; text-align: center;">
                <p style="color: #64748b; font-size: 12px; margin: 0;">
                    You're receiving this because you're subscribed to weekly digests.<br>
                    <a href="https://predixen.app/settings/notifications" style="color: #6366f1; text-decoration: none;">Manage preferences</a>
                </p>
            </div>
        </div>
    </div>
</body>
</html>
"""
        
        text_content = f"""
{company_name} - Weekly Digest
Week of {timestamp}

Financial Health: {health_status}

KEY METRICS
-----------
MRR: ${mrr:,.0f} ({mrr_change:+.1f}%)
Runway: {runway:.1f} months
Burn Rate: ${burn_rate:,.0f}/month
Survival Probability: {survival_prob:.0f}%

{"ALERTS" + chr(10) + chr(10).join([f"- {a.get('message', '')}" for a in alerts]) if alerts else ""}

{"RECOMMENDATIONS" + chr(10) + chr(10).join([f"{i}. {r}" for i, r in enumerate(recommendations, 1)]) if recommendations else ""}

View your full dashboard: https://predixen.app/dashboard
"""
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {credentials['api_key']}",
                    "Content-Type": "application/json"
                },
                json={
                    "from": from_email,
                    "to": [to_email],
                    "subject": f"[Predixen] Weekly Digest - {company_name}",
                    "html": html_content,
                    "text": text_content
                },
                timeout=30.0
            )
            
            if response.status_code in (200, 201):
                print(f"Weekly digest sent to: {to_email}")
                return True
            else:
                print(f"Failed to send weekly digest: {response.text}")
                return False
                
    except Exception as e:
        print(f"Error sending weekly digest: {e}")
        return False
