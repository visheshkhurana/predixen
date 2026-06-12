"""
Send update email v36 - What's New: shareable simulator, industry pages, embed widget.
Sender: Arjun from FounderConsole <arjun@founderconsole.ai>
"""
import os, sys, time, uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from server.email.service import _send_email_sync

CAMPAIGN = "founderconsole_update_jun2026_v37_whatsnew_fcdomain"

BASE_URL = "https://founderconsole.ai"

RECIPIENTS = [
    {"email": "nikitafl2024@gmail.com", "id": "nikita_fl2024", "name": "Nikita"},
    {"email": "vysheshk@gmail.com", "id": "vyshesh_k", "name": "Vyshesh"},
    {"email": "nikita.luther@gmail.com", "id": "nikita_luther", "name": "Nikita"},
    {"email": "start@runora.ai", "id": "start_runora", "name": "Team"},
]


def build_plain_text(rcpt: dict) -> str:
    return f"""Hi {rcpt['name']},

Quick product update from FounderConsole. We just shipped a batch of features focused on getting your runway analysis in front of more founders.

===========================================
  WHAT'S NEW
===========================================

  - Shareable Survival Simulator results
    Every simulation now generates a clean social card. Share your
    runway analysis on X or LinkedIn and the preview renders automatically.

  - Industry-specific runway calculators
    SaaS, ecommerce, fintech, marketplace, AI, hardware, biotech, and
    devtools each get their own calculator with real benchmarks.

  - Embeddable runway widget
    Drop the calculator into any site or newsletter with a single iframe.

  - 7-day onboarding for new founders
    A guided email sequence walks new users through Truth Scan,
    simulations, the Copilot, and Fundraising OS.

  - Growth analytics dashboard
    Internal funnel, cohort retention, and top-page tracking.

Everything is live now and free for everyone.

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

<p><strong>Quick product update from FounderConsole.</strong></p>

<p style="font-size:14px;color:#4b5563;">We just shipped a batch of features focused on getting your runway analysis in front of more founders &mdash; and making onboarding effortless.</p>

<!-- Header banner -->
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:24px 0;border-radius:12px;overflow:hidden;">
<tr>
<td style="padding:32px 28px;background:linear-gradient(135deg,#0f172a 0%,#1e293b 50%,#0f172a 100%);text-align:center;">
<p style="margin:0 0 6px;font-size:13px;font-weight:600;color:#10b981;letter-spacing:2px;">WHAT'S NEW</p>
<p style="margin:0;font-size:28px;font-weight:900;color:#ffffff;letter-spacing:-1px;line-height:1.2;">5 new ways to share &amp; grow</p>
</td>
</tr>
</table>

<!-- Feature list -->
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:6px 0;">
<tr><td style="padding:14px 16px;background:#ecfdf5;border-left:3px solid #10b981;border-radius:0 6px 6px 0;margin-bottom:8px;">
<p style="margin:0;font-size:14px;font-weight:700;color:#065f46;">Shareable Survival Simulator results</p>
<p style="margin:4px 0 0;font-size:13px;color:#1f2937;">Every simulation now generates a clean social card. Paste the link on X or LinkedIn and the preview renders automatically.</p>
</td></tr>
</table>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:8px 0;">
<tr><td style="padding:14px 16px;background:#eff6ff;border-left:3px solid #0ea5e9;border-radius:0 6px 6px 0;">
<p style="margin:0;font-size:14px;font-weight:700;color:#075985;">Industry-specific runway calculators</p>
<p style="margin:4px 0 0;font-size:13px;color:#1f2937;">SaaS, ecommerce, fintech, marketplace, AI, hardware, biotech, and devtools &mdash; each with real benchmarks.</p>
</td></tr>
</table>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:8px 0;">
<tr><td style="padding:14px 16px;background:#faf5ff;border-left:3px solid #8b5cf6;border-radius:0 6px 6px 0;">
<p style="margin:0;font-size:14px;font-weight:700;color:#5b21b6;">Embeddable runway widget</p>
<p style="margin:4px 0 0;font-size:13px;color:#1f2937;">Drop the calculator into any site or newsletter with a single iframe.</p>
</td></tr>
</table>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:8px 0;">
<tr><td style="padding:14px 16px;background:#fffbeb;border-left:3px solid #f59e0b;border-radius:0 6px 6px 0;">
<p style="margin:0;font-size:14px;font-weight:700;color:#92400e;">7-day onboarding for new founders</p>
<p style="margin:4px 0 0;font-size:13px;color:#1f2937;">A guided sequence walks new users through Truth Scan, simulations, the Copilot, and Fundraising OS.</p>
</td></tr>
</table>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:8px 0;">
<tr><td style="padding:14px 16px;background:#fdf2f8;border-left:3px solid #ec4899;border-radius:0 6px 6px 0;">
<p style="margin:0;font-size:14px;font-weight:700;color:#9d174d;">Growth analytics dashboard</p>
<p style="margin:4px 0 0;font-size:13px;color:#1f2937;">Internal funnel, cohort retention, and top-page tracking.</p>
</td></tr>
</table>

<p style="font-size:14px;color:#4b5563;margin-top:24px;">Everything is live now and free for everyone.</p>

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
    sender = "Arjun from FounderConsole <arjun@founderconsole.ai>"

    print(f"Sending update v37 (what's new) to {len(RECIPIENTS)} recipients...")
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
            subject="What's new in FounderConsole",
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
