"""
Send update email v30 - Flight Simulator: MiroFish-Inspired Multi-Agent Simulation Engine.
Sender: Arjun from FounderConsole <arjun@founderconsole.ai>
"""
import os, sys, time, uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from server.email.service import _send_email_sync

CAMPAIGN = "founderconsole_update_mar2026_v30"

BASE_URL = "https://fund-flow.replit.app"

RECIPIENTS = [
    {"email": "nikita.luther@gmail.com", "id": "nikita_luther", "name": "Nikita"},
    {"email": "nikita@predixen.ai", "id": "nikita_predixen", "name": "Nikita"},
    {"email": "nikitafl2024@gmail.com", "id": "nikita_fl2024", "name": "Nikita"},
    {"email": "vysheshk@gmail.com", "id": "vyshesh_k", "name": "Vyshesh"},
]


def build_plain_text(rcpt: dict) -> str:
    return f"""Hi {rcpt['name']},

Major update shipped on FounderConsole — the Flight Simulator has been completely rebuilt from the ground up.

---

1. MIROFISH-INSPIRED MULTI-AGENT SIMULATION ENGINE

The Flight Simulator now runs a full LLM-powered multi-agent simulation. Seven AI agents — Founder, two Investors, Customer, Team, Market, and Competitor — each with unique LLM-generated personas, make independent decisions every round using OpenAI gpt-4o-mini.

Each agent has:
- Short-term memory (recent decisions) and long-term memory (accumulated learnings)
- Stage-based activity levels — Founder dominates early, Investors ramp up mid-simulation, Competitors intensify late
- Chain-of-thought reasoning with realistic impact constraints
- Anti-repetition logic so agents vary their strategy round to round

The engine runs 6-24 month simulations with monthly dynamics: customer acquisition, churn, cash flow, and burn rate all update each round based on agent actions.

---

2. REAL-TIME SSE STREAMING

The simulation streams results live to the browser via Server-Sent Events. As agents make decisions, you see:
- Agent persona cards appear as the LLM generates them
- A live event feed showing each agent's decision with reasoning, impact tags, and chain reactions
- Animated metric counters (Cash, MRR, Burn, Runway, Customers) updating in real-time after each round
- A horizontal step progress tracker showing which simulation stage you're in

No page reloads, no polling — pure streaming from the backend.

---

3. GLASSMORPHISM UI REDESIGN

The entire Simulation Console has been redesigned with a MiroFish-inspired glassmorphism aesthetic:
- Frosted glass cards with backdrop-blur and gradient borders
- Background animated orbs for depth
- Staggered entrance animations on all panels
- Shimmer skeleton loading states during agent generation
- Status badges with semantic colors (positive/negative/neutral)
- Collapsible terminal log drawer for debugging
- Social-media-style agent event cards with reason/impact/chain display

All animations use the fc- prefix and respect prefers-reduced-motion.

---

4. POST-SIMULATION AI REPORT

After the simulation completes, an LLM generates a structured executive report:
- Outcome score (0-100) and term sheet probability
- Executive summary, key findings, risk factors, and opportunities
- Strategic recommendation based on all agent decisions
- Plausibility warnings if metrics exceed realistic bounds (MRR > $100M, customers > 1M)

---

5. SIMULATION ENGINE GUARDRAILS

Built-in safeguards to keep results realistic:
- Growth rate auto-converts from percentage to decimal and caps at 50%/month max
- Cash flow now properly accounts for revenue: cash += MRR - burn (not just subtracting burn)
- All LLM impact deltas are clamped proportionally — customer changes max ±15% of current, MRR delta max ±$5K per action
- Hard ceilings: MRR caps at $100M, customers at 1M per simulation
- Metrics like morale, quality, and confidence clamped to [0, 1]

---

All 5 tabs remain: Scenarios, Stress Tests, What-If, History, and Flight Simulator. The Flight Simulator is the 5th tab at /simulate.

Everything is live now.

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

<p>Major update shipped on FounderConsole &mdash; the <strong>Flight Simulator</strong> has been completely rebuilt from the ground up.</p>

<!-- 1. Multi-Agent Engine -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #6366f1;">1. MiroFish-Inspired Multi-Agent Simulation Engine</h2>

<p style="font-size:13px;color:#4b5563;margin:0 0 12px;">Seven AI agents &mdash; Founder, two Investors, Customer, Team, Market, and Competitor &mdash; each with unique LLM-generated personas, make independent decisions every round using OpenAI gpt-4o-mini.</p>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:14px 16px;background:#eef2ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 8px;font-weight:700;font-size:14px;color:#4338ca;">Per-Agent Intelligence</p>
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:13px;color:#4b5563;">
<tr><td style="padding:3px 0;">Short-term memory (recent decisions) + long-term memory (accumulated learnings)</td></tr>
<tr><td style="padding:3px 0;">Stage-based activity: Founder dominates early, Investors ramp mid, Competitors intensify late</td></tr>
<tr><td style="padding:3px 0;">Chain-of-thought reasoning with realistic impact constraints</td></tr>
<tr><td style="padding:3px 0;">Anti-repetition logic &mdash; agents vary strategy round to round</td></tr>
</table>
</td>
</tr>
</table>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:14px 16px;background:#f0fdf4;border-left:3px solid #16a34a;border-radius:0 6px 6px 0;">
<p style="margin:0 0 8px;font-weight:700;font-size:14px;color:#15803d;">Monthly Dynamics</p>
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:13px;color:#4b5563;">
<tr><td style="padding:3px 0;">6&ndash;24 month simulation horizon</td></tr>
<tr><td style="padding:3px 0;">Customer acquisition, churn, cash flow, and burn update each round</td></tr>
<tr><td style="padding:3px 0;">Revenue properly flows into cash: cash += MRR &minus; burn</td></tr>
</table>
</td>
</tr>
</table>

<!-- 2. SSE Streaming -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #0ea5e9;">2. Real-Time SSE Streaming</h2>

<p style="font-size:13px;color:#4b5563;margin:0 0 12px;">The simulation streams results live to the browser via Server-Sent Events. No page reloads, no polling.</p>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:14px 16px;background:#f0f9ff;border-left:3px solid #0ea5e9;border-radius:0 6px 6px 0;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:13px;color:#4b5563;">
<tr><td style="padding:3px 0;">Agent persona cards appear as the LLM generates them</td></tr>
<tr><td style="padding:3px 0;">Live event feed: each decision with reasoning, impact tags, chain reactions</td></tr>
<tr><td style="padding:3px 0;">Animated metric counters (Cash, MRR, Burn, Runway, Customers) update per round</td></tr>
<tr><td style="padding:3px 0;">Horizontal step progress tracker showing simulation stage</td></tr>
</table>
</td>
</tr>
</table>

<!-- 3. Glassmorphism UI -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #8b5cf6;">3. Glassmorphism UI Redesign</h2>

<p style="font-size:13px;color:#4b5563;margin:0 0 12px;">The entire Simulation Console has been redesigned with a MiroFish-inspired glassmorphism aesthetic.</p>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:14px 16px;background:#faf5ff;border-left:3px solid #8b5cf6;border-radius:0 6px 6px 0;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:13px;color:#4b5563;">
<tr><td style="padding:3px 0;">Frosted glass cards with backdrop-blur and gradient borders</td></tr>
<tr><td style="padding:3px 0;">Background animated orbs for depth</td></tr>
<tr><td style="padding:3px 0;">Staggered entrance animations on all panels</td></tr>
<tr><td style="padding:3px 0;">Shimmer skeleton loading during agent generation</td></tr>
<tr><td style="padding:3px 0;">Social-media-style agent event cards with reason/impact/chain</td></tr>
<tr><td style="padding:3px 0;">Collapsible terminal log drawer</td></tr>
<tr><td style="padding:3px 0;">All animations use <code style="background:#ede9fe;padding:1px 4px;border-radius:3px;font-size:12px;">fc-</code> prefix, respect <code style="background:#ede9fe;padding:1px 4px;border-radius:3px;font-size:12px;">prefers-reduced-motion</code></td></tr>
</table>
</td>
</tr>
</table>

<!-- 4. AI Report -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #f59e0b;">4. Post-Simulation AI Report</h2>

<p style="font-size:13px;color:#4b5563;margin:0 0 12px;">After the simulation completes, an LLM generates a structured executive report.</p>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:14px 16px;background:#fffbeb;border-left:3px solid #f59e0b;border-radius:0 6px 6px 0;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:13px;color:#4b5563;">
<tr><td style="padding:3px 0;">Outcome score (0&ndash;100) and term sheet probability</td></tr>
<tr><td style="padding:3px 0;">Executive summary, key findings, risk factors, opportunities</td></tr>
<tr><td style="padding:3px 0;">Strategic recommendation based on all agent decisions</td></tr>
<tr><td style="padding:3px 0;">Plausibility warnings if metrics exceed realistic bounds</td></tr>
</table>
</td>
</tr>
</table>

<!-- 5. Guardrails -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #16a34a;">5. Simulation Engine Guardrails</h2>

<p style="font-size:13px;color:#4b5563;margin:0 0 12px;">Built-in safeguards to keep results realistic.</p>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:14px 16px;background:#f0fdf4;border-left:3px solid #16a34a;border-radius:0 6px 6px 0;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:13px;color:#4b5563;">
<tr><td style="padding:3px 0;">Growth rate auto-converts percentage &rarr; decimal, caps at 50%/mo</td></tr>
<tr><td style="padding:3px 0;">Cash flow: <code style="background:#dcfce7;padding:1px 4px;border-radius:3px;font-size:12px;">cash += MRR - burn</code> (revenue counted)</td></tr>
<tr><td style="padding:3px 0;">LLM impact deltas clamped: customers &plusmn;15%, MRR &plusmn;$5K per action</td></tr>
<tr><td style="padding:3px 0;">Hard ceilings: MRR $100M, customers 1M</td></tr>
<tr><td style="padding:3px 0;">Morale, quality, confidence clamped to [0, 1]</td></tr>
</table>
</td>
</tr>
</table>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:24px 0 0;">
<tr>
<td style="padding:14px 16px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;text-align:center;">
<p style="margin:0;font-size:14px;font-weight:700;color:#15803d;">All changes are live. Flight Simulator available at /simulate (5th tab). Application running stable.</p>
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

    print(f"Sending update v30 to {len(RECIPIENTS)} recipients...")
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
            subject="FounderConsole Update: Flight Simulator Rebuilt — MiroFish Multi-Agent AI Engine, SSE Streaming & Glassmorphism UI",
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
