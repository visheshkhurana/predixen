"""
Send scenario differentiation update email v9 to 4 recipients.
Transactional-style: minimal HTML, plain-text companion, new sender ID.
Content: Default scenarios now have differentiated parameters producing distinct simulation results.
"""
import os, sys, time, uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from server.email.service import _send_email_sync

CAMPAIGN = "predixen_scenario_update_feb2026_v9"
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

Quick update on something we just shipped -- the scenario comparison engine now produces genuinely different results for each scenario.

WHAT CHANGED
-------------

Previously, the five default scenarios (Baseline, Conservative, Moderate Growth, Aggressive Growth, Cost Cutting) all ran with the same underlying parameters. That meant the simulation outputs were nearly identical, which made scenario comparison pointless.

Now each scenario has distinct, meaningful financial inputs:

1. BASELINE
   No changes -- this is your reference trajectory.
   All parameters at 0%.

2. CONSERVATIVE CUT
   Goal: Extend runway by cutting costs, accepting slower growth.
   - Burn Reduction: 20% (aggressive cost cuts)
   - Growth Uplift: -5% (slower growth accepted)
   - Gross Margin Delta: +2%

3. MODERATE GROWTH
   Goal: Balanced improvement through pricing and growth levers.
   - Growth Uplift: +10%
   - Pricing Change: +10%
   - No burn reduction (maintain current spending)

4. AGGRESSIVE GROWTH
   Goal: Invest heavily to maximize growth, at the cost of higher burn.
   - Growth Uplift: +25%
   - Pricing Change: +20%
   - Burn Reduction: -15% (spending MORE, not less)
   - Gross Margin Delta: -5%

5. COST CUTTING
   Goal: Maximum expense reduction, slight price concessions to retain customers.
   - Burn Reduction: 30%
   - Pricing Change: -5%
   - Growth Uplift: -5%
   - Gross Margin Delta: +5%

WHY THIS MATTERS
-----------------

When you run simulations across these five scenarios, you now get meaningfully different P10/P50/P90 ranges for revenue, cash, runway, and survival probability. The Decision Ranking page can actually rank them because the outcomes diverge.

For example, with the demo account (TechFlow Analytics):
  - Baseline might show 21.3 months runway at P50
  - Conservative Cut extends that to ~26 months (lower burn)
  - Aggressive Growth could shorten it to ~16 months (higher spending) but with 2-3x the revenue trajectory

These tradeoffs are now visible and quantifiable.

TRY IT
-------

Log in to the demo account:
{BASE_URL}/auth
Login: demo@predixen.ai / demo123

Go to Scenarios, run all five, and compare the results on the Decision Ranking page. You'll see real differences now.

Let me know what you think.

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

<p>Quick update on something we just shipped &mdash; the scenario comparison engine now produces genuinely different results for each scenario.</p>

<h3 style="font-size:16px;color:#111;margin:28px 0 12px;">What Changed</h3>

<p>Previously, the five default scenarios (Baseline, Conservative, Moderate Growth, Aggressive Growth, Cost Cutting) all ran with the same underlying parameters. That meant the simulation outputs were nearly identical, which made scenario comparison pointless.</p>

<p>Now each scenario has distinct, meaningful financial inputs:</p>

<h4 style="font-size:14px;color:#333;margin:22px 0 8px;">1. Baseline</h4>
<p>No changes &mdash; this is your reference trajectory. All parameters at 0%.</p>

<h4 style="font-size:14px;color:#333;margin:22px 0 8px;">2. Conservative Cut</h4>
<p>Goal: Extend runway by cutting costs, accepting slower growth.</p>
<ul style="padding-left:20px;color:#333;">
<li style="margin-bottom:4px;"><strong>Burn Reduction:</strong> 20% (aggressive cost cuts)</li>
<li style="margin-bottom:4px;"><strong>Growth Uplift:</strong> -5% (slower growth accepted)</li>
<li style="margin-bottom:4px;"><strong>Gross Margin Delta:</strong> +2%</li>
</ul>

<h4 style="font-size:14px;color:#333;margin:22px 0 8px;">3. Moderate Growth</h4>
<p>Goal: Balanced improvement through pricing and growth levers.</p>
<ul style="padding-left:20px;color:#333;">
<li style="margin-bottom:4px;"><strong>Growth Uplift:</strong> +10%</li>
<li style="margin-bottom:4px;"><strong>Pricing Change:</strong> +10%</li>
<li style="margin-bottom:4px;">No burn reduction (maintain current spending)</li>
</ul>

<h4 style="font-size:14px;color:#333;margin:22px 0 8px;">4. Aggressive Growth</h4>
<p>Goal: Invest heavily to maximize growth, at the cost of higher burn.</p>
<ul style="padding-left:20px;color:#333;">
<li style="margin-bottom:4px;"><strong>Growth Uplift:</strong> +25%</li>
<li style="margin-bottom:4px;"><strong>Pricing Change:</strong> +20%</li>
<li style="margin-bottom:4px;"><strong>Burn Reduction:</strong> -15% (spending MORE)</li>
<li style="margin-bottom:4px;"><strong>Gross Margin Delta:</strong> -5%</li>
</ul>

<h4 style="font-size:14px;color:#333;margin:22px 0 8px;">5. Cost Cutting</h4>
<p>Goal: Maximum expense reduction, slight price concessions to retain customers.</p>
<ul style="padding-left:20px;color:#333;">
<li style="margin-bottom:4px;"><strong>Burn Reduction:</strong> 30%</li>
<li style="margin-bottom:4px;"><strong>Pricing Change:</strong> -5%</li>
<li style="margin-bottom:4px;"><strong>Growth Uplift:</strong> -5%</li>
<li style="margin-bottom:4px;"><strong>Gross Margin Delta:</strong> +5%</li>
</ul>

<h3 style="font-size:16px;color:#111;margin:28px 0 12px;">Why This Matters</h3>

<p>When you run simulations across these five scenarios, you now get meaningfully different P10/P50/P90 ranges for revenue, cash, runway, and survival probability. The Decision Ranking page can actually rank them because the outcomes diverge.</p>

<p>For example, with the demo account (TechFlow Analytics):</p>
<ul style="padding-left:20px;color:#333;">
<li style="margin-bottom:4px;">Baseline might show 21.3 months runway at P50</li>
<li style="margin-bottom:4px;">Conservative Cut extends that to ~26 months (lower burn)</li>
<li style="margin-bottom:4px;">Aggressive Growth could shorten it to ~16 months (higher spending) but with 2&ndash;3x the revenue trajectory</li>
</ul>

<p>These tradeoffs are now visible and quantifiable.</p>

<h3 style="font-size:16px;color:#111;margin:28px 0 12px;">Try It</h3>

<p>Log in to the demo account:<br>
<a href="{BASE_URL}/auth" style="color:#4f46e5;">{BASE_URL}/auth</a><br>
Login: demo@predixen.ai / demo123</p>

<p>Go to Scenarios, run all five, and compare the results on the Decision Ranking page. You&rsquo;ll see real differences now.</p>

<p>Let me know what you think.</p>

<p style="margin-top:30px;padding-top:15px;border-top:1px solid #e5e5e5;font-size:13px;color:#888;">
Predixen Intelligence OS
</p>

</div>
</body>
</html>"""


def send_all():
    sender = "Predixen Product <product@predixen.app>"

    print(f"Sending scenario update emails to {len(RECIPIENTS)} recipients...")
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
            subject="Scenario simulations now produce different results",
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
