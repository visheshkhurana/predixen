"""
Send data connectors update email v10 to 4 recipients.
Transactional-style: minimal HTML, plain-text companion.
Content: 4 new production-ready data connectors (Plaid, HubSpot, Gusto, Xero).
Sender: nfl9@founderconsole.ai
"""
import os, sys, time, uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from server.email.service import _send_email_sync

CAMPAIGN = "founderconsole_connectors_update_feb2026_v10"
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

We just shipped live data connectors -- FounderConsole can now pull real financial data directly from your tools instead of relying on manual CSV uploads.

4 CONNECTORS NOW LIVE
----------------------

1. PLAID (Banking)
   Connect your bank accounts to automatically sync:
   - Account balances (checking, savings, credit)
   - Transaction history
   - Real-time cash position
   Setup: Enter your Plaid client_id, secret, and access_token.

2. HUBSPOT (CRM)
   Pull your sales pipeline data:
   - Deal values and stages
   - Contact and company records
   - Revenue pipeline totals
   Setup: Enter your HubSpot Private App access token.

3. GUSTO (Payroll)
   Import payroll and headcount data:
   - Employee records and compensation
   - Payroll run history and costs
   - Benefits and tax data
   Setup: Enter your Gusto API credentials.

4. XERO (Accounting)
   Sync your books directly:
   - Invoices and payments
   - Profit & Loss statements
   - Balance sheet data
   - Bank transactions
   Setup: Enter your Xero OAuth credentials.

WHY THIS MATTERS
-----------------

Until now, getting data into FounderConsole meant uploading CSVs or typing numbers manually. That's fine for a demo, but real startups need their actual data flowing in automatically.

With these connectors:
- Your financial baseline updates itself -- no more stale spreadsheets
- Simulations run on real numbers, not estimates
- The AI copilot can reference actual transactions and payroll data
- KPI dashboards reflect live balances and revenue

The connector catalog has 37 total integrations listed. These 4 are fully production-ready with real API calls. The rest are on the roadmap.

HOW TO CONNECT
---------------

1. Log in: {BASE_URL}/auth
   Demo: demo@founderconsole.ai / demo123

2. Go to the Integrations page (sidebar)

3. Pick a connector (e.g. Plaid), click Connect

4. Enter your API credentials in the form

5. Hit Connect -- the system authenticates and syncs your data

Each connector handles authentication, data sync, and error recovery. You can disconnect and reconnect at any time.

Let me know if you have questions or want to prioritize a specific connector.

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

<p>We just shipped live data connectors &mdash; FounderConsole can now pull real financial data directly from your tools instead of relying on manual CSV uploads.</p>

<h3 style="font-size:16px;color:#111;margin:28px 0 12px;">4 Connectors Now Live</h3>

<h4 style="font-size:14px;color:#333;margin:22px 0 8px;">1. Plaid (Banking)</h4>
<p>Connect your bank accounts to automatically sync:</p>
<ul style="padding-left:20px;color:#333;">
<li style="margin-bottom:4px;">Account balances (checking, savings, credit)</li>
<li style="margin-bottom:4px;">Transaction history</li>
<li style="margin-bottom:4px;">Real-time cash position</li>
</ul>
<p style="font-size:13px;color:#666;">Setup: Enter your Plaid client_id, secret, and access_token.</p>

<h4 style="font-size:14px;color:#333;margin:22px 0 8px;">2. HubSpot (CRM)</h4>
<p>Pull your sales pipeline data:</p>
<ul style="padding-left:20px;color:#333;">
<li style="margin-bottom:4px;">Deal values and stages</li>
<li style="margin-bottom:4px;">Contact and company records</li>
<li style="margin-bottom:4px;">Revenue pipeline totals</li>
</ul>
<p style="font-size:13px;color:#666;">Setup: Enter your HubSpot Private App access token.</p>

<h4 style="font-size:14px;color:#333;margin:22px 0 8px;">3. Gusto (Payroll)</h4>
<p>Import payroll and headcount data:</p>
<ul style="padding-left:20px;color:#333;">
<li style="margin-bottom:4px;">Employee records and compensation</li>
<li style="margin-bottom:4px;">Payroll run history and costs</li>
<li style="margin-bottom:4px;">Benefits and tax data</li>
</ul>
<p style="font-size:13px;color:#666;">Setup: Enter your Gusto API credentials.</p>

<h4 style="font-size:14px;color:#333;margin:22px 0 8px;">4. Xero (Accounting)</h4>
<p>Sync your books directly:</p>
<ul style="padding-left:20px;color:#333;">
<li style="margin-bottom:4px;">Invoices and payments</li>
<li style="margin-bottom:4px;">Profit &amp; Loss statements</li>
<li style="margin-bottom:4px;">Balance sheet data</li>
<li style="margin-bottom:4px;">Bank transactions</li>
</ul>
<p style="font-size:13px;color:#666;">Setup: Enter your Xero OAuth credentials.</p>

<h3 style="font-size:16px;color:#111;margin:28px 0 12px;">Why This Matters</h3>

<p>Until now, getting data into FounderConsole meant uploading CSVs or typing numbers manually. That&rsquo;s fine for a demo, but real startups need their actual data flowing in automatically.</p>

<p>With these connectors:</p>
<ul style="padding-left:20px;color:#333;">
<li style="margin-bottom:4px;">Your financial baseline updates itself &mdash; no more stale spreadsheets</li>
<li style="margin-bottom:4px;">Simulations run on real numbers, not estimates</li>
<li style="margin-bottom:4px;">The AI copilot can reference actual transactions and payroll data</li>
<li style="margin-bottom:4px;">KPI dashboards reflect live balances and revenue</li>
</ul>

<p>The connector catalog has 37 total integrations listed. These 4 are fully production-ready with real API calls. The rest are on the roadmap.</p>

<h3 style="font-size:16px;color:#111;margin:28px 0 12px;">How to Connect</h3>

<ol style="padding-left:20px;color:#333;">
<li style="margin-bottom:6px;">Log in: <a href="{BASE_URL}/auth" style="color:#4f46e5;">{BASE_URL}/auth</a><br>Demo: demo@founderconsole.ai / demo123</li>
<li style="margin-bottom:6px;">Go to the <strong>Integrations</strong> page (sidebar)</li>
<li style="margin-bottom:6px;">Pick a connector (e.g. Plaid), click <strong>Connect</strong></li>
<li style="margin-bottom:6px;">Enter your API credentials in the form</li>
<li style="margin-bottom:6px;">Hit Connect &mdash; the system authenticates and syncs your data</li>
</ol>

<p>Each connector handles authentication, data sync, and error recovery. You can disconnect and reconnect at any time.</p>

<p>Let me know if you have questions or want to prioritize a specific connector.</p>

<p style="margin-top:30px;padding-top:15px;border-top:1px solid #e5e5e5;font-size:13px;color:#888;">
FounderConsole
</p>

</div>
</body>
</html>"""


def send_all():
    sender = "FounderConsole <nfl9@founderconsole.ai>"

    print(f"Sending data connectors update emails to {len(RECIPIENTS)} recipients...")
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
            subject="New: Live data connectors (Plaid, HubSpot, Gusto, Xero)",
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
