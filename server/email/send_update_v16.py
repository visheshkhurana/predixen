"""
Send platform update email v16 - New Features & Intelligence Upgrades.
Sender: wlk2qbda@predixen.app
"""
import os, sys, time, uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from server.email.service import _send_email_sync

CAMPAIGN = "predixen_platform_update_feb2026_v16"

RECIPIENTS = [
    {"email": "nikita.luther@gmail.com", "id": "nikita_luther", "name": "Nikita"},
    {"email": "nikita@predixen.ai", "id": "nikita_predixen", "name": "Nikita"},
    {"email": "nikitafl2024@gmail.com", "id": "nikita_fl2024", "name": "Nikita"},
]


def build_plain_text(rcpt: dict) -> str:
    return f"""Hi {rcpt['name']},

Here's what's new in Predixen Intelligence OS:

1. AI Decision Summary
Consultant-grade recommendation card at the top of every simulation. Includes a Decision Score (1-10), GO / CONDITIONAL / NO-GO verdict, and 3 supporting bullet points covering key risk, opportunity, and the metric to watch.

2. Reorganized Simulation Results
All analysis tools are now visible inline - no hidden tabs or "Advanced View" toggles. Results flow in decision-intelligence-first order: AI Summary, Decision Recommendations, Before/After Deltas, Sensitivity Levers, Stress Tests, Monte Carlo distributions, Charts, and Fundraising Intelligence.

3. Scenario Tools Tab Bar
Strategic Builder, Classic Wizard, Detailed Results, Compare All, Enhanced view, History, and Discussion tabs are now promoted to a clearly visible "Scenario Tools" section below the inline results.

4. Automatic Counter-Move Simulations
Every scenario now automatically generates 3 counter-moves (Cost Cut 20%, Raise Prices 10%, Freeze Hiring) showing runway and survival deltas vs your current plan. Apply any counter-move with one click.

5. Dual-Path "Or" Detection
Type "X or Y" or "X vs Y" in the scenario input and the system runs both simulations in parallel for side-by-side comparison.

6. Cross-Page Intelligence Alerts
Contextual alerts (critical, warning, opportunity) now appear on the Dashboard, Data Input, and Fundraising pages based on your latest simulation data.

7. Sensitivity Sliders & Breaking Points
Interactive sliders to stress-test individual variables and instantly see how they affect runway and survival probability.

All of these are live now. Let me know if you have any questions.

--
Predixen Intelligence OS
"""


def build_html(rcpt: dict) -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;font-size:15px;line-height:1.6;color:#1a1a1a;background-color:#ffffff;">
<div style="max-width:580px;margin:0 auto;padding:30px 20px;">

<p>Hi {rcpt['name']},</p>

<p>Here's what's new in Predixen Intelligence OS:</p>

<div style="margin:20px 0;padding:16px 20px;border-left:3px solid #6366f1;background:#f8f7ff;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:600;color:#4338ca;">AI Decision Summary</p>
<p style="margin:0;font-size:14px;color:#4b5563;">Consultant-grade recommendation card at the top of every simulation. Includes a Decision Score (1&ndash;10), GO / CONDITIONAL / NO-GO verdict, and 3 supporting bullet points covering key risk, opportunity, and the metric to watch.</p>
</div>

<div style="margin:20px 0;padding:16px 20px;border-left:3px solid #6366f1;background:#f8f7ff;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:600;color:#4338ca;">Reorganized Simulation Results</p>
<p style="margin:0;font-size:14px;color:#4b5563;">All analysis tools are now visible inline &mdash; no hidden tabs or &ldquo;Advanced View&rdquo; toggles. Results flow in decision-intelligence-first order: AI Summary &rarr; Decision Recommendations &rarr; Before/After Deltas &rarr; Sensitivity Levers &rarr; Stress Tests &rarr; Monte Carlo &rarr; Charts &rarr; Fundraising Intelligence.</p>
</div>

<div style="margin:20px 0;padding:16px 20px;border-left:3px solid #6366f1;background:#f8f7ff;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:600;color:#4338ca;">Scenario Tools Tab Bar</p>
<p style="margin:0;font-size:14px;color:#4b5563;">Strategic Builder, Classic Wizard, Detailed Results, Compare All, Enhanced view, History, and Discussion tabs are now promoted to a clearly visible section below the inline results.</p>
</div>

<div style="margin:20px 0;padding:16px 20px;border-left:3px solid #6366f1;background:#f8f7ff;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:600;color:#4338ca;">Automatic Counter-Move Simulations</p>
<p style="margin:0;font-size:14px;color:#4b5563;">Every scenario now automatically generates 3 counter-moves (Cost Cut 20%, Raise Prices 10%, Freeze Hiring) showing runway and survival deltas vs your current plan. Apply any counter-move with one click.</p>
</div>

<div style="margin:20px 0;padding:16px 20px;border-left:3px solid #6366f1;background:#f8f7ff;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:600;color:#4338ca;">Dual-Path &ldquo;Or&rdquo; Detection</p>
<p style="margin:0;font-size:14px;color:#4b5563;">Type &ldquo;X or Y&rdquo; or &ldquo;X vs Y&rdquo; in the scenario input and the system runs both simulations in parallel for side-by-side comparison.</p>
</div>

<div style="margin:20px 0;padding:16px 20px;border-left:3px solid #6366f1;background:#f8f7ff;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:600;color:#4338ca;">Cross-Page Intelligence Alerts</p>
<p style="margin:0;font-size:14px;color:#4b5563;">Contextual alerts (critical, warning, opportunity) now appear on the Dashboard, Data Input, and Fundraising pages based on your latest simulation data.</p>
</div>

<div style="margin:20px 0;padding:16px 20px;border-left:3px solid #6366f1;background:#f8f7ff;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:600;color:#4338ca;">Sensitivity Sliders &amp; Breaking Points</p>
<p style="margin:0;font-size:14px;color:#4b5563;">Interactive sliders to stress-test individual variables and instantly see how they affect runway and survival probability.</p>
</div>

<p style="margin-top:24px;">All of these are live now. Let me know if you have any questions.</p>

<p style="margin-top:30px;padding-top:15px;border-top:1px solid #e5e5e5;font-size:13px;color:#888;">
Predixen Intelligence OS
</p>

</div>
</body>
</html>"""


def send_all():
    sender = "Predixen <wlk2qbda@predixen.app>"

    print(f"Sending platform update v16 to {len(RECIPIENTS)} recipients...")
    print(f"Sender: {sender}")
    print(f"Campaign: {CAMPAIGN}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    for rcpt in RECIPIENTS:
        email = rcpt["email"]
        rid = rcpt["id"]

        html = build_html(rcpt)
        text = build_plain_text(rcpt)

        headers = {
            "X-Entity-Ref-ID": str(uuid.uuid4()),
            "X-PM-Message-Stream": "outbound",
        }

        utm_params = {
            "utm_source": "email",
            "utm_medium": "transactional",
            "utm_campaign": CAMPAIGN,
            "utm_content": rid,
        }

        result = _send_email_sync(
            to=email,
            subject="Predixen Intelligence OS - New Features & Intelligence Upgrades",
            html_content=html,
            text_content=text,
            from_email=sender,
            recipient_id=rid,
            campaign=CAMPAIGN,
            utm_params=utm_params,
            headers=headers
        )

        status = "SENT" if result.get("success") else "FAILED"
        msg_id = result.get("message_id", result.get("error", ""))
        print(f"  [{status}] {email} -> {msg_id}")

        time.sleep(2)

    print()
    print("Done!")


if __name__ == "__main__":
    send_all()
