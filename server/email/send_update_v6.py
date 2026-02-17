"""
Send simulation engine update email v6 to 4 recipients with full email tracking.
Covers Round 2-3 simulation bug fixes, validation, and survival probability improvements.
"""
import os, sys, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from server.email.service import _send_email_sync
from server.api.email_tracking import create_tracked_link

CAMPAIGN = "founderconsole_simulation_update_feb2026_v6"
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
<title>FounderConsole - Simulation Engine Hardened</title>
</head>
<body style="margin:0;padding:0;background-color:#0a0a0f;font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#e0e0e0;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0a0a0f;">
<tr><td align="center" style="padding:40px 20px;">
<table width="600" cellpadding="0" cellspacing="0" style="background-color:#111118;border-radius:12px;overflow:hidden;border:1px solid #1e1e2e;">

<!-- Header -->
<tr><td style="background:linear-gradient(135deg,#059669 0%,#10b981 50%,#34d399 100%);padding:40px 40px 30px;text-align:center;">
<h1 style="margin:0;font-size:28px;font-weight:700;color:#ffffff;letter-spacing:-0.5px;">FounderConsole</h1>
<p style="margin:8px 0 0;font-size:14px;color:rgba(255,255,255,0.9);letter-spacing:1px;text-transform:uppercase;">Simulation Engine Hardened &middot; February 2026</p>
</td></tr>

<!-- Greeting -->
<tr><td style="padding:35px 40px 10px;">
<p style="margin:0;font-size:16px;line-height:1.6;color:#c4c4d4;">Hi {name},</p>
<p style="margin:14px 0 0;font-size:16px;line-height:1.6;color:#c4c4d4;">We just shipped <strong style="color:#e0e7ff;">16 critical fixes</strong> to the simulation engine. The Monte Carlo projections are now significantly more accurate, edge cases are handled gracefully, and invalid inputs are caught before they corrupt your results.</p>
<p style="margin:14px 0 0;font-size:16px;line-height:1.6;color:#c4c4d4;">Here's what changed.</p>
</td></tr>

<!-- TRY DEMO CTA -->
<tr><td style="padding:20px 40px;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:linear-gradient(135deg,#064e3b,#065f46);border-radius:10px;border:1px solid #059669;">
<tr><td style="padding:25px 30px;text-align:center;">
<p style="margin:0 0 6px;font-size:13px;color:#6ee7b7;text-transform:uppercase;letter-spacing:1.5px;font-weight:600;">Try It Now</p>
<p style="margin:0 0 16px;font-size:15px;color:#a7f3d0;">Login with <strong style="color:#ecfdf5;">demo@founderconsole.ai</strong> / <strong style="color:#ecfdf5;">demo123</strong></p>
<a href="{tracked_links['demo']}" style="display:inline-block;background:#059669;color:#fff;padding:12px 36px;border-radius:8px;text-decoration:none;font-weight:600;font-size:15px;">Run a Simulation</a>
</td></tr>
</table>
</td></tr>

<!-- ROUND 1: Growth Rate Fix -->
<tr><td style="padding:10px 40px 5px;">
<h2 style="margin:0;font-size:20px;font-weight:700;color:#e0e7ff;border-bottom:1px solid #1e1e2e;padding-bottom:10px;">Critical Fix: Growth Rate Sync</h2>
</td></tr>
<tr><td style="padding:5px 40px 20px;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#1a1a2e;border-radius:8px;border-left:3px solid #ef4444;">
<tr><td style="padding:20px;">
<p style="margin:0;font-size:14px;color:#fca5a5;font-weight:600;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Bug Squashed</p>
<p style="margin:0;font-size:15px;color:#c4c4d4;line-height:1.7;">Previously, entering 10% growth in Data Input would save to the financial record but <strong style="color:#fca5a5;">never sync to the simulation engine</strong>, which saw 0% growth. Simulations were projecting flat revenue despite positive growth inputs.</p>
<p style="margin:12px 0 0;font-size:14px;color:#9ca3af;line-height:1.6;"><span style="display:inline-block;background:#22c55e;color:#fff;border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700;margin-right:6px;">FIXED</span> Growth rate now syncs to truth scan on every save, and the simulation engine falls back to the financial record if truth scan shows 0%.</p>
</td></tr>
</table>
</td></tr>

