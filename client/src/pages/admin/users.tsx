import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';
import { Users, UserCheck, UserX, Shield } from 'lucide-react';
import { api } from '@/api/client';

const ROLES = [
  { value: 'owner', label: 'Owner', color: 'bg-purple-500' },
  { value: 'admin', label: 'Admin', color: 'bg-blue-500' },
  { value: 'analyst', label: 'Analyst', color: 'bg-green-500' },
  { value: 'viewer', label: 'Viewer', color: 'bg-gray-500' },
];

export default function AdminUsers() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
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
      toast({ title: 'User suspended' });
    },
    onError: (err: any) => {
      toast({ title: 'Failed to suspend user', description: err.message, variant: 'destructive' });
    },
  });

  const activateMutation = useMutation({
    mutationFn: (userId: number) => api.admin.users.activate(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/admin/users'] });
      toast({ title: 'User activated' });
    },
    onError: (err: any) => {
      toast({ title: 'Failed to activate user', description: err.message, variant: 'destructive' });
    },
  });

  const getRoleBadge = (role: string) => {
    const roleConfig = ROLES.find((r) => r.value === role) || ROLES[3];
    return (
      <Badge variant="secondary" className={`${roleConfig.color} text-white`}>
        {roleConfig.label}
      </Badge>
    );
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <Users className="h-8 w-8 text-primary" />
        <div>
          <h1 className="text-2xl font-bold">User Management</h1>
          <p className="text-muted-foreground">Manage users and their roles</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            All Users ({users?.length ?? 0})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full" data-testid="table-users">
                <thead>
                  <tr className="border-b text-left">
                    <th className="p-3 font-medium">Email</th>
                    <th className="p-3 font-medium">Role</th>
                    <th className="p-3 font-medium">Companies</th>
                    <th className="p-3 font-medium">Status</th>
                    <th className="p-3 font-medium">Created</th>
                    <th className="p-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users?.map((user) => (
                    <tr key={user.id} className="border-b" data-testid={`row-user-${user.id}`}>
                      <td className="p-3">{user.email}</td>
                      <td className="p-3">
                        {editingUserId === user.id ? (
                          <Select
                            defaultValue={user.role}
                            onValueChange={(value) => {
                              updateMutation.mutate({ userId: user.id, data: { role: value } });
                            }}
                          >
                            <SelectTrigger className="w-32" data-testid={`select-role-${user.id}`}>
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
                          getRoleBadge(user.role)
                        )}
                      </td>
                      <td className="p-3">{user.company_count}</td>
                      <td className="p-3">
                        <Badge variant={user.is_active ? 'default' : 'destructive'}>
                          {user.is_active ? 'Active' : 'Suspended'}
                        </Badge>
                      </td>
                      <td className="p-3 text-muted-foreground text-sm">
                        {new Date(user.created_at).toLocaleDateString()}
                      </td>
                      <td className="p-3">
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => setEditingUserId(editingUserId === user.id ? null : user.id)}
                            data-testid={`button-edit-${user.id}`}
                          >
                            {editingUserId === user.id ? 'Done' : 'Edit Role'}
                          </Button>
                          {user.is_active ? (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => suspendMutation.mutate(user.id)}
                              disabled={suspendMutation.isPending}
                              data-testid={`button-suspend-${user.id}`}
                            >
                              <UserX className="h-4 w-4 mr-1" />
                              Suspend
                            </Button>
                          ) : (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => activateMutation.mutate(user.id)}
                              disabled={activateMutation.isPending}
                              data-testid={`button-activate-${user.id}`}
                            >
                              <UserCheck className="h-4 w-4 mr-1" />
                              Activate
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
