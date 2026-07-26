import { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import {
  BookOpen, Plus, Calendar, TrendingUp, TrendingDown, AlertTriangle,
  CheckCircle2, ArrowUpRight, ArrowDownRight, Minus, Clock, Target,
} from "lucide-react";
import { useFounderStore } from "@/store/founderStore";
import { useToast } from "@/hooks/use-toast";
import { apiRequest, queryClient } from "@/lib/queryClient";

interface JournalEntry {
  id: number;
  title: string;
  decision: string;
  reasoning: string;
  outcome?: string;
  status: "pending" | "resolved" | "revisit";
  date: string;
  impact: "high" | "medium" | "low";
}

interface ApiDecision {
  id: string;
  title: string;
  context: string | null;
  status: string;
  confidence: string;
  created_at: string | null;
  updated_at: string | null;
  implemented_at: string | null;
  metrics_snapshot_at_decision: Record<string, number> | null;
  metrics_snapshot_at_followup: Record<string, number> | null;
  outcome_recorded_at: string | null;
  outcome_delta_json: Record<string, MetricDelta> | null;
  outcome_rating: string | null;
  followup_days: number;
  tags?: string[];
}

interface MetricDelta {
  before: number;
  after: number;
  absolute_change: number;
  percent_change: number;
}

const demoEntries: JournalEntry[] = [
  {
    id: 1,
    title: "Expand to Enterprise Tier",
    decision: "Launch enterprise pricing tier at $499/mo with dedicated support",
    reasoning: "Top 5 customers requested SLAs and priority support. Enterprise deal pipeline shows 8 qualified leads worth $47K ARR.",
    outcome: "Closed 3 enterprise deals in first month, +$18K MRR",
    status: "resolved",
    date: "2026-01-15",
    impact: "high",
  },
  {
    id: 2,
    title: "Reduce CAC via Content Marketing",
    decision: "Shift 30% of paid ad budget to SEO content and webinars",
    reasoning: "CAC trending up to $1,800. Organic leads convert 2.3x better and have 40% lower churn. Content has 6-month compounding effect.",
    status: "pending",
    date: "2026-02-01",
    impact: "high",
  },
  {
    id: 3,
    title: "Hire Senior Backend Engineer",
    decision: "Prioritize hiring a senior backend engineer over a second sales rep",
    reasoning: "API reliability is at 99.2%, below target. Churn exit surveys cite performance issues. Engineering bottleneck blocks 3 feature releases.",
    outcome: "Hired in Feb. API uptime improved to 99.8%, unblocked Q2 roadmap.",
    status: "resolved",
    date: "2026-01-22",
    impact: "medium",
  },
  {
    id: 4,
    title: "Extend Runway Decision",
    decision: "Cut discretionary spend by 15% to extend runway from 18 to 21+ months",
    reasoning: "Fundraising market tightening. Current burn gives 18mo runway. Need buffer to hit Series A metrics without pressure.",
    status: "revisit",
    date: "2026-02-05",
    impact: "high",
  },
];

const statusConfig = {
  pending: { label: "In Progress", variant: "secondary" as const, icon: Calendar },
  resolved: { label: "Resolved", variant: "secondary" as const, icon: CheckCircle2 },
  revisit: { label: "Revisit", variant: "destructive" as const, icon: AlertTriangle },
};

const impactColors = {
  high: "text-red-400",
  medium: "text-amber-400",
  low: "text-emerald-400",
};

const STORAGE_KEY = "founderconsole-journal";

function loadEntries(companyId: number | null): JournalEntry[] {
  if (!companyId) return demoEntries;
  try {
    const raw = localStorage.getItem(`${STORAGE_KEY}-${companyId}`);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0) return parsed;
    }
  } catch {}
  return demoEntries;
}

function saveEntries(companyId: number | null, entries: JournalEntry[]) {
  if (!companyId) return;
  localStorage.setItem(`${STORAGE_KEY}-${companyId}`, JSON.stringify(entries));
}

