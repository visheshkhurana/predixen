// One-time script to send founder feedback email via Resend integration
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
    fromEmail: connectionSettings.settings.from_email
  };
}

async function sendEmail() {
  console.log('Fetching Resend credentials...');
  const { apiKey, fromEmail } = await getCredentials();
  console.log('From email:', fromEmail);

  const resend = new Resend(apiKey);

  const recipients = [
    'nikita@predixen.ai',
    'nikita.luther@gmail.com',
    'nikitafl2024@gmail.com',
    'vysheshk@gmail.com'
  ];

  const { data, error } = await resend.emails.send({
    from: 'Predixen <hi@predixen.app>',
    to: recipients,
    subject: 'Founder Feedback Session - Key Insights & Product Direction for Predixen',
    html: `
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
              <p style="margin:8px 0 0;color:#c7d2fe;font-size:13px;letter-spacing:1px;">FOUNDER FEEDBACK SESSION SUMMARY</p>
            </td>
          </tr>

          <!-- Intro -->
          <tr>
            <td style="padding:40px 40px 0;">
              <p style="margin:0 0 20px;color:#94a3b8;font-size:15px;line-height:1.7;">
                Thank you for the incredibly valuable conversation. Below is a structured summary of the key insights, product direction, and next steps we discussed. This document serves as our shared reference point going forward.
              </p>
            </td>
          </tr>

          <!-- Section: The Core Problem -->
          <tr>
            <td style="padding:24px 40px 0;">
              <h2 style="margin:0 0 12px;color:#f1f5f9;font-size:20px;font-weight:600;border-bottom:2px solid #6366f1;padding-bottom:8px;">The Core Problem</h2>
              <p style="margin:0 0 16px;color:#94a3b8;font-size:14px;line-height:1.7;">
                Even with all data available, startups don't have a unified, real-time, forward-looking system that can <strong style="color:#e2e8f0;">simulate decisions before committing capital</strong>.
              </p>
              <p style="margin:0 0 16px;color:#94a3b8;font-size:14px;line-height:1.7;">
                After raising significant capital, a company might face 3 possible growth paths &mdash; backward integration, forward integration, or international expansion. Realistically, you can't pursue all three. Traditionally, founders test each with small pilots, but that's slow, expensive, and often reactive.
              </p>
              <p style="margin:0 0 8px;color:#c7d2fe;font-size:14px;font-weight:600;">
                This is the gap Predixen is solving.
              </p>
            </td>
          </tr>

          <!-- Section: Three Product Layers -->
          <tr>
            <td style="padding:32px 40px 0;">
              <h2 style="margin:0 0 16px;color:#f1f5f9;font-size:20px;font-weight:600;border-bottom:2px solid #6366f1;padding-bottom:8px;">The Three Product Layers</h2>
            </td>
          </tr>

          <!-- Layer A -->
          <tr>
            <td style="padding:0 40px;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f172a;border-radius:10px;margin-bottom:16px;">
                <tr>
                  <td style="padding:20px;">
                    <h3 style="margin:0 0 8px;color:#818cf8;font-size:15px;font-weight:700;">A. Unified KPI Monitoring Engine</h3>
                    <p style="margin:0 0 12px;color:#94a3b8;font-size:13px;line-height:1.6;">
                      Integrates accounting, HR/payroll, analytics, ad platforms, banking, and operational APIs into a single real-time dashboard.
                    </p>
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td width="50%" valign="top" style="padding:4px 8px 4px 0;">
                          <p style="margin:0;color:#64748b;font-size:12px;">&#8226; Runway visibility</p>
                          <p style="margin:4px 0 0;color:#64748b;font-size:12px;">&#8226; Burn trends</p>
                          <p style="margin:4px 0 0;color:#64748b;font-size:12px;">&#8226; CAC trends + alerts</p>
                          <p style="margin:4px 0 0;color:#64748b;font-size:12px;">&#8226; Revenue forecasting</p>
                        </td>
                        <td width="50%" valign="top" style="padding:4px 0 4px 8px;">
                          <p style="margin:0;color:#64748b;font-size:12px;">&#8226; Margin movement</p>
                          <p style="margin:4px 0 0;color:#64748b;font-size:12px;">&#8226; Payroll growth spikes</p>
                          <p style="margin:4px 0 0;color:#64748b;font-size:12px;">&#8226; Cash commitments</p>
                          <p style="margin:4px 0 0;color:#64748b;font-size:12px;">&#8226; Proactive alerts</p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Layer B -->
          <tr>
            <td style="padding:0 40px;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f172a;border-radius:10px;margin-bottom:16px;">
                <tr>
                  <td style="padding:20px;">
                    <h3 style="margin:0 0 8px;color:#818cf8;font-size:15px;font-weight:700;">B. Decision Simulator (Core Engine)</h3>
                    <p style="margin:0 0 12px;color:#94a3b8;font-size:13px;line-height:1.6;">
                      The heart of the product. Simulate revenue drops, marketing cuts, hiring surges, product launches, debt vs equity funding, and capex-heavy expansion &mdash; all before committing a single dollar.
                    </p>
                    <p style="margin:0 0 8px;color:#e2e8f0;font-size:13px;font-weight:600;">Monte Carlo outputs:</p>
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td width="50%" style="padding:4px 0;">
                          <p style="margin:0;color:#64748b;font-size:12px;">&#8226; Runway impact (P10/P50/P90)</p>
                          <p style="margin:4px 0 0;color:#64748b;font-size:12px;">&#8226; Cash flow projections</p>
                        </td>
                        <td width="50%" style="padding:4px 0;">
                          <p style="margin:0;color:#64748b;font-size:12px;">&#8226; Break-even timelines</p>
                          <p style="margin:4px 0 0;color:#64748b;font-size:12px;">&#8226; Capital required estimates</p>
                        </td>
                      </tr>
                    </table>
                    <p style="margin:12px 0 0;color:#c7d2fe;font-size:13px;font-style:italic;">
                      "Test decisions before you execute them."
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Layer C -->
          <tr>
            <td style="padding:0 40px;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f172a;border-radius:10px;margin-bottom:16px;">
                <tr>
                  <td style="padding:20px;">
                    <h3 style="margin:0 0 8px;color:#818cf8;font-size:15px;font-weight:700;">C. AI Co-Pilot</h3>
                    <p style="margin:0 0 8px;color:#94a3b8;font-size:13px;line-height:1.6;">
                      A continuous McKinsey-style strategic partner grounded in real company data. With full business context, historical data, market benchmarks, and internet access, it can:
                    </p>
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td width="50%" style="padding:4px 0;">
                          <p style="margin:0;color:#64748b;font-size:12px;">&#8226; Discuss strategy in context</p>
                          <p style="margin:4px 0 0;color:#64748b;font-size:12px;">&#8226; Recommend fundraising levels</p>
                        </td>
                        <td width="50%" style="padding:4px 0;">
                          <p style="margin:0;color:#64748b;font-size:12px;">&#8226; Evaluate growth levers</p>
                          <p style="margin:4px 0 0;color:#64748b;font-size:12px;">&#8226; Benchmark vs industry</p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Section: Real-World Case Study -->
          <tr>
            <td style="padding:24px 40px 0;">
              <h2 style="margin:0 0 12px;color:#f1f5f9;font-size:20px;font-weight:600;border-bottom:2px solid #6366f1;padding-bottom:8px;">Real-World Insights from Our Discussion</h2>
              <p style="margin:0 0 16px;color:#94a3b8;font-size:14px;line-height:1.7;">
                We explored a business operating across three verticals &mdash; each with different capital intensity, IRR profiles, break-even curves, and margin structures:
              </p>
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:16px;">
                <tr>
                  <td style="padding:8px 0;border-bottom:1px solid #334155;">
                    <p style="margin:0;color:#818cf8;font-size:13px;font-weight:600;">1. EBO / Store-Level Revenue Share</p>
                  </td>
                </tr>
                <tr>
                  <td style="padding:8px 0;border-bottom:1px solid #334155;">
                    <p style="margin:0;color:#818cf8;font-size:13px;font-weight:600;">2. Multi-Brand Retail (Inventory on Books)</p>
                  </td>
                </tr>
                <tr>
                  <td style="padding:8px 0;">
                    <p style="margin:0;color:#818cf8;font-size:13px;font-weight:600;">3. Large Strip Mall / Asset Development</p>
                  </td>
                </tr>
              </table>
              <p style="margin:0 0 8px;color:#e2e8f0;font-size:14px;font-weight:600;">
                The key decision question: Which vertical should they double down on?
              </p>
              <p style="margin:0 0 16px;color:#94a3b8;font-size:14px;line-height:1.7;">
                This is exactly where scenario simulation becomes powerful &mdash; modeling growth using internal cash alone, adding debt at varying cost of capital, or adding equity, and seeing how each lever changes the growth trajectory.
              </p>
            </td>
          </tr>

          <!-- Section: Pain Points -->
          <tr>
            <td style="padding:24px 40px 0;">
              <h2 style="margin:0 0 16px;color:#f1f5f9;font-size:20px;font-weight:600;border-bottom:2px solid #6366f1;padding-bottom:8px;">Key Pain Points Identified</h2>
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="padding:10px 0;border-bottom:1px solid #1e293b;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td width="32" valign="top">
                          <div style="width:24px;height:24px;border-radius:6px;background-color:#7f1d1d;color:#fca5a5;font-size:13px;font-weight:700;text-align:center;line-height:24px;">!</div>
                        </td>
                        <td style="padding-left:12px;">
                          <p style="margin:0;color:#e2e8f0;font-size:13px;font-weight:600;">Cash flow shocks from hiring sprees</p>
                          <p style="margin:4px 0 0;color:#64748b;font-size:12px;">Senior leaders hiring aggressively without central visibility, creating payroll spikes.</p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
                <tr>
                  <td style="padding:10px 0;border-bottom:1px solid #1e293b;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td width="32" valign="top">
                          <div style="width:24px;height:24px;border-radius:6px;background-color:#7f1d1d;color:#fca5a5;font-size:13px;font-weight:700;text-align:center;line-height:24px;">!</div>
                        </td>
                        <td style="padding-left:12px;">
                          <p style="margin:0;color:#e2e8f0;font-size:13px;font-weight:600;">Appraisal cycle cash surprises</p>
                          <p style="margin:4px 0 0;color:#64748b;font-size:12px;">Deferred increment payouts creating sudden April cash hits.</p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
                <tr>
                  <td style="padding:10px 0;border-bottom:1px solid #1e293b;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td width="32" valign="top">
                          <div style="width:24px;height:24px;border-radius:6px;background-color:#7f1d1d;color:#fca5a5;font-size:13px;font-weight:700;text-align:center;line-height:24px;">!</div>
                        </td>
                        <td style="padding-left:12px;">
                          <p style="margin:0;color:#e2e8f0;font-size:13px;font-weight:600;">Lack of proactive alerts</p>
                          <p style="margin:4px 0 0;color:#64748b;font-size:12px;">CAC tripling month-over-month without immediate founder-level visibility.</p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
                <tr>
                  <td style="padding:10px 0;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td width="32" valign="top">
                          <div style="width:24px;height:24px;border-radius:6px;background-color:#7f1d1d;color:#fca5a5;font-size:13px;font-weight:700;text-align:center;line-height:24px;">!</div>
                        </td>
                        <td style="padding-left:12px;">
                          <p style="margin:0;color:#e2e8f0;font-size:13px;font-weight:600;">Too many dashboards, too little action</p>
                          <p style="margin:4px 0 0;color:#64748b;font-size:12px;">Adoption fatigue is real. Founders only look at 5-8 core metrics daily.</p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Section: Product Philosophy -->
          <tr>
            <td style="padding:32px 40px 0;">
              <h2 style="margin:0 0 12px;color:#f1f5f9;font-size:20px;font-weight:600;border-bottom:2px solid #6366f1;padding-bottom:8px;">Product Philosophy</h2>
              <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f172a;border-radius:10px;">
                <tr>
                  <td style="padding:20px;">
                    <p style="margin:0 0 12px;color:#94a3b8;font-size:14px;line-height:1.7;">
                      The product must surface only the <strong style="color:#e2e8f0;">5-8 critical founder metrics</strong>, give alerts (not just dashboards), and be proactive rather than retrospective.
                    </p>
                    <p style="margin:0;color:#c7d2fe;font-size:14px;font-weight:600;font-style:italic;">
                      The goal: "Why didn't I see this coming?" should never be asked again.
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Section: Next Steps -->
          <tr>
            <td style="padding:32px 40px 0;">
              <h2 style="margin:0 0 16px;color:#f1f5f9;font-size:20px;font-weight:600;border-bottom:2px solid #6366f1;padding-bottom:8px;">Agreed Next Steps</h2>
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="padding:8px 0;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td width="28" valign="top">
                          <div style="width:22px;height:22px;border-radius:6px;background-color:#1e3a5f;color:#60a5fa;font-size:12px;font-weight:700;text-align:center;line-height:22px;">1</div>
                        </td>
                        <td style="padding-left:10px;">
                          <p style="margin:0;color:#e2e8f0;font-size:13px;">Connect with engineering team to understand internal dashboard architecture</p>
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
                          <p style="margin:0;color:#e2e8f0;font-size:13px;">Refine scenario engine logic around capital structure (debt vs equity modeling)</p>
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
                          <p style="margin:0;color:#e2e8f0;font-size:13px;">Improve proactive alert systems for cash flow, payroll, and CAC anomalies</p>
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
                          <p style="margin:0;color:#e2e8f0;font-size:13px;">Design founder-centric minimal dashboard (focused on the 5-8 core metrics)</p>
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
                          <p style="margin:0;color:#e2e8f0;font-size:13px;">Expand HR and accounting integrations for predictive payroll modeling</p>
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
              <p style="margin:0;color:#475569;font-size:11px;text-align:center;">
                Predixen Intelligence OS &mdash; Investor-grade financial intelligence for startups.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
    `
  });

  if (error) {
    console.error('Failed to send email:', error);
    process.exit(1);
  }

  console.log('Email sent successfully!');
  console.log('Email ID:', data?.id);
  console.log('Sent to:', recipients.join(', '));
}

sendEmail().catch(err => {
  console.error('Error:', err.message);
  process.exit(1);
});
