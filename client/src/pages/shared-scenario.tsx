import { useState, useEffect } from "react";
import { useRoute } from "wouter";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
} from "recharts";
import { TrendingUp, TrendingDown, Shield, Clock, BarChart3 } from "lucide-react";

function formatCurrency(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

export default function SharedScenarioPage() {
  const [, params] = useRoute("/scenarios/shared/:uuid");
  const uuid = params?.uuid;
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!uuid) return;
    fetch(`/api/scenarios/shared/${uuid}`)
      .then(res => {
        if (!res.ok) throw new Error("Scenario not found");
        return res.json();
      })
      .then(d => { setData(d); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  }, [uuid]);

  if (loading) {
    return (
      <div className="min-h-screen bg-background p-8">
        <div className="max-w-4xl mx-auto space-y-6">
          <Skeleton className="h-10 w-64" />
          <div className="grid grid-cols-3 gap-4">
            <Skeleton className="h-32" />
            <Skeleton className="h-32" />
            <Skeleton className="h-32" />
          </div>
          <Skeleton className="h-[300px]" />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Card className="max-w-md">
          <CardContent className="pt-6 text-center space-y-4">
            <Shield className="h-12 w-12 mx-auto text-muted-foreground" />
            <h2 className="text-xl font-bold" data-testid="text-shared-error">Scenario Not Found</h2>
            <p className="text-muted-foreground">This shared scenario link may have expired or is invalid.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const sim = data.simulation_data || {};
  const runway = sim.runway || {};
  const survival = sim.survival || {};
  const bands = sim.bands || {};
  const cashBand = bands.cash || {};

  const chartData = (cashBand.p50 || []).map((val: number, i: number) => ({
    month: `M${i}`,
    p10: cashBand.p10?.[i] ?? 0,
    p50: val,
    p90: cashBand.p90?.[i] ?? 0,
  }));

  return (
    <div className="min-h-screen bg-background p-4 md:p-8">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-2xl font-bold" data-testid="text-shared-title">{data.scenario_name}</h1>
              <Badge variant="secondary" data-testid="badge-shared-readonly">Read Only</Badge>
            </div>
            {data.scenario_description && (
              <p className="text-sm text-muted-foreground mt-1">{data.scenario_description}</p>
            )}
            {data.created_at && (
              <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                <Clock className="h-3 w-3" />
                Shared {new Date(data.created_at).toLocaleDateString()}
              </p>
            )}
          </div>
          <Badge className="bg-blue-500/20 text-blue-400">
            <BarChart3 className="h-3 w-3 mr-1" />
            FounderConsole Simulation
          </Badge>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="border-emerald-500/30 bg-emerald-50/30 dark:bg-emerald-950/10" data-testid="card-shared-p90">
            <CardContent className="pt-4 pb-4 px-4">
              <div className="flex items-center gap-2 mb-2">
                <div className="h-2 w-2 rounded-full bg-emerald-500" />
                <span className="text-xs font-medium text-emerald-600 dark:text-emerald-400">Best Case (P90)</span>
              </div>
              <p className="text-2xl font-bold" data-testid="text-shared-runway-p90">{runway.p90?.toFixed(1) ?? "—"} months</p>
              <p className="text-xs text-muted-foreground mt-1">Runway</p>
              {survival?.["12_month"] != null && (
                <p className="text-xs text-muted-foreground">
                  12m survival: {(survival["12_month"] * 100).toFixed(0)}%
                </p>
              )}
            </CardContent>
          </Card>

          <Card className="border-blue-500/30 bg-blue-50/30 dark:bg-blue-950/10" data-testid="card-shared-p50">
            <CardContent className="pt-4 pb-4 px-4">
              <div className="flex items-center gap-2 mb-2">
                <div className="h-2 w-2 rounded-full bg-blue-500" />
                <span className="text-xs font-medium text-blue-600 dark:text-blue-400">Median (P50)</span>
              </div>
              <p className="text-2xl font-bold" data-testid="text-shared-runway-p50">{runway.p50?.toFixed(1) ?? "—"} months</p>
              <p className="text-xs text-muted-foreground mt-1">Runway</p>
            </CardContent>
          </Card>

          <Card className="border-amber-500/30 bg-amber-50/30 dark:bg-amber-950/10" data-testid="card-shared-p10">
            <CardContent className="pt-4 pb-4 px-4">
              <div className="flex items-center gap-2 mb-2">
                <div className="h-2 w-2 rounded-full bg-amber-500" />
                <span className="text-xs font-medium text-amber-600 dark:text-amber-400">Worst Case (P10)</span>
              </div>
              <p className="text-2xl font-bold" data-testid="text-shared-runway-p10">{runway.p10?.toFixed(1) ?? "—"} months</p>
              <p className="text-xs text-muted-foreground mt-1">Runway</p>
            </CardContent>
          </Card>
        </div>

        {chartData.length > 0 && (
          <Card data-testid="card-shared-chart">
            <CardHeader>
              <CardTitle className="text-lg">Cash Projection (24 months)</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
                  <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                  <YAxis tickFormatter={(v: number) => formatCurrency(v)} tick={{ fontSize: 11 }} />
                  <RechartsTooltip
                    formatter={(value: number) => formatCurrency(value)}
                    contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))" }}
                  />
                  <Area type="monotone" dataKey="p90" stroke="#22c55e" fill="#22c55e" fillOpacity={0.1} name="P90" />
                  <Area type="monotone" dataKey="p50" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.15} name="P50" strokeWidth={2} />
                  <Area type="monotone" dataKey="p10" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.1} name="P10" />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}

        <div className="text-center py-4">
          <p className="text-xs text-muted-foreground">
            Powered by <a href="https://founderconsole.ai" className="text-primary hover:underline">FounderConsole</a> &mdash; AI-powered financial simulation
          </p>
        </div>
      </div>
    </div>
  );
}
