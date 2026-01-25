import { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface SensitivityResult {
  parameter: string;
  label: string;
  baselineValue: number;
  lowValue: number;
  highValue: number;
  runwayAtLow: number;
  runwayAtHigh: number;
  runwayAtBaseline: number;
  impact: number;
  direction: "positive" | "negative" | "mixed";
}

interface TornadoChartData {
  scenarioId: number;
  targetMetric: string;
  baselineValue: number;
  parameters: SensitivityResult[];
}

interface TornadoChartProps {
  data: TornadoChartData;
  maxBars?: number;
}

export function TornadoChart({ data, maxBars = 10 }: TornadoChartProps) {
  const chartData = useMemo(() => {
    const params = data.parameters.slice(0, maxBars);
    return params.map((p) => ({
      name: p.label,
      parameter: p.parameter,
      low: p.runwayAtLow - data.baselineValue,
      high: p.runwayAtHigh - data.baselineValue,
      impact: p.impact,
      direction: p.direction,
      baselineValue: p.baselineValue,
      lowValue: p.lowValue,
      highValue: p.highValue,
      runwayAtLow: p.runwayAtLow,
      runwayAtHigh: p.runwayAtHigh,
    }));
  }, [data, maxBars]);

  const maxDeviation = useMemo(() => {
    let max = 0;
    chartData.forEach((d) => {
      max = Math.max(max, Math.abs(d.low), Math.abs(d.high));
    });
    return Math.ceil(max * 1.2);
  }, [chartData]);

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const item = payload[0].payload;
      return (
        <div className="bg-popover border rounded-lg p-3 shadow-lg">
          <p className="font-semibold text-foreground mb-2">{item.name}</p>
          <div className="space-y-1 text-sm">
            <div className="flex justify-between gap-4">
              <span className="text-muted-foreground">Low value:</span>
              <span className="font-mono">{item.lowValue.toFixed(1)}</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-muted-foreground">High value:</span>
              <span className="font-mono">{item.highValue.toFixed(1)}</span>
            </div>
            <div className="border-t pt-1 mt-1">
              <div className="flex justify-between gap-4">
                <span className="text-muted-foreground">Runway at low:</span>
                <span className="font-mono">{item.runwayAtLow.toFixed(1)} mo</span>
              </div>
              <div className="flex justify-between gap-4">
                <span className="text-muted-foreground">Runway at high:</span>
                <span className="font-mono">{item.runwayAtHigh.toFixed(1)} mo</span>
              </div>
            </div>
            <div className="border-t pt-1 mt-1">
              <div className="flex justify-between gap-4">
                <span className="text-muted-foreground">Impact:</span>
                <span className="font-mono font-semibold">{item.impact.toFixed(1)} mo</span>
              </div>
            </div>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Sensitivity Analysis</CardTitle>
            <CardDescription>
              Parameter impact on runway (baseline: {data.baselineValue.toFixed(1)} months)
            </CardDescription>
          </div>
          <Badge variant="outline" className="font-mono">
            Top {Math.min(maxBars, data.parameters.length)} drivers
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-[400px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              layout="vertical"
              data={chartData}
              margin={{ top: 20, right: 30, left: 100, bottom: 5 }}
            >
              <XAxis
                type="number"
                domain={[-maxDeviation, maxDeviation]}
                tickFormatter={(v) => `${v > 0 ? "+" : ""}${v.toFixed(0)}`}
              />
              <YAxis
                type="category"
                dataKey="name"
                width={90}
                tick={{ fontSize: 12 }}
              />
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine x={0} stroke="hsl(var(--muted-foreground))" strokeDasharray="3 3" />
              <Bar dataKey="low" stackId="stack" name="Low">
                {chartData.map((entry, index) => (
                  <Cell
                    key={`low-${index}`}
                    fill={entry.low < 0 ? "hsl(var(--destructive))" : "hsl(var(--chart-2))"}
                  />
                ))}
              </Bar>
              <Bar dataKey="high" stackId="stack" name="High">
                {chartData.map((entry, index) => (
                  <Cell
                    key={`high-${index}`}
                    fill={entry.high > 0 ? "hsl(var(--chart-2))" : "hsl(var(--destructive))"}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="mt-6 space-y-3">
          <h4 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">
            Key Insights
          </h4>
          <div className="grid gap-3">
            {chartData.slice(0, 3).map((item, idx) => (
              <div
                key={item.parameter}
                className="flex items-start gap-3 p-3 rounded-lg bg-muted/50"
                data-testid={`insight-${item.parameter}`}
              >
                <div className="flex-shrink-0 mt-0.5">
                  {item.direction === "positive" ? (
                    <TrendingUp className="h-4 w-4 text-green-500" />
                  ) : item.direction === "negative" ? (
                    <TrendingDown className="h-4 w-4 text-red-500" />
                  ) : (
                    <Minus className="h-4 w-4 text-muted-foreground" />
                  )}
                </div>
                <div className="flex-1">
                  <p className="text-sm">
                    <span className="font-medium">{item.name}</span>
                    {item.direction === "positive" ? (
                      <span className="text-muted-foreground">
                        {" "}
                        - Increasing from {item.lowValue.toFixed(1)} to {item.highValue.toFixed(1)} extends
                        runway by {item.impact.toFixed(1)} months
                      </span>
                    ) : item.direction === "negative" ? (
                      <span className="text-muted-foreground">
                        {" "}
                        - Increasing from {item.lowValue.toFixed(1)} to {item.highValue.toFixed(1)} reduces
                        runway by {Math.abs(item.impact).toFixed(1)} months
                      </span>
                    ) : (
                      <span className="text-muted-foreground">
                        {" "}
                        - Has a {item.impact.toFixed(1)} month impact on runway
                      </span>
                    )}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export type { TornadoChartData, SensitivityResult };
