"""
Send redesign update email v5 to recipients with full email tracking.
Explains the UX redesign and the thinking behind it from the MVP Deep Review.
"""
import os, sys, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from server.email.service import _send_email_sync
from server.api.email_tracking import create_tracked_link

CAMPAIGN = "founderconsole_redesign_feb2026_v5"
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
<title>FounderConsole - Major UX Redesign</title>
</head>
<body style="margin:0;padding:0;background-color:#0a0a0f;font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#e0e0e0;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0a0a0f;">
<tr><td align="center" style="padding:40px 20px;">
<table width="600" cellpadding="0" cellspacing="0" style="background-color:#111118;border-radius:12px;overflow:hidden;border:1px solid #1e1e2e;">

<!-- Header -->
<tr><td style="background:linear-gradient(135deg,#6366f1 0%,#8b5cf6 50%,#a855f7 100%);padding:40px 40px 30px;text-align:center;">
<h1 style="margin:0;font-size:28px;font-weight:700;color:#ffffff;letter-spacing:-0.5px;">FounderConsole</h1>
<p style="margin:8px 0 0;font-size:14px;color:rgba(255,255,255,0.85);letter-spacing:1px;text-transform:uppercase;">Major UX Redesign &middot; February 2026</p>
</td></tr>

<!-- Greeting -->
<tr><td style="padding:35px 40px 10px;">
<p style="margin:0;font-size:16px;line-height:1.6;color:#c4c4d4;">Hi {name},</p>
<p style="margin:14px 0 0;font-size:16px;line-height:1.6;color:#c4c4d4;">We just shipped a major redesign of the FounderConsole experience. This isn't a cosmetic refresh &mdash; it's a fundamental rethink of how founders interact with the platform, informed by a deep review from a poker decision theorist, an AI/ML engineer, and a world-class UX designer.</p>
<p style="margin:14px 0 0;font-size:16px;line-height:1.6;color:#c4c4d4;">Here's what changed and <strong style="color:#e0e7ff;">why</strong>.</p>
</td></tr>

<!-- TRY DEMO CTA -->
<tr><td style="padding:20px 40px;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:linear-gradient(135deg,#1e1b4b,#312e81);border-radius:10px;border:1px solid #4338ca;">
<tr><td style="padding:25px 30px;text-align:center;">
<p style="margin:0 0 6px;font-size:13px;color:#a5b4fc;text-transform:uppercase;letter-spacing:1.5px;font-weight:600;">See It Live</p>
<p style="margin:0 0 16px;font-size:15px;color:#c7d2fe;">Login with <strong style="color:#e0e7ff;">demo@founderconsole.ai</strong> / <strong style="color:#e0e7ff;">demo123</strong></p>
<a href="{tracked_links['demo']}" style="display:inline-block;background:#6366f1;color:#fff;padding:12px 36px;border-radius:8px;text-decoration:none;font-weight:600;font-size:15px;">Launch Demo Account</a>
</td></tr>
</table>
</td></tr>

<!-- THE CORE INSIGHT -->
<tr><td style="padding:10px 40px 5px;">
<h2 style="margin:0;font-size:20px;font-weight:700;color:#e0e7ff;border-bottom:1px solid #1e1e2e;padding-bottom:10px;">The Core Insight</h2>
</td></tr>
<tr><td style="padding:5px 40px 20px;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#1a1a2e;border-radius:8px;border-left:3px solid #6366f1;">
<tr><td style="padding:20px;">
<p style="margin:0;font-size:14px;color:#a5b4fc;font-weight:600;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">The Poker Principle</p>
<p style="margin:0;font-size:15px;color:#c4c4d4;line-height:1.7;font-style:italic;">"In poker, your edge comes from one thing &mdash; making better decisions with incomplete information. You don't need every stat on your HUD. You need the 4&ndash;5 numbers that actually change your action."</p>
<p style="margin:12px 0 0;font-size:14px;color:#9ca3af;line-height:1.6;">FounderConsole had 22+ navigation items across 7 sections. A founder opening it for the first time felt like they walked into a cockpit. The value proposition &mdash; <strong style="color:#e0e7ff;">"test your decisions before you make them"</strong> &mdash; was buried under metric catalogs, marketplace connectors, and admin settings.</p>
</td></tr>
</table>
</td></tr>

