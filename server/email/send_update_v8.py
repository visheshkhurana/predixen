"""
Send detailed simulation explainer email v8 to 4 recipients.
Transactional-style: minimal HTML, plain-text companion, personal sender.
Content: How FounderConsole Monte Carlo simulations work, with concrete examples.
"""
import os, sys, time, uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from server.email.service import _send_email_sync

CAMPAIGN = "founderconsole_simulation_explainer_feb2026_v8"
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

I wanted to walk through how the FounderConsole simulation engine actually works under the hood -- since it's the core of every projection, runway estimate, and decision recommendation on the platform.

HOW MONTE CARLO SIMULATIONS WORK
---------------------------------

Instead of giving you a single "best guess" projection, we run 1,000 independent simulations of your company's next 24 months. Each simulation samples from probability distributions around your inputs, so you get a full range of outcomes -- optimistic, pessimistic, and everything in between.

Here's the step-by-step:

1. YOUR INPUTS BECOME THE BASELINE

When you enter data on the Data Input page, those numbers set the starting point:
  - Monthly Revenue (MRR): e.g. $43,949
  - Cash on Hand: e.g. $513,746
  - Growth Rate: e.g. 10% month-over-month
  - Expense Breakdown: payroll, marketing, operating, COGS
  - Gross Margin: e.g. 65%

2. SCENARIO PARAMETERS ADJUST THE BASELINE

On the Scenarios page, you can dial in adjustments:
  - Growth Uplift: +5% means your 10% baseline becomes 15%
  - Churn Change: +2% adds 2 percentage points of monthly churn
  - Pricing Change: +10% boosts revenue per customer by 10%
  - Gross Margin Delta: -5% reduces your margin from 65% to 60%
  - Burn Reduction: 15% cuts operating costs by 15%

These are applied BEFORE the simulation loop starts, so every one of the 1,000 runs uses the adjusted values.

3. EACH MONTH IS SIMULATED WITH RANDOMNESS

For each of the 1,000 simulations, we step through 24 months. Each month:
  - Revenue grows by the adjusted growth rate, plus random noise (normal distribution with ~2% standard deviation)
  - Customer churn is applied as a percentage reduction
  - Expenses include payroll (grows with headcount), COGS (tied to revenue via gross margin), and operating costs
  - Cash = previous cash + revenue - all expenses

If cash hits zero in any simulation, that simulation records the month as the runway endpoint.

4. RESULTS ARE PERCENTILE RANGES, NOT SINGLE NUMBERS

After all 1,000 runs complete, we calculate:
  - P10 (pessimistic): Only 10% of simulations did worse than this
  - P50 (median): The middle outcome
  - P90 (optimistic): Only 10% of simulations did better than this
  - Survival probability: What % of simulations still had cash at month 6, 12, 18, 24

CONCRETE EXAMPLE
-----------------

Say you're the demo company (TechFlow Analytics):
  - MRR: $43,949 | Cash: $513,746 | Growth: 10% | Burn: ~$22K/mo

Baseline simulation (no scenario changes):
  - P50 Revenue at Month 24: ~$460K/mo
  - P50 Cash at Month 24: ~$2.1M
  - Survival Rate: 94.7% at 24 months
  - Runway: 21.3 months (P50)

Now apply a scenario: "What if growth drops to 5% and churn increases 3%?"
  - Set growth_uplift_pct = -5 (10% baseline - 5% = 5% effective)
  - Set churn_change_pct = +3

New results:
  - P50 Revenue at Month 24: ~$120K/mo (much lower trajectory)
  - P50 Cash at Month 24: ~$180K
  - Survival Rate: ~72% at 24 months
  - Runway: 14.2 months (P50)

The gap between P10 and P90 widens too -- more uncertainty in a stressed scenario.

RUNWAY EXTRAPOLATION
---------------------

If a company is still alive at month 24 (the simulation horizon), we extrapolate:
  - If net cash flow is positive (profitable), runway is capped at 48 months
  - If net cash flow is negative, we project: remaining_cash / monthly_burn to estimate how much further the company can go, up to 48 months max

