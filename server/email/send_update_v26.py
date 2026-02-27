"""
Send update email v26 - 48-Hour Task Summary: Bug Fixes, Calibration & Stability.
Sender: noreply@founderconsole.ai
"""
import os, sys, time, uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from server.email.service import _send_email_sync

CAMPAIGN = "founderconsole_48hr_update_feb2026_v26"

RECIPIENTS = [
    {"email": "nikita.luther@gmail.com", "id": "nikita_luther", "name": "Nikita"},
    {"email": "nikita@founderconsole.ai", "id": "nikita_founderconsole", "name": "Nikita"},
    {"email": "nikitafl2024@gmail.com", "id": "nikita_fl2024", "name": "Nikita"},
]


def build_plain_text(rcpt: dict) -> str:
    return f"""Hi {rcpt['name']},

Here's a summary of everything completed on FounderConsole in the last 48 hours.

---

1. SIMULATION CALIBRATION FIX (P0)

Problem: "Hire 5 engineers" was getting an 8/10 GO verdict despite a 96% burn increase. The AI Decision Summary was dangerously optimistic for high-burn scenarios.

Fixes Applied:
- Verdict downgrade: GO now automatically downgrades to CONDITIONAL GO when burn increases 50%+ vs baseline. A near-doubling of burn rate can never receive a clean GO.
- Stronger score penalties: Score deduction increased from -1.5 to -2.5 (50%+ burn) and -3.5 (75%+ burn). A scenario that scored 8/10 now correctly scores around 4-5/10.
- Key Risk prioritization: When burn increases 50%+, the Key Risk bullet now leads with burn warnings instead of generic survival/runway text.
- Backend decision engine: Escalating penalties strengthened to cumulative -0.47 for extreme burn increases (was -0.35).

Result: High-burn hiring scenarios now show CONDITIONAL GO with realistic risk warnings, preventing founders from making uninformed commitments.

---

2. BURN LABEL CLARITY FIX (P1)

Problem: When burn increases (negative burn_reduction_pct), the UI showed "Burn Cut: -96%" which is confusing and misleading.

Fix: All locations now show "Burn Increase: +96%" with red styling when burn goes up. Fixed across: ScenarioCard, ScenarioWizard, Copilot page, Scenarios results, and AI Decision Summary.

---

3. SIMULATION SEARCH BAR PERSISTENCE (P0)

Problem: Typing a custom scenario and clicking Simulate would clear the input text, making it impossible to iterate on scenarios.

Fix: Removed setQuestionInput('') calls from the submit handler. Input text now persists through the full simulation lifecycle. "Run Another Scenario" button intentionally clears for a fresh start.

---

4. ONBOARDING STEP 3 PRE-FILL & PERSISTENCE (P1)

Problem: Step 3 (Expense Breakdown) started at $0 despite Step 2 having Payroll ($85K) and OpEx ($22K). Data was also not saved to the backend.

Fix: Step 3 Payroll and Operating Expenses now pre-fill from Step 2 data. "Next: Data Sources" button saves expense breakdown to the backend before advancing to Step 4.

---

5. BRIEFING PROGRESS INDICATOR (P1)

Problem: The 4-step progress checklist completed in ~3 seconds but actual briefing generation takes 20+ seconds.

Fix: Step durations now total 35 seconds (5s + 8s + 10s + 12s), spread proportionally across actual generation time with "Generating strategic briefing" as the fourth step.

---

6. STRATEGY CARD BURN WARNINGS (P1)

Problem: Strategy cards with extreme burn increases showed no warning, making high-risk strategies look equivalent to low-risk ones.

Fix: Cards with burn change >50% now display a red warning banner with phased execution advice. Cards with >75% burn change get stronger language about cost offsets.

---

7. DEPLOYMENT STABILITY (P0)

- Instant port binding: Port 5000 opens within milliseconds of process start.
- Environment propagation: FastAPI correctly detects production mode, skips seeding/migrations.
- SIGHUP resilience: Node process ignores SIGHUP signals (prevents workflow restart crashes).
- Database reliability: pool_pre_ping=True, pool_recycle=1800 for automatic connection recovery.
- Phased startup: Critical routes (auth, billing, onboarding) register in <1s. Remaining modules load in background.

---

8. INFRASTRUCTURE & API

- Billing API: /billing/plans (Free/Pro/Team), /billing/subscription, /billing/subscribe, /billing/cancel.
- Onboarding API: /onboarding/steps (4 steps), /onboarding/industries (7 industries with benchmarks).
- Demo metrics: /demo/metrics returns sample SaaS KPIs for unauthenticated demo experience.
- 375 total routes registered across all modules.
- Password validation simplified to 8 chars + 1 number (frontend and backend aligned).
- 401 redirect fix: Only fires on mutation 401s, not GET queries (prevents infinite redirect loops).

---

All changes are live in development. The application is running stable with all 375 routes registered and no errors.

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

<p>Here&rsquo;s a summary of everything completed on FounderConsole in the last 48 hours.</p>

<!-- T003: Simulation Calibration -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #dc2626;">1. Simulation Calibration Fix (P0)</h2>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:12px 16px;background:#fef2f2;border-left:3px solid #dc2626;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#991b1b;">Problem</p>
<p style="margin:0;font-size:13px;color:#4b5563;">&ldquo;Hire 5 engineers&rdquo; was getting an 8/10 GO verdict despite a 96% burn increase. The AI Decision Summary was dangerously optimistic for high-burn scenarios.</p>
</td>
</tr>
</table>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:12px 16px;background:#f0fdf4;border-left:3px solid #16a34a;border-radius:0 6px 6px 0;">
<p style="margin:0 0 8px;font-weight:700;font-size:14px;color:#15803d;">Fixes Applied</p>
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:13px;color:#4b5563;">
<tr><td style="padding:3px 0;"><strong>Verdict downgrade:</strong> GO automatically downgrades to CONDITIONAL GO when burn increases 50%+ vs baseline.</td></tr>
<tr><td style="padding:3px 0;"><strong>Stronger score penalties:</strong> Deduction increased from &minus;1.5 to &minus;2.5 (50%+ burn) and &minus;3.5 (75%+ burn). Previous 8/10 now scores ~4&ndash;5/10.</td></tr>
<tr><td style="padding:3px 0;"><strong>Key Risk priority:</strong> When burn increases 50%+, the Key Risk bullet now leads with burn warnings.</td></tr>
<tr><td style="padding:3px 0;"><strong>Backend engine:</strong> Escalating penalties strengthened to cumulative &minus;0.47 for extreme burn increases (was &minus;0.35).</td></tr>
</table>
</td>
</tr>
</table>

<!-- T002: Burn Label -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #f59e0b;">2. Burn Label Clarity Fix (P1)</h2>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:12px 16px;background:#fef3c7;border-left:3px solid #f59e0b;border-radius:0 6px 6px 0;">
<p style="margin:0;font-size:13px;color:#4b5563;">When burn increases, the UI previously showed <strong>&ldquo;Burn Cut: &minus;96%&rdquo;</strong>. Now correctly shows <strong style="color:#dc2626;">&ldquo;Burn Increase: +96%&rdquo;</strong> with red styling. Fixed across all components: ScenarioCard, ScenarioWizard, Copilot, Scenarios results, and AI Decision Summary.</p>
</td>
</tr>
</table>

<!-- T001: Search Bar -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #6366f1;">3. Simulation Search Bar Persistence (P0)</h2>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:12px 16px;background:#eef2ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0;font-size:13px;color:#4b5563;">Input text now persists through the full simulation lifecycle &mdash; type a custom scenario, click Simulate, and the text stays visible for iteration. &ldquo;Run Another Scenario&rdquo; button intentionally clears for a fresh start.</p>
</td>
</tr>
</table>

<!-- T005: Onboarding -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #8b5cf6;">4. Onboarding Step 3 Pre-fill &amp; Persistence (P1)</h2>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:12px 16px;background:#f5f3ff;border-left:3px solid #8b5cf6;border-radius:0 6px 6px 0;">
<p style="margin:0;font-size:13px;color:#4b5563;">Step 3 Payroll and Operating Expenses now pre-fill from Step 2 data. &ldquo;Next: Data Sources&rdquo; button saves expense breakdown to the backend before advancing to Step 4.</p>
</td>
</tr>
</table>

<!-- T004: Briefing Progress -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #0ea5e9;">5. Briefing Progress Indicator (P1)</h2>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:12px 16px;background:#f0f9ff;border-left:3px solid #0ea5e9;border-radius:0 6px 6px 0;">
<p style="margin:0;font-size:13px;color:#4b5563;">Step durations now total 35 seconds (5s + 8s + 10s + 12s), spread proportionally across actual generation time with &ldquo;Generating strategic briefing&rdquo; as the fourth step. No more misleading instant completion.</p>
</td>
</tr>
</table>

<!-- T006: Strategy Card Warnings -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #ec4899;">6. Strategy Card Burn Warnings (P1)</h2>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:12px 16px;background:#fdf2f8;border-left:3px solid #ec4899;border-radius:0 6px 6px 0;">
<p style="margin:0;font-size:13px;color:#4b5563;">Cards with burn change &gt;50% now display a red warning banner with phased execution advice. Cards with &gt;75% burn change get stronger language about cost offsets before committing.</p>
</td>
</tr>
</table>

<!-- Deployment Stability -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #16a34a;">7. Deployment Stability (P0)</h2>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:14px 16px;background:#f0fdf4;border-left:3px solid #16a34a;border-radius:0 6px 6px 0;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:13px;color:#4b5563;">
<tr><td style="padding:3px 0;"><strong>Instant port binding:</strong> Port 5000 opens within milliseconds of process start.</td></tr>
<tr><td style="padding:3px 0;"><strong>Environment propagation:</strong> FastAPI correctly detects production mode, skips seeding/migrations.</td></tr>
<tr><td style="padding:3px 0;"><strong>SIGHUP resilience:</strong> Node process ignores SIGHUP signals (prevents workflow restart crashes).</td></tr>
<tr><td style="padding:3px 0;"><strong>Database reliability:</strong> pool_pre_ping=True, pool_recycle=1800 for automatic connection recovery.</td></tr>
<tr><td style="padding:3px 0;"><strong>Phased startup:</strong> Critical routes (auth, billing, onboarding) register in &lt;1s. Remaining modules load in background.</td></tr>
</table>
</td>
</tr>
</table>

<!-- Infrastructure -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #64748b;">8. Infrastructure &amp; API</h2>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:14px 16px;background:#f8fafc;border-left:3px solid #64748b;border-radius:0 6px 6px 0;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:13px;color:#4b5563;">
<tr><td style="padding:3px 0;">Billing API: /billing/plans (Free/Pro/Team), subscription management, subscribe/cancel endpoints.</td></tr>
<tr><td style="padding:3px 0;">Onboarding API: 4 steps, 7 industries with benchmark flags.</td></tr>
<tr><td style="padding:3px 0;">Demo metrics endpoint for unauthenticated demo experience.</td></tr>
<tr><td style="padding:3px 0;"><strong>375 total routes</strong> registered across all modules.</td></tr>
<tr><td style="padding:3px 0;">Password validation simplified to 8 chars + 1 number (aligned frontend/backend).</td></tr>
<tr><td style="padding:3px 0;">401 redirect fix: Only fires on mutations, not GET queries (prevents infinite loops).</td></tr>
</table>
</td>
</tr>
</table>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:24px 0 0;">
<tr>
<td style="padding:14px 16px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;text-align:center;">
<p style="margin:0;font-size:14px;font-weight:700;color:#15803d;">All changes are live in development. Application running stable with no errors.</p>
</td>
</tr>
</table>

<p style="margin-top:30px;padding-top:15px;border-top:1px solid #e5e5e5;font-size:13px;color:#888;">
FounderConsole
</p>

</div>
</body>
</html>"""


def send_all():
    sender = "Nikita from FounderConsole <noreply@founderconsole.ai>"

    print(f"Sending 48-hour task update v26 to {len(RECIPIENTS)} recipients...")
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
            subject="48-Hour Update: Simulation Calibration Fix, Burn Label Clarity, Deployment Stability & More",
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
