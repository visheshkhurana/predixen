import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface MonthData {
  month: number;
  revenue_p50: number;
  cash_p50: number;
  burn_p50: number;
  survival_rate: number;
}

interface ScenarioResult {
  name: string;
  month_data: MonthData[];
}

interface ScenarioComparisonChartProps {
  scenarios: Record<string, ScenarioResult>;
  selectedScenarios?: string[];
  testId?: string;
}

type MetricKey = 'cash_p50' | 'revenue_p50' | 'burn_p50' | 'survival_rate';

const COLORS = [
  'hsl(var(--chart-1))',
  'hsl(var(--chart-2))',
  'hsl(var(--chart-3))',
  'hsl(var(--chart-4))',
  'hsl(var(--chart-5))',
];

export function ScenarioComparisonChart({
  scenarios,
  selectedScenarios,
  testId = 'scenario-comparison-chart'
}: ScenarioComparisonChartProps) {
  const [metric, setMetric] = useState<MetricKey>('cash_p50');

  const scenarioKeys = selectedScenarios || Object.keys(scenarios);

  const chartData = scenarios[scenarioKeys[0]]?.month_data.map((_, idx) => {
    const dataPoint: Record<string, number | string> = {
      month: `M${idx + 1}`
    };
    
    scenarioKeys.forEach((key) => {
      const scenario = scenarios[key];
      if (scenario?.month_data[idx]) {
        dataPoint[key] = scenario.month_data[idx][metric];
      }
    });
    
    return dataPoint;
  }) || [];

  const formatValue = (value: number) => {
    if (metric === 'survival_rate') {
      return `${(value * 100).toFixed(0)}%`;
    }
    if (Math.abs(value) >= 1000000) {
      return `$${(value / 1000000).toFixed(1)}M`;
    }
    return `$${(value / 1000).toFixed(0)}K`;
  };

  const metricLabels: Record<MetricKey, string> = {
    cash_p50: 'Cash Balance',
    revenue_p50: 'Revenue',
    burn_p50: 'Monthly Burn',
    survival_rate: 'Survival Rate'
  };

  return (
    <Card data-testid={testId}>
      <CardHeader className="pb-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <CardTitle className="text-lg">Scenario Comparison</CardTitle>
            <CardDescription>
              Compare trajectories across different scenarios
            </CardDescription>
          </div>
          <Select value={metric} onValueChange={(v) => setMetric(v as MetricKey)}>
            <SelectTrigger className="w-[150px]" data-testid="select-chart-metric">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="cash_p50">Cash Balance</SelectItem>
              <SelectItem value="revenue_p50">Revenue</SelectItem>
              <SelectItem value="burn_p50">Monthly Burn</SelectItem>
              <SelectItem value="survival_rate">Survival Rate</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-[350px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border/50" />
              <XAxis 
                dataKey="month" 
                tick={{ fontSize: 11 }}
                tickLine={false}
                className="text-muted-foreground"
              />
              <YAxis 
                tickFormatter={formatValue}
                tick={{ fontSize: 11 }}
                tickLine={false}
                className="text-muted-foreground"
                width={70}
              />
              <Tooltip
                formatter={(value: number) => [formatValue(value), metricLabels[metric]]}
                contentStyle={{
                  backgroundColor: 'hsl(var(--popover))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '6px',
                }}
                labelStyle={{ color: 'hsl(var(--popover-foreground))' }}
              />
              <Legend />
              {scenarioKeys.map((key, idx) => (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  name={scenarios[key]?.name || key}
                  stroke={COLORS[idx % COLORS.length]}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
