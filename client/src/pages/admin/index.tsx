import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Users, Building2, CreditCard, Activity, BarChart3, Shield, TrendingUp } from 'lucide-react';
import { api } from '@/api/client';

export default function AdminDashboard() {
  const { data: metrics, isLoading } = useQuery({
    queryKey: ['/admin/dashboard'],
    queryFn: () => api.admin.dashboard(),
  });

  const statCards = [
    { 
      title: 'Total Users', 
      value: metrics?.total_users ?? 0, 
      icon: Users, 
      description: `${metrics?.active_users ?? 0} active` 
    },
    { 
      title: 'Companies', 
      value: metrics?.total_companies ?? 0, 
      icon: Building2, 
      description: 'Total registered' 
    },
    { 
      title: 'Active Subscriptions', 
      value: metrics?.total_subscriptions ?? 0, 
      icon: CreditCard, 
      description: 'Paying customers' 
    },
    { 
      title: 'MRR', 
      value: `$${(metrics?.mrr ?? 0).toLocaleString()}`, 
      icon: TrendingUp, 
      description: 'Monthly recurring revenue' 
    },
    { 
      title: 'Active Simulations', 
      value: metrics?.active_simulations ?? 0, 
      icon: Activity, 
      description: 'Last 7 days' 
    },
    { 
      title: 'Truth Scans Today', 
      value: metrics?.truth_scans_today ?? 0, 
      icon: BarChart3, 
      description: 'Today' 
    },
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <Shield className="h-8 w-8 text-primary" />
        <div>
          <h1 className="text-2xl font-bold">Admin Dashboard</h1>
          <p className="text-muted-foreground">System overview and management</p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {statCards.map((stat) => (
          <Card key={stat.title} data-testid={`card-stat-${stat.title.toLowerCase().replace(/\s/g, '-')}`}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 gap-2">
              <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
              <stat.icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <Skeleton className="h-8 w-24" />
              ) : (
                <>
                  <div className="text-2xl font-bold" data-testid={`text-value-${stat.title.toLowerCase().replace(/\s/g, '-')}`}>
                    {stat.value}
                  </div>
                  <p className="text-xs text-muted-foreground">{stat.description}</p>
                </>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
