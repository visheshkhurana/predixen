"""
Send update email v18 - Narrative Strategic Briefing (Decisions Page Redesign).
Sender: wlk2qbda@predixen.app
"""
import os, sys, time, uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from server.email.service import _send_email_sync

CAMPAIGN = "predixen_decisions_briefing_feb2026_v18"

RECIPIENTS = [
    {"email": "nikita.luther@gmail.com", "id": "nikita_luther", "name": "Nikita"},
    {"email": "nikita@predixen.ai", "id": "nikita_predixen", "name": "Nikita"},
    {"email": "nikitafl2024@gmail.com", "id": "nikita_fl2024", "name": "Nikita"},
]


def build_plain_text(rcpt: dict) -> str:
    return f"""Hi {rcpt['name']},

The Decisions page in Predixen Intelligence OS has been completely redesigned. It now reads like a strategic briefing document from a senior advisor -- no charts, no dashboards, just clear prose that tells you what to do and why.

---

THE NEW DECISIONS PAGE - NARRATIVE STRATEGIC BRIEFING

The entire page has been rebuilt as a founder's briefing document. Instead of charts, KPI cards, and percentage badges, you now see five clearly written sections that read like a memo from a McKinsey partner who has spent a week inside your company.

---

SECTION 1: THE SITUATION

An AI-generated 3-5 sentence paragraph describing your current financial state using your real data -- MRR, burn rate, runway, growth rate. No jargon, no dashboards. Just a clear assessment of where you stand right now, written as prose you could forward to your board.

---

SECTION 2: WHAT WE RECOMMEND

A bold action headline followed by 2-3 full paragraphs of written rationale. This section explains:
- WHY this specific action (not just what)
- WHY NOW (the cost of waiting)
- Trade-offs you are accepting
- The mechanics of execution

Plus a time-bound urgency indicator that tells you exactly how many days you have before this decision loses its effectiveness.

---

SECTION 3: WHAT HAPPENS IF YOU DO NOTHING

A 2-3 paragraph narrative projection of what happens if you ignore the recommendation. Includes:
- Your specific cash exhaustion date at current trajectory
- The exact growth rate needed to break even
- How your negotiating position deteriorates week by week
- The point at which options start disappearing

---

SECTION 4: EXECUTION PLAYBOOK

This is the most important section. 6-10 specific, team-ready action items the founder can forward directly to their team. Each item includes:
- Phase (Preparation Week 1-2, Execution Week 3-6, Optimization Week 7-8)
- A clear directive (not vague advice)
- Owner (the role responsible)
- Timeline (specific deadline)
- Done when: (verifiable completion criteria)

The playbook adapts based on whether you are in survival mode (<12 months runway) or growth mode (>12 months runway). Every action item uses your actual company numbers to set targets.

---

SECTION 5: KEY RISKS & CONTINGENCY PLANS

3-5 specific risks, each presented as a mini-paragraph that tells a vivid scenario:
- What could go wrong (specific scenario with your numbers)
- Why it is likely given your current data
- How severe the consequences would be

Each risk includes:
- Likelihood label (High / Medium / Low)
- "If this happens:" -- 2-3 sentences of specific, executable contingency actions
- "When to pivot:" -- a concrete deadline or metric threshold that tells you exactly when to change course if the risk materializes

These are not generic risks. They reference your actual burn rate, runway, revenue concentration, and growth trajectory.

---

All five sections are generated using your real financial data and AI analysis. The page is designed so a founder can read it in 5 minutes and know exactly what to do, why, and by when.

--
Predixen Intelligence OS
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

<p>The Decisions page in Predixen Intelligence OS has been completely redesigned. It now reads like a strategic briefing document from a senior advisor &mdash; no charts, no dashboards, just clear prose that tells you what to do and why.</p>

<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #6366f1;">The New Decisions Page &mdash; Narrative Strategic Briefing</h2>

<p style="font-size:14px;color:#4b5563;">The entire page has been rebuilt as a founder&rsquo;s briefing document. Instead of charts, KPI cards, and percentage badges, you now see five clearly written sections that read like a memo from a McKinsey partner who has spent a week inside your company.</p>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:16px 0;">

<tr>
<td style="padding:14px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:15px;color:#4338ca;">Section 1: The Situation</p>
<p style="margin:0;font-size:13px;color:#4b5563;">An AI-generated 3&ndash;5 sentence paragraph describing your current financial state using your real data &mdash; MRR, burn rate, runway, growth rate. No jargon, no dashboards. Just a clear assessment of where you stand, written as prose you could forward to your board.</p>
</td>
</tr>
<tr><td style="height:10px;"></td></tr>

<tr>
<td style="padding:14px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:15px;color:#4338ca;">Section 2: What We Recommend</p>
<p style="margin:0;font-size:13px;color:#4b5563;">A bold action headline followed by 2&ndash;3 full paragraphs explaining WHY this action, WHY NOW, the trade-offs you&rsquo;re accepting, and the mechanics of execution. Plus a time-bound urgency indicator.</p>
</td>
</tr>
<tr><td style="height:10px;"></td></tr>

<tr>
<td style="padding:14px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:15px;color:#4338ca;">Section 3: What Happens If You Do Nothing</p>
<p style="margin:0;font-size:13px;color:#4b5563;">A 2&ndash;3 paragraph narrative projection with your specific cash exhaustion date, the exact growth rate needed to break even, and how your position deteriorates week by week.</p>
</td>
</tr>
<tr><td style="height:10px;"></td></tr>

<tr>
<td style="padding:14px 16px;background:#f0fdf4;border-left:3px solid #16a34a;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:15px;color:#15803d;">Section 4: Execution Playbook (Most Important)</p>
<p style="margin:0 0 8px;font-size:13px;color:#4b5563;">6&ndash;10 specific, team-ready action items grouped into three phases. Each item includes:</p>
<table cellpadding="0" cellspacing="0" border="0" style="font-size:13px;color:#4b5563;">
<tr><td style="padding:2px 8px 2px 0;font-weight:600;color:#15803d;">Phase</td><td style="padding:2px 0;">Preparation (Wk 1&ndash;2), Execution (Wk 3&ndash;6), Optimization (Wk 7&ndash;8)</td></tr>
<tr><td style="padding:2px 8px 2px 0;font-weight:600;color:#15803d;">Action</td><td style="padding:2px 0;">Clear directive using your actual numbers</td></tr>
<tr><td style="padding:2px 8px 2px 0;font-weight:600;color:#15803d;">Owner</td><td style="padding:2px 0;">The role responsible</td></tr>
<tr><td style="padding:2px 8px 2px 0;font-weight:600;color:#15803d;">Timeline</td><td style="padding:2px 0;">Specific deadline within the phase</td></tr>
<tr><td style="padding:2px 8px 2px 0;font-weight:600;color:#15803d;">Done when</td><td style="padding:2px 0;">Verifiable completion criteria</td></tr>
</table>
<p style="margin:8px 0 0;font-size:12px;color:#6b7280;">Adapts automatically for survival mode (&lt;12mo runway) vs growth mode (&gt;12mo runway).</p>
</td>
</tr>
<tr><td style="height:10px;"></td></tr>

<tr>
<td style="padding:14px 16px;background:#fef9f0;border-left:3px solid #d97706;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:15px;color:#b45309;">Section 5: Key Risks &amp; Contingency Plans</p>
<p style="margin:0 0 8px;font-size:13px;color:#4b5563;">3&ndash;5 specific risks, each as a mini-paragraph describing what could go wrong, why it&rsquo;s likely, and the severity. Each risk includes:</p>
<table cellpadding="0" cellspacing="0" border="0" style="font-size:13px;color:#4b5563;">
<tr><td style="padding:2px 8px 2px 0;font-weight:600;color:#b45309;">Likelihood</td><td style="padding:2px 0;">High / Medium / Low</td></tr>
<tr><td style="padding:2px 8px 2px 0;font-weight:600;color:#b45309;">If this happens</td><td style="padding:2px 0;">2&ndash;3 sentences of specific contingency actions</td></tr>
<tr><td style="padding:2px 8px 2px 0;font-weight:600;color:#b45309;">When to pivot</td><td style="padding:2px 0;">Concrete deadline or metric threshold for changing course</td></tr>
</table>
<p style="margin:8px 0 0;font-size:12px;color:#6b7280;">All risks reference your actual burn rate, runway, revenue concentration, and growth trajectory.</p>
</td>
</tr>

</table>

<p style="font-size:14px;color:#4b5563;margin-top:20px;">All five sections are generated using your real financial data and AI analysis. The page is designed so a founder can read it in 5 minutes and know exactly what to do, why, and by when.</p>

<p style="margin-top:30px;padding-top:15px;border-top:1px solid #e5e5e5;font-size:13px;color:#888;">
Predixen Intelligence OS
</p>

</div>
</body>
</html>"""


def send_all():
    sender = "Predixen <wlk2qbda@predixen.app>"

    print(f"Sending Decisions page redesign update v18 to {len(RECIPIENTS)} recipients...")
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
            subject="Predixen Decisions Page - Narrative Strategic Briefing Redesign",
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