<!-- ROUND 2: Simulation Accuracy -->
<tr><td style="padding:10px 40px 5px;">
<h2 style="margin:0;font-size:20px;font-weight:700;color:#e0e7ff;border-bottom:1px solid #1e1e2e;padding-bottom:10px;">10 Simulation Accuracy Fixes</h2>
</td></tr>
<tr><td style="padding:5px 40px 20px;font-size:14px;color:#9ca3af;line-height:1.7;">

<table width="100%" cellpadding="0" cellspacing="0">
<tr><td style="padding:10px 0;border-bottom:1px solid #1a1a2e;">
<p style="margin:0;font-size:15px;font-weight:600;color:#a78bfa;">Timeseries Data</p>
<p style="margin:4px 0 0;font-size:14px;color:#9ca3af;">Revenue, cash, and burn charts now show correct month-by-month projections instead of empty graphs.</p>
</td></tr>
<tr><td style="padding:10px 0;border-bottom:1px solid #1a1a2e;">
<p style="margin:0;font-size:15px;font-weight:600;color:#a78bfa;">Runway Cap</p>
<p style="margin:4px 0 0;font-size:14px;color:#9ca3af;">Runway projections are now capped at 24 months (the simulation horizon) instead of showing impossible 200+ month values.</p>
</td></tr>
<tr><td style="padding:10px 0;border-bottom:1px solid #1a1a2e;">
<p style="margin:0;font-size:15px;font-weight:600;color:#a78bfa;">Churn & CAC Parameters</p>
<p style="margin:4px 0 0;font-size:14px;color:#9ca3af;">Churn rate and CAC change sliders now correctly flow through to Monte Carlo simulations. Previously these were ignored entirely.</p>
</td></tr>
<tr><td style="padding:10px 0;border-bottom:1px solid #1a1a2e;">
<p style="margin:0;font-size:15px;font-weight:600;color:#a78bfa;">Break-Even Calculation</p>
<p style="margin:4px 0 0;font-size:14px;color:#9ca3af;">Break-even month now uses P10/P50/P90 percentile analysis instead of always showing the same value across scenarios.</p>
</td></tr>
<tr><td style="padding:10px 0;">
<p style="margin:0;font-size:15px;font-weight:600;color:#a78bfa;">Data Consistency</p>
<p style="margin:4px 0 0;font-size:14px;color:#9ca3af;">Metrics header (MRR, Cash, Runway, LTV:CAC) stays consistent across all pages. No more flashing "$0" on navigation.</p>
</td></tr>
</table>

</td></tr>

<!-- ROUND 3: Validation & Safety -->
<tr><td style="padding:10px 40px 5px;">
<h2 style="margin:0;font-size:20px;font-weight:700;color:#e0e7ff;border-bottom:1px solid #1e1e2e;padding-bottom:10px;">Input Validation & Safety</h2>
</td></tr>
<tr><td style="padding:5px 40px 20px;font-size:14px;color:#9ca3af;line-height:1.7;">

