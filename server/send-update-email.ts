// One-time script to send v1.0.0 product update email via Resend integration
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
    'nikita@predixen.ai',
    'nikita.luther@gmail.com',
    'nikitafl2024@gmail.com',
    'vysheshk@gmail.com'
  ];

  const senderEmail = 'Predixen <new1@predixen.app>';
  const subject = 'Predixen v1.0.0 Update: Critical Bug Fixes & New Features Shipped Based on Your Feedback';
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
              <h1 style="margin:0;color:#ffffff;font-size:26px;font-weight:700;">Predixen Intelligence OS</h1>
              <p style="margin:8px 0 0;color:#c7d2fe;font-size:13px;letter-spacing:1px;">v1.0.0 PRODUCT UPDATE &mdash; FEBRUARY 2026</p>
            </td>
          </tr>

          <!-- Intro -->
          <tr>
            <td style="padding:40px 40px 0;">
              <p style="margin:0 0 20px;color:#94a3b8;font-size:15px;line-height:1.7;">
                Following our recent founder feedback session, we've shipped a comprehensive set of bug fixes and new features directly addressing the issues raised. Every change below was driven by real feedback from a $1B+ company founder testing the platform.
              </p>
              <p style="margin:0 0 20px;color:#e2e8f0;font-size:15px;line-height:1.7;font-weight:600;">
                Here's what's new:
              </p>
            </td>
          </tr>

          <!-- SECTION: Critical Bug Fixes -->
          <tr>
            <td style="padding:24px 40px 0;">
              <h2 style="margin:0 0 16px;color:#f1f5f9;font-size:20px;font-weight:600;border-bottom:2px solid #ef4444;padding-bottom:8px;">Critical Bug Fixes</h2>
            </td>
          </tr>

          <!-- Bug Fix 1 -->
          <tr>
            <td style="padding:0 40px 16px;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f172a;border-radius:10px;">
                <tr>
                  <td style="padding:20px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td width="70" valign="top">
                          <div style="background-color:#7f1d1d;color:#fca5a5;font-size:11px;font-weight:700;text-align:center;padding:4px 8px;border-radius:4px;text-transform:uppercase;">Critical</div>
                        </td>
                        <td style="padding-left:12px;">
                          <h3 style="margin:0 0 8px;color:#f1f5f9;font-size:15px;font-weight:600;">Strategic Briefing Infinite Loading Fixed</h3>
                          <p style="margin:0;color:#94a3b8;font-size:13px;line-height:1.6;">
                            The Decisions page "Generate Strategic Diagnosis" would sometimes get stuck in a perpetual loading state with no way to recover. We've added a <strong style="color:#e2e8f0;">30-second timeout</strong> with automatic error detection, a clear error message, and a <strong style="color:#e2e8f0;">one-click retry button</strong>. The loading animation now shows real-time progress stages so you always know what's happening.
                          </p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Bug Fix 2 -->
          <tr>
            <td style="padding:0 40px 16px;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f172a;border-radius:10px;">
                <tr>
                  <td style="padding:20px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td width="70" valign="top">
                          <div style="background-color:#7f1d1d;color:#fca5a5;font-size:11px;font-weight:700;text-align:center;padding:4px 8px;border-radius:4px;text-transform:uppercase;">Critical</div>
                        </td>
                        <td style="padding-left:12px;">
                          <h3 style="margin:0 0 8px;color:#f1f5f9;font-size:15px;font-weight:600;">Data Consistency Across All Pages</h3>
                          <p style="margin:0;color:#94a3b8;font-size:13px;line-height:1.6;">
                            Previously, the Dashboard, Overview, and Scenarios pages each computed financial metrics independently, leading to <strong style="color:#e2e8f0;">different numbers appearing on different pages</strong> for the same metric. We've built a centralized <code style="color:#818cf8;background:#1e293b;padding:2px 4px;border-radius:3px;">useFinancialMetrics</code> hook that serves as the single source of truth. Every page now pulls from the same calculation pipeline &mdash; MRR, ARR, runway, burn rate, growth rate, and 15+ other metrics are always consistent.
                          </p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Bug Fix 3 -->
          <tr>
            <td style="padding:0 40px 16px;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f172a;border-radius:10px;">
                <tr>
                  <td style="padding:20px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td width="70" valign="top">
                          <div style="background-color:#7f1d1d;color:#fca5a5;font-size:11px;font-weight:700;text-align:center;padding:4px 8px;border-radius:4px;text-transform:uppercase;">Critical</div>
                        </td>
                        <td style="padding-left:12px;">
                          <h3 style="margin:0 0 8px;color:#f1f5f9;font-size:15px;font-weight:600;">Missing Industry Categories & Stages</h3>
                          <p style="margin:0;color:#94a3b8;font-size:13px;line-height:1.6;">
                            The onboarding only supported 5 industry categories and 4 company stages, which excluded the majority of non-SaaS companies. Now expanded to <strong style="color:#e2e8f0;">15 industry categories</strong> (including D2C, Healthcare, EdTech, AgriTech, DeepTech, Climate, Media, Logistics, Real Estate, Food) and <strong style="color:#e2e8f0;">8 company stages</strong> (adding Pre-Series A, Growth, Pre-IPO, Public). The overview page benchmark selectors are also updated to match.
                          </p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- SECTION: Additional Fixes -->
          <tr>
            <td style="padding:24px 40px 0;">
              <h2 style="margin:0 0 16px;color:#f1f5f9;font-size:20px;font-weight:600;border-bottom:2px solid #f59e0b;padding-bottom:8px;">Additional Fixes</h2>
            </td>
          </tr>

          <!-- Bug Fix 4 -->
          <tr>
            <td style="padding:0 40px 16px;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f172a;border-radius:10px;">
                <tr>
                  <td style="padding:20px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td width="50" valign="top">
                          <div style="background-color:#78350f;color:#fcd34d;font-size:11px;font-weight:700;text-align:center;padding:4px 8px;border-radius:4px;text-transform:uppercase;">Fix</div>
                        </td>
                        <td style="padding-left:12px;">
                          <h3 style="margin:0 0 8px;color:#f1f5f9;font-size:15px;font-weight:600;">"AI Estimated" Badges on Derived Metrics</h3>
                          <p style="margin:0;color:#94a3b8;font-size:13px;line-height:1.6;">
                            Metrics that aren't directly reported by the company but are calculated or estimated by AI now show clear badges &mdash; <span style="color:#fcd34d;font-weight:600;">"AI Est."</span> for estimated values and <span style="color:#60a5fa;font-weight:600;">"Derived"</span> for computed values. Every metric tracks its provenance (<code style="color:#818cf8;background:#1e293b;padding:2px 4px;border-radius:3px;">reported</code>, <code style="color:#818cf8;background:#1e293b;padding:2px 4px;border-radius:3px;">computed</code>, or <code style="color:#818cf8;background:#1e293b;padding:2px 4px;border-radius:3px;">estimated</code>) so founders always know what's real data vs. what's inferred.
                          </p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Bug Fix 5 -->
          <tr>
            <td style="padding:0 40px 16px;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f172a;border-radius:10px;">
                <tr>
                  <td style="padding:20px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td width="50" valign="top">
                          <div style="background-color:#78350f;color:#fcd34d;font-size:11px;font-weight:700;text-align:center;padding:4px 8px;border-radius:4px;text-transform:uppercase;">Fix</div>
                        </td>
                        <td style="padding-left:12px;">
                          <h3 style="margin:0 0 8px;color:#f1f5f9;font-size:15px;font-weight:600;">US-Centric Defaults Removed</h3>
                          <p style="margin:0;color:#94a3b8;font-size:13px;line-height:1.6;">
                            The platform previously hardcoded USD everywhere. Now when a company enters their website during onboarding, the system <strong style="color:#e2e8f0;">auto-detects the likely currency from the TLD</strong> (e.g., .in &rarr; INR, .co.uk &rarr; GBP, .eu &rarr; EUR, .jp &rarr; JPY). Supports 25+ country TLD mappings with a manual currency selector as override.
                          </p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- SECTION: New Features -->
          <tr>
            <td style="padding:24px 40px 0;">
              <h2 style="margin:0 0 16px;color:#f1f5f9;font-size:20px;font-weight:600;border-bottom:2px solid #22c55e;padding-bottom:8px;">New Features</h2>
            </td>
          </tr>

          <!-- Feature 1: Multi-Currency -->
          <tr>
            <td style="padding:0 40px 16px;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f172a;border-radius:10px;">
                <tr>
                  <td style="padding:20px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td width="50" valign="top">
                          <div style="background-color:#14532d;color:#86efac;font-size:11px;font-weight:700;text-align:center;padding:4px 8px;border-radius:4px;text-transform:uppercase;">New</div>
                        </td>
                        <td style="padding-left:12px;">
                          <h3 style="margin:0 0 8px;color:#f1f5f9;font-size:15px;font-weight:600;">Full Multi-Currency Support</h3>
                          <p style="margin:0;color:#94a3b8;font-size:13px;line-height:1.6;">
                            Every financial figure across the platform &mdash; simulations, scenarios, KPIs, charts &mdash; now renders in the company's own currency. The new <code style="color:#818cf8;background:#1e293b;padding:2px 4px;border-radius:3px;">useCurrency</code> hook provides consistent formatting everywhere. Supports <strong style="color:#e2e8f0;">20 currencies</strong> including USD, EUR, GBP, INR, JPY, AUD, CAD, SGD, AED, BRL, and more. Abbreviations adapt automatically (e.g., "$1.2M" vs "&#8377;1.2Cr" vs "&#165;120M").
                          </p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Feature 2: Industry-Adaptive Terminology -->
          <tr>
            <td style="padding:0 40px 16px;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f172a;border-radius:10px;">
                <tr>
                  <td style="padding:20px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td width="50" valign="top">
                          <div style="background-color:#14532d;color:#86efac;font-size:11px;font-weight:700;text-align:center;padding:4px 8px;border-radius:4px;text-transform:uppercase;">New</div>
                        </td>
                        <td style="padding-left:12px;">
                          <h3 style="margin:0 0 8px;color:#f1f5f9;font-size:15px;font-weight:600;">Industry-Adaptive Terminology</h3>
                          <p style="margin:0;color:#94a3b8;font-size:13px;line-height:1.6;">
                            The platform now speaks your industry's language. A healthcare company sees <strong style="color:#e2e8f0;">"Patients"</strong> instead of "Customers," an EdTech sees <strong style="color:#e2e8f0;">"Learners,"</strong> a marketplace sees <strong style="color:#e2e8f0;">"GMV"</strong> instead of "Revenue." The <code style="color:#818cf8;background:#1e293b;padding:2px 4px;border-radius:3px;">useIndustryTerms</code> hook covers 11 industry verticals and adapts KPI labels, churn terminology, and revenue metrics throughout the dashboard.
                          </p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- SECTION: Technical Summary -->
          <tr>
            <td style="padding:24px 40px 0;">
              <h2 style="margin:0 0 16px;color:#f1f5f9;font-size:20px;font-weight:600;border-bottom:2px solid #6366f1;padding-bottom:8px;">Technical Summary</h2>
            </td>
          </tr>

          <tr>
            <td style="padding:0 40px 16px;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f172a;border-radius:10px;">
                <tr>
                  <td style="padding:20px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td width="50%" valign="top" style="padding:4px 8px 4px 0;">
                          <p style="margin:0 0 8px;color:#818cf8;font-size:12px;font-weight:700;text-transform:uppercase;">New Hooks Created</p>
                          <p style="margin:0;color:#64748b;font-size:12px;">&#8226; useFinancialMetrics</p>
                          <p style="margin:4px 0 0;color:#64748b;font-size:12px;">&#8226; useCurrency</p>
                          <p style="margin:4px 0 0;color:#64748b;font-size:12px;">&#8226; useIndustryTerms</p>
                        </td>
                        <td width="50%" valign="top" style="padding:4px 0 4px 8px;">
                          <p style="margin:0 0 8px;color:#818cf8;font-size:12px;font-weight:700;text-transform:uppercase;">Pages Updated</p>
                          <p style="margin:0;color:#64748b;font-size:12px;">&#8226; Decisions (timeout + retry)</p>
                          <p style="margin:4px 0 0;color:#64748b;font-size:12px;">&#8226; Overview (badges + terms)</p>
                          <p style="margin:4px 0 0;color:#64748b;font-size:12px;">&#8226; Scenarios (currency)</p>
                          <p style="margin:4px 0 0;color:#64748b;font-size:12px;">&#8226; Onboarding (categories)</p>
                        </td>
                      </tr>
                    </table>
                    <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:16px;">
                      <tr>
                        <td width="50%" valign="top" style="padding:4px 8px 4px 0;">
                          <p style="margin:0 0 8px;color:#818cf8;font-size:12px;font-weight:700;text-transform:uppercase;">Metrics Tracked</p>
                          <p style="margin:0;color:#64748b;font-size:12px;">&#8226; 20+ financial metrics</p>
                          <p style="margin:4px 0 0;color:#64748b;font-size:12px;">&#8226; Source provenance per metric</p>
                          <p style="margin:4px 0 0;color:#64748b;font-size:12px;">&#8226; Merge: API + truth scan + baseline</p>
                        </td>
                        <td width="50%" valign="top" style="padding:4px 0 4px 8px;">
                          <p style="margin:0 0 8px;color:#818cf8;font-size:12px;font-weight:700;text-transform:uppercase;">Coverage</p>
                          <p style="margin:0;color:#64748b;font-size:12px;">&#8226; 15 industry categories</p>
                          <p style="margin:4px 0 0;color:#64748b;font-size:12px;">&#8226; 8 company stages</p>
                          <p style="margin:4px 0 0;color:#64748b;font-size:12px;">&#8226; 20 currencies / 25+ TLDs</p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- SECTION: What's Next -->
          <tr>
            <td style="padding:24px 40px 0;">
              <h2 style="margin:0 0 12px;color:#f1f5f9;font-size:20px;font-weight:600;border-bottom:2px solid #6366f1;padding-bottom:8px;">What's Coming Next</h2>
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="padding:8px 0;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td width="28" valign="top">
                          <div style="width:22px;height:22px;border-radius:6px;background-color:#1e3a5f;color:#60a5fa;font-size:12px;font-weight:700;text-align:center;line-height:22px;">1</div>
                        </td>
                        <td style="padding-left:10px;">
                          <p style="margin:0;color:#e2e8f0;font-size:13px;">Enhanced Decisions page with sticky TOC sidebar, animated loading, and section dividers</p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
                <tr>
                  <td style="padding:8px 0;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td width="28" valign="top">
                          <div style="width:22px;height:22px;border-radius:6px;background-color:#1e3a5f;color:#60a5fa;font-size:12px;font-weight:700;text-align:center;line-height:22px;">2</div>
                        </td>
                        <td style="padding-left:10px;">
                          <p style="margin:0;color:#e2e8f0;font-size:13px;">Color-coded risk badges and urgency callouts across the briefing document</p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
                <tr>
                  <td style="padding:8px 0;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td width="28" valign="top">
                          <div style="width:22px;height:22px;border-radius:6px;background-color:#1e3a5f;color:#60a5fa;font-size:12px;font-weight:700;text-align:center;line-height:22px;">3</div>
                        </td>
                        <td style="padding-left:10px;">
                          <p style="margin:0;color:#e2e8f0;font-size:13px;">Alternative Paths section &mdash; automatically generated counter-scenarios</p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
                <tr>
                  <td style="padding:8px 0;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td width="28" valign="top">
                          <div style="width:22px;height:22px;border-radius:6px;background-color:#1e3a5f;color:#60a5fa;font-size:12px;font-weight:700;text-align:center;line-height:22px;">4</div>
                        </td>
                        <td style="padding-left:10px;">
                          <p style="margin:0;color:#e2e8f0;font-size:13px;">Email sharing of strategic briefings directly from the platform</p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
                <tr>
                  <td style="padding:8px 0;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td width="28" valign="top">
                          <div style="width:22px;height:22px;border-radius:6px;background-color:#1e3a5f;color:#60a5fa;font-size:12px;font-weight:700;text-align:center;line-height:22px;">5</div>
                        </td>
                        <td style="padding-left:10px;">
                          <p style="margin:0;color:#e2e8f0;font-size:13px;">Capital structure modeling (debt vs equity) in the scenario simulator</p>
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
                    <a href="https://predixen-intelligence-os.replit.app" style="display:inline-block;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#ffffff;font-size:15px;font-weight:600;text-decoration:none;padding:14px 36px;border-radius:8px;">
                      Explore the Platform
                    </a>
                  </td>
                </tr>
                <tr>
                  <td align="center" style="padding-top:12px;">
                    <p style="margin:0;color:#64748b;font-size:12px;">
                      Demo: demo@predixen.ai / demo123
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:20px 40px;border-top:1px solid #334155;">
              <p style="margin:0 0 8px;color:#475569;font-size:11px;text-align:center;">
                Predixen Intelligence OS &mdash; Investor-grade financial intelligence for startups.
              </p>
              <p style="margin:0;color:#334155;font-size:10px;text-align:center;">
                This is a transactional update email sent individually to stakeholders.
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

  for (const recipient of recipients) {
    console.log(`Sending to ${recipient}...`);
    const { data, error } = await resend.emails.send({
      from: senderEmail,
      to: [recipient],
      subject,
      html: htmlContent
    });

    if (error) {
      console.error(`Failed to send to ${recipient}:`, error);
    } else {
      console.log(`Sent to ${recipient} - ID: ${data?.id}`);
    }
    await new Promise(resolve => setTimeout(resolve, 1500));
  }

  console.log('All update emails sent.');
}

sendUpdateEmails().catch(err => {
  console.error('Error:', err.message);
  process.exit(1);
});
