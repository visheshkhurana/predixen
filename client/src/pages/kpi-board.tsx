import { useState, useEffect, useCallback, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { useFounderStore } from '@/store/founderStore';
import { useRealtimeKPI, KPIMetrics } from '@/hooks/useRealtimeKPI';
import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Users, 
  Clock, 
  Percent, 
  Activity,
  RefreshCw,
  Wifi,
  WifiOff,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';

function formatCurrency(value: number): string {
  if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
  if (value >= 1000) return `$${(value / 1000).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

interface KPITileProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  isLive?: boolean;
}

function KPITile({ title, value, subtitle, icon, trend, trendValue, isLive }: KPITileProps) {
  return (
    <Card className="relative overflow-visible">
      {isLive && (
        <div className="absolute top-2 right-2">
          <span className="flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
          </span>
        </div>
      )}
      <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        <div className="h-8 w-8 rounded-md bg-primary/10 flex items-center justify-center text-primary">
          {icon}
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold" data-testid={`kpi-value-${title.toLowerCase().replace(/\s/g, '-')}`}>
          {value}
        </div>
        {(subtitle || trendValue) && (
          <div className="flex items-center gap-2 mt-1">
            {trend && trend !== 'neutral' && (
              <span className={`flex items-center text-xs ${trend === 'up' ? 'text-green-500' : 'text-red-500'}`}>
                {trend === 'up' ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
                {trendValue}
              </span>
            )}
            {subtitle && <span className="text-xs text-muted-foreground">{subtitle}</span>}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function KPIBoardPage() {
  const { currentCompany } = useFounderStore();
  const [historicalData, setHistoricalData] = useState<Array<KPIMetrics & { time: string }>>([]);
  
  const handleKPIUpdate = useCallback((update: import('@/hooks/useRealtimeKPI').KPIUpdate) => {
    setHistoricalData(prev => {
      const newData = [...prev, { ...update.metrics, time: new Date(update.timestamp).toLocaleTimeString() }];
      return newData.slice(-20);
    });
  }, []);
  
  const kpiOptions = useMemo(() => ({
    enabled: !!currentCompany?.id,
    onUpdate: handleKPIUpdate
  }), [currentCompany?.id, handleKPIUpdate]);
  
  const { data: liveData, isConnected, error } = useRealtimeKPI(
    currentCompany?.id ?? null,
    kpiOptions
  );

  const metrics = liveData?.metrics ?? {
    monthly_revenue: 0,
    mrr: 0,
    arr: 0,
    cash_balance: 0,
    net_burn: 0,
    runway_months: 0,
    gross_margin: 0,
    churn_rate: 0,
    cac: 0,
    ltv: 0,
    ltv_cac_ratio: 0,
    headcount: 0,
    revenue_per_employee: 0
  };

  if (!currentCompany) {
    return (
      <div className="p-6">
        <Card className="p-8 text-center">
          <p className="text-muted-foreground">Please select a company to view KPIs</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold" data-testid="page-title-kpi-board">KPI Board</h1>
          <p className="text-muted-foreground">Real-time metrics for {currentCompany.name}</p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant={isConnected ? "default" : "secondary"} className="gap-1">
            {isConnected ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
            {isConnected ? 'Live' : 'Disconnected'}
          </Badge>
          {liveData && (
            <span className="text-xs text-muted-foreground">
              Last update: {new Date(liveData.timestamp).toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPITile
          title="MRR"
          value={formatCurrency(metrics.mrr)}
          icon={<TrendingUp className="h-4 w-4" />}
          trend="up"
          trendValue="+8%"
          subtitle="Monthly Recurring Revenue"
          isLive={isConnected}
        />
        <KPITile
          title="ARR"
          value={formatCurrency(metrics.arr)}
          icon={<DollarSign className="h-4 w-4" />}
          trend="up"
          subtitle="Annual Recurring Revenue"
          isLive={isConnected}
        />
        <KPITile
          title="Cash Balance"
          value={formatCurrency(metrics.cash_balance)}
          icon={<DollarSign className="h-4 w-4" />}
          isLive={isConnected}
        />
        <KPITile
          title="Runway"
          value={`${metrics.runway_months.toFixed(1)} mo`}
          icon={<Clock className="h-4 w-4" />}
          trend={metrics.runway_months < 6 ? 'down' : 'neutral'}
          subtitle={metrics.runway_months < 6 ? 'Low runway' : ''}
          isLive={isConnected}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPITile
          title="Net Burn"
          value={formatCurrency(metrics.net_burn)}
          icon={<TrendingDown className="h-4 w-4" />}
          subtitle="per month"
          isLive={isConnected}
        />
        <KPITile
          title="Gross Margin"
          value={formatPercent(metrics.gross_margin)}
          icon={<Percent className="h-4 w-4" />}
          trend={metrics.gross_margin >= 0.7 ? 'up' : 'neutral'}
          isLive={isConnected}
        />
        <KPITile
          title="Churn Rate"
          value={formatPercent(metrics.churn_rate)}
          icon={<Activity className="h-4 w-4" />}
          trend={metrics.churn_rate <= 0.03 ? 'up' : 'down'}
          isLive={isConnected}
        />
        <KPITile
          title="Headcount"
          value={metrics.headcount}
          icon={<Users className="h-4 w-4" />}
          subtitle={`$${(metrics.revenue_per_employee / 1000).toFixed(0)}K/emp`}
          isLive={isConnected}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <KPITile
          title="CAC"
          value={formatCurrency(metrics.cac)}
          icon={<DollarSign className="h-4 w-4" />}
          isLive={isConnected}
        />
        <KPITile
          title="LTV"
          value={formatCurrency(metrics.ltv)}
          icon={<DollarSign className="h-4 w-4" />}
          isLive={isConnected}
        />
        <KPITile
          title="LTV/CAC Ratio"
          value={`${metrics.ltv_cac_ratio.toFixed(1)}x`}
          icon={<TrendingUp className="h-4 w-4" />}
          trend={metrics.ltv_cac_ratio >= 3 ? 'up' : metrics.ltv_cac_ratio < 2 ? 'down' : 'neutral'}
          subtitle={metrics.ltv_cac_ratio >= 3 ? 'Healthy' : metrics.ltv_cac_ratio < 2 ? 'Needs improvement' : ''}
          isLive={isConnected}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Revenue Trend</CardTitle>
          </CardHeader>
          <CardContent>
            {historicalData.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={historicalData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="time" tick={{ fontSize: 12 }} className="text-muted-foreground" />
                  <YAxis tickFormatter={(v) => `$${(v/1000).toFixed(0)}K`} tick={{ fontSize: 12 }} />
                  <Tooltip formatter={(value: number) => formatCurrency(value)} />
                  <Area 
                    type="monotone" 
                    dataKey="monthly_revenue" 
                    stroke="hsl(var(--primary))" 
                    fill="hsl(var(--primary) / 0.2)" 
                    name="Revenue"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[250px] flex items-center justify-center text-muted-foreground">
                <p>Waiting for live data...</p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Burn & Runway</CardTitle>
          </CardHeader>
          <CardContent>
            {historicalData.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={historicalData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="time" tick={{ fontSize: 12 }} />
                  <YAxis yAxisId="left" tickFormatter={(v) => `$${(v/1000).toFixed(0)}K`} tick={{ fontSize: 12 }} />
                  <YAxis yAxisId="right" orientation="right" tickFormatter={(v) => `${v}mo`} tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Legend />
                  <Line 
                    yAxisId="left"
                    type="monotone" 
                    dataKey="net_burn" 
                    stroke="hsl(var(--destructive))" 
                    name="Net Burn"
                    dot={false}
                  />
                  <Line 
                    yAxisId="right"
                    type="monotone" 
                    dataKey="runway_months" 
                    stroke="hsl(var(--chart-2))" 
                    name="Runway (months)"
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[250px] flex items-center justify-center text-muted-foreground">
                <p>Waiting for live data...</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Unit Economics</CardTitle>
          </CardHeader>
          <CardContent>
            {historicalData.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={historicalData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="time" tick={{ fontSize: 12 }} />
                  <YAxis tickFormatter={(v) => `$${(v/1000).toFixed(0)}K`} tick={{ fontSize: 12 }} />
                  <Tooltip formatter={(value: number) => formatCurrency(value)} />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="cac" 
                    stroke="hsl(var(--chart-1))" 
                    name="CAC"
                    dot={false}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="ltv" 
                    stroke="hsl(var(--chart-3))" 
                    name="LTV"
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[250px] flex items-center justify-center text-muted-foreground">
                <p>Waiting for live data...</p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Margins & Churn</CardTitle>
          </CardHeader>
          <CardContent>
            {historicalData.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={historicalData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="time" tick={{ fontSize: 12 }} />
                  <YAxis tickFormatter={(v) => `${(v*100).toFixed(0)}%`} tick={{ fontSize: 12 }} />
                  <Tooltip formatter={(value: number) => formatPercent(value)} />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="gross_margin" 
                    stroke="hsl(var(--chart-2))" 
                    name="Gross Margin"
                    dot={false}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="churn_rate" 
                    stroke="hsl(var(--destructive))" 
                    name="Churn Rate"
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[250px] flex items-center justify-center text-muted-foreground">
                <p>Waiting for live data...</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
