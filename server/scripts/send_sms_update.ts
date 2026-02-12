// SMS update script using Twilio Replit Connector
import twilio from 'twilio';

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
    'https://' + hostname + '/api/v2/connection?include_secrets=true&connector_names=twilio',
    {
      headers: {
        'Accept': 'application/json',
        'X_REPLIT_TOKEN': xReplitToken
      }
    }
  );
  const data = await res.json();
  const connectionSettings = data.items?.[0];

  const s = connectionSettings.settings;
  if (!s.account_sid || !s.api_key || !s.api_key_secret) {
    throw new Error('Twilio not connected');
  }

  return {
    apiKeySid: s.account_sid,
    apiKeySecret: s.api_key,
    phoneNumber: s.phone_number
  };
}

async function sendSMS() {
  const { apiKeySid, apiKeySecret, phoneNumber } = await getCredentials();
  const accountSid = process.env.TWILIO_ACCOUNT_SID;
  if (!accountSid) throw new Error('TWILIO_ACCOUNT_SID secret not set');
  const client = twilio(apiKeySid, apiKeySecret, { accountSid });

  const toNumber = '+919818540514';

  const messageBody = `Predixen Intelligence OS - Simulation Engine Update

New changes live:

1. AI Decision Summary - Consultant-grade card with Decision Score (1-10), GO/CONDITIONAL/NO-GO verdict, key risk, opportunity & watch metric

2. Results Hierarchy Reorganized - All 11 analysis layers visible inline, no hidden tabs. Order: AI Summary > Recommendations > Before/After > Sensitivity Levers > Tornado/What-If > Stress Tests > Counter-Moves > Monte Carlo > Charts > Fundraising Intelligence

3. Counter-Move Simulations - 3 auto-generated counter-moves per scenario (Cost Cut 20%, Raise Prices 10%, Freeze Hiring) with one-click apply

4. Dual-Path "Or" Detection - Type "X or Y" to run parallel simulations with side-by-side comparison

5. Sensitivity Sliders - Interactive variable stress-testing with breaking point markers

6. Cross-Page Alerts - Intelligence alerts on Dashboard, Data Input & Fundraising pages

7. Founder Mode - Toggle for executive summary view

All live now.
- Predixen`;

  console.log(`Sending SMS to ${toNumber} from ${phoneNumber}...`);

  try {
    const message = await client.messages.create({
      body: messageBody,
      from: phoneNumber,
      to: toNumber
    });
    console.log(`[SENT] SID: ${message.sid}, Status: ${message.status}`);
  } catch (err: any) {
    console.error(`[FAILED] ${err.message}`);
  }
}

sendSMS();
