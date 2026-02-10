import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  ComposedChart,
  Legend,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import type { MonthlyProjection } from "@shared/schema";
import { formatCurrencyAbbrev, formatCurrencyFull } from "@/lib/utils";

interface CashFlowChartProps {
  projections: MonthlyProjection[];
  title?: string;
  showRunwayLine?: boolean;
  currency?: string;
}

export function CashFlowChart({
  projections,
  title = "Cash Balance Projection",
  showRunwayLine = true,
  currency = 'USD',
}: CashFlowChartProps) {
  const formatCurrency = (value: number) => formatCurrencyAbbrev(value, currency);
  const formatTooltipValue = (value: number) => formatCurrencyFull(value, currency);

  const cashOutMonth = projections.find((p) => p.cashBalance <= 0);

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-popover border border-popover-border rounded-lg shadow-lg p-3">
          <p className="font-medium text-sm mb-2">{label}</p>
          {payload.map((entry: any, index: number) => (
            <div key={index} className="flex items-center gap-2 text-sm">
              <div
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: entry.color }}
              />
              <span className="text-muted-foreground">{entry.name}:</span>
              <span className="font-mono font-medium">
                {formatTooltipValue(entry.value)}
              </span>
            </div>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <Card data-testid="chart-cash-flow">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg">{title}</CardTitle>
        <CardDescription>
          {cashOutMonth
            ? `Warning: Cash runs out in ${cashOutMonth.date}`
            : "Projected cash position over time"}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[350px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart
              data={projections}
              margin={{ top: 20, right: 20, left: 10, bottom: 20 }}
            >
              <defs>
                <linearGradient id="cashGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--chart-1))" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="hsl(var(--chart-1))" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="hsl(var(--border))"
                vertical={false}
              />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                tickLine={false}
                axisLine={{ stroke: "hsl(var(--border))" }}
              />
              <YAxis
                tickFormatter={formatCurrency}
                tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                tickLine={false}
                axisLine={false}
                width={60}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                wrapperStyle={{ paddingTop: "20px" }}
                formatter={(value) => (
                  <span className="text-xs text-muted-foreground">{value}</span>
                )}
              />
              {showRunwayLine && (
                <ReferenceLine
                  y={0}
                  stroke="hsl(var(--destructive))"
                  strokeDasharray="5 5"
                  label={{
                    value: "Cash Out",
                    position: "right",
                    fill: "hsl(var(--destructive))",
                    fontSize: 11,
                  }}
                />
              )}
              <Area
                type="monotone"
                dataKey="cashBalance"
                name="Cash Balance"
                stroke="hsl(var(--chart-1))"
                fill="url(#cashGradient)"
                strokeWidth={2}
              />
              <Line
                type="monotone"
                dataKey="revenue"
                name="Revenue"
                stroke="hsl(var(--chart-2))"
                strokeWidth={2}
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="expenses"
                name="Expenses"
                stroke="hsl(var(--chart-5))"
                strokeWidth={2}
                dot={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