<!-- WHAT WE REDESIGNED -->
<tr><td style="padding:10px 40px 5px;">
<h2 style="margin:0;font-size:20px;font-weight:700;color:#e0e7ff;border-bottom:1px solid #1e1e2e;padding-bottom:10px;">What We Redesigned</h2>
</td></tr>
<tr><td style="padding:5px 40px 20px;font-size:14px;color:#9ca3af;line-height:1.7;">

<!-- Item 1: Workflow Stepper -->
<table width="100%" cellpadding="0" cellspacing="0">
<tr><td style="padding:12px 0;border-bottom:1px solid #1a1a2e;">
<p style="margin:0;font-size:15px;font-weight:600;color:#a78bfa;">1. Workflow Stepper Navigation</p>
<p style="margin:6px 0 0;font-size:14px;color:#9ca3af;line-height:1.6;">Replaced the cluttered sidebar with a clear 3-step flow: <strong style="color:#e0e7ff;">Know Your Truth</strong> &rarr; <strong style="color:#e0e7ff;">Simulate</strong> &rarr; <strong style="color:#e0e7ff;">Decide &amp; Act</strong>. This mirrors the poker decision framework: understand your position, model the outcomes, then commit.</p>
<p style="margin:6px 0 0;font-size:13px;color:#6366f1;font-style:italic;">Why: Founders don't think in "metric catalogs" and "scenario builders." They think in decisions. The stepper guides them through a decision workflow.</p>
</td></tr>

<!-- Item 2: Morning Briefing -->
<tr><td style="padding:12px 0;border-bottom:1px solid #1a1a2e;">
<p style="margin:0;font-size:15px;font-weight:600;color:#a78bfa;">2. Morning Briefing</p>
<p style="margin:6px 0 0;font-size:14px;color:#9ca3af;line-height:1.6;">When you open the app, you get a personalized 30-second summary: "Your MRR is $43,949. Cash: $513,746. Runway: 21.3 months." Plus an AI-generated simulation suggestion based on your current metrics.</p>
<p style="margin:6px 0 0;font-size:13px;color:#6366f1;font-style:italic;">Why: This is the daily hook. It turns FounderConsole from a tool founders use during board prep into something they check every morning &mdash; like checking their financial newspaper.</p>
</td></tr>

<!-- Item 3: Goal Tracker -->
<tr><td style="padding:12px 0;border-bottom:1px solid #1a1a2e;">
<p style="margin:0;font-size:15px;font-weight:600;color:#a78bfa;">3. Goal Tracking with Progress</p>
<p style="margin:6px 0 0;font-size:14px;color:#9ca3af;line-height:1.6;">Founders can now set goals like "Reach $100K MRR by Q3" or "Cut churn to 2%." The dashboard shows real-time progress bars. When they're off track, we automatically suggest corrective simulations.</p>
<p style="margin:6px 0 0;font-size:13px;color:#6366f1;font-style:italic;">Why: This gives founders a reason to check in daily &mdash; like checking a fitness tracker. It connects simulations to outcomes they actually care about.</p>
</td></tr>

<!-- Item 4: Competitive Benchmarks -->
<tr><td style="padding:12px 0;border-bottom:1px solid #1a1a2e;">
<p style="margin:0;font-size:15px;font-weight:600;color:#a78bfa;">4. Competitive Benchmark Pills</p>
<p style="margin:6px 0 0;font-size:14px;color:#9ca3af;line-height:1.6;">Every KPI card now shows where you rank: "Top 20% seed SaaS" for ARPU, "Above median" for Active Users, "Top 25% seed SaaS" for NRR. Founders don't just see their numbers &mdash; they see their numbers <em>in context</em>.</p>
<p style="margin:6px 0 0;font-size:13px;color:#6366f1;font-style:italic;">Why: Founders always ask "Is my 65% gross margin good?" Benchmark pills answer that instantly, without needing to Google or ask an advisor.</p>
</td></tr>

