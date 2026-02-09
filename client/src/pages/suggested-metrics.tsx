import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { useFounderStore } from "@/store/founderStore";
import { apiRequest, queryClient } from "@/lib/queryClient";
import {
  Sparkles,
  Search,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  Play,
  Eye,
  RefreshCw,
  TrendingUp,
  DollarSign,
  Users,
  BarChart3,
  Zap,
  Info,
  Database,
  Code,
} from "lucide-react";

interface Suggestion {
  id: number;
  company_id: number;
  data_source_id: number | null;
  suggestion_key: string;
  title: string;
  description: string;
  category: string;
  metric_dsl_yaml: string;
  dependencies: any[];
  confidence_score: number;
  reason: any;
  status: string;
  accepted_metric_id: number | null;
  created_at: string;
  updated_at: string;
}

function getStatusBadge(status: string) {
  switch (status) {
    case "new":
      return <Badge variant="default" data-testid="badge-status-new"><Sparkles className="h-3 w-3 mr-1" />New</Badge>;
    case "accepted":
      return <Badge variant="secondary" data-testid="badge-status-accepted"><CheckCircle className="h-3 w-3 mr-1" />Accepted</Badge>;
    case "dismissed":
      return <Badge variant="outline" data-testid="badge-status-dismissed"><XCircle className="h-3 w-3 mr-1" />Dismissed</Badge>;
    case "blocked":
      return <Badge variant="destructive" data-testid="badge-status-blocked"><AlertTriangle className="h-3 w-3 mr-1" />Blocked</Badge>;
    default:
      return <Badge variant="secondary"><Clock className="h-3 w-3 mr-1" />{status}</Badge>;
  }
}

function getConfidenceBadge(score: number) {
  if (score >= 90) {
    return <Badge variant="default" className="text-xs" data-testid="badge-confidence-high">High Confidence</Badge>;
  } else if (score >= 70) {
    return <Badge variant="secondary" className="text-xs" data-testid="badge-confidence-medium">Medium Confidence</Badge>;
  } else {
    return <Badge variant="outline" className="text-xs" data-testid="badge-confidence-low">Low Confidence</Badge>;
  }
}

function getCategoryIcon(category: string) {
  switch (category) {
    case "Finance":
      return <DollarSign className="h-4 w-4" />;
    case "Growth":
      return <TrendingUp className="h-4 w-4" />;
    case "Product":
      return <BarChart3 className="h-4 w-4" />;
    case "Sales":
      return <Users className="h-4 w-4" />;
    default:
      return <Zap className="h-4 w-4" />;
  }
}

