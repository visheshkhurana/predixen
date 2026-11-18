import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Skeleton } from '@/components/ui/skeleton';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Users, UserPlus, MoreVertical, Shield, Edit, Trash2, Mail, Clock, XCircle, AlertCircle, Link2, CheckCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { copyToClipboard, inviteStatusLine, memberStatusLine } from '@/lib/teamInvites';

export interface TeamMember {
  id: number;
  user_id: number;
  email: string;
  role: 'owner' | 'admin' | 'editor' | 'viewer';
  status: 'active' | 'pending' | 'suspended';
  invited_at: string;
  joined_at?: string;
}

export interface WorkspaceInvite {
  id: number;
  email: string;
  role: 'admin' | 'editor' | 'viewer';
  status: 'pending' | 'accepted' | 'expired';
  invited_at: string;
  expires_at: string;
}

interface TeamWorkspaceProps {
  companyId: number;
  companyName: string;
  members: TeamMember[];
  invites: WorkspaceInvite[];
  isLoading: boolean;
  currentUserEmail: string;
  currentUserRole: string;
  /** Resolves with the invite's accept link when the server returns one. */
  onInviteMember: (email: string, role: string) => Promise<string | void>;
  onUpdateRole: (memberId: number, role: string) => Promise<void>;
  onRemoveMember: (memberId: number) => Promise<void>;
  onRevokeInvite: (inviteId: number) => Promise<void>;
  onResendInvite: (inviteId: number) => Promise<void>;
  onCopyInviteLink?: (inviteId: number) => Promise<void>;
}

const ROLE_DESCRIPTIONS = {
  owner: 'Full access including billing and team management',
  admin: 'Manage team members, scenarios, and all settings',
  editor: 'Create and edit scenarios, run simulations',
  viewer: 'View scenarios and simulation results only',
};

const ROLE_COLORS = {
  owner: 'bg-purple-500',
  admin: 'bg-blue-500',
  editor: 'bg-green-500',
  viewer: 'bg-gray-500',
};

function getInitials(email: string): string {
  const parts = email.split('@')[0].split(/[._-]/);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return email.substring(0, 2).toUpperCase();
}

