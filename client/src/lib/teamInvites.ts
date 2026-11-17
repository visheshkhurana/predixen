// Copy and small rules for the Settings → Team tab (TeamWorkspace).
// Pure so server/tests/team-invites.test.ts can check it without a browser.
import { validationDetailMessage } from './errors';

export interface ToastCopy {
  title: string;
  description: string;
}

/** Success feedback for POST /api/workspace/companies/{id}/invite. */
export function inviteCreatedCopy(email: string, emailSent: boolean | undefined): ToastCopy {
  if (emailSent) {
    return {
      title: 'Invite sent',
      description: `We emailed ${email} a link to join.`,
    };
  }
  // The API doesn't return the join link, so there's nothing to copy: say
  // plainly that the email did not go out and the invite is waiting.
  return {
    title: "Invite created, but the email couldn't be sent",
    description: `The invite for ${email} is pending. We couldn't email it, so let them know you've invited them.`,
  };
}

/**
 * POST /api/workspace/invites/{id}/resend renews the invite for 7 days; it
 * does not send an email yet (server/api/workspace.py), so don't claim it did.
 */
export function inviteRenewedCopy(email: string): ToastCopy {
  return {
    title: 'Invite renewed',
    description: `The invite for ${email} is valid for another 7 days. We couldn't email it, so let them know it's waiting.`,
  };
}

/**
 * The server's own sentence for a failed workspace call. apiRequest throws an
 * ApiError whose message is "400: Bad Request" for string details, with the
 * real text in `.detail`; 422s carry a pydantic list.
 */
export function teamErrorMessage(err: unknown, fallback = 'Something went wrong. Please try again.'): string {
  const e = err as { detail?: unknown; message?: unknown } | null | undefined;
  const detail = e?.detail;
  if (typeof detail === 'string' && detail.trim()) return detail;
  const validation = validationDetailMessage(detail);
  if (validation) return validation;
  if (detail && typeof detail === 'object' && typeof (detail as { message?: unknown }).message === 'string') {
    return (detail as { message: string }).message;
  }
  if (typeof e?.message === 'string' && e.message.trim()) {
    return e.message.replace(/^\d{3}:\s*/, '');
  }
  return fallback;
}

/** The signed-in user's role in this workspace, from the members list. */
export function roleForEmail(
  members: ReadonlyArray<{ email: string; role: string }> | undefined,
  email: string | null | undefined,
): string {
  if (!members || !email) return 'viewer';
  const me = members.find((m) => m.email.toLowerCase() === email.toLowerCase());
  return me?.role ?? 'viewer';
}

export function canManageTeam(role: string): boolean {
  return role === 'owner' || role === 'admin';
}

/**
 * The workspace API returns naive UTC timestamps ("2026-11-17T03:00:00.123"),
 * which `new Date()` would read as local time. Treat a string with no zone as UTC.
 */
export function parseServerDate(value: string): Date {
  const hasZone = /([zZ]|[+-]\d{2}:?\d{2})$/.test(value);
  return new Date(hasZone ? value : `${value}Z`);
}
