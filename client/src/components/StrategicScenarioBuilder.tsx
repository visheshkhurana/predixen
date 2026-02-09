import { useState, useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { GoalSelector, type SimulationGoal } from '@/components/GoalSelector';
import { StrategyCard, type StrategyPreview } from '@/components/StrategyCard';
import { ImpactBar } from '@/components/ImpactBar';
import { QuestionInput, PRICING_OPTIONS, EXPENSE_REDUCTION_OPTIONS } from '@/components/QuestionInput';
import { StickyActionBar } from '@/components/StickyActionBar';
import { getStrategiesForGoal, getStrategyById, type StrategyTemplate } from '@/config/strategies';
import { generateRecommendations, type Recommendation } from '@/config/recommendations';
import { 
  ArrowLeft, 
  Sparkles, 
  ChevronRight,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  TrendingDown,
  Info,
} from 'lucide-react';
import { cn } from '@/lib/utils';

type BuilderStep = 'goal' | 'strategy' | 'customize' | 'results';

interface BaseMetrics {
  cashOnHand: number;
  monthlyExpenses: number;
  monthlyRevenue: number;
  currentRunway: number;
  growthRate: number;
}

interface StrategicScenarioBuilderProps {
  baseMetrics?: BaseMetrics;
  onRunSimulation: (params: SimulationParams) => Promise<void>;
  onSaveScenario: (params: SimulationParams) => Promise<void>;
  isRunning?: boolean;
  simulation?: SimulationResult | null;
}

interface SimulationParams {
  name: string;
  pricing_change_pct: number;
  growth_uplift_pct: number;
  burn_reduction_pct: number;
  gross_margin_delta_pct: number;
  churn_change_pct: number;
  cac_change_pct: number;
  fundraise_month: number | null;
  fundraise_amount: number;
  tags: string[];
}

interface SimulationResult {
  runway?: { p10: number; p50: number; p90: number };
  survival?: { '12m': number; '18m': number; '24m': number };
  summary?: { end_cash: number };
}

const DEFAULT_BASE_METRICS: BaseMetrics = {
  cashOnHand: 500000,
  monthlyExpenses: 80000,
  monthlyRevenue: 50000,
  currentRunway: 16.7,
  growthRate: 10,
};

function estimateProjectedRunway(
  baseMetrics: BaseMetrics,
  params: Partial<SimulationParams>
): number {
  const burnReduction = baseMetrics.monthlyExpenses * ((params.burn_reduction_pct || 0) / 100);
  const adjustedExpenses = baseMetrics.monthlyExpenses - burnReduction;
  
  const pricingImpact = baseMetrics.monthlyRevenue * ((params.pricing_change_pct || 0) / 100);
  const growthImpact = baseMetrics.monthlyRevenue * ((params.growth_uplift_pct || 0) / 100) * 0.5;
  const adjustedRevenue = baseMetrics.monthlyRevenue + pricingImpact + growthImpact;
  
  const adjustedCash = baseMetrics.cashOnHand + (params.fundraise_amount || 0);
  
  const newBurn = adjustedExpenses - adjustedRevenue;
  if (newBurn <= 0) return 999;
  
  return adjustedCash / newBurn;
}

export function StrategicScenarioBuilder({
  baseMetrics = DEFAULT_BASE_METRICS,
  onRunSimulation,
  onSaveScenario,
  isRunning = false,
  simulation,
}: StrategicScenarioBuilderProps) {
  const [step, setStep] = useState<BuilderStep>('goal');
  const [selectedGoal, setSelectedGoal] = useState<SimulationGoal | undefined>();
  const [selectedStrategy, setSelectedStrategy] = useState<StrategyTemplate | undefined>();
  const [pendingStrategyId, setPendingStrategyId] = useState<string | null>(null);
  const [customParams, setCustomParams] = useState<Partial<SimulationParams>>({});
  const [isSaving, setIsSaving] = useState(false);
  
  const strategies = useMemo(() => {
    if (!selectedGoal) return [];
    return getStrategiesForGoal(selectedGoal).map(s => ({
      id: s.id,
      name: s.name,
      description: s.description,
      narrative: s.narrative,
      icon: <s.icon className="w-4 h-4" />,
      projectedRunway: baseMetrics.currentRunway + s.projections.runwayChange,
      survivalProbability: s.projections.survivalProbability,
      arrGrowth: s.projections.arrGrowth,
      burnChange: s.projections.burnChange,
      assumptions: s.assumptions,
      riskLevel: s.riskLevel,
      recommended: s.recommended,
    } as StrategyPreview));
  }, [selectedGoal, baseMetrics]);
  
  const currentParams = useMemo(() => {
    if (!selectedStrategy) return customParams;
    return {
      ...selectedStrategy.params,
      ...customParams,
    };
  }, [selectedStrategy, customParams]);
  
  const projectedRunway = useMemo(() => {
    return estimateProjectedRunway(baseMetrics, currentParams);
  }, [baseMetrics, currentParams]);
  
  const recommendations = useMemo(() => {
    if (!simulation) return [];
    return generateRecommendations({
      runwayMonths: simulation.runway?.p50 || projectedRunway,
      survivalProbability: simulation.survival?.['18m'] || 70,
      burnRate: baseMetrics.monthlyExpenses - baseMetrics.monthlyRevenue,
      revenueGrowth: baseMetrics.growthRate + (currentParams.growth_uplift_pct || 0),
      grossMargin: 60 + (currentParams.gross_margin_delta_pct || 0),
      cashBalance: baseMetrics.cashOnHand,
    });
  }, [simulation, projectedRunway, baseMetrics, currentParams]);
  
  const handleGoalSelect = (goal: SimulationGoal) => {
    setSelectedGoal(goal);
    setStep('strategy');
  };
  
  const handleStrategySelect = (strategyId: string) => {
    const strategy = getStrategyById(strategyId);
    if (strategy) {
      setPendingStrategyId(strategyId);
      setSelectedStrategy(strategy);
      setCustomParams({});
      setStep('customize');
      setPendingStrategyId(null);
    }
  };
  
  const handleParamChange = (key: keyof SimulationParams, value: number | string) => {
    setCustomParams(prev => ({
      ...prev,
      [key]: typeof value === 'string' ? parseFloat(value) || 0 : value,
    }));
  };
  
  const handleRunSimulation = async () => {
    const params: SimulationParams = {
      name: selectedStrategy?.name || 'Custom Scenario',
      pricing_change_pct: currentParams.pricing_change_pct || 0,
      growth_uplift_pct: currentParams.growth_uplift_pct || 0,
      burn_reduction_pct: currentParams.burn_reduction_pct || 0,
      gross_margin_delta_pct: currentParams.gross_margin_delta_pct || 0,
      churn_change_pct: currentParams.churn_change_pct || 0,
      cac_change_pct: 0,
      fundraise_month: currentParams.fundraise_amount ? 3 : null,
      fundraise_amount: currentParams.fundraise_amount || 0,
      tags: selectedGoal ? [selectedGoal] : [],
    };
    
    await onRunSimulation(params);
    setStep('results');
  };
  
  const handleSaveScenario = async () => {
    setIsSaving(true);
    try {
      const params: SimulationParams = {
        name: selectedStrategy?.name || 'Custom Scenario',
        pricing_change_pct: currentParams.pricing_change_pct || 0,
        growth_uplift_pct: currentParams.growth_uplift_pct || 0,
        burn_reduction_pct: currentParams.burn_reduction_pct || 0,
        gross_margin_delta_pct: currentParams.gross_margin_delta_pct || 0,
        churn_change_pct: currentParams.churn_change_pct || 0,
        cac_change_pct: 0,
        fundraise_month: currentParams.fundraise_amount ? 3 : null,
        fundraise_amount: currentParams.fundraise_amount || 0,
        tags: selectedGoal ? [selectedGoal] : [],
      };
      await onSaveScenario(params);
    } finally {
      setIsSaving(false);
    }
  };
  
  const handleReset = () => {
    setStep('goal');
    setSelectedGoal(undefined);
    setSelectedStrategy(undefined);
    setPendingStrategyId(null);
    setCustomParams({});
  };
  
  const handleBack = () => {
    switch (step) {
      case 'strategy':
        setStep('goal');
        break;
      case 'customize':
        setStep('strategy');
        break;
      case 'results':
        setStep('customize');
        break;
    }
  };
  
  const stepNumber = step === 'goal' ? 1 : step === 'strategy' ? 2 : step === 'customize' ? 3 : 4;
  
  return (
    <div className="space-y-6 pb-20">
      {step !== 'goal' && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleBack}
            className="gap-1 -ml-2"
            data-testid="button-back-nav"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </Button>
          <span className="text-muted-foreground/50">/</span>
          <span>{selectedGoal === 'extend_runway' ? 'Extend Runway' : selectedGoal === 'accelerate_growth' ? 'Accelerate Growth' : 'Balance'}</span>
          {selectedStrategy && (
            <>
              <span className="text-muted-foreground/50">/</span>
              <span>{selectedStrategy.shortName}</span>
            </>
          )}
        </div>
      )}
      
      {baseMetrics && step !== 'results' && (
        <Card className="bg-muted/30">
          <CardContent className="py-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <div className="text-xs text-muted-foreground">Cash on Hand</div>
                <div className="text-lg font-semibold">${(baseMetrics.cashOnHand / 1000).toFixed(0)}K</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Monthly Burn</div>
                <div className="text-lg font-semibold text-red-500">
                  ${((baseMetrics.monthlyExpenses - baseMetrics.monthlyRevenue) / 1000).toFixed(0)}K
                </div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Current Runway</div>
                <div className="text-lg font-semibold">{baseMetrics.currentRunway.toFixed(1)} months</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Growth Rate</div>
                <div className="text-lg font-semibold text-emerald-500">+{baseMetrics.growthRate}%</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
      
      {step === 'goal' && (
        <GoalSelector
          selectedGoal={selectedGoal}
          onSelectGoal={handleGoalSelect}
        />
      )}
      
      {step === 'strategy' && (
        <div className="space-y-6">
          <div className="text-center">
            <h2 className="text-xl font-semibold">Choose a Strategy</h2>
            <p className="text-muted-foreground mt-1">
              Select a pre-built strategy or customize your own approach
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {strategies.map(strategy => (
              <StrategyCard
                key={strategy.id}
                strategy={strategy}
                currentRunway={baseMetrics.currentRunway}
                onSimulate={handleStrategySelect}
                isSelected={pendingStrategyId === strategy.id}
                isLoading={pendingStrategyId !== null}
              />
            ))}
          </div>
        </div>
      )}
      
      {step === 'customize' && selectedStrategy && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <selectedStrategy.icon className="w-5 h-5" />
                    {selectedStrategy.name}
                  </CardTitle>
                  <CardDescription className="mt-1">
                    {selectedStrategy.description}
                  </CardDescription>
                </div>
                <Badge variant="outline" className={cn(
                  "capitalize",
                  selectedStrategy.riskLevel === 'low' && "border-emerald-500/30 text-emerald-500",
                  selectedStrategy.riskLevel === 'medium' && "border-amber-500/30 text-amber-500",
                  selectedStrategy.riskLevel === 'high' && "border-red-500/30 text-red-500",
                )}>
                  {selectedStrategy.riskLevel} risk
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              <ImpactBar
                baselineRunway={baseMetrics.currentRunway}
                projectedRunway={projectedRunway}
              />
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <QuestionInput
                  id="pricing"
                  question="How will you adjust pricing?"
                  helpText="Price changes directly impact revenue. Higher prices can extend runway but may affect customer acquisition."
                  type="select"
                  value={String(currentParams.pricing_change_pct || 0)}
                  onChange={(v) => handleParamChange('pricing_change_pct', v)}
                  options={PRICING_OPTIONS}
                />
                
                <QuestionInput
                  id="growth"
                  question="Expected growth change?"
                  helpText="Growth assumptions affect future revenue projections. Be realistic about what's achievable."
                  type="number"
                  value={currentParams.growth_uplift_pct || 0}
                  onChange={(v) => handleParamChange('growth_uplift_pct', v)}
                  min={-30}
                  max={50}
                  unit="%"
                />
                
                <QuestionInput
                  id="expenses"
                  question="How much can you reduce expenses?"
                  helpText="Expense reductions directly extend runway. Consider what's realistic without hurting core operations."
                  type="select"
                  value={String(currentParams.burn_reduction_pct || 0)}
                  onChange={(v) => handleParamChange('burn_reduction_pct', v)}
                  options={EXPENSE_REDUCTION_OPTIONS}
                />
                
                <QuestionInput
                  id="fundraise"
                  question="Any fundraising planned?"
                  helpText="Enter expected funding amount. This will be modeled as arriving in month 3."
                  type="number"
                  value={currentParams.fundraise_amount || 0}
                  onChange={(v) => handleParamChange('fundraise_amount', v)}
                  min={0}
                  max={10000000}
                  step={50000}
                  unit="$"
                />
              </div>
              
              <div className="p-4 rounded-lg bg-muted/50 border border-border/50">
                <div className="flex items-start gap-3">
                  <Sparkles className="w-5 h-5 text-primary mt-0.5" />
                  <div>
                    <div className="font-medium text-sm">What This Means</div>
                    <p className="text-sm text-muted-foreground mt-1">
                      {projectedRunway > baseMetrics.currentRunway ? (
                        <>
                          These changes would <span className="text-emerald-500 font-medium">extend your runway by {(projectedRunway - baseMetrics.currentRunway).toFixed(1)} months</span> to approximately {projectedRunway.toFixed(1)} months.
                        </>
                      ) : projectedRunway < baseMetrics.currentRunway ? (
                        <>
                          These changes would <span className="text-red-500 font-medium">reduce your runway by {(baseMetrics.currentRunway - projectedRunway).toFixed(1)} months</span> to approximately {projectedRunway.toFixed(1)} months.
                        </>
                      ) : (
                        <>Your runway would remain approximately the same at {projectedRunway.toFixed(1)} months.</>
                      )}
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
      
      {step === 'results' && simulation && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                Simulation Complete
              </CardTitle>
              <CardDescription>
                {selectedStrategy?.name || 'Custom Scenario'} results
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-4 rounded-lg bg-muted/50">
                  <div className="text-xs text-muted-foreground">Runway (P50)</div>
                  <div className="text-2xl font-bold">{simulation.runway?.p50?.toFixed(1) || '--'} mo</div>
                  {simulation.runway?.p50 && baseMetrics && (
                    <div className={cn(
                      "text-xs flex items-center gap-1 mt-1",
                      simulation.runway.p50 > baseMetrics.currentRunway ? "text-emerald-500" : "text-red-500"
                    )}>
                      {simulation.runway.p50 > baseMetrics.currentRunway ? (
                        <TrendingUp className="w-3 h-3" />
                      ) : (
                        <TrendingDown className="w-3 h-3" />
                      )}
                      {(simulation.runway.p50 - baseMetrics.currentRunway).toFixed(1)} months
                    </div>
                  )}
                </div>
                
                <div className="p-4 rounded-lg bg-muted/50">
                  <div className="text-xs text-muted-foreground">Survival (18m)</div>
                  <div className="text-2xl font-bold">{((simulation.survival?.['18m'] || 0) * 100).toFixed(0)}%</div>
                </div>
                
                <div className="p-4 rounded-lg bg-muted/50">
                  <div className="text-xs text-muted-foreground">Runway Range</div>
                  <div className="text-lg font-semibold">
                    {simulation.runway?.p10?.toFixed(0)} - {simulation.runway?.p90?.toFixed(0)} mo
                  </div>
                  <div className="text-xs text-muted-foreground">P10 to P90</div>
                </div>
                
                <div className="p-4 rounded-lg bg-muted/50">
                  <div className="text-xs text-muted-foreground">End Cash (P50)</div>
                  <div className="text-lg font-semibold">
                    ${((simulation.summary?.end_cash || 0) / 1000).toFixed(0)}K
                  </div>
                </div>
              </div>
              
              {/* Calculation Assumptions Panel */}
              <div className="space-y-3 border-t pt-4">
                <h3 className="font-medium flex items-center gap-2 text-sm">
                  <Info className="w-4 h-4 text-muted-foreground" />
                  Simulation Assumptions
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                  <div className="p-2 rounded bg-muted/30">
                    <div className="text-muted-foreground">Base Cash</div>
                    <div className="font-medium">${(baseMetrics.cashOnHand / 1000).toFixed(0)}K</div>
                  </div>
                  <div className="p-2 rounded bg-muted/30">
                    <div className="text-muted-foreground">Monthly Revenue</div>
                    <div className="font-medium">${(baseMetrics.monthlyRevenue / 1000).toFixed(0)}K</div>
                  </div>
                  <div className="p-2 rounded bg-muted/30">
                    <div className="text-muted-foreground">Monthly Expenses</div>
                    <div className="font-medium">${(baseMetrics.monthlyExpenses / 1000).toFixed(0)}K</div>
                  </div>
                  <div className="p-2 rounded bg-muted/30">
                    <div className="text-muted-foreground">Base Growth Rate</div>
                    <div className="font-medium">{baseMetrics.growthRate}% MoM</div>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">
                  Runway is calculated using Monte Carlo simulation with 1,000 scenarios, accounting for revenue growth, 
                  burn adjustments, and your scenario parameters. P10/P50/P90 represent confidence intervals.
                </p>
              </div>
              
              {recommendations.length > 0 && (
                <div className="space-y-3">
                  <h3 className="font-medium flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-primary" />
                    Recommendations
                  </h3>
                  <div className="space-y-2">
                    {recommendations.slice(0, 3).map(rec => (
                      <div 
                        key={rec.id}
                        className={cn(
                          "p-3 rounded-lg border",
                          rec.priority === 'high' && "border-red-500/30 bg-red-500/5",
                          rec.priority === 'medium' && "border-amber-500/30 bg-amber-500/5",
                          rec.priority === 'low' && "border-border bg-muted/30",
                        )}
                      >
                        <div className="flex items-start gap-3">
                          {rec.priority === 'high' ? (
                            <AlertTriangle className="w-4 h-4 text-red-500 mt-0.5" />
                          ) : (
                            <Info className="w-4 h-4 text-muted-foreground mt-0.5" />
                          )}
                          <div>
                            <div className="font-medium text-sm">{rec.title}</div>
                            <p className="text-xs text-muted-foreground mt-0.5">{rec.description}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
      
      {step !== 'goal' && (
        <StickyActionBar
          onRunSimulation={handleRunSimulation}
          onSaveScenario={handleSaveScenario}
          onResetInputs={handleReset}
          onBack={step !== 'strategy' ? handleBack : undefined}
          isRunning={isRunning}
          isSaving={isSaving}
          canRun={step === 'customize'}
          canSave={step === 'results' && !!simulation}
          canGoBack={step !== 'strategy'}
          currentStep={stepNumber}
          totalSteps={4}
          statusMessage={
            step === 'strategy' ? (pendingStrategyId ? 'Loading strategy...' : 'Select a strategy to customize') :
            step === 'customize' ? 'Adjust parameters and run simulation' :
            step === 'results' ? 'Save this scenario or try another' :
            undefined
          }
        />
      )}
    </div>
  );
}