export function TeamWorkspace({
  companyId,
  companyName,
  members,
  invites,
  isLoading,
  currentUserEmail,
  currentUserRole,
  onInviteMember,
  onUpdateRole,
  onRemoveMember,
  onRevokeInvite,
  onResendInvite,
  onCopyInviteLink,
}: TeamWorkspaceProps) {
  const [inviteDialogOpen, setInviteDialogOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<string>('viewer');
  const [isInviting, setIsInviting] = useState(false);
  const [inviteError, setInviteError] = useState<string | null>(null);
  // Set right after an invite is created, so the dialog can offer its link.
  const [createdInvite, setCreatedInvite] = useState<{ email: string; url: string } | null>(null);
  const [linkCopied, setLinkCopied] = useState(false);

  const closeInviteDialog = (open: boolean) => {
    setInviteDialogOpen(open);
    if (!open) {
      setCreatedInvite(null);
      setLinkCopied(false);
      setInviteError(null);
    }
  };

  const canManageTeam = ['owner', 'admin'].includes(currentUserRole);
  const pendingInvites = invites.filter(i => i.status === 'pending');

  const handleInvite = async () => {
    if (!inviteEmail.trim()) return;
    
    setIsInviting(true);
    setInviteError(null);
    
    try {
      const url = await onInviteMember(inviteEmail, inviteRole);
      if (url) {
        setCreatedInvite({ email: inviteEmail.trim(), url });
        setLinkCopied(false);
      } else {
        setInviteDialogOpen(false);
      }
      setInviteEmail('');
      setInviteRole('viewer');
    } catch (err: any) {
      setInviteError((err instanceof Error ? err.message : typeof err === 'string' ? err : '') || 'Failed to send invite');
    } finally {
      setIsInviting(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div className="flex items-center gap-2">
              <Users className="h-5 w-5 text-primary" />
              <div>
                <CardTitle className="text-lg">Team Members</CardTitle>
                <CardDescription>Manage who has access to {companyName}</CardDescription>
              </div>
            </div>
            {canManageTeam && (
              <Dialog open={inviteDialogOpen} onOpenChange={closeInviteDialog}>
                <DialogTrigger asChild>
                  <Button data-testid="button-invite-member">
                    <UserPlus className="h-4 w-4 mr-2" />
                    Invite Member
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Invite Team Member</DialogTitle>
                    <DialogDescription>
                      Send an invitation to join {companyName} workspace
                    </DialogDescription>
                  </DialogHeader>
                  {createdInvite ? (
                  <>
                  <div className="space-y-3 py-4" data-testid="invite-created">
                    <p className="text-sm">
                      Invite created for <span className="font-medium">{createdInvite.email}</span>.
                      Share this link with them. It only works for that email address and expires in 7 days.
                    </p>
                    <div className="flex items-center gap-2">
                      <Input
                        readOnly
                        value={createdInvite.url}
                        onFocus={(e) => e.currentTarget.select()}
                        aria-label="Invite link"
                        data-testid="input-invite-link"
                      />
                      <Button
                        variant="outline"
                        onClick={async () => setLinkCopied(await copyToClipboard(createdInvite.url))}
                        data-testid="button-copy-new-invite-link"
                      >
                        {linkCopied ? <CheckCircle className="h-4 w-4 mr-2" /> : <Link2 className="h-4 w-4 mr-2" />}
                        {linkCopied ? 'Copied' : 'Copy link'}
                      </Button>
                    </div>
                  </div>
                  <DialogFooter>
                    <Button onClick={() => closeInviteDialog(false)} data-testid="button-invite-done">
                      Done
                    </Button>
                  </DialogFooter>
                  </>
                  ) : (
                  <>
                  <div className="space-y-4 py-4">
                    {inviteError && (
                      <Alert variant="destructive">
                        <AlertCircle className="h-4 w-4" />
                        <AlertDescription>{inviteError}</AlertDescription>
                      </Alert>
                    )}
                    <div className="space-y-2">
                      <Label htmlFor="invite-email">Email Address</Label>
                      <Input
                        id="invite-email"
                        type="email"
                        placeholder="colleague@company.com"
                        value={inviteEmail}
                        onChange={(e) => setInviteEmail(e.target.value)}
                        data-testid="input-invite-email"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="invite-role">Role</Label>
                      <Select value={inviteRole} onValueChange={setInviteRole}>
                        <SelectTrigger data-testid="select-invite-role">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="admin">
                            <div className="flex items-center gap-2">
                              <span className={cn('w-2 h-2 rounded-full', ROLE_COLORS.admin)} />
                              Admin
                            </div>
                          </SelectItem>
                          <SelectItem value="editor">
                            <div className="flex items-center gap-2">
                              <span className={cn('w-2 h-2 rounded-full', ROLE_COLORS.editor)} />
                              Editor
                            </div>
                          </SelectItem>
                          <SelectItem value="viewer">
                            <div className="flex items-center gap-2">
                              <span className={cn('w-2 h-2 rounded-full', ROLE_COLORS.viewer)} />
                              Viewer
                            </div>
                          </SelectItem>
                        </SelectContent>
                      </Select>
                      <p className="text-xs text-muted-foreground">
                        {ROLE_DESCRIPTIONS[inviteRole as keyof typeof ROLE_DESCRIPTIONS]}
                      </p>
                    </div>
                  </div>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => closeInviteDialog(false)}>
                      Cancel
                    </Button>
                    <Button 
                      onClick={handleInvite} 
                      disabled={!inviteEmail.trim() || isInviting}
                      data-testid="button-send-invite"
                    >
                      <Mail className="h-4 w-4 mr-2" />
                      {isInviting ? 'Sending...' : 'Send Invite'}
                    </Button>
                  </DialogFooter>
                  </>
                  )}
                </DialogContent>
              </Dialog>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
            </div>
          ) : (
            // Plain overflow, not ScrollArea: Radix's table-layout viewport stops
            // long emails from truncating at phone width.
            <div className="max-h-[300px] overflow-y-auto">
              <div className="space-y-2">
                {members.map(member => (
                  <div
                    key={member.id}
                    className="flex items-center justify-between gap-2 sm:gap-4 p-3 rounded-lg border"
                    data-testid={`member-row-${member.id}`}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <Avatar>
                        <AvatarFallback>{getInitials(member.email)}</AvatarFallback>
                      </Avatar>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="font-medium truncate" title={member.email}>{member.email}</span>
                          {member.email === currentUserEmail && (
                            <Badge variant="outline" className="text-xs shrink-0">You</Badge>
                          )}
                        </div>
                        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
                          <Badge variant="secondary" className="gap-1">
                            <span className={cn('w-1.5 h-1.5 rounded-full', ROLE_COLORS[member.role])} />
                            {member.role}
                          </Badge>
                          {memberStatusLine(member) && (
                            <span className="flex items-center gap-1" data-testid={`member-status-${member.id}`}>
                              <Clock className="h-3 w-3" />
                              {memberStatusLine(member)}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    {canManageTeam && member.role !== 'owner' && member.email !== currentUserEmail && (
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon" className="shrink-0" aria-label={`Manage ${member.email}`}>
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => onUpdateRole(member.id, 'admin')}>
                            <Shield className="h-4 w-4 mr-2" />
                            Make Admin
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => onUpdateRole(member.id, 'editor')}>
                            <Edit className="h-4 w-4 mr-2" />
                            Make Editor
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => onUpdateRole(member.id, 'viewer')}>
                            <Users className="h-4 w-4 mr-2" />
                            Make Viewer
                          </DropdownMenuItem>
                          <DropdownMenuItem 
                            onClick={() => onRemoveMember(member.id)}
                            className="text-destructive"
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            Remove
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {pendingInvites.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Mail className="h-4 w-4" />
              Pending Invitations
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {pendingInvites.map(invite => (
                <div
                  key={invite.id}
                  className="flex items-center justify-between gap-2 sm:gap-4 p-3 rounded-lg border border-dashed"
                  data-testid={`invite-row-${invite.id}`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <Avatar className="opacity-50">
                      <AvatarFallback>{getInitials(invite.email)}</AvatarFallback>
                    </Avatar>
                    <div className="min-w-0">
                      <span className="block font-medium truncate" title={invite.email}>{invite.email}</span>
                      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
                        <Badge variant="outline" className="gap-1">
                          <span className={cn('w-1.5 h-1.5 rounded-full', ROLE_COLORS[invite.role])} />
                          {invite.role}
                        </Badge>
                        <span data-testid={`invite-status-${invite.id}`}>{inviteStatusLine(invite)}</span>
                      </div>
                    </div>
                  </div>
                  {canManageTeam && (
                    <div className="flex items-center gap-1 shrink-0">
                      {onCopyInviteLink && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onCopyInviteLink(invite.id)}
                          aria-label={`Copy invite link for ${invite.email}`}
                          data-testid={`button-copy-invite-link-${invite.id}`}
                        >
                          <Link2 className="h-4 w-4 sm:mr-1" />
                          <span className="hidden sm:inline">Copy link</span>
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onResendInvite(invite.id)}
                        aria-label={`Resend invite to ${invite.email}`}
                        data-testid={`button-resend-invite-${invite.id}`}
                      >
                        <Mail className="h-4 w-4 sm:mr-1" />
                        <span className="hidden sm:inline">Resend</span>
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onRevokeInvite(invite.id)}
                        className="text-destructive"
                        aria-label={`Revoke invite to ${invite.email}`}
                        data-testid={`button-revoke-invite-${invite.id}`}
                      >
                        <XCircle className="h-4 w-4" />
                      </Button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