<!-- Item 5: Alert System -->
<tr><td style="padding:12px 0;border-bottom:1px solid #1a1a2e;">
<p style="margin:0;font-size:15px;font-weight:600;color:#a78bfa;">5. Alert Bell &amp; Proactive Nudges</p>
<p style="margin:6px 0 0;font-size:14px;color:#9ca3af;line-height:1.6;">Alerts moved from a standalone page to a header bell icon with badge count. Critical warnings (runway dropping, churn spiking) surface immediately instead of hiding behind a nav item with "0 alerts."</p>
<p style="margin:6px 0 0;font-size:13px;color:#6366f1;font-style:italic;">Why: A standalone Alerts page was always dormant. A bell icon creates urgency and keeps the dashboard clean.</p>
</td></tr>

<!-- Item 6: Briefing Modal -->
<tr><td style="padding:12px 0;">
<p style="margin:0;font-size:15px;font-weight:600;color:#a78bfa;">6. Confidence Score &amp; Briefing Modal</p>
<p style="margin:6px 0 0;font-size:14px;color:#9ca3af;line-height:1.6;">The header now shows a persistent Confidence percentage badge. Clicking "Briefing" opens a detailed modal with 4 metric cards, AI insights, and quick-action buttons to jump to simulation or fundraising.</p>
<p style="margin:6px 0 0;font-size:13px;color:#6366f1;font-style:italic;">Why: The Health Score / Confidence was buried in the Truth Scan page. Now it's always visible, building trust in data quality without requiring a separate page visit.</p>
</td></tr>
</table>

</td></tr>

<!-- THE DESIGN PHILOSOPHY -->
<tr><td style="padding:10px 40px 5px;">
<h2 style="margin:0;font-size:20px;font-weight:700;color:#e0e7ff;border-bottom:1px solid #1e1e2e;padding-bottom:10px;">The Design Philosophy</h2>
</td></tr>
<tr><td style="padding:5px 40px 20px;">
<table width="100%" cellpadding="0" cellspacing="0">
<tr><td style="padding:10px 0;border-bottom:1px solid #1a1a2e;">
<p style="margin:0;font-size:14px;color:#9ca3af;line-height:1.7;">
<span style="display:inline-block;background:#22c55e;color:#fff;border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700;margin-right:8px;">BEFORE</span> 22 nav items, 7 sections, 9 simulation sub-tabs. A cockpit.</p>
</td></tr>
<tr><td style="padding:10px 0;border-bottom:1px solid #1a1a2e;">
<p style="margin:0;font-size:14px;color:#9ca3af;line-height:1.7;">
<span style="display:inline-block;background:#6366f1;color:#fff;border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700;margin-right:8px;">AFTER</span> Workflow-driven navigation. Dashboard is truth. Simulate is exploration. Decide is action. Everything else is accessible but not in your face.</p>
</td></tr>
<tr><td style="padding:10px 0;">
<p style="margin:0;font-size:14px;color:#9ca3af;line-height:1.7;">
<span style="display:inline-block;background:#a855f7;color:#fff;border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700;margin-right:8px;">RESULT</span> 75% reduction in cognitive load. Features that drive daily engagement (briefing, goals, benchmarks) are front and center. The simulation experience becomes conversational, not wizard-based.</p>
</td></tr>
</table>
</td></tr>

<!-- WHAT'S NEXT -->
<tr><td style="padding:10px 40px 5px;">
<h2 style="margin:0;font-size:20px;font-weight:700;color:#e0e7ff;border-bottom:1px solid #1e1e2e;padding-bottom:10px;">What's Next</h2>
</td></tr>
<tr><td style="padding:5px 40px 20px;font-size:14px;color:#9ca3af;line-height:1.7;">
<table width="100%" cellpadding="0" cellspacing="0">
<tr><td style="padding:6px 0;"><span style="display:inline-block;background:#f59e0b;color:#fff;border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700;margin-right:8px;">PLANNED</span> Decision Journal &mdash; track decisions and compare predicted vs. actual outcomes at 30/60/90 days</td></tr>
<tr><td style="padding:6px 0;"><span style="display:inline-block;background:#f59e0b;color:#fff;border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700;margin-right:8px;">PLANNED</span> Conversational simulation &mdash; type "What if we hire 3 engineers?" instead of filling wizard forms</td></tr>
<tr><td style="padding:6px 0;"><span style="display:inline-block;background:#f59e0b;color:#fff;border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700;margin-right:8px;">PLANNED</span> Board Meeting Prep Generator &mdash; auto-generate board-ready reports from your data</td></tr>
<tr><td style="padding:6px 0;"><span style="display:inline-block;background:#f59e0b;color:#fff;border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700;margin-right:8px;">PLANNED</span> Proactive AI nudges &mdash; automatic mini-simulations when data shows something significant</td></tr>
</table>
</td></tr>

