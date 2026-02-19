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
import { useCreateCompany, useManualBaseline, useRunTruthScan } from '@/api/hooks';
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
  { id: 1, title: 'Company Info', description: 'Tell us about your startup' },
  { id: 2, title: 'Financial Snapshot', description: 'Quick financial baseline' },
  { id: 3, title: 'First Truth Scan', description: 'Analyzing your data' },
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
      let company;
      
      company = await createCompanyMutation.mutateAsync(companyData);
      
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
    setStep(3);
    setScanError(null);

    try {
      const truthScan = await runTruthScanMutation.mutateAsync(currentCompany.id);
      setTruthScan(truthScan);
      setStoreStep('truth');
      toast({ title: 'Setup complete!', description: 'Your first Truth Scan is ready.' });
      setTimeout(() => setLocation('/'), 1500);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        toast({ title: 'Session expired', description: 'Please log in again.', variant: 'destructive' });
        setLocation('/auth');
        return;
      }
      const message = err instanceof ApiError ? err.message : 'Failed to run Truth Scan. Please try again.';
      setScanError(message);
      toast({ title: 'Error', description: message, variant: 'destructive' });
      setStep(2);
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
      
      toast({ title: 'Baseline saved!', description: 'Running your first analysis...' });
      handleRunTruthScan();
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
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className={`w-full space-y-6 ${step === 3 ? 'max-w-3xl' : 'max-w-xl'}`}>
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
                    accept=".pdf,.xls,.xlsx,.csv"
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
                        <p className="font-medium">Upload your pitch deck, financial report, or spreadsheet</p>
                        <p className="text-sm text-muted-foreground">
                          Drop a file here or click to browse. AI will auto-fill company and financial details.
                        </p>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <FileText className="w-3 h-3" />
                        <span>PDF, Excel (.xls, .xlsx), or CSV - up to 20MB</span>
                      </div>
                    </div>
                  )}
                </div>
                
                {extractedData && extractedData.confidence && (
                  <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Check className="w-3 h-3 text-green-500" />
                      Company info: {Math.round((extractedData.confidence.company_info || 0) * 100)}% confident
                    </span>
                    <span className="flex items-center gap-1">
                      <Check className="w-3 h-3 text-green-500" />
                      Financials: {Math.round((extractedData.confidence.financials || 0) * 100)}% confident
                    </span>
                    {extractedData.extraction_method && (
                      <Badge variant="outline" className="text-xs">
                        {extractedData.extraction_method.includes('excel') ? 'Excel' : 
                         extractedData.extraction_method.includes('csv') ? 'CSV' : 'PDF'}
                      </Badge>
                    )}
                  </div>
                )}
                
                {/* Data Cross-Check Section */}
                {extractedData && (
                  <div className="mt-4 p-4 bg-muted/30 rounded-lg border">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="text-sm font-medium flex items-center gap-2">
                        <Eye className="w-4 h-4" />
                        Extracted Data Cross-Check
                      </h4>
                      <div className="flex gap-2">
                        {extractedData.raw_data_preview && (
                          <Dialog open={showDataPreview} onOpenChange={setShowDataPreview}>
                            <DialogTrigger asChild>
                              <Button variant="outline" size="sm" data-testid="button-view-raw-data">
                                <FileText className="w-3 h-3 mr-1" />
                                View Source Data
                              </Button>
                            </DialogTrigger>
                            <DialogContent className="max-w-4xl max-h-[80vh] overflow-auto">
                              <DialogHeader>
                                <DialogTitle>Source Data Preview</DialogTitle>
                                <DialogDescription>
                                  Raw data from your uploaded file ({extractedData.raw_data_preview.row_count} rows)
                                </DialogDescription>
                              </DialogHeader>
                              <div className="overflow-auto">
                                <Table>
                                  <TableHeader>
                                    <TableRow>
                                      {extractedData.raw_data_preview.columns.map((col) => (
                                        <TableHead key={col} className="whitespace-nowrap">{col}</TableHead>
                                      ))}
                                    </TableRow>
                                  </TableHeader>
                                  <TableBody>
                                    {extractedData.raw_data_preview.sample_rows.map((row, idx) => (
                                      <TableRow key={idx}>
                                        {extractedData.raw_data_preview!.columns.map((col) => (
                                          <TableCell key={col} className="whitespace-nowrap">
                                            {String(row[col] ?? '')}
                                          </TableCell>
                                        ))}
                                      </TableRow>
                                    ))}
                                  </TableBody>
                                </Table>
                              </div>
                            </DialogContent>
                          </Dialog>
                        )}
                        <Dialog open={showFeedbackDialog} onOpenChange={setShowFeedbackDialog}>
                          <DialogTrigger asChild>
                            <Button variant="ghost" size="sm" data-testid="button-report-discrepancy">
                              <MessageSquare className="w-3 h-3 mr-1" />
                              Report Issue
                            </Button>
                          </DialogTrigger>
                          <DialogContent>
                            <DialogHeader>
                              <DialogTitle>Report a Discrepancy</DialogTitle>
                              <DialogDescription>
                                Let us know if the extracted data doesn't match your document
                              </DialogDescription>
                            </DialogHeader>
                            <Textarea
                              placeholder="Describe what values look incorrect or are missing..."
                              value={feedbackText}
                              onChange={(e) => setFeedbackText(e.target.value)}
                              rows={4}
                              data-testid="input-feedback"
                            />
                            <div className="flex justify-end gap-2">
                              <Button variant="outline" onClick={() => setShowFeedbackDialog(false)}>
                                Cancel
                              </Button>
                              <Button 
                                onClick={() => {
                                  toast({ title: 'Feedback sent', description: 'Thank you for your feedback!' });
                                  setShowFeedbackDialog(false);
                                  setFeedbackText('');
                                }}
                                disabled={!feedbackText.trim()}
                              >
                                Send Feedback
                              </Button>
                            </div>
                          </DialogContent>
                        </Dialog>
                      </div>
                    </div>
                    
                    {/* Extracted Values Table */}
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      {[
                        { label: 'Monthly Revenue', value: extractedData.financials.monthly_revenue, format: 'currency' },
                        { label: 'Gross Margin', value: extractedData.financials.gross_margin_pct, format: 'percent' },
                        { label: 'Opex', value: extractedData.financials.opex, format: 'currency' },
                        { label: 'Payroll', value: extractedData.financials.payroll, format: 'currency' },
                        { label: 'Cash Balance', value: extractedData.financials.cash_balance, format: 'currency' },
                        { label: 'Headcount', value: extractedData.financials.headcount, format: 'number' },
                      ].map(({ label, value, format }) => (
                        <div key={label} className="flex justify-between p-2 bg-background rounded border">
                          <span className="text-muted-foreground">{label}</span>
                          {value !== undefined && value !== null ? (
                            <span className="font-medium text-green-600 dark:text-green-400">
                              {format === 'currency' 
                                ? `$${Number(value).toLocaleString()}` 
                                : format === 'percent' 
                                  ? `${value}%` 
                                  : value}
                            </span>
                          ) : (
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <span className="text-amber-500 flex items-center gap-1 cursor-help">
                                  <Info className="w-3 h-3" />
                                  Not found
                                </span>
                              </TooltipTrigger>
                              <TooltipContent>
                                <p>This metric wasn't found in your document. You can enter it manually below.</p>
                              </TooltipContent>
                            </Tooltip>
                          )}
                        </div>
                      ))}
                    </div>
                    
                    <p className="mt-3 text-xs text-muted-foreground">
                      Review the extracted values above. You can override any value in the form fields below.
                    </p>
                  </div>
                )}
                
                {/* Upload History */}
                {uploadHistory.length > 0 && (
                  <div className="mt-4 p-3 bg-muted/30 rounded-md">
                    <div className="flex items-center gap-2 mb-2">
                      <History className="w-4 h-4 text-muted-foreground" />
                      <span className="text-sm font-medium">Upload History</span>
                    </div>
                    <div className="space-y-1">
                      {uploadHistory.map((file, idx) => (
                        <div 
                          key={`${file.name}-${idx}`} 
                          className="flex items-center justify-between text-xs text-muted-foreground"
                        >
                          <div className="flex items-center gap-2">
                            <FileText className="w-3 h-3" />
                            <span className="truncate max-w-[200px]">{file.name}</span>
                            {idx === 0 && <Badge variant="secondary" className="text-[10px] px-1.5 py-0">Current</Badge>}
                          </div>
                          <span className="text-[10px]">
                            {file.uploadedAt.toLocaleTimeString()}
                          </span>
                        </div>
                      ))}
                    </div>
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
                  <div className="flex gap-2">
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
                      className={extractedData?.company_info?.website ? 'border-green-500/50' : ''}
                    />
                    <Button
                      type="button"
                      variant="outline"
                      onClick={fetchCompanyDetailsAI}
                      disabled={isFetchingAI || !companyData.website?.trim()}
                      data-testid="button-fetch-company-ai"
                      className="shrink-0 gap-2"
                    >
                      {isFetchingAI ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Fetching...
                        </>
                      ) : (
                        <>
                          <Sparkles className="h-4 w-4" />
                          Fetch using AI
                        </>
                      )}
                    </Button>
                  </div>
                  {aiLookupSummary && (
                    <div className="mt-2 p-3 bg-primary/5 border border-primary/20 rounded-md text-sm">
                      <div className="flex items-start gap-2">
                        <Globe className="h-4 w-4 text-primary mt-0.5 shrink-0" />
                        <p className="text-muted-foreground">{aiLookupSummary}</p>
                      </div>
                    </div>
                  )}
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
                    <p className="text-xs text-muted-foreground">We use this to benchmark you against similar companies in your sector.</p>
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
                    <p className="text-xs text-muted-foreground">Sets smart defaults for your financial snapshot in the next step.</p>
                  </div>
                </div>

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
                  <p className="text-xs text-muted-foreground">
                    {companyData.currency !== 'USD' 
                      ? `All financial values will be displayed in ${companyData.currency}.`
                      : 'Ensures all figures are shown in your local currency for accuracy.'}
                  </p>
                </div>

                <div className="space-y-2">
                  <Label>Values entered in</Label>
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
                  {companyData.amount_scale !== 'UNITS' && (() => {
                    const symbols: Record<string, string> = {
                      USD: '$', EUR: '€', GBP: '£', INR: '₹', JPY: '¥',
                      CNY: '¥', KRW: '₩', BRL: 'R$', CHF: 'CHF', SEK: 'kr',
                      AED: 'AED', HKD: 'HK$', MXN: 'MX$', ILS: '₪', NGN: '₦',
                      KES: 'KSh', ZAR: 'R', SGD: 'S$', AUD: 'A$', CAD: 'C$',
                    };
                    const sym = symbols[companyData.currency] || companyData.currency;
                    const multipliers: Record<string, number> = {
                      UNITS: 1, THOUSANDS: 1000, MILLIONS: 1000000, CRORES: 10000000,
                    };
                    const mult = multipliers[companyData.amount_scale] || 1;
                    const exampleInput = 25;
                    const exampleOutput = exampleInput * mult;
                    const formatted = exampleOutput.toLocaleString();
                    return (
                      <div className="p-2.5 bg-muted/50 rounded-md space-y-1" data-testid="scale-preview">
                        <p className="text-xs font-medium text-muted-foreground">Live Preview</p>
                        <p className="text-sm">
                          You enter <span className="font-mono font-semibold">{sym}{exampleInput}</span>
                          {' → '}
                          FounderConsole reads it as <span className="font-mono font-semibold">{sym}{formatted}</span>
                        </p>
                      </div>
                    );
                  })()}
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
                  : 'Upload an Excel/CSV with financials or enter values manually below.'}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {/* Financial File Upload Zone */}
              <div className="mb-6">
                <div
                  className={`relative border-2 border-dashed rounded-lg p-4 transition-colors cursor-pointer ${
                    isDragging 
                      ? 'border-primary bg-primary/5' 
                      : 'border-muted-foreground/30 hover:border-primary/50 hover:bg-muted/20'
                  }`}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => !isExtracting && fileInputRef.current?.click()}
                  data-testid="dropzone-financials-upload"
                >
                  {isExtracting ? (
                    <div className="flex items-center justify-center gap-3">
                      <Loader2 className="w-5 h-5 text-primary animate-spin" />
                      <span className="text-sm">Extracting financial data...</span>
                    </div>
                  ) : (
                    <div className="flex items-center justify-center gap-3 text-center">
                      <Upload className="w-5 h-5 text-muted-foreground" />
                      <div>
                        <p className="text-sm font-medium">Upload Excel/CSV with financials</p>
                        <p className="text-xs text-muted-foreground">
                          Drag & drop or click to browse (.xlsx, .xls, .csv)
                        </p>
                      </div>
                    </div>
                  )}
                </div>
                
                {extractedData?.financials && (
                  <div className="mt-3 p-3 bg-green-500/10 border border-green-500/30 rounded-md">
                    <div className="flex items-center gap-2 mb-2">
                      <Check className="w-4 h-4 text-green-500" />
                      <span className="text-sm font-medium text-green-500">Financial data extracted</span>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Values below have been pre-filled from your uploaded file. You can adjust them if needed.
                    </p>
                  </div>
                )}
                
                <div className="relative my-4">
                  <div className="absolute inset-0 flex items-center">
                    <span className="w-full border-t" />
                  </div>
                  <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-card px-2 text-muted-foreground">Or enter manually</span>
                  </div>
                </div>
              </div>
              
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
                
                <Button
                  type="submit"
                  className="w-full"
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
                      Continue to Data Sources
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </>
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
