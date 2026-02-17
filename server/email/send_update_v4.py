"""
Send platform update email v4 to 4 recipients with full email tracking.
Sends from TWO sender IDs: update05@founderconsole.ai and NFL@founderconsole.ai
"""
import os, sys, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from server.email.service import _send_email_sync
from server.api.email_tracking import create_tracked_link

CAMPAIGN = "founderconsole_update_feb2026_v4"
BASE_URL = "https://founderconsole.ai"

SENDERS = [
    "FounderConsole Updates <update05@founderconsole.ai>",
    "FounderConsole <NFL@founderconsole.ai>",
]

RECIPIENTS = [
    {"email": "nikita.luther@gmail.com", "id": "nikita_luther", "name": "Nikita"},
    {"email": "nikita@founderconsole.ai", "id": "nikita_founderconsole", "name": "Nikita"},
    {"email": "nikitafl2024@gmail.com", "id": "nikita_fl2024", "name": "Nikita"},
    {"email": "vysheshk@gmail.com", "id": "vyshesh_k", "name": "Vyshesh"},
]


def build_html(rcpt: dict, tracked_links: dict) -> str:
    name = rcpt["name"]
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FounderConsole - Latest Updates</title>
</head>
<body style="margin:0;padding:0;background-color:#0a0a0f;font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#e0e0e0;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0a0a0f;">
<tr><td align="center" style="padding:40px 20px;">
<table width="600" cellpadding="0" cellspacing="0" style="background-color:#111118;border-radius:12px;overflow:hidden;border:1px solid #1e1e2e;">

<!-- Header -->
<tr><td style="background:linear-gradient(135deg,#6366f1 0%,#8b5cf6 50%,#a855f7 100%);padding:40px 40px 30px;text-align:center;">
<h1 style="margin:0;font-size:28px;font-weight:700;color:#ffffff;letter-spacing:-0.5px;">FounderConsole</h1>
<p style="margin:8px 0 0;font-size:14px;color:rgba(255,255,255,0.85);letter-spacing:1px;text-transform:uppercase;">Latest Updates &middot; February 2026</p>
</td></tr>

<!-- Greeting -->
<tr><td style="padding:35px 40px 10px;">
<p style="margin:0;font-size:16px;line-height:1.6;color:#c4c4d4;">Hi {name},</p>
<p style="margin:14px 0 0;font-size:16px;line-height:1.6;color:#c4c4d4;">We've been shipping fast. Here's everything new &mdash; bug fixes, UX improvements, and platform upgrades. Try them out with the demo account below.</p>
</td></tr>

<!-- TRY DEMO CTA -->
<tr><td style="padding:20px 40px;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:linear-gradient(135deg,#1e1b4b,#312e81);border-radius:10px;border:1px solid #4338ca;">
<tr><td style="padding:25px 30px;text-align:center;">
<p style="margin:0 0 6px;font-size:13px;color:#a5b4fc;text-transform:uppercase;letter-spacing:1.5px;font-weight:600;">Try It Now</p>
<p style="margin:0 0 16px;font-size:15px;color:#c7d2fe;">Login with <strong style="color:#e0e7ff;">demo@founderconsole.ai</strong> / <strong style="color:#e0e7ff;">demo123</strong></p>
<a href="{tracked_links['demo']}" style="display:inline-block;background:#6366f1;color:#fff;padding:12px 36px;border-radius:8px;text-decoration:none;font-weight:600;font-size:15px;">Launch Demo Account</a>
<p style="margin:12px 0 0;font-size:13px;color:#818cf8;">Pre-loaded with TechFlow Analytics &mdash; explore every feature instantly</p>
</td></tr>
</table>
</td></tr>

