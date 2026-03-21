import { useState, useEffect, useRef, useCallback, lazy, Suspense } from 'react';
import { useSEO } from "@/lib/seo";
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiRequest } from '@/lib/queryClient';
import {
  FlaskConical, Zap, Shield, History, Target, Play, Activity, Clock, DollarSign,
  AlertTriangle, RefreshCw, TrendingUp, TrendingDown, Minus, Loader2, ShieldCheck
} from 'lucide-react';
import { useFounderStore } from '@/store/founderStore';
import { useFinancialMetrics } from '@/hooks/useFinancialMetrics';
import { useCounter } from '@/hooks/useCounter';
import '@/styles/simulation-animations.css';
import type { LucideIcon } from 'lucide-react';
import { SimGlassCard } from '@/components/ui/sim-glass-card';
import { SimStatusBadge } from '@/components/ui/sim-status-badge';
import { SimAnimatedCounter } from '@/components/ui/sim-animated-counter';
import { SimStepProgress } from '@/components/ui/sim-step-progress';
import { SimTerminalDrawer } from '@/components/ui/sim-terminal-drawer';
import { SimSkeleton } from '@/components/ui/sim-skeleton';
import { SimBackgroundOrbs } from '@/components/ui/sim-background-orbs';
import { SimEventCard } from '@/components/ui/sim-event-card';

interface AccuracyRecord {
  id: number;
  simulation_run_id: number | null;
  scenario_id: number | null;
  prediction_month: number;
  predicted_revenue: number | null;
  actual_revenue: number | null;
  predicted_burn: number | null;
  actual_burn: number | null;
  predicted_cash: number | null;
  actual_cash: number | null;
  predicted_churn: number | null;
  actual_churn: number | null;
  variance_pct: Record<string, number>;
  accuracy_score: number | null;
  computed_at: string | null;
}

interface TrendPoint {
  score: number;
  date: string | null;
}

interface AccuracySummary {
  total_comparisons: number;
  overall_accuracy: number | null;
  min_accuracy: number | null;
  max_accuracy: number | null;
  per_metric: Record<string, number | null>;
  trend: TrendPoint[];
}

interface AccuracyResponse {
  summary: AccuracySummary;
  history: AccuracyRecord[];
}

interface BiasDetail {
  bias_pct: number;
  confidence: string;
  applied_at: string | null;
}

interface BiasResponse {
  biases: Record<string, BiasDetail>;
}
import { useCurrency } from '@/hooks/useCurrency';
import { WhatIfExplorer, StressTestPanel, ReverseStressTest, TornadoChart } from '@/components/simulation';
import { calculateSensitivity, calculateRunway, calculateWhatIfImpact, type FinancialState } from '@/lib/simulation/sensitivityAnalysis';
import { useScenarios } from '@/api/hooks';
import { ActualVsSimulatedComparison, MultiMetricComparison } from '@/components/ActualVsSimulatedComparison';

const ScenariosPage = lazy(() => import('@/pages/scenarios'));

function WorkspaceLoading() {
  return (
    <div className="p-6 space-y-4">
      <Skeleton className="h-8 w-64" />
      <Skeleton className="h-4 w-96" />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
        <Skeleton className="h-40" />
        <Skeleton className="h-40" />
        <Skeleton className="h-40" />
      </div>
    </div>
  );
}

function buildFinancialState(metrics: any): FinancialState {
  const totalExpenses = metrics.totalMonthlyExpenses ?? metrics.burnRate ?? 0;
  return {
    cashBalance: metrics.cashOnHand ?? 0,
    monthlyRevenue: metrics.mrr ?? 0,
    monthlyBurn: metrics.burnRate ?? totalExpenses,
    growthRate: metrics.monthlyGrowthRate ?? 10,
    churnRate: metrics.churnRatePct ?? 5,
    grossMargin: metrics.grossMarginPct ?? 70,
    opex: totalExpenses * 0.3,
    payroll: totalExpenses * 0.5,
    otherCosts: totalExpenses * 0.2,
    cac: metrics.cac ?? 500,
    ltv: metrics.ltv ?? 5000,
  };
}

