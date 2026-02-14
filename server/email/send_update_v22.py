"""
Send update email v22 - Notion Auto-Push: QA Reports Now Publish Automatically.
Sender: f5987291@predixen.app
"""
import os, sys, time, uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from server.email.service import _send_email_sync

CAMPAIGN = "predixen_notion_autopush_feb2026_v22b"

RECIPIENTS = [
    {"email": "nikita.luther@gmail.com", "id": "nikita_luther", "name": "Nikita"},
    {"email": "nikita@predixen.ai", "id": "nikita_predixen", "name": "Nikita"},
    {"email": "nikitafl2024@gmail.com", "id": "nikita_fl2024", "name": "Nikita"},
]


def build_plain_text(rcpt: dict) -> str:
    return f"""Hi {rcpt['name']},

QA reports now auto-publish to Notion after every test run. No manual copy-paste needed.

---

WHAT CHANGED

---

1. AUTOMATIC NOTION PUBLISHING

Every time you run bash qa-lab/run.sh, the QA report is automatically pushed to a "Predixen QA Reports" Notion database. Each run creates a new page with:

- Status: "All Passed" or "Has Failures"
- Pass Rate: e.g., "100.0%"
- Total Tests / Passed / Failed counts
- Duration
- Run Date

The full report content (summary, all test tables, backlog items) is converted from markdown to native Notion blocks - headings, tables, callouts, bullet lists, and dividers.

2. TABLE CHUNKING FOR LARGE REPORTS

The scenario tests table has 121 rows, but Notion limits tables to 100 rows. The push script automatically splits large tables into chunks of 98 rows (plus header), each as a separate Notion table block. Headers are repeated on each chunk so every table is self-contained and readable.

3. REPORTS PUSH REGARDLESS OF TEST OUTCOME

Whether tests pass or fail, the report gets pushed. Failed test runs are just as important to track. The push is non-fatal - if Notion is unreachable, the QA run still completes normally and preserves its exit code.

4. ZERO CONFIGURATION

Uses Replit's built-in Notion connection for authentication. No API keys to manage. The database is auto-created on first run if it doesn't exist.

---

COUNTER-MOVE SHARE BUTTONS

Each counter-move card (Cost Cut 20%, Raise Prices 10%, Freeze Hiring) now has its own share button. You can email individual counter-move simulation results directly from the card, along with the full recommendation context.

---

DASHBOARD HEADER FIX

The right-side header items (alerts, settings, user menu) no longer wrap to a second line on narrower screens. Spacing was tightened and flex-wrap removed from that section.

---

CURRENT STATE

- 150/150 QA tests passing
- Reports auto-publish to Notion on every run
- Counter-move share buttons live
- Dashboard header alignment fixed

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
<div style="max-width:620px;margin:0 auto;padding:30px 20px;">

<p>Hi {rcpt['name']},</p>

<p>QA reports now auto-publish to Notion after every test run. No manual copy-paste needed.</p>

<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #6366f1;">Notion Auto-Push &mdash; QA Reports Publish Automatically</h2>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:16px 0;">
<tr>
<td style="padding:14px 16px;background:#f0fdf4;border-left:3px solid #16a34a;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:16px;color:#15803d;">Fully Automated: Run &rarr; Test &rarr; Report &rarr; Notion</p>
<p style="margin:0;font-size:13px;color:#4b5563;">Every <code style="background:#f3f4f6;padding:2px 5px;border-radius:3px;font-size:12px;">bash qa-lab/run.sh</code> now ends with a Notion page creation. 150 tests run, report generates, and the full results publish to your Notion workspace &mdash; all in ~12 seconds.</p>
</td>
</tr>
</table>

<h3 style="font-size:15px;color:#1e1b4b;margin:24px 0 8px;">How It Works</h3>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">

<tr>
<td style="padding:12px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#4338ca;">1. Auto-Creates Database</p>
<p style="margin:0;font-size:13px;color:#4b5563;">On first run, creates a &ldquo;Predixen QA Reports&rdquo; database in your Notion workspace with columns for Status, Pass Rate, Tests, Passed, Failed, Duration, and Run Date. Subsequent runs reuse the same database.</p>
</td>
</tr>
<tr><td style="height:8px;"></td></tr>

<tr>
<td style="padding:12px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#4338ca;">2. Full Report Conversion</p>
<p style="margin:0;font-size:13px;color:#4b5563;">Markdown is converted to native Notion blocks: headings, tables, callouts, bullet lists, and dividers. Not just raw text &mdash; properly structured and readable.</p>
</td>
</tr>
<tr><td style="height:8px;"></td></tr>

<tr>
<td style="padding:12px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#4338ca;">3. Table Chunking</p>
<p style="margin:0;font-size:13px;color:#4b5563;">The scenario tests table has 121 rows, but Notion caps tables at 100 rows. The script automatically splits large tables into chunks of 98 rows (plus header), each as a separate Notion table. Headers repeat on each chunk.</p>
</td>
</tr>
<tr><td style="height:8px;"></td></tr>

<tr>
<td style="padding:12px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#4338ca;">4. Always Pushes</p>
<p style="margin:0;font-size:13px;color:#4b5563;">Reports push whether tests pass or fail &mdash; failed runs are just as important to track. The push is non-fatal: if Notion is unreachable, the QA run completes normally.</p>
</td>
</tr>
<tr><td style="height:8px;"></td></tr>

<tr>
<td style="padding:12px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#4338ca;">5. Zero Configuration</p>
<p style="margin:0;font-size:13px;color:#4b5563;">Uses Replit&rsquo;s built-in Notion connection for auth. No API keys to manage or rotate.</p>
</td>
</tr>

</table>

<h3 style="font-size:15px;color:#1e1b4b;margin:24px 0 8px;">Notion Page Properties</h3>

<table cellpadding="6" cellspacing="0" border="0" width="100%" style="margin:10px 0;font-size:13px;border:1px solid #e5e7eb;border-radius:6px;border-collapse:collapse;">
<tr style="background:#f9fafb;">
<th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;">Property</th>
<th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;">Example Value</th>
</tr>
<tr><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">Title</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">QA Run &mdash; 2026-02-14 16:48 &mdash; 100.0%</td></tr>
<tr><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">Status</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;color:#16a34a;font-weight:600;">All Passed</td></tr>
<tr><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">Pass Rate</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">100.0%</td></tr>
<tr><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">Tests</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">150</td></tr>
<tr><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">Passed</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">150</td></tr>
<tr><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">Failed</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">0</td></tr>
<tr><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">Duration</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">11.8s</td></tr>
<tr><td style="padding:6px 8px;">Run Date</td><td style="padding:6px 8px;">2026-02-14</td></tr>
</table>

<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #6366f1;">Other Updates</h2>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">

<tr>
<td style="padding:12px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#4338ca;">Counter-Move Share Buttons</p>
<p style="margin:0;font-size:13px;color:#4b5563;">Each counter-move card (Cost Cut 20%, Raise Prices 10%, Freeze Hiring) now has its own share button. Email individual counter-move results directly from the simulation results page.</p>
</td>
</tr>
<tr><td style="height:8px;"></td></tr>

<tr>
<td style="padding:12px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#4338ca;">Dashboard Header Fix</p>
<p style="margin:0;font-size:13px;color:#4b5563;">Right-side header items (alerts, settings, user menu) no longer wrap to a second line on narrower screens.</p>
</td>
</tr>

</table>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:24px 0;">
<tr>
<td style="padding:14px 16px;background:#f0fdf4;border-left:3px solid #16a34a;border-radius:0 6px 6px 0;">
<p style="margin:0;font-weight:700;font-size:14px;color:#15803d;">Current State: 150/150 tests passing, auto-publishing to Notion</p>
</td>
</tr>
</table>

<p style="margin-top:30px;padding-top:15px;border-top:1px solid #e5e5e5;font-size:13px;color:#888;">
Predixen Intelligence OS
</p>

</div>
</body>
</html>"""


def send_all():
    sender = "Nikita from Predixen <updates@predixen.app>"

    print(f"Sending Notion Auto-Push update v22b to {len(RECIPIENTS)} recipients...")
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
            "List-Unsubscribe": "<mailto:updates@predixen.app?subject=unsubscribe>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
            "Precedence": "bulk",
        }

        utm_params = {
            "utm_source": "email",
            "utm_medium": "transactional",
            "utm_campaign": CAMPAIGN,
            "utm_content": rid,
        }

        result = _send_email_sync(
            to=email,
            subject="QA Reports Now Auto-Publish to Notion",
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
