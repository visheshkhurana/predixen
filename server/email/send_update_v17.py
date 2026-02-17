"""
Send detailed simulation changes update email v17.
Sender: wlk2qbda@founderconsole.ai
"""
import os, sys, time, uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from server.email.service import _send_email_sync

CAMPAIGN = "founderconsole_simulation_deep_dive_feb2026_v17"

RECIPIENTS = [
    {"email": "nikita.luther@gmail.com", "id": "nikita_luther", "name": "Nikita"},
    {"email": "nikita@founderconsole.ai", "id": "nikita_founderconsole", "name": "Nikita"},
    {"email": "nikitafl2024@gmail.com", "id": "nikita_fl2024", "name": "Nikita"},
]


def build_plain_text(rcpt: dict) -> str:
    return f"""Hi {rcpt['name']},

Detailed breakdown of the simulation engine changes in FounderConsole:

---

RESULTS HIERARCHY - DECISION-INTELLIGENCE-FIRST ORDER

The entire simulation results page has been reorganized. Previously, key insights were buried under tabs or hidden behind an "Advanced View" toggle. Now everything renders inline in a fixed top-to-bottom order designed for fast decision-making:

1. AI Decision Summary (gradient-bordered card, always first)
   - 1-2 sentence consultant-grade recommendation
   - Decision Score from 1 to 10
   - GO / CONDITIONAL / NO-GO verdict badge
   - 3 bullet points: Key Risk, Key Opportunity, Watch Metric

2. Decision Recommendations
   - Data-driven action items ranked by impact

3. Before/After Delta Cards
   - Auto-detects your baseline scenario
   - Shows metric-by-metric comparison with directional arrows
   - Color-coded improvement vs regression

4. Sensitivity Levers + Breaking Points
   - Interactive sliders for each input variable
   - Drag to see real-time runway/survival impact
   - Breaking point markers show exactly where a metric flips from safe to critical

5. Tornado Chart + What-If Explorer
   - Tornado chart ranks variables by influence magnitude
   - What-If Explorer lets you override any single variable and re-simulate instantly

6. Sensitivity Analysis
   - Full matrix of variable interactions
   - Identifies which combinations amplify or dampen risk

7. Stress Tests
   - Pre-built stress scenarios (market crash, customer churn spike, funding delay)
   - Shows survival probability under each stress condition

8. Automatic Counter-Move Simulations
   - 3 counter-moves auto-generated for every scenario:
     * Cost Cut 20%
     * Raise Prices 10%
     * Freeze Hiring
   - Each shows runway delta and survival delta vs your current plan
   - One-click "Apply" creates a new derived scenario

9. P10 / P50 / P90 Monte Carlo Distributions
   - 1000-iteration Monte Carlo with full distribution curves
   - Payback Clock Widget showing P10-P90 range
   - Risk Alert Banner with warning and critical thresholds

10. Charts
    - Revenue, burn, runway, and cash balance projections over 24 months
    - Probability distribution histograms

11. Fundraising Intelligence
    - Dilution impact analysis
    - Optimal raise timing based on simulation outcomes
    - Investor-grade metrics summary

---

DUAL-PATH "OR" DETECTION

When you type a scenario like "hire 5 engineers or cut marketing 30%", the system now:
- Detects the two decision paths automatically
- Runs both Monte Carlo simulations in parallel
- Displays results side-by-side for direct comparison
- Handles partial failures gracefully (if one path fails, the other still shows)
- Shows a visual preview indicator below the search bar while running

---

FOUNDER MODE

A toggle that condenses the full results into a single executive summary card with just the Decision Score, verdict, and top 3 bullets. Expand to see the full detail stack when needed.

---

SCENARIO TOOLS TAB BAR

Below the inline results, a clearly labeled "Scenario Tools" section provides:
- Strategic Builder: guided scenario construction
- Classic Wizard: step-by-step parameter entry
- Detailed Results: raw data tables
- Compare All: multi-scenario comparison grid
- Enhanced: advanced visualization options
- History: version history with restore
- Discussion: team collaboration thread

These were previously the primary navigation but are now secondary to the inline intelligence.

---

All changes are live. The simulation page is designed so that the most actionable intelligence appears first, and deeper analysis tools are always accessible without switching views.

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

<p>Detailed breakdown of the simulation engine changes in FounderConsole:</p>

<!-- Section: Results Hierarchy -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #6366f1;">Results Hierarchy &mdash; Decision-Intelligence-First Order</h2>

<p style="font-size:14px;color:#4b5563;">The entire simulation results page has been reorganized. Previously, key insights were buried under tabs or hidden behind an &ldquo;Advanced View&rdquo; toggle. Now everything renders inline in a fixed top-to-bottom order designed for fast decision-making:</p>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:16px 0;">
<tr>
<td style="padding:12px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;margin-bottom:8px;">
<p style="margin:0 0 2px;font-weight:700;font-size:14px;color:#4338ca;">1. AI Decision Summary</p>
<p style="margin:0;font-size:13px;color:#4b5563;">Gradient-bordered card, always first. 1&ndash;2 sentence consultant-grade recommendation, Decision Score (1&ndash;10), GO / CONDITIONAL / NO-GO verdict, and 3 supporting bullets: Key Risk, Key Opportunity, Watch Metric.</p>
</td>
</tr>
<tr><td style="height:8px;"></td></tr>
<tr>
<td style="padding:12px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 2px;font-weight:700;font-size:14px;color:#4338ca;">2. Decision Recommendations</p>
<p style="margin:0;font-size:13px;color:#4b5563;">Data-driven action items ranked by impact on runway and survival.</p>
</td>
</tr>
<tr><td style="height:8px;"></td></tr>
<tr>
<td style="padding:12px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 2px;font-weight:700;font-size:14px;color:#4338ca;">3. Before/After Delta Cards</p>
<p style="margin:0;font-size:13px;color:#4b5563;">Auto-detects baseline scenario. Metric-by-metric comparison with directional arrows. Color-coded improvement vs regression.</p>
</td>
</tr>
<tr><td style="height:8px;"></td></tr>
<tr>
<td style="padding:12px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 2px;font-weight:700;font-size:14px;color:#4338ca;">4. Sensitivity Levers + Breaking Points</p>
<p style="margin:0;font-size:13px;color:#4b5563;">Interactive sliders for each input variable. Drag to see real-time runway/survival impact. Breaking point markers show exactly where a metric flips from safe to critical.</p>
</td>
</tr>
<tr><td style="height:8px;"></td></tr>
<tr>
<td style="padding:12px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 2px;font-weight:700;font-size:14px;color:#4338ca;">5. Tornado Chart + What-If Explorer</p>
<p style="margin:0;font-size:13px;color:#4b5563;">Tornado chart ranks variables by influence magnitude. What-If Explorer lets you override any single variable and re-simulate instantly.</p>
</td>
</tr>
<tr><td style="height:8px;"></td></tr>
<tr>
<td style="padding:12px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 2px;font-weight:700;font-size:14px;color:#4338ca;">6. Sensitivity Analysis</p>
<p style="margin:0;font-size:13px;color:#4b5563;">Full matrix of variable interactions. Identifies which combinations amplify or dampen risk.</p>
</td>
</tr>
<tr><td style="height:8px;"></td></tr>
<tr>
<td style="padding:12px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 2px;font-weight:700;font-size:14px;color:#4338ca;">7. Stress Tests</p>
<p style="margin:0;font-size:13px;color:#4b5563;">Pre-built stress scenarios (market crash, customer churn spike, funding delay). Shows survival probability under each stress condition.</p>
</td>
</tr>
<tr><td style="height:8px;"></td></tr>
<tr>
<td style="padding:12px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 2px;font-weight:700;font-size:14px;color:#4338ca;">8. Automatic Counter-Move Simulations</p>
<p style="margin:0;font-size:13px;color:#4b5563;">3 counter-moves auto-generated: Cost Cut 20%, Raise Prices 10%, Freeze Hiring. Each shows runway and survival deltas vs current plan. One-click &ldquo;Apply&rdquo; creates a derived scenario.</p>
</td>
</tr>
<tr><td style="height:8px;"></td></tr>
<tr>
<td style="padding:12px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 2px;font-weight:700;font-size:14px;color:#4338ca;">9. P10 / P50 / P90 Monte Carlo</p>
<p style="margin:0;font-size:13px;color:#4b5563;">1000-iteration Monte Carlo with full distribution curves. Payback Clock Widget with P10&ndash;P90 range. Risk Alert Banner with warning/critical thresholds.</p>
</td>
</tr>
<tr><td style="height:8px;"></td></tr>
<tr>
<td style="padding:12px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 2px;font-weight:700;font-size:14px;color:#4338ca;">10. Charts</p>
<p style="margin:0;font-size:13px;color:#4b5563;">Revenue, burn, runway, and cash balance projections over 24 months. Probability distribution histograms.</p>
</td>
</tr>
<tr><td style="height:8px;"></td></tr>
<tr>
<td style="padding:12px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 2px;font-weight:700;font-size:14px;color:#4338ca;">11. Fundraising Intelligence</p>
<p style="margin:0;font-size:13px;color:#4b5563;">Dilution impact analysis, optimal raise timing based on simulation outcomes, investor-grade metrics summary.</p>
</td>
</tr>
</table>

<!-- Section: Dual-Path -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #6366f1;">Dual-Path &ldquo;Or&rdquo; Detection</h2>
<p style="font-size:14px;color:#4b5563;">When you type a scenario like &ldquo;hire 5 engineers or cut marketing 30%&rdquo;, the system detects the two decision paths automatically, runs both Monte Carlo simulations in parallel, and displays results side-by-side for direct comparison. Handles partial failures gracefully and shows a visual preview indicator while running.</p>

<!-- Section: Founder Mode -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #6366f1;">Founder Mode</h2>
<p style="font-size:14px;color:#4b5563;">A toggle that condenses the full results into a single executive summary card with just the Decision Score, verdict, and top 3 bullets. Expand to see the full detail stack when needed.</p>

<!-- Section: Scenario Tools -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #6366f1;">Scenario Tools Tab Bar</h2>
<p style="font-size:14px;color:#4b5563;">Below the inline results, a clearly labeled &ldquo;Scenario Tools&rdquo; section provides: Strategic Builder, Classic Wizard, Detailed Results, Compare All, Enhanced, History, and Discussion. These were previously the primary navigation but are now secondary to the inline intelligence.</p>

<p style="margin-top:24px;">All changes are live. The simulation page is designed so the most actionable intelligence appears first, and deeper analysis tools are always accessible without switching views.</p>

<p style="margin-top:30px;padding-top:15px;border-top:1px solid #e5e5e5;font-size:13px;color:#888;">
FounderConsole
</p>

</div>
</body>
</html>"""


def send_all():
    sender = "FounderConsole <wlk2qbda@founderconsole.ai>"

    print(f"Sending simulation deep-dive update v17 to {len(RECIPIENTS)} recipients...")
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
            subject="FounderConsole Simulation Engine - Detailed Changes & New Intelligence Layer",
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
