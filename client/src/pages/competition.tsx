import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { useFounderStore } from "@/store/founderStore";
import { useToast } from "@/hooks/use-toast";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Target, Plus, RefreshCw, Trash2, ExternalLink, Globe, Linkedin,
  Newspaper, ChevronDown, ChevronRight, Rss, X as XIcon, Sparkles,
} from "lucide-react";

interface Competitor {
  id: number;
  name: string;
  website?: string | null;
  blog_url?: string | null;
  linkedin_url?: string | null;
  x_handle?: string | null;
  description?: string | null;
  signal_count: number;
  unread_count?: number;
  last_scanned_at?: string | null;
}

interface Signal {
  id: number;
  source_type: string;
  title?: string | null;
  url?: string | null;
  summary?: string | null;
  sentiment?: string | null;
  threat_level?: string | null;
  impact?: string | null;
  created_at?: string | null;
}

const threatBadge = (t?: string | null) => {
  if (t === "high") return "text-red-500 border-red-500/40 bg-red-500/10";
  if (t === "low") return "text-emerald-500 border-emerald-500/30 bg-emerald-500/10";
  return "text-amber-500 border-amber-500/30 bg-amber-500/10"; // medium / default
};

const sourceIcon = (t: string) => {
  switch (t) {
    case "news": return <Newspaper className="h-3.5 w-3.5" />;
    case "blog": return <Rss className="h-3.5 w-3.5" />;
    case "linkedin": return <Linkedin className="h-3.5 w-3.5" />;
    case "x": return <XIcon className="h-3.5 w-3.5" />;
    default: return <Globe className="h-3.5 w-3.5" />;
  }
};

const sentimentColor = (s?: string | null) => {
  if (s === "positive") return "text-emerald-500 border-emerald-500/30 bg-emerald-500/10";
  if (s === "negative") return "text-red-500 border-red-500/30 bg-red-500/10";
  return "text-muted-foreground border-border bg-muted/30";
};

