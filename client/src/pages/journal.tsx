import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { BookOpen, Plus, Calendar, TrendingUp, AlertTriangle, CheckCircle2 } from "lucide-react";
import { useFounderStore } from "@/store/founderStore";

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

export default function JournalPage() {
  const { currentCompany } = useFounderStore();
  const [entries] = useState<JournalEntry[]>(demoEntries);

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
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
        <Button data-testid="button-new-entry">
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

      <div className="space-y-3">
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
    </div>
  );
}
