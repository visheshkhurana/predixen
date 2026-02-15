import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { HelpCircle, TrendingUp, TrendingDown, Users, DollarSign, Clock, Repeat, Target, UserMinus } from 'lucide-react';
import { formatCurrencyAbbrev, formatPercent } from '@/lib/utils';
import { useCurrency } from '@/hooks/useCurrency';

interface UnitEconomicsMetrics {
  cac?: number | null;
  ltv?: number | null;
  ltv_cac_ratio?: number | null;
  payback_months?: number | null;
  mrr?: number | null;
  arr?: number | null;
  arpu?: number | null;
  customer_count?: number | null;
  churn_rate_customer?: number | null;
  churn_rate_revenue?: number | null;
  net_revenue_retention?: number | null;
}

interface UnitEconomicsPanelProps {
  metrics: UnitEconomicsMetrics;
  currency?: string;
}

interface DetailedTooltip {
  description: string;
  benchmark: string;
  impact: string;
}

interface MetricItemProps {
  icon: React.ReactNode;
  title: string;
  value: string | number;
  subtitle?: string;
  tooltip: string | DetailedTooltip;
  variant?: 'default' | 'success' | 'warning' | 'danger';
  testId: string;
}

function MetricItem({ icon, title, value, subtitle, tooltip, variant = 'default', testId }: MetricItemProps) {
  const getVariantStyles = () => {
    switch (variant) {
      case 'success':
        return 'border-l-emerald-500 bg-emerald-500/5';
      case 'warning':
        return 'border-l-amber-500 bg-amber-500/5';
      case 'danger':
        return 'border-l-red-500 bg-red-500/5';
      default:
        return 'border-l-primary/50';
    }
  };

  return (
    <div 
      className={`p-4 rounded-lg border-l-4 ${getVariantStyles()}`}
      data-testid={testId}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 text-muted-foreground">
          {icon}
          <span className="text-sm font-medium">{title}</span>
          <Tooltip>
            <TooltipTrigger asChild>
              <button type="button" className="p-0.5">
                <HelpCircle className="h-3 w-3" />
              </button>
            </TooltipTrigger>
            <TooltipContent className="max-w-xs">
              {typeof tooltip === 'string' ? (
                <p className="text-sm">{tooltip}</p>
              ) : (
                <div className="space-y-2">
                  <p className="text-sm">{tooltip.description}</p>
                  <p className="text-xs text-primary">{tooltip.benchmark}</p>
                  <p className="text-xs text-amber-400">{tooltip.impact}</p>
                </div>
              )}
            </TooltipContent>
          </Tooltip>
        </div>
      </div>
      <div className="mt-2">
        <span className="text-2xl font-bold font-mono">{value}</span>
        {subtitle && <span className="text-sm text-muted-foreground ml-2">{subtitle}</span>}
      </div>
    </div>
  );
}

