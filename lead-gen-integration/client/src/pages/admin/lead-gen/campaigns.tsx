/**
 * Campaigns page — /admin/lead-gen/campaigns
 * Place at: client/src/pages/admin/lead-gen/campaigns.tsx
 *
 * Minimal v1 — list campaigns + status + create. Richer editing
 * (cadence editor, segment builder) can come in v2.
 */

import { useQuery } from "@tanstack/react-query";
import { leadGenApi, leadGenKeys } from "@/lib/api/lead-gen";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function CampaignsPage() {
  const { data: campaigns, isLoading } = useQuery({
    queryKey: leadGenKeys.campaigns(),
    queryFn: leadGenApi.listCampaigns,
  });

  if (isLoading || !campaigns) return <div className="text-center py-12 text-muted-foreground">Loading…</div>;

  return (
    <div className="space-y-4">
      {campaigns.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center space-y-2">
            <p className="text-muted-foreground">No campaigns yet.</p>
            <p className="text-xs text-muted-foreground">
              Create one via <code>POST /api/admin/lead-gen/campaigns</code>. UI for creation coming in v2.
            </p>
          </CardContent>
        </Card>
      ) : (
        campaigns.map(c => (
          <Card key={c.id}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">{c.name}</CardTitle>
                <Badge variant={c.status === "active" ? "default" : "secondary"}>{c.status}</Badge>
              </div>
            </CardHeader>
            <CardContent className="text-sm space-y-2">
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
        ))
      )}
    </div>
  );
}
