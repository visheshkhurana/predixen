import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatCurrencyAbbrev } from "@/lib/utils";
import { Briefcase, AlertTriangle } from "lucide-react";

// Pipeline snapshots from CRM connectors (server/services/crm_pipeline.py).

interface Stage { stage: string; count: number; value: number }

interface CrmSnapshot {
  source: string;
  snapshot_date: string;
  currency: string | null;
  open_count: number;
  open_value: number;
  weighted_value: number | null;
  won_count_30d: number;
  won_value_30d: number;
  lost_count_30d: number;
  win_rate_90d: number | null;
  avg_won_deal_90d: number | null;
  deals_read: number;
  truncated: boolean;
  stages: Stage[];
  other_currencies: Record<string, { count: number; value: number }>;
  trend: { date: string; open_value: number; open_count: number }[];
}

const LABELS: Record<string, string> = {
  hubspot: "HubSpot",
  pipedrive: "Pipedrive",
  zoho_crm: "Zoho CRM",
  salesforce: "Salesforce",
  close_crm: "Close",
};

function money(v: number | null | undefined, currency: string): string {
  if (v == null) return "—";
  try {
    return formatCurrencyAbbrev(v, currency);
  } catch {
    return `${currency} ${Math.round(v).toLocaleString()}`;
  }
}

function Tile({ label, value, sub, testId }: { label: string; value: string; sub?: string; testId: string }) {
  return (
    <div className="rounded-md border p-3" data-testid={testId}>
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-xl font-semibold tabular-nums">{value}</div>
      {sub && <div className="text-xs text-muted-foreground">{sub}</div>}
    </div>
  );
}

function trendNote(s: CrmSnapshot, currency: string): string | null {
  if (s.trend.length < 2) return null;
  const first = s.trend[0];
  const delta = s.open_value - first.open_value;
  if (Math.abs(delta) < 0.005) return `Open pipeline unchanged since ${first.date}`;
  return `${delta > 0 ? "Up" : "Down"} ${money(Math.abs(delta), currency)} since ${first.date}`;
}

function CrmBlock({ s }: { s: CrmSnapshot }) {
  const currency = s.currency || "USD";
  const maxStage = Math.max(1, ...s.stages.map((st) => st.value));
  const other = Object.entries(s.other_currencies || {});
  const note = trendNote(s, currency);
  return (
    <div className="space-y-4" data-testid={`crm-pipeline-${s.source}`}>
      <div className="flex items-center gap-2">
        <span className="text-sm font-semibold">{LABELS[s.source] || s.source}</span>
        <Badge variant="outline" className="font-normal">as of {s.snapshot_date}</Badge>
      </div>
      <div className="grid gap-3 sm:grid-cols-4">
        <Tile testId="tile-open-pipeline" label="Open pipeline" value={money(s.open_value, currency)} sub={`${s.open_count} open ${s.open_count === 1 ? "deal" : "deals"}`} />
        <Tile testId="tile-weighted-pipeline" label="Weighted by stage" value={money(s.weighted_value, currency)} />
        <Tile testId="tile-won-30d" label="Won, last 30 days" value={money(s.won_value_30d, currency)} sub={`${s.won_count_30d} won · ${s.lost_count_30d} lost`} />
        <Tile
          testId="tile-win-rate"
          label="Win rate, 90 days"
          value={s.win_rate_90d == null ? "—" : `${Math.round(s.win_rate_90d * 100)}%`}
          sub={s.avg_won_deal_90d != null ? `avg won deal ${money(s.avg_won_deal_90d, currency)}` : undefined}
        />
      </div>
      {note && <p className="text-xs text-muted-foreground">{note}</p>}
      {s.stages.length > 0 && (
        <div className="space-y-1.5">
          {s.stages.slice(0, 8).map((st) => (
            <div key={st.stage} className="grid grid-cols-[minmax(0,10rem)_1fr_auto] items-center gap-3 text-sm">
              <span className="truncate" title={st.stage}>{st.stage}</span>
              <div className="h-2 rounded-full bg-muted overflow-hidden">
                <div className="h-full bg-primary" style={{ width: `${(st.value / maxStage) * 100}%` }} />
              </div>
              <span className="tabular-nums text-xs text-muted-foreground">{money(st.value, currency)} · {st.count}</span>
            </div>
          ))}
        </div>
      )}
      {(s.truncated || other.length > 0) && (
        <div className="flex items-start gap-2 rounded-md border border-destructive/40 p-3 text-xs">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
          <span>
            {s.truncated && `Read the first ${s.deals_read.toLocaleString()} deals only, so totals may be low. `}
            {other.length > 0 &&
              `${other.map(([cur, b]) => `${b.count} ${cur} ${b.count === 1 ? "deal" : "deals"} (${money(b.value, cur)})`).join(", ")} not added to ${currency} totals.`}
          </span>
        </div>
      )}
    </div>
  );
}

export function CrmPipelineCard({ companyId }: { companyId: number }) {
  const { data } = useQuery<{ crms: CrmSnapshot[] }>({
    queryKey: [`/api/connectors/companies/${companyId}/crm-pipeline`],
    enabled: !!companyId,
    staleTime: 60_000,
  });
  if (!data || data.crms.length === 0) return null;
  return (
    <Card data-testid="card-crm-pipeline">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Briefcase className="h-5 w-5 text-muted-foreground" />
          Sales pipeline
        </CardTitle>
        <CardDescription>
          From your CRM at the last sync. Pipeline is what's open, not booked revenue; each sync adds a point to the trend.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {data.crms.map((s) => <CrmBlock key={s.source} s={s} />)}
      </CardContent>
    </Card>
  );
}
