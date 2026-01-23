"""
Notification service for sending email updates about platform changes.
Uses Resend integration for email delivery.
"""

import os
import httpx
from typing import List, Optional
from datetime import datetime


NOTIFICATION_RECIPIENTS = [
    "nikita@predixen.ai",
    "vysheshk@gmail.com",
    "nikita.luther@gmail.com"
]


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
    author: Optional[str] = None
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
                    "from": credentials["from_email"],
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
