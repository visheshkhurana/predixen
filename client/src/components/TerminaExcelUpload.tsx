import { useState, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useToast } from "@/hooks/use-toast";
import { useTerminaExcelUpload } from "@/api/hooks";
import { 
  FileUp, 
  FileSpreadsheet, 
  Check, 
  Loader2, 
  Sparkles,
  DollarSign,
  TrendingUp,
  Building2,
  X,
  Table2,
  AlertCircle
} from "lucide-react";
import { Input } from "@/components/ui/input";

interface TerminaExcelUploadProps {
  companyId: number;
  onSuccess?: (metrics: any) => void;
}

interface ExtractedMetrics {
  revenue?: number;
  gross_margin?: number;
  gross_profit?: number;
  operating_income?: number;
  net_income?: number;
  cogs?: number;
  opex?: number;
  payroll?: number;
  cash_balance?: number;
  [key: string]: any;
}

interface EditableMetric {
  key: string;
  label: string;
  value: number | undefined;
  isPercent?: boolean;
  required?: boolean;
}

interface EstimatedFields {
  [key: string]: boolean;
}

function calculateIndustryEstimates(metrics: Record<string, number | undefined>): {
  estimates: Record<string, number>;
  explanations: Record<string, string>;
} {
  const estimates: Record<string, number> = {};
  const explanations: Record<string, string> = {};
  
  const revenue = metrics.revenue || 0;
  let opex = metrics.opex;
  let payroll = metrics.payroll;
  const cogs = metrics.cogs || 0;
  
  if (opex === undefined || opex === null) {
    if (revenue > 0) {
      opex = Math.round(revenue * 0.3);
      estimates.opex = opex;
      explanations.opex = "Estimated at 30% of revenue (typical SaaS operating expense ratio)";
    }
  }
  
  if ((payroll === undefined || payroll === null) && (opex && opex > 0)) {
    payroll = Math.round(opex * 0.5);
    estimates.payroll = payroll;
    explanations.payroll = "Estimated at 50% of operating expenses (industry benchmark: 40-60%)";
  }
  
  const effectiveOpex = opex || 0;
  const effectivePayroll = payroll || 0;
  const totalMonthlyExpenses = effectiveOpex + effectivePayroll + cogs;
  
  if (!metrics.cash_balance && metrics.cash_balance !== 0) {
    const estimatedCash = totalMonthlyExpenses > 0 ? totalMonthlyExpenses * 6 : revenue * 3;
    if (estimatedCash > 0) {
      estimates.cash_balance = Math.round(estimatedCash);
      explanations.cash_balance = "Estimated at 6 months of operating expenses (industry standard for runway)";
    }
  }
  
  if (!metrics.monthlyGrowthRate && metrics.monthlyGrowthRate !== 0) {
    estimates.monthlyGrowthRate = 5;
    explanations.monthlyGrowthRate = "Conservative estimate for high-growth companies (5% MoM)";
  }
  
  return { estimates, explanations };
}

