import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Users, UserPlus, MoreVertical, Shield, Edit, Trash2, Mail, Clock, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';

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
  onInviteMember: (email: string, role: string) => Promise<void>;
  onUpdateRole: (memberId: number, role: string) => Promise<void>;
  onRemoveMember: (memberId: number) => Promise<void>;
  onRevokeInvite: (inviteId: number) => Promise<void>;
  onResendInvite: (inviteId: number) => Promise<void>;
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
}: TeamWorkspaceProps) {
  const [inviteDialogOpen, setInviteDialogOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<string>('viewer');
  const [isInviting, setIsInviting] = useState(false);
  const [inviteError, setInviteError] = useState<string | null>(null);

  const canManageTeam = ['owner', 'admin'].includes(currentUserRole);
  const pendingInvites = invites.filter(i => i.status === 'pending');

  const handleInvite = async () => {
    if (!inviteEmail.trim()) return;
    
    setIsInviting(true);
    setInviteError(null);
    
    try {
      await onInviteMember(inviteEmail, inviteRole);
      setInviteDialogOpen(false);
      setInviteEmail('');
      setInviteRole('viewer');
    } catch (err: any) {
      setInviteError(err.message || 'Failed to send invite');
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
              <Dialog open={inviteDialogOpen} onOpenChange={setInviteDialogOpen}>
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
                    <Button variant="outline" onClick={() => setInviteDialogOpen(false)}>
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
            <ScrollArea className="h-[300px]">
              <div className="space-y-2">
                {members.map(member => (
                  <div
                    key={member.id}
                    className="flex items-center justify-between gap-4 p-3 rounded-lg border"
                    data-testid={`member-row-${member.id}`}
                  >
                    <div className="flex items-center gap-3">
                      <Avatar>
                        <AvatarFallback>{getInitials(member.email)}</AvatarFallback>
                      </Avatar>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{member.email}</span>
                          {member.email === currentUserEmail && (
                            <Badge variant="outline" className="text-xs">You</Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <Badge variant="secondary" className="gap-1">
                            <span className={cn('w-1.5 h-1.5 rounded-full', ROLE_COLORS[member.role])} />
                            {member.role}
                          </Badge>
                          {member.joined_at && (
                            <span className="flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              Joined {formatDistanceToNow(new Date(member.joined_at), { addSuffix: true })}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    {canManageTeam && member.role !== 'owner' && member.email !== currentUserEmail && (
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
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
            </ScrollArea>
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
                  className="flex items-center justify-between gap-4 p-3 rounded-lg border border-dashed"
                >
                  <div className="flex items-center gap-3">
                    <Avatar className="opacity-50">
                      <AvatarFallback>{getInitials(invite.email)}</AvatarFallback>
                    </Avatar>
                    <div>
                      <span className="font-medium">{invite.email}</span>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <Badge variant="outline" className="gap-1">
                          <span className={cn('w-1.5 h-1.5 rounded-full', ROLE_COLORS[invite.role])} />
                          {invite.role}
                        </Badge>
                        <span>Invited {formatDistanceToNow(new Date(invite.invited_at), { addSuffix: true })}</span>
                      </div>
                    </div>
                  </div>
                  {canManageTeam && (
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onResendInvite(invite.id)}
                      >
                        <Mail className="h-4 w-4 mr-1" />
                        Resend
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onRevokeInvite(invite.id)}
                        className="text-destructive"
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
