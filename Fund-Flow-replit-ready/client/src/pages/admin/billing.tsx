import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';
import { CreditCard, DollarSign } from 'lucide-react';
import { api } from '@/api/client';

const PLANS = [
  { value: 'free', label: 'Free', price: 0 },
  { value: 'starter', label: 'Starter', price: 49 },
  { value: 'pro', label: 'Pro', price: 149 },
  { value: 'enterprise', label: 'Enterprise', price: 499 },
];

const STATUS_COLORS: Record<string, string> = {
  active: 'bg-green-500',
  past_due: 'bg-yellow-500',
  canceled: 'bg-red-500',
  trialing: 'bg-blue-500',
};

export default function AdminBilling() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [editingId, setEditingId] = useState<number | null>(null);

  const { data: subscriptions, isLoading } = useQuery({
    queryKey: ['/admin/subscriptions'],
    queryFn: () => api.admin.subscriptions.list(),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: { plan?: string; seats?: number; status?: string } }) =>
      api.admin.subscriptions.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/admin/subscriptions'] });
      toast({ title: 'Subscription updated' });
      setEditingId(null);
    },
    onError: (err: any) => {
      toast({ title: 'Failed to update subscription', description: err.message, variant: 'destructive' });
    },
  });

  const totalMRR = subscriptions?.reduce((sum, s) => sum + (s.status === 'active' ? s.monthly_price : 0), 0) ?? 0;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <CreditCard className="h-8 w-8 text-primary" />
        <div>
          <h1 className="text-2xl font-bold">Billing Management</h1>
          <p className="text-muted-foreground">Manage subscriptions and billing</p>
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-2">
          <CardTitle className="flex items-center gap-2">
            <DollarSign className="h-5 w-5" />
            MRR: ${totalMRR.toLocaleString()}
          </CardTitle>
          <Badge variant="outline">{subscriptions?.length ?? 0} subscriptions</Badge>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : subscriptions?.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No subscriptions found. Create subscriptions when users upgrade their plans.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full" data-testid="table-subscriptions">
                <thead>
                  <tr className="border-b text-left">
                    <th className="p-3 font-medium">User</th>
                    <th className="p-3 font-medium">Company</th>
                    <th className="p-3 font-medium">Plan</th>
                    <th className="p-3 font-medium">Status</th>
                    <th className="p-3 font-medium">Seats</th>
                    <th className="p-3 font-medium">Price</th>
                    <th className="p-3 font-medium">Renewal</th>
                    <th className="p-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {subscriptions?.map((sub) => (
                    <tr key={sub.id} className="border-b" data-testid={`row-subscription-${sub.id}`}>
                      <td className="p-3">{sub.user_email || '-'}</td>
                      <td className="p-3">{sub.company_name || '-'}</td>
                      <td className="p-3">
                        {editingId === sub.id ? (
                          <Select
                            defaultValue={sub.plan}
                            onValueChange={(value) => {
                              const plan = PLANS.find((p) => p.value === value);
                              updateMutation.mutate({ id: sub.id, data: { plan: value } });
                            }}
                          >
                            <SelectTrigger className="w-32" data-testid={`select-plan-${sub.id}`}>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {PLANS.map((plan) => (
                                <SelectItem key={plan.value} value={plan.value}>
                                  {plan.label} (${plan.price})
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        ) : (
                          <Badge variant="secondary">{sub.plan}</Badge>
                        )}
                      </td>
                      <td className="p-3">
                        <Badge className={`${STATUS_COLORS[sub.status] || 'bg-gray-500'} text-white`}>
                          {sub.status}
                        </Badge>
                      </td>
                      <td className="p-3">{sub.seats}</td>
                      <td className="p-3">${sub.monthly_price}/mo</td>
                      <td className="p-3 text-muted-foreground text-sm">
                        {sub.current_period_end
                          ? new Date(sub.current_period_end).toLocaleDateString()
                          : '-'}
                      </td>
                      <td className="p-3">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setEditingId(editingId === sub.id ? null : sub.id)}
                          data-testid={`button-edit-${sub.id}`}
                        >
                          {editingId === sub.id ? 'Done' : 'Edit'}
                        </Button>
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
