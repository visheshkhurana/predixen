import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getErrorMessage } from '@/lib/errors';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { 
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter 
} from '@/components/ui/dialog';
import { useToast } from '@/hooks/use-toast';
import { 
  Mail, UserPlus, Clock, CheckCircle, XCircle, MoreHorizontal, 
  Send, Trash2, RefreshCw, Copy
} from 'lucide-react';
import { 
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, 
  DropdownMenuSeparator, DropdownMenuTrigger 
} from '@/components/ui/dropdown-menu';
import { api } from '@/api/client';
import { format, formatDistanceToNow } from 'date-fns';

const ROLES = [
  { value: 'owner', label: 'Owner', color: 'bg-purple-500' },
  { value: 'admin', label: 'Admin', color: 'bg-blue-500' },
  { value: 'analyst', label: 'Analyst', color: 'bg-green-500' },
  { value: 'viewer', label: 'Viewer', color: 'bg-gray-500' },
];

export default function AdminInvites() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [isInviteDialogOpen, setIsInviteDialogOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('viewer');

  const { data: invites, isLoading } = useQuery({
    queryKey: ['/admin/invites'],
    queryFn: () => api.admin.invites.list(),
  });

  const createMutation = useMutation({
    mutationFn: ({ email, role }: { email: string; role: string }) =>
      api.admin.invites.create(email, role),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['/admin/invites'] });
      toast({ title: 'Invite sent successfully', description: `Invitation sent to ${inviteEmail}` });
      setIsInviteDialogOpen(false);
      setInviteEmail('');
      setInviteRole('viewer');
    },
    onError: (err: any) => {
      toast({ title: 'Failed to send invite', description: getErrorMessage(err, 'Failed to send invite'), variant: 'destructive' });
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (inviteId: number) => api.admin.invites.revoke(inviteId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/admin/invites'] });
      toast({ title: 'Invite revoked successfully' });
    },
    onError: (err: any) => {
      toast({ title: 'Failed to revoke invite', description: getErrorMessage(err, 'Failed to revoke invite'), variant: 'destructive' });
    },
  });

  const resendMutation = useMutation({
    mutationFn: (inviteId: number) => api.admin.invites.resend(inviteId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/admin/invites'] });
      toast({ title: 'Invite resent successfully' });
    },
    onError: (err: any) => {
      toast({ title: 'Failed to resend invite', description: getErrorMessage(err, 'Failed to resend invite'), variant: 'destructive' });
    },
  });

  const handleSendInvite = () => {
    if (!inviteEmail.trim()) {
      toast({ title: 'Email required', variant: 'destructive' });
      return;
    }
    createMutation.mutate({ email: inviteEmail.trim(), role: inviteRole });
  };

  const getRoleBadgeClass = (role: string) => {
    const roleConfig = ROLES.find((r) => r.value === role);
    return roleConfig?.color || 'bg-gray-500';
  };

  const pendingCount = invites?.filter(i => !i.accepted && !i.is_expired).length ?? 0;
  const acceptedCount = invites?.filter(i => i.accepted).length ?? 0;
  const expiredCount = invites?.filter(i => i.is_expired && !i.accepted).length ?? 0;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
            <Mail className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Invitations</h1>
            <p className="text-muted-foreground text-sm">Invite new users to the platform</p>
          </div>
        </div>
        <Button onClick={() => setIsInviteDialogOpen(true)} data-testid="button-invite-user">
          <UserPlus className="h-4 w-4 mr-2" />
          Invite User
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Pending</p>
                <p className="text-2xl font-bold text-yellow-600">{pendingCount}</p>
              </div>
              <Clock className="h-8 w-8 text-yellow-500/50" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Accepted</p>
                <p className="text-2xl font-bold text-green-600">{acceptedCount}</p>
              </div>
              <CheckCircle className="h-8 w-8 text-green-500/50" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Expired</p>
                <p className="text-2xl font-bold text-red-600">{expiredCount}</p>
              </div>
              <XCircle className="h-8 w-8 text-red-500/50" />
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Send className="h-5 w-5" />
            All Invitations
          </CardTitle>
          <CardDescription>Track and manage user invitations</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : invites && invites.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full" data-testid="table-invites">
                <thead>
                  <tr className="border-b text-left">
                    <th className="p-3 font-medium text-muted-foreground">Email</th>
                    <th className="p-3 font-medium text-muted-foreground">Role</th>
                    <th className="p-3 font-medium text-muted-foreground">Status</th>
                    <th className="p-3 font-medium text-muted-foreground">Invited By</th>
                    <th className="p-3 font-medium text-muted-foreground">Expires</th>
                    <th className="p-3 font-medium text-muted-foreground text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {invites.map((invite) => (
                    <tr 
                      key={invite.id} 
                      className="border-b hover:bg-muted/50 transition-colors" 
                      data-testid={`row-invite-${invite.id}`}
                    >
                      <td className="p-3">
                        <div className="flex items-center gap-3">
                          <div className="h-9 w-9 rounded-full bg-primary/10 flex items-center justify-center">
                            <Mail className="h-4 w-4 text-primary" />
                          </div>
                          <span className="font-medium text-sm">{invite.email}</span>
                        </div>
                      </td>
                      <td className="p-3">
                        <Badge variant="secondary" className={`${getRoleBadgeClass(invite.role)} text-white`}>
                          {ROLES.find(r => r.value === invite.role)?.label || invite.role}
                        </Badge>
                      </td>
                      <td className="p-3">
                        {invite.accepted ? (
                          <Badge variant="default" className="bg-green-500">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            Accepted
                          </Badge>
                        ) : invite.is_expired ? (
                          <Badge variant="destructive">
                            <XCircle className="h-3 w-3 mr-1" />
                            Expired
                          </Badge>
                        ) : (
                          <Badge variant="secondary" className="bg-yellow-500 text-white">
                            <Clock className="h-3 w-3 mr-1" />
                            Pending
                          </Badge>
                        )}
                      </td>
                      <td className="p-3 text-sm text-muted-foreground">
                        {invite.invited_by_email}
                      </td>
                      <td className="p-3 text-sm text-muted-foreground">
                        {invite.is_expired 
                          ? format(new Date(invite.expires_at), 'MMM d, yyyy')
                          : formatDistanceToNow(new Date(invite.expires_at), { addSuffix: true })
                        }
                      </td>
                      <td className="p-3 text-right">
                        {!invite.accepted && (
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button size="icon" variant="ghost" data-testid={`button-actions-${invite.id}`}>
                                <MoreHorizontal className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem 
                                onClick={() => resendMutation.mutate(invite.id)}
                                disabled={resendMutation.isPending}
                              >
                                <RefreshCw className="h-4 w-4 mr-2" />
                                Resend Invite
                              </DropdownMenuItem>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem 
                                onClick={() => revokeMutation.mutate(invite.id)}
                                className="text-red-600"
                                disabled={revokeMutation.isPending}
                              >
                                <Trash2 className="h-4 w-4 mr-2" />
                                Revoke Invite
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              <Mail className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <h3 className="text-lg font-medium mb-2">No invitations yet</h3>
              <p className="text-sm mb-4">Send your first invitation to grow your team</p>
              <Button onClick={() => setIsInviteDialogOpen(true)}>
                <UserPlus className="h-4 w-4 mr-2" />
                Invite User
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={isInviteDialogOpen} onOpenChange={setIsInviteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Invite New User</DialogTitle>
            <DialogDescription>
              Send an invitation to join the platform. The user will receive access based on the role you assign.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="invite-email">Email Address</Label>
              <Input
                id="invite-email"
                type="email"
                placeholder="user@company.com"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                data-testid="input-invite-email"
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="invite-role">Role</Label>
              <Select value={inviteRole} onValueChange={setInviteRole}>
                <SelectTrigger data-testid="select-invite-role">
                  <SelectValue placeholder="Select a role" />
                </SelectTrigger>
                <SelectContent>
                  {ROLES.map((role) => (
                    <SelectItem key={role.value} value={role.value}>
                      <div className="flex items-center gap-2">
                        <div className={`h-2 w-2 rounded-full ${role.color}`} />
                        {role.label}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                {inviteRole === 'owner' && 'Full access including billing and admin settings'}
                {inviteRole === 'admin' && 'Full access to platform features and user management'}
                {inviteRole === 'analyst' && 'Can create and manage companies, run simulations'}
                {inviteRole === 'viewer' && 'Read-only access to view data and reports'}
              </p>
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsInviteDialogOpen(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleSendInvite} 
              disabled={createMutation.isPending}
              data-testid="button-send-invite"
            >
              {createMutation.isPending ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Sending...
                </>
              ) : (
                <>
                  <Send className="h-4 w-4 mr-2" />
                  Send Invite
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