WHAT THIS MEANS FOR DECISIONS
------------------------------

When you compare scenarios side by side, the Decision Ranking page scores each one on:
  - Survival probability (higher is better)
  - Expected cash position (P50)
  - Runway length
  - Revenue trajectory

This is how FounderConsole tells you "Scenario A is 23% better than Scenario B" -- it's comparing thousands of simulated futures, not a single spreadsheet row.

You can try all of this in the demo account:
{BASE_URL}/auth
Login: demo@founderconsole.ai / demo123

Go to Scenarios, create two scenarios with different parameters, run simulations on both, then check the Decision Ranking page.

Let me know if you have questions about any of this.

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

<p>I wanted to walk through how the FounderConsole simulation engine actually works under the hood &mdash; since it&rsquo;s the core of every projection, runway estimate, and decision recommendation on the platform.</p>

<h3 style="font-size:16px;color:#111;margin:28px 0 12px;">How Monte Carlo Simulations Work</h3>

<p>Instead of giving you a single &ldquo;best guess&rdquo; projection, we run <strong>1,000 independent simulations</strong> of your company&rsquo;s next 24 months. Each simulation samples from probability distributions around your inputs, so you get a full range of outcomes &mdash; optimistic, pessimistic, and everything in between.</p>

<h4 style="font-size:14px;color:#333;margin:22px 0 8px;">1. Your Inputs Become the Baseline</h4>

<p>When you enter data on the Data Input page, those numbers set the starting point:</p>
<ul style="padding-left:20px;color:#333;">
<li style="margin-bottom:4px;">Monthly Revenue (MRR): e.g. $43,949</li>
<li style="margin-bottom:4px;">Cash on Hand: e.g. $513,746</li>
<li style="margin-bottom:4px;">Growth Rate: e.g. 10% month-over-month</li>
<li style="margin-bottom:4px;">Expense Breakdown: payroll, marketing, operating, COGS</li>
<li style="margin-bottom:4px;">Gross Margin: e.g. 65%</li>
</ul>

<h4 style="font-size:14px;color:#333;margin:22px 0 8px;">2. Scenario Parameters Adjust the Baseline</h4>

<p>On the Scenarios page, you can dial in adjustments:</p>
<ul style="padding-left:20px;color:#333;">
<li style="margin-bottom:4px;"><strong>Growth Uplift:</strong> +5% means your 10% baseline becomes 15%</li>
<li style="margin-bottom:4px;"><strong>Churn Change:</strong> +2% adds 2 percentage points of monthly churn</li>
<li style="margin-bottom:4px;"><strong>Pricing Change:</strong> +10% boosts revenue per customer by 10%</li>
<li style="margin-bottom:4px;"><strong>Gross Margin Delta:</strong> -5% reduces your margin from 65% to 60%</li>
<li style="margin-bottom:4px;"><strong>Burn Reduction:</strong> 15% cuts operating costs by 15%</li>
</ul>

<p>These are applied <strong>before</strong> the simulation loop starts, so every one of the 1,000 runs uses the adjusted values.</p>

<h4 style="font-size:14px;color:#333;margin:22px 0 8px;">3. Each Month Is Simulated with Randomness</h4>

<p>For each of the 1,000 simulations, we step through 24 months. Each month:</p>
<ul style="padding-left:20px;color:#333;">
<li style="margin-bottom:4px;">Revenue grows by the adjusted growth rate, plus random noise (normal distribution, ~2% std dev)</li>
<li style="margin-bottom:4px;">Customer churn is applied as a percentage reduction</li>
<li style="margin-bottom:4px;">Expenses include payroll (grows with headcount), COGS (tied to revenue via gross margin), and operating costs</li>
<li style="margin-bottom:4px;">Cash = previous cash + revenue &minus; all expenses</li>
</ul>

<p>If cash hits zero in any simulation, that simulation records the month as the runway endpoint.</p>

<h4 style="font-size:14px;color:#333;margin:22px 0 8px;">4. Results Are Percentile Ranges</h4>

