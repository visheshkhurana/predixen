import { useState, useMemo, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { useFounderStore } from '@/store/founderStore';
import { useRealtimeKPI } from '@/hooks/useRealtimeKPI';
import { useFinancialMetrics } from '@/hooks/useFinancialMetrics';
import { Sparkline } from '@/components/Sparkline';
import { formatCurrencyAbbrev, cn } from '@/lib/utils';
import { useLocation } from 'wouter';
import { FadeIn, StaggerChildren, StaggerItem, ScrollReveal } from '@/components/ui/motion-primitives';
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
  ArrowDownRight,
  RefreshCw,
  Calendar,
  Filter,
  CheckCircle2,
  AlertCircle,
  Circle,
  Plus,
  BarChart3,
  Zap
} from 'lucide-react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';

function formatCurrency(value: number): string {
  return formatCurrencyAbbrev(value);
}

function formatPercent(value: number): string {
  const pct = Math.abs(value) > 0 && Math.abs(value) <= 1 ? value * 100 : value;
  const fixed = pct.toFixed(1);
  return `${fixed.replace(/\.0$/, '')}%`;
}

type DateRange = '7d' | '30d' | '90d' | '12m' | 'ytd';
type DataSource = 'all' | 'stripe' | 'quickbooks' | 'manual';

interface FilterBarProps {
  dateRange: DateRange;
  onDateRangeChange: (range: DateRange) => void;
  dataSource: DataSource;
  onDataSourceChange: (source: DataSource) => void;
  isConnected: boolean;
  lastUpdate: string | null;
  onRefresh: () => void;
  isRefreshing: boolean;
}

function FilterBar({
  dateRange,
  onDateRangeChange,
  dataSource,
  onDataSourceChange,
  isConnected,
  lastUpdate,
  onRefresh,
  isRefreshing,
}: FilterBarProps) {
  return (
    <div className="flex items-center justify-between flex-wrap gap-3">
      <div className="flex items-center gap-2 flex-wrap">
        <div className="flex items-center gap-1.5">
          <Calendar className="h-4 w-4 text-muted-foreground" />
          <Select value={dateRange} onValueChange={(v) => onDateRangeChange(v as DateRange)}>
            <SelectTrigger className="w-[130px]" data-testid="select-date-range">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7d">Last 7 days</SelectItem>
              <SelectItem value="30d">Last 30 days</SelectItem>
              <SelectItem value="90d">Last 90 days</SelectItem>
              <SelectItem value="12m">Last 12 months</SelectItem>
              <SelectItem value="ytd">Year to date</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center gap-1.5">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <Select value={dataSource} onValueChange={(v) => onDataSourceChange(v as DataSource)}>
            <SelectTrigger className="w-[140px]" data-testid="select-data-source">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Sources</SelectItem>
              <SelectItem value="stripe">Stripe</SelectItem>
              <SelectItem value="quickbooks">QuickBooks</SelectItem>
              <SelectItem value="manual">Manual Entry</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <Tooltip>
          <TooltipTrigger asChild>
            <div className={cn(
              "flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium",
              isConnected
                ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                : "bg-muted text-muted-foreground"
            )}>
              {isConnected ? (
                <>
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
                  </span>
                  Auto-refresh
                </>
              ) : (
                <>
                  <WifiOff className="h-3 w-3" />
                  Offline
                </>
              )}
            </div>
          </TooltipTrigger>
          <TooltipContent>
            {isConnected
              ? `Live data updates enabled${lastUpdate ? `. Last: ${new Date(lastUpdate).toLocaleTimeString()}` : ''}`
              : 'Reconnecting...'}
          </TooltipContent>
        </Tooltip>

        <Button
          variant="outline"
          size="sm"
          onClick={onRefresh}
          disabled={isRefreshing}
          data-testid="button-refresh"
        >
          <RefreshCw className={cn("h-3.5 w-3.5 mr-1.5", isRefreshing && "animate-spin")} />
          Refresh
        </Button>
      </div>
    </div>
  );
}

interface EnhancedKPICardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  sparklineData?: number[];
  source?: string;
  isLive?: boolean;
  isLoading?: boolean;
  hoverDetail?: string;
  testId?: string;
}