<table width="100%" cellpadding="0" cellspacing="0">
<tr><td style="padding:10px 0;border-bottom:1px solid #1a1a2e;">
<p style="margin:0;font-size:15px;font-weight:600;color:#34d399;">Negative Fundraise Prevention</p>
<p style="margin:4px 0 0;font-size:14px;color:#9ca3af;">The API now rejects negative fundraise amounts with a clear error instead of simulating cash destruction.</p>
</td></tr>
<tr><td style="padding:10px 0;border-bottom:1px solid #1a1a2e;">
<p style="margin:0;font-size:15px;font-weight:600;color:#34d399;">Burn Reduction Guard</p>
<p style="margin:4px 0 0;font-size:14px;color:#9ca3af;">Burn reduction is now clamped to 0&ndash;100%. Values over 100% (which would create negative expenses) are rejected at the API and clamped in the engine.</p>
</td></tr>
<tr><td style="padding:10px 0;border-bottom:1px solid #1a1a2e;">
<p style="margin:0;font-size:15px;font-weight:600;color:#34d399;">Fundraise Timing Fix</p>
<p style="margin:4px 0 0;font-size:14px;color:#9ca3af;">Setting fundraise month to 0 now auto-corrects to month 1 (immediate) instead of silently never injecting the cash.</p>
</td></tr>
<tr><td style="padding:10px 0;">
<p style="margin:0;font-size:15px;font-weight:600;color:#34d399;">Survival Probability Compat</p>
<p style="margin:4px 0 0;font-size:14px;color:#9ca3af;">Old simulation runs now display survival probability correctly. Previously, switching between scenarios showed "?%" for older simulations.</p>
</td></tr>
</table>

</td></tr>

<!-- METRICS CARD -->
<tr><td style="padding:10px 40px 20px;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:linear-gradient(135deg,#1e1b4b,#312e81);border-radius:10px;border:1px solid #4338ca;">
<tr><td style="padding:20px 25px;">
<p style="margin:0 0 12px;font-size:13px;color:#a5b4fc;text-transform:uppercase;letter-spacing:1.5px;font-weight:600;">Demo Account Metrics (Consistent Everywhere)</p>
<table width="100%" cellpadding="0" cellspacing="0">
<tr>
<td width="25%" style="text-align:center;padding:8px;">
<p style="margin:0;font-size:22px;font-weight:700;color:#e0e7ff;">$43.9K</p>
<p style="margin:2px 0 0;font-size:11px;color:#a5b4fc;">MRR</p>
</td>
<td width="25%" style="text-align:center;padding:8px;">
<p style="margin:0;font-size:22px;font-weight:700;color:#e0e7ff;">$513.7K</p>
<p style="margin:2px 0 0;font-size:11px;color:#a5b4fc;">Cash</p>
</td>
<td width="25%" style="text-align:center;padding:8px;">
<p style="margin:0;font-size:22px;font-weight:700;color:#e0e7ff;">21.3mo</p>
<p style="margin:2px 0 0;font-size:11px;color:#a5b4fc;">Runway</p>
</td>
<td width="25%" style="text-align:center;padding:8px;">
<p style="margin:0;font-size:22px;font-weight:700;color:#e0e7ff;">3.2x</p>
<p style="margin:2px 0 0;font-size:11px;color:#a5b4fc;">LTV:CAC</p>
</td>
</tr>
</table>
</td></tr>
</table>
</td></tr>

