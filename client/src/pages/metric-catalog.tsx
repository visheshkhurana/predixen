import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { useFounderStore } from "@/store/founderStore";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer } from "recharts";
import {
  Plus,
  Search,
  CheckCircle,
  AlertCircle,
  Clock,
  FileCode,
  Play,
  Upload,
  Trash2,
  Edit,
  Eye,
  RefreshCw,
  ChevronRight,
  TrendingUp,
  TrendingDown,
  Info,
  Activity,
  Database,
  GitBranch,
  Code,
  Archive,
} from "lucide-react";

interface MetricDefinition {
  id: number;
  company_id: number;
  key: string;
  name: string;
  description: string | null;
  definition: string | null;
  formula: string | null;
  source_connector: string | null;
  grain: string;
  unit: string | null;
  format_type: string;
  version: number;
  status: string;
  is_system: boolean;
  dependencies: any[] | null;
  config: any | null;
  tags: string[] | null;
  owners: string[] | null;
  created_at: string;
  updated_at: string | null;
  published_at: string | null;
  last_computed_at: string | null;
  latest_value: number | null;
}

interface MetricValue {
  period_start: string;
  period_end: string;
  value: number;
  computed_at: string | null;
  raw_event_count: number;
  contributing_connectors: string[] | null;
}

