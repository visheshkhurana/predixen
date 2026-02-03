"""
Script to send platform update emails to all users.
Run with: python -m server.scripts.send_update_emails
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from server.email.service import send_platform_update_email, is_email_configured
from server.core.db import SessionLocal
from sqlalchemy import text


UPDATES_LAST_24_HOURS = [
    {
        "title": "AI-Powered Company Lookup",
        "description": "Enter any company website URL during onboarding and our AI will automatically fetch and fill in company details including name, industry, founding year, team size, and description. Powered by Perplexity AI for accurate, real-time data."
    },
    {
        "title": "Real-Time KPI Dashboard",
        "description": "Your financial KPIs now update automatically every 10 seconds with live data polling. View MRR, ARR, runway, burn rate, and 12+ other metrics in real-time without refreshing the page."
    },
    {
        "title": "Enhanced File Upload System",
        "description": "Upload financial documents (Excel, PDF, CSV) at any step of onboarding. We now support upload history tracking showing your last 5 uploaded files with timestamps."
    },
    {
        "title": "Intelligent Document Extraction",
        "description": "AI-powered extraction now works with complex Excel files and PDFs. Automatically extracts revenue, expenses, cash balance, headcount, and other financial metrics with improved accuracy."
    },
    {
        "title": "Truth Scan Data Validation",
        "description": "Enhanced Truth Scan module validates all extracted data before simulations. Detects anomalies, missing values, and inconsistencies with auto-fix suggestions and full audit trails."
    },
    {
        "title": "Fixed KPI Dashboard Authentication",
        "description": "Resolved authentication issues with the KPI dashboard. Real-time data now flows correctly with proper Bearer token authentication for secure, uninterrupted monitoring."
    },
    {
        "title": "Improved Onboarding Flow",
        "description": "Onboarding now handles existing companies intelligently - updates instead of creating duplicates. Smoother transitions between steps with better error handling."
    },
    {
        "title": "Multi-LLM AI Router",
        "description": "Smart task-based routing across OpenAI GPT-4o, Anthropic Claude, and Google Gemini. Each query is automatically directed to the best model for optimal results."
    },
    {
        "title": "Monte Carlo Decision Simulator",
        "description": "Run probabilistic simulations with 24-month projections. Get P10/P50/P90 survival probabilities and ranked decision recommendations based on your financial data."
    },
    {
        "title": "Email Notification System",
        "description": "Platform updates, invites, and alerts delivered via Resend with delivery tracking. You're receiving this email as part of our new notification system!"
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


async def send_update_to_all_users():
    """Send platform update email to all users."""
    if not is_email_configured():
        print("Email service not configured. Please set up Resend integration.")
        return
    
    app_url = os.getenv("APP_BASE_URL", "https://predixen.app")
    
    # Specific list of emails requested by the user
    emails = [
        "nikita@predixen.ai",
        "vysheshk@gmail.com",
        "nikita.luther@gmail.com",
        "nikitafl2024@gmail.com"
    ]
    print(f"Sending updates to {len(emails)} specified addresses")
    
    success_count = 0
    fail_count = 0
    failed_emails = []
    
    for email in emails:
        print(f"Sending to {email}...")
        try:
            result = await send_platform_update_email(
                to_email=email,
                updates=UPDATES_LAST_24_HOURS,
                app_url=app_url
            )
            if result.get("success"):
                print(f"  ✓ Sent successfully to {email}")
                success_count += 1
            else:
                print(f"  ✗ Failed: {result.get('error', 'Unknown error')}")
                failed_emails.append(email)
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            failed_emails.append(email)
        
        await asyncio.sleep(0.6)
    
    if failed_emails:
        print(f"\nRetrying {len(failed_emails)} failed emails after delay...")
        await asyncio.sleep(2)
        
        for email in failed_emails:
            print(f"Retry: {email}...")
            try:
                result = await send_platform_update_email(
                    to_email=email,
                    updates=UPDATES_LAST_24_HOURS,
                    app_url=app_url
                )
                if result.get("success"):
                    print(f"  ✓ Sent successfully to {email}")
                    success_count += 1
                else:
                    print(f"  ✗ Failed: {result.get('error', 'Unknown error')}")
                    fail_count += 1
            except Exception as e:
                print(f"  ✗ Error: {str(e)}")
                fail_count += 1
            
            await asyncio.sleep(0.6)
    
    print(f"\nComplete: {success_count} sent, {fail_count} failed")
    return {"success": success_count, "failed": fail_count}


if __name__ == "__main__":
    asyncio.run(send_update_to_all_users())