const METRIC_LABELS: Record<string, string> = {
  mrr: "MRR",
  monthly_burn: "Monthly Burn",
  cash_balance: "Cash Balance",
  runway_months: "Runway",
  churn_rate: "Churn Rate",
  growth_rate: "Growth Rate",
  headcount: "Headcount",
  customers: "Customers",
};

const METRIC_FORMAT: Record<string, (v: number) => string> = {
  mrr: (v) => `$${v >= 1000 ? (v / 1000).toFixed(1) + "K" : v.toFixed(0)}`,
  monthly_burn: (v) => `$${v >= 1000 ? (v / 1000).toFixed(1) + "K" : v.toFixed(0)}`,
  cash_balance: (v) => `$${v >= 1e6 ? (v / 1e6).toFixed(1) + "M" : v >= 1000 ? (v / 1000).toFixed(0) + "K" : v.toFixed(0)}`,
  runway_months: (v) => `${v.toFixed(1)} mo`,
  churn_rate: (v) => `${(v * 100).toFixed(1)}%`,
  growth_rate: (v) => `${(v * 100).toFixed(1)}%`,
  headcount: (v) => v.toFixed(0),
  customers: (v) => v.toFixed(0),
};

function formatMetric(key: string, value: number): string {
  const formatter = METRIC_FORMAT[key];
  return formatter ? formatter(value) : value.toFixed(2);
}

const BURN_LOWER_IS_BETTER = new Set(["monthly_burn", "churn_rate"]);

function isPositiveChange(key: string, pctChange: number): boolean {
  if (BURN_LOWER_IS_BETTER.has(key)) return pctChange < 0;
  return pctChange > 0;
}

