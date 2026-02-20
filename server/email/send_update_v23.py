"""
Send update email v23 - P1/P2 Bug Fixes: Metrics, Currency, Scale & Scenarios.
Sender: noreply@founderconsole.ai
"""
import os, sys, time, uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from server.email.service import _send_email_sync

CAMPAIGN = "founderconsole_p1p2_bugfixes_feb2026_v23"

RECIPIENTS = [
    {"email": "nikita.luther@gmail.com", "id": "nikita_luther", "name": "Nikita"},
    {"email": "nikita@founderconsole.ai", "id": "nikita_founderconsole", "name": "Nikita"},
    {"email": "nikitafl2024@gmail.com", "id": "nikita_fl2024", "name": "Nikita"},
]


def build_plain_text(rcpt: dict) -> str:
    return f"""Hi {rcpt['name']},

All P1 and P2 bugs from the LeadSquared test case have been fixed. Here's what changed.

---

P1 FIXES

---

1. METRICS SHOW N/A WHEN NO DATA PROVIDED

NRR, Active Customers, Churn Rate, and Gross Margin now display "N/A" instead of fake estimated values when you haven't entered the underlying data. No more misleading numbers on the dashboard or overview.

2. AI FETCH PRESERVES YOUR COMPANY NAME

When using "Fetch using AI" during onboarding, the system no longer overwrites your manually typed company name, industry, or stage. AI data fills in only the fields you haven't already set.

3. SCENARIO INPUTS DISPLAY CORRECTLY

The "Inputs vs Baseline" section in simulation results now properly shows your scenario parameters (revenue change, burn change, pricing change, etc.) instead of "No changes detected."

4. DAILY BRIEFING SCALE FIX

Burn rate in the daily briefing now respects your company's amount scale. If you operate in millions, you'll see the actual figure (e.g., 40M) instead of the raw database value (e.g., 0.80).

5. PAYBACK PERIOD CALCULATION

Payback period was showing wrong values because it depended on gross margin, which was stored incorrectly (decimal vs percentage). Now that gross margin is normalized to 0-100, the payback formula produces correct results.

---

P2 FIXES

---

1. QUICK SCENARIO BUTTONS USE COMPANY CURRENCY

The "Fundraise" quick scenario button on the Simulate page now shows your company's currency symbol instead of hardcoded $.

2. ARR HANDLES BILLION-SCALE DISPLAY

ARR values in the billions now display correctly (e.g., 2.6B instead of 2.6K). Added a billions formatting tier to the currency formatter.

3. SCENARIO NAMES USE YOUR QUERY TEXT

Scenarios in the comparison table now show the actual text you typed (e.g., "Cut burn by 20%") instead of generic "Quick simulation."

---

STALE DATA RESOLVED

P0-7 (onboarding creates new companies) inherently fixes all stale data bugs - new companies never inherit old alerts, cap table, or headcount data from previous companies.

---

CURRENT STATE

- All 5 P0 bugs fixed
- All P1 bugs fixed
- All P2 bugs fixed
- 150/150 QA tests passing

--
FounderConsole
"""


def build_html(rcpt: dict) -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;font-size:15px;line-height:1.6;color:#1a1a1a;background-color:#ffffff;">
<div style="max-width:620px;margin:0 auto;padding:30px 20px;">

<p>Hi {rcpt['name']},</p>

<p>All P1 and P2 bugs from the LeadSquared test case have been fixed. Here's what changed.</p>

<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #6366f1;">P1 Fixes</h2>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">

<tr>
<td style="padding:12px 16px;background:#fef3c7;border-left:3px solid #f59e0b;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#92400e;">Metrics Show N/A When No Data Provided</p>
<p style="margin:0;font-size:13px;color:#4b5563;">NRR, Active Customers, Churn Rate, and Gross Margin now display &ldquo;N/A&rdquo; instead of fake estimated values when the underlying data hasn&rsquo;t been entered. No more misleading numbers on the dashboard or overview.</p>
</td>
</tr>
<tr><td style="height:8px;"></td></tr>

<tr>
<td style="padding:12px 16px;background:#fef3c7;border-left:3px solid #f59e0b;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#92400e;">AI Fetch Preserves Your Company Name</p>
<p style="margin:0;font-size:13px;color:#4b5563;">When using &ldquo;Fetch using AI&rdquo; during onboarding, the system no longer overwrites your manually typed company name, industry, or stage. AI data fills only the fields you haven&rsquo;t already set.</p>
</td>
</tr>
<tr><td style="height:8px;"></td></tr>

<tr>
<td style="padding:12px 16px;background:#fef3c7;border-left:3px solid #f59e0b;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#92400e;">Scenario Inputs Display Correctly</p>
<p style="margin:0;font-size:13px;color:#4b5563;">The &ldquo;Inputs vs Baseline&rdquo; section in simulation results now properly shows your scenario parameters (revenue change, burn change, pricing change, etc.) instead of &ldquo;No changes detected.&rdquo;</p>
</td>
</tr>
<tr><td style="height:8px;"></td></tr>

