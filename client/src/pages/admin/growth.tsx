import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  TrendingUp, Users, Rocket, Activity, Target, Calendar,
} from "lucide-react";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  AreaChart, Area, Legend,
} from "recharts";

interface FunnelData {
  summary: {
    total_users: number;
    signups_7d: number;
    signups_30d: number;
    active_7d: number;
    active_30d: number;
    sim_runs_total: number;
    sim_runs_7d: number;
    sim_runs_30d: number;
  };
  rates: {
    sim_to_signup_pct: number;
    signup_to_active_pct: number;
    activation_pct: number;
  };
  funnel: { stage: string; count: number }[];
}

interface TimeseriesPoint { day: string; signups: number; sims: number; active: number; }
interface Cohort { cohort_week: string; cohort_size: number; w1_pct: number; w2_pct: number; w3_pct: number; }

function StatCard({
  title, value, sub, icon: Icon, isLoading,
}: {
  title: string; value: string | number; sub?: string; icon: any; isLoading: boolean;
}) {
  return (
    <Card data-testid={`growth-stat-${title.toLowerCase().replace(/\s/g, "-")}`}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        <Icon className="h-4 w-4 text-primary" />
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-8 w-24" />
        ) : (
          <>
            <div className="text-2xl font-bold" data-testid={`growth-stat-value-${title.toLowerCase().replace(/\s/g, "-")}`}>
              {value}
            </div>
            {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
          </>
        )}
      </CardContent>
    </Card>
  );
}

function retentionColor(pct: number) {
  if (pct >= 50) return "bg-emerald-600/30 text-emerald-200";
  if (pct >= 25) return "bg-amber-600/30 text-amber-200";
  if (pct > 0) return "bg-zinc-700/40 text-zinc-200";
  return "bg-zinc-800/40 text-zinc-500";
}