<!-- HOW TO TEST -->
<tr><td style="padding:10px 40px 5px;">
<h2 style="margin:0;font-size:20px;font-weight:700;color:#e0e7ff;border-bottom:1px solid #1e1e2e;padding-bottom:10px;">How to Test the Redesign</h2>
</td></tr>
<tr><td style="padding:5px 40px 20px;">
<table width="100%" cellpadding="0" cellspacing="0">
<tr><td style="padding:8px 0;">
<p style="margin:0;font-size:14px;color:#9ca3af;"><span style="display:inline-block;background:#6366f1;color:#fff;border-radius:50%;width:22px;height:22px;text-align:center;line-height:22px;font-size:12px;font-weight:700;margin-right:8px;">1</span><strong style="color:#e0e7ff;">Login</strong> &mdash; demo@founderconsole.ai / demo123 &mdash; notice the Morning Briefing banner at the top</p>
</td></tr>
<tr><td style="padding:8px 0;">
<p style="margin:0;font-size:14px;color:#9ca3af;"><span style="display:inline-block;background:#6366f1;color:#fff;border-radius:50%;width:22px;height:22px;text-align:center;line-height:22px;font-size:12px;font-weight:700;margin-right:8px;">2</span><strong style="color:#e0e7ff;">Check the Header</strong> &mdash; see the workflow stepper, alert bell, Briefing button, and Confidence badge</p>
</td></tr>
<tr><td style="padding:8px 0;">
<p style="margin:0;font-size:14px;color:#9ca3af;"><span style="display:inline-block;background:#6366f1;color:#fff;border-radius:50%;width:22px;height:22px;text-align:center;line-height:22px;font-size:12px;font-weight:700;margin-right:8px;">3</span><strong style="color:#e0e7ff;">Scroll to KPIs</strong> &mdash; notice the competitive benchmark pills under ARPU, Active Users, NRR, LTV:CAC</p>
</td></tr>
<tr><td style="padding:8px 0;">
<p style="margin:0;font-size:14px;color:#9ca3af;"><span style="display:inline-block;background:#6366f1;color:#fff;border-radius:50%;width:22px;height:22px;text-align:center;line-height:22px;font-size:12px;font-weight:700;margin-right:8px;">4</span><strong style="color:#e0e7ff;">Find Goal Tracker</strong> &mdash; 3 active goals (MRR, Runway, Churn) with progress bars and "+ Add Goal"</p>
</td></tr>
<tr><td style="padding:8px 0;">
<p style="margin:0;font-size:14px;color:#9ca3af;"><span style="display:inline-block;background:#6366f1;color:#fff;border-radius:50%;width:22px;height:22px;text-align:center;line-height:22px;font-size:12px;font-weight:700;margin-right:8px;">5</span><strong style="color:#e0e7ff;">Click through the Stepper</strong> &mdash; "Know Your Truth" &rarr; "Simulate" &rarr; "Decide &amp; Act" to see the workflow</p>
</td></tr>
</table>
</td></tr>

<!-- CTA -->
<tr><td style="padding:20px 40px 30px;text-align:center;">
<a href="{tracked_links['app']}" style="display:inline-block;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;padding:14px 48px;border-radius:8px;text-decoration:none;font-weight:700;font-size:16px;">See the Redesign</a>
</td></tr>

<!-- Footer -->
<tr><td style="padding:20px 40px 30px;border-top:1px solid #1e1e2e;text-align:center;">
<p style="margin:0;font-size:12px;color:#6b7280;">FounderConsole &middot; AI-powered financial intelligence for startups</p>
<p style="margin:8px 0 0;font-size:12px;color:#6b7280;">
<a href="{tracked_links['feedback']}" style="color:#818cf8;text-decoration:none;">Share Feedback on the Redesign</a>
</p>
</td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""


def send_all():
    print(f"Sending redesign update emails to {len(RECIPIENTS)} recipients from {len(SENDERS)} senders...")
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
                "utm_term": "redesign_update"
            }

            result = _send_email_sync(
                to=email,
                subject="FounderConsole - Major UX Redesign: The Thinking Behind It (Feb 2026)",
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
