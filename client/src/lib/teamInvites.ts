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
      description: `We emailed ${email} a link to join. You can also copy the invite link and send it yourself.`,
    };
  }
  // The API returns the join link (invite_url), and the dialog shows it with a
  // Copy button, so point there instead of leaving the owner stuck.
  return {
    title: "Invite created, but the email couldn't be sent",
    description: `The invite for ${email} is pending. Copy the invite link and send it to them yourself.`,
  };
}

/**
 * POST /api/workspace/invites/{id}/resend renews the invite for 7 days and
 * issues a new link; it does not send an email yet (server/api/workspace.py),
 * so don't claim it did.
 */
export function inviteRenewedCopy(email: string): ToastCopy {
  return {
    title: 'Invite renewed',
    description: `The invite for ${email} is valid for another 7 days with a new link (older links stop working). We couldn't email it, so use Copy link to send it to them.`,
  };
}

export function inviteLinkCopiedCopy(email: string): ToastCopy {
  return {
    title: 'Invite link copied',
    description: `Send it to ${email}. It only works for that email address.`,
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

/** "17 Nov 2026": an absolute date, so a list never reads "15 minutes ago" for an old join. */
export function formatTeamDate(value: string | null | undefined): string | null {
  if (!value) return null;
  const d = parseServerDate(value);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

/**
 * The status line under a team member. Only an active member with a join date
 * "joined"; anyone still pending reads as invited, never as joined.
 */
export function memberStatusLine(member: { status?: string; joined_at?: string | null; invited_at?: string | null }): string | null {
  if (member.status && member.status !== 'active') {
    const invited = formatTeamDate(member.invited_at);
    const state = member.status === 'pending' ? 'pending' : member.status;
    return invited ? `Invited ${invited} · ${state}` : state;
  }
  const joined = formatTeamDate(member.joined_at);
  return joined ? `Joined ${joined}` : null;
}

/** The status line under a pending invitation. */
export function inviteStatusLine(invite: { invited_at?: string | null; expires_at?: string | null }): string {
  const invited = formatTeamDate(invite.invited_at);
  const expires = formatTeamDate(invite.expires_at);
  const head = invited ? `Invited ${invited} · pending` : 'Pending';
  return expires ? `${head} · expires ${expires}` : head;
}

/** Copy text, falling back to a hidden textarea where the Clipboard API is blocked. */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // fall through to the textarea path
  }
  try {
    if (typeof document === 'undefined') return false;
    const el = document.createElement('textarea');
    el.value = text;
    el.setAttribute('readonly', '');
    el.style.position = 'fixed';
    el.style.opacity = '0';
    document.body.appendChild(el);
    el.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(el);
    return ok;
  } catch {
    return false;
  }
}
