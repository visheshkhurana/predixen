import { useState, useCallback, lazy, Suspense } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import {
  FlaskConical, Zap, Shield, History,
  AlertTriangle
} from 'lucide-react';
import { useFounderStore } from '@/store/founderStore';
import { useFinancialMetrics } from '@/hooks/useFinancialMetrics';
import { useCurrency } from '@/hooks/useCurrency';
import { WhatIfExplorer, StressTestPanel, ReverseStressTest, TornadoChart } from '@/components/simulation';
import { calculateSensitivity, calculateRunway, calculateWhatIfImpact, type FinancialState } from '@/lib/simulation/sensitivityAnalysis';
import { useScenarios } from '@/api/hooks';

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

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[1,2,3,4,5,6].map(i => <Skeleton key={i} className="h-40" />)}
      </div>
    );
  }

  if (!scenarios || scenarios.length === 0) {
    return (
      <div className="text-center py-16">
        <History className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
        <h3 className="text-lg font-semibold mb-2">No Saved Scenarios</h3>
        <p className="text-muted-foreground text-sm mb-4">
          Run your first simulation to start building your scenario library.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold mb-1" data-testid="text-history-title">Scenario History</h2>
          <p className="text-sm text-muted-foreground">{scenarios.length} saved scenarios</p>
        </div>
      </div>

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
