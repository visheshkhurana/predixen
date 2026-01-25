import { useState, useRef, useCallback } from 'react';
import { useLocation } from 'wouter';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Progress } from '@/components/ui/progress';
import { useToast } from '@/hooks/use-toast';
import { ApiError } from '@/api/client';
import { useFounderStore } from '@/store/founderStore';
import { useCreateCompany, useManualBaseline, useRunTruthScan } from '@/api/hooks';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { HelpCircle, Upload, FileText, Sparkles, Check, AlertCircle, Loader2 } from 'lucide-react';

const STEPS = [
  { id: 1, title: 'Company Info', description: 'Tell us about your startup' },
  { id: 2, title: 'Financial Baseline', description: 'Enter your current financials' },
  { id: 3, title: 'First Truth Scan', description: 'Analyzing your data' },
];

const SAMPLE_COMPANY = {
  name: 'TechFlow AI',
  website: 'https://techflow.ai',
  industry: 'general_saas',
  stage: 'seed',
  currency: 'USD',
};

const SAMPLE_FINANCIALS = {
  monthly_revenue: 85000,
  gross_margin_pct: 75,
  opex: 25000,
  payroll: 45000,
  other_costs: 8000,
  cash_balance: 750000,
};

interface ExtractedData {
  company_info: {
    name?: string;
    website?: string;
    industry?: string;
    stage?: string;
  };
  financials: {
    monthly_revenue?: number;
    gross_margin_pct?: number;
    operating_margin_pct?: number;
    opex?: number;
    payroll?: number;
    other_costs?: number;
    cash_balance?: number;
    net_burn?: number;
  };
  computed_metrics?: {
    revenue_growth_mom?: number;
    revenue_growth_yoy?: number;
    cmgr?: number;
    burn_multiple?: number;
    concentration_top5?: number;
    ndr?: number;
    churn_rate?: number;
    ltv_cac_ratio?: number;
  };
  currency?: string;
  confidence?: { company_info: number; financials: number };
  summary?: string;
}

