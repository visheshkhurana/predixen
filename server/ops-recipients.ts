// Recipient list for the one-off ops email scripts (send-*.ts).
// Addresses are never committed: they come from the RECIPIENTS env var
// (comma-separated emails) or from RECIPIENTS_FILE, defaulting to the
// gitignored server/email/recipients.local.txt (one `email[,name[,id]]` per
// line, `#` comments allowed). Same format as server/email/recipients.py.
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';

export function loadRecipientEmails(): string[] {
  const fromEnv = (process.env.RECIPIENTS || '').trim();
  if (fromEnv) {
    return fromEnv.split(',').map((s) => s.trim()).filter(Boolean)
      .map((s) => (s.match(/<([^>]+)>/)?.[1] ?? s).trim());
  }
  const file = process.env.RECIPIENTS_FILE
    || path.join(process.cwd(), 'server', 'email', 'recipients.local.txt');
  if (!existsSync(file)) {
    throw new Error(`No recipients configured: set RECIPIENTS or create ${file}`);
  }
  return readFileSync(file, 'utf8').split('\n')
    .map((line) => line.split('#')[0].trim())
    .filter(Boolean)
    .map((line) => line.split(',')[0].trim());
}
