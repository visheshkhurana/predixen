import { useState, useEffect } from "react";
import { useLocation } from "wouter";
import { useQuery, useMutation } from "@tanstack/react-query";
import { format } from "date-fns";
import { 
  Users, Building2, CreditCard, TrendingUp, Activity, DollarSign, 
  Shield, RefreshCw, LogOut, ChevronRight, AlertTriangle, CheckCircle,
  Clock, Eye, UserCheck, Flame, Target, PieChart, BarChart3,
  Monitor, Smartphone, Tablet, Globe, Search, Filter, Download
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useToast } from "@/hooks/use-toast";
import { useFounderStore } from "@/store/founderStore";
import { api } from "@/api/client";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart as RechartsPieChart, Pie, Cell, BarChart, Bar, Legend
} from "recharts";

const CHART_COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"];

export default function OwnerConsole() {
  const [, navigate] = useLocation();
  const { user, logout } = useFounderStore();
  const { toast } = useToast();
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const { data: meData, isLoading: meLoading } = useQuery({
    queryKey: ["/api/admin/me"],
    queryFn: () => api.admin.me(),
    enabled: !!user,
  });

  const { data: dashboard, isLoading: dashLoading, refetch: refetchDashboard } = useQuery({
    queryKey: ["/api/admin/dashboard"],
    queryFn: () => api.admin.dashboard(),
    enabled: !!user && meData?.is_admin,
  });

  const { data: metrics, refetch: refetchMetrics } = useQuery({
    queryKey: ["/api/admin/metrics/aggregate"],
    queryFn: () => api.admin.metrics(),
    enabled: !!user && meData?.is_admin,
  });

  const { data: users, refetch: refetchUsers } = useQuery({
    queryKey: ["/api/admin/users"],
    queryFn: () => api.admin.users.list(),
    enabled: !!user && meData?.is_admin,
  });

  const { data: companies, refetch: refetchCompanies } = useQuery({
    queryKey: ["/api/admin/companies"],
    queryFn: () => api.admin.companies.list(),
    enabled: !!user && meData?.is_admin,
  });

  const { data: subscriptions, refetch: refetchSubscriptions } = useQuery({
    queryKey: ["/api/admin/subscriptions"],
    queryFn: () => api.admin.subscriptions.list(),
    enabled: !!user && meData?.is_admin,
  });

  const { data: activityStats, refetch: refetchActivity } = useQuery({
    queryKey: ["/api/admin/stats/activity"],
    queryFn: () => api.admin.activityStats(),
    enabled: !!user && meData?.is_admin,
  });

  const { data: loginHistory, refetch: refetchLogins } = useQuery({
    queryKey: ["/api/admin/login-history"],
    queryFn: () => api.admin.loginHistory(),
    enabled: !!user && meData?.is_admin,
  });

  const { data: auditLogs, refetch: refetchAudit } = useQuery({
    queryKey: ["/api/admin/audit-logs"],
    queryFn: () => api.admin.auditLogs(),
    enabled: !!user && meData?.is_admin,
  });

  const { data: notifications, refetch: refetchNotifications } = useQuery({
    queryKey: ["/api/admin/notifications"],
    queryFn: () => api.admin.notifications(),
    enabled: !!user && meData?.is_admin,
  });

  useEffect(() => {
    if (!user) {
      navigate("/auth");
    }
  }, [user, navigate]);

  useEffect(() => {
    if (meData && meData.role !== "owner") {
      toast({
        title: "Access Denied",
        description: "Only owners can access this console.",
        variant: "destructive",
      });
      navigate("/");
    }
  }, [meData, navigate, toast]);

  const handleRefreshAll = async () => {
    setIsRefreshing(true);
    try {
      await Promise.all([
        refetchDashboard(),
        refetchMetrics(),
        refetchUsers(),
        refetchCompanies(),
        refetchSubscriptions(),
        refetchActivity(),
        refetchLogins(),
        refetchAudit(),
        refetchNotifications(),
      ]);
      toast({ title: "Data refreshed", description: "All metrics updated" });
    } catch (err) {
      toast({ title: "Refresh failed", variant: "destructive" });
    }
    setIsRefreshing(false);
  };

  const handleLogout = () => {
    logout();
    navigate("/auth");
  };

  if (!user || meLoading) {
    return (
      <div className="min-h-screen bg-background">
        <header className="sticky top-0 z-50 bg-background/95 backdrop-blur border-b">
          <div className="max-w-[1800px] mx-auto px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Skeleton className="h-10 w-10 rounded-lg" />
              <div className="space-y-1">
                <Skeleton className="h-5 w-32" />
                <Skeleton className="h-3 w-40" />
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Skeleton className="h-6 w-16 rounded-full" />
              <Skeleton className="h-8 w-20" />
              <Skeleton className="h-8 w-20" />
            </div>
          </div>
        </header>
        <main className="max-w-[1800px] mx-auto p-6 space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
            {Array(8).fill(0).map((_, i) => (
              <Card key={i}>
                <CardContent className="p-4">
                  <Skeleton className="h-4 w-16 mb-2" />
                  <Skeleton className="h-7 w-12" />
                </CardContent>
              </Card>
            ))}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {Array(3).fill(0).map((_, i) => (
              <Card key={i}>
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div className="space-y-2">
                      <Skeleton className="h-4 w-24" />
                      <Skeleton className="h-8 w-32" />
                    </div>
                    <Skeleton className="h-12 w-12 rounded" />
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
          <div className="space-y-4">
            <Skeleton className="h-10 w-96" />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <Card>
                <CardHeader className="pb-2">
                  <Skeleton className="h-5 w-40" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-[250px] w-full" />
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <Skeleton className="h-5 w-32" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-[200px] w-full" />
                </CardContent>
              </Card>
            </div>
          </div>
        </main>
      </div>
    );
  }

  if (meData && meData.role !== "owner") {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Card className="max-w-md">
          <CardHeader className="text-center">
            <Shield className="h-12 w-12 mx-auto text-destructive mb-4" />
            <CardTitle className="text-destructive">Access Denied</CardTitle>
            <CardDescription>
              This console is exclusively for software owners.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-center">
            <Button onClick={() => navigate("/")} data-testid="button-go-home">
              Return to Dashboard
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const chartData = activityStats?.logins_by_date
    ? Object.entries(activityStats.logins_by_date)
        .map(([date, count]) => ({ date: format(new Date(date), "MMM d"), logins: count }))
        .slice(-14)
    : [];

  const roleData = metrics?.users_by_role
    ? Object.entries(metrics.users_by_role).map(([role, count]) => ({
        name: role.charAt(0).toUpperCase() + role.slice(1),
        value: count as number,
      }))
    : [];

  const stageData = metrics?.companies_by_stage
    ? Object.entries(metrics.companies_by_stage).map(([stage, count]) => ({
        name: stage.charAt(0).toUpperCase() + stage.slice(1),
        value: count as number,
      }))
    : [];

  const filteredUsers = users?.filter((u: any) =>
    u.email.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  const filteredCompanies = companies?.filter((c: any) =>
    c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    c.user_email.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];
  const auditLogItems = auditLogs || [];

  const loginRate = dashboard ? Math.round((dashboard.active_users / dashboard.total_users) * 100) || 0 : 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-muted/20">
      <header className="sticky top-0 z-50 bg-background/95 backdrop-blur border-b">
        <div className="max-w-[1800px] mx-auto px-6 py-4 flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-4">
            <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-primary to-primary/60 flex items-center justify-center shrink-0">
              <Shield className="h-5 w-5 text-primary-foreground" />
            </div>
            <div>
              <h1 className="text-xl font-bold">Owner Console</h1>
              <p className="text-sm text-muted-foreground">FounderConsole</p>
            </div>
          </div>
          <div className="flex items-center gap-3 flex-wrap">
            <Badge variant="outline" className="text-emerald-500 border-emerald-500/30">
              <span className="h-2 w-2 rounded-full bg-emerald-500 mr-2 animate-pulse" />
              Live
            </Badge>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefreshAll}
              disabled={isRefreshing}
              data-testid="button-refresh-all"
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleLogout}
              data-testid="button-logout"
            >
              <LogOut className="h-4 w-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-[1800px] mx-auto p-6 space-y-6">
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
          <StatCard 
            title="Users" 
            value={dashboard?.total_users || 0} 
            icon={Users} 
            loading={dashLoading}
            color="blue"
          />
          <StatCard 
            title="Active" 
            value={dashboard?.active_users || 0} 
            icon={UserCheck} 
            loading={dashLoading}
            color="green"
          />
          <StatCard 
            title="Companies" 
            value={dashboard?.total_companies || 0} 
            icon={Building2} 
            loading={dashLoading}
            color="purple"
          />
          <StatCard 
            title="Subscriptions" 
            value={dashboard?.total_subscriptions || 0} 
            icon={CreditCard} 
            loading={dashLoading}
            color="amber"
          />
          <StatCard 
            title="MRR" 
            value={`$${(dashboard?.mrr || 0).toLocaleString()}`} 
            icon={DollarSign} 
            loading={dashLoading}
            color="emerald"
          />
          <StatCard 
            title="Simulations" 
            value={dashboard?.active_simulations || 0} 
            icon={Activity} 
            loading={dashLoading}
            color="rose"
          />
          <StatCard 
            title="Truth Scans" 
            value={dashboard?.truth_scans_today || 0} 
            icon={Target} 
            loading={dashLoading}
            color="cyan"
          />
          <StatCard 
            title="Login Rate" 
            value={`${loginRate}%`} 
            icon={TrendingUp} 
            loading={dashLoading}
            color="indigo"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Card className="bg-gradient-to-br from-blue-500/10 to-blue-600/5 border-blue-500/20">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Revenue</p>
                  <p className="text-3xl font-bold text-blue-500">
                    ${(metrics?.financial?.total_revenue || 0).toLocaleString()}
                  </p>
                </div>
                <DollarSign className="h-12 w-12 text-blue-500/30" />
              </div>
            </CardContent>
          </Card>
          <Card className="bg-gradient-to-br from-amber-500/10 to-amber-600/5 border-amber-500/20">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Avg Monthly Burn</p>
                  <p className="text-3xl font-bold text-amber-500">
                    ${(metrics?.financial?.avg_burn || 0).toLocaleString()}
                  </p>
                </div>
                <Flame className="h-12 w-12 text-amber-500/30" />
              </div>
            </CardContent>
          </Card>
          <Card className="bg-gradient-to-br from-emerald-500/10 to-emerald-600/5 border-emerald-500/20">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Avg Runway</p>
                  <p className="text-3xl font-bold text-emerald-500">
                    {(metrics?.financial?.avg_runway_months || 0).toFixed(1)} mo
                  </p>
                </div>
                <Clock className="h-12 w-12 text-emerald-500/30" />
              </div>
            </CardContent>
          </Card>
        </div>

        <Tabs defaultValue="overview" className="space-y-4">
          <TabsList className="bg-muted/50">
            <TabsTrigger value="overview" data-testid="tab-overview">
              <BarChart3 className="h-4 w-4 mr-2" />
              Overview
            </TabsTrigger>
            <TabsTrigger value="users" data-testid="tab-users">
              <Users className="h-4 w-4 mr-2" />
              Users
            </TabsTrigger>
            <TabsTrigger value="companies" data-testid="tab-companies">
              <Building2 className="h-4 w-4 mr-2" />
              Companies
            </TabsTrigger>
            <TabsTrigger value="activity" data-testid="tab-activity">
              <Activity className="h-4 w-4 mr-2" />
              Activity
            </TabsTrigger>
            <TabsTrigger value="billing" data-testid="tab-billing">
              <CreditCard className="h-4 w-4 mr-2" />
              Billing
            </TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Activity className="h-5 w-5 text-primary" />
                    Login Activity (14 Days)
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-[250px]">
                    {chartData.length > 0 ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={chartData}>
                          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                          <XAxis dataKey="date" className="text-xs" />
                          <YAxis className="text-xs" />
                          <Tooltip 
                            contentStyle={{ 
                              backgroundColor: "hsl(var(--card))", 
                              border: "1px solid hsl(var(--border))" 
                            }} 
                          />
                          <Area
                            type="monotone"
                            dataKey="logins"
                            stroke="#3b82f6"
                            fill="#3b82f6"
                            fillOpacity={0.2}
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="flex items-center justify-center h-full text-muted-foreground">
                        No login data available
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>

              <div className="grid grid-cols-1 gap-4">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <PieChart className="h-5 w-5 text-primary" />
                      Users by Role
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[100px]">
                      {roleData.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                          <RechartsPieChart>
                            <Pie
                              data={roleData}
                              cx="50%"
                              cy="50%"
                              innerRadius={25}
                              outerRadius={45}
                              dataKey="value"
                              label={({ name, value }) => `${name}: ${value}`}
                            >
                              {roleData.map((_, index) => (
                                <Cell key={index} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                              ))}
                            </Pie>
                            <Tooltip />
                          </RechartsPieChart>
                        </ResponsiveContainer>
                      ) : (
                        <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                          No role data
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Building2 className="h-5 w-5 text-primary" />
                      Companies by Stage
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[100px]">
                      {stageData.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={stageData} layout="vertical">
                            <XAxis type="number" hide />
                            <YAxis type="category" dataKey="name" width={80} className="text-xs" />
                            <Tooltip />
                            <Bar dataKey="value" fill="#8b5cf6" radius={[0, 4, 4, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      ) : (
                        <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                          No stage data
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg">Recent Logins</CardTitle>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-[200px]">
                    {loginHistory?.slice(0, 10).map((login: any) => (
                      <div key={login.id} className="flex items-center justify-between py-2 border-b last:border-0">
                        <div className="flex items-center gap-3">
                          <DeviceIcon type={login.device_type} />
                          <div>
                            <p className="text-sm font-medium">{login.email}</p>
                            <p className="text-xs text-muted-foreground">
                              {login.browser} / {login.os}
                            </p>
                          </div>
                        </div>
                        <div className="text-right">
                          <Badge variant={login.success ? "default" : "destructive"} className="text-xs">
                            {login.success ? "Success" : "Failed"}
                          </Badge>
                          <p className="text-xs text-muted-foreground mt-1">
                            {login.created_at ? format(new Date(login.created_at), "MMM d, HH:mm") : "N/A"}
                          </p>
                        </div>
                      </div>
                    )) || (
                      <p className="text-sm text-muted-foreground text-center py-8">No login history</p>
                    )}
                  </ScrollArea>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg">Admin Activity</CardTitle>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-[200px]">
                    {auditLogItems.length > 0 ? auditLogItems.slice(0, 10).map((log: any) => (
                      <div key={log.id} className="flex items-center gap-3 py-2 border-b last:border-0">
                        <div className="h-8 w-8 rounded-full bg-muted flex items-center justify-center">
                          <Activity className="h-4 w-4 text-muted-foreground" />
                        </div>
                        <div className="flex-1">
                          <p className="text-sm">
                            <span className="font-medium">{log.user_email}</span>
                            {" "}
                            <span className="text-muted-foreground">{log.action.replace(/_/g, " ")}</span>
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {log.created_at ? format(new Date(log.created_at), "MMM d, HH:mm") : "N/A"}
                          </p>
                        </div>
                      </div>
                    )) : (
                      <p className="text-sm text-muted-foreground text-center py-8">No admin activity</p>
                    )}
                  </ScrollArea>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="users" className="space-y-4">
            <Card>
              <CardHeader className="pb-4">
                <div className="flex items-center justify-between">
                  <CardTitle>User Management</CardTitle>
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
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[400px]">
                  <div className="space-y-2">
                    {filteredUsers.map((user: any) => (
                      <div key={user.id} className="flex items-center justify-between p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors" data-testid={`user-row-${user.id}`}>
                        <div className="flex items-center gap-3">
                          <Avatar className="h-10 w-10">
                            <AvatarFallback className="bg-primary/10 text-primary">
                              {user.email.charAt(0).toUpperCase()}
                            </AvatarFallback>
                          </Avatar>
                          <div>
                            <p className="font-medium">{user.email}</p>
                            <p className="text-sm text-muted-foreground">
                              {user.company_count} companies
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <Badge variant={user.role === "owner" ? "default" : "secondary"}>
                            {user.role}
                          </Badge>
                          <Badge variant={user.is_active ? "outline" : "destructive"} className="text-xs">
                            {user.is_active ? "Active" : "Suspended"}
                          </Badge>
                          <p className="text-xs text-muted-foreground w-24 text-right">
                            {user.created_at ? format(new Date(user.created_at), "MMM d, yyyy") : "N/A"}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="companies" className="space-y-4">
            <Card>
              <CardHeader className="pb-4">
                <div className="flex items-center justify-between">
                  <CardTitle>All Companies</CardTitle>
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Search companies..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-9 w-64"
                      data-testid="input-search-companies"
                    />
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[400px]">
                  <div className="space-y-2">
                    {filteredCompanies.map((company: any) => (
                      <div key={company.id} className="flex items-center justify-between p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors" data-testid={`company-row-${company.id}`}>
                        <div className="flex items-center gap-3">
                          <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                            <Building2 className="h-5 w-5 text-primary" />
                          </div>
                          <div>
                            <p className="font-medium">{company.name}</p>
                            <p className="text-sm text-muted-foreground">{company.user_email}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          {company.industry && (
                            <Badge variant="outline">{company.industry}</Badge>
                          )}
                          {company.stage && (
                            <Badge variant="secondary">{company.stage}</Badge>
                          )}
                          <p className="text-xs text-muted-foreground w-24 text-right">
                            {company.created_at ? format(new Date(company.created_at), "MMM d, yyyy") : "N/A"}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="activity" className="space-y-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle>Login History</CardTitle>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-[400px]">
                    {loginHistory?.map((login: any) => (
                      <div key={login.id} className="flex items-center justify-between py-3 border-b last:border-0">
                        <div className="flex items-center gap-3">
                          <DeviceIcon type={login.device_type} />
                          <div>
                            <p className="font-medium">{login.email}</p>
                            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                              <span>{login.browser}</span>
                              <span>/</span>
                              <span>{login.os}</span>
                            </div>
                            <p className="text-xs text-muted-foreground">{login.ip_address}</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <Badge variant={login.success ? "default" : "destructive"}>
                            {login.success ? "Success" : "Failed"}
                          </Badge>
                          <p className="text-xs text-muted-foreground mt-1">
                            {login.created_at ? format(new Date(login.created_at), "MMM d, HH:mm:ss") : "N/A"}
                          </p>
                        </div>
                      </div>
                    )) || (
                      <p className="text-muted-foreground text-center py-8">No login history</p>
                    )}
                  </ScrollArea>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle>Audit Logs</CardTitle>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-[400px]">
                    {auditLogItems.length > 0 ? auditLogItems.map((log: any) => (
                      <div key={log.id} className="py-3 border-b last:border-0">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="font-medium">{log.action.replace(/_/g, " ")}</p>
                            <p className="text-sm text-muted-foreground">{log.user_email}</p>
                          </div>
                          <p className="text-xs text-muted-foreground">
                            {log.created_at ? format(new Date(log.created_at), "MMM d, HH:mm") : "N/A"}
                          </p>
                        </div>
                        {log.details && (
                          <pre className="mt-2 text-xs bg-muted p-2 rounded overflow-x-auto">
                            {JSON.stringify(log.details, null, 2)}
                          </pre>
                        )}
                      </div>
                    )) : (
                      <p className="text-muted-foreground text-center py-8">No audit logs</p>
                    )}
                  </ScrollArea>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="billing" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Subscriptions</CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[400px]">
                  <div className="space-y-3">
                    {subscriptions?.map((sub: any) => (
                      <div key={sub.id} className="p-4 rounded-lg border bg-card" data-testid={`subscription-${sub.id}`}>
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="font-medium">{sub.company_name || "No company"}</p>
                            <p className="text-sm text-muted-foreground">{sub.user_email}</p>
                          </div>
                          <div className="text-right">
                            <Badge 
                              variant={sub.status === "active" ? "default" : 
                                       sub.status === "trialing" ? "secondary" : "destructive"}
                            >
                              {sub.status}
                            </Badge>
                            <p className="text-lg font-bold mt-1">${sub.monthly_price}/mo</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-4 mt-3 text-sm text-muted-foreground">
                          <span>Plan: {sub.plan}</span>
                          <span>Seats: {sub.seats}</span>
                          {sub.current_period_end && (
                            <span>Renews: {format(new Date(sub.current_period_end), "MMM d, yyyy")}</span>
                          )}
                        </div>
                      </div>
                    )) || (
                      <p className="text-muted-foreground text-center py-8">No subscriptions</p>
                    )}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {notifications && notifications.length > 0 && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-lg flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-amber-500" />
                System Notifications
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[150px]">
                {notifications.slice(0, 5).map((n: any) => (
                  <div key={n.id} className="flex items-start gap-3 py-2 border-b last:border-0">
                    {n.severity === "critical" ? (
                      <AlertTriangle className="h-5 w-5 text-destructive mt-0.5" />
                    ) : n.severity === "warning" ? (
                      <AlertTriangle className="h-5 w-5 text-amber-500 mt-0.5" />
                    ) : (
                      <CheckCircle className="h-5 w-5 text-emerald-500 mt-0.5" />
                    )}
                    <div>
                      <p className="font-medium">{n.title}</p>
                      <p className="text-sm text-muted-foreground">{n.message}</p>
                    </div>
                  </div>
                ))}
              </ScrollArea>
            </CardContent>
          </Card>
        )}
      </main>

      <footer className="border-t mt-8 py-6 text-center text-sm text-muted-foreground">
        FounderConsole - Owner Console v1.0
      </footer>
    </div>
  );
}

function StatCard({ 
  title, 
  value, 
  icon: Icon, 
  loading,
  color 
}: { 
  title: string; 
  value: string | number; 
  icon: any; 
  loading?: boolean;
  color?: string;
}) {
  const colorClasses: Record<string, string> = {
    blue: "text-blue-500",
    green: "text-emerald-500",
    purple: "text-purple-500",
    amber: "text-amber-500",
    emerald: "text-emerald-500",
    rose: "text-rose-500",
    cyan: "text-cyan-500",
    indigo: "text-indigo-500",
  };

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <Icon className={`h-5 w-5 ${colorClasses[color || "blue"]}`} />
        </div>
        {loading ? (
          <Skeleton className="h-8 w-16 mt-2" />
        ) : (
          <p className="text-2xl font-bold mt-2">{value}</p>
        )}
        <p className="text-xs text-muted-foreground">{title}</p>
      </CardContent>
    </Card>
  );
}

function DeviceIcon({ type }: { type?: string }) {
  if (type === "mobile") return <Smartphone className="h-5 w-5 text-muted-foreground" />;
  if (type === "tablet") return <Tablet className="h-5 w-5 text-muted-foreground" />;
  return <Monitor className="h-5 w-5 text-muted-foreground" />;
}
