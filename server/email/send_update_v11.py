"""
Send data connectors expansion update email v11 to 4 recipients.
Transactional-style: minimal HTML, plain-text companion.
Content: All 37 connectors now fully production-ready with real API integration.
Sender: nfl9@predixen.app
"""
import os, sys, time, uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from server.email.service import _send_email_sync

CAMPAIGN = "predixen_connectors_full_catalog_feb2026_v11"
BASE_URL = "https://predixen.app"

RECIPIENTS = [
    {"email": "nikita.luther@gmail.com", "id": "nikita_luther", "name": "Nikita"},
    {"email": "nikita@predixen.ai", "id": "nikita_predixen", "name": "Nikita"},
    {"email": "nikitafl2024@gmail.com", "id": "nikita_fl2024", "name": "Nikita"},
    {"email": "vysheshk@gmail.com", "id": "vyshesh_k", "name": "Vyshesh"},
]


def build_plain_text(rcpt: dict) -> str:
    name = rcpt["name"]
    return f"""Hi {name},

Last update we shipped 4 live connectors. Now all 37 connectors in the catalog are fully production-ready with real API integration. Every connector listed on the Integrations page actually works.

37 CONNECTORS ACROSS 6 CATEGORIES
-----------------------------------

FINANCE & ACCOUNTING (10)
- Stripe: MRR/ARR calculation, invoices, balance transactions, subscription analytics
- QuickBooks: Chart of accounts, invoices, P&L, balance sheet
- Xero: Invoices, payments, P&L, balance sheet, bank transactions
- Zoho Books: Invoices, chart of accounts, bank transactions
- FreshBooks: Invoices, expenses, clients, payments, time entries
- Wave: Invoices, accounts, transactions (GraphQL API)
- Bench: Monthly financials, categorized transactions
- Chargebee: Subscriptions, invoices, MRR, customers, plans
- Recurly: Subscriptions, invoices, accounts, revenue recognition
- Shopify: Orders, revenue, products, customers, refunds

CRM (4)
- HubSpot: Deals, contacts, companies, pipeline revenue
- Salesforce: Opportunities, accounts, contacts via SOQL queries
- Pipedrive: Deals, persons, organizations, pipeline stages
- Close CRM: Leads, opportunities, activities, pipeline data

PAYROLL & HRIS (6)
- Gusto: Employees, payroll runs, compensation, benefits
- Rippling: Workers, pay runs, departments, compensation
- Deel: Contracts, invoices, payments for global teams
- RazorpayX: Payouts, fund accounts, transactions
- Keka: Employees, attendance, payroll summaries
- greytHR: Employee directory, leave, attendance, payroll

BANKING & SPEND (4)
- Plaid: Bank accounts, balances, transaction history
- Mercury: Accounts, transactions, real-time cash position
- Brex: Card transactions, accounts, statements, expenses
- Ramp: Transactions, card programs, departments, merchants

ANALYTICS (4)
- Google Analytics GA4: Sessions, users, conversions, traffic sources
- Mixpanel: Events, funnels, user profiles, retention
- ProfitWell (Paddle): MRR, churn, subscribers, revenue metrics
- Amplitude: Events, user analytics, cohort analysis, retention

ERP, DATABASE & CUSTOM (5)
- Tally: Ledger entries via Tally XML API
- NetSuite: Financial data via OAuth 1.0 HMAC-SHA256 authentication
- MySQL: Direct database queries against your MySQL instance
- REST API: Connect any service with a custom REST endpoint
- Google Sheets: Import financial data from spreadsheets

WHAT CHANGED
-------------

Every connector now makes real API calls -- authentication, data sync, error handling, and connection testing all work end-to-end. This isn't a catalog of placeholders. Each one uses httpx with proper async handling, follows the same BaseConnector interface, and stores synced data as standardized financial records.

Notable implementations:
- Stripe now calculates MRR/ARR from actual subscription data
- Wave uses GraphQL instead of REST
- NetSuite handles OAuth 1.0 with HMAC-SHA256 signature generation
- Salesforce uses SOQL for flexible data queries

HOW TO CONNECT
---------------

1. Log in: {BASE_URL}/auth
   Demo: demo@predixen.ai / demo123

2. Go to the Integrations page (sidebar)

3. Pick any connector, click Connect

4. Enter your API credentials in the form

5. Hit Connect -- the system authenticates and syncs your data

Each connector handles authentication, data sync, and error recovery. You can disconnect and reconnect at any time.

Let me know if you have questions or run into any issues with a specific connector.

--
Predixen Intelligence OS
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

<p>Last update we shipped 4 live connectors. Now all 37 connectors in the catalog are fully production-ready with real API integration. Every connector listed on the Integrations page actually works.</p>

<h3 style="font-size:16px;color:#111;margin:28px 0 12px;">37 Connectors Across 6 Categories</h3>

<h4 style="font-size:14px;color:#333;margin:22px 0 8px;">Finance &amp; Accounting (10)</h4>
<ul style="padding-left:20px;color:#333;">
<li style="margin-bottom:4px;"><strong>Stripe</strong> &mdash; MRR/ARR calculation, invoices, balance transactions, subscription analytics</li>
<li style="margin-bottom:4px;"><strong>QuickBooks</strong> &mdash; Chart of accounts, invoices, P&amp;L, balance sheet</li>
<li style="margin-bottom:4px;"><strong>Xero</strong> &mdash; Invoices, payments, P&amp;L, balance sheet, bank transactions</li>
<li style="margin-bottom:4px;"><strong>Zoho Books</strong> &mdash; Invoices, chart of accounts, bank transactions</li>
<li style="margin-bottom:4px;"><strong>FreshBooks</strong> &mdash; Invoices, expenses, clients, payments, time entries</li>
<li style="margin-bottom:4px;"><strong>Wave</strong> &mdash; Invoices, accounts, transactions (GraphQL API)</li>
<li style="margin-bottom:4px;"><strong>Bench</strong> &mdash; Monthly financials, categorized transactions</li>
<li style="margin-bottom:4px;"><strong>Chargebee</strong> &mdash; Subscriptions, invoices, MRR, customers, plans</li>
<li style="margin-bottom:4px;"><strong>Recurly</strong> &mdash; Subscriptions, invoices, accounts, revenue recognition</li>
<li style="margin-bottom:4px;"><strong>Shopify</strong> &mdash; Orders, revenue, products, customers, refunds</li>
</ul>

<h4 style="font-size:14px;color:#333;margin:22px 0 8px;">CRM (4)</h4>
<ul style="padding-left:20px;color:#333;">
<li style="margin-bottom:4px;"><strong>HubSpot</strong> &mdash; Deals, contacts, companies, pipeline revenue</li>
<li style="margin-bottom:4px;"><strong>Salesforce</strong> &mdash; Opportunities, accounts, contacts via SOQL queries</li>
<li style="margin-bottom:4px;"><strong>Pipedrive</strong> &mdash; Deals, persons, organizations, pipeline stages</li>
<li style="margin-bottom:4px;"><strong>Close CRM</strong> &mdash; Leads, opportunities, activities, pipeline data</li>
</ul>

<h4 style="font-size:14px;color:#333;margin:22px 0 8px;">Payroll &amp; HRIS (6)</h4>
<ul style="padding-left:20px;color:#333;">
<li style="margin-bottom:4px;"><strong>Gusto</strong> &mdash; Employees, payroll runs, compensation, benefits</li>
<li style="margin-bottom:4px;"><strong>Rippling</strong> &mdash; Workers, pay runs, departments, compensation</li>
<li style="margin-bottom:4px;"><strong>Deel</strong> &mdash; Contracts, invoices, payments for global teams</li>
<li style="margin-bottom:4px;"><strong>RazorpayX</strong> &mdash; Payouts, fund accounts, transactions</li>
<li style="margin-bottom:4px;"><strong>Keka</strong> &mdash; Employees, attendance, payroll summaries</li>
<li style="margin-bottom:4px;"><strong>greytHR</strong> &mdash; Employee directory, leave, attendance, payroll</li>
</ul>

<h4 style="font-size:14px;color:#333;margin:22px 0 8px;">Banking &amp; Spend (4)</h4>
<ul style="padding-left:20px;color:#333;">
<li style="margin-bottom:4px;"><strong>Plaid</strong> &mdash; Bank accounts, balances, transaction history</li>
<li style="margin-bottom:4px;"><strong>Mercury</strong> &mdash; Accounts, transactions, real-time cash position</li>
<li style="margin-bottom:4px;"><strong>Brex</strong> &mdash; Card transactions, accounts, statements, expenses</li>
<li style="margin-bottom:4px;"><strong>Ramp</strong> &mdash; Transactions, card programs, departments, merchants</li>
</ul>

<h4 style="font-size:14px;color:#333;margin:22px 0 8px;">Analytics (4)</h4>
<ul style="padding-left:20px;color:#333;">
<li style="margin-bottom:4px;"><strong>Google Analytics GA4</strong> &mdash; Sessions, users, conversions, traffic sources</li>
<li style="margin-bottom:4px;"><strong>Mixpanel</strong> &mdash; Events, funnels, user profiles, retention</li>
<li style="margin-bottom:4px;"><strong>ProfitWell (Paddle)</strong> &mdash; MRR, churn, subscribers, revenue metrics</li>
<li style="margin-bottom:4px;"><strong>Amplitude</strong> &mdash; Events, user analytics, cohort analysis, retention</li>
</ul>

<h4 style="font-size:14px;color:#333;margin:22px 0 8px;">ERP, Database &amp; Custom (5)</h4>
<ul style="padding-left:20px;color:#333;">
<li style="margin-bottom:4px;"><strong>Tally</strong> &mdash; Ledger entries via Tally XML API</li>
<li style="margin-bottom:4px;"><strong>NetSuite</strong> &mdash; Financial data via OAuth 1.0 HMAC-SHA256 authentication</li>
<li style="margin-bottom:4px;"><strong>MySQL</strong> &mdash; Direct database queries against your MySQL instance</li>
<li style="margin-bottom:4px;"><strong>REST API</strong> &mdash; Connect any service with a custom REST endpoint</li>
<li style="margin-bottom:4px;"><strong>Google Sheets</strong> &mdash; Import financial data from spreadsheets</li>
</ul>

<h3 style="font-size:16px;color:#111;margin:28px 0 12px;">What Changed</h3>

<p>Every connector now makes real API calls &mdash; authentication, data sync, error handling, and connection testing all work end-to-end. This isn&rsquo;t a catalog of placeholders. Each one uses httpx with proper async handling, follows the same BaseConnector interface, and stores synced data as standardized financial records.</p>

<p>Notable implementations:</p>
<ul style="padding-left:20px;color:#333;">
<li style="margin-bottom:4px;">Stripe now calculates MRR/ARR from actual subscription data</li>
<li style="margin-bottom:4px;">Wave uses GraphQL instead of REST</li>
<li style="margin-bottom:4px;">NetSuite handles OAuth 1.0 with HMAC-SHA256 signature generation</li>
<li style="margin-bottom:4px;">Salesforce uses SOQL for flexible data queries</li>
</ul>

<h3 style="font-size:16px;color:#111;margin:28px 0 12px;">How to Connect</h3>

<ol style="padding-left:20px;color:#333;">
<li style="margin-bottom:6px;">Log in: <a href="{BASE_URL}/auth" style="color:#4f46e5;">{BASE_URL}/auth</a><br>Demo: demo@predixen.ai / demo123</li>
<li style="margin-bottom:6px;">Go to the <strong>Integrations</strong> page (sidebar)</li>
<li style="margin-bottom:6px;">Pick any connector, click <strong>Connect</strong></li>
<li style="margin-bottom:6px;">Enter your API credentials in the form</li>
<li style="margin-bottom:6px;">Hit Connect &mdash; the system authenticates and syncs your data</li>
</ol>

<p>Each connector handles authentication, data sync, and error recovery. You can disconnect and reconnect at any time.</p>

<p>Let me know if you have questions or run into any issues with a specific connector.</p>

<p style="margin-top:30px;padding-top:15px;border-top:1px solid #e5e5e5;font-size:13px;color:#888;">
Predixen Intelligence OS
</p>

</div>
</body>
</html>"""


def send_all():
    sender = "Predixen <nfl9@predixen.app>"

    print(f"Sending full connector catalog update emails to {len(RECIPIENTS)} recipients...")
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
            subject="All 37 data connectors now live (Stripe, Salesforce, GA4, Mercury + 33 more)",
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
