// Twilio integration via Replit Connectors API
import twilio from 'twilio';

let connectionSettings: any;

async function getCredentials() {
  const hostname = process.env.REPLIT_CONNECTORS_HOSTNAME;
  const xReplitToken = process.env.REPL_IDENTITY
    ? 'repl ' + process.env.REPL_IDENTITY
    : process.env.WEB_REPL_RENEWAL
    ? 'depl ' + process.env.WEB_REPL_RENEWAL
    : null;

  if (!xReplitToken) {
    throw new Error('Twilio credentials not available');
  }

  connectionSettings = await fetch(
    'https://' + hostname + '/api/v2/connection?include_secrets=true&connector_names=twilio',
    {
      headers: {
        'Accept': 'application/json',
        'X_REPLIT_TOKEN': xReplitToken,
      },
    }
  )
    .then((res) => res.json())
    .then((data) => data.items?.[0]);

  if (
    !connectionSettings ||
    !connectionSettings.settings.account_sid ||
    !connectionSettings.settings.api_key ||
    !connectionSettings.settings.api_key_secret
  ) {
    throw new Error('Twilio not connected');
  }
  return {
    accountSid: connectionSettings.settings.account_sid,
    apiKey: connectionSettings.settings.api_key,
    apiKeySecret: connectionSettings.settings.api_key_secret,
    phoneNumber: connectionSettings.settings.phone_number,
  };
}

export async function getTwilioClient() {
  const { accountSid, apiKey, apiKeySecret } = await getCredentials();
  return twilio(apiKey, apiKeySecret, {
    accountSid: accountSid,
  });
}

export async function getTwilioFromPhoneNumber() {
  const { phoneNumber } = await getCredentials();
  return phoneNumber;
}

export interface SendSmsParams {
  to: string;
  body: string;
  from?: string;
}

export interface SendWhatsAppParams {
  to: string;
  body: string;
  from?: string;
}

export async function sendSms({ to, body, from }: SendSmsParams) {
  const client = await getTwilioClient();
  const fromNumber = from || (await getTwilioFromPhoneNumber());

  if (!fromNumber) {
    throw new Error('No Twilio phone number configured');
  }

  const message = await client.messages.create({
    body,
    from: fromNumber,
    to,
  });

  return {
    sid: message.sid,
    status: message.status,
    to: message.to,
    from: message.from,
    body: message.body,
    dateSent: message.dateCreated,
  };
}

export async function sendWhatsApp({ to, body, from }: SendWhatsAppParams) {
  const client = await getTwilioClient();
  const fromNumber = from || (await getTwilioFromPhoneNumber());

  if (!fromNumber) {
    throw new Error('No Twilio phone number configured');
  }

  const whatsappFrom = fromNumber.startsWith('whatsapp:')
    ? fromNumber
    : `whatsapp:${fromNumber}`;
  const whatsappTo = to.startsWith('whatsapp:') ? to : `whatsapp:${to}`;

  const message = await client.messages.create({
    body,
    from: whatsappFrom,
    to: whatsappTo,
  });

  return {
    sid: message.sid,
    status: message.status,
    to: message.to,
    from: message.from,
    body: message.body,
    dateSent: message.dateCreated,
  };
}

export async function getMessageHistory(limit: number = 20) {
  const client = await getTwilioClient();
  const messages = await client.messages.list({ limit });

  return messages.map((m) => ({
    sid: m.sid,
    direction: m.direction,
    from: m.from,
    to: m.to,
    body: m.body,
    status: m.status,
    dateSent: m.dateSent,
    dateCreated: m.dateCreated,
    numSegments: m.numSegments,
    price: m.price,
    priceUnit: m.priceUnit,
  }));
}

export async function isTwilioConfigured(): Promise<boolean> {
  try {
    await getCredentials();
    return true;
  } catch {
    return false;
  }
}
