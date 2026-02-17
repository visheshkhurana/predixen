// FounderConsole - SMS Update via Twilio Replit Connector
import twilio from 'twilio';

const RECIPIENTS = [
  { phone: "+919818540514", name: "Nikita" },
];

const MESSAGE = `FounderConsole — Multi-Currency Support Live

33 global currencies now supported across the entire platform:

- Set your company's base currency (USD, EUR, GBP, INR, SGD, JPY, AED + 26 more)
- Dashboard, KPIs, simulations, charts all auto-convert
- Live ECB exchange rates with 6-hour cache
- Full audit trail: original currency + FX rate stored per record

To set: Sidebar → Edit Company → Currency dropdown

Try it: demo@founderconsole.ai / demo123
https://founderconsole.ai

— FounderConsole Team`;

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
        'X_REPLIT_TOKEN': xReplitToken,
      },
    }
  );
  const data = await res.json();
  const connectionSettings = data.items?.[0];

  if (!connectionSettings?.settings) {
    throw new Error('Twilio not connected. Please set up the Twilio connector.');
  }

  const s = connectionSettings.settings;

  const accountSid = process.env.TWILIO_ACCOUNT_SID || s.account_sid;
  const apiKey = s.api_key?.startsWith('SK') ? s.api_key : s.account_sid?.startsWith('SK') ? s.account_sid : s.api_key;
  const apiKeySecret = s.api_key_secret;
  const phoneNumber = s.phone_number;

  if (!accountSid) throw new Error('No Account SID found');
  if (!apiKey) throw new Error('No API Key found');
  if (!apiKeySecret) throw new Error('No API Key Secret found');

  return { accountSid, apiKey, apiKeySecret, phoneNumber };
}

async function sendUpdateSMS() {
  console.log("=== FounderConsole SMS Update ===\n");

  const creds = await getCredentials();
  const client = twilio(creds.apiKey, creds.apiKeySecret, {
    accountSid: creds.accountSid,
  });

  const fromNumber = creds.phoneNumber;
  if (!fromNumber) {
    throw new Error("No Twilio phone number configured in the connector.");
  }

  console.log(`From: ${fromNumber}\n`);

  for (const rcpt of RECIPIENTS) {
    try {
      const msg = await client.messages.create({
        body: MESSAGE,
        from: fromNumber,
        to: rcpt.phone,
      });
      console.log(`[SENT] ${rcpt.name} (${rcpt.phone}) -> SID: ${msg.sid}`);
    } catch (err: any) {
      console.error(`[FAILED] ${rcpt.name} (${rcpt.phone}) -> ${err.message}`);
    }
  }

  console.log("\nDone!");
}

sendUpdateSMS().catch(err => {
  console.error("Fatal error:", err.message);
  process.exit(1);
});
