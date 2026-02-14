import { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { BarChart3, TrendingUp, TrendingDown, HelpCircle, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ReferenceLine } from 'recharts';
import { cn, formatCurrencyAbbrev } from '@/lib/utils';

interface DistributionData {
  value: number;
  count: number;
  percentile: number;
}

interface DistributionViewProps {
  title: string;
  description?: string;
  data: number[];
  unit?: string;
  benchmark?: { p25: number; p50: number; p75: number };
  thresholds?: { warning: number; critical: number };
  higherIsBetter?: boolean;
}

function computeHistogram(data: number[], bins: number = 30): DistributionData[] {
  if (data.length === 0) return [];
  
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const binWidth = range / bins;
  
  const histogram: Map<number, number> = new Map();
  
  data.forEach(value => {
    const binIndex = Math.min(Math.floor((value - min) / binWidth), bins - 1);
    const binValue = min + (binIndex + 0.5) * binWidth;
    histogram.set(binValue, (histogram.get(binValue) || 0) + 1);
  });
  
  const sortedData = [...data].sort((a, b) => a - b);
  
  return Array.from(histogram.entries())
    .map(([value, count]) => ({
      value: Math.round(value * 100) / 100,
      count,
      percentile: (sortedData.filter(v => v <= value).length / sortedData.length) * 100,
    }))
    .sort((a, b) => a.value - b.value);
}

function computePercentiles(data: number[]): { p10: number; p25: number; p50: number; p75: number; p90: number } {
  if (data.length === 0) return { p10: 0, p25: 0, p50: 0, p75: 0, p90: 0 };
  
  const sorted = [...data].sort((a, b) => a - b);
  const getPercentile = (p: number) => {
    const index = Math.floor((p / 100) * (sorted.length - 1));
    return sorted[index];
  };
  
  return {
    p10: getPercentile(10),
    p25: getPercentile(25),
    p50: getPercentile(50),
    p75: getPercentile(75),
    p90: getPercentile(90),
  };
}

export function DistributionView({
  title,
  description,
  data,
  unit = '',
  benchmark,
  thresholds,
  higherIsBetter = true,
}: DistributionViewProps) {
  const histogram = useMemo(() => computeHistogram(data), [data]);
  const percentiles = useMemo(() => computePercentiles(data), [data]);
  
  const mean = useMemo(() => {
    if (data.length === 0) return 0;
    return data.reduce((a, b) => a + b, 0) / data.length;
  }, [data]);
  
  const stdDev = useMemo(() => {
    if (data.length === 0) return 0;
    const variance = data.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / data.length;
    return Math.sqrt(variance);
  }, [data, mean]);

  const getStatusColor = (value: number) => {
    if (!thresholds) return 'text-foreground';
    if (higherIsBetter) {
      if (value >= thresholds.warning) return 'text-green-600';
      if (value >= thresholds.critical) return 'text-amber-600';
      return 'text-red-600';
    } else {
      if (value <= thresholds.warning) return 'text-green-600';
      if (value <= thresholds.critical) return 'text-amber-600';
      return 'text-red-600';
    }
  };

  const getStatusIcon = (value: number) => {
    if (!thresholds) return null;
    const isGood = higherIsBetter 
      ? value >= thresholds.warning 
      : value <= thresholds.warning;
    const isCritical = higherIsBetter 
      ? value < thresholds.critical 
      : value > thresholds.critical;
    
    if (isGood) return <CheckCircle2 className="h-4 w-4 text-green-600" />;
    if (isCritical) return <AlertTriangle className="h-4 w-4 text-red-600" />;
    return <AlertTriangle className="h-4 w-4 text-amber-600" />;
  };

  const formatValue = (value: number) => {
    if (unit === 'months') return `${value.toFixed(1)} mo`;
    if (unit === '%') return `${value.toFixed(1)}%`;
    if (unit === '$' || unit === 'currency') return formatCurrencyAbbrev(value);
    return value.toFixed(1);
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-primary" />
            <CardTitle className="text-lg">{title}</CardTitle>
            <Tooltip>
              <TooltipTrigger asChild>
                <button type="button" className="p-0.5">
                  <HelpCircle className="h-4 w-4 text-muted-foreground" />
                </button>
              </TooltipTrigger>
              <TooltipContent className="max-w-xs">
                <p className="text-sm">
                  Distribution of {data.length.toLocaleString()} simulation runs. 
                  The chart shows how outcomes are distributed across different values.
                </p>
              </TooltipContent>
            </Tooltip>
          </div>
          <Badge variant="outline">{data.length.toLocaleString()} runs</Badge>
        </div>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="h-[200px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={histogram} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="distributionGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis 
                dataKey="value" 
                tick={{ fontSize: 11 }}
                tickFormatter={(v) => formatValue(v)}
              />
              <YAxis 
                tick={{ fontSize: 11 }}
                tickFormatter={(v) => v.toLocaleString()}
              />
              <RechartsTooltip
                content={({ active, payload }) => {
                  if (!active || !payload?.length) return null;
                  const data = payload[0].payload as DistributionData;
                  return (
                    <div className="bg-popover border rounded-lg shadow-lg p-2 text-sm">
                      <p className="font-medium">{formatValue(data.value)}</p>
                      <p className="text-muted-foreground">{data.count} runs</p>
                      <p className="text-muted-foreground">Percentile: {data.percentile.toFixed(0)}%</p>
                    </div>
                  );
                }}
              />
              {thresholds && (
                <>
                  <ReferenceLine 
                    x={thresholds.warning} 
                    stroke="hsl(var(--chart-4))" 
                    strokeDasharray="3 3"
                    label={{ value: 'Target', position: 'top', fontSize: 10 }}
                  />
                  <ReferenceLine 
                    x={thresholds.critical} 
                    stroke="hsl(var(--destructive))" 
                    strokeDasharray="3 3"
                    label={{ value: 'Critical', position: 'top', fontSize: 10 }}
                  />
                </>
              )}
              <Area
                type="monotone"
                dataKey="count"
                stroke="hsl(var(--primary))"
                fill="url(#distributionGradient)"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="grid grid-cols-5 gap-2">
          {[
            { label: 'P10', value: percentiles.p10 },
            { label: 'P25', value: percentiles.p25 },
            { label: 'P50 (Median)', value: percentiles.p50, highlight: true },
            { label: 'P75', value: percentiles.p75 },
            { label: 'P90', value: percentiles.p90 },
          ].map(({ label, value, highlight }) => (
            <div
              key={label}
              className={cn(
                'text-center p-2 rounded-lg',
                highlight ? 'bg-primary/10' : 'bg-muted/50'
              )}
            >
              <p className="text-xs text-muted-foreground">{label}</p>
              <p className={cn(
                'font-mono font-medium text-sm',
                getStatusColor(value)
              )}>
                {formatValue(value)}
              </p>
            </div>
          ))}
        </div>

        <div className="flex items-center justify-between text-sm border-t pt-3">
          <div className="flex items-center gap-4">
            <div>
              <span className="text-muted-foreground">Mean: </span>
              <span className="font-mono">{formatValue(mean)}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Std Dev: </span>
              <span className="font-mono">{formatValue(stdDev)}</span>
            </div>
          </div>
          {thresholds && (
            <div className="flex items-center gap-2">
              {getStatusIcon(percentiles.p50)}
              <span className={getStatusColor(percentiles.p50)}>
                {higherIsBetter 
                  ? percentiles.p50 >= thresholds.warning ? 'On Track' : 'Below Target'
                  : percentiles.p50 <= thresholds.warning ? 'On Track' : 'Above Target'
                }
              </span>
            </div>
          )}
        </div>

        {benchmark && (
          <div className="text-xs text-muted-foreground border-t pt-3">
            <span className="font-medium">Industry Benchmarks: </span>
            P25: {formatValue(benchmark.p25)} | P50: {formatValue(benchmark.p50)} | P75: {formatValue(benchmark.p75)}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
