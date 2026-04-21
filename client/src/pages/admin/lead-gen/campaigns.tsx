/**
 * Campaigns page — /admin/lead-gen/campaigns
 *
 * Shows:
 *  1. Smartlead campaigns section at top — real sent/open/reply/bounce numbers
 *     pulled from the Smartlead analytics API. The source of truth for
 *     outbound performance.
 *  2. Predixen-internal campaigns (db-backed LeadCampaign rows) below.
 *
 * Smartlead data drives decisions; internal campaigns describe the
 * segmentation + template strategy.
 */

import { useQuery } from "@tanstack/react-query";
import { leadGenApi, leadGenKeys, type SmartleadCampaign } from "@/lib/api/lead-gen";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle, ExternalLink, Mail, MousePointerClick, Reply, Ban } from "lucide-react";

export default function CampaignsPage() {
  return (
    <div className="space-y-8">
      <SmartleadCampaignsSection />
      <PredixenCampaignsSection />
    </div>
  );
}

// -------------------------------------------------------------
// Smartlead (external) KPIs
// -------------------------------------------------------------

function SmartleadCampaignsSection() {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: leadGenKeys.smartleadCampaigns(),
    queryFn: leadGenApi.listSmartleadCampaigns,
    refetchInterval: 60_000,
    retry: false,
  });

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Smartlead campaigns</h2>
        <p className="text-xs text-muted-foreground">
          {data?.source === "smartlead" && "Live from Smartlead · refreshes every 60s"}
        </p>
      </div>

      {data?.source === "empty" && (
        <Alert className="border-amber-500/30 bg-amber-50 dark:bg-amber-950/20">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {data.error || "Smartlead API key not configured."}
          </AlertDescription>
        </Alert>
      )}

      {data?.source === "error" && (
        <Alert className="border-red-500/30 bg-red-50 dark:bg-red-950/20">
          <AlertCircle className="h-4 w-4 text-red-600" />
          <AlertDescription className="text-sm">
            <div className="font-medium">Failed to reach Smartlead</div>
            <div className="text-xs mt-1 font-mono">{data.error}</div>
          </AlertDescription>
        </Alert>
      )}

      {isError && (
        <Alert className="border-red-500/30 bg-red-50 dark:bg-red-950/20">
          <AlertCircle className="h-4 w-4 text-red-600" />
          <AlertDescription>
            Request failed: {(error as Error)?.message ?? "unknown error"}
          </AlertDescription>
        </Alert>
      )}

      {isLoading ? (
        <Card><CardContent className="py-8 text-center text-sm text-muted-foreground">Loading Smartlead campaigns…</CardContent></Card>
      ) : !data || data.data.length === 0 ? (
        <Card><CardContent className="py-8 text-center text-sm text-muted-foreground">No Smartlead campaigns found.</CardContent></Card>
      ) : (
        <div className="space-y-3">
          {data.data.map((c) => <SmartleadCampaignCard key={c.id} campaign={c} />)}
        </div>
      )}
    </section>
  );
}

