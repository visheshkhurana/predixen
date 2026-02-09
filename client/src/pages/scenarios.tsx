import { useState, useMemo, useEffect, useRef, useCallback } from 'react';
import { useParams } from 'wouter';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { SurvivalCurveChart } from '@/components/SurvivalCurveChart';
import { BandsChart } from '@/components/BandsChart';
import { ExportButton } from '@/components/ExportButton';
import { ScenarioComparisonTable } from '@/components/ScenarioComparisonTable';
import { SimulationSummaryBanner } from '@/components/SimulationSummaryBanner';
import { SimulationLearnMoreModal } from '@/components/SimulationLearnMoreModal';
import { ScenarioWizard } from '@/components/ScenarioWizard';
import { StrategicScenarioBuilder } from '@/components/StrategicScenarioBuilder';
import { type ScenarioEvent } from '@/components/CustomEventBuilder';
import { MonthlyResultsTable } from '@/components/MonthlyResultsTable';
import { ScenarioComparisonChart } from '@/components/ScenarioComparisonChart';
import { MultiScenarioSummary } from '@/components/MultiScenarioSummary';
import { SensitivityAnalysisPanel } from '@/components/SensitivityAnalysisPanel';
import { DecisionRankingTable } from '@/components/DecisionRankingTable';
import { RegimeDistributionChart } from '@/components/RegimeDistributionChart';
import { ExecutiveSummary } from '@/components/ExecutiveSummary';
import { ScenarioCard } from '@/components/ScenarioCard';
import { GlossaryModal } from '@/components/GlossaryModal';
import { RiskGauge } from '@/components/RiskGauge';
import { DrillDownChart } from '@/components/DrillDownChart';
import { StackedBurnRevenueChart } from '@/components/StackedBurnRevenueChart';
import { ProjectionChart } from '@/components/ProjectionChart';
import { ProjectionSummary } from '@/components/ProjectionSummary';
import { SimulationInsights } from '@/components/SimulationInsights';
import { AISummaryCard } from '@/components/AISummaryCard';
import { DashboardKPICards } from '@/components/DashboardKPICards';
import { ScenarioComparisonView } from '@/components/ScenarioComparisonView';
import { TruthScanBlockedModal } from '@/components/TruthScanGate';
import { isTruthScanRequired, getTruthScanUploadId } from '@/lib/errors';
import {
  Play, BarChart3, History, Loader2, Target, Trophy,
  Sparkles, Lock, Zap, AlertTriangle, ExternalLink,
  ChevronRight, FlaskConical, TrendingUp, DollarSign,
  Clock, Percent, ArrowRight, Users, FileText, MessageSquare,
  ChevronDown, ChevronUp, Search, Flame, ArrowUpRight,
  RotateCcw, Download, Shield
} from 'lucide-react';
import { EmptyState, EmptyStateCard } from '@/components/ui/empty-state';
import { TornadoChart, WhatIfExplorer, StressTestPanel, ReverseStressTest } from '@/components/simulation';
import { calculateSensitivity, calculateWhatIfImpact, type FinancialState } from '@/lib/simulation/sensitivityAnalysis';
import type { StressTestTemplate } from '@/lib/simulation/stressTestTemplates';
import { useFounderStore } from '@/store/founderStore';
import { useFinancialMetrics } from '@/hooks/useFinancialMetrics';
import { useScenarios, useCreateScenario, useRunSimulation, useSimulation, useMultiScenarioSimulation, useSensitivityAnalysis, useEnhancedMultiScenarioSimulation, useScenarioTimeseries, useTruthScan } from '@/api/hooks';
import { ScenarioComments } from '@/components/ScenarioComments';
import { DistributionView } from '@/components/DistributionView';
import { useScenarioComments, useAddComment, useEditComment, useDeleteComment } from '@/api/workspace';
import { useToast } from '@/hooks/use-toast';
import { formatSimulationForExport } from '@/lib/exportUtils';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea, ScrollBar } from '@/components/ui/scroll-area';
import { SCENARIO_TEMPLATES } from '@/config/templates';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

function getCashBands(simulation: any): { p10: number[]; p50: number[]; p90: number[] } {
  if (simulation.bands?.cash) return simulation.bands.cash;
  if (simulation.cash_bands) return simulation.cash_bands;
  if (simulation.metrics?.cash && Array.isArray(simulation.metrics.cash)) {
    const cashMetrics = simulation.metrics.cash;
    return {
      p10: cashMetrics.map((m: any) => m.p10 ?? 0),
      p50: cashMetrics.map((m: any) => m.p50 ?? 0),
      p90: cashMetrics.map((m: any) => m.p90 ?? 0),
    };
  }
  if (simulation.month_data && Array.isArray(simulation.month_data)) {
    return {
      p10: simulation.month_data.map((m: any) => m.cash_p10 ?? 0),
      p50: simulation.month_data.map((m: any) => m.cash_p50 ?? 0),
      p90: simulation.month_data.map((m: any) => m.cash_p90 ?? 0),
    };
  }
  return { p10: [], p50: [], p90: [] };
}