export default function OnboardingPage() {
  const [, setLocation] = useLocation();
  const { toast } = useToast();
  const { setCurrentCompany, setTruthScan, setCurrentStep: setStoreStep } = useFounderStore();
  const [step, setStep] = useState(1);
  const [companyData, setCompanyData] = useState({
    name: '',
    website: '',
    industry: '',
    stage: '',
    currency: 'USD',
  });
  const [baselineData, setBaselineData] = useState({
    monthly_revenue: 50000,
    gross_margin_pct: 70,
    opex: 20000,
    payroll: 30000,
    other_costs: 5000,
    cash_balance: 500000,
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSampleMode, setIsSampleMode] = useState(false);
  const [scanError, setScanError] = useState<string | null>(null);
  
  // File upload state
  const [isDragging, setIsDragging] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [isExtracting, setIsExtracting] = useState(false);
  const [extractedData, setExtractedData] = useState<ExtractedData | null>(null);
  const [extractionError, setExtractionError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);
  
  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);
  
  const processFile = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      toast({ title: 'Invalid file', description: 'Please upload a PDF file', variant: 'destructive' });
      return;
    }
    
    if (file.size > 20 * 1024 * 1024) {
      toast({ title: 'File too large', description: 'Maximum file size is 20MB', variant: 'destructive' });
      return;
    }
    
    const { token } = useFounderStore.getState();
    if (!token) {
      toast({ 
        title: 'Session expired', 
        description: 'Please log in again to continue.', 
        variant: 'destructive' 
      });
      setLocation('/auth');
      return;
    }
    
    setUploadedFile(file);
    setIsExtracting(true);
    setExtractionError(null);
    setExtractedData(null);
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch('/api/ingest/onboarding/extract-deck', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });
      
      if (!response.ok) {
        if (response.status === 401) {
          toast({ 
            title: 'Session expired', 
            description: 'Please log in again to continue.', 
            variant: 'destructive' 
          });
          setLocation('/auth');
          return;
        }
        const error = await response.json();
        throw new Error(error.detail || 'Extraction failed');
      }
      
      const data: ExtractedData = await response.json();
      setExtractedData(data);
      
      // Autofill company data with extracted values
      const extractedName = data.company_info?.name || '';
      const extractedIndustry = data.company_info?.industry || '';
      const extractedStage = data.company_info?.stage || '';
      
      if (data.company_info) {
        setCompanyData(prev => ({
          ...prev,
          name: extractedName || prev.name,
          website: data.company_info.website || prev.website,
          industry: extractedIndustry || prev.industry,
          stage: extractedStage || prev.stage,
          currency: data.currency || prev.currency,
        }));
      }
      
      // Autofill financial data
      if (data.financials) {
        setBaselineData(prev => ({
          monthly_revenue: data.financials.monthly_revenue ?? prev.monthly_revenue,
          gross_margin_pct: data.financials.gross_margin_pct ?? prev.gross_margin_pct,
          opex: data.financials.opex ?? prev.opex,
          payroll: data.financials.payroll ?? prev.payroll,
          other_costs: data.financials.other_costs ?? prev.other_costs,
          cash_balance: data.financials.cash_balance ?? prev.cash_balance,
        }));
      }
      
      // Build feedback message about what was extracted vs what's missing
      const missingFields: string[] = [];
      if (!extractedName) missingFields.push('company name');
      if (!extractedIndustry) missingFields.push('industry');
      if (!extractedStage) missingFields.push('stage');
      
      if (missingFields.length > 0) {
        toast({ 
          title: 'Partial extraction', 
          description: `Please fill in: ${missingFields.join(', ')}` 
        });
      } else {
        toast({ 
          title: 'Information extracted', 
          description: data.summary || 'All company details extracted successfully!' 
        });
      }
      
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to extract information';
      setExtractionError(message);
      toast({ title: 'Extraction failed', description: message, variant: 'destructive' });
    } finally {
      setIsExtracting(false);
    }
  };
  
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const file = e.dataTransfer.files[0];
    if (file) {
      processFile(file);
    }
  }, []);
  
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      processFile(file);
    }
  };
  
  const clearUpload = () => {
    setUploadedFile(null);
    setExtractedData(null);
    setExtractionError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };
  
  const createCompanyMutation = useCreateCompany();
  const manualBaselineMutation = useManualBaseline();
  const runTruthScanMutation = useRunTruthScan();
  
  const loadSampleCompany = async () => {
    if (isSubmitting || createCompanyMutation.isPending) return;
    
    const { token } = useFounderStore.getState();
    if (!token) {
      toast({ 
        title: 'Session expired', 
        description: 'Please log in again to continue.', 
        variant: 'destructive' 
      });
      setLocation('/auth');
      return;
    }
    
    setIsSubmitting(true);
    setIsSampleMode(true);
    setCompanyData(SAMPLE_COMPANY);
    setBaselineData(SAMPLE_FINANCIALS);
    
    try {
      const company = await createCompanyMutation.mutateAsync(SAMPLE_COMPANY);
      setCurrentCompany(company);
      toast({ 
        title: 'Sample company loaded', 
        description: 'TechFlow AI has been created with sample financials' 
      });
      setStep(2);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        toast({ 
          title: 'Session expired', 
          description: 'Please log in again to continue.', 
          variant: 'destructive' 
        });
        setLocation('/auth');
        return;
      }
      const message = err instanceof ApiError ? err.message : 'Failed to create sample company. Please try again.';
      toast({ title: 'Error', description: message, variant: 'destructive' });
      setIsSampleMode(false);
    } finally {
      setIsSubmitting(false);
    }
  };
  
  const handleCompanySubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    
    if (isSubmitting || createCompanyMutation.isPending) return;
    
    const { token } = useFounderStore.getState();
    if (!token) {
      toast({ 
        title: 'Session expired', 
        description: 'Please log in again to continue.', 
        variant: 'destructive' 
      });
      setLocation('/auth');
      return;
    }
    
    if (!companyData.name.trim()) {
      toast({ title: 'Validation Error', description: 'Company name is required', variant: 'destructive' });
      return;
    }
    
    if (!companyData.industry) {
      toast({ title: 'Validation Error', description: 'Please select an industry', variant: 'destructive' });
      return;
    }
    
    if (!companyData.stage) {
      toast({ title: 'Validation Error', description: 'Please select a company stage', variant: 'destructive' });
      return;
    }
    
    setIsSubmitting(true);
    try {
      // Include extracted data for use by truth scan
      const companyPayload = {
        ...companyData,
        extracted_metrics: extractedData?.computed_metrics || null,
        extracted_financials: extractedData?.financials || null
      };
      const company = await createCompanyMutation.mutateAsync(companyPayload);
      setCurrentCompany(company);
      setStep(2);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        toast({ 
          title: 'Session expired', 
          description: 'Please log in again to continue.', 
          variant: 'destructive' 
        });
        setLocation('/auth');
        return;
      }
      const message = err instanceof ApiError ? err.message : 'Failed to create company. Please try again.';
      toast({ title: 'Error', description: message, variant: 'destructive' });
    } finally {
      setIsSubmitting(false);
    }
  };
  
  const validateBaseline = (): string | null => {
    if (baselineData.monthly_revenue < 0) return 'Monthly revenue cannot be negative';
    if (baselineData.gross_margin_pct < 0 || baselineData.gross_margin_pct > 100) return 'Gross margin must be between 0 and 100%';
    if (baselineData.opex < 0) return 'Operating expenses cannot be negative';
    if (baselineData.payroll < 0) return 'Payroll cannot be negative';
    if (baselineData.other_costs < 0) return 'Other costs cannot be negative';
    if (baselineData.cash_balance < 0) return 'Cash balance cannot be negative';
    return null;
  };
  
  const handleBaselineSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    
    if (isSubmitting) return;
    
    setScanError(null);
    
    const validationError = validateBaseline();
    if (validationError) {
      toast({ title: 'Validation Error', description: validationError, variant: 'destructive' });
      return;
    }
    
    const { currentCompany, token } = useFounderStore.getState();
    if (!token) {
      toast({ 
        title: 'Session expired', 
        description: 'Please log in again to continue.', 
        variant: 'destructive' 
      });
      setLocation('/auth');
      return;
    }
    
    if (!currentCompany) {
      toast({ 
        title: 'Error', 
        description: 'No company selected. Please go back and create a company first.', 
        variant: 'destructive' 
      });
      setStep(1);
      return;
    }
    
    setIsSubmitting(true);
    setStep(3);
    
    try {
      await manualBaselineMutation.mutateAsync({
        companyId: currentCompany.id,
        data: baselineData,
      });
      
      const truthScan = await runTruthScanMutation.mutateAsync(currentCompany.id);
      setTruthScan(truthScan);
      setStoreStep('truth');
      
      toast({ title: 'Setup complete!', description: 'Your first Truth Scan is ready.' });
      setTimeout(() => setLocation('/'), 1500);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        toast({ 
          title: 'Session expired', 
          description: 'Please log in again to continue.', 
          variant: 'destructive' 
        });
        setLocation('/auth');
        return;
      }
      const message = err instanceof ApiError 
        ? err.message 
        : 'Failed to run Truth Scan. Please check your financial data and try again.';
      setScanError(message);
      toast({ title: 'Error', description: message, variant: 'destructive' });
      setStep(2);
    } finally {
      setIsSubmitting(false);
    }
  };
  
  const progress = (step / STEPS.length) * 100;
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-xl space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold">Getting Started</h1>
          <p className="text-muted-foreground">
            Step {step} of {STEPS.length}: {STEPS[step - 1].title}
          </p>
        </div>
        
        <Progress value={progress} className="h-2" data-testid="onboarding-progress" />
        
        {step === 1 && (
          <Card>
            <CardHeader>
              <CardTitle>Company Information</CardTitle>
              <CardDescription>Tell us about your startup</CardDescription>
            </CardHeader>
            <CardContent>
              {/* AI-Powered Upload Zone */}
              <div className="mb-6">
                <div
                  className={`relative border-2 border-dashed rounded-lg p-6 transition-colors cursor-pointer ${
                    isDragging 
                      ? 'border-primary bg-primary/5' 
                      : uploadedFile 
                        ? 'border-muted-foreground/30 bg-muted/30' 
                        : 'border-muted-foreground/30 hover:border-primary/50 hover:bg-muted/20'
                  }`}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => !isExtracting && fileInputRef.current?.click()}
                  data-testid="dropzone-deck-upload"
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf"
                    onChange={handleFileSelect}
                    className="hidden"
                    data-testid="input-file-upload"
                  />
                  
                  {isExtracting ? (
                    <div className="flex flex-col items-center gap-3 text-center">
                      <div className="p-3 rounded-full bg-primary/10">
                        <Loader2 className="w-8 h-8 text-primary animate-spin" />
                      </div>
                      <div>
                        <p className="font-medium">Analyzing your document...</p>
                        <p className="text-sm text-muted-foreground">
                          AI is extracting company and financial information
                        </p>
                      </div>
                    </div>
                  ) : extractedData ? (
                    <div className="flex flex-col items-center gap-3 text-center">
                      {/* Show green if all required fields present, amber if partial */}
                      {companyData.name && companyData.industry && companyData.stage ? (
                        <div className="p-3 rounded-full bg-green-500/10">
                          <Check className="w-8 h-8 text-green-500" />
                        </div>
                      ) : (
                        <div className="p-3 rounded-full bg-amber-500/10">
                          <AlertCircle className="w-8 h-8 text-amber-500" />
                        </div>
                      )}
                      <div>
                        <p className={`font-medium ${companyData.name && companyData.industry && companyData.stage ? 'text-green-600 dark:text-green-400' : 'text-amber-600 dark:text-amber-400'}`}>
                          {companyData.name && companyData.industry && companyData.stage 
                            ? 'Information extracted successfully' 
                            : 'Partial extraction - please complete missing fields'}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {uploadedFile?.name} - Check fields below
                        </p>
                        {(!companyData.name || !companyData.industry || !companyData.stage) && (
                          <p className="text-xs text-amber-500 mt-1">
                            Missing: {[
                              !companyData.name && 'Company Name',
                              !companyData.industry && 'Industry',
                              !companyData.stage && 'Stage'
                            ].filter(Boolean).join(', ')}
                          </p>
                        )}
                      </div>
                      <Button 
                        type="button" 
                        variant="ghost" 
                        size="sm" 
                        onClick={(e) => { e.stopPropagation(); clearUpload(); }}
                        data-testid="button-clear-upload"
                      >
                        Upload different file
                      </Button>
                    </div>
                  ) : extractionError ? (
                    <div className="flex flex-col items-center gap-3 text-center">
                      <div className="p-3 rounded-full bg-destructive/10">
                        <AlertCircle className="w-8 h-8 text-destructive" />
                      </div>
                      <div>
                        <p className="font-medium text-destructive">Extraction failed</p>
                        <p className="text-sm text-muted-foreground">{extractionError}</p>
                      </div>
                      <Button 
                        type="button" 
                        variant="ghost" 
                        size="sm" 
                        onClick={(e) => { e.stopPropagation(); clearUpload(); }}
                      >
                        Try again
                      </Button>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center gap-3 text-center">
                      <div className="p-3 rounded-full bg-primary/10">
                        <Sparkles className="w-8 h-8 text-primary" />
                      </div>
                      <div>
                        <p className="font-medium">Upload your pitch deck or investor update</p>
                        <p className="text-sm text-muted-foreground">
                          Drop a PDF here or click to browse. AI will auto-fill company and financial details.
                        </p>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <FileText className="w-3 h-3" />
                        <span>PDF files up to 20MB</span>
                      </div>
                    </div>
                  )}
                </div>
                
                {extractedData && extractedData.confidence && (
                  <div className="mt-3 flex items-center gap-4 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Check className="w-3 h-3 text-green-500" />
                      Company info: {Math.round((extractedData.confidence.company_info || 0) * 100)}% confident
                    </span>
                    <span className="flex items-center gap-1">
                      <Check className="w-3 h-3 text-green-500" />
                      Financials: {Math.round((extractedData.confidence.financials || 0) * 100)}% confident
                    </span>
                  </div>
                )}
                
                <div className="relative my-4">
                  <div className="absolute inset-0 flex items-center">
                    <span className="w-full border-t" />
                  </div>
                  <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-card px-2 text-muted-foreground">Or fill in manually</span>
                  </div>
                </div>
              </div>
              
              <form onSubmit={handleCompanySubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="company-name">Company Name <span className="text-destructive">*</span></Label>
                  <Input
                    id="company-name"
                    value={companyData.name}
                    onChange={(e) => setCompanyData({ ...companyData, name: e.target.value })}
                    required
                    placeholder="Your Company"
                    data-testid="input-company-name"
                    className={extractedData?.company_info?.name ? 'border-green-500/50' : !companyData.name.trim() ? 'border-amber-500/50' : ''}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="company-website">Website (optional)</Label>
                  <Input
                    id="company-website"
                    value={companyData.website}
                    onChange={(e) => setCompanyData({ ...companyData, website: e.target.value })}
                    placeholder="https://yourcompany.com"
                    data-testid="input-company-website"
                    className={extractedData?.company_info?.website ? 'border-green-500/50' : ''}
                  />
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Industry <span className="text-destructive">*</span></Label>
                    <Select
                      value={companyData.industry}
                      onValueChange={(v) => setCompanyData({ ...companyData, industry: v })}
                    >
                      <SelectTrigger 
                        data-testid="select-industry"
                        className={extractedData?.company_info?.industry ? 'border-green-500/50' : !companyData.industry ? 'border-amber-500/50' : ''}
                      >
                        <SelectValue placeholder="Select industry..." />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="general_saas">SaaS</SelectItem>
                        <SelectItem value="fintech">Fintech</SelectItem>
                        <SelectItem value="ecommerce">E-commerce</SelectItem>
                        <SelectItem value="marketplace">Marketplace</SelectItem>
                        <SelectItem value="other">Other</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Stage <span className="text-destructive">*</span></Label>
                    <Select
                      value={companyData.stage}
                      onValueChange={(v) => setCompanyData({ ...companyData, stage: v })}
                    >
                      <SelectTrigger 
                        data-testid="select-stage"
                        className={extractedData?.company_info?.stage ? 'border-green-500/50' : !companyData.stage ? 'border-amber-500/50' : ''}
                      >
                        <SelectValue placeholder="Select stage..." />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="pre_seed">Pre-seed</SelectItem>
                        <SelectItem value="seed">Seed</SelectItem>
                        <SelectItem value="series_a">Series A</SelectItem>
                        <SelectItem value="series_b">Series B+</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                
                {/* Show validation message if form is incomplete */}
                {(!companyData.name.trim() || !companyData.industry || !companyData.stage) && (
                  <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-md text-sm text-amber-600 dark:text-amber-400">
                    Please fill in all required fields: {[
                      !companyData.name.trim() && 'Company Name',
                      !companyData.industry && 'Industry',
                      !companyData.stage && 'Stage'
                    ].filter(Boolean).join(', ')}
                  </div>
                )}
                
                <Button
                  type="submit"
                  className="w-full"
                  disabled={isSubmitting || createCompanyMutation.isPending || !companyData.name.trim() || !companyData.industry || !companyData.stage}
                  data-testid="button-next-step"
                >
                  {isSubmitting || createCompanyMutation.isPending ? 'Creating...' : 'Continue'}
                </Button>
                
                <div className="relative my-4">
                  <div className="absolute inset-0 flex items-center">
                    <span className="w-full border-t" />
                  </div>
                  <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-card px-2 text-muted-foreground">Or try with sample data</span>
                  </div>
                </div>
                
                <Button
                  type="button"
                  variant="outline"
                  className="w-full"
                  onClick={loadSampleCompany}
                  disabled={isSubmitting || createCompanyMutation.isPending}
                  data-testid="button-load-sample"
                >
                  {isSubmitting && isSampleMode ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Loading Sample Company...
                    </>
                  ) : (
                    <>
                      <Sparkles className="mr-2 h-4 w-4" />
                      Load Sample Company
                    </>
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>
        )}
        
        {step === 2 && (
          <Card>
            <CardHeader>
              <CardTitle>Financial Baseline</CardTitle>
              <CardDescription>
                {isSampleMode 
                  ? 'Sample financials are pre-filled below. Click "Run First Truth Scan" to continue.'
                  : 'Enter your current monthly financials. These values will be used to compute your first Truth Scan.'}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {scanError && (
                <div className="mb-4 p-3 bg-destructive/10 border border-destructive/30 rounded-md flex items-start gap-2">
                  <AlertCircle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-destructive">Truth Scan Failed</p>
                    <p className="text-xs text-muted-foreground">{scanError}</p>
                  </div>
                </div>
              )}
              <form onSubmit={handleBaselineSubmit} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <div className="flex items-center gap-1">
                      <Label htmlFor="revenue">Monthly Revenue ($)</Label>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <HelpCircle className="h-3.5 w-3.5 text-muted-foreground cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent side="top" className="max-w-xs">
                          <p>Your total monthly recurring revenue (MRR) from subscriptions and recurring sales.</p>
                        </TooltipContent>
                      </Tooltip>
                    </div>
                    <Input
                      id="revenue"
                      type="number"
                      value={baselineData.monthly_revenue}
                      onChange={(e) => setBaselineData({ ...baselineData, monthly_revenue: Number(e.target.value) })}
                      required
                      min={0}
                      data-testid="input-revenue"
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex items-center gap-1">
                      <Label htmlFor="gross-margin">Gross Margin (%)</Label>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <HelpCircle className="h-3.5 w-3.5 text-muted-foreground cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent side="top" className="max-w-xs">
                          <p>Revenue minus cost of goods sold, divided by revenue. SaaS companies typically have 70-85% gross margin.</p>
                        </TooltipContent>
                      </Tooltip>
                    </div>
                    <Input
                      id="gross-margin"
                      type="number"
                      value={baselineData.gross_margin_pct}
                      onChange={(e) => setBaselineData({ ...baselineData, gross_margin_pct: Number(e.target.value) })}
                      required
                      min={0}
                      max={100}
                      data-testid="input-gross-margin"
                    />
                  </div>
                </div>
                
                <div className="grid grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <div className="flex items-center gap-1">
                      <Label htmlFor="opex">Opex ($)</Label>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <HelpCircle className="h-3.5 w-3.5 text-muted-foreground cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent side="top" className="max-w-xs">
                          <p>Operating expenses: rent, software, marketing, and other non-payroll costs.</p>
                        </TooltipContent>
                      </Tooltip>
                    </div>
                    <Input
                      id="opex"
                      type="number"
                      value={baselineData.opex}
                      onChange={(e) => setBaselineData({ ...baselineData, opex: Number(e.target.value) })}
                      required
                      min={0}
                      data-testid="input-opex"
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex items-center gap-1">
                      <Label htmlFor="payroll">Payroll ($)</Label>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <HelpCircle className="h-3.5 w-3.5 text-muted-foreground cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent side="top" className="max-w-xs">
                          <p>Total monthly employee salaries, benefits, and payroll taxes.</p>
                        </TooltipContent>
                      </Tooltip>
                    </div>
                    <Input
                      id="payroll"
                      type="number"
                      value={baselineData.payroll}
                      onChange={(e) => setBaselineData({ ...baselineData, payroll: Number(e.target.value) })}
                      required
                      min={0}
                      data-testid="input-payroll"
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex items-center gap-1">
                      <Label htmlFor="other-costs">Other Costs ($)</Label>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <HelpCircle className="h-3.5 w-3.5 text-muted-foreground cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent side="top" className="max-w-xs">
                          <p>Miscellaneous expenses not included in Opex or Payroll.</p>
                        </TooltipContent>
                      </Tooltip>
                    </div>
                    <Input
                      id="other-costs"
                      type="number"
                      value={baselineData.other_costs}
                      onChange={(e) => setBaselineData({ ...baselineData, other_costs: Number(e.target.value) })}
                      min={0}
                      data-testid="input-other-costs"
                    />
                  </div>
                </div>
                
                <div className="space-y-2">
                  <div className="flex items-center gap-1">
                    <Label htmlFor="cash">Cash Balance ($)</Label>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <HelpCircle className="h-3.5 w-3.5 text-muted-foreground cursor-help" />
                      </TooltipTrigger>
                      <TooltipContent side="top" className="max-w-xs">
                        <p>Total cash and cash equivalents currently in your bank accounts.</p>
                      </TooltipContent>
                    </Tooltip>
                  </div>
                  <Input
                    id="cash"
                    type="number"
                    value={baselineData.cash_balance}
                    onChange={(e) => setBaselineData({ ...baselineData, cash_balance: Number(e.target.value) })}
                    required
                    min={0}
                    data-testid="input-cash-balance"
                  />
                </div>
                
                <Button
                  type="submit"
                  className="w-full"
                  disabled={isSubmitting || manualBaselineMutation.isPending || runTruthScanMutation.isPending}
                  data-testid="button-run-scan"
                >
                  {isSubmitting || manualBaselineMutation.isPending || runTruthScanMutation.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Running Truth Scan...
                    </>
                  ) : scanError ? (
                    'Retry Truth Scan'
                  ) : (
                    'Run First Truth Scan'
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>
        )}
        
        {step === 3 && (
          <Card>
            <CardHeader className="text-center">
              <CardTitle>Analyzing Your Data</CardTitle>
              <CardDescription>Running your first Truth Scan...</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col items-center py-8">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
              <p className="mt-4 text-muted-foreground">Computing 24 metrics and benchmarks</p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
