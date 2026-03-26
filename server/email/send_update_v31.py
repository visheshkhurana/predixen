"""
Send update email v31 - Production Bug Fixes & Brand Refresh.
Sender: Arjun from FounderConsole <arjun@founderconsole.ai>
"""
import os, sys, time, uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from server.email.service import _send_email_sync

CAMPAIGN = "founderconsole_update_mar2026_v31"

BASE_URL = "https://fund-flow.replit.app"

RECIPIENTS = [
    {"email": "nikita.luther@gmail.com", "id": "nikita_luther", "name": "Nikita"},
    {"email": "nikita@predixen.ai", "id": "nikita_predixen", "name": "Nikita"},
    {"email": "nikitafl2024@gmail.com", "id": "nikita_fl2024", "name": "Nikita"},
    {"email": "vysheshk@gmail.com", "id": "vyshesh_k", "name": "Vyshesh"},
]


def build_plain_text(rcpt: dict) -> str:
    return f"""Hi {rcpt['name']},

Quick update — we've shipped a round of production bug fixes and a brand refresh on FounderConsole.

---

1. SMARTER NLP SCENARIO PARSING

The natural language scenario engine now handles industry-specific inputs much better:

- "COD returns spike from 15% to 35%" — correctly parses the delta (20pp impact), not the absolute target
- "Competitor launches similar product" — properly triggers pessimistic effects (higher churn, lower growth), no longer confused with "market expansion"
- "Shipping costs increase 25%" — recognized as opex increase with margin impact
- "Lose 20% customers" — correctly maps to churn + growth reduction
- Handles plurals naturally: "returns", "rates", "costs" all work

---

2. DELTA-BASED SCORE CALIBRATION

Scenario risk scores now use a composite delta-based formula instead of absolute values:

- 40% survival component + 40% runway change vs baseline + 20% P10 downside penalty
- Scores properly differentiate: "cut burn 30%" scores 8-9, "lose 20% customers" scores 2-4
- Counter-move cards now compare against a clean baseline simulation, showing accurate positive deltas

---

3. WHAT-IF EXPLORER FIX

Slider values in the What-If Explorer no longer show floating-point noise (e.g., "5.000000000000001%"). All values display cleanly rounded to their step precision.

---

4. FLIGHT SIMULATOR STABILITY

Fixed a regression where the Flight Simulator could hang during agent persona generation. The LLM calls now run with proper async handling and a 45-second timeout per agent, with graceful fallback to deterministic personas.

---

5. DIGITAL TWIN ACCURACY

The Digital Twin now picks the most accurate data source when CompanyState and TruthScan disagree by more than 5x. Previously it only checked for zero values — now it detects stale data and automatically uses the fresher source.

---

6. COPILOT FOLLOW-UP VARIETY

Follow-up suggestions after Copilot responses are now drawn from randomized pools of 5-7 options per topic category. No more seeing the same 3 suggestions every time.

---

7. BRAND REFRESH

New logo and favicon across the entire platform:
- Clean teal/emerald gradient icon with bar chart mark
- Consistent across sidebar, marketing pages, auth screens, and admin console
- No more duplicated text in the logo area
- Matching favicon replaces the old generic icon

---

All changes are live now.

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

<p>Quick update &mdash; we&rsquo;ve shipped a round of production bug fixes and a brand refresh on FounderConsole.</p>

<!-- 1. NLP Parsing -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #10b981;">1. Smarter NLP Scenario Parsing</h2>

<p style="font-size:13px;color:#4b5563;margin:0 0 12px;">The natural language scenario engine now handles industry-specific inputs much better.</p>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:14px 16px;background:#ecfdf5;border-left:3px solid #10b981;border-radius:0 6px 6px 0;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:13px;color:#4b5563;">
<tr><td style="padding:3px 0;">&ldquo;COD returns spike from 15% to 35%&rdquo; &rarr; correctly parses the 20pp delta, not the absolute target</td></tr>
<tr><td style="padding:3px 0;">&ldquo;Competitor launches similar product&rdquo; &rarr; pessimistic effects (higher churn, lower growth)</td></tr>
<tr><td style="padding:3px 0;">&ldquo;Shipping costs increase 25%&rdquo; &rarr; recognized as opex increase with margin impact</td></tr>
<tr><td style="padding:3px 0;">&ldquo;Lose 20% customers&rdquo; &rarr; maps to churn + growth reduction</td></tr>
<tr><td style="padding:3px 0;">Handles plurals naturally: &ldquo;returns&rdquo;, &ldquo;rates&rdquo;, &ldquo;costs&rdquo;</td></tr>
</table>
</td>
</tr>
</table>

<!-- 2. Score Calibration -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #6366f1;">2. Delta-Based Score Calibration</h2>

<p style="font-size:13px;color:#4b5563;margin:0 0 12px;">Scenario risk scores now use a composite delta-based formula instead of absolute values.</p>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:14px 16px;background:#eef2ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:13px;color:#4b5563;">
<tr><td style="padding:3px 0;">40% survival component + 40% runway change vs baseline + 20% P10 downside penalty</td></tr>
<tr><td style="padding:3px 0;">&ldquo;Cut burn 30%&rdquo; scores 8&ndash;9, &ldquo;Lose 20% customers&rdquo; scores 2&ndash;4</td></tr>
<tr><td style="padding:3px 0;">Counter-move cards compare against clean baseline &rarr; accurate positive deltas</td></tr>
</table>
</td>
</tr>
</table>

<!-- 3. What-If Fix -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #0ea5e9;">3. What-If Explorer Fix</h2>

<p style="font-size:13px;color:#4b5563;margin:0 0 4px;">Slider values no longer show floating-point noise (e.g., &ldquo;5.000000000000001%&rdquo;). All values display cleanly rounded to their step precision.</p>

<!-- 4. Flight Simulator -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #f59e0b;">4. Flight Simulator Stability</h2>

<p style="font-size:13px;color:#4b5563;margin:0 0 4px;">Fixed a regression where the Flight Simulator could hang during agent persona generation. LLM calls now run with proper async handling and a 45-second timeout per agent, with graceful fallback to deterministic personas.</p>

<!-- 5. Digital Twin -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #8b5cf6;">5. Digital Twin Accuracy</h2>

<p style="font-size:13px;color:#4b5563;margin:0 0 4px;">The Digital Twin now detects when CompanyState and TruthScan disagree by more than 5x, and automatically uses the fresher, more accurate source. Previously it only checked for zero values.</p>

<!-- 6. Copilot -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #16a34a;">6. Copilot Follow-Up Variety</h2>

<p style="font-size:13px;color:#4b5563;margin:0 0 4px;">Follow-up suggestions are now drawn from randomized pools of 5&ndash;7 options per topic category. No more seeing the same 3 suggestions every time.</p>

<!-- 7. Brand Refresh -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #14b8a6;">7. Brand Refresh</h2>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:14px 16px;background:#f0fdfa;border-left:3px solid #14b8a6;border-radius:0 6px 6px 0;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:13px;color:#4b5563;">
<tr><td style="padding:3px 0;">New teal/emerald gradient icon with bar chart mark</td></tr>
<tr><td style="padding:3px 0;">Consistent across sidebar, marketing pages, auth screens, and admin console</td></tr>
<tr><td style="padding:3px 0;">No more duplicated text in the logo area</td></tr>
<tr><td style="padding:3px 0;">Matching favicon replaces the old generic icon</td></tr>
</table>
</td>
</tr>
</table>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:24px 0 0;">
<tr>
<td style="padding:14px 16px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;text-align:center;">
<p style="margin:0;font-size:14px;font-weight:700;color:#15803d;">All changes are live now.</p>
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
    sender = "Arjun from FounderConsole <arjun@runoraai.com>"

    print(f"Sending update v31 to {len(RECIPIENTS)} recipients...")
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
            subject="FounderConsole Update: Production Bug Fixes + Brand Refresh — NLP Parsing, Score Calibration, Flight Simulator & More",
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
