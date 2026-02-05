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
        "title": "Advanced Simulation Analysis Tab",
        "description": "New 'Analysis' tab in Scenarios with 4 powerful simulation tools: Tornado Chart for sensitivity analysis, What-If Explorer for real-time scenario modeling, Stress Test Panel with 6 pre-built crisis scenarios, and Reverse Stress Test for breaking point analysis."
    },
    {
        "title": "Tornado Chart - Sensitivity Analysis",
        "description": "Visual bar chart showing which variables have the biggest impact on your runway. Instantly see how changes to revenue growth, churn, gross margin, and expenses affect your financial trajectory."
    },
    {
        "title": "What-If Explorer",
        "description": "Interactive sliders let you adjust revenue growth, churn rate, gross margin, burn rate, and fundraising amount in real-time. See immediate impact on runway, 18-month survival probability, and projected cash position."
    },
    {
        "title": "Stress Test Panel",
        "description": "6 pre-built crisis scenarios: Mild Recession, Severe Downturn, Funding Winter, Key Customer Loss, Competitive Disruption, and Hiring Freeze. Each applies realistic adjustments to your financial model to simulate worst-case scenarios."
    },
    {
        "title": "Reverse Stress Test - Breaking Point Analysis",
        "description": "Discover exactly what would need to go wrong to deplete your runway. Shows the percentage increase in churn, decrease in growth, or expense increase that would push your company to critical status."
    },
    {
        "title": "Bug Fixes & Improvements",
        "description": "Fixed stress test template application to properly handle all adjustments including expense components. Improved financial state calculations with better data sourcing from simulation results. Enhanced baseline results alignment with actual Monte Carlo outputs."
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
    
    subject = "Predixen Intelligence OS - New Advanced Simulation Features"
    
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