<!-- HOW TO TEST -->
<tr><td style="padding:10px 40px 5px;">
<h2 style="margin:0;font-size:20px;font-weight:700;color:#e0e7ff;border-bottom:1px solid #1e1e2e;padding-bottom:10px;">How to Verify</h2>
</td></tr>
<tr><td style="padding:5px 40px 20px;">
<table width="100%" cellpadding="0" cellspacing="0">
<tr><td style="padding:8px 0;">
<p style="margin:0;font-size:14px;color:#9ca3af;"><span style="display:inline-block;background:#059669;color:#fff;border-radius:50%;width:22px;height:22px;text-align:center;line-height:22px;font-size:12px;font-weight:700;margin-right:8px;">1</span><strong style="color:#e0e7ff;">Login</strong> &mdash; demo@founderconsole.ai / demo123 &mdash; check the metrics header stays consistent</p>
</td></tr>
<tr><td style="padding:8px 0;">
<p style="margin:0;font-size:14px;color:#9ca3af;"><span style="display:inline-block;background:#059669;color:#fff;border-radius:50%;width:22px;height:22px;text-align:center;line-height:22px;font-size:12px;font-weight:700;margin-right:8px;">2</span><strong style="color:#e0e7ff;">Navigate to Simulate</strong> &mdash; open the scenario simulator and check existing simulation results</p>
</td></tr>
<tr><td style="padding:8px 0;">
<p style="margin:0;font-size:14px;color:#9ca3af;"><span style="display:inline-block;background:#059669;color:#fff;border-radius:50%;width:22px;height:22px;text-align:center;line-height:22px;font-size:12px;font-weight:700;margin-right:8px;">3</span><strong style="color:#e0e7ff;">Run a New Simulation</strong> &mdash; try changing churn rate and CAC &mdash; results should vary meaningfully</p>
</td></tr>
<tr><td style="padding:8px 0;">
<p style="margin:0;font-size:14px;color:#9ca3af;"><span style="display:inline-block;background:#059669;color:#fff;border-radius:50%;width:22px;height:22px;text-align:center;line-height:22px;font-size:12px;font-weight:700;margin-right:8px;">4</span><strong style="color:#e0e7ff;">Check Survival Probability</strong> &mdash; P10/P50/P90 cards should show actual percentages, not "?%"</p>
</td></tr>
<tr><td style="padding:8px 0;">
<p style="margin:0;font-size:14px;color:#9ca3af;"><span style="display:inline-block;background:#059669;color:#fff;border-radius:50%;width:22px;height:22px;text-align:center;line-height:22px;font-size:12px;font-weight:700;margin-right:8px;">5</span><strong style="color:#e0e7ff;">Go to Data Input</strong> &mdash; save with 10% growth &mdash; re-run simulation &mdash; projections should reflect growth</p>
</td></tr>
</table>
</td></tr>

<!-- CTA -->
<tr><td style="padding:20px 40px 30px;text-align:center;">
<a href="{tracked_links['app']}" style="display:inline-block;background:linear-gradient(135deg,#059669,#10b981);color:#fff;padding:14px 48px;border-radius:8px;text-decoration:none;font-weight:700;font-size:16px;">Test the Simulation Engine</a>
</td></tr>

<!-- Footer -->
<tr><td style="padding:20px 40px 30px;border-top:1px solid #1e1e2e;text-align:center;">
<p style="margin:0;font-size:12px;color:#6b7280;">FounderConsole &middot; AI-powered financial intelligence for startups</p>
<p style="margin:8px 0 0;font-size:12px;color:#6b7280;">
<a href="{tracked_links['feedback']}" style="color:#34d399;text-decoration:none;">Share Feedback on Simulation Accuracy</a>
</p>
</td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""


def send_all():
    print(f"Sending simulation engine update emails to {len(RECIPIENTS)} recipients from {len(SENDERS)} senders...")
    print(f"Campaign: {CAMPAIGN}")
    print(f"Timestamp: {datetime.now().isoformat()}")
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
            app_url = f"{BASE_URL}/scenarios?{utm_base}&utm_term=test_simulation"
            feedback_url = f"{BASE_URL}/email-tracking/feedback?email={email}&campaign={campaign_with_sender}"

            demo_link = create_tracked_link(demo_url, recipient_email=email, recipient_id=rid, link_label="demo_cta", base_url=BASE_URL)
            app_link = create_tracked_link(app_url, recipient_email=email, recipient_id=rid, link_label="test_simulation", base_url=BASE_URL)
            feedback_link = create_tracked_link(feedback_url, recipient_email=email, recipient_id=rid, link_label="feedback_link", base_url=BASE_URL)

            tracked = {"demo": demo_link, "app": app_link, "feedback": feedback_link}
            html = build_html(rcpt, tracked)

            utm_params = {
                "utm_source": "email",
                "utm_medium": "update",
                "utm_campaign": campaign_with_sender,
                "utm_content": rid,
                "utm_term": "simulation_update"
            }

            result = _send_email_sync(
                to=email,
                subject="FounderConsole - Simulation Engine Hardened: 16 Critical Fixes Shipped",
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
