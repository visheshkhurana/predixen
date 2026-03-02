import { useState, useMemo } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Flag, Plus, Target, TrendingUp, Clock, CheckCircle2 } from "lucide-react";
import { useFounderStore } from "@/store/founderStore";
import { useFinancialMetrics } from "@/hooks/useFinancialMetrics";
import { computeCoreMetrics, resolveGoalMetric, deriveGoalStatus, formatMetricValue } from "@/lib/computeMetrics";

interface Goal {
  id: number;
  title: string;
  description: string;
  metric: string;
  current: number;
  target: number;
  unit: string;
  prefix?: string;
  deadline: string;
  status: "on_track" | "at_risk" | "behind" | "completed";
  category: "growth" | "efficiency" | "fundraising";
}

const defaultGoals: Goal[] = [
  {
    id: 1,
    title: "Hit $50K MRR",
    description: "Reach $50K monthly recurring revenue before Series A raise",
    metric: "MRR",
    current: 0,
    target: 50000,
    prefix: "$",
    unit: "",
    deadline: "2026-06-30",
    status: "on_track",
    category: "growth",
  },
  {
    id: 2,
    title: "Reduce CAC to $1,200",
    description: "Lower customer acquisition cost through organic channels",
    metric: "CAC",
    current: 0,
    target: 1200,
    prefix: "$",
    unit: "",
    deadline: "2026-05-31",
    status: "at_risk",
    category: "efficiency",
  },
  {
    id: 3,
    title: "25+ Active Customers",
    description: "Expand customer base with focus on mid-market SaaS",
    metric: "Customers",
    current: 0,
    target: 25,
    unit: "",
    deadline: "2026-04-30",
    status: "on_track",
    category: "growth",
  },
  {
    id: 4,
    title: "Extend Runway to 24 Months",
    description: "Maintain runway buffer for fundraising optionality",
    metric: "Runway",
    current: 0,
    target: 24,
    unit: " mo",
    deadline: "2026-06-30",
    status: "at_risk",
    category: "efficiency",
  },
  {
    id: 5,
    title: "Close Series A at $3M",
    description: "Raise Series A with target $3M at $15M pre-money valuation",
    metric: "Raised",
    current: 0,
    target: 3000000,
    prefix: "$",
    unit: "",
    deadline: "2026-09-30",
    status: "behind",
    category: "fundraising",
  },
  {
    id: 6,
    title: "LTV:CAC Above 4x",
    description: "Improve unit economics to investor-grade levels",
    metric: "LTV:CAC",
    current: 0,
    target: 4.0,
    unit: "x",
    deadline: "2026-06-30",
    status: "on_track",
    category: "efficiency",
  },
];

const statusConfig = {
  on_track: { label: "On Track", className: "bg-emerald-500/15 text-emerald-500" },
  at_risk: { label: "At Risk", className: "bg-amber-500/15 text-amber-500" },
  behind: { label: "Behind", className: "bg-red-500/15 text-red-500" },
  completed: { label: "Completed", className: "bg-primary/15 text-primary" },
};

const categoryLabels = {
  growth: "Growth",
  efficiency: "Efficiency",
  fundraising: "Fundraising",
};

const INVERSE_METRICS = new Set(["CAC", "Churn Rate"]);