export default function AdminGrowth() {
  const funnelQ = useQuery<FunnelData>({ queryKey: ["/api/admin/growth/funnel"] });
  const tsQ = useQuery<{ series: TimeseriesPoint[] }>({ queryKey: ["/api/admin/growth/timeseries"] });
  const cohortQ = useQuery<{ cohorts: Cohort[] }>({ queryKey: ["/api/admin/growth/cohorts"] });
  const pagesQ = useQuery<{ pages: { path: string; hits: number }[] }>({
    queryKey: ["/api/admin/growth/top-pages"],
  });

  const summary = funnelQ.data?.summary;
  const rates = funnelQ.data?.rates;
  const funnel = funnelQ.data?.funnel ?? [];
  const series = tsQ.data?.series ?? [];
  const cohorts = cohortQ.data?.cohorts ?? [];
  const pages = pagesQ.data?.pages ?? [];

  return (
    <div className="space-y-6 p-6" data-testid="admin-growth-page">
      <div>
        <h1 className="text-3xl font-bold tracking-tight" data-testid="growth-title">Growth</h1>
        <p className="text-muted-foreground mt-1">
          Acquisition funnel, retention cohorts, and the top-of-funnel pulse for FounderConsole.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total signups"
          value={summary?.total_users ?? 0}
          sub={`+${summary?.signups_30d ?? 0} in 30d`}
          icon={Users}
          isLoading={funnelQ.isLoading}
        />
        <StatCard
          title="Active 30d"
          value={summary?.active_30d ?? 0}
          sub={`${summary?.active_7d ?? 0} active in 7d`}
          icon={Activity}
          isLoading={funnelQ.isLoading}
        />
        <StatCard
          title="Survival sims (30d)"
          value={summary?.sim_runs_30d ?? 0}
          sub={`${summary?.sim_runs_total ?? 0} all-time`}
          icon={Rocket}
          isLoading={funnelQ.isLoading}
        />
        <StatCard
          title="Sim → signup"
          value={`${rates?.sim_to_signup_pct ?? 0}%`}
          sub={`Activation ${rates?.activation_pct ?? 0}% · Signup→Active ${rates?.signup_to_active_pct ?? 0}%`}
          icon={Target}
          isLoading={funnelQ.isLoading}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-primary" /> Acquisition funnel (last 30d)
          </CardTitle>
          <CardDescription>From the public Survival Simulator down to active users.</CardDescription>
        </CardHeader>
        <CardContent>
          {funnelQ.isLoading ? (
            <Skeleton className="h-72 w-full" />
          ) : funnel.length === 0 ? (
            <p className="text-sm text-muted-foreground" data-testid="funnel-empty">No data yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={funnel} layout="vertical" margin={{ left: 24, right: 24 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                <XAxis type="number" stroke="#a1a1aa" />
                <YAxis dataKey="stage" type="category" width={180} stroke="#a1a1aa" />
                <Tooltip contentStyle={{ background: "#18181b", border: "1px solid #27272a" }} />
                <Bar dataKey="count" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-primary" /> Daily activity (last 30d)
          </CardTitle>
          <CardDescription>Signups, simulator runs, and distinct active users per day.</CardDescription>
        </CardHeader>
        <CardContent>
          {tsQ.isLoading ? (
            <Skeleton className="h-72 w-full" />
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={series}>
                <defs>
                  <linearGradient id="g-sims" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.5} />
                    <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="g-signups" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.5} />
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="g-active" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.5} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                <XAxis dataKey="day" stroke="#a1a1aa" tick={{ fontSize: 11 }} />
                <YAxis stroke="#a1a1aa" />
                <Tooltip contentStyle={{ background: "#18181b", border: "1px solid #27272a" }} />
                <Legend />
                <Area type="monotone" dataKey="sims" stroke="hsl(var(--primary))" fill="url(#g-sims)" name="Sim runs" />
                <Area type="monotone" dataKey="signups" stroke="#f59e0b" fill="url(#g-signups)" name="Signups" />
                <Area type="monotone" dataKey="active" stroke="#10b981" fill="url(#g-active)" name="Active users" />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Weekly signup cohorts</CardTitle>
            <CardDescription>Retention by week-after-signup (W1 / W2 / W3 return).</CardDescription>
          </CardHeader>
          <CardContent>
            {cohortQ.isLoading ? (
              <Skeleton className="h-48 w-full" />
            ) : cohorts.length === 0 ? (
              <p className="text-sm text-muted-foreground" data-testid="cohorts-empty">No cohorts yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm" data-testid="cohort-table">
                  <thead className="text-muted-foreground text-left">
                    <tr>
                      <th className="py-2 pr-4">Cohort</th>
                      <th className="py-2 pr-4">Size</th>
                      <th className="py-2 pr-4">W1</th>
                      <th className="py-2 pr-4">W2</th>
                      <th className="py-2">W3</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cohorts.map((c) => (
                      <tr key={c.cohort_week} className="border-t border-zinc-800" data-testid={`cohort-row-${c.cohort_week}`}>
                        <td className="py-2 pr-4 font-mono text-xs">{c.cohort_week}</td>
                        <td className="py-2 pr-4">{c.cohort_size}</td>
                        <td className="py-2 pr-4">
                          <span className={`px-2 py-1 rounded text-xs ${retentionColor(c.w1_pct)}`}>{c.w1_pct}%</span>
                        </td>
                        <td className="py-2 pr-4">
                          <span className={`px-2 py-1 rounded text-xs ${retentionColor(c.w2_pct)}`}>{c.w2_pct}%</span>
                        </td>
                        <td className="py-2">
                          <span className={`px-2 py-1 rounded text-xs ${retentionColor(c.w3_pct)}`}>{c.w3_pct}%</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top entry pages (30d)</CardTitle>
            <CardDescription>From analytics events. Empty until pageview tracking is wired in.</CardDescription>
          </CardHeader>
          <CardContent>
            {pagesQ.isLoading ? (
              <Skeleton className="h-48 w-full" />
            ) : pages.length === 0 ? (
              <p className="text-sm text-muted-foreground" data-testid="pages-empty">
                No pageview events recorded. Wire up PostHog or analytics_events to populate this.
              </p>
            ) : (
              <ul className="space-y-2" data-testid="pages-list">
                {pages.map((p) => (
                  <li key={p.path} className="flex items-center justify-between text-sm" data-testid={`page-row-${p.path}`}>
                    <span className="font-mono truncate pr-2">{p.path}</span>
                    <Badge variant="secondary">{p.hits}</Badge>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
