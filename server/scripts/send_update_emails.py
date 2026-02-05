"""
Script to send platform update emails to all users.
Run with: python -m server.scripts.send_update_emails
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from server.email.service import send_email, is_email_configured
from server.email.templates import render_platform_update_template
from server.core.db import SessionLocal
from sqlalchemy import text


UPDATES_LATEST = [
    {
        "title": "Redesigned Sidebar Navigation",
        "description": "New collapsible sidebar groups organize features into logical sections: Analytics, Data & Setup, Planning, and Stakeholders. Click chevrons to expand/collapse sections and reduce visual clutter."
    },
    {
        "title": "AI Copilot Prominent Placement",
        "description": "The AI Copilot now sits at the top of the sidebar with enhanced styling for quick access. Your intelligent financial assistant is always one click away."
    },
    {
        "title": "Consistent Empty States",
        "description": "All empty states now feature engaging designs with circular icons, clear headlines, helpful descriptions, and action buttons. No more confusing blank screens."
    },
    {
        "title": "Design System Compliance",
        "description": "Updated hover effects and visual interactions across the platform to follow our design system guidelines. Smoother, more consistent experience throughout."
    },
    {
        "title": "Bug Fixes",
        "description": "Fixed authentication flow edge cases and improved login history tracking. Enhanced error messages for failed login attempts."
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
    from_email: str = "Predixen Updates <newchanges5@predixen.app>"
):
    """Send platform update email to specified users."""
    if not is_email_configured():
        print("Email service not configured. Please set up Resend integration.")
        return {"success": 0, "failed": len(emails)}
    
    app_url = os.getenv("APP_BASE_URL", "https://predixen.app")
    
    print(f"Sending updates to {len(emails)} specified addresses using sender: {from_email}")
    
    success_count = 0
    fail_count = 0
    failed_emails = []
    
    html_content = render_platform_update_template(
        updates=updates,
        app_url=app_url
    )
    
    subject = "Predixen Intelligence OS - UX Improvements & Bug Fixes"
    
    for email in emails:
        print(f"Sending to {email}...")
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
                failed_emails.append(email)
        except Exception as e:
            print(f"  Error: {str(e)}")
            failed_emails.append(email)
        
        await asyncio.sleep(0.6)
    
    if failed_emails:
        print(f"\nRetrying {len(failed_emails)} failed emails after delay...")
        await asyncio.sleep(2)
        
        for email in failed_emails:
            print(f"Retry: {email}...")
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
    
    from_email = "Predixen Bug Fixes <bugfix@predixen.app>"
    
    return await send_update_to_specified_users(
        emails=emails,
        updates=UPDATES_LATEST,
        from_email=from_email
    )


if __name__ == "__main__":
    asyncio.run(main())
