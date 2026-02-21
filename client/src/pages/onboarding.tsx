import { useState, useRef, useCallback, useEffect } from 'react';
import { useLocation } from 'wouter';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Progress } from '@/components/ui/progress';
import { useToast } from '@/hooks/use-toast';
import { ApiError } from '@/api/client';
import { apiRequest } from '@/lib/queryClient';
import { useFounderStore } from '@/store/founderStore';
import { useCreateCompany, useManualBaseline, useRunTruthScan, useSeedSample } from '@/api/hooks';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { HelpCircle, Upload, FileText, Sparkles, Check, AlertCircle, Loader2, Eye, MessageSquare, Download, Info, Search, Globe, History, Database, CreditCard, BarChart3, Users, Building2, Link2, ArrowRight, ExternalLink, ChevronRight, SkipForward } from 'lucide-react';
import type { AmountScale } from '@/lib/utils';
import { SCALE_LABELS } from '@/lib/utils';
import { Skeleton } from '@/components/ui/skeleton';

const STEPS = [
  { id: 1, title: 'Company Basics', description: 'Tell us about your startup' },
  { id: 2, title: 'Financial Snapshot', description: 'Quick financial overview' },
  { id: 3, title: 'Expense Breakdown', description: 'Optional detailed costs' },
  { id: 4, title: 'Data Sources', description: 'Connect or upload data' },
];

interface DataSourceConnector {
  id: string;
  name: string;
  category: string;
  description: string;
  auth_type: string;
  native: boolean;
  beta: boolean;
  popularity_rank: number;
  setup_complexity: string;
  metrics_unlocked: string[];
  implemented: boolean;
  [key: string]: unknown;
}

const CATEGORY_ICONS: Record<string, typeof Database> = {
  Finance: CreditCard,
  Banking: Building2,
  Payroll: Users,
  CRM: Users,
  Analytics: BarChart3,
  ERP: Building2,
  Files: FileText,
  Databases: Database,
  Custom: Link2,
};

const CATEGORY_ORDER = ['Finance', 'Banking', 'Payroll', 'CRM', 'Analytics', 'ERP', 'Files'];

const CURRENCY_MAP: Record<string, { currency: string; label: string }> = {
  '.in': { currency: 'INR', label: 'Indian Rupee (INR)' },
  '.uk': { currency: 'GBP', label: 'British Pound (GBP)' },
  '.co.uk': { currency: 'GBP', label: 'British Pound (GBP)' },
  '.eu': { currency: 'EUR', label: 'Euro (EUR)' },
  '.de': { currency: 'EUR', label: 'Euro (EUR)' },
  '.fr': { currency: 'EUR', label: 'Euro (EUR)' },
  '.es': { currency: 'EUR', label: 'Euro (EUR)' },
  '.it': { currency: 'EUR', label: 'Euro (EUR)' },
  '.nl': { currency: 'EUR', label: 'Euro (EUR)' },
  '.sg': { currency: 'SGD', label: 'Singapore Dollar (SGD)' },
  '.au': { currency: 'AUD', label: 'Australian Dollar (AUD)' },
  '.ca': { currency: 'CAD', label: 'Canadian Dollar (CAD)' },
  '.jp': { currency: 'JPY', label: 'Japanese Yen (JPY)' },
  '.br': { currency: 'BRL', label: 'Brazilian Real (BRL)' },
  '.ng': { currency: 'NGN', label: 'Nigerian Naira (NGN)' },
  '.ke': { currency: 'KES', label: 'Kenyan Shilling (KES)' },
  '.za': { currency: 'ZAR', label: 'South African Rand (ZAR)' },
  '.ae': { currency: 'AED', label: 'UAE Dirham (AED)' },
  '.se': { currency: 'SEK', label: 'Swedish Krona (SEK)' },
  '.ch': { currency: 'CHF', label: 'Swiss Franc (CHF)' },
  '.kr': { currency: 'KRW', label: 'South Korean Won (KRW)' },
  '.cn': { currency: 'CNY', label: 'Chinese Yuan (CNY)' },
  '.hk': { currency: 'HKD', label: 'Hong Kong Dollar (HKD)' },
  '.mx': { currency: 'MXN', label: 'Mexican Peso (MXN)' },
  '.il': { currency: 'ILS', label: 'Israeli Shekel (ILS)' },
};

