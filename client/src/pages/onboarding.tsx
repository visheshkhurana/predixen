import { useState, useEffect } from 'react';
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
import { useCreateCompany, useManualBaseline, useRunTruthScan, useSeedSample } from '@/api/hooks';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Badge } from '@/components/ui/badge';
import { HelpCircle, Sparkles, Check, AlertCircle, Loader2, ArrowRight, ArrowLeft, TrendingDown, DollarSign, Activity } from 'lucide-react';
import type { AmountScale } from '@/lib/utils';

const STEPS = [
  { id: 1, title: 'Welcome', description: 'Tell us about your startup' },
  { id: 2, title: 'Connect Data', description: 'Choose your data source' },
  { id: 3, title: 'First Insight', description: 'See your key metrics' },
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
      setLocation('/');
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

  const isSeedingInProgress = createCompanyMutation.isPending || seedSampleMutation.isPending;
  const currentCompany = useFounderStore((s) => s.currentCompany);

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
      const company = await createCompanyMutation.mutateAsync(companyData);
      setCurrentCompany(company);
      markStepComplete(1);

      const defaults = STAGE_DEFAULTS[companyData.stage];
      if (defaults) {
        setBaselineData(defaults);
      }

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

  const handleConnectDataNext = async () => {
    if (dataSourceChoice === 'manual' && !baselineSaved) {
      await handleSaveBaseline();
    }
    markStepComplete(2);
    setStep(3);
  };

  const handleFinishSetup = async () => {
    const { token } = useFounderStore.getState();
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
      markStepComplete(3);
      localStorage.setItem('founderConsoleOnboardingComplete', 'true');
      toast({ title: 'Setup complete!', description: 'Your dashboard is ready.' });
      setLocation('/');
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        toast({ title: 'Session expired', description: 'Please log in again.', variant: 'destructive' });
        setLocation('/auth');
        return;
      }
      const message = err instanceof ApiError ? err.message : 'Failed to run analysis. Redirecting to dashboard.';
      setScanError(message);
      localStorage.setItem('founderConsoleOnboardingComplete', 'true');
      setTimeout(() => setLocation('/'), 2000);
    } finally {
      setIsSubmitting(false);
    }
  };

  const totalExpenses = baselineData.opex + baselineData.payroll + baselineData.other_costs;
  const netBurn = totalExpenses - baselineData.monthly_revenue;
  const runwayMonths = netBurn > 0 && baselineData.cash_balance > 0 ? baselineData.cash_balance / netBurn : null;
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

                  {dataSourceChoice === 'manual' && showManualInputs && (
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
                            value={baselineData.monthly_revenue}
                            onChange={(e) => setBaselineData({ ...baselineData, monthly_revenue: Number(e.target.value) })}
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
                            value={baselineData.gross_margin_pct}
                            onChange={(e) => setBaselineData({ ...baselineData, gross_margin_pct: Number(e.target.value) })}
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
                            value={baselineData.opex}
                            onChange={(e) => setBaselineData({ ...baselineData, opex: Number(e.target.value) })}
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
                            value={baselineData.payroll}
                            onChange={(e) => setBaselineData({ ...baselineData, payroll: Number(e.target.value) })}
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
                            value={baselineData.other_costs}
                            onChange={(e) => setBaselineData({ ...baselineData, other_costs: Number(e.target.value) })}
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
                            value={baselineData.cash_balance}
                            onChange={(e) => setBaselineData({ ...baselineData, cash_balance: Number(e.target.value) })}
                            min={0}
                            data-testid="input-cash-balance"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="headcount">Headcount</Label>
                          <Input
                            id="headcount"
                            type="number"
                            value={baselineData.headcount}
                            onChange={(e) => setBaselineData({ ...baselineData, headcount: Number(e.target.value) })}
                            min={0}
                            data-testid="input-headcount"
                          />
                        </div>
                      </div>

                      {baselineSaved && (
                        <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
                          <Check className="w-4 h-4" />
                          <span>Data saved</span>
                        </div>
                      )}
                    </div>
                  )}

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
                        <h3 className="font-medium">Upload Files</h3>
                        <p className="text-sm text-muted-foreground mt-1">
                          Upload PDF, Excel, or CSV files. We'll extract financial data automatically.
                        </p>
                      </div>
                    </div>
                  </div>

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
              <CardTitle data-testid="text-step3-title">Your First Insight</CardTitle>
              <CardDescription>Here's a preview of the key metrics we'll track for {companyData.name || 'your company'}.</CardDescription>
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
                        {totalExpenses > 0 ? formatCurrency(Math.abs(netBurn)) : 'N/A'}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {netBurn < 0 ? 'Cash flow positive' : netBurn > 0 ? 'Monthly net burn' : 'Add expense data to calculate'}
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
                        {totalExpenses > 0 || baselineData.cash_balance > 0 ? `${healthScore}/100` : 'N/A'}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {healthScore >= 70
                          ? 'Strong financial health'
                          : healthScore >= 50
                          ? 'Room for improvement'
                          : totalExpenses > 0 || baselineData.cash_balance > 0
                          ? 'Needs attention'
                          : 'Add data to calculate'}
                      </p>
                    </CardContent>
                  </Card>
                </div>

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
                    onClick={handleFinishSetup}
                    disabled={isSubmitting || runTruthScanMutation.isPending}
                    data-testid="button-run-simulation"
                  >
                    {isSubmitting || runTruthScanMutation.isPending ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Analyzing...
                      </>
                    ) : (
                      <>
                        <Sparkles className="mr-2 h-4 w-4" />
                        Run Simulation
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
