import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useLocation } from "wouter";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { AlertCircle, CheckCircle, AlertTriangle, Info, ChevronRight, Loader2, Shield, Database, TrendingUp, Wallet, Zap, FileCheck, RefreshCw } from "lucide-react";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";
import { formatCurrencyAbbrev } from "@/lib/utils";

interface TruthScanUploadResponse {
  upload_id: string;
  company_id: number;
  source_kind: string;
  status: string;
  created_at: string | null;
  truth_dataset: {
    id: string | null;
    version: number | null;
    finalized: boolean;
    assumptions: Record<string, any>;
    coverage: Record<string, number>;
    confidence: Record<string, any>;
  };
  latest_month_metrics: Record<string, any>;
  issues: {
    auto_fixed: Issue[];
    needs_confirmation: Issue[];
    blocked: Issue[];
  };
  questions: Question[];
  can_finalize: boolean;
}

interface Issue {
  id: string;
  severity: string;
  category: string;
  metric_key: string;
  message: string;
  evidence: Record<string, any>;
  suggestion: { options?: string[] } | null;
  status: string;
}

interface Question {
  issue_id: string;
  question: string;
  options: string[];
  metric_key: string;
}

interface TruthScanGateProps {
  uploadId: string;
  companyId: number;
  onComplete?: () => void;
  isDialog?: boolean;
  onClose?: () => void;
}

function getSeverityColor(severity: string): string {
  switch (severity) {
    case "blocked":
      return "bg-red-500/10 text-red-600 border-red-500/20";
    case "high":
      return "bg-orange-500/10 text-orange-600 border-orange-500/20";
    case "medium":
      return "bg-yellow-500/10 text-yellow-600 border-yellow-500/20";
    case "low":
      return "bg-blue-500/10 text-blue-600 border-blue-500/20";
    default:
      return "bg-muted text-muted-foreground";
  }
}

function getSeverityIcon(severity: string) {
  switch (severity) {
    case "blocked":
      return <AlertCircle className="h-4 w-4 text-red-500" />;
    case "high":
      return <AlertTriangle className="h-4 w-4 text-orange-500" />;
    case "medium":
      return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
    case "low":
      return <Info className="h-4 w-4 text-blue-500" />;
    default:
      return <Info className="h-4 w-4" />;
  }
}

