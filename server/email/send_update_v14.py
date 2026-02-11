"""
Send update email v14 to 4 recipients.
Transactional-style: minimal HTML, plain-text companion.
Content: Bug fixes and 6 new scenario intelligence features.
Sender: nfl9@predixen.app
"""
import os, sys, time, uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from server.email.service import _send_email_sync

CAMPAIGN = "predixen_scenario_intelligence_feb2026_v14"
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

Major update to the Predixen scenarios engine -- 6 new features and several bug fixes.

NEW FEATURES
--------------

1. DECISION SCORE CARD
Visual score card in the Strategic Assessment section showing:
- Risk (X/10) -- calculated from survival probability, runway, and P10-P90 spread
- Reward (X/10) -- calculated from revenue growth and runway gains vs baseline
- Capital Efficiency (X/10) -- calculated from breakeven timing and runway
- Survival Impact (+X%) -- delta vs baseline or absolute change
Each score has a colored progress bar (green/amber/red based on thresholds).

2. SIDE-BY-SIDE SCENARIO COMPARISON
"Compare Scenarios" button lets you pick 2-3 saved simulations and see them in columns side by side. Compare Baseline vs Scenario A vs Scenario B like poker hands -- runway, survival, revenue, cash, and key metrics all lined up for instant comparison.

3. SENSITIVITY SLIDERS
Interactive sliders below the scenario input for:
- Churn rate (0-10%)
- Burn reduction (0-50%)
- Price increase (0-30%)
Drag a slider and see real-time impact preview on survival and runway before running a full simulation. Helps you understand which levers matter most.

4. FUNDRAISE DILUTION MODEL
For fundraising scenarios, an ownership/dilution calculator shows:
- Pre-money and post-money valuation
- Founder ownership % and investor ownership %
- Dilution impact
- Runway extension from the raise
- Survival probability lift

5. FOUNDER MODE TOGGLE
Toggle at the top of the scenarios page. When enabled, collapses everything to 5 core metrics:
- Survival %
- Runway (months)
- ARR at 24 months
- Cash at month 18
- Risk Score
Click "Show Full Analysis" to expand the detailed sections when needed.

6. DOWNLOADABLE INVESTOR PDF
The Export button now offers "Download PDF Report" -- generates a professional A4 PDF with:
- Executive summary with P90/P50/P10 outcome bands
- Decision scores with colored progress bars
- Top sensitivity levers
- Counter-move analysis table
- Fundraising impact (if applicable)
- Survival probability curve
- Cash projection bands
- Confidential header and professional formatting
Ready to attach to board decks or investor updates.

BUG FIXES
-----------

- Fixed survival curve data normalization (handles 0-1 vs 0-100 range formats)
- Fixed counter-move simulation result parsing for edge cases
- Improved cash band chart rendering with missing data points
- Fixed scenario comparison layout on smaller screens

HOW TO TRY IT
---------------

1. Log in: {BASE_URL}/auth
   Demo: demo@predixen.ai / demo123

2. Go to Scenarios in the sidebar

3. Run a simulation on any scenario

4. You'll see the new Decision Score Card, Sensitivity Sliders, and Founder Mode toggle

5. Click "Compare Scenarios" to try side-by-side comparison

6. Click the Export button and select "Download PDF Report"

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

<p>Major update to the Predixen scenarios engine &mdash; <strong>6 new features</strong> and several bug fixes.</p>

<h3 style="font-size:16px;color:#111;margin:28px 0 12px;">New Features</h3>

