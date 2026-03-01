import { useMemo, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { useFounderStore } from '@/store/founderStore';
import { useRealtimeKPI } from '@/hooks/useRealtimeKPI';
import { useFinancialMetrics } from '@/hooks/useFinancialMetrics';
import { formatCurrencyAbbrev } from '@/lib/utils';
import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Users, 
  Clock, 
  Percent, 
  Activity,
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
  return formatCurrencyAbbrev(value);
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
  isLoading?: boolean;
}

function KPITile({ title, value, subtitle, icon, trend, trendValue, isLive, isLoading }: KPITileProps) {
  if (isLoading) {
    return (
      <Card className="relative overflow-visible">
        <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0 pb-2">
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-8 w-8 rounded-md" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-7 w-24 mb-1" />
          <Skeleton className="h-3 w-16" />
        </CardContent>
      </Card>
    );
  }

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

interface HistoryRecord {
  time: string;
  monthly_revenue: number;
  mrr: number;
  arr: number;
  cash_balance: number;
  net_burn: number;
  runway_months: number;
  gross_margin: number;
  churn_rate: number;
  cac: number;
  ltv: number;
  ltv_cac_ratio: number;
  headcount: number;
  revenue_per_employee: number;
}

function computeTrend(history: HistoryRecord[], key: keyof HistoryRecord): { trend: 'up' | 'down' | 'neutral'; value: string } {
  if (!history || history.length < 2) return { trend: 'neutral', value: '' };
  const current = Number(history[history.length - 1]?.[key] ?? 0);
  const previous = Number(history[history.length - 2]?.[key] ?? 0);
  if (previous === 0) return { trend: 'neutral', value: '' };
  const changePct = ((current - previous) / Math.abs(previous)) * 100;
  return {
    trend: changePct > 0.5 ? 'up' : changePct < -0.5 ? 'down' : 'neutral',
    value: `${changePct > 0 ? '+' : ''}${changePct.toFixed(1)}%`
  };
}

export default function KPIBoardPage() {
  const { currentCompany } = useFounderStore();
  const companyId = currentCompany?.id ?? null;
  const { metrics: sharedMetrics, isLoading: sharedLoading } = useFinancialMetrics();

  const handleKPIUpdate = useCallback(() => {}, []);

  const kpiOptions = useMemo(() => ({
    enabled: !!companyId,
    onUpdate: handleKPIUpdate
  }), [companyId, handleKPIUpdate]);

  const { data: liveData, isConnected } = useRealtimeKPI(companyId, kpiOptions);

  const { data: historyResponse, isLoading: historyLoading } = useQuery<{ data: HistoryRecord[] }>({
    queryKey: ['/api/realtime/kpi', String(companyId), 'history?months=12'],
    enabled: !!companyId,
    staleTime: 60_000,
  });

  const historicalData = historyResponse?.data ?? [];

  const latestSnapshot = liveData?.metrics;
  const latestHistory = historicalData.length > 0 ? historicalData[historicalData.length - 1] : null;

  const metrics = useMemo(() => {
    const pick = (liveVal: number | undefined, histVal: number | undefined, fallback: number) => {
      if (liveVal && liveVal > 0) return liveVal;
      if (histVal && histVal > 0) return histVal;
      return fallback;
    };

    const normalizeChurn = (val: number): number => {
      if (val > 1) return val / 100;
      return val;
    };

    const runwayFallback = sharedMetrics.runway === Infinity ? 60 : sharedMetrics.runway;

    const rawChurn = pick(latestSnapshot?.churn_rate, latestHistory?.churn_rate, sharedMetrics.churnRate);

    return {
      monthly_revenue: pick(latestSnapshot?.monthly_revenue, latestHistory?.monthly_revenue, sharedMetrics.mrr),
      mrr: pick(latestSnapshot?.mrr, latestHistory?.mrr, sharedMetrics.mrr),
      arr: pick(latestSnapshot?.arr, latestHistory?.arr, sharedMetrics.arr),
      cash_balance: pick(latestSnapshot?.cash_balance, latestHistory?.cash_balance, sharedMetrics.cashOnHand),
      net_burn: sharedMetrics.netBurn || latestSnapshot?.net_burn || latestHistory?.net_burn || 0,
      runway_months: Math.max(0, Math.min(sharedMetrics.runway === Infinity ? 60 : (sharedMetrics.runway || pick(latestSnapshot?.runway_months, latestHistory?.runway_months, runwayFallback)), 60)),
      gross_margin: pick(latestSnapshot?.gross_margin, latestHistory?.gross_margin, sharedMetrics.grossMargin),
      churn_rate: normalizeChurn(rawChurn),
      cac: pick(latestSnapshot?.cac, latestHistory?.cac, sharedMetrics.cac),
      ltv: pick(latestSnapshot?.ltv, latestHistory?.ltv, sharedMetrics.ltv),
      ltv_cac_ratio: pick(latestSnapshot?.ltv_cac_ratio, latestHistory?.ltv_cac_ratio, sharedMetrics.ltvCacRatio),
      headcount: pick(latestSnapshot?.headcount, latestHistory?.headcount, sharedMetrics.headcount),
      revenue_per_employee: pick(latestSnapshot?.revenue_per_employee, latestHistory?.revenue_per_employee, sharedMetrics.revenuePerEmployee),
    };
  }, [latestSnapshot, latestHistory, sharedMetrics]);

  const isLoading = (historyLoading || sharedLoading) && !latestSnapshot;

  const mrrTrend = computeTrend(historicalData, 'mrr');
  const arrTrend = computeTrend(historicalData, 'arr');
  const burnTrend = computeTrend(historicalData, 'net_burn');

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
    <div className="p-4 md:p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-2">
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
          value={isLoading ? '—' : formatCurrency(metrics.mrr)}
          icon={<TrendingUp className="h-4 w-4" />}
          trend={mrrTrend.trend}
          trendValue={mrrTrend.value}
          subtitle="Monthly Recurring Revenue"
          isLive={isConnected}
          isLoading={isLoading}
        />
        <KPITile
          title="ARR"
          value={isLoading ? '—' : formatCurrency(metrics.arr)}
          icon={<DollarSign className="h-4 w-4" />}
          trend={arrTrend.trend}
          trendValue={arrTrend.value}
          subtitle="Annual Recurring Revenue"
          isLive={isConnected}
          isLoading={isLoading}
        />
        <KPITile
          title="Cash Balance"
          value={isLoading ? '—' : formatCurrency(metrics.cash_balance)}
          icon={<DollarSign className="h-4 w-4" />}
          isLive={isConnected}
          isLoading={isLoading}
        />
        <KPITile
          title="Runway"
          value={isLoading ? '—' : metrics.runway_months >= 120 ? '\u221E' : `${metrics.runway_months.toFixed(1)} mo`}
          icon={<Clock className="h-4 w-4" />}
          trend={metrics.runway_months < 6 ? 'down' : 'neutral'}
          subtitle={metrics.runway_months >= 120 ? 'Profitable' : metrics.runway_months < 6 ? 'Low runway' : ''}
          isLive={isConnected}
          isLoading={isLoading}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPITile
          title="Net Burn"
          value={isLoading ? '—' : formatCurrency(metrics.net_burn)}
          icon={<TrendingDown className="h-4 w-4" />}
          trend={burnTrend.trend === 'up' ? 'down' : burnTrend.trend === 'down' ? 'up' : 'neutral'}
          trendValue={burnTrend.value}
          subtitle="per month"
          isLive={isConnected}
          isLoading={isLoading}
        />
        <KPITile
          title="Gross Margin"
          value={isLoading ? '—' : formatPercent(metrics.gross_margin)}
          icon={<Percent className="h-4 w-4" />}
          trend={metrics.gross_margin >= 0.7 ? 'up' : 'neutral'}
          isLive={isConnected}
          isLoading={isLoading}
        />
        <KPITile
          title="Churn Rate"
          value={isLoading ? '—' : formatPercent(metrics.churn_rate)}
          icon={<Activity className="h-4 w-4" />}
          trend={metrics.churn_rate <= 0.03 ? 'up' : metrics.churn_rate > 0.05 ? 'down' : 'neutral'}
          isLive={isConnected}
          isLoading={isLoading}
        />
        <KPITile
          title="Headcount"
          value={isLoading ? '—' : metrics.headcount}
          icon={<Users className="h-4 w-4" />}
          subtitle={metrics.revenue_per_employee > 0 ? `${formatCurrency(metrics.revenue_per_employee)}/emp` : undefined}
          isLive={isConnected}
          isLoading={isLoading}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <KPITile
          title="CAC"
          value={isLoading ? '—' : metrics.cac > 0 ? formatCurrency(metrics.cac) : '—'}
          icon={<DollarSign className="h-4 w-4" />}
          isLive={isConnected}
          isLoading={isLoading}
        />
        <KPITile
          title="LTV"
          value={isLoading ? '—' : metrics.ltv > 0 ? formatCurrency(metrics.ltv) : '—'}
          icon={<DollarSign className="h-4 w-4" />}
          isLive={isConnected}
          isLoading={isLoading}
        />
        <KPITile
          title="LTV/CAC Ratio"
          value={isLoading ? '—' : (metrics.ltv > 0 && metrics.cac > 0 && metrics.ltv_cac_ratio > 0) ? `${metrics.ltv_cac_ratio.toFixed(1)}x` : '—'}
          icon={<TrendingUp className="h-4 w-4" />}
          trend={(metrics.ltv > 0 && metrics.cac > 0 && metrics.ltv_cac_ratio >= 3) ? 'up' : (metrics.ltv > 0 && metrics.cac > 0 && metrics.ltv_cac_ratio > 0 && metrics.ltv_cac_ratio < 2) ? 'down' : 'neutral'}
          subtitle={(metrics.ltv > 0 && metrics.cac > 0 && metrics.ltv_cac_ratio >= 3) ? 'Healthy' : (metrics.ltv > 0 && metrics.cac > 0 && metrics.ltv_cac_ratio > 0 && metrics.ltv_cac_ratio < 2) ? 'Needs improvement' : undefined}
          isLive={isConnected}
          isLoading={isLoading}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Revenue Trend</CardTitle>
          </CardHeader>
          <CardContent>
            {historyLoading ? (
              <Skeleton className="h-[250px] w-full" />
            ) : historicalData.length >= 2 ? (
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
                <div className="text-center">
                  <Activity className="h-10 w-10 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">Upload financial data to see revenue trends</p>
                  <p className="text-xs mt-1">At least 2 months of data required</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Burn & Runway</CardTitle>
          </CardHeader>
          <CardContent>
            {historyLoading ? (
              <Skeleton className="h-[250px] w-full" />
            ) : historicalData.length >= 2 ? (
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
                <div className="text-center">
                  <Activity className="h-10 w-10 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">Upload financial data to see burn trends</p>
                  <p className="text-xs mt-1">At least 2 months of data required</p>
                </div>
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
            {historyLoading ? (
              <Skeleton className="h-[250px] w-full" />
            ) : historicalData.length >= 2 && historicalData.some(d => d.cac > 0 || d.ltv > 0) ? (
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
                <div className="text-center">
                  <Activity className="h-10 w-10 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">Connect Stripe or import customer data for unit economics</p>
                  <p className="text-xs mt-1">CAC and LTV require transaction data</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Margins & Churn</CardTitle>
          </CardHeader>
          <CardContent>
            {historyLoading ? (
              <Skeleton className="h-[250px] w-full" />
            ) : historicalData.length >= 2 ? (
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
                <div className="text-center">
                  <Activity className="h-10 w-10 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">Upload financial data to see margin trends</p>
                  <p className="text-xs mt-1">At least 2 months of data required</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
