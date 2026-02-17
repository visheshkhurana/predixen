"""
Send transactional-style update email v7 to 4 recipients.
Designed to land in Primary inbox, not Promotions:
- Minimal HTML (no gradients, no big buttons, no marketing layout)
- Plain-text companion included
- Transactional headers (X-Entity-Ref-ID, precedence)
- Single sender, personal tone
- Simple inline links instead of styled CTAs
"""
import os, sys, time, uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from server.email.service import _send_email_sync

CAMPAIGN = "founderconsole_eng_update_feb2026_v7"
BASE_URL = "https://founderconsole.ai"

RECIPIENTS = [
    {"email": "nikita.luther@gmail.com", "id": "nikita_luther", "name": "Nikita"},
    {"email": "nikita@founderconsole.ai", "id": "nikita_founderconsole", "name": "Nikita"},
    {"email": "nikitafl2024@gmail.com", "id": "nikita_fl2024", "name": "Nikita"},
    {"email": "vysheshk@gmail.com", "id": "vyshesh_k", "name": "Vyshesh"},
]


def build_plain_text(rcpt: dict) -> str:
    name = rcpt["name"]
    return f"""Hi {name},

Quick update on the simulation engine -- we shipped 16 fixes this week.

The big ones:

- Growth rate sync: When you enter 10% growth in Data Input, it now actually flows through to simulations. Previously it was silently ignored.

- Churn & CAC parameters: Changing churn rate or CAC in the scenario builder now affects Monte Carlo results. These sliders were previously disconnected.

- Runway cap: Projections are capped at the simulation horizon instead of showing impossible 200+ month values.

- Break-even: Uses P10/P50/P90 percentile analysis instead of a single flat number.

- Input validation: Negative fundraise amounts, burn reduction over 100%, and fundraise month 0 are all caught and corrected before they corrupt results.

- Survival probability: Old simulation runs now display correctly instead of showing "?%".

- Metrics consistency: MRR ($43,949), Cash ($513,746), Runway (21.3mo), LTV:CAC (3.2x) stay consistent across all pages.

You can verify all of this in the demo account:
{BASE_URL}/auth
Login: demo@founderconsole.ai / demo123

Try running a simulation with different churn/CAC values -- the results should now vary meaningfully.

Let me know if anything looks off.

--
FounderConsole
"""


def build_html(rcpt: dict) -> str:
    name = rcpt["name"]
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;font-size:15px;line-height:1.6;color:#1a1a1a;background-color:#ffffff;">
<div style="max-width:580px;margin:0 auto;padding:30px 20px;">

<p>Hi {name},</p>

<p>Quick update on the simulation engine &mdash; we shipped 16 fixes this week.</p>

<p><strong>The big ones:</strong></p>

<ul style="padding-left:20px;color:#333;">
<li style="margin-bottom:8px;"><strong>Growth rate sync:</strong> When you enter 10% growth in Data Input, it now actually flows through to simulations. Previously it was silently ignored.</li>
<li style="margin-bottom:8px;"><strong>Churn &amp; CAC parameters:</strong> Changing churn rate or CAC in the scenario builder now affects Monte Carlo results. These sliders were previously disconnected.</li>
<li style="margin-bottom:8px;"><strong>Runway cap:</strong> Projections are capped at the simulation horizon instead of showing impossible 200+ month values.</li>
<li style="margin-bottom:8px;"><strong>Break-even:</strong> Uses P10/P50/P90 percentile analysis instead of a single flat number.</li>
<li style="margin-bottom:8px;"><strong>Input validation:</strong> Negative fundraise amounts, burn reduction over 100%, and fundraise month 0 are all caught and corrected before they corrupt results.</li>
<li style="margin-bottom:8px;"><strong>Survival probability:</strong> Old simulation runs now display correctly instead of showing &ldquo;?%&rdquo;.</li>
<li style="margin-bottom:8px;"><strong>Metrics consistency:</strong> MRR ($43,949), Cash ($513,746), Runway (21.3mo), LTV:CAC (3.2x) stay consistent across all pages.</li>
</ul>

<p>You can verify all of this in the demo account:<br>
<a href="{BASE_URL}/auth" style="color:#4f46e5;">{BASE_URL}/auth</a><br>
Login: demo@founderconsole.ai / demo123</p>

<p>Try running a simulation with different churn/CAC values &mdash; the results should now vary meaningfully.</p>

<p>Let me know if anything looks off.</p>

<p style="margin-top:30px;padding-top:15px;border-top:1px solid #e5e5e5;font-size:13px;color:#888;">
FounderConsole
</p>

</div>
</body>
</html>"""


def send_all():
    sender = "Nikita at FounderConsole <nikita@founderconsole.ai>"

    print(f"Sending transactional update emails to {len(RECIPIENTS)} recipients...")
    print(f"Campaign: {CAMPAIGN}")
    print(f"Sender: {sender}")
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
            subject="Simulation engine update - 16 fixes shipped",
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
