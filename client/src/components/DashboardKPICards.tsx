import { useState, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { 
  TrendingUp, 
  TrendingDown, 
  Clock, 
  DollarSign, 
  Percent, 
  Users,
  AlertTriangle,
  CheckCircle,
  HelpCircle,
  Wifi,
  WifiOff,
  RefreshCw
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { KPIConfigWizard, useKPIConfig } from './KPIConfigWizard';
import { useWebSocket } from '@/lib/websocket';
import { useCurrency } from '@/hooks/useCurrency';

interface KPICardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: 'up' | 'down' | 'stable';
  trendValue?: string;
  status?: 'healthy' | 'warning' | 'critical' | 'neutral';
  icon: React.ReactNode;
  tooltip?: string;
  testId?: string;
}

function KPICard({ title, value, subtitle, trend, trendValue, status = 'neutral', icon, tooltip, testId }: KPICardProps) {
  const statusColors = {
    healthy: 'border-emerald-500/50 dark:border-emerald-400/50 bg-emerald-500/5 dark:bg-emerald-500/10',
    warning: 'border-amber-500/50 dark:border-amber-400/50 bg-amber-500/5 dark:bg-amber-500/10',
    critical: 'border-red-500/50 dark:border-red-400/50 bg-red-500/5 dark:bg-red-500/10',
    neutral: 'border-border',
  };
  
  const statusBadge = {
    healthy: { variant: 'default' as const, label: 'Healthy' },
    warning: { variant: 'secondary' as const, label: 'At Risk' },
    critical: { variant: 'destructive' as const, label: 'Critical' },
    neutral: null,
  };
  
  return (
    <Card className={cn("border-2 transition-colors", statusColors[status])} data-testid={testId}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="flex items-center gap-2 text-muted-foreground">
            {icon}
            <span className="text-sm font-medium">{title}</span>
            {tooltip && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <HelpCircle className="h-3 w-3 cursor-help" />
                </TooltipTrigger>
                <TooltipContent className="max-w-xs">
                  <p className="text-sm">{tooltip}</p>
                </TooltipContent>
              </Tooltip>
            )}
          </div>
          {statusBadge[status] && (
            <Badge variant={statusBadge[status].variant} className="text-xs">
              {statusBadge[status].label}
            </Badge>
          )}
        </div>
        
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-bold font-mono" data-testid={`${testId}-value`}>
            {value}
          </span>
          {trend && trendValue && (
            <span className={cn(
              "flex items-center text-sm",
              trend === 'up' && "text-emerald-600 dark:text-emerald-400",
              trend === 'down' && "text-red-600 dark:text-red-400",
              trend === 'stable' && "text-muted-foreground"
            )}>
              {trend === 'up' && <TrendingUp className="h-3 w-3 mr-0.5" />}
              {trend === 'down' && <TrendingDown className="h-3 w-3 mr-0.5" />}
              {trendValue}
            </span>
          )}
        </div>
        
        {subtitle && (
          <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
        )}
      </CardContent>
    </Card>
  );
}

interface SimulationData {
  runway?: {
    p10?: number;
    p50?: number;
    p90?: number;
  };
  survival?: {
    '12m'?: number;
    '18m'?: number;
    '24m'?: number;
  };
  summary?: {
    start_cash?: number;
    end_cash?: number;
    avg_burn?: number;
    total_revenue?: number;
  };
}

interface TruthScanMetrics {
  monthly_revenue?: number | { value: number };
  revenue_growth_mom?: number | { value: number };
  burn_multiple?: number | { value: number };
  gross_margin?: number | { value: number };
  net_burn?: number | { value: number };
  cash_balance?: number | { value: number };
  runway_months?: number | { value: number };
  churn_rate?: number | { value: number };
  ltv_cac_ratio?: number | { value: number };
  net_revenue_retention?: number | { value: number };
}

