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
        "title": "Data Integration Infrastructure",
        "description": "New integration framework supporting OAuth2, API Key, and Service Account authentication with configurable data point selection and flexible sync intervals (5min to weekly)."
    },
    {
        "title": "Google Sheets Connector",
        "description": "Import financial data directly from Google Sheets with multi-step configuration: spreadsheet selection, sheet mapping, column data type assignment (currency, percentage, number, date), and automatic sync scheduling."
    },
    {
        "title": "Analytics Integrations Tab",
        "description": "New Analytics tab with connectors for Google Analytics 4 (sessions, users, conversions), Mixpanel (events, funnels, retention), and ChartMogul (MRR, ARR, churn metrics) to import product and revenue analytics."
    },
    {
        "title": "Spreadsheets Tab",
        "description": "Dedicated Spreadsheets tab for importing data from Google Sheets, Excel Online, and Airtable. Perfect for custom metrics, budgets, and manual KPI tracking that isn't available in your other systems."
    },
    {
        "title": "Bug Fixes & Improvements",
        "description": "Fixed modal state management to properly clear selection on close. Improved integration card status indicators. Enhanced connection flow with better error handling and retry logic."
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
    
    subject = "Predixen Intelligence OS - New Data Integrations & Analytics"
    
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
    
    from_email = "Predixen Updates <newchanges5@predixen.app>"
    
    return await send_update_to_specified_users(
        emails=emails,
        updates=UPDATES_LATEST,
        from_email=from_email
    )


if __name__ == "__main__":
    asyncio.run(main())