const ALL_CURRENCIES = [
  { value: 'USD', label: 'US Dollar (USD)' },
  { value: 'EUR', label: 'Euro (EUR)' },
  { value: 'GBP', label: 'British Pound (GBP)' },
  { value: 'INR', label: 'Indian Rupee (INR)' },
  { value: 'SGD', label: 'Singapore Dollar (SGD)' },
  { value: 'AUD', label: 'Australian Dollar (AUD)' },
  { value: 'CAD', label: 'Canadian Dollar (CAD)' },
  { value: 'JPY', label: 'Japanese Yen (JPY)' },
  { value: 'BRL', label: 'Brazilian Real (BRL)' },
  { value: 'CHF', label: 'Swiss Franc (CHF)' },
  { value: 'SEK', label: 'Swedish Krona (SEK)' },
  { value: 'AED', label: 'UAE Dirham (AED)' },
  { value: 'HKD', label: 'Hong Kong Dollar (HKD)' },
  { value: 'KRW', label: 'South Korean Won (KRW)' },
  { value: 'CNY', label: 'Chinese Yuan (CNY)' },
  { value: 'ILS', label: 'Israeli Shekel (ILS)' },
  { value: 'MXN', label: 'Mexican Peso (MXN)' },
  { value: 'NGN', label: 'Nigerian Naira (NGN)' },
  { value: 'KES', label: 'Kenyan Shilling (KES)' },
  { value: 'ZAR', label: 'South African Rand (ZAR)' },
];

function detectCurrencyFromWebsite(url: string): string | null {
  try {
    const hostname = new URL(url.startsWith('http') ? url : `https://${url}`).hostname.toLowerCase();
    for (const [tld, info] of Object.entries(CURRENCY_MAP)) {
      if (hostname.endsWith(tld)) return info.currency;
    }
  } catch {}
  return null;
}

const SAMPLE_COMPANY = {
  name: 'TechFlow AI',
  website: 'https://techflow.ai',
  industry: 'general_saas',
  stage: 'seed',
  currency: 'USD',
  amount_scale: 'UNITS' as AmountScale,
};

const SAMPLE_FINANCIALS = {
  monthly_revenue: 85000,
  gross_margin_pct: 75,
  opex: 25000,
  payroll: 45000,
  other_costs: 8000,
  cash_balance: 750000,
  headcount: 12,
};

const STAGE_DEFAULTS: Record<string, { monthly_revenue: number; gross_margin_pct: number; opex: number; payroll: number; other_costs: number; cash_balance: number; headcount: number }> = {
  pre_seed: { monthly_revenue: 0, gross_margin_pct: 0, opex: 5000, payroll: 0, other_costs: 2000, cash_balance: 50000, headcount: 3 },
  seed: { monthly_revenue: 25000, gross_margin_pct: 75, opex: 15000, payroll: 35000, other_costs: 5000, cash_balance: 1000000, headcount: 8 },
  pre_series_a: { monthly_revenue: 60000, gross_margin_pct: 72, opex: 30000, payroll: 80000, other_costs: 10000, cash_balance: 2000000, headcount: 18 },
  series_a: { monthly_revenue: 150000, gross_margin_pct: 70, opex: 40000, payroll: 80000, other_costs: 15000, cash_balance: 2000000, headcount: 25 },
  series_b: { monthly_revenue: 500000, gross_margin_pct: 72, opex: 100000, payroll: 200000, other_costs: 30000, cash_balance: 5000000, headcount: 60 },
  growth: { monthly_revenue: 1000000, gross_margin_pct: 75, opex: 200000, payroll: 400000, other_costs: 50000, cash_balance: 10000000, headcount: 120 },
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
    opex?: number;
    payroll?: number;
    other_costs?: number;
    cash_balance?: number;
    arr?: number;
    mrr?: number;
    headcount?: number;
  };
  currency?: string;
  confidence?: { company_info: number; financials: number };
  summary?: string;
  extraction_method?: string;
  raw_data_preview?: {
    columns: string[];
    row_count: number;
    sample_rows: Record<string, unknown>[];
  };
}

