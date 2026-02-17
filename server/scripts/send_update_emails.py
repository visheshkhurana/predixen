"""
Script to send platform update emails to all users.
Run with: python -m server.scripts.send_update_emails
"""
import asyncio
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from server.email.service import send_email, is_email_configured
from server.email.templates import render_platform_update_template, render_text_only_update_template
from server.core.db import SessionLocal
from sqlalchemy import text
from datetime import datetime


UPDATES_LATEST = [
    {
        "title": "Smarter AI Copilot Responses",
        "description": "The AI Copilot now understands conversational context. It remembers your last 10 messages, gives intelligent replies to greetings and follow-ups, and renders responses with proper formatting including bold text, bullet points, and tables."
    },
    {
        "title": "Instant Metric Lookups",
        "description": "Use /fetch-metric followed by a metric name (mrr, runway, burn, cac, ltv, etc.) to instantly pull your latest data. The copilot now filters to exactly the metric you ask for."
    },
    {
        "title": "Inline Scenario Simulations",
        "description": "Suggestion buttons like 'Run burn cut scenario' now run directly in your chat conversation instead of navigating you away. Get simulation insights without leaving the copilot."
    },
    {
        "title": "Better Error Handling",
        "description": "When something goes wrong, the copilot now shows a clear, friendly error message right in the chat instead of failing silently. No more wondering if your question was received."
    },
    {
        "title": "Feedback with Comments",
        "description": "The thumbs down button now lets you tell us what went wrong. An optional text field appears so you can share specific feedback to help us improve."
    }
]


def get_all_user_emails():
    """Fetch all unique user emails from database."""
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT DISTINCT email FROM users WHERE email IS NOT NULL AND email != ''"))
        rows = result.fetchall()
        return [row[0] for row in rows]
    finally:
        db.close()


