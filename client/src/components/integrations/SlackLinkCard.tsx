import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Loader2, MessageSquare, Copy } from "lucide-react";
import { apiRequest } from "@/lib/queryClient";
import { getErrorMessage } from "@/lib/errors";
import { useToast } from "@/hooks/use-toast";

interface SlackLinkStatus {
  linked: boolean;
  team_id: string | null;
  channel_id: string | null;
  linked_at: string | number | null;
}

interface SlackLinkCode {
  code: string;
  expires_in_seconds: number;
  instructions: string;
}

export function slackLinkPaths(companyId: number) {
  return {
    status: `/api/companies/${companyId}/integrations/slack`,
    linkCode: `/api/companies/${companyId}/integrations/slack/link-code`,
  };
}

export function slackLinkCommand(code: string): string {
  return `/fc-link ${code}`;
}

/** "15 minutes" for 900 seconds; never shows 0. */
export function formatExpiry(seconds: number): string {
  const mins = Math.max(1, Math.round(seconds / 60));
  return `${mins} minute${mins === 1 ? "" : "s"}`;
}

function formatLinkedAt(v: string | number | null): string | null {
  if (v == null) return null;
  const d = typeof v === "number" ? new Date(v * 1000) : new Date(v);
  return Number.isNaN(d.getTime()) ? null : d.toLocaleString();
}

/**
 * Link this company to a Slack workspace: generate a one-time code, run
 * `/fc-link <code>` in the Slack channel, unlink when done.
 */
export function SlackLinkCard({ companyId }: { companyId: number }) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const paths = slackLinkPaths(companyId);
  const [issued, setIssued] = useState<{ code: string; expiresAt: number; ttl: number } | null>(null);

  const statusQuery = useQuery<SlackLinkStatus>({
    queryKey: [paths.status],
    queryFn: async () => (await apiRequest("GET", paths.status)).json(),
    enabled: companyId > 0,
  });

  const generate = useMutation({
    mutationFn: async (): Promise<SlackLinkCode> => (await apiRequest("POST", paths.linkCode)).json(),
    onSuccess: (data) => {
      setIssued({ code: data.code, ttl: data.expires_in_seconds, expiresAt: Date.now() + data.expires_in_seconds * 1000 });
    },
    onError: (err) => toast({ title: "Could not create a link code", description: getErrorMessage(err), variant: "destructive" }),
  });

  const unlink = useMutation({
    mutationFn: async () => (await apiRequest("DELETE", paths.status)).json(),
    onSuccess: () => {
      setIssued(null);
      queryClient.invalidateQueries({ queryKey: [paths.status] });
      toast({ title: "Slack unlinked" });
    },
    onError: (err) => toast({ title: "Could not unlink Slack", description: getErrorMessage(err), variant: "destructive" }),
  });

  if (companyId <= 0) return null;

  const status = statusQuery.data;
  const linked = !!status?.linked;
  const expired = issued != null && Date.now() >= issued.expiresAt;
  const linkedAt = formatLinkedAt(status?.linked_at ?? null);

  const copyCommand = async () => {
    if (!issued) return;
    try {
      await navigator.clipboard.writeText(slackLinkCommand(issued.code));
      toast({ title: "Command copied" });
    } catch {
      toast({ title: "Copy failed", description: "Select the command and copy it manually.", variant: "destructive" });
    }
  };

  return (
    <Card data-testid="card-slack-link">
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <MessageSquare className="h-5 w-5" />
            <div>
              <CardTitle className="text-base">Slack</CardTitle>
              <CardDescription>Ask FounderConsole about your numbers from a Slack channel.</CardDescription>
            </div>
          </div>
          {statusQuery.isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : statusQuery.isError ? (
            <Badge variant="outline" data-testid="badge-slack-status">Status unavailable</Badge>
          ) : (
            <Badge variant={linked ? "default" : "outline"} data-testid="badge-slack-status">
              {linked ? "Linked" : "Not linked"}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        {linked && (
          <p className="text-muted-foreground" data-testid="text-slack-linked">
            Linked to workspace {status?.team_id}
            {status?.channel_id ? `, channel ${status.channel_id}` : ""}
            {linkedAt ? ` since ${linkedAt}` : ""}.
          </p>
        )}

        {issued && !expired && (
          <div className="rounded-md border p-3 space-y-2" data-testid="slack-link-code">
            <p>In the Slack channel to link, run:</p>
            <div className="flex items-center gap-2">
              <code className="rounded bg-muted px-2 py-1 font-mono" data-testid="text-slack-command">
                {slackLinkCommand(issued.code)}
              </code>
              <Button size="icon" variant="ghost" onClick={copyCommand} aria-label="Copy command" data-testid="button-copy-slack-command">
                <Copy className="h-4 w-4" />
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Single use. Expires in {formatExpiry(issued.ttl)}.
            </p>
          </div>
        )}
        {issued && expired && (
          <p className="text-xs text-muted-foreground">That code has expired. Generate a new one.</p>
        )}

        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant={linked ? "outline" : "default"}
            onClick={() => generate.mutate()}
            disabled={generate.isPending}
            data-testid="button-generate-slack-code"
          >
            {generate.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {linked ? "Link another channel" : "Generate link code"}
          </Button>
          {linked && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => unlink.mutate()}
              disabled={unlink.isPending}
              data-testid="button-unlink-slack"
            >
              {unlink.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Unlink
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