function SmartleadCampaignCard({ campaign: c }: { campaign: SmartleadCampaign }) {
  const openPct = Math.round(c.open_rate * 1000) / 10;
  const replyPct = Math.round(c.reply_rate * 1000) / 10;
  const bouncePct = Math.round(c.bounce_rate * 1000) / 10;

  const statusTone =
    c.status === "ACTIVE" ? "default" :
    c.status === "COMPLETED" ? "outline" :
    c.status === "PAUSED" ? "secondary" :
    "secondary";

  // Deliverability heuristic for UI tone
  const bounceWarn = bouncePct >= 5;
  const replyGood = replyPct >= 5;

  return (
    <Card data-testid={`smartlead-campaign-${c.id}`}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <CardTitle className="text-base truncate">{c.name}</CardTitle>
            <p className="text-xs text-muted-foreground mt-0.5">
              ID {c.id} · {c.sequence_count} emails in sequence
              {c.created_at && <> · created {new Date(c.created_at).toLocaleDateString()}</>}
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <Badge variant={statusTone as any}>{c.status ?? "unknown"}</Badge>
            <a
              className="text-xs text-muted-foreground hover:text-foreground inline-flex items-center gap-1"
              href={`https://app.smartlead.ai/app/email-campaign/${c.id}`}
              target="_blank"
              rel="noreferrer"
              data-testid={`link-smartlead-${c.id}`}
            >
              Open <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <KpiCell icon={<Mail className="h-3.5 w-3.5" />} label="Sent" value={c.unique_sent_count || c.sent_count} />
          <KpiCell icon={<Mail className="h-3.5 w-3.5 text-blue-600" />} label="Open rate" value={`${openPct}%`} sub={`${c.unique_open_count || c.open_count} opens`} />
          <KpiCell icon={<MousePointerClick className="h-3.5 w-3.5" />} label="Click rate" value={`${c.sent_count > 0 ? Math.round(((c.unique_click_count || c.click_count) / c.sent_count) * 1000) / 10 : 0}%`} sub={`${c.unique_click_count || c.click_count} clicks`} />
          <KpiCell
            icon={<Reply className={`h-3.5 w-3.5 ${replyGood ? "text-emerald-600" : ""}`} />}
            label="Reply rate"
            value={`${replyPct}%`}
            tone={replyGood ? "good" : replyPct >= 2 ? "neutral" : "warn"}
            sub={`${c.reply_count} replies`}
          />
          <KpiCell
            icon={<Ban className={`h-3.5 w-3.5 ${bounceWarn ? "text-red-600" : ""}`} />}
            label="Bounce rate"
            value={`${bouncePct}%`}
            tone={bounceWarn ? "warn" : "neutral"}
            sub={`${c.bounce_count} bounces`}
          />
        </div>
        <div className="flex gap-2 mt-3 text-xs text-muted-foreground flex-wrap">
          <span>Total leads: <span className="font-mono">{c.total_leads.toLocaleString()}</span></span>
          {c.unsubscribed_count > 0 && <span>· Unsubs: <span className="font-mono">{c.unsubscribed_count}</span></span>}
          {c.block_count > 0 && <span>· Blocks: <span className="font-mono">{c.block_count}</span></span>}
        </div>
      </CardContent>
    </Card>
  );
}

function KpiCell({ icon, label, value, sub, tone }: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  sub?: string;
  tone?: "good" | "warn" | "neutral";
}) {
  const toneClass = tone === "good" ? "text-emerald-600" : tone === "warn" ? "text-red-600" : "";
  return (
    <div>
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">{icon}{label}</div>
      <div className={`text-lg font-semibold mt-0.5 ${toneClass}`}>{value}</div>
      {sub && <div className="text-xs text-muted-foreground">{sub}</div>}
    </div>
  );
}

// -------------------------------------------------------------
// Predixen-internal campaigns (db-backed LeadCampaign rows)
// -------------------------------------------------------------

function PredixenCampaignsSection() {
  const { data: campaigns, isLoading } = useQuery({
    queryKey: leadGenKeys.campaigns(),
    queryFn: leadGenApi.listCampaigns,
  });

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold">Internal campaign definitions</h2>

      {isLoading || !campaigns ? (
        <Card><CardContent className="py-8 text-center text-sm text-muted-foreground">Loading…</CardContent></Card>
      ) : campaigns.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center space-y-2">
            <p className="text-muted-foreground text-sm">No internal campaigns yet.</p>
            <p className="text-xs text-muted-foreground">
              Create one via <code>POST /api/admin/lead-gen/campaigns</code>. UI for creation coming in v2.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {campaigns.map(c => (
            <Card key={c.id}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">{c.name}</CardTitle>
                  <Badge variant={c.status === "active" ? "default" : "secondary"}>{c.status}</Badge>
                </div>
              </CardHeader>
              <CardContent className="text-sm space-y-2 pt-0">
                {c.description && <p className="text-muted-foreground">{c.description}</p>}
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div><span className="text-muted-foreground">Goal:</span> {c.goal_metric}</div>
                  <div><span className="text-muted-foreground">Cadence:</span> {c.cadence_days.join(", ")} days</div>
                  {c.n8n_workflow_id && <div><span className="text-muted-foreground">n8n:</span> <code>{c.n8n_workflow_id}</code></div>}
                  {c.n8n_webhook_path && <div className="truncate"><span className="text-muted-foreground">Webhook:</span> <code className="truncate">{c.n8n_webhook_path}</code></div>}
                </div>
                {Object.keys(c.target_segment).length > 0 && (
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Targeting</p>
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(c.target_segment).flatMap(([k, arr]) =>
                        (arr as string[]).map(v => <Badge key={`${k}:${v}`} variant="outline" className="text-xs">{k}={v}</Badge>)
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </section>
  );
}
