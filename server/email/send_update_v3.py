"""
Send platform update email v3 to 4 recipients with full email tracking.
"""
import os, sys, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from server.email.service import _send_email_sync
from server.api.email_tracking import create_tracked_link

CAMPAIGN = "predixen_update_feb2026_v3"
BASE_URL = "https://predixen.app"

RECIPIENTS = [
    {"email": "nikita.luther@gmail.com", "id": "nikita_luther", "name": "Nikita"},
    {"email": "nikita@predixen.ai", "id": "nikita_predixen", "name": "Nikita"},
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
<title>Predixen Intelligence OS - Platform Update</title>
</head>
<body style="margin:0;padding:0;background-color:#0a0a0f;font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#e0e0e0;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0a0a0f;">
<tr><td align="center" style="padding:40px 20px;">
<table width="600" cellpadding="0" cellspacing="0" style="background-color:#111118;border-radius:12px;overflow:hidden;border:1px solid #1e1e2e;">

<!-- Header -->
<tr><td style="background:linear-gradient(135deg,#6366f1 0%,#8b5cf6 50%,#a855f7 100%);padding:40px 40px 30px;text-align:center;">
<h1 style="margin:0;font-size:28px;font-weight:700;color:#ffffff;letter-spacing:-0.5px;">Predixen Intelligence OS</h1>
<p style="margin:8px 0 0;font-size:14px;color:rgba(255,255,255,0.85);letter-spacing:1px;text-transform:uppercase;">Platform Update &middot; February 2026</p>
</td></tr>

<!-- Greeting -->
<tr><td style="padding:35px 40px 10px;">
<p style="margin:0;font-size:16px;line-height:1.6;color:#c4c4d4;">Hi {name},</p>
<p style="margin:14px 0 0;font-size:16px;line-height:1.6;color:#c4c4d4;">We've shipped major updates to Predixen. Here's everything new and how to get started.</p>
</td></tr>

<!-- TRY DEMO CTA -->
<tr><td style="padding:20px 40px;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:linear-gradient(135deg,#1e1b4b,#312e81);border-radius:10px;border:1px solid #4338ca;">
<tr><td style="padding:25px 30px;text-align:center;">
<p style="margin:0 0 6px;font-size:13px;color:#a5b4fc;text-transform:uppercase;letter-spacing:1.5px;font-weight:600;">Try It Now</p>
<p style="margin:0 0 16px;font-size:15px;color:#c7d2fe;">Login with <strong style="color:#e0e7ff;">demo@predixen.ai</strong> / <strong style="color:#e0e7ff;">demo123</strong></p>
<a href="{tracked_links['demo']}" style="display:inline-block;background:#6366f1;color:#fff;padding:12px 36px;border-radius:8px;text-decoration:none;font-weight:600;font-size:15px;">Launch Demo Account</a>
<p style="margin:12px 0 0;font-size:13px;color:#818cf8;">Pre-loaded with TechFlow Analytics &mdash; explore every feature instantly</p>
</td></tr>
</table>
</td></tr>

<!-- WHAT THE PLATFORM DOES -->
<tr><td style="padding:10px 40px 5px;">
<h2 style="margin:0;font-size:20px;font-weight:700;color:#e0e7ff;border-bottom:1px solid #1e1e2e;padding-bottom:10px;">What Predixen Does</h2>
</td></tr>
<tr><td style="padding:5px 40px 20px;">
<table width="100%" cellpadding="0" cellspacing="0">
<tr><td style="padding:10px 0;border-bottom:1px solid #1a1a2e;">
<p style="margin:0;font-size:15px;font-weight:600;color:#a78bfa;">AI Financial Copilot</p>
<p style="margin:4px 0 0;font-size:14px;color:#9ca3af;">Ask questions in plain English. Get answers grounded in your real financial data, simulations, and market context &mdash; never hallucinated numbers.</p>
</td></tr>
<tr><td style="padding:10px 0;border-bottom:1px solid #1a1a2e;">
<p style="margin:0;font-size:15px;font-weight:600;color:#a78bfa;">Monte Carlo Simulations</p>
<p style="margin:4px 0 0;font-size:14px;color:#9ca3af;">Run 10,000+ probabilistic scenarios on your runway, burn, and revenue. See P10/P50/P90 outcomes so you plan for uncertainty, not assumptions.</p>
</td></tr>
<tr><td style="padding:10px 0;border-bottom:1px solid #1a1a2e;">
<p style="margin:0;font-size:15px;font-weight:600;color:#a78bfa;">Truth Engine</p>
<p style="margin:4px 0 0;font-size:14px;color:#9ca3af;">Upload messy CSVs, PDFs, or Excel files. Our 5-stage validation pipeline cleans, normalizes, and verifies every data point before it touches a simulation.</p>
</td></tr>
<tr><td style="padding:10px 0;border-bottom:1px solid #1a1a2e;">
<p style="margin:0;font-size:15px;font-weight:600;color:#a78bfa;">Scenario Planning & Versioning</p>
<p style="margin:4px 0 0;font-size:14px;color:#9ca3af;">Compare base, best, and worst case scenarios side by side. Version control every assumption. Rank decisions by survival probability.</p>
</td></tr>
<tr><td style="padding:10px 0;">
<p style="margin:0;font-size:15px;font-weight:600;color:#a78bfa;">Fundraising OS</p>
<p style="margin:4px 0 0;font-size:14px;color:#9ca3af;">Cap table management, dilution modeling, round tracking, and an Investor Room to share materials &mdash; all in one place.</p>
</td></tr>
</table>
</td></tr>

<!-- NEW FEATURES -->
<tr><td style="padding:10px 40px 5px;">
<h2 style="margin:0;font-size:20px;font-weight:700;color:#e0e7ff;border-bottom:1px solid #1e1e2e;padding-bottom:10px;">What's New</h2>
</td></tr>
<tr><td style="padding:5px 40px 20px;">
<table width="100%" cellpadding="0" cellspacing="0">

<tr><td style="padding:12px 0;border-bottom:1px solid #1a1a2e;">
<table cellpadding="0" cellspacing="0"><tr>
<td style="vertical-align:top;padding-right:12px;"><span style="display:inline-block;background:#6366f1;color:#fff;border-radius:6px;padding:3px 10px;font-size:11px;font-weight:700;text-transform:uppercase;">New</span></td>
<td><p style="margin:0;font-size:15px;font-weight:600;color:#c4b5fd;">AI Governance Virtual Boardroom</p>
<p style="margin:4px 0 0;font-size:13px;color:#9ca3af;">14 specialized AI agents (CFO, CMO, CTO, Legal, Risk, Strategy, etc.) debate your decisions in a virtual boardroom. Get multi-perspective analysis before committing.</p></td>
</tr></table>
</td></tr>

<tr><td style="padding:12px 0;border-bottom:1px solid #1a1a2e;">
<table cellpadding="0" cellspacing="0"><tr>
<td style="vertical-align:top;padding-right:12px;"><span style="display:inline-block;background:#6366f1;color:#fff;border-radius:6px;padding:3px 10px;font-size:11px;font-weight:700;text-transform:uppercase;">New</span></td>
<td><p style="margin:0;font-size:15px;font-weight:600;color:#c4b5fd;">Multi-LLM Router</p>
<p style="margin:4px 0 0;font-size:13px;color:#9ca3af;">Automatically picks the best AI model (OpenAI, Claude, Gemini) for each task. Complex reasoning goes to Claude, fast queries to Gemini, financial analysis to GPT-4o.</p></td>
</tr></table>
</td></tr>

<tr><td style="padding:12px 0;border-bottom:1px solid #1a1a2e;">
<table cellpadding="0" cellspacing="0"><tr>
<td style="vertical-align:top;padding-right:12px;"><span style="display:inline-block;background:#6366f1;color:#fff;border-radius:6px;padding:3px 10px;font-size:11px;font-weight:700;text-transform:uppercase;">New</span></td>
<td><p style="margin:0;font-size:15px;font-weight:600;color:#c4b5fd;">Decision Advisor Agent</p>
<p style="margin:4px 0 0;font-size:13px;color:#9ca3af;">Ask "Should we hire 3 engineers or spend on marketing?" &mdash; it auto-runs simulations, maps financial levers, and gives an opinionated recommendation with risk scores.</p></td>
</tr></table>
</td></tr>

<tr><td style="padding:12px 0;border-bottom:1px solid #1a1a2e;">
<table cellpadding="0" cellspacing="0"><tr>
<td style="vertical-align:top;padding-right:12px;"><span style="display:inline-block;background:#6366f1;color:#fff;border-radius:6px;padding:3px 10px;font-size:11px;font-weight:700;text-transform:uppercase;">New</span></td>
<td><p style="margin:0;font-size:15px;font-weight:600;color:#c4b5fd;">Copilot Trust Module</p>
<p style="margin:4px 0 0;font-size:13px;color:#9ca3af;">Every number the AI quotes is verified against simulation data with full provenance (run ID, timestamp, snapshot). No fabricated stats &mdash; ever.</p></td>
</tr></table>
</td></tr>

<tr><td style="padding:12px 0;border-bottom:1px solid #1a1a2e;">
<table cellpadding="0" cellspacing="0"><tr>
<td style="vertical-align:top;padding-right:12px;"><span style="display:inline-block;background:#6366f1;color:#fff;border-radius:6px;padding:3px 10px;font-size:11px;font-weight:700;text-transform:uppercase;">New</span></td>
<td><p style="margin:0;font-size:15px;font-weight:600;color:#c4b5fd;">Sensitivity Analysis & Tornado Charts</p>
<p style="margin:4px 0 0;font-size:13px;color:#9ca3af;">See which single variable moves your runway the most. Tornado charts rank drivers so you focus on what actually matters.</p></td>
</tr></table>
</td></tr>

<tr><td style="padding:12px 0;">
<table cellpadding="0" cellspacing="0"><tr>
<td style="vertical-align:top;padding-right:12px;"><span style="display:inline-block;background:#6366f1;color:#fff;border-radius:6px;padding:3px 10px;font-size:11px;font-weight:700;text-transform:uppercase;">New</span></td>
<td><p style="margin:0;font-size:15px;font-weight:600;color:#c4b5fd;">Email Tracking & Analytics</p>
<p style="margin:4px 0 0;font-size:13px;color:#9ca3af;">Full delivery, open, and click tracking with bot detection, per-recipient UTM attribution, and a real-time analytics dashboard.</p></td>
</tr></table>
</td></tr>

</table>
</td></tr>

<!-- BUG FIXES -->
<tr><td style="padding:10px 40px 5px;">
<h2 style="margin:0;font-size:20px;font-weight:700;color:#e0e7ff;border-bottom:1px solid #1e1e2e;padding-bottom:10px;">Bug Fixes & Improvements</h2>
</td></tr>
<tr><td style="padding:5px 40px 20px;font-size:14px;color:#9ca3af;line-height:1.7;">
<table width="100%" cellpadding="0" cellspacing="0">
<tr><td style="padding:4px 0;"><span style="color:#22c55e;font-weight:600;">Fixed</span> &mdash; KPI board data flickering and $0 flash on page navigation</td></tr>
<tr><td style="padding:4px 0;"><span style="color:#22c55e;font-weight:600;">Fixed</span> &mdash; Overview page crash from React hooks ordering issue</td></tr>
<tr><td style="padding:4px 0;"><span style="color:#22c55e;font-weight:600;">Fixed</span> &mdash; Churn rate KPI now displays correctly as a percentage</td></tr>
<tr><td style="padding:4px 0;"><span style="color:#22c55e;font-weight:600;">Fixed</span> &mdash; Decision ranking uses correct scenario key mapping</td></tr>
<tr><td style="padding:4px 0;"><span style="color:#22c55e;font-weight:600;">Fixed</span> &mdash; Simulation timeseries & scenario cache invalidation after runs</td></tr>
<tr><td style="padding:4px 0;"><span style="color:#22c55e;font-weight:600;">Fixed</span> &mdash; Metric catalog auto-initializes per company on first visit</td></tr>
<tr><td style="padding:4px 0;"><span style="color:#3b82f6;font-weight:600;">Improved</span> &mdash; Demo login auto-selects TechFlow Analytics company</td></tr>
<tr><td style="padding:4px 0;"><span style="color:#3b82f6;font-weight:600;">Improved</span> &mdash; KPI trend charts load from 12 months of historical records</td></tr>
<tr><td style="padding:4px 0;"><span style="color:#3b82f6;font-weight:600;">Improved</span> &mdash; Production hardening: env-driven CORS, graceful shutdown, health endpoints</td></tr>
</table>
</td></tr>

<!-- HOW TO USE THE DEMO -->
<tr><td style="padding:10px 40px 5px;">
<h2 style="margin:0;font-size:20px;font-weight:700;color:#e0e7ff;border-bottom:1px solid #1e1e2e;padding-bottom:10px;">How to Explore the Demo</h2>
</td></tr>
<tr><td style="padding:5px 40px 20px;">
<table width="100%" cellpadding="0" cellspacing="0">
<tr><td style="padding:8px 0;">
<p style="margin:0;font-size:14px;color:#9ca3af;"><span style="display:inline-block;background:#6366f1;color:#fff;border-radius:50%;width:22px;height:22px;text-align:center;line-height:22px;font-size:12px;font-weight:700;margin-right:8px;">1</span><strong style="color:#e0e7ff;">Login</strong> with demo@predixen.ai / demo123 &mdash; TechFlow Analytics loads automatically</p>
</td></tr>
<tr><td style="padding:8px 0;">
<p style="margin:0;font-size:14px;color:#9ca3af;"><span style="display:inline-block;background:#6366f1;color:#fff;border-radius:50%;width:22px;height:22px;text-align:center;line-height:22px;font-size:12px;font-weight:700;margin-right:8px;">2</span><strong style="color:#e0e7ff;">Overview Dashboard</strong> &mdash; See financial health score, runway, burn rate, and KPI trends at a glance</p>
</td></tr>
<tr><td style="padding:8px 0;">
<p style="margin:0;font-size:14px;color:#9ca3af;"><span style="display:inline-block;background:#6366f1;color:#fff;border-radius:50%;width:22px;height:22px;text-align:center;line-height:22px;font-size:12px;font-weight:700;margin-right:8px;">3</span><strong style="color:#e0e7ff;">AI Copilot</strong> &mdash; Ask "What's my runway?" or "Should I raise now?" and get data-backed answers</p>
</td></tr>
<tr><td style="padding:8px 0;">
<p style="margin:0;font-size:14px;color:#9ca3af;"><span style="display:inline-block;background:#6366f1;color:#fff;border-radius:50%;width:22px;height:22px;text-align:center;line-height:22px;font-size:12px;font-weight:700;margin-right:8px;">4</span><strong style="color:#e0e7ff;">Simulations</strong> &mdash; Run Monte Carlo with pre-loaded scenarios, view probability fans and sensitivity charts</p>
</td></tr>
<tr><td style="padding:8px 0;">
<p style="margin:0;font-size:14px;color:#9ca3af;"><span style="display:inline-block;background:#6366f1;color:#fff;border-radius:50%;width:22px;height:22px;text-align:center;line-height:22px;font-size:12px;font-weight:700;margin-right:8px;">5</span><strong style="color:#e0e7ff;">Truth Engine</strong> &mdash; Upload a CSV or PDF and watch it get validated, cleaned, and scored</p>
</td></tr>
<tr><td style="padding:8px 0;">
<p style="margin:0;font-size:14px;color:#9ca3af;"><span style="display:inline-block;background:#6366f1;color:#fff;border-radius:50%;width:22px;height:22px;text-align:center;line-height:22px;font-size:12px;font-weight:700;margin-right:8px;">6</span><strong style="color:#e0e7ff;">Fundraising</strong> &mdash; Explore cap table, dilution calculator, and investor room</p>
</td></tr>
</table>
</td></tr>

<!-- CTA -->
<tr><td style="padding:20px 40px 30px;text-align:center;">
<a href="{tracked_links['app']}" style="display:inline-block;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;padding:14px 48px;border-radius:8px;text-decoration:none;font-weight:700;font-size:16px;">Open Predixen</a>
</td></tr>

<!-- Footer -->
<tr><td style="padding:20px 40px 30px;border-top:1px solid #1e1e2e;text-align:center;">
<p style="margin:0;font-size:12px;color:#6b7280;">Predixen Intelligence OS &middot; AI-powered financial intelligence for startups</p>
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
    print(f"Sending update emails to {len(RECIPIENTS)} recipients...")
    print(f"Campaign: {CAMPAIGN}")
    print()

    for rcpt in RECIPIENTS:
        email = rcpt["email"]
        rid = rcpt["id"]

        utm_base = f"utm_source=email&utm_medium=update&utm_campaign={CAMPAIGN}&utm_content={rid}"

        demo_url = f"{BASE_URL}/auth?{utm_base}&utm_term=demo_cta"
        app_url = f"{BASE_URL}?{utm_base}&utm_term=open_app"
        feedback_url = f"{BASE_URL}/email-tracking/feedback?email={email}&campaign={CAMPAIGN}"

        demo_link = create_tracked_link(demo_url, recipient_email=email, recipient_id=rid, link_label="demo_cta", base_url=BASE_URL)
        app_link = create_tracked_link(app_url, recipient_email=email, recipient_id=rid, link_label="open_app", base_url=BASE_URL)
        feedback_link = create_tracked_link(feedback_url, recipient_email=email, recipient_id=rid, link_label="feedback_link", base_url=BASE_URL)

        tracked = {"demo": demo_link, "app": app_link, "feedback": feedback_link}
        html = build_html(rcpt, tracked)

        utm_params = {
            "utm_source": "email",
            "utm_medium": "update",
            "utm_campaign": CAMPAIGN,
            "utm_content": rid,
            "utm_term": "platform_update"
        }

        result = _send_email_sync(
            to=email,
            subject="Predixen Intelligence OS - Full Platform Update (Feb 2026)",
            html_content=html,
            recipient_id=rid,
            campaign=CAMPAIGN,
            utm_params=utm_params
        )

        status = "SENT" if result.get("success") else "FAILED"
        msg_id = result.get("message_id", result.get("error", ""))
        print(f"  [{status}] {email} (id: {rid}) -> {msg_id}")

        time.sleep(1.5)

    print()
    print("Done! Track results at:")
    print(f"  {BASE_URL}/email-tracking/analytics?token=predixen-analytics-2026&campaign={CAMPAIGN}")


if __name__ == "__main__":
    send_all()
