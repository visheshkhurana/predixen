// One-time script to send feature update SMS via Twilio integration
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

  if (!connectionSettings || !connectionSettings.settings.account_sid || !connectionSettings.settings.api_key || !connectionSettings.settings.api_key_secret) {
    throw new Error('Twilio not connected. Settings: ' + JSON.stringify(data));
  }
  return {
    accountSid: connectionSettings.settings.account_sid,
    apiKey: connectionSettings.settings.api_key,
    apiKeySecret: connectionSettings.settings.api_key_secret,
    phoneNumber: connectionSettings.settings.phone_number
  };
}

async function sendSMS() {
  console.log('Fetching Twilio credentials...');
  const { accountSid, apiKey, apiKeySecret, phoneNumber } = await getCredentials();
  console.log('Got credentials. From number:', phoneNumber);

  const realAccountSid = process.env.TWILIO_ACCOUNT_SID || accountSid;
  console.log('Using Account SID starting with:', realAccountSid?.substring(0, 2));
  
  const client = twilio(accountSid, apiKeySecret, { accountSid: realAccountSid });

  const message = await client.messages.create({
    body: `FounderConsole - New Feature Update

Hi! Here's what's new in FounderConsole v1.0:

- AI Virtual Boardroom with 14-agent copilot system
- Enhanced Monte Carlo simulations with regime-aware modeling
- Truth Engine for data validation & quality scoring
- Fundraising OS with cap table & dilution tracking
- Multi-LLM Router (OpenAI, Anthropic, Gemini)
- Real-time KPI monitoring & anomaly alerts
- Connector Marketplace for payroll/ERP integrations
- Admin Dashboard with platform-wide analytics

Log in at your FounderConsole dashboard to explore these features.

— FounderConsole Team`,
    from: phoneNumber,
    to: '+919818540514'
  });

  console.log('SMS sent successfully!');
  console.log('Message SID:', message.sid);
  console.log('Status:', message.status);
}

sendSMS().catch(err => {
  console.error('Failed to send SMS:', err.message);
  process.exit(1);
});
