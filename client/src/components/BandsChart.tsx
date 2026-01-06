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
}

export function BandsChart({
  data,
  title,
  yAxisLabel = 'Value',
  formatValue = (v) => `$${(v / 1000).toFixed(0)}k`,
  testId = 'bands-chart',
}: BandsChartProps) {
  const chartData = data.p50.map((_, index) => ({
    month: index + 1,
    p10: data.p10[index],
    p50: data.p50[index],
    p90: data.p90[index],
  }));
  
  return (
    <Card className="overflow-visible" data-testid={testId}>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg">{title}</CardTitle>
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
                }}
                formatter={(value: number, name: string) => [formatValue(value), name.toUpperCase()]}
                labelFormatter={(label) => `Month ${label}`}
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
