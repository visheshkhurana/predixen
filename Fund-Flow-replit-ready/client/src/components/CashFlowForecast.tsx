import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { HelpCircle, TrendingUp } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, ResponsiveContainer, Tooltip as RechartsTooltip, ReferenceLine } from 'recharts';
import { formatCurrencyAbbrev } from '@/lib/utils';

interface CashFlowMonth {
  month: number;
  inflow: number;
  outflow: number;
  net: number;
  cash_balance: number;
}

interface CashFlowForecastProps {
  forecast: CashFlowMonth[] | null;
  currency?: string;
}

export function CashFlowForecast({ forecast, currency = 'USD' }: CashFlowForecastProps) {
  if (!forecast || forecast.length === 0) {
    return (
      <Card className="overflow-visible">
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-primary" />
            Cash Flow Forecast
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No forecast data available</p>
        </CardContent>
      </Card>
    );
  }

  const formatCurrency = (value: number) => formatCurrencyAbbrev(value, currency);

  // Find when cash goes negative (if ever)
  const negativeMonth = forecast.find(m => m.cash_balance <= 0);
  const runwayEndMonth = negativeMonth?.month;

  // Prepare chart data with month labels
  const chartData = forecast.map(m => ({
    ...m,
    monthLabel: `M${m.month}`,
  }));

  // Get context-aware impact message based on cash flow values
  const getImpactMessage = (data: CashFlowMonth) => {
    const netRatio = data.inflow > 0 ? (data.outflow / data.inflow) : 999;
    const monthsLeft = data.cash_balance > 0 && data.net < 0 ? Math.round(data.cash_balance / Math.abs(data.net)) : null;
    
    if (data.cash_balance <= 0) {
      return { text: 'Cash depleted - Immediate action required to secure funding or reduce burn.', severity: 'critical' };
    }
    if (monthsLeft && monthsLeft < 6) {
      return { text: `Only ${monthsLeft} months runway at current burn. Consider cutting costs or accelerating fundraise.`, severity: 'warning' };
    }
    if (data.net >= 0) {
      return { text: 'Cash-positive month - Your revenue exceeds expenses. This is ideal for sustainable growth.', severity: 'healthy' };
    }
    if (netRatio > 2) {
      return { text: 'High burn rate - Expenses are more than 2x revenue. Focus on reducing costs or boosting sales.', severity: 'warning' };
    }
    if (netRatio > 1.5) {
      return { text: 'Moderate burn - Expenses exceed revenue by 50%+. Normal for growth stage, but monitor closely.', severity: 'info' };
    }
    return { text: 'Healthy burn level - You are efficiently investing in growth while managing cash consumption.', severity: 'healthy' };
  };

  // Custom tooltip with detailed impact explanations
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload as CashFlowMonth;
      const impact = getImpactMessage(data);
      const coverageRatio = data.inflow > 0 ? ((data.inflow / data.outflow) * 100).toFixed(0) : 0;
      
      return (
        <div className="bg-popover border rounded-lg p-3 shadow-lg text-sm max-w-xs">
          <p className="font-semibold mb-2">Month {data.month} Cash Flow</p>
          <div className="space-y-1.5 text-muted-foreground">
            <div className="flex justify-between">
              <span>Inflow (Revenue):</span>
              <span className="text-emerald-500 font-mono">{formatCurrency(data.inflow)}</span>
            </div>
            <div className="flex justify-between">
              <span>Outflow (Expenses):</span>
              <span className="text-red-500 font-mono">{formatCurrency(data.outflow)}</span>
            </div>
            <div className="flex justify-between pt-1 border-t">
              <span>Net Cash Flow:</span>
              <span className={`font-mono font-medium ${data.net >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                {formatCurrency(data.net)}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Ending Balance:</span>
              <span className={`font-mono font-medium ${data.cash_balance <= 0 ? 'text-red-500' : ''}`}>
                {formatCurrency(data.cash_balance)}
              </span>
            </div>
          </div>
          <div className={`mt-3 pt-2 border-t text-xs ${
            impact.severity === 'critical' ? 'text-red-400' : 
            impact.severity === 'warning' ? 'text-amber-400' : 
            impact.severity === 'healthy' ? 'text-emerald-400' : 'text-muted-foreground'
          }`}>
            <p className="font-medium mb-1">
              {impact.severity === 'critical' ? 'Critical:' : 
               impact.severity === 'warning' ? 'Caution:' : 
               impact.severity === 'healthy' ? 'Good:' : 'Note:'}
            </p>
            <p>{impact.text}</p>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            Revenue covers {coverageRatio}% of expenses this month.
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <Card className="overflow-visible">
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-primary" />
          12-Month Cash Flow Forecast
          <Tooltip>
            <TooltipTrigger asChild>
              <button type="button" className="p-0.5">
                <HelpCircle className="h-3 w-3 text-muted-foreground" />
              </button>
            </TooltipTrigger>
            <TooltipContent className="max-w-xs">
              <p className="text-sm">
                Projected cash inflows (revenue) vs outflows (expenses) over the next 12 months based on current growth trends.
              </p>
            </TooltipContent>
          </Tooltip>
          {runwayEndMonth && (
            <span className="text-xs text-red-500 ml-2">
              Cash depletes in Month {runwayEndMonth}
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-48" data-testid="cash-flow-chart">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="colorInflow" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#22c55e" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="colorOutflow" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <XAxis 
                dataKey="monthLabel" 
                tick={{ fontSize: 10 }} 
                tickLine={false}
                axisLine={false}
              />
              <YAxis 
                tick={{ fontSize: 10 }} 
                tickFormatter={(v) => formatCurrency(v)}
                tickLine={false}
                axisLine={false}
                width={60}
              />
              <RechartsTooltip content={<CustomTooltip />} />
              <ReferenceLine y={0} stroke="#666" strokeDasharray="3 3" />
              <Area 
                type="monotone" 
                dataKey="inflow" 
                stroke="#22c55e" 
                strokeWidth={2}
                fill="url(#colorInflow)"
                name="Inflow"
              />
              <Area 
                type="monotone" 
                dataKey="outflow" 
                stroke="#ef4444" 
                strokeWidth={2}
                fill="url(#colorOutflow)"
                name="Outflow"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Summary */}
        <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t">
          <div className="text-center">
            <p className="text-xs text-muted-foreground">Month 1 Balance</p>
            <p className="font-mono font-medium">{formatCurrency(chartData[0]?.cash_balance || 0)}</p>
          </div>
          <div className="text-center">
            <p className="text-xs text-muted-foreground">Month 6 Balance</p>
            <p className="font-mono font-medium">{formatCurrency(chartData[5]?.cash_balance || 0)}</p>
          </div>
          <div className="text-center">
            <p className="text-xs text-muted-foreground">Month 12 Balance</p>
            <p className={`font-mono font-medium ${(chartData[11]?.cash_balance || 0) < 0 ? 'text-red-500' : ''}`}>
              {formatCurrency(chartData[11]?.cash_balance || 0)}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
