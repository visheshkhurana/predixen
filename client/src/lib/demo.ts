// Demo sessions: per-visitor throwaway accounts on the reserved
// demo.founderconsole.invalid domain, plus the legacy shared account.
// Mirrors server/core/demo_workspace.py:is_demo_email.
export const LEGACY_DEMO_EMAIL = 'demo@founderconsole.ai';
export const DEMO_EMAIL_DOMAIN = 'demo.founderconsole.invalid';

export function isDemoEmail(email: string | null | undefined): boolean {
  const e = (email || '').trim().toLowerCase();
  return e === LEGACY_DEMO_EMAIL || e.endsWith('@' + DEMO_EMAIL_DOMAIN);
}
