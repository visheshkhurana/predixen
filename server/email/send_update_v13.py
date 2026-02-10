"""
Send update email v13 to 4 recipients.
Transactional-style: minimal HTML, plain-text companion.
Content: Multi-currency support with 33 global currencies.
Sender: nfl9@predixen.app
"""
import os, sys, time, uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from server.email.service import _send_email_sync

CAMPAIGN = "predixen_multi_currency_feb2026_v13"
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

Predixen now supports 33 global currencies across the entire platform.

MULTI-CURRENCY SUPPORT
-----------------------

You can now set your company's base currency to any of 33 supported currencies. All financial displays -- dashboard, KPI cards, simulations, charts, and data tables -- automatically show values in your selected currency.

Supported currencies:
- Americas: USD, CAD, BRL, MXN
- Europe: EUR, GBP, CHF, SEK, NOK, DKK, PLN, CZK, HUF, RON, BGN, ISK, TRY
- Asia-Pacific: INR, SGD, JPY, CNY, HKD, KRW, TWD, THB, IDR, MYR, PHP
- Middle East & Africa: AED, ILS, ZAR
- Oceania: AUD, NZD

HOW IT WORKS
-------------

1. Exchange rates are sourced from the European Central Bank via frankfurter.app (free, no API key needed)
2. Rates are cached for 6 hours with static fallback rates when the API is unavailable
3. Financial records track the original currency and FX rate used, so data is always auditable
4. Currency conversion API available for programmatic use

WHAT'S UPDATED
---------------

Every financial display across the platform now respects your company currency:
- Dashboard KPI cards (MRR, ARR, Cash Balance, Runway)
- Simulation summaries and Monte Carlo results
- Cash flow charts and trend lines
- Decision ranking tables
- Data input tables and CSV imports
- Scenario comparison views

Currency symbols, formatting, and decimal handling adapt automatically (e.g., JPY has no decimals, INR uses the Indian numbering system).

HOW TO SET YOUR CURRENCY
--------------------------

1. Log in: {BASE_URL}/auth
   Demo: demo@predixen.ai / demo123

2. Click the company name in the sidebar

3. Select "Edit Company"

4. Choose your currency from the dropdown (33 options)

5. All financial displays update immediately

Let me know if you have questions.

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

<p>Predixen now supports <strong>33 global currencies</strong> across the entire platform.</p>

<h3 style="font-size:16px;color:#111;margin:28px 0 12px;">Multi-Currency Support</h3>

<p>You can now set your company's base currency to any of 33 supported currencies. All financial displays &mdash; dashboard, KPI cards, simulations, charts, and data tables &mdash; automatically show values in your selected currency.</p>

<table style="width:100%;border-collapse:collapse;margin:16px 0;">
<tr>
<td style="vertical-align:top;padding:8px 12px 8px 0;border-bottom:1px solid #eee;width:50%;">
<strong style="font-size:13px;color:#555;">Americas</strong><br>
<span style="font-size:13px;color:#333;">USD, CAD, BRL, MXN</span>
</td>
<td style="vertical-align:top;padding:8px 0 8px 12px;border-bottom:1px solid #eee;width:50%;">
<strong style="font-size:13px;color:#555;">Europe</strong><br>
<span style="font-size:13px;color:#333;">EUR, GBP, CHF, SEK, NOK, DKK, PLN, CZK, HUF, RON, BGN, ISK, TRY</span>
</td>
</tr>
<tr>
<td style="vertical-align:top;padding:8px 12px 8px 0;border-bottom:1px solid #eee;">
<strong style="font-size:13px;color:#555;">Asia-Pacific</strong><br>
<span style="font-size:13px;color:#333;">INR, SGD, JPY, CNY, HKD, KRW, TWD, THB, IDR, MYR, PHP</span>
</td>
<td style="vertical-align:top;padding:8px 0 8px 12px;border-bottom:1px solid #eee;">
<strong style="font-size:13px;color:#555;">Middle East, Africa &amp; Oceania</strong><br>
<span style="font-size:13px;color:#333;">AED, ILS, ZAR, AUD, NZD</span>
</td>
</tr>
</table>

<h3 style="font-size:16px;color:#111;margin:28px 0 12px;">How It Works</h3>

<ul style="padding-left:20px;color:#333;">
<li style="margin-bottom:6px;">Exchange rates sourced from the <strong>European Central Bank</strong> (free, no API key needed)</li>
<li style="margin-bottom:6px;">Rates cached for 6 hours with static fallback when API is unavailable</li>
<li style="margin-bottom:6px;">Financial records track original currency and FX rate for full auditability</li>
<li style="margin-bottom:6px;">Currency conversion API available for programmatic use</li>
</ul>

<h3 style="font-size:16px;color:#111;margin:28px 0 12px;">What's Updated</h3>

<p>Every financial display across the platform now respects your company currency:</p>

<ul style="padding-left:20px;color:#333;">
<li style="margin-bottom:4px;">Dashboard KPI cards (MRR, ARR, Cash Balance, Runway)</li>
<li style="margin-bottom:4px;">Simulation summaries and Monte Carlo results</li>
<li style="margin-bottom:4px;">Cash flow charts and trend lines</li>
<li style="margin-bottom:4px;">Decision ranking tables</li>
<li style="margin-bottom:4px;">Data input tables and CSV imports</li>
<li style="margin-bottom:4px;">Scenario comparison views</li>
</ul>

<p>Currency symbols, formatting, and decimal handling adapt automatically (e.g., JPY has no decimals, INR uses the correct symbol).</p>

<h3 style="font-size:16px;color:#111;margin:28px 0 12px;">How to Set Your Currency</h3>

<ol style="padding-left:20px;color:#333;">
<li style="margin-bottom:6px;">Log in: <a href="{BASE_URL}/auth" style="color:#4f46e5;">{BASE_URL}/auth</a><br>Demo: demo@predixen.ai / demo123</li>
<li style="margin-bottom:6px;">Click the company name in the sidebar</li>
<li style="margin-bottom:6px;">Select <strong>&ldquo;Edit Company&rdquo;</strong></li>
<li style="margin-bottom:6px;">Choose your currency from the dropdown (33 options)</li>
<li style="margin-bottom:6px;">All financial displays update immediately</li>
</ol>

<p>Let me know if you have questions.</p>

<p style="margin-top:30px;padding-top:15px;border-top:1px solid #e5e5e5;font-size:13px;color:#888;">
Predixen Intelligence OS
</p>

</div>
</body>
</html>"""


def send_all():
    sender = "Predixen <nfl9@predixen.app>"

    print(f"Sending multi-currency update emails to {len(RECIPIENTS)} recipients...")
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
            subject="New: Multi-currency support (33 global currencies)",
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
