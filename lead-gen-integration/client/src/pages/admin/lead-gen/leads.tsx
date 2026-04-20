/**
 * Leads list page — /admin/lead-gen/leads
 * Place at: client/src/pages/admin/lead-gen/leads.tsx
 *
 * Filter by search/status/source, paginate, and row-click opens a detail
 * drawer with event timeline + manual actions.
 */

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useToast } from "@/hooks/use-toast";
import { leadGenApi, leadGenKeys, type Lead } from "@/lib/api/lead-gen";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Card, CardContent } from "@/components/ui/card";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { ExternalLink, Mail, Pause, Play, Ban, Check } from "lucide-react";

const STATUS_OPTIONS = [
  "", "new", "enriching", "enriched", "queued", "contacted",
  "replied", "converted", "paused", "unsubscribed", "bounced", "do_not_contact",
];
const SOURCE_OPTIONS = ["", "manual", "scraper", "csv", "web", "signup", "demo_request"];

export default function LeadsPage() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [source, setSource] = useState("");
  const [page, setPage] = useState(1);
  const [openId, setOpenId] = useState<number | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: leadGenKeys.leads({ search, status, source, page }),
    queryFn: () => leadGenApi.listLeads({
      search: search || undefined,
      status: status || undefined,
      source: source || undefined,
      page,
      page_size: 25,
    }),
    keepPreviousData: true,
  });

  const leads = data?.items ?? [];
  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <>
      <Card>
        <CardContent className="pt-6 space-y-4">
          <div className="flex flex-wrap gap-2 items-center">
            <Input
              placeholder="Search email, company, name…"
              value={search}
              onChange={e => { setSearch(e.target.value); setPage(1); }}
              className="max-w-xs"
            />
            <Select value={status} onValueChange={v => { setStatus(v === "all" ? "" : v); setPage(1); }}>
              <SelectTrigger className="w-40"><SelectValue placeholder="Status" /></SelectTrigger>
              <SelectContent>
                {STATUS_OPTIONS.map(s => (
                  <SelectItem key={s || "all"} value={s || "all"}>
                    {s ? s.replace(/_/g, " ") : "All statuses"}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={source} onValueChange={v => { setSource(v === "all" ? "" : v); setPage(1); }}>
              <SelectTrigger className="w-36"><SelectValue placeholder="Source" /></SelectTrigger>
              <SelectContent>
                {SOURCE_OPTIONS.map(s => (
                  <SelectItem key={s || "all"} value={s || "all"}>
                    {s || "All sources"}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <div className="flex-1" />
            <span className="text-sm text-muted-foreground">
              {data ? `${data.total} leads` : ""}
            </span>
          </div>

          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Email</TableHead>
                  <TableHead>Name / Company</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead>Last email</TableHead>
                  <TableHead className="text-right">Reply</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  <TableRow><TableCell colSpan={6} className="text-center py-12 text-muted-foreground">Loading…</TableCell></TableRow>
                ) : leads.length === 0 ? (
                  <TableRow><TableCell colSpan={6} className="text-center py-12 text-muted-foreground">No leads match.</TableCell></TableRow>
                ) : (
                  leads.map(l => (
                    <TableRow key={l.id} className="cursor-pointer hover:bg-muted/50" onClick={() => setOpenId(l.id)}>
                      <TableCell className="font-mono text-xs">{l.email}</TableCell>
                      <TableCell>
                        <div className="font-medium">{[l.first_name, l.last_name].filter(Boolean).join(" ") || "—"}</div>
                        {l.company && <div className="text-xs text-muted-foreground">{l.company}</div>}
                      </TableCell>
                      <TableCell><StatusBadge status={l.status} /></TableCell>
                      <TableCell className="text-xs">{l.source}</TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {l.last_email_at ? new Date(l.last_email_at).toLocaleDateString() : "—"}
                      </TableCell>
                      <TableCell className="text-right">
                        {l.reply_category ? <Badge variant="outline">{l.reply_category}</Badge> : "—"}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Page {page} of {totalPages}</span>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Previous</Button>
                <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>Next</Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <LeadDetailDrawer id={openId} onClose={() => setOpenId(null)} />
    </>
  );
}

function StatusBadge({ status }: { status: string }) {
  const variants: Record<string, string> = {
    new: "bg-blue-500/10 text-blue-700 dark:text-blue-400",
    queued: "bg-amber-500/10 text-amber-700 dark:text-amber-400",
    contacted: "bg-violet-500/10 text-violet-700 dark:text-violet-400",
    replied: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
    converted: "bg-emerald-600/15 text-emerald-800 dark:text-emerald-300 font-semibold",
    paused: "bg-muted",
    unsubscribed: "bg-red-500/10 text-red-700 dark:text-red-400",
    bounced: "bg-red-500/10 text-red-700 dark:text-red-400",
    do_not_contact: "bg-red-600/15 text-red-800 dark:text-red-300",
  };
  return (
    <span className={`inline-flex px-2 py-0.5 rounded text-xs ${variants[status] ?? "bg-muted"}`}>
      {status.replace(/_/g, " ")}
    </span>
  );
}

function LeadDetailDrawer({ id, onClose }: { id: number | null; onClose: () => void }) {
  const qc = useQueryClient();
  const { toast } = useToast();
  const { data: lead, isLoading } = useQuery({
    queryKey: leadGenKeys.lead(id ?? 0),
    queryFn: () => leadGenApi.getLead(id!),
    enabled: id !== null,
  });

  const actionMut = useMutation({
    mutationFn: (body: Parameters<typeof leadGenApi.leadAction>[1]) =>
      leadGenApi.leadAction(id!, body),
    onSuccess: (r) => {
      toast({ title: `Lead ${r.status}`, description: "Action dispatched to n8n." });
      qc.invalidateQueries({ queryKey: leadGenKeys.all });
    },
    onError: (e: Error) => toast({ title: "Action failed", description: e.message, variant: "destructive" }),
  });

  if (id === null) return null;

  return (
    <Sheet open={id !== null} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className="sm:max-w-lg overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{lead?.email ?? "Loading…"}</SheetTitle>
          <SheetDescription>
            {lead ? [lead.first_name, lead.last_name].filter(Boolean).join(" ") || lead.company || "No name" : null}
          </SheetDescription>
        </SheetHeader>

        {isLoading || !lead ? (
          <div className="py-8 text-center text-muted-foreground">Loading…</div>
        ) : (
          <div className="space-y-6 py-4">
            <div className="grid grid-cols-2 gap-2 text-sm">
              <Field label="Status" value={<StatusBadge status={lead.status} />} />
              <Field label="Source" value={lead.source} />
              <Field label="Stage" value={lead.stage ?? "—"} />
              <Field label="Sector" value={lead.sector ?? "—"} />
              <Field label="Hunter" value={lead.hunter_status ?? "—"} />
              <Field label="Plan" value={lead.plan ?? "—"} />
              <Field label="Simulated?" value={lead.has_simulated ? `yes · P50=${lead.p50_survival ?? "?"}` : "no"} />
              <Field label="Last email" value={lead.last_email_at ? new Date(lead.last_email_at).toLocaleString() : "—"} />
            </div>

            {lead.hook && (
              <div>
                <p className="text-xs text-muted-foreground mb-1">Personalization hook</p>
                <p className="text-sm italic">&ldquo;{lead.hook}&rdquo;</p>
              </div>
            )}

            {lead.linkedin_url && (
              <a href={lead.linkedin_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sm text-primary hover:underline">
                LinkedIn <ExternalLink className="h-3 w-3" />
              </a>
            )}

            <div className="flex flex-wrap gap-2">
              <Button size="sm" onClick={() => actionMut.mutate({ action: "send_email", template_key: "cold_email_1" })} disabled={actionMut.isPending}>
                <Mail className="h-4 w-4 mr-1" /> Send email #1
              </Button>
              {lead.status === "paused" ? (
                <Button size="sm" variant="outline" onClick={() => actionMut.mutate({ action: "resume" })}>
                  <Play className="h-4 w-4 mr-1" /> Resume
                </Button>
              ) : (
                <Button size="sm" variant="outline" onClick={() => actionMut.mutate({ action: "pause" })}>
                  <Pause className="h-4 w-4 mr-1" /> Pause
                </Button>
              )}
              <Button size="sm" variant="outline" onClick={() => actionMut.mutate({ action: "mark_replied" })}>
                <Check className="h-4 w-4 mr-1" /> Mark replied
              </Button>
              <Button size="sm" variant="destructive" onClick={() => actionMut.mutate({ action: "mark_unsubscribed" })}>
                <Ban className="h-4 w-4 mr-1" /> Unsubscribe
              </Button>
            </div>

            <div>
              <h3 className="font-semibold mb-2">Timeline ({lead.recent_events.length})</h3>
              {lead.recent_events.length === 0 ? (
                <p className="text-sm text-muted-foreground">No events yet.</p>
              ) : (
                <ul className="space-y-2">
                  {lead.recent_events.map(e => (
                    <li key={e.id} className="text-sm border-l-2 border-muted pl-3 pb-2">
                      <div className="flex items-center justify-between">
                        <Badge variant="secondary" className="text-xs">{e.kind}</Badge>
                        <span className="text-xs text-muted-foreground">{new Date(e.created_at).toLocaleString()}</span>
                      </div>
                      {e.email_subject && <p className="text-xs text-muted-foreground mt-1">{e.email_subject}</p>}
                      {e.email_body_preview && <p className="text-xs mt-1 whitespace-pre-wrap">{e.email_body_preview}</p>}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-sm mt-0.5">{value}</div>
    </div>
  );
}
