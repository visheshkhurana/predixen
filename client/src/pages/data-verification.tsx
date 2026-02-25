import { useState, useEffect } from "react";
import { useLocation, useRoute } from "wouter";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useToast } from "@/hooks/use-toast";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { getErrorMessage } from "@/lib/errors";
import { useFounderStore, FinancialBaseline } from "@/store/founderStore";
import { 
  FileSpreadsheet, 
  AlertTriangle, 
  CheckCircle2, 
  ArrowLeft, 
  Save, 
  Download,
  DollarSign,
  TrendingUp,
  Wallet,
  PiggyBank,
  RefreshCw
} from "lucide-react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

interface ClassifiedRow {
  index: number;
  label: string;
  classification: string;
  expense_bucket: string | null;
  confidence: string;
  is_header: boolean;
  has_children: boolean;
  parent_index: number | null;
  values: Record<string, { raw: number; normalized: number; warnings: string[] }>;
  include_in_totals: boolean;
  notes: string[];
}

interface ImportSession {
  id: number;
  company_id: number;
  source_type: string;
  filename: string | null;
  status: string;
  detected_sign_convention: string;
  detected_time_granularity: string;
  selected_period_mode: string;
  selected_period: string | null;
  warnings: string[];
  errors: string[];
  periods: string[];
  rows: ClassifiedRow[];
  summary: {
    revenue_rows: number;
    expense_rows: number;
    derived_rows: number;
    header_rows: number;
    other_rows: number;
  };
}

interface VerifyResponse {
  baseline: {
    revenue: number;
    total_expenses: number;
    net_burn: number;
    burn_status: string;
    runway_months: number | null;
    cash_on_hand: number | null;
    growth_rate_mom: number | null;
  };
  expense_breakdown: Record<string, number>;
  burn_display: {
    label: string;
    value: number;
    is_surplus: boolean;
  };
  runway_display: string;
  warnings: string[];
  errors: string[];
  benchmark_injected: Array<{
    field: string;
    value: number;
    source: string;
    confidence: string;
  }>;
}

function formatCurrency(value: number): string {
  if (value === null || value === undefined || isNaN(value)) return 'N/A';
  
  const absValue = Math.abs(value);
  const sign = value < 0 ? '-' : '';
  
  if (absValue >= 1_000_000_000) {
    const billions = absValue / 1_000_000_000;
    return `${sign}$${billions.toFixed(1)}B`;
  } else if (absValue >= 1_000_000) {
    const millions = absValue / 1_000_000;
    return `${sign}$${millions.toFixed(1)}M`;
  } else if (absValue >= 1_000) {
    const thousands = absValue / 1_000;
    return `${sign}$${thousands.toFixed(1)}K`;
  } else if (absValue > 0) {
    return `${sign}$${absValue.toFixed(0)}`;
  }
  return '$0';
}

function formatCurrencyInWords(value: number, currency: string = "USD"): string {
  if (value === null || value === undefined || isNaN(value)) {
    return "";
  }
  
  const absValue = Math.abs(value);
  const sign = value < 0 ? "Negative " : "";
  
  const currencyNames: Record<string, string> = {
    USD: "US Dollars",
    EUR: "Euros",
    GBP: "British Pounds",
    INR: "Indian Rupees",
  };
  
  const currencyName = currencyNames[currency] || currency;
  
  if (absValue >= 1_000_000_000) {
    const billions = absValue / 1_000_000_000;
    return `${sign}${billions.toFixed(1)} billion ${currencyName}`;
  } else if (absValue >= 1_000_000) {
    const millions = absValue / 1_000_000;
    return `${sign}${millions.toFixed(1)} million ${currencyName}`;
  } else if (absValue >= 1_000) {
    const thousands = absValue / 1_000;
    return `${sign}${thousands.toFixed(1)} thousand ${currencyName}`;
  } else {
    return `${sign}${absValue.toFixed(2)} ${currencyName}`;
  }
}

