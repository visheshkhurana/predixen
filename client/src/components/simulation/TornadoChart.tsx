import { useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip as RechartsTooltip, ReferenceLine, Cell, ResponsiveContainer } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { BarChart3, Info } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';

interface SensitivityVariable {
  name: string;
  displayName: string;
  baseValue: number;
  unit: string;
  lowImpact: number;
  highImpact: number;
  currentValue: number;
}

interface TornadoChartProps {
  baselineRunway: number;
  variables: SensitivityVariable[];
  onVariableClick?: (variable: string) => void;
  testId?: string;
}

export function TornadoChart({ baselineRunway, variables, onVariableClick, testId = 'tornado-chart' }: TornadoChartProps) {
  const sortedData = useMemo(() => {
    return [...variables]
      .map(v => ({
        ...v,
        totalSwing: Math.abs(v.lowImpact) + Math.abs(v.highImpact),
        low: v.lowImpact,
        high: v.highImpact,
      }))
      .sort((a, b) => b.totalSwing - a.totalSwing);
  }, [variables]);

  const maxSwing = Math.max(...sortedData.map(d => Math.max(Math.abs(d.low), Math.abs(d.high))), 1);

  if (sortedData.length === 0) {
    return (
      <Card data-testid={testId}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Sensitivity Analysis
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-sm">No sensitivity data available</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card data-testid={testId}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Sensitivity Analysis
          </CardTitle>
          <Tooltip>
            <TooltipTrigger asChild>
              <Info className="h-4 w-4 text-muted-foreground cursor-help" />
            </TooltipTrigger>
            <TooltipContent side="left" className="max-w-xs">
              <p>Shows which variables have the biggest impact on your runway when changed by +/-20%</p>
            </TooltipContent>
          </Tooltip>
        </div>
        <CardDescription>
          Which variables have the biggest impact on your runway?
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="text-center text-sm text-muted-foreground mb-4">
          Baseline: {baselineRunway.toFixed(1)} months
        </div>

        <ResponsiveContainer width="100%" height={sortedData.length * 50 + 40}>
          <BarChart 
            data={sortedData} 
            layout="vertical" 
            margin={{ left: 100, right: 40, top: 10, bottom: 10 }}
          >
            <XAxis 
              type="number" 
              domain={[-maxSwing * 1.1, maxSwing * 1.1]} 
              tickFormatter={(v) => `${v > 0 ? '+' : ''}${v.toFixed(1)}mo`} 
              stroke="hsl(var(--muted-foreground))"
              fontSize={11}
            />
            <YAxis 
              type="category" 
              dataKey="displayName" 
              stroke="hsl(var(--muted-foreground))"
              tick={{ fill: 'hsl(var(--foreground))', fontSize: 11 }} 
              width={95}
            />
            <RechartsTooltip
              contentStyle={{ 
                backgroundColor: 'hsl(var(--card))', 
                border: '1px solid hsl(var(--border))', 
                borderRadius: '8px',
                color: 'hsl(var(--foreground))'
              }}
              formatter={(value: number, name: string) => {
                return [`${value > 0 ? '+' : ''}${value.toFixed(1)} months`, name === 'low' ? 'If decreased 20%' : 'If increased 20%'];
              }}
              labelFormatter={(label) => label}
            />
            <ReferenceLine x={0} stroke="hsl(var(--muted-foreground))" strokeWidth={2} />
            <Bar 
              dataKey="low" 
              stackId="a" 
              fill="#EF4444" 
              radius={[4, 0, 0, 4]} 
              onClick={(data) => onVariableClick?.(data.name)} 
              cursor="pointer"
            >
              {sortedData.map((entry, index) => (
                <Cell key={`low-${index}`} fill={entry.low < 0 ? '#EF4444' : '#10B981'} />
              ))}
            </Bar>
            <Bar 
              dataKey="high" 
              stackId="a" 
              fill="#10B981" 
              radius={[0, 4, 4, 0]} 
              onClick={(data) => onVariableClick?.(data.name)} 
              cursor="pointer"
            >
              {sortedData.map((entry, index) => (
                <Cell key={`high-${index}`} fill={entry.high > 0 ? '#10B981' : '#EF4444'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>

        <div className="mt-4 flex items-center justify-center gap-6 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-red-500 rounded"></div>
            <span className="text-muted-foreground">Decreases runway</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-green-500 rounded"></div>
            <span className="text-muted-foreground">Increases runway</span>
          </div>
        </div>

        <p className="text-muted-foreground text-xs text-center mt-4">Click on any bar to drill into that variable</p>
      </CardContent>
    </Card>
  );
}

export default TornadoChart;
