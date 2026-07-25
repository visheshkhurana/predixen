import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { useFounderStore } from "@/store/founderStore";
import { useToast } from "@/hooks/use-toast";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { Slider } from "@/components/ui/slider";
import {
  Activity,
  Cpu,
  TrendingUp,
  TrendingDown,
  DollarSign,
  AlertTriangle,
  CheckCircle,
  Clock,
  Zap,
  Play,
  BarChart3,
  Target,
  Shield,
  Loader2,
  RefreshCw,
  ChevronRight,
  ArrowUpRight,
  ArrowDownRight,
} from "lucide-react";

function formatCurrency(value: number | null | undefined): string {
  if (value == null) return "N/A";
  if (Math.abs(value) >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

function formatNumber(value: number | null | undefined): string {
  if (value == null) return "N/A";
  return value.toLocaleString();
}

function RiskBadge({ severity }: { severity: string }) {
  const variants: Record<string, string> = {
    critical: "bg-red-500/15 text-red-400 border-red-500/30",
    warning: "bg-amber-500/15 text-amber-400 border-amber-500/30",
    info: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  };
  return (
    <Badge className={`text-xs border ${variants[severity] || variants.info}`} data-testid={`badge-risk-${severity}`}>
      {severity}
    </Badge>
  );
}

function TwinHealthScore({ health }: { health: any }) {
  if (!health) return null;
  const colors: Record<string, string> = {
    excellent: "text-emerald-400",
    good: "text-blue-400",
    needs_data: "text-amber-400",
  };
  const progressColors: Record<string, string> = {
    excellent: "[&>div]:bg-emerald-500",
    good: "[&>div]:bg-blue-500",
    needs_data: "[&>div]:bg-amber-500",
  };
  return (
    <div className="space-y-2" data-testid="twin-health-score">
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">Twin Health</span>
        <span className={`text-sm font-bold font-mono ${colors[health.status] || "text-muted-foreground"}`}>
          {health.score}/100
        </span>
      </div>
      <Progress value={health.score} className={`h-1.5 bg-muted/40 ${progressColors[health.status] || ""}`} />
      <div className="flex flex-wrap gap-1">
        {health.factors?.map((f: string) => (
          <Badge key={f} variant="outline" className="text-[10px] px-1.5 py-0 h-4">
            {f.replace(/_/g, " ")}
          </Badge>
        ))}
      </div>
    </div>
  );
}

function MetricCard({
  label,
  value,
  icon: Icon,
  trend,
  testId,
}: {
  label: string;
  value: string;
  icon: any;
  trend?: "up" | "down" | null;
  testId: string;
}) {
  return (
    <Card className="bg-card/50 border-border/50" data-testid={testId}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-2">
          <Icon className="h-4 w-4 text-muted-foreground" />
          {trend === "up" && <ArrowUpRight className="h-3.5 w-3.5 text-emerald-400" />}
          {trend === "down" && <ArrowDownRight className="h-3.5 w-3.5 text-red-400" />}
        </div>
        <div className="text-xl font-bold font-mono" data-testid={`${testId}-value`}>{value}</div>
        <div className="text-xs text-muted-foreground mt-1">{label}</div>
      </CardContent>
    </Card>
  );
}

function SimulationExplorer({ companyId }: { companyId: number }) {
  const { toast } = useToast();
  const [pricingChange, setPricingChange] = useState(0);
  const [growthUplift, setGrowthUplift] = useState(0);
  const [burnReduction, setBurnReduction] = useState(0);
  const [fundraiseAmount, setFundraiseAmount] = useState("");
  const [fundraiseMonth, setFundraiseMonth] = useState("");

  const simMutation = useMutation({
    mutationFn: async (config: any) => {
      const res = await apiRequest("POST", `/api/companies/${companyId}/twin/simulate`, config);
      return await res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/companies", companyId, "twin"] });
      toast({ title: "Simulation complete" });
    },
    onError: () => {
      toast({ title: "Simulation failed", variant: "destructive" });
    },
  });

  const runSimulation = () => {
    simMutation.mutate({
      scenario_name: "Twin Explorer",
      pricing_change_pct: pricingChange,
      growth_uplift_pct: growthUplift,
      burn_reduction_pct: burnReduction,
      fundraise_amount: fundraiseAmount ? parseInt(fundraiseAmount) : undefined,
      fundraise_month: fundraiseMonth ? parseInt(fundraiseMonth) : undefined,
    });
  };

  const results = simMutation.data?.results;

  return (
    <Card data-testid="simulation-explorer">
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <Zap className="h-4 w-4 text-primary" />
          Simulation Explorer
        </CardTitle>
        <CardDescription>Adjust levers and run instant Monte Carlo simulations</CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid gap-4">
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Pricing Change</span>
              <span className="font-mono text-xs">{pricingChange > 0 ? "+" : ""}{pricingChange}%</span>
            </div>
            <Slider
              value={[pricingChange]}
              onValueChange={([v]) => setPricingChange(v)}
              min={-50}
              max={100}
              step={5}
              data-testid="slider-pricing"
            />
          </div>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Growth Uplift</span>
              <span className="font-mono text-xs">{growthUplift > 0 ? "+" : ""}{growthUplift}%</span>
            </div>
            <Slider
              value={[growthUplift]}
              onValueChange={([v]) => setGrowthUplift(v)}
              min={-50}
              max={200}
              step={5}
              data-testid="slider-growth"
            />
          </div>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Burn Reduction</span>
              <span className="font-mono text-xs">{burnReduction}%</span>
            </div>
            <Slider
              value={[burnReduction]}
              onValueChange={([v]) => setBurnReduction(v)}
              min={0}
              max={80}
              step={5}
              data-testid="slider-burn"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Fundraise Amount</label>
              <Input
                placeholder="e.g. 2000000"
                value={fundraiseAmount}
                onChange={(e) => setFundraiseAmount(e.target.value)}
                data-testid="input-fundraise-amount"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Fundraise Month</label>
              <Input
                placeholder="e.g. 3"
                value={fundraiseMonth}
                onChange={(e) => setFundraiseMonth(e.target.value)}
                data-testid="input-fundraise-month"
              />
            </div>
          </div>
        </div>

        <Button
          onClick={runSimulation}
          disabled={simMutation.isPending}
          className="w-full"
          data-testid="button-run-simulation"
        >
          {simMutation.isPending ? (
            <><Loader2 className="h-4 w-4 animate-spin mr-2" /> Running 1,000 Simulations...</>
          ) : (
            <><Play className="h-4 w-4 mr-2" /> Run Monte Carlo Simulation</>
          )}
        </Button>

        {results && (
          <div className="mt-4 space-y-3" data-testid="simulation-results">
            <div className="text-sm font-medium">Results</div>
            <div className="grid grid-cols-3 gap-3">
              <div className="rounded-lg bg-red-500/10 border border-red-500/20 p-3 text-center">
                <div className="text-[10px] text-red-400 uppercase tracking-wider mb-1">P10 (Worst)</div>
                <div className="text-lg font-bold font-mono text-red-400" data-testid="text-p10-runway">
                  {results.p10_runway?.toFixed(1) ?? "—"}
                </div>
                <div className="text-[10px] text-muted-foreground">months</div>
              </div>
              <div className="rounded-lg bg-blue-500/10 border border-blue-500/20 p-3 text-center">
                <div className="text-[10px] text-blue-400 uppercase tracking-wider mb-1">P50 (Median)</div>
                <div className="text-lg font-bold font-mono text-blue-400" data-testid="text-p50-runway">
                  {results.p50_runway?.toFixed(1) ?? "—"}
                </div>
                <div className="text-[10px] text-muted-foreground">months</div>
              </div>
              <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/20 p-3 text-center">
                <div className="text-[10px] text-emerald-400 uppercase tracking-wider mb-1">P90 (Best)</div>
                <div className="text-lg font-bold font-mono text-emerald-400" data-testid="text-p90-runway">
                  {results.p90_runway?.toFixed(1) ?? "—"}
                </div>
                <div className="text-[10px] text-muted-foreground">months</div>
              </div>
            </div>
            {results.survival_probability != null && (
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/30 border border-border/50">
                <span className="text-sm text-muted-foreground">24-Month Survival</span>
                <span className={`text-lg font-bold font-mono ${results.survival_probability >= 0.7 ? "text-emerald-400" : results.survival_probability >= 0.4 ? "text-amber-400" : "text-red-400"}`} data-testid="text-survival">
                  {(results.survival_probability * 100).toFixed(1)}%
                </span>
              </div>
            )}
            {simMutation.data?.fallback && (
              <p className="text-[11px] text-muted-foreground italic">
                Using simplified model (enhanced Monte Carlo unavailable)
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function DecisionTimeline({ companyId }: { companyId: number }) {
  const { data, isLoading } = useQuery({
    queryKey: ["/api/companies", companyId, "twin", "decisions"],
    enabled: !!companyId,
  });

  if (isLoading) return <Skeleton className="h-48" />;

  const decisions = data?.decisions || [];

  return (
    <Card data-testid="decision-timeline">
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <Target className="h-4 w-4 text-primary" />
          Decision Memory
        </CardTitle>
        <CardDescription>Past decisions and their outcomes feed the twin's learning</CardDescription>
      </CardHeader>
      <CardContent>
        {decisions.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">No decisions recorded yet</p>
        ) : (
          <div className="space-y-3">
            {decisions.slice(0, 8).map((d: any) => (
              <div key={d.id} className="flex items-start gap-3 p-3 rounded-lg bg-muted/20 border border-border/30" data-testid={`decision-${d.id}`}>
                <div className={`mt-0.5 h-2 w-2 rounded-full flex-shrink-0 ${
                  d.status === "accepted" ? "bg-emerald-500" : d.status === "rejected" ? "bg-red-500" : "bg-amber-500"
                }`} />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{d.title}</div>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4">
                      {d.status}
                    </Badge>
                    {d.confidence && (
                      <span className="text-[10px] text-muted-foreground font-mono">
                        {d.confidence}
                      </span>
                    )}
                    {d.tags?.length > 0 && (
                      <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4">
                        {d.tags[0]}
                      </Badge>
                    )}
                  </div>
                </div>
                <span className="text-[10px] text-muted-foreground whitespace-nowrap">
                  {d.created_at ? new Date(d.created_at).toLocaleDateString() : ""}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function EventLog({ companyId }: { companyId: number }) {
  const { data, isLoading } = useQuery({
    queryKey: ["/api/companies", companyId, "twin", "events"],
    enabled: !!companyId,
  });

  if (isLoading) return <Skeleton className="h-48" />;

  const events = data?.events || [];
  const iconMap: Record<string, any> = {
    state_update: RefreshCw,
    simulation_run: Zap,
    decision_made: Target,
    alert_triggered: AlertTriangle,
    connector_sync: Activity,
    revenue_update: TrendingUp,
    expense_update: TrendingDown,
  };

  return (
    <Card data-testid="event-log">
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <Clock className="h-4 w-4 text-primary" />
          Twin Event Log
        </CardTitle>
      </CardHeader>
      <CardContent>
        {events.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">No events recorded yet. Events are generated as you use the platform.</p>
        ) : (
          <div className="space-y-2 max-h-[400px] overflow-y-auto">
            {events.map((e: any) => {
              const EIcon = iconMap[e.event_type] || Activity;
              return (
                <div key={e.id} className="flex items-center gap-3 p-2 rounded-md hover:bg-muted/30 transition-colors" data-testid={`event-${e.id}`}>
                  <EIcon className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <span className="text-sm">{e.event_type.replace(/_/g, " ")}</span>
                    <span className="text-[10px] text-muted-foreground ml-2">via {e.source}</span>
                  </div>
                  <span className="text-[10px] text-muted-foreground whitespace-nowrap">
                    {e.created_at ? new Date(e.created_at).toLocaleString() : ""}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function DigitalTwinPage() {
  const { currentCompany } = useFounderStore();
  const companyId = currentCompany?.id;

  const { data: twinState, isLoading, isError, refetch } = useQuery<any>({
    queryKey: ["/api/companies", companyId, "twin", "state"],
    enabled: !!companyId,
    refetchInterval: 30000,
  });

  if (!companyId) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-muted-foreground">Select a company to view its Digital Twin</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-24" />)}
        </div>
        <Skeleton className="h-96" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-6 flex flex-col items-center justify-center gap-4">
        <AlertTriangle className="h-10 w-10 text-destructive" />
        <p className="text-muted-foreground">Failed to load Digital Twin data</p>
        <Button variant="outline" onClick={() => refetch()} data-testid="button-retry">
          <RefreshCw className="h-4 w-4 mr-2" /> Retry
        </Button>
      </div>
    );
  }

  const fin = twinState?.financials || {};
  const derived = twinState?.derived_metrics || {};
  const risks = twinState?.risk_indicators || [];
  const hasCriticalRisk = risks.some((r: any) => r.severity === "critical");

  return (
    <div className="p-6 space-y-6 max-w-[1400px] mx-auto" data-testid="digital-twin-page">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-primary/20 to-violet-500/20 flex items-center justify-center">
              <Cpu className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight" data-testid="text-twin-title">
                Digital Twin
              </h1>
              <p className="text-sm text-muted-foreground">
                {twinState?.company_name || "Company"} — Live virtual model
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {twinState?.snapshot_id && (
            <Badge variant="outline" className="font-mono text-[10px]" data-testid="badge-snapshot">
              Snapshot: {twinState.snapshot_id.slice(0, 8)}
            </Badge>
          )}
          <Button variant="outline" size="sm" onClick={() => refetch()} data-testid="button-refresh-twin">
            <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
            Refresh
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          label="Cash Balance"
          value={formatCurrency(fin.cash_balance)}
          icon={DollarSign}
          testId="metric-cash"
        />
        <MetricCard
          label="Monthly Burn"
          value={formatCurrency(fin.monthly_burn)}
          icon={TrendingDown}
          trend="down"
          testId="metric-burn"
        />
        <MetricCard
          label="Monthly Revenue"
          value={formatCurrency(fin.revenue_monthly)}
          icon={TrendingUp}
          trend={fin.revenue_growth_rate > 0 ? "up" : fin.revenue_growth_rate < 0 ? "down" : null}
          testId="metric-revenue"
        />
        <MetricCard
          label="Runway"
          value={derived.runway_months != null ? `${derived.runway_months} mo` : "N/A"}
          icon={Clock}
          trend={derived.runway_months != null && derived.runway_months < 6 ? "down" : null}
          testId="metric-runway"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="bg-card/50" data-testid="card-risk-indicators">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              {hasCriticalRisk ? (
                <AlertTriangle className="h-4 w-4 text-red-400" />
              ) : (
                <Shield className="h-4 w-4 text-emerald-400" />
              )}
              Risk Indicators
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {risks.map((r: any, i: number) => (
              <div key={i} className="flex items-center justify-between p-2 rounded-md bg-muted/20">
                <div className="flex items-center gap-2">
                  <RiskBadge severity={r.severity} />
                  <span className="text-sm">{r.message}</span>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="bg-card/50" data-testid="card-derived-metrics">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-primary" />
              Derived Metrics
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-3">
              {[
                // gross_margin and churn_rate are stored as percentages already
                // (twin seeds gross_margin=(1-cogs/rev)*100=72.3, churnRate=3.2),
                // so don't multiply by 100 again -- that produced 7230% / 320.0%.
                { label: "Gross Margin", value: derived.gross_margin != null ? `${derived.gross_margin.toFixed(0)}%` : "N/A" },
                { label: "Churn Rate", value: derived.churn_rate != null ? `${derived.churn_rate.toFixed(1)}%` : "N/A" },
                { label: "LTV", value: derived.ltv != null ? formatCurrency(derived.ltv) : "N/A" },
                { label: "CAC", value: derived.cac != null ? formatCurrency(derived.cac) : "N/A" },
                { label: "LTV/CAC", value: derived.ltv_cac_ratio != null ? `${derived.ltv_cac_ratio}x` : "N/A" },
                { label: "Headcount", value: derived.headcount != null ? formatNumber(derived.headcount) : "N/A" },
              ].map((m) => (
                <div key={m.label} className="p-2 rounded-md bg-muted/20">
                  <div className="text-[10px] text-muted-foreground uppercase tracking-wider">{m.label}</div>
                  <div className="text-sm font-bold font-mono mt-0.5">{m.value}</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card/50" data-testid="card-twin-health">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-primary" />
              Twin Status
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <TwinHealthScore health={twinState?.twin_health} />
            {twinState?.last_updated && (
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>Last Updated</span>
                <span className="font-mono">{new Date(twinState.last_updated).toLocaleString()}</span>
              </div>
            )}
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>History Depth</span>
              <span className="font-mono">{twinState?.financial_history?.length || 0} months</span>
            </div>
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>Recent Events</span>
              <span className="font-mono">{twinState?.recent_events?.length || 0}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="simulate" className="space-y-4">
        <TabsList data-testid="twin-tabs">
          <TabsTrigger value="simulate" data-testid="tab-simulate">
            <Zap className="h-3.5 w-3.5 mr-1.5" />
            Simulate
          </TabsTrigger>
          <TabsTrigger value="decisions" data-testid="tab-decisions">
            <Target className="h-3.5 w-3.5 mr-1.5" />
            Decisions
          </TabsTrigger>
          <TabsTrigger value="events" data-testid="tab-events">
            <Clock className="h-3.5 w-3.5 mr-1.5" />
            Events
          </TabsTrigger>
        </TabsList>

        <TabsContent value="simulate">
          <SimulationExplorer companyId={companyId} />
        </TabsContent>

        <TabsContent value="decisions">
          <DecisionTimeline companyId={companyId} />
        </TabsContent>

        <TabsContent value="events">
          <EventLog companyId={companyId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
