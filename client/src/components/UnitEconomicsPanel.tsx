import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { HelpCircle, TrendingUp, TrendingDown, Users, DollarSign, Clock, Repeat, Target, UserMinus } from 'lucide-react';
import { formatCurrencyAbbrev, formatPercent } from '@/lib/utils';

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

interface MetricItemProps {
  icon: React.ReactNode;
  title: string;
  value: string | number;
  subtitle?: string;
  tooltip: string;
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
              <p className="text-sm">{tooltip}</p>
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

  const formatCurrency = (value: number | null | undefined) => {
    if (!isValidNumber(value)) return 'N/A';
    return formatCurrencyAbbrev(value, currency);
  };

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
            <div className="text-center p-3 rounded-lg bg-muted/30" data-testid="metric-mrr">
              <p className="text-sm text-muted-foreground">MRR</p>
              <p className="text-2xl font-bold font-mono">{formatCurrency(metrics.mrr)}</p>
            </div>
            <div className="text-center p-3 rounded-lg bg-muted/30" data-testid="metric-arr">
              <p className="text-sm text-muted-foreground">ARR</p>
              <p className="text-2xl font-bold font-mono">{formatCurrency(metrics.arr)}</p>
            </div>
            <div className="text-center p-3 rounded-lg bg-muted/30" data-testid="metric-arpu">
              <p className="text-sm text-muted-foreground">ARPU</p>
              <p className="text-2xl font-bold font-mono">{formatCurrency(metrics.arpu)}</p>
            </div>
            <div className="text-center p-3 rounded-lg bg-muted/30" data-testid="metric-customers">
              <p className="text-sm text-muted-foreground">Customers</p>
              <p className="text-2xl font-bold font-mono">{metrics.customer_count ?? 'N/A'}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Customer Acquisition & Retention */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricItem
          icon={<Target className="h-4 w-4" />}
          title="CAC"
          value={formatCurrency(metrics.cac)}
          tooltip="Customer Acquisition Cost: Total marketing and sales spend divided by new customers acquired"
          testId="metric-cac"
        />
        <MetricItem
          icon={<TrendingUp className="h-4 w-4" />}
          title="LTV"
          value={formatCurrency(metrics.ltv)}
          tooltip="Lifetime Value: Predicted total revenue from a customer over their entire relationship"
          testId="metric-ltv"
        />
        <MetricItem
          icon={<Repeat className="h-4 w-4" />}
          title="LTV:CAC"
          value={formatRatio(metrics.ltv_cac_ratio)}
          subtitle={metrics.ltv_cac_ratio && metrics.ltv_cac_ratio >= 3 ? 'Healthy' : 'Below target'}
          tooltip="LTV to CAC ratio: Measures return on customer acquisition investment. 3x+ is healthy, 5x+ is excellent"
          variant={getLtvCacVariant()}
          testId="metric-ltv-cac"
        />
        <MetricItem
          icon={<Clock className="h-4 w-4" />}
          title="Payback"
          value={formatMonths(metrics.payback_months)}
          subtitle={metrics.payback_months && metrics.payback_months <= 12 ? 'Good' : undefined}
          tooltip="CAC Payback Period: Months to recover customer acquisition cost. Under 12 months is excellent"
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
          tooltip="Monthly customer churn rate: Percentage of customers lost per month. Under 5% is healthy"
          variant={getChurnVariant()}
          testId="metric-churn-customer"
        />
        <MetricItem
          icon={<TrendingDown className="h-4 w-4" />}
          title="Revenue Churn"
          value={formatPct(metrics.churn_rate_revenue)}
          subtitle="monthly"
          tooltip="Monthly revenue churn: Percentage of MRR lost from churned customers and downgrades"
          variant={getChurnVariant()}
          testId="metric-churn-revenue"
        />
        <MetricItem
          icon={<Users className="h-4 w-4" />}
          title="NDR"
          value={formatPct(metrics.net_revenue_retention)}
          subtitle={metrics.net_revenue_retention && metrics.net_revenue_retention >= 100 ? 'Net positive' : 'Net negative'}
          tooltip="Net Dollar Retention: Revenue retained from existing customers including expansions. 100%+ means growth without new customers"
          variant={getNdrVariant()}
          testId="metric-ndr"
        />
      </div>
    </div>
  );
}
