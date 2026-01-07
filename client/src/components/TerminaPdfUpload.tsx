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
import { useTerminaPdfUpload } from "@/api/hooks";
import { 
  FileUp, 
  FileText, 
  Check, 
  AlertCircle, 
  Loader2, 
  Sparkles,
  DollarSign,
  TrendingUp,
  Building2,
  X
} from "lucide-react";

interface TerminaPdfUploadProps {
  companyId: number;
  onSuccess?: (metrics: any) => void;
}

interface ExtractedMetrics {
  monthly_revenue?: number;
  gross_margin?: number;
  cash_balance?: number;
  runway_months?: number;
  yoy_growth?: number;
  net_burn?: number;
  customers?: number;
  arr?: number;
  ndr?: number;
  [key: string]: any;
}

export function TerminaPdfUpload({ companyId, onSuccess }: TerminaPdfUploadProps) {
  const { toast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [saveAsBaseline, setSaveAsBaseline] = useState(true);
  const [extractedMetrics, setExtractedMetrics] = useState<ExtractedMetrics | null>(null);
  const [summary, setSummary] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);

  const uploadMutation = useTerminaPdfUpload();

  const handleFileSelect = (file: File) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      toast({
        title: "Invalid file type",
        description: "Please upload a PDF file",
        variant: "destructive",
      });
      return;
    }
    setSelectedFile(file);
    setExtractedMetrics(null);
    setSummary(null);
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

      toast({
        title: "Report analyzed successfully",
        description: `Extracted ${result.extracted_fields} financial metrics`,
      });

      if (onSuccess) {
        onSuccess(result.metrics);
      }
    } catch (error: any) {
      toast({
        title: "Failed to analyze report",
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
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <Card className="overflow-visible">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <FileText className="h-5 w-5" />
          Termina Report Upload
        </CardTitle>
        <CardDescription>
          Upload a Termina Mini Scan PDF to automatically extract financial metrics
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
          data-testid="dropzone-pdf"
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
            data-testid="input-pdf-file"
          />

          {selectedFile ? (
            <div className="space-y-3">
              <div className="flex items-center justify-center gap-2">
                <FileText className="h-8 w-8 text-primary" />
                <div className="text-left">
                  <p className="font-medium" data-testid="text-selected-file">{selectedFile.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {(selectedFile.size / 1024).toFixed(1)} KB
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={clearFile}
                  className="ml-2"
                  data-testid="button-clear-file"
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
                  Drag and drop your Termina PDF here, or
                </p>
                <Button
                  variant="link"
                  className="px-1"
                  onClick={() => fileInputRef.current?.click()}
                  data-testid="button-browse-files"
                >
                  browse files
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Supports Termina Mini Scan and Full Report PDFs
              </p>
            </div>
          )}
        </div>

        {selectedFile && !extractedMetrics && (
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Switch
                id="save-baseline"
                checked={saveAsBaseline}
                onCheckedChange={setSaveAsBaseline}
                data-testid="switch-save-baseline"
              />
              <Label htmlFor="save-baseline" className="text-sm">
                Save as baseline data
              </Label>
            </div>
            <Button
              onClick={handleUpload}
              disabled={uploadMutation.isPending}
              data-testid="button-analyze-pdf"
            >
              {uploadMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4 mr-2" />
                  Analyze with AI
                </>
              )}
            </Button>
          </div>
        )}

        {uploadMutation.isPending && (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Extracting text and analyzing with AI...
            </div>
            <Progress value={66} className="h-2" />
          </div>
        )}

        {extractedMetrics && (
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Check className="h-5 w-5 text-green-500" />
              <span className="font-medium">Analysis Complete</span>
              {saveAsBaseline && (
                <Badge variant="secondary" className="ml-2">Saved as Baseline</Badge>
              )}
            </div>

            {summary && (
              <div className="bg-muted/50 rounded-md p-4">
                <p className="text-sm text-muted-foreground" data-testid="text-summary">
                  {summary}
                </p>
              </div>
            )}

            <Separator />

            <ScrollArea className="max-h-[400px]">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {extractedMetrics.monthly_revenue !== undefined && (
                  <MetricCard
                    label="Monthly Revenue"
                    value={formatCurrency(extractedMetrics.monthly_revenue)}
                    icon={DollarSign}
                  />
                )}
                {extractedMetrics.arr !== undefined && (
                  <MetricCard
                    label="ARR"
                    value={formatCurrency(extractedMetrics.arr)}
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
                {extractedMetrics.cash_balance !== undefined && (
                  <MetricCard
                    label="Cash Balance"
                    value={formatCurrency(extractedMetrics.cash_balance)}
                    icon={DollarSign}
                  />
                )}
                {extractedMetrics.net_burn !== undefined && (
                  <MetricCard
                    label="Net Burn"
                    value={formatCurrency(extractedMetrics.net_burn)}
                    icon={DollarSign}
                  />
                )}
                {extractedMetrics.runway_months !== undefined && (
                  <MetricCard
                    label="Runway"
                    value={`${extractedMetrics.runway_months} months`}
                    icon={Building2}
                  />
                )}
                {extractedMetrics.yoy_growth !== undefined && (
                  <MetricCard
                    label="YoY Growth"
                    value={formatPercent(extractedMetrics.yoy_growth)}
                    icon={TrendingUp}
                  />
                )}
                {extractedMetrics.ndr !== undefined && (
                  <MetricCard
                    label="Net Dollar Retention"
                    value={formatPercent(extractedMetrics.ndr)}
                    icon={TrendingUp}
                  />
                )}
                {extractedMetrics.customers !== undefined && (
                  <MetricCard
                    label="Customers"
                    value={extractedMetrics.customers.toLocaleString()}
                    icon={Building2}
                  />
                )}
              </div>
            </ScrollArea>

            <div className="flex justify-end">
              <Button variant="outline" onClick={clearFile} data-testid="button-upload-another">
                Upload Another Report
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
