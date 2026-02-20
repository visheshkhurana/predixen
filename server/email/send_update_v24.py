"""
Send update email v24 - QA Front Complete, NLP Engine, Security Hardening & Deployment Stability.
Sender: hello@founderconsole.ai
"""
import os, sys, time, uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from server.email.service import _send_email_sync

CAMPAIGN = "founderconsole_qa_security_feb2026_v24"

RECIPIENTS = [
    {"email": "nikita.luther@gmail.com", "id": "nikita_luther", "name": "Nikita"},
    {"email": "nikita@founderconsole.ai", "id": "nikita_founderconsole", "name": "Nikita"},
    {"email": "nikitafl2024@gmail.com", "id": "nikita_fl2024", "name": "Nikita"},
]


def build_plain_text(rcpt: dict) -> str:
    return f"""Hi {rcpt['name']},

Here's an update on what's been completed since the last report.

---

QA FRONT ADMIN INTERFACE

---

The QA Front admin interface is now fully operational with 10 validation tabs, each providing PASS/FAIL reporting with detailed breakdowns:

1. Smoke Tests - Core endpoint health and authentication checks
2. RBAC - Role-based access control enforcement
3. Tenant Isolation - Cross-tenant data leak prevention checks
4. KPI Sanity - Metric bounds validation with sanity checks
5. Scenario Engine - NLP parsing, invariant testing, simulation validation
6. Route Health - Frontend and API route availability
7. Health Consistency - Truth scan and health score consistency
8. Briefing - Strategic briefing generation checks
9. Regression - Cross-page consistency and feature regression
10. Calculation Tests - 94 automated canonical calculation tests

One-click test account creation is available from the QA Front page.

---

CALCULATION TEST RESULTS

---

- 55/55 Core B2B SaaS canonical calculations: PASS
- 25/25 Consumer subscription calculations: PASS
- 14/14 Scenario directionality tests: PASS
- All scenario invariants: PASS
- 12/12 NLP scenario parsing tests: PASS

---

NLP SCENARIO ENGINE

---

The natural language parser now correctly handles 30 scenario types:
- Cost cuts (marketing, overhead, cloud, infrastructure, expenses)
- Hiring actions (hire, layoff, freeze hiring)
- Revenue changes (growth, decline, pricing adjustments)
- Fundraising (raise Series A/B, fundraise amounts)
- Churn modifications (reduce churn, boost retention)
- Compound scenarios (multiple actions in one query)

Fixed: "freeze hiring for 6 months" now correctly extracts hiring_freeze_months parameter (regex wasn't matching plural "months").

---

SECURITY HARDENING

---

1. XSS Prevention: All email template fields (category, feature_name, description, author) are now HTML-escaped using html.escape(). All export HTML content (titles, metric names/values, flag severity/title/description, benchmark labels) are escaped via escapeHtml().

2. CSV Upload Protection: Both csv-detect and import-csv endpoints enforce 5MB file size and 10,000 row limits. Oversized uploads return 413 with clear error messages.

3. Internal Route Protection: X-Internal-Secret header validation on internal API routes.

---

DEPLOYMENT STABILITY

---

1. Port Configuration: Simplified getFastAPIPort() to always return "8001", eliminating conditional logic that caused port mismatch in production.

2. Deferred Startup: Database migrations, schema creation, and seed data now run as background tasks AFTER the FastAPI server opens its port. This prevents deployment health check timeouts. The /health endpoint returns a "ready" flag to track startup completion.

3. Startup Wait: Increased FastAPI wait timeout from 90 to 120 retries (4 minutes) for production stability.

---

CURRENT STATE

---

- All P0/P1/P2 bugs: Fixed
- QA Front: 10 tabs operational
- Canonical calculations: 94/94 passing
- NLP parsing: 12/12 passing
- Directionality: 14/14 passing
- Security: XSS + CSV limits + internal route auth
- Deployment: Stable with deferred startup pattern

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

<p>Here&rsquo;s an update on what&rsquo;s been completed since the last report.</p>

<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #6366f1;">QA Front Admin Interface</h2>

<p style="font-size:14px;color:#374151;">The QA Front admin interface is now fully operational with <strong>10 validation tabs</strong>, each providing PASS/FAIL reporting with detailed breakdowns:</p>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:10px 16px;background:#f0fdf4;border-left:3px solid #16a34a;border-radius:0 6px 6px 0;">
<table cellpadding="2" cellspacing="0" border="0" width="100%" style="font-size:13px;color:#374151;">
<tr><td style="padding:2px 0;"><strong>1.</strong> Smoke Tests</td><td style="padding:2px 0;">Core endpoint health &amp; auth</td></tr>
<tr><td style="padding:2px 0;"><strong>2.</strong> RBAC</td><td style="padding:2px 0;">Role-based access control</td></tr>
<tr><td style="padding:2px 0;"><strong>3.</strong> Tenant Isolation</td><td style="padding:2px 0;">Cross-tenant data leak prevention</td></tr>
<tr><td style="padding:2px 0;"><strong>4.</strong> KPI Sanity</td><td style="padding:2px 0;">Metric bounds validation</td></tr>
<tr><td style="padding:2px 0;"><strong>5.</strong> Scenario Engine</td><td style="padding:2px 0;">NLP parsing &amp; invariant testing</td></tr>
<tr><td style="padding:2px 0;"><strong>6.</strong> Route Health</td><td style="padding:2px 0;">Frontend &amp; API route availability</td></tr>
<tr><td style="padding:2px 0;"><strong>7.</strong> Health Consistency</td><td style="padding:2px 0;">Truth scan &amp; health score checks</td></tr>
<tr><td style="padding:2px 0;"><strong>8.</strong> Briefing</td><td style="padding:2px 0;">Strategic briefing generation</td></tr>
<tr><td style="padding:2px 0;"><strong>9.</strong> Regression</td><td style="padding:2px 0;">Cross-page consistency</td></tr>
<tr><td style="padding:2px 0;"><strong>10.</strong> Calculation Tests</td><td style="padding:2px 0;">94 automated canonical tests</td></tr>
</table>
</td>
</tr>
</table>

<p style="font-size:13px;color:#6b7280;">One-click test account creation is available from the QA Front page.</p>

<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #6366f1;">Calculation Test Results</h2>

<table cellpadding="6" cellspacing="0" border="0" width="100%" style="margin:10px 0;font-size:13px;border:1px solid #e5e7eb;border-radius:6px;border-collapse:collapse;">
<tr style="background:#f9fafb;">
<th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;">Test Suite</th>
<th style="text-align:center;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;">Result</th>
<th style="text-align:center;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;">Status</th>
</tr>
<tr><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">Core B2B SaaS Canonical</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;text-align:center;">55/55</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;text-align:center;color:#16a34a;font-weight:600;">PASS</td></tr>
<tr><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">Consumer Subscription</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;text-align:center;">25/25</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;text-align:center;color:#16a34a;font-weight:600;">PASS</td></tr>
<tr><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">Scenario Directionality</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;text-align:center;">14/14</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;text-align:center;color:#16a34a;font-weight:600;">PASS</td></tr>
<tr><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;">Scenario Invariants</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;text-align:center;">All</td><td style="padding:6px 8px;border-bottom:1px solid #f3f4f6;text-align:center;color:#16a34a;font-weight:600;">PASS</td></tr>
<tr><td style="padding:6px 8px;">NLP Scenario Parsing</td><td style="padding:6px 8px;text-align:center;">12/12</td><td style="padding:6px 8px;text-align:center;color:#16a34a;font-weight:600;">PASS</td></tr>
</table>

<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #6366f1;">NLP Scenario Engine</h2>

<p style="font-size:14px;color:#374151;">The natural language parser now correctly handles <strong>30 scenario types</strong> including:</p>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:10px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0;font-size:13px;color:#374151;line-height:1.8;">
Cost cuts (marketing, overhead, cloud, infrastructure) &bull;
Hiring actions (hire, layoff, freeze) &bull;
Revenue changes (growth, decline, pricing) &bull;
Fundraising (Series A/B, amounts with M/K) &bull;
Churn modifications (reduce churn, boost retention) &bull;
Compound scenarios (multiple actions in one query)
</p>
</td>
</tr>
<tr><td style="height:8px;"></td></tr>
<tr>
<td style="padding:10px 16px;background:#f0fdf4;border-left:3px solid #16a34a;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:13px;color:#15803d;">Fixed</p>
<p style="margin:0;font-size:13px;color:#4b5563;">&ldquo;freeze hiring for 6 months&rdquo; now correctly extracts the hiring_freeze_months parameter. The regex pattern wasn&rsquo;t matching the plural &ldquo;months&rdquo;.</p>
</td>
</tr>
</table>

<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #6366f1;">Security Hardening</h2>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:12px 16px;background:#fef3c7;border-left:3px solid #f59e0b;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#92400e;">XSS Prevention</p>
<p style="margin:0;font-size:13px;color:#4b5563;">All email template fields and export HTML content are now HTML-escaped. This covers notification emails (category, feature name, description, author) and data exports (titles, metric names/values, flag severity, benchmark labels).</p>
</td>
</tr>
<tr><td style="height:8px;"></td></tr>
<tr>
<td style="padding:12px 16px;background:#fef3c7;border-left:3px solid #f59e0b;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#92400e;">CSV Upload Protection</p>
<p style="margin:0;font-size:13px;color:#4b5563;">Both csv-detect and import-csv endpoints enforce a 5 MB file size limit and a 10,000 row limit. Oversized uploads return HTTP 413 with clear error messages.</p>
</td>
</tr>
<tr><td style="height:8px;"></td></tr>
<tr>
<td style="padding:12px 16px;background:#fef3c7;border-left:3px solid #f59e0b;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#92400e;">Internal Route Protection</p>
<p style="margin:0;font-size:13px;color:#4b5563;">Internal API routes are guarded by X-Internal-Secret header validation, preventing unauthorized access to administrative endpoints.</p>
</td>
</tr>
</table>

<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #6366f1;">Deployment Stability</h2>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:12px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#4338ca;">Deferred Startup Pattern</p>
<p style="margin:0;font-size:13px;color:#4b5563;">Database migrations, schema creation, and seed data now run as background tasks after the server opens its port. This prevents deployment health check timeouts. The /health endpoint returns a &ldquo;ready&rdquo; flag to track startup completion.</p>
</td>
</tr>
<tr><td style="height:8px;"></td></tr>
<tr>
<td style="padding:12px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#4338ca;">Port Configuration Fixed</p>
<p style="margin:0;font-size:13px;color:#4b5563;">Simplified FastAPI port configuration to always bind to port 8001, eliminating conditional logic that caused port mismatches in production.</p>
</td>
</tr>
<tr><td style="height:8px;"></td></tr>
<tr>
<td style="padding:12px 16px;background:#f8f7ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#4338ca;">Extended Health Check Window</p>
<p style="margin:0;font-size:13px;color:#4b5563;">Increased FastAPI startup wait timeout from 90 to 120 retries (4 minutes) for production stability.</p>
</td>
</tr>
</table>

<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #6366f1;">Current State</h2>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:14px 16px;background:#f0fdf4;border-left:3px solid #16a34a;border-radius:0 6px 6px 0;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:13px;color:#15803d;font-weight:600;">
<tr><td style="padding:3px 0;">All P0/P1/P2 bugs: Fixed</td></tr>
<tr><td style="padding:3px 0;">QA Front: 10 tabs operational</td></tr>
<tr><td style="padding:3px 0;">Canonical calculations: 94/94 passing</td></tr>
<tr><td style="padding:3px 0;">NLP parsing: 12/12 passing</td></tr>
<tr><td style="padding:3px 0;">Directionality: 14/14 passing</td></tr>
<tr><td style="padding:3px 0;">Security: XSS + CSV limits + internal route auth</td></tr>
<tr><td style="padding:3px 0;">Deployment: Stable with deferred startup</td></tr>
</table>
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
    sender = "Nikita from FounderConsole <hello@founderconsole.ai>"

    print(f"Sending QA/Security/Deployment update v24 to {len(RECIPIENTS)} recipients...")
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
            subject="Update: QA Front Complete, 94/94 Tests Passing, Security Hardening & Deployment Stability",
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
