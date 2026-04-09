"""
Send update email v34 - 125 Active Users & Complete Feature Overview.
Sender: Arjun from FounderConsole <arjun@runora.xyz>
"""
import os, sys, time, uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from server.email.service import _send_email_sync

CAMPAIGN = "founderconsole_update_apr2026_v34"

BASE_URL = "https://fund-flow.replit.app"

RECIPIENTS = [
    {"email": "nikita.luther@gmail.com", "id": "nikita_luther", "name": "Nikita"},
    {"email": "nikita@predixen.ai", "id": "nikita_predixen", "name": "Nikita"},
    {"email": "nikitafl2024@gmail.com", "id": "nikita_fl2024", "name": "Nikita"},
    {"email": "vysheshk@gmail.com", "id": "vyshesh_k", "name": "Vyshesh"},
]


def build_plain_text(rcpt: dict) -> str:
    return f"""Hi {rcpt['name']},

Quick update — FounderConsole now has 125 active users.

Growth is picking up. More founders are running simulations, scoring decisions, and using the AI Copilot every week. Here's a snapshot of where things stand and everything the platform offers today.

===========================================
  PLATFORM SNAPSHOT (April 2026)
===========================================

  125 Active Users
  9 Companies onboarded
  39+ Simulations run
  63+ Scenarios modeled
  82+ Decisions scored & tracked
  27+ AI Copilot conversations
  54 Shareholders managed
  38 Data connectors available
  854 Investors in database

===========================================
  FULL FEATURE SET
===========================================

DATA & INTELLIGENCE
-------------------

Truth Engine
Upload financials (CSV, Excel, PDF) — get 24 validated metrics with industry benchmarks. Multi-stage validation catches inconsistencies and flags AI-estimated values.

38 Data Connectors
QuickBooks, Stripe, Gusto, Shopify, WooCommerce, Xero, Salesforce, HubSpot, Plaid, Mercury, Brex, Ramp, Chargebee, Recurly, Rippling, Deel, NetSuite, and 21 more. Ecommerce connectors track COD/prepaid splits, shipping costs, refund rates, and AOV.

Digital Twin
Continuously updated virtual representation of your company. Integrates all data sources, detects stale or conflicting data, computes health scores and risk indicators in real time.

Data Confidence Engine
Metric reliability scoring based on freshness, source diversity, and consistency.


SIMULATION & FORECASTING
-------------------------

Monte Carlo Simulation Engine
Thousands of probabilistic scenarios with 24-month projections. P10/P50/P90 runway, survival rates at 12/18/24 months, and sensitivity analysis up to 60 months.

Natural Language Scenarios
Type in plain English: "COD returns spike from 15% to 35%", "competitor launches similar product", "cut burn 30%". The engine parses 65+ industry terms and runs the simulation automatically.

Flight Simulator — Multi-Agent AI
7 LLM-powered AI agents (Founder, 2 Investors, Customer, Team, Market, Competitor) with unique personas, memory, and stage-based behavior. Real-time streaming with animated metrics. Post-simulation AI report with outcome scores and recommendations.

What-If Explorer
Interactive sliders for Revenue Growth, Churn Rate, Gross Margin, Burn Rate, and Fundraising with instant real-time impact calculations.

Stress Testing & Counter-Moves
Multi-variable stress tests up to 60 months. Automatic counter-move simulations with delta-based scoring. Scenario versioning, comparison, and sharing.

Simulation Accuracy Tracker
Compares past predictions against actuals. Auto-calibration improves future projections.


DECISIONS & AI
--------------

Decision Scoring Engine
Survival-weighted composite scoring: 35% survival + 25% downside risk + 20% growth + 10% optionality + 10% reversibility. Ranked recommendations with outcome tracking.

Decision Outcome Tracking
Track actual outcomes against predictions. Measure decision quality over time.

AI Copilot
Plain English questions get CFO-grade analysis. Multi-LLM routing (OpenAI, Anthropic, Gemini, Perplexity, Grok). AI Learning Loop improves from user feedback. Context-aware follow-ups.

Founder Autopilot
Daily automated risk detection and briefings. Triggers monthly simulation accuracy computation.

Alerts & Monitoring
Automated metric monitoring with severity-based filtering, Z-score anomaly detection, threshold alerts.


FUNDRAISING
-----------

Cap Table Management
54 shareholders tracked. Dilution modeling across fundraising scenarios. Exit waterfall analysis.

Fundraising Readiness Score
Weighted scoring across multiple dimensions with radar chart. AI-generated investment one-pager.

Investor Database
854 investors with firm, stage, sector, and geography data. Search, filter, and track outreach.

Investor Room & Data Room
Organized due diligence materials by category. KPI snapshots and pipeline tracking.

Outreach Sequences
Manage investor outreach campaigns with sequenced follow-ups.

Board Deck Export
AI-generated board presentations in PDF and HTML.

Fundraising CRM
Dashboard banner, pipeline management, and investor tracking.


PLATFORM TOOLS
--------------

Cross-Company Learning — privacy-first benchmarking with anonymized data
Document Generator — financial models, investor memos, KPI reports, pitch outlines
AI Graphics Studio — professional graphics via OpenAI gpt-image-1
Hiring Planner — role/department/location with salary + runway impact
Activity Email Triggers — auto-reports on simulation, document, and decision events
Feature Flags — runtime toggles with global/company/user overrides
AI Governance — agent permissions, daily limits, human approval flags
Intelligence Graph — related metrics and strategy pattern discovery


Everything is live at {BASE_URL}

We're shipping new features every week. More updates coming soon.

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

<p>Quick update &mdash; <strong>FounderConsole now has 125 active users.</strong></p>

<p style="font-size:14px;color:#4b5563;">Growth is picking up. More founders are running simulations, scoring decisions, and using the AI Copilot every week. Here&rsquo;s where things stand.</p>

<!-- Milestone Banner -->
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:24px 0;border-radius:12px;overflow:hidden;">
<tr>
<td style="padding:28px;background:linear-gradient(135deg,#0f172a 0%,#1e293b 50%,#0f172a 100%);text-align:center;">
<p style="margin:0 0 6px;font-size:52px;font-weight:900;color:#10b981;letter-spacing:-2px;">125</p>
<p style="margin:0 0 22px;font-size:15px;font-weight:600;color:#ffffff;letter-spacing:1.5px;">ACTIVE USERS</p>
<table cellpadding="0" cellspacing="0" border="0" width="100%">
<tr>
<td width="14%" style="text-align:center;padding:6px 2px;">
<p style="margin:0;font-size:20px;font-weight:800;color:#0ea5e9;">9</p>
<p style="margin:1px 0 0;font-size:9px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">Companies</p>
</td>
<td width="14%" style="text-align:center;padding:6px 2px;">
<p style="margin:0;font-size:20px;font-weight:800;color:#8b5cf6;">39</p>
<p style="margin:1px 0 0;font-size:9px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">Simulations</p>
</td>
<td width="14%" style="text-align:center;padding:6px 2px;">
<p style="margin:0;font-size:20px;font-weight:800;color:#f59e0b;">63</p>
<p style="margin:1px 0 0;font-size:9px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">Scenarios</p>
</td>
<td width="14%" style="text-align:center;padding:6px 2px;">
<p style="margin:0;font-size:20px;font-weight:800;color:#ec4899;">82</p>
<p style="margin:1px 0 0;font-size:9px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">Decisions</p>
</td>
<td width="14%" style="text-align:center;padding:6px 2px;">
<p style="margin:0;font-size:20px;font-weight:800;color:#14b8a6;">27</p>
<p style="margin:1px 0 0;font-size:9px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">AI Chats</p>
</td>
<td width="14%" style="text-align:center;padding:6px 2px;">
<p style="margin:0;font-size:20px;font-weight:800;color:#f97316;">854</p>
<p style="margin:1px 0 0;font-size:9px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">Investors</p>
</td>
<td width="14%" style="text-align:center;padding:6px 2px;">
<p style="margin:0;font-size:20px;font-weight:800;color:#6366f1;">38</p>
<p style="margin:1px 0 0;font-size:9px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">Connectors</p>
</td>
</tr>
</table>
</td>
</tr>
</table>

<!-- DATA & INTELLIGENCE -->
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:28px 0 16px;">
<tr><td style="padding:10px 16px;background:#0f172a;border-radius:6px;">
<p style="margin:0;font-size:13px;font-weight:700;color:#10b981;text-transform:uppercase;letter-spacing:2px;">Data &amp; Intelligence</p>
</td></tr>
</table>

<h3 style="font-size:15px;color:#1e1b4b;margin:18px 0 8px;">Truth Engine</h3>
<p style="font-size:13px;color:#4b5563;margin:0 0 6px;">Upload financials (CSV, Excel, PDF) &mdash; get 24 validated metrics with industry benchmarks. Multi-stage validation catches inconsistencies and flags AI-estimated values.</p>

<h3 style="font-size:15px;color:#1e1b4b;margin:18px 0 8px;">38 Data Connectors</h3>
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:6px 0;">
<tr><td style="padding:10px 14px;background:#f8fafc;border-left:3px solid #0ea5e9;border-radius:0 6px 6px 0;font-size:12px;color:#4b5563;">
QuickBooks &bull; Stripe &bull; Gusto &bull; Shopify &bull; WooCommerce &bull; Xero &bull; Salesforce &bull; HubSpot &bull; Plaid &bull; Mercury &bull; Brex &bull; Ramp &bull; Chargebee &bull; Recurly &bull; Rippling &bull; Deel &bull; NetSuite &bull; and 21 more. Ecommerce: COD/prepaid split, shipping costs, refund rates, AOV.
</td></tr>
</table>

<h3 style="font-size:15px;color:#1e1b4b;margin:18px 0 8px;">Digital Twin</h3>
<p style="font-size:13px;color:#4b5563;margin:0 0 6px;">Continuously updated virtual company representation. Health scores, risk indicators, intelligent data source selection when sources conflict.</p>

<h3 style="font-size:15px;color:#1e1b4b;margin:18px 0 8px;">Data Confidence Engine</h3>
<p style="font-size:13px;color:#4b5563;margin:0 0 6px;">Metric reliability scoring based on freshness, source diversity, and consistency.</p>

<!-- SIMULATION & FORECASTING -->
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:28px 0 16px;">
<tr><td style="padding:10px 16px;background:#0f172a;border-radius:6px;">
<p style="margin:0;font-size:13px;font-weight:700;color:#8b5cf6;text-transform:uppercase;letter-spacing:2px;">Simulation &amp; Forecasting</p>
</td></tr>
</table>

<h3 style="font-size:15px;color:#1e1b4b;margin:18px 0 8px;">Monte Carlo Simulation Engine</h3>
<p style="font-size:13px;color:#4b5563;margin:0 0 6px;">Thousands of probabilistic scenarios with 24-month projections. P10/P50/P90 runway, survival rates at 12/18/24 months, sensitivity analysis up to 60 months.</p>

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
<tr><td style="padding:2px 0;">Stage-based activity &mdash; Founder early, Investors mid, Competitors late</td></tr>
<tr><td style="padding:2px 0;">Real-time SSE streaming with animated metric counters</td></tr>
<tr><td style="padding:2px 0;">Post-simulation AI report: outcome score, risks, recommendations</td></tr>
</table>
</td></tr>
</table>

<h3 style="font-size:15px;color:#1e1b4b;margin:18px 0 8px;">What-If Explorer</h3>
<p style="font-size:13px;color:#4b5563;margin:0 0 6px;">Interactive sliders for 5 key variables with instant real-time impact on runway, survival, and cash projections.</p>

<h3 style="font-size:15px;color:#1e1b4b;margin:18px 0 8px;">Stress Testing &amp; Counter-Moves</h3>
<p style="font-size:13px;color:#4b5563;margin:0 0 6px;">Multi-variable stress tests up to 60 months. Automatic counter-move simulations with delta-based scoring. Scenario versioning, comparison, and sharing.</p>

<h3 style="font-size:15px;color:#1e1b4b;margin:18px 0 8px;">Simulation Accuracy Tracker</h3>
<p style="font-size:13px;color:#4b5563;margin:0 0 6px;">Compares past predictions against actuals. Auto-calibration improves future projections.</p>

<!-- DECISIONS & AI -->
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:28px 0 16px;">
<tr><td style="padding:10px 16px;background:#0f172a;border-radius:6px;">
<p style="margin:0;font-size:13px;font-weight:700;color:#f59e0b;text-transform:uppercase;letter-spacing:2px;">Decisions &amp; AI</p>
</td></tr>
</table>

<h3 style="font-size:15px;color:#1e1b4b;margin:18px 0 8px;">Decision Scoring Engine</h3>
<p style="font-size:13px;color:#4b5563;margin:0 0 6px;">Survival-weighted composite: 35% survival + 25% downside + 20% growth + 10% optionality + 10% reversibility. Ranked recommendations with outcome tracking.</p>

<h3 style="font-size:15px;color:#1e1b4b;margin:18px 0 8px;">Decision Outcome Tracking <span style="display:inline-block;padding:2px 8px;background:#dcfce7;color:#15803d;font-size:10px;font-weight:700;border-radius:10px;vertical-align:middle;">NEW</span></h3>
<p style="font-size:13px;color:#4b5563;margin:0 0 6px;">Track actual outcomes against predictions. Measure decision quality over time and learn from past choices.</p>

<h3 style="font-size:15px;color:#1e1b4b;margin:18px 0 8px;">AI Copilot</h3>
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:6px 0;">
<tr><td style="padding:10px 14px;background:#f0fdf4;border-left:3px solid #16a34a;border-radius:0 6px 6px 0;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:12px;color:#4b5563;">
<tr><td style="padding:2px 0;">Plain English questions &rarr; CFO-grade analysis</td></tr>
<tr><td style="padding:2px 0;">Multi-LLM routing: OpenAI, Anthropic, Gemini, Perplexity, Grok</td></tr>
<tr><td style="padding:2px 0;">AI Learning Loop &mdash; user feedback improves future responses</td></tr>
<tr><td style="padding:2px 0;">Context-aware follow-ups from randomized topic pools</td></tr>
</table>
</td></tr>
</table>

<h3 style="font-size:15px;color:#1e1b4b;margin:18px 0 8px;">Founder Autopilot &amp; Alerts</h3>
<p style="font-size:13px;color:#4b5563;margin:0 0 6px;">Daily automated risk detection and briefings. Z-score anomaly detection, threshold monitoring, severity-based alert filtering.</p>

<!-- FUNDRAISING -->
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:28px 0 16px;">
<tr><td style="padding:10px 16px;background:#0f172a;border-radius:6px;">
<p style="margin:0;font-size:13px;font-weight:700;color:#ec4899;text-transform:uppercase;letter-spacing:2px;">Fundraising</p>
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

<h3 style="font-size:15px;color:#1e1b4b;margin:18px 0 8px;">Investor Database <span style="display:inline-block;padding:2px 8px;background:#dcfce7;color:#15803d;font-size:10px;font-weight:700;border-radius:10px;vertical-align:middle;">NEW</span></h3>
<p style="font-size:13px;color:#4b5563;margin:0 0 6px;">854 investors with firm, stage, sector, and geography data. Search, filter, and add to your pipeline directly.</p>

<h3 style="font-size:15px;color:#1e1b4b;margin:18px 0 8px;">Outreach Sequences <span style="display:inline-block;padding:2px 8px;background:#dcfce7;color:#15803d;font-size:10px;font-weight:700;border-radius:10px;vertical-align:middle;">NEW</span></h3>
<p style="font-size:13px;color:#4b5563;margin:0 0 6px;">Manage investor outreach campaigns with sequenced follow-ups and tracking.</p>

<h3 style="font-size:15px;color:#1e1b4b;margin:18px 0 8px;">Fundraising CRM <span style="display:inline-block;padding:2px 8px;background:#dcfce7;color:#15803d;font-size:10px;font-weight:700;border-radius:10px;vertical-align:middle;">NEW</span></h3>
<p style="font-size:13px;color:#4b5563;margin:0 0 6px;">Dashboard banner with pipeline overview, investor status tracking, and deal management.</p>

<!-- PLATFORM TOOLS -->
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:28px 0 16px;">
<tr><td style="padding:10px 16px;background:#0f172a;border-radius:6px;">
<p style="margin:0;font-size:13px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:2px;">Platform Tools</p>
</td></tr>
</table>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:6px 0;">
<tr><td style="padding:10px 14px;background:#f8fafc;border-left:3px solid #64748b;border-radius:0 6px 6px 0;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:12px;color:#4b5563;">
<tr><td style="padding:2px 0;"><strong>Cross-Company Learning</strong> &mdash; privacy-first benchmarking with anonymized data</td></tr>
<tr><td style="padding:2px 0;"><strong>Document Generator</strong> &mdash; financial models, investor memos, KPI reports, pitch outlines</td></tr>
<tr><td style="padding:2px 0;"><strong>AI Graphics Studio</strong> &mdash; professional graphics via OpenAI gpt-image-1</td></tr>
<tr><td style="padding:2px 0;"><strong>Hiring Planner</strong> &mdash; role/department/location with salary + runway impact</td></tr>
<tr><td style="padding:2px 0;"><strong>Simulation Accuracy Tracker</strong> &mdash; predictions vs actuals, auto-calibration</td></tr>
<tr><td style="padding:2px 0;"><strong>Activity Email Triggers</strong> &mdash; auto-reports on simulation, document, decision events</td></tr>
<tr><td style="padding:2px 0;"><strong>Feature Flags</strong> &mdash; runtime toggles with global/company/user overrides</td></tr>
<tr><td style="padding:2px 0;"><strong>AI Governance</strong> &mdash; agent permissions, daily limits, human approval flags</td></tr>
<tr><td style="padding:2px 0;"><strong>Intelligence Graph</strong> &mdash; related metrics and strategy pattern discovery</td></tr>
<tr><td style="padding:2px 0;"><strong>SEO Optimization</strong> &mdash; meta tags, Open Graph, structured data across all pages</td></tr>
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

<p style="font-size:14px;color:#4b5563;text-align:center;">Shipping new features every week. More updates coming soon.</p>

<p style="margin-top:30px;padding-top:15px;border-top:1px solid #e5e5e5;font-size:13px;color:#888;">
Arjun<br>FounderConsole
</p>

</div>
<img src="{open_tracking_url}" width="1" height="1" style="display:none" alt="" />
</body>
</html>"""


def send_all():
    sender = "Arjun from FounderConsole <arjun@runora.xyz>"

    print(f"Sending update v34 to {len(RECIPIENTS)} recipients...")
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
            subject="FounderConsole — 125 Active Users & Full Feature Update",
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
