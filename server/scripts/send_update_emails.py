"""
Script to send platform update emails to all users.
Run with: python -m server.scripts.send_update_emails
"""
import asyncio
import os
import sys
import uuid
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from server.email.service import send_email, is_email_configured
from server.email.templates import render_platform_update_template, render_text_only_update_template
from server.core.db import SessionLocal
from sqlalchemy import text
from datetime import datetime


ALL_VERIFIED_DOMAINS = [
    "founderconsole.ai",
    "founderconsole.co",
    "founderconsole.com",
    "founderconsole.in",
    "founderconsole.info",
    "founderconsole.net",
    "founderconsole.shop",
    "updates.founderconsole.ai",
    "predixen.app",
    "predixen.in",
    "predixen.me",
    "predixen.email",
    "updates.predixen.me",
    "kpibeacon.ai",
    "kpibeacon.com",
    "runora.xyz",
    "runora.in",
    "runora.me",
    "runoraai.co",
    "runoraai.com",
]


def get_rotating_from_email(index: int, sender_name: str = "FounderConsole Updates") -> str:
    """Get a from email address that rotates across ALL verified domains.
    
    Used for outreach/update/pitch emails — distributes sending load
    across all 20 domains (founderconsole, predixen, kpibeacon, runora).
    """
    domain = ALL_VERIFIED_DOMAINS[index % len(ALL_VERIFIED_DOMAINS)]
    local_part = f"updates{index + 1}"
    return f"{sender_name} <{local_part}@{domain}>"


