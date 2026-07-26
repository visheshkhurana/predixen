"""
Send update email v32 - Comprehensive Platform Update with Active User Data.
Sender: Arjun from FounderConsole <arjun@founderconsole.ai>
"""
import os, sys, time, uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from server.email.service import _send_email_sync

CAMPAIGN = "founderconsole_update_mar2026_v32"

BASE_URL = "https://fund-flow.replit.app"

RECIPIENTS = [
    {"email": "nikita.luther@gmail.com", "id": "nikita_luther", "name": "Nikita"},
    {"email": "nikita@predixen.ai", "id": "nikita_predixen", "name": "Nikita"},
    {"email": "nikitafl2024@gmail.com", "id": "nikita_fl2024", "name": "Nikita"},
    {"email": "vysheshk@gmail.com", "id": "vyshesh_k", "name": "Vyshesh"},
]


def build_plain_text(rcpt: dict) -> str:
    return f"""Hi {rcpt['name']},

Here's a comprehensive update on everything we've shipped on FounderConsole recently, along with current platform activity.

===========================================
  PLATFORM ACTIVITY (as of March 26, 2026)
===========================================

  Total Users:            75
  Real Users (non-test):  21
  New Signups (30 days):  10
  Total Companies:        9
  Total Shareholders:     54

  Simulations Run:        39  (all in last 30 days)
  Copilot Conversations:  27  (9 in last 7 days)
  Scenarios Created:      63
  Decisions Tracked:      82
  Truth Scans Completed:  9

======================
  FEATURES SHIPPED
======================

1. FLIGHT SIMULATOR — MULTI-AGENT AI ENGINE (v30)

Completely rebuilt simulation engine with 7 LLM-powered AI agents (Founder, 2 Investors, Customer, Team, Market, Competitor). Each agent has:
- Short-term + long-term memory
- Stage-based activity levels (Founder early, Investors mid, Competitors late)
- Chain-of-thought reasoning via OpenAI gpt-5.6-luna
- Anti-repetition logic for varied strategies
- Real-time SSE streaming with animated metrics
- Post-simulation AI report with outcome score, risk factors, and recommendations
- Glassmorphism UI with animated orbs, shimmer loading, and staggered animations

2. NATURAL LANGUAGE SCENARIO ENGINE (v31)

Type scenarios in plain English and the engine parses them:
- "COD returns spike from 15% to 35%" — delta-based parsing (20pp impact)
- "Competitor launches similar product" — pessimistic effects
- "Shipping costs increase 25%" — opex/margin impact
- "Lose 20% customers" — churn + growth reduction
- "Cut burn 30%" — optimistic score (8-9)
- Handles plurals, prepositions, and industry abbreviations (65+ terms)

3. DELTA-BASED SCORE CALIBRATION (v31)

Scenario risk scores use composite formula:
- 40% survival + 40% runway change vs baseline + 20% P10 downside penalty
- Hard caps: survival <50% caps score at 4.5/10, <70% caps at 6.5/10
- Counter-move cards compare against clean baseline for accurate positive deltas

4. WHAT-IF EXPLORER (v31)

Interactive sliders for Revenue Growth, Churn Rate, Gross Margin, Burn Rate, and Fundraising with instant real-time impact calculations. Fixed floating-point display issues.

5. DIGITAL TWIN (v31)

Virtual representation of the company that picks the most accurate data source when CompanyState and TruthScan disagree by >5x. Health scoring and risk indicators.

6. AI COPILOT IMPROVEMENTS (v31)

- Context-aware follow-up suggestions from randomized pools (5-7 per topic)
- 10 topic categories with company-specific metric values
- NLP term recognition for 65+ financial abbreviations
- Consolidated data gap warnings instead of repetitive alerts

7. BRAND REFRESH (v31)

New teal/emerald gradient logo with bar chart icon mark. Consistent across sidebar, marketing pages, auth screens, admin console, and favicon.

8. ACTIVITY EMAIL TRIGGERS (v30)

Automatic email reports when simulations complete, documents are generated, or decision recommendations are created.

9. AI LEARNING LOOP (v30)

Closed-loop feedback system — users rate Copilot responses, feedback aggregated and injected into future prompts.

10. SIMULATION ACCURACY TRACKER (v30)

Compares past Monte Carlo predictions against actuals, computes accuracy scores, auto-calibration system.

11. FUNDRAISING OS

Cap table management with 54 shareholders, dilution calculations, Investor Room with data room, fundraising readiness scoring with radar chart, AI-generated investment one-pager.

12. 38 DATA CONNECTORS

QuickBooks, Stripe, Gusto, Shopify, WooCommerce, Xero, Salesforce, HubSpot, and 30 more. Ecommerce connectors include COD/prepaid split, shipping costs, refund rates, and AOV.

======================
  BUG FIXES (v31)
======================

- Flight Simulator regression: async timeout + executor fix for agent persona generation
- NLP parsing: plural handling ("returns", "rates"), competitor vs market priority
- What-If Explorer: floating-point rounding on slider values
- Digital Twin: ratio-based fallback to TruthScan/FinancialRecord for stale data
- Counter-move baseline: email share uses clean baseline for accurate deltas
- Copilot follow-ups: no more repetitive suggestions

---

All changes are live at {BASE_URL}

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

<p>Here&rsquo;s a comprehensive update on everything we&rsquo;ve shipped on FounderConsole recently, along with current platform activity.</p>

<!-- Platform Stats -->
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:20px 0;border-radius:10px;overflow:hidden;">
<tr>
<td style="padding:20px 24px;background:linear-gradient(135deg,#0f172a 0%,#1e293b 100%);">
<p style="margin:0 0 16px;font-size:14px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:2px;">Platform Activity &mdash; March 26, 2026</p>
<table cellpadding="0" cellspacing="0" border="0" width="100%">
<tr>
<td width="33%" style="padding:8px 0;text-align:center;">
<p style="margin:0;font-size:28px;font-weight:800;color:#10b981;">75</p>
<p style="margin:2px 0 0;font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;">Total Users</p>
</td>
<td width="33%" style="padding:8px 0;text-align:center;">
<p style="margin:0;font-size:28px;font-weight:800;color:#0ea5e9;">9</p>
<p style="margin:2px 0 0;font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;">Companies</p>
</td>
<td width="33%" style="padding:8px 0;text-align:center;">
<p style="margin:0;font-size:28px;font-weight:800;color:#8b5cf6;">39</p>
<p style="margin:2px 0 0;font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;">Simulations</p>
</td>
</tr>
<tr>
<td width="33%" style="padding:8px 0;text-align:center;">
<p style="margin:0;font-size:28px;font-weight:800;color:#f59e0b;">27</p>
<p style="margin:2px 0 0;font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;">Copilot Chats</p>
</td>
<td width="33%" style="padding:8px 0;text-align:center;">
<p style="margin:0;font-size:28px;font-weight:800;color:#ec4899;">63</p>
<p style="margin:2px 0 0;font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;">Scenarios</p>
</td>
<td width="33%" style="padding:8px 0;text-align:center;">
<p style="margin:0;font-size:28px;font-weight:800;color:#14b8a6;">82</p>
<p style="margin:2px 0 0;font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;">Decisions</p>
</td>
</tr>
</table>
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-top:14px;border-top:1px solid #334155;padding-top:12px;">
<tr>
<td style="font-size:12px;color:#64748b;">New signups (30d): <strong style="color:#10b981;">10</strong></td>
<td style="font-size:12px;color:#64748b;text-align:center;">Truth Scans: <strong style="color:#0ea5e9;">9</strong></td>
<td style="font-size:12px;color:#64748b;text-align:right;">Shareholders: <strong style="color:#8b5cf6;">54</strong></td>
</tr>
</table>
</td>
</tr>
</table>

<!-- Features Section -->
<h2 style="font-size:18px;color:#0f172a;margin:32px 0 16px;text-transform:uppercase;letter-spacing:1px;">Features Shipped</h2>

<!-- 1. Flight Simulator -->
<h3 style="font-size:16px;color:#1e1b4b;margin:24px 0 10px;padding-bottom:5px;border-bottom:2px solid #6366f1;">1. Flight Simulator &mdash; Multi-Agent AI Engine</h3>

<p style="font-size:13px;color:#4b5563;margin:0 0 10px;">7 LLM-powered AI agents (Founder, 2 Investors, Customer, Team, Market, Competitor) with unique personas, memory, and stage-based activity.</p>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:8px 0;">
<tr>
<td style="padding:12px 14px;background:#eef2ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:12px;color:#4b5563;">
<tr><td style="padding:2px 0;">Per-agent short-term + long-term memory with chain-of-thought reasoning</td></tr>
<tr><td style="padding:2px 0;">Real-time SSE streaming with animated metric counters</td></tr>
<tr><td style="padding:2px 0;">Post-simulation AI report: outcome score, risk factors, recommendations</td></tr>
<tr><td style="padding:2px 0;">Glassmorphism UI: frosted glass cards, animated orbs, shimmer loading</td></tr>
<tr><td style="padding:2px 0;">Engine guardrails: growth cap 50%/mo, MRR cap $100M, customers cap 1M</td></tr>
</table>
</td>
</tr>
</table>

<!-- 2. NLP Scenario Engine -->
<h3 style="font-size:16px;color:#1e1b4b;margin:24px 0 10px;padding-bottom:5px;border-bottom:2px solid #10b981;">2. Natural Language Scenario Engine</h3>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:8px 0;">
<tr>
<td style="padding:12px 14px;background:#ecfdf5;border-left:3px solid #10b981;border-radius:0 6px 6px 0;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:12px;color:#4b5563;">
<tr><td style="padding:2px 0;">&ldquo;COD returns spike from 15% to 35%&rdquo; &rarr; 20pp delta parsing</td></tr>
<tr><td style="padding:2px 0;">&ldquo;Competitor launches product&rdquo; &rarr; pessimistic (churn + growth drop)</td></tr>
<tr><td style="padding:2px 0;">&ldquo;Shipping costs increase 25%&rdquo; &rarr; opex/margin impact</td></tr>
<tr><td style="padding:2px 0;">&ldquo;Lose 20% customers&rdquo; / &ldquo;Cut burn 30%&rdquo; &rarr; calibrated scores</td></tr>
<tr><td style="padding:2px 0;">65+ industry abbreviations: ARR, MRR, CAC, LTV, AOV, COD, NRR&hellip;</td></tr>
</table>
</td>
</tr>
</table>

<!-- 3. Score Calibration -->
<h3 style="font-size:16px;color:#1e1b4b;margin:24px 0 10px;padding-bottom:5px;border-bottom:2px solid #8b5cf6;">3. Delta-Based Score Calibration</h3>

<p style="font-size:13px;color:#4b5563;margin:0 0 6px;">Composite formula: 40% survival + 40% runway change vs baseline + 20% P10 downside. Hard caps on low-survival scenarios. Counter-moves compare against clean baseline.</p>

<!-- 4. What-If Explorer -->
<h3 style="font-size:16px;color:#1e1b4b;margin:24px 0 10px;padding-bottom:5px;border-bottom:2px solid #0ea5e9;">4. What-If Explorer</h3>

<p style="font-size:13px;color:#4b5563;margin:0 0 6px;">Interactive sliders for Revenue Growth, Churn, Gross Margin, Burn Rate, and Fundraising with instant real-time impact calculations on runway, survival, and cash at 18 months.</p>

<!-- 5. Digital Twin -->
<h3 style="font-size:16px;color:#1e1b4b;margin:24px 0 10px;padding-bottom:5px;border-bottom:2px solid #f59e0b;">5. Digital Twin</h3>

<p style="font-size:13px;color:#4b5563;margin:0 0 6px;">Continuously updated virtual company representation with health scoring, risk indicators, and intelligent data source selection when multiple sources disagree.</p>

<!-- 6. AI Copilot -->
<h3 style="font-size:16px;color:#1e1b4b;margin:24px 0 10px;padding-bottom:5px;border-bottom:2px solid #16a34a;">6. AI Copilot</h3>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:8px 0;">
<tr>
<td style="padding:12px 14px;background:#f0fdf4;border-left:3px solid #16a34a;border-radius:0 6px 6px 0;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:12px;color:#4b5563;">
<tr><td style="padding:2px 0;">Context-aware follow-ups from randomized topic pools</td></tr>
<tr><td style="padding:2px 0;">Multi-LLM routing (OpenAI, Anthropic, Gemini, Perplexity, Grok)</td></tr>
<tr><td style="padding:2px 0;">AI Learning Loop: user feedback improves future responses</td></tr>
<tr><td style="padding:2px 0;">Consolidated data gap warnings</td></tr>
</table>
</td>
</tr>
</table>

<!-- 7. Fundraising OS -->
<h3 style="font-size:16px;color:#1e1b4b;margin:24px 0 10px;padding-bottom:5px;border-bottom:2px solid #ec4899;">7. Fundraising OS</h3>

<p style="font-size:13px;color:#4b5563;margin:0 0 6px;">Cap table (54 shareholders), dilution modeling, Investor Room with data room, fundraising readiness radar chart, AI investment one-pager, exit waterfall analysis.</p>

<!-- 8. Data Connectors -->
<h3 style="font-size:16px;color:#1e1b4b;margin:24px 0 10px;padding-bottom:5px;border-bottom:2px solid #f97316;">8. 38 Data Connectors</h3>

<p style="font-size:13px;color:#4b5563;margin:0 0 6px;">QuickBooks, Stripe, Gusto, Shopify, WooCommerce, Xero, Salesforce, HubSpot, Plaid, Mercury, Brex, Ramp, and 26 more. Ecommerce connectors include COD/prepaid split, shipping costs, refund rates, and AOV.</p>

<!-- 9. Other Features -->
<h3 style="font-size:16px;color:#1e1b4b;margin:24px 0 10px;padding-bottom:5px;border-bottom:2px solid #64748b;">9. Additional Features</h3>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:8px 0;">
<tr>
<td style="padding:12px 14px;background:#f8fafc;border-left:3px solid #64748b;border-radius:0 6px 6px 0;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:12px;color:#4b5563;">
<tr><td style="padding:2px 0;">Activity Email Triggers &mdash; auto-send on simulation, document, or decision events</td></tr>
<tr><td style="padding:2px 0;">Simulation Accuracy Tracker &mdash; compare predictions vs actuals</td></tr>
<tr><td style="padding:2px 0;">Board Deck Export &mdash; AI-generated PDF/HTML presentations</td></tr>
<tr><td style="padding:2px 0;">Hiring Planner &mdash; role/department/location with salary and runway impact</td></tr>
<tr><td style="padding:2px 0;">Founder Autopilot &mdash; daily risk detection and briefing generation</td></tr>
<tr><td style="padding:2px 0;">Feature Flags &mdash; runtime toggles with global/company/user overrides</td></tr>
<tr><td style="padding:2px 0;">Brand Refresh &mdash; new teal/emerald logo, matching favicon</td></tr>
</table>
</td>
</tr>
</table>

<!-- Bug Fixes -->
<h2 style="font-size:18px;color:#0f172a;margin:32px 0 16px;text-transform:uppercase;letter-spacing:1px;">Bug Fixes (Latest)</h2>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:8px 0;">
<tr>
<td style="padding:12px 14px;background:#fef2f2;border-left:3px solid #ef4444;border-radius:0 6px 6px 0;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:12px;color:#4b5563;">
<tr><td style="padding:2px 0;"><strong>Flight Simulator regression</strong> &mdash; async timeout + executor fix for agent persona generation</td></tr>
<tr><td style="padding:2px 0;"><strong>NLP parsing</strong> &mdash; plural handling, competitor vs market priority, from/to delta parsing</td></tr>
<tr><td style="padding:2px 0;"><strong>What-If Explorer</strong> &mdash; floating-point rounding on slider values</td></tr>
<tr><td style="padding:2px 0;"><strong>Digital Twin</strong> &mdash; ratio-based fallback for stale data detection</td></tr>
<tr><td style="padding:2px 0;"><strong>Counter-moves</strong> &mdash; baseline comparison for accurate positive deltas</td></tr>
<tr><td style="padding:2px 0;"><strong>Copilot follow-ups</strong> &mdash; randomized pools, no more repetitive suggestions</td></tr>
</table>
</td>
</tr>
</table>

<!-- CTA -->
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:28px 0;">
<tr>
<td style="text-align:center;">
<a href="{BASE_URL}" style="display:inline-block;padding:14px 32px;background:linear-gradient(135deg,#10b981 0%,#0d9488 100%);color:#ffffff;text-decoration:none;font-weight:700;font-size:15px;border-radius:8px;">Open FounderConsole</a>
</td>
</tr>
</table>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:20px 0 0;">
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

    print(f"Sending update v32 to {len(RECIPIENTS)} recipients...")
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
            subject="FounderConsole — Full Platform Update: 12 Features, 6 Bug Fixes & Live User Data",
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