<p>After all 1,000 runs complete, we calculate:</p>
<ul style="padding-left:20px;color:#333;">
<li style="margin-bottom:4px;"><strong>P10</strong> (pessimistic): Only 10% of simulations did worse</li>
<li style="margin-bottom:4px;"><strong>P50</strong> (median): The middle outcome</li>
<li style="margin-bottom:4px;"><strong>P90</strong> (optimistic): Only 10% did better</li>
<li style="margin-bottom:4px;"><strong>Survival probability:</strong> % of simulations still solvent at month 6, 12, 18, 24</li>
</ul>

<h3 style="font-size:16px;color:#111;margin:28px 0 12px;">Concrete Example</h3>

<p>Take the demo company (TechFlow Analytics):<br>
MRR: $43,949 &nbsp;|&nbsp; Cash: $513,746 &nbsp;|&nbsp; Growth: 10% &nbsp;|&nbsp; Burn: ~$22K/mo</p>

<p><strong>Baseline simulation</strong> (no scenario changes):</p>
<ul style="padding-left:20px;color:#333;">
<li style="margin-bottom:4px;">P50 Revenue at Month 24: ~$460K/mo</li>
<li style="margin-bottom:4px;">P50 Cash at Month 24: ~$2.1M</li>
<li style="margin-bottom:4px;">Survival Rate: 94.7% at 24 months</li>
<li style="margin-bottom:4px;">Runway: 21.3 months (P50)</li>
</ul>

<p><strong>Stressed scenario</strong> (&ldquo;What if growth drops to 5% and churn increases 3%?&rdquo;):</p>
<ul style="padding-left:20px;color:#333;">
<li style="margin-bottom:4px;">Set growth_uplift_pct = -5 (10% baseline &minus; 5% = 5% effective)</li>
<li style="margin-bottom:4px;">Set churn_change_pct = +3</li>
</ul>

<p>New results:</p>
<ul style="padding-left:20px;color:#333;">
<li style="margin-bottom:4px;">P50 Revenue at Month 24: ~$120K/mo (much lower trajectory)</li>
<li style="margin-bottom:4px;">P50 Cash at Month 24: ~$180K</li>
<li style="margin-bottom:4px;">Survival Rate: ~72% at 24 months</li>
<li style="margin-bottom:4px;">Runway: 14.2 months (P50)</li>
</ul>

<p>The gap between P10 and P90 widens too &mdash; more uncertainty in a stressed scenario.</p>

<h3 style="font-size:16px;color:#111;margin:28px 0 12px;">Runway Extrapolation</h3>

<p>If a company is still alive at month 24 (the simulation horizon), we extrapolate:</p>
<ul style="padding-left:20px;color:#333;">
<li style="margin-bottom:4px;">If net cash flow is positive (profitable) &rarr; runway is capped at 48 months</li>
<li style="margin-bottom:4px;">If net cash flow is negative &rarr; remaining_cash / monthly_burn, up to 48 months max</li>
</ul>

<h3 style="font-size:16px;color:#111;margin:28px 0 12px;">What This Means for Decisions</h3>

<p>When you compare scenarios side by side, the Decision Ranking page scores each one on survival probability, expected cash position (P50), runway length, and revenue trajectory. This is how FounderConsole tells you &ldquo;Scenario A is 23% better than Scenario B&rdquo; &mdash; it&rsquo;s comparing thousands of simulated futures, not a single spreadsheet row.</p>

<p>You can try all of this in the demo account:<br>
<a href="{BASE_URL}/auth" style="color:#4f46e5;">{BASE_URL}/auth</a><br>
Login: demo@founderconsole.ai / demo123</p>

<p>Go to Scenarios, create two scenarios with different parameters, run simulations on both, then check the Decision Ranking page.</p>

<p>Let me know if you have questions about any of this.</p>

<p style="margin-top:30px;padding-top:15px;border-top:1px solid #e5e5e5;font-size:13px;color:#888;">
FounderConsole
</p>

</div>
</body>
</html>"""


def send_all():
    sender = "Nikita at FounderConsole <nikita@founderconsole.ai>"

    print(f"Sending simulation explainer emails to {len(RECIPIENTS)} recipients...")
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
            subject="How FounderConsole simulations work (with examples)",
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