function SignalsFeed({ companyId, competitorId }: { companyId: number; competitorId: number }) {
  const { toast } = useToast();
  const { data, isLoading } = useQuery({
    queryKey: ["/api/companies", companyId, "competitors", competitorId, "signals"],
    enabled: !!companyId,
    queryFn: async () => {
      const res = await apiRequest("GET", `/api/companies/${companyId}/competitors/${competitorId}/signals`);
      return res.json();
    },
  });

  const decisionMut = useMutation({
    mutationFn: async (signalId: number) => {
      const res = await apiRequest("POST", `/api/companies/${companyId}/competitors/signals/${signalId}/to-decision`);
      return res.json();
    },
    onSuccess: () => toast({ title: "Tracked as a Decision", description: "Find it under Decisions." }),
    onError: () => toast({ title: "Couldn't create decision", variant: "destructive" }),
  });

  if (isLoading) return <div className="p-4"><Skeleton className="h-16 w-full" /></div>;
  const signals: Signal[] = data?.signals || [];
  if (signals.length === 0) {
    return <p className="text-sm text-muted-foreground p-4">No signals yet — hit <b>Scan</b> to pull the latest news, blog posts and social activity.</p>;
  }
  return (
    <div className="divide-y divide-border">
      {signals.map((s) => (
        <div key={s.id} className="p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1 flex-wrap">
                <Badge variant="outline" className="gap-1 text-[10px] uppercase">{sourceIcon(s.source_type)}{s.source_type}</Badge>
                {s.threat_level && <Badge variant="outline" className={`text-[10px] uppercase ${threatBadge(s.threat_level)}`}>{s.threat_level} threat</Badge>}
                {s.sentiment && s.sentiment !== "neutral" && <Badge variant="outline" className={`text-[10px] ${sentimentColor(s.sentiment)}`}>for them: {s.sentiment}</Badge>}
              </div>
              <p className="font-medium text-sm">{s.title || s.summary}</p>
              {s.summary && s.title && <p className="text-sm text-muted-foreground mt-0.5">{s.summary}</p>}
              {s.impact && <p className="text-xs text-primary mt-1">Why it matters: {s.impact}</p>}
              <Button
                size="sm"
                variant="ghost"
                className="h-7 px-2 mt-1 text-xs text-muted-foreground hover:text-foreground"
                onClick={() => decisionMut.mutate(s.id)}
                disabled={decisionMut.isPending}
                data-testid={`track-decision-${s.id}`}
              >
                <Plus className="h-3 w-3 mr-1" /> Track as Decision
              </Button>
            </div>
            {s.url && (
              <a href={s.url} target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-foreground shrink-0">
                <ExternalLink className="h-4 w-4" />
              </a>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function CompetitionPage() {
  const { currentCompany } = useFounderStore();
  const companyId = currentCompany?.id;
  const { toast } = useToast();
  const [showAdd, setShowAdd] = useState(false);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [form, setForm] = useState({ name: "", website: "", blog_url: "", linkedin_url: "", x_handle: "", description: "" });

  const competitorsQuery = useQuery({
    queryKey: ["/api/companies", companyId, "competitors"],
    enabled: !!companyId,
    queryFn: async () => {
      const res = await apiRequest("GET", `/api/companies/${companyId}/competitors`);
      return res.json();
    },
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["/api/companies", companyId, "competitors"] });

  const createMut = useMutation({
    mutationFn: async () => {
      const res = await apiRequest("POST", `/api/companies/${companyId}/competitors`, form);
      return res.json();
    },
    onSuccess: () => {
      invalidate();
      setForm({ name: "", website: "", blog_url: "", linkedin_url: "", x_handle: "", description: "" });
      setShowAdd(false);
      toast({ title: "Competitor added" });
    },
    onError: () => toast({ title: "Couldn't add competitor", variant: "destructive" }),
  });

  const deleteMut = useMutation({
    mutationFn: async (id: number) => apiRequest("DELETE", `/api/companies/${companyId}/competitors/${id}`),
    onSuccess: () => { invalidate(); toast({ title: "Competitor removed" }); },
  });

  const scanMut = useMutation({
    mutationFn: async (id: number) => {
      const res = await apiRequest("POST", `/api/companies/${companyId}/competitors/${id}/scan`);
      return res.json();
    },
    onSuccess: (data: any, id: number) => {
      queryClient.invalidateQueries({ queryKey: ["/api/companies", companyId, "competitors", id, "signals"] });
      invalidate();
      setExpanded(id);
      toast({ title: data.added > 0 ? `${data.added} new signal${data.added === 1 ? "" : "s"} found` : "Up to date — no new signals" });
    },
    onError: () => toast({ title: "Scan failed", description: "Web search is temporarily unavailable.", variant: "destructive" }),
  });

  const digestMut = useMutation({
    mutationFn: async () => {
      const res = await apiRequest("GET", `/api/companies/${companyId}/competitors/digest`);
      return res.json();
    },
    onError: () => toast({ title: "Couldn't generate digest", variant: "destructive" }),
  });

  const competitors: Competitor[] = competitorsQuery.data?.competitors || [];
  const totalSignals = competitors.reduce((n, c) => n + (c.signal_count || 0), 0);

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2"><Target className="h-6 w-6 text-primary" /> Competition</h1>
          <p className="text-muted-foreground">Track your competitors' news, blog posts and social activity in one feed.</p>
        </div>
        <Button onClick={() => setShowAdd((v) => !v)} data-testid="button-add-competitor">
          <Plus className="h-4 w-4 mr-1" /> Add Competitor
        </Button>
      </div>

      {showAdd && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Add a competitor</CardTitle>
            <CardDescription>Name is required. Add links so scans can find the right sources.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid md:grid-cols-2 gap-3">
              <Input placeholder="Competitor name *" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="input-competitor-name" />
              <Input placeholder="Website (https://...)" value={form.website} onChange={(e) => setForm({ ...form, website: e.target.value })} />
              <Input placeholder="Blog URL" value={form.blog_url} onChange={(e) => setForm({ ...form, blog_url: e.target.value })} />
              <Input placeholder="LinkedIn URL" value={form.linkedin_url} onChange={(e) => setForm({ ...form, linkedin_url: e.target.value })} />
              <Input placeholder="X / Twitter (@handle)" value={form.x_handle} onChange={(e) => setForm({ ...form, x_handle: e.target.value })} />
              <Input placeholder="What they do (optional)" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </div>
            <div className="flex gap-2">
              <Button onClick={() => createMut.mutate()} disabled={!form.name.trim() || createMut.isPending}>
                {createMut.isPending ? "Adding…" : "Add"}
              </Button>
              <Button variant="outline" onClick={() => setShowAdd(false)}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {competitors.length > 0 && (
        <Card className="border-primary/30 bg-primary/5">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between gap-3">
              <CardTitle className="text-base flex items-center gap-2"><Sparkles className="h-4 w-4 text-primary" /> Competitor Digest</CardTitle>
              <Button size="sm" variant="outline" onClick={() => digestMut.mutate()} disabled={digestMut.isPending || totalSignals === 0} data-testid="button-digest">
                <RefreshCw className={`h-4 w-4 mr-1 ${digestMut.isPending ? "animate-spin" : ""}`} />
                {digestMut.data?.digest ? "Refresh" : "Generate"}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {digestMut.isPending ? (
              <div className="space-y-2"><Skeleton className="h-4 w-full" /><Skeleton className="h-4 w-11/12" /><Skeleton className="h-4 w-3/4" /></div>
            ) : digestMut.data?.digest ? (
              <p className="text-sm leading-relaxed">{digestMut.data.digest}</p>
            ) : (
              <p className="text-sm text-muted-foreground">
                {totalSignals === 0 ? "Scan a competitor first, then generate a one-paragraph brief on what's changed." : "Get a one-paragraph AI brief on what's changed across all your competitors."}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {competitorsQuery.isLoading ? (
        <div className="space-y-3">{[1, 2].map((i) => <Skeleton key={i} className="h-20 w-full" />)}</div>
      ) : competitors.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Target className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
            <p className="font-medium">No competitors tracked yet</p>
            <p className="text-sm text-muted-foreground mb-4">Add your first competitor to start tracking their moves.</p>
            <Button onClick={() => setShowAdd(true)}><Plus className="h-4 w-4 mr-1" /> Add Competitor</Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {competitors.map((c) => (
            <Card key={c.id} data-testid={`competitor-${c.id}`}>
              <div className="p-4 flex items-center justify-between gap-3">
                <button className="flex items-center gap-2 text-left flex-1" onClick={() => {
                  const willExpand = expanded !== c.id;
                  setExpanded(willExpand ? c.id : null);
                  if (willExpand) setTimeout(() => invalidate(), 900);
                }}>
                  {expanded === c.id ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                  <div>
                    <div className="font-semibold flex items-center gap-2">
                      {c.name}
                      {(c.unread_count ?? 0) > 0 && <Badge className="bg-primary text-primary-foreground">{c.unread_count} new</Badge>}
                      {c.signal_count > 0 && <Badge variant="secondary">{c.signal_count} signals</Badge>}
                    </div>
                    {c.description && <p className="text-xs text-muted-foreground">{c.description}</p>}
                  </div>
                </button>
                <div className="flex items-center gap-1 shrink-0">
                  {c.website && <a href={c.website} target="_blank" rel="noopener noreferrer" className="p-2 text-muted-foreground hover:text-foreground"><Globe className="h-4 w-4" /></a>}
                  {c.linkedin_url && <a href={c.linkedin_url} target="_blank" rel="noopener noreferrer" className="p-2 text-muted-foreground hover:text-foreground"><Linkedin className="h-4 w-4" /></a>}
                  <Button size="sm" variant="outline" onClick={() => scanMut.mutate(c.id)} disabled={scanMut.isPending} data-testid={`scan-${c.id}`}>
                    <RefreshCw className={`h-4 w-4 mr-1 ${scanMut.isPending && scanMut.variables === c.id ? "animate-spin" : ""}`} /> Scan
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => deleteMut.mutate(c.id)} className="text-muted-foreground hover:text-red-500">
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              {expanded === c.id && (
                <div className="border-t border-border">
                  {companyId && <SignalsFeed companyId={companyId} competitorId={c.id} />}
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
