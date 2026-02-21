import { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AdvancedMetric {
  id: string;
  label: string;
  value: string | number;
  category: 'unit_economics' | 'efficiency' | 'growth';
  source: 'manual' | 'calculated' | 'stripe' | 'quickbooks';
  tooltip?: string;
}

interface TruthScanTier3AdvancedMetricsProps {
  metrics: AdvancedMetric[];
  isLoading: boolean;
  defaultExpanded?: boolean;
  onMetricClick?: (metric: AdvancedMetric) => void;
}

export function TruthScanTier3AdvancedMetrics({
  metrics,
  isLoading,
  defaultExpanded = false,
  onMetricClick,
}: TruthScanTier3AdvancedMetricsProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  const getCategoryLabel = (category: string) => {
    switch (category) {
      case 'unit_economics':
        return 'Unit Economics';
      case 'efficiency':
        return 'Efficiency';
      case 'growth':
        return 'Growth';
      default:
        return category;
    }
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'unit_economics':
        return 'bg-blue-500/10 border-blue-500/30';
      case 'efficiency':
        return 'bg-purple-500/10 border-purple-500/30';
      case 'growth':
        return 'bg-emerald-500/10 border-emerald-500/30';
      default:
        return 'bg-secondary/50 border-border';
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

  // Group metrics by category
  const groupedMetrics = metrics.reduce(
    (acc, metric) => {
      const category = metric.category;
      if (!acc[category]) {
        acc[category] = [];
      }
      acc[category].push(metric);
      return acc;
    },
    {} as Record<string, AdvancedMetric[]>
  );

  const totalCount = metrics.length;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Advanced Metrics</h2>
        <Badge variant="secondary">{totalCount} metrics</Badge>
      </div>

      <Card className={cn('border-2', isExpanded ? 'border-primary/50' : 'border-border')}>
        <CardContent className="p-6">
          <Button
            variant="ghost"
            className="w-full justify-between h-auto p-0 hover:bg-transparent"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            <span className="text-base font-medium flex items-center gap-2">
              {isExpanded ? 'Hide All Metrics' : 'Show All Metrics'}
              <span className="text-sm text-muted-foreground">({totalCount} total)</span>
            </span>
            {isExpanded ? (
              <ChevronUp className="h-5 w-5 text-muted-foreground" />
            ) : (
              <ChevronDown className="h-5 w-5 text-muted-foreground" />
            )}
          </Button>

          {isExpanded && (
            <div className="mt-6 space-y-6">
              {isLoading ? (
                Array(3)
                  .fill(0)
                  .map((_, i) => (
                    <div key={i} className="space-y-3">
                      <Skeleton className="h-5 w-32" />
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <Skeleton className="h-20" />
                        <Skeleton className="h-20" />
                      </div>
                    </div>
                  ))
              ) : (
                Object.entries(groupedMetrics).map(([category, categoryMetrics]) => (
                  <div key={category} className="space-y-3">
                    <h3 className="text-sm font-semibold text-muted-foreground">
                      {getCategoryLabel(category)} ({categoryMetrics.length})
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                      {categoryMetrics.map((metric) => {
                        const sourceBadge = getSourceBadge(metric.source);
                        return (
                          <div
                            key={metric.id}
                            className={cn(
                              'border rounded-lg p-4 cursor-pointer hover:shadow-sm transition-shadow',
                              getCategoryColor(category)
                            )}
                            onClick={() => onMetricClick?.(metric)}
                          >
                            <div className="space-y-2">
                              <div className="flex items-start justify-between gap-2">
                                <p className="text-sm font-medium text-muted-foreground flex-1">{metric.label}</p>
                                <Badge variant="secondary" className={`text-xs shrink-0 ${sourceBadge.className}`}>
                                  {sourceBadge.label}
                                </Badge>
                              </div>
                              <p className="text-xl font-bold font-mono">{metric.value}</p>
                              {metric.tooltip && (
                                <p className="text-xs text-muted-foreground line-clamp-2">{metric.tooltip}</p>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
