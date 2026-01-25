import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { TrendingUp, TrendingDown, Minus, Info } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Sparkline } from './Sparkline';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: 'up' | 'down' | 'stable';
  trendValue?: string;
  trendData?: number[];
  benchmark?: {
    position: 'above_p75' | 'above_p50' | 'above_p25' | 'below_p25';
    direction: 'higher_is_better' | 'lower_is_better';
  };
  variant?: 'default' | 'warning' | 'danger' | 'success';
  testId?: string;
  tooltip?: string;
  onClick?: () => void;
}

export function MetricCard({
  title,
  value,
  subtitle,
  trend,
  trendValue,
  trendData,
  benchmark,
  variant = 'default',
  testId = 'metric-card',
  tooltip,
  onClick,
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
    <Card 
      className={cn('overflow-visible', onClick && 'cursor-pointer hover-elevate')} 
      data-testid={testId}
      onClick={onClick}
    >
      <CardContent className="p-4">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div className="flex items-center gap-1.5">
            <span className="text-sm font-medium text-muted-foreground">{title}</span>
            {tooltip && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    className="inline-flex items-center justify-center rounded-full p-0.5"
                    onClick={(e) => e.stopPropagation()}
                    data-testid={`${testId}-tooltip`}
                  >
                    <Info className="h-3.5 w-3.5 text-muted-foreground" />
                  </button>
                </TooltipTrigger>
                <TooltipContent className="max-w-xs" side="top">
                  <p className="text-sm">{tooltip}</p>
                </TooltipContent>
              </Tooltip>
            )}
          </div>
          <div className="flex items-center gap-2">
            {getVariantBadge()}
            {getBenchmarkBadge()}
          </div>
        </div>
        <div className="mt-2 flex items-end justify-between gap-2">
          <div>
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
          {trendData && trendData.length > 1 && (
            <div className="flex-shrink-0" data-testid={`${testId}-sparkline`}>
              <Sparkline data={trendData} width={50} height={24} />
            </div>
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
