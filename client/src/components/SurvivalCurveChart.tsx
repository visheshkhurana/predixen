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
        <CardTitle className="text-lg">{title}</CardTitle>
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
                }}
                formatter={(value: number) => [`${value.toFixed(1)}%`, 'Survival Rate']}
                labelFormatter={(label) => `Month ${label}`}
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
