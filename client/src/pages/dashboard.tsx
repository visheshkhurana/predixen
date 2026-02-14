import { useState, useCallback, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { EnhancedKPICard } from "@/components/enhanced-kpi-card";
import { CashFlowChart } from "@/components/cash-flow-chart";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Link } from "wouter";
import { useFounderStore } from "@/store/founderStore";
import { CrossPageIntelligence } from "@/components/CrossPageIntelligence";
import { useRealtimeKPI, KPIMetrics } from "@/hooks/useRealtimeKPI";
import { useFinancialMetrics } from "@/hooks/useFinancialMetrics";
import {
  DollarSign,
  Flame,
  Calendar,
  TrendingUp,
  TrendingDown,
  Plus,
  ArrowRight,
  ArrowUpRight,
  ArrowDownRight,
  Info,
  Percent,
  Target,
  AlertCircle,
  Lightbulb,
  BarChart3,
  AlertTriangle,
  ExternalLink,
  Download,
  Wifi,
  WifiOff,
  Clock,
  Activity,
  Users,
  RefreshCw,
  Mail,
  Loader2,
  Send,
} from "lucide-react";
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { SimulationResult, Scenario, DashboardKPIs } from "@shared/schema";
import { formatCurrencyAbbrev, formatRunway } from "@/lib/utils";

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

type TimePeriod = "last_month" | "this_quarter" | "last_quarter" | "this_year" | "last_12_months";

const periodLabels: Record<TimePeriod, string> = {
  last_month: "Last Month",
  this_quarter: "This Quarter",
  last_quarter: "Last Quarter",
  this_year: "This Year",
  last_12_months: "Last 12 Months",
};