function OutcomeRatingBadge({ rating }: { rating: string }) {
  const config: Record<string, { label: string; className: string }> = {
    positive: { label: "Positive Outcome", className: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30" },
    neutral: { label: "Neutral Outcome", className: "bg-amber-500/15 text-amber-400 border-amber-500/30" },
    negative: { label: "Negative Outcome", className: "bg-red-500/15 text-red-400 border-red-500/30" },
  };
  const c = config[rating] || config.neutral;
  return (
    <Badge variant="outline" className={`text-[10px] ${c.className}`} data-testid={`badge-outcome-${rating}`}>
      {rating === "positive" ? <ArrowUpRight className="h-3 w-3 mr-0.5" /> :
       rating === "negative" ? <ArrowDownRight className="h-3 w-3 mr-0.5" /> :
       <Minus className="h-3 w-3 mr-0.5" />}
      {c.label}
    </Badge>
  );
}

function OutcomeTrackingCard({ decision, onUpdateFollowupDays }: { decision: ApiDecision; onUpdateFollowupDays?: (days: number) => void }) {
  const hasOutcome = !!decision.outcome_recorded_at;
  const isImplemented = decision.status === "implemented";
  const hasSnapshot = !!decision.metrics_snapshot_at_decision;

  if (!isImplemented || !hasSnapshot) return null;

  if (!hasOutcome && decision.implemented_at) {
    const implDate = new Date(decision.implemented_at);
    const followupDays = decision.followup_days || 60;
    const now = new Date();
    const elapsed = Math.floor((now.getTime() - implDate.getTime()) / (1000 * 60 * 60 * 24));
    const remaining = Math.max(0, followupDays - elapsed);
    const progress = Math.min(100, (elapsed / followupDays) * 100);

    return (
      <div className="mt-3 p-3 rounded-lg bg-primary/5 border border-primary/10" data-testid="outcome-tracking-pending">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Clock className="h-3.5 w-3.5 text-primary" />
            <span className="text-xs font-medium text-primary">Outcome Tracking In Progress</span>
          </div>
          {onUpdateFollowupDays && (
            <Select
              value={String(followupDays)}
              onValueChange={(val) => onUpdateFollowupDays(Number(val))}
            >
              <SelectTrigger className="h-6 w-[90px] text-[10px]" data-testid="select-followup-days">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="30">30 days</SelectItem>
                <SelectItem value="60">60 days</SelectItem>
                <SelectItem value="90">90 days</SelectItem>
                <SelectItem value="180">180 days</SelectItem>
              </SelectContent>
            </Select>
          )}
        </div>
        <div className="flex items-center gap-2 mb-1.5">
          <div className="flex-1 h-1.5 rounded-full bg-secondary overflow-hidden">
            <div
              className="h-full rounded-full bg-primary transition-all"
              style={{ width: `${progress}%` }}
              data-testid="progress-bar-outcome"
            />
          </div>
          <span className="text-[10px] text-muted-foreground font-mono">{Math.round(progress)}%</span>
        </div>
        <p className="text-[11px] text-muted-foreground">
          Results in {remaining} day{remaining !== 1 ? "s" : ""} ({followupDays}-day tracking window)
        </p>
      </div>
    );
  }

  if (hasOutcome) {
    const deltas = decision.outcome_delta_json || {};
    const metricsEntries = Object.entries(deltas).filter(
      ([, v]) => v && typeof v === "object" && "before" in v
    );

    return (
      <div className="mt-3 p-3 rounded-lg bg-secondary/50 border border-border" data-testid="outcome-tracking-complete">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Target className="h-3.5 w-3.5 text-emerald-500" />
            <span className="text-xs font-medium">Decision Outcome</span>
          </div>
          {decision.outcome_rating && <OutcomeRatingBadge rating={decision.outcome_rating} />}
        </div>
        {metricsEntries.length > 0 ? (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-2">
            {metricsEntries.map(([key, delta]) => {
              const d = delta as MetricDelta;
              const positive = isPositiveChange(key, d.percent_change);
              return (
                <div key={key} className="p-2 rounded bg-background/50" data-testid={`metric-delta-${key}`}>
                  <p className="text-[10px] text-muted-foreground mb-0.5">{METRIC_LABELS[key] || key}</p>
                  <div className="flex items-center gap-1">
                    <span className="text-xs font-mono text-muted-foreground">{formatMetric(key, d.before)}</span>
                    <ArrowUpRight className={`h-3 w-3 ${positive ? "text-emerald-500" : "text-red-400"} ${!positive ? "rotate-90" : ""}`} />
                    <span className={`text-xs font-mono font-medium ${positive ? "text-emerald-500" : "text-red-400"}`}>
                      {formatMetric(key, d.after)}
                    </span>
                  </div>
                  <p className={`text-[10px] font-mono ${positive ? "text-emerald-500" : "text-red-400"}`}>
                    {d.percent_change >= 0 ? "+" : ""}{d.percent_change.toFixed(1)}%
                  </p>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground mt-1">Outcome recorded but no metric changes were detected.</p>
        )}
      </div>
    );
  }

  return null;
}

export default function JournalPage() {
  const { currentCompany } = useFounderStore();
  const { toast } = useToast();
  const [entries, setEntries] = useState<JournalEntry[]>(() => loadEntries(currentCompany?.id ?? null));
  const [dialogOpen, setDialogOpen] = useState(false);
  const [expandedDecision, setExpandedDecision] = useState<string | null>(null);
  const [newTitle, setNewTitle] = useState("");
  const [newDecision, setNewDecision] = useState("");
  const [newReasoning, setNewReasoning] = useState("");
  const [newImpact, setNewImpact] = useState<"high" | "medium" | "low">("medium");

  const companyId = currentCompany?.id;

  const { data: apiResponse, isLoading: isLoadingDecisions } = useQuery<{ items: ApiDecision[]; total: number }>({
    queryKey: [`/api/companies/${companyId}/decisions?page_size=200`],
    enabled: !!companyId,
  });

  const updateFollowupMutation = useMutation({
    mutationFn: async ({ decisionId, followupDays }: { decisionId: string; followupDays: number }) => {
      await apiRequest("PATCH", `/api/companies/${companyId}/decisions/${decisionId}`, {
        followup_days: followupDays,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [`/api/companies/${companyId}/decisions?page_size=200`] });
      toast({ title: "Updated", description: "Follow-up tracking period updated." });
    },
  });

  const apiDecisions = apiResponse?.items || [];

  const implementedDecisions = (apiDecisions).filter(
    (d) => d.status === "implemented" && d.metrics_snapshot_at_decision
  );

  // Decisions that have been captured (e.g. via "Track as Decision" from
  // Competition, Copilot, etc.) but not yet marked implemented. Without this
  // list they'd have no home in the UI — the outcome-tracking section only
  // shows implemented ones.
  const trackedDecisions = (apiDecisions).filter((d) => d.status !== "implemented");

  const implementMutation = useMutation({
    mutationFn: async (decisionId: string) => {
      await apiRequest("PATCH", `/api/companies/${companyId}/decisions/${decisionId}`, {
        status: "implemented",
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [`/api/companies/${companyId}/decisions?page_size=200`] });
      toast({ title: "Marked as implemented", description: "Now tracking its outcome over time." });
    },
  });

  const outcomeStats = {
    tracked: implementedDecisions.length,
    completed: implementedDecisions.filter((d) => d.outcome_recorded_at).length,
    positive: implementedDecisions.filter((d) => d.outcome_rating === "positive").length,
    negative: implementedDecisions.filter((d) => d.outcome_rating === "negative").length,
  };

  useEffect(() => {
    setEntries(loadEntries(currentCompany?.id ?? null));
  }, [currentCompany?.id]);

  const handleCreate = () => {
    if (!newTitle.trim() || !newDecision.trim()) {
      toast({ title: "Missing fields", description: "Title and decision are required.", variant: "destructive" });
      return;
    }

    const entry: JournalEntry = {
      id: Date.now(),
      title: newTitle.trim(),
      decision: newDecision.trim(),
      reasoning: newReasoning.trim(),
      status: "pending",
      date: new Date().toISOString().split("T")[0],
      impact: newImpact,
    };

    const updated = [entry, ...entries];
    setEntries(updated);
    saveEntries(currentCompany?.id ?? null, updated);
    setDialogOpen(false);
    setNewTitle("");
    setNewDecision("");
    setNewReasoning("");
    setNewImpact("medium");
    toast({ title: "Entry added", description: "Your decision has been recorded." });
  };

  return (
    <div className="p-4 md:p-6 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2" data-testid="text-journal-title">
            <BookOpen className="h-6 w-6 text-primary" />
            Decision Journal
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Track decisions, reasoning, and outcomes to improve decision quality over time.
          </p>
        </div>
        <Button onClick={() => setDialogOpen(true)} data-testid="button-new-entry">
          <Plus className="h-4 w-4 mr-2" />
          New Entry
        </Button>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <Card>
          <CardContent className="pt-4 pb-3 text-center">
            <p className="text-2xl font-bold font-mono" data-testid="text-total-decisions">{entries.length}</p>
            <p className="text-xs text-muted-foreground">Total Decisions</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-3 text-center">
            <p className="text-2xl font-bold font-mono text-emerald-500" data-testid="text-resolved-count">
              {entries.filter(e => e.status === "resolved").length}
            </p>
            <p className="text-xs text-muted-foreground">Resolved</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-3 text-center">
            <p className="text-2xl font-bold font-mono text-amber-500" data-testid="text-pending-count">
              {entries.filter(e => e.status === "pending" || e.status === "revisit").length}
            </p>
            <p className="text-xs text-muted-foreground">Open</p>
          </CardContent>
        </Card>
      </div>

      {outcomeStats.tracked > 0 && (
        <Card data-testid="card-outcome-summary">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-3">
              <Target className="h-4 w-4 text-primary" />
              <span className="text-sm font-semibold">Outcome Tracking Summary</span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="text-center p-2 rounded bg-secondary/30">
                <p className="text-lg font-bold font-mono" data-testid="text-tracked-count">{outcomeStats.tracked}</p>
                <p className="text-[10px] text-muted-foreground">Tracked</p>
              </div>
              <div className="text-center p-2 rounded bg-secondary/30">
                <p className="text-lg font-bold font-mono" data-testid="text-completed-outcomes">{outcomeStats.completed}</p>
                <p className="text-[10px] text-muted-foreground">Outcomes Recorded</p>
              </div>
              <div className="text-center p-2 rounded bg-emerald-500/10">
                <p className="text-lg font-bold font-mono text-emerald-500" data-testid="text-positive-outcomes">{outcomeStats.positive}</p>
                <p className="text-[10px] text-muted-foreground">Positive</p>
              </div>
              <div className="text-center p-2 rounded bg-red-500/10">
                <p className="text-lg font-bold font-mono text-red-400" data-testid="text-negative-outcomes">{outcomeStats.negative}</p>
                <p className="text-[10px] text-muted-foreground">Negative</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {isLoadingDecisions && companyId && (
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-sm text-muted-foreground" data-testid="text-loading-outcomes">Loading outcome tracking data...</p>
          </CardContent>
        </Card>
      )}

      {trackedDecisions.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider" data-testid="text-captured-decisions-header">
            Tracked Decisions
          </h2>
          {trackedDecisions.map((decision) => (
            <Card key={decision.id} className="hover-elevate" data-testid={`card-captured-decision-${decision.id}`}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-4 flex-wrap">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <h3 className="font-semibold text-sm" data-testid={`text-captured-title-${decision.id}`}>{decision.title}</h3>
                      <Badge variant="outline" className="text-[10px] capitalize">{decision.status}</Badge>
                      {decision.confidence && (
                        <Badge variant="secondary" className="text-[10px] capitalize">{decision.confidence} confidence</Badge>
                      )}
                      {(decision.tags || []).slice(0, 3).map((tag) => (
                        <Badge key={tag} variant="outline" className="text-[10px] bg-primary/5 text-primary/80 border-primary/20">{tag}</Badge>
                      ))}
                    </div>
                    {decision.context && (
                      <p className="text-xs text-muted-foreground leading-relaxed mb-1 whitespace-pre-line">{decision.context}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-[11px] text-muted-foreground font-mono">
                      {decision.created_at
                        ? new Date(decision.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })
                        : ""}
                    </span>
                    <Button
                      size="sm"
                      variant="outline"
                      className="text-[11px] h-7"
                      disabled={implementMutation.isPending}
                      onClick={() => implementMutation.mutate(decision.id)}
                      data-testid={`button-implement-${decision.id}`}
                    >
                      <CheckCircle2 className="h-3 w-3 mr-1" />
                      Mark Implemented
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {implementedDecisions.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider" data-testid="text-tracked-decisions-header">
            Decisions with Outcome Tracking
          </h2>
          {implementedDecisions.map((decision) => (
            <Card
              key={decision.id}
              className="hover-elevate cursor-pointer"
              data-testid={`card-tracked-decision-${decision.id}`}
              onClick={() => setExpandedDecision(expandedDecision === decision.id ? null : decision.id)}
            >
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-4 flex-wrap">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <h3 className="font-semibold text-sm" data-testid={`text-tracked-title-${decision.id}`}>{decision.title}</h3>
                      <Badge variant="secondary" className="text-[10px]">
                        <CheckCircle2 className="h-3 w-3 mr-1" />
                        Implemented
                      </Badge>
                      {decision.outcome_rating && <OutcomeRatingBadge rating={decision.outcome_rating} />}
                      {!decision.outcome_recorded_at && decision.implemented_at && (
                        <Badge variant="outline" className="text-[10px] bg-primary/10 text-primary border-primary/20">
                          <Clock className="h-3 w-3 mr-0.5" />
                          Tracking
                        </Badge>
                      )}
                    </div>
                    {decision.context && (
                      <p className="text-xs text-muted-foreground leading-relaxed mb-1">{decision.context}</p>
                    )}
                  </div>
                  <span className="text-[11px] text-muted-foreground shrink-0 font-mono">
                    {decision.implemented_at
                      ? new Date(decision.implemented_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })
                      : ""}
                  </span>
                </div>
                {expandedDecision === decision.id && (
                  <OutcomeTrackingCard
                    decision={decision}
                    onUpdateFollowupDays={(days) =>
                      updateFollowupMutation.mutate({ decisionId: decision.id, followupDays: days })
                    }
                  />
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
          Journal Entries
        </h2>
        {entries.map((entry) => {
          const config = statusConfig[entry.status];
          const StatusIcon = config.icon;
          return (
            <Card key={entry.id} className="hover-elevate cursor-pointer" data-testid={`card-journal-${entry.id}`}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-4 flex-wrap">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <h3 className="font-semibold text-sm" data-testid={`text-journal-title-${entry.id}`}>{entry.title}</h3>
                      <Badge variant={config.variant} className="text-[10px]" data-testid={`badge-journal-status-${entry.id}`}>
                        <StatusIcon className="h-3 w-3 mr-1" />
                        {config.label}
                      </Badge>
                      <span className={`text-[10px] font-medium ${impactColors[entry.impact]}`} data-testid={`text-journal-impact-${entry.id}`}>
                        <TrendingUp className="h-3 w-3 inline mr-0.5" />
                        {entry.impact.charAt(0).toUpperCase() + entry.impact.slice(1)} Impact
                      </span>
                    </div>
                    <p className="text-sm text-foreground/90 mb-1.5" data-testid={`text-journal-decision-${entry.id}`}>{entry.decision}</p>
                    <p className="text-xs text-muted-foreground leading-relaxed">{entry.reasoning}</p>
                    {entry.outcome && (
                      <div className="mt-2 flex items-start gap-1.5">
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 mt-0.5 shrink-0" />
                        <p className="text-xs text-emerald-500/90" data-testid={`text-journal-outcome-${entry.id}`}>{entry.outcome}</p>
                      </div>
                    )}
                  </div>
                  <span className="text-[11px] text-muted-foreground shrink-0 font-mono">
                    {new Date(entry.date).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                  </span>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-lg" data-testid="dialog-new-entry">
          <DialogHeader>
            <DialogTitle>New Decision Entry</DialogTitle>
            <DialogDescription>Record a decision, your reasoning, and its expected impact.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 pt-2">
            <div className="space-y-2">
              <Label htmlFor="entry-title">Title</Label>
              <Input
                id="entry-title"
                placeholder="e.g. Hire a second engineer"
                value={newTitle}
                onChange={e => setNewTitle(e.target.value)}
                data-testid="input-entry-title"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="entry-decision">Decision</Label>
              <Textarea
                id="entry-decision"
                placeholder="What did you decide?"
                value={newDecision}
                onChange={e => setNewDecision(e.target.value)}
                className="min-h-[80px]"
                data-testid="input-entry-decision"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="entry-reasoning">Reasoning</Label>
              <Textarea
                id="entry-reasoning"
                placeholder="Why did you make this decision?"
                value={newReasoning}
                onChange={e => setNewReasoning(e.target.value)}
                className="min-h-[80px]"
                data-testid="input-entry-reasoning"
              />
            </div>
            <div className="space-y-2">
              <Label>Impact Level</Label>
              <Select value={newImpact} onValueChange={(v) => setNewImpact(v as "high" | "medium" | "low")}>
                <SelectTrigger data-testid="select-entry-impact">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="high">High Impact</SelectItem>
                  <SelectItem value="medium">Medium Impact</SelectItem>
                  <SelectItem value="low">Low Impact</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button onClick={handleCreate} className="w-full" data-testid="button-submit-entry">
              Save Entry
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
