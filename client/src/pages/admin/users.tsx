import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { 
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter 
} from '@/components/ui/dialog';
import { useToast } from '@/hooks/use-toast';
import { 
  Users, UserCheck, UserX, Shield, Search, MoreHorizontal, 
  Building2, Calendar, MapPin, Monitor, Globe, Clock
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

function UserDetailModal({ userId, open, onClose }: { userId: number | null; open: boolean; onClose: () => void }) {
  const { data: user, isLoading } = useQuery({
    queryKey: ['/admin/users', userId],
    queryFn: () => userId ? api.admin.users.get(userId) : null,
    enabled: !!userId,
  });

  if (!userId) return null;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>User Details</DialogTitle>
          <DialogDescription>Detailed information about this user</DialogDescription>
        </DialogHeader>
        
        {isLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        ) : user ? (
          <div className="space-y-4">
            <div className="flex items-center gap-4">
              <Avatar className="h-16 w-16">
                <AvatarFallback className="text-lg bg-primary/10 text-primary">
                  {user.email.charAt(0).toUpperCase()}
                </AvatarFallback>
              </Avatar>
              <div>
                <h3 className="font-semibold">{user.email}</h3>
                <div className="flex items-center gap-2 mt-1">
                  <Badge variant="secondary" className={`${ROLES.find(r => r.value === user.role)?.color || 'bg-gray-500'} text-white`}>
                    {user.role}
                  </Badge>
                  <Badge variant={user.is_active ? 'default' : 'destructive'}>
                    {user.is_active ? 'Active' : 'Suspended'}
                  </Badge>
                </div>
              </div>
            </div>

            <div className="space-y-3 pt-4 border-t">
              <div className="flex items-center gap-3 text-sm">
                <Building2 className="h-4 w-4 text-muted-foreground" />
                <span>{user.company_count} companies</span>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <span>Joined {format(new Date(user.created_at), 'MMM d, yyyy')}</span>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <span>{user.total_logins} total logins</span>
              </div>
              
              {user.last_login && (
                <>
                  <div className="pt-3 border-t">
                    <p className="text-xs text-muted-foreground mb-2">Last Login</p>
                    <div className="space-y-2">
                      <div className="flex items-center gap-3 text-sm">
                        <Globe className="h-4 w-4 text-muted-foreground" />
                        <span>{user.last_login.ip_address || 'Unknown IP'}</span>
                      </div>
                      <div className="flex items-center gap-3 text-sm">
                        <Monitor className="h-4 w-4 text-muted-foreground" />
                        <span>{user.last_login.device_type} · {user.last_login.browser}</span>
                      </div>
                      {user.last_login.timestamp && (
                        <div className="flex items-center gap-3 text-sm text-muted-foreground">
                          <Clock className="h-4 w-4" />
                          <span>{formatDistanceToNow(new Date(user.last_login.timestamp), { addSuffix: true })}</span>
                        </div>
                      )}
                    </div>
                  </div>
                </>
              )}

              {user.companies && user.companies.length > 0 && (
                <div className="pt-3 border-t">
                  <p className="text-xs text-muted-foreground mb-2">Companies</p>
                  <div className="flex flex-wrap gap-2">
                    {user.companies.map((company) => (
                      <Badge key={company.id} variant="secondary">
                        {company.name}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : (
          <p className="text-muted-foreground">User not found</p>
        )}
        
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function AdminUsers() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('all');
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [editingUserId, setEditingUserId] = useState<number | null>(null);

  const { data: users, isLoading } = useQuery({
    queryKey: ['/admin/users'],
    queryFn: () => api.admin.users.list(),
  });

  const updateMutation = useMutation({
    mutationFn: ({ userId, data }: { userId: number; data: { role?: string; is_active?: boolean } }) =>
      api.admin.users.update(userId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/admin/users'] });
      toast({ title: 'User updated successfully' });
      setEditingUserId(null);
    },
    onError: (err: any) => {
      toast({ title: 'Failed to update user', description: err.message, variant: 'destructive' });
    },
  });

  const suspendMutation = useMutation({
    mutationFn: (userId: number) => api.admin.users.suspend(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/admin/users'] });
      queryClient.invalidateQueries({ queryKey: ['/admin/dashboard'] });
      toast({ title: 'User suspended successfully' });
    },
    onError: (err: any) => {
      toast({ title: 'Failed to suspend user', description: err.message, variant: 'destructive' });
    },
  });

  const activateMutation = useMutation({
    mutationFn: (userId: number) => api.admin.users.activate(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/admin/users'] });
      queryClient.invalidateQueries({ queryKey: ['/admin/dashboard'] });
      toast({ title: 'User activated successfully' });
    },
    onError: (err: any) => {
      toast({ title: 'Failed to activate user', description: err.message, variant: 'destructive' });
    },
  });

  const filteredUsers = users?.filter((user) => {
    const matchesSearch = user.email.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesRole = roleFilter === 'all' || user.role === roleFilter;
    return matchesSearch && matchesRole;
  });

  const getRoleBadgeClass = (role: string) => {
    const roleConfig = ROLES.find((r) => r.value === role);
    return roleConfig?.color || 'bg-gray-500';
  };

  const activeCount = users?.filter(u => u.is_active).length ?? 0;
  const suspendedCount = users?.filter(u => !u.is_active).length ?? 0;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
          <Users className="h-6 w-6 text-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-bold">User Management</h1>
          <p className="text-muted-foreground text-sm">Manage users, roles, and permissions</p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Users</p>
                <p className="text-2xl font-bold">{users?.length ?? 0}</p>
              </div>
              <Users className="h-8 w-8 text-muted-foreground/50" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Active</p>
                <p className="text-2xl font-bold text-green-600">{activeCount}</p>
              </div>
              <UserCheck className="h-8 w-8 text-green-500/50" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Suspended</p>
                <p className="text-2xl font-bold text-red-600">{suspendedCount}</p>
              </div>
              <UserX className="h-8 w-8 text-red-500/50" />
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                All Users
              </CardTitle>
              <CardDescription>Manage user accounts and permissions</CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input 
                  placeholder="Search users..." 
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 w-64"
                  data-testid="input-search-users"
                />
              </div>
              <Select value={roleFilter} onValueChange={setRoleFilter}>
                <SelectTrigger className="w-36" data-testid="select-filter-role">
                  <SelectValue placeholder="Filter by role" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Roles</SelectItem>
                  {ROLES.map((role) => (
                    <SelectItem key={role.value} value={role.value}>
                      {role.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full" data-testid="table-users">
                <thead>
                  <tr className="border-b text-left">
                    <th className="p-3 font-medium text-muted-foreground">User</th>
                    <th className="p-3 font-medium text-muted-foreground">Role</th>
                    <th className="p-3 font-medium text-muted-foreground">Companies</th>
                    <th className="p-3 font-medium text-muted-foreground">Status</th>
                    <th className="p-3 font-medium text-muted-foreground">Joined</th>
                    <th className="p-3 font-medium text-muted-foreground text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredUsers?.map((user) => (
                    <tr 
                      key={user.id} 
                      className="border-b hover:bg-muted/50 transition-colors" 
                      data-testid={`row-user-${user.id}`}
                    >
                      <td className="p-3">
                        <div className="flex items-center gap-3">
                          <Avatar className="h-9 w-9">
                            <AvatarFallback className="bg-primary/10 text-primary text-sm">
                              {user.email.charAt(0).toUpperCase()}
                            </AvatarFallback>
                          </Avatar>
                          <div>
                            <p className="font-medium text-sm">{user.email}</p>
                            <p className="text-xs text-muted-foreground">ID: {user.id}</p>
                          </div>
                        </div>
                      </td>
                      <td className="p-3">
                        {editingUserId === user.id ? (
                          <Select
                            defaultValue={user.role}
                            onValueChange={(value) => {
                              updateMutation.mutate({ userId: user.id, data: { role: value } });
                            }}
                          >
                            <SelectTrigger className="w-28" data-testid={`select-role-${user.id}`}>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {ROLES.map((role) => (
                                <SelectItem key={role.value} value={role.value}>
                                  {role.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        ) : (
                          <Badge variant="secondary" className={`${getRoleBadgeClass(user.role)} text-white`}>
                            {ROLES.find(r => r.value === user.role)?.label || user.role}
                          </Badge>
                        )}
                      </td>
                      <td className="p-3">
                        <span className="text-sm">{user.company_count}</span>
                      </td>
                      <td className="p-3">
                        <Badge variant={user.is_active ? 'default' : 'destructive'}>
                          {user.is_active ? 'Active' : 'Suspended'}
                        </Badge>
                      </td>
                      <td className="p-3 text-muted-foreground text-sm">
                        {format(new Date(user.created_at), 'MMM d, yyyy')}
                      </td>
                      <td className="p-3 text-right">
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button size="icon" variant="ghost" data-testid={`button-actions-${user.id}`}>
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => setSelectedUserId(user.id)}>
                              View Details
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => setEditingUserId(editingUserId === user.id ? null : user.id)}>
                              {editingUserId === user.id ? 'Done Editing' : 'Edit Role'}
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            {user.is_active ? (
                              <DropdownMenuItem 
                                onClick={() => suspendMutation.mutate(user.id)}
                                className="text-red-600"
                                disabled={suspendMutation.isPending}
                              >
                                <UserX className="h-4 w-4 mr-2" />
                                Suspend User
                              </DropdownMenuItem>
                            ) : (
                              <DropdownMenuItem 
                                onClick={() => activateMutation.mutate(user.id)}
                                className="text-green-600"
                                disabled={activateMutation.isPending}
                              >
                                <UserCheck className="h-4 w-4 mr-2" />
                                Activate User
                              </DropdownMenuItem>
                            )}
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              
              {filteredUsers?.length === 0 && (
                <div className="text-center py-8 text-muted-foreground">
                  <Users className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>No users found</p>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <UserDetailModal 
        userId={selectedUserId} 
        open={!!selectedUserId} 
        onClose={() => setSelectedUserId(null)} 
      />
    </div>
  );
}
