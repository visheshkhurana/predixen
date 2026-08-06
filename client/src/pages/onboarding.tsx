import { useState, useEffect, useRef } from 'react';
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
import { useFounderStore } from '@/store/founderStore';
import { useCreateCompany, useManualBaseline, useRunTruthScan, useSeedSample, useTerminaExcelUpload, useTerminaPdfUpload } from '@/api/hooks';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Badge } from '@/components/ui/badge';
import { HelpCircle, Sparkles, Check, AlertCircle, Loader2, ArrowRight, ArrowLeft, TrendingDown, DollarSign, Activity, FileUp, FileText, X } from 'lucide-react';
import type { AmountScale } from '@/lib/utils';
import { trackEvent } from '@/lib/posthog';

const STEPS = [
  { id: 1, title: 'Welcome', description: 'Tell us about your startup' },
  { id: 2, title: 'Connect Data', description: 'Choose your data source' },
  { id: 3, title: 'Health Check', description: 'Validate your financials' },
  { id: 4, title: 'First Simulation', description: 'Run your first scenario' },
  { id: 5, title: 'AI Copilot', description: 'Get strategic insights' },
];

const STAGE_DEFAULTS: Record<string, { monthly_revenue: number; gross_margin_pct: number; opex: number; payroll: number; other_costs: number; cash_balance: number; headcount: number }> = {
  pre_seed: { monthly_revenue: 0, gross_margin_pct: 0, opex: 5000, payroll: 0, other_costs: 2000, cash_balance: 50000, headcount: 3 },
  seed: { monthly_revenue: 25000, gross_margin_pct: 75, opex: 15000, payroll: 35000, other_costs: 5000, cash_balance: 1000000, headcount: 8 },
  pre_series_a: { monthly_revenue: 60000, gross_margin_pct: 72, opex: 30000, payroll: 80000, other_costs: 10000, cash_balance: 2000000, headcount: 18 },
  series_a: { monthly_revenue: 150000, gross_margin_pct: 70, opex: 40000, payroll: 80000, other_costs: 15000, cash_balance: 2000000, headcount: 25 },
  series_b: { monthly_revenue: 500000, gross_margin_pct: 72, opex: 100000, payroll: 200000, other_costs: 30000, cash_balance: 5000000, headcount: 60 },
  growth: { monthly_revenue: 1000000, gross_margin_pct: 75, opex: 200000, payroll: 400000, other_costs: 50000, cash_balance: 10000000, headcount: 120 },
};

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

function formatCurrency(value: number): string {
  if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
  if (value >= 1000) return `$${(value / 1000).toFixed(0)}K`;
  return `$${value.toLocaleString()}`;
}