function SuggestionCard({
  suggestion,
  onAccept,
  onDismiss,
  onExplain,
  isAccepting,
}: {
  suggestion: Suggestion;
  onAccept: (id: number, autoCompute: boolean) => void;
  onDismiss: (id: number) => void;
  onExplain: (id: number) => void;
  isAccepting: boolean;
}) {
  const isActionable = suggestion.status === "new";
  const isBlocked = suggestion.status === "blocked";
  
  return (
    <Card className="hover-elevate" data-testid={`card-suggestion-${suggestion.suggestion_key}`}>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            {getCategoryIcon(suggestion.category)}
            <div>
              <CardTitle className="text-base">{suggestion.title}</CardTitle>
              <CardDescription className="text-xs mt-1">{suggestion.category}</CardDescription>
            </div>
          </div>
          <div className="flex flex-col items-end gap-1">
            {getStatusBadge(suggestion.status)}
            {getConfidenceBadge(suggestion.confidence_score)}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted-foreground line-clamp-2" data-testid={`text-description-${suggestion.id}`}>
          {suggestion.description}
        </p>
        
        {isBlocked && suggestion.reason?.blocked_by && (
          <div className="p-2 rounded bg-destructive/10 text-destructive text-xs" data-testid={`alert-blocked-${suggestion.id}`}>
            <AlertTriangle className="h-3 w-3 inline mr-1" />
            Missing: {suggestion.reason.blocked_by.join(", ")}
          </div>
        )}
        
        {suggestion.dependencies && suggestion.dependencies.length > 0 && (
          <div className="flex flex-wrap gap-1" data-testid={`dependencies-${suggestion.id}`}>
            {suggestion.dependencies.slice(0, 3).map((dep, i) => (
              <Badge key={i} variant="outline" className="text-xs" data-testid={`badge-dep-${suggestion.id}-${i}`}>
                {dep.data_source_type || dep.metric || "dependency"}
              </Badge>
            ))}
          </div>
        )}
        
        <div className="flex items-center gap-2 pt-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onExplain(suggestion.id)}
            data-testid={`button-explain-${suggestion.id}`}
          >
            <Eye className="h-4 w-4 mr-1" />
            Explain
          </Button>
          
          {isActionable && (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onDismiss(suggestion.id)}
                data-testid={`button-dismiss-${suggestion.id}`}
              >
                <XCircle className="h-4 w-4 mr-1" />
                Dismiss
              </Button>
              <Button
                size="sm"
                onClick={() => onAccept(suggestion.id, false)}
                disabled={isAccepting}
                data-testid={`button-accept-${suggestion.id}`}
              >
                <CheckCircle className="h-4 w-4 mr-1" />
                Accept
              </Button>
              <Button
                size="sm"
                variant="default"
                onClick={() => onAccept(suggestion.id, true)}
                disabled={isAccepting}
                data-testid={`button-accept-compute-${suggestion.id}`}
              >
                <Play className="h-4 w-4 mr-1" />
                Accept & Compute
              </Button>
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function ExplainDrawer({
  suggestionId,
  companyId,
  open,
  onClose,
}: {
  suggestionId: number | null;
  companyId: number;
  open: boolean;
  onClose: () => void;
}) {
  const { data: explanation, isLoading } = useQuery<any>({
    queryKey: ["/api/suggestions", suggestionId, "explain", companyId],
    queryFn: async () => {
      const res = await fetch(`/api/suggestions/${suggestionId}/explain?company_id=${companyId}`);
      if (!res.ok) throw new Error("Failed to fetch explanation");
      return res.json();
    },
    enabled: !!suggestionId && open,
  });
  
  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent className="w-[500px] sm:w-[600px] overflow-y-auto">
        <SheetHeader>
          <SheetTitle data-testid="text-explain-title">{explanation?.title || "Suggestion Details"}</SheetTitle>
          <SheetDescription>{explanation?.description}</SheetDescription>
        </SheetHeader>
        
        {isLoading ? (
          <div className="space-y-4 mt-6">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-40 w-full" />
            <Skeleton className="h-60 w-full" />
          </div>
        ) : explanation ? (
          <div className="space-y-6 mt-6">
            <div>
              <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                <Info className="h-4 w-4" />
                Why Suggested
              </h4>
              <div className="p-3 rounded bg-muted/50 space-y-2">
                <p className="text-sm"><strong>Trigger:</strong> {explanation.reason?.trigger}</p>
                {explanation.reason?.fields_used?.length > 0 && (
                  <p className="text-sm"><strong>Fields Used:</strong> {explanation.reason.fields_used.join(", ")}</p>
                )}
                {explanation.reason?.assumptions?.length > 0 && (
                  <div>
                    <p className="text-sm font-medium">Assumptions:</p>
                    <ul className="list-disc list-inside text-sm text-muted-foreground">
                      {explanation.reason.assumptions.map((a: string, i: number) => (
                        <li key={i}>{a}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
            
            <div>
              <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                <Database className="h-4 w-4" />
                Dependencies
              </h4>
              <div className="space-y-2">
                {explanation.dependencies?.map((dep: any, i: number) => (
                  <div key={i} className="p-2 rounded bg-muted/50 flex items-center gap-2">
                    <Badge variant="outline">
                      {dep.data_source_type || dep.metric || dep.config || "Required"}
                    </Badge>
                    {dep.required && <Badge variant="secondary" className="text-xs">Required</Badge>}
                  </div>
                ))}
              </div>
            </div>
            
            <div>
              <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                <Code className="h-4 w-4" />
                Metric DSL Definition
              </h4>
              <pre className="p-3 rounded bg-muted/50 overflow-auto text-xs font-mono whitespace-pre-wrap max-h-[300px]" data-testid="text-dsl-yaml">
                {explanation.metric_dsl_yaml}
              </pre>
            </div>
            
            {explanation.compiled_sql_preview && (
              <div>
                <h4 className="text-sm font-medium mb-2">Compiled SQL Preview</h4>
                <pre className="p-3 rounded bg-muted/50 overflow-auto text-xs font-mono whitespace-pre-wrap max-h-[200px]" data-testid="text-compiled-sql">
                  {explanation.compiled_sql_preview}
                </pre>
              </div>
            )}
          </div>
        ) : null}
      </SheetContent>
    </Sheet>
  );
}

export default function SuggestedMetrics() {
  const { currentCompany } = useFounderStore();
  const { toast } = useToast();
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("new");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [explainId, setExplainId] = useState<number | null>(null);
  
  const companyId = currentCompany?.id;
  
  const { data: suggestions, isLoading, refetch } = useQuery<Suggestion[]>({
    queryKey: ["/api/suggestions", companyId, statusFilter],
    queryFn: async () => {
      const params = new URLSearchParams({ company_id: String(companyId) });
      if (statusFilter && statusFilter !== "all") params.append("status", statusFilter);
      const token = localStorage.getItem('predixen-token');
      const headers: Record<string, string> = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const res = await fetch(`/api/suggestions?${params}`, { headers, credentials: 'include' });
      if (!res.ok) throw new Error("Failed to fetch suggestions");
      return res.json();
    },
    enabled: !!companyId,
  });
  
  const generateMutation = useMutation({
    mutationFn: async () => {
      if (!companyId) throw new Error("No company selected");
      const token = localStorage.getItem('predixen-token');
      const headers: Record<string, string> = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      headers['Content-Type'] = 'application/json';
      const res = await fetch(`/api/suggestions/generate?company_id=${companyId}`, {
        method: 'POST',
        headers,
        credentials: 'include',
        body: JSON.stringify({ force_refresh: false }),
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `${res.status} ${res.statusText}`);
      }
      return res.json();
    },
    onSuccess: (data: any) => {
      const count = data.generated_count ?? data.suggestions?.length ?? 0;
      toast({ title: "Suggestions Generated", description: `${count} metric suggestions are ready for review.` });
      queryClient.invalidateQueries({ queryKey: ["/api/suggestions"] });
      refetch();
    },
    onError: (err: any) => {
      toast({ title: "Failed to generate suggestions", description: err?.message || "Please try again", variant: "destructive" });
    },
  });
  
  const acceptMutation = useMutation({
    mutationFn: async ({ id, autoCompute }: { id: number; autoCompute: boolean }) => {
      const res = await apiRequest("POST", `/api/suggestions/${id}/accept?company_id=${companyId}`, { auto_compute: autoCompute });
      return res.json();
    },
    onSuccess: (data: any) => {
      toast({ title: `Created metric: ${data.metric?.name ?? 'metric'}` });
      queryClient.invalidateQueries({ queryKey: ["/api/suggestions"] });
      queryClient.invalidateQueries({ queryKey: ["/api/metrics"] });
      refetch();
    },
    onError: (err: any) => {
      toast({ title: "Failed to accept suggestion", description: err.message, variant: "destructive" });
    },
  });
  
  const dismissMutation = useMutation({
    mutationFn: (id: number) => apiRequest("POST", `/api/suggestions/${id}/dismiss?company_id=${companyId}`, {}),
    onSuccess: () => {
      toast({ title: "Suggestion dismissed" });
      queryClient.invalidateQueries({ queryKey: ["/api/suggestions"] });
      refetch();
    },
    onError: (err: any) => {
      toast({ title: "Failed to dismiss", description: err.message, variant: "destructive" });
    },
  });
  
  const filteredSuggestions = suggestions?.filter(s => {
    const matchesSearch = !searchQuery ||
      s.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.description?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = categoryFilter === "all" || s.category === categoryFilter;
    return matchesSearch && matchesCategory;
  }) || [];
  
  const groupedByCategory = filteredSuggestions.reduce((acc, s) => {
    if (!acc[s.category]) acc[s.category] = [];
    acc[s.category].push(s);
    return acc;
  }, {} as Record<string, Suggestion[]>);
  
  if (!companyId) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">Please select a company to view suggestions.</p>
          </CardContent>
        </Card>
      </div>
    );
  }
  
  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2" data-testid="text-page-title">
            <Sparkles className="h-6 w-6" />
            Suggested Metrics
          </h1>
          <p className="text-muted-foreground">AI-detected metrics from your connected data sources</p>
        </div>
        <Button
          onClick={() => generateMutation.mutate()}
          disabled={generateMutation.isPending || !companyId}
          data-testid="button-generate-suggestions"
        >
          <RefreshCw className={`h-4 w-4 mr-1 ${generateMutation.isPending ? "animate-spin" : ""}`} />
          {generateMutation.isPending ? "Generating..." : "Generate Suggestions"}
        </Button>
      </div>
      
      <div className="flex items-center gap-4 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search suggestions..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
            data-testid="input-search-suggestions"
          />
        </div>
        <Tabs value={statusFilter} onValueChange={setStatusFilter}>
          <TabsList>
            <TabsTrigger value="new" data-testid="tab-status-new">New</TabsTrigger>
            <TabsTrigger value="blocked" data-testid="tab-status-blocked">Blocked</TabsTrigger>
            <TabsTrigger value="accepted" data-testid="tab-status-accepted">Accepted</TabsTrigger>
            <TabsTrigger value="dismissed" data-testid="tab-status-dismissed">Dismissed</TabsTrigger>
            <TabsTrigger value="all" data-testid="tab-status-all">All</TabsTrigger>
          </TabsList>
        </Tabs>
        <Select value={categoryFilter} onValueChange={setCategoryFilter}>
          <SelectTrigger className="w-[150px]" data-testid="select-category-filter">
            <SelectValue placeholder="All Categories" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all" data-testid="select-item-all">All Categories</SelectItem>
            <SelectItem value="Finance" data-testid="select-item-finance">Finance</SelectItem>
            <SelectItem value="Growth" data-testid="select-item-growth">Growth</SelectItem>
            <SelectItem value="Product" data-testid="select-item-product">Product</SelectItem>
            <SelectItem value="Sales" data-testid="select-item-sales">Sales</SelectItem>
          </SelectContent>
        </Select>
      </div>
      
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-48" />
          ))}
        </div>
      ) : filteredSuggestions.length > 0 ? (
        <div className="space-y-8">
          {Object.entries(groupedByCategory).map(([category, categorySuggestions]) => (
            <div key={category}>
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                {getCategoryIcon(category)}
                {category}
                <Badge variant="secondary" className="ml-2">{categorySuggestions.length}</Badge>
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {categorySuggestions.map(suggestion => (
                  <SuggestionCard
                    key={suggestion.id}
                    suggestion={suggestion}
                    onAccept={(id, autoCompute) => acceptMutation.mutate({ id, autoCompute })}
                    onDismiss={(id) => dismissMutation.mutate(id)}
                    onExplain={(id) => setExplainId(id)}
                    isAccepting={acceptMutation.isPending}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <Sparkles className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <h3 className="text-lg font-semibold mb-2">No Suggestions Found</h3>
            <p className="text-muted-foreground mb-4">
              {searchQuery || categoryFilter !== "all"
                ? "No suggestions match your filters."
                : "Connect a data source and generate suggestions to get started."}
            </p>
            <Button onClick={() => generateMutation.mutate()} disabled={!companyId} data-testid="button-generate-empty">
              <RefreshCw className="h-4 w-4 mr-1" />
              Generate Suggestions
            </Button>
          </CardContent>
        </Card>
      )}
      
      <ExplainDrawer
        suggestionId={explainId}
        companyId={companyId}
        open={!!explainId}
        onClose={() => setExplainId(null)}
      />
    </div>
  );
}