function PredictionAccuracySection({ companyId }: { companyId: number }) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data: accuracyData, isLoading } = useQuery<AccuracyResponse>({
    queryKey: ['/api/companies', companyId, 'simulation', 'accuracy'],
    enabled: !!companyId,
  });

  const { data: biasData } = useQuery<BiasResponse>({
    queryKey: ['/api/companies', companyId, 'simulation', 'biases'],
    enabled: !!companyId,
  });

  const computeMutation = useMutation({
    mutationFn: async () => {
      const res = await apiRequest('POST', `/api/companies/${companyId}/simulation/accuracy/compute`);
      return res.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['/api/companies', companyId, 'simulation', 'accuracy'] });
      toast({
        title: 'Accuracy Computed',
        description: `${data.records_created} comparison records created. Overall accuracy: ${data.overall_accuracy ?? 'N/A'}%`,
      });
    },
    onError: () => {
      toast({ title: 'Error', description: 'Failed to compute accuracy', variant: 'destructive' });
    },
  });

  const calibrateMutation = useMutation({
    mutationFn: async () => {
      const res = await apiRequest('POST', `/api/companies/${companyId}/simulation/calibrate`);
      return res.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['/api/companies', companyId, 'simulation', 'biases'] });
      const applied = data.calibration?.applied ?? 0;
      toast({
        title: applied > 0 ? 'Calibration Applied' : 'No Adjustments Needed',
        description: applied > 0
          ? `${applied} bias correction(s) applied to future simulations.`
          : 'Predictions are within acceptable range.',
      });
    },
    onError: () => {
      toast({ title: 'Error', description: 'Failed to run calibration', variant: 'destructive' });
    },
  });

  const summary = accuracyData?.summary;
  const biases = biasData?.biases;

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-6">
          <Skeleton className="h-6 w-48 mb-4" />
          <Skeleton className="h-32" />
        </CardContent>
      </Card>
    );
  }

  const overallAccuracy = summary?.overall_accuracy;
  const trend = summary?.trend ?? [];
  const perMetric = summary?.per_metric ?? {};

  return (
    <Card data-testid="card-prediction-accuracy">
      <CardHeader>
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <Target className="h-5 w-5" />
              Prediction Accuracy
            </CardTitle>
            <CardDescription>
              How well past simulations matched reality
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => computeMutation.mutate()}
              disabled={computeMutation.isPending}
              data-testid="button-compute-accuracy"
            >
              {computeMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <RefreshCw className="h-4 w-4 mr-1" />}
              Compute
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => calibrateMutation.mutate()}
              disabled={calibrateMutation.isPending}
              data-testid="button-auto-calibrate"
            >
              {calibrateMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Target className="h-4 w-4 mr-1" />}
              Auto-Calibrate
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-3 rounded-lg bg-muted/50">
            <div className="text-2xl font-bold" data-testid="text-overall-accuracy">
              {overallAccuracy != null ? `${overallAccuracy}%` : '—'}
            </div>
            <div className="text-xs text-muted-foreground">Overall Accuracy</div>
          </div>
          <div className="text-center p-3 rounded-lg bg-muted/50">
            <div className="text-2xl font-bold" data-testid="text-revenue-bias">
              {perMetric.revenue_bias_pct != null ? `${perMetric.revenue_bias_pct > 0 ? '+' : ''}${perMetric.revenue_bias_pct}%` : '—'}
            </div>
            <div className="text-xs text-muted-foreground">Revenue Bias</div>
          </div>
          <div className="text-center p-3 rounded-lg bg-muted/50">
            <div className="text-2xl font-bold" data-testid="text-burn-bias">
              {perMetric.burn_bias_pct != null ? `${perMetric.burn_bias_pct > 0 ? '+' : ''}${perMetric.burn_bias_pct}%` : '—'}
            </div>
            <div className="text-xs text-muted-foreground">Burn Bias</div>
          </div>
          <div className="text-center p-3 rounded-lg bg-muted/50">
            <div className="text-2xl font-bold" data-testid="text-cash-bias">
              {perMetric.cash_bias_pct != null ? `${perMetric.cash_bias_pct > 0 ? '+' : ''}${perMetric.cash_bias_pct}%` : '—'}
            </div>
            <div className="text-xs text-muted-foreground">Cash Bias</div>
          </div>
          <div className="text-center p-3 rounded-lg bg-muted/50">
            <div className="text-2xl font-bold" data-testid="text-churn-bias">
              {perMetric.churn_bias_pct != null ? `${perMetric.churn_bias_pct > 0 ? '+' : ''}${perMetric.churn_bias_pct}%` : '—'}
            </div>
            <div className="text-xs text-muted-foreground">Churn Bias</div>
          </div>
        </div>

        {trend.length > 0 && (
          <div>
            <h4 className="text-sm font-medium mb-2">Accuracy Trend</h4>
            <div className="flex items-end gap-1 h-16">
              {trend.map((t: TrendPoint, i: number) => (
                <div
                  key={i}
                  className="flex-1 rounded-t bg-primary/70 transition-all"
                  style={{ height: `${Math.max(4, (t.score / 100) * 100)}%` }}
                  title={`${t.score?.toFixed(0)}% - ${t.date ? new Date(t.date).toLocaleDateString() : ''}`}
                  data-testid={`bar-trend-${i}`}
                />
              ))}
            </div>
          </div>
        )}

        {biases && Object.keys(biases).length > 0 && (
          <div>
            <h4 className="text-sm font-medium mb-2">Active Calibration Biases</h4>
            <div className="space-y-2">
              {Object.entries(biases).map(([metric, data]) => (
                <div key={metric} className="flex items-center justify-between p-2 rounded bg-muted/30" data-testid={`bias-${metric}`}>
                  <span className="text-sm font-medium capitalize">{metric}</span>
                  <div className="flex items-center gap-2">
                    {data.bias_pct > 0 ? (
                      <TrendingUp className="h-3 w-3 text-green-500" />
                    ) : data.bias_pct < 0 ? (
                      <TrendingDown className="h-3 w-3 text-red-500" />
                    ) : (
                      <Minus className="h-3 w-3 text-muted-foreground" />
                    )}
                    <span className="text-sm font-mono">
                      {data.bias_pct > 0 ? '+' : ''}{data.bias_pct?.toFixed(1)}%
                    </span>
                    <Badge variant="outline" className="text-[10px]">{data.confidence}</Badge>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {summary?.total_comparisons === 0 && (
          <div className="text-center py-4 text-muted-foreground text-sm">
            No accuracy data yet. Click "Compute" to compare past predictions against actual results.
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function StressTestWorkspace() {
  const currentCompany = useFounderStore((s) => s.currentCompany);
  const { metrics: baseMetrics } = useFinancialMetrics();
  const { toast } = useToast();

  if (!currentCompany || !baseMetrics?.hasData) {
    return (
      <div className="text-center py-16">
        <Shield className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
        <h3 className="text-lg font-semibold mb-2">Stress Testing</h3>
        <p className="text-muted-foreground text-sm">
          Load your financial data to run stress tests against your company.
        </p>
      </div>
    );
  }

  const currentState = buildFinancialState(baseMetrics);
  const baselineRunway = calculateRunway(currentState);
  const sensitivityVars = calculateSensitivity(currentState);

  const handleApplyStressTest = (stressedState: any, template: any) => {
    toast({
      title: `Stress Test: ${template.name}`,
      description: `Applied ${template.severity} scenario. Runway impact calculated.`,
    });
  };

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-xl font-bold mb-1" data-testid="text-stress-title">Stress Test Your Financials</h2>
        <p className="text-sm text-muted-foreground">
          Apply market shocks, funding delays, and worst-case scenarios to find your breaking points.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-500" />
              Sensitivity Tornado
            </CardTitle>
            <CardDescription>Which variables impact your runway the most?</CardDescription>
          </CardHeader>
          <CardContent>
            <TornadoChart
              baselineRunway={baselineRunway}
              variables={sensitivityVars}
              testId="workspace-tornado"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Shield className="h-4 w-4 text-red-500" />
              Reverse Stress Test
            </CardTitle>
            <CardDescription>Find the exact thresholds that put your company at risk.</CardDescription>
          </CardHeader>
          <CardContent>
            <ReverseStressTest
              currentState={currentState}
              testId="workspace-reverse-stress"
            />
          </CardContent>
        </Card>
      </div>

      <StressTestPanel
        currentState={currentState}
        currentRunway={baselineRunway}
        onApplyStressTest={handleApplyStressTest}
        testId="workspace-stress-panel"
      />
    </div>
  );
}

function WhatIfWorkspace() {
  const currentCompany = useFounderStore((s) => s.currentCompany);
  const { metrics: baseMetrics } = useFinancialMetrics();
  const { toast } = useToast();

  if (!currentCompany || !baseMetrics?.hasData) {
    return (
      <div className="text-center py-16">
        <Zap className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
        <h3 className="text-lg font-semibold mb-2">What-If Explorer</h3>
        <p className="text-muted-foreground text-sm">
          Load your financial data to explore what-if scenarios.
        </p>
      </div>
    );
  }

  const currentState = buildFinancialState(baseMetrics);
  const baselineRunway = calculateRunway(currentState);
  const survival18m = Math.min(100, Math.max(0, (baselineRunway / 18) * 100));
  const totalExpenses = currentState.opex + currentState.payroll + currentState.otherCosts;
  const monthlyGrossProfit = currentState.monthlyRevenue * (currentState.grossMargin / 100);
  const netBurn = totalExpenses - monthlyGrossProfit;
  const cashAt18m = Math.max(0, currentState.cashBalance - (netBurn * 18));

  const baselineResults = {
    runway: baselineRunway,
    survival18m,
    cashAt18m,
  };

  const quickImpact = useCallback((adjustments: Record<string, number>) => {
    return calculateWhatIfImpact(currentState, adjustments, baselineResults);
  }, [currentState, baselineResults]);

  const handleRunFullSimulation = (adjustments: Record<string, number>) => {
    toast({
      title: 'Full Simulation',
      description: 'Go to the Scenarios tab to run a full Monte Carlo simulation with these parameters.',
    });
  };

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-xl font-bold mb-1" data-testid="text-whatif-title">What-If Explorer</h2>
        <p className="text-sm text-muted-foreground">
          Adjust variables in real time and see how they affect your runway instantly.
        </p>
      </div>

      <WhatIfExplorer
        baselineState={currentState}
        baselineResults={baselineResults}
        onRunFullSimulation={handleRunFullSimulation}
        calculateQuickImpact={quickImpact}
        testId="workspace-whatif"
      />
    </div>
  );
}

function HistoryWorkspace() {
  const currentCompany = useFounderStore((s) => s.currentCompany);
  const { data: scenarios, isLoading } = useScenarios(currentCompany?.id || null);
  const { format: formatCurrency } = useCurrency();
  const { data: accuracyData } = useQuery<AccuracyResponse>({
    queryKey: ['/api/companies', currentCompany?.id, 'simulation', 'accuracy'],
    enabled: !!currentCompany?.id,
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[1,2,3,4,5,6].map(i => <Skeleton key={i} className="h-40" />)}
      </div>
    );
  }

  const history: AccuracyRecord[] = accuracyData?.history ?? [];

  const revenueData = history
    .filter((h) => h.predicted_revenue != null && h.actual_revenue != null)
    .slice(0, 12)
    .map((h) => ({
      month: `M${h.prediction_month}`,
      actual: h.actual_revenue!,
      simulated: h.predicted_revenue!,
    }));

  const burnData = history
    .filter((h) => h.predicted_burn != null && h.actual_burn != null)
    .slice(0, 12)
    .map((h) => ({
      month: `M${h.prediction_month}`,
      actual: h.actual_burn!,
      simulated: h.predicted_burn!,
    }));

  const cashData = history
    .filter((h) => h.predicted_cash != null && h.actual_cash != null)
    .slice(0, 12)
    .map((h) => ({
      month: `M${h.prediction_month}`,
      actual: h.actual_cash!,
      simulated: h.predicted_cash!,
    }));

  const churnData = history
    .filter((h) => h.predicted_churn != null && h.actual_churn != null)
    .slice(0, 12)
    .map((h) => ({
      month: `M${h.prediction_month}`,
      actual: h.actual_churn!,
      simulated: h.predicted_churn!,
    }));

  const comparisonMetrics = [
    { id: 'revenue', label: 'Revenue', data: revenueData },
    { id: 'burn', label: 'Burn Rate', data: burnData },
    { id: 'cash', label: 'Cash Balance', data: cashData },
    { id: 'churn', label: 'Churn', data: churnData },
  ].filter(m => m.data.length > 0);

  return (
    <div className="space-y-6">
      {currentCompany && (
        <PredictionAccuracySection companyId={currentCompany.id} />
      )}

      {comparisonMetrics.length > 0 && (
        <MultiMetricComparison metrics={comparisonMetrics} />
      )}

      {comparisonMetrics.length > 0 && (
        <div className="space-y-4">
          {revenueData.length > 0 && (
            <ActualVsSimulatedComparison
              metricName="revenue"
              metricLabel="Revenue"
              data={revenueData}
            />
          )}
          {cashData.length > 0 && (
            <ActualVsSimulatedComparison
              metricName="cash"
              metricLabel="Cash Balance"
              data={cashData}
            />
          )}
        </div>
      )}

      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold mb-1" data-testid="text-history-title">Scenario History</h2>
          <p className="text-sm text-muted-foreground">{scenarios?.length ?? 0} saved scenarios</p>
        </div>
      </div>

      {(!scenarios || scenarios.length === 0) ? (
        <div className="text-center py-16">
          <History className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <h3 className="text-lg font-semibold mb-2">No Saved Scenarios</h3>
          <p className="text-muted-foreground text-sm mb-4">
            Run your first simulation to start building your scenario library.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {scenarios.map((s: any) => (
            <Card key={s.id} className="hover-elevate cursor-pointer" data-testid={`card-history-${s.id}`}>
              <CardContent className="p-4">
                <h4 className="font-semibold text-sm mb-2 truncate" data-testid={`text-history-name-${s.id}`}>{s.name}</h4>
                {s.latest_simulation ? (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-muted-foreground">Runway (P50)</span>
                      <span className="text-sm font-mono font-semibold" data-testid={`text-history-runway-${s.id}`}>
                        {s.latest_simulation.runway?.p50 != null
                          ? (s.latest_simulation.runway.p50 >= 900 ? 'Sustainable' : `${s.latest_simulation.runway.p50.toFixed(1)} mo`)
                          : '\u2014'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-muted-foreground">18m Survival</span>
                      <span className="text-sm font-mono font-semibold" data-testid={`text-history-survival-${s.id}`}>
                        {(s.latest_simulation.survival?.['18m'] || 0).toFixed(0)}%
                      </span>
                    </div>
                    {s.latest_simulation.summary?.end_cash != null && (
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-muted-foreground">End Cash</span>
                        <span className="text-sm font-mono" data-testid={`text-history-endcash-${s.id}`}>
                          {formatCurrency(s.latest_simulation.summary.end_cash)}
                        </span>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground">Not yet simulated</p>
                )}
                {s.created_at && (
                  <p className="text-[10px] text-muted-foreground mt-3 pt-2 border-t" data-testid={`text-history-date-${s.id}`}>
                    Created {new Date(s.created_at).toLocaleDateString()}
                  </p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

interface BackendEvent {
  agentType?: string;
  type?: string;
  eventType?: string;
  description?: string;
  message?: string;
  impact?: Record<string, number>;
  severity?: string;
  month?: number;
  time?: string;
  metadata?: Record<string, unknown>;
}

interface BackendRecommendation {
  priority?: string;
  title?: string;
  action?: string;
  description?: string;
  impact?: string;
  category?: string;
}

interface BackendRisk {
  type?: string;
  description?: string;
  risk?: string;
  severity?: string;
  probability?: number;
  occurrences?: number;
}

interface BackendTimelineEntry {
  month: number;
  cash_balance?: number;
  cash?: number;
  monthly_revenue?: number;
  revenue?: number;
  monthly_burn?: number;
  burn?: number;
  runway_months?: number;
  runway?: number;
  headcount?: number;
}

interface BackendSimulationResponse {
  summary: {
    survivalProbability: number;
    fundingProbability: number;
    finalCash: number;
    finalRunway: number;
    peakBurn: number;
    revenueGrowth: number;
  };
  timeline: BackendTimelineEntry[];
  events: BackendEvent[];
  keyRisks: BackendRisk[];
  recommendations: BackendRecommendation[];
  trajectories: Record<string, number[]>;
  shareToken?: string;
  simulationId?: number;
}

interface SimEvent {
  type: 'investor' | 'customer' | 'team' | 'market' | 'founder';
  message: string;
  reason: string;
  impact: string;
  time: string;
  severity?: string;
  chainedFrom?: string;
}

interface TimelineMonth {
  month: number;
  cash: number;
  revenue: number;
  burn: number;
  runway: number;
  headcount: number;
}

interface SimRecommendation {
  action: string;
  impact: string;
  priority: string;
  why: string;
  affects: string;
  confidence: number;
}

interface SimulationResult {
  summary: {
    survivalProbability: number;
    fundingProbability: number;
    finalCash: number;
    finalRunway: number;
    peakBurn: number;
    revenueGrowth: number;
  };
  timeline: TimelineMonth[];
  events: SimEvent[];
  keyRisks: Array<{ risk: string; severity: string; probability: number; driver?: string }>;
  recommendations: SimRecommendation[];
  trajectories: Record<string, number[]>;
  shareToken?: string;
  simulationId?: number;
}

const THINKING_MESSAGES = [
  "Analyzing investor sentiment...",
  "Evaluating survival probability...",
  "Recalculating runway projections...",
  "Modeling customer acquisition patterns...",
  "Assessing team capacity and morale...",
  "Simulating market conditions...",
  "Computing burn rate trajectories...",
  "Running counter-move analysis...",
  "Evaluating fundraising readiness...",
  "Scoring decision confidence levels...",
];

const AGENT_CHAIN_ORDER = ['team', 'customer', 'market', 'investor', 'founder'];

const SIMULATION_STAGES = [
  { id: 'init', label: 'Initializing agents' },
  { id: 'knowledge', label: 'Building knowledge graph' },
  { id: 'simulate', label: 'Running simulation rounds' },
  { id: 'analyze', label: 'Analyzing outcomes' },
  { id: 'report', label: 'Compiling report' },
];

function mapBackendEvent(e: BackendEvent): SimEvent {
  const agentType = e.agentType || e.type || 'market';
  const impactObj = e.impact || {};
  const impactParts: string[] = [];
  if (impactObj.burn_increase) impactParts.push(`+$${Math.round(impactObj.burn_increase).toLocaleString()} burn`);
  if (impactObj.burn_reduction_pct) impactParts.push(`${Math.round(impactObj.burn_reduction_pct * 100)}% burn cut`);
  if (impactObj.headcount_change) impactParts.push(`+${impactObj.headcount_change} headcount`);
  if (impactObj.funding_climate_change) impactParts.push(`${(impactObj.funding_climate_change * 100).toFixed(0)}% funding shift`);
  if (impactObj.market_growth_change) impactParts.push(`${(impactObj.market_growth_change * 100).toFixed(0)}% growth shift`);
  if (impactObj.revenue_change) impactParts.push(`$${Math.round(impactObj.revenue_change).toLocaleString()} revenue`);
  if (impactObj.team_morale) impactParts.push(`${(impactObj.team_morale * 100).toFixed(0)}% morale`);
  if (impactObj.productivity_multiplier) impactParts.push(`${Math.round(impactObj.productivity_multiplier * 100)}% productivity`);

  const eventType = e.eventType || '';
  const reasonMap: Record<string, string> = {
    hiring_decision: 'Founder confidence high, runway sufficient',
    fundraising_initiated: 'Low runway triggered fundraising urgency',
    cost_cutting: 'Low confidence with declining runway',
    investment_interest: 'Metrics attracted investor attention',
    investment_pass: 'Metrics below investor threshold',
    churn_spike: 'Product quality or pricing pressure',
    growth_surge: 'Strong product-market fit signal',
    morale_crisis: 'Overwork or uncertainty in team',
    market_downturn: 'Macroeconomic cycle shift',
    market_opportunity: 'Expanding market conditions',
    competitor_move: 'Competitive landscape change',
    key_hire: 'Strategic talent acquisition',
    attrition: 'Team retention issues',
  };

  return {
    type: agentType as SimEvent['type'],
    message: e.description || e.message || '',
    reason: reasonMap[eventType] || `Triggered by ${eventType.replace(/_/g, ' ')}`,
    impact: impactParts.length > 0 ? impactParts.join(', ') : 'Indirect system effect',
    time: e.time || `Month ${e.month || '?'}`,
    severity: e.severity || 'info',
  };
}

function mapBackendRecommendation(r: BackendRecommendation): SimRecommendation {
  const categoryWhyMap: Record<string, string> = {
    survival: 'Critical runway risk detected by simulation',
    efficiency: 'Burn efficiency below optimal threshold',
    growth: 'Growth metrics triggered optimization',
    team: 'Team dynamics impacting performance',
    fundraising: 'Funding readiness score below threshold',
    general: 'Overall trajectory analysis',
  };

  const categoryAffectsMap: Record<string, string> = {
    survival: 'Cash runway, survival probability',
    efficiency: 'Burn rate, investor attractiveness',
    growth: 'Revenue trajectory, market position',
    team: 'Productivity, retention, morale',
    fundraising: 'Funding probability, investor confidence',
    general: 'Overall company health',
  };

  const priorityConfidenceMap: Record<string, number> = {
    critical: 92,
    high: 78,
    medium: 65,
    low: 50,
    info: 40,
  };

  return {
    action: r.title || r.action || '',
    impact: r.impact || r.description || '',
    priority: r.priority || 'medium',
    why: categoryWhyMap[r.category || 'general'] || r.description || 'Simulation analysis',
    affects: categoryAffectsMap[r.category || 'general'] || 'Multiple metrics',
    confidence: priorityConfidenceMap[r.priority || 'medium'] || 60,
  };
}

function chainEvents(events: SimEvent[]): SimEvent[] {
  if (events.length < 2) return events;
  const chained = [...events];
  for (let i = 1; i < chained.length; i++) {
    const prev = chained[i - 1];
    const curr = chained[i];
    if (prev.time === curr.time) {
      const prevIdx = AGENT_CHAIN_ORDER.indexOf(prev.type);
      const currIdx = AGENT_CHAIN_ORDER.indexOf(curr.type);
      if (currIdx > prevIdx && prevIdx >= 0) {
        curr.chainedFrom = prev.type;
      }
    }
  }
  return chained;
}

function SimulationStageTracker({ isActive, isComplete }: { isActive: boolean; isComplete: boolean }) {
  const [activeStage, setActiveStage] = useState(0);

  useEffect(() => {
    if (!isActive) {
      if (isComplete) setActiveStage(SIMULATION_STAGES.length);
      return;
    }
    setActiveStage(0);
    const interval = setInterval(() => {
      setActiveStage(prev => prev >= SIMULATION_STAGES.length - 1 ? prev : prev + 1);
    }, 3000);
    return () => clearInterval(interval);
  }, [isActive, isComplete]);

  return (
    <div className="stage-tracker flex flex-col gap-0" data-testid="stage-tracker">
      {SIMULATION_STAGES.map((stage, i) => {
        const isDone = isComplete || i < activeStage;
        const isCurrent = isActive && i === activeStage;
        return (
          <div key={stage.id} className="flex items-start gap-2">
            <div className="flex flex-col items-center">
              <div className={`stage-dot ${isDone ? 'stage-dot--complete' : ''} ${isCurrent ? 'stage-dot--active' : ''}`} data-testid={`stage-${stage.id}`} />
              {i < SIMULATION_STAGES.length - 1 && (
                <div className={`stage-line h-4 ${isDone ? 'stage-line--complete' : ''}`} />
              )}
            </div>
            <span className={`text-[10px] -mt-0.5 ${isDone ? 'text-emerald-500' : isCurrent ? 'text-blue-400' : 'text-muted-foreground/50'}`}>
              {isDone ? '✓ ' : ''}{stage.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function ConsoleThinkingState({ isActive }: { isActive: boolean }) {
  const [msgIndex, setMsgIndex] = useState(0);
  const [logEntries, setLogEntries] = useState<string[]>([]);

  useEffect(() => {
    if (!isActive) {
      setLogEntries([]);
      return;
    }
    const interval = setInterval(() => {
      setMsgIndex(prev => {
        const next = (prev + 1) % THINKING_MESSAGES.length;
        const ts = new Date().toLocaleTimeString('en-US', { hour12: false });
        const prefix = next < 3 ? '<span class="log-info">INFO</span>' : next < 7 ? '<span class="log-success">✓</span>' : '<span class="log-warn">PROC</span>';
        setLogEntries(prev => {
          const newEntries = [...prev, `<span class="log-time">${ts}</span> ${prefix} ${THINKING_MESSAGES[next]}`];
          return newEntries.slice(-8);
        });
        return next;
      });
    }, 2500);
    return () => clearInterval(interval);
  }, [isActive]);

  if (!isActive) return null;

  return (
    <div className="space-y-2 mb-2" data-testid="thinking-state">
      <div className="thinking-text flex items-center gap-2 px-3 py-2 rounded-lg bg-muted/20 border border-border/30" key={msgIndex}>
        <Loader2 className="h-3.5 w-3.5 animate-spin text-cyan-400 shrink-0" />
        <span className="text-xs text-cyan-400/90">{THINKING_MESSAGES[msgIndex]}</span>
        <span className="text-xs">
          <span className="dot-1">.</span>
          <span className="dot-2">.</span>
          <span className="dot-3">.</span>
        </span>
      </div>
      {logEntries.length > 0 && (
        <div className="system-log" data-testid="system-log">
          {logEntries.map((entry, i) => (
            <div key={i} dangerouslySetInnerHTML={{ __html: entry }} />
          ))}
        </div>
      )}
    </div>
  );
}

function DataFreshness({ lastUpdated }: { lastUpdated: number | null }) {
  const [ago, setAgo] = useState('');

  useEffect(() => {
    if (!lastUpdated) return;
    const tick = () => {
      const diff = Math.floor((Date.now() - lastUpdated) / 1000);
      if (diff < 5) setAgo('just now');
      else if (diff < 60) setAgo(`${diff}s ago`);
      else setAgo(`${Math.floor(diff / 60)}m ago`);
    };
    tick();
    const interval = setInterval(tick, 2000);
    return () => clearInterval(interval);
  }, [lastUpdated]);

  if (!lastUpdated) return null;

  const isStale = Date.now() - lastUpdated > 120000;

  return (
    <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground" data-testid="data-freshness">
      <div className={`freshness-dot ${isStale ? 'freshness-dot--stale' : ''}`} />
      <span>Live</span>
      <span className="opacity-60">(updated {ago})</span>
    </div>
  );
}

function LiveMetricCard({
  label, value, prefix, suffix, trend, icon: Icon, color = 'text-foreground', testId
}: {
  label: string; value: number; prefix?: string; suffix?: string;
  trend?: 'up' | 'down' | 'flat'; icon: LucideIcon; color?: string; testId: string;
}) {
  const animatedValue = useCounter(value);
  const isNegativeTrend = trend === 'down';
  const isPositiveTrend = trend === 'up';

  return (
    <div className="p-3 rounded-lg bg-card border border-border/50 sim-card-live" data-testid={testId}>
      <div className="flex items-center justify-between mb-1">
        <span className="text-[11px] text-muted-foreground uppercase tracking-wider">{label}</span>
        <Icon className={`h-3.5 w-3.5 ${color}`} />
      </div>
      <div className={`text-lg font-bold font-mono sim-number-pop ${color}`}>
        {prefix}{typeof value === 'number' && !isNaN(value) ? (value >= 1000 ? `${(animatedValue / 1000).toFixed(0)}k` : animatedValue.toFixed(value % 1 === 0 ? 0 : 1)) : '—'}{suffix}
      </div>
      {trend && (
        <div className={`flex items-center gap-1 mt-0.5 text-[10px] ${isPositiveTrend ? 'text-emerald-500' : isNegativeTrend ? 'text-red-400' : 'text-muted-foreground'}`}>
          {isPositiveTrend ? <TrendingUp className="h-3 w-3" /> : isNegativeTrend ? <TrendingDown className="h-3 w-3" /> : null}
          {isPositiveTrend ? 'Improving' : isNegativeTrend ? 'Declining' : 'Stable'}
        </div>
      )}
    </div>
  );
}

function ConsoleEventFeed({ events, isLive }: { events: SimEvent[]; isLive: boolean }) {
  const feedRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (feedRef.current) feedRef.current.scrollTop = feedRef.current.scrollHeight;
  }, [events.length]);

  const typeColors: Record<string, string> = {
    investor: 'bg-purple-500/10 border-purple-500/30',
    customer: 'bg-blue-500/10 border-blue-500/30',
    team: 'bg-green-500/10 border-green-500/30',
    market: 'bg-orange-500/10 border-orange-500/30',
    founder: 'bg-cyan-500/10 border-cyan-500/30',
  };

  const typeLabelColors: Record<string, string> = {
    investor: 'text-purple-400',
    customer: 'text-blue-400',
    team: 'text-green-400',
    market: 'text-orange-400',
    founder: 'text-cyan-400',
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-1 mb-2">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Agent Events</h3>
        {isLive && (
          <div className="flex items-center gap-1.5">
            <div className="sim-status-dot" />
            <span className="text-[10px] text-emerald-500 font-medium">LIVE</span>
          </div>
        )}
      </div>
      <div ref={feedRef} className="flex-1 overflow-y-auto space-y-1.5 min-h-0 max-h-[420px] pr-1" data-testid="event-feed">
        {events.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground text-xs">
            <Activity className="h-6 w-6 mx-auto mb-2 opacity-40" />
            Run a simulation to see agent events
          </div>
        ) : (
          events.map((event, i) => {
            const colorClass = typeColors[event.type] || 'bg-muted/50 border-border/40';
            const labelColor = typeLabelColors[event.type] || 'text-muted-foreground';
            const isChained = !!event.chainedFrom;
            return (
              <div
                key={i}
                className={`event-item flex items-start gap-3 p-3 rounded-lg border ${colorClass} ${isChained ? 'chain-connector' : ''}`}
                data-testid={`event-${i}`}
              >
                <div className={`text-[10px] uppercase tracking-wide font-medium w-16 shrink-0 pt-0.5 ${labelColor}`}>
                  {event.type}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs leading-snug">{event.message}</p>
                  {event.reason && (
                    <p className="text-[10px] text-muted-foreground mt-1 flex items-center gap-1">
                      <span className="opacity-50">→</span> {event.reason}
                    </p>
                  )}
                  {event.impact && event.impact !== 'Indirect system effect' && (
                    <p className="text-[10px] text-muted-foreground/70 mt-0.5 flex items-center gap-1">
                      <span className="opacity-50">→</span> {event.impact}
                    </p>
                  )}
                  <span className="text-[10px] text-muted-foreground/50 mt-1 block">{event.time}</span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

function ConsoleTimeline({ timeline, currentMonth }: { timeline: TimelineMonth[]; currentMonth: number }) {
  const maxCash = Math.max(...timeline.map(t => t.cash), 1);

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between px-1 mb-2">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Cash Timeline</h3>
        <span className="text-[10px] text-muted-foreground font-mono">{timeline.length} months</span>
      </div>
      <div className="space-y-0.5" data-testid="timeline-bars">
        {timeline.map((m, i) => {
          const pct = Math.max(2, (m.cash / maxCash) * 100);
          const isActive = i === currentMonth;
          const isDanger = m.runway < 3;
          const isWarning = m.runway < 6;
          const barColor = isDanger ? 'bg-red-500/80' : isWarning ? 'bg-amber-500/70' : 'bg-emerald-500/60';

          return (
            <div key={i} className={`sim-timeline-bar ${isActive ? 'ring-1 ring-emerald-500/50' : ''}`} data-testid={`timeline-month-${i}`}>
              <div
                className={`sim-timeline-bar__fill ${barColor}`}
                style={{ width: `${pct}%`, '--bar-width': `${pct}%` } as React.CSSProperties}
              />
              <div className="absolute inset-0 flex items-center justify-between px-2 text-[10px]">
                <span className="font-medium">M{m.month}</span>
                <span className="font-mono opacity-70">${(m.cash / 1000).toFixed(0)}k</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ConsoleInvestorPanel({ probability, risks, previousProb }: {
  probability: number;
  risks: Array<{ risk: string; severity: string; probability: number; driver?: string }>;
  previousProb: number | null;
}) {
  const animatedProb = useCounter(probability);
  const probColor = probability >= 60 ? 'bg-emerald-500' : probability >= 30 ? 'bg-amber-500' : 'bg-red-500';
  const delta = previousProb !== null ? probability - previousProb : null;
  const topDriver = risks.length > 0 ? (risks[0].driver || risks[0].risk.split(' ')[0].toLowerCase()) : null;

  return (
    <div className="space-y-3">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Investor Outlook</h3>
      <div className="p-3 rounded-lg bg-muted/30 border border-border/40">
        <div className="text-[10px] text-muted-foreground mb-1">Term Sheet Probability</div>
        <div className="flex items-baseline gap-2">
          <div className="text-2xl font-bold font-mono sim-number-pop" data-testid="text-investor-prob">
            {animatedProb.toFixed(0)}%
          </div>
          {delta !== null && delta !== 0 && (
            <span className={`text-xs font-mono sim-fade-in ${delta > 0 ? 'text-emerald-400' : 'text-red-400'}`} data-testid="investor-delta">
              {delta > 0 ? '+' : ''}{delta.toFixed(0)}%
            </span>
          )}
        </div>
        <div className="sim-progress-bar mt-2">
          <div className={`sim-progress-bar__fill ${probColor}`} style={{ width: `${probability}%` }} />
        </div>
        {topDriver && (
          <div className="mt-2 text-[10px] text-muted-foreground flex items-center gap-1" data-testid="investor-driver">
            <span className="opacity-50">Key driver:</span>
            <span className="text-foreground/80">{topDriver}</span>
          </div>
        )}
      </div>
      {risks.length > 0 && (
        <div className="space-y-1.5">
          <div className="text-[10px] text-muted-foreground uppercase tracking-wider">Key Risks</div>
          {risks.slice(0, 3).map((r, i) => (
            <div key={i} className="flex items-start gap-2 p-2 rounded bg-muted/20 text-xs" data-testid={`risk-${i}`}>
              <AlertTriangle className={`h-3 w-3 shrink-0 mt-0.5 ${r.severity === 'high' ? 'text-red-400' : r.severity === 'medium' ? 'text-amber-400' : 'text-muted-foreground'}`} />
              <div className="flex-1">
                <span className="leading-snug">{r.risk}</span>
                {r.driver && (
                  <span className="text-[10px] text-muted-foreground/60 ml-1">({r.driver})</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ConsoleCohortPanel({ timeline }: { timeline: TimelineMonth[] }) {
  if (timeline.length === 0) return null;

  const firstRevenue = timeline[0]?.revenue || 1;
  const retentionPoints = timeline.slice(0, 8).map((m, i) => {
    const revenueRetention = firstRevenue > 0 ? Math.min(100, (m.revenue / firstRevenue) * 100) : 100 - (i * 5);
    const burnPressure = m.burn > 0 ? Math.min(20, (m.burn / Math.max(m.revenue, 1)) * 3) : 0;
    const retention = Math.max(10, revenueRetention - burnPressure);
    return { month: m.month, retention: Math.min(100, retention) };
  });

  return (
    <div className="space-y-3">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Cohort Retention</h3>
      <div className="space-y-1" data-testid="cohort-bars">
        {retentionPoints.map((p, i) => {
          const prev = i > 0 ? retentionPoints[i - 1].retention : 100;
          const delta = p.retention - prev;
          const trend = delta > 2 ? '↑' : delta < -3 ? '↓' : '';
          const trendColor = delta > 2 ? 'text-emerald-400' : delta < -3 ? 'text-red-400' : '';

          return (
            <div key={p.month} className="flex items-center gap-2">
              <span className="text-[10px] text-muted-foreground w-6 text-right font-mono">M{p.month}</span>
              <div className="flex-1 sim-progress-bar">
                <div className="sim-progress-bar__fill bg-cyan-500/70" style={{ width: `${p.retention}%` }} />
              </div>
              <span className="text-[10px] font-mono w-8 text-right">{p.retention.toFixed(0)}%</span>
              {trend && (
                <span className={`text-[10px] w-3 ${trendColor}`} data-testid={`cohort-trend-${p.month}`}>{trend}</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ConsoleDecisionReplay({ recommendations }: { recommendations: SimRecommendation[] }) {
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    if (recommendations.length <= 1) return;
    const interval = setInterval(() => {
      setActiveIndex(prev => (prev + 1) % recommendations.length);
    }, 3000);
    return () => clearInterval(interval);
  }, [recommendations.length]);

  if (recommendations.length === 0) return null;

  const current = recommendations[activeIndex];
  const priorityColors: Record<string, string> = {
    critical: 'bg-red-500/20 text-red-400 border-red-500/30',
    high: 'bg-red-500/20 text-red-400 border-red-500/30',
    medium: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    low: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    info: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Decision Replay</h3>
        <span className="text-[10px] text-muted-foreground font-mono">{activeIndex + 1}/{recommendations.length}</span>
      </div>
      <div className="p-3 rounded-lg bg-muted/20 border border-border/40 sim-fade-in" key={activeIndex} data-testid="decision-replay-card">
        <div className="flex items-center gap-2 mb-2">
          <ShieldCheck className="h-3.5 w-3.5 text-cyan-400" />
          <Badge variant="outline" className={`text-[9px] px-1.5 py-0 ${priorityColors[current.priority] || ''}`}>
            {current.priority}
          </Badge>
          <span className="text-[9px] font-mono text-muted-foreground ml-auto" data-testid="decision-confidence">
            {current.confidence}% confidence
          </span>
        </div>
        <p className="text-xs leading-snug mb-1.5 font-medium">{current.action}</p>
        <p className="text-[10px] text-muted-foreground mb-2">{current.impact}</p>
        <div className="space-y-1 pt-2 border-t border-border/30">
          <p className="text-[10px] text-muted-foreground/70 flex gap-1">
            <span className="opacity-50 shrink-0">Why:</span>
            <span>{current.why}</span>
          </p>
          <p className="text-[10px] text-muted-foreground/70 flex gap-1">
            <span className="opacity-50 shrink-0">Affects:</span>
            <span>{current.affects}</span>
          </p>
        </div>
      </div>
      <div className="flex gap-1 justify-center">
        {recommendations.map((_, i) => (
          <button
            key={i}
            onClick={() => setActiveIndex(i)}
            className={`h-1 rounded-full transition-all duration-300 ${i === activeIndex ? 'w-4 bg-cyan-500' : 'w-1.5 bg-muted-foreground/30 hover:bg-muted-foreground/50'}`}
            data-testid={`decision-dot-${i}`}
          />
        ))}
      </div>
    </div>
  );
}

function ConsoleScenarioSlider({
  label, value, onChange, min, max, step, unit, testId
}: {
  label: string; value: number; onChange: (v: number) => void;
  min: number; max: number; step: number; unit?: string; testId: string;
}) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <label className="text-[11px] text-muted-foreground">{label}</label>
        <span className="text-xs font-mono font-medium">{value}{unit}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={e => onChange(Number(e.target.value))}
        className="w-full h-1 bg-muted rounded-full appearance-none cursor-pointer accent-emerald-500"
        data-testid={testId}
      />
    </div>
  );
}

interface V2AgentPersona {
  id: string;
  name: string;
  agent_type: string;
  bio: string;
  personality_traits: string[];
  goals: string[];
  emotional_tendency: number;
  activity_level: number;
  influence: number;
  risk_tolerance: number;
}

interface V2CompanyState {
  mrr: number;
  arr: number;
  burn_rate: number;
  cash: number;
  runway_months: number;
  customers: number;
  churn_rate: number;
  team_size: number;
  team_morale: number;
  product_quality: number;
  market_fit: number;
  brand_reputation: number;
  investor_confidence: number;
  growth_rate: number;
}

interface V2AgentEvent {
  round: number;
  month: string;
  agent_id: string;
  agent_name: string;
  agent_type: string;
  action: string;
  reasoning: string;
  description: string;
  impact: Record<string, number>;
  sentiment: string;
}

interface V2Report {
  title: string;
  executive_summary: string;
  key_findings: string[];
  risk_factors: string[];
  opportunities: string[];
  recommendation: string;
  outcome_score: number;
  term_sheet_probability: number;
}

type SimStep = 'idle' | 'generating_agents' | 'simulating' | 'generating_report' | 'complete';

function AgentSimulationConsole() {
  const currentCompany = useFounderStore((s) => s.currentCompany);
  const { metrics: baseMetrics } = useFinancialMetrics();
  const { toast } = useToast();

  const [numRounds, setNumRounds] = useState(12);
  const [fundingClimate, setFundingClimate] = useState(0.6);
  const [marketGrowth, setMarketGrowth] = useState(0.5);
  const [marketVolatility, setMarketVolatility] = useState(0.1);
  const [isSimulating, setIsSimulating] = useState(false);
  const [currentStep, setCurrentStep] = useState<SimStep>('idle');
  const [progressPct, setProgressPct] = useState(0);
  const [lastUpdated, setLastUpdated] = useState<number | null>(null);
  const [terminalLogs, setTerminalLogs] = useState<Array<{ time: string; msg: string; type?: "info" | "success" | "error" | "warn" }>>([]);
  const [agents, setAgents] = useState<V2AgentPersona[]>([]);
  const [liveState, setLiveState] = useState<V2CompanyState | null>(null);
  const [streamEvents, setStreamEvents] = useState<V2AgentEvent[]>([]);
  const [report, setReport] = useState<V2Report | null>(null);
  const [completedRounds, setCompletedRounds] = useState(0);
  const [simulationId, setSimulationId] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const eventFeedRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const addLog = useCallback((msg: string, type: "info" | "success" | "error" | "warn" = "info") => {
    const time = new Date().toLocaleTimeString('en-US', { hour12: false });
    setTerminalLogs(prev => [...prev.slice(-50), { time, msg, type }]);
  }, []);

  const stepMap: Record<SimStep, Array<{ id: string; label: string; status: 'complete' | 'active' | 'pending' }>> = {
    idle: [
      { id: 'agents', label: 'Generate Agents', status: 'pending' },
      { id: 'simulate', label: 'Run Simulation', status: 'pending' },
      { id: 'analyze', label: 'Analyze Outcomes', status: 'pending' },
      { id: 'report', label: 'Compile Report', status: 'pending' },
    ],
    generating_agents: [
      { id: 'agents', label: 'Generate Agents', status: 'active' },
      { id: 'simulate', label: 'Run Simulation', status: 'pending' },
      { id: 'analyze', label: 'Analyze Outcomes', status: 'pending' },
      { id: 'report', label: 'Compile Report', status: 'pending' },
    ],
    simulating: [
      { id: 'agents', label: 'Generate Agents', status: 'complete' },
      { id: 'simulate', label: 'Run Simulation', status: 'active' },
      { id: 'analyze', label: 'Analyze Outcomes', status: 'pending' },
      { id: 'report', label: 'Compile Report', status: 'pending' },
    ],
    generating_report: [
      { id: 'agents', label: 'Generate Agents', status: 'complete' },
      { id: 'simulate', label: 'Run Simulation', status: 'complete' },
      { id: 'analyze', label: 'Analyze Outcomes', status: 'complete' },
      { id: 'report', label: 'Compile Report', status: 'active' },
    ],
    complete: [
      { id: 'agents', label: 'Generate Agents', status: 'complete' },
      { id: 'simulate', label: 'Run Simulation', status: 'complete' },
      { id: 'analyze', label: 'Analyze Outcomes', status: 'complete' },
      { id: 'report', label: 'Compile Report', status: 'complete' },
    ],
  };

  const simSteps = stepMap[currentStep];

  const runSimulation = useCallback(async () => {
    setIsSimulating(true);
    setCurrentStep('generating_agents');
    setProgressPct(0);
    setStreamEvents([]);
    setAgents([]);
    setReport(null);
    setLiveState(null);
    setCompletedRounds(0);
    setSimulationId(null);
    setTerminalLogs([]);
    addLog('Starting MiroFish-style multi-agent simulation...');

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const res = await fetch('/api/simulation/v2/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        signal: controller.signal,
        body: JSON.stringify({
          total_rounds: numRounds,
          monthly_revenue: baseMetrics?.mrr ?? 50000,
          monthly_burn: baseMetrics?.burnRate ?? 80000,
          cash_balance: baseMetrics?.cashOnHand ?? 500000,
          customers: 50,
          team_size: baseMetrics?.headcount || 10,
          growth_rate: baseMetrics?.monthlyGrowthRate ?? 0.05,
          churn_rate: 0.03,
          funding_climate: fundingClimate,
          market_growth: marketGrowth,
          market_volatility: marketVolatility,
        }),
      });

      if (!res.ok) {
        const errText = await res.text();
        throw new Error(errText || `HTTP ${res.status}`);
      }

      const reader = res.body?.getReader();
      if (!reader) throw new Error('No response stream');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const raw = line.slice(6).trim();
          if (!raw) continue;

          try {
            const msg = JSON.parse(raw);

            switch (msg.type) {
              case 'progress':
                setCurrentStep(msg.step as SimStep);
                setProgressPct(msg.pct ?? 0);
                addLog(msg.msg || `${msg.step}: ${msg.pct}%`);
                break;

              case 'agent_event': {
                const evt = msg.data as V2AgentEvent;
                setStreamEvents(prev => [...prev, evt]);
                addLog(`[Month ${evt.round}] ${evt.agent_name}: ${evt.description}`);
                break;
              }

              case 'round_complete':
                setLiveState(msg.state as V2CompanyState);
                setCompletedRounds(msg.round);
                break;

              case 'agents_generated':
                setAgents(msg.agents as V2AgentPersona[]);
                addLog(`${(msg.agents as V2AgentPersona[]).length} agent personas generated`, 'success');
                break;

              case 'complete': {
                const result = msg.result;
                setSimulationId(result.simulation_id);
                setReport(result.report as V2Report);
                setLiveState(result.final_state as V2CompanyState);
                if (result.agents) setAgents(result.agents);
                setCurrentStep('complete');
                setIsSimulating(false);
                setLastUpdated(Date.now());
                const score = result.report?.outcome_score ?? 0;
                addLog(`Simulation complete — Outcome score: ${score}/100`, 'success');
                toast({ title: 'Simulation Complete', description: `Outcome score: ${score}/100` });
                break;
              }

              case 'error':
                throw new Error(msg.message || 'Simulation failed');
            }
          } catch (parseErr) {
            if ((parseErr as Error).message?.includes('Simulation failed') ||
                (parseErr as Error).message?.includes('HTTP')) {
              throw parseErr;
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name === 'AbortError') return;
      setIsSimulating(false);
      setCurrentStep('idle');
      addLog(`Simulation failed: ${err.message}`, 'error');
      toast({ title: 'Simulation Failed', description: err.message || 'An error occurred', variant: 'destructive' });
    }
  }, [numRounds, fundingClimate, marketGrowth, marketVolatility, baseMetrics, addLog, toast]);

  useEffect(() => {
    if (eventFeedRef.current) {
      eventFeedRef.current.scrollTop = eventFeedRef.current.scrollHeight;
    }
  }, [streamEvents.length]);

  const initCash = baseMetrics?.cashOnHand ?? 500000;
  const initBurn = baseMetrics?.burnRate ?? 80000;
  const currentCash = liveState?.cash ?? initCash;
  const currentBurn = liveState?.burn_rate ?? initBurn;
  const currentRunway = liveState?.runway_months ?? (initBurn > 0 ? initCash / initBurn : 0);
  const currentMrr = liveState?.mrr ?? baseMetrics?.mrr ?? 50000;
  const currentCustomers = liveState?.customers ?? 50;
  const outcomeScore = report?.outcome_score ?? 0;
  const termSheetProb = report?.term_sheet_probability ?? 0;
  const isComplete = currentStep === 'complete';
  const riskHigh = currentRunway > 0 && currentRunway < 10;
  const simStatus = isSimulating ? 'running' : isComplete ? 'complete' : 'ready';

  return (
    <div className="relative min-h-[600px]">
      <SimBackgroundOrbs color="blue" />

      <div className="relative z-10">
        <SimStepProgress steps={simSteps} />

        <div className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-bold flex items-center gap-2" data-testid="text-sim-title">
              <Zap className="h-5 w-5 text-primary" />
              Flight Simulator
            </h2>
            <SimStatusBadge status={simStatus} />
            <DataFreshness lastUpdated={lastUpdated} />
            {isSimulating && completedRounds > 0 && (
              <span className="text-[10px] font-mono text-zinc-500">
                Month {completedRounds}/{numRounds}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              onClick={runSimulation}
              disabled={isSimulating}
              className="h-8 text-sm gap-2 shadow-[0_0_20px_rgba(79,125,249,0.2)] hover:shadow-[0_0_30px_rgba(79,125,249,0.4)] transition-all duration-300"
              data-testid="button-run-simulation"
            >
              {isSimulating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
              {isSimulating ? 'Simulating...' : 'Run Simulation'}
            </Button>
          </div>
        </div>

        {agents.length > 0 && (
          <div className="px-4 pb-3 overflow-x-auto">
            <div className="flex gap-2 min-w-max">
              {agents.map((agent, i) => (
                <div
                  key={agent.id}
                  className="flex-shrink-0 w-48 p-3 rounded-lg border border-white/[0.06] bg-white/[0.02] backdrop-blur-sm fc-animate-fade-up"
                  style={{ animationDelay: `${i * 80}ms` }}
                  data-testid={`agent-card-${agent.id}`}
                >
                  <div className="flex items-center gap-2 mb-1.5">
                    <div className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center text-[10px] font-bold text-primary">
                      {agent.name.charAt(0)}
                    </div>
                    <div className="min-w-0">
                      <div className="text-xs font-medium text-zinc-200 truncate">{agent.name}</div>
                      <div className="text-[10px] text-zinc-500">{agent.agent_type}</div>
                    </div>
                  </div>
                  <p className="text-[10px] text-zinc-500 line-clamp-2 leading-relaxed">{agent.bio}</p>
                  <div className="flex gap-1 mt-1.5 flex-wrap">
                    {agent.personality_traits.slice(0, 2).map(t => (
                      <span key={t} className="text-[9px] px-1.5 py-0.5 rounded bg-white/[0.05] text-zinc-500">{t}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="grid grid-cols-12 gap-4 px-4 pb-16">
          <div className="col-span-12 lg:col-span-3 space-y-3 fc-stagger">
            <SimGlassCard variant={isSimulating ? 'processing' : 'elevated'} className="p-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-3">Live Metrics</h3>
              <div className="space-y-3 fc-stagger">
                <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]" data-testid="metric-cash">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] text-zinc-500 uppercase tracking-wider">Cash</span>
                    <DollarSign className="h-3.5 w-3.5 text-emerald-400" />
                  </div>
                  <SimAnimatedCounter value={currentCash} prefix="$" className="text-lg font-bold font-mono text-emerald-400" />
                  {liveState && (
                    <div className={`flex items-center gap-1 mt-0.5 text-[10px] ${liveState.cash > initCash ? 'text-emerald-400' : 'text-red-400'}`}>
                      {liveState.cash > initCash ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                      {liveState.cash > initCash ? 'Improving' : 'Declining'}
                    </div>
                  )}
                </div>
                <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]" data-testid="metric-mrr">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] text-zinc-500 uppercase tracking-wider">MRR</span>
                    <TrendingUp className="h-3.5 w-3.5 text-blue-400" />
                  </div>
                  <SimAnimatedCounter value={currentMrr} prefix="$" className="text-lg font-bold font-mono text-blue-400" />
                </div>
                <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]" data-testid="metric-burn">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] text-zinc-500 uppercase tracking-wider">Monthly Burn</span>
                    <TrendingDown className="h-3.5 w-3.5 text-red-400" />
                  </div>
                  <SimAnimatedCounter value={currentBurn} prefix="$" className="text-lg font-bold font-mono text-red-400" />
                </div>
                <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]" data-testid="metric-runway">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] text-zinc-500 uppercase tracking-wider">Runway</span>
                    <Clock className="h-3.5 w-3.5" />
                  </div>
                  <SimAnimatedCounter
                    value={currentRunway}
                    suffix=" mo"
                    className={`text-lg font-bold font-mono ${currentRunway < 6 ? 'text-red-400' : currentRunway < 12 ? 'text-amber-400' : 'text-emerald-400'}`}
                    decimals={1}
                  />
                </div>
                <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]" data-testid="metric-customers">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] text-zinc-500 uppercase tracking-wider">Customers</span>
                    <Activity className="h-3.5 w-3.5 text-violet-400" />
                  </div>
                  <SimAnimatedCounter value={currentCustomers} className="text-lg font-bold font-mono text-violet-400" />
                </div>
                <div className={`mt-1 px-2 py-1 text-xs rounded-md font-mono ${riskHigh ? 'bg-red-500/10 text-red-400 border border-red-500/20' : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'}`} data-testid="risk-badge">
                  Risk: {riskHigh ? 'High' : 'Moderate'}
                </div>
              </div>
            </SimGlassCard>

            <SimGlassCard variant="elevated" className="p-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-3">Scenario Controls</h3>
              <div className="space-y-3">
                <ConsoleScenarioSlider label="Simulation Months" value={numRounds} onChange={setNumRounds} min={6} max={36} step={1} testId="slider-rounds" />
                <ConsoleScenarioSlider label="Funding Climate" value={fundingClimate} onChange={setFundingClimate} min={0} max={1} step={0.1} testId="slider-funding" />
                <ConsoleScenarioSlider label="Market Growth" value={marketGrowth} onChange={setMarketGrowth} min={0} max={1} step={0.1} testId="slider-market" />
                <ConsoleScenarioSlider label="Market Volatility" value={marketVolatility} onChange={setMarketVolatility} min={0} max={0.5} step={0.05} testId="slider-volatility" />
              </div>
            </SimGlassCard>
          </div>

          <div className="col-span-12 lg:col-span-6 space-y-3">
            {isSimulating && currentStep === 'generating_agents' && (
              <SimGlassCard variant="processing" className="p-4 fc-animate-fade-up">
                <div className="flex items-center gap-3">
                  <Loader2 className="h-5 w-5 animate-spin text-primary" />
                  <div>
                    <h3 className="text-sm font-medium text-zinc-200">Generating Agent Personas</h3>
                    <p className="text-xs text-zinc-500">LLM is creating 7 unique personas based on your company data...</p>
                  </div>
                </div>
              </SimGlassCard>
            )}

            <SimGlassCard variant="default" className="p-4 min-h-[300px]">
              {streamEvents.length > 0 ? (
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">Agent Events</h3>
                    <span className="text-[10px] font-mono text-zinc-500">{streamEvents.length} events</span>
                  </div>
                  <div ref={eventFeedRef} className="max-h-[420px] overflow-y-auto -mx-4">
                    {streamEvents.map((evt, i) => (
                      <SimEventCard
                        key={`${evt.round}-${evt.agent_id}-${i}`}
                        agentName={evt.agent_name}
                        agentType={evt.agent_type}
                        action={evt.action}
                        description={evt.description}
                        timestamp={evt.month}
                        sentiment={
                          evt.sentiment === 'very_negative' || evt.sentiment === 'negative' ? 'negative' :
                          evt.sentiment === 'very_positive' || evt.sentiment === 'positive' ? 'positive' : 'neutral'
                        }
                        index={i}
                        impact={evt.reasoning}
                        chainedFrom={undefined}
                      />
                    ))}
                  </div>
                </div>
              ) : isSimulating ? (
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-4">Agent Events</h3>
                  <SimSkeleton lines={5} />
                  <p className="text-xs text-zinc-500 text-center mt-4">Waiting for agent events...</p>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 fc-animate-fade-up">
                  <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-4 fc-animate-glow">
                    <Zap className="h-8 w-8 text-primary" />
                  </div>
                  <h3 className="text-sm font-medium text-zinc-300 mb-2">Ready to Simulate</h3>
                  <p className="text-xs text-zinc-500 max-w-sm text-center mb-4">
                    Seven LLM-powered agents — Founder, Investors, Customer, Team, Market, and Competitor — will make decisions month-by-month to model realistic outcomes.
                  </p>
                  <Button
                    onClick={runSimulation}
                    className="shadow-[0_0_20px_rgba(79,125,249,0.2)] hover:shadow-[0_0_30px_rgba(79,125,249,0.4)] transition-all duration-300"
                    data-testid="button-run-empty"
                  >
                    <Play className="h-4 w-4 mr-2" /> Launch Simulation
                  </Button>
                </div>
              )}
            </SimGlassCard>
          </div>

          <div className="col-span-12 lg:col-span-3 space-y-3 fc-stagger">
            {report ? (
              <>
                <SimGlassCard variant="elevated" className="p-4 fc-animate-fade-up">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-2">Outcome Score</h3>
                  <div className="flex items-center gap-3 mb-3">
                    <SimAnimatedCounter
                      value={outcomeScore}
                      suffix="/100"
                      className={`text-2xl font-bold font-mono ${outcomeScore >= 70 ? 'text-emerald-400' : outcomeScore >= 40 ? 'text-amber-400' : 'text-red-400'}`}
                    />
                  </div>
                  <div className="text-[10px] text-zinc-500 mb-2">Term Sheet Probability</div>
                  <SimAnimatedCounter
                    value={termSheetProb}
                    suffix="%"
                    className={`text-lg font-bold font-mono ${termSheetProb >= 60 ? 'text-emerald-400' : termSheetProb >= 30 ? 'text-amber-400' : 'text-red-400'}`}
                  />
                </SimGlassCard>

                <SimGlassCard variant="default" className="p-4 fc-animate-fade-up">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-2">{report.title}</h3>
                  <p className="text-xs text-zinc-400 leading-relaxed mb-3">{report.executive_summary}</p>
                </SimGlassCard>

                {report.key_findings.length > 0 && (
                  <SimGlassCard variant="default" className="p-4 fc-animate-fade-up">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-2">Key Findings</h3>
                    <ul className="space-y-1.5">
                      {report.key_findings.map((f, i) => (
                        <li key={i} className="text-xs text-zinc-400 flex items-start gap-1.5">
                          <span className="text-emerald-400 mt-0.5">&#x2022;</span>
                          {f}
                        </li>
                      ))}
                    </ul>
                  </SimGlassCard>
                )}

                {report.risk_factors.length > 0 && (
                  <SimGlassCard variant="default" className="p-4 fc-animate-fade-up">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-2">Risk Factors</h3>
                    <ul className="space-y-1.5">
                      {report.risk_factors.map((r, i) => (
                        <li key={i} className="text-xs text-zinc-400 flex items-start gap-1.5">
                          <AlertTriangle className="h-3 w-3 text-amber-400 mt-0.5 shrink-0" />
                          {r}
                        </li>
                      ))}
                    </ul>
                  </SimGlassCard>
                )}

                {report.recommendation && (
                  <SimGlassCard variant="default" className="p-4 fc-animate-fade-up">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-2">Recommendation</h3>
                    <p className="text-xs text-zinc-400 leading-relaxed">{report.recommendation}</p>
                  </SimGlassCard>
                )}
              </>
            ) : isComplete ? null : (
              <SimGlassCard variant="default" className="p-4">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-3">AI Report</h3>
                {isSimulating ? (
                  <>
                    <SimSkeleton lines={4} />
                    <p className="text-xs text-zinc-500 text-center mt-3">Report generates after simulation</p>
                  </>
                ) : (
                  <>
                    <SimSkeleton lines={4} />
                    <p className="text-xs text-zinc-500 text-center mt-3">Run a simulation to see the report</p>
                  </>
                )}
              </SimGlassCard>
            )}
          </div>
        </div>
      </div>

      <SimTerminalDrawer logs={terminalLogs} label="Simulation Log" />
    </div>
  );
}

export default function SimulateWorkspace() {
  useSEO({
    title: "Scenario Simulator — What-If Analysis for Startups | FounderConsole",
    description: "Run Monte Carlo simulations to model hiring, pricing, and fundraising scenarios. See P10/P50/P90 confidence bands and compare outcomes side by side.",
    path: "/simulate",
    robots: "noindex, nofollow",
  });
  const [activeTab, setActiveTab] = useState('scenarios');
  const currentCompany = useFounderStore((s) => s.currentCompany);
  const { data: scenarios } = useScenarios(currentCompany?.id || null);
  const scenarioCount = scenarios?.length ?? 0;

  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto">
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <div className="flex items-center justify-between gap-4 mb-6 flex-wrap">
          <TabsList className="h-auto p-1 gap-1" data-testid="workspace-tabs">
            <TabsTrigger value="scenarios" className="gap-2" data-testid="workspace-tab-scenarios">
              <FlaskConical className="h-4 w-4" />
              Scenarios
            </TabsTrigger>
            <TabsTrigger value="stress-test" className="gap-2" data-testid="workspace-tab-stress">
              <Shield className="h-4 w-4" />
              Stress Tests
            </TabsTrigger>
            <TabsTrigger value="what-if" className="gap-2" data-testid="workspace-tab-whatif">
              <Zap className="h-4 w-4" />
              What-If
            </TabsTrigger>
            <TabsTrigger value="history" className="gap-2" data-testid="workspace-tab-history">
              <History className="h-4 w-4" />
              History
              {scenarioCount > 0 && (
                <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4 bg-primary/15 text-primary border-0">
                  {scenarioCount}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="console" className="gap-2" data-testid="workspace-tab-console">
              <Zap className="h-4 w-4" />
              Flight Simulator
            </TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="scenarios" className="mt-0">
          <Suspense fallback={<WorkspaceLoading />}>
            <ScenariosPage />
          </Suspense>
        </TabsContent>

        <TabsContent value="stress-test" className="mt-0">
          <StressTestWorkspace />
        </TabsContent>

        <TabsContent value="what-if" className="mt-0">
          <WhatIfWorkspace />
        </TabsContent>

        <TabsContent value="history" className="mt-0">
          <HistoryWorkspace />
        </TabsContent>

        <TabsContent value="console" className="mt-0">
          <AgentSimulationConsole />
        </TabsContent>
      </Tabs>
    </div>
  );
}
