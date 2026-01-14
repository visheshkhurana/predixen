import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  Users, Building2, CreditCard, Activity, BarChart3, Shield, TrendingUp, 
  CheckCircle, XCircle, Clock, RefreshCw
} from 'lucide-react';
import { api } from '@/api/client';
import { format, formatDistanceToNow } from 'date-fns';
import { 
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  AreaChart, Area
} from 'recharts';

function StatCard({ 
  title, 
  value, 
  icon: Icon, 
  description, 
  trend,
  isLoading 
}: { 
  title: string; 
  value: string | number; 
  icon: any; 
  description: string; 
  trend?: { value: number; isPositive: boolean };
  isLoading: boolean;
}) {
  return (
    <Card className="hover-elevate transition-all" data-testid={`card-stat-${title.toLowerCase().replace(/\s/g, '-')}`}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 gap-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center">
          <Icon className="h-4 w-4 text-primary" />
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-8 w-24" />
        ) : (
          <>
            <div className="flex items-baseline gap-2">
              <div className="text-2xl font-bold" data-testid={`text-value-${title.toLowerCase().replace(/\s/g, '-')}`}>
                {value}
              </div>
              {trend && (
                <span className={`text-xs font-medium ${trend.isPositive ? 'text-green-500' : 'text-red-500'}`}>
                  {trend.isPositive ? '+' : ''}{trend.value}%
                </span>
              )}
            </div>
            <p className="text-xs text-muted-foreground mt-1">{description}</p>
          </>
        )}
      </CardContent>
    </Card>
  );
}

