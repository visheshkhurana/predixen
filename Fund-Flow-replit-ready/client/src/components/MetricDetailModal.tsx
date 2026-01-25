import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { TrendingUp, TrendingDown, Target, Info } from 'lucide-react';
import { MetricDefinition } from '@/lib/metricDefinitions';
import { cn } from '@/lib/utils';

interface MetricDetailModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  metric: MetricDefinition | null;
  currentValue?: number | string;
  benchmarkData?: {
    value: number;
    p25: number;
    p50: number;
    p75: number;
  };
}

export function MetricDetailModal({
  open,
  onOpenChange,
  metric,
  currentValue,
  benchmarkData,
}: MetricDetailModalProps) {
  if (!metric) return null;

  const IconComponent = metric.icon;
  const isHigherBetter = metric.direction === 'higher_is_better';

  const getQuartilePosition = () => {
    if (!benchmarkData) return null;
    const { value, p25, p50, p75 } = benchmarkData;
    if (value >= p75) return { label: 'Top Quartile (>P75)', color: 'text-emerald-500', position: 'above_p75' };
    if (value >= p50) return { label: 'Above Median (P50-P75)', color: 'text-blue-500', position: 'above_p50' };
    if (value >= p25) return { label: 'Below Median (P25-P50)', color: 'text-amber-500', position: 'above_p25' };
    return { label: 'Bottom Quartile (<P25)', color: 'text-red-500', position: 'below_p25' };
  };

  const quartile = getQuartilePosition();
  const isGoodPosition = quartile && (
    (isHigherBetter && (quartile.position === 'above_p75' || quartile.position === 'above_p50')) ||
    (!isHigherBetter && (quartile.position === 'below_p25' || quartile.position === 'above_p25'))
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <IconComponent className="h-5 w-5 text-primary" />
            {metric.displayName}
          </DialogTitle>
          <DialogDescription>{metric.shortDescription}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {currentValue !== undefined && (
            <Card className="overflow-visible">
              <CardContent className="p-4">
                <p className="text-sm text-muted-foreground mb-1">Current Value</p>
                <p className="text-3xl font-bold font-mono">{currentValue}</p>
              </CardContent>
            </Card>
          )}

          <div className="space-y-3">
            <div>
              <h4 className="text-sm font-medium flex items-center gap-1.5 mb-1">
                <Info className="h-4 w-4 text-muted-foreground" />
                What is this?
              </h4>
              <p className="text-sm text-muted-foreground">{metric.longDescription}</p>
            </div>

            {metric.formula && (
              <div>
                <h4 className="text-sm font-medium mb-1">Formula</h4>
                <div className="bg-secondary rounded-md p-3">
                  <code className="text-sm font-mono">{metric.formula}</code>
                </div>
              </div>
            )}

            <div>
              <h4 className="text-sm font-medium flex items-center gap-1.5 mb-1">
                <Target className="h-4 w-4 text-muted-foreground" />
                Why it matters
              </h4>
              <p className="text-sm text-muted-foreground">{metric.whyItMatters}</p>
            </div>

            <Separator />

            <div>
              <h4 className="text-sm font-medium mb-2">Direction & Benchmarks</h4>
              <div className="flex items-center gap-2 mb-2">
                {isHigherBetter ? (
                  <Badge variant="secondary" className="bg-emerald-500/20 text-emerald-400">
                    <TrendingUp className="h-3 w-3 mr-1" />
                    Higher is better
                  </Badge>
                ) : (
                  <Badge variant="secondary" className="bg-blue-500/20 text-blue-400">
                    <TrendingDown className="h-3 w-3 mr-1" />
                    Lower is better
                  </Badge>
                )}
              </div>
              {metric.benchmarkContext && (
                <p className="text-sm text-muted-foreground">{metric.benchmarkContext}</p>
              )}
            </div>

            {benchmarkData && quartile && (
              <>
                <Separator />
                <div>
                  <h4 className="text-sm font-medium mb-2">Industry Comparison</h4>
                  <div className="relative h-8 bg-secondary rounded-full overflow-hidden">
                    <div className="absolute inset-0 flex">
                      <div className="flex-1 border-r border-background/50" title="P0-P25" />
                      <div className="flex-1 border-r border-background/50" title="P25-P50" />
                      <div className="flex-1 border-r border-background/50" title="P50-P75" />
                      <div className="flex-1" title="P75-P100" />
                    </div>
                    <div
                      className={cn(
                        'absolute top-1 bottom-1 w-2 rounded-full',
                        isGoodPosition ? 'bg-emerald-500' : 'bg-amber-500'
                      )}
                      style={{
                        left: `calc(${Math.min(Math.max(
                          ((benchmarkData.value - benchmarkData.p25) / (benchmarkData.p75 - benchmarkData.p25 || 1)) * 50 + 25,
                          5
                        ), 95)}% - 4px)`,
                      }}
                    />
                  </div>
                  <div className="flex justify-between text-xs text-muted-foreground mt-1">
                    <span>P25: {benchmarkData.p25.toLocaleString()}</span>
                    <span>P50: {benchmarkData.p50.toLocaleString()}</span>
                    <span>P75: {benchmarkData.p75.toLocaleString()}</span>
                  </div>
                  <p className={cn('text-sm mt-2 font-medium', quartile.color)}>
                    Your position: {quartile.label}
                  </p>
                </div>
              </>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