function EnhancedKPICard({
  title,
  value,
  subtitle,
  icon,
  trend,
  trendValue,
  sparklineData,
  source,
  isLive,
  isLoading,
  hoverDetail,
  testId,
}: EnhancedKPICardProps) {
  if (isLoading) {
    return (
      <Card className="overflow-visible">
        <CardContent className="p-4">
          <div className="flex items-center justify-between gap-2 mb-3">
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-6 w-6 rounded-md" />
          </div>
          <Skeleton className="h-7 w-28 mb-2" />
          <Skeleton className="h-3 w-16" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Card className="overflow-visible hover-elevate" data-testid={testId}>
          <CardContent className="p-4">
            <div className="flex items-center justify-between gap-2 mb-1">
              <div className="flex items-center gap-1.5">
                <div className="h-7 w-7 rounded-md bg-primary/10 flex items-center justify-center text-primary">
                  {icon}
                </div>
                <span className="text-xs font-medium text-muted-foreground">{title}</span>
              </div>
              <div className="flex items-center gap-1.5">
                {source && (
                  <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                    {source}
                  </Badge>
                )}
                {isLive && (
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
                  </span>
                )}
              </div>
            </div>

            <div className="flex items-end justify-between gap-2 mt-2">
              <div>
                <div className="text-2xl font-bold font-mono tracking-tight" data-testid={`${testId}-value`}>
                  {value}
                </div>
                <div className="flex items-center gap-2 mt-1">
                  {trend && trend !== 'neutral' && trendValue && (
                    <span className={cn(
                      "flex items-center text-xs font-medium",
                      trend === 'up' ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'
                    )}>
                      {trend === 'up' ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
                      {trendValue}
                    </span>
                  )}
                  {subtitle && <span className="text-xs text-muted-foreground">{subtitle}</span>}
                </div>
              </div>
              {sparklineData && sparklineData.length > 1 && (
                <div className="flex-shrink-0">
                  <Sparkline data={sparklineData} width={56} height={24} />
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </TooltipTrigger>
      {hoverDetail && (
        <TooltipContent side="bottom" className="max-w-xs">
          <p className="text-sm">{hoverDetail}</p>
        </TooltipContent>
      )}
    </Tooltip>
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

function extractSparkline(history: HistoryRecord[], key: keyof HistoryRecord): number[] {
  if (!history || history.length < 2) return [];
  return history.slice(-8).map(r => Number(r[key] ?? 0));
}

interface DataSourceInfo {
  name: string;
  icon: React.ReactNode;
  status: 'connected' | 'syncing' | 'error' | 'disconnected';
  lastSync?: string;
  metrics?: number;
}

function DataSourcesPanel({ onAddIntegration }: { onAddIntegration: () => void }) {
  const { currentCompany } = useFounderStore();
  const companyId = currentCompany?.id ?? null;

  const { data: connectorsResponse } = useQuery<{ company_id: number; connectors: any[] }>({
    queryKey: ['/api/connectors/companies', companyId, 'status'],
    enabled: !!companyId,
    staleTime: 60_000,
  });

  const sources: DataSourceInfo[] = useMemo(() => {
    const connectors = connectorsResponse?.connectors;
    const connected = connectors?.filter((c: any) => c.connected) ?? [];
    const base: DataSourceInfo[] = [
      { name: 'Manual Entry', icon: <BarChart3 className="h-4 w-4" />, status: 'connected' as const, lastSync: 'Just now', metrics: 8 },
    ];
    if (connected.length === 0) return base;
    return [
      ...base,
      ...connected.map((c: any) => ({
        name: c.provider_id?.charAt(0).toUpperCase() + c.provider_id?.slice(1) || 'Unknown',
        icon: <Zap className="h-4 w-4" />,
        status: (c.error ? 'error' : 'connected') as DataSourceInfo['status'],
        lastSync: c.last_sync ? new Date(c.last_sync).toLocaleString() : undefined,
        metrics: c.records_synced || 0,
      })),
    ];
  }, [connectorsResponse]);

  const statusDotColor: Record<string, string> = {
    connected: 'bg-emerald-500',
    syncing: 'bg-amber-500 animate-pulse',
    error: 'bg-red-500',
    disconnected: 'bg-muted-foreground',
  };

  const statusLabel: Record<string, string> = {
    connected: 'Connected',
    syncing: 'Syncing...',
    error: 'Error',
    disconnected: 'Not connected',
  };

  return (
    <Card className="overflow-visible" data-testid="panel-data-sources">
      <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0 pb-3">
        <CardTitle className="text-lg">Data Sources</CardTitle>
        <Button variant="outline" size="sm" onClick={onAddIntegration} data-testid="button-add-integration">
          <Plus className="h-3.5 w-3.5 mr-1.5" />
          Add Integration
        </Button>
      </CardHeader>
      <CardContent className="space-y-3">
        {sources.length === 0 && (
          <div className="text-center py-6 text-muted-foreground">
            <Zap className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No data sources connected</p>
            <p className="text-xs mt-1">Add an integration to start syncing metrics</p>
          </div>
        )}
        {sources.map((src, idx) => (
          <div key={idx} className="flex items-center justify-between gap-3 p-2.5 rounded-md bg-muted/30" data-testid={`data-source-${idx}`}>
            <div className="flex items-center gap-2.5">
              <div className="h-8 w-8 rounded-md bg-primary/10 flex items-center justify-center text-primary">
                {src.icon}
              </div>
              <div>
                <div className="text-sm font-medium">{src.name}</div>
                {src.lastSync && (
                  <div className="text-[10px] text-muted-foreground">Last sync: {src.lastSync}</div>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {src.metrics !== undefined && src.metrics > 0 && (
                <Badge variant="secondary" className="text-[10px]">{src.metrics} metrics</Badge>
              )}
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="flex items-center gap-1.5">
                    <span className={cn("h-2 w-2 rounded-full", statusDotColor[src.status])} />
                    <span className="text-xs text-muted-foreground">{statusLabel[src.status]}</span>
                  </div>
                </TooltipTrigger>
                <TooltipContent>{statusLabel[src.status]}</TooltipContent>
              </Tooltip>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export default function KPIBoardPage() {
  const { currentCompany } = useFounderStore();
  const companyId = currentCompany?.id ?? null;
  const { metrics: sharedMetrics, isLoading: sharedLoading } = useFinancialMetrics();
  const [, navigate] = useLocation();

  const [dateRange, setDateRange] = useState<DateRange>('12m');
  const [dataSource, setDataSource] = useState<DataSource>('all');
  const [isRefreshing, setIsRefreshing] = useState(false);

  const rangeMonths = useMemo(() => {
    const map: Record<DateRange, number> = { '7d': 1, '30d': 1, '90d': 3, '12m': 12, 'ytd': Math.max(1, new Date().getMonth() + 1) };
    return map[dateRange] || 12;
  }, [dateRange]);

  const handleKPIUpdate = useCallback(() => {}, []);
  const kpiOptions = useMemo(() => ({
    enabled: !!companyId,
    onUpdate: handleKPIUpdate
  }), [companyId, handleKPIUpdate]);

  const { data: liveData, isConnected } = useRealtimeKPI(companyId, kpiOptions);

  const { data: historyResponse, isLoading: historyLoading, refetch: refetchHistory } = useQuery<{ data: HistoryRecord[] }>({
    queryKey: ['/api/realtime/kpi', String(companyId), `history?months=${rangeMonths}`],
    enabled: !!companyId,
    staleTime: 60_000,
  });

  const historicalData = useMemo(() => {
    const raw = historyResponse?.data ?? [];
    if (dateRange === '7d' || dateRange === '30d') return raw.slice(-1);
    return raw;
  }, [historyResponse, dateRange]);
  const latestSnapshot = liveData?.metrics;
  const latestHistory = historicalData.length > 0 ? historicalData[historicalData.length - 1] : null;

  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    await refetchHistory();
    setTimeout(() => setIsRefreshing(false), 800);
  }, [refetchHistory]);

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
  const cashTrend = computeTrend(historicalData, 'cash_balance');

  const mrrSparkline = extractSparkline(historicalData, 'mrr');
  const arrSparkline = extractSparkline(historicalData, 'arr');
  const cashSparkline = extractSparkline(historicalData, 'cash_balance');
  const burnSparkline = extractSparkline(historicalData, 'net_burn');

  const revenueExpenseData = useMemo(() => {
    if (!historicalData || historicalData.length < 2) return [];
    return historicalData.slice(-6).map(d => ({
      time: d.time,
      Revenue: d.monthly_revenue || d.mrr || 0,
      Expenses: (d.net_burn || 0) + (d.monthly_revenue || d.mrr || 0),
    }));
  }, [historicalData]);

  const customerGrowthData = useMemo(() => {
    if (!historicalData || historicalData.length < 2) return [];
    return historicalData.slice(-8).map(d => ({
      time: d.time,
      Headcount: d.headcount || 0,
    }));
  }, [historicalData]);

  if (!currentCompany) {
    return (
      <div className="p-6">
        <Card className="p-8 text-center">
          <p className="text-muted-foreground" data-testid="text-no-company">Please select a company to view KPIs</p>
        </Card>
      </div>
    );
  }

  return (
    <FadeIn delay={0.05} duration={0.4}>
    <div className="p-4 md:p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-2xl font-bold" data-testid="page-title-kpi-board">KPI Board</h1>
          <p className="text-sm text-muted-foreground">Real-time metrics for {currentCompany.name}</p>
        </div>
        <Badge variant={isConnected ? "default" : "secondary"} className="gap-1">
          {isConnected ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
          {isConnected ? 'Live' : 'Disconnected'}
        </Badge>
      </div>

      <FilterBar
        dateRange={dateRange}
        onDateRangeChange={setDateRange}
        dataSource={dataSource}
        onDataSourceChange={setDataSource}
        isConnected={isConnected}
        lastUpdate={liveData?.timestamp ?? null}
        onRefresh={handleRefresh}
        isRefreshing={isRefreshing}
      />

      {!isLoading && metrics.mrr === 0 && metrics.arr === 0 && metrics.cash_balance === 0 && metrics.net_burn === 0 && (
        <Card className="border-dashed border-amber-500/30 bg-amber-50/50 dark:bg-amber-900/10" data-testid="card-kpi-empty-state">
          <CardContent className="flex items-center gap-4 py-4">
            <div className="p-2 rounded-full bg-amber-100 dark:bg-amber-900/30">
              <AlertCircle className="h-5 w-5 text-amber-600 dark:text-amber-400" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-amber-800 dark:text-amber-300">No financial data yet</p>
              <p className="text-xs text-amber-600 dark:text-amber-400">Upload your financials or connect an integration to populate these KPIs with real numbers.</p>
            </div>
            <Button asChild variant="outline" size="sm" data-testid="button-kpi-add-data">
              <a href="/data-input">
                <Plus className="h-3.5 w-3.5 mr-1" />
                Add Data
              </a>
            </Button>
          </CardContent>
        </Card>
      )}

      <StaggerChildren className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4" staggerDelay={0.08}>
        <StaggerItem>
        <EnhancedKPICard
          title="MRR"
          value={isLoading ? '—' : formatCurrency(metrics.mrr)}
          icon={<TrendingUp className="h-4 w-4" />}
          trend={mrrTrend.trend}
          trendValue={mrrTrend.value}
          subtitle="Monthly Recurring Revenue"
          sparklineData={mrrSparkline}
          source={sharedMetrics.sources?.mrr === 'reported' ? 'Verified' : undefined}
          isLive={isConnected}
          isLoading={isLoading}
          hoverDetail={`MRR is ${formatCurrency(metrics.mrr)}. ${mrrTrend.value ? `Changed ${mrrTrend.value} from prior period.` : ''} ARR equivalent: ${formatCurrency(metrics.arr)}.`}
          testId="kpi-card-mrr"
        />
        </StaggerItem>
        <StaggerItem>
        <EnhancedKPICard
          title="ARR"
          value={isLoading ? '—' : formatCurrency(metrics.arr)}
          icon={<DollarSign className="h-4 w-4" />}
          trend={arrTrend.trend}
          trendValue={arrTrend.value}
          subtitle="Annual Recurring Revenue"
          sparklineData={arrSparkline}
          isLive={isConnected}
          isLoading={isLoading}
          hoverDetail={`Annualized recurring revenue: ${formatCurrency(metrics.arr)}.`}
          testId="kpi-card-arr"
        />
        </StaggerItem>
        <StaggerItem>
        <EnhancedKPICard
          title="Cash Balance"
          value={isLoading ? '—' : formatCurrency(metrics.cash_balance)}
          icon={<DollarSign className="h-4 w-4" />}
          trend={cashTrend.trend}
          trendValue={cashTrend.value}
          sparklineData={cashSparkline}
          isLive={isConnected}
          isLoading={isLoading}
          hoverDetail={`Current cash on hand: ${formatCurrency(metrics.cash_balance)}.`}
          testId="kpi-card-cash"
        />
        </StaggerItem>
        <StaggerItem>
        <EnhancedKPICard
          title="Runway"
          value={isLoading ? '—' : (metrics.runway_months >= 120) ? '\u221E' : `${metrics.runway_months.toFixed(1)} mo`}
          icon={<Clock className="h-4 w-4" />}
          trend={metrics.runway_months < 6 ? 'down' : 'neutral'}
          subtitle={metrics.runway_months >= 120 ? 'Profitable' : metrics.runway_months < 6 ? 'Low runway' : ''}
          isLive={isConnected}
          isLoading={isLoading}
          hoverDetail={metrics.runway_months >= 120 ? 'Company is profitable or cash-flow positive.' : `At current burn rate, cash lasts approximately ${metrics.runway_months.toFixed(1)} months.`}
          testId="kpi-card-runway"
        />
        </StaggerItem>
      </StaggerChildren>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <EnhancedKPICard
          title="Net Burn"
          value={isLoading ? '—' : formatCurrency(metrics.net_burn)}
          icon={<TrendingDown className="h-4 w-4" />}
          trend={burnTrend.trend === 'up' ? 'down' : burnTrend.trend === 'down' ? 'up' : 'neutral'}
          trendValue={burnTrend.value}
          subtitle="per month"
          sparklineData={burnSparkline}
          isLive={isConnected}
          isLoading={isLoading}
          hoverDetail={`Monthly net cash outflow: ${formatCurrency(metrics.net_burn)}.`}
          testId="kpi-card-burn"
        />
        <EnhancedKPICard
          title="Gross Margin"
          value={isLoading ? '—' : formatPercent(metrics.gross_margin)}
          icon={<Percent className="h-4 w-4" />}
          trend={metrics.gross_margin >= 0.7 ? 'up' : 'neutral'}
          subtitle={metrics.gross_margin >= 0.7 ? 'Strong' : metrics.gross_margin >= 0.5 ? 'Moderate' : 'Below target'}
          isLive={isConnected}
          isLoading={isLoading}
          hoverDetail={`Gross margin is ${formatPercent(metrics.gross_margin)}. SaaS target is typically >70%.`}
          testId="kpi-card-margin"
        />
        <EnhancedKPICard
          title="Churn Rate"
          value={isLoading ? '—' : formatPercent(metrics.churn_rate)}
          icon={<Activity className="h-4 w-4" />}
          trend={metrics.churn_rate <= 0.03 ? 'up' : metrics.churn_rate > 0.05 ? 'down' : 'neutral'}
          subtitle={metrics.churn_rate <= 0.03 ? 'Low churn' : metrics.churn_rate > 0.05 ? 'High churn' : 'Moderate'}
          isLive={isConnected}
          isLoading={isLoading}
          hoverDetail={`Monthly churn: ${formatPercent(metrics.churn_rate)}. Target: <3% monthly.`}
          testId="kpi-card-churn"
        />
        <EnhancedKPICard
          title="Headcount"
          value={isLoading ? '—' : metrics.headcount}
          icon={<Users className="h-4 w-4" />}
          subtitle={metrics.revenue_per_employee > 0 ? `${formatCurrency(metrics.revenue_per_employee)}/emp` : undefined}
          isLive={isConnected}
          isLoading={isLoading}
          hoverDetail={metrics.revenue_per_employee > 0 ? `Revenue per employee: ${formatCurrency(metrics.revenue_per_employee)}.` : 'Team size and efficiency metrics.'}
          testId="kpi-card-headcount"
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <EnhancedKPICard
          title="CAC"
          value={isLoading ? '—' : metrics.cac > 0 ? formatCurrency(metrics.cac) : '—'}
          icon={<DollarSign className="h-4 w-4" />}
          source={metrics.cac > 0 && sharedMetrics.sources?.cac === 'reported' ? 'Stripe' : undefined}
          isLive={isConnected}
          isLoading={isLoading}
          hoverDetail="Customer acquisition cost. Connect Stripe or add customer data to compute."
          testId="kpi-card-cac"
        />
        <EnhancedKPICard
          title="LTV"
          value={isLoading ? '—' : metrics.ltv > 0 ? formatCurrency(metrics.ltv) : '—'}
          icon={<DollarSign className="h-4 w-4" />}
          isLive={isConnected}
          isLoading={isLoading}
          hoverDetail="Customer lifetime value. Derived from ARPU and churn rate."
          testId="kpi-card-ltv"
        />
        <EnhancedKPICard
          title="LTV/CAC Ratio"
          value={isLoading ? '—' : (metrics.ltv > 0 && metrics.cac > 0 && metrics.ltv_cac_ratio > 0) ? `${metrics.ltv_cac_ratio.toFixed(1)}x` : '—'}
          icon={<TrendingUp className="h-4 w-4" />}
          trend={(metrics.ltv > 0 && metrics.cac > 0 && metrics.ltv_cac_ratio >= 3) ? 'up' : (metrics.ltv > 0 && metrics.cac > 0 && metrics.ltv_cac_ratio > 0 && metrics.ltv_cac_ratio < 2) ? 'down' : 'neutral'}
          subtitle={(metrics.ltv > 0 && metrics.cac > 0 && metrics.ltv_cac_ratio >= 3) ? 'Healthy' : (metrics.ltv > 0 && metrics.cac > 0 && metrics.ltv_cac_ratio > 0 && metrics.ltv_cac_ratio < 2) ? 'Needs improvement' : undefined}
          isLive={isConnected}
          isLoading={isLoading}
          hoverDetail="LTV to CAC ratio. 3x+ is considered healthy for SaaS businesses."
          testId="kpi-card-ltv-cac"
        />
      </div>

      <ScrollReveal>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card data-testid="chart-mrr-trend">
          <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0 pb-2">
            <CardTitle className="text-lg">MRR Trend</CardTitle>
            <Badge variant="secondary" className="text-[10px]">Area Chart</Badge>
          </CardHeader>
          <CardContent>
            {historyLoading ? (
              <Skeleton className="h-[250px] w-full" />
            ) : historicalData.length >= 2 ? (
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={historicalData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="time" tick={{ fontSize: 12 }} className="text-muted-foreground" />
                  <YAxis tickFormatter={(v) => `$${(v / 1000).toFixed(0)}K`} tick={{ fontSize: 12 }} />
                  <RechartsTooltip
                    formatter={(value: number) => formatCurrency(value)}
                    contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '6px' }}
                  />
                  <Area
                    type="monotone"
                    dataKey="mrr"
                    stroke="hsl(var(--primary))"
                    fill="hsl(var(--primary) / 0.15)"
                    name="MRR"
                    strokeWidth={2}
                  />
                  <Area
                    type="monotone"
                    dataKey="monthly_revenue"
                    stroke="hsl(var(--chart-2))"
                    fill="hsl(var(--chart-2) / 0.1)"
                    name="Revenue"
                    strokeWidth={1.5}
                    strokeDasharray="4 4"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[250px] flex items-center justify-center text-muted-foreground">
                <div className="text-center">
                  <Activity className="h-10 w-10 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">Upload financial data to see MRR trends</p>
                  <p className="text-xs mt-1">At least 2 months of data required</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card data-testid="chart-revenue-expenses">
          <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0 pb-2">
            <CardTitle className="text-lg">Revenue vs Expenses</CardTitle>
            <Badge variant="secondary" className="text-[10px]">Bar Chart</Badge>
          </CardHeader>
          <CardContent>
            {historyLoading ? (
              <Skeleton className="h-[250px] w-full" />
            ) : revenueExpenseData.length >= 2 ? (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={revenueExpenseData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="time" tick={{ fontSize: 12 }} />
                  <YAxis tickFormatter={(v) => `$${(v / 1000).toFixed(0)}K`} tick={{ fontSize: 12 }} />
                  <RechartsTooltip
                    formatter={(value: number) => formatCurrency(value)}
                    contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '6px' }}
                  />
                  <Legend />
                  <Bar dataKey="Revenue" fill="hsl(var(--chart-2))" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Expenses" fill="hsl(var(--destructive) / 0.6)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[250px] flex items-center justify-center text-muted-foreground">
                <div className="text-center">
                  <BarChart3 className="h-10 w-10 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">Upload financial data to compare revenue & expenses</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
      </ScrollReveal>

      <ScrollReveal delay={0.1}>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card data-testid="chart-cash-flow">
          <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0 pb-2">
            <CardTitle className="text-lg">Cash Flow & Runway</CardTitle>
          </CardHeader>
          <CardContent>
            {historyLoading ? (
              <Skeleton className="h-[250px] w-full" />
            ) : historicalData.length >= 2 ? (
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={historicalData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="time" tick={{ fontSize: 12 }} />
                  <YAxis yAxisId="left" tickFormatter={(v) => `$${(v / 1000).toFixed(0)}K`} tick={{ fontSize: 12 }} />
                  <YAxis yAxisId="right" orientation="right" tickFormatter={(v) => `${v}mo`} tick={{ fontSize: 12 }} />
                  <RechartsTooltip
                    contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '6px' }}
                  />
                  <Legend />
                  <Line
                    yAxisId="left"
                    type="monotone"
                    dataKey="cash_balance"
                    stroke="hsl(var(--primary))"
                    name="Cash Balance"
                    dot={false}
                    strokeWidth={2}
                  />
                  <Line
                    yAxisId="left"
                    type="monotone"
                    dataKey="net_burn"
                    stroke="hsl(var(--destructive))"
                    name="Net Burn"
                    dot={false}
                    strokeWidth={1.5}
                    strokeDasharray="4 4"
                  />
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="runway_months"
                    stroke="hsl(var(--chart-2))"
                    name="Runway (months)"
                    dot={false}
                    strokeWidth={1.5}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[250px] flex items-center justify-center text-muted-foreground">
                <div className="text-center">
                  <Activity className="h-10 w-10 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">Upload financial data to see cash flow trends</p>
                  <p className="text-xs mt-1">At least 2 months of data required</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card data-testid="chart-customer-growth">
          <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0 pb-2">
            <CardTitle className="text-lg">Team & Customer Growth</CardTitle>
          </CardHeader>
          <CardContent>
            {historyLoading ? (
              <Skeleton className="h-[250px] w-full" />
            ) : customerGrowthData.length >= 2 && customerGrowthData.some(d => d.Headcount > 0) ? (
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={customerGrowthData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="time" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <RechartsTooltip
                    contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '6px' }}
                  />
                  <Area
                    type="monotone"
                    dataKey="Headcount"
                    stroke="hsl(var(--chart-3))"
                    fill="hsl(var(--chart-3) / 0.15)"
                    strokeWidth={2}
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[250px] flex items-center justify-center text-muted-foreground">
                <div className="text-center">
                  <Users className="h-10 w-10 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">Connect Stripe or import data for growth metrics</p>
                  <p className="text-xs mt-1">Tracks headcount and customer growth over time</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
      </ScrollReveal>

      <ScrollReveal delay={0.15}>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card data-testid="chart-unit-economics">
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
                  <YAxis tickFormatter={(v) => `$${(v / 1000).toFixed(0)}K`} tick={{ fontSize: 12 }} />
                  <RechartsTooltip
                    formatter={(value: number) => formatCurrency(value)}
                    contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '6px' }}
                  />
                  <Legend />
                  <Line type="monotone" dataKey="cac" stroke="hsl(var(--chart-1))" name="CAC" dot={false} strokeWidth={2} />
                  <Line type="monotone" dataKey="ltv" stroke="hsl(var(--chart-3))" name="LTV" dot={false} strokeWidth={2} />
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

        <Card data-testid="chart-margins-churn">
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
                  <YAxis tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} tick={{ fontSize: 12 }} />
                  <RechartsTooltip
                    formatter={(value: number) => formatPercent(value)}
                    contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '6px' }}
                  />
                  <Legend />
                  <Line type="monotone" dataKey="gross_margin" stroke="hsl(var(--chart-2))" name="Gross Margin" dot={false} strokeWidth={2} />
                  <Line type="monotone" dataKey="churn_rate" stroke="hsl(var(--destructive))" name="Churn Rate" dot={false} strokeWidth={2} />
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
      </ScrollReveal>

      <DataSourcesPanel onAddIntegration={() => navigate('/integrations')} />
    </div>
    </FadeIn>
  );
}