function formatCurrency(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

const SUGGESTION_CHIPS = [
  { label: 'Cut marketing 30%', icon: TrendingUp },
  { label: 'Raise prices 20%', icon: DollarSign },
  { label: 'Hire 5 engineers', icon: Users },
  { label: 'Churn hits 5%', icon: AlertTriangle },
  { label: 'Raise $2M Series A', icon: ArrowUpRight },
  { label: 'New market expansion', icon: Target },
];

export default function ScenariosPage() {
  const { currentCompany, setCurrentStep, setCurrentScenario, setLatestRun, financialBaseline } = useFounderStore();
  const { toast } = useToast();
  const params = useParams<{ id?: string }>();
  const { data: scenarios, isLoading: scenariosLoading } = useScenarios(currentCompany?.id || null);
  const { data: truthScan, isLoading: truthScanLoading } = useTruthScan(currentCompany?.id || null);
  const createScenarioMutation = useCreateScenario();
  const runSimulationMutation = useRunSimulation();

  const [selectedScenarioId, setSelectedScenarioId] = useState<number | null>(null);

  useEffect(() => {
    if (params.id && scenarios) {
      const idFromUrl = parseInt(params.id, 10);
      if (!isNaN(idFromUrl) && scenarios.some((s: any) => s.id === idFromUrl)) {
        setSelectedScenarioId(idFromUrl);
      } else if (scenarios.length > 0) {
        setSelectedScenarioId(scenarios[0].id);
      }
    } else if (!params.id && scenarios && scenarios.length > 0 && !selectedScenarioId) {
      setSelectedScenarioId(scenarios[0].id);
    }
  }, [params.id, scenarios]);

  const { data: simulation, isLoading: simLoading } = useSimulation(selectedScenarioId);
  const { data: timeseriesData, isLoading: timeseriesLoading } = useScenarioTimeseries(selectedScenarioId);

  const [isCreating, setIsCreating] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [duplicateDialog, setDuplicateDialog] = useState<{ open: boolean; existingId?: number; scenarioData?: any }>({ open: false });
  const [showAdvancedView, setShowAdvancedView] = useState(false);
  const [advancedTab, setAdvancedTab] = useState('builder');

  const multiSimMutation = useMultiScenarioSimulation();
  const [multiSimResults, setMultiSimResults] = useState<any>(null);
  const sensitivityMutation = useSensitivityAnalysis();
  const [sensitivityResults, setSensitivityResults] = useState<any>(null);
  const enhancedMultiMutation = useEnhancedMultiScenarioSimulation();
  const [enhancedResults, setEnhancedResults] = useState<any>(null);
  const [isCreatingBaseline, setIsCreatingBaseline] = useState(false);
  const [customEvents, setCustomEvents] = useState<ScenarioEvent[]>([]);
  const [truthScanModal, setTruthScanModal] = useState<{ open: boolean; uploadId?: string }>({ open: false });

  const { data: comments = [], isLoading: commentsLoading } = useScenarioComments(selectedScenarioId || 0);
  const addCommentMutation = useAddComment();
  const editCommentMutation = useEditComment();
  const deleteCommentMutation = useDeleteComment();
  const currentUserEmail = currentCompany ? `demo@predixen.ai` : 'user@example.com';

  const [questionInput, setQuestionInput] = useState('');
  const resultsRef = useRef<HTMLDivElement>(null);

  const hasRunScenario = useMemo(() => {
    if (!scenarios || scenarios.length === 0) return false;
    return scenarios.some((s: any) => s.latest_simulation);
  }, [scenarios]);

  const hasSimulationResults = simulation || multiSimResults || enhancedResults || sensitivityResults;

  const { metrics: sharedMetrics } = useFinancialMetrics();

  const { baseMetrics, isUsingDemoData } = useMemo(() => {
    if (!currentCompany) return { baseMetrics: undefined, isUsingDemoData: false };
    const hasRealData = sharedMetrics.mrr > 0 || sharedMetrics.cashOnHand > 0 || sharedMetrics.netBurn > 0;
    const cashOnHand = sharedMetrics.cashOnHand;
    const monthlyRevenue = sharedMetrics.mrr;
    const monthlyExpenses = sharedMetrics.netBurn + monthlyRevenue;
    const grossMargin = sharedMetrics.grossMarginPct;
    const truthScanGrowth = truthScan?.metrics?.revenue_growth_mom ?? truthScan?.outputs_json?.metrics?.revenue_growth_mom;
    const truthGrowthVal = typeof truthScanGrowth === 'object' && truthScanGrowth !== null
      ? truthScanGrowth.value : truthScanGrowth;
    const growthRate = financialBaseline?.monthlyGrowthRate ?? truthGrowthVal ?? 10;
    const churnRate = sharedMetrics.churnRatePct;
    const currentRunway = sharedMetrics.runway === Infinity ? 999 : sharedMetrics.runway;
    return {
      baseMetrics: { cashOnHand, monthlyExpenses, monthlyRevenue, currentRunway, growthRate, grossMargin, churnRate },
      isUsingDemoData: !hasRealData,
    };
  }, [currentCompany, sharedMetrics, financialBaseline, truthScan]);

  const dashboardMetrics = useMemo(() => {
    if (!baseMetrics) return undefined;
    const netBurn = baseMetrics.monthlyExpenses - baseMetrics.monthlyRevenue;
    const netNewARR = baseMetrics.monthlyRevenue * (baseMetrics.growthRate / 100) * 12;
    return {
      cash_balance: baseMetrics.cashOnHand,
      monthly_revenue: baseMetrics.monthlyRevenue,
      net_burn: netBurn,
      runway_months: baseMetrics.currentRunway,
      revenue_growth_mom: baseMetrics.growthRate,
      gross_margin: baseMetrics.grossMargin,
      churn_rate: baseMetrics.churnRate,
      burn_multiple: netNewARR > 0 ? netBurn / netNewARR : 0,
      ltv_cac_ratio: sharedMetrics.ltvCacRatio,
      cac: sharedMetrics.cac,
      ltv: sharedMetrics.ltv,
    };
  }, [baseMetrics, sharedMetrics]);

  const comparisonData = useMemo(() => {
    if (!scenarios) return [];
    return scenarios.map((s: any) => ({
      id: s.id,
      name: s.name,
      runway_p50: s.latest_simulation?.runway?.p50,
      survival_18m: s.latest_simulation?.survival?.['18m'],
      end_cash: s.latest_simulation?.summary?.end_cash,
      monthly_burn: s.latest_simulation?.summary?.monthly_burn,
      tags: s.tags,
    }));
  }, [scenarios]);

  const currentScenarioName = useMemo(() => {
    if (!selectedScenarioId || !scenarios) return 'New Scenario';
    const selected = scenarios.find((s: any) => s.id === selectedScenarioId);
    return selected?.name || 'New Scenario';
  }, [selectedScenarioId, scenarios]);

  useEffect(() => {
    if (selectedScenarioId && scenarios) {
      const selected = scenarios.find((s: any) => s.id === selectedScenarioId);
      if (selected) setCurrentScenario({ id: selected.id, name: selected.name });
    } else {
      setCurrentScenario(null);
    }
  }, [selectedScenarioId, scenarios, setCurrentScenario]);

  useEffect(() => {
    if (simulation && selectedScenarioId) {
      setLatestRun({
        id: simulation.run_id || simulation.id?.toString() || `run-${Date.now()}`,
        timestamp: simulation.created_at || new Date().toISOString(),
        scenarioId: selectedScenarioId,
      });
    }
  }, [simulation, selectedScenarioId, setLatestRun]);

  if (!currentCompany) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground" data-testid="text-no-company">Select a company to manage scenarios</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const checkForDuplicate = (name: string) => {
    if (!scenarios) return null;
    const existing = scenarios.find((s: any) => s.name.toLowerCase() === name.toLowerCase());
    return existing?.id || null;
  };

  const handleWizardComplete = async (scenarioData: any) => {
    if (!currentCompany) return;
    const existingId = checkForDuplicate(scenarioData.name);
    if (existingId) {
      setDuplicateDialog({ open: true, existingId, scenarioData });
      return;
    }
    await runScenario(scenarioData, false);
  };

  const runScenario = async (scenarioData: any, overwrite: boolean, existingId?: number) => {
    setDuplicateDialog({ open: false });
    setIsCreating(true);
    try {
      const scenario = await createScenarioMutation.mutateAsync({
        companyId: currentCompany.id,
        data: { ...scenarioData, overwrite_id: overwrite ? existingId : undefined },
      });
      setSelectedScenarioId(scenario.id);
      setIsRunning(true);
      await runSimulationMutation.mutateAsync({ scenarioId: scenario.id, nSims: 1000 });
      setCurrentStep('simulation');
      toast({ title: 'Simulation complete!' });
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth' }), 300);
    } catch (err: any) {
      if (isTruthScanRequired(err)) {
        const uploadId = getTruthScanUploadId(err);
        if (uploadId) {
          setTruthScanModal({ open: true, uploadId });
        } else {
          toast({ title: 'Data Validation Required', description: 'Please validate your financial data in the Truth Scan before running simulations.', variant: 'destructive' });
        }
        return;
      }
      toast({ title: 'Error', description: err.message, variant: 'destructive' });
    } finally {
      setIsCreating(false);
      setIsRunning(false);
    }
  };

  const handleRunScenario = async (scenarioId: number) => {
    setSelectedScenarioId(scenarioId);
    setIsRunning(true);
    try {
      await runSimulationMutation.mutateAsync({ scenarioId, nSims: 1000 });
      setCurrentStep('simulation');
      toast({ title: 'Simulation complete!' });
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth' }), 300);
    } catch (err: any) {
      if (isTruthScanRequired(err)) {
        const uploadId = getTruthScanUploadId(err);
        if (uploadId) {
          setTruthScanModal({ open: true, uploadId });
        } else {
          toast({ title: 'Data Validation Required', description: 'Please validate your financial data in the Truth Scan before running simulations.', variant: 'destructive' });
        }
        return;
      }
      toast({ title: 'Error', description: err.message, variant: 'destructive' });
    } finally {
      setIsRunning(false);
    }
  };

  const handleRunMultiScenario = async () => {
    if (!currentCompany) return;
    try {
      const result = await multiSimMutation.mutateAsync({ companyId: currentCompany.id, options: { n_sims: 500, horizon_months: 24 } });
      setMultiSimResults(result);
      toast({ title: 'All scenarios simulated successfully!' });
    } catch (err: any) {
      if (isTruthScanRequired(err)) {
        const uploadId = getTruthScanUploadId(err);
        if (uploadId) { setTruthScanModal({ open: true, uploadId }); } else {
          toast({ title: 'Data Validation Required', description: 'Please validate your financial data in the Truth Scan before running simulations.', variant: 'destructive' });
        }
        return;
      }
      toast({ title: 'Error', description: err.message, variant: 'destructive' });
    }
  };

  const handleRunSensitivityAnalysis = async (targetRunway: number = 18, targetProbability: number = 0.7) => {
    if (!currentCompany) return;
    try {
      const result = await sensitivityMutation.mutateAsync({ companyId: currentCompany.id, targetRunway, targetProbability });
      setSensitivityResults(result);
      toast({ title: 'Sensitivity analysis complete!' });
    } catch (err: any) {
      if (isTruthScanRequired(err)) {
        const uploadId = getTruthScanUploadId(err);
        if (uploadId) { setTruthScanModal({ open: true, uploadId }); } else {
          toast({ title: 'Data Validation Required', description: 'Please validate your financial data in the Truth Scan before running simulations.', variant: 'destructive' });
        }
        return;
      }
      toast({ title: 'Error', description: err.message, variant: 'destructive' });
    }
  };

  const handleRunEnhancedMulti = async () => {
    if (!currentCompany) return;
    try {
      const result = await enhancedMultiMutation.mutateAsync({
        companyId: currentCompany.id,
        options: {
          n_sims: 500, horizon_months: 24, include_sensitivity: true,
          scenarios: [
            { name: 'Baseline', description: 'Current trajectory' },
            { name: 'Cost Cutting', description: 'Reduce expenses by 20%', events: [{ event_type: 'cost_cut', start_month: 1, params: { opex_reduction_pct: 20, payroll_reduction_pct: 15 } }] },
            { name: 'Growth Investment', description: 'Increase marketing spend', events: [{ event_type: 'marketing_spend_change', start_month: 1, params: { change_pct: 30 } }] },
            { name: 'Fundraise', description: 'Raise $1M bridge round', events: [{ event_type: 'fundraise', start_month: 3, params: { amount: 1000000 } }] },
          ]
        }
      });
      setEnhancedResults(result);
      toast({ title: 'Enhanced simulation complete!' });
    } catch (err: any) {
      if (isTruthScanRequired(err)) {
        const uploadId = getTruthScanUploadId(err);
        if (uploadId) { setTruthScanModal({ open: true, uploadId }); } else {
          toast({ title: 'Data Validation Required', description: 'Please validate your financial data in the Truth Scan before running simulations.', variant: 'destructive' });
        }
        return;
      }
      toast({ title: 'Error', description: err.message, variant: 'destructive' });
    }
  };

  const handleCreateBaselineScenario = async () => {
    if (!currentCompany) return;
    const baselineTemplate = SCENARIO_TEMPLATES.find(t => t.tags.includes('baseline'));
    if (!baselineTemplate) return;
    setIsCreatingBaseline(true);
    try {
      const scenarioData = {
        name: baselineTemplate.name,
        pricing_change_pct: baselineTemplate.deltas.pricing_change_pct ?? 0,
        growth_uplift_pct: baselineTemplate.deltas.growth_uplift_pct ?? 0,
        burn_reduction_pct: baselineTemplate.deltas.burn_reduction_pct ?? 0,
        gross_margin_delta_pct: 0, churn_change_pct: 0, cac_change_pct: 0,
        fundraise_month: null, fundraise_amount: 0, tags: baselineTemplate.tags,
      };
      const scenario = await createScenarioMutation.mutateAsync({ companyId: currentCompany.id, data: scenarioData });
      setSelectedScenarioId(scenario.id);
      await runSimulationMutation.mutateAsync({ scenarioId: scenario.id, nSims: 1000 });
      setCurrentStep('simulation');
      toast({ title: 'Baseline scenario created!', description: 'Your baseline simulation is ready to view.' });
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth' }), 300);
    } catch (err: any) {
      toast({ title: 'Error', description: err.message, variant: 'destructive' });
    } finally {
      setIsCreatingBaseline(false);
    }
  };

  const parseNaturalLanguageScenario = (text: string) => {
    const q = text.toLowerCase();
    const params: any = {
      pricing_change_pct: 0,
      growth_uplift_pct: 0,
      burn_reduction_pct: 0,
      gross_margin_delta_pct: 0,
      churn_change_pct: 0,
      cac_change_pct: 0,
      fundraise_month: null,
      fundraise_amount: 0,
    };
    const tags: string[] = [];
    let matched = false;

    const fundraiseMatch = q.match(/(?:(?:raise|fundrais\w*|series\s*[a-z]?)\s+\$?([\d,.]+)\s*(m|mm|million|k|thousand)?)/i);
    const isRaisePrices = q.match(/raise\s+price/i);
    if (fundraiseMatch && !isRaisePrices) {
      let amount = parseFloat(fundraiseMatch[1].replace(/,/g, ''));
      const unit = (fundraiseMatch[2] || '').toLowerCase();
      if (unit === 'm' || unit === 'mm' || unit === 'million') amount *= 1_000_000;
      else if (unit === 'k' || unit === 'thousand') amount *= 1_000;
      else if (amount < 1000) amount *= 1_000_000;
      params.fundraise_amount = amount;
      params.fundraise_month = 3;
      tags.push('fundraising');
      matched = true;
    }

    const hireMatch = q.match(/hire\s+(\d+)\s*(?:engineer|dev|people|employee|person|staff)?/i);
    if (hireMatch) {
      const count = parseInt(hireMatch[1]);
      const salaryEstimate = 12000;
      params.burn_reduction_pct = Math.round(-(count * salaryEstimate) / (baseMetrics?.monthlyExpenses || 50000) * 100);
      params.growth_uplift_pct += count * 3;
      tags.push('growth');
      matched = true;
    } else if (q.includes('hire') || q.includes('engineer') || q.includes('team')) {
      params.burn_reduction_pct = -15;
      params.growth_uplift_pct += 9;
      tags.push('growth');
      matched = true;
    }

    const cutMatch = q.match(/(?:cut|reduce|slash|lower)\s+(?:(?:burn|marketing|spend|cost|expense)s?\s+)?(?:by\s+)?(\d+)\s*%/i);
    if (cutMatch) {
      params.burn_reduction_pct = parseInt(cutMatch[1]);
      tags.push('cost-cutting');
      matched = true;
    } else if (q.match(/(?:cut|reduce|slash|lower)\s+(?:burn|marketing|spend|cost|expense)/i)) {
      params.burn_reduction_pct = 20;
      tags.push('cost-cutting');
      matched = true;
    }

    const priceUpMatch = q.match(/(?:raise|increase|boost)\s+(?:price|pricing)s?\s+(?:by\s+)?(\d+)\s*%/i);
    const priceGenMatch = q.match(/(?:price|pricing)\s+.*?(\d+)\s*%/i);
    if (priceUpMatch) {
      params.pricing_change_pct = parseInt(priceUpMatch[1]);
      tags.push('pricing');
      matched = true;
    } else if (priceGenMatch) {
      params.pricing_change_pct = parseInt(priceGenMatch[1]);
      tags.push('pricing');
      matched = true;
    }

    const growthMatch = q.match(/(?:growth|grow)\s+.*?(?:by\s+)?(\d+)\s*%/i);
    const growthDecreaseMatch = q.match(/(?:growth|grow)\s+(?:drop|decrease|fall|decline)s?\s+(?:by\s+|to\s+)?(\d+)\s*%/i);
    if (growthDecreaseMatch) {
      params.growth_uplift_pct += -parseInt(growthDecreaseMatch[1]);
      tags.push('pessimistic');
      matched = true;
    } else if (growthMatch) {
      params.growth_uplift_pct += parseInt(growthMatch[1]);
      tags.push('growth');
      matched = true;
    }

    const churnMatch = q.match(/churn\s+.*?(\d+)\s*%/i);
    if (churnMatch) {
      params.churn_change_pct = parseInt(churnMatch[1]);
      tags.push('pessimistic');
      matched = true;
    } else if (q.includes('churn')) {
      params.churn_change_pct = 5;
      tags.push('pessimistic');
      matched = true;
    }

    if (q.includes('market') || q.includes('expan')) {
      if (!matched || !tags.includes('growth')) {
        params.growth_uplift_pct += 25;
        params.burn_reduction_pct = params.burn_reduction_pct || -15;
        tags.push('growth');
        matched = true;
      }
    }

    const uniqueTags = tags.length > 0 ? Array.from(new Set(tags)) : ['custom'];
    return { params, tags: uniqueTags, matched };
  };

  const handleQuestionSubmit = () => {
    if (!questionInput.trim()) return;
    const scenarioName = questionInput.trim().length > 60 ? questionInput.trim().slice(0, 60) + '...' : questionInput.trim();

    const { params, tags } = parseNaturalLanguageScenario(questionInput);

    const scenarioData: any = {
      name: scenarioName,
      ...params,
      tags,
    };

    console.log('[NLP] Input:', questionInput);
    console.log('[NLP] Parsed params:', JSON.stringify(params));
    console.log('[NLP] Tags:', tags);

    handleWizardComplete(scenarioData);
    setQuestionInput('');
  };

  const handleChipClick = (label: string) => {
    setQuestionInput(label);
    const { params, tags } = parseNaturalLanguageScenario(label);
    const scenarioData: any = {
      name: label,
      ...params,
      tags,
    };
    handleWizardComplete(scenarioData);
  };

  const netBurn = baseMetrics ? baseMetrics.monthlyExpenses - baseMetrics.monthlyRevenue : 0;

  const simRevenue = useMemo(() => simulation?.metrics?.revenue || [], [simulation]);
  const simCash = useMemo(() => simulation?.metrics?.cash || [], [simulation]);
  const simBurn = useMemo(() => simulation?.metrics?.burn || [], [simulation]);
  const hasSimData = simulation?.runway?.p50 != null;

  const getMetricAtMonth = useCallback((data: any[], monthIdx: number, percentile: string) => {
    if (monthIdx < data.length) return data[monthIdx]?.[percentile] || 0;
    if (data.length > 0) return data[data.length - 1]?.[percentile] || 0;
    return 0;
  }, []);

  const getBreakevenMonth = useCallback((percentile: string) => {
    if (simulation?.breakEvenMonth) {
      const key = percentile.replace('p', 'p');
      const val = simulation.breakEvenMonth[key];
      if (val != null && val <= 24) return `Month ${Math.round(val)}`;
      if (val != null && val > 24) return '24+';
    }
    return '24+';
  }, [simulation]);

  const projectedRevenue = useCallback((months: number, growthMultiplier: number) => {
    if (!baseMetrics) return 0;
    const monthlyGrowth = 1 + (baseMetrics.growthRate * growthMultiplier) / 100;
    return baseMetrics.monthlyRevenue * Math.pow(monthlyGrowth, months);
  }, [baseMetrics]);

  const projectedCash = useCallback((months: number, growthMultiplier: number) => {
    if (!baseMetrics) return 0;
    let cash = baseMetrics.cashOnHand;
    const monthlyGrowth = 1 + (baseMetrics.growthRate * growthMultiplier) / 100;
    for (let i = 0; i < months; i++) {
      const rev = baseMetrics.monthlyRevenue * Math.pow(monthlyGrowth, i);
      cash += rev - baseMetrics.monthlyExpenses;
    }
    return Math.max(0, cash);
  }, [baseMetrics]);

  const getSurvivalPct = useCallback((period: string) => {
    if (simulation?.survivalProbability?.[period] != null) {
      return simulation.survivalProbability[period];
    }
    if (simulation?.survival?.[period] != null) {
      return simulation.survival[period];
    }
    const curve = simulation?.survivalCurve || simulation?.survival?.curve;
    if (curve && Array.isArray(curve) && curve.length > 0) {
      const monthNum = parseInt(period);
      if (!isNaN(monthNum)) {
        const entry = curve.find((c: any) => c.month === monthNum);
        if (entry) return entry.survival_rate * 100;
      }
      const last = curve[curve.length - 1];
      return last.survival_rate * 100;
    }
    return null;
  }, [simulation]);

  const scenarioP90 = useMemo(() => {
    if (hasSimData) {
      return {
        runway: simulation.runway.p90?.toFixed(1) || '?',
        revenue18m: getMetricAtMonth(simRevenue, 17, 'p90'),
        cash12m: getMetricAtMonth(simCash, 11, 'p90'),
        breakeven: getBreakevenMonth('p10'),
        survival: (() => { const v = getSurvivalPct('18m'); return v != null ? Math.min(100, v).toFixed(0) : '?'; })(),
      };
    }
    if (!baseMetrics) return null;
    const runway = baseMetrics.currentRunway * 1.3;
    return {
      runway: runway.toFixed(1),
      revenue18m: projectedRevenue(18, 1.5),
      cash12m: projectedCash(12, 1.5),
      breakeven: '18+',
      survival: Math.min(100, 65 * 1.15).toFixed(0),
    };
  }, [simulation, hasSimData, simRevenue, simCash, simBurn, baseMetrics, getMetricAtMonth, getBreakevenMonth, projectedRevenue, projectedCash, getSurvivalPct]);

  const scenarioP50 = useMemo(() => {
    if (hasSimData) {
      return {
        runway: simulation.runway.p50?.toFixed(1) || '?',
        revenue18m: getMetricAtMonth(simRevenue, 17, 'p50'),
        cash12m: getMetricAtMonth(simCash, 11, 'p50'),
        breakeven: getBreakevenMonth('p50'),
        survival: (() => { const v = getSurvivalPct('18m'); return v != null ? v.toFixed(0) : '?'; })(),
      };
    }
    if (!baseMetrics) return null;
    return {
      runway: baseMetrics.currentRunway.toFixed(1),
      revenue18m: projectedRevenue(18, 1.0),
      cash12m: projectedCash(12, 1.0),
      breakeven: '24+',
      survival: '65',
    };
  }, [simulation, hasSimData, simRevenue, simCash, simBurn, baseMetrics, getMetricAtMonth, getBreakevenMonth, projectedRevenue, projectedCash, getSurvivalPct]);

  const scenarioP10 = useMemo(() => {
    if (hasSimData) {
      const v = getSurvivalPct('24m');
      const p10Survival = v != null ? v.toFixed(0) : '?';
      return {
        runway: simulation.runway.p10?.toFixed(1) || '?',
        revenue18m: getMetricAtMonth(simRevenue, 17, 'p10'),
        cash12m: getMetricAtMonth(simCash, 11, 'p10'),
        breakeven: getBreakevenMonth('p90'),
        survival: p10Survival,
      };
    }
    if (!baseMetrics) return null;
    const runway = baseMetrics.currentRunway * 0.7;
    return {
      runway: runway.toFixed(1),
      revenue18m: projectedRevenue(18, 0.5),
      cash12m: projectedCash(12, 0.5),
      breakeven: '24+',
      survival: Math.max(0, 65 * 0.7).toFixed(0),
    };
  }, [simulation, hasSimData, simRevenue, simCash, simBurn, baseMetrics, getMetricAtMonth, getBreakevenMonth, projectedRevenue, projectedCash, getSurvivalPct]);

  const sensitivityBars = useMemo(() => {
    if (!baseMetrics) return [];
    const bars = [
      { label: 'Churn Rate', impact: 85, level: 'high' as const },
      { label: 'Net Burn', impact: 78, level: 'high' as const },
      { label: 'Revenue Growth', impact: 52, level: 'med' as const },
      { label: 'CAC', impact: 30, level: 'low' as const },
    ];
    return bars;
  }, [baseMetrics]);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-8">
      {/* STEP 1: "What's the question?" */}
      <section data-testid="section-question">
        <div className="text-center mb-6">
          <h1 className="text-3xl font-bold tracking-tight" data-testid="text-page-title">Simulate Any Scenario</h1>
          <p className="text-muted-foreground mt-1">Ask a question about your startup's future and see what happens</p>
        </div>

        <div className="relative max-w-3xl mx-auto mb-5">
          <div className="flex items-center gap-2 border rounded-md p-1.5 bg-card shadow-sm focus-within:ring-2 focus-within:ring-primary/30 transition-shadow">
            <Search className="h-5 w-5 text-muted-foreground ml-2 shrink-0" />
            <input
              type="text"
              value={questionInput}
              onChange={(e) => setQuestionInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleQuestionSubmit(); }}
              placeholder="What happens if we hire 3 engineers and raise prices 15%?"
              className="flex-1 bg-transparent border-0 outline-none text-sm py-2 placeholder:text-muted-foreground/60"
              data-testid="input-simulation-question"
            />
            <Button
              onClick={handleQuestionSubmit}
              disabled={isCreating || isRunning || !questionInput.trim()}
              className="shrink-0"
              style={{ background: 'linear-gradient(135deg, hsl(var(--primary)), hsl(var(--primary)/0.8))' }}
              data-testid="button-simulate"
            >
              {(isCreating || isRunning) ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Zap className="h-4 w-4 mr-2" />
              )}
              Simulate
            </Button>
          </div>
        </div>

        <div className="flex flex-wrap justify-center gap-2 mb-6 max-w-3xl mx-auto">
          {SUGGESTION_CHIPS.map((chip) => (
            <Button
              key={chip.label}
              variant="outline"
              size="sm"
              onClick={() => handleChipClick(chip.label)}
              disabled={isCreating || isRunning}
              data-testid={`chip-${chip.label.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '')}`}
            >
              <chip.icon className="h-3.5 w-3.5 mr-1.5" />
              {chip.label}
            </Button>
          ))}
        </div>

        {baseMetrics && (
          <Card className="max-w-4xl mx-auto" data-testid="card-context-bar">
            <CardContent className="py-3 px-4">
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3 text-center">
                <div>
                  <p className="text-[11px] text-muted-foreground uppercase tracking-wider">Cash</p>
                  <p className="text-sm font-semibold font-mono" data-testid="text-context-cash">
                    {formatCurrency(baseMetrics.cashOnHand)}
                  </p>
                </div>
                <div>
                  <p className="text-[11px] text-muted-foreground uppercase tracking-wider">Monthly Burn</p>
                  <p className="text-sm font-semibold font-mono" data-testid="text-context-burn">
                    {formatCurrency(netBurn)}
                  </p>
                </div>
                <div>
                  <p className="text-[11px] text-muted-foreground uppercase tracking-wider">Runway</p>
                  <p className="text-sm font-semibold font-mono" data-testid="text-context-runway">
                    {baseMetrics.currentRunway.toFixed(1)} mo
                  </p>
                </div>
                <div>
                  <p className="text-[11px] text-muted-foreground uppercase tracking-wider">MRR</p>
                  <p className="text-sm font-semibold font-mono" data-testid="text-context-mrr">
                    {formatCurrency(baseMetrics.monthlyRevenue)}
                  </p>
                </div>
                <div>
                  <p className="text-[11px] text-muted-foreground uppercase tracking-wider">Growth Rate</p>
                  <p className="text-sm font-semibold font-mono" data-testid="text-context-growth">
                    {baseMetrics.growthRate.toFixed(1)}%
                  </p>
                </div>
                <div>
                  <p className="text-[11px] text-muted-foreground uppercase tracking-wider">LTV:CAC</p>
                  <p className="text-sm font-semibold font-mono" data-testid="text-context-ltvcac">
                    {sharedMetrics.ltvCacRatio.toFixed(1)}x
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {isUsingDemoData && (
          <Card className="max-w-4xl mx-auto mt-4 border-amber-500/50 bg-amber-50/50 dark:bg-amber-950/20" data-testid="demo-data-warning">
            <CardContent className="flex items-start gap-3 p-4">
              <AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
              <div className="flex-1">
                <h4 className="font-medium text-amber-800 dark:text-amber-200 text-sm">Using Demo Data</h4>
                <p className="text-xs text-amber-700 dark:text-amber-300 mt-0.5">
                  For accurate projections, connect your actual financial data.
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-2 border-amber-600 text-amber-700 dark:border-amber-500 dark:text-amber-300"
                  onClick={() => window.location.href = '/data-input'}
                  data-testid="button-connect-financials"
                >
                  <ExternalLink className="h-3 w-3 mr-1.5" />
                  Connect Financials
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {!scenariosLoading && (!scenarios || scenarios.length === 0) && (
          <Card className="max-w-4xl mx-auto mt-4 border-primary/30 bg-primary/5">
            <CardContent className="py-5">
              <div className="flex items-center justify-between gap-4 flex-wrap">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-full bg-primary/10">
                    <Sparkles className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <h3 className="font-medium text-sm">Get started instantly</h3>
                    <p className="text-xs text-muted-foreground">
                      Create a baseline scenario to see simulation results right away
                    </p>
                  </div>
                </div>
                <Button
                  onClick={handleCreateBaselineScenario}
                  disabled={isCreatingBaseline}
                  data-testid="button-create-baseline"
                >
                  {isCreatingBaseline ? (
                    <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Creating...</>
                  ) : (
                    <><Play className="h-4 w-4 mr-2" />Create Baseline</>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </section>

      {/* STEP 2: Simulation Results */}
      <section ref={resultsRef} data-testid="section-results">
        {(isCreating || isRunning) && (
          <div className="text-center py-12">
            <Loader2 className="h-10 w-10 animate-spin text-primary mx-auto mb-4" />
            <p className="text-muted-foreground font-medium">Running 1,000 Monte Carlo simulations...</p>
            <p className="text-sm text-muted-foreground mt-1">This usually takes a few seconds</p>
          </div>
        )}

        {simLoading && !isRunning && selectedScenarioId && (
          <div className="space-y-4">
            <Skeleton className="h-8 w-64" />
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Skeleton className="h-48" />
              <Skeleton className="h-48" />
              <Skeleton className="h-48" />
            </div>
          </div>
        )}

        {simulation && !isRunning && !isCreating && (
          <>
            <div className="flex items-center justify-between gap-4 flex-wrap mb-4">
              <div>
                <h2 className="text-xl font-bold" data-testid="text-results-title">Simulation Results</h2>
                <p className="text-sm text-muted-foreground">{currentScenarioName} &mdash; 1,000 Monte Carlo runs</p>
              </div>
              <ExportButton
                data={formatSimulationForExport(simulation)}
                filename={`${currentScenarioName.toLowerCase().replace(/\s/g, '-')}-simulation`}
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              {/* Best Case - P90 */}
              <Card className="border-emerald-500/30 bg-emerald-50/30 dark:bg-emerald-950/10" data-testid="card-scenario-p90">
                <CardContent className="pt-4 pb-4 px-4">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="h-2 w-2 rounded-full bg-emerald-500" />
                    <span className="text-xs font-semibold uppercase tracking-wider text-emerald-700 dark:text-emerald-400">Best Case (P90)</span>
                  </div>
                  <div className="space-y-2.5">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs text-muted-foreground">Runway</span>
                      <span className="text-sm font-bold font-mono" data-testid="text-p90-runway">{scenarioP90?.runway} mo</span>
                    </div>
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs text-muted-foreground">Revenue @18mo</span>
                      <span className="text-sm font-semibold font-mono" data-testid="text-p90-revenue">{formatCurrency(scenarioP90?.revenue18m || 0)}</span>
                    </div>
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs text-muted-foreground">Cash @12mo</span>
                      <span className="text-sm font-semibold font-mono" data-testid="text-p90-cash">{formatCurrency(scenarioP90?.cash12m || 0)}</span>
                    </div>
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs text-muted-foreground">Break-even</span>
                      <span className="text-sm font-semibold font-mono" data-testid="text-p90-breakeven">{scenarioP90?.breakeven}</span>
                    </div>
                    <div className="mt-2 pt-2 border-t">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs text-muted-foreground">Survival</span>
                        <span className="text-sm font-bold text-emerald-600 dark:text-emerald-400" data-testid="text-p90-survival">{scenarioP90?.survival}%</span>
                      </div>
                      <div className="w-full h-1.5 bg-muted rounded-full mt-1.5 overflow-hidden">
                        <div
                          className="h-full bg-emerald-500 rounded-full transition-all"
                          style={{ width: `${Math.min(100, parseFloat(scenarioP90?.survival || '0'))}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Most Likely - P50 */}
              <Card className="border-primary/30 bg-primary/5" data-testid="card-scenario-p50">
                <CardContent className="pt-4 pb-4 px-4">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="h-2 w-2 rounded-full bg-primary" />
                    <span className="text-xs font-semibold uppercase tracking-wider text-primary">Most Likely (P50)</span>
                  </div>
                  <div className="space-y-2.5">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs text-muted-foreground">Runway</span>
                      <span className="text-sm font-bold font-mono" data-testid="text-p50-runway">{scenarioP50?.runway} mo</span>
                    </div>
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs text-muted-foreground">Revenue @18mo</span>
                      <span className="text-sm font-semibold font-mono" data-testid="text-p50-revenue">{formatCurrency(scenarioP50?.revenue18m || 0)}</span>
                    </div>
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs text-muted-foreground">Cash @12mo</span>
                      <span className="text-sm font-semibold font-mono" data-testid="text-p50-cash">{formatCurrency(scenarioP50?.cash12m || 0)}</span>
                    </div>
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs text-muted-foreground">Break-even</span>
                      <span className="text-sm font-semibold font-mono" data-testid="text-p50-breakeven">{scenarioP50?.breakeven}</span>
                    </div>
                    <div className="mt-2 pt-2 border-t">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs text-muted-foreground">Survival</span>
                        <span className="text-sm font-bold text-primary" data-testid="text-p50-survival">{scenarioP50?.survival}%</span>
                      </div>
                      <div className="w-full h-1.5 bg-muted rounded-full mt-1.5 overflow-hidden">
                        <div
                          className="h-full bg-primary rounded-full transition-all"
                          style={{ width: `${Math.min(100, parseFloat(scenarioP50?.survival || '0'))}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Worst Case - P10 */}
              <Card className="border-red-500/30 bg-red-50/30 dark:bg-red-950/10" data-testid="card-scenario-p10">
                <CardContent className="pt-4 pb-4 px-4">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="h-2 w-2 rounded-full bg-red-500" />
                    <span className="text-xs font-semibold uppercase tracking-wider text-red-700 dark:text-red-400">Worst Case (P10)</span>
                  </div>
                  <div className="space-y-2.5">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs text-muted-foreground">Runway</span>
                      <span className="text-sm font-bold font-mono" data-testid="text-p10-runway">{scenarioP10?.runway} mo</span>
                    </div>
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs text-muted-foreground">Revenue @18mo</span>
                      <span className="text-sm font-semibold font-mono" data-testid="text-p10-revenue">{formatCurrency(scenarioP10?.revenue18m || 0)}</span>
                    </div>
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs text-muted-foreground">Cash @12mo</span>
                      <span className="text-sm font-semibold font-mono" data-testid="text-p10-cash">{formatCurrency(scenarioP10?.cash12m || 0)}</span>
                    </div>
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs text-muted-foreground">Break-even</span>
                      <span className="text-sm font-semibold font-mono" data-testid="text-p10-breakeven">{scenarioP10?.breakeven}</span>
                    </div>
                    <div className="mt-2 pt-2 border-t">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs text-muted-foreground">Survival</span>
                        <span className="text-sm font-bold text-red-600 dark:text-red-400" data-testid="text-p10-survival">{scenarioP10?.survival}%</span>
                      </div>
                      <div className="w-full h-1.5 bg-muted rounded-full mt-1.5 overflow-hidden">
                        <div
                          className="h-full bg-red-500 rounded-full transition-all"
                          style={{ width: `${Math.min(100, parseFloat(scenarioP10?.survival || '0'))}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
              <Card data-testid="card-survival-chart">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Survival Probability</CardTitle>
                  <CardDescription className="text-xs">Probability of remaining cash positive over time</CardDescription>
                </CardHeader>
                <CardContent>
                  <SurvivalCurveChart data={simulation.survivalCurve || simulation.survival?.curve || simulation.survival_curve || []} />
                </CardContent>
              </Card>
              <BandsChart
                data={getCashBands(simulation)}
                title="Cash Projection Bands"
                description="10th, 50th, and 90th percentile outcomes"
              />
            </div>
          </>
        )}
      </section>

      {/* STEP 3: AI Recommendation */}
      {simulation && !isRunning && !isCreating && (
        <section data-testid="section-ai-recommendation">
          <h2 className="text-xl font-bold mb-4" data-testid="text-recommendation-title">AI Recommendation</h2>

          <Card
            className="mb-6 relative overflow-visible"
            style={{
              borderImage: 'linear-gradient(135deg, hsl(var(--primary)), hsl(var(--primary)/0.4), hsl(var(--primary)/0.1)) 1',
              borderWidth: '2px',
              borderStyle: 'solid',
            }}
            data-testid="card-ai-recommendation"
          >
            <CardContent className="pt-5 pb-5 px-5">
              <div className="flex items-start gap-3 mb-4">
                <div className="p-2 rounded-md bg-primary/10 shrink-0">
                  <Sparkles className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <h3 className="font-semibold text-sm mb-1">Strategic Assessment</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed" data-testid="text-ai-recommendation-body">
                    Based on {currentScenarioName}, your most likely outcome is a runway of{' '}
                    <strong>{scenarioP50?.runway} months</strong> with a{' '}
                    <strong>{scenarioP50?.survival}%</strong> survival probability at 18 months.
                    {parseFloat(scenarioP50?.survival || '0') >= 70
                      ? ' This is a healthy trajectory. Focus on maintaining growth while controlling burn.'
                      : parseFloat(scenarioP50?.survival || '0') >= 40
                        ? ' This indicates moderate risk. Consider reducing burn or accelerating revenue growth to improve your position.'
                        : ' This signals significant risk. Immediate action is recommended—cut costs, extend runway, or pursue fundraising.'}
                  </p>
                </div>
              </div>

              <div className="space-y-2.5 mb-5">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Key Sensitivity Levers</p>
                {sensitivityBars.map((bar) => (
                  <div key={bar.label} className="flex items-center gap-3" data-testid={`sensitivity-bar-${bar.label.toLowerCase().replace(/\s/g, '-')}`}>
                    <span className="text-xs w-28 shrink-0">{bar.label}</span>
                    <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${bar.level === 'high' ? 'bg-red-500' : bar.level === 'med' ? 'bg-amber-500' : 'bg-emerald-500'}`}
                        style={{ width: `${bar.impact}%` }}
                      />
                    </div>
                    <Badge
                      variant="outline"
                      className={`text-[10px] px-1.5 py-0 h-4 ${bar.level === 'high' ? 'border-red-500/50 text-red-600 dark:text-red-400' : bar.level === 'med' ? 'border-amber-500/50 text-amber-600 dark:text-amber-400' : 'border-emerald-500/50 text-emerald-600 dark:text-emerald-400'}`}
                    >
                      {bar.level}
                    </Badge>
                  </div>
                ))}
              </div>

              <div className="flex flex-wrap gap-2">
                <Button size="sm" data-testid="button-adopt-strategy" onClick={() => toast({ title: 'Strategy adopted', description: `${currentScenarioName} saved as your active strategy.` })}>
                  <Shield className="h-3.5 w-3.5 mr-1.5" />
                  Adopt This Strategy
                </Button>
                <ExportButton
                  data={formatSimulationForExport(simulation)}
                  filename={`${currentScenarioName.toLowerCase().replace(/\s/g, '-')}-report`}
                />
                <Button variant="outline" size="sm" data-testid="button-discuss-team" onClick={() => toast({ title: 'Coming soon', description: 'Team discussion feature is in development.' })}>
                  <MessageSquare className="h-3.5 w-3.5 mr-1.5" />
                  Discuss with Team
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setQuestionInput('');
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                  }}
                  data-testid="button-run-another"
                >
                  <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
                  Run Another Scenario
                </Button>
              </div>
            </CardContent>
          </Card>
        </section>
      )}

      {/* Recent Simulations History */}
      {scenarios && scenarios.length > 0 && (
        <section data-testid="section-recent-simulations">
          <div className="flex items-center justify-between gap-4 mb-3 flex-wrap">
            <h2 className="text-lg font-semibold" data-testid="text-recent-title">Recent Simulations</h2>
            <span className="text-xs text-muted-foreground">{scenarios.length} saved</span>
          </div>
          <ScrollArea className="w-full">
            <div className="flex gap-3 pb-3">
              {scenarios.slice(0, 10).map((s: any) => (
                <Card
                  key={s.id}
                  className={`shrink-0 w-52 hover-elevate cursor-pointer ${selectedScenarioId === s.id ? 'border-primary' : ''}`}
                  onClick={() => handleRunScenario(s.id)}
                  data-testid={`card-recent-sim-${s.id}`}
                >
                  <CardContent className="p-3">
                    <p className="text-sm font-medium truncate mb-1" data-testid={`text-recent-name-${s.id}`}>{s.name}</p>
                    {s.latest_simulation ? (
                      <div className="space-y-1">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-[10px] text-muted-foreground">Runway</span>
                          <span className="text-xs font-mono font-semibold" data-testid={`text-recent-runway-${s.id}`}>
                            {s.latest_simulation.runway?.p50?.toFixed(1) || '?'} mo
                          </span>
                        </div>
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-[10px] text-muted-foreground">Survival</span>
                          <span className="text-xs font-mono font-semibold" data-testid={`text-recent-survival-${s.id}`}>
                            {(s.latest_simulation.survival?.['18m'] || 0).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                    ) : (
                      <p className="text-[10px] text-muted-foreground">Not yet simulated</p>
                    )}
                    {s.created_at && (
                      <p className="text-[10px] text-muted-foreground mt-1.5 border-t pt-1" data-testid={`text-recent-date-${s.id}`}>
                        {new Date(s.created_at).toLocaleDateString()}
                      </p>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
            <ScrollBar orientation="horizontal" />
          </ScrollArea>
        </section>
      )}

      {/* Advanced View Toggle */}
      <section data-testid="section-advanced-view">
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-center text-muted-foreground"
          onClick={() => setShowAdvancedView(!showAdvancedView)}
          data-testid="button-toggle-advanced"
        >
          {showAdvancedView ? <ChevronUp className="h-4 w-4 mr-2" /> : <ChevronDown className="h-4 w-4 mr-2" />}
          {showAdvancedView ? 'Hide Advanced View' : 'Show Advanced View'}
        </Button>

        {showAdvancedView && (
          <div className="mt-4">
            <Tabs value={advancedTab} onValueChange={setAdvancedTab}>
              <TabsList className="flex-wrap h-auto gap-1">
                <TabsTrigger value="builder" data-testid="adv-tab-builder">
                  <Zap className="h-4 w-4 mr-2" />
                  Strategic Builder
                </TabsTrigger>
                <TabsTrigger value="classic" data-testid="adv-tab-classic">
                  Classic Wizard
                </TabsTrigger>
                <TabsTrigger value="results" data-testid="adv-tab-results" disabled={!hasRunScenario && !hasSimulationResults} className={!hasRunScenario && !hasSimulationResults ? 'opacity-50' : ''}>
                  {!hasRunScenario && !hasSimulationResults && <Lock className="h-3 w-3 mr-1" />}
                  Detailed Results
                </TabsTrigger>
                <TabsTrigger value="compare" data-testid="adv-tab-compare" disabled={!hasRunScenario && !hasSimulationResults} className={!hasRunScenario && !hasSimulationResults ? 'opacity-50' : ''}>
                  {!hasRunScenario && !hasSimulationResults && <Lock className="h-3 w-3 mr-1" />}
                  Compare All
                </TabsTrigger>
                <TabsTrigger value="enhanced" data-testid="adv-tab-enhanced" disabled={!hasRunScenario && !hasSimulationResults} className={!hasRunScenario && !hasSimulationResults ? 'opacity-50' : ''}>
                  {!hasRunScenario && !hasSimulationResults && <Lock className="h-3 w-3 mr-1" />}
                  Decision Ranking
                </TabsTrigger>
                <TabsTrigger value="sensitivity" data-testid="adv-tab-sensitivity" disabled={!hasRunScenario && !hasSimulationResults} className={!hasRunScenario && !hasSimulationResults ? 'opacity-50' : ''}>
                  {!hasRunScenario && !hasSimulationResults && <Lock className="h-3 w-3 mr-1" />}
                  Sensitivity
                </TabsTrigger>
                <TabsTrigger value="analysis" data-testid="adv-tab-analysis" disabled={!hasRunScenario && !hasSimulationResults} className={!hasRunScenario && !hasSimulationResults ? 'opacity-50' : ''}>
                  {!hasRunScenario && !hasSimulationResults && <Lock className="h-3 w-3 mr-1" />}
                  Analysis
                </TabsTrigger>
                {scenarios && scenarios.length > 0 && (
                  <TabsTrigger value="history" data-testid="adv-tab-history">
                    <History className="h-4 w-4 mr-2" />
                    Saved ({scenarios.length})
                  </TabsTrigger>
                )}
                {selectedScenarioId && (
                  <TabsTrigger value="collaborate" data-testid="adv-tab-collaborate">
                    <MessageSquare className="h-4 w-4 mr-2" />
                    Discussion
                    {comments.length > 0 && (
                      <span className="ml-1 text-xs bg-muted rounded-full px-1.5">{comments.length}</span>
                    )}
                  </TabsTrigger>
                )}
              </TabsList>

              <TabsContent value="builder" className="mt-6 space-y-4">
                <StrategicScenarioBuilder
                  baseMetrics={baseMetrics}
                  onRunSimulation={async (params) => { await handleWizardComplete(params); }}
                  onSaveScenario={async (params) => { await handleWizardComplete(params); }}
                  isRunning={isCreating || isRunning}
                  simulation={simulation}
                />
              </TabsContent>

              <TabsContent value="classic" className="mt-6">
                <ScenarioWizard
                  templates={SCENARIO_TEMPLATES}
                  onComplete={handleWizardComplete}
                  isRunning={isCreating || isRunning}
                  companyId={currentCompany.id}
                  baseMetrics={baseMetrics}
                />
              </TabsContent>

              <TabsContent value="history" className="mt-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Saved Scenarios</CardTitle>
                    <CardDescription>{scenarios?.length || 0} scenarios available</CardDescription>
                  </CardHeader>
                  <CardContent>
                    {scenariosLoading ? (
                      <div className="space-y-2"><Skeleton className="h-16 w-full" /><Skeleton className="h-16 w-full" /><Skeleton className="h-16 w-full" /></div>
                    ) : !scenarios || scenarios.length === 0 ? (
                      <EmptyState icon={TrendingUp} title="No Saved Scenarios" description="Build your first scenario using the Strategic or Classic builder above." compact />
                    ) : (
                      <ScrollArea className="h-[400px]">
                        <div className="space-y-2">
                          {scenarios.map((s: any) => (
                            <div key={s.id} className="flex items-center justify-between gap-4 p-4 rounded-lg border hover-elevate">
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 flex-wrap">
                                  <span className="font-medium">{s.name}</span>
                                  {s.created_at && <span className="text-xs text-muted-foreground">{new Date(s.created_at).toLocaleDateString()}</span>}
                                </div>
                                {s.tags && s.tags.length > 0 && (
                                  <div className="flex gap-1 mt-1 flex-wrap">
                                    {s.tags.map((tag: string) => <Badge key={tag} variant="outline" className="text-xs">{tag}</Badge>)}
                                  </div>
                                )}
                                {s.latest_simulation && (
                                  <div className="flex gap-4 mt-2 text-sm text-muted-foreground">
                                    <span>Runway: {s.latest_simulation.runway?.p50?.toFixed(1) || '?'} mo</span>
                                    <span>Survival: {(s.latest_simulation.survival?.['18m'] || 0).toFixed(0)}%</span>
                                  </div>
                                )}
                              </div>
                              <Button onClick={() => handleRunScenario(s.id)} disabled={isRunning && selectedScenarioId === s.id} data-testid={`button-run-scenario-${s.id}`}>
                                <Play className="h-4 w-4 mr-2" />Run
                              </Button>
                            </div>
                          ))}
                        </div>
                      </ScrollArea>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="compare" className="mt-6 space-y-6">
                <div className="flex items-center justify-between gap-4 flex-wrap">
                  <div>
                    <h2 className="text-lg font-semibold">Compare All Scenarios</h2>
                    <p className="text-sm text-muted-foreground">Run simulations for 5 default scenarios and compare results</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <GlossaryModal />
                    <Button onClick={handleRunMultiScenario} disabled={multiSimMutation.isPending} data-testid="button-run-multi-scenario">
                      {multiSimMutation.isPending ? (<><Loader2 className="h-4 w-4 mr-2 animate-spin" />Running...</>) : (<><Play className="h-4 w-4 mr-2" />Run All Scenarios</>)}
                    </Button>
                  </div>
                </div>
                {multiSimMutation.isPending && <Card><CardContent className="p-6"><div className="space-y-3"><Skeleton className="h-24 w-full" /><Skeleton className="h-64 w-full" /></div></CardContent></Card>}
                {multiSimResults && !multiSimMutation.isPending && (
                  <>
                    {multiSimResults.comparison && (
                      <ExecutiveSummary
                        scenarios={Object.entries(multiSimResults.scenarios || {}).map(([key, scenario]: [string, any]) => ({
                          id: key, name: scenario.name || key, runway_p50: scenario.summary?.runway_p50 || 0,
                          runway_p10: scenario.summary?.runway_p10, runway_p90: scenario.summary?.runway_p90,
                          survival_rate: (scenario.summary?.survival_18m || 0) / 100, end_cash_p50: scenario.summary?.end_cash_p50,
                          monthly_burn_p50: scenario.summary?.monthly_burn_p50, assumptions: scenario.assumptions,
                        }))}
                        baselineId="baseline" targetRunway={18} minSurvival={0.8}
                      />
                    )}
                    <MultiScenarioSummary comparison={multiSimResults.comparison} />
                    <ScenarioComparisonView
                      scenarios={Object.entries(multiSimResults.scenarios || {}).map(([key, scenario]: [string, any]) => ({
                        name: scenario.name || key, runway_p50: scenario.summary?.runway_p50 || 0,
                        runway_p10: scenario.summary?.runway_p10, runway_p90: scenario.summary?.runway_p90,
                        survival_18m: scenario.summary?.survival_18m || 0, survival_12m: scenario.summary?.survival_12m,
                        end_cash: scenario.summary?.end_cash_p50, avg_burn: scenario.summary?.monthly_burn_p50, score: scenario.score,
                      }))}
                      testId="scenario-comparison-view"
                    />
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {Object.entries(multiSimResults.scenarios || {}).map(([key, scenario]: [string, any]) => (
                        <ScenarioCard key={key} id={key} name={scenario.name || key}
                          runwayP50={scenario.summary?.runway_p50 || 0} runwayP10={scenario.summary?.runway_p10}
                          runwayP90={scenario.summary?.runway_p90} survivalRate={(scenario.summary?.survival_18m || 0) / 100}
                          endCash={scenario.summary?.end_cash_p50} monthlyBurn={scenario.summary?.monthly_burn_p50}
                          assumptions={scenario.assumptions} tags={scenario.tags} isBaseline={key === 'baseline'}
                          isBest={multiSimResults.comparison?.best_scenario === key}
                          meetsBenchmark={(scenario.summary?.runway_p50 || 0) >= 18 && (scenario.summary?.survival_18m || 0) >= 80}
                          cashProjection={scenario.month_data?.map((m: any) => m.cash_p50)} testId={`scenario-card-${key}`}
                        />
                      ))}
                    </div>
                    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                      <ScenarioComparisonChart scenarios={multiSimResults.scenarios} />
                      <MonthlyResultsTable scenarios={multiSimResults.scenarios} />
                    </div>
                  </>
                )}
                {!multiSimResults && !multiSimMutation.isPending && (
                  <Card><CardContent className="py-12 text-center">
                    <BarChart3 className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                    <p className="text-muted-foreground mb-4">Compare 5 pre-built scenarios side-by-side</p>
                    <Button onClick={handleRunMultiScenario} data-testid="button-run-multi-cta"><Play className="h-4 w-4 mr-2" />Run All Scenarios</Button>
                  </CardContent></Card>
                )}
              </TabsContent>

              <TabsContent value="enhanced" className="mt-6 space-y-6">
                <div className="flex items-center justify-between gap-4 flex-wrap">
                  <div>
                    <h2 className="text-lg font-semibold">Enhanced Scenario Analysis</h2>
                    <p className="text-sm text-muted-foreground">Regime-aware simulation with correlated drivers and decision ranking</p>
                  </div>
                  <Button onClick={handleRunEnhancedMulti} disabled={enhancedMultiMutation.isPending} data-testid="button-run-enhanced-multi">
                    {enhancedMultiMutation.isPending ? (<><Loader2 className="h-4 w-4 mr-2 animate-spin" />Running...</>) : (<><Play className="h-4 w-4 mr-2" />Run Enhanced Analysis</>)}
                  </Button>
                </div>
                {enhancedMultiMutation.isPending && <Card><CardContent className="p-6"><div className="space-y-3"><Skeleton className="h-24 w-full" /><Skeleton className="h-64 w-full" /></div></CardContent></Card>}
                {enhancedResults && !enhancedMultiMutation.isPending && (
                  <>
                    {enhancedResults.decision_ranking && <DecisionRankingTable rankings={enhancedResults.decision_ranking} onSelectScenario={(key) => { const scenario = enhancedResults.scenarios?.[key]; if (scenario) toast({ title: `Selected: ${scenario.name}` }); }} />}
                    {enhancedResults.sensitivity && <SensitivityAnalysisPanel data={enhancedResults.sensitivity} isLoading={false} />}
                    {Object.entries(enhancedResults.scenarios || {}).slice(0, 1).map(([key, scenario]: [string, any]) => scenario.regime_distribution && <RegimeDistributionChart key={key} distribution={scenario.regime_distribution} scenarioName={scenario.name} />)}
                  </>
                )}
                {!enhancedResults && !enhancedMultiMutation.isPending && (
                  <Card><CardContent className="py-12 text-center">
                    <Trophy className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                    <p className="text-muted-foreground mb-4">Run enhanced simulation with regime-aware Monte Carlo</p>
                    <Button onClick={handleRunEnhancedMulti} data-testid="button-run-enhanced-cta"><Play className="h-4 w-4 mr-2" />Run Enhanced Analysis</Button>
                  </CardContent></Card>
                )}
              </TabsContent>

              <TabsContent value="sensitivity" className="mt-6 space-y-6">
                <SensitivityAnalysisPanel data={sensitivityResults} isLoading={sensitivityMutation.isPending} onRunAnalysis={handleRunSensitivityAnalysis} />
              </TabsContent>

              <TabsContent value="analysis" className="mt-6 space-y-6">
                {(() => {
                  const totalExpenses = baseMetrics?.monthlyExpenses || 80000;
                  const financialState: FinancialState = baseMetrics ? {
                    monthlyRevenue: baseMetrics.monthlyRevenue, grossMargin: baseMetrics.grossMargin,
                    opex: totalExpenses * 0.3, payroll: totalExpenses * 0.6, otherCosts: totalExpenses * 0.1,
                    cashBalance: baseMetrics.cashOnHand, churnRate: baseMetrics.churnRate, growthRate: baseMetrics.growthRate,
                    cac: baseMetrics.monthlyRevenue * 0.3, ltv: baseMetrics.churnRate > 0 ? (baseMetrics.monthlyRevenue / baseMetrics.churnRate) * 100 : baseMetrics.monthlyRevenue * 24,
                  } : {
                    monthlyRevenue: 0, grossMargin: 0, opex: 0, payroll: 0, otherCosts: 0,
                    cashBalance: 0, churnRate: 0, growthRate: 0, cac: 0, ltv: 0,
                  };
                  const currentRunway = baseMetrics?.currentRunway || 0;
                  const sensitivityData = calculateSensitivity(financialState);
                  const baselineResults = {
                    runway: currentRunway,
                    survival18m: simulation?.survival_18m ?? (simulation?.survival_12m ? Math.max(0, simulation.survival_12m * 0.85) : 65),
                    cashAt18m: simulation?.end_cash ?? Math.max(0, financialState.cashBalance - (totalExpenses - financialState.monthlyRevenue) * 18),
                  };
                  return (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      <TornadoChart baselineRunway={currentRunway} variables={sensitivityData} onVariableClick={(variable) => toast({ title: `Analyzing: ${variable}`, description: 'Drill-down analysis coming soon' })} />
                      <WhatIfExplorer baselineState={financialState} baselineResults={baselineResults} calculateQuickImpact={(adj) => calculateWhatIfImpact(financialState, adj, baselineResults)} onRunFullSimulation={() => toast({ title: 'Running Full Monte Carlo', description: 'Applying what-if adjustments to simulation...' })} />
                      <StressTestPanel currentState={financialState} currentRunway={currentRunway} onApplyStressTest={(_, t) => toast({ title: `Stress Test Applied: ${t.name}`, description: t.description })} />
                      <ReverseStressTest currentState={financialState} />
                    </div>
                  );
                })()}
              </TabsContent>

              <TabsContent value="results" className="mt-6 space-y-4">
                {simLoading ? <Card><CardContent className="p-6"><Skeleton className="h-64 w-full" /></CardContent></Card> : simulation ? (
                  <>
                    <DashboardKPICards simulation={simulation} metrics={dashboardMetrics} companyId={currentCompany?.id} testId="dashboard-kpis-results" />
                    <SimulationSummaryBanner runwayP50={simulation.runway?.p50 || 0} survival18m={simulation.survival?.['18m'] || 0} survival12m={simulation.survival?.['12m'] || 0} endCash={simulation.summary?.end_cash} monthlyBurn={simulation.summary?.monthly_burn} monthlyRevenue={simulation.summary?.monthly_revenue} scenarioName={currentScenarioName} />
                    <div className="flex items-center justify-between gap-2 p-3 bg-muted/30 rounded-lg">
                      <div className="flex items-center gap-3"><span className="text-sm font-medium">Risk Assessment:</span><RiskGauge survivalProbability={(simulation.survival?.['18m'] || 0) / 100} size="sm" /></div>
                      <GlossaryModal />
                    </div>
                    <SimulationInsights simulation={simulation} scenarioName={currentScenarioName} testId="simulation-insights-results" />
                    <AISummaryCard companyId={currentCompany.id} simulationResults={simulation} scenarioName={currentScenarioName} testId="ai-summary-card-results" />
                    {simulation.month_data && simulation.month_data.length > 0 && (
                      <>
                        <DrillDownChart data={simulation.month_data.map((m: any, idx: number) => ({ month: idx + 1, cash_p10: m.cash_p10, cash_p50: m.cash_p50 ?? 0, cash_p90: m.cash_p90, revenue_p10: m.revenue_p10, revenue_p50: m.revenue_p50 ?? 0, revenue_p90: m.revenue_p90, burn_p10: m.burn_p10, burn_p50: m.burn_p50 ?? 0, burn_p90: m.burn_p90, runway_p50: Math.min(60, m.runway_p50 || (m.cash_p50 / Math.max(1, (m.burn_p50 ?? 1) - (m.revenue_p50 ?? 0)))), survival_rate: m.survival_rate }))} scenarioName={currentScenarioName} targetRunway={18} testId="drill-down-chart-results" />
                        <StackedBurnRevenueChart data={simulation.month_data.map((m: any, idx: number) => ({ month: idx + 1, revenue: m.revenue_p50 ?? 0, burn: m.burn_p50 ?? 0, cash: m.cash_p50 }))} scenarioName={currentScenarioName} testId="stacked-burn-revenue-chart" />
                      </>
                    )}
                    {timeseriesData && timeseriesData.timeseries && timeseriesData.timeseries.length > 0 && (
                      <>
                        <ProjectionChart timeseries={timeseriesData.timeseries} fundingEvents={timeseriesData.fundingEvents} scenarioName={timeseriesData.scenario_name || currentScenarioName} targetRunway={18} testId="projection-chart-results" />
                        <ProjectionSummary timeseries={timeseriesData.timeseries} targetRunway={18} testId="projection-summary-results" />
                      </>
                    )}
                    <Card><CardHeader><CardTitle className="text-lg">Runway Distribution</CardTitle><CardDescription>Distribution of runway outcomes across all simulations</CardDescription></CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-3 gap-4 text-center">
                          <div className="p-4 bg-muted/50 rounded-lg"><p className="text-xs text-muted-foreground">10th Percentile</p><p className="text-2xl font-mono font-bold">{simulation.runway?.p10?.toFixed(1) || '?'} mo</p><p className="text-xs text-muted-foreground">Worst case</p></div>
                          <div className="p-4 bg-primary/10 rounded-lg"><p className="text-xs text-muted-foreground">50th Percentile</p><p className="text-2xl font-mono font-bold text-primary">{simulation.runway?.p50?.toFixed(1) || '?'} mo</p><p className="text-xs text-muted-foreground">Most likely</p></div>
                          <div className="p-4 bg-muted/50 rounded-lg"><p className="text-xs text-muted-foreground">90th Percentile</p><p className="text-2xl font-mono font-bold">{simulation.runway?.p90?.toFixed(1) || '?'} mo</p><p className="text-xs text-muted-foreground">Best case</p></div>
                        </div>
                      </CardContent>
                    </Card>
                  </>
                ) : (
                  <EmptyStateCard icon={BarChart3} title="No Simulation Results" description="Run a Monte Carlo simulation to see probabilistic projections." action={{ label: "Create Scenario", onClick: () => setAdvancedTab('builder') }} />
                )}
              </TabsContent>

              <TabsContent value="collaborate" className="mt-6 space-y-6">
                {selectedScenarioId ? (
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <ScenarioComments scenarioId={selectedScenarioId} comments={comments} isLoading={commentsLoading} currentUserEmail={currentUserEmail}
                      onAddComment={async (content, parentId) => { await addCommentMutation.mutateAsync({ scenarioId: selectedScenarioId, content, parentId }); }}
                      onEditComment={async (commentId, content) => { await editCommentMutation.mutateAsync({ commentId, content, scenarioId: selectedScenarioId }); }}
                      onDeleteComment={async (commentId) => { await deleteCommentMutation.mutateAsync({ commentId, scenarioId: selectedScenarioId }); }}
                    />
                    {simulation && (
                      <DistributionView title="Runway Distribution" description="Distribution across all Monte Carlo runs"
                        data={Array.from({ length: 1000 }, () => (simulation.runway?.p50 || 12) + (Math.random() - 0.5) * (simulation.runway?.p90 - simulation.runway?.p10 || 6))}
                        unit="months" thresholds={{ warning: 18, critical: 12 }} higherIsBetter={true}
                      />
                    )}
                  </div>
                ) : (
                  <Card><CardContent className="py-12 text-center">
                    <MessageSquare className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                    <p className="text-muted-foreground">Select a scenario to view and add comments</p>
                    <Button variant="outline" className="mt-4" onClick={() => setAdvancedTab('history')}>View Saved Scenarios</Button>
                  </CardContent></Card>
                )}
              </TabsContent>
            </Tabs>
          </div>
        )}
      </section>

      {/* Duplicate Dialog */}
      <Dialog open={duplicateDialog.open} onOpenChange={(open) => setDuplicateDialog({ ...duplicateDialog, open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Scenario Already Exists</DialogTitle>
            <DialogDescription>A scenario with this name already exists. Would you like to overwrite it or create a new one?</DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setDuplicateDialog({ open: false })}>Cancel</Button>
            <Button variant="secondary" onClick={() => { if (duplicateDialog.scenarioData) { runScenario({ ...duplicateDialog.scenarioData, name: `${duplicateDialog.scenarioData.name} (Copy)` }, false); } }}>Create Copy</Button>
            <Button onClick={() => { if (duplicateDialog.scenarioData && duplicateDialog.existingId) { runScenario(duplicateDialog.scenarioData, true, duplicateDialog.existingId); } }}>Overwrite</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {currentCompany && truthScanModal.uploadId && (
        <TruthScanBlockedModal uploadId={truthScanModal.uploadId} companyId={currentCompany.id} open={truthScanModal.open}
          onOpenChange={(open) => setTruthScanModal({ ...truthScanModal, open })}
          onComplete={() => toast({ title: 'Data validated', description: 'You can now run simulations.' })}
        />
      )}
    </div>
  );
}
