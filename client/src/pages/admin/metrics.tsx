import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Tooltip as UITooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { BarChart3, PieChart, TrendingUp, DollarSign, Flame, Clock, HelpCircle } from 'lucide-react';
import { api } from '@/api/client';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart as RechartsPie, Pie, Cell, Legend } from 'recharts';

const COLORS = ['#8b5cf6', '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#6366f1'];

export default function AdminMetrics() {
  const { data: metrics, isLoading } = useQuery({
    queryKey: ['/admin/metrics'],
    queryFn: () => api.admin.metrics(),
  });

  const usersByRoleData = metrics?.users_by_role
    ? Object.entries(metrics.users_by_role).map(([name, value]) => ({
        name: name.charAt(0).toUpperCase() + name.slice(1),
        value,
      }))
    : [];

  const companiesByStageData = metrics?.companies_by_stage
    ? Object.entries(metrics.companies_by_stage).map(([name, value]) => ({
        name: name.charAt(0).toUpperCase() + name.slice(1),
        value,
      }))
    : [];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <BarChart3 className="h-8 w-8 text-primary" />
        <div>
          <h1 className="text-2xl font-bold">Platform Metrics</h1>
          <p className="text-muted-foreground">Aggregated analytics across all companies</p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card data-testid="card-total-revenue">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 gap-2">
            <div className="flex items-center gap-2">
              <CardTitle className="text-sm font-medium">Total Revenue (All Companies)</CardTitle>
              <UITooltip>
                <TooltipTrigger asChild>
                  <HelpCircle className="h-4 w-4 text-muted-foreground cursor-help" />
                </TooltipTrigger>
                <TooltipContent className="max-w-xs">
                  <p>Sum of all monthly recurring revenue reported by companies on the platform. Calculated from the latest financial records.</p>
                </TooltipContent>
              </UITooltip>
            </div>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <div className="text-2xl font-bold">
                ${(metrics?.financial.total_revenue ?? 0).toLocaleString()}
              </div>
            )}
          </CardContent>
        </Card>

        <Card data-testid="card-avg-burn">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 gap-2">
            <div className="flex items-center gap-2">
              <CardTitle className="text-sm font-medium">Avg Monthly Burn</CardTitle>
              <UITooltip>
                <TooltipTrigger asChild>
                  <HelpCircle className="h-4 w-4 text-muted-foreground cursor-help" />
                </TooltipTrigger>
                <TooltipContent className="max-w-xs">
                  <p>Average monthly cash burn rate across all companies. Calculated as (Total Expenses - Total Revenue) / Number of Companies.</p>
                </TooltipContent>
              </UITooltip>
            </div>
            <Flame className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <div className="text-2xl font-bold">
                ${Math.abs(metrics?.financial.avg_burn ?? 0).toLocaleString()}
              </div>
            )}
          </CardContent>
        </Card>

        <Card data-testid="card-avg-runway">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 gap-2">
            <div className="flex items-center gap-2">
              <CardTitle className="text-sm font-medium">Avg Runway</CardTitle>
              <UITooltip>
                <TooltipTrigger asChild>
                  <HelpCircle className="h-4 w-4 text-muted-foreground cursor-help" />
                </TooltipTrigger>
                <TooltipContent className="max-w-xs">
                  <p>Average remaining runway in months across all companies. Calculated as Cash Balance / Monthly Burn Rate for each company, then averaged.</p>
                </TooltipContent>
              </UITooltip>
            </div>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <div className="text-2xl font-bold">
                {(metrics?.financial.avg_runway_months ?? 0).toFixed(1)} months
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card data-testid="card-users-by-role">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <PieChart className="h-5 w-5" />
              Users by Role
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-64 w-full" />
            ) : usersByRoleData.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <RechartsPie>
                  <Pie
                    data={usersByRoleData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  >
                    {usersByRoleData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </RechartsPie>
              </ResponsiveContainer>
            ) : (
              <div className="h-64 flex items-center justify-center text-muted-foreground">
                No user data available
              </div>
            )}
          </CardContent>
        </Card>

        <Card data-testid="card-companies-by-stage">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Companies by Stage
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-64 w-full" />
            ) : companiesByStageData.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={companiesByStageData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="name" className="text-xs" />
                  <YAxis className="text-xs" />
                  <Tooltip />
                  <Bar dataKey="value" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-64 flex items-center justify-center text-muted-foreground">
                No company data available
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