UPDATES_LATEST = [
    {
        "title": "Investor Data Room",
        "description": "A brand new Data Room tab in the Investor Room lets you upload and organize documents by category — Finance, Legal, Product & Tech, GTM, HR, and more. Keep your due diligence materials organized and ready for investors at all times."
    },
    {
        "title": "Board Deck HTML Export",
        "description": "Export your AI-generated Board Decks as HTML files, in addition to PDF. Import the HTML directly into Google Slides or PowerPoint for easy editing and customization before your next board meeting."
    },
    {
        "title": "AI-Estimated Value Badges",
        "description": "Metrics estimated by AI are now clearly flagged with an 'Estimated' badge throughout the platform — in Truth Scan results, the Overview dashboard, and Board Decks. You always know which numbers come from your actual data and which were AI-inferred."
    },
    {
        "title": "Cap Table Duplicate Prevention",
        "description": "The Cap Table now automatically detects and prevents duplicate stakeholder entries. If you try to add a stakeholder that already exists (by name or email), you'll get a clear warning instead of creating duplicates."
    },
    {
        "title": "Cap Table Guided Onboarding",
        "description": "New to cap tables? A step-by-step guided walkthrough now appears when you first visit the Cap Table, explaining how to add founders, investors, and option pools. Makes equity management approachable even if you've never managed a cap table before."
    },
    {
        "title": "Use of Funds Pre-Population",
        "description": "The Fundraising Prep section now pre-populates your Use of Funds breakdown using your actual financial data — headcount costs, R&D spend, sales & marketing, and more. No more starting from a blank slate."
    },
    {
        "title": "Smarter AI Copilot",
        "description": "The Copilot no longer floods you with repetitive data gap warnings. It now consolidates missing data into a single, concise summary and focuses on giving you actionable insights with the data you have."
    },
    {
        "title": "Headcount Bug Fix",
        "description": "Fixed an issue where headcount entered in Simple Mode wasn't properly flowing through to simulations, board decks, and other features. Your team size now accurately reflects everywhere across the platform.",
        "type": "fix"
    },
    {
        "title": "Improved Metric Propagation",
        "description": "ARR, Gross Margin, and Churn Rate now reliably propagate from data input through Truth Scan to Board Decks, Simulations, and the Copilot. What you enter is what you see — everywhere.",
        "type": "fix"
    },
    {
        "title": "Investor Room Stability",
        "description": "Fixed crashes that could occur when opening certain Investor Room tabs before generating materials. The Investor Room is now stable and accessible at all times, even before you've run your first analysis.",
        "type": "fix"
    },
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
    from_email: str = None,
    use_text_only: bool = False,
    rotate_domains: bool = True,
    sender_name: str = "FounderConsole Updates"
):
    """Send platform update email to specified users with domain rotation.
    
    When rotate_domains=True (default), each email is sent from a different
    verified domain to distribute sending load across all 20 domains.
    """
    if not is_email_configured():
        print("Email service not configured. Please set up Resend integration.")
        return {"success": 0, "failed": len(emails)}
    
    app_url = os.getenv("APP_BASE_URL", "https://founderconsole.ai")
    
    random.shuffle(emails)
    
    template_type = "text-only with tracking pixel" if use_text_only else "HTML"
    if rotate_domains:
        print(f"Sending {template_type} updates to {len(emails)} addresses with domain rotation across {len(ALL_VERIFIED_DOMAINS)} domains")
    else:
        effective_from = from_email or get_rotating_from_email(0, sender_name)
        print(f"Sending {template_type} updates to {len(emails)} addresses using sender: {effective_from}")
    
    success_count = 0
    fail_count = 0
    failed_emails = []
    
    subject = "FounderConsole — 10 New Features & Fixes Just Shipped"
    db = SessionLocal()
    
    try:
        for i, email in enumerate(emails):
            tracking_id = str(uuid.uuid4())
            
            if rotate_domains:
                current_from = get_rotating_from_email(i, sender_name)
            else:
                current_from = from_email or get_rotating_from_email(0, sender_name)
            
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
            
            print(f"[{i+1}/{len(emails)}] Sending to {email} via {current_from.split('<')[1].rstrip('>')} ...")
            try:
                result = await send_email(
                    to=email,
                    subject=subject,
                    html_content=html_content,
                    from_email=current_from
                )
                if result.get("success"):
                    print(f"  Sent successfully")
                    success_count += 1
                else:
                    print(f"  Failed: {result.get('error', 'Unknown error')}")
                    failed_emails.append((email, tracking_id, i))
            except Exception as e:
                print(f"  Error: {str(e)}")
                failed_emails.append((email, tracking_id, i))
            
            await asyncio.sleep(0.6)
        
        if failed_emails:
            print(f"\nRetrying {len(failed_emails)} failed emails after delay...")
            await asyncio.sleep(2)
            
            for email, tracking_id, orig_idx in failed_emails:
                retry_from = get_rotating_from_email(orig_idx + len(ALL_VERIFIED_DOMAINS), sender_name)
                print(f"Retry: {email} via {retry_from.split('<')[1].rstrip('>')}...")
                
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
                        from_email=retry_from
                    )
                    if result.get("success"):
                        print(f"  Sent successfully")
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
    
    print(f"\nComplete: {success_count} sent, {fail_count} failed out of {len(emails)} total")
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
    from_email: str = None,
    rotate_domains: bool = True,
    sender_name: str = "FounderConsole"
):
    """Send pitch emails to specified users with domain rotation."""
    if not is_email_configured():
        print("Email service not configured. Please set up Resend integration.")
        return {"success": 0, "failed": len(emails)}
    
    app_url = os.getenv("APP_BASE_URL", "https://founderconsole.ai")
    
    random.shuffle(emails)
    
    if rotate_domains:
        print(f"Sending pitch emails to {len(emails)} addresses with domain rotation across {len(ALL_VERIFIED_DOMAINS)} domains")
    else:
        effective_from = from_email or get_rotating_from_email(0, sender_name)
        print(f"Sending pitch emails to {len(emails)} addresses using sender: {effective_from}")
    
    success_count = 0
    fail_count = 0
    
    subject = "Stop guessing your runway. Start knowing it."
    db = SessionLocal()
    
    try:
        for i, email in enumerate(emails):
            tracking_id = str(uuid.uuid4())
            
            if rotate_domains:
                current_from = get_rotating_from_email(i, sender_name)
            else:
                current_from = from_email or get_rotating_from_email(0, sender_name)
            
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
            
            print(f"[{i+1}/{len(emails)}] Sending pitch to {email} via {current_from.split('<')[1].rstrip('>')}...")
            try:
                result = await send_email(
                    to=email,
                    subject=subject,
                    html_content=html_content,
                    from_email=current_from
                )
                if result.get("success"):
                    print(f"  Sent successfully")
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
    
    print(f"\nComplete: {success_count} sent, {fail_count} failed out of {len(emails)} total")
    return {"success": success_count, "failed": fail_count}


async def main():
    """Main entry point for sending update emails with domain rotation."""
    emails = get_all_user_emails()
    if not emails:
        emails = [
            "nikita.luther@gmail.com",
            "nikitafl2024@gmail.com",
            "nikita@founderconsole.ai",
            "vysheshk@gmail.com"
        ]
    
    return await send_update_to_specified_users(
        emails=emails,
        updates=UPDATES_LATEST,
        rotate_domains=True,
        use_text_only=False
    )


if __name__ == "__main__":
    asyncio.run(main())