async def send_update_to_specified_users(
    emails: list,
    updates: list,
    from_email: str = "FounderConsole Updates <newchanges5@founderconsole.ai>",
    use_text_only: bool = False
):
    """Send platform update email to specified users."""
    if not is_email_configured():
        print("Email service not configured. Please set up Resend integration.")
        return {"success": 0, "failed": len(emails)}
    
    app_url = os.getenv("APP_BASE_URL", "https://founderconsole.ai")
    
    template_type = "text-only with tracking pixel" if use_text_only else "HTML"
    print(f"Sending {template_type} updates to {len(emails)} addresses using sender: {from_email}")
    
    success_count = 0
    fail_count = 0
    failed_emails = []
    
    subject = "FounderConsole - AI Copilot Upgrades & New Features"
    db = SessionLocal()
    
    try:
        for email in emails:
            tracking_id = str(uuid.uuid4())
            
            if use_text_only:
                html_content = render_text_only_update_template(
                    updates=updates,
                    app_url=app_url,
                    tracking_id=tracking_id
                )
            else:
                html_content = render_platform_update_template(
                    updates=updates,
                    app_url=app_url
                )
            
            db.execute(text("""
                INSERT INTO email_events (email_id, to_email, subject, created_at, updated_at)
                VALUES (:email_id, :to_email, :subject, :created_at, :updated_at)
            """), {
                "email_id": tracking_id,
                "to_email": email,
                "subject": subject,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
            db.commit()
            
            print(f"Sending to {email} (tracking: {tracking_id[:8]}...)...")
            try:
                result = await send_email(
                    to=email,
                    subject=subject,
                    html_content=html_content,
                    from_email=from_email
                )
                if result.get("success"):
                    print(f"  Sent successfully to {email}")
                    success_count += 1
                else:
                    print(f"  Failed: {result.get('error', 'Unknown error')}")
                    failed_emails.append((email, tracking_id))
            except Exception as e:
                print(f"  Error: {str(e)}")
                failed_emails.append((email, tracking_id))
            
            await asyncio.sleep(0.6)
        
        if failed_emails:
            print(f"\nRetrying {len(failed_emails)} failed emails after delay...")
            await asyncio.sleep(2)
            
            for email, tracking_id in failed_emails:
                print(f"Retry: {email}...")
                
                if use_text_only:
                    html_content = render_text_only_update_template(
                        updates=updates,
                        app_url=app_url,
                        tracking_id=tracking_id
                    )
                else:
                    html_content = render_platform_update_template(
                        updates=updates,
                        app_url=app_url
                    )
                
                try:
                    result = await send_email(
                        to=email,
                        subject=subject,
                        html_content=html_content,
                        from_email=from_email
                    )
                    if result.get("success"):
                        print(f"  Sent successfully to {email}")
                        success_count += 1
                    else:
                        print(f"  Failed: {result.get('error', 'Unknown error')}")
                        fail_count += 1
                except Exception as e:
                    print(f"  Error: {str(e)}")
                    fail_count += 1
                
                await asyncio.sleep(0.6)
    finally:
        db.close()
    
    print(f"\nComplete: {success_count} sent, {fail_count} failed")
    return {"success": success_count, "failed": fail_count}


def render_pitch_email_template(app_url: str, tracking_id: str) -> str:
    """Render a comprehensive pitch email with all platform features."""
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FounderConsole</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #f1f5f9;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0" style="max-width: 600px; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                    
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 40px; text-align: center;">
                            <div style="display: inline-block; width: 48px; height: 48px; background-color: #0ea5e9; border-radius: 12px; text-align: center; line-height: 48px; color: #ffffff; font-weight: 700; font-size: 24px; margin-bottom: 16px;">P</div>
                            <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 700; letter-spacing: -0.5px;">FounderConsole</h1>
                            <p style="margin: 12px 0 0 0; color: #94a3b8; font-size: 14px; text-transform: uppercase; letter-spacing: 2px;">AI-Powered Financial Intelligence for Startups</p>
                        </td>
                    </tr>
                    
                    <!-- Hero -->
                    <tr>
                        <td style="padding: 40px;">
                            <h2 style="margin: 0 0 16px 0; color: #0f172a; font-size: 24px; font-weight: 600; line-height: 1.3;">Stop guessing your runway.<br/>Start knowing it.</h2>
                            <p style="margin: 0 0 24px 0; color: #64748b; font-size: 16px; line-height: 1.7;">
                                Running a startup means making critical financial decisions with incomplete data. What if you could see exactly how every choice impacts your survival—before you make it?
                            </p>
                            
                            <!-- CTA Button -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                                <tr>
                                    <td style="background-color: #0ea5e9; border-radius: 10px;">
                                        <a href="{app_url}" target="_blank" style="display: inline-block; padding: 16px 32px; color: #ffffff; text-decoration: none; font-weight: 600; font-size: 16px;">Explore FounderConsole</a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Core Features Section -->
                    <tr>
                        <td style="padding: 0 40px 40px 40px;">
                            <p style="margin: 0 0 24px 0; color: #0f172a; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 2px;">Core Features</p>
                            
                            <!-- Feature 1: Truth Engine -->
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 20px; background-color: #f8fafc; border-radius: 12px;">
                                <tr>
                                    <td style="padding: 20px;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                                            <tr>
                                                <td width="44" valign="top" style="padding-right: 16px;">
                                                    <div style="width: 40px; height: 40px; background-color: #0ea5e9; border-radius: 10px; text-align: center; line-height: 40px; color: #ffffff; font-size: 20px;">&#128202;</div>
                                                </td>
                                                <td valign="top">
                                                    <p style="margin: 0 0 6px 0; color: #0f172a; font-weight: 600; font-size: 16px;">Truth Engine</p>
                                                    <p style="margin: 0; color: #64748b; font-size: 14px; line-height: 1.5;">Upload your financials (CSV, Excel, or PDF) and instantly get 24 validated metrics with industry benchmarks. No more spreadsheet nightmares.</p>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- Feature 2: Monte Carlo Simulation -->
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 20px; background-color: #f8fafc; border-radius: 12px;">
                                <tr>
                                    <td style="padding: 20px;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                                            <tr>
                                                <td width="44" valign="top" style="padding-right: 16px;">
                                                    <div style="width: 40px; height: 40px; background-color: #8b5cf6; border-radius: 10px; text-align: center; line-height: 40px; color: #ffffff; font-size: 20px;">&#128200;</div>
                                                </td>
                                                <td valign="top">
                                                    <p style="margin: 0 0 6px 0; color: #0f172a; font-weight: 600; font-size: 16px;">Monte Carlo Simulation</p>
                                                    <p style="margin: 0; color: #64748b; font-size: 14px; line-height: 1.5;">Run thousands of scenarios to see your probabilistic runway, survival rates at 12/18/24 months, and identify the drivers that matter most.</p>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- Feature 3: Decision Scoring -->
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 20px; background-color: #f8fafc; border-radius: 12px;">
                                <tr>
                                    <td style="padding: 20px;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                                            <tr>
                                                <td width="44" valign="top" style="padding-right: 16px;">
                                                    <div style="width: 40px; height: 40px; background-color: #22c55e; border-radius: 10px; text-align: center; line-height: 40px; color: #ffffff; font-size: 20px;">&#9889;</div>
                                                </td>
                                                <td valign="top">
                                                    <p style="margin: 0 0 6px 0; color: #0f172a; font-weight: 600; font-size: 16px;">Decision Scoring</p>
                                                    <p style="margin: 0; color: #64748b; font-size: 14px; line-height: 1.5;">Get ranked recommendations that optimize for survival, growth potential, and minimal dilution—not just cost-cutting.</p>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- Feature 4: AI Copilot -->
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #f8fafc; border-radius: 12px;">
                                <tr>
                                    <td style="padding: 20px;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                                            <tr>
                                                <td width="44" valign="top" style="padding-right: 16px;">
                                                    <div style="width: 40px; height: 40px; background-color: #f59e0b; border-radius: 10px; text-align: center; line-height: 40px; color: #ffffff; font-size: 20px;">&#129302;</div>
                                                </td>
                                                <td valign="top">
                                                    <p style="margin: 0 0 6px 0; color: #0f172a; font-weight: 600; font-size: 16px;">AI Copilot</p>
                                                    <p style="margin: 0; color: #64748b; font-size: 14px; line-height: 1.5;">Ask questions in plain English. Get CFO-grade analysis with market context, competitor insights, and strategic recommendations.</p>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Fundraising OS Section -->
                    <tr>
                        <td style="padding: 0 40px 40px 40px;">
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border-radius: 12px;">
                                <tr>
                                    <td style="padding: 28px;">
                                        <p style="margin: 0 0 4px 0; color: #f59e0b; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 2px;">Coming Soon</p>
                                        <p style="margin: 0 0 16px 0; color: #ffffff; font-size: 20px; font-weight: 600;">Fundraising OS</p>
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                                            <tr>
                                                <td style="padding: 6px 0; color: #94a3b8; font-size: 14px;">&#10003; Cap Table Modeling — Visualize dilution across scenarios</td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 6px 0; color: #94a3b8; font-size: 14px;">&#10003; Investor Room — Auto-generate data rooms & KPI snapshots</td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 6px 0; color: #94a3b8; font-size: 14px;">&#10003; Pipeline Tracking — Manage investors from intro to term sheet</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Why Choose Section -->
                    <tr>
                        <td style="padding: 0 40px 40px 40px;">
                            <p style="margin: 0 0 20px 0; color: #0f172a; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 2px;">Why Founders Choose FounderConsole</p>
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                                <tr>
                                    <td width="50%" valign="top" style="padding-right: 10px;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 16px;">
                                            <tr>
                                                <td style="padding: 4px 10px 4px 0; color: #0ea5e9; font-size: 16px;">&#10003;</td>
                                                <td style="color: #334155; font-size: 14px;"><strong>Investor-Grade Analysis</strong> in minutes, not weeks</td>
                                            </tr>
                                        </table>
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                                            <tr>
                                                <td style="padding: 4px 10px 4px 0; color: #0ea5e9; font-size: 16px;">&#10003;</td>
                                                <td style="color: #334155; font-size: 14px;"><strong>Probabilistic Forecasting</strong> that accounts for uncertainty</td>
                                            </tr>
                                        </table>
                                    </td>
                                    <td width="50%" valign="top" style="padding-left: 10px;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 16px;">
                                            <tr>
                                                <td style="padding: 4px 10px 4px 0; color: #0ea5e9; font-size: 16px;">&#10003;</td>
                                                <td style="color: #334155; font-size: 14px;"><strong>Actionable Recommendations</strong> ranked by impact</td>
                                            </tr>
                                        </table>
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                                            <tr>
                                                <td style="padding: 4px 10px 4px 0; color: #0ea5e9; font-size: 16px;">&#10003;</td>
                                                <td style="color: #334155; font-size: 14px;"><strong>Multi-Agent AI</strong> with specialized expertise</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- CTA Section -->
                    <tr>
                        <td style="padding: 0 40px 40px 40px;">
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #f0f9ff; border-radius: 12px; border: 1px solid #bae6fd;">
                                <tr>
                                    <td style="padding: 28px; text-align: center;">
                                        <p style="margin: 0 0 16px 0; color: #0f172a; font-size: 18px; font-weight: 600;">Ready to see your real runway?</p>
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center">
                                            <tr>
                                                <td style="background-color: #0ea5e9; border-radius: 10px;">
                                                    <a href="{app_url}" target="_blank" style="display: inline-block; padding: 14px 28px; color: #ffffff; text-decoration: none; font-weight: 600; font-size: 15px;">Get Started Free</a>
                                                </td>
                                            </tr>
                                        </table>
                                        <p style="margin: 16px 0 0 0; color: #64748b; font-size: 13px;">Our users typically discover 3-6 months of hidden runway through optimization opportunities.</p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f8fafc; padding: 24px 40px; text-align: center; border-top: 1px solid #e2e8f0;">
                            <p style="margin: 0 0 4px 0; color: #0f172a; font-size: 16px; font-weight: 600;">FounderConsole</p>
                            <p style="margin: 0; color: #64748b; font-size: 13px;">AI-Powered Financial Intelligence</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
    
    <!-- Tracking Pixel -->
    <img src="{app_url}/api/email/track/{tracking_id}" width="1" height="1" style="display:none;" alt="" />
</body>
</html>
"""


async def send_pitch_emails(
    emails: list,
    from_email: str = "FounderConsole <new@founderconsole.ai>"
):
    """Send pitch emails to specified users."""
    if not is_email_configured():
        print("Email service not configured. Please set up Resend integration.")
        return {"success": 0, "failed": len(emails)}
    
    app_url = os.getenv("APP_BASE_URL", "https://founderconsole.ai")
    
    print(f"Sending pitch emails to {len(emails)} addresses using sender: {from_email}")
    
    success_count = 0
    fail_count = 0
    
    subject = "Stop guessing your runway. Start knowing it."
    db = SessionLocal()
    
    try:
        for email in emails:
            tracking_id = str(uuid.uuid4())
            
            html_content = render_pitch_email_template(
                app_url=app_url,
                tracking_id=tracking_id
            )
            
            db.execute(text("""
                INSERT INTO email_events (email_id, to_email, subject, created_at, updated_at)
                VALUES (:email_id, :to_email, :subject, :created_at, :updated_at)
            """), {
                "email_id": tracking_id,
                "to_email": email,
                "subject": subject,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
            db.commit()
            
            print(f"Sending pitch to {email}...")
            try:
                result = await send_email(
                    to=email,
                    subject=subject,
                    html_content=html_content,
                    from_email=from_email
                )
                if result.get("success"):
                    print(f"  Sent successfully to {email}")
                    success_count += 1
                else:
                    print(f"  Failed: {result.get('error', 'Unknown error')}")
                    fail_count += 1
            except Exception as e:
                print(f"  Error: {str(e)}")
                fail_count += 1
            
            await asyncio.sleep(0.6)
    finally:
        db.close()
    
    print(f"\nComplete: {success_count} sent, {fail_count} failed")
    return {"success": success_count, "failed": fail_count}


async def main():
    """Main entry point for sending update emails."""
    emails = get_all_user_emails()
    if not emails:
        emails = [
            "nikita.luther@gmail.com",
            "nikitafl2024@gmail.com",
            "nikita@founderconsole.ai",
            "vysheshk@gmail.com"
        ]
    
    from_email = "FounderConsole Updates <newchanges23@founderconsole.ai>"
    
    return await send_update_to_specified_users(
        emails=emails,
        updates=UPDATES_LATEST,
        from_email=from_email,
        use_text_only=False
    )


if __name__ == "__main__":
    asyncio.run(main())
