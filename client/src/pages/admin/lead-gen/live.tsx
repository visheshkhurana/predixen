/**
 * Live Executions page — /admin/lead-gen/live
 *
 * Streams recent n8n workflow executions via the /api/admin/lead-gen/executions
 * proxy. Auto-refreshes every 10s. Shows status, duration, errors.
 */

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { leadGenApi, leadGenKeys, type Execution } from "@/lib/api/lead-gen";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  AlertCircle,
  CheckCircle2,
  Circle,
  Clock,
  ExternalLink,
  RefreshCw,
  XCircle,
} from "lucide-react";

const STATUS_META: Record<
  string,
  { label: string; icon: React.ElementType; color: string }
> = {
  success: { label: "Success", icon: CheckCircle2, color: "text-emerald-600" },
  error: { label: "Error", icon: XCircle, color: "text-red-600" },
  running: { label: "Running", icon: Circle, color: "text-blue-600" },
  waiting: { label: "Waiting", icon: Clock, color: "text-amber-600" },
  canceled: { label: "Canceled", icon: XCircle, color: "text-zinc-500" },
  unknown: { label: "Unknown", icon: AlertCircle, color: "text-zinc-500" },
};

export default function LiveExecutionsPage() {
  const [statusFilter, setStatusFilter] = useState<string>("");
  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: leadGenKeys.executions({ status: statusFilter }),
    queryFn: () =>
      leadGenApi.listExecutions(statusFilter ? { status: statusFilter, limit: 20 } : { limit: 20 }),
    refetchInterval: 10_000,
    retry: false,
  });

  const executions = data?.data ?? [];
  const errors = executions.filter((e) => e.status === "error");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Live n8n Executions</h2>
          <p className="text-sm text-muted-foreground">
            Recent workflow runs from your connected n8n instance.
            {data?.source === "n8n" && " Auto-refreshes every 10s."}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            className="text-xs bg-background border border-input rounded px-2 py-1"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            data-testid="select-status-filter"
          >
            <option value="">All statuses</option>
            <option value="success">Success</option>
            <option value="error">Error</option>
            <option value="waiting">Waiting</option>
            <option value="running">Running</option>
          </select>
          <Button
            size="sm"
            variant="outline"
            onClick={() => refetch()}
            disabled={isFetching}
            data-testid="button-refresh-executions"
          >
            <RefreshCw className={`h-3 w-3 mr-1 ${isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      {data?.source === "empty" && (
        <Alert className="border-amber-500/30 bg-amber-50 dark:bg-amber-950/20">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {data.error || "n8n is not configured."} Set the base URL and API key in{" "}
            <a href="/admin/lead-gen/settings" className="underline">Settings</a>.
          </AlertDescription>
        </Alert>
      )}

      {data?.source === "error" && (
        <Alert className="border-red-500/30 bg-red-50 dark:bg-red-950/20">
          <AlertCircle className="h-4 w-4 text-red-600" />
          <AlertDescription className="text-sm">
            <div className="font-medium">Failed to reach n8n</div>
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

      {errors.length > 0 && (
        <Card className="border-red-500/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <XCircle className="h-4 w-4 text-red-600" />
              Recent errors ({errors.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <ul className="space-y-2">
              {errors.slice(0, 5).map((e) => (
                <li key={e.id} className="text-sm border-l-2 border-red-500 pl-3">
                  <div className="font-mono text-xs text-muted-foreground">
                    #{e.id}
                    {e.error_node && <> · node: <span className="text-red-600">{e.error_node}</span></>}
                    {e.started_at && <> · {new Date(e.started_at).toLocaleString()}</>}
                  </div>
                  {e.error_message && (
                    <div className="mt-1 text-xs text-red-600">{e.error_message}</div>
                  )}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Executions</CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          {isLoading ? (
            <div className="py-8 text-center text-sm text-muted-foreground">Loading…</div>
          ) : executions.length === 0 ? (
            <div className="py-8 text-center text-sm text-muted-foreground">
              {data?.source === "n8n" ? "No executions yet." : "Unable to fetch executions."}
            </div>
          ) : (
            <div className="space-y-2">
              {executions.map((e) => (
                <ExecutionRow key={e.id} execution={e} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function ExecutionRow({ execution: e }: { execution: Execution }) {
  const meta = STATUS_META[e.status] ?? STATUS_META.unknown;
  const Icon = meta.icon;
  return (
    <div
      className="flex items-center justify-between border-b last:border-0 pb-2 last:pb-0"
      data-testid={`execution-row-${e.id}`}
    >
      <div className="flex items-center gap-3 min-w-0">
        <Icon className={`h-4 w-4 shrink-0 ${meta.color}`} />
        <div className="min-w-0">
          <div className="text-sm truncate">
            <span className="font-medium">{e.workflow_name ?? "(unnamed workflow)"}</span>
            <span className="text-xs text-muted-foreground font-mono ml-2">#{e.id}</span>
          </div>
          <div className="text-xs text-muted-foreground mt-0.5">
            {e.started_at ? new Date(e.started_at).toLocaleString() : "—"}
            {e.duration_ms !== null && e.duration_ms !== undefined && (
              <> · {(e.duration_ms / 1000).toFixed(1)}s</>
            )}
            {e.mode && <> · {e.mode}</>}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0 ml-4">
        <Badge variant="outline" className={`text-xs ${meta.color} border-current`}>
          {meta.label}
        </Badge>
        {e.workflow_id && (
          <Button
            size="icon"
            variant="ghost"
            className="h-7 w-7"
            asChild
          >
            <a
              href={`https://vysheshk.app.n8n.cloud/workflow/${e.workflow_id}/executions/${e.id}`}
              target="_blank"
              rel="noreferrer"
              data-testid={`link-execution-${e.id}`}
            >
              <ExternalLink className="h-3 w-3" />
            </a>
          </Button>
        )}
      </div>
    </div>
  );
}
