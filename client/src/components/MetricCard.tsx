import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: 'up' | 'down' | 'stable';
  trendValue?: string;
  benchmark?: {
    position: 'above_p75' | 'above_p50' | 'above_p25' | 'below_p25';
    direction: 'higher_is_better' | 'lower_is_better';
  };
  variant?: 'default' | 'warning' | 'danger' | 'success';
  testId?: string;
}

export function MetricCard({
  title,
  value,
  subtitle,
  trend,
  trendValue,
  benchmark,
  variant = 'default',
  testId = 'metric-card',
}: MetricCardProps) {
  const getTrendIcon = () => {
    if (!trend) return null;
    switch (trend) {
      case 'up':
        return <TrendingUp className="h-3 w-3" />;
      case 'down':
        return <TrendingDown className="h-3 w-3" />;
      case 'stable':
        return <Minus className="h-3 w-3" />;
    }
  };

  const getTrendColor = () => {
    if (!trend) return '';
    switch (trend) {
      case 'up':
        return 'text-emerald-500';
      case 'down':
        return 'text-red-500';
      case 'stable':
        return 'text-muted-foreground';
    }
  };

  const getBenchmarkBadge = () => {
    if (!benchmark) return null;
    
    const isGood =
      (benchmark.direction === 'higher_is_better' && benchmark.position.startsWith('above')) ||
      (benchmark.direction === 'lower_is_better' && benchmark.position === 'below_p25');
    
    const labels: Record<string, string> = {
      above_p75: 'Top Quartile',
      above_p50: 'Above Median',
      above_p25: 'Above P25',
      below_p25: 'Below P25',
    };
    
    return (
      <Badge
        variant="secondary"
        className={cn(
          'text-xs',
          isGood
            ? 'bg-emerald-500/20 text-emerald-400'
            : 'bg-amber-500/20 text-amber-400'
        )}
      >
        {labels[benchmark.position]}
      </Badge>
    );
  };

  const getVariantBadge = () => {
    switch (variant) {
      case 'warning':
        return (
          <Badge variant="secondary" className="bg-amber-500/20 text-amber-400 text-xs">
            Caution
          </Badge>
        );
      case 'danger':
        return (
          <Badge variant="destructive" className="text-xs">
            Critical
          </Badge>
        );
      case 'success':
        return (
          <Badge variant="secondary" className="bg-emerald-500/20 text-emerald-400 text-xs">
            Healthy
          </Badge>
        );
      default:
        return null;
    }
  };

  return (
    <Card className="overflow-visible" data-testid={testId}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <span className="text-sm font-medium text-muted-foreground">{title}</span>
          <div className="flex items-center gap-2">
            {getVariantBadge()}
            {getBenchmarkBadge()}
          </div>
        </div>
        <div className="mt-2">
          <span
            className="text-2xl font-semibold font-mono tracking-tight"
            data-testid={`${testId}-value`}
          >
            {value}
          </span>
          {subtitle && (
            <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
          )}
        </div>
        {trend && trendValue && (
          <div className={cn('flex items-center gap-1 mt-2 text-xs', getTrendColor())}>
            {getTrendIcon()}
            <span>{trendValue}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
