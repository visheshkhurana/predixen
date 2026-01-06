import { useState } from 'react';
import { useLocation } from 'wouter';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Progress } from '@/components/ui/progress';
import { useToast } from '@/hooks/use-toast';
import { api, ApiError } from '@/api/client';
import { useFounderStore } from '@/store/founderStore';
import { useCreateCompany, useManualBaseline, useRunTruthScan } from '@/api/hooks';

const STEPS = [
  { id: 1, title: 'Company Info', description: 'Tell us about your startup' },
  { id: 2, title: 'Financial Baseline', description: 'Enter your current financials' },
  { id: 3, title: 'First Truth Scan', description: 'Analyzing your data' },
];

export default function OnboardingPage() {
  const [, setLocation] = useLocation();
  const { toast } = useToast();
  const { setCurrentCompany, setTruthScan, setCurrentStep: setStoreStep } = useFounderStore();
  const [step, setStep] = useState(1);
  const [companyData, setCompanyData] = useState({
    name: '',
    website: '',
    industry: 'general_saas',
    stage: 'seed',
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
  
  const createCompanyMutation = useCreateCompany();
  const manualBaselineMutation = useManualBaseline();
  const runTruthScanMutation = useRunTruthScan();
  
  const handleCompanySubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    try {
      const company = await createCompanyMutation.mutateAsync(companyData);
      setCurrentCompany(company);
      setStep(2);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Failed to create company';
      toast({ title: 'Error', description: message, variant: 'destructive' });
    }
  };
  
  const handleBaselineSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const { currentCompany } = useFounderStore.getState();
    if (!currentCompany) return;
    
    try {
      await manualBaselineMutation.mutateAsync({
        companyId: currentCompany.id,
        data: baselineData,
      });
      setStep(3);
      
      const truthScan = await runTruthScanMutation.mutateAsync(currentCompany.id);
      setTruthScan(truthScan);
      setStoreStep('truth');
      
      toast({ title: 'Setup complete!', description: 'Your first Truth Scan is ready.' });
      setTimeout(() => setLocation('/'), 1500);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Failed to save baseline';
      toast({ title: 'Error', description: message, variant: 'destructive' });
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
              <form onSubmit={handleCompanySubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="company-name">Company Name</Label>
                  <Input
                    id="company-name"
                    value={companyData.name}
                    onChange={(e) => setCompanyData({ ...companyData, name: e.target.value })}
                    required
                    placeholder="Your Company"
                    data-testid="input-company-name"
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
                  />
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Industry</Label>
                    <Select
                      value={companyData.industry}
                      onValueChange={(v) => setCompanyData({ ...companyData, industry: v })}
                    >
                      <SelectTrigger data-testid="select-industry">
                        <SelectValue />
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
                    <Label>Stage</Label>
                    <Select
                      value={companyData.stage}
                      onValueChange={(v) => setCompanyData({ ...companyData, stage: v })}
                    >
                      <SelectTrigger data-testid="select-stage">
                        <SelectValue />
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
                
                <Button
                  type="submit"
                  className="w-full"
                  disabled={createCompanyMutation.isPending}
                  data-testid="button-next-step"
                >
                  {createCompanyMutation.isPending ? 'Creating...' : 'Continue'}
                </Button>
              </form>
            </CardContent>
          </Card>
        )}
        
        {step === 2 && (
          <Card>
            <CardHeader>
              <CardTitle>Financial Baseline</CardTitle>
              <CardDescription>Enter your current monthly financials</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleBaselineSubmit} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="revenue">Monthly Revenue ($)</Label>
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
                    <Label htmlFor="gross-margin">Gross Margin (%)</Label>
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
                    <Label htmlFor="opex">Opex ($)</Label>
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
                    <Label htmlFor="payroll">Payroll ($)</Label>
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
                    <Label htmlFor="other-costs">Other Costs ($)</Label>
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
                  <Label htmlFor="cash">Cash Balance ($)</Label>
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
                  disabled={manualBaselineMutation.isPending || runTruthScanMutation.isPending}
                  data-testid="button-run-scan"
                >
                  {manualBaselineMutation.isPending || runTruthScanMutation.isPending
                    ? 'Running Truth Scan...'
                    : 'Run First Truth Scan'}
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
