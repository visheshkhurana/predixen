import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { 
  DollarSign, 
  TrendingUp, 
  TrendingDown, 
  Percent, 
  Calendar, 
  Wallet,
  AlertTriangle,
  CheckCircle2,
  Clock
} from 'lucide-react';
import { cn, formatCurrencyAbbrev } from '@/lib/utils';

interface ScenarioParams {
  name: string;
  pricing_change_pct: number;
  growth_uplift_pct: number;
  burn_reduction_pct: number;
  gross_margin_delta_pct: number;
  churn_change_pct: number;
  cac_change_pct: number;
  fundraise_month: number | null;
  fundraise_amount: number;
  tags: string[];
}

interface BaseMetrics {
  cashOnHand: number;
  monthlyExpenses: number;
  monthlyRevenue: number;
  currentRunway: number;
  growthRate: number;
}

interface ScenarioSummarySidebarProps {
  params: ScenarioParams;
  baseMetrics?: BaseMetrics;
  className?: string;
}

function formatCurrency(value: number): string {
  return formatCurrencyAbbrev(value);
}

function calculateProjectedMetrics(params: ScenarioParams, baseMetrics?: BaseMetrics) {
  if (!baseMetrics) return null;

  const burnReduction = baseMetrics.monthlyExpenses * (params.burn_reduction_pct / 100);
  const projectedExpenses = baseMetrics.monthlyExpenses - burnReduction;
  
  const pricingImpact = baseMetrics.monthlyRevenue * (params.pricing_change_pct / 100);
  const growthImpact = baseMetrics.monthlyRevenue * (params.growth_uplift_pct / 100) * 0.5;
  const projectedRevenue = baseMetrics.monthlyRevenue + pricingImpact + growthImpact;
  
  const projectedCash = baseMetrics.cashOnHand + params.fundraise_amount;
  const netBurn = projectedExpenses - projectedRevenue;
  
  const isProfitable = netBurn <= 0;
  const projectedRunway = netBurn > 0 ? projectedCash / netBurn : 900;
  const runwayChange = projectedRunway - baseMetrics.currentRunway;

  return {
    projectedExpenses,
    projectedRevenue,
    projectedCash,
    netBurn,
    isProfitable,
    projectedRunway,
    runwayChange,
    revenueChange: projectedRevenue - baseMetrics.monthlyRevenue,
    expenseChange: projectedExpenses - baseMetrics.monthlyExpenses,
  };
}