<!-- LATEST BUG FIXES -->
<tr><td style="padding:10px 40px 5px;">
<h2 style="margin:0;font-size:20px;font-weight:700;color:#e0e7ff;border-bottom:1px solid #1e1e2e;padding-bottom:10px;">Latest Bug Fixes</h2>
</td></tr>
<tr><td style="padding:5px 40px 20px;font-size:14px;color:#9ca3af;line-height:1.7;">
<table width="100%" cellpadding="0" cellspacing="0">
<tr><td style="padding:6px 0;"><span style="display:inline-block;background:#22c55e;color:#fff;border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700;margin-right:8px;">FIXED</span> Overview page now loads data correctly &mdash; no more blank dashboard on first visit</td></tr>
<tr><td style="padding:6px 0;"><span style="display:inline-block;background:#22c55e;color:#fff;border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700;margin-right:8px;">FIXED</span> "N/Ax" formatting bug &mdash; metrics like Gross Margin no longer show broken suffixes</td></tr>
<tr><td style="padding:6px 0;"><span style="display:inline-block;background:#22c55e;color:#fff;border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700;margin-right:8px;">FIXED</span> Layout overflow &mdash; pages no longer clip under the sidebar on smaller screens</td></tr>
<tr><td style="padding:6px 0;"><span style="display:inline-block;background:#22c55e;color:#fff;border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700;margin-right:8px;">FIXED</span> Confidence badge truncation &mdash; "Confidence" label fully visible, no more "Confidenc..."</td></tr>
<tr><td style="padding:6px 0;"><span style="display:inline-block;background:#22c55e;color:#fff;border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700;margin-right:8px;">FIXED</span> Cleaned stale demo data &mdash; removed incorrect $7.7M revenue test records from Truth Engine</td></tr>
<tr><td style="padding:6px 0;"><span style="display:inline-block;background:#22c55e;color:#fff;border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700;margin-right:8px;">FIXED</span> KPI board data flickering and $0 flash on page navigation</td></tr>
<tr><td style="padding:6px 0;"><span style="display:inline-block;background:#22c55e;color:#fff;border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700;margin-right:8px;">FIXED</span> Churn rate KPI now displays correctly as a percentage</td></tr>
<tr><td style="padding:6px 0;"><span style="display:inline-block;background:#22c55e;color:#fff;border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700;margin-right:8px;">FIXED</span> Decision ranking uses correct scenario key mapping</td></tr>
</table>
</td></tr>

<!-- IMPROVEMENTS -->
<tr><td style="padding:10px 40px 5px;">
<h2 style="margin:0;font-size:20px;font-weight:700;color:#e0e7ff;border-bottom:1px solid #1e1e2e;padding-bottom:10px;">Improvements</h2>
</td></tr>
<tr><td style="padding:5px 40px 20px;font-size:14px;color:#9ca3af;line-height:1.7;">
<table width="100%" cellpadding="0" cellspacing="0">
<tr><td style="padding:6px 0;"><span style="display:inline-block;background:#3b82f6;color:#fff;border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700;margin-right:8px;">IMPROVED</span> Demo login auto-selects TechFlow Analytics &mdash; no manual company selection needed</td></tr>
<tr><td style="padding:6px 0;"><span style="display:inline-block;background:#3b82f6;color:#fff;border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700;margin-right:8px;">IMPROVED</span> KPI trend charts now load from 12 months of historical financial records</td></tr>
<tr><td style="padding:6px 0;"><span style="display:inline-block;background:#3b82f6;color:#fff;border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700;margin-right:8px;">IMPROVED</span> Email tracking with per-recipient UTM attribution, bot detection, and analytics dashboard</td></tr>
<tr><td style="padding:6px 0;"><span style="display:inline-block;background:#3b82f6;color:#fff;border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700;margin-right:8px;">IMPROVED</span> Production hardening &mdash; env-driven CORS, graceful shutdown, health endpoints</td></tr>
<tr><td style="padding:6px 0;"><span style="display:inline-block;background:#3b82f6;color:#fff;border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700;margin-right:8px;">IMPROVED</span> Consistent demo metrics across all sections: MRR $43,949 &middot; Cash $513,746 &middot; Runway 21.3mo &middot; Gross Margin 75%</td></tr>
</table>
</td></tr>

