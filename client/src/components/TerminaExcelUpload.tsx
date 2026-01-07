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
  Table2
} from "lucide-react";

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
  [key: string]: any;
}

export function TerminaExcelUpload({ companyId, onSuccess }: TerminaExcelUploadProps) {
  const { toast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [saveAsBaseline, setSaveAsBaseline] = useState(true);
  const [extractedMetrics, setExtractedMetrics] = useState<ExtractedMetrics | null>(null);
  const [sheetName, setSheetName] = useState<string | null>(null);
  const [reportDate, setReportDate] = useState<string | null>(null);
  const [summary, setSummary] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);

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
        saveAsBaseline,
      });

      setExtractedMetrics(result.metrics);
      setSummary(result.summary);
      setSheetName(result.sheet_name);
      setReportDate(result.report_date);

      toast({
        title: "Spreadsheet analyzed successfully",
        description: `Extracted ${result.extracted_fields} financial metrics from ${result.sheet_name}`,
      });

      if (onSuccess) {
        onSuccess(result.metrics);
      }
    } catch (error: any) {
      toast({
        title: "Failed to analyze spreadsheet",
        description: error.message || "Please try again",
        variant: "destructive",
      });
    }
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
                  variant="link"
                  className="px-1"
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
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Switch
                id="save-baseline-excel"
                checked={saveAsBaseline}
                onCheckedChange={setSaveAsBaseline}
                data-testid="switch-save-baseline-excel"
              />
              <Label htmlFor="save-baseline-excel" className="text-sm">
                Save as baseline data
              </Label>
            </div>
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
              <span className="font-medium">Analysis Complete</span>
              {sheetName && (
                <Badge variant="outline" className="ml-2">{sheetName}</Badge>
              )}
              {reportDate && (
                <Badge variant="secondary" className="ml-1">Period: {reportDate}</Badge>
              )}
              {saveAsBaseline && (
                <Badge variant="secondary" className="ml-2">Saved as Baseline</Badge>
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

            <Separator />

            <ScrollArea className="max-h-[400px]">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {extractedMetrics.revenue !== undefined && (
                  <MetricCard
                    label="Revenue"
                    value={formatCurrency(extractedMetrics.revenue)}
                    icon={DollarSign}
                  />
                )}
                {extractedMetrics.gross_profit !== undefined && (
                  <MetricCard
                    label="Gross Profit"
                    value={formatCurrency(extractedMetrics.gross_profit)}
                    icon={DollarSign}
                  />
                )}
                {extractedMetrics.gross_margin !== undefined && (
                  <MetricCard
                    label="Gross Margin"
                    value={formatPercent(extractedMetrics.gross_margin)}
                    icon={TrendingUp}
                  />
                )}
                {extractedMetrics.operating_income !== undefined && (
                  <MetricCard
                    label="Operating Income"
                    value={formatCurrency(extractedMetrics.operating_income)}
                    icon={DollarSign}
                  />
                )}
                {extractedMetrics.net_income !== undefined && (
                  <MetricCard
                    label="Net Income"
                    value={formatCurrency(extractedMetrics.net_income)}
                    icon={DollarSign}
                  />
                )}
                {extractedMetrics.cogs !== undefined && (
                  <MetricCard
                    label="COGS"
                    value={formatCurrency(extractedMetrics.cogs)}
                    icon={Building2}
                  />
                )}
                {extractedMetrics.opex !== undefined && (
                  <MetricCard
                    label="Operating Expenses"
                    value={formatCurrency(extractedMetrics.opex)}
                    icon={Building2}
                  />
                )}
                {extractedMetrics.payroll !== undefined && (
                  <MetricCard
                    label="Payroll"
                    value={formatCurrency(extractedMetrics.payroll)}
                    icon={Building2}
                  />
                )}
                {extractedMetrics.net_revenue_india !== undefined && (
                  <MetricCard
                    label="India Revenue"
                    value={formatCurrency(extractedMetrics.net_revenue_india)}
                    icon={DollarSign}
                  />
                )}
                {extractedMetrics.net_revenue_international !== undefined && (
                  <MetricCard
                    label="International Revenue"
                    value={formatCurrency(extractedMetrics.net_revenue_international)}
                    icon={DollarSign}
                  />
                )}
              </div>
            </ScrollArea>

            <div className="flex justify-end">
              <Button variant="outline" onClick={clearFile} data-testid="button-upload-another-excel">
                Upload Another File
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