function formatValue(value: number, unit: string | null, format: string): string {
  if (value === null || value === undefined || isNaN(value)) return "—";
  
  if (format === "currency" || unit === "USD") {
    if (Math.abs(value) >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
    if (Math.abs(value) >= 1000) return `$${(value / 1000).toFixed(1)}K`;
    return `$${value.toFixed(0)}`;
  }
  
  if (format === "percentage" || unit === "%") {
    return `${value.toFixed(1)}%`;
  }
  
  if (Math.abs(value) >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
  if (Math.abs(value) >= 1000) return `${(value / 1000).toFixed(1)}K`;
  return value.toFixed(1);
}

function getStatusBadge(status: string) {
  switch (status) {
    case "certified":
      return <Badge className="bg-green-500/10 text-green-500 border-green-500/20"><CheckCircle className="h-3 w-3 mr-1" />Certified</Badge>;
    case "deprecated":
      return <Badge className="bg-red-500/10 text-red-500 border-red-500/20"><Archive className="h-3 w-3 mr-1" />Deprecated</Badge>;
    default:
      return <Badge variant="secondary"><Clock className="h-3 w-3 mr-1" />Draft</Badge>;
  }
}

function MetricCard({ metric, onClick }: { metric: MetricDefinition; onClick: () => void }) {
  return (
    <Card className="hover-elevate cursor-pointer" onClick={onClick} data-testid={`card-metric-${metric.key}`}>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-base truncate">{metric.name}</CardTitle>
            <CardDescription className="text-xs mt-1 truncate">{metric.key}</CardDescription>
          </div>
          {getStatusBadge(metric.status)}
        </div>
      </CardHeader>
      <CardContent className="pb-3">
        <div className="flex items-end justify-between gap-2">
          <div>
            <p className="text-2xl font-bold">
              {metric.latest_value !== null 
                ? formatValue(metric.latest_value, metric.unit, metric.format_type)
                : "—"
              }
            </p>
            {metric.last_computed_at && (
              <p className="text-xs text-muted-foreground mt-1">
                Updated {new Date(metric.last_computed_at).toLocaleDateString()}
              </p>
            )}
          </div>
          <div className="flex items-center gap-1">
            {metric.is_system && <Badge variant="outline" className="text-xs">System</Badge>}
            {metric.definition && <Badge variant="outline" className="text-xs">DSL</Badge>}
          </div>
        </div>
        {metric.tags && metric.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-3">
            {metric.tags.slice(0, 3).map(tag => (
              <Badge key={tag} variant="secondary" className="text-xs">{tag}</Badge>
            ))}
            {metric.tags.length > 3 && (
              <Badge variant="secondary" className="text-xs">+{metric.tags.length - 3}</Badge>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function MetricDetail({ metric, companyId, onClose }: { metric: MetricDefinition; companyId: number; onClose: () => void }) {
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState("overview");
  
  const { data: values, isLoading: valuesLoading } = useQuery<{ data: MetricValue[] }>({
    queryKey: ["/api/metrics", metric.key, "values", { company_id: companyId }],
  });
  
  const { data: lineage } = useQuery<any>({
    queryKey: ["/api/metrics", metric.key, "lineage", { company_id: companyId }],
    enabled: activeTab === "lineage",
  });
  
  const computeMutation = useMutation({
    mutationFn: () => apiRequest("POST", `/api/metrics/${metric.key}/compute?company_id=${companyId}`),
    onSuccess: () => {
      toast({ title: "Metric computed successfully" });
      queryClient.invalidateQueries({ queryKey: ["/api/metrics"] });
    },
    onError: (err: any) => {
      toast({ title: "Compute failed", description: err.message, variant: "destructive" });
    },
  });
  
  const publishMutation = useMutation({
    mutationFn: () => apiRequest("POST", `/api/metrics/${metric.key}/publish?company_id=${companyId}`),
    onSuccess: () => {
      toast({ title: "Metric published successfully" });
      queryClient.invalidateQueries({ queryKey: ["/api/metrics"] });
      onClose();
    },
    onError: (err: any) => {
      toast({ title: "Publish failed", description: err.message, variant: "destructive" });
    },
  });
  
  const validateMutation = useMutation({
    mutationFn: () => apiRequest("POST", `/api/metrics/${metric.key}/validate?company_id=${companyId}`),
    onSuccess: (data: any) => {
      if (data.is_valid) {
        toast({ title: "Definition is valid" });
      } else {
        toast({ title: "Validation issues found", description: JSON.stringify(data.validation_result?.issues || data.parse_error), variant: "destructive" });
      }
    },
    onError: (err: any) => {
      toast({ title: "Validation failed", description: err.message, variant: "destructive" });
    },
  });
  
  const chartData = values?.data?.map(v => ({
    date: new Date(v.period_start).toLocaleDateString("en-US", { month: "short", year: "2-digit" }),
    value: v.value,
  })) || [];
  
  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-2xl font-bold">{metric.name}</h2>
          <p className="text-muted-foreground">{metric.description || "No description"}</p>
          <div className="flex items-center gap-2 mt-2">
            {getStatusBadge(metric.status)}
            <Badge variant="outline">v{metric.version}</Badge>
            <Badge variant="outline">{metric.grain}</Badge>
            {metric.unit && <Badge variant="outline">{metric.unit}</Badge>}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {metric.definition && (
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => validateMutation.mutate()}
              disabled={validateMutation.isPending}
              data-testid="button-validate-metric"
            >
              <CheckCircle className="h-4 w-4 mr-1" />
              Validate
            </Button>
          )}
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => computeMutation.mutate()}
            disabled={computeMutation.isPending}
            data-testid="button-compute-metric"
          >
            <RefreshCw className={`h-4 w-4 mr-1 ${computeMutation.isPending ? "animate-spin" : ""}`} />
            Compute
          </Button>
          {!metric.is_system && metric.status === "draft" && (
            <Button 
              size="sm" 
              onClick={() => publishMutation.mutate()}
              disabled={publishMutation.isPending}
              data-testid="button-publish-metric"
            >
              <Upload className="h-4 w-4 mr-1" />
              Publish
            </Button>
          )}
        </div>
      </div>
      
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="definition">Definition</TabsTrigger>
          <TabsTrigger value="lineage">Lineage</TabsTrigger>
        </TabsList>
        
        <TabsContent value="overview" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Values Over Time</CardTitle>
            </CardHeader>
            <CardContent>
              {valuesLoading ? (
                <Skeleton className="h-64 w-full" />
              ) : chartData.length > 0 ? (
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis dataKey="date" className="text-xs" />
                      <YAxis className="text-xs" tickFormatter={(v) => formatValue(v, metric.unit, metric.format_type)} />
                      <RechartsTooltip 
                        formatter={(v: number) => [formatValue(v, metric.unit, metric.format_type), metric.name]}
                        contentStyle={{ backgroundColor: "hsl(var(--background))", border: "1px solid hsl(var(--border))" }}
                      />
                      <Line 
                        type="monotone" 
                        dataKey="value" 
                        stroke="hsl(var(--primary))" 
                        strokeWidth={2}
                        dot={{ fill: "hsl(var(--primary))" }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-64 flex items-center justify-center text-muted-foreground">
                  <div className="text-center">
                    <Activity className="h-12 w-12 mx-auto mb-2 opacity-50" />
                    <p>No computed values yet</p>
                    <p className="text-sm">Click "Compute" to generate values</p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
          
          {metric.dependencies && metric.dependencies.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Dependencies</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {metric.dependencies.map((dep: any, i: number) => (
                    <div key={i} className="flex items-center gap-2 p-2 rounded bg-muted/50">
                      <Database className="h-4 w-4 text-muted-foreground" />
                      <span className="font-medium">{dep.data_source_type}</span>
                      {dep.event_type && <Badge variant="outline" className="text-xs">{dep.event_type}</Badge>}
                      {dep.required && <Badge className="text-xs bg-amber-500/10 text-amber-500">Required</Badge>}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
        
        <TabsContent value="definition" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Code className="h-5 w-5" />
                {metric.definition ? "DSL Definition" : "Formula"}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {metric.definition ? (
                <pre className="p-4 rounded bg-muted/50 overflow-auto text-sm font-mono whitespace-pre-wrap">
                  {metric.definition}
                </pre>
              ) : metric.formula ? (
                <code className="block p-4 rounded bg-muted/50 font-mono">
                  {metric.formula}
                </code>
              ) : (
                <p className="text-muted-foreground">No definition or formula specified</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="lineage" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <GitBranch className="h-5 w-5" />
                Data Lineage
              </CardTitle>
            </CardHeader>
            <CardContent>
              {lineage ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-muted-foreground">Metric Version</p>
                      <p className="font-medium">v{lineage.metric_version}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Last Computed</p>
                      <p className="font-medium">{lineage.computed_at ? new Date(lineage.computed_at).toLocaleString() : "Never"}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Raw Events Used</p>
                      <p className="font-medium">{lineage.raw_event_count || 0}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Data Sources</p>
                      <p className="font-medium">{lineage.contributing_connectors?.join(", ") || "None"}</p>
                    </div>
                  </div>
                  {lineage.compiled_sql && (
                    <div className="mt-4">
                      <p className="text-sm text-muted-foreground mb-2">Compiled SQL</p>
                      <pre className="p-3 rounded bg-muted/50 overflow-auto text-xs font-mono">
                        {lineage.compiled_sql}
                      </pre>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-muted-foreground">No lineage data available. Compute the metric first.</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function CreateMetricDialog({ companyId, onCreated }: { companyId: number; onCreated: () => void }) {
  const { toast } = useToast();
  const [open, setOpen] = useState(false);
  const [key, setKey] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [formula, setFormula] = useState("");
  const [definition, setDefinition] = useState("");
  const [unit, setUnit] = useState("");
  const [grain, setGrain] = useState("monthly");
  const [mode, setMode] = useState<"formula" | "dsl">("formula");
  
  const createMutation = useMutation({
    mutationFn: (data: any) => apiRequest("POST", `/api/metrics?company_id=${companyId}`, data),
    onSuccess: () => {
      toast({ title: "Metric created successfully" });
      setOpen(false);
      resetForm();
      onCreated();
    },
    onError: (err: any) => {
      toast({ title: "Failed to create metric", description: err.message, variant: "destructive" });
    },
  });
  
  const resetForm = () => {
    setKey("");
    setName("");
    setDescription("");
    setFormula("");
    setDefinition("");
    setUnit("");
    setGrain("monthly");
    setMode("formula");
  };
  
  const handleSubmit = () => {
    if (!key || !name) {
      toast({ title: "Key and name are required", variant: "destructive" });
      return;
    }
    
    createMutation.mutate({
      key,
      name,
      description: description || null,
      formula: mode === "formula" ? formula : null,
      definition: mode === "dsl" ? definition : null,
      unit: unit || null,
      grain,
      format_type: unit === "USD" ? "currency" : unit === "%" ? "percentage" : "number",
    });
  };
  
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button data-testid="button-create-metric">
          <Plus className="h-4 w-4 mr-1" />
          Create Metric
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create New Metric</DialogTitle>
          <DialogDescription>Define a new metric for your company.</DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4 py-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="key">Key (slug)</Label>
              <Input 
                id="key" 
                value={key} 
                onChange={(e) => setKey(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, "_"))}
                placeholder="mrr, churn_rate, etc."
                data-testid="input-metric-key"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input 
                id="name" 
                value={name} 
                onChange={(e) => setName(e.target.value)}
                placeholder="Monthly Recurring Revenue"
                data-testid="input-metric-name"
              />
            </div>
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea 
              id="description" 
              value={description} 
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe what this metric measures..."
              rows={2}
              data-testid="input-metric-description"
            />
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="unit">Unit</Label>
              <Select value={unit} onValueChange={setUnit}>
                <SelectTrigger id="unit" data-testid="select-metric-unit">
                  <SelectValue placeholder="Select unit" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="USD">USD ($)</SelectItem>
                  <SelectItem value="%">Percentage (%)</SelectItem>
                  <SelectItem value="count">Count</SelectItem>
                  <SelectItem value="days">Days</SelectItem>
                  <SelectItem value="months">Months</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="grain">Grain</Label>
              <Select value={grain} onValueChange={setGrain}>
                <SelectTrigger id="grain" data-testid="select-metric-grain">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="daily">Daily</SelectItem>
                  <SelectItem value="weekly">Weekly</SelectItem>
                  <SelectItem value="monthly">Monthly</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          
          <div className="space-y-2">
            <Label>Definition Mode</Label>
            <Tabs value={mode} onValueChange={(v) => setMode(v as "formula" | "dsl")}>
              <TabsList className="w-full">
                <TabsTrigger value="formula" className="flex-1">Simple Formula</TabsTrigger>
                <TabsTrigger value="dsl" className="flex-1">YAML DSL</TabsTrigger>
              </TabsList>
              
              <TabsContent value="formula" className="mt-2">
                <Input 
                  value={formula} 
                  onChange={(e) => setFormula(e.target.value)}
                  placeholder='sum(amount), avg(price), count()'
                  data-testid="input-metric-formula"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Supported: sum, avg, count, min, max. Use "where" for filters: sum(amount) where status == "paid"
                </p>
              </TabsContent>
              
              <TabsContent value="dsl" className="mt-2">
                <Textarea 
                  value={definition} 
                  onChange={(e) => setDefinition(e.target.value)}
                  placeholder={`meta:
  id: ${key || "my_metric"}
  name: ${name || "My Metric"}
  grain: monthly

logic:
  type: aggregate
  measures:
    - name: value
      agg: sum
      field: amount`}
                  rows={12}
                  className="font-mono text-sm"
                  data-testid="input-metric-definition"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Full YAML DSL with meta, dependencies, mapping, logic, and postprocess sections.
                </p>
              </TabsContent>
            </Tabs>
          </div>
        </div>
        
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
          <Button onClick={handleSubmit} disabled={createMutation.isPending} data-testid="button-submit-metric">
            {createMutation.isPending ? "Creating..." : "Create Metric"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function MetricCatalog() {
  const { currentCompany } = useFounderStore();
  const { toast } = useToast();
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selectedMetric, setSelectedMetric] = useState<MetricDefinition | null>(null);
  
  const companyId = currentCompany?.id;
  
  const { data: metrics, isLoading, refetch } = useQuery<MetricDefinition[]>({
    queryKey: ["/api/metrics", { company_id: companyId }],
    enabled: !!companyId,
  });
  
  const initializeMutation = useMutation({
    mutationFn: () => apiRequest("POST", `/api/metrics/initialize?company_id=${companyId}`),
    onSuccess: (data: any) => {
      toast({ title: `Initialized ${data.created_count} system metrics` });
      refetch();
    },
    onError: (err: any) => {
      toast({ title: "Initialization failed", description: err.message, variant: "destructive" });
    },
  });
  
  const filteredMetrics = metrics?.filter(m => {
    const matchesSearch = !searchQuery || 
      m.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.key.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.description?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === "all" || m.status === statusFilter;
    return matchesSearch && matchesStatus;
  }) || [];
  
  if (!companyId) {
    return (
      <div className="container mx-auto py-8">
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">Please select a company to view metrics.</p>
          </CardContent>
        </Card>
      </div>
    );
  }
  
  if (selectedMetric) {
    return (
      <div className="container mx-auto py-6 space-y-4">
        <Button variant="ghost" onClick={() => setSelectedMetric(null)} data-testid="button-back-to-catalog">
          <ChevronRight className="h-4 w-4 mr-1 rotate-180" />
          Back to Catalog
        </Button>
        <MetricDetail metric={selectedMetric} companyId={companyId} onClose={() => setSelectedMetric(null)} />
      </div>
    );
  }
  
  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold">Metric Catalog</h1>
          <p className="text-muted-foreground">Define, compute, and manage your business metrics</p>
        </div>
        <div className="flex items-center gap-2">
          {(!metrics || metrics.length === 0) && (
            <Button 
              variant="outline" 
              onClick={() => initializeMutation.mutate()}
              disabled={initializeMutation.isPending}
              data-testid="button-initialize-metrics"
            >
              <Database className="h-4 w-4 mr-1" />
              Initialize System Metrics
            </Button>
          )}
          <CreateMetricDialog companyId={companyId} onCreated={() => refetch()} />
        </div>
      </div>
      
      <div className="flex items-center gap-4 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input 
            placeholder="Search metrics..." 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
            data-testid="input-search-metrics"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[150px]" data-testid="select-status-filter">
            <SelectValue placeholder="All Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="draft">Draft</SelectItem>
            <SelectItem value="certified">Certified</SelectItem>
            <SelectItem value="deprecated">Deprecated</SelectItem>
          </SelectContent>
        </Select>
      </div>
      
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-48" />
          ))}
        </div>
      ) : filteredMetrics.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filteredMetrics.map(metric => (
            <MetricCard 
              key={metric.id} 
              metric={metric} 
              onClick={() => setSelectedMetric(metric)}
            />
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <FileCode className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <h3 className="text-lg font-semibold mb-2">No Metrics Found</h3>
            <p className="text-muted-foreground mb-4">
              {searchQuery || statusFilter !== "all"
                ? "No metrics match your search criteria."
                : "Get started by creating your first metric or initializing system metrics."}
            </p>
            {!searchQuery && statusFilter === "all" && (
              <div className="flex items-center justify-center gap-2">
                <Button variant="outline" onClick={() => initializeMutation.mutate()} data-testid="button-init-empty">
                  <Database className="h-4 w-4 mr-1" />
                  Initialize System Metrics
                </Button>
                <CreateMetricDialog companyId={companyId} onCreated={() => refetch()} />
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
