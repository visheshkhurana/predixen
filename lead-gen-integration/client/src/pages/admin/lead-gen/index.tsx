/**
 * Admin → Lead Gen dashboard.
 * Place at: client/src/pages/admin/lead-gen/index.tsx
 *
 * Entry point for /admin/lead-gen. Uses Wouter for routing between
 * sub-tabs (matches predixen's existing pattern). Shows funnel metrics
 * at the top, recent activity feed, and links to sub-pages.
 */

import { useQuery } from "@tanstack/react-query";
import { Link, Route, Switch } from "wouter";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { leadGenApi, leadGenKeys } from "@/lib/api/lead-gen";
import { Activity, Users, Mail, TrendingUp, Settings as SettingsIcon } from "lucide-react";
import LeadsPage from "./leads";
import TemplatesPage from "./templates";
import SettingsPage from "./settings";
import CampaignsPage from "./campaigns";

export default function LeadGenAdminLayout() {
  return (
    <div className="container mx-auto max-w-7xl p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Lead Gen</h1>
          <p className="text-sm text-muted-foreground">
            Outbound, inbound, and activation — unified view. Automation runs in n8n; this panel controls it.
          </p>
        </div>
        <nav className="flex gap-2">
          <Link href="/admin/lead-gen"><Button variant="ghost">Overview</Button></Link>
          <Link href="/admin/lead-gen/leads"><Button variant="ghost">Leads</Button></Link>
          <Link href="/admin/lead-gen/campaigns"><Button variant="ghost">Campaigns</Button></Link>
          <Link href="/admin/lead-gen/templates"><Button variant="ghost">Templates</Button></Link>
          <Link href="/admin/lead-gen/settings">
            <Button variant="ghost" size="icon"><SettingsIcon className="h-4 w-4" /></Button>
          </Link>
        </nav>
      </div>

      <Switch>
        <Route path="/admin/lead-gen" component={LeadGenOverview} />
        <Route path="/admin/lead-gen/leads" component={LeadsPage} />
        <Route path="/admin/lead-gen/leads/:id" component={LeadsPage} />
        <Route path="/admin/lead-gen/campaigns" component={CampaignsPage} />
        <Route path="/admin/lead-gen/templates" component={TemplatesPage} />
        <Route path="/admin/lead-gen/settings" component={SettingsPage} />
      </Switch>
    </div>
  );
}

function LeadGenOverview() {
  const { data: stats, isLoading } = useQuery({
    queryKey: leadGenKeys.stats(),
    queryFn: leadGenApi.stats,
    refetchInterval: 30_000,
  });
  const { data: settings } = useQuery({
    queryKey: leadGenKeys.settings(),
    queryFn: leadGenApi.getSettings,
  });

  if (isLoading || !stats) return <Skeleton />;

  const totalLeads = Object.values(stats.totals).reduce((a, b) => a + b, 0);
  const replyRatePct = Math.round(stats.reply_rate_7d * 1000) / 10;

  return (
    <div className="space-y-6">
      {!settings?.is_enabled && (
        <Card className="border-amber-500/30 bg-amber-50 dark:bg-amber-950/20">
          <CardContent className="pt-6 flex items-center justify-between">
            <div>
              <p className="font-medium">Lead-gen is disabled.</p>
              <p className="text-sm text-muted-foreground">
                Nothing will send. Finish the n8n setup + flip the switch in Settings.
              </p>
            </div>
            <Link href="/admin/lead-gen/settings"><Button>Go to Settings</Button></Link>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <MetricCard
          icon={<Users className="h-4 w-4" />}
          label="Total leads"
          value={totalLeads.toLocaleString()}
          sub={`${stats.totals["new"] ?? 0} new · ${stats.totals["replied"] ?? 0} replied`}
        />
        <MetricCard
          icon={<Mail className="h-4 w-4" />}
          label="Sends (7d)"
          value={stats.last_7d_sends.toLocaleString()}
        />
        <MetricCard
          icon={<Activity className="h-4 w-4" />}
          label="Reply rate (7d)"
          value={`${replyRatePct}%`}
          sub={`${stats.last_7d_replies} replies`}
          tone={replyRatePct >= 5 ? "good" : replyRatePct >= 2 ? "neutral" : "warn"}
        />
        <MetricCard
          icon={<TrendingUp className="h-4 w-4" />}
          label="Trial signups (7d)"
          value={stats.trial_signups_7d.toLocaleString()}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader><CardTitle className="text-base">Funnel by status</CardTitle></CardHeader>
          <CardContent>
            <ul className="space-y-1">
              {Object.entries(stats.totals).sort((a, b) => b[1] - a[1]).map(([status, count]) => (
                <li key={status} className="flex justify-between text-sm">
                  <span className="capitalize">{status.replace(/_/g, " ")}</span>
                  <span className="font-mono">{count}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-base">Leads by source</CardTitle></CardHeader>
          <CardContent>
            <ul className="space-y-1">
              {Object.entries(stats.sources).sort((a, b) => b[1] - a[1]).map(([source, count]) => (
                <li key={source} className="flex justify-between text-sm">
                  <span className="capitalize">{source}</span>
                  <span className="font-mono">{count}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">Recent activity</CardTitle></CardHeader>
        <CardContent>
          {stats.recent_events.length === 0 ? (
            <p className="text-sm text-muted-foreground">No events yet. Once n8n starts firing, they'll appear here.</p>
          ) : (
            <ul className="space-y-2">
              {stats.recent_events.map(e => (
                <li key={e.id} className="flex items-start justify-between gap-4 text-sm border-b pb-2 last:border-0">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary" className="text-xs">{e.kind}</Badge>
                      {e.reply_category && <Badge variant="outline" className="text-xs">{e.reply_category}</Badge>}
                    </div>
                    {e.email_subject && <p className="truncate text-xs text-muted-foreground mt-1">{e.email_subject}</p>}
                  </div>
                  <span className="text-xs text-muted-foreground whitespace-nowrap">
                    {new Date(e.created_at).toLocaleString()}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function MetricCard({ icon, label, value, sub, tone }: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub?: string;
  tone?: "good" | "warn" | "neutral";
}) {
  const toneClass = tone === "good" ? "text-emerald-600" : tone === "warn" ? "text-amber-600" : "";
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">{icon}{label}</div>
        <div className={`text-2xl font-semibold mt-1 ${toneClass}`}>{value}</div>
        {sub && <div className="text-xs text-muted-foreground mt-1">{sub}</div>}
      </CardContent>
    </Card>
  );
}

function Skeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      {[1, 2, 3, 4].map(i => (
        <Card key={i}><CardContent className="pt-6 h-24 animate-pulse bg-muted/50 rounded" /></Card>
      ))}
    </div>
  );
}
