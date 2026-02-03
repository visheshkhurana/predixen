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
        "title": "Connector Marketplace",
        "description": "New integration marketplace with 20+ connectors including Stripe, QuickBooks, Xero, HubSpot, Salesforce, Google Analytics, and more. Browse, search, filter by category, and connect your data sources with guided setup wizards."
    },
    {
        "title": "Enhanced KPI Dashboard with Time-Series Trends",
        "description": "Financial Trends chart now shows MRR, Cash, Runway, and Churn projections over time with 3/6/12 month toggle buttons. Dual Y-axes display financial metrics alongside runway and churn percentages."
    },
    {
        "title": "New KPI Metrics: ARPU, NRR & Active Users",
        "description": "Added Average Revenue Per User (ARPU), Net Revenue Retention (NRR), and Active Users cards with detailed tooltips explaining formulas, good ranges, and warning thresholds."
    },
    {
        "title": "LTV:CAC Ratio Health Indicators",
        "description": "Visual color-coded health status for LTV:CAC ratio - green for healthy (>3x), yellow for warning (2-3x), and red for critical (<2x). Shows exact LTV and CAC values with contextual badges."
    },
    {
        "title": "Segment Analysis Feature",
        "description": "Break down your metrics by acquisition channel (Organic, Paid Search, Content, Referral), customer tier (Enterprise, Pro, Starter), or region (North America, Europe, APAC). View CAC, LTV, LTV:CAC, and churn by segment."
    },
    {
        "title": "Industry Benchmark Comparisons",
        "description": "Real-time benchmark data powered by Perplexity AI. Compare your metrics against industry standards for your stage (Seed, Series A/B/C) with automatic sourcing and citations."
    },
    {
        "title": "Connector Detail Drawer",
        "description": "Click any connector to see detailed information including data collected, sync behavior, security permissions, metrics unlocked, and setup complexity before connecting."
    },
    {
        "title": "Data Source Setup Wizard",
        "description": "Step-by-step wizard for connecting data sources with auth-type-specific flows (OAuth, API Key, Database Connection, Webhook, File Upload). Includes connection testing and entity selection."
    },
    {
        "title": "Enhanced Metric Tooltips",
        "description": "Every KPI now has detailed tooltips showing the calculation formula, what makes a 'good' range, and warning thresholds. Helps founders understand exactly what each metric means."
    },
    {
        "title": "Trust & Security Indicators",
        "description": "All integrations clearly show read-only access badges, encryption status, and data handling policies. Connectors display native/beta badges and real-time/webhook support."
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
