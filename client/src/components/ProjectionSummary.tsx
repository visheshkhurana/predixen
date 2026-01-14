import { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { TrendingUp, TrendingDown, DollarSign, Clock, Users, Target, AlertTriangle } from 'lucide-react';

export interface MonthlyDataPoint {
  month: number;
  cashBalance: number;
  monthlyBurn: number;
  monthlyRevenue: number;
  runwayRemaining: number;
  headcount?: number;
}

interface ProjectionSummaryProps {
  timeseries: MonthlyDataPoint[];
  targetRunway?: number;
  testId?: string;
}

const formatCurrency = (value: number): string => {
  if (value >= 1000000) {
    return `$${(value / 1000000).toFixed(2)}M`;
  }
  if (value >= 1000) {
    return `$${(value / 1000).toFixed(0)}K`;
  }
  return `$${value.toFixed(0)}`;
};

interface StatCardProps {
  label: string;
  value: string;
  subLabel?: string;
  icon: React.ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'danger';
}

interface StatCardPropsWithTestId extends StatCardProps {
  testId?: string;
}

function StatCard({ label, value, subLabel, icon, variant = 'default', testId }: StatCardPropsWithTestId) {
  const variantClasses = {
    default: 'bg-muted/50',
    success: 'bg-emerald-500/10 border-emerald-500/20',
    warning: 'bg-amber-500/10 border-amber-500/20',
    danger: 'bg-red-500/10 border-red-500/20',
  };

  const iconClasses = {
    default: 'text-muted-foreground',
    success: 'text-emerald-600',
    warning: 'text-amber-600',
    danger: 'text-red-600',
  };

  const slugLabel = label.toLowerCase().replace(/\s+/g, '-');

  return (
    <div 
      className={`p-4 rounded-lg border ${variantClasses[variant]}`}
      data-testid={testId || `stat-card-${slugLabel}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs text-muted-foreground uppercase tracking-wide">{label}</p>
          <p className="text-xl font-mono font-bold mt-1" data-testid={`text-value-${slugLabel}`}>{value}</p>
          {subLabel && (
            <p className="text-xs text-muted-foreground mt-1">{subLabel}</p>
          )}
        </div>
        <div className={iconClasses[variant]}>
          {icon}
        </div>
      </div>
    </div>
  );
}

export function ProjectionSummary({
  timeseries,
  targetRunway = 18,
  testId = 'projection-summary',
}: ProjectionSummaryProps) {
  const stats = useMemo(() => {
    if (!timeseries || timeseries.length === 0) {
      return null;
    }

    let peakCash = { month: 0, value: 0 };
    let lowestCash = { month: 0, value: Infinity };
    let totalRevenue = 0;
    let totalBurn = 0;
    let breakEvenMonth: number | null = null;

    for (const point of timeseries) {
      totalRevenue += point.monthlyRevenue;
      totalBurn += point.monthlyBurn;

      if (point.cashBalance > peakCash.value) {
        peakCash = { month: point.month, value: point.cashBalance };
      }

      if (point.cashBalance < lowestCash.value && point.cashBalance > 0) {
        lowestCash = { month: point.month, value: point.cashBalance };
      }

      if (breakEvenMonth === null && point.monthlyRevenue >= point.monthlyBurn) {
        breakEvenMonth = point.month;
      }
    }

    if (lowestCash.value === Infinity) {
      lowestCash = { month: 0, value: 0 };
    }

    const avgBurn = totalBurn / timeseries.length;
    const avgRevenue = totalRevenue / timeseries.length;

    const runway3m = timeseries.length > 3 ? timeseries[2].runwayRemaining : null;
    const runway6m = timeseries.length > 6 ? timeseries[5].runwayRemaining : null;
    const runway12m = timeseries.length > 12 ? timeseries[11].runwayRemaining : null;
    const runwayEnd = timeseries[timeseries.length - 1].runwayRemaining;

    const meetsTarget = runwayEnd >= targetRunway;

    return {
      peakCash,
      lowestCash,
      totalRevenue,
      avgBurn,
      avgRevenue,
      runway3m,
      runway6m,
      runway12m,
      runwayEnd,
      breakEvenMonth,
      meetsTarget,
    };
  }, [timeseries, targetRunway]);

  if (!stats) {
    return (
      <Card data-testid={testId}>
        <CardContent className="py-12 text-center">
          <p className="text-muted-foreground">No projection data available</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card data-testid={testId}>
      <CardHeader>
        <CardTitle className="text-lg">Projection Summary</CardTitle>
        <CardDescription>
          Key financial statistics from the simulation
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          <StatCard
            label="Peak Cash Balance"
            value={formatCurrency(stats.peakCash.value)}
            subLabel={`Month ${stats.peakCash.month}`}
            icon={<TrendingUp className="h-5 w-5" />}
            variant="success"
          />
          
          <StatCard
            label="Lowest Cash"
            value={formatCurrency(stats.lowestCash.value)}
            subLabel={`Month ${stats.lowestCash.month}`}
            icon={<TrendingDown className="h-5 w-5" />}
            variant={stats.lowestCash.value < stats.avgBurn * 3 ? 'danger' : 'warning'}
          />
          
          <StatCard
            label="Total Revenue"
            value={formatCurrency(stats.totalRevenue)}
            subLabel="Over projection period"
            icon={<DollarSign className="h-5 w-5" />}
            variant="success"
          />
          
          <StatCard
            label="Avg Monthly Burn"
            value={formatCurrency(stats.avgBurn)}
            subLabel={`Net: ${formatCurrency(stats.avgBurn - stats.avgRevenue)}/mo`}
            icon={<TrendingDown className="h-5 w-5" />}
            variant="default"
          />
          
          <StatCard
            label="Avg Monthly Revenue"
            value={formatCurrency(stats.avgRevenue)}
            subLabel={`${((stats.avgRevenue / stats.avgBurn) * 100).toFixed(0)}% of burn`}
            icon={<TrendingUp className="h-5 w-5" />}
            variant={stats.avgRevenue >= stats.avgBurn ? 'success' : 'default'}
          />
          
          <StatCard
            label="Break-Even"
            value={stats.breakEvenMonth !== null ? `Month ${stats.breakEvenMonth}` : 'Not reached'}
            subLabel={stats.breakEvenMonth !== null ? 'Revenue ≥ Burn' : 'Within horizon'}
            icon={<Target className="h-5 w-5" />}
            variant={stats.breakEvenMonth !== null ? 'success' : 'warning'}
          />
          
          <StatCard
            label="Target Runway"
            value={stats.meetsTarget ? 'Achieved' : 'Not Met'}
            subLabel={`Target: ${targetRunway} mo, Actual: ${stats.runwayEnd.toFixed(1)} mo`}
            icon={stats.meetsTarget ? <Target className="h-5 w-5" /> : <AlertTriangle className="h-5 w-5" />}
            variant={stats.meetsTarget ? 'success' : 'danger'}
          />
          
          <StatCard
            label="End Runway"
            value={`${stats.runwayEnd.toFixed(1)} mo`}
            subLabel="At projection end"
            icon={<Clock className="h-5 w-5" />}
            variant={stats.runwayEnd >= targetRunway ? 'success' : stats.runwayEnd >= 6 ? 'warning' : 'danger'}
          />
        </div>

        <div className="mt-6 p-4 bg-muted/30 rounded-lg" data-testid="section-runway-intervals">
          <h4 className="text-sm font-medium mb-3">Runway at Key Intervals</h4>
          <div className="grid grid-cols-4 gap-4 text-center">
            <div data-testid="runway-interval-3m">
              <p className="text-xs text-muted-foreground">Month 3</p>
              <p className="font-mono font-medium" data-testid="text-runway-3m">
                {stats.runway3m !== null ? `${stats.runway3m.toFixed(1)} mo` : '-'}
              </p>
            </div>
            <div data-testid="runway-interval-6m">
              <p className="text-xs text-muted-foreground">Month 6</p>
              <p className="font-mono font-medium" data-testid="text-runway-6m">
                {stats.runway6m !== null ? `${stats.runway6m.toFixed(1)} mo` : '-'}
              </p>
            </div>
            <div data-testid="runway-interval-12m">
              <p className="text-xs text-muted-foreground">Month 12</p>
              <p className="font-mono font-medium" data-testid="text-runway-12m">
                {stats.runway12m !== null ? `${stats.runway12m.toFixed(1)} mo` : '-'}
              </p>
            </div>
            <div data-testid="runway-interval-end">
              <p className="text-xs text-muted-foreground">End</p>
              <p className="font-mono font-bold text-primary" data-testid="text-runway-end">
                {stats.runwayEnd.toFixed(1)} mo
              </p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
