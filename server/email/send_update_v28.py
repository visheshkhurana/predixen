"""
Send update email v28 - Multi-LLM Routing, Board Deck Redesign, AI Graphics Studio & Security Hardening.
Sender: noreply@founderconsole.ai
"""
import os, sys, time, uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from server.email.service import _send_email_sync
from server.api.email_tracking import create_tracked_link

CAMPAIGN = "founderconsole_48hr_update_mar2026_v28b"

BASE_URL = "https://fund-flow.replit.app"

RECIPIENTS = [
    {"email": "nikita.luther@gmail.com", "id": "nikita_luther", "name": "Nikita"},
    {"email": "nikita@predixen.ai", "id": "nikita_predixen", "name": "Nikita"},
    {"email": "nikitafl2024@gmail.com", "id": "nikita_fl2024", "name": "Nikita"},
]


def build_plain_text(rcpt: dict) -> str:
    return f"""Hi {rcpt['name']},

Here's a summary of everything completed on FounderConsole in the last 48 hours.

---

1. MULTI-LLM INTELLIGENT ROUTING (P0)

FounderConsole now routes every AI request to the optimal model based on task type:
- Financial Analysis & Metrics -> GPT-4o (best at structured data)
- Strategy & Planning -> Claude Sonnet (balanced reasoning)
- Complex Reasoning & Coding -> Claude Opus (deepest reasoning)
- General Chat & Quick Tasks -> Gemini Flash (fastest, most cost-effective)
- Web Search & Real-Time Data -> Perplexity Sonar (web-grounded with citations)
- Market Research -> Perplexity Sonar Reasoning Pro (step-by-step analysis)
- Competitor Analysis -> Perplexity Sonar Pro (detailed research)
- News & Current Events -> Grok 4.1 Fast via OpenRouter (real-time, 2M context)
- Image Generation -> gpt-image-1 (professional graphics)
- Creative Writing & Document Analysis -> Claude Sonnet

All 8 provider/task-type routing tests pass. Fallback chains ensure resilience if any provider is unavailable.

---

2. BOARD DECK EXPORT REDESIGN (P0)

The board deck export has been completely rebuilt with professional presentation design:

Preview Modal (in-app):
- Interactive Recharts area/bar charts for Revenue, MRR, Burn, and Cash Balance trends
- Circular SVG progress rings for Monte Carlo P10/P50/P90 runway and survival probability
- Styled metric cards with colored top borders, large bold values, and trend deltas
- Scenario comparison cards with progress bars and detailed metrics
- AI narrative sections in styled containers with left border accents
- Color-coded model badges showing which AI generated each section (Claude=amber, GPT-4o=green, Gemini=indigo)
- Gradient download buttons and slide-type icons

PDF Export:
- Stunning gradient cover slide (indigo->purple->cyan) with company branding
- Inline SVG line/area/bar/gauge/donut charts that render in print without JavaScript
- Professional metric cards with colored top borders and shadows
- Scenario comparison cards with progress bars
- Consistent header/footer with FC branding, model badges, and slide counter
- Print-optimized with exact color adjustment for gradients

---

3. BOARD DECK SMART LLM ROUTING (P1)

Board deck sections now route to the optimal AI model based on content type:
- Executive Summary & Vision -> Claude Sonnet (creative writing)
- Strategy & Recommendations -> Claude Sonnet (strategic reasoning)
- Financial Metrics & Projections -> GPT-4o (structured data analysis)
- Monte Carlo & Simulations -> GPT-4o (financial analysis)
- Quick summaries -> Gemini Flash (fast, cost-effective)

Each section displays the model that generated it via color-coded badges.

---

4. AI GRAPHICS STUDIO (P1)

New standalone page at /ai-graphics for generating professional AI graphics:
- Text prompt input with 5 style presets (Professional, Infographic, Chart, Illustration, Minimal)
- 4 aspect ratio options (1:1, 16:9, 4:3, 9:16)
- AI-suggested graphics based on company metrics (Growth trajectory, Market positioning, etc.)
- Session gallery of generated images with download capability
- Also integrated into board deck export via "Generate Graphic" endpoint

Backend: server/api/ai_graphics.py (generate, styles, suggestions endpoints)
Frontend: client/src/pages/ai-graphics.tsx

---

5. SECURITY HARDENING - HTML INJECTION FIX (P0)

All dynamic text in the PDF generator is now HTML-escaped before interpolation:
- Company name in cover slide, headers, and page title
- Slide titles, metric labels, metric values, delta indicators
- Scenario names and descriptions
- Model badge display names
- Added escHtml() utility function for consistent sanitization

This prevents potential XSS if company names or metric labels contain special characters.

---

6. ZERO-VALUE CHART DATA FIX (P1)

Fixed a bug in PreviewModal.tsx where chart data points with value 0 were being dropped:
- Changed `if (fr.revenue)` to `if (fr.revenue != null)` for all metric fields
- Zero-value data points (revenue, MRR, net_burn, cash_balance) now correctly appear in charts
- Prevents misleading gaps in trend visualizations

---

7. LLM USAGE DASHBOARD ENDPOINT (P1)

New API endpoint at /api/companies/{id}/llm-usage:
- Returns usage stats grouped by model, provider, and task type
- Aggregates total calls, tokens used, and average latency
- Time range filtering (last 7 days, 30 days, all time)
- Data sourced from llm_audit_logs table

---

8. INFRASTRUCTURE

- Perplexity client defaults updated from deprecated sonar-small to sonar
- Model descriptions updated for sonar/sonar-pro/sonar-reasoning-pro/sonar-deep-research
- OpenRouter client for Grok models with proper fallback chains
- 440+ total routes registered across all modules
- Application running stable with no errors

---

All changes are live in development. The application is running stable with all routes registered and no errors.

--
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

<p>Here&rsquo;s a summary of everything completed on FounderConsole in the last 48 hours.</p>

<!-- 1. Multi-LLM Routing -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #6366f1;">1. Multi-LLM Intelligent Routing (P0)</h2>

<p style="font-size:13px;color:#4b5563;margin:0 0 12px;">Every AI request now routes to the optimal model based on task type. Full classifier-based routing with automatic fallback chains.</p>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:14px 16px;background:#eef2ff;border-left:3px solid #6366f1;border-radius:0 6px 6px 0;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:13px;color:#4b5563;">
<tr><td style="padding:3px 0;"><strong>Financial Analysis &amp; Metrics</strong> &rarr; GPT-4o (best at structured data)</td></tr>
<tr><td style="padding:3px 0;"><strong>Strategy &amp; Planning</strong> &rarr; Claude Sonnet (balanced reasoning)</td></tr>
<tr><td style="padding:3px 0;"><strong>Complex Reasoning &amp; Coding</strong> &rarr; Claude Opus (deepest reasoning)</td></tr>
<tr><td style="padding:3px 0;"><strong>General Chat &amp; Quick Tasks</strong> &rarr; Gemini Flash (fastest)</td></tr>
<tr><td style="padding:3px 0;"><strong>Web Search &amp; Real-Time Data</strong> &rarr; Perplexity Sonar (citations)</td></tr>
<tr><td style="padding:3px 0;"><strong>Market Research</strong> &rarr; Perplexity Sonar Reasoning Pro</td></tr>
<tr><td style="padding:3px 0;"><strong>News &amp; Current Events</strong> &rarr; Grok 4.1 Fast via OpenRouter</td></tr>
<tr><td style="padding:3px 0;"><strong>Image Generation</strong> &rarr; gpt-image-1</td></tr>
<tr><td style="padding:3px 0;"><strong>Creative Writing &amp; Docs</strong> &rarr; Claude Sonnet</td></tr>
</table>
</td>
</tr>
</table>

<!-- 2. Board Deck Redesign -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #0ea5e9;">2. Board Deck Export Redesign (P0)</h2>

<p style="font-size:13px;color:#4b5563;margin:0 0 8px;">Complete rebuild of the board deck preview and PDF export with professional presentation design.</p>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:14px 16px;background:#f0f9ff;border-left:3px solid #0ea5e9;border-radius:0 6px 6px 0;">
<p style="margin:0 0 8px;font-weight:700;font-size:14px;color:#0369a1;">Preview Modal (In-App)</p>
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:13px;color:#4b5563;">
<tr><td style="padding:3px 0;">Interactive Recharts area/bar charts for Revenue, MRR, Burn, Cash Balance</td></tr>
<tr><td style="padding:3px 0;">Circular SVG progress rings for Monte Carlo P10/P50/P90 runway</td></tr>
<tr><td style="padding:3px 0;">Styled metric cards with colored top borders and trend deltas</td></tr>
<tr><td style="padding:3px 0;">Color-coded model badges (Claude=amber, GPT-4o=green, Gemini=indigo)</td></tr>
<tr><td style="padding:3px 0;">Gradient download buttons and slide-type icons</td></tr>
</table>
</td>
</tr>
</table>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:14px 16px;background:#faf5ff;border-left:3px solid #8b5cf6;border-radius:0 6px 6px 0;">
<p style="margin:0 0 8px;font-weight:700;font-size:14px;color:#7c3aed;">PDF Export</p>
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:13px;color:#4b5563;">
<tr><td style="padding:3px 0;">Gradient cover slide (indigo&rarr;purple&rarr;cyan) with company branding</td></tr>
<tr><td style="padding:3px 0;">Inline SVG line/area/bar/gauge/donut charts (no JavaScript needed)</td></tr>
<tr><td style="padding:3px 0;">Professional metric cards with shadows and colored borders</td></tr>
<tr><td style="padding:3px 0;">Scenario comparison cards with progress bars</td></tr>
<tr><td style="padding:3px 0;">Print-optimized with exact color adjustment for gradients</td></tr>
</table>
</td>
</tr>
</table>

<!-- 3. Board Deck Smart Routing -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #f59e0b;">3. Board Deck Smart LLM Routing (P1)</h2>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:14px 16px;background:#fffbeb;border-left:3px solid #f59e0b;border-radius:0 6px 6px 0;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:13px;color:#4b5563;">
<tr><td style="padding:3px 0;"><strong>Executive Summary &amp; Vision</strong> &rarr; Claude Sonnet (creative writing)</td></tr>
<tr><td style="padding:3px 0;"><strong>Strategy &amp; Recommendations</strong> &rarr; Claude Sonnet (strategic reasoning)</td></tr>
<tr><td style="padding:3px 0;"><strong>Financial Metrics &amp; Projections</strong> &rarr; GPT-4o (structured data)</td></tr>
<tr><td style="padding:3px 0;"><strong>Monte Carlo &amp; Simulations</strong> &rarr; GPT-4o (financial analysis)</td></tr>
<tr><td style="padding:3px 0;"><strong>Quick Summaries</strong> &rarr; Gemini Flash (fast, cost-effective)</td></tr>
</table>
<p style="margin:8px 0 0;font-size:12px;color:#92400e;">Each section displays the model that generated it via color-coded badges.</p>
</td>
</tr>
</table>

<!-- 4. AI Graphics Studio -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #ec4899;">4. AI Graphics Studio (P1)</h2>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:14px 16px;background:#fdf2f8;border-left:3px solid #ec4899;border-radius:0 6px 6px 0;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:13px;color:#4b5563;">
<tr><td style="padding:3px 0;">New standalone page at <strong>/ai-graphics</strong> for generating professional AI graphics</td></tr>
<tr><td style="padding:3px 0;">5 style presets: Professional, Infographic, Chart, Illustration, Minimal</td></tr>
<tr><td style="padding:3px 0;">4 aspect ratios: 1:1, 16:9, 4:3, 9:16</td></tr>
<tr><td style="padding:3px 0;">AI-suggested graphics based on company metrics</td></tr>
<tr><td style="padding:3px 0;">Session gallery with download capability</td></tr>
<tr><td style="padding:3px 0;">Also integrated into board deck export via generate-graphic endpoint</td></tr>
</table>
</td>
</tr>
</table>

<!-- 5. Security -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #dc2626;">5. Security Hardening &mdash; HTML Injection Fix (P0)</h2>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:12px 16px;background:#fef2f2;border-left:3px solid #dc2626;border-radius:0 6px 6px 0;">
<p style="margin:0;font-size:13px;color:#4b5563;">All dynamic text in the PDF generator is now HTML-escaped before interpolation &mdash; company names, slide titles, metric labels/values, scenario names, model badges, and delta indicators. Prevents potential XSS from special characters in user data. Added <code style="background:#fee2e2;padding:1px 4px;border-radius:3px;font-size:12px;">escHtml()</code> utility for consistent sanitization.</p>
</td>
</tr>
</table>

<!-- 6. Zero-Value Fix -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #16a34a;">6. Zero-Value Chart Data Fix (P1)</h2>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:12px 16px;background:#f0fdf4;border-left:3px solid #16a34a;border-radius:0 6px 6px 0;">
<p style="margin:0;font-size:13px;color:#4b5563;">Fixed bug where chart data points with value 0 were being dropped (<code style="background:#dcfce7;padding:1px 4px;border-radius:3px;font-size:12px;">if (fr.revenue)</code> &rarr; <code style="background:#dcfce7;padding:1px 4px;border-radius:3px;font-size:12px;">if (fr.revenue != null)</code>). Zero-value data points now correctly appear in trend visualizations without misleading gaps.</p>
</td>
</tr>
</table>

<!-- 7. LLM Usage -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #8b5cf6;">7. LLM Usage Dashboard Endpoint (P1)</h2>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:12px 16px;background:#f5f3ff;border-left:3px solid #8b5cf6;border-radius:0 6px 6px 0;">
<p style="margin:0;font-size:13px;color:#4b5563;">New API endpoint at <code style="background:#ede9fe;padding:1px 4px;border-radius:3px;font-size:12px;">/api/companies/&#123;id&#125;/llm-usage</code> returns usage stats by model/provider/task type, with total calls, tokens, average latency, and time range filtering (7d, 30d, all).</p>
</td>
</tr>
</table>

<!-- 8. Infrastructure -->
<h2 style="font-size:17px;color:#1e1b4b;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid #64748b;">8. Infrastructure</h2>

<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0;">
<tr>
<td style="padding:14px 16px;background:#f8fafc;border-left:3px solid #64748b;border-radius:0 6px 6px 0;">
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="font-size:13px;color:#4b5563;">
<tr><td style="padding:3px 0;">Perplexity client defaults updated from deprecated sonar-small to sonar.</td></tr>
<tr><td style="padding:3px 0;">Model descriptions updated for sonar/sonar-pro/sonar-reasoning-pro/sonar-deep-research.</td></tr>
<tr><td style="padding:3px 0;">OpenRouter client for Grok models with proper fallback chains.</td></tr>
<tr><td style="padding:3px 0;"><strong>440+ total routes</strong> registered across all modules.</td></tr>
<tr><td style="padding:3px 0;">Application running stable with no errors.</td></tr>
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
<img src="{open_tracking_url}" width="1" height="1" style="display:none" alt="" />
</body>
</html>"""


def send_all():
    sender = "Nikita from FounderConsole <nikita@founderconsole.ai>"

    print(f"Sending 48-hour task update v28 to {len(RECIPIENTS)} recipients...")
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
            subject="48-Hour Update: Multi-LLM Routing, Board Deck Redesign, AI Graphics Studio & Security Hardening",
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
