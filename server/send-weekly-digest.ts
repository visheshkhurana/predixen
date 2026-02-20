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

async function sendWeeklyDigest() {
  console.log('Fetching Resend credentials...');
  const { apiKey } = await getCredentials();

  const resend = new Resend(apiKey);

  const recipients = [
    'nikita@founderconsole.ai',
    'nikita.luther@gmail.com',
    'nikitafl2024@gmail.com',
    'vysheshk@gmail.com'
  ];

  const senderEmail = 'FounderConsole Weekly <hello@founderconsole.ai>';
  const subject = 'FounderConsole Weekly Digest — Feb 8-14, 2026: 5 Bug Fixes, 4 New Features, 3 UI Upgrades';
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
            <td style="background:linear-gradient(135deg,#6366f1,#8b5cf6,#a855f7);padding:40px 40px 30px;">
              <p style="margin:0 0 4px;color:#c7d2fe;font-size:11px;letter-spacing:2px;text-transform:uppercase;font-weight:600;">Weekly Digest</p>
              <h1 style="margin:0;color:#ffffff;font-size:28px;font-weight:700;">FounderConsole</h1>
              <p style="margin:10px 0 0;color:#e0e7ff;font-size:14px;">Week of February 8&ndash;14, 2026</p>
            </td>
          </tr>

          <!-- Summary Stats Bar -->
          <tr>
            <td style="padding:0;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#1e1b4b;">
                <tr>
                  <td width="33%" align="center" style="padding:16px 0;border-right:1px solid #312e81;">
                    <p style="margin:0;color:#ef4444;font-size:24px;font-weight:700;">5</p>
                    <p style="margin:2px 0 0;color:#94a3b8;font-size:11px;text-transform:uppercase;letter-spacing:1px;">Bugs Fixed</p>
                  </td>
                  <td width="33%" align="center" style="padding:16px 0;border-right:1px solid #312e81;">
                    <p style="margin:0;color:#22c55e;font-size:24px;font-weight:700;">4</p>
                    <p style="margin:2px 0 0;color:#94a3b8;font-size:11px;text-transform:uppercase;letter-spacing:1px;">New Features</p>
                  </td>
                  <td width="34%" align="center" style="padding:16px 0;">
                    <p style="margin:0;color:#818cf8;font-size:24px;font-weight:700;">3</p>
                    <p style="margin:2px 0 0;color:#94a3b8;font-size:11px;text-transform:uppercase;letter-spacing:1px;">UI Upgrades</p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ===================== BUG FIXES ===================== -->
          <tr>
            <td style="padding:32px 40px 0;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td width="10" style="background-color:#ef4444;border-radius:4px;">&nbsp;</td>
                  <td style="padding-left:16px;">
                    <h2 style="margin:0;color:#f1f5f9;font-size:20px;font-weight:700;">Bug Fixes</h2>
                    <p style="margin:4px 0 0;color:#64748b;font-size:12px;">Critical issues resolved from founder beta feedback</p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Bug 1 -->
          <tr>
            <td style="padding:16px 40px 0;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f172a;border-radius:10px;">
                <tr>
                  <td style="padding:16px 20px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td>
                          <span style="display:inline-block;background-color:#7f1d1d;color:#fca5a5;font-size:10px;font-weight:700;padding:3px 8px;border-radius:4px;text-transform:uppercase;vertical-align:middle;">Critical</span>
                          <span style="color:#f1f5f9;font-size:14px;font-weight:600;margin-left:10px;vertical-align:middle;">Strategic Briefing Infinite Loading</span>
                        </td>
                      </tr>
                      <tr>
                        <td style="padding-top:8px;">
                          <p style="margin:0;color:#94a3b8;font-size:13px;line-height:1.6;">
                            The Decisions page would get stuck in a perpetual loading state with no recovery path. Added a 30-second timeout with automatic error detection, clear error messaging, and a one-click retry button. Loading animation now shows real-time progress stages.
                          </p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Bug 2 -->
          <tr>
            <td style="padding:12px 40px 0;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f172a;border-radius:10px;">
                <tr>
                  <td style="padding:16px 20px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td>
                          <span style="display:inline-block;background-color:#7f1d1d;color:#fca5a5;font-size:10px;font-weight:700;padding:3px 8px;border-radius:4px;text-transform:uppercase;vertical-align:middle;">Critical</span>
                          <span style="color:#f1f5f9;font-size:14px;font-weight:600;margin-left:10px;vertical-align:middle;">Data Inconsistency Across Pages</span>
                        </td>
                      </tr>
                      <tr>
                        <td style="padding-top:8px;">
                          <p style="margin:0;color:#94a3b8;font-size:13px;line-height:1.6;">
                            Dashboard, Overview, and Scenarios pages each calculated financial metrics independently, showing different numbers for the same metric. Built a centralized <code style="color:#818cf8;background:#1e293b;padding:2px 4px;border-radius:3px;">useFinancialMetrics</code> hook as the single source of truth. MRR, ARR, runway, burn rate, and 15+ metrics are now always consistent across every page.
                          </p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Bug 3 -->
          <tr>
            <td style="padding:12px 40px 0;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f172a;border-radius:10px;">
                <tr>
                  <td style="padding:16px 20px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td>
                          <span style="display:inline-block;background-color:#7f1d1d;color:#fca5a5;font-size:10px;font-weight:700;padding:3px 8px;border-radius:4px;text-transform:uppercase;vertical-align:middle;">Critical</span>
                          <span style="color:#f1f5f9;font-size:14px;font-weight:600;margin-left:10px;vertical-align:middle;">Missing Industry Categories &amp; Stages</span>
                        </td>
                      </tr>
                      <tr>
                        <td style="padding-top:8px;">
                          <p style="margin:0;color:#94a3b8;font-size:13px;line-height:1.6;">
                            Onboarding only supported 5 industries and 4 stages, excluding most non-SaaS companies. Expanded to <strong style="color:#e2e8f0;">15 industry categories</strong> (D2C, Healthcare, EdTech, AgriTech, DeepTech, Climate, Media, Logistics, Real Estate, Food) and <strong style="color:#e2e8f0;">8 company stages</strong> (adding Pre-Series A, Growth, Pre-IPO, Public).
                          </p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Bug 4 -->
          <tr>
            <td style="padding:12px 40px 0;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f172a;border-radius:10px;">
                <tr>
                  <td style="padding:16px 20px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td>
                          <span style="display:inline-block;background-color:#78350f;color:#fcd34d;font-size:10px;font-weight:700;padding:3px 8px;border-radius:4px;text-transform:uppercase;vertical-align:middle;">Fix</span>
                          <span style="color:#f1f5f9;font-size:14px;font-weight:600;margin-left:10px;vertical-align:middle;">No Metric Source Attribution</span>
                        </td>
                      </tr>
                      <tr>
                        <td style="padding-top:8px;">
                          <p style="margin:0;color:#94a3b8;font-size:13px;line-height:1.6;">
                            Founders couldn't tell which metrics were real data vs. AI-inferred. Added provenance tracking &mdash; every metric now shows <span style="color:#fcd34d;font-weight:600;">"AI Est."</span> for estimated values and <span style="color:#60a5fa;font-weight:600;">"Derived"</span> for computed values, with full source attribution (reported / computed / estimated).
                          </p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Bug 5 -->
          <tr>
            <td style="padding:12px 40px 0;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f172a;border-radius:10px;">
                <tr>
                  <td style="padding:16px 20px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td>
                          <span style="display:inline-block;background-color:#78350f;color:#fcd34d;font-size:10px;font-weight:700;padding:3px 8px;border-radius:4px;text-transform:uppercase;vertical-align:middle;">Fix</span>
                          <span style="color:#f1f5f9;font-size:14px;font-weight:600;margin-left:10px;vertical-align:middle;">US-Centric Currency Default</span>
                        </td>
                      </tr>
                      <tr>
                        <td style="padding-top:8px;">
                          <p style="margin:0;color:#94a3b8;font-size:13px;line-height:1.6;">
                            Previously hardcoded to USD everywhere. Now auto-detects currency from company website TLD during onboarding (e.g., .in &rarr; INR, .co.uk &rarr; GBP, .jp &rarr; JPY). Supports 25+ country TLD mappings with manual override.
                          </p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ===================== NEW FEATURES ===================== -->
          <tr>
            <td style="padding:32px 40px 0;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td width="10" style="background-color:#22c55e;border-radius:4px;">&nbsp;</td>
                  <td style="padding-left:16px;">
                    <h2 style="margin:0;color:#f1f5f9;font-size:20px;font-weight:700;">New Features</h2>
                    <p style="margin:4px 0 0;color:#64748b;font-size:12px;">Capabilities that didn't exist before this week</p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Feature 1 -->
          <tr>
            <td style="padding:16px 40px 0;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f172a;border-radius:10px;">
                <tr>
                  <td style="padding:16px 20px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td>
                          <span style="display:inline-block;background-color:#14532d;color:#86efac;font-size:10px;font-weight:700;padding:3px 8px;border-radius:4px;text-transform:uppercase;vertical-align:middle;">New</span>
                          <span style="color:#f1f5f9;font-size:14px;font-weight:600;margin-left:10px;vertical-align:middle;">Full Multi-Currency Support</span>
                        </td>
                      </tr>
                      <tr>
                        <td style="padding-top:8px;">
                          <p style="margin:0;color:#94a3b8;font-size:13px;line-height:1.6;">
                            Every financial figure &mdash; simulations, scenarios, KPIs, charts &mdash; now renders in the company's own currency. The <code style="color:#818cf8;background:#1e293b;padding:2px 4px;border-radius:3px;">useCurrency</code> hook provides consistent formatting for <strong style="color:#e2e8f0;">20 currencies</strong> (USD, EUR, GBP, INR, JPY, AUD, CAD, SGD, AED, BRL, and more). Abbreviations adapt automatically ($1.2M vs &#8377;1.2Cr vs &#165;120M).
                          </p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Feature 2 -->
          <tr>
            <td style="padding:12px 40px 0;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f172a;border-radius:10px;">
                <tr>
                  <td style="padding:16px 20px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td>
                          <span style="display:inline-block;background-color:#14532d;color:#86efac;font-size:10px;font-weight:700;padding:3px 8px;border-radius:4px;text-transform:uppercase;vertical-align:middle;">New</span>
                          <span style="color:#f1f5f9;font-size:14px;font-weight:600;margin-left:10px;vertical-align:middle;">Industry-Adaptive Terminology</span>
                        </td>
                      </tr>
                      <tr>
                        <td style="padding-top:8px;">
                          <p style="margin:0;color:#94a3b8;font-size:13px;line-height:1.6;">
                            The platform now speaks your industry's language. Healthcare sees "Patients" instead of "Customers," EdTech sees "Learners," Marketplace sees "GMV" instead of "Revenue." Covers <strong style="color:#e2e8f0;">11 industry verticals</strong> and adapts KPI labels, churn terminology, and revenue metrics throughout the dashboard.
                          </p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Feature 3 -->
          <tr>
            <td style="padding:12px 40px 0;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f172a;border-radius:10px;">
                <tr>
                  <td style="padding:16px 20px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td>
                          <span style="display:inline-block;background-color:#14532d;color:#86efac;font-size:10px;font-weight:700;padding:3px 8px;border-radius:4px;text-transform:uppercase;vertical-align:middle;">New</span>
                          <span style="color:#f1f5f9;font-size:14px;font-weight:600;margin-left:10px;vertical-align:middle;">Narrative Strategic Briefing (Decisions Page v2)</span>
                        </td>
                      </tr>
                      <tr>
                        <td style="padding-top:8px;">
                          <p style="margin:0;color:#94a3b8;font-size:13px;line-height:1.6;">
                            Complete redesign of the Decisions page into a text-based, narrative-driven "founder's briefing document." No charts or KPI cards &mdash; reads like a strategic memo. Five sections: The Situation, What We Recommend, What Happens If You Do Nothing, Key Risks &amp; Contingency Plans. AI generates consultant-grade prose using real company data.
                          </p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Feature 4 -->
          <tr>
            <td style="padding:12px 40px 0;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f172a;border-radius:10px;">
                <tr>
                  <td style="padding:16px 20px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td>
                          <span style="display:inline-block;background-color:#14532d;color:#86efac;font-size:10px;font-weight:700;padding:3px 8px;border-radius:4px;text-transform:uppercase;vertical-align:middle;">New</span>
                          <span style="color:#f1f5f9;font-size:14px;font-weight:600;margin-left:10px;vertical-align:middle;">Email Sharing of Strategic Briefings</span>
                        </td>
                      </tr>
                      <tr>
                        <td style="padding-top:8px;">
                          <p style="margin:0;color:#94a3b8;font-size:13px;line-height:1.6;">
                            Founders can now share individual sections of their strategic briefing (Situation, Recommendation, Inaction Risk, Risks) via email directly from the platform. Each shared section is formatted as a standalone advisory email with proper formatting and branding.
                          </p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ===================== UI UPGRADES ===================== -->
          <tr>
            <td style="padding:32px 40px 0;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td width="10" style="background-color:#818cf8;border-radius:4px;">&nbsp;</td>
                  <td style="padding-left:16px;">
                    <h2 style="margin:0;color:#f1f5f9;font-size:20px;font-weight:700;">UI Upgrades</h2>
                    <p style="margin:4px 0 0;color:#64748b;font-size:12px;">Visual polish and experience improvements</p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- UI 1 -->
          <tr>
            <td style="padding:16px 40px 0;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f172a;border-radius:10px;">
                <tr>
                  <td style="padding:16px 20px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td>
                          <span style="display:inline-block;background-color:#312e81;color:#a5b4fc;font-size:10px;font-weight:700;padding:3px 8px;border-radius:4px;text-transform:uppercase;vertical-align:middle;">Polish</span>
                          <span style="color:#f1f5f9;font-size:14px;font-weight:600;margin-left:10px;vertical-align:middle;">Sticky TOC with Active Indicator</span>
                        </td>
                      </tr>
                      <tr>
                        <td style="padding-top:8px;">
                          <p style="margin:0;color:#94a3b8;font-size:13px;line-height:1.6;">
                            Fixed-position table of contents with frosted-glass card background, vertical progress line with circle markers per section, and animated active indicator that highlights the current section as you scroll. CSS-relative positioning ensures accurate alignment at any zoom level.
                          </p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- UI 2 -->
          <tr>
            <td style="padding:12px 40px 0;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f172a;border-radius:10px;">
                <tr>
                  <td style="padding:16px 20px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td>
                          <span style="display:inline-block;background-color:#312e81;color:#a5b4fc;font-size:10px;font-weight:700;padding:3px 8px;border-radius:4px;text-transform:uppercase;vertical-align:middle;">Polish</span>
                          <span style="color:#f1f5f9;font-size:14px;font-weight:600;margin-left:10px;vertical-align:middle;">Animated Loading with Progress Bar</span>
                        </td>
                      </tr>
                      <tr>
                        <td style="padding-top:8px;">
                          <p style="margin:0;color:#94a3b8;font-size:13px;line-height:1.6;">
                            AI briefing generation now shows a gradient progress bar (indigo &rarr; violet) that smoothly fills to 100%, a pulsing brain icon with gradient ring, completed steps marked with green checkmarks, and slide-in fade animations for each step. Previously the bar capped at 90% &mdash; now it cleanly reaches 100%.
                          </p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- UI 3 -->
          <tr>
            <td style="padding:12px 40px 0;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f172a;border-radius:10px;">
                <tr>
                  <td style="padding:16px 20px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td>
                          <span style="display:inline-block;background-color:#312e81;color:#a5b4fc;font-size:10px;font-weight:700;padding:3px 8px;border-radius:4px;text-transform:uppercase;vertical-align:middle;">Polish</span>
                          <span style="color:#f1f5f9;font-size:14px;font-weight:600;margin-left:10px;vertical-align:middle;">Numbered Section Dividers</span>
                        </td>
                      </tr>
                      <tr>
                        <td style="padding-top:8px;">
                          <p style="margin:0;color:#94a3b8;font-size:13px;line-height:1.6;">
                            Each briefing section now starts with a numbered circle (matching the TOC) and a gradient fade-out line. Increased section spacing for better readability. The document now feels like a structured advisory memo rather than a data screen.
                          </p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ===================== TECHNICAL DETAILS ===================== -->
          <tr>
            <td style="padding:32px 40px 0;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td width="10" style="background-color:#475569;border-radius:4px;">&nbsp;</td>
                  <td style="padding-left:16px;">
                    <h2 style="margin:0;color:#f1f5f9;font-size:20px;font-weight:700;">Technical Summary</h2>
                    <p style="margin:4px 0 0;color:#64748b;font-size:12px;">For the engineering-minded</p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <tr>
            <td style="padding:16px 40px 0;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f172a;border-radius:10px;">
                <tr>
                  <td style="padding:20px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td width="50%" valign="top" style="padding-right:12px;">
                          <p style="margin:0 0 8px;color:#818cf8;font-size:11px;font-weight:700;text-transform:uppercase;">New Hooks</p>
                          <p style="margin:0;color:#94a3b8;font-size:12px;line-height:1.8;">
                            <code style="color:#e2e8f0;background:#1e293b;padding:1px 4px;border-radius:3px;">useFinancialMetrics</code><br/>
                            <code style="color:#e2e8f0;background:#1e293b;padding:1px 4px;border-radius:3px;">useCurrency</code><br/>
                            <code style="color:#e2e8f0;background:#1e293b;padding:1px 4px;border-radius:3px;">useIndustryTerms</code>
                          </p>
                        </td>
                        <td width="50%" valign="top" style="padding-left:12px;">
                          <p style="margin:0 0 8px;color:#818cf8;font-size:11px;font-weight:700;text-transform:uppercase;">Pages Updated</p>
                          <p style="margin:0;color:#94a3b8;font-size:12px;line-height:1.8;">
                            Decisions, Overview, Scenarios,<br/>Onboarding, Dashboard
                          </p>
                        </td>
                      </tr>
                    </table>
                    <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:16px;">
                      <tr>
                        <td width="50%" valign="top" style="padding-right:12px;">
                          <p style="margin:0 0 8px;color:#818cf8;font-size:11px;font-weight:700;text-transform:uppercase;">Coverage</p>
                          <p style="margin:0;color:#94a3b8;font-size:12px;line-height:1.8;">
                            20+ financial metrics tracked<br/>
                            20 currencies / 25+ TLDs<br/>
                            15 industries / 8 stages<br/>
                            11 terminology verticals
                          </p>
                        </td>
                        <td width="50%" valign="top" style="padding-left:12px;">
                          <p style="margin:0 0 8px;color:#818cf8;font-size:11px;font-weight:700;text-transform:uppercase;">Quality</p>
                          <p style="margin:0;color:#94a3b8;font-size:12px;line-height:1.8;">
                            Metric source provenance<br/>
                            Centralized data pipeline<br/>
                            Dead code removed<br/>
                            Layout compliance verified
                          </p>
                        </td>
                      </tr>
                    </table>
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
                      Explore the Platform
                    </a>
                  </td>
                </tr>
                <tr>
                  <td align="center" style="padding-top:12px;">
                    <p style="margin:0;color:#475569;font-size:12px;">Reply to this email with any feedback or feature requests</p>
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
                Weekly Digest &bull; Week of Feb 8&ndash;14, 2026
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

  console.log(`Sending weekly digest to ${recipients.length} recipients from ${senderEmail}...`);

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

sendWeeklyDigest().catch(console.error);
