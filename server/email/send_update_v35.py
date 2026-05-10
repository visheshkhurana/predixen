"""
Send update email v35 - 500 Active Users milestone.
Sender: Arjun from FounderConsole <arjun@runora.xyz>
"""
import os, sys, time, uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from server.email.service import _send_email_sync

CAMPAIGN = "founderconsole_update_may2026_v35_500users"

BASE_URL = "https://founderconsole.ai"

RECIPIENTS = [
    {"email": "nikita.luther@gmail.com", "id": "nikita_luther", "name": "Nikita"},
    {"email": "nikita@predixen.ai", "id": "nikita_predixen", "name": "Nikita"},
    {"email": "nikitafl2024@gmail.com", "id": "nikita_fl2024", "name": "Nikita"},
    {"email": "vysheshk@gmail.com", "id": "vyshesh_k", "name": "Vyshesh"},
    {"email": "start@runora.ai", "id": "start_runora", "name": "Team"},
]


def build_plain_text(rcpt: dict) -> str:
    return f"""Hi {rcpt['name']},

Big milestone — FounderConsole just crossed 500 active users.

We were at 125 a few weeks ago. 4x growth since then, with founders running more simulations, scoring more decisions, and leaning on the AI Copilot every day.

===========================================
  WHERE WE ARE (May 2026)
===========================================

  500 Active Users (4x in 4 weeks)
  9+ Companies onboarded
  150+ Simulations run
  200+ Scenarios modeled
  300+ Decisions scored
  100+ AI Copilot conversations
  854 Investors in database
  38 Data connectors live

===========================================
  WHAT'S DRIVING IT
===========================================

  - Free for everyone right now (paywall paused)
  - Flight Simulator (multi-agent AI) is the most-used feature
  - Investor Database + Outreach Sequences shipping fundraising workflow
  - Truth Engine + 38 connectors making onboarding faster

Thanks for being part of the early run. More coming soon.

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

<p><strong>Big milestone &mdash; FounderConsole just crossed 500 active users.</strong></p>

<p style="font-size:14px;color:#4b5563;">We were at 125 a few weeks ago. 4x growth since then, with founders running more simulations, scoring more decisions, and leaning on the AI Copilot every day.</p>

<!-- Milestone Banner -->
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:24px 0;border-radius:12px;overflow:hidden;">
<tr>
<td style="padding:36px 28px;background:linear-gradient(135deg,#0f172a 0%,#1e293b 50%,#0f172a 100%);text-align:center;">
<p style="margin:0 0 6px;font-size:72px;font-weight:900;color:#10b981;letter-spacing:-3px;line-height:1;">500</p>
<p style="margin:0 0 6px;font-size:15px;font-weight:600;color:#ffffff;letter-spacing:1.5px;">ACTIVE USERS</p>
<p style="margin:0 0 24px;font-size:12px;font-weight:600;color:#10b981;letter-spacing:1px;">4x GROWTH IN 4 WEEKS</p>
<table cellpadding="0" cellspacing="0" border="0" width="100%">
<tr>
<td width="16%" style="text-align:center;padding:6px 2px;">
<p style="margin:0;font-size:20px;font-weight:800;color:#0ea5e9;">9+</p>
<p style="margin:1px 0 0;font-size:9px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">Companies</p>
</td>
<td width="16%" style="text-align:center;padding:6px 2px;">
<p style="margin:0;font-size:20px;font-weight:800;color:#8b5cf6;">150+</p>
<p style="margin:1px 0 0;font-size:9px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">Simulations</p>
</td>
<td width="16%" style="text-align:center;padding:6px 2px;">
<p style="margin:0;font-size:20px;font-weight:800;color:#f59e0b;">200+</p>
<p style="margin:1px 0 0;font-size:9px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">Scenarios</p>
</td>
<td width="16%" style="text-align:center;padding:6px 2px;">
<p style="margin:0;font-size:20px;font-weight:800;color:#ec4899;">300+</p>
<p style="margin:1px 0 0;font-size:9px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">Decisions</p>
</td>
<td width="16%" style="text-align:center;padding:6px 2px;">
<p style="margin:0;font-size:20px;font-weight:800;color:#14b8a6;">100+</p>
<p style="margin:1px 0 0;font-size:9px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">AI Chats</p>
</td>
<td width="16%" style="text-align:center;padding:6px 2px;">
<p style="margin:0;font-size:20px;font-weight:800;color:#f97316;">854</p>
<p style="margin:1px 0 0;font-size:9px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">Investors</p>
</td>
</tr>
</table>
</td>
</tr>
</table>

<!-- WHAT'S DRIVING IT -->
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:28px 0 16px;">
<tr><td style="padding:10px 16px;background:#0f172a;border-radius:6px;">
<p style="margin:0;font-size:13px;font-weight:700;color:#10b981;text-transform:uppercase;letter-spacing:2px;">What's Driving It</p>
</td></tr>
</table>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:6px 0;">
<tr><td style="padding:14px 16px;background:#ecfdf5;border-left:3px solid #10b981;border-radius:0 6px 6px 0;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:13px;color:#1f2937;">
<tr><td style="padding:5px 0;"><strong>Free for everyone</strong> &mdash; paywall paused while we grow</td></tr>
<tr><td style="padding:5px 0;"><strong>Flight Simulator</strong> &mdash; the multi-agent AI is the most-used feature</td></tr>
<tr><td style="padding:5px 0;"><strong>Investor Database + Outreach</strong> &mdash; the full fundraising workflow now lives in one place</td></tr>
<tr><td style="padding:5px 0;"><strong>Truth Engine + 38 connectors</strong> &mdash; founders are getting set up in minutes, not days</td></tr>
</table>
</td></tr>
</table>

<p style="font-size:14px;color:#4b5563;margin-top:24px;">Thanks for being part of the early run. More coming soon.</p>

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

    print(f"Sending update v35 (500 users milestone) to {len(RECIPIENTS)} recipients...")
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
            subject="FounderConsole just crossed 500 active users",
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