export function ScenarioSummarySidebar({ params, baseMetrics, className }: ScenarioSummarySidebarProps) {
  const projected = calculateProjectedMetrics(params, baseMetrics);

  const getRunwayStatus = () => {
    if (!projected) return { color: 'text-muted-foreground', label: 'Unknown', icon: Clock };
    if (projected.isProfitable) return { color: 'text-emerald-500', label: 'Sustainable', icon: CheckCircle2 };
    if (projected.projectedRunway >= 18) return { color: 'text-emerald-500', label: 'Healthy', icon: CheckCircle2 };
    if (projected.projectedRunway >= 12) return { color: 'text-amber-500', label: 'Moderate', icon: AlertTriangle };
    return { color: 'text-red-500', label: 'Critical', icon: AlertTriangle };
  };

  const runwayStatus = getRunwayStatus();
  const StatusIcon = runwayStatus.icon;

  return (
    <Card className={cn('sticky top-4', className)} data-testid="scenario-summary-sidebar">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center gap-2">
          <Wallet className="h-4 w-4" />
          Live Summary
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Scenario</span>
            <span className="font-medium truncate max-w-[140px]" title={params.name}>
              {params.name || 'Untitled'}
            </span>
          </div>

          <Separator />

          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Adjustments</p>
            
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground flex items-center gap-1.5">
                <DollarSign className="h-3 w-3" />
                Pricing
              </span>
              <Badge variant={params.pricing_change_pct > 0 ? 'default' : params.pricing_change_pct < 0 ? 'secondary' : 'outline'} className="text-xs">
                {params.pricing_change_pct > 0 ? '+' : ''}{params.pricing_change_pct}%
              </Badge>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-muted-foreground flex items-center gap-1.5">
                <TrendingUp className="h-3 w-3" />
                Growth
              </span>
              <Badge variant={params.growth_uplift_pct > 0 ? 'default' : params.growth_uplift_pct < 0 ? 'secondary' : 'outline'} className="text-xs">
                {params.growth_uplift_pct > 0 ? '+' : ''}{params.growth_uplift_pct}%
              </Badge>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-muted-foreground flex items-center gap-1.5">
                <TrendingDown className="h-3 w-3" />
                Burn Reduction
              </span>
              <Badge variant={params.burn_reduction_pct > 0 ? 'default' : params.burn_reduction_pct < 0 ? 'secondary' : 'outline'} className="text-xs">
                {params.burn_reduction_pct > 0 ? '+' : ''}{params.burn_reduction_pct}%
              </Badge>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-muted-foreground flex items-center gap-1.5">
                <Percent className="h-3 w-3" />
                Gross Margin
              </span>
              <Badge variant={params.gross_margin_delta_pct > 0 ? 'default' : params.gross_margin_delta_pct < 0 ? 'secondary' : 'outline'} className="text-xs">
                {params.gross_margin_delta_pct > 0 ? '+' : ''}{params.gross_margin_delta_pct}%
              </Badge>
            </div>

            {params.churn_change_pct !== 0 && (
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground text-xs">Churn</span>
                <Badge variant={params.churn_change_pct < 0 ? 'default' : 'secondary'} className="text-xs">
                  {params.churn_change_pct > 0 ? '+' : ''}{params.churn_change_pct}%
                </Badge>
              </div>
            )}

            {params.cac_change_pct !== 0 && (
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground text-xs">CAC</span>
                <Badge variant={params.cac_change_pct < 0 ? 'default' : 'secondary'} className="text-xs">
                  {params.cac_change_pct > 0 ? '+' : ''}{params.cac_change_pct}%
                </Badge>
              </div>
            )}
          </div>

          {(params.fundraise_month || params.fundraise_amount > 0) && (
            <>
              <Separator />
              <div className="space-y-2">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Fundraising</p>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground flex items-center gap-1.5">
                    <Calendar className="h-3 w-3" />
                    Month
                  </span>
                  <span className="font-mono">{params.fundraise_month || '—'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground flex items-center gap-1.5">
                    <DollarSign className="h-3 w-3" />
                    Amount
                  </span>
                  <span className="font-mono">{params.fundraise_amount > 0 ? formatCurrency(params.fundraise_amount) : '—'}</span>
                </div>
              </div>
            </>
          )}

          {projected && (
            <>
              <Separator />
              <div className="space-y-2">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Projected Impact</p>
                
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Monthly Revenue</span>
                  <div className="flex items-center gap-1.5">
                    <span className="font-mono">{formatCurrency(projected.projectedRevenue)}</span>
                    {projected.revenueChange !== 0 && (
                      <Badge variant={projected.revenueChange > 0 ? 'default' : 'secondary'} className="text-xs">
                        {projected.revenueChange > 0 ? '+' : ''}{formatCurrency(projected.revenueChange)}
                      </Badge>
                    )}
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Monthly Expenses</span>
                  <div className="flex items-center gap-1.5">
                    <span className="font-mono">{formatCurrency(projected.projectedExpenses)}</span>
                    {projected.expenseChange !== 0 && (
                      <Badge variant={projected.expenseChange < 0 ? 'default' : 'secondary'} className="text-xs">
                        {projected.expenseChange > 0 ? '+' : ''}{formatCurrency(projected.expenseChange)}
                      </Badge>
                    )}
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Net Burn</span>
                  <span className={cn('font-mono', projected.isProfitable && 'text-emerald-500')}>
                    {projected.isProfitable ? 'Net Positive' : formatCurrency(projected.netBurn) + '/mo'}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Cash on Hand</span>
                  <span className="font-mono">{formatCurrency(projected.projectedCash)}</span>
                </div>
              </div>

              <Separator />

              <div className="bg-muted/50 rounded-lg p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <StatusIcon className={cn('h-4 w-4', runwayStatus.color)} />
                    <span className="font-medium">Runway</span>
                  </div>
                  <Badge variant="outline" className={cn('text-xs', runwayStatus.color)}>
                    {runwayStatus.label}
                  </Badge>
                </div>
                <div className="text-center">
                  <span className="text-2xl font-bold font-mono">
                    {projected.isProfitable || projected.projectedRunway >= 900 ? 'Sustainable' : `${projected.projectedRunway.toFixed(1)}`}
                  </span>
                  {!projected.isProfitable && projected.projectedRunway < 900 && (
                    <span className="text-muted-foreground text-sm ml-1">months</span>
                  )}
                </div>
                {projected.runwayChange !== 0 && !projected.isProfitable && projected.projectedRunway < 900 && baseMetrics && (
                  <p className="text-xs text-center text-muted-foreground">
                    {projected.runwayChange > 0 ? '+' : ''}{projected.runwayChange.toFixed(1)} months vs. current ({baseMetrics.currentRunway >= 900 ? 'Sustainable' : `${baseMetrics.currentRunway.toFixed(1)} mo`})
                  </p>
                )}
              </div>
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
