import {
  AreaChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Info } from 'lucide-react';
import { Tooltip as UITooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';

interface BandsChartProps {
  data: {
    p10: number[];
    p50: number[];
    p90: number[];
  };
  title: string;
  yAxisLabel?: string;
  formatValue?: (value: number) => string;
  testId?: string;
  description?: string;
}

export function BandsChart({
  data,
  title,
  yAxisLabel = 'Value',
  formatValue = (v) => {
    if (v == null || isNaN(v) || !isFinite(v)) return 'N/A';
    return `$${(v / 1000).toFixed(0)}k`;
  },
  testId = 'bands-chart',
  description = 'Shows P10, P50 (median), and P90 projections from Monte Carlo simulation. P10 is the pessimistic case, P90 is optimistic.',
}: BandsChartProps) {
  if (!data || !data.p50 || !Array.isArray(data.p50) || data.p50.length === 0) {
    return (
      <Card className="overflow-visible" data-testid={testId}>
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 flex items-center justify-center text-muted-foreground">
            No data available
          </div>
        </CardContent>
      </Card>
    );
  }

  const chartData = data.p50.map((_, index) => {
    const p10 = data.p10?.[index];
    const p50 = data.p50[index];
    const p90 = data.p90?.[index];
    return {
      month: index + 1,
      p10: (p10 == null || isNaN(p10)) ? 0 : p10,
      p50: (p50 == null || isNaN(p50)) ? 0 : p50,
      p90: (p90 == null || isNaN(p90)) ? 0 : p90,
    };
  });
  
  return (
    <Card className="overflow-visible" data-testid={testId}>
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          <CardTitle className="text-lg">{title}</CardTitle>
          <UITooltip>
            <TooltipTrigger asChild>
              <button type="button" className="inline-flex">
                <Info className="h-4 w-4 text-muted-foreground" />
              </button>
            </TooltipTrigger>
            <TooltipContent className="max-w-xs">
              <p className="text-sm">{description}</p>
            </TooltipContent>
          </UITooltip>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id={`gradient-${title}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0.05} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.1} />
              <XAxis
                dataKey="month"
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
                tickLine={false}
                axisLine={false}
                tickFormatter={formatValue}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                  padding: '12px',
                }}
                content={({ active, payload, label }) => {
                  if (active && payload && payload.length) {
                    const entry = payload[0]?.payload;
                    const p10 = entry?.p10 ?? (payload.find(p => p.dataKey === 'p10')?.value as number);
                    const p50 = entry?.p50 ?? (payload.find(p => p.dataKey === 'p50')?.value as number);
                    const p90 = entry?.p90 ?? (payload.find(p => p.dataKey === 'p90')?.value as number);
                    return (
                      <div className="bg-card border border-border rounded-lg p-3 shadow-lg">
                        <p className="font-medium text-sm mb-2">Month {label}</p>
                        <div className="space-y-1 text-sm">
                          <div className="flex justify-between gap-4">
                            <span className="text-muted-foreground">P90 (Optimistic):</span>
                            <span className="font-mono text-emerald-400">{formatValue(p90)}</span>
                          </div>
                          <div className="flex justify-between gap-4">
                            <span className="text-muted-foreground">P50 (Median):</span>
                            <span className="font-mono font-bold">{formatValue(p50)}</span>
                          </div>
                          <div className="flex justify-between gap-4">
                            <span className="text-muted-foreground">P10 (Pessimistic):</span>
                            <span className="font-mono text-amber-400">{formatValue(p10)}</span>
                          </div>
                        </div>
                        <p className="text-xs text-muted-foreground mt-2">
                          Range: {formatValue((p90 ?? 0) - (p10 ?? 0))} spread
                        </p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Area
                type="monotone"
                dataKey="p10"
                stroke="none"
                fill={`url(#gradient-${title})`}
                fillOpacity={0.5}
              />
              <Area
                type="monotone"
                dataKey="p90"
                stroke="none"
                fill={`url(#gradient-${title})`}
                fillOpacity={0.3}
              />
              <Line
                type="monotone"
                dataKey="p10"
                stroke="hsl(var(--muted-foreground))"
                strokeWidth={1}
                strokeDasharray="3 3"
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="p50"
                stroke="hsl(var(--primary))"
                strokeWidth={2}
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="p90"
                stroke="hsl(var(--muted-foreground))"
                strokeWidth={1}
                strokeDasharray="3 3"
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div className="flex justify-center gap-4 mt-2 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <span className="w-3 h-0.5 bg-muted-foreground" style={{ borderStyle: 'dashed' }} />
            P10/P90
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-0.5 bg-primary" />
            P50 (Median)
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
