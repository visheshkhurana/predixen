import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TrendingUp } from "lucide-react";

// Monthly website traffic from the Google Analytics connector
// (GET /api/connectors/companies/{id}/web-traffic, filled at each sync).

interface TrafficMonth {
  period: string; // YYYY-MM
  sessions: number;
  users: number;
  new_users: number;
  key_events: number;
}

interface WebTraffic {
  connected: boolean;
  property_id: string | null;
  synced_at: string | null;
  months: TrafficMonth[];
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function monthLabel(period: string): string {
  const [y, m] = period.split("-");
  return `${MONTHS[Number(m) - 1] ?? m} ${y}`;
}

function n(v: number): string {
  return Math.round(v).toLocaleString();
}

function change(cur: number, prev: number | undefined): string | undefined {
  if (prev == null || prev === 0) return undefined;
  const pct = Math.round(((cur - prev) / prev) * 100);
  return `${pct > 0 ? "+" : ""}${pct}% vs previous month`;
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

export function WebTrafficCard({ companyId }: { companyId: number }) {
  const { data } = useQuery<WebTraffic>({
    queryKey: [`/api/connectors/companies/${companyId}/web-traffic`],
    enabled: !!companyId,
    staleTime: 60_000,
  });
  if (!data || !data.connected || data.months.length === 0) return null;

  const months = data.months;
  // The current month is partial; the tiles use the last full month when there is one.
  const thisMonth = new Date().toISOString().slice(0, 7);
  const full = months.filter((m) => m.period < thisMonth);
  const latest = full.length ? full[full.length - 1] : months[months.length - 1];
  const prev = full.length >= 2 ? full[full.length - 2] : undefined;
  const conv = latest.sessions ? (latest.key_events / latest.sessions) * 100 : null;
  const maxSessions = Math.max(1, ...months.map((m) => m.sessions));

  return (
    <Card data-testid="card-web-traffic">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-muted-foreground" />
          Website traffic
        </CardTitle>
        <CardDescription>
          From Google Analytics{data.property_id ? ` (property ${data.property_id})` : ""}, read-only. Key events are what GA4 counts as conversions, not revenue.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold">{monthLabel(latest.period)}</span>
          {latest.period === thisMonth && <Badge variant="outline" className="font-normal">month so far</Badge>}
        </div>
        <div className="grid gap-3 sm:grid-cols-4">
          <Tile testId="tile-sessions" label="Sessions" value={n(latest.sessions)} sub={change(latest.sessions, prev?.sessions)} />
          <Tile testId="tile-users" label="Users" value={n(latest.users)} sub={`${n(latest.new_users)} new`} />
          <Tile testId="tile-key-events" label="Key events" value={n(latest.key_events)} sub={change(latest.key_events, prev?.key_events)} />
          <Tile testId="tile-conversion" label="Key events per session" value={conv == null ? "—" : `${conv.toFixed(1)}%`} />
        </div>
        <div className="space-y-1.5" data-testid="web-traffic-months">
          {months.map((m) => (
            <div key={m.period} className="grid grid-cols-[6rem_1fr_auto] items-center gap-3 text-sm">
              <span>{monthLabel(m.period)}</span>
              <div className="h-2 rounded-full bg-muted overflow-hidden">
                <div className="h-full bg-primary" style={{ width: `${(m.sessions / maxSessions) * 100}%` }} />
              </div>
              <span className="tabular-nums text-xs text-muted-foreground">
                {n(m.sessions)} sessions · {n(m.users)} users · {n(m.key_events)} key events
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