export default function GoalsPage() {
  const { currentCompany } = useFounderStore();
  const { metrics: rawMetrics, isLoading } = useFinancialMetrics();
  const computed = useMemo(() => computeCoreMetrics(rawMetrics), [rawMetrics]);
  const [filter, setFilter] = useState<string>("all");

  const enrichedGoals = useMemo(() => {
    return defaultGoals.map((goal) => {
      const liveValue = resolveGoalMetric(goal.metric, computed);
      const current = liveValue !== null && computed.hasData ? liveValue : goal.current;
      const isInverse = INVERSE_METRICS.has(goal.metric);
      const status = computed.hasData
        ? deriveGoalStatus(current, goal.target, goal.deadline, isInverse)
        : goal.status;
      return { ...goal, current, status };
    });
  }, [computed]);

  const filteredGoals = filter === "all" ? enrichedGoals : enrichedGoals.filter(g => g.category === filter);
  const onTrackCount = enrichedGoals.filter(g => g.status === "on_track" || g.status === "completed").length;

  if (isLoading) {
    return (
      <div className="p-4 md:p-6 max-w-4xl mx-auto space-y-6">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2" data-testid="text-goals-title">
              <Flag className="h-6 w-6 text-primary" />
              Goals
            </h1>
            <p className="text-sm text-muted-foreground mt-1">Loading your goal metrics...</p>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-3">
          {[1, 2, 3].map(i => (
            <Card key={i}><CardContent className="pt-4 pb-3"><Skeleton className="h-8 w-16 mx-auto mb-1" /><Skeleton className="h-3 w-20 mx-auto" /></CardContent></Card>
          ))}
        </div>
        <div className="space-y-3">
          {[1, 2, 3, 4].map(i => (
            <Card key={i}><CardContent className="p-4"><Skeleton className="h-4 w-48 mb-2" /><Skeleton className="h-3 w-full mb-3" /><Skeleton className="h-1.5 w-full" /></CardContent></Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2" data-testid="text-goals-title">
            <Flag className="h-6 w-6 text-primary" />
            Goals
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            {computed.hasData
              ? "Track progress against your key milestones using live data."
              : "Set targets, track progress, and stay accountable to your key milestones."}
          </p>
        </div>
        <Button data-testid="button-new-goal">
          <Plus className="h-4 w-4 mr-2" />
          New Goal
        </Button>
      </div>

      {!computed.hasData && (
        <div className="rounded-md border border-amber-500/30 bg-amber-500/5 px-4 py-3 text-sm text-amber-500" data-testid="banner-demo-data">
          Showing sample goals. Add financial data to see live metrics here.
        </div>
      )}

      <div className="grid grid-cols-3 gap-3">
        <Card>
          <CardContent className="pt-4 pb-3 text-center">
            <p className="text-2xl font-bold font-mono" data-testid="text-total-goals">{enrichedGoals.length}</p>
            <p className="text-xs text-muted-foreground">Active Goals</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-3 text-center">
            <p className="text-2xl font-bold font-mono text-emerald-500" data-testid="text-on-track-count">{onTrackCount}</p>
            <p className="text-xs text-muted-foreground">On Track</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-3 text-center">
            <p className="text-2xl font-bold font-mono text-amber-500" data-testid="text-at-risk-count">
              {enrichedGoals.filter(g => g.status === "at_risk" || g.status === "behind").length}
            </p>
            <p className="text-xs text-muted-foreground">Needs Attention</p>
          </CardContent>
        </Card>
      </div>

      <div className="flex items-center gap-2">
        {["all", "growth", "efficiency", "fundraising"].map((cat) => (
          <Button
            key={cat}
            variant={filter === cat ? "default" : "outline"}
            size="sm"
            onClick={() => setFilter(cat)}
            data-testid={`button-filter-${cat}`}
          >
            {cat === "all" ? "All" : categoryLabels[cat as keyof typeof categoryLabels]}
          </Button>
        ))}
      </div>

      <div className="space-y-3">
        {filteredGoals.map((goal) => {
          const config = statusConfig[goal.status];
          const isInverse = INVERSE_METRICS.has(goal.metric);
          const progress = isInverse
            ? Math.min(100, Math.round(((goal.target / (goal.current || 1)) * 100)))
            : Math.min(100, Math.round((goal.current / goal.target) * 100));
          const daysLeft = Math.max(0, Math.ceil((new Date(goal.deadline).getTime() - Date.now()) / (1000 * 60 * 60 * 24)));

          return (
            <Card key={goal.id} className="hover-elevate cursor-pointer" data-testid={`card-goal-${goal.id}`}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-4 mb-3 flex-wrap">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                      <h3 className="font-semibold text-sm" data-testid={`text-goal-title-${goal.id}`}>{goal.title}</h3>
                      <Badge className={`text-[10px] border-0 ${config.className}`} data-testid={`badge-goal-status-${goal.id}`}>
                        {config.label}
                      </Badge>
                      {computed.hasData && resolveGoalMetric(goal.metric, computed) !== null && (
                        <Badge variant="outline" className="text-[9px] px-1 py-0 border-primary/30 text-primary/70" data-testid={`badge-live-${goal.id}`}>
                          Live
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground">{goal.description}</p>
                  </div>
                  <div className="flex items-center gap-1 text-[11px] text-muted-foreground shrink-0">
                    <Clock className="h-3 w-3" />
                    <span className="font-mono">{daysLeft}d left</span>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-2 text-xs">
                    <span className="text-muted-foreground">{goal.metric}</span>
                    <span className="font-mono font-medium" data-testid={`text-goal-progress-${goal.id}`}>
                      {formatMetricValue(goal.current, goal.prefix, goal.unit)}
                      <span className="text-muted-foreground mx-1">/</span>
                      {formatMetricValue(goal.target, goal.prefix, goal.unit)}
                    </span>
                  </div>
                  <Progress
                    value={progress}
                    className={`h-1.5 ${
                      goal.status === "on_track" || goal.status === "completed"
                        ? "[&>div]:bg-emerald-500"
                        : goal.status === "at_risk"
                        ? "[&>div]:bg-amber-500"
                        : "[&>div]:bg-red-500"
                    }`}
                  />
                  <div className="flex items-center justify-between gap-2 text-[11px] text-muted-foreground">
                    <span data-testid={`text-goal-percent-${goal.id}`}>{progress}% complete</span>
                    <span data-testid={`text-goal-deadline-${goal.id}`}>Due {new Date(goal.deadline).toLocaleDateString("en-US", { month: "short", year: "numeric" })}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
