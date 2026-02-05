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
        "title": "Enhanced KPI Dashboard",
        "description": "The KPI Board now intelligently merges real-time data with your baseline financials. No more zero values when data is loading - your dashboard always shows meaningful metrics."
    },
    {
        "title": "Improved Data Accuracy",
        "description": "Fixed decimal input support across all financial forms. You can now enter precise values like $1,234.56 without any issues."
    },
    {
        "title": "Better Runway Calculations",
        "description": "All runway calculations now use a unified formula across the platform, ensuring consistent projections in charts, dashboards, and reports."
    },
    {
        "title": "New Help & Documentation",
        "description": "Added a dedicated Help & Docs section to the sidebar. Access guides, tutorials, and support resources directly from the platform."
    },
    {
        "title": "Chart & Visualization Fixes",
        "description": "Fixed NaN display issues in cash projection charts. Tooltips now show clean, formatted values even when data is incomplete."
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
    from_email: str = "Predixen Updates <newchanges5@predixen.app>",
    use_text_only: bool = False
):
    """Send platform update email to specified users."""
    if not is_email_configured():
        print("Email service not configured. Please set up Resend integration.")
        return {"success": 0, "failed": len(emails)}
    
    app_url = os.getenv("APP_BASE_URL", "https://predixen.app")
    
    template_type = "text-only with tracking pixel" if use_text_only else "HTML"
    print(f"Sending {template_type} updates to {len(emails)} addresses using sender: {from_email}")
    
    success_count = 0
    fail_count = 0
    failed_emails = []
    
    subject = "Predixen Intelligence OS - UX Improvements & Bug Fixes"
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


async def main():
    """Main entry point for sending update emails."""
    emails = [
        "nikita.luther@gmail.com",
        "nikitafl2024@gmail.com",
        "nikita@predixen.ai",
        "vysheshk@gmail.com"
    ]
    
    from_email = "Predixen Updates <new@predixen.in>"
    
    return await send_update_to_specified_users(
        emails=emails,
        updates=UPDATES_LATEST,
        from_email=from_email,
        use_text_only=True
    )


if __name__ == "__main__":
    asyncio.run(main())