function ActivityFeed({ loginHistory, isLoading }: { loginHistory: any[]; isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="flex items-center gap-3">
            <Skeleton className="h-8 w-8 rounded-full" />
            <div className="flex-1 space-y-1">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-1/2" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (!loginHistory || loginHistory.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
        <Activity className="h-8 w-8 mb-2 opacity-50" />
        <p className="text-sm">No recent activity</p>
      </div>
    );
  }

  return (
    <ScrollArea className="h-[320px] pr-4">
      <div className="space-y-3">
        {loginHistory.slice(0, 10).map((entry) => (
          <div 
            key={entry.id} 
            className="flex items-start gap-3 p-2 rounded-lg hover:bg-muted/50 transition-colors"
            data-testid={`activity-item-${entry.id}`}
          >
            <Avatar className="h-8 w-8">
              <AvatarFallback className={entry.success ? 'bg-green-500/20 text-green-600' : 'bg-red-500/20 text-red-600'}>
                {entry.success ? <CheckCircle className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium truncate">{entry.email}</span>
                <Badge variant="secondary" className="text-xs">
                  {entry.success ? 'Login' : 'Failed'}
                </Badge>
              </div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span>{entry.device_type || 'Unknown'}</span>
                <span>·</span>
                <span>{entry.browser || 'Unknown'}</span>
                <span>·</span>
                <span>{formatDistanceToNow(new Date(entry.created_at), { addSuffix: true })}</span>
              </div>
              {!entry.success && entry.failure_reason && (
                <p className="text-xs text-red-500 mt-1">{entry.failure_reason}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </ScrollArea>
  );
}

function LoginTrendChart({ data, isLoading }: { data: Record<string, number>; isLoading: boolean }) {
  if (isLoading) {
    return <Skeleton className="h-[200px] w-full" />;
  }

  const chartData = Object.entries(data || {})
    .sort(([a], [b]) => a.localeCompare(b))
    .slice(-14)
    .map(([date, count]) => ({
      date: format(new Date(date), 'MMM d'),
      logins: count,
    }));

  if (chartData.length === 0) {
    return (
      <div className="h-[200px] flex items-center justify-center text-muted-foreground">
        <p className="text-sm">No data available</p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={chartData}>
        <defs>
          <linearGradient id="loginGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3}/>
            <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0}/>
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
        <XAxis 
          dataKey="date" 
          tick={{ fontSize: 12 }} 
          tickLine={false}
          axisLine={false}
          className="text-muted-foreground"
        />
        <YAxis 
          tick={{ fontSize: 12 }} 
          tickLine={false}
          axisLine={false}
          className="text-muted-foreground"
        />
        <Tooltip 
          contentStyle={{ 
            backgroundColor: 'hsl(var(--card))', 
            border: '1px solid hsl(var(--border))',
            borderRadius: '8px'
          }}
        />
        <Area 
          type="monotone" 
          dataKey="logins" 
          stroke="hsl(var(--primary))" 
          fill="url(#loginGradient)"
          strokeWidth={2}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export default function AdminDashboard() {
  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ['/admin/dashboard'],
    queryFn: () => api.admin.dashboard(),
    refetchInterval: 30000,
  });

  const { data: loginHistory, isLoading: historyLoading } = useQuery({
    queryKey: ['/admin/login-history'],
    queryFn: () => api.admin.loginHistory(20),
  });

  const { data: activityStats, isLoading: statsLoading } = useQuery({
    queryKey: ['/admin/stats/activity'],
    queryFn: () => api.admin.activityStats(14),
  });

  const { data: auditLogs, isLoading: logsLoading } = useQuery({
    queryKey: ['/admin/audit-logs'],
    queryFn: () => api.admin.auditLogs(5),
  });

  const isLoading = metricsLoading;

  const statCards = [
    { 
      title: 'Total Users', 
      value: metrics?.total_users ?? 0, 
      icon: Users, 
      description: `${metrics?.active_users ?? 0} active users`,
      trend: { value: 12, isPositive: true }
    },
    { 
      title: 'Companies', 
      value: metrics?.total_companies ?? 0, 
      icon: Building2, 
      description: 'Total registered companies',
      trend: { value: 8, isPositive: true }
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
      description: 'Monthly recurring revenue',
      trend: { value: 5, isPositive: true }
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
      description: 'Scans run today' 
    },
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
            <Shield className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Admin Dashboard</h1>
            <p className="text-muted-foreground text-sm">System overview and management</p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <RefreshCw className="h-3 w-3" />
          <span>Auto-refresh every 30s</span>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {statCards.map((stat) => (
          <StatCard key={stat.title} {...stat} isLoading={isLoading} />
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-2">
            <CardTitle className="text-base font-semibold">Login Activity</CardTitle>
            <Badge variant="secondary" className="text-xs">Last 14 days</Badge>
          </CardHeader>
          <CardContent>
            <LoginTrendChart data={activityStats?.logins_by_date || {}} isLoading={statsLoading} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-2">
            <CardTitle className="text-base font-semibold">Recent Activity</CardTitle>
            <Badge variant="secondary" className="text-xs">Live</Badge>
          </CardHeader>
          <CardContent>
            <ActivityFeed loginHistory={loginHistory || []} isLoading={historyLoading} />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-2">
          <CardTitle className="text-base font-semibold">Recent Admin Actions</CardTitle>
          <Clock className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          {logsLoading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : auditLogs && auditLogs.length > 0 ? (
            <div className="space-y-2">
              {auditLogs.map((log) => (
                <div 
                  key={log.id} 
                  className="flex items-center justify-between p-3 rounded-lg bg-muted/50"
                  data-testid={`audit-log-${log.id}`}
                >
                  <div className="flex items-center gap-3">
                    <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                      <Activity className="h-4 w-4 text-primary" />
                    </div>
                    <div>
                      <p className="text-sm font-medium">
                        {log.user_email || 'System'} performed <span className="text-primary">{log.action}</span>
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {log.resource_type && `on ${log.resource_type}`}
                        {log.ip_address && ` · ${log.ip_address}`}
                      </p>
                    </div>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {formatDistanceToNow(new Date(log.created_at), { addSuffix: true })}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-4">No recent admin actions</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
