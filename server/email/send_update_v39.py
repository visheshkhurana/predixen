"""
Send update email v38 - Quarterly update: 2500 users, 500 paid, 10K+ simulations, 20K+ decisions.
Sender: Arjun from FounderConsole <arjun@runora.xyz>
"""
import os, sys, time, uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from server.email.service import _send_email_sync

CAMPAIGN = "founderconsole_quarterly_jun2026_v39_2500users_runora"

BASE_URL = "https://founderconsole.ai"

RECIPIENTS = [
    {"email": "nikitafl2024@gmail.com", "id": "nikita_fl2024", "name": "Nikita"},
    {"email": "vysheshk@gmail.com", "id": "vyshesh_k", "name": "Vyshesh"},
    {"email": "nikita.luther@gmail.com", "id": "nikita_luther", "name": "Nikita"},
    {"email": "start@runora.ai", "id": "start_runora", "name": "Team"},
]


def build_plain_text(rcpt: dict) -> str:
    return f"""Hi {rcpt['name']},

Time for our quarterly update — and it's a big one.

FounderConsole has crossed 2,500 users, with 500 now on paid plans. Founders are
running the platform hard: over 10,000 simulations and 20,000+ decisions generated.

===========================================
  THE QUARTER IN NUMBERS
===========================================

  2,500   Total users
  500     Paid users
  10,000+ Simulations run
  20,000+ Decisions generated

===========================================
  WHAT IT MEANS
===========================================

  - Real traction: paid conversion is healthy and accelerating.
  - Heavy usage: founders are running simulations and acting on the
    decisions the platform generates, not just signing up.
  - The AI Copilot, Flight Simulator, and Fundraising OS are doing
    the heavy lifting day to day.

Thank you for being part of this quarter. More to come.

Open the platform: {BASE_URL}

--
Arjun
FounderConsole
"""


def build_html(rcpt: dict) -> str:
    email = rcpt['email']
    open_tracking_url = f"{BASE_URL}/email-tracking/analytics?token=founderconsole-analytics-2026&campaign={CAMPAIGN}&email={email}&event=open"
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;font-size:15px;line-height:1.6;color:#1a1a1a;background-color:#ffffff;">
<div style="max-width:620px;margin:0 auto;padding:30px 20px;">

<p>Hi {rcpt['name']},</p>

<p><strong>Time for our quarterly update &mdash; and it's a big one.</strong></p>

<p style="font-size:14px;color:#4b5563;">FounderConsole has crossed <strong>2,500 users</strong>, with <strong>500 now on paid plans</strong>. Founders are running the platform hard.</p>

<!-- Quarterly Banner -->
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:24px 0;border-radius:12px;overflow:hidden;">
<tr>
<td style="padding:34px 28px;background:linear-gradient(135deg,#0f172a 0%,#1e293b 50%,#0f172a 100%);text-align:center;">
<p style="margin:0 0 4px;font-size:12px;font-weight:600;color:#10b981;letter-spacing:2px;">QUARTERLY UPDATE &middot; Q2 2026</p>
<p style="margin:0 0 24px;font-size:72px;font-weight:900;color:#10b981;letter-spacing:-3px;line-height:1;">2,500</p>
<p style="margin:-18px 0 24px;font-size:15px;font-weight:600;color:#ffffff;letter-spacing:1.5px;">TOTAL USERS</p>
<table cellpadding="0" cellspacing="0" border="0" width="100%">
<tr>
<td width="33%" style="text-align:center;padding:6px 4px;">
<p style="margin:0;font-size:26px;font-weight:800;color:#0ea5e9;">500</p>
<p style="margin:2px 0 0;font-size:10px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">Paid Users</p>
</td>
<td width="33%" style="text-align:center;padding:6px 4px;">
<p style="margin:0;font-size:26px;font-weight:800;color:#8b5cf6;">10K+</p>
<p style="margin:2px 0 0;font-size:10px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">Simulations</p>
</td>
<td width="33%" style="text-align:center;padding:6px 4px;">
<p style="margin:0;font-size:26px;font-weight:800;color:#f59e0b;">20K+</p>
<p style="margin:2px 0 0;font-size:10px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">Decisions</p>
</td>
</tr>
</table>
</td>
</tr>
</table>

<!-- WHAT IT MEANS -->
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:28px 0 16px;">
<tr><td style="padding:10px 16px;background:#0f172a;border-radius:6px;">
<p style="margin:0;font-size:13px;font-weight:700;color:#10b981;text-transform:uppercase;letter-spacing:2px;">What It Means</p>
</td></tr>
</table>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:6px 0;">
<tr><td style="padding:14px 16px;background:#ecfdf5;border-left:3px solid #10b981;border-radius:0 6px 6px 0;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:13px;color:#1f2937;">
<tr><td style="padding:5px 0;"><strong>Real traction</strong> &mdash; paid conversion is healthy and accelerating</td></tr>
<tr><td style="padding:5px 0;"><strong>Heavy usage</strong> &mdash; founders are running simulations and acting on the decisions, not just signing up</td></tr>
<tr><td style="padding:5px 0;"><strong>Copilot, Flight Simulator &amp; Fundraising OS</strong> &mdash; doing the heavy lifting day to day</td></tr>
</table>
</td></tr>
</table>

<p style="font-size:14px;color:#4b5563;margin-top:24px;">Thank you for being part of this quarter. More to come.</p>

<!-- CTA -->
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:32px 0;">
<tr>
<td style="text-align:center;">
<a href="{BASE_URL}" style="display:inline-block;padding:16px 40px;background:linear-gradient(135deg,#10b981 0%,#0d9488 100%);color:#ffffff;text-decoration:none;font-weight:700;font-size:16px;border-radius:10px;letter-spacing:0.5px;">Open FounderConsole</a>
</td>
</tr>
</table>

<p style="margin-top:30px;padding-top:15px;border-top:1px solid #e5e5e5;font-size:13px;color:#888;">
Arjun<br>FounderConsole
</p>

</div>
<img src="{open_tracking_url}" width="1" height="1" style="display:none" alt="" />
</body>
</html>"""


def send_all():
    sender = "Arjun from FounderConsole <arjun@runora.xyz>"

    print(f"Sending quarterly update v39 (2500 users) to {len(RECIPIENTS)} recipients...")
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
        }

        utm_params = {
            "utm_source": "email",
            "utm_medium": "transactional",
            "utm_campaign": CAMPAIGN,
            "utm_content": rid,
        }

        result = _send_email_sync(
            to=email,
            subject="FounderConsole Quarterly Update: 2,500 users, 500 paid",
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
