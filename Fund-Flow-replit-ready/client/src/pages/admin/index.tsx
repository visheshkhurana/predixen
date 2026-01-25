import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Users, Building2, CreditCard, Activity, BarChart3, Shield, TrendingUp, 
  CheckCircle, XCircle, Clock, RefreshCw, DollarSign, Flame, Calendar,
  Monitor, Smartphone, Tablet, Globe, Bell, AlertTriangle, Info,
  UserPlus, UserMinus, Settings, Eye, Zap, PieChart
} from 'lucide-react';
import { api } from '@/api/client';
import { format, formatDistanceToNow } from 'date-fns';
import { 
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  AreaChart, Area, BarChart, Bar, PieChart as RechartsPie, Pie, Cell, Legend
} from 'recharts';

const COLORS = ['hsl(var(--primary))', 'hsl(var(--chart-2))', 'hsl(var(--chart-3))', 'hsl(var(--chart-4))', 'hsl(var(--chart-5))'];

function StatCard({ 
  title, 
  value, 
  icon: Icon, 
  description, 
  trend,
  isLoading,
  className = ''
}: { 
  title: string; 
  value: string | number; 
  icon: any; 
  description: string; 
  trend?: { value: number; isPositive: boolean };
  isLoading: boolean;
  className?: string;
}) {
  return (
    <Card className={`hover-elevate transition-all ${className}`} data-testid={`card-stat-${title.toLowerCase().replace(/\s/g, '-')}`}>
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

function LoginActivityChart({ data, isLoading }: { data: Record<string, number>; isLoading: boolean }) {
  if (isLoading) return <Skeleton className="h-[200px] w-full" />;

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
        <p className="text-sm">No login data available</p>
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
        <XAxis dataKey="date" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
        <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px' }} />
        <Area type="monotone" dataKey="logins" stroke="hsl(var(--primary))" fill="url(#loginGradient)" strokeWidth={2} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

function UsersByRoleChart({ data, isLoading }: { data: Record<string, number>; isLoading: boolean }) {
  if (isLoading) return <Skeleton className="h-[200px] w-full" />;

  const chartData = Object.entries(data || {}).map(([role, count]) => ({
    name: role.charAt(0).toUpperCase() + role.slice(1),
    value: count,
  }));

  if (chartData.length === 0) {
    return (
      <div className="h-[200px] flex items-center justify-center text-muted-foreground">
        <p className="text-sm">No user data available</p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <RechartsPie>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          innerRadius={50}
          outerRadius={80}
          paddingAngle={2}
          dataKey="value"
          label={({ name, value }) => `${name}: ${value}`}
          labelLine={false}
        >
          {chartData.map((_, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip />
      </RechartsPie>
    </ResponsiveContainer>
  );
}

function CompaniesByStageChart({ data, isLoading }: { data: Record<string, number>; isLoading: boolean }) {
  if (isLoading) return <Skeleton className="h-[200px] w-full" />;

  const chartData = Object.entries(data || {}).map(([stage, count]) => ({
    stage: stage.charAt(0).toUpperCase() + stage.slice(1),
    count,
  }));

  if (chartData.length === 0) {
    return (
      <div className="h-[200px] flex items-center justify-center text-muted-foreground">
        <p className="text-sm">No company data available</p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
        <XAxis dataKey="stage" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
        <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px' }} />
        <Bar dataKey="count" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

function getDeviceIcon(deviceType: string | null) {
  switch (deviceType?.toLowerCase()) {
    case 'mobile': return <Smartphone className="h-4 w-4" />;
    case 'tablet': return <Tablet className="h-4 w-4" />;
    default: return <Monitor className="h-4 w-4" />;
  }
}

function getActionIcon(action: string) {
  switch (action) {
    case 'user_suspended': return <UserMinus className="h-4 w-4" />;
    case 'user_activated': return <UserPlus className="h-4 w-4" />;
    case 'user_updated': return <Settings className="h-4 w-4" />;
    case 'subscription_updated': return <CreditCard className="h-4 w-4" />;
    default: return <Activity className="h-4 w-4" />;
  }
}

function getActionColor(action: string) {
  switch (action) {
    case 'user_suspended': return 'bg-red-500/20 text-red-600';
    case 'user_activated': return 'bg-green-500/20 text-green-600';
    case 'user_updated': return 'bg-blue-500/20 text-blue-600';
    case 'subscription_updated': return 'bg-purple-500/20 text-purple-600';
    default: return 'bg-primary/20 text-primary';
  }
}

function getSeverityColor(severity: string) {
  switch (severity) {
    case 'critical': return 'bg-red-500/20 text-red-600';
    case 'warning': return 'bg-yellow-500/20 text-yellow-600';
    case 'info': return 'bg-blue-500/20 text-blue-600';
    default: return 'bg-muted text-muted-foreground';
  }
}

function getSeverityIcon(severity: string) {
  switch (severity) {
    case 'critical': return <AlertTriangle className="h-4 w-4" />;
    case 'warning': return <Bell className="h-4 w-4" />;
    default: return <Info className="h-4 w-4" />;
  }
}

export default function AdminDashboard() {
  const { data: metrics, isLoading: metricsLoading, refetch: refetchMetrics } = useQuery({
    queryKey: ['/admin/dashboard'],
    queryFn: () => api.admin.dashboard(),
    refetchInterval: 30000,
  });

  const { data: aggregateMetrics, isLoading: aggregateLoading } = useQuery({
    queryKey: ['/admin/metrics/aggregate'],
    queryFn: () => api.admin.metrics(),
    refetchInterval: 30000,
  });

  const { data: loginHistory, isLoading: historyLoading } = useQuery({
    queryKey: ['/admin/login-history', 50],
    queryFn: () => api.admin.loginHistory(50),
  });

  const { data: activityStats, isLoading: statsLoading } = useQuery({
    queryKey: ['/admin/stats/activity', 30],
    queryFn: () => api.admin.activityStats(30),
  });

  const { data: auditLogs, isLoading: logsLoading } = useQuery({
    queryKey: ['/admin/audit-logs', 20],
    queryFn: () => api.admin.auditLogs(20),
  });

  const { data: users, isLoading: usersLoading } = useQuery({
    queryKey: ['/admin/users'],
    queryFn: () => api.admin.users.list(),
  });

  const { data: companies, isLoading: companiesLoading } = useQuery({
    queryKey: ['/admin/companies'],
    queryFn: () => api.admin.companies.list(),
  });

  const { data: subscriptions, isLoading: subscriptionsLoading } = useQuery({
    queryKey: ['/admin/subscriptions'],
    queryFn: () => api.admin.subscriptions.list(),
  });

  const { data: notifications, isLoading: notificationsLoading } = useQuery({
    queryKey: ['/admin/notifications'],
    queryFn: () => api.admin.notifications(20),
  });

  const handleRefreshAll = () => {
    refetchMetrics();
  };

  const suspendedUsers = users?.filter(u => !u.is_active).length ?? 0;
  const activeSubscriptions = subscriptions?.filter(s => s.status === 'active').length ?? 0;
  const totalMRR = subscriptions?.filter(s => s.status === 'active').reduce((sum, s) => sum + (s.monthly_price || 0), 0) ?? 0;
  const successfulLogins = loginHistory?.filter(l => l.success).length ?? 0;
  const failedLogins = loginHistory?.filter(l => !l.success).length ?? 0;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
            <Shield className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Admin Command Center</h1>
            <p className="text-muted-foreground text-sm">Complete platform overview and management</p>
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={handleRefreshAll} data-testid="button-refresh-all">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh All
        </Button>
      </div>

      <div className="grid gap-4 grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-8">
        <StatCard 
          title="Total Users" 
          value={metrics?.total_users ?? 0} 
          icon={Users} 
          description={`${suspendedUsers} suspended`}
          isLoading={metricsLoading} 
        />
        <StatCard 
          title="Active Users" 
          value={metrics?.active_users ?? 0} 
          icon={CheckCircle} 
          description="Currently active"
          isLoading={metricsLoading} 
        />
        <StatCard 
          title="Companies" 
          value={metrics?.total_companies ?? 0} 
          icon={Building2} 
          description="Registered companies"
          isLoading={metricsLoading} 
        />
        <StatCard 
          title="Subscriptions" 
          value={activeSubscriptions} 
          icon={CreditCard} 
          description="Active subscriptions"
          isLoading={subscriptionsLoading} 
        />
        <StatCard 
          title="MRR" 
          value={`$${totalMRR.toLocaleString()}`} 
          icon={DollarSign} 
          description="Monthly revenue"
          isLoading={subscriptionsLoading} 
        />
        <StatCard 
          title="Simulations" 
          value={metrics?.active_simulations ?? 0} 
          icon={Zap} 
          description="Last 7 days"
          isLoading={metricsLoading} 
        />
        <StatCard 
          title="Truth Scans" 
          value={metrics?.truth_scans_today ?? 0} 
          icon={BarChart3} 
          description="Today"
          isLoading={metricsLoading} 
        />
        <StatCard 
          title="Login Rate" 
          value={`${successfulLogins}/${(loginHistory?.length ?? 0)}`} 
          icon={Activity} 
          description={`${failedLogins} failed`}
          isLoading={historyLoading} 
        />
      </div>


      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between gap-2">
            <div>
              <CardTitle className="text-base font-semibold">Login Activity Trend</CardTitle>
              <CardDescription>Daily successful logins over 30 days</CardDescription>
            </div>
            <Badge variant="secondary" className="text-xs">30 days</Badge>
          </CardHeader>
          <CardContent>
            <LoginActivityChart data={activityStats?.logins_by_date || {}} isLoading={statsLoading} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-2">
            <div>
              <CardTitle className="text-base font-semibold">Users by Role</CardTitle>
              <CardDescription>Role distribution</CardDescription>
            </div>
            <PieChart className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <UsersByRoleChart data={aggregateMetrics?.users_by_role || {}} isLoading={aggregateLoading} />
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-2">
            <div>
              <CardTitle className="text-base font-semibold">Companies by Stage</CardTitle>
              <CardDescription>Startup stage distribution</CardDescription>
            </div>
            <Building2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <CompaniesByStageChart data={aggregateMetrics?.companies_by_stage || {}} isLoading={aggregateLoading} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-2">
            <div>
              <CardTitle className="text-base font-semibold">System Notifications</CardTitle>
              <CardDescription>Alerts and notifications</CardDescription>
            </div>
            <Bell className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {notificationsLoading ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => <Skeleton key={i} className="h-12 w-full" />)}
              </div>
            ) : notifications && notifications.length > 0 ? (
              <ScrollArea className="h-[200px]">
                <div className="space-y-2">
                  {notifications.slice(0, 10).map((notification) => (
                    <div 
                      key={notification.id}
                      className="flex items-start gap-3 p-2 rounded-lg hover:bg-muted/50"
                      data-testid={`notification-${notification.id}`}
                    >
                      <div className={`h-8 w-8 rounded-full flex items-center justify-center ${getSeverityColor(notification.severity)}`}>
                        {getSeverityIcon(notification.severity)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{notification.title}</p>
                        <p className="text-xs text-muted-foreground line-clamp-1">{notification.message}</p>
                        <p className="text-xs text-muted-foreground mt-1">
                          {formatDistanceToNow(new Date(notification.created_at), { addSuffix: true })}
                        </p>
                      </div>
                      {!notification.read && (
                        <div className="h-2 w-2 rounded-full bg-primary" />
                      )}
                    </div>
                  ))}
                </div>
              </ScrollArea>
            ) : (
              <div className="h-[200px] flex flex-col items-center justify-center text-muted-foreground">
                <Bell className="h-8 w-8 mb-2 opacity-50" />
                <p className="text-sm">No notifications</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-2">
            <div>
              <CardTitle className="text-base font-semibold">Recent Login History</CardTitle>
              <CardDescription>All login attempts with device info</CardDescription>
            </div>
            <Badge variant="secondary" className="text-xs">{loginHistory?.length ?? 0} entries</Badge>
          </CardHeader>
          <CardContent>
            {historyLoading ? (
              <div className="space-y-2">
                {[1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-12 w-full" />)}
              </div>
            ) : loginHistory && loginHistory.length > 0 ? (
              <ScrollArea className="h-[400px]">
                <div className="space-y-2">
                  {loginHistory.map((entry) => (
                    <div 
                      key={entry.id}
                      className="flex items-center gap-3 p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors"
                      data-testid={`login-entry-${entry.id}`}
                    >
                      <Avatar className="h-9 w-9">
                        <AvatarFallback className={entry.success ? 'bg-green-500/20 text-green-600' : 'bg-red-500/20 text-red-600'}>
                          {entry.success ? <CheckCircle className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
                        </AvatarFallback>
                      </Avatar>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-sm font-medium truncate">{entry.email}</span>
                          <Badge variant={entry.success ? "default" : "destructive"} className="text-xs">
                            {entry.success ? 'Success' : 'Failed'}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1 flex-wrap">
                          <span className="flex items-center gap-1">
                            {getDeviceIcon(entry.device_type)}
                            {entry.device_type || 'Unknown'}
                          </span>
                          <span>·</span>
                          <span>{entry.browser || 'Unknown'}</span>
                          <span>·</span>
                          <span>{entry.os || 'Unknown'}</span>
                          {entry.ip_address && (
                            <>
                              <span>·</span>
                              <span className="flex items-center gap-1">
                                <Globe className="h-3 w-3" />
                                {entry.ip_address}
                              </span>
                            </>
                          )}
                        </div>
                        {!entry.success && entry.failure_reason && (
                          <p className="text-xs text-red-500 mt-1">{entry.failure_reason}</p>
                        )}
                      </div>
                      <span className="text-xs text-muted-foreground whitespace-nowrap">
                        {formatDistanceToNow(new Date(entry.created_at), { addSuffix: true })}
                      </span>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            ) : (
              <div className="h-[400px] flex flex-col items-center justify-center text-muted-foreground">
                <Activity className="h-8 w-8 mb-2 opacity-50" />
                <p className="text-sm">No login history</p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-2">
            <div>
              <CardTitle className="text-base font-semibold">Admin Activity Logs</CardTitle>
              <CardDescription>All administrative actions</CardDescription>
            </div>
            <Badge variant="secondary" className="text-xs">{auditLogs?.length ?? 0} entries</Badge>
          </CardHeader>
          <CardContent>
            {logsLoading ? (
              <div className="space-y-2">
                {[1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-12 w-full" />)}
              </div>
            ) : auditLogs && auditLogs.length > 0 ? (
              <ScrollArea className="h-[400px]">
                <div className="space-y-2">
                  {auditLogs.map((log) => (
                    <div 
                      key={log.id}
                      className="flex items-start gap-3 p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors"
                      data-testid={`audit-log-${log.id}`}
                    >
                      <div className={`h-9 w-9 rounded-full flex items-center justify-center ${getActionColor(log.action)}`}>
                        {getActionIcon(log.action)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-sm font-medium">{log.user_email || 'System'}</span>
                          <Badge variant="outline" className="text-xs">
                            {log.action.replace(/_/g, ' ')}
                          </Badge>
                        </div>
                        <div className="text-xs text-muted-foreground mt-1">
                          {log.resource_type && (
                            <span>Resource: {log.resource_type} #{log.resource_id}</span>
                          )}
                          {log.ip_address && (
                            <span className="ml-2 flex items-center gap-1 inline-flex">
                              <Globe className="h-3 w-3" />
                              {log.ip_address}
                            </span>
                          )}
                        </div>
                        {log.details && (
                          <div className="text-xs text-muted-foreground mt-1 bg-muted/50 p-2 rounded">
                            <pre className="whitespace-pre-wrap font-mono text-xs">
                              {JSON.stringify(log.details, null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                      <span className="text-xs text-muted-foreground whitespace-nowrap">
                        {formatDistanceToNow(new Date(log.created_at), { addSuffix: true })}
                      </span>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            ) : (
              <div className="h-[400px] flex flex-col items-center justify-center text-muted-foreground">
                <Clock className="h-8 w-8 mb-2 opacity-50" />
                <p className="text-sm">No admin actions recorded</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-2">
            <div>
              <CardTitle className="text-base font-semibold">Recent Users</CardTitle>
              <CardDescription>Latest registered users</CardDescription>
            </div>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {usersLoading ? (
              <div className="space-y-2">
                {[1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-12 w-full" />)}
              </div>
            ) : users && users.length > 0 ? (
              <ScrollArea className="h-[300px]">
                <div className="space-y-2">
                  {users.slice(0, 15).map((user) => (
                    <div 
                      key={user.id}
                      className="flex items-center gap-3 p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors"
                      data-testid={`user-item-${user.id}`}
                    >
                      <Avatar className="h-9 w-9">
                        <AvatarFallback className="bg-primary/10 text-primary">
                          {user.email.charAt(0).toUpperCase()}
                        </AvatarFallback>
                      </Avatar>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium truncate">{user.email}</span>
                          {!user.is_active && (
                            <Badge variant="destructive" className="text-xs">Suspended</Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <Badge variant="outline" className="text-xs">{user.role}</Badge>
                          <span>·</span>
                          <span>{user.company_count} companies</span>
                        </div>
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {format(new Date(user.created_at), 'MMM d, yyyy')}
                      </span>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            ) : (
              <div className="h-[300px] flex flex-col items-center justify-center text-muted-foreground">
                <Users className="h-8 w-8 mb-2 opacity-50" />
                <p className="text-sm">No users found</p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-2">
            <div>
              <CardTitle className="text-base font-semibold">Recent Companies</CardTitle>
              <CardDescription>Latest registered companies</CardDescription>
            </div>
            <Building2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {companiesLoading ? (
              <div className="space-y-2">
                {[1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-12 w-full" />)}
              </div>
            ) : companies && companies.length > 0 ? (
              <ScrollArea className="h-[300px]">
                <div className="space-y-2">
                  {companies.slice(0, 15).map((company) => (
                    <div 
                      key={company.id}
                      className="flex items-center gap-3 p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors"
                      data-testid={`company-item-${company.id}`}
                    >
                      <Avatar className="h-9 w-9">
                        <AvatarFallback className="bg-primary/10 text-primary">
                          {company.name.charAt(0).toUpperCase()}
                        </AvatarFallback>
                      </Avatar>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{company.name}</p>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          {company.stage && <Badge variant="outline" className="text-xs">{company.stage}</Badge>}
                          {company.industry && <span>{company.industry}</span>}
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-muted-foreground truncate max-w-[120px]">{company.user_email}</p>
                        <p className="text-xs text-muted-foreground">
                          {format(new Date(company.created_at), 'MMM d')}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            ) : (
              <div className="h-[300px] flex flex-col items-center justify-center text-muted-foreground">
                <Building2 className="h-8 w-8 mb-2 opacity-50" />
                <p className="text-sm">No companies found</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-2">
          <div>
            <CardTitle className="text-base font-semibold">Subscriptions Overview</CardTitle>
            <CardDescription>All subscription details</CardDescription>
          </div>
          <CreditCard className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          {subscriptionsLoading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => <Skeleton key={i} className="h-16 w-full" />)}
            </div>
          ) : subscriptions && subscriptions.length > 0 ? (
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
              {subscriptions.slice(0, 9).map((sub) => (
                <div 
                  key={sub.id}
                  className="p-4 rounded-lg border bg-card hover:bg-muted/30 transition-colors"
                  data-testid={`subscription-${sub.id}`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <Badge variant={sub.status === 'active' ? 'default' : 'secondary'}>
                      {sub.status}
                    </Badge>
                    <span className="text-lg font-bold">${sub.monthly_price}/mo</span>
                  </div>
                  <p className="text-sm font-medium truncate">{sub.company_name || 'No company'}</p>
                  <p className="text-xs text-muted-foreground truncate">{sub.user_email}</p>
                  <div className="flex items-center justify-between mt-2 text-xs text-muted-foreground">
                    <span>{sub.plan} plan</span>
                    <span>{sub.seats} seats</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-12 flex flex-col items-center justify-center text-muted-foreground">
              <CreditCard className="h-8 w-8 mb-2 opacity-50" />
              <p className="text-sm">No subscriptions found</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
