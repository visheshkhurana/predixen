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
  HelpCircle
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';

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
}

interface DashboardKPICardsProps {
  simulation?: SimulationData;
  metrics?: TruthScanMetrics;
  previousMetrics?: TruthScanMetrics;
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

function formatCurrency(value: number): string {
  if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
  if (value >= 1000) return `$${(value / 1000).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

export function DashboardKPICards({ simulation, metrics, previousMetrics, testId = 'dashboard-kpis' }: DashboardKPICardsProps) {
  const runwayP50 = simulation?.runway?.p50 || extractValue(metrics?.runway_months);
  const survival18m = simulation?.survival?.['18m'] || 0;
  const mrr = extractValue(metrics?.monthly_revenue);
  const burnMultiple = extractValue(metrics?.burn_multiple);
  const grossMargin = extractValue(metrics?.gross_margin);
  const netBurn = extractValue(metrics?.net_burn);
  const cashBalance = extractValue(metrics?.cash_balance);
  const growthRate = extractValue(metrics?.revenue_growth_mom);
  const churnRate = extractValue(metrics?.churn_rate);
  
  const prevMrr = previousMetrics ? extractValue(previousMetrics.monthly_revenue) : null;
  const mrrTrend = prevMrr && mrr ? (mrr > prevMrr ? 'up' : mrr < prevMrr ? 'down' : 'stable') : undefined;
  const mrrChange = prevMrr && mrr ? `${((mrr - prevMrr) / prevMrr * 100).toFixed(1)}%` : undefined;

  return (
    <div className="space-y-4" data-testid={testId}>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard
          title="Runway (P50)"
          value={`${runwayP50.toFixed(1)} mo`}
          subtitle={simulation?.runway ? `P10: ${simulation.runway.p10?.toFixed(1)} / P90: ${simulation.runway.p90?.toFixed(1)}` : undefined}
          status={getRunwayStatus(runwayP50)}
          icon={<Clock className="h-4 w-4" />}
          tooltip="Months of runway remaining at current burn rate. P50 is the median outcome from Monte Carlo simulations."
          testId={`${testId}-runway`}
        />
        
        <KPICard
          title="18-Month Survival"
          value={`${survival18m.toFixed(0)}%`}
          subtitle={simulation?.survival?.['12m'] ? `12-mo: ${simulation.survival['12m'].toFixed(0)}%` : undefined}
          status={getSurvivalStatus(survival18m)}
          icon={survival18m >= 80 ? <CheckCircle className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
          tooltip="Probability of having positive cash balance after 18 months based on simulations."
          testId={`${testId}-survival`}
        />
        
        <KPICard
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
        
        <KPICard
          title="Burn Multiple"
          value={burnMultiple ? burnMultiple.toFixed(1) : 'N/A'}
          subtitle={burnMultiple ? (burnMultiple <= 1.5 ? 'Efficient' : burnMultiple <= 3 ? 'Moderate' : 'High burn') : undefined}
          status={burnMultiple ? getBurnMultipleStatus(burnMultiple) : 'neutral'}
          icon={<Percent className="h-4 w-4" />}
          tooltip="Net burn divided by net new ARR. Lower is better - indicates how efficiently you convert spend into growth."
          testId={`${testId}-burn-multiple`}
        />
      </div>
      
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard
          title="Cash Balance"
          value={formatCurrency(cashBalance)}
          status="neutral"
          icon={<DollarSign className="h-4 w-4" />}
          tooltip="Current cash on hand."
          testId={`${testId}-cash`}
        />
        
        <KPICard
          title="Net Burn"
          value={formatCurrency(Math.abs(netBurn))}
          subtitle={netBurn > 0 ? 'Cash positive' : 'Monthly outflow'}
          status="neutral"
          icon={<TrendingDown className="h-4 w-4" />}
          tooltip="Monthly cash outflow (expenses minus revenue)."
          testId={`${testId}-burn`}
        />
        
        <KPICard
          title="Gross Margin"
          value={`${grossMargin.toFixed(0)}%`}
          subtitle={grossMargin >= 70 ? 'Strong' : grossMargin >= 50 ? 'Moderate' : 'Needs improvement'}
          status={grossMargin >= 70 ? 'healthy' : grossMargin >= 50 ? 'warning' : 'critical'}
          icon={<Percent className="h-4 w-4" />}
          tooltip="Revenue minus cost of goods sold, as a percentage of revenue."
          testId={`${testId}-margin`}
        />
        
        <KPICard
          title="Churn Rate"
          value={churnRate ? `${(churnRate * 100).toFixed(1)}%` : 'N/A'}
          subtitle={churnRate ? (churnRate <= 0.03 ? 'Low churn' : churnRate <= 0.05 ? 'Moderate' : 'High churn') : undefined}
          status={churnRate ? (churnRate <= 0.03 ? 'healthy' : churnRate <= 0.05 ? 'warning' : 'critical') : 'neutral'}
          icon={<Users className="h-4 w-4" />}
          tooltip="Monthly customer or revenue churn rate."
          testId={`${testId}-churn`}
        />
      </div>
    </div>
  );
}