interface DashboardKPICardsProps {
  simulation?: SimulationData;
  metrics?: TruthScanMetrics;
  previousMetrics?: TruthScanMetrics;
  companyId?: number | null;
  showConfig?: boolean;
  testId?: string;
}

function extractValue(metric: number | { value: number } | undefined, defaultValue: number = 0): number {
  if (metric === undefined || metric === null) return defaultValue;
  if (typeof metric === 'object' && 'value' in metric) return metric.value;
  return metric;
}

function getRunwayStatus(months: number): 'healthy' | 'warning' | 'critical' {
  if (months >= 18) return 'healthy';
  if (months >= 12) return 'warning';
  return 'critical';
}

function getSurvivalStatus(probability: number): 'healthy' | 'warning' | 'critical' {
  if (probability >= 80) return 'healthy';
  if (probability >= 50) return 'warning';
  return 'critical';
}

function getBurnMultipleStatus(multiple: number): 'healthy' | 'warning' | 'critical' {
  if (multiple <= 1.5) return 'healthy';
  if (multiple <= 3) return 'warning';
  return 'critical';
}

export function DashboardKPICards({ simulation, metrics, previousMetrics, companyId, showConfig = true, testId = 'dashboard-kpis' }: DashboardKPICardsProps) {
  const { configs, handleConfigChange } = useKPIConfig();
  const { isConnected, metrics: wsMetrics, subscribe } = useWebSocket(companyId || null);
  const { format: formatCurrency } = useCurrency();
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [isUpdating, setIsUpdating] = useState(false);

  useEffect(() => {
    if (!companyId) return;
    
    const handleUpdate = () => {
      setLastUpdate(new Date());
      setIsUpdating(true);
      setTimeout(() => setIsUpdating(false), 1000);
    };

    const unsubMetric = subscribe('metric_update', handleUpdate);
    const unsubTruth = subscribe('truth_scan_update', handleUpdate);

    return () => {
      unsubMetric();
      unsubTruth();
    };
  }, [companyId, subscribe]);

  const mergedMetrics = { ...metrics };
  if (wsMetrics && Object.keys(wsMetrics).length > 0) {
    Object.entries(wsMetrics).forEach(([key, value]) => {
      if (typeof value === 'number' && !isNaN(value)) {
        (mergedMetrics as any)[key] = value;
      }
    });
  }

  const rawRunwayP50 = simulation?.runway?.p50 || extractValue(mergedMetrics?.runway_months);
  const survival18m = simulation?.survival?.['18m'] || 0;
  const mrr = extractValue(mergedMetrics?.monthly_revenue);
  const burnMultiple = extractValue(mergedMetrics?.burn_multiple);
  const grossMargin = extractValue(mergedMetrics?.gross_margin);
  const netBurn = extractValue(mergedMetrics?.net_burn);
  const cashBalance = extractValue(mergedMetrics?.cash_balance);
  const growthRate = extractValue(mergedMetrics?.revenue_growth_mom);
  const churnRate = extractValue(mergedMetrics?.churn_rate);
  const ltvCac = extractValue(mergedMetrics?.ltv_cac_ratio);
  
  const isSustainable = rawRunwayP50 >= 36 || netBurn <= 0;
  const runwayP50 = Math.min(rawRunwayP50, 60);
  const effectiveSurvival = isSustainable ? 100 : survival18m;
  
  const prevMrr = previousMetrics ? extractValue(previousMetrics.monthly_revenue) : null;
  const mrrTrend = prevMrr && mrr ? (mrr > prevMrr ? 'up' : mrr < prevMrr ? 'down' : 'stable') : undefined;
  const mrrChange = prevMrr && mrr ? `${((mrr - prevMrr) / prevMrr * 100).toFixed(1)}%` : undefined;

  const kpiCards: Record<string, JSX.Element> = {
    runway: (
      <KPICard
        key="runway"
        title="Runway (P50)"
        value={isSustainable ? 'Sustainable' : `${runwayP50.toFixed(1)} mo`}
        subtitle={!isSustainable && simulation?.runway ? `P10: ${Math.min(simulation.runway.p10 || 0, 60).toFixed(1)} / P90: ${Math.min(simulation.runway.p90 || 0, 60).toFixed(1)}` : (isSustainable ? 'Positive cash flow' : undefined)}
        status={isSustainable ? 'healthy' : getRunwayStatus(runwayP50)}
        icon={<Clock className="h-4 w-4" />}
        tooltip="Months of runway remaining at current burn rate. P50 is the median outcome from Monte Carlo simulations."
        testId={`${testId}-runway`}
      />
    ),
    survival: (
      <KPICard
        key="survival"
        title="18-Month Survival"
        value={`${effectiveSurvival.toFixed(0)}%`}
        subtitle={!isSustainable && simulation?.survival?.['12m'] ? `12-mo: ${simulation.survival['12m'].toFixed(0)}%` : (isSustainable ? 'Sustainable' : undefined)}
        status={getSurvivalStatus(effectiveSurvival)}
        icon={effectiveSurvival >= 80 ? <CheckCircle className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
        tooltip="Probability of having positive cash balance after 18 months based on simulations."
        testId={`${testId}-survival`}
      />
    ),
    mrr: (
      <KPICard
        key="mrr"
        title="Monthly Revenue"
        value={formatCurrency(mrr)}
        trend={mrrTrend}
        trendValue={mrrChange}
        subtitle={growthRate ? `${growthRate > 0 ? '+' : ''}${growthRate.toFixed(1)}% MoM` : undefined}
        status="neutral"
        icon={<DollarSign className="h-4 w-4" />}
        tooltip="Monthly recurring revenue from all customers."
        testId={`${testId}-mrr`}
      />
    ),
    burn_multiple: (
      <KPICard
        key="burn_multiple"
        title="Burn Multiple"
        value={burnMultiple ? burnMultiple.toFixed(1) : 'N/A'}
        subtitle={burnMultiple ? (burnMultiple <= 1.5 ? 'Efficient' : burnMultiple <= 3 ? 'Moderate' : 'High burn') : undefined}
        status={burnMultiple ? getBurnMultipleStatus(burnMultiple) : 'neutral'}
        icon={<Percent className="h-4 w-4" />}
        tooltip="Net burn divided by net new ARR. Lower is better - indicates how efficiently you convert spend into growth."
        testId={`${testId}-burn-multiple`}
      />
    ),
    cash_balance: (
      <KPICard
        key="cash_balance"
        title="Cash Balance"
        value={formatCurrency(cashBalance)}
        status="neutral"
        icon={<DollarSign className="h-4 w-4" />}
        tooltip="Current cash on hand."
        testId={`${testId}-cash`}
      />
    ),
    net_burn: (
      <KPICard
        key="net_burn"
        title="Net Burn"
        value={formatCurrency(Math.abs(netBurn))}
        subtitle={netBurn < 0 ? 'Cash positive' : 'Monthly outflow'}
        status={netBurn < 0 ? 'healthy' : netBurn > 50000 ? 'critical' : 'warning'}
        icon={<TrendingDown className="h-4 w-4" />}
        tooltip="Monthly cash outflow (expenses minus revenue). Negative means profitable."
        testId={`${testId}-burn`}
      />
    ),
    gross_margin: (
      <KPICard
        key="gross_margin"
        title="Gross Margin"
        value={`${grossMargin.toFixed(0)}%`}
        subtitle={grossMargin >= 70 ? 'Strong' : grossMargin >= 50 ? 'Moderate' : 'Needs improvement'}
        status={grossMargin >= 70 ? 'healthy' : grossMargin >= 50 ? 'warning' : 'critical'}
        icon={<Percent className="h-4 w-4" />}
        tooltip="Revenue minus cost of goods sold, as a percentage of revenue."
        testId={`${testId}-margin`}
      />
    ),
    churn_rate: (
      <KPICard
        key="churn_rate"
        title="Churn Rate"
        value={churnRate ? `${churnRate.toFixed(1)}%` : 'N/A'}
        subtitle={churnRate ? (churnRate <= 3 ? 'Low churn' : churnRate <= 5 ? 'Moderate' : 'High churn') : undefined}
        status={churnRate ? (churnRate <= 3 ? 'healthy' : churnRate <= 5 ? 'warning' : 'critical') : 'neutral'}
        icon={<Users className="h-4 w-4" />}
        tooltip="Monthly customer or revenue churn rate."
        testId={`${testId}-churn`}
      />
    ),
    ltv_cac: (
      <KPICard
        key="ltv_cac"
        title="LTV:CAC Ratio"
        value={ltvCac ? `${ltvCac.toFixed(1)}x` : 'N/A'}
        subtitle={ltvCac ? (ltvCac >= 3 ? 'Healthy' : ltvCac >= 1 ? 'Moderate' : 'Low') : undefined}
        status={ltvCac ? (ltvCac >= 3 ? 'healthy' : ltvCac >= 1 ? 'warning' : 'critical') : 'neutral'}
        icon={<Users className="h-4 w-4" />}
        tooltip="Lifetime value to customer acquisition cost ratio. 3x or higher is considered healthy."
        testId={`${testId}-ltv-cac`}
      />
    ),
    arr_growth: (
      <KPICard
        key="arr_growth"
        title="ARR Growth"
        value={growthRate ? `${(growthRate * 12).toFixed(0)}%` : 'N/A'}
        subtitle="Annualized growth rate"
        status={growthRate && growthRate * 12 >= 100 ? 'healthy' : growthRate && growthRate * 12 >= 50 ? 'warning' : 'neutral'}
        icon={<TrendingUp className="h-4 w-4" />}
        tooltip="Annual recurring revenue growth rate (MoM x 12)."
        testId={`${testId}-arr-growth`}
      />
    ),
    nrr: (() => {
      const rawNrr = extractValue(mergedMetrics?.net_revenue_retention);
      const nrrValid = rawNrr > 0 && rawNrr <= 200;
      return (
        <KPICard
          key="nrr"
          title="Net Revenue Retention"
          value={nrrValid ? `${rawNrr.toFixed(0)}%` : "N/A"}
          subtitle="Including expansion"
          status={!nrrValid ? "warning" : rawNrr >= 100 ? "healthy" : "critical"}
          icon={<Percent className="h-4 w-4" />}
          tooltip="Revenue retention including expansion revenue from existing customers. Requires customer data to compute."
          testId={`${testId}-nrr`}
        />
      );
    })(),
  };

  const enabledCards = configs
    .filter(c => c.enabled)
    .sort((a, b) => a.order - b.order)
    .map(c => kpiCards[c.id])
    .filter(Boolean);

  const firstRow = enabledCards.slice(0, 4);
  const secondRow = enabledCards.slice(4, 8);

  return (
    <div className="space-y-4" data-testid={testId}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <div className={cn(
                "flex items-center gap-1.5 px-2 py-1 rounded-full text-xs",
                isConnected ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400" : "bg-muted text-muted-foreground"
              )}>
                {isConnected ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
                {isConnected ? 'Live' : 'Offline'}
                {isUpdating && <RefreshCw className="h-3 w-3 animate-spin" />}
              </div>
            </TooltipTrigger>
            <TooltipContent>
              {isConnected 
                ? `Real-time updates enabled${lastUpdate ? `. Last update: ${lastUpdate.toLocaleTimeString()}` : ''}`
                : 'Connecting to real-time updates...'}
            </TooltipContent>
          </Tooltip>
        </div>
        {showConfig && (
          <KPIConfigWizard configs={configs} onConfigChange={handleConfigChange} />
        )}
      </div>

      {firstRow.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {firstRow}
        </div>
      )}
      
      {secondRow.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {secondRow}
        </div>
      )}
    </div>
  );
}