function formatPercentage(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function getClassificationBadgeVariant(classification: string): "default" | "secondary" | "destructive" | "outline" {
  switch (classification) {
    case "revenue": return "default";
    case "expense": return "destructive";
    case "derived": return "secondary";
    case "header": return "outline";
    default: return "outline";
  }
}

function getConfidenceBadgeVariant(confidence: string): "default" | "secondary" | "destructive" | "outline" {
  switch (confidence) {
    case "high": return "default";
    case "medium": return "secondary";
    case "low": return "destructive";
    default: return "outline";
  }
}

export default function DataVerification() {
  const [, navigate] = useLocation();
  const [, params] = useRoute("/data/verify/:sessionId");
  const sessionId = params?.sessionId ? parseInt(params.sessionId) : null;
  const { toast } = useToast();
  const { setFinancialBaseline, clearFinancialBaseline, setLastExtraction } = useFounderStore();

  const [selectedPeriod, setSelectedPeriod] = useState<string>("");
  const [cashOnHand, setCashOnHand] = useState<string>("");
  const [revenueOverride, setRevenueOverride] = useState<string>("");
  const [expenseOverride, setExpenseOverride] = useState<string>("");
  const [rowToggles, setRowToggles] = useState<Record<number, boolean>>({});
  const [benchmarkOptIn, setBenchmarkOptIn] = useState(false);

  const { data: session, isLoading: sessionLoading } = useQuery<ImportSession>({
    queryKey: ['/api/imports', sessionId],
    enabled: !!sessionId,
  });

  useEffect(() => {
    if (session?.periods?.length && !selectedPeriod) {
      setSelectedPeriod(session.periods[0]);
    }
    if (session?.rows) {
      const toggles: Record<number, boolean> = {};
      session.rows.forEach(row => {
        toggles[row.index] = row.include_in_totals;
      });
      setRowToggles(toggles);
    }
  }, [session, selectedPeriod]);

  const verifyMutation = useMutation({
    mutationFn: async () => {
      const rowOverrides: Record<string, { include_in_totals: boolean }> = {};
      Object.entries(rowToggles).forEach(([idx, include]) => {
        rowOverrides[idx] = { include_in_totals: include };
      });

      const res = await apiRequest("POST", `/api/imports/${sessionId}/verify`, {
        selected_period_mode: "latest",
        selected_period: selectedPeriod,
        row_overrides: rowOverrides,
        cash_on_hand: cashOnHand ? parseFloat(cashOnHand) : null,
        revenue_override: revenueOverride ? parseFloat(revenueOverride) : null,
        expense_override: expenseOverride ? parseFloat(expenseOverride) : null,
        benchmark_opt_in: benchmarkOptIn,
      });
      return res.json() as Promise<VerifyResponse>;
    },
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      const rowOverrides: Record<string, { include_in_totals: boolean }> = {};
      Object.entries(rowToggles).forEach(([idx, include]) => {
        rowOverrides[idx] = { include_in_totals: include };
      });

      const res = await apiRequest("POST", `/api/imports/${sessionId}/save`, {
        selected_period: selectedPeriod,
        cash_on_hand: cashOnHand ? parseFloat(cashOnHand) : null,
        revenue_override: revenueOverride ? parseFloat(revenueOverride) : null,
        expense_override: expenseOverride ? parseFloat(expenseOverride) : null,
        row_overrides: rowOverrides,
      });
      return res.json();
    },
    onSuccess: (data) => {
      if (data.baseline) {
        const savedBaseline = data.baseline;
        const baseline: FinancialBaseline = {
          cashOnHand: savedBaseline.cashOnHand || null,
          monthlyRevenue: savedBaseline.monthlyRevenue || null,
          totalMonthlyExpenses: savedBaseline.totalMonthlyExpenses || null,
          monthlyGrowthRate: savedBaseline.monthlyGrowthRate !== null 
            ? savedBaseline.monthlyGrowthRate * 100 
            : null,
          expenseBreakdown: {
            payroll: savedBaseline.expenseBreakdown?.payroll || null,
            marketing: savedBaseline.expenseBreakdown?.marketing || null,
            operating: savedBaseline.expenseBreakdown?.operating || null,
            cogs: savedBaseline.expenseBreakdown?.cogs || null,
            otherOpex: savedBaseline.expenseBreakdown?.otherOpex || null,
          },
          hasManualExpenseOverride: false,
          currency: savedBaseline.currency || 'USD',
          asOfDate: savedBaseline.asOfDate || selectedPeriod || new Date().toISOString().split('T')[0],
        };
        setFinancialBaseline(baseline);
      }
      
      toast({
        title: "Data Saved",
        description: "Financial data has been saved and applied to your dashboard.",
      });
      queryClient.invalidateQueries({ queryKey: ['/api/companies'] });
      navigate("/data");
    },
    onError: (error: unknown) => {
      toast({
        title: "Save Failed",
        description: getErrorMessage(error, 'Failed to save data'),
        variant: "destructive",
      });
    },
  });

  useEffect(() => {
    if (selectedPeriod && sessionId) {
      verifyMutation.mutate();
    }
  }, [selectedPeriod, cashOnHand, revenueOverride, expenseOverride, rowToggles, benchmarkOptIn]);

  if (!sessionId) {
    return (
      <div className="p-6">
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Invalid Session</AlertTitle>
          <AlertDescription>No import session ID provided.</AlertDescription>
        </Alert>
        <Button className="mt-4" onClick={() => navigate("/data")}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Data Input
        </Button>
      </div>
    );
  }

  if (sessionLoading) {
    return (
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Skeleton className="h-10 w-10 rounded" />
            <div className="space-y-2">
              <Skeleton className="h-6 w-48" />
              <Skeleton className="h-4 w-72" />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Skeleton className="h-9 w-32" />
            <Skeleton className="h-9 w-36" />
          </div>
        </div>
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Skeleton className="h-5 w-5" />
                <div className="space-y-1">
                  <Skeleton className="h-4 w-40" />
                  <Skeleton className="h-3 w-24" />
                </div>
              </div>
              <div className="flex items-center gap-4">
                <Skeleton className="h-6 w-32 rounded-full" />
                <Skeleton className="h-9 w-44" />
              </div>
            </div>
          </CardHeader>
        </Card>
        <div className="grid md:grid-cols-4 gap-4">
          {Array(4).fill(0).map((_, i) => (
            <Card key={i}>
              <CardContent className="p-4">
                <Skeleton className="h-4 w-20 mb-2" />
                <Skeleton className="h-8 w-28" />
              </CardContent>
            </Card>
          ))}
        </div>
        <Card>
          <CardHeader>
            <Skeleton className="h-5 w-32" />
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {Array(5).fill(0).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="p-6">
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Session Not Found</AlertTitle>
          <AlertDescription>The import session could not be found.</AlertDescription>
        </Alert>
        <Button className="mt-4" onClick={() => navigate("/data")}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Data Input
        </Button>
      </div>
    );
  }

  const verifyData = verifyMutation.data;
  const hasErrors = (verifyData?.errors?.length || 0) > 0;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate("/data")} data-testid="button-back">
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold">Verify Financial Data</h1>
            <p className="text-muted-foreground">Review and verify extracted metrics before saving</p>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button 
                variant="ghost" 
                size="icon"
                onClick={() => {
                  queryClient.clear();
                  clearFinancialBaseline();
                  setLastExtraction(null);
                  localStorage.removeItem('founder-storage');
                  toast({
                    title: "Cache Cleared",
                    description: "All cached data has been cleared. Redirecting to Data Input...",
                  });
                  setTimeout(() => navigate("/data"), 500);
                }}
                data-testid="button-clear-cache"
              >
                <RefreshCw className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Clear cache and start fresh</p>
            </TooltipContent>
          </Tooltip>
          <Button variant="outline" onClick={() => {}} data-testid="button-download-csv">
            <Download className="h-4 w-4 mr-2" />
            Download CSV
          </Button>
          <Button 
            onClick={() => saveMutation.mutate()} 
            disabled={hasErrors || saveMutation.isPending}
            data-testid="button-save-baseline"
          >
            <Save className="h-4 w-4 mr-2" />
            {saveMutation.isPending ? "Saving..." : "Save as Baseline"}
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div className="flex items-center gap-3">
              <FileSpreadsheet className="h-5 w-5 text-muted-foreground" />
              <div>
                <CardTitle className="text-base">{session.filename || "Uploaded File"}</CardTitle>
                <CardDescription>Source: {session.source_type.toUpperCase()}</CardDescription>
              </div>
            </div>
            <div className="flex items-center gap-4 flex-wrap">
              <div className="flex items-center gap-2">
                <Badge variant={session.detected_sign_convention === "accounting" ? "default" : "secondary"}>
                  {session.detected_sign_convention === "accounting" 
                    ? "Accounting (expenses negative)" 
                    : session.detected_sign_convention === "all_positive"
                    ? "All Positive"
                    : "Mixed Signs"}
                </Badge>
                <CheckCircle2 className="h-4 w-4 text-green-500" />
              </div>
              <div className="flex items-center gap-2">
                <Label htmlFor="period-select" className="text-sm text-muted-foreground whitespace-nowrap">Period:</Label>
                <Select value={selectedPeriod} onValueChange={setSelectedPeriod}>
                  <SelectTrigger className="w-[180px]" id="period-select" data-testid="select-period">
                    <SelectValue placeholder="Select period" />
                  </SelectTrigger>
                  <SelectContent>
                    {session.periods.map((period) => (
                      <SelectItem key={period} value={period}>{period}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
        </CardHeader>
      </Card>

      {verifyData && (verifyData.baseline.revenue > 50_000_000 || verifyData.baseline.total_expenses > 50_000_000) && (
        <Alert className="border-amber-500/50 bg-amber-500/10">
          <AlertTriangle className="h-4 w-4 text-amber-500" />
          <AlertTitle className="text-amber-600">Values Seem Unusually High</AlertTitle>
          <AlertDescription className="text-amber-700">
            The extracted values appear very large (over $50 million). Please verify these are correct. 
            If your document uses abbreviations like "K" for thousands, please use the override fields 
            below to enter the correct values. For example, if revenue should be $116,100 (not $116.1 million), 
            enter "116100" in the override field.
          </AlertDescription>
        </Alert>
      )}

      {(verifyData?.warnings?.length || 0) > 0 && (
        <Alert>
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Warnings</AlertTitle>
          <AlertDescription>
            <ul className="list-disc list-inside mt-2">
              {verifyData?.warnings.map((warning, idx) => (
                <li key={idx}>{warning}</li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}

      {hasErrors && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Errors (must resolve before saving)</AlertTitle>
          <AlertDescription>
            <ul className="list-disc list-inside mt-2">
              {verifyData?.errors.map((error: unknown, idx: number) => (
                <li key={idx}>{typeof error === 'string' ? error : getErrorMessage(error)}</li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <DollarSign className="h-4 w-4" />
              Monthly Revenue
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="text-2xl font-bold font-mono">
                {verifyData ? formatCurrency(verifyData.baseline.revenue) : "--"}
              </div>
              {verifyData && (
                <p className="text-xs text-muted-foreground italic">
                  {formatCurrencyInWords(verifyData.baseline.revenue)}
                </p>
              )}
              <Input
                type="number"
                placeholder="Override revenue..."
                value={revenueOverride}
                onChange={(e) => setRevenueOverride(e.target.value)}
                data-testid="input-revenue-override"
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <PiggyBank className="h-4 w-4" />
              Total Expenses
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="text-2xl font-bold font-mono">
                {verifyData ? formatCurrency(verifyData.baseline.total_expenses) : "--"}
              </div>
              {verifyData && (
                <p className="text-xs text-muted-foreground italic">
                  {formatCurrencyInWords(verifyData.baseline.total_expenses)}
                </p>
              )}
              <Input
                type="number"
                placeholder="Override expenses..."
                value={expenseOverride}
                onChange={(e) => setExpenseOverride(e.target.value)}
                data-testid="input-expense-override"
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Wallet className="h-4 w-4" />
              Cash on Hand
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="text-2xl font-bold font-mono">
                {cashOnHand 
                  ? formatCurrency(parseFloat(cashOnHand)) 
                  : verifyData?.baseline?.cash_on_hand 
                    ? formatCurrency(verifyData.baseline.cash_on_hand)
                    : "--"}
              </div>
              {(cashOnHand || verifyData?.baseline?.cash_on_hand) && (
                <p className="text-xs text-muted-foreground italic">
                  {formatCurrencyInWords(cashOnHand ? parseFloat(cashOnHand) : (verifyData?.baseline?.cash_on_hand || 0))}
                  {!cashOnHand && verifyData?.baseline?.cash_on_hand && (
                    <span className="text-amber-500"> (estimated)</span>
                  )}
                </p>
              )}
              <Input
                type="number"
                placeholder="Enter cash on hand..."
                value={cashOnHand}
                onChange={(e) => setCashOnHand(e.target.value)}
                data-testid="input-cash-on-hand"
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              {verifyData?.burn_display?.label || "Net Burn"}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono">
              {verifyData ? (
                <span className={verifyData.burn_display.is_surplus ? "text-green-600" : "text-red-600"}>
                  {formatCurrency(verifyData.burn_display.value)}
                </span>
              ) : "--"}
            </div>
            {verifyData && (
              <p className="text-xs text-muted-foreground italic">
                {formatCurrencyInWords(verifyData.burn_display.value)}
              </p>
            )}
            <div className="text-sm text-muted-foreground mt-1">
              Runway: {verifyData?.runway_display || "--"}
            </div>
          </CardContent>
        </Card>
      </div>

      {verifyData?.expense_breakdown && Object.keys(verifyData.expense_breakdown).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Expense Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Object.entries(verifyData.expense_breakdown).map(([bucket, value]) => (
                <div key={bucket} className="space-y-1">
                  <div className="text-sm text-muted-foreground capitalize">{bucket}</div>
                  <div className="text-lg font-mono font-semibold">{formatCurrency(value)}</div>
                  <p className="text-xs text-muted-foreground italic">
                    {formatCurrencyInWords(value)}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {(verifyData?.benchmark_injected?.length || 0) > 0 && (
        <Card className="border-yellow-500/50 bg-yellow-500/5">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-yellow-500" />
              Benchmark Defaults Applied
            </CardTitle>
            <CardDescription>
              The following values were estimated from industry benchmarks
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {verifyData?.benchmark_injected.map((item, idx) => (
                <Badge key={idx} variant="outline" className="border-yellow-500/50">
                  {item.field}: {typeof item.value === 'number' && item.value < 1 
                    ? formatPercentage(item.value) 
                    : item.value}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Extracted Data Preview</CardTitle>
              <CardDescription>
                Toggle rows to include/exclude from totals. {session.summary.revenue_rows} revenue, {session.summary.expense_rows} expense rows detected.
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Switch
                id="benchmark-opt-in"
                checked={benchmarkOptIn}
                onCheckedChange={setBenchmarkOptIn}
                data-testid="switch-benchmark-opt-in"
              />
              <Label htmlFor="benchmark-opt-in" className="text-sm">Apply benchmark defaults</Label>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-[400px]">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[50px]">Include</TableHead>
                  <TableHead>Source Label</TableHead>
                  <TableHead>Classification</TableHead>
                  <TableHead>Bucket</TableHead>
                  <TableHead className="text-right">Raw Value</TableHead>
                  <TableHead className="text-right">Normalized</TableHead>
                  <TableHead>Confidence</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {session.rows.map((row) => {
                  const periodValues = row.values[selectedPeriod];
                  return (
                    <TableRow key={row.index} className={row.is_header ? "bg-muted/50" : ""}>
                      <TableCell>
                        <Switch
                          checked={rowToggles[row.index] ?? row.include_in_totals}
                          onCheckedChange={(checked) => {
                            setRowToggles(prev => ({ ...prev, [row.index]: checked }));
                          }}
                          disabled={row.is_header || row.classification === "derived"}
                          data-testid={`switch-include-row-${row.index}`}
                        />
                      </TableCell>
                      <TableCell className="font-medium">
                        {row.parent_index !== null && <span className="text-muted-foreground mr-2">└</span>}
                        {row.label}
                      </TableCell>
                      <TableCell>
                        <Badge variant={getClassificationBadgeVariant(row.classification)}>
                          {row.classification}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {row.expense_bucket && (
                          <Badge variant="outline">{row.expense_bucket}</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {periodValues ? formatCurrency(periodValues.raw) : "--"}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {periodValues ? formatCurrency(periodValues.normalized) : "--"}
                      </TableCell>
                      <TableCell>
                        <Badge variant={getConfidenceBadgeVariant(row.confidence)}>
                          {row.confidence}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
}