export function UnitEconomicsPanel({ metrics, currency = 'USD' }: UnitEconomicsPanelProps) {
  const isValidNumber = (value: number | null | undefined): value is number => {
    return value != null && typeof value === 'number' && !isNaN(value) && isFinite(value);
  };

  // P0 FIX: Use scale-aware formatting
  const { format: formatCurrency } = useCurrency();

  const formatRatio = (value: number | null | undefined) => {
    if (!isValidNumber(value)) return 'N/A';
    return `${value.toFixed(1)}x`;
  };

  const formatMonths = (value: number | null | undefined) => {
    if (!isValidNumber(value)) return 'N/A';
    return `${value.toFixed(1)} mo`;
  };

  const formatPct = (value: number | null | undefined) => {
    if (!isValidNumber(value)) return 'N/A';
    return `${value.toFixed(1)}%`;
  };

  // Determine variant for LTV:CAC ratio
  const getLtvCacVariant = (): 'success' | 'warning' | 'danger' | 'default' => {
    const ratio = metrics.ltv_cac_ratio;
    if (!isValidNumber(ratio)) return 'default';
    if (ratio >= 5) return 'success';
    if (ratio >= 3) return 'default';
    if (ratio >= 2) return 'warning';
    return 'danger';
  };

  // Determine variant for churn rate
  const getChurnVariant = (): 'success' | 'warning' | 'danger' | 'default' => {
    const churn = metrics.churn_rate_customer;
    if (!isValidNumber(churn)) return 'default';
    if (churn <= 2) return 'success';
    if (churn <= 5) return 'default';
    if (churn <= 8) return 'warning';
    return 'danger';
  };

  // Determine variant for NDR
  const getNdrVariant = (): 'success' | 'warning' | 'danger' | 'default' => {
    const ndr = metrics.net_revenue_retention;
    if (!isValidNumber(ndr)) return 'default';
    if (ndr >= 120) return 'success';
    if (ndr >= 100) return 'default';
    if (ndr >= 90) return 'warning';
    return 'danger';
  };

  // Determine variant for payback
  const getPaybackVariant = (): 'success' | 'warning' | 'danger' | 'default' => {
    const months = metrics.payback_months;
    if (!isValidNumber(months)) return 'default';
    if (months <= 12) return 'success';
    if (months <= 18) return 'default';
    if (months <= 24) return 'warning';
    return 'danger';
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <h2 className="text-xl font-semibold">Unit Economics</h2>
        <Tooltip>
          <TooltipTrigger asChild>
            <button type="button" className="p-0.5" data-testid="tooltip-unit-economics">
              <HelpCircle className="h-4 w-4 text-muted-foreground" />
            </button>
          </TooltipTrigger>
          <TooltipContent className="max-w-xs">
            <p className="text-sm">
              Key metrics measuring customer acquisition efficiency, retention, and revenue sustainability.
            </p>
          </TooltipContent>
        </Tooltip>
      </div>

      {/* MRR/ARR Row */}
      <Card className="overflow-visible">
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <DollarSign className="h-4 w-4 text-primary" />
            Recurring Revenue
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="text-center p-3 rounded-lg bg-muted/30 cursor-help hover:bg-muted/50 transition-colors" data-testid="metric-mrr">
                  <p className="text-sm text-muted-foreground">MRR</p>
                  <p className="text-2xl font-bold font-mono">{formatCurrency(metrics.mrr)}</p>
                </div>
              </TooltipTrigger>
              <TooltipContent className="max-w-xs">
                <div className="space-y-2">
                  <p className="font-medium">Monthly Recurring Revenue</p>
                  <p className="text-xs">Predictable revenue earned each month from subscriptions.</p>
                  <p className="text-xs text-primary">Benchmark: Seed $10K-$100K, Series A $100K-$500K MRR</p>
                  <p className="text-xs text-amber-400">Impact: Foundation of SaaS valuation. Higher MRR = stronger product-market fit.</p>
                </div>
              </TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="text-center p-3 rounded-lg bg-muted/30 cursor-help hover:bg-muted/50 transition-colors" data-testid="metric-arr">
                  <p className="text-sm text-muted-foreground">ARR</p>
                  <p className="text-2xl font-bold font-mono">{formatCurrency(metrics.arr)}</p>
                </div>
              </TooltipTrigger>
              <TooltipContent className="max-w-xs">
                <div className="space-y-2">
                  <p className="font-medium">Annual Recurring Revenue</p>
                  <p className="text-xs">MRR multiplied by 12 - your yearly revenue projection.</p>
                  <p className="text-xs text-primary">Benchmark: Series A $1M-$5M, Series B $5M-$15M ARR</p>
                  <p className="text-xs text-amber-400">Impact: Primary valuation metric. Valuations often 8-15x ARR for growth companies.</p>
                </div>
              </TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="text-center p-3 rounded-lg bg-muted/30 cursor-help hover:bg-muted/50 transition-colors" data-testid="metric-arpu">
                  <p className="text-sm text-muted-foreground">ARPU</p>
                  <p className="text-2xl font-bold font-mono">{formatCurrency(metrics.arpu)}</p>
                </div>
              </TooltipTrigger>
              <TooltipContent className="max-w-xs">
                <div className="space-y-2">
                  <p className="font-medium">Average Revenue Per User</p>
                  <p className="text-xs">MRR divided by total customers - your average deal size.</p>
                  <p className="text-xs text-primary">Benchmark: SMB $50-$500, Mid-market $1K-$10K, Enterprise $10K+</p>
                  <p className="text-xs text-amber-400">Impact: Higher ARPU allows for more customer acquisition spending and faster growth.</p>
                </div>
              </TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="text-center p-3 rounded-lg bg-muted/30 cursor-help hover:bg-muted/50 transition-colors" data-testid="metric-customers">
                  <p className="text-sm text-muted-foreground">Customers</p>
                  <p className="text-2xl font-bold font-mono">{metrics.customer_count ?? 'N/A'}</p>
                </div>
              </TooltipTrigger>
              <TooltipContent className="max-w-xs">
                <div className="space-y-2">
                  <p className="font-medium">Active Customer Count</p>
                  <p className="text-xs">Total number of paying customers on your platform.</p>
                  <p className="text-xs text-primary">Growth: Aim for 5-10% monthly customer growth</p>
                  <p className="text-xs text-amber-400">Impact: Customer concentration risk - avoid having any single customer above 10% of revenue.</p>
                </div>
              </TooltipContent>
            </Tooltip>
          </div>
        </CardContent>
      </Card>

      {/* Customer Acquisition & Retention */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricItem
          icon={<Target className="h-4 w-4" />}
          title="CAC"
          value={isValidNumber(metrics.cac) && metrics.cac! > 0 ? formatCurrency(metrics.cac) : 'N/A'}
          tooltip={{
            description: "Customer Acquisition Cost - Total marketing and sales spend divided by new customers acquired.",
            benchmark: "Target: $1 CAC for every $3+ of LTV. SMB CAC typically $100-$500, Enterprise $5K-$50K.",
            impact: "High CAC limits growth speed. Focus on reducing CAC through better targeting and conversion optimization."
          }}
          testId="metric-cac"
        />
        <MetricItem
          icon={<TrendingUp className="h-4 w-4" />}
          title="LTV"
          value={isValidNumber(metrics.ltv) && metrics.ltv! > 0 ? formatCurrency(metrics.ltv) : 'N/A'}
          tooltip={{
            description: "Lifetime Value - Predicted total revenue from a customer over their entire relationship with you.",
            benchmark: "Healthy LTV should be 3x+ CAC. Top SaaS companies achieve 5-7x LTV:CAC.",
            impact: "Higher LTV justifies more acquisition spending and indicates strong retention and expansion."
          }}
          testId="metric-ltv"
        />
        <MetricItem
          icon={<Repeat className="h-4 w-4" />}
          title="LTV:CAC"
          value={isValidNumber(metrics.ltv_cac_ratio) && metrics.ltv_cac_ratio! > 0 && isValidNumber(metrics.ltv) && metrics.ltv! > 0 && isValidNumber(metrics.cac) && metrics.cac! > 0 ? formatRatio(metrics.ltv_cac_ratio) : 'N/A'}
          subtitle={isValidNumber(metrics.ltv_cac_ratio) && metrics.ltv_cac_ratio! > 0 && isValidNumber(metrics.ltv) && metrics.ltv! > 0 && isValidNumber(metrics.cac) && metrics.cac! > 0 ? (metrics.ltv_cac_ratio! >= 3 ? 'Healthy' : 'Below target') : undefined}
          tooltip={{
            description: "LTV to CAC ratio - Measures return on customer acquisition investment.",
            benchmark: "3x = Good, 5x+ = Excellent. Below 3x means acquisition is too expensive or retention is poor.",
            impact: "Below 3x: Risk of running out of cash before seeing ROI. Above 5x: Opportunity to invest more in growth."
          }}
          variant={getLtvCacVariant()}
          testId="metric-ltv-cac"
        />
        <MetricItem
          icon={<Clock className="h-4 w-4" />}
          title="Payback"
          value={formatMonths(metrics.payback_months)}
          subtitle={metrics.payback_months && metrics.payback_months <= 12 ? 'Good' : undefined}
          tooltip={{
            description: "CAC Payback Period - Months needed to recover customer acquisition cost from that customer's revenue.",
            benchmark: "Under 12 months = Excellent. 12-18 months = Good. Over 24 months = Concerning.",
            impact: "Long payback ties up capital and increases risk. Shorter payback enables faster reinvestment in growth."
          }}
          variant={getPaybackVariant()}
          testId="metric-payback"
        />
      </div>

      {/* Retention Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricItem
          icon={<UserMinus className="h-4 w-4" />}
          title="Customer Churn"
          value={formatPct(metrics.churn_rate_customer)}
          subtitle="monthly"
          tooltip={{
            description: "Monthly Customer Churn - Percentage of customers lost per month.",
            benchmark: "SMB: Under 5% monthly is healthy. Enterprise: Under 2% monthly.",
            impact: "High churn destroys growth. 5% monthly churn = 46% annual churn, meaning you must replace half your customers yearly."
          }}
          variant={getChurnVariant()}
          testId="metric-churn-customer"
        />
        <MetricItem
          icon={<TrendingDown className="h-4 w-4" />}
          title="Revenue Churn"
          value={formatPct(metrics.churn_rate_revenue)}
          subtitle="monthly"
          tooltip={{
            description: "Monthly Revenue Churn - Percentage of MRR lost from churned customers and downgrades.",
            benchmark: "Under 2% monthly is good. Negative revenue churn (more expansions than churn) is ideal.",
            impact: "Revenue churn is often more impactful than customer churn - losing big customers hurts more."
          }}
          variant={getChurnVariant()}
          testId="metric-churn-revenue"
        />
        <MetricItem
          icon={<Users className="h-4 w-4" />}
          title="NDR"
          value={formatPct(metrics.net_revenue_retention)}
          subtitle={metrics.net_revenue_retention && metrics.net_revenue_retention >= 100 ? 'Net positive' : 'Net negative'}
          tooltip={{
            description: "Net Dollar Retention - Revenue retained from existing customers including expansions minus churn.",
            benchmark: "100% = Stable. 110%+ = Good. 120%+ = Excellent (best-in-class SaaS).",
            impact: "NDR above 100% means you grow even without new customers. This is the most powerful growth lever."
          }}
          variant={getNdrVariant()}
          testId="metric-ndr"
        />
      </div>
    </div>
  );
}