export function TerminaExcelUpload({ companyId, onSuccess }: TerminaExcelUploadProps) {
  const { toast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [extractedMetrics, setExtractedMetrics] = useState<ExtractedMetrics | null>(null);
  const [editableMetrics, setEditableMetrics] = useState<Record<string, number | undefined>>({});
  const [estimatedFields, setEstimatedFields] = useState<EstimatedFields>({});
  const [estimateExplanations, setEstimateExplanations] = useState<Record<string, string>>({});
  const [sheetName, setSheetName] = useState<string | null>(null);
  const [reportDate, setReportDate] = useState<string | null>(null);
  const [summary, setSummary] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [hasApplied, setHasApplied] = useState(false);

  const uploadMutation = useTerminaExcelUpload();

  const handleFileSelect = (file: File) => {
    const ext = file.name.toLowerCase().split('.').pop();
    if (ext !== 'xlsx' && ext !== 'xls') {
      toast({
        title: "Invalid file type",
        description: "Please upload an Excel file (.xlsx or .xls)",
        variant: "destructive",
      });
      return;
    }
    setSelectedFile(file);
    setExtractedMetrics(null);
    setSummary(null);
    setSheetName(null);
    setReportDate(null);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    
    if (e.dataTransfer.files?.[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(true);
  };

  const handleDragLeave = () => {
    setDragActive(false);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    try {
      const result = await uploadMutation.mutateAsync({
        companyId,
        file: selectedFile,
        saveAsBaseline: false,
      });

      setExtractedMetrics(result.metrics);
      setSummary(result.summary);
      setSheetName(result.sheet_name);
      setReportDate(result.report_date);
      setHasApplied(false);
      
      const extractedValues: Record<string, number | undefined> = {
        revenue: result.metrics?.revenue,
        cogs: result.metrics?.cogs,
        opex: result.metrics?.opex,
        payroll: result.metrics?.payroll,
        cash_balance: result.metrics?.cash_balance,
        gross_margin: result.metrics?.gross_margin,
        monthlyGrowthRate: undefined,
      };
      
      const { estimates, explanations } = calculateIndustryEstimates(extractedValues);
      
      const newEstimatedFields: EstimatedFields = {};
      const mergedMetrics = { ...extractedValues };
      
      Object.entries(estimates).forEach(([key, value]) => {
        if (mergedMetrics[key] === undefined || mergedMetrics[key] === null) {
          mergedMetrics[key] = value;
          newEstimatedFields[key] = true;
        }
      });
      
      setEditableMetrics(mergedMetrics);
      setEstimatedFields(newEstimatedFields);
      setEstimateExplanations(explanations);

      const estimatedCount = Object.keys(newEstimatedFields).length;
      toast({
        title: "Spreadsheet analyzed",
        description: estimatedCount > 0 
          ? `Review extracted metrics. ${estimatedCount} field(s) auto-filled with industry estimates.`
          : "Review the extracted metrics below and click 'Apply to Financials' to save.",
      });
    } catch (error: any) {
      toast({
        title: "Failed to analyze spreadsheet",
        description: error.message || "Please try again",
        variant: "destructive",
      });
    }
  };

  const handleApplyToFinancials = async () => {
    setIsApplying(true);
    try {
      const growthRate = (editableMetrics.monthlyGrowthRate || 0) / 100;
      const payload = {
        cashOnHand: editableMetrics.cash_balance || 0,
        monthlyRevenue: editableMetrics.revenue || 0,
        totalMonthlyExpenses: (editableMetrics.opex || 0) + (editableMetrics.payroll || 0),
        monthlyGrowthRate: growthRate,
        expenseBreakdown: {
          payroll: editableMetrics.payroll || 0,
          marketing: 0,
          operating: editableMetrics.opex || 0,
        },
        currency: 'USD',
        asOfDate: null,
      };

      const response = await fetch(`/api/companies/${companyId}/financials/save`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to save financials');
      }

      setHasApplied(true);
      toast({
        title: "Financials saved successfully",
        description: "Your data has been applied. Run Truth Scan to see updated metrics.",
      });

      if (onSuccess) {
        onSuccess(editableMetrics);
      }
    } catch (error: any) {
      toast({
        title: "Failed to save financials",
        description: error.message || "Please try again",
        variant: "destructive",
      });
    } finally {
      setIsApplying(false);
    }
  };

  const updateMetric = (key: string, value: string) => {
    const numValue = parseFloat(value.replace(/[^0-9.-]/g, ''));
    setEditableMetrics(prev => ({
      ...prev,
      [key]: isNaN(numValue) ? undefined : numValue,
    }));
    if (estimatedFields[key]) {
      setEstimatedFields(prev => {
        const updated = { ...prev };
        delete updated[key];
        return updated;
      });
    }
  };

  const getMissingFields = (): string[] => {
    const missing: string[] = [];
    if (!editableMetrics.revenue && editableMetrics.revenue !== 0) missing.push('Revenue');
    if (!editableMetrics.cash_balance && editableMetrics.cash_balance !== 0) missing.push('Cash Balance');
    return missing;
  };

  const formatCurrency = (value: number | undefined) => {
    if (value === undefined || value === null) return "N/A";
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatPercent = (value: number | undefined) => {
    if (value === undefined || value === null) return "N/A";
    return `${value.toFixed(1)}%`;
  };

  const clearFile = () => {
    setSelectedFile(null);
    setExtractedMetrics(null);
    setSummary(null);
    setSheetName(null);
    setReportDate(null);
    setEstimatedFields({});
    setEstimateExplanations({});
    setHasApplied(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <Card className="overflow-visible">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <FileSpreadsheet className="h-5 w-5" />
          Termina Excel Upload
        </CardTitle>
        <CardDescription>
          Upload a Termina export Excel file to automatically extract financial metrics from the Income Statement
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div
          className={`
            border-2 border-dashed rounded-md p-8 text-center transition-colors
            ${dragActive ? 'border-primary bg-primary/5' : 'border-muted-foreground/25'}
            ${selectedFile ? 'bg-muted/30' : ''}
          `}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          data-testid="dropzone-excel"
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx,.xls"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
            data-testid="input-excel-file"
          />

          {selectedFile ? (
            <div className="space-y-3">
              <div className="flex items-center justify-center gap-2">
                <FileSpreadsheet className="h-8 w-8 text-primary" />
                <div className="text-left">
                  <p className="font-medium" data-testid="text-selected-excel-file">{selectedFile.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {(selectedFile.size / 1024).toFixed(1)} KB
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={clearFile}
                  className="ml-2"
                  data-testid="button-clear-excel-file"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <FileUp className="h-12 w-12 mx-auto text-muted-foreground" />
              <div>
                <p className="text-muted-foreground">
                  Drag and drop your Termina Excel export here, or
                </p>
                <Button
                  variant="ghost"
                  className="px-1 h-auto underline"
                  onClick={() => fileInputRef.current?.click()}
                  data-testid="button-browse-excel-files"
                >
                  browse files
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Supports .xlsx and .xls files with Income Statement data
              </p>
            </div>
          )}
        </div>

        {selectedFile && !extractedMetrics && (
          <div className="flex items-center justify-end">
            <Button
              onClick={handleUpload}
              disabled={uploadMutation.isPending}
              data-testid="button-analyze-excel"
            >
              {uploadMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Table2 className="h-4 w-4 mr-2" />
                  Extract Metrics
                </>
              )}
            </Button>
          </div>
        )}

        {uploadMutation.isPending && (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Parsing spreadsheet and extracting metrics...
            </div>
            <Progress value={50} className="h-2" />
          </div>
        )}

        {extractedMetrics && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 flex-wrap">
              <Check className="h-5 w-5 text-green-500" />
              <span className="font-medium">Analysis Complete - Review & Edit Values</span>
              {sheetName && (
                <Badge variant="outline" className="ml-2">{sheetName}</Badge>
              )}
              {reportDate && (
                <Badge variant="secondary" className="ml-1">Period: {reportDate}</Badge>
              )}
              {hasApplied && (
                <Badge className="bg-emerald-500/20 text-emerald-400">Applied</Badge>
              )}
            </div>

            {summary && (
              <div className="bg-muted/50 rounded-md p-4">
                <div className="flex items-start gap-2">
                  <Sparkles className="h-4 w-4 mt-0.5 text-primary" />
                  <p className="text-sm text-muted-foreground" data-testid="text-excel-summary">
                    {summary}
                  </p>
                </div>
              </div>
            )}

            {getMissingFields().length > 0 && (
              <div className="bg-amber-500/10 border border-amber-500/30 rounded-md p-3">
                <div className="flex items-center gap-2 text-amber-400 text-sm">
                  <AlertCircle className="h-4 w-4" />
                  <span>Missing required fields: {getMissingFields().join(', ')}</span>
                </div>
              </div>
            )}

            {Object.keys(estimatedFields).length > 0 && (
              <div className="bg-blue-500/10 border border-blue-500/30 rounded-md p-3">
                <div className="flex items-center gap-2 text-blue-400 text-sm">
                  <Sparkles className="h-4 w-4" />
                  <span>
                    {Object.keys(estimatedFields).length} field(s) auto-filled with industry-standard estimates. 
                    Fields marked with <Badge variant="outline" className="ml-1 text-xs bg-blue-500/10 text-blue-400 border-blue-500/30">Estimated</Badge> can be edited before applying.
                  </span>
                </div>
              </div>
            )}

            <Separator />

            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Review the extracted values below. You can edit any field before applying to your financials.
              </p>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <EditableMetricField
                  label="Monthly Revenue"
                  value={editableMetrics.revenue}
                  onChange={(val) => updateMetric('revenue', val)}
                  required
                  testId="input-edit-revenue"
                />
                <EditableMetricField
                  label="Cash Balance"
                  value={editableMetrics.cash_balance}
                  onChange={(val) => updateMetric('cash_balance', val)}
                  required
                  isEstimated={estimatedFields.cash_balance}
                  estimateHint={estimateExplanations.cash_balance}
                  testId="input-edit-cash"
                />
                <EditableMetricField
                  label="Operating Expenses"
                  value={editableMetrics.opex}
                  onChange={(val) => updateMetric('opex', val)}
                  isEstimated={estimatedFields.opex}
                  estimateHint={estimateExplanations.opex}
                  testId="input-edit-opex"
                />
                <EditableMetricField
                  label="Payroll"
                  value={editableMetrics.payroll}
                  onChange={(val) => updateMetric('payroll', val)}
                  isEstimated={estimatedFields.payroll}
                  estimateHint={estimateExplanations.payroll}
                  testId="input-edit-payroll"
                />
                <EditableMetricField
                  label="Monthly Growth Rate %"
                  value={editableMetrics.monthlyGrowthRate}
                  onChange={(val) => updateMetric('monthlyGrowthRate', val)}
                  isPercent
                  isEstimated={estimatedFields.monthlyGrowthRate}
                  estimateHint={estimateExplanations.monthlyGrowthRate}
                  testId="input-edit-growth"
                />
                <EditableMetricField
                  label="COGS"
                  value={editableMetrics.cogs}
                  onChange={(val) => updateMetric('cogs', val)}
                  testId="input-edit-cogs"
                />
                <EditableMetricField
                  label="Gross Margin %"
                  value={editableMetrics.gross_margin}
                  onChange={(val) => updateMetric('gross_margin', val)}
                  isPercent
                  testId="input-edit-margin"
                />
              </div>
            </div>

            <Separator />

            <div className="flex justify-between gap-4 flex-wrap">
              <Button variant="outline" onClick={clearFile} data-testid="button-upload-another-excel">
                Upload Another File
              </Button>
              <Button 
                onClick={handleApplyToFinancials}
                disabled={isApplying || hasApplied || getMissingFields().length > 0}
                data-testid="button-apply-financials"
              >
                {isApplying ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Applying...
                  </>
                ) : hasApplied ? (
                  <>
                    <Check className="h-4 w-4 mr-2" />
                    Applied to Financials
                  </>
                ) : (
                  <>
                    <DollarSign className="h-4 w-4 mr-2" />
                    Apply to Financials
                  </>
                )}
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function MetricCard({ 
  label, 
  value, 
  icon: Icon 
}: { 
  label: string; 
  value: string; 
  icon: React.ComponentType<{ className?: string }>; 
}) {
  return (
    <div className="bg-muted/30 rounded-md p-3">
      <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
        <Icon className="h-3 w-3" />
        {label}
      </div>
      <p className="font-mono font-medium" data-testid={`text-metric-${label.toLowerCase().replace(/\s+/g, '-')}`}>
        {value}
      </p>
    </div>
  );
}

function EditableMetricField({
  label,
  value,
  onChange,
  isPercent = false,
  required = false,
  isEstimated = false,
  estimateHint,
  testId,
}: {
  label: string;
  value: number | undefined;
  onChange: (value: string) => void;
  isPercent?: boolean;
  required?: boolean;
  isEstimated?: boolean;
  estimateHint?: string;
  testId: string;
}) {
  const formatDisplayValue = (val: number | undefined) => {
    if (val === undefined || val === null) return '';
    if (isPercent) return val.toString();
    return new Intl.NumberFormat('en-US').format(val);
  };

  return (
    <div className="space-y-1.5">
      <label className="text-sm text-muted-foreground flex items-center gap-1 flex-wrap">
        {label}
        {required && <span className="text-destructive">*</span>}
        {isEstimated && (
          <Badge variant="outline" className="ml-1 text-xs bg-blue-500/10 text-blue-400 border-blue-500/30">
            Estimated
          </Badge>
        )}
      </label>
      <div className="relative">
        {!isPercent && (
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
        )}
        <Input
          type="text"
          value={formatDisplayValue(value)}
          onChange={(e) => onChange(e.target.value)}
          className={`${isPercent ? '' : 'pl-7'} font-mono ${isEstimated ? 'border-blue-500/30' : ''}`}
          placeholder={isPercent ? '0' : '0'}
          data-testid={testId}
        />
        {isPercent && (
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground">%</span>
        )}
      </div>
      {isEstimated && estimateHint && (
        <p className="text-xs text-blue-400/80">{estimateHint}</p>
      )}
    </div>
  );
}