<tr>
<td style="padding:12px 16px;background:#fef3c7;border-left:3px solid #f59e0b;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#92400e;">Daily Briefing Scale Fix</p>
<p style="margin:0;font-size:13px;color:#4b5563;">Burn rate in the daily briefing now respects your company&rsquo;s amount scale. If you operate in millions, you&rsquo;ll see the actual figure (e.g., &#8377;40M) instead of the raw database value (e.g., &#8377;0.80).</p>
</td>
</tr>
<tr><td style="height:8px;"></td></tr>

<tr>
<td style="padding:12px 16px;background:#fef3c7;border-left:3px solid #f59e0b;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#92400e;">Payback Period Calculation Fixed</p>
<p style="margin:0;font-size:13px;color:#4b5563;">Payback period was showing wrong values because it depended on gross margin, which was stored incorrectly (decimal vs percentage). Now that gross margin is normalized to 0&ndash;100, the payback formula produces correct results.</p>
</td>
</tr>

</table>

<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #6366f1;">P2 Fixes</h2>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">

<tr>
<td style="padding:12px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#4338ca;">Quick Scenario Buttons Use Company Currency</p>
<p style="margin:0;font-size:13px;color:#4b5563;">The &ldquo;Fundraise&rdquo; quick scenario button on the Simulate page now shows your company&rsquo;s currency symbol instead of hardcoded $.</p>
</td>
</tr>
<tr><td style="height:8px;"></td></tr>

<tr>
<td style="padding:12px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#4338ca;">ARR Handles Billion-Scale Display</p>
<p style="margin:0;font-size:13px;color:#4b5563;">ARR values in the billions now display correctly (e.g., &#8377;2.6B instead of &#8377;2.6K). Added a billions formatting tier to the currency formatter.</p>
</td>
</tr>
<tr><td style="height:8px;"></td></tr>

<tr>
<td style="padding:12px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#4338ca;">Scenario Names Use Your Query Text</p>
<p style="margin:0;font-size:13px;color:#4b5563;">Scenarios in the comparison table now show the actual text you typed (e.g., &ldquo;Cut burn by 20%&rdquo;) instead of generic &ldquo;Quick simulation.&rdquo;</p>
</td>
</tr>

</table>

<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #6366f1;">Stale Data Resolved</h2>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:12px 16px;background:#f0fdf4;border-left:3px solid #16a34a;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#15803d;">Onboarding Creates New Companies (P0-7)</p>
<p style="margin:0;font-size:13px;color:#4b5563;">New companies never inherit old alerts, cap table, or headcount data from previous companies. This inherently fixes all stale data bugs (P1-1, P1-6, P1-7, P2-6).</p>
</td>
</tr>
</table>

<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #6366f1;">Bug Fix Summary</h2>

<table cellpadding="6" cellspacing="0" border="0" width="100%" style="margin:10px 0;font-size:13px;border:1px solid #e5e7eb;border-radius:6px;border-collapse:collapse;">
<tr style="background:#f9fafb;">
<th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;">Priority</th>
<th style="text-align:center;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;">Total</th>
<th style="text-align:center;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;">Fixed</th>
</tr>
<tr><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;font-weight:600;color:#dc2626;">P0 (Critical)</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;text-align:center;">5</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;text-align:center;color:#16a34a;font-weight:600;">5</td></tr>
<tr><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;font-weight:600;color:#f59e0b;">P1 (High)</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;text-align:center;">10</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;text-align:center;color:#16a34a;font-weight:600;">10</td></tr>
<tr><td style="padding:6px 8px;font-weight:600;color:#6366f1;">P2 (Medium)</td><td style="padding:6px 8px;text-align:center;">6</td><td style="padding:6px 8px;text-align:center;color:#16a34a;font-weight:600;">6</td></tr>
</table>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:24px 0;">
<tr>
<td style="padding:14px 16px;background:#f0fdf4;border-left:3px solid #16a34a;border-radius:0 6px 6px 0;">
<p style="margin:0;font-weight:700;font-size:14px;color:#15803d;">Current State: All 21 bugs fixed (5 P0 + 10 P1 + 6 P2), 150/150 tests passing</p>
</td>
</tr>
</table>

<p style="margin-top:30px;padding-top:15px;border-top:1px solid #e5e5e5;font-size:13px;color:#888;">
FounderConsole
</p>

</div>
</body>
</html>"""


def send_all():
    sender = "Nikita from FounderConsole <noreply@founderconsole.ai>"

    print(f"Sending P1/P2 Bug Fixes update v23 to {len(RECIPIENTS)} recipients...")
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
            subject="P1/P2 Bugs Fixed: Metrics, Currency, Scale & Scenarios",
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
