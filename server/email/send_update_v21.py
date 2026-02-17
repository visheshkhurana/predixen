"""
Send update email v21 - QA Lab: Automated Testing Infrastructure & 150/150 Report.
Sender: f5987291@founderconsole.ai
"""
import os, sys, time, uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from server.email.service import _send_email_sync

CAMPAIGN = "founderconsole_qa_lab_report_feb2026_v21"

RECIPIENTS = [
    {"email": "nikita.luther@gmail.com", "id": "nikita_luther", "name": "Nikita"},
    {"email": "nikita@founderconsole.ai", "id": "nikita_founderconsole", "name": "Nikita"},
    {"email": "nikitafl2024@gmail.com", "id": "nikita_fl2024", "name": "Nikita"},
]


def build_plain_text(rcpt: dict) -> str:
    return f"""Hi {rcpt['name']},

We've built a fully automated QA Lab for FounderConsole's simulation engine. Here's what it does and the latest results.

---

QA LAB v1.0 - AUTOMATED TESTING INFRASTRUCTURE

---

WHAT IS THE QA LAB?

The QA Lab is an automated testing system that validates every financial calculation in FounderConsole. It creates synthetic companies, seeds them with financial data, runs simulations, and checks the results against canonical formulas. You can run it anytime with a single command: bash qa-lab/run.sh

It generates a full markdown report at qa-lab/latest-report.md that's ready to paste into Notion or Jira.

---

LATEST RESULTS: 150/150 TESTS PASSING

Total Tests: 150
Passed: 150
Failed: 0
Pass Rate: 100%
Runtime: ~12 seconds

---

TEST BREAKDOWN

1. BASELINE VALIDATION (15 tests)

15 synthetic companies across USD, INR, different scales (units, millions), and different industries (SaaS, logistics, fintech, healthcare, edtech, gaming, etc.). Each one validates:
- COGS = Revenue x (1 - Gross Margin / 100)
- Total Expenses = COGS + Opex + Payroll + Other Costs
- Net Burn = Total Expenses - Revenue
- Runway = Cash / Net Burn (or Infinite if profitable)

Companies tested:
- DS01 FlowForge (Seed SaaS, USD) - 11.7mo runway
- DS02 CloudLedger (Profitable SaaS, USD) - Infinite runway
- DS03 GlowCart (D2C E-commerce, INR Millions) - 6.7mo runway
- DS04 BazaarBridge (Marketplace, INR Millions) - 5.5mo runway
- DS05 Shadowbox Logistics (Pre-IPO Logistics, INR Millions) - Infinite runway
- DS06 CredPulse (Fintech, INR Millions) - 5.2mo runway
- DS07 ProtoFab (Manufacturing, INR Millions) - 25mo runway
- DS08 StudioSprint (Agency, INR Millions) - 3mo runway
- DS09 ArenaNova (Gaming, USD) - 18.5mo runway
- DS10 CareArc Clinics (Healthcare, INR Millions) - 5mo runway
- DS11 TutorLoop (Edtech, INR Millions) - 6.2mo runway
- DS12 ApexExchange (Crypto, INR Millions) - Infinite runway
- DS13 ZeroRev Labs (Pre-revenue, USD) - 4.7mo runway
- DS14 MaxGM Co (100% Gross Margin edge case, USD) - Infinite runway
- DS15 MinGM Co (0% Gross Margin edge case, USD) - 7.5mo runway

---

2. SCENARIO TESTS (120 tests = 8 scenarios x 15 datasets)

Each of the 15 companies is tested against 8 scenarios:
- S0: Baseline identity (no changes)
- S1: Pricing Lift (+5% Revenue)
- S2: Demand Shock (-15% Revenue)
- S3: Cost Optimization (+3pp Gross Margin, capped at 100%)
- S4: Hiring Wave (+10% Payroll)
- S5: Marketing Push (+20% Opex)
- S6: Cash Event (-30% Cash)
- S7: Mixed Stack (S1+S4+S5 combined, then reset to baseline)

Each test validates directional correctness: if revenue goes up 5%, the output should show higher revenue. If payroll goes up 10%, expenses should increase. Zero-revenue edge cases (DS13) are handled correctly - 5% of $0 is still $0.

---

3. MONTE CARLO REPRODUCIBILITY (15 tests)

Each company is simulated twice with seed=42 and 1000 iterations. The test verifies that both runs produce byte-identical P10/P50/P90 runway distributions and survival probabilities. All 15 pass - confirming full deterministic reproducibility.

---

BUGS & FEATURE IDEAS IDENTIFIED

The report also generates a prioritized backlog of 15 improvement ideas organized by category:

Trust (P0):
- Add "last updated" badge when financial data is stale
- Show "estimated" badge for metrics using fallback values
- Thread currency symbol through simulation output charts

Onboarding:
- Add pre-revenue onboarding flow with milestone tracking
- Show live preview of amount scale (e.g., "25M displays as 25")

Scenario Builder:
- Add start/end month pickers for time-phased scenarios
- Add scenario composition builder with drag-and-drop
- Add "Reset to Baseline" button

Outputs:
- Show delta indicators for changed inputs vs baseline
- Add PDF/PNG export for board decks
- Display seed + iteration count in results footer
- Side-by-side before/after comparison view

Data Quality:
- Use Decimal for financial calculations to avoid floating point drift
- Add server-side GM clamp + UI warning
- Centralize scale conversion in response serializer

---

FOUNDER TAKEAWAYS BY PERSONA

The report includes persona-based insights for each test company. For example:
- Shadowbox Logistics (your beta company profile): Infinite runway, focus on growth investment
- StudioSprint (agency): 3mo runway, immediate action needed
- ZeroRev Labs (pre-revenue): 4.7mo runway, consider fundraising

---

The full report is at qa-lab/latest-report.md and can be re-generated anytime with bash qa-lab/run.sh.

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

<p>We've built a fully automated QA Lab for FounderConsole's simulation engine. Here's what it does and the latest results.</p>

<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #6366f1;">QA Lab v1.0 &mdash; Automated Testing Infrastructure</h2>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:16px 0;">

<tr>
<td style="padding:14px 16px;background:#f0fdf4;border-left:3px solid #16a34a;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:16px;color:#15803d;">150 / 150 Tests Passing</p>
<p style="margin:0;font-size:13px;color:#4b5563;">15 baseline validations + 120 scenario tests (8 scenarios &times; 15 datasets) + 15 Monte Carlo reproducibility checks. Runtime: ~12 seconds. Run anytime with <code style="background:#f3f4f6;padding:2px 5px;border-radius:3px;font-size:12px;">bash qa-lab/run.sh</code></p>
</td>
</tr>
<tr><td style="height:14px;"></td></tr>

</table>

<h3 style="font-size:15px;color:#1e1b4b;margin:24px 0 8px;">What Does It Test?</h3>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">

<tr>
<td style="padding:12px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#4338ca;">1. Baseline Validation (15 tests)</p>
<p style="margin:0;font-size:13px;color:#4b5563;">15 synthetic companies across USD/INR, different scales, and 11+ industries. Each validates canonical formulas: <strong>COGS = Rev &times; (1 - GM/100)</strong>, <strong>Net Burn = Expenses - Revenue</strong>, <strong>Runway = Cash / Net Burn</strong>. Covers edge cases like zero-revenue (DS13), 100% GM (DS14), 0% GM (DS15), and profitable companies with infinite runway.</p>
</td>
</tr>
<tr><td style="height:8px;"></td></tr>

<tr>
<td style="padding:12px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#4338ca;">2. Scenario Tests (120 tests)</p>
<p style="margin:0;font-size:13px;color:#4b5563;">8 scenarios applied to all 15 companies: Pricing Lift (+5% Rev), Demand Shock (-15% Rev), Cost Optimization (+3pp GM), Hiring Wave (+10% Payroll), Marketing Push (+20% Opex), Cash Event (-30% Cash), Mixed Stack (S1+S4+S5 combined then reset). Each validates directional correctness.</p>
</td>
</tr>
<tr><td style="height:8px;"></td></tr>

<tr>
<td style="padding:12px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#4338ca;">3. Monte Carlo Reproducibility (15 tests)</p>
<p style="margin:0;font-size:13px;color:#4b5563;">Each company simulated <strong>twice</strong> with seed=42 and 1,000 iterations. Verifies byte-identical P10/P50/P90 runway distributions and survival probabilities across both runs. Confirms full deterministic reproducibility.</p>
</td>
</tr>

</table>

<h3 style="font-size:15px;color:#1e1b4b;margin:24px 0 8px;">Test Companies</h3>

<table cellpadding="6" cellspacing="0" border="0" width="100%" style="margin:10px 0;font-size:12px;border:1px solid #e5e7eb;border-radius:6px;border-collapse:collapse;">
<tr style="background:#f9fafb;">
<th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;">ID</th>
<th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;">Company</th>
<th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;">Type</th>
<th style="text-align:right;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;">Runway</th>
</tr>
<tr><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">DS01</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">FlowForge</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">Seed SaaS</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;text-align:right;">11.7mo</td></tr>
<tr><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">DS02</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">CloudLedger</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">Profitable SaaS</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;text-align:right;color:#16a34a;font-weight:600;">Infinite</td></tr>
<tr><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">DS03</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">GlowCart</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">D2C (INR)</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;text-align:right;">6.7mo</td></tr>
<tr><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">DS04</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">BazaarBridge</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">Marketplace (INR)</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;text-align:right;color:#dc2626;font-weight:600;">5.5mo</td></tr>
<tr><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">DS05</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">Shadowbox Logistics</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">Logistics (INR)</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;text-align:right;color:#16a34a;font-weight:600;">Infinite</td></tr>
<tr><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">DS06</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">CredPulse</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">Fintech (INR)</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;text-align:right;color:#dc2626;font-weight:600;">5.2mo</td></tr>
<tr><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">DS07</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">ProtoFab</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">Manufacturing (INR)</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;text-align:right;">25mo</td></tr>
<tr><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">DS08</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">StudioSprint</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">Agency (INR)</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;text-align:right;color:#dc2626;font-weight:600;">3mo</td></tr>
<tr><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">DS09</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">ArenaNova</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">Gaming (USD)</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;text-align:right;">18.5mo</td></tr>
<tr><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">DS10</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">CareArc Clinics</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">Healthcare (INR)</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;text-align:right;color:#dc2626;font-weight:600;">5mo</td></tr>
<tr><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">DS11</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">TutorLoop</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">Edtech (INR)</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;text-align:right;">6.2mo</td></tr>
<tr><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">DS12</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">ApexExchange</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">Crypto (INR)</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;text-align:right;color:#16a34a;font-weight:600;">Infinite</td></tr>
<tr><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">DS13</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">ZeroRev Labs</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">Pre-revenue (USD)</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;text-align:right;color:#dc2626;font-weight:600;">4.7mo</td></tr>
<tr><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">DS14</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">MaxGM Co</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">100% GM edge case</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;text-align:right;color:#16a34a;font-weight:600;">Infinite</td></tr>
<tr><td style="padding:6px 8px;">DS15</td><td style="padding:6px 8px;">MinGM Co</td><td style="padding:6px 8px;">0% GM edge case</td><td style="padding:6px 8px;text-align:right;">7.5mo</td></tr>
</table>

<h3 style="font-size:15px;color:#1e1b4b;margin:24px 0 8px;">Bugs &amp; Feature Ideas Identified (15 items)</h3>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:12px 16px;background:#fef2f2;border-left:3px solid #dc2626;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#b91c1c;">Trust (P0) &mdash; 3 items</p>
<p style="margin:0;font-size:13px;color:#4b5563;">&bull; Add &ldquo;last updated&rdquo; badge when financial data is stale<br>&bull; Show &ldquo;estimated&rdquo; badge for metrics using fallback values<br>&bull; Thread currency symbol through simulation output charts</p>
</td>
</tr>
<tr><td style="height:8px;"></td></tr>

<tr>
<td style="padding:12px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#4338ca;">Scenario Builder &mdash; 3 items</p>
<p style="margin:0;font-size:13px;color:#4b5563;">&bull; Time-phased scenario support (start/end month pickers)<br>&bull; Scenario composition builder with drag-and-drop<br>&bull; &ldquo;Reset to Baseline&rdquo; button after applying scenarios</p>
</td>
</tr>
<tr><td style="height:8px;"></td></tr>

<tr>
<td style="padding:12px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#4338ca;">Outputs &amp; Explainability &mdash; 4 items</p>
<p style="margin:0;font-size:13px;color:#4b5563;">&bull; Delta indicators showing input changes vs baseline<br>&bull; PDF/PNG export for board decks<br>&bull; Display seed + iteration count in results footer<br>&bull; Side-by-side before/after comparison view</p>
</td>
</tr>
<tr><td style="height:8px;"></td></tr>

<tr>
<td style="padding:12px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#4338ca;">Onboarding + Data Quality &mdash; 5 items</p>
<p style="margin:0;font-size:13px;color:#4b5563;">&bull; Pre-revenue onboarding flow with milestone tracking<br>&bull; Live preview of amount scale selection<br>&bull; Decimal precision for financial calculations<br>&bull; Server-side GM clamp + UI warning<br>&bull; Centralized scale conversion in response serializer</p>
</td>
</tr>

</table>

<h3 style="font-size:15px;color:#1e1b4b;margin:24px 0 8px;">How To Run</h3>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:12px 16px;background:#f3f4f6;border-radius:6px;">
<p style="margin:0;font-size:13px;color:#4b5563;">
<strong>Run all tests:</strong> <code style="background:#e5e7eb;padding:2px 5px;border-radius:3px;font-size:12px;">bash qa-lab/run.sh</code><br>
<strong>Report location:</strong> <code style="background:#e5e7eb;padding:2px 5px;border-radius:3px;font-size:12px;">qa-lab/latest-report.md</code><br>
<strong>Datasets:</strong> <code style="background:#e5e7eb;padding:2px 5px;border-radius:3px;font-size:12px;">qa-lab/datasets/all-datasets.json</code> (15 companies)<br>
<strong>Scenarios:</strong> <code style="background:#e5e7eb;padding:2px 5px;border-radius:3px;font-size:12px;">qa-lab/scenarios/all-scenarios.json</code> (8 scenarios)<br>
<strong>Runner:</strong> <code style="background:#e5e7eb;padding:2px 5px;border-radius:3px;font-size:12px;">qa-lab/runner/qa_runner.py</code>
</p>
</td>
</tr>
</table>

<p style="font-size:14px;color:#4b5563;margin-top:20px;">The full report is Notion/Jira-ready markdown with summary tables, pass/fail for every test, and a prioritized improvement backlog.</p>

<p style="margin-top:30px;padding-top:15px;border-top:1px solid #e5e5e5;font-size:13px;color:#888;">
FounderConsole
</p>

</div>
</body>
</html>"""


def send_all():
    sender = "FounderConsole <f5987291@founderconsole.ai>"

    print(f"Sending QA Lab Report update v21 to {len(RECIPIENTS)} recipients...")
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
            subject="FounderConsole QA Lab v1.0 - 150/150 Tests Passing: Automated Testing Infrastructure Live",
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
