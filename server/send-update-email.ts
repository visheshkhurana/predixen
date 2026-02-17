// One-time script to send v1.0.1 Decisions page UI enhancement update email via Resend integration
import { Resend } from 'resend';

async function getCredentials() {
  const hostname = process.env.REPLIT_CONNECTORS_HOSTNAME;
  const xReplitToken = process.env.REPL_IDENTITY
    ? 'repl ' + process.env.REPL_IDENTITY
    : process.env.WEB_REPL_RENEWAL
    ? 'depl ' + process.env.WEB_REPL_RENEWAL
    : null;

  if (!xReplitToken) {
    throw new Error('X_REPLIT_TOKEN not found');
  }

  const res = await fetch(
    'https://' + hostname + '/api/v2/connection?include_secrets=true&connector_names=resend',
    {
      headers: {
        'Accept': 'application/json',
        'X_REPLIT_TOKEN': xReplitToken
      }
    }
  );
  const data = await res.json();
  const connectionSettings = data.items?.[0];

  if (!connectionSettings || !connectionSettings.settings.api_key) {
    throw new Error('Resend not connected. Response: ' + JSON.stringify(data));
  }
  return {
    apiKey: connectionSettings.settings.api_key,
  };
}

async function sendUpdateEmails() {
  console.log('Fetching Resend credentials...');
  const { apiKey } = await getCredentials();

  const resend = new Resend(apiKey);

  const recipients = [
    'nikita@founderconsole.ai',
    'nikita.luther@gmail.com',
    'nikitafl2024@gmail.com',
    'vysheshk@gmail.com'
  ];

  const senderEmail = 'FounderConsole Updates <new1@founderconsole.ai>';
  const subject = 'FounderConsole v1.0.1: Decisions Page UI Enhancements — Why We Made These Changes';
  const htmlContent = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background-color:#0f172a;font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f172a;padding:40px 20px;">
    <tr>
      <td align="center">
        <table width="640" cellpadding="0" cellspacing="0" style="background-color:#1e293b;border-radius:12px;overflow:hidden;">

          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#6366f1,#8b5cf6);padding:40px 40px 30px;">
              <h1 style="margin:0;color:#ffffff;font-size:26px;font-weight:700;">FounderConsole</h1>
              <p style="margin:8px 0 0;color:#c7d2fe;font-size:13px;letter-spacing:1px;">v1.0.1 UI ENHANCEMENT UPDATE &mdash; FEBRUARY 2026</p>
            </td>
          </tr>

          <!-- Intro -->
          <tr>
            <td style="padding:40px 40px 0;">
              <p style="margin:0 0 20px;color:#e2e8f0;font-size:16px;line-height:1.7;font-weight:600;">
                What changed &amp; why we did it
              </p>
              <p style="margin:0 0 20px;color:#94a3b8;font-size:15px;line-height:1.7;">
                The Decisions page is the most important screen in FounderConsole &mdash; it's the founder's strategic briefing document. After shipping v1.0.0 with the core narrative structure, we focused this sprint on making the reading experience feel as polished and professional as the content itself. Here's what we improved and the reasoning behind each change.
              </p>
            </td>
          </tr>

          <!-- CHANGE 1: Sticky TOC -->
          <tr>
            <td style="padding:24px 40px 0;">
              <h2 style="margin:0 0 16px;color:#f1f5f9;font-size:20px;font-weight:600;border-bottom:2px solid #6366f1;padding-bottom:8px;">1. Sticky Table of Contents with Active Indicator</h2>
            </td>
          </tr>
          <tr>
            <td style="padding:0 40px 16px;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f172a;border-radius:10px;">
                <tr>
                  <td style="padding:20px;">
                    <p style="margin:0 0 12px;color:#818cf8;font-size:12px;font-weight:700;text-transform:uppercase;">What Changed</p>
                    <p style="margin:0 0 12px;color:#94a3b8;font-size:13px;line-height:1.6;">
                      The TOC sidebar now has a frosted-glass card background with a subtle border. Each section gets a small circle marker on a vertical progress line. The active section is highlighted with a filled primary-color dot and a vertical accent bar, with smooth CSS transitions between sections.
                    </p>
                    <p style="margin:0 0 12px;color:#818cf8;font-size:12px;font-weight:700;text-transform:uppercase;">Why We Did It</p>
                    <p style="margin:0;color:#94a3b8;font-size:13px;line-height:1.6;">
                      The strategic briefing is a <strong style="color:#e2e8f0;">long document with 5+ sections</strong>. Without clear wayfinding, founders lose context on where they are in the document. The progress-line metaphor communicates "you're on step 3 of 5" at a glance without requiring any reading. The frosted card gives the TOC visual weight so it's discoverable but not distracting. We also switched from hardcoded pixel positioning to CSS-relative alignment so the indicator works correctly at any font size or zoom level.
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- CHANGE 2: Loading Progress -->
          <tr>
            <td style="padding:24px 40px 0;">
              <h2 style="margin:0 0 16px;color:#f1f5f9;font-size:20px;font-weight:600;border-bottom:2px solid #22c55e;padding-bottom:8px;">2. Animated Loading with Gradient Progress Bar</h2>
            </td>
          </tr>
          <tr>
            <td style="padding:0 40px 16px;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f172a;border-radius:10px;">
                <tr>
                  <td style="padding:20px;">
                    <p style="margin:0 0 12px;color:#818cf8;font-size:12px;font-weight:700;text-transform:uppercase;">What Changed</p>
                    <p style="margin:0 0 12px;color:#94a3b8;font-size:13px;line-height:1.6;">
                      When the AI generates a strategic briefing, the loading state now shows: a gradient progress bar (indigo &rarr; violet) that smoothly fills to 100%, a pulsing brain icon with a gradient ring, completed steps marked with green checkmarks instead of dots, and each step slides in with a fade animation. The bar reaches exactly 100% when all steps finish.
                    </p>
                    <p style="margin:0 0 12px;color:#818cf8;font-size:12px;font-weight:700;text-transform:uppercase;">Why We Did It</p>
                    <p style="margin:0;color:#94a3b8;font-size:13px;line-height:1.6;">
                      The v1.0.0 loading state was functional but felt cheap &mdash; just text and dots. For a platform that charges for AI-powered analysis, <strong style="color:#e2e8f0;">the loading experience IS part of the product</strong>. A smooth progress bar signals "real work is happening" rather than "are we stuck?" The checkmarks on completed steps give confidence that the system isn't frozen. Previously the bar capped at 90% which felt like it got stuck &mdash; now it cleanly reaches 100% on completion.
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- CHANGE 3: Section Dividers -->
          <tr>
            <td style="padding:24px 40px 0;">
              <h2 style="margin:0 0 16px;color:#f1f5f9;font-size:20px;font-weight:600;border-bottom:2px solid #f59e0b;padding-bottom:8px;">3. Numbered Section Dividers with Gradient Accents</h2>
            </td>
          </tr>
          <tr>
            <td style="padding:0 40px 16px;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f172a;border-radius:10px;">
                <tr>
                  <td style="padding:20px;">
                    <p style="margin:0 0 12px;color:#818cf8;font-size:12px;font-weight:700;text-transform:uppercase;">What Changed</p>
                    <p style="margin:0 0 12px;color:#94a3b8;font-size:13px;line-height:1.6;">
                      Each section of the briefing now starts with a numbered circle (primary color) followed by an uppercase label and a gradient line that fades from the border color to transparent. Section spacing increased from 40px to 48px.
                    </p>
                    <p style="margin:0 0 12px;color:#818cf8;font-size:12px;font-weight:700;text-transform:uppercase;">Why We Did It</p>
                    <p style="margin:0;color:#94a3b8;font-size:13px;line-height:1.6;">
                      The briefing reads like a document, not a dashboard. Good documents have clear section breaks. The numbered circles serve two purposes: they <strong style="color:#e2e8f0;">match the TOC sidebar</strong> (so when you click "Section 3" in the TOC, you visually land on a circle labeled "3") and they give the document a <strong style="color:#e2e8f0;">structured, professional feel</strong> &mdash; like a McKinsey deck or board memo. The gradient fade-out line is more elegant than a hard border and prevents the sections from feeling boxy.
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- CHANGE 4: Code Quality -->
          <tr>
            <td style="padding:24px 40px 0;">
              <h2 style="margin:0 0 16px;color:#f1f5f9;font-size:20px;font-weight:600;border-bottom:2px solid #64748b;padding-bottom:8px;">4. Under-the-Hood Improvements</h2>
            </td>
          </tr>
          <tr>
            <td style="padding:0 40px 16px;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f172a;border-radius:10px;">
                <tr>
                  <td style="padding:20px;">
                    <p style="margin:0;color:#94a3b8;font-size:13px;line-height:1.8;">
                      <span style="color:#e2e8f0;font-weight:600;">Removed unused imports</span> &mdash; cleaned up dead code (useRef) to keep the bundle lean.<br/>
                      <span style="color:#e2e8f0;font-weight:600;">Fixed layout compliance</span> &mdash; all flex containers with justify-between now include gap classes to prevent element overlap on smaller screens.<br/>
                      <span style="color:#e2e8f0;font-weight:600;">Hover states standardized</span> &mdash; replaced custom group-hover CSS with the platform's built-in hover-elevate utility for consistent interaction patterns across the app.<br/>
                      <span style="color:#e2e8f0;font-weight:600;">Responsive TOC positioning</span> &mdash; active indicator now uses CSS-relative positioning instead of hardcoded pixel offsets, so it works correctly at any font size, zoom level, or browser setting.
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Summary -->
          <tr>
            <td style="padding:24px 40px 0;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background:linear-gradient(135deg,#312e81,#4c1d95);border-radius:10px;">
                <tr>
                  <td style="padding:24px;">
                    <p style="margin:0 0 8px;color:#c7d2fe;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:1px;">The Bottom Line</p>
                    <p style="margin:0;color:#e2e8f0;font-size:14px;line-height:1.7;">
                      These changes make the Decisions page feel like a <strong style="color:#ffffff;">polished advisory document</strong> rather than a raw data dump. Every interaction &mdash; scrolling, waiting for AI, navigating between sections &mdash; now has visual feedback that builds trust. The strategic briefing is the product's most differentiated feature, and it now looks the part.
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- CTA -->
          <tr>
            <td style="padding:32px 40px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center">
                    <a href="https://founderconsole.ai" style="display:inline-block;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#ffffff;font-size:15px;font-weight:600;text-decoration:none;padding:14px 36px;border-radius:8px;">
                      See It Live
                    </a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color:#0f172a;padding:24px 40px;">
              <p style="margin:0;color:#475569;font-size:11px;text-align:center;line-height:1.6;">
                FounderConsole &mdash; AI-Powered Financial Intelligence for Startups<br/>
                This is an automated product update. Reply to share feedback.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
`;

  console.log(`Sending to ${recipients.length} recipients from ${senderEmail}...`);

  for (let i = 0; i < recipients.length; i++) {
    const to = recipients[i];
    if (i > 0) await new Promise(r => setTimeout(r, 1500));
    try {
      const result = await resend.emails.send({
        from: senderEmail,
        to,
        subject,
        html: htmlContent,
      });
      console.log(`Sent to ${to}:`, result);
    } catch (err: any) {
      console.error(`Failed to send to ${to}:`, err?.message || err);
    }
  }

  console.log('Done.');
}

sendUpdateEmails().catch(console.error);