export default function Dashboard() {
  const { metrics: financialMetrics, isLoading: metricsLoading } = useFinancialMetrics();
  const { currentCompany: selectedCompany } = useFounderStore();
  const companyCurrency = selectedCompany?.currency || 'USD';
  const formatCurrency = useCallback((value: number) => formatCurrencyAbbrev(value, companyCurrency), [companyCurrency]);
  const [selectedPeriod, setSelectedPeriod] = useState<TimePeriod>("last_12_months");
  const [activeTab, setActiveTab] = useState<string>("overview");
  const [historicalData, setHistoricalData] = useState<Array<KPIMetrics & { time: string }>>([]);
  
  const handleKPIUpdate = useCallback((update: import('@/hooks/useRealtimeKPI').KPIUpdate) => {
    setHistoricalData(prev => {
      const newData = [...prev, { ...update.metrics, time: new Date(update.timestamp).toLocaleTimeString() }];
      return newData.slice(-20);
    });
  }, []);
  
  const kpiOptions = useMemo(() => ({
    enabled: !!selectedCompany?.id && activeTab === 'realtime',
    onUpdate: handleKPIUpdate
  }), [selectedCompany?.id, activeTab, handleKPIUpdate]);
  
  const { data: liveData, isConnected } = useRealtimeKPI(
    selectedCompany?.id ?? null,
    kpiOptions
  );

  const rawMetrics = liveData?.metrics ?? {
    monthly_revenue: financialMetrics.mrr,
    mrr: financialMetrics.mrr,
    arr: financialMetrics.arr,
    cash_balance: financialMetrics.cashOnHand,
    net_burn: financialMetrics.netBurn,
    runway_months: financialMetrics.runway === Infinity ? 60 : financialMetrics.runway,
    gross_margin: financialMetrics.grossMarginPct,
    churn_rate: financialMetrics.churnRatePct,
    cac: financialMetrics.cac,
    ltv: financialMetrics.ltv,
    ltv_cac_ratio: financialMetrics.ltvCacRatio,
    headcount: financialMetrics.headcount,
    revenue_per_employee: financialMetrics.revenuePerEmployee
  };
  
  const liveMetrics = {
    ...rawMetrics,
    runway_months: Math.max(0, Math.min(rawMetrics.runway_months || (financialMetrics.runway === Infinity ? 60 : financialMetrics.runway) || 18, 60)),
    cac: rawMetrics.cac > 0 ? rawMetrics.cac : financialMetrics.cac,
    ltv: rawMetrics.ltv > 0 ? rawMetrics.ltv : financialMetrics.ltv,
    ltv_cac_ratio: rawMetrics.ltv_cac_ratio > 0 ? rawMetrics.ltv_cac_ratio : financialMetrics.ltvCacRatio,
  };
  
  const { data: scenarios, isLoading: scenariosLoading } = useQuery<Scenario[]>({
    queryKey: ["/api/scenarios"],
  });

  const { data: latestResult, isLoading: resultLoading } = useQuery<SimulationResult>({
    queryKey: ["/api/simulations/latest"],
  });

  const { data: kpis, isLoading: kpisLoading } = useQuery<DashboardKPIs>({
    queryKey: ["/api/dashboard/companies", selectedCompany?.id, "kpis", selectedPeriod],
    queryFn: async () => {
      const res = await fetch(`/api/dashboard/companies/${selectedCompany?.id}/kpis?period=${selectedPeriod}`);
      if (!res.ok) throw new Error("Failed to fetch KPIs");
      return res.json();
    },
    enabled: !!selectedCompany?.id,
  });

  const { data: trendData } = useQuery<{ days: number; data: Array<{ date: string; runway_p50?: number; runway_p10?: number; runway_p90?: number }> }>({
    queryKey: ["/api/companies", selectedCompany?.id, "trends"],
    queryFn: async () => {
      const token = localStorage.getItem('predixen-token');
      const res = await fetch(`/api/companies/${selectedCompany?.id}/trends?days=90`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (!res.ok) return { days: 90, data: [] };
      return res.json();
    },
    enabled: !!selectedCompany?.id,
  });

  const [digestSending, setDigestSending] = useState(false);

  const { data: digestPrefs } = useQuery<{ monthly_digest: boolean }>({
    queryKey: ["/api/companies", selectedCompany?.id, "digest/preferences"],
    queryFn: async () => {
      const t = localStorage.getItem('predixen-token');
      const res = await fetch(`/api/companies/${selectedCompany?.id}/digest/preferences`, {
        headers: { 'Authorization': `Bearer ${t}` },
      });
      if (!res.ok) return { monthly_digest: true };
      return res.json();
    },
    enabled: !!selectedCompany?.id,
  });

  const isLoading = scenariosLoading || resultLoading || kpisLoading;

  const getPriorityBadge = (priority: string) => {
    switch (priority) {
      case "high":
        return <Badge variant="destructive" className="text-xs">High Priority</Badge>;
      case "medium":
        return <Badge variant="secondary" className="bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400 text-xs">Medium</Badge>;
      default:
        return <Badge variant="secondary" className="text-xs">Low</Badge>;
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      <CrossPageIntelligence context="dashboard" className="mb-2" testId="dashboard-intelligence" />
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Monitor your startup's financial health
          </p>
        </div>
        <div className="flex items-center gap-3">
          {activeTab === 'overview' && (
            <Select
              value={selectedPeriod}
              onValueChange={(value) => setSelectedPeriod(value as TimePeriod)}
            >
              <SelectTrigger className="w-[160px]" data-testid="select-period">
                <SelectValue placeholder="Select period" />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(periodLabels).map(([value, label]) => (
                  <SelectItem key={value} value={value} data-testid={`select-period-${value}`}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          
          {activeTab === 'realtime' && (
            <Badge variant={isConnected ? "default" : "secondary"} className="gap-1">
              {isConnected ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
              {isConnected ? 'Live' : 'Disconnected'}
            </Badge>
          )}
          
          {kpis && (
            <Tooltip>
              <TooltipTrigger asChild>
                <div 
                  className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-muted cursor-help"
                  data-testid="indicator-data-confidence"
                >
                  <Info className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm font-medium" data-testid="text-data-confidence-value">
                    Data Confidence: {kpis.dataConfidence}%
                  </span>
                </div>
              </TooltipTrigger>
              <TooltipContent className="max-w-xs">
                <p>Data confidence score reflects the completeness and accuracy of your financial inputs. Upload more data to improve this score.</p>
              </TooltipContent>
            </Tooltip>
          )}
          {selectedCompany?.id && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Select
                  onValueChange={async (format) => {
                    const { token } = useFounderStore.getState();
                    const url = `/api/companies/${selectedCompany.id}/financials/export?format=${format}`;
                    try {
                      const res = await fetch(url, {
                        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
                      });
                      if (!res.ok) {
                        if (res.status === 404) {
                          console.warn('No financial data to export');
                          return;
                        }
                        throw new Error('Export failed');
                      }
                      let downloadUrl: string;
                      if (format === 'csv') {
                        const blob = await res.blob();
                        downloadUrl = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = downloadUrl;
                        a.download = `${selectedCompany.name || 'financials'}_export.csv`;
                        a.click();
                      } else {
                        const data = await res.json();
                        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                        downloadUrl = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = downloadUrl;
                        a.download = `${selectedCompany.name || 'financials'}_export.json`;
                        a.click();
                      }
                      // Clean up download URL after a short delay
                      setTimeout(() => window.URL.revokeObjectURL(downloadUrl), 1000);
                    } catch (err) {
                      console.error('Export failed:', err);
                    }
                  }}
                >
                  <SelectTrigger className="w-[140px]" data-testid="select-export-format">
                    <Download className="h-4 w-4 mr-2" />
                    <SelectValue placeholder="Export Data" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="csv" data-testid="select-export-csv">Export CSV</SelectItem>
                    <SelectItem value="json" data-testid="select-export-json">Export JSON</SelectItem>
                  </SelectContent>
                </Select>
              </TooltipTrigger>
              <TooltipContent>
                <p>Download your reconciled financial data</p>
              </TooltipContent>
            </Tooltip>
          )}
          <Button asChild data-testid="button-new-scenario">
            <Link href="/scenarios">
              <Plus className="h-4 w-4 mr-2" />
              New Scenario
            </Link>
          </Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList data-testid="tabs-dashboard-view">
          <TabsTrigger value="overview" data-testid="tab-overview">Overview</TabsTrigger>
          <TabsTrigger value="realtime" data-testid="tab-realtime">Real-time</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          {kpis?.missingData && kpis.missingData.length > 0 && (
        <Alert variant="destructive" className="border-amber-500/50 bg-amber-50 dark:bg-amber-900/20" data-testid="alert-missing-data">
          <AlertTriangle className="h-4 w-4 text-amber-600" />
          <AlertTitle className="text-amber-800 dark:text-amber-400">Data Missing</AlertTitle>
          <AlertDescription className="text-amber-700 dark:text-amber-300">
            <ul className="mt-2 space-y-1">
              {kpis.missingData.map((item: { field: string; message: string }, idx: number) => (
                <li key={idx} className="flex items-center gap-2">
                  <span>{item.message}</span>
                </li>
              ))}
            </ul>
            <Button asChild variant="outline" size="sm" className="mt-3" data-testid="button-fix-data">
              <Link href="/ingest">
                <ExternalLink className="h-3 w-3 mr-1" />
                Fix Now
              </Link>
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {isLoading ? (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <Card className="lg:col-span-1 lg:row-span-2">
              <CardContent className="p-6">
                <Skeleton className="h-4 w-24 mb-2" />
                <Skeleton className="h-12 w-32 mb-4" />
                <Skeleton className="h-16 w-full" />
              </CardContent>
            </Card>
            {[...Array(4)].map((_, i) => (
              <Card key={i}>
                <CardContent className="p-4">
                  <Skeleton className="h-4 w-24 mb-2" />
                  <Skeleton className="h-8 w-32" />
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      ) : kpis ? (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-1 lg:row-span-2">
              <EnhancedKPICard
                data={kpis.runway}
                title="Runway (P50)"
                format="months"
                icon={<Calendar className="h-5 w-5" />}
                highlighted={true}
                testId="kpi-runway"
              />
            </div>
            
            <EnhancedKPICard
              data={kpis.cashOnHand}
              title="Cash on Hand"
              format="currency"
              currency={companyCurrency}
              icon={<DollarSign className="h-4 w-4" />}
              testId="kpi-cash"
            />
            
            <EnhancedKPICard
              data={kpis.netBurn}
              title="Net Burn"
              format="currency"
              currency={companyCurrency}
              icon={<Flame className="h-4 w-4" />}
              testId="kpi-burn"
            />
            
            <EnhancedKPICard
              data={kpis.mrr}
              title="MRR"
              format="currency"
              currency={companyCurrency}
              icon={<TrendingUp className="h-4 w-4" />}
              testId="kpi-mrr"
            />
            
            <EnhancedKPICard
              data={kpis.grossMargin}
              title="Gross Margin"
              format="percent"
              icon={<Percent className="h-4 w-4" />}
              testId="kpi-margin"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <EnhancedKPICard
              data={kpis.revenueGrowth}
              title="Revenue Growth (YoY)"
              format="percent"
              icon={<BarChart3 className="h-4 w-4" />}
              testId="kpi-growth"
            />
            
            <EnhancedKPICard
              data={kpis.burnMultiple}
              title="Burn Multiple"
              format="multiple"
              icon={<Target className="h-4 w-4" />}
              testId="kpi-burn-multiple"
            />
            
            <Card className="overflow-visible" data-testid="kpi-quality-of-growth">
              <CardContent className="p-4">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium text-muted-foreground">Quality of Growth</span>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span 
                        className="text-muted-foreground cursor-help"
                        data-testid="tooltip-trigger-qog"
                      >
                        <Info className="h-3 w-3" />
                      </span>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Composite score based on growth efficiency, unit economics, and capital efficiency</p>
                    </TooltipContent>
                  </Tooltip>
                </div>
                <div className="mt-2">
                  <span className="text-2xl font-semibold font-mono tracking-tight" data-testid="text-qog-value">
                    {kpis.qualityOfGrowthIndex !== null ? kpis.qualityOfGrowthIndex : "N/A"}
                  </span>
                  <span className="text-sm text-muted-foreground ml-1">/100</span>
                </div>
                <p className="text-xs text-muted-foreground mt-2" data-testid="text-top-concentration">
                  Top 5 concentration: {kpis.topConcentration !== null ? `${kpis.topConcentration}%` : "N/A"}
                </p>
              </CardContent>
            </Card>
          </div>

          {kpis.recommendations && kpis.recommendations.length > 0 && (
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2">
                  <Lightbulb className="h-5 w-5 text-primary" />
                  <CardTitle className="text-lg">Top Recommendations</CardTitle>
                </div>
                <CardDescription>Context-aware suggestions based on your metrics</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {kpis.recommendations.map((rec) => (
                    <div
                      key={rec.id}
                      className="flex items-start justify-between gap-4 p-4 rounded-lg bg-muted/50"
                      data-testid={`recommendation-${rec.id}`}
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                          <h4 className="font-medium text-sm" data-testid={`text-recommendation-title-${rec.id}`}>
                            {rec.title}
                          </h4>
                          {getPriorityBadge(rec.priority)}
                        </div>
                        <p className="text-sm text-muted-foreground" data-testid={`text-recommendation-desc-${rec.id}`}>
                          {rec.description}
                        </p>
                      </div>
                      {rec.action && (
                        <Button 
                          variant="outline" 
                          size="sm" 
                          asChild
                          data-testid={`button-recommendation-action-${rec.id}`}
                        >
                          <Link href="/scenarios">
                            {rec.action}
                            <ArrowRight className="h-3 w-3 ml-1" />
                          </Link>
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {latestResult && <CashFlowChart projections={latestResult.projections} currency={companyCurrency} />}

          {scenarios && scenarios.length > 0 && (
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <CardTitle className="text-lg">Recent Scenarios</CardTitle>
                    <CardDescription>Compare different financial scenarios</CardDescription>
                  </div>
                  <Button variant="ghost" size="sm" asChild>
                    <Link href="/scenarios">
                      View all
                      <ArrowRight className="h-4 w-4 ml-1" />
                    </Link>
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {scenarios.slice(0, 3).map((scenario) => (
                    <div
                      key={scenario.id}
                      className="flex items-center justify-between p-3 rounded-md bg-muted/50"
                      data-testid={`scenario-item-${scenario.id}`}
                    >
                      <div>
                        <p className="font-medium text-sm">{scenario.name}</p>
                        {scenario.description && (
                          <p className="text-xs text-muted-foreground">{scenario.description}</p>
                        )}
                      </div>
                      <Button variant="ghost" size="sm" asChild>
                        <Link href={`/scenarios?id=${scenario.id}`}>
                          <ArrowRight className="h-4 w-4" />
                        </Link>
                      </Button>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      ) : latestResult ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-4">
                <span className="text-sm font-medium text-muted-foreground">Cash on Hand</span>
                <div className="mt-2">
                  <span className="text-2xl font-semibold font-mono">
                    ${(latestResult.summary.initialCash / 1000000).toFixed(1)}M
                  </span>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <span className="text-sm font-medium text-muted-foreground">Monthly Burn</span>
                <div className="mt-2">
                  <span className="text-2xl font-semibold font-mono">
                    ${(latestResult.summary.avgMonthlyBurn / 1000).toFixed(0)}K
                  </span>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <span className="text-sm font-medium text-muted-foreground">Runway</span>
                <div className="mt-2">
                  <span className="text-2xl font-semibold font-mono">
                    {formatRunway(latestResult.summary.runwayMonths)}
                  </span>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <span className="text-sm font-medium text-muted-foreground">MRR</span>
                <div className="mt-2">
                  <span className="text-2xl font-semibold font-mono">
                    ${((latestResult.projections[0]?.revenue || 0) / 1000).toFixed(0)}K
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>

          <CashFlowChart projections={latestResult.projections} currency={companyCurrency} />

          {trendData && trendData.data && trendData.data.length > 1 && (
            <Card data-testid="card-runway-trend">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Activity className="h-5 w-5 text-primary" />
                  Runway Trend (90 days)
                </CardTitle>
                <CardDescription>How your projected runway has changed over time based on simulation snapshots</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={trendData.data}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(v: string) => { const d = new Date(v); return `${d.getMonth()+1}/${d.getDate()}`; }} />
                    <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${v.toFixed(0)}mo`} />
                    <RechartsTooltip contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))" }} formatter={(value: number) => [`${value.toFixed(1)} months`]} />
                    <Line type="monotone" dataKey="runway_p50" stroke="#3b82f6" strokeWidth={2} dot={false} name="Runway (P50)" />
                    <Line type="monotone" dataKey="runway_p90" stroke="#22c55e" strokeWidth={1} strokeDasharray="4 4" dot={false} name="Best Case (P90)" />
                    <Line type="monotone" dataKey="runway_p10" stroke="#f59e0b" strokeWidth={1} strokeDasharray="4 4" dot={false} name="Worst Case (P10)" />
                    <Legend />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}
        </>
      ) : (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <div className="p-4 rounded-full bg-muted mb-4">
              <FlaskConical className="h-8 w-8 text-muted-foreground" />
            </div>
            <h3 className="font-semibold text-lg mb-2">No simulations yet</h3>
            <p className="text-muted-foreground text-sm text-center max-w-md mb-4">
              Create your first scenario to see projected cash flow, runway, and financial metrics
            </p>
            <Button asChild data-testid="button-create-first-scenario">
              <Link href="/scenarios">
                <Plus className="h-4 w-4 mr-2" />
                Create Scenario
              </Link>
            </Button>
          </CardContent>
        </Card>
      )}

          <Card data-testid="card-digest-preferences">
            <CardContent className="p-4 flex items-center justify-between gap-4 flex-wrap">
              <div className="flex items-center gap-3">
                <Mail className="h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium">Monthly Digest Email</p>
                  <p className="text-xs text-muted-foreground">Receive a summary of your key metrics, risks, and recommendations each month</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Switch
                  checked={digestPrefs?.monthly_digest ?? true}
                  onCheckedChange={async (checked) => {
                    if (!selectedCompany) return;
                    try {
                      const t = localStorage.getItem('predixen-token');
                      const res = await fetch(`/api/companies/${selectedCompany.id}/digest/preferences`, {
                        method: 'PUT',
                        headers: { 'Authorization': `Bearer ${t}`, 'Content-Type': 'application/json' },
                        body: JSON.stringify({ monthly_digest: checked }),
                      });
                      if (!res.ok) throw new Error();
                      const { queryClient } = await import("@/lib/queryClient");
                      queryClient.invalidateQueries({ queryKey: ["/api/companies", selectedCompany.id, "digest/preferences"] });
                    } catch {
                      const { queryClient } = await import("@/lib/queryClient");
                      queryClient.invalidateQueries({ queryKey: ["/api/companies", selectedCompany.id, "digest/preferences"] });
                    }
                  }}
                  data-testid="switch-digest"
                />
                <Button
                  variant="outline"
                  size="sm"
                  disabled={digestSending}
                  onClick={async () => {
                    if (!selectedCompany) return;
                    setDigestSending(true);
                    const t = localStorage.getItem('predixen-token');
                    try {
                      await fetch(`/api/companies/${selectedCompany.id}/digest/send`, {
                        method: 'POST',
                        headers: { 'Authorization': `Bearer ${t}` },
                      });
                    } catch {}
                    setDigestSending(false);
                  }}
                  data-testid="button-send-digest"
                >
                  {digestSending ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Send className="h-4 w-4 mr-1" />}
                  Send Now
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="realtime" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <KPITile
              title="MRR"
              value={formatCurrency(liveMetrics.mrr)}
              icon={<TrendingUp className="h-4 w-4" />}
              trend="up"
              trendValue="+8%"
              subtitle="Monthly Recurring Revenue"
              isLive={isConnected}
            />
            <KPITile
              title="ARR"
              value={formatCurrency(liveMetrics.arr)}
              icon={<DollarSign className="h-4 w-4" />}
              trend="up"
              subtitle="Annual Recurring Revenue"
              isLive={isConnected}
            />
            <KPITile
              title="Cash Balance"
              value={formatCurrency(liveMetrics.cash_balance)}
              icon={<DollarSign className="h-4 w-4" />}
              isLive={isConnected}
            />
            <KPITile
              title="Runway"
              value={formatRunway(liveMetrics.runway_months)}
              icon={<Clock className="h-4 w-4" />}
              trend={liveMetrics.runway_months < 6 ? 'down' : 'neutral'}
              subtitle={liveMetrics.runway_months < 6 ? 'Low runway' : ''}
              isLive={isConnected}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <KPITile
              title="Net Burn"
              value={formatCurrency(liveMetrics.net_burn)}
              icon={<TrendingDown className="h-4 w-4" />}
              subtitle="per month"
              isLive={isConnected}
            />
            <KPITile
              title="Gross Margin"
              value={formatPercent(liveMetrics.gross_margin)}
              icon={<Percent className="h-4 w-4" />}
              trend={liveMetrics.gross_margin >= 0.7 ? 'up' : 'neutral'}
              isLive={isConnected}
            />
            <KPITile
              title="Churn Rate"
              value={formatPercent(liveMetrics.churn_rate)}
              icon={<Activity className="h-4 w-4" />}
              trend={liveMetrics.churn_rate <= 0.03 ? 'up' : 'down'}
              isLive={isConnected}
            />
            <KPITile
              title="Headcount"
              value={liveMetrics.headcount}
              icon={<Users className="h-4 w-4" />}
              subtitle={`${formatCurrency(liveMetrics.revenue_per_employee)}/emp`}
              isLive={isConnected}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <KPITile
              title="CAC"
              value={metricsLoading ? '...' : financialMetrics.cac > 0 ? formatCurrency(financialMetrics.cac) : 'N/A'}
              icon={<DollarSign className="h-4 w-4" />}
              isLive={isConnected}
            />
            <KPITile
              title="LTV"
              value={metricsLoading ? '...' : financialMetrics.ltv > 0 ? formatCurrency(financialMetrics.ltv) : 'N/A'}
              icon={<DollarSign className="h-4 w-4" />}
              isLive={isConnected}
            />
            <KPITile
              title="LTV/CAC Ratio"
              value={metricsLoading ? '...' : financialMetrics.ltvCacRatio > 0 ? `${financialMetrics.ltvCacRatio.toFixed(1)}x` : 'N/A'}
              icon={<TrendingUp className="h-4 w-4" />}
              trend={financialMetrics.ltvCacRatio > 0 ? (financialMetrics.ltvCacRatio >= 3 ? 'up' : financialMetrics.ltvCacRatio < 2 ? 'down' : 'neutral') : 'neutral'}
              subtitle={financialMetrics.ltvCacRatio > 0 ? (financialMetrics.ltvCacRatio >= 3 ? 'Healthy' : financialMetrics.ltvCacRatio < 2 ? 'Needs improvement' : '') : ''}
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
                      <YAxis tickFormatter={(v) => formatCurrency(v)} tick={{ fontSize: 12 }} />
                      <RechartsTooltip formatter={(value: number) => formatCurrency(value)} />
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
                      <YAxis yAxisId="left" tickFormatter={(v) => formatCurrency(v)} tick={{ fontSize: 12 }} />
                      <YAxis yAxisId="right" orientation="right" tickFormatter={(v) => `${v}mo`} tick={{ fontSize: 12 }} />
                      <RechartsTooltip />
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
                      <YAxis tickFormatter={(v) => formatCurrency(v)} tick={{ fontSize: 12 }} />
                      <RechartsTooltip formatter={(value: number) => formatCurrency(value)} />
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
                      <RechartsTooltip formatter={(value: number) => formatPercent(value)} />
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
        </TabsContent>
      </Tabs>
    </div>
  );
}

function FlaskConical(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M10 2v7.31" />
      <path d="M14 9.3V2" />
      <path d="M8.5 2h7" />
      <path d="M14 9.3a6.5 6.5 0 1 1-4 0" />
      <path d="M5.52 16h12.96" />
    </svg>
  );
}