export default function OnboardingPage() {
  const [, setLocation] = useLocation();
  const { toast } = useToast();
  const { setCurrentCompany, setTruthScan, setCurrentStep: setStoreStep } = useFounderStore();
  const [step, setStep] = useState(1);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);
  const [showDefaultsBanner, setShowDefaultsBanner] = useState(false);
  const [companyData, setCompanyData] = useState({
    name: '',
    website: '',
    industry: '',
    stage: '',
    currency: 'USD',
    amount_scale: 'UNITS' as AmountScale,
  });
  const [baselineData, setBaselineData] = useState({
    monthly_revenue: 0,
    gross_margin_pct: 0,
    opex: 0,
    payroll: 0,
    other_costs: 0,
    cash_balance: 0,
    headcount: 0,
  });
  const [expenseBreakdown, setExpenseBreakdown] = useState({
    payroll: 0,
    marketing: 0,
    operating: 0,
    cogs: 0,
  });
  const [dataSourceChoice, setDataSourceChoice] = useState<'manual' | 'upload' | 'connect' | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSampleMode, setIsSampleMode] = useState(false);
  const [scanError, setScanError] = useState<string | null>(null);
  const [showCompletionScreen, setShowCompletionScreen] = useState(false);
  
  // File upload state
  const [isDragging, setIsDragging] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [isExtracting, setIsExtracting] = useState(false);
  const [extractedData, setExtractedData] = useState<ExtractedData | null>(null);
  const [extractionError, setExtractionError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Data preview/cross-check state
  const [showDataPreview, setShowDataPreview] = useState(false);
  const [showFeedbackDialog, setShowFeedbackDialog] = useState(false);
  const [feedbackText, setFeedbackText] = useState('');
  
  // AI company lookup state
  const [isFetchingAI, setIsFetchingAI] = useState(false);
  const [aiLookupSummary, setAiLookupSummary] = useState<string | null>(null);
  
  // Uploaded file history
  const [uploadHistory, setUploadHistory] = useState<Array<{ name: string; uploadedAt: Date; type: string }>>([]);
  
  // Query existing companies for the user
  const { data: existingCompanies } = useQuery<Array<{ id: number; name: string; industry?: string; stage?: string; website?: string }>>({
    queryKey: ['/api/companies'],
  });
  
  // If user has an existing company, pre-fill the form
  useEffect(() => {
    if (existingCompanies && existingCompanies.length > 0 && !companyData.name) {
      const existing = existingCompanies[0];
      setCompanyData(prev => ({
        ...prev,
        name: existing.name || prev.name,
        industry: existing.industry || prev.industry,
        stage: existing.stage || prev.stage,
        website: existing.website || prev.website,
      }));
    }
  }, [existingCompanies]);
  
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);
  
  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);
  
  const processFile = async (file: File) => {
    const fileName = file.name.toLowerCase();
    const validExtensions = ['.pdf', '.xls', '.xlsx', '.csv'];
    const hasValidExtension = validExtensions.some(ext => fileName.endsWith(ext));
    
    if (!hasValidExtension) {
      toast({ title: 'Invalid file', description: 'Please upload a PDF, Excel (.xls, .xlsx), or CSV file', variant: 'destructive' });
      return;
    }
    
    if (file.size > 20 * 1024 * 1024) {
      toast({ title: 'File too large', description: 'Maximum file size is 20MB', variant: 'destructive' });
      return;
    }
    
    // Note: extract-deck endpoint is unauthenticated to support onboarding before login
    // Auth token is optional - send if available for better logging
    const { token } = useFounderStore.getState();
    
    setUploadedFile(file);
    setIsExtracting(true);
    setExtractionError(null);
    setExtractedData(null);
    
    // Add to upload history
    setUploadHistory(prev => [
      { name: file.name, uploadedAt: new Date(), type: file.type || 'document' },
      ...prev.slice(0, 4) // Keep last 5 files
    ]);
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const headers: Record<string, string> = {};
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      
      const response = await fetch('/api/ingest/onboarding/extract-deck', {
        method: 'POST',
        headers,
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
        // Handle 422 (unprocessable/corrupted file) specifically
        if (response.status === 422) {
          throw new Error(error.detail || 'The file could not be processed. Please try a different PDF or enter details manually.');
        }
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
          headcount: data.financials.headcount ?? prev.headcount,
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
  
  const fetchCompanyDetailsAI = async () => {
    const website = companyData.website?.trim();
    if (!website) {
      toast({ 
        title: 'Website required', 
        description: 'Please enter a company website to fetch details.', 
        variant: 'destructive' 
      });
      return;
    }
    
    setIsFetchingAI(true);
    setAiLookupSummary(null);
    
    try {
      const response = await fetch('/api/lookup/company-from-website', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ website }),
      });
      
      const data = await response.json();
      
      if (data.success && data.company) {
        const company = data.company;
        setCompanyData(prev => ({
          ...prev,
          name: prev.name.trim() ? prev.name : (company.name || prev.name),
          industry: prev.industry ? prev.industry : (company.industry || prev.industry),
          stage: prev.stage ? prev.stage : (company.stage || prev.stage),
        }));
        
        setAiLookupSummary(data.summary || company.description);
        
        toast({ 
          title: 'Company details fetched!', 
          description: `Found information about ${company.name || 'the company'}` 
        });
      } else {
        toast({ 
          title: 'Could not fetch details', 
          description: data.error || 'Unable to find company information. Please fill in manually.', 
          variant: 'destructive' 
        });
      }
    } catch (err) {
      toast({ 
        title: 'Error', 
        description: 'Failed to fetch company details. Please try again.', 
        variant: 'destructive' 
      });
    } finally {
      setIsFetchingAI(false);
    }
  };
  
  const createCompanyMutation = useCreateCompany();
  const manualBaselineMutation = useManualBaseline();
  const runTruthScanMutation = useRunTruthScan();
  const seedSampleMutation = useSeedSample();
  
  const isSeedingInProgress = createCompanyMutation.isPending || seedSampleMutation.isPending;
  
  const loadSampleCompany = async () => {
    if (isSubmitting || isSeedingInProgress) return;
    
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
      
      await seedSampleMutation.mutateAsync(company.id);
      
      toast({ 
        title: 'Sample data loaded!', 
        description: 'Redirecting to dashboard...' 
      });
      setLocation("/");
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
  
  const markStepComplete = (stepNum: number) => {
    if (!completedSteps.includes(stepNum)) {
      setCompletedSteps([...completedSteps, stepNum]);
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
      let company;

      company = await createCompanyMutation.mutateAsync(companyData);

      setCurrentCompany(company);
      markStepComplete(1);
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
    if (baselineData.monthly_revenue <= 0 && baselineData.cash_balance <= 0) return 'Please enter at least monthly revenue or cash balance';
    if (baselineData.monthly_revenue < 0) return 'Monthly revenue cannot be negative';
    if (baselineData.gross_margin_pct < 0 || baselineData.gross_margin_pct > 100) return 'Gross margin must be between 0 and 100%';
    if (baselineData.opex < 0) return 'Operating expenses cannot be negative';
    if (baselineData.payroll < 0) return 'Payroll cannot be negative';
    if (baselineData.other_costs < 0) return 'Other costs cannot be negative';
    if (baselineData.cash_balance < 0) return 'Cash balance cannot be negative';
    if (baselineData.headcount < 0) return 'Headcount cannot be negative';
    return null;
  };
  
  const [selectedConnectors, setSelectedConnectors] = useState<Set<string>>(new Set());
  const [activeCategory, setActiveCategory] = useState<string | null>(null);

  const { data: connectorCatalog, isLoading: connectorsLoading } = useQuery<DataSourceConnector[]>({
    queryKey: ['/api/connectors/catalog'],
    enabled: step === 3,
  });

  const groupedConnectors = (() => {
    if (!connectorCatalog) return {};
    const groups: Record<string, DataSourceConnector[]> = {};
    for (const c of connectorCatalog) {
      if (c.category === 'Custom' || c.category === 'Databases') continue;
      if (!groups[c.category]) groups[c.category] = [];
      groups[c.category].push(c);
    }
    for (const cat of Object.keys(groups)) {
      groups[cat].sort((a, b) => a.popularity_rank - b.popularity_rank);
    }
    return groups;
  })();

  const toggleConnector = (id: string) => {
    setSelectedConnectors(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleRunTruthScan = async () => {
    const { currentCompany, token } = useFounderStore.getState();
    if (!token) {
      toast({ title: 'Session expired', description: 'Please log in again.', variant: 'destructive' });
      setLocation('/auth');
      return;
    }
    if (!currentCompany) {
      toast({ title: 'Error', description: 'No company found. Please go back.', variant: 'destructive' });
      setStep(1);
      return;
    }

    setIsSubmitting(true);
    setScanError(null);

    try {
      const truthScan = await runTruthScanMutation.mutateAsync(currentCompany.id);
      setTruthScan(truthScan);
      setStoreStep('truth');
      markStepComplete(4);
      setShowCompletionScreen(true);
      toast({ title: 'Setup complete!', description: 'Your first Truth Scan is ready.' });
      setTimeout(() => setLocation('/'), 2000);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        toast({ title: 'Session expired', description: 'Please log in again.', variant: 'destructive' });
        setLocation('/auth');
        return;
      }
      const message = err instanceof ApiError ? err.message : 'Failed to run Truth Scan. Please try again.';
      setScanError(message);
      toast({ title: 'Error', description: message, variant: 'destructive' });
      setStep(4);
    } finally {
      setIsSubmitting(false);
    }
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

    try {
      await manualBaselineMutation.mutateAsync({
        companyId: currentCompany.id,
        data: baselineData,
      });

      markStepComplete(2);
      toast({ title: 'Financial snapshot saved!' });
      setStep(3);
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
        : 'Failed to save baseline. Please try again.';
      toast({ title: 'Error', description: message, variant: 'destructive' });
    } finally {
      setIsSubmitting(false);
    }
  };
  
  const progress = (step / STEPS.length) * 100;

  if (showCompletionScreen) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <div className="w-full max-w-xl space-y-6">
          <Card>
            <CardContent className="flex flex-col items-center text-center pt-8">
              <div className="p-4 rounded-full bg-green-500/10 mb-4">
                <Check className="w-12 h-12 text-green-500" />
              </div>
              <h2 className="text-2xl font-bold mb-2">Your company is set up!</h2>
              <p className="text-muted-foreground mb-6">
                Here's what happens next...
              </p>

              <div className="w-full bg-muted/50 rounded-lg p-4 mb-6 border">
                <div className="flex items-start gap-3">
                  <Sparkles className="w-5 h-5 text-primary mt-1 shrink-0" />
                  <div className="text-left">
                    <h4 className="font-medium mb-1">Truth Scan Ready</h4>
                    <p className="text-sm text-muted-foreground">
                      We've computed 24 financial metrics and benchmarks specific to your {companyData.stage?.replace(/_/g, ' ')} {companyData.industry} company.
                    </p>
                  </div>
                </div>
              </div>

              <div className="w-full space-y-3 mb-6">
                <div className="flex items-center gap-2 text-sm text-left">
                  <Check className="w-4 h-4 text-green-500" />
                  <span>Cash runway and burn analysis</span>
                </div>
                <div className="flex items-center gap-2 text-sm text-left">
                  <Check className="w-4 h-4 text-green-500" />
                  <span>Benchmarks against similar companies</span>
                </div>
                <div className="flex items-center gap-2 text-sm text-left">
                  <Check className="w-4 h-4 text-green-500" />
                  <span>Growth trajectory and profitability forecast</span>
                </div>
              </div>

              <Button
                className="w-full"
                onClick={() => setLocation('/')}
              >
                <Sparkles className="mr-2 h-4 w-4" />
                Run Your First Truth Scan
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-2xl space-y-6">
        {/* Progress Bar with Step Indicators */}
        <div className="space-y-4">
          <div className="flex items-center justify-between mb-2">
            <h1 className="text-2xl font-bold">Getting Started</h1>
            {step < STEPS.length && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  toast({
                    title: 'Progress saved',
                    description: 'You can return to this onboarding flow anytime.',
                  });
                }}
                className="text-xs"
              >
                <SkipForward className="w-3.5 h-3.5 mr-1.5" />
                Save & Continue Later
              </Button>
            )}
          </div>

          <div className="flex items-center justify-between gap-2">
            {STEPS.map((s, idx) => (
              <div key={s.id} className="flex items-center flex-1">
                <div className="flex items-center gap-2 flex-1">
                  <div className={`flex items-center justify-center w-8 h-8 rounded-full font-medium text-sm ${
                    completedSteps.includes(s.id)
                      ? 'bg-green-500 text-white'
                      : step === s.id
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted text-muted-foreground'
                  }`}>
                    {completedSteps.includes(s.id) ? (
                      <Check className="w-4 h-4" />
                    ) : (
                      s.id
                    )}
                  </div>
                  <div className="hidden sm:block">
                    <p className="text-sm font-medium">{s.title}</p>
                    <p className="text-xs text-muted-foreground">{s.description}</p>
                  </div>
                </div>
                {idx < STEPS.length - 1 && (
                  <ChevronRight className="w-5 h-5 text-muted-foreground mx-2 shrink-0" />
                )}
              </div>
            ))}
          </div>

          <Progress value={progress} className="h-2" data-testid="onboarding-progress" />
        </div>
        
        {step === 1 && (
          <Card>
            <CardHeader>
              <CardTitle>Company Basics</CardTitle>
              <CardDescription>Tell us about your startup so we can find relevant benchmarks</CardDescription>
            </CardHeader>
            <CardContent>
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
                    onBlur={(e) => {
                      const detected = detectCurrencyFromWebsite(e.target.value);
                      if (detected && companyData.currency === 'USD') {
                        setCompanyData(prev => ({ ...prev, currency: detected }));
                      }
                    }}
                    placeholder="https://yourcompany.com"
                    data-testid="input-company-website"
                  />
                  <p className="text-xs text-muted-foreground">Used to detect your location for currency conversion</p>
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
                        <SelectItem value="d2c">D2C / Consumer</SelectItem>
                        <SelectItem value="marketplace">Marketplace</SelectItem>
                        <SelectItem value="healthcare">Healthcare / BioTech</SelectItem>
                        <SelectItem value="edtech">EdTech</SelectItem>
                        <SelectItem value="agritech">AgriTech</SelectItem>
                        <SelectItem value="deeptech">DeepTech / Hardware</SelectItem>
                        <SelectItem value="climate">Climate / CleanTech</SelectItem>
                        <SelectItem value="media">Media / Entertainment</SelectItem>
                        <SelectItem value="logistics">Logistics / Supply Chain</SelectItem>
                        <SelectItem value="real_estate">Real Estate / PropTech</SelectItem>
                        <SelectItem value="food">Food / CPG</SelectItem>
                        <SelectItem value="other">Other</SelectItem>
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground mt-1">Helps us find the right benchmarks for your company</p>
                  </div>

                  <div className="space-y-2">
                    <Label>Stage <span className="text-destructive">*</span></Label>
                    <Select
                      value={companyData.stage}
                      onValueChange={(v) => {
                        setCompanyData({ ...companyData, stage: v });
                        const defaults = STAGE_DEFAULTS[v];
                        if (defaults) {
                          const untouched = Object.values(baselineData).every(val => val === 0);
                          if (untouched) {
                            setBaselineData(defaults);
                            setShowDefaultsBanner(true);
                          }
                        }
                      }}
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
                        <SelectItem value="pre_series_a">Pre-Series A</SelectItem>
                        <SelectItem value="series_a">Series A</SelectItem>
                        <SelectItem value="series_b">Series B+</SelectItem>
                        <SelectItem value="growth">Growth Stage</SelectItem>
                        <SelectItem value="pre_ipo">Pre-IPO</SelectItem>
                        <SelectItem value="public">Public / Listed</SelectItem>
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground mt-1">This helps us calibrate financial expectations</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Currency</Label>
                    <Select
                      value={companyData.currency}
                      onValueChange={(v) => setCompanyData({ ...companyData, currency: v })}
                    >
                      <SelectTrigger data-testid="select-currency">
                        <SelectValue placeholder="Select currency..." />
                      </SelectTrigger>
                      <SelectContent>
                        {ALL_CURRENCIES.map(c => (
                          <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Amount Scale</Label>
                    <Select
                      value={companyData.amount_scale}
                      onValueChange={(v) => setCompanyData({ ...companyData, amount_scale: v as AmountScale })}
                    >
                      <SelectTrigger data-testid="select-amount-scale">
                        <SelectValue placeholder="Select scale..." />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="UNITS">Units</SelectItem>
                        <SelectItem value="THOUSANDS">Thousands</SelectItem>
                        <SelectItem value="MILLIONS">Millions</SelectItem>
                        <SelectItem value="CRORES">Crores</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <Button
                  type="submit"
                  className="w-full"
                  disabled={isSubmitting || createCompanyMutation.isPending || !companyData.name.trim() || !companyData.industry || !companyData.stage}
                  data-testid="button-next-step"
                >
                  {isSubmitting || createCompanyMutation.isPending ? 'Creating...' : 'Next: Financial Snapshot'}
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </form>
            </CardContent>
          </Card>
        )}
        
        {step === 2 && (
          <Card>
            <CardHeader>
              <CardTitle>Financial Snapshot</CardTitle>
              <CardDescription>Tell us about your current financial position. We'll use this to model your growth trajectory.</CardDescription>
            </CardHeader>
            <CardContent>
              {showDefaultsBanner && companyData.stage && (
                <div className="p-3 bg-blue-500/10 border border-blue-500/30 rounded-md text-sm flex items-center justify-between gap-2 mb-4" data-testid="banner-defaults">
                  <span>Pre-filled with typical values for {companyData.stage.replace(/_/g, ' ')} companies. Adjust to match your actuals.</span>
                  <button onClick={() => setShowDefaultsBanner(false)} className="text-muted-foreground hover:bg-blue-500/5 rounded-md px-1" data-testid="button-dismiss-banner" aria-label="Dismiss">x</button>
                </div>
              )}
              
              {companyData.amount_scale !== 'UNITS' && (
                <div className="mb-4 p-3 bg-blue-500/10 border border-blue-500/30 rounded-md flex items-center gap-2">
                  <Info className="h-4 w-4 text-blue-500 shrink-0" />
                  <p className="text-sm text-blue-600 dark:text-blue-400">
                    All monetary values in {companyData.amount_scale.charAt(0) + companyData.amount_scale.slice(1).toLowerCase()}
                  </p>
                </div>
              )}

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
                      step="any"
                      value={baselineData.monthly_revenue}
                      onChange={(e) => setBaselineData({ ...baselineData, monthly_revenue: Number(e.target.value) })}
                      required
                      min={0}
                      data-testid="input-revenue"
                    />
                    {baselineData.monthly_revenue === 0 && (
                      <Card className="overflow-visible border-blue-500/30 bg-blue-500/5" data-testid="card-pre-revenue-guidance">
                        <CardContent className="p-4">
                          <div className="flex items-start gap-3">
                            <Info className="h-5 w-5 text-blue-400 mt-0.5" />
                            <div className="space-y-3">
                              <div>
                                <h4 className="font-medium text-sm">Pre-Revenue Company</h4>
                                <p className="text-xs text-muted-foreground mt-1">
                                  No revenue? No problem. FounderConsole will optimize for runway extension and milestone tracking instead of growth metrics.
                                </p>
                              </div>
                              <div className="space-y-2">
                                <p className="text-xs font-medium text-muted-foreground">Key Milestones to Track:</p>
                                <div className="grid grid-cols-2 gap-2">
                                  {[
                                    { label: 'First Customer', icon: 'Users' },
                                    { label: 'Product Launch', icon: 'Zap' },
                                    { label: 'First Revenue', icon: 'DollarSign' },
                                    { label: 'Break Even', icon: 'Target' },
                                  ].map(m => (
                                    <div key={m.label} className="flex items-center gap-2 p-2 rounded-md bg-muted/30 text-xs">
                                      <span>{m.label}</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    )}
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
                      step="0.1"
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
                      step="any"
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
                      step="any"
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
                      step="any"
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
                    step="any"
                    value={baselineData.cash_balance}
                    onChange={(e) => setBaselineData({ ...baselineData, cash_balance: Number(e.target.value) })}
                    required
                    min={0}
                    data-testid="input-cash-balance"
                  />
                </div>
                
                <div className="space-y-2">
                  <div className="flex items-center gap-1">
                    <Label htmlFor="headcount">Number of Employees</Label>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <HelpCircle className="h-3.5 w-3.5 text-muted-foreground cursor-help" />
                      </TooltipTrigger>
                      <TooltipContent side="top" className="max-w-xs">
                        <p>Total number of full-time employees (including founders and contractors counted as FTE).</p>
                      </TooltipContent>
                    </Tooltip>
                  </div>
                  <Input
                    id="headcount"
                    type="number"
                    value={baselineData.headcount}
                    onChange={(e) => setBaselineData({ ...baselineData, headcount: Number(e.target.value) })}
                    min={0}
                    data-testid="input-headcount"
                  />
                </div>
                
                {/* Metric Formulas Documentation */}
                <div className="p-4 bg-muted/30 rounded-lg border mt-4">
                  <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                    <Info className="w-4 h-4" />
                    How Your Metrics Are Computed
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs text-muted-foreground">
                    <div className="p-2 bg-background rounded">
                      <span className="font-medium text-foreground">Gross Profit</span>
                      <p>= Revenue × (Gross Margin % / 100)</p>
                    </div>
                    <div className="p-2 bg-background rounded">
                      <span className="font-medium text-foreground">Net Burn</span>
                      <p>= Total Expenses - Revenue</p>
                    </div>
                    <div className="p-2 bg-background rounded">
                      <span className="font-medium text-foreground">Runway (months)</span>
                      <p>= Cash Balance / Net Burn</p>
                    </div>
                    <div className="p-2 bg-background rounded">
                      <span className="font-medium text-foreground">Total Expenses</span>
                      <p>= Opex + Payroll + Other Costs + COGS</p>
                    </div>
                  </div>
                  <p className="mt-3 text-xs text-muted-foreground">
                    If any input is missing or zero, the dependent metrics will show "Data unavailable".
                  </p>
                </div>
                
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    className="flex-1"
                    onClick={() => setStep(1)}
                    disabled={isSubmitting}
                  >
                    Back
                  </Button>
                  <Button
                    type="submit"
                    className="flex-1"
                    disabled={isSubmitting || manualBaselineMutation.isPending}
                    data-testid="button-save-baseline"
                  >
                    {isSubmitting || manualBaselineMutation.isPending ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Saving...
                      </>
                    ) : (
                      <>
                        Next: Expense Breakdown
                        <ArrowRight className="ml-2 h-4 w-4" />
                      </>
                    )}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        )}
        
        {step === 3 && (
          <Card>
            <CardHeader>
              <CardTitle>Expense Breakdown</CardTitle>
              <CardDescription>Optional: Provide a detailed breakdown to improve our burn accuracy by up to 30%</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <div className="flex items-center gap-1">
                      <Label htmlFor="payroll-detail">Payroll</Label>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <HelpCircle className="h-3.5 w-3.5 text-muted-foreground cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent side="top" className="max-w-xs">
                          <p>Total employee salaries, benefits, and payroll taxes</p>
                        </TooltipContent>
                      </Tooltip>
                    </div>
                    <Input
                      id="payroll-detail"
                      type="number"
                      step="any"
                      min={0}
                      value={expenseBreakdown.payroll}
                      onChange={(e) => setExpenseBreakdown({ ...expenseBreakdown, payroll: Number(e.target.value) })}
                      placeholder="0"
                    />
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center gap-1">
                      <Label htmlFor="marketing-detail">Marketing & Sales</Label>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <HelpCircle className="h-3.5 w-3.5 text-muted-foreground cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent side="top" className="max-w-xs">
                          <p>Customer acquisition, marketing campaigns, and sales costs</p>
                        </TooltipContent>
                      </Tooltip>
                    </div>
                    <Input
                      id="marketing-detail"
                      type="number"
                      step="any"
                      min={0}
                      value={expenseBreakdown.marketing}
                      onChange={(e) => setExpenseBreakdown({ ...expenseBreakdown, marketing: Number(e.target.value) })}
                      placeholder="0"
                    />
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center gap-1">
                      <Label htmlFor="operating-detail">Operating Expenses</Label>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <HelpCircle className="h-3.5 w-3.5 text-muted-foreground cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent side="top" className="max-w-xs">
                          <p>Rent, utilities, software, infrastructure, and other overhead</p>
                        </TooltipContent>
                      </Tooltip>
                    </div>
                    <Input
                      id="operating-detail"
                      type="number"
                      step="any"
                      min={0}
                      value={expenseBreakdown.operating}
                      onChange={(e) => setExpenseBreakdown({ ...expenseBreakdown, operating: Number(e.target.value) })}
                      placeholder="0"
                    />
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center gap-1">
                      <Label htmlFor="cogs-detail">Cost of Goods Sold</Label>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <HelpCircle className="h-3.5 w-3.5 text-muted-foreground cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent side="top" className="max-w-xs">
                          <p>Direct costs to produce goods or deliver services</p>
                        </TooltipContent>
                      </Tooltip>
                    </div>
                    <Input
                      id="cogs-detail"
                      type="number"
                      step="any"
                      min={0}
                      value={expenseBreakdown.cogs}
                      onChange={(e) => setExpenseBreakdown({ ...expenseBreakdown, cogs: Number(e.target.value) })}
                      placeholder="0"
                    />
                  </div>
                </div>

                <div className="p-4 bg-muted/30 rounded-lg border">
                  <div className="flex items-start gap-3">
                    <Info className="w-4 h-4 text-muted-foreground mt-1 shrink-0" />
                    <div className="text-sm space-y-1">
                      <p className="font-medium text-foreground">Can't fill in the details right now?</p>
                      <p className="text-muted-foreground">No problem! Skip this step and you can always add this breakdown later to improve accuracy.</p>
                    </div>
                  </div>
                </div>

                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    className="flex-1"
                    onClick={() => setStep(2)}
                  >
                    Back
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    className="flex-1"
                    onClick={() => {
                      markStepComplete(3);
                      setStep(4);
                    }}
                  >
                    Skip
                  </Button>
                  <Button
                    type="button"
                    className="flex-1"
                    onClick={() => {
                      markStepComplete(3);
                      setStep(4);
                    }}
                  >
                    Next: Data Sources
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {step === 4 && (
          <Card>
            <CardHeader>
              <CardTitle>Set Up Data Sources</CardTitle>
              <CardDescription>Choose how you'd like to keep your financial data up to date. You can always change this later.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="grid grid-cols-1 gap-3">
                  {/* Manual Entry Card */}
                  <div
                    className={`p-4 border rounded-lg cursor-pointer transition-all ${
                      dataSourceChoice === 'manual'
                        ? 'border-primary bg-primary/5'
                        : 'border-muted hover:border-primary/50 hover:bg-muted/30'
                    }`}
                    onClick={() => setDataSourceChoice('manual')}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`w-5 h-5 rounded border-2 flex items-center justify-center shrink-0 ${
                        dataSourceChoice === 'manual' ? 'border-primary bg-primary' : 'border-muted-foreground'
                      }`}>
                        {dataSourceChoice === 'manual' && <Check className="w-3 h-3 text-primary-foreground" />}
                      </div>
                      <div className="flex-1">
                        <h3 className="font-medium">Manual Entry</h3>
                        <p className="text-sm text-muted-foreground mt-1">
                          Update your financials manually each month. Perfect for getting started quickly.
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Upload Card */}
                  <div
                    className={`p-4 border rounded-lg cursor-pointer transition-all ${
                      dataSourceChoice === 'upload'
                        ? 'border-primary bg-primary/5'
                        : 'border-muted hover:border-primary/50 hover:bg-muted/30'
                    }`}
                    onClick={() => setDataSourceChoice('upload')}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`w-5 h-5 rounded border-2 flex items-center justify-center shrink-0 ${
                        dataSourceChoice === 'upload' ? 'border-primary bg-primary' : 'border-muted-foreground'
                      }`}>
                        {dataSourceChoice === 'upload' && <Check className="w-3 h-3 text-primary-foreground" />}
                      </div>
                      <div className="flex-1">
                        <h3 className="font-medium">Upload Files</h3>
                        <p className="text-sm text-muted-foreground mt-1">
                          Upload monthly Excel or CSV files. We'll extract and track changes automatically.
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Connect Apps Card */}
                  <div
                    className={`p-4 border rounded-lg cursor-pointer transition-all ${
                      dataSourceChoice === 'connect'
                        ? 'border-primary bg-primary/5'
                        : 'border-muted hover:border-primary/50 hover:bg-muted/30'
                    }`}
                    onClick={() => setDataSourceChoice('connect')}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`w-5 h-5 rounded border-2 flex items-center justify-center shrink-0 ${
                        dataSourceChoice === 'connect' ? 'border-primary bg-primary' : 'border-muted-foreground'
                      }`}>
                        {dataSourceChoice === 'connect' && <Check className="w-3 h-3 text-primary-foreground" />}
                      </div>
                      <div className="flex-1">
                        <h3 className="font-medium">Connect Apps</h3>
                        <p className="text-sm text-muted-foreground mt-1">
                          Sync with Stripe, QuickBooks, Gusto, and more. Real-time data updates. Recommended for accuracy.
                        </p>
                        {dataSourceChoice === 'connect' && (
                          <div className="mt-3 flex flex-wrap gap-2">
                            <Badge variant="secondary" className="text-xs">Stripe</Badge>
                            <Badge variant="secondary" className="text-xs">QuickBooks</Badge>
                            <Badge variant="secondary" className="text-xs">Gusto</Badge>
                            <Badge variant="secondary" className="text-xs">+ More</Badge>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="p-4 bg-blue-500/5 border border-blue-500/30 rounded-lg">
                  <div className="flex items-start gap-2">
                    <Info className="w-4 h-4 text-blue-500 mt-0.5 shrink-0" />
                    <p className="text-sm text-blue-600 dark:text-blue-400">
                      You can always add more data sources later or switch to a different method at any time.
                    </p>
                  </div>
                </div>

                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    className="flex-1"
                    onClick={() => setStep(3)}
                  >
                    Back
                  </Button>
                  <Button
                    type="button"
                    className="flex-1"
                    disabled={!dataSourceChoice}
                    onClick={handleRunTruthScan}
                  >
                    {isSubmitting ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Setting up...
                      </>
                    ) : (
                      <>
                        Finish Setup
                        <ArrowRight className="ml-2 h-4 w-4" />
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
