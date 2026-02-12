"""
Send update email v19 - Enhanced Decisions Page UX (Sticky TOC, Checkboxes, Loading, Alt Paths).
Sender: ivl58oxz@predixen.app
"""
import os, sys, time, uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from server.email.service import _send_email_sync

CAMPAIGN = "predixen_decisions_ux_feb2026_v19"

BASE_URL = "https://predixen.app"
IMG_AI_SUMMARY = f"{BASE_URL}/email-assets/sim-ai-summary.png"
IMG_SENSITIVITY = f"{BASE_URL}/email-assets/sim-sensitivity.png"
IMG_STRESS_TESTS = f"{BASE_URL}/email-assets/sim-stress-tests.png"
IMG_COUNTER_MOVES = f"{BASE_URL}/email-assets/sim-counter-moves.png"
IMG_METRICS = f"{BASE_URL}/email-assets/sim-metrics.png"

RECIPIENTS = [
    {"email": "nikita.luther@gmail.com", "id": "nikita_luther", "name": "Nikita"},
    {"email": "nikita@predixen.ai", "id": "nikita_predixen", "name": "Nikita"},
    {"email": "nikitafl2024@gmail.com", "id": "nikita_fl2024", "name": "Nikita"},
]


def build_plain_text(rcpt: dict) -> str:
    return f"""Hi {rcpt['name']},

The Decisions page just got a significant UX upgrade. Here is what changed:

---

ENHANCED DECISIONS PAGE - NEW UX FEATURES

Building on the narrative strategic briefing we shipped earlier, the Decisions page now includes several usability improvements that make the briefing more actionable and easier to navigate.

---

1. STICKY TABLE OF CONTENTS

On wider screens, a persistent navigation sidebar appears on the right side of the page. It tracks which section you are currently reading and lets you jump to any section with a single click. Sections are numbered 1 through 6 for quick reference.

---

2. ANIMATED LOADING PROGRESS

Instead of a generic spinner, generating a briefing now shows a 4-step progress indicator:
- Analyzing financial data
- Evaluating growth trajectory
- Building execution playbook
- Assessing risks and alternatives

Each step animates in sequence with green completion dots and an amber pulse for the active step.

---

3. PLAYBOOK CHECKBOXES WITH PERSISTENCE

Every action item in the Execution Playbook now has a checkbox. Check items off as your team completes them. Progress is saved automatically and persists across sessions. A counter at the top shows "X of Y completed" so you always know where you stand. Checked items get a line-through style and fade slightly.

---

4. SECTION DIVIDERS

Each section now opens with a labeled divider (SECTION 1, SECTION 2, etc.) followed by a horizontal rule. This gives the document a clearer visual hierarchy and makes it easier to scan.

---

5. COLOR-CODED RISK BADGES

In the Key Risks section, each risk now displays a color-coded likelihood badge:
- High likelihood: red badge
- Medium likelihood: amber badge
- Low likelihood: green badge

---

6. NEW SECTION: ALTERNATIVE PATHS CONSIDERED

A sixth section has been added after Key Risks. It presents 3 alternative strategies that were evaluated but not recommended, each with:
- The strategy name
- Why it was not chosen right now
- Under what conditions it might become the right call

---

7. URGENCY CALLOUT BOX

The urgency text in the recommendation section now renders as a distinct amber-bordered callout box with a warning icon, making it impossible to miss.

---

8. COPY BRIEF BUTTON

A new "Copy Brief" button in the header copies the entire briefing as formatted plain text to your clipboard. Forward it to your board, co-founder, or advisor in seconds.

---

9. IMPROVED ERROR HANDLING

If loading fails, you now see a clear error card with a "Try Again" button instead of an infinite spinner. If cached data exists, it stays visible with an "Updating" badge while refreshing in the background.

---

10. DATE BUG FIX

All AI-generated dates (pivot deadlines, exhaustion projections, timeline references) now correctly use today's date as the reference point. No more past dates in the output.

---

These changes make the Decisions page more interactive, easier to navigate, and genuinely useful as a working document for your team.

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

<p>The Decisions page just got a significant UX upgrade. Building on the narrative strategic briefing, the page now includes several usability improvements that make it more actionable and easier to navigate.</p>

<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #6366f1;">Enhanced Decisions Page &mdash; New UX Features</h2>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:16px 0;">

<tr>
<td style="padding:14px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:15px;color:#4338ca;">Sticky Table of Contents</p>
<p style="margin:0;font-size:13px;color:#4b5563;">On wider screens, a persistent navigation sidebar appears on the right side of the page. It tracks which section you&rsquo;re currently reading using scroll detection and lets you jump to any section with a single click. All six sections are numbered for quick reference.</p>
</td>
</tr>
<tr><td style="height:10px;"></td></tr>

<tr>
<td style="padding:14px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:15px;color:#4338ca;">Animated Loading Progress</p>
<p style="margin:0;font-size:13px;color:#4b5563;">Instead of a generic spinner, generating a briefing now shows a 4-step progress indicator: analyzing financial data, evaluating growth, building playbook, assessing risks. Each step animates in sequence with green completion dots and an amber pulse for the active step.</p>
</td>
</tr>
<tr><td style="height:10px;"></td></tr>

<tr>
<td style="padding:14px 16px;background:#f0fdf4;border-left:3px solid #16a34a;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:15px;color:#15803d;">Playbook Checkboxes with Persistence</p>
<p style="margin:0;font-size:13px;color:#4b5563;">Every action item in the Execution Playbook now has a checkbox. Check items off as your team completes them. Progress saves automatically and persists across sessions. A counter shows &ldquo;X of Y completed&rdquo; so you always know where you stand. Checked items get a line-through style and fade slightly.</p>
</td>
</tr>
<tr><td style="height:10px;"></td></tr>

<tr>
<td style="padding:14px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:15px;color:#4338ca;">Section Dividers &amp; Visual Hierarchy</p>
<p style="margin:0;font-size:13px;color:#4b5563;">Each section now opens with a labeled divider (SECTION 1, SECTION 2, etc.) followed by a horizontal rule. This gives the document a clearer structure and makes it easier to scan quickly.</p>
</td>
</tr>
<tr><td style="height:10px;"></td></tr>

<tr>
<td style="padding:14px 16px;background:#fef9f0;border-left:3px solid #d97706;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:15px;color:#b45309;">Color-Coded Risk Badges</p>
<p style="margin:0;font-size:13px;color:#4b5563;">In the Key Risks section, each risk now displays a color-coded likelihood badge: <span style="color:#dc2626;font-weight:600;">High</span> (red), <span style="color:#d97706;font-weight:600;">Medium</span> (amber), <span style="color:#16a34a;font-weight:600;">Low</span> (green). Makes severity instantly scannable.</p>
</td>
</tr>
<tr><td style="height:10px;"></td></tr>

<tr>
<td style="padding:14px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:15px;color:#4338ca;">New Section: Alternative Paths Considered</p>
<p style="margin:0;font-size:13px;color:#4b5563;">A sixth section has been added after Key Risks. It presents 3 alternative strategies that were evaluated but not recommended, each explaining why it was rejected and under what conditions it might become the right call.</p>
</td>
</tr>
<tr><td style="height:10px;"></td></tr>

<tr>
<td style="padding:14px 16px;background:#fef9f0;border-left:3px solid #d97706;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:15px;color:#b45309;">Urgency Callout Box</p>
<p style="margin:0;font-size:13px;color:#4b5563;">The urgency text in the recommendation section now renders as a distinct amber-bordered callout box with a warning icon, making it impossible to miss.</p>
</td>
</tr>
<tr><td style="height:10px;"></td></tr>

<tr>
<td style="padding:14px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:15px;color:#4338ca;">Copy Brief &amp; Error Handling</p>
<p style="margin:0;font-size:13px;color:#4b5563;">A new &ldquo;Copy Brief&rdquo; button copies the entire briefing as formatted plain text to your clipboard. Error states now show a clear card with a &ldquo;Try Again&rdquo; button instead of infinite spinners, and cached data stays visible during refreshes.</p>
</td>
</tr>
<tr><td style="height:10px;"></td></tr>

<tr>
<td style="padding:14px 16px;background:#f0fdf4;border-left:3px solid #16a34a;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:15px;color:#15803d;">Date Bug Fix</p>
<p style="margin:0;font-size:13px;color:#4b5563;">All AI-generated dates (pivot deadlines, exhaustion projections, timeline references) now correctly use today&rsquo;s date as the reference point. No more past dates appearing in the output.</p>
</td>
</tr>

</table>

<p style="font-size:14px;color:#4b5563;margin-top:20px;">These changes make the Decisions page more interactive, easier to navigate, and genuinely useful as a working document for your team.</p>

<p style="margin-top:30px;padding-top:15px;border-top:1px solid #e5e5e5;font-size:13px;color:#888;">
Predixen Intelligence OS
</p>

</div>
</body>
</html>"""


def send_all():
    sender = "Predixen <ivl58oxz@predixen.app>"

    print(f"Sending Decisions UX upgrade update v19 to {len(RECIPIENTS)} recipients...")
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
            subject="Predixen Decisions Page - Enhanced UX: Sticky TOC, Playbook Checkboxes, Alt Paths",
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
