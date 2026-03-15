import { useState, useCallback, lazy, Suspense } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiRequest } from '@/lib/queryClient';
import {
  FlaskConical, Zap, Shield, History, Target,
  AlertTriangle, RefreshCw, TrendingUp, TrendingDown, Minus, Loader2
} from 'lucide-react';
import { useFounderStore } from '@/store/founderStore';
import { useFinancialMetrics } from '@/hooks/useFinancialMetrics';

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

export default function SimulateWorkspace() {
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
      </Tabs>
    </div>
  );
}
