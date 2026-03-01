import { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Info } from 'lucide-react';
import { formatCurrencyAbbrev } from '@/lib/utils';
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ReferenceLine,
} from 'recharts';

interface MonthlyData {
  month: number;
  revenue: number;
  burn: number;
  cash?: number;
}

interface StackedBurnRevenueChartProps {
  data: MonthlyData[];
  scenarioName?: string;
  currency?: string;
  testId?: string;
}

export function StackedBurnRevenueChart({
  data,
  scenarioName = 'Scenario',
  currency = 'USD',
  testId = 'stacked-burn-revenue-chart',
}: StackedBurnRevenueChartProps) {
  const chartData = useMemo(() => {
    return data.map((d) => ({
      ...d,
      netBurn: d.burn - d.revenue,
      profitability: d.revenue >= d.burn ? 'Profitable' : 'Burning',
    }));
  }, [data]);
  
  const breakEvenMonth = useMemo(() => {
    return chartData.findIndex(d => d.revenue >= d.burn) + 1;
  }, [chartData]);
  
  const totalBurn = chartData.reduce((sum, d) => sum + Math.max(0, d.burn - d.revenue), 0);
  const endingRevenue = chartData[chartData.length - 1]?.revenue || 0;
  
  const formatCurrency = (value: number) => formatCurrencyAbbrev(value, currency);
  
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-popover border rounded-lg p-3 shadow-lg">
          <p className="font-semibold mb-2">Month {label}</p>
          <div className="space-y-1 text-sm">
            <div className="flex justify-between gap-4">
              <span className="text-emerald-600 dark:text-emerald-400">Revenue:</span>
              <span className="font-mono font-medium">{formatCurrency(data.revenue)}</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-red-600 dark:text-red-400">Burn:</span>
              <span className="font-mono">{formatCurrency(data.burn)}</span>
            </div>
            <div className="flex justify-between gap-4 pt-1 border-t">
              <span className="text-muted-foreground">Net:</span>
              <span className={`font-mono font-medium ${data.netBurn > 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                {data.netBurn > 0 ? '-' : '+'}{formatCurrency(Math.abs(data.netBurn))}
              </span>
            </div>
            {data.cash !== undefined && (
              <div className="flex justify-between gap-4">
                <span className="text-muted-foreground">Cash:</span>
                <span className="font-mono">{formatCurrency(data.cash)}</span>
              </div>
            )}
          </div>
        </div>
      );
    }
    return null;
  };
  
  return (
    <Card data-testid={testId}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <CardTitle className="text-lg">{scenarioName}: Revenue vs Burn</CardTitle>
            <Tooltip>
              <TooltipTrigger asChild>
                <button type="button" className="inline-flex">
                  <Info className="h-4 w-4 text-muted-foreground" />
                </button>
              </TooltipTrigger>
              <TooltipContent className="max-w-xs">
                <p>Shows monthly revenue (green) and burn (red) over time. When revenue exceeds burn, you reach profitability.</p>
              </TooltipContent>
            </Tooltip>
          </div>
          
          <div className="flex items-center gap-2">
            {breakEvenMonth > 0 && breakEvenMonth <= chartData.length && (
              <Badge variant="outline" className="border-emerald-500 text-emerald-600">
                Break-even: Month {breakEvenMonth}
              </Badge>
            )}
            {breakEvenMonth === 0 || breakEvenMonth > chartData.length && (
              <Badge variant="outline" className="border-amber-500 text-amber-600">
                Not profitable in horizon
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      
      <CardContent>
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className="text-center p-3 bg-muted/50 rounded-lg">
            <p className="text-xs text-muted-foreground">Total Net Burn</p>
            <p className="text-xl font-mono font-bold text-red-600 dark:text-red-400">
              {formatCurrency(totalBurn)}
            </p>
          </div>
          <div className="text-center p-3 bg-muted/50 rounded-lg">
            <p className="text-xs text-muted-foreground">Ending MRR</p>
            <p className="text-xl font-mono font-bold text-emerald-600 dark:text-emerald-400">
              {formatCurrency(endingRevenue)}
            </p>
          </div>
          <div className="text-center p-3 bg-muted/50 rounded-lg">
            <p className="text-xs text-muted-foreground">Revenue Growth</p>
            <p className="text-xl font-mono font-bold">
              {chartData.length > 1 
                ? `${((endingRevenue / (chartData[0]?.revenue || 1) - 1) * 100).toFixed(0)}%`
                : '0%'
              }
            </p>
          </div>
        </div>
        
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 10, right: 30, left: 10, bottom: 10 }}>
              <defs>
                <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(142, 76%, 36%)" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="hsl(142, 76%, 36%)" stopOpacity={0.1} />
                </linearGradient>
                <linearGradient id="burnGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(0, 84%, 60%)" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="hsl(0, 84%, 60%)" stopOpacity={0.1} />
                </linearGradient>
              </defs>
              
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              
              <XAxis 
                dataKey="month" 
                tickFormatter={(v) => `M${v}`}
                stroke="hsl(var(--muted-foreground))"
                tick={{ fontSize: 12 }}
              />
              <YAxis 
                tickFormatter={formatCurrency}
                stroke="hsl(var(--muted-foreground))"
                tick={{ fontSize: 12 }}
                width={70}
              />
              
              <RechartsTooltip content={<CustomTooltip />} />
              
              <Area
                type="monotone"
                dataKey="burn"
                stroke="hsl(0, 84%, 60%)"
                strokeWidth={2}
                fill="url(#burnGradient)"
                name="Monthly Burn"
              />
              
              <Area
                type="monotone"
                dataKey="revenue"
                stroke="hsl(142, 76%, 36%)"
                strokeWidth={2}
                fill="url(#revenueGradient)"
                name="Monthly Revenue"
              />
              
              {breakEvenMonth > 0 && breakEvenMonth <= chartData.length && (
                <ReferenceLine 
                  x={breakEvenMonth}
                  stroke="hsl(var(--primary))"
                  strokeDasharray="5 5"
                  label={{
                    value: 'Break-even',
                    position: 'top',
                    fill: 'hsl(var(--primary))',
                    fontSize: 11,
                  }}
                />
              )}
              
              <Legend />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
