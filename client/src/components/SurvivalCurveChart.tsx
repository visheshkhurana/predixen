import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Info } from 'lucide-react';
import { Tooltip as UITooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';

interface SurvivalCurveChartProps {
  data: Array<{ month: number; survival_rate: number }>;
  title?: string;
  testId?: string;
}

export function SurvivalCurveChart({
  data,
  title = 'Survival Curve',
  testId = 'survival-curve-chart',
}: SurvivalCurveChartProps) {
  const formattedData = data.map((d) => ({
    month: d.month,
    survival: d.survival_rate * 100,
  }));
  
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
              <p className="text-sm">Monte Carlo probability that your company survives (cash &gt; 0) at each month. The 50% line shows when you have a coin-flip chance of running out.</p>
            </TooltipContent>
          </UITooltip>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={formattedData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.1} />
              <XAxis
                dataKey="month"
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
                tickLine={false}
                axisLine={false}
                label={{ value: 'Month', position: 'insideBottom', offset: -5, fontSize: 11 }}
              />
              <YAxis
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
                tickLine={false}
                axisLine={false}
                domain={[0, 100]}
                tickFormatter={(v) => `${v}%`}
                label={{ value: 'Survival %', angle: -90, position: 'insideLeft', fontSize: 11 }}
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
                    const survival = payload[0].value as number;
                    const status = survival >= 75 ? 'Strong' : survival >= 50 ? 'Moderate' : 'At Risk';
                    const statusColor = survival >= 75 ? 'text-emerald-500' : survival >= 50 ? 'text-amber-500' : 'text-red-500';
                    return (
                      <div className="bg-card border border-border rounded-lg p-3 shadow-lg">
                        <p className="font-medium text-sm mb-1">Month {label}</p>
                        <p className="text-lg font-mono font-bold">{survival.toFixed(1)}%</p>
                        <p className={`text-xs ${statusColor}`}>{status} position</p>
                        <p className="text-xs text-muted-foreground mt-1">
                          {survival >= 50 
                            ? `${(100 - survival).toFixed(0)}% chance of cash depletion`
                            : `More likely to run out of cash than survive`
                          }
                        </p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <ReferenceLine y={50} stroke="hsl(var(--muted-foreground))" strokeDasharray="3 3" />
              <Line
                type="monotone"
                dataKey="survival"
                stroke="hsl(var(--primary))"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: 'hsl(var(--primary))' }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
