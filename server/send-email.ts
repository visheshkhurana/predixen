// One-time script to send simulation feature email via Resend integration
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

  const { data, error } = await resend.emails.send({
    from: fromEmail || 'Predixen <onboarding@resend.dev>',
    to: ['nikita@predixen.ai', 'nikita.luther@gmail.com', 'nikitafl2024@gmail.com'],
    subject: 'See How Monte Carlo Simulations Can Predict Your Startup\'s Future',
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
        <table width="600" cellpadding="0" cellspacing="0" style="background-color:#1e293b;border-radius:12px;overflow:hidden;">
          
          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#6366f1,#8b5cf6);padding:40px 40px 30px;">
              <h1 style="margin:0;color:#ffffff;font-size:28px;font-weight:700;">Predixen Intelligence OS</h1>
              <p style="margin:8px 0 0;color:#c7d2fe;font-size:14px;letter-spacing:1px;">FINANCIAL INTELLIGENCE FOR STARTUPS</p>
            </td>
          </tr>

          <!-- Main Content -->
          <tr>
            <td style="padding:40px;">
              <h2 style="margin:0 0 16px;color:#f1f5f9;font-size:22px;font-weight:600;">
                How Our Monte Carlo Simulations Work
              </h2>
              <p style="margin:0 0 24px;color:#94a3b8;font-size:15px;line-height:1.7;">
                Making financial decisions for your startup shouldn't feel like guessing. That's why we built a simulation engine that runs <strong style="color:#e2e8f0;">thousands of possible futures</strong> for your company, so you can plan with confidence.
              </p>

              <!-- Step 1 -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
                <tr>
                  <td width="48" valign="top">
                    <div style="width:40px;height:40px;border-radius:10px;background-color:#312e81;color:#818cf8;font-size:18px;font-weight:700;text-align:center;line-height:40px;">1</div>
                  </td>
                  <td style="padding-left:16px;">
                    <h3 style="margin:0 0 6px;color:#e2e8f0;font-size:16px;font-weight:600;">Upload Your Financial Data</h3>
                    <p style="margin:0;color:#94a3b8;font-size:14px;line-height:1.6;">
                      Import your revenue, expenses, headcount, and other metrics via CSV, manual entry, or AI-powered extraction from spreadsheets and PDFs.
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Step 2 -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
                <tr>
                  <td width="48" valign="top">
                    <div style="width:40px;height:40px;border-radius:10px;background-color:#312e81;color:#818cf8;font-size:18px;font-weight:700;text-align:center;line-height:40px;">2</div>
                  </td>
                  <td style="padding-left:16px;">
                    <h3 style="margin:0 0 6px;color:#e2e8f0;font-size:16px;font-weight:600;">Truth Engine Validates Everything</h3>
                    <p style="margin:0;color:#94a3b8;font-size:14px;line-height:1.6;">
                      Before any simulation runs, our Truth Engine scans your data for inconsistencies, outliers, and errors. It auto-repairs what it can and flags what needs your attention. No garbage in, no garbage out.
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Step 3 -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
                <tr>
                  <td width="48" valign="top">
                    <div style="width:40px;height:40px;border-radius:10px;background-color:#312e81;color:#818cf8;font-size:18px;font-weight:700;text-align:center;line-height:40px;">3</div>
                  </td>
                  <td style="padding-left:16px;">
                    <h3 style="margin:0 0 6px;color:#e2e8f0;font-size:16px;font-weight:600;">Monte Carlo Runs 10,000+ Scenarios</h3>
                    <p style="margin:0;color:#94a3b8;font-size:14px;line-height:1.6;">
                      The engine generates thousands of possible 24-month projections using probability distributions, regime-aware modeling, and custom event triggers. Each run accounts for real-world uncertainty.
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Step 4 -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
                <tr>
                  <td width="48" valign="top">
                    <div style="width:40px;height:40px;border-radius:10px;background-color:#312e81;color:#818cf8;font-size:18px;font-weight:700;text-align:center;line-height:40px;">4</div>
                  </td>
                  <td style="padding-left:16px;">
                    <h3 style="margin:0 0 6px;color:#e2e8f0;font-size:16px;font-weight:600;">Get Actionable Insights</h3>
                    <p style="margin:0;color:#94a3b8;font-size:14px;line-height:1.6;">
                      See your survival probability, runway projections (P10/P50/P90), sensitivity tornado charts showing which levers matter most, and ranked decision recommendations from our AI copilot.
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Divider -->
              <hr style="border:none;border-top:1px solid #334155;margin:32px 0;">

              <!-- Key Metrics Box -->
              <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f172a;border-radius:10px;overflow:hidden;margin-bottom:32px;">
                <tr>
                  <td style="padding:24px;">
                    <h3 style="margin:0 0 16px;color:#e2e8f0;font-size:16px;font-weight:600;">What You'll Discover:</h3>
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td width="50%" style="padding:8px 0;">
                          <p style="margin:0;color:#818cf8;font-size:13px;font-weight:600;">SURVIVAL PROBABILITY</p>
                          <p style="margin:4px 0 0;color:#94a3b8;font-size:13px;">What are your odds of making it to the next round?</p>
                        </td>
                        <td width="50%" style="padding:8px 0;">
                          <p style="margin:0;color:#818cf8;font-size:13px;font-weight:600;">RUNWAY RANGE</p>
                          <p style="margin:4px 0 0;color:#94a3b8;font-size:13px;">Best case, expected, and worst case months of runway.</p>
                        </td>
                      </tr>
                      <tr>
                        <td width="50%" style="padding:8px 0;">
                          <p style="margin:0;color:#818cf8;font-size:13px;font-weight:600;">KEY DRIVERS</p>
                          <p style="margin:4px 0 0;color:#94a3b8;font-size:13px;">Which financial levers have the biggest impact on outcomes.</p>
                        </td>
                        <td width="50%" style="padding:8px 0;">
                          <p style="margin:0;color:#818cf8;font-size:13px;font-weight:600;">DECISION RANKING</p>
                          <p style="margin:4px 0 0;color:#94a3b8;font-size:13px;">AI-scored recommendations for your next strategic move.</p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>

              <!-- CTA -->
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center">
                    <a href="https://predixen-intelligence-os.replit.app" style="display:inline-block;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#ffffff;font-size:16px;font-weight:600;text-decoration:none;padding:14px 40px;border-radius:8px;">
                      Try Simulations Now
                    </a>
                  </td>
                </tr>
                <tr>
                  <td align="center" style="padding-top:16px;">
                    <p style="margin:0;color:#64748b;font-size:13px;">
                      Demo account: demo@predixen.ai / demo123
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:24px 40px;border-top:1px solid #334155;">
              <p style="margin:0;color:#475569;font-size:12px;text-align:center;">
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
}

sendEmail().catch(err => {
  console.error('Error:', err.message);
  process.exit(1);
});
