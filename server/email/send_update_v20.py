"""
Send update email v20 - QA v1.0.2+ Trust & Simulation Accuracy Fixes.
Sender: ivl58oxz@founderconsole.ai
"""
import os, sys, time, uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from server.email.service import _send_email_sync

CAMPAIGN = "founderconsole_qa_trust_fixes_feb2026_v20"

RECIPIENTS = [
    {"email": "nikita.luther@gmail.com", "id": "nikita_luther", "name": "Nikita"},
    {"email": "nikita@founderconsole.ai", "id": "nikita_founderconsole", "name": "Nikita"},
    {"email": "nikitafl2024@gmail.com", "id": "nikita_fl2024", "name": "Nikita"},
]


def build_plain_text(rcpt: dict) -> str:
    return f"""Hi {rcpt['name']},

We just shipped a round of QA fixes (v1.0.2+) based on real beta feedback from a pre-IPO logistics company. These changes address trust, accuracy, and reproducibility across the platform.

---

QA v1.0.2+ TRUST & SIMULATION ACCURACY FIXES

---

1. MULTI-CURRENCY & DENOMINATION SUPPORT

Every financial number now respects your company's configured currency and denomination scale. If you report in lakhs, crores, thousands, or millions, the platform stores values in base units and converts at display boundaries. No more hardcoded "$" signs - currency symbols adapt to your company settings across all 19+ components.

---

2. NO MORE FABRICATED DEFAULTS

Previously, simulations would silently fall back to hardcoded numbers (70% gross margin, 10% growth, $50K revenue, $500K cash, etc.) when your data was incomplete. These fabricated defaults are now completely removed. The simulator pulls exclusively from your actual financial records. If a metric is missing, it uses 0 rather than inventing a number.

---

3. INDUSTRY TEMPLATE PACKS

New API endpoint for bulk time-series upload with pre-built templates for logistics, SaaS, e-commerce, healthcare, and fintech. Each template includes industry-appropriate metrics, distributions, and benchmarks so you can get started with realistic parameters instead of generic defaults.

---

4. SIMPLE VS ADVANCED DATA INPUT

The data input page now has a toggle between Simple mode (key metrics at a glance) and Advanced mode (full multi-period time-series editor). The Advanced mode uses a new MetricTimeSeriesEditor component for entering monthly data across all tracked metrics.

---

5. REPRODUCIBLE MONTE CARLO SIMULATIONS

Simulations are now fully deterministic when you provide a seed. Each run creates its own random number generator instead of using a shared global state. This means:
- Same seed + same inputs = identical results every time
- Event impacts (cash, revenue, growth, margin, churn, headcount, costs) all use the per-run generator
- You can set iteration count (100-5000) and seed directly from the UI

---

6. CONSISTENT ITERATION DEFAULTS

Frontend and backend now agree on 500 iterations as the default. Previously the backend defaulted to 1000 while the frontend sent 500, causing confusion about which count was actually being used.

---

7. UNIFIED BASELINE COMPUTATION

The simulation engine now computes its baseline entirely from your FinancialRecord data. The extract_metric_value function pulls from actual fields (gross_margin, opex, payroll, other_costs, revenue, cash_balance, mom_growth) before falling back to 0. No synthetic data is ever injected.

---

These fixes ensure that every number you see in FounderConsole comes from your actual data, displayed in your currency, and is reproducible on demand.

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

<p>We just shipped a round of QA fixes (v1.0.2+) based on real beta feedback from a pre-IPO logistics company. These changes address trust, accuracy, and reproducibility across the platform.</p>

<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #6366f1;">QA v1.0.2+ &mdash; Trust &amp; Simulation Accuracy Fixes</h2>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:16px 0;">

<tr>
<td style="padding:14px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:15px;color:#4338ca;">Multi-Currency &amp; Denomination Support</p>
<p style="margin:0;font-size:13px;color:#4b5563;">Every financial number now respects your company&rsquo;s configured currency and denomination scale (lakhs, crores, thousands, millions). Values are stored in base units and converted at display boundaries. No more hardcoded &ldquo;$&rdquo; signs &mdash; currency symbols adapt across all 19+ components.</p>
</td>
</tr>
<tr><td style="height:10px;"></td></tr>

<tr>
<td style="padding:14px 16px;background:#fef2f2;border-left:3px solid #dc2626;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:15px;color:#b91c1c;">No More Fabricated Defaults</p>
<p style="margin:0;font-size:13px;color:#4b5563;">Removed all hardcoded fallback values from the simulation engine: 70% gross margin, 10% growth, $50K revenue, $500K cash, $20K opex, $30K payroll, $5K other costs. The simulator now pulls <strong>exclusively</strong> from your actual financial records. Missing metrics use 0, never invented numbers.</p>
</td>
</tr>
<tr><td style="height:10px;"></td></tr>

<tr>
<td style="padding:14px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:15px;color:#4338ca;">Industry Template Packs</p>
<p style="margin:0;font-size:13px;color:#4b5563;">New bulk time-series upload endpoint with pre-built templates for <strong>logistics, SaaS, e-commerce, healthcare, and fintech</strong>. Each template includes industry-appropriate metrics, distributions, and benchmarks so you start with realistic parameters instead of generic defaults.</p>
</td>
</tr>
<tr><td style="height:10px;"></td></tr>

<tr>
<td style="padding:14px 16px;background:#f0fdf4;border-left:3px solid #16a34a;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:15px;color:#15803d;">Simple vs Advanced Data Input</p>
<p style="margin:0;font-size:13px;color:#4b5563;">The data input page now has a toggle between Simple mode (key metrics at a glance) and Advanced mode (full multi-period time-series editor with the new MetricTimeSeriesEditor component for entering monthly data).</p>
</td>
</tr>
<tr><td style="height:10px;"></td></tr>

<tr>
<td style="padding:14px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:15px;color:#4338ca;">Reproducible Monte Carlo Simulations</p>
<p style="margin:0;font-size:13px;color:#4b5563;">Simulations are now fully deterministic with a seed. Each run creates its own random number generator instead of shared global state. Same seed + same inputs = identical results every time. All event impacts (cash, revenue, growth, margin, churn, headcount, costs) use the per-run generator. Set iteration count (100&ndash;5,000) and seed directly from the UI.</p>
</td>
</tr>
<tr><td style="height:10px;"></td></tr>

<tr>
<td style="padding:14px 16px;background:#f0fdf4;border-left:3px solid #16a34a;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:15px;color:#15803d;">Consistent Defaults &amp; Unified Baseline</p>
<p style="margin:0;font-size:13px;color:#4b5563;">Frontend and backend now agree on 500 iterations as the default. The simulation engine computes its baseline entirely from your FinancialRecord data &mdash; revenue, cash, gross margin, opex, payroll, growth rate &mdash; before falling back to 0. No synthetic data is ever injected.</p>
</td>
</tr>

</table>

<p style="font-size:14px;color:#4b5563;margin-top:20px;">These fixes ensure that every number you see in FounderConsole comes from your actual data, displayed in your currency, and is reproducible on demand.</p>

<p style="margin-top:30px;padding-top:15px;border-top:1px solid #e5e5e5;font-size:13px;color:#888;">
FounderConsole
</p>

</div>
</body>
</html>"""


def send_all():
    sender = "FounderConsole <ivl58oxz@founderconsole.ai>"

    print(f"Sending QA Trust & Simulation Accuracy update v20 to {len(RECIPIENTS)} recipients...")
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
            subject="FounderConsole QA v1.0.2+ - Trust & Simulation Accuracy Fixes: No More Fabricated Defaults",
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