<!-- PLATFORM FEATURES RECAP -->
<tr><td style="padding:10px 40px 5px;">
<h2 style="margin:0;font-size:20px;font-weight:700;color:#e0e7ff;border-bottom:1px solid #1e1e2e;padding-bottom:10px;">Platform Features</h2>
</td></tr>
<tr><td style="padding:5px 40px 20px;">
<table width="100%" cellpadding="0" cellspacing="0">
<tr><td style="padding:10px 0;border-bottom:1px solid #1a1a2e;">
<p style="margin:0;font-size:15px;font-weight:600;color:#a78bfa;">AI Financial Copilot</p>
<p style="margin:4px 0 0;font-size:14px;color:#9ca3af;">Ask questions in plain English. Get answers grounded in your real financial data, simulations, and market context.</p>
</td></tr>
<tr><td style="padding:10px 0;border-bottom:1px solid #1a1a2e;">
<p style="margin:0;font-size:15px;font-weight:600;color:#a78bfa;">AI Governance Virtual Boardroom</p>
<p style="margin:4px 0 0;font-size:14px;color:#9ca3af;">14 specialized AI agents (CFO, CMO, CTO, Legal, Risk, Strategy, etc.) debate your decisions in a virtual boardroom.</p>
</td></tr>
<tr><td style="padding:10px 0;border-bottom:1px solid #1a1a2e;">
<p style="margin:0;font-size:15px;font-weight:600;color:#a78bfa;">Monte Carlo Simulations</p>
<p style="margin:4px 0 0;font-size:14px;color:#9ca3af;">Run 10,000+ probabilistic scenarios on your runway, burn, and revenue. See P10/P50/P90 outcomes.</p>
</td></tr>
<tr><td style="padding:10px 0;border-bottom:1px solid #1a1a2e;">
<p style="margin:0;font-size:15px;font-weight:600;color:#a78bfa;">Truth Engine</p>
<p style="margin:4px 0 0;font-size:14px;color:#9ca3af;">Upload messy CSVs, PDFs, or Excel files. 5-stage validation pipeline cleans and verifies every data point.</p>
</td></tr>
<tr><td style="padding:10px 0;">
<p style="margin:0;font-size:15px;font-weight:600;color:#a78bfa;">Fundraising OS</p>
<p style="margin:4px 0 0;font-size:14px;color:#9ca3af;">Cap table management, dilution modeling, round tracking, and an Investor Room &mdash; all in one place.</p>
</td></tr>
</table>
</td></tr>

<!-- HOW TO TEST -->
<tr><td style="padding:10px 40px 5px;">
<h2 style="margin:0;font-size:20px;font-weight:700;color:#e0e7ff;border-bottom:1px solid #1e1e2e;padding-bottom:10px;">How to Test</h2>
</td></tr>
<tr><td style="padding:5px 40px 20px;">
<table width="100%" cellpadding="0" cellspacing="0">
<tr><td style="padding:8px 0;">
<p style="margin:0;font-size:14px;color:#9ca3af;"><span style="display:inline-block;background:#6366f1;color:#fff;border-radius:50%;width:22px;height:22px;text-align:center;line-height:22px;font-size:12px;font-weight:700;margin-right:8px;">1</span><strong style="color:#e0e7ff;">Login</strong> with demo@founderconsole.ai / demo123 &mdash; TechFlow Analytics loads automatically</p>
</td></tr>
<tr><td style="padding:8px 0;">
<p style="margin:0;font-size:14px;color:#9ca3af;"><span style="display:inline-block;background:#6366f1;color:#fff;border-radius:50%;width:22px;height:22px;text-align:center;line-height:22px;font-size:12px;font-weight:700;margin-right:8px;">2</span><strong style="color:#e0e7ff;">Check Overview</strong> &mdash; Verify all metrics load without blank sections or formatting bugs</p>
</td></tr>
<tr><td style="padding:8px 0;">
<p style="margin:0;font-size:14px;color:#9ca3af;"><span style="display:inline-block;background:#6366f1;color:#fff;border-radius:50%;width:22px;height:22px;text-align:center;line-height:22px;font-size:12px;font-weight:700;margin-right:8px;">3</span><strong style="color:#e0e7ff;">Try AI Copilot</strong> &mdash; Ask "What's my runway?" or "Should I hire more engineers?"</p>
</td></tr>
<tr><td style="padding:8px 0;">
<p style="margin:0;font-size:14px;color:#9ca3af;"><span style="display:inline-block;background:#6366f1;color:#fff;border-radius:50%;width:22px;height:22px;text-align:center;line-height:22px;font-size:12px;font-weight:700;margin-right:8px;">4</span><strong style="color:#e0e7ff;">Run Simulations</strong> &mdash; Monte Carlo with pre-loaded scenarios, sensitivity charts, tornado plots</p>
</td></tr>
<tr><td style="padding:8px 0;">
<p style="margin:0;font-size:14px;color:#9ca3af;"><span style="display:inline-block;background:#6366f1;color:#fff;border-radius:50%;width:22px;height:22px;text-align:center;line-height:22px;font-size:12px;font-weight:700;margin-right:8px;">5</span><strong style="color:#e0e7ff;">Explore Fundraising</strong> &mdash; Cap table, dilution calculator, investor room</p>
</td></tr>
</table>
</td></tr>