export default function OnboardingPage() {
  const [, setLocation] = useLocation();
  const { toast } = useToast();
  const { setCurrentCompany, setTruthScan, setCurrentStep: setStoreStep } = useFounderStore();

  useEffect(() => {
    const completed = localStorage.getItem('founderConsoleOnboardingComplete');
    if (completed === 'true') {
      if (useFounderStore.getState().currentCompany) {
        setLocation('/');
      } else {
        // Stale flag from a previous account/demo session. Without a company,
        // redirecting away just bounces back here forever (React #185) —
        // clear the flag and let the user onboard.
        localStorage.removeItem('founderConsoleOnboardingComplete');
      }
    }
  }, [setLocation]);

  const [step, setStep] = useState(1);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);
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
  const [dataSourceChoice, setDataSourceChoice] = useState<'manual' | 'upload' | 'connect' | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSampleMode, setIsSampleMode] = useState(false);
  const [scanError, setScanError] = useState<string | null>(null);
  const [showManualInputs, setShowManualInputs] = useState(false);
  const [baselineSaved, setBaselineSaved] = useState(false);
  // Has the founder actually supplied any baseline numbers — typed them,
  // extracted them from an upload, or explicitly accepted the stage defaults?
  // Until they have, the Health Check must say "no data" rather than present
  // arithmetic over numbers nobody entered.
  const [baselineTouched, setBaselineTouched] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSummary, setUploadSummary] = useState<string | null>(null);
  const [uploadDragActive, setUploadDragActive] = useState(false);
  const uploadInputRef = useRef<HTMLInputElement>(null);

  const stageDefaults = companyData.stage ? STAGE_DEFAULTS[companyData.stage] : undefined;

  const updateBaseline = (patch: Partial<typeof baselineData>) => {
    setBaselineTouched(true);
    setBaselineSaved(false);
    setBaselineData((prev) => ({ ...prev, ...patch }));
  };

  const { data: existingCompaniesRaw } = useQuery<any>({
    queryKey: ['/api/companies'],
  });
  const existingCompanies = Array.isArray(existingCompaniesRaw) ? existingCompaniesRaw : (existingCompaniesRaw?.items || []) as Array<{ id: number; name: string; industry?: string; stage?: string; website?: string }>;

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

  const createCompanyMutation = useCreateCompany();
  const manualBaselineMutation = useManualBaseline();
  const runTruthScanMutation = useRunTruthScan();
  const seedSampleMutation = useSeedSample();
  const excelUploadMutation = useTerminaExcelUpload();
  const pdfUploadMutation = useTerminaPdfUpload();
  const isExtracting = excelUploadMutation.isPending || pdfUploadMutation.isPending;

  const isSeedingInProgress = createCompanyMutation.isPending || seedSampleMutation.isPending;
  const currentCompany = useFounderStore((s) => s.currentCompany);

  const loadSampleCompany = async () => {
    if (isSubmitting || isSeedingInProgress) return;

    const { user } = useFounderStore.getState();
    if (!user) {
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
    setBaselineTouched(true);

    try {
      const company = await createCompanyMutation.mutateAsync(SAMPLE_COMPANY);
      setCurrentCompany(company);

      await seedSampleMutation.mutateAsync(company.id);

      localStorage.setItem('founderConsoleOnboardingComplete', 'true');
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
      setCompletedSteps(prev => [...prev, stepNum]);
    }
  };

  const handleCompanySubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (isSubmitting || createCompanyMutation.isPending) return;

    const { user } = useFounderStore.getState();
    if (!user) {
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
      const company = await createCompanyMutation.mutateAsync(companyData);
      setCurrentCompany(company);
      markStepComplete(1);

      // NOTE: we deliberately do NOT prefill baselineData from STAGE_DEFAULTS
      // here. Doing so meant an untouched form produced a confident-looking
      // Health Check ($30K burn / 33.3 mo runway / health 100) built entirely
      // out of stage averages the founder never entered. Stage defaults are now
      // opt-in via the "Use typical ... numbers" button and are shown as
      // placeholders only.
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

  const handleSaveBaseline = async () => {
    if (isSubmitting || !currentCompany) return;

    setIsSubmitting(true);
    try {
      await manualBaselineMutation.mutateAsync({
        companyId: currentCompany.id,
        data: baselineData,
      });
      setBaselineSaved(true);
      toast({ title: 'Financial data saved!' });
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        toast({ title: 'Session expired', description: 'Please log in again.', variant: 'destructive' });
        setLocation('/auth');
        return;
      }
      const message = err instanceof ApiError ? err.message : 'Failed to save data. Please try again.';
      toast({ title: 'Error', description: message, variant: 'destructive' });
    } finally {
      setIsSubmitting(false);
    }
  };

  const pickUploadFile = (file: File) => {
    const ext = file.name.toLowerCase().split('.').pop() || '';
    if (!['xlsx', 'xls', 'pdf'].includes(ext)) {
      setUploadError('Please choose an .xlsx, .xls or .pdf file. CSV imports live on the Data page after setup.');
      return;
    }
    setUploadError(null);
    setUploadSummary(null);
    setUploadFile(file);
  };

  /**
   * Extract a baseline from an uploaded statement.
   *
   * The "Upload Files" option used to be a radio button that rendered nothing —
   * picking it and hitting Next carried the founder into a Health Check built
   * from stage averages. This wires it to the same extraction endpoints the
   * Data page uses, then drops the extracted numbers into the review grid so
   * they can be corrected before anything is saved.
   */
  const handleExtractUpload = async () => {
    if (!uploadFile || !currentCompany) return;
    setUploadError(null);
    const ext = uploadFile.name.toLowerCase().split('.').pop() || '';

    try {
      const result: any = ext === 'pdf'
        ? await pdfUploadMutation.mutateAsync({ companyId: currentCompany.id, file: uploadFile, saveAsBaseline: false })
        : await excelUploadMutation.mutateAsync({ companyId: currentCompany.id, file: uploadFile, saveAsBaseline: false });

      const m = result?.metrics || {};
      const num = (...candidates: any[]): number | undefined => {
        for (const c of candidates) {
          if (typeof c === 'number' && Number.isFinite(c)) return c;
        }
        return undefined;
      };

      const extracted = {
        monthly_revenue: num(m.monthly_revenue, m.revenue),
        gross_margin_pct: num(m.gross_margin, m.gross_margin_pct),
        opex: num(m.opex),
        payroll: num(m.payroll),
        other_costs: num(m.other_costs, m.cogs),
        cash_balance: num(m.cash_balance),
        headcount: num(m.headcount, m.employees),
      };

      const found = Object.entries(extracted).filter(([, v]) => v !== undefined);
      if (found.length === 0) {
        setUploadError("We couldn't find financial figures in that file. Enter the numbers manually below, or try a different export.");
        setShowManualInputs(true);
        return;
      }

      setBaselineData((prev) => ({
        ...prev,
        ...Object.fromEntries(found) as Partial<typeof prev>,
      }));
      setBaselineTouched(true);
      setBaselineSaved(false);
      setShowManualInputs(true);
      setUploadSummary(
        result?.summary ||
        `Pulled ${found.length} figure${found.length === 1 ? '' : 's'} from ${uploadFile.name}. Check them below before continuing.`
      );
      toast({ title: 'File analyzed', description: 'Review the extracted numbers before continuing.' });
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        toast({ title: 'Session expired', description: 'Please log in again.', variant: 'destructive' });
        setLocation('/auth');
        return;
      }
      const message = err instanceof ApiError ? err.message : 'We could not read that file.';
      setUploadError(`${message} You can enter the numbers manually instead.`);
      setShowManualInputs(true);
    }
  };

  const handleConnectDataNext = async () => {
    // Any branch that produced numbers must persist them — previously only the
    // manual branch saved, so an upload-extracted baseline was silently dropped
    // and the Health Check fell back to whatever was in state.
    if (baselineTouched && !baselineSaved) {
      await handleSaveBaseline();
    }
    markStepComplete(2);
    setStep(3);
  };

  const handleRunHealthCheck = async () => {
    const { user: currentUser } = useFounderStore.getState();
    if (!currentUser) {
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
      markStepComplete(3);
      setStep(4);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        toast({ title: 'Session expired', description: 'Please log in again.', variant: 'destructive' });
        setLocation('/auth');
        return;
      }
      const message = err instanceof ApiError ? err.message : 'Health check encountered an issue.';
      setScanError(message);
      markStepComplete(3);
      setStep(4);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleGoToSimulate = () => {
    markStepComplete(4);
    setStep(5);
  };

  const handleFinishSetup = () => {
    markStepComplete(5);
    localStorage.setItem('founderConsoleOnboardingComplete', 'true');
    // Activation conversion: the new user reached a live dashboard.
    if (typeof window !== 'undefined' && (window as any).gtag) {
      (window as any).gtag('event', 'onboarding_complete', {});
    }
    trackEvent('onboarding_complete', { company_id: currentCompany?.id });
    toast({ title: 'Setup complete!', description: 'Your dashboard is ready.' });
    setLocation('/');
  };

  const totalExpenses = baselineData.opex + baselineData.payroll + baselineData.other_costs;
  const netBurn = totalExpenses - baselineData.monthly_revenue;
  // Only treat the baseline as real if the founder actually put numbers in.
  // Everything on the Health Check hangs off this: without it, an untouched
  // form still rendered a burn rate, a runway and a health score.
  const hasBaselineNumbers =
    baselineTouched &&
    (totalExpenses > 0 || baselineData.cash_balance > 0 || baselineData.monthly_revenue > 0);
  const runwayMonths = hasBaselineNumbers && netBurn > 0 && baselineData.cash_balance > 0 ? baselineData.cash_balance / netBurn : null;
  const healthScore = (() => {
    let score = 50;
    if (runwayMonths !== null) {
      if (runwayMonths >= 18) score += 30;
      else if (runwayMonths >= 12) score += 20;
      else if (runwayMonths >= 6) score += 10;
      else score -= 10;
    }
    if (baselineData.gross_margin_pct >= 70) score += 15;
    else if (baselineData.gross_margin_pct >= 50) score += 10;
    if (baselineData.monthly_revenue > 0) score += 5;
    return Math.min(100, Math.max(0, score));
  })();

  const baselineFieldsPanel = (
    <div className="p-4 border rounded-md bg-muted/30 space-y-4" data-testid="section-manual-inputs">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-1">
            <Label htmlFor="revenue">Monthly Revenue ($)</Label>
            <Tooltip>
              <TooltipTrigger asChild>
                <HelpCircle className="h-3.5 w-3.5 text-muted-foreground cursor-help" />
              </TooltipTrigger>
              <TooltipContent side="top" className="max-w-xs">
                <p>Your total monthly recurring revenue (MRR).</p>
              </TooltipContent>
            </Tooltip>
          </div>
          <Input
            id="revenue"
            type="number"
            step="any"
            value={baselineTouched || baselineData.monthly_revenue !== 0 ? baselineData.monthly_revenue : ''}
            placeholder={stageDefaults ? String(stageDefaults.monthly_revenue) : '0'}
            onChange={(e) => updateBaseline({ monthly_revenue: Number(e.target.value) })}
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
                <p>SaaS companies typically have 70-85%.</p>
              </TooltipContent>
            </Tooltip>
          </div>
          <Input
            id="gross-margin"
            type="number"
            step="0.1"
            value={baselineTouched || baselineData.gross_margin_pct !== 0 ? baselineData.gross_margin_pct : ''}
            placeholder={stageDefaults ? String(stageDefaults.gross_margin_pct) : '0'}
            onChange={(e) => updateBaseline({ gross_margin_pct: Number(e.target.value) })}
            min={0}
            max={100}
            data-testid="input-gross-margin"
          />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="space-y-2">
          <Label htmlFor="opex">Opex ($)</Label>
          <Input
            id="opex"
            type="number"
            step="any"
            value={baselineTouched || baselineData.opex !== 0 ? baselineData.opex : ''}
            placeholder={stageDefaults ? String(stageDefaults.opex) : '0'}
            onChange={(e) => updateBaseline({ opex: Number(e.target.value) })}
            min={0}
            data-testid="input-opex"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="payroll">Payroll ($)</Label>
          <Input
            id="payroll"
            type="number"
            step="any"
            value={baselineTouched || baselineData.payroll !== 0 ? baselineData.payroll : ''}
            placeholder={stageDefaults ? String(stageDefaults.payroll) : '0'}
            onChange={(e) => updateBaseline({ payroll: Number(e.target.value) })}
            min={0}
            data-testid="input-payroll"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="other-costs">Other ($)</Label>
          <Input
            id="other-costs"
            type="number"
            step="any"
            value={baselineTouched || baselineData.other_costs !== 0 ? baselineData.other_costs : ''}
            placeholder={stageDefaults ? String(stageDefaults.other_costs) : '0'}
            onChange={(e) => updateBaseline({ other_costs: Number(e.target.value) })}
            min={0}
            data-testid="input-other-costs"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-1">
            <Label htmlFor="cash">Cash Balance ($)</Label>
            <Tooltip>
              <TooltipTrigger asChild>
                <HelpCircle className="h-3.5 w-3.5 text-muted-foreground cursor-help" />
              </TooltipTrigger>
              <TooltipContent side="top" className="max-w-xs">
                <p>Total cash currently in your bank accounts.</p>
              </TooltipContent>
            </Tooltip>
          </div>
          <Input
            id="cash"
            type="number"
            step="any"
            value={baselineTouched || baselineData.cash_balance !== 0 ? baselineData.cash_balance : ''}
            placeholder={stageDefaults ? String(stageDefaults.cash_balance) : '0'}
            onChange={(e) => updateBaseline({ cash_balance: Number(e.target.value) })}
            min={0}
            data-testid="input-cash-balance"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="headcount">Headcount</Label>
          <Input
            id="headcount"
            type="number"
            value={baselineTouched || baselineData.headcount !== 0 ? baselineData.headcount : ''}
            placeholder={stageDefaults ? String(stageDefaults.headcount) : '0'}
            onChange={(e) => updateBaseline({ headcount: Number(e.target.value) })}
            min={0}
            data-testid="input-headcount"
          />
        </div>
      </div>

      {stageDefaults && !baselineTouched && (
        <div className="flex items-start gap-2 text-xs text-muted-foreground">
          <HelpCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          <span>
            Don't have exact figures yet? The greyed-out numbers are typical for a{' '}
            {companyData.stage?.replace(/_/g, ' ')} company.{' '}
            <Button
              type="button"
              variant="ghost"
              className="px-1 h-auto underline align-baseline text-xs"
              onClick={() => updateBaseline(stageDefaults)}
              data-testid="button-use-stage-defaults"
            >
              Use them as a starting point
            </Button>
            {' '}— they're estimates, not your data.
          </span>
        </div>
      )}


      {baselineSaved && (
        <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
          <Check className="w-4 h-4" />
          <span>Data saved</span>
        </div>
      )}
    </div>
  );

  const progress = (step / STEPS.length) * 100;

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-2xl space-y-6">
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <h1 className="text-2xl font-bold" data-testid="text-onboarding-title">Getting Started</h1>
            <Button
              variant="ghost"
              size="sm"
              onClick={loadSampleCompany}
              disabled={isSubmitting || isSeedingInProgress}
              data-testid="button-load-sample"
            >
              {isSeedingInProgress ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                  Loading...
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5 mr-1.5" />
                  Try Sample Company
                </>
              )}
            </Button>
          </div>

          <div className="flex items-center gap-1">
            {STEPS.map((s, idx) => (
              <div key={s.id} className="flex items-center flex-1">
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  <div className={`flex items-center justify-center w-8 h-8 rounded-full font-medium text-sm shrink-0 ${
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
                  <div className="hidden sm:block min-w-0">
                    <p className="text-sm font-medium truncate">{s.title}</p>
                    <p className="text-xs text-muted-foreground truncate">{s.description}</p>
                  </div>
                </div>
                {idx < STEPS.length - 1 && (
                  <div className={`h-0.5 w-6 mx-2 shrink-0 ${
                    completedSteps.includes(s.id) ? 'bg-green-500' : 'bg-muted'
                  }`} />
                )}
              </div>
            ))}
          </div>

          <Progress value={progress} className="h-2" data-testid="onboarding-progress" />
        </div>

        {step === 1 && (
          <Card>
            <CardHeader>
              <CardTitle data-testid="text-step1-title">Welcome to FounderConsole</CardTitle>
              <CardDescription>Tell us about your startup so we can find relevant benchmarks and insights.</CardDescription>
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
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Industry <span className="text-destructive">*</span></Label>
                    <Select
                      value={companyData.industry}
                      onValueChange={(v) => setCompanyData({ ...companyData, industry: v })}
                    >
                      <SelectTrigger data-testid="select-industry">
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
                  </div>

                  <div className="space-y-2">
                    <Label>Stage <span className="text-destructive">*</span></Label>
                    <Select
                      value={companyData.stage}
                      onValueChange={(v) => setCompanyData({ ...companyData, stage: v })}
                    >
                      <SelectTrigger data-testid="select-stage">
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
                  </div>
                </div>

                <Button
                  type="submit"
                  className="w-full"
                  disabled={isSubmitting || createCompanyMutation.isPending || !companyData.name.trim() || !companyData.industry || !companyData.stage}
                  data-testid="button-next-step"
                >
                  {isSubmitting || createCompanyMutation.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    <>
                      Next: Connect Data
                      <ArrowRight className="ml-2 h-4 w-4" />
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
              <CardTitle data-testid="text-step2-title">Connect Your Data</CardTitle>
              <CardDescription>Choose how you'd like to provide your financial data. You can always change this later.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="grid grid-cols-1 gap-3">
                  <div
                    className={`p-4 border rounded-md cursor-pointer transition-colors ${
                      dataSourceChoice === 'manual'
                        ? 'border-primary bg-primary/5'
                        : 'hover-elevate'
                    }`}
                    onClick={() => {
                      setDataSourceChoice('manual');
                      setShowManualInputs(true);
                    }}
                    data-testid="option-manual-entry"
                  >
                    <div className="flex items-start gap-3">
                      <div className={`w-5 h-5 rounded border-2 flex items-center justify-center shrink-0 mt-0.5 ${
                        dataSourceChoice === 'manual' ? 'border-primary bg-primary' : 'border-muted-foreground'
                      }`}>
                        {dataSourceChoice === 'manual' && <Check className="w-3 h-3 text-primary-foreground" />}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h3 className="font-medium">Manual Entry</h3>
                          <Badge variant="default" className="text-xs" data-testid="badge-recommended">Recommended</Badge>
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">
                          Enter your key financial numbers directly. Quick setup in under 2 minutes.
                        </p>
                      </div>
                    </div>
                  </div>

                  {dataSourceChoice === 'manual' && showManualInputs && baselineFieldsPanel}

                  <div
                    className={`p-4 border rounded-md cursor-pointer transition-colors ${
                      dataSourceChoice === 'upload'
                        ? 'border-primary bg-primary/5'
                        : 'hover-elevate'
                    }`}
                    onClick={() => {
                      setDataSourceChoice('upload');
                      setShowManualInputs(false);
                    }}
                    data-testid="option-upload-files"
                  >
                    <div className="flex items-start gap-3">
                      <div className={`w-5 h-5 rounded border-2 flex items-center justify-center shrink-0 mt-0.5 ${
                        dataSourceChoice === 'upload' ? 'border-primary bg-primary' : 'border-muted-foreground'
                      }`}>
                        {dataSourceChoice === 'upload' && <Check className="w-3 h-3 text-primary-foreground" />}
                      </div>
                      <div className="flex-1">
                        <h3 className="font-medium">Upload a Statement</h3>
                        <p className="text-sm text-muted-foreground mt-1">
                          Upload a PDF or Excel financial statement and we'll pull the numbers out for you to check.
                        </p>
                      </div>
                    </div>
                  </div>

                  {dataSourceChoice === 'upload' && (
                    <div className="p-4 border rounded-md bg-muted/30 space-y-4" data-testid="section-upload-panel">
                      <div
                        className={`border-2 border-dashed rounded-md p-6 text-center transition-colors ${
                          uploadDragActive ? 'border-primary bg-primary/5' : 'border-muted-foreground/25'
                        }`}
                        onDrop={(e) => {
                          e.preventDefault();
                          setUploadDragActive(false);
                          if (e.dataTransfer.files?.[0]) pickUploadFile(e.dataTransfer.files[0]);
                        }}
                        onDragOver={(e) => { e.preventDefault(); setUploadDragActive(true); }}
                        onDragLeave={() => setUploadDragActive(false)}
                        data-testid="dropzone-onboarding-upload"
                      >
                        <input
                          ref={uploadInputRef}
                          type="file"
                          accept=".xlsx,.xls,.pdf"
                          className="hidden"
                          onChange={(e) => e.target.files?.[0] && pickUploadFile(e.target.files[0])}
                          data-testid="input-onboarding-file"
                        />
                        {uploadFile ? (
                          <div className="flex items-center justify-center gap-2">
                            <FileText className="h-7 w-7 text-primary shrink-0" />
                            <div className="text-left">
                              <p className="font-medium text-sm" data-testid="text-onboarding-selected-file">{uploadFile.name}</p>
                              <p className="text-xs text-muted-foreground">{(uploadFile.size / 1024).toFixed(1)} KB</p>
                            </div>
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              className="ml-1"
                              onClick={() => {
                                setUploadFile(null);
                                setUploadSummary(null);
                                setUploadError(null);
                                if (uploadInputRef.current) uploadInputRef.current.value = '';
                              }}
                              data-testid="button-clear-onboarding-file"
                            >
                              <X className="h-4 w-4" />
                            </Button>
                          </div>
                        ) : (
                          <div className="space-y-2">
                            <FileUp className="h-9 w-9 mx-auto text-muted-foreground" />
                            <p className="text-sm text-muted-foreground">
                              Drop your statement here, or{' '}
                              <Button
                                type="button"
                                variant="ghost"
                                className="px-1 h-auto underline align-baseline"
                                onClick={() => uploadInputRef.current?.click()}
                                data-testid="button-browse-onboarding-file"
                              >
                                browse files
                              </Button>
                            </p>
                            <p className="text-xs text-muted-foreground">
                              .xlsx, .xls or .pdf — CSV imports are available on the Data page once you're set up.
                            </p>
                          </div>
                        )}
                      </div>

                      {uploadFile && (
                        <div className="flex justify-end">
                          <Button
                            type="button"
                            onClick={handleExtractUpload}
                            disabled={isExtracting}
                            data-testid="button-extract-onboarding-file"
                          >
                            {isExtracting ? (
                              <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Reading file...
                              </>
                            ) : (
                              <>
                                <Sparkles className="mr-2 h-4 w-4" />
                                Extract Numbers
                              </>
                            )}
                          </Button>
                        </div>
                      )}

                      {uploadSummary && (
                        <div className="flex items-start gap-2 text-sm text-muted-foreground" data-testid="text-upload-summary">
                          <Check className="h-4 w-4 text-green-500 shrink-0 mt-0.5" />
                          <span>{uploadSummary}</span>
                        </div>
                      )}

                      {uploadError && (
                        <div className="flex items-start gap-2 text-sm" data-testid="text-upload-error">
                          <AlertCircle className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
                          <span className="text-muted-foreground">{uploadError}</span>
                        </div>
                      )}

                      {showManualInputs ? baselineFieldsPanel : (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => setShowManualInputs(true)}
                          data-testid="button-enter-manually-instead"
                        >
                          Enter the numbers myself
                        </Button>
                      )}
                    </div>
                  )}

                  <div
                    className={`p-4 border rounded-md cursor-pointer transition-colors ${
                      dataSourceChoice === 'connect'
                        ? 'border-primary bg-primary/5'
                        : 'hover-elevate'
                    }`}
                    onClick={() => {
                      setDataSourceChoice('connect');
                      setShowManualInputs(false);
                    }}
                    data-testid="option-connect-apps"
                  >
                    <div className="flex items-start gap-3">
                      <div className={`w-5 h-5 rounded border-2 flex items-center justify-center shrink-0 mt-0.5 ${
                        dataSourceChoice === 'connect' ? 'border-primary bg-primary' : 'border-muted-foreground'
                      }`}>
                        {dataSourceChoice === 'connect' && <Check className="w-3 h-3 text-primary-foreground" />}
                      </div>
                      <div className="flex-1">
                        <h3 className="font-medium">Connect Apps</h3>
                        <p className="text-sm text-muted-foreground mt-1">
                          Sync with Stripe, QuickBooks, Gusto, and 20+ integrations for real-time data.
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

                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    className="flex-1"
                    onClick={() => setStep(1)}
                    disabled={isSubmitting}
                    data-testid="button-back-step2"
                  >
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Back
                  </Button>
                  <Button
                    type="button"
                    className="flex-1"
                    disabled={!dataSourceChoice || isSubmitting || manualBaselineMutation.isPending}
                    onClick={handleConnectDataNext}
                    data-testid="button-next-step2"
                  >
                    {isSubmitting || manualBaselineMutation.isPending ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Saving...
                      </>
                    ) : (
                      <>
                        Next: First Insight
                        <ArrowRight className="ml-2 h-4 w-4" />
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {step === 3 && (
          <Card>
            <CardHeader>
              <CardTitle data-testid="text-step3-title">Health Check</CardTitle>
              <CardDescription>Let's validate your financial data and show key metrics for {companyData.name || 'your company'}.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <Card className="overflow-visible" data-testid="card-metric-runway">
                    <CardContent className="p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <DollarSign className="w-5 h-5 text-primary" />
                        <span className="text-sm font-medium text-muted-foreground">Runway Estimate</span>
                      </div>
                      <p className="text-2xl font-bold" data-testid="text-runway-value">
                        {runwayMonths !== null ? `${runwayMonths.toFixed(1)} mo` : 'N/A'}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {runwayMonths !== null
                          ? runwayMonths >= 12
                            ? 'Healthy runway'
                            : runwayMonths >= 6
                            ? 'Consider fundraising soon'
                            : 'Critical - act now'
                          : 'Add financial data to calculate'}
                      </p>
                    </CardContent>
                  </Card>

                  <Card className="overflow-visible" data-testid="card-metric-burn">
                    <CardContent className="p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <TrendingDown className="w-5 h-5 text-primary" />
                        <span className="text-sm font-medium text-muted-foreground">Net Burn Rate</span>
                      </div>
                      <p className="text-2xl font-bold" data-testid="text-burn-value">
                        {hasBaselineNumbers && totalExpenses > 0 ? formatCurrency(Math.abs(netBurn)) : 'N/A'}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {!hasBaselineNumbers || totalExpenses === 0
                          ? 'Add expense data to calculate'
                          : netBurn < 0 ? 'Cash flow positive' : 'Monthly net burn'}
                      </p>
                    </CardContent>
                  </Card>

                  <Card className="overflow-visible" data-testid="card-metric-health">
                    <CardContent className="p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <Activity className="w-5 h-5 text-primary" />
                        <span className="text-sm font-medium text-muted-foreground">Health Score</span>
                      </div>
                      <p className="text-2xl font-bold" data-testid="text-health-value">
                        {hasBaselineNumbers ? `${healthScore}/100` : 'N/A'}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {!hasBaselineNumbers
                          ? 'Add data to calculate'
                          : healthScore >= 70
                          ? 'Strong financial health'
                          : healthScore >= 50
                          ? 'Room for improvement'
                          : 'Needs attention'}
                      </p>
                    </CardContent>
                  </Card>
                </div>

                {!hasBaselineNumbers && (
                  <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-md flex items-start gap-2" data-testid="banner-no-baseline">
                    <AlertCircle className="h-5 w-5 text-amber-500 shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-sm font-medium">No financial data yet</p>
                      <p className="text-xs text-muted-foreground">
                        We won't invent numbers for you. Go back and enter or upload your financials and these
                        metrics will fill in — or continue now and add them from the Data page later.
                      </p>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="px-1 h-auto underline mt-1"
                        onClick={() => setStep(2)}
                        data-testid="button-add-data-from-health-check"
                      >
                        Add my numbers
                      </Button>
                    </div>
                  </div>
                )}

                <div className="p-4 bg-muted/30 rounded-md border">
                  <div className="flex items-start gap-3">
                    <Sparkles className="w-5 h-5 text-primary mt-0.5 shrink-0" />
                    <div>
                      <h4 className="font-medium text-sm">What happens next</h4>
                      <ul className="mt-2 space-y-2 text-sm text-muted-foreground">
                        <li className="flex items-center gap-2">
                          <Check className="w-4 h-4 text-green-500 shrink-0" />
                          Full financial health analysis with 24+ metrics
                        </li>
                        <li className="flex items-center gap-2">
                          <Check className="w-4 h-4 text-green-500 shrink-0" />
                          Benchmarks against similar {companyData.stage?.replace(/_/g, ' ')} companies
                        </li>
                        <li className="flex items-center gap-2">
                          <Check className="w-4 h-4 text-green-500 shrink-0" />
                          AI-powered scenario simulations and forecasting
                        </li>
                      </ul>
                    </div>
                  </div>
                </div>

                {scanError && (
                  <div className="p-3 bg-destructive/10 border border-destructive/30 rounded-md flex items-start gap-2">
                    <AlertCircle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-destructive">Analysis Error</p>
                      <p className="text-xs text-muted-foreground">{scanError}</p>
                    </div>
                  </div>
                )}

                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    className="flex-1"
                    onClick={() => setStep(2)}
                    disabled={isSubmitting}
                    data-testid="button-back-step3"
                  >
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Back
                  </Button>
                  <Button
                    type="button"
                    className="flex-1"
                    onClick={handleRunHealthCheck}
                    disabled={isSubmitting || runTruthScanMutation.isPending}
                    data-testid="button-run-health-check"
                  >
                    {isSubmitting || runTruthScanMutation.isPending ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Validating data...
                      </>
                    ) : (
                      <>
                        <Activity className="mr-2 h-4 w-4" />
                        Run Health Check
                        <ArrowRight className="ml-2 h-4 w-4" />
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {step === 4 && (
          <Card>
            <CardHeader>
              <CardTitle data-testid="text-step4-title">Your First Simulation</CardTitle>
              <CardDescription>Now let's test a decision before you make it. This is where FounderConsole becomes your flight simulator.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                <div className="p-6 rounded-xl border bg-gradient-to-br from-violet-500/5 to-primary/5">
                  <h4 className="font-semibold text-foreground mb-3">What Monte Carlo simulations do</h4>
                  <p className="text-sm text-muted-foreground leading-relaxed mb-4">
                    Instead of guessing what might happen, we run thousands of scenarios with different assumptions. 
                    You get P10 (pessimistic), P50 (likely), and P90 (optimistic) outcomes — the same analysis venture capitalists use.
                  </p>
                  <div className="grid grid-cols-3 gap-3">
                    <div className="text-center p-3 rounded-lg bg-background/50 border">
                      <p className="text-xs text-muted-foreground mb-1">P10 (Worst)</p>
                      <p className="text-lg font-bold font-mono text-red-400">6 mo</p>
                    </div>
                    <div className="text-center p-3 rounded-lg bg-background/50 border border-primary/20">
                      <p className="text-xs text-muted-foreground mb-1">P50 (Likely)</p>
                      <p className="text-lg font-bold font-mono text-foreground">14 mo</p>
                    </div>
                    <div className="text-center p-3 rounded-lg bg-background/50 border">
                      <p className="text-xs text-muted-foreground mb-1">P90 (Best)</p>
                      <p className="text-lg font-bold font-mono text-emerald-400">24+ mo</p>
                    </div>
                  </div>
                </div>

                <div className="p-4 bg-muted/30 rounded-md border">
                  <h4 className="font-medium text-sm mb-2">Try these scenarios after setup:</h4>
                  <ul className="space-y-2 text-sm text-muted-foreground">
                    <li className="flex items-center gap-2">
                      <Check className="w-4 h-4 text-primary shrink-0" />
                      What if we hire 3 engineers next quarter?
                    </li>
                    <li className="flex items-center gap-2">
                      <Check className="w-4 h-4 text-primary shrink-0" />
                      What if we raise prices by 20%?
                    </li>
                    <li className="flex items-center gap-2">
                      <Check className="w-4 h-4 text-primary shrink-0" />
                      When should we start fundraising?
                    </li>
                  </ul>
                </div>

                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    className="flex-1"
                    onClick={() => setStep(3)}
                    data-testid="button-back-step4"
                  >
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Back
                  </Button>
                  <Button
                    type="button"
                    className="flex-1"
                    onClick={handleGoToSimulate}
                    data-testid="button-next-step4"
                  >
                    <Sparkles className="mr-2 h-4 w-4" />
                    Continue to AI Copilot
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {step === 5 && (
          <Card>
            <CardHeader>
              <CardTitle data-testid="text-step5-title">Meet Your AI Copilot</CardTitle>
              <CardDescription>Your AI-powered strategic advisor is ready. Ask anything about your company.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                <div className="p-6 rounded-xl border bg-gradient-to-br from-amber-500/5 to-orange-500/5">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="h-10 w-10 rounded-full bg-gradient-to-br from-primary to-violet-500 flex items-center justify-center">
                      <Sparkles className="h-5 w-5 text-white" />
                    </div>
                    <div>
                      <h4 className="font-semibold text-foreground">AI Founder Copilot</h4>
                      <p className="text-xs text-muted-foreground">Powered by GPT-4o, Claude & Gemini</p>
                    </div>
                  </div>
                  <p className="text-sm text-muted-foreground leading-relaxed mb-4">
                    Ask strategic questions in plain English. The copilot analyzes your financial data, 
                    runs simulations, and provides recommendations backed by real numbers.
                  </p>
                  <div className="space-y-2">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Try asking:</p>
                    {[
                      "What's our biggest financial risk right now?",
                      "Should we hire or extend runway first?",
                      "How does our burn rate compare to similar startups?",
                    ].map((q) => (
                      <div key={q} className="p-2.5 rounded-lg bg-background/50 border text-sm text-foreground flex items-center gap-2">
                        <span className="text-primary font-mono text-xs">&gt;</span>
                        {q}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    className="flex-1"
                    onClick={() => setStep(4)}
                    data-testid="button-back-step5"
                  >
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Back
                  </Button>
                  <Button
                    type="button"
                    className="flex-1"
                    onClick={handleFinishSetup}
                    data-testid="button-finish-setup"
                  >
                    Launch Dashboard
                    <ArrowRight className="ml-2 h-4 w-4" />
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