<table style="width:100%;border-collapse:collapse;margin:16px 0;">
<tr>
<td style="vertical-align:top;padding:12px;border-bottom:1px solid #eee;">
<strong style="color:#111;">1. Decision Score Card</strong><br>
<span style="font-size:14px;color:#333;">Visual score card showing <strong>Risk</strong>, <strong>Reward</strong>, and <strong>Capital Efficiency</strong> (each X/10) plus <strong>Survival Impact</strong> (+X%). Calculated from simulation data with colored progress bars (green/amber/red).</span>
</td>
</tr>
<tr>
<td style="vertical-align:top;padding:12px;border-bottom:1px solid #eee;">
<strong style="color:#111;">2. Side-by-Side Scenario Comparison</strong><br>
<span style="font-size:14px;color:#333;">Compare 2-3 scenarios in columns. Pick Baseline vs Scenario A vs Scenario B and see runway, survival, revenue, and cash metrics lined up side by side.</span>
</td>
</tr>
<tr>
<td style="vertical-align:top;padding:12px;border-bottom:1px solid #eee;">
<strong style="color:#111;">3. Sensitivity Sliders</strong><br>
<span style="font-size:14px;color:#333;">Interactive sliders for churn (0-10%), burn reduction (0-50%), and price increase (0-30%). See real-time impact preview on survival and runway before running a full simulation.</span>
</td>
</tr>
<tr>
<td style="vertical-align:top;padding:12px;border-bottom:1px solid #eee;">
<strong style="color:#111;">4. Fundraise Dilution Model</strong><br>
<span style="font-size:14px;color:#333;">Ownership/dilution calculator showing pre-money &amp; post-money valuation, founder vs investor ownership %, dilution impact, runway extension, and survival lift.</span>
</td>
</tr>
<tr>
<td style="vertical-align:top;padding:12px;border-bottom:1px solid #eee;">
<strong style="color:#111;">5. Founder Mode Toggle</strong><br>
<span style="font-size:14px;color:#333;">Toggle at the top of Scenarios. Collapses everything to 5 core metrics: Survival %, Runway, ARR @24m, Cash @18m, Risk Score. Expand details when needed.</span>
</td>
</tr>
<tr>
<td style="vertical-align:top;padding:12px;border-bottom:1px solid #eee;">
<strong style="color:#111;">6. Downloadable Investor PDF</strong><br>
<span style="font-size:14px;color:#333;">Export button now generates a professional A4 PDF with executive summary, decision scores, sensitivity levers, counter-moves, fundraising impact, survival curve, and cash projections. Ready for board decks.</span>
</td>
</tr>
</table>

<h3 style="font-size:16px;color:#111;margin:28px 0 12px;">Bug Fixes</h3>

<ul style="padding-left:20px;color:#333;">
<li style="margin-bottom:4px;">Fixed survival curve data normalization (handles 0-1 vs 0-100 range formats)</li>
<li style="margin-bottom:4px;">Fixed counter-move simulation result parsing for edge cases</li>
<li style="margin-bottom:4px;">Improved cash band chart rendering with missing data points</li>
<li style="margin-bottom:4px;">Fixed scenario comparison layout on smaller screens</li>
</ul>

<h3 style="font-size:16px;color:#111;margin:28px 0 12px;">How to Try It</h3>

<ol style="padding-left:20px;color:#333;">
<li style="margin-bottom:6px;">Log in: <a href="{BASE_URL}/auth" style="color:#4f46e5;">{BASE_URL}/auth</a><br>Demo: demo@predixen.ai / demo123</li>
<li style="margin-bottom:6px;">Go to <strong>Scenarios</strong> in the sidebar</li>
<li style="margin-bottom:6px;">Run a simulation on any scenario</li>
<li style="margin-bottom:6px;">See the new Decision Score Card, Sensitivity Sliders, and Founder Mode toggle</li>
<li style="margin-bottom:6px;">Click <strong>&ldquo;Compare Scenarios&rdquo;</strong> to try side-by-side comparison</li>
<li style="margin-bottom:6px;">Click the <strong>Export</strong> button and select <strong>&ldquo;Download PDF Report&rdquo;</strong></li>
</ol>

<p>Let me know if you have questions.</p>

<p style="margin-top:30px;padding-top:15px;border-top:1px solid #e5e5e5;font-size:13px;color:#888;">
Predixen Intelligence OS
</p>

</div>
</body>
</html>"""


def send_all():
    sender = "Predixen <8w0s1b38@predixen.app>"

    print(f"Sending scenario intelligence update emails to {len(RECIPIENTS)} recipients...")
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
            subject="New: 6 scenario intelligence features + investor PDF export",
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