<!-- CTA -->
<tr><td style="padding:20px 40px 30px;text-align:center;">
<a href="{tracked_links['app']}" style="display:inline-block;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;padding:14px 48px;border-radius:8px;text-decoration:none;font-weight:700;font-size:16px;">Open FounderConsole</a>
</td></tr>

<!-- Footer -->
<tr><td style="padding:20px 40px 30px;border-top:1px solid #1e1e2e;text-align:center;">
<p style="margin:0;font-size:12px;color:#6b7280;">FounderConsole &middot; AI-powered financial intelligence for startups</p>
<p style="margin:8px 0 0;font-size:12px;color:#6b7280;">
<a href="{tracked_links['feedback']}" style="color:#818cf8;text-decoration:none;">Share Feedback</a>
</p>
</td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""


def send_all():
    print(f"Sending update emails to {len(RECIPIENTS)} recipients from {len(SENDERS)} senders...")
    print(f"Campaign: {CAMPAIGN}")
    print(f"Senders: {SENDERS}")
    print()

    for sender in SENDERS:
        sender_tag = sender.split("<")[1].rstrip(">").split("@")[0].lower() if "<" in sender else sender.split("@")[0]
        campaign_with_sender = f"{CAMPAIGN}_{sender_tag}"
        print(f"--- Sending from: {sender} (campaign tag: {campaign_with_sender}) ---")
        print()

        for rcpt in RECIPIENTS:
            email = rcpt["email"]
            rid = rcpt["id"]

            utm_base = f"utm_source=email&utm_medium=update&utm_campaign={campaign_with_sender}&utm_content={rid}"

            demo_url = f"{BASE_URL}/auth?{utm_base}&utm_term=demo_cta"
            app_url = f"{BASE_URL}?{utm_base}&utm_term=open_app"
            feedback_url = f"{BASE_URL}/email-tracking/feedback?email={email}&campaign={campaign_with_sender}"

            demo_link = create_tracked_link(demo_url, recipient_email=email, recipient_id=rid, link_label="demo_cta", base_url=BASE_URL)
            app_link = create_tracked_link(app_url, recipient_email=email, recipient_id=rid, link_label="open_app", base_url=BASE_URL)
            feedback_link = create_tracked_link(feedback_url, recipient_email=email, recipient_id=rid, link_label="feedback_link", base_url=BASE_URL)

            tracked = {"demo": demo_link, "app": app_link, "feedback": feedback_link}
            html = build_html(rcpt, tracked)

            utm_params = {
                "utm_source": "email",
                "utm_medium": "update",
                "utm_campaign": campaign_with_sender,
                "utm_content": rid,
                "utm_term": "platform_update"
            }

            result = _send_email_sync(
                to=email,
                subject="FounderConsole - Bug Fixes & Platform Updates (Feb 2026)",
                html_content=html,
                from_email=sender,
                recipient_id=rid,
                campaign=campaign_with_sender,
                utm_params=utm_params
            )

            status = "SENT" if result.get("success") else "FAILED"
            msg_id = result.get("message_id", result.get("error", ""))
            print(f"  [{status}] {email} (id: {rid}) -> {msg_id}")

            time.sleep(1.5)

        print()

    print("Done! Track results at:")
    print(f"  {BASE_URL}/email-tracking/analytics?token=founderconsole-analytics-2026&campaign={CAMPAIGN}")


if __name__ == "__main__":
    send_all()
