// Settings → Team: invite copy (email_sent=false must not claim an email went
// out), server error messages, role lookup, and the wiring that mounts it.
import assert from "assert";
import { readFileSync } from "fs";
import {
  canManageTeam,
  inviteCreatedCopy,
  inviteRenewedCopy,
  roleForEmail,
  teamErrorMessage,
} from "../../client/src/lib/teamInvites";
import { ApiError } from "../../client/src/lib/errors";

const sent = inviteCreatedCopy("teammate@example.com", true);
assert.equal(sent.title, "Invite sent");
assert.ok(sent.description.includes("teammate@example.com"));

const notSent = inviteCreatedCopy("teammate@example.com", false);
assert.ok(/couldn't be sent/i.test(notSent.title), "email_sent=false says the email did not go out");
assert.ok(/pending/i.test(notSent.description), "and that the invite is pending");
assert.ok(!/^Invite sent$/.test(notSent.title));
assert.deepEqual(inviteCreatedCopy("a@b.co", undefined), inviteCreatedCopy("a@b.co", false), "unknown = not sent");
assert.ok(!/emailed/i.test(inviteRenewedCopy("a@b.co").description), "resend doesn't email yet; don't claim it");

// apiRequest throws "400: Bad Request" with the sentence in .detail.
assert.equal(teamErrorMessage(new ApiError(400, "400: Bad Request", "Invitation already pending")), "Invitation already pending");
assert.equal(teamErrorMessage(new ApiError(403, "403: Forbidden", "Requires admin role or higher")), "Requires admin role or higher");
assert.equal(
  teamErrorMessage(new ApiError(422, "422: Unprocessable Entity", [{ loc: ["body", "email"], msg: "value is not a valid email address" }])),
  "Please use a real email address you can receive mail at.",
);
assert.equal(teamErrorMessage(new ApiError(0, "Network request failed: offline")), "Network request failed: offline");
assert.equal(teamErrorMessage(new ApiError(500, "500: Internal Server Error")), "Internal Server Error");
assert.equal(teamErrorMessage(null), "Something went wrong. Please try again.");

const members = [
  { email: "Owner@Example.com", role: "owner" },
  { email: "ed@example.com", role: "editor" },
];
assert.equal(roleForEmail(members, "owner@example.com"), "owner");
assert.equal(roleForEmail(members, "ed@example.com"), "editor");
assert.equal(roleForEmail(members, "nobody@example.com"), "viewer");
assert.equal(roleForEmail(undefined, "owner@example.com"), "viewer");
assert.ok(canManageTeam("owner") && canManageTeam("admin"));
assert.ok(!canManageTeam("editor") && !canManageTeam("viewer"));

// Wiring: the Settings page mounts TeamWorkspace on a Team tab with real hooks,
// and sample companies get a note instead of invites.
const settings = readFileSync(new URL("../../client/src/pages/settings.tsx", import.meta.url), "utf8");
assert.ok(settings.includes("<TeamWorkspace"), "Settings renders TeamWorkspace");
assert.ok(/TabsTrigger value="team"/.test(settings), "Settings has a Team tab");
for (const hook of ["useWorkspaceMembers", "useWorkspaceInvites", "useInviteMember", "useRevokeInvite", "useResendInvite"]) {
  assert.ok(settings.includes(`${hook}(`), `Settings calls ${hook}`);
}
assert.ok(settings.includes("is_sample"), "sample companies are handled");
assert.ok(settings.includes("inviteCreatedCopy("), "invite success uses email_sent-aware copy");
console.log("team-invites: ok");
import { parseServerDate } from "../../client/src/lib/teamInvites";
assert.equal(parseServerDate("2026-11-17T03:00:00.5").toISOString(), "2026-11-17T03:00:00.500Z", "naive = UTC");
assert.equal(parseServerDate("2026-11-17T03:00:00Z").toISOString(), "2026-11-17T03:00:00.000Z");
assert.equal(parseServerDate("2026-11-17T07:00:00+04:00").toISOString(), "2026-11-17T03:00:00.000Z");
console.log("team-invites dates: ok");

// Copy invite link + honest status lines (tester findings 2026-11-18).
import {
  formatTeamDate,
  inviteLinkCopiedCopy,
  inviteStatusLine,
  memberStatusLine,
} from "../../client/src/lib/teamInvites";
assert.ok(/copy the invite link/i.test(inviteCreatedCopy("a@b.co", false).description), "no-email invite points at Copy link");
assert.ok(inviteLinkCopiedCopy("a@b.co").description.includes("a@b.co"));
assert.equal(formatTeamDate(null), null);
assert.equal(formatTeamDate("not a date"), null);
assert.ok(/2026/.test(formatTeamDate("2026-11-17T12:00:00")!), "absolute date, not relative");
const pendingMember = memberStatusLine({ status: "pending", invited_at: "2026-11-17T12:00:00", joined_at: "2026-11-18T12:00:00" });
assert.ok(pendingMember!.startsWith("Invited ") && pendingMember!.endsWith("· pending"), "pending never reads as joined");
assert.ok(!/joined|ago/i.test(pendingMember!));
const activeMember = memberStatusLine({ status: "active", invited_at: "2026-11-01T12:00:00", joined_at: "2026-11-17T12:00:00" });
assert.ok(activeMember!.startsWith("Joined ") && !/ago/.test(activeMember!), "members show their join date");
assert.equal(memberStatusLine({ status: "active", joined_at: undefined }), null);
const inviteLine = inviteStatusLine({ invited_at: "2026-11-17T12:00:00", expires_at: "2026-11-24T12:00:00" });
assert.ok(/^Invited .+ · pending · expires .+2026$/.test(inviteLine), inviteLine);
assert.equal(inviteStatusLine({}), "Pending");

const team = readFileSync(new URL("../../client/src/components/TeamWorkspace.tsx", import.meta.url), "utf8");
assert.ok(team.includes("button-copy-invite-link-"), "each pending invite has Copy link");
assert.ok(team.includes("button-copy-new-invite-link"), "a new invite offers its link right away");
assert.ok(!team.includes("formatDistanceToNow"), "no relative 'x minutes ago' join times");
assert.ok(settings.includes("fetchInviteLink("), "Copy link fetches the link from the owner/admin endpoint");
console.log("team-invites copy-link: ok");