export function TruthScanGate({ uploadId, companyId, onComplete, isDialog = false, onClose }: TruthScanGateProps) {
  const [, setLocation] = useLocation();
  const { toast } = useToast();
  const [selectedAnswers, setSelectedAnswers] = useState<Record<string, string>>({});

  const { data: uploadData, isLoading, refetch } = useQuery<TruthScanUploadResponse>({
    queryKey: ["/api/truth-scan/uploads", uploadId],
    enabled: !!uploadId,
  });

  const resolveMutation = useMutation({
    mutationFn: async (answers: Array<{ issue_id: string; choice: string }>) => {
      const response = await apiRequest("POST", `/api/truth-scan/uploads/${uploadId}/resolve`, {
        answers,
      });
      return response.json();
    },
    onSuccess: () => {
      toast({ title: "Issues resolved", description: "Your answers have been saved." });
      refetch();
      setSelectedAnswers({});
      queryClient.invalidateQueries({ queryKey: ["/api/truth-scan/uploads", uploadId] });
    },
    onError: () => {
      toast({ title: "Error", description: "Failed to resolve issues", variant: "destructive" });
    },
  });

  const finalizeMutation = useMutation({
    mutationFn: async () => {
      const response = await apiRequest("POST", `/api/truth-scan/uploads/${uploadId}/finalize`);
      return response.json();
    },
    onSuccess: () => {
      toast({ title: "Success", description: "Truth dataset finalized. You can now run simulations." });
      queryClient.invalidateQueries({ queryKey: ["/api/companies", companyId, "truth", "latest"] });
      if (onComplete) {
        onComplete();
      } else {
        setLocation(`/companies/${companyId}/scenarios`);
      }
    },
    onError: () => {
      toast({ title: "Error", description: "Failed to finalize. Blocked issues may still exist.", variant: "destructive" });
    },
  });

  const handleAnswerSelect = (issueId: string, choice: string) => {
    setSelectedAnswers((prev) => ({ ...prev, [issueId]: choice }));
  };

  const handleResolveAnswers = () => {
    const answers = Object.entries(selectedAnswers).map(([issue_id, choice]) => ({
      issue_id,
      choice,
    }));
    if (answers.length > 0) {
      resolveMutation.mutate(answers);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!uploadData) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="h-12 w-12 mx-auto text-destructive mb-4" />
        <h2 className="text-lg font-semibold mb-2">Truth Scan Not Found</h2>
        <p className="text-muted-foreground">The validation data could not be loaded.</p>
      </div>
    );
  }

  const { truth_dataset, latest_month_metrics, issues, can_finalize } = uploadData;
  const assumptions = truth_dataset?.assumptions || {};
  const coverage = truth_dataset?.coverage || {};

  const content = (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card data-testid="card-what-we-found">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Database className="h-5 w-5" />
              What We Found
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-3 gap-3">
              <div className="p-2 rounded-lg bg-muted/50">
                <div className="text-xs text-muted-foreground">Currency</div>
                <div className="font-medium text-sm">{assumptions.currency || "USD"}</div>
              </div>
              <div className="p-2 rounded-lg bg-muted/50">
                <div className="text-xs text-muted-foreground">Scale</div>
                <div className="font-medium text-sm capitalize">{assumptions.scale || "Unit"}</div>
              </div>
              <div className="p-2 rounded-lg bg-muted/50">
                <div className="text-xs text-muted-foreground">Time Base</div>
                <div className="font-medium text-sm capitalize">{assumptions.time_granularity || "Monthly"}</div>
              </div>
            </div>

            <Separator />

            <div className="space-y-2">
              <h4 className="text-sm font-medium">Latest Metrics</h4>
              <div className="grid grid-cols-2 gap-2">
                <div className="flex items-center gap-2 p-2 rounded-lg border">
                  <TrendingUp className="h-4 w-4 text-green-500" />
                  <div>
                    <div className="text-xs text-muted-foreground">Revenue</div>
                    <div className="font-medium text-sm">
                      {latest_month_metrics?.revenue?.value 
                        ? formatCurrencyAbbrev(latest_month_metrics.revenue.value)
                        : "N/A"}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2 p-2 rounded-lg border">
                  <Wallet className="h-4 w-4 text-blue-500" />
                  <div>
                    <div className="text-xs text-muted-foreground">Cash</div>
                    <div className="font-medium text-sm">
                      {latest_month_metrics?.cash_balance?.value
                        ? formatCurrencyAbbrev(latest_month_metrics.cash_balance.value)
                        : "N/A"}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2 p-2 rounded-lg border">
                  <Zap className="h-4 w-4 text-orange-500" />
                  <div>
                    <div className="text-xs text-muted-foreground">Net Burn</div>
                    <div className="font-medium text-sm">
                      {latest_month_metrics?.net_burn?.label || "N/A"}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2 p-2 rounded-lg border">
                  <FileCheck className="h-4 w-4 text-purple-500" />
                  <div>
                    <div className="text-xs text-muted-foreground">Runway</div>
                    <div className="font-medium text-sm">
                      {latest_month_metrics?.runway?.label || "N/A"}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {Object.keys(coverage).length > 0 && (
              <>
                <Separator />
                <div className="space-y-2">
                  <h4 className="text-sm font-medium">Data Coverage</h4>
                  <div className="space-y-1.5">
                    {Object.entries(coverage).slice(0, 5).map(([key, value]) => {
                      if (typeof value !== "number") return null;
                      return (
                        <div key={key} className="flex items-center gap-2">
                          <span className="text-xs capitalize w-20 truncate">{key.replace(/_/g, " ")}</span>
                          <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                            <div
                              className="h-full bg-primary rounded-full transition-all"
                              style={{ width: `${Math.min(value, 100)}%` }}
                            />
                          </div>
                          <span className="text-xs text-muted-foreground w-10 text-right">{value.toFixed(0)}%</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <Card data-testid="card-issues">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Issues & Fixes</CardTitle>
          </CardHeader>
          <CardContent className="pb-0">
            <Tabs defaultValue="blocked" className="w-full">
              <TabsList className="grid w-full grid-cols-3 mb-3">
                <TabsTrigger value="auto_fixed" className="text-xs gap-1" data-testid="tab-auto-fixed">
                  <CheckCircle className="h-3 w-3" />
                  Fixed
                  <Badge variant="secondary" className="ml-0.5 h-5 px-1">{issues.auto_fixed.length}</Badge>
                </TabsTrigger>
                <TabsTrigger value="needs_confirmation" className="text-xs gap-1" data-testid="tab-needs-confirmation">
                  <AlertTriangle className="h-3 w-3" />
                  Confirm
                  <Badge variant="secondary" className="ml-0.5 h-5 px-1">{issues.needs_confirmation.length}</Badge>
                </TabsTrigger>
                <TabsTrigger value="blocked" className="text-xs gap-1" data-testid="tab-blocked">
                  <AlertCircle className="h-3 w-3" />
                  Blocked
                  <Badge variant="destructive" className="ml-0.5 h-5 px-1">{issues.blocked.length}</Badge>
                </TabsTrigger>
              </TabsList>

              <div className="max-h-[240px] overflow-y-auto">
                <TabsContent value="auto_fixed" className="space-y-2 mt-0">
                  {issues.auto_fixed.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-4">No auto-fixed issues</p>
                  ) : (
                    issues.auto_fixed.map((issue) => (
                      <div key={issue.id} className="p-2 rounded-lg border bg-green-500/5 border-green-500/20">
                        <div className="flex items-start gap-2">
                          <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                          <div>
                            <p className="text-sm">{issue.message}</p>
                            <p className="text-xs text-muted-foreground">
                              {issue.metric_key}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </TabsContent>

                <TabsContent value="needs_confirmation" className="space-y-2 mt-0">
                  {issues.needs_confirmation.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-4">No issues need confirmation</p>
                  ) : (
                    issues.needs_confirmation.map((issue) => (
                      <div key={issue.id} className={`p-2 rounded-lg border ${getSeverityColor(issue.severity)}`}>
                        <div className="flex items-start gap-2">
                          {getSeverityIcon(issue.severity)}
                          <div className="flex-1 min-w-0">
                            <p className="text-sm">{issue.message}</p>
                            {issue.suggestion?.options && (
                              <div className="flex flex-wrap gap-1.5 mt-1.5">
                                {issue.suggestion.options.map((option) => (
                                  <Button
                                    key={option}
                                    size="sm"
                                    variant={selectedAnswers[issue.id] === option ? "default" : "outline"}
                                    className="h-7 text-xs"
                                    onClick={() => handleAnswerSelect(issue.id, option)}
                                    data-testid={`button-option-${issue.id}-${option}`}
                                  >
                                    {option}
                                  </Button>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </TabsContent>

                <TabsContent value="blocked" className="space-y-2 mt-0">
                  {issues.blocked.length === 0 ? (
                    <div className="text-center py-4">
                      <CheckCircle className="h-6 w-6 mx-auto text-green-500 mb-1" />
                      <p className="text-sm text-muted-foreground">No blocked issues</p>
                    </div>
                  ) : (
                    issues.blocked.map((issue) => (
                      <div key={issue.id} className="p-2 rounded-lg border bg-red-500/10 border-red-500/20">
                        <div className="flex items-start gap-2">
                          <AlertCircle className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium">{issue.message}</p>
                            {issue.suggestion?.options && (
                              <div className="flex flex-wrap gap-1.5 mt-1.5">
                                {issue.suggestion.options.map((option) => (
                                  <Button
                                    key={option}
                                    size="sm"
                                    variant={selectedAnswers[issue.id] === option ? "default" : "outline"}
                                    className="h-7 text-xs"
                                    onClick={() => handleAnswerSelect(issue.id, option)}
                                    data-testid={`button-option-${issue.id}-${option}`}
                                  >
                                    {option}
                                  </Button>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </TabsContent>
              </div>
            </Tabs>
          </CardContent>
          <CardFooter className="flex flex-col gap-2 pt-4">
            {Object.keys(selectedAnswers).length > 0 && (
              <Button
                className="w-full"
                variant="outline"
                onClick={handleResolveAnswers}
                disabled={resolveMutation.isPending}
                data-testid="button-resolve-answers"
              >
                {resolveMutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                Apply {Object.keys(selectedAnswers).length} Answer(s)
              </Button>
            )}
            <Button
              className="w-full"
              disabled={!can_finalize || finalizeMutation.isPending}
              onClick={() => finalizeMutation.mutate()}
              data-testid="button-finalize"
            >
              {finalizeMutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              {can_finalize ? "Finalize & Continue" : "Resolve Blocked Issues First"}
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </CardFooter>
        </Card>
      </div>
    </div>
  );

  if (isDialog) {
    return (
      <Dialog open={true} onOpenChange={onClose}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-primary" />
              Truth Scan Gate
            </DialogTitle>
            <DialogDescription>
              Validate your financial data before running simulations
            </DialogDescription>
          </DialogHeader>
          {content}
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <div className="container mx-auto p-6 max-w-7xl">
      <div className="flex items-center gap-3 mb-6">
        <Shield className="h-8 w-8 text-primary" />
        <div>
          <h1 className="text-2xl font-bold">Truth Scan Gate</h1>
          <p className="text-muted-foreground">Validate your financial data before running simulations</p>
        </div>
        <Button variant="ghost" size="sm" className="ml-auto" onClick={() => refetch()} data-testid="button-refresh">
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>
      {content}
    </div>
  );
}

export function TruthScanBlockedModal({ 
  uploadId, 
  companyId, 
  open, 
  onOpenChange, 
  onComplete 
}: { 
  uploadId: string; 
  companyId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onComplete?: () => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            Truth Scan Required
          </DialogTitle>
          <DialogDescription>
            Please complete data validation before running simulations
          </DialogDescription>
        </DialogHeader>
        <TruthScanGate 
          uploadId={uploadId} 
          companyId={companyId} 
          onComplete={() => {
            onOpenChange(false);
            onComplete?.();
          }}
        />
      </DialogContent>
    </Dialog>
  );
}
