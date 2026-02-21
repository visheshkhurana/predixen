import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

interface KeyMetric {
  id: string;
  label: string;
  value: string | number;
  trend?: 'up' | 'down' | 'stable';
  trendValue?: string;
  benchmark?: string; // e.g., "Top Quartile" or "Above Median"
  status: 'healthy' | 'warning' | 'critical';
  source: 'manual' | 'calculated' | 'stripe' | 'quickbooks';
  tooltip?: string;
}

interface TruthScanTier2KeyMetricsProps {
  metrics: KeyMetric[];
  isLoading: boolean;
  onMetricClick?: (metric: KeyMetric) => void;
}

export function TruthScanTier2KeyMetrics({ metrics, isLoading, onMetricClick }: TruthScanTier2KeyMetricsProps) {
  const getTrendIcon = (trend?: string) => {
    switch (trend) {
      case 'up':
        return <TrendingUp className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />;
      case 'down':
        return <TrendingDown className="h-4 w-4 text-red-600 dark:text-red-400" />;
      case 'stable':
        return <Minus className="h-4 w-4 text-muted-foreground" />;
      default:
        return null;
    }
  };

  const getStatusDot = (status: string) => {
    switch (status) {
      case 'healthy':
        return <div className="w-2.5 h-2.5 rounded-full bg-emerald-500" />;
      case 'warning':
        return <div className="w-2.5 h-2.5 rounded-full bg-amber-500" />;
      case 'critical':
        return <div className="w-2.5 h-2.5 rounded-full bg-red-500" />;
      default:
        return null;
    }
  };

  const getSourceBadge = (source: string) => {
    switch (source) {
      case 'manual':
        return { label: 'Manual', className: 'bg-green-500/20 text-green-700 dark:text-green-300' };
      case 'calculated':
        return { label: 'Calculated', className: 'bg-blue-500/20 text-blue-700 dark:text-blue-300' };
      case 'stripe':
        return { label: 'Stripe', className: 'bg-purple-500/20 text-purple-700 dark:text-purple-300' };
      case 'quickbooks':
        return { label: 'QuickBooks', className: 'bg-purple-500/20 text-purple-700 dark:text-purple-300' };
      default:
        return { label: 'Unknown', className: 'bg-secondary text-muted-foreground' };
    }
  };

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Key Metrics</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {isLoading
          ? Array(9)
              .fill(0)
              .map((_, i) => (
                <Card key={i}>
                  <CardContent className="p-4">
                    <Skeleton className="h-4 w-20 mb-2" />
                    <Skeleton className="h-8 w-24 mb-2" />
                    <Skeleton className="h-3 w-16" />
                  </CardContent>
                </Card>
              ))
          : metrics.map((metric) => {
              const sourceBadge = getSourceBadge(metric.source);
              return (
                <Tooltip key={metric.id}>
                  <TooltipTrigger asChild>
                    <Card
                      className={cn('cursor-pointer hover:shadow-md transition-shadow', 'overflow-visible')}
                      onClick={() => onMetricClick?.(metric)}
                    >
                      <CardContent className="p-4">
                        <div className="space-y-3">
                          {/* Header: Label + Status Dot + Source Badge */}
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex items-center gap-2 flex-1 min-w-0">
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-muted-foreground truncate">{metric.label}</p>
                              </div>
                              {getStatusDot(metric.status)}
                            </div>
                            <Badge variant="secondary" className={`text-xs shrink-0 ${sourceBadge.className}`}>
                              {sourceBadge.label}
                            </Badge>
                          </div>

                          {/* Value */}
                          <div className="flex items-baseline gap-2">
                            <span className="text-2xl font-bold font-mono">{metric.value}</span>
                          </div>

                          {/* Trend + Benchmark */}
                          <div className="flex items-center justify-between gap-2 flex-wrap text-xs">
                            <div className="flex items-center gap-1">
                              {getTrendIcon(metric.trend)}
                              {metric.trendValue && (
                                <span className="text-muted-foreground">{metric.trendValue}</span>
                              )}
                            </div>
                            {metric.benchmark && (
                              <span className="text-muted-foreground">{metric.benchmark}</span>
                            )}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </TooltipTrigger>
                  {metric.tooltip && (
                    <TooltipContent className="max-w-xs">
                      <p className="text-sm">{metric.tooltip}</p>
                    </TooltipContent>
                  )}
                </Tooltip>
              );
            })}
      </div>
    </div>
  );
}
