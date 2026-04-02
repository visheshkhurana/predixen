"""
Send update email v33 - 100+ Users Milestone & All Features Overview.
Sender: Arjun from FounderConsole <arjun@runora.xyz>
"""
import os, sys, time, uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from server.email.service import _send_email_sync

CAMPAIGN = "founderconsole_update_apr2026_v33"

BASE_URL = "https://fund-flow.replit.app"

RECIPIENTS = [
    {"email": "nikita.luther@gmail.com", "id": "nikita_luther", "name": "Nikita"},
    {"email": "nikita@predixen.ai", "id": "nikita_predixen", "name": "Nikita"},
    {"email": "nikitafl2024@gmail.com", "id": "nikita_fl2024", "name": "Nikita"},
    {"email": "vysheshk@gmail.com", "id": "vyshesh_k", "name": "Vyshesh"},
]


def build_plain_text(rcpt: dict) -> str:
    return f"""Hi {rcpt['name']},

Big milestone -- FounderConsole just crossed 100 users.

When we started building this, the goal was simple: give founders the same financial intelligence that investors use to evaluate them. Not a dashboard. Not another spreadsheet. A system that actually thinks about your numbers and tells you what to do next.

Here's everything the platform does today.

===========================================
  THE NUMBERS (April 2026)
===========================================

  100+ Users
  9 Companies onboarded
  39 Monte Carlo simulations run
  63 Scenarios modeled
  82 Decisions scored
  27 Copilot conversations
  54 Shareholders tracked
  9 Truth Scans completed
  38 Data connectors available

===========================================
  WHAT FOUNDERCONSOLE DOES
===========================================

UNDERSTAND YOUR DATA
--------------------

Truth Engine
Upload financials (CSV, Excel, PDF) and get 24 validated metrics with industry benchmarks. Multi-stage validation catches inconsistencies, flags AI-estimated values, and establishes a single source of truth.

38 Data Connectors
QuickBooks, Stripe, Gusto, Shopify, WooCommerce, Xero, Salesforce, HubSpot, Plaid, Mercury, Brex, Ramp, and 26 more. Ecommerce connectors track COD/prepaid splits, shipping costs, refund rates, and average order value.

Digital Twin
A continuously updated virtual representation of your company. Integrates all data sources, detects stale or conflicting data, computes health scores and risk indicators in real time.


SIMULATE YOUR FUTURE
---------------------

Monte Carlo Simulation Engine
Run thousands of probabilistic scenarios with 24-month projections. See P10/P50/P90 runway, survival rates at 12/18/24 months, and sensitivity analysis up to 60 months.

Natural Language Scenarios
Type in plain English: "COD returns spike from 15% to 35%", "competitor launches similar product", "cut burn 30%", "lose 20% customers". The engine parses 65+ industry terms and runs the simulation automatically.

Flight Simulator (Multi-Agent AI)
7 LLM-powered AI agents -- Founder, 2 Investors, Customer, Team, Market, Competitor -- each with unique personas, memory, and stage-based behavior. Real-time SSE streaming, animated metrics, and a post-simulation AI report with outcome scores and strategic recommendations.

What-If Explorer
Interactive sliders for Revenue Growth, Churn Rate, Gross Margin, Burn Rate, and Fundraising. Instant real-time impact on runway, survival, and cash projections.

Stress Testing
Run scenarios across multiple variables simultaneously. Projections up to 60 months so stressed companies actually run out of cash within the window.

Scenario Versioning & Counter-Moves
Save, compare, and share scenarios. Automatic counter-move simulations with delta-based scoring against clean baselines.

Simulation Accuracy Tracker
Compares past predictions against actuals. Auto-calibration improves future projections.


MAKE BETTER DECISIONS
---------------------

Decision Scoring Engine
Survival-weighted scoring: 35% survival + 25% downside risk + 20% growth + 10% optionality + 10% reversibility. Hard caps for low-survival scenarios. Ranked recommendations with composite scores.

AI Copilot
Ask questions in plain English, get CFO-grade analysis. Multi-LLM routing (OpenAI, Anthropic, Gemini, Perplexity, Grok). Context-aware follow-ups, AI Learning Loop that improves from user feedback, and NLP recognition for 65+ financial terms.

Founder Autopilot
Daily automated risk detection and briefing generation. Triggers monthly simulation accuracy computation.

Alerts & Monitoring
Automated metric monitoring with severity-based filtering, Z-score anomaly detection, threshold alerts.


RAISE SMARTER
-------------

Cap Table Management
54 shareholders tracked. Dilution modeling across fundraising scenarios. Exit waterfall analysis.

Fundraising Readiness Score
Weighted scoring across multiple dimensions with radar chart visualization. AI-generated investment one-pager.

Investor Room
Data Room for organizing due diligence materials by category. KPI snapshots and pipeline tracking.

Board Deck Export
AI-generated board presentations in PDF and HTML. Import directly into Google Slides or PowerPoint.


PLATFORM INTELLIGENCE
---------------------

Cross-Company Learning
Privacy-first benchmarking with anonymized data. Enriches the Intelligence Graph, Decision Engine, and Copilot context.

Document Generator
AI-powered generation for financial models, investor memos, KPI reports, pitch deck outlines.

AI Graphics Studio
Professional AI graphics via OpenAI's gpt-image-1.

Hiring Planner
Plan hires by role, department, and location with salary modeling and runway impact analysis.

Activity Email Triggers
Automatic reports when simulations complete, documents are generated, or decisions are created.

Feature Flags
Runtime feature toggles with global, per-company, and per-user overrides.

AI Governance
Agent permission tracking, daily request limits, and human approval flags.


Everything is live at {BASE_URL}

We're just getting started. More features shipping every week.

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

<p>Big milestone &mdash; <strong>FounderConsole just crossed 100 users.</strong></p>

<p style="font-size:14px;color:#4b5563;">When we started building this, the goal was simple: give founders the same financial intelligence that investors use to evaluate them. Not a dashboard. Not another spreadsheet. A system that actually thinks about your numbers and tells you what to do next.</p>

<p style="font-size:14px;color:#4b5563;">Here&rsquo;s everything the platform does today.</p>

<!-- Milestone Banner -->
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:24px 0;border-radius:12px;overflow:hidden;">
<tr>
<td style="padding:28px;background:linear-gradient(135deg,#0f172a 0%,#1e293b 50%,#0f172a 100%);text-align:center;">
<p style="margin:0 0 6px;font-size:48px;font-weight:900;color:#10b981;letter-spacing:-2px;">100+</p>
<p style="margin:0 0 20px;font-size:16px;font-weight:600;color:#ffffff;letter-spacing:1px;">USERS ON FOUNDERCONSOLE</p>
<table cellpadding="0" cellspacing="0" border="0" width="100%">
<tr>
<td width="16%" style="text-align:center;padding:6px 2px;">
<p style="margin:0;font-size:22px;font-weight:800;color:#0ea5e9;">9</p>
<p style="margin:1px 0 0;font-size:9px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">Companies</p>
</td>
<td width="16%" style="text-align:center;padding:6px 2px;">
<p style="margin:0;font-size:22px;font-weight:800;color:#8b5cf6;">39</p>
<p style="margin:1px 0 0;font-size:9px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">Simulations</p>
</td>
<td width="16%" style="text-align:center;padding:6px 2px;">
<p style="margin:0;font-size:22px;font-weight:800;color:#f59e0b;">63</p>
<p style="margin:1px 0 0;font-size:9px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">Scenarios</p>
</td>
<td width="16%" style="text-align:center;padding:6px 2px;">
<p style="margin:0;font-size:22px;font-weight:800;color:#ec4899;">82</p>
<p style="margin:1px 0 0;font-size:9px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">Decisions</p>
</td>
<td width="16%" style="text-align:center;padding:6px 2px;">
<p style="margin:0;font-size:22px;font-weight:800;color:#14b8a6;">27</p>
<p style="margin:1px 0 0;font-size:9px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">AI Chats</p>
</td>
<td width="16%" style="text-align:center;padding:6px 2px;">
<p style="margin:0;font-size:22px;font-weight:800;color:#f97316;">38</p>
<p style="margin:1px 0 0;font-size:9px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">Connectors</p>
</td>
</tr>
</table>
</td>
</tr>
</table>

<!-- UNDERSTAND YOUR DATA -->
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:28px 0 16px;">
<tr><td style="padding:10px 16px;background:#0f172a;border-radius:6px;">
<p style="margin:0;font-size:13px;font-weight:700;color:#10b981;text-transform:uppercase;letter-spacing:2px;">Understand Your Data</p>
</td></tr>
</table>

<h3 style="font-size:15px;color:#1e1b4b;margin:18px 0 8px;">Truth Engine</h3>
<p style="font-size:13px;color:#4b5563;margin:0 0 6px;">Upload financials (CSV, Excel, PDF) and get 24 validated metrics with industry benchmarks. Multi-stage validation catches inconsistencies and flags AI-estimated values.</p>

<h3 style="font-size:15px;color:#1e1b4b;margin:18px 0 8px;">38 Data Connectors</h3>
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:6px 0;">
<tr><td style="padding:10px 14px;background:#f8fafc;border-left:3px solid #0ea5e9;border-radius:0 6px 6px 0;font-size:12px;color:#4b5563;">
QuickBooks &bull; Stripe &bull; Gusto &bull; Shopify &bull; WooCommerce &bull; Xero &bull; Salesforce &bull; HubSpot &bull; Plaid &bull; Mercury &bull; Brex &bull; Ramp &bull; Chargebee &bull; Recurly &bull; Rippling &bull; Deel &bull; NetSuite &bull; and 21 more. Ecommerce connectors include COD/prepaid split, shipping costs, refund rates, and AOV.
</td></tr>
</table>

<h3 style="font-size:15px;color:#1e1b4b;margin:18px 0 8px;">Digital Twin</h3>
<p style="font-size:13px;color:#4b5563;margin:0 0 6px;">Continuously updated virtual representation of your company. Integrates all data sources, detects stale or conflicting data, computes health scores and risk indicators in real time.</p>

<!-- SIMULATE YOUR FUTURE -->
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:28px 0 16px;">
<tr><td style="padding:10px 16px;background:#0f172a;border-radius:6px;">
<p style="margin:0;font-size:13px;font-weight:700;color:#8b5cf6;text-transform:uppercase;letter-spacing:2px;">Simulate Your Future</p>
</td></tr>
</table>

<h3 style="font-size:15px;color:#1e1b4b;margin:18px 0 8px;">Monte Carlo Simulation Engine</h3>
<p style="font-size:13px;color:#4b5563;margin:0 0 6px;">Thousands of probabilistic scenarios with 24-month projections. P10/P50/P90 runway, survival rates at 12/18/24 months, and sensitivity analysis up to 60 months.</p>

<h3 style="font-size:15px;color:#1e1b4b;margin:18px 0 8px;">Natural Language Scenarios</h3>
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:6px 0;">
<tr><td style="padding:10px 14px;background:#ecfdf5;border-left:3px solid #10b981;border-radius:0 6px 6px 0;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:12px;color:#4b5563;">
<tr><td style="padding:2px 0;">&ldquo;COD returns spike from 15% to 35%&rdquo; &rarr; delta-based impact</td></tr>
<tr><td style="padding:2px 0;">&ldquo;Competitor launches similar product&rdquo; &rarr; churn + growth effects</td></tr>
<tr><td style="padding:2px 0;">&ldquo;Cut burn 30%&rdquo; / &ldquo;Lose 20% customers&rdquo; &rarr; calibrated scores</td></tr>
<tr><td style="padding:2px 0;">65+ industry terms: ARR, MRR, CAC, LTV, AOV, COD, NRR, EBITDA&hellip;</td></tr>
</table>
</td></tr>
</table>

<h3 style="font-size:15px;color:#1e1b4b;margin:18px 0 8px;">Flight Simulator &mdash; Multi-Agent AI</h3>
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:6px 0;">
<tr><td style="padding:10px 14px;background:#eef2ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:12px;color:#4b5563;">
<tr><td style="padding:2px 0;">7 AI agents: Founder, 2 Investors, Customer, Team, Market, Competitor</td></tr>
<tr><td style="padding:2px 0;">LLM-generated personas with short-term + long-term memory</td></tr>
<tr><td style="padding:2px 0;">Stage-based activity: Founder early, Investors mid, Competitors late</td></tr>
<tr><td style="padding:2px 0;">Real-time SSE streaming with animated metric counters</td></tr>
<tr><td style="padding:2px 0;">Post-simulation AI report: outcome score, risks, recommendations</td></tr>
</table>
</td></tr>
</table>

<h3 style="font-size:15px;color:#1e1b4b;margin:18px 0 8px;">What-If Explorer</h3>
<p style="font-size:13px;color:#4b5563;margin:0 0 6px;">Interactive sliders for 5 key variables with instant real-time impact on runway, survival, and cash projections.</p>

<h3 style="font-size:15px;color:#1e1b4b;margin:18px 0 8px;">Stress Testing &amp; Counter-Moves</h3>
<p style="font-size:13px;color:#4b5563;margin:0 0 6px;">Multi-variable stress tests up to 60 months. Automatic counter-move simulations with delta-based scoring against clean baselines. Scenario versioning, comparison, and sharing.</p>

<!-- MAKE BETTER DECISIONS -->
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:28px 0 16px;">
<tr><td style="padding:10px 16px;background:#0f172a;border-radius:6px;">
<p style="margin:0;font-size:13px;font-weight:700;color:#f59e0b;text-transform:uppercase;letter-spacing:2px;">Make Better Decisions</p>
</td></tr>
</table>

<h3 style="font-size:15px;color:#1e1b4b;margin:18px 0 8px;">Decision Scoring Engine</h3>
<p style="font-size:13px;color:#4b5563;margin:0 0 6px;">Survival-weighted composite: 35% survival + 25% downside risk + 20% growth + 10% optionality + 10% reversibility. Hard caps for low-survival scenarios. Ranked recommendations.</p>

<h3 style="font-size:15px;color:#1e1b4b;margin:18px 0 8px;">AI Copilot</h3>
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:6px 0;">
<tr><td style="padding:10px 14px;background:#f0fdf4;border-left:3px solid #16a34a;border-radius:0 6px 6px 0;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:12px;color:#4b5563;">
<tr><td style="padding:2px 0;">Plain English questions &rarr; CFO-grade analysis</td></tr>
<tr><td style="padding:2px 0;">Multi-LLM routing: OpenAI, Anthropic, Gemini, Perplexity, Grok</td></tr>
<tr><td style="padding:2px 0;">AI Learning Loop: user feedback improves future responses</td></tr>
<tr><td style="padding:2px 0;">Context-aware follow-ups from randomized topic pools</td></tr>
</table>
</td></tr>
</table>

<h3 style="font-size:15px;color:#1e1b4b;margin:18px 0 8px;">Founder Autopilot &amp; Alerts</h3>
<p style="font-size:13px;color:#4b5563;margin:0 0 6px;">Daily automated risk detection and briefings. Z-score anomaly detection, threshold monitoring, severity-based alert filtering.</p>

<!-- RAISE SMARTER -->
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:28px 0 16px;">
<tr><td style="padding:10px 16px;background:#0f172a;border-radius:6px;">
<p style="margin:0;font-size:13px;font-weight:700;color:#ec4899;text-transform:uppercase;letter-spacing:2px;">Raise Smarter</p>
</td></tr>
</table>

<h3 style="font-size:15px;color:#1e1b4b;margin:18px 0 8px;">Fundraising OS</h3>
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:6px 0;">
<tr><td style="padding:10px 14px;background:#fdf2f8;border-left:3px solid #ec4899;border-radius:0 6px 6px 0;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:12px;color:#4b5563;">
<tr><td style="padding:2px 0;">Cap Table &mdash; 54 shareholders, dilution modeling, exit waterfall</td></tr>
<tr><td style="padding:2px 0;">Fundraising Readiness Score &mdash; weighted radar chart + AI one-pager</td></tr>
<tr><td style="padding:2px 0;">Investor Room &mdash; data room, KPI snapshots, pipeline tracking</td></tr>
<tr><td style="padding:2px 0;">Board Deck Export &mdash; AI-generated PDF/HTML presentations</td></tr>
</table>
</td></tr>
</table>

<!-- PLATFORM INTELLIGENCE -->
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:28px 0 16px;">
<tr><td style="padding:10px 16px;background:#0f172a;border-radius:6px;">
<p style="margin:0;font-size:13px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:2px;">Platform Intelligence</p>
</td></tr>
</table>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:6px 0;">
<tr><td style="padding:10px 14px;background:#f8fafc;border-left:3px solid #64748b;border-radius:0 6px 6px 0;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:12px;color:#4b5563;">
<tr><td style="padding:2px 0;"><strong>Cross-Company Learning</strong> &mdash; privacy-first benchmarking with anonymized data</td></tr>
<tr><td style="padding:2px 0;"><strong>Document Generator</strong> &mdash; financial models, investor memos, KPI reports, pitch outlines</td></tr>
<tr><td style="padding:2px 0;"><strong>AI Graphics Studio</strong> &mdash; professional graphics via OpenAI gpt-image-1</td></tr>
<tr><td style="padding:2px 0;"><strong>Hiring Planner</strong> &mdash; role/department/location with salary + runway impact</td></tr>
<tr><td style="padding:2px 0;"><strong>Simulation Accuracy Tracker</strong> &mdash; compares predictions vs actuals, auto-calibration</td></tr>
<tr><td style="padding:2px 0;"><strong>Activity Email Triggers</strong> &mdash; auto-reports on simulation, document, and decision events</td></tr>
<tr><td style="padding:2px 0;"><strong>Feature Flags</strong> &mdash; runtime toggles with global/company/user overrides</td></tr>
<tr><td style="padding:2px 0;"><strong>AI Governance</strong> &mdash; agent permissions, daily limits, human approval flags</td></tr>
</table>
</td></tr>
</table>

<!-- CTA -->
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:32px 0;">
<tr>
<td style="text-align:center;">
<a href="{BASE_URL}" style="display:inline-block;padding:16px 40px;background:linear-gradient(135deg,#10b981 0%,#0d9488 100%);color:#ffffff;text-decoration:none;font-weight:700;font-size:16px;border-radius:10px;letter-spacing:0.5px;">Open FounderConsole</a>
</td>
</tr>
</table>

<p style="font-size:14px;color:#4b5563;text-align:center;">We&rsquo;re just getting started. More features shipping every week.</p>

<p style="margin-top:30px;padding-top:15px;border-top:1px solid #e5e5e5;font-size:13px;color:#888;">
Arjun<br>FounderConsole
</p>

</div>
<img src="{open_tracking_url}" width="1" height="1" style="display:none" alt="" />
</body>
</html>"""


def send_all():
    sender = "Arjun from FounderConsole <arjun@runora.xyz>"

    print(f"Sending update v33 to {len(RECIPIENTS)} recipients...")
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
            subject="FounderConsole Crossed 100 Users — Here's Everything the Platform Does Today",
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
