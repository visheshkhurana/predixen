"""
Send update email v25 - Deployment Stability Fix: Instant Port Binding & Production Environment Detection.
Sender: kavibe8@founderconsole.ai
"""
import os, sys, time, uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from server.email.service import _send_email_sync

CAMPAIGN = "founderconsole_deploy_fix_feb2026_v25"

RECIPIENTS = [
    {"email": "nikita.luther@gmail.com", "id": "nikita_luther", "name": "Nikita"},
    {"email": "nikita@founderconsole.ai", "id": "nikita_founderconsole", "name": "Nikita"},
    {"email": "nikitafl2024@gmail.com", "id": "nikita_fl2024", "name": "Nikita"},
]


def build_plain_text(rcpt: dict) -> str:
    return f"""Hi {rcpt['name']},

Here's an update on deployment stability fixes completed today.

---

DEPLOYMENT FIX: INSTANT PORT BINDING

---

Problem: Deployment was failing because port 5000 wasn't opening fast enough for the health check. The Node.js server was waiting for the entire FastAPI backend (including database migrations and demo data seeding) to finish before opening the port.

Root Cause: Two issues were identified:

1. Port 5000 was opened AFTER all middleware registration and FastAPI readiness checks, causing a 30-60 second delay before the health check could connect.

2. esbuild replaces process.env.NODE_ENV at compile time, so the actual environment variable was never set in the process. When Node.js spawned the Python/FastAPI child process, it inherited no NODE_ENV variable, causing FastAPI to think it was in development mode and run all seeding operations.

---

FIXES APPLIED

---

1. Instant Port Binding
   Port 5000 now opens immediately after server creation, before ANY middleware, proxy setup, or FastAPI spawn. The health check can respond within milliseconds of process start.

2. Environment Variable Propagation
   The FastAPI child process now explicitly receives NODE_ENV and ENVIRONMENT variables matching the Node.js production setting. This ensures FastAPI correctly detects production mode and skips all seeding/migration operations.

3. Reduced FastAPI Wait Timeout
   Changed from 60 retries at 3 seconds to 30 retries at 2 seconds. The wait runs fully asynchronously without blocking any request handling.

4. Production Database Flags
   All four startup operations are disabled in production:
   - CREATE_SCHEMA=false
   - RUN_MIGRATIONS=false
   - SEED_BENCHMARKS=false
   - SEED_DEMO_DATA=false
   ENVIRONMENT=production is also explicitly set as a production env var.

---

RESULT

---

- Port 5000 opens within milliseconds of process start
- FastAPI starts in background without blocking requests
- Health checks pass immediately
- No database seeding or migration on production deploy
- API requests proxy to FastAPI as soon as it becomes available

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

<p>Here&rsquo;s an update on deployment stability fixes completed today.</p>

<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #dc2626;">Deployment Fix: Instant Port Binding</h2>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:12px 16px;background:#fef2f2;border-left:3px solid #dc2626;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#991b1b;">Problem</p>
<p style="margin:0;font-size:13px;color:#4b5563;">Deployment was failing because port 5000 wasn&rsquo;t opening fast enough for the health check. The Node.js server was waiting for the entire FastAPI backend (including database migrations and demo data seeding) to finish before accepting connections.</p>
</td>
</tr>
</table>

<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #f59e0b;">Root Causes Identified</h2>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:12px 16px;background:#fef3c7;border-left:3px solid #f59e0b;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#92400e;">1. Late Port Binding</p>
<p style="margin:0;font-size:13px;color:#4b5563;">Port 5000 was opened AFTER all middleware registration and FastAPI readiness checks, causing a 30&ndash;60 second delay before the health check could connect.</p>
</td>
</tr>
<tr><td style="height:8px;"></td></tr>
<tr>
<td style="padding:12px 16px;background:#fef3c7;border-left:3px solid #f59e0b;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#92400e;">2. Environment Variable Not Propagated</p>
<p style="margin:0;font-size:13px;color:#4b5563;">esbuild replaces <code>process.env.NODE_ENV</code> at compile time, so the actual environment variable was never set. When Node.js spawned the Python/FastAPI child process, it inherited no NODE_ENV, causing FastAPI to think it was in development mode and run all seeding operations.</p>
</td>
</tr>
</table>

<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #16a34a;">Fixes Applied</h2>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:12px 16px;background:#f0fdf4;border-left:3px solid #16a34a;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#15803d;">Instant Port Binding</p>
<p style="margin:0;font-size:13px;color:#4b5563;">Port 5000 now opens immediately after server creation, before ANY middleware, proxy setup, or FastAPI spawn. Health checks can respond within milliseconds of process start.</p>
</td>
</tr>
<tr><td style="height:8px;"></td></tr>
<tr>
<td style="padding:12px 16px;background:#f0fdf4;border-left:3px solid #16a34a;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#15803d;">Environment Variable Propagation</p>
<p style="margin:0;font-size:13px;color:#4b5563;">The FastAPI child process now explicitly receives NODE_ENV and ENVIRONMENT variables matching the Node.js production setting. FastAPI correctly detects production mode and skips all seeding/migration operations.</p>
</td>
</tr>
<tr><td style="height:8px;"></td></tr>
<tr>
<td style="padding:12px 16px;background:#f0fdf4;border-left:3px solid #16a34a;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#15803d;">Reduced Wait Timeout</p>
<p style="margin:0;font-size:13px;color:#4b5563;">FastAPI readiness check changed from 60 retries at 3s to 30 retries at 2s, running fully asynchronously without blocking any request handling.</p>
</td>
</tr>
<tr><td style="height:8px;"></td></tr>
<tr>
<td style="padding:12px 16px;background:#f0fdf4;border-left:3px solid #16a34a;border-radius:0 6px 6px 0;">
<p style="margin:0 0 4px;font-weight:700;font-size:14px;color:#15803d;">Production Database Flags</p>
<p style="margin:0;font-size:13px;color:#4b5563;">All four startup operations disabled in production: CREATE_SCHEMA, RUN_MIGRATIONS, SEED_BENCHMARKS, SEED_DEMO_DATA. ENVIRONMENT=production is also explicitly set.</p>
</td>
</tr>
</table>

<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #6366f1;">Result</h2>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:14px 16px;background:#f0fdf4;border-left:3px solid #16a34a;border-radius:0 6px 6px 0;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:13px;color:#15803d;font-weight:600;">
<tr><td style="padding:3px 0;">Port 5000 opens within milliseconds of process start</td></tr>
<tr><td style="padding:3px 0;">FastAPI starts in background without blocking requests</td></tr>
<tr><td style="padding:3px 0;">Health checks pass immediately</td></tr>
<tr><td style="padding:3px 0;">No database seeding or migration on production deploy</td></tr>
<tr><td style="padding:3px 0;">API requests proxy to FastAPI as soon as it becomes available</td></tr>
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
    sender = "Nikita from FounderConsole <kavibe8@founderconsole.ai>"

    print(f"Sending deployment fix update v25 to {len(RECIPIENTS)} recipients...")
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
            "List-Unsubscribe": "<mailto:kavibe8@founderconsole.ai?subject=unsubscribe>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
            "Precedence": "bulk",
        }

        utm_params = {
            "utm_source": "email",
            "utm_medium": "transactional",
            "utm_campaign": CAMPAIGN,
            "utm_content": rid,
        }

        result = _send_email_sync(
            to=email,
            subject="Update: Deployment Stability Fix - Instant Port Binding & Environment Detection",
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
