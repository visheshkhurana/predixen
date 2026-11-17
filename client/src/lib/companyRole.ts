/**
 * A teammate invited as a viewer can read a company but not change it
 * (the server refuses their writes). Screens use this to hide actions
 * that would only end in a "view-only access" error.
 */
export interface MemberLike {
  user_id: number;
  role: string;
  status?: string;
}

export function isViewOnlyMember(members: MemberLike[] | undefined, userId: number | undefined): boolean {
  if (!members || userId == null) return false;
  const me = members.find((m) => m.user_id === userId && (m.status ?? 'active') === 'active');
  return me?.role === 'viewer';
}
