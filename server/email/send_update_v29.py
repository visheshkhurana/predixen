"""
Send update email v29 - Klipfolio-Style Data Integrations Phase 1.
Sender: Arjun from FounderConsole <arjun@founderconsole.ai>
"""
import os, sys, time, uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from server.email.service import _send_email_sync

CAMPAIGN = "founderconsole_update_mar2026_v29"

BASE_URL = "https://fund-flow.replit.app"

RECIPIENTS = [
    {"email": "nikita.luther@gmail.com", "id": "nikita_luther", "name": "Nikita"},
    {"email": "nikita@predixen.ai", "id": "nikita_predixen", "name": "Nikita"},
    {"email": "nikitafl2024@gmail.com", "id": "nikita_fl2024", "name": "Nikita"},
]


def build_plain_text(rcpt: dict) -> str:
    return f"""Hi {rcpt['name']},

Quick update on what shipped on FounderConsole today.

---

1. KLIPFOLIO-STYLE KPI DASHBOARD

The KPI Board has been completely redesigned with a Klipfolio-inspired layout:

- Filter Bar: Date range selector (7d, 30d, 90d, 12m, YTD) and data source filter with auto-refresh indicator and live/disconnected status badge
- Enhanced KPI Cards: Large metric values with sparkline mini-charts, period-over-period delta arrows (green/red), data source badges, and hover detail tooltips
- Revenue Insights Panel: Four interactive Recharts widgets - MRR Trend (area chart), Revenue vs Expenses (bar chart), Cash Flow & Runway (line chart), Team & Customer Growth (area chart)
- Data Sources Status: Connected integrations panel with sync status dots, last sync time, record counts, and Add Integration button

---

2. ENHANCED STRIPE CONNECTOR

The Stripe data connector now pulls a much richer set of metrics:

- Paginated MRR calculation from active subscriptions
- Refunds sync with total amount and count
- Customer count with 30-day new customer tracking
- Churn metrics using canceled_at timestamps (accurate churn rate)
- ARPU (Average Revenue Per User)
- 12-month monthly revenue breakdown using calendar-accurate month boundaries
- Total revenue now calculated from actual charges instead of balance snapshots

---

3. STRIPE CONNECT MODAL

New dedicated Stripe connection experience on the Integrations page:

- Dark-themed modal with Stripe branding
- API key input with show/hide toggle and format validation (sk_live_, sk_test_, rk_live_, rk_test_)
- Test Connection button with animated progress bar
- Security note about encrypted storage and read-only access
- Data sync badges showing what metrics get pulled (MRR, ARR, Customers, Churn, Refunds, ARPU, Revenue)
- Success state with one-click Sync Now to trigger initial data pull
- Error state with clear messaging and retry option

---

4. BUG FIXES

- Fixed getToken crash on KPI Board: Removed undefined getToken reference in the realtime KPI hook that was causing the entire page to error out. Auth now correctly uses cookie-based credentials.
- Fixed total_revenue calculation: Revenue metrics now sum actual charges from monthly breakdown instead of reading Stripe balance snapshots, which was inaccurate for revenue reporting.

---

All changes are live. 442+ routes registered, application running stable.

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

<p>Quick update on what shipped on FounderConsole today.</p>

<!-- 1. Klipfolio KPI Dashboard -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #6366f1;">1. Klipfolio-Style KPI Dashboard</h2>

<p style="font-size:13px;color:#4b5563;margin:0 0 12px;">The KPI Board has been completely redesigned with a Klipfolio-inspired data visualization layout.</p>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:14px 16px;background:#eef2ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 8px;font-weight:700;font-size:14px;color:#4338ca;">Filter Bar</p>
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:13px;color:#4b5563;">
<tr><td style="padding:3px 0;">Date range selector: 7d, 30d, 90d, 12m, YTD</td></tr>
<tr><td style="padding:3px 0;">Data source filter with auto-refresh indicator</td></tr>
<tr><td style="padding:3px 0;">Live / Disconnected status badge</td></tr>
</table>
</td>
</tr>
</table>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:14px 16px;background:#f0fdf4;border-left:3px solid #16a34a;border-radius:0 6px 6px 0;">
<p style="margin:0 0 8px;font-weight:700;font-size:14px;color:#15803d;">Enhanced KPI Cards</p>
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:13px;color:#4b5563;">
<tr><td style="padding:3px 0;">Large metric values with sparkline mini-charts</td></tr>
<tr><td style="padding:3px 0;">Period-over-period delta arrows (green up / red down)</td></tr>
<tr><td style="padding:3px 0;">Data source badges and hover detail tooltips</td></tr>
</table>
</td>
</tr>
</table>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:14px 16px;background:#f0f9ff;border-left:3px solid #0ea5e9;border-radius:0 6px 6px 0;">
<p style="margin:0 0 8px;font-weight:700;font-size:14px;color:#0369a1;">Revenue Insights Panel</p>
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:13px;color:#4b5563;">
<tr><td style="padding:3px 0;"><strong>MRR Trend</strong> &mdash; area chart with gradient fill</td></tr>
<tr><td style="padding:3px 0;"><strong>Revenue vs Expenses</strong> &mdash; stacked bar chart</td></tr>
<tr><td style="padding:3px 0;"><strong>Cash Flow &amp; Runway</strong> &mdash; dual-line chart</td></tr>
<tr><td style="padding:3px 0;"><strong>Team &amp; Customer Growth</strong> &mdash; area chart</td></tr>
</table>
</td>
</tr>
</table>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:14px 16px;background:#faf5ff;border-left:3px solid #8b5cf6;border-radius:0 6px 6px 0;">
<p style="margin:0 0 8px;font-weight:700;font-size:14px;color:#7c3aed;">Data Sources Status</p>
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:13px;color:#4b5563;">
<tr><td style="padding:3px 0;">Connected integrations with sync status dots</td></tr>
<tr><td style="padding:3px 0;">Last sync time and record counts</td></tr>
<tr><td style="padding:3px 0;">Add Integration button to connect new sources</td></tr>
</table>
</td>
</tr>
</table>

<!-- 2. Enhanced Stripe Connector -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #0ea5e9;">2. Enhanced Stripe Connector</h2>

<p style="font-size:13px;color:#4b5563;margin:0 0 12px;">The Stripe data connector now pulls a much richer set of metrics automatically.</p>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:14px 16px;background:#f0f9ff;border-left:3px solid #0ea5e9;border-radius:0 6px 6px 0;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:13px;color:#4b5563;">
<tr><td style="padding:3px 0;"><strong>Paginated MRR</strong> from active subscriptions</td></tr>
<tr><td style="padding:3px 0;"><strong>Refunds</strong> sync with total amount and count</td></tr>
<tr><td style="padding:3px 0;"><strong>Customer count</strong> with 30-day new customer tracking</td></tr>
<tr><td style="padding:3px 0;"><strong>Churn metrics</strong> using <code style="background:#e0f2fe;padding:1px 4px;border-radius:3px;font-size:12px;">canceled_at</code> timestamps</td></tr>
<tr><td style="padding:3px 0;"><strong>ARPU</strong> (Average Revenue Per User)</td></tr>
<tr><td style="padding:3px 0;"><strong>12-month revenue breakdown</strong> with calendar-accurate month boundaries</td></tr>
<tr><td style="padding:3px 0;"><strong>Total revenue</strong> from actual charges (not balance snapshots)</td></tr>
</table>
</td>
</tr>
</table>

<!-- 3. Stripe Connect Modal -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #ec4899;">3. Stripe Connect Modal</h2>

<p style="font-size:13px;color:#4b5563;margin:0 0 12px;">New dedicated Stripe connection experience on the Integrations page.</p>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:14px 16px;background:#fdf2f8;border-left:3px solid #ec4899;border-radius:0 6px 6px 0;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:13px;color:#4b5563;">
<tr><td style="padding:3px 0;">Dark-themed modal with Stripe branding</td></tr>
<tr><td style="padding:3px 0;">API key input with show/hide toggle and format validation</td></tr>
<tr><td style="padding:3px 0;">Test Connection button with animated progress bar</td></tr>
<tr><td style="padding:3px 0;">Security note: encrypted storage, read-only access</td></tr>
<tr><td style="padding:3px 0;">Data sync badges: MRR, ARR, Customers, Churn, Refunds, ARPU, Revenue</td></tr>
<tr><td style="padding:3px 0;">Success state with one-click Sync Now</td></tr>
<tr><td style="padding:3px 0;">Error handling with clear messaging and retry</td></tr>
</table>
</td>
</tr>
</table>

<!-- 4. Bug Fixes -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #16a34a;">4. Bug Fixes</h2>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:12px 16px;background:#f0fdf4;border-left:3px solid #16a34a;border-radius:0 6px 6px 0;">
<p style="margin:0 0 8px;font-size:13px;color:#4b5563;"><strong>KPI Board crash fix:</strong> Removed undefined <code style="background:#dcfce7;padding:1px 4px;border-radius:3px;font-size:12px;">getToken</code> reference in the realtime KPI hook that was causing the entire page to error out. Auth now correctly uses cookie-based credentials.</p>
<p style="margin:0;font-size:13px;color:#4b5563;"><strong>Revenue calculation fix:</strong> Total revenue now sums actual charges from monthly breakdown instead of reading Stripe balance snapshots, which was inaccurate for revenue reporting.</p>
</td>
</tr>
</table>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:24px 0 0;">
<tr>
<td style="padding:14px 16px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;text-align:center;">
<p style="margin:0;font-size:14px;font-weight:700;color:#15803d;">All changes are live. 442+ routes registered. Application running stable.</p>
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

    print(f"Sending update v29 to {len(RECIPIENTS)} recipients...")
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
            subject="FounderConsole Update: Klipfolio KPI Dashboard, Enhanced Stripe Connector & Connect Modal",
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
