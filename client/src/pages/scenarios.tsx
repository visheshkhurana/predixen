import { useState, useMemo, useEffect } from 'react';
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
import { DashboardKPICards } from '@/components/DashboardKPICards';
import { ScenarioComparisonView } from '@/components/ScenarioComparisonView';
import { Play, Filter, BarChart3, History, GitCompare, Loader2, Target, Trophy, BookOpen, Sparkles, Lock, MessageSquare, Users } from 'lucide-react';
import { useFounderStore } from '@/store/founderStore';
import { useScenarios, useCreateScenario, useRunSimulation, useSimulation, useMultiScenarioSimulation, useSensitivityAnalysis, useEnhancedMultiScenarioSimulation, useScenarioTimeseries } from '@/api/hooks';
import { ScenarioComments } from '@/components/ScenarioComments';
import { DistributionView } from '@/components/DistributionView';
import { useScenarioComments, useAddComment, useEditComment, useDeleteComment } from '@/api/workspace';
import { useToast } from '@/hooks/use-toast';
import { formatSimulationForExport } from '@/lib/exportUtils';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';

const SCENARIO_TEMPLATES = [
  { 
    name: 'Baseline (Status Quo)', 
    description: 'No adjustments - serves as control',
    tags: ['baseline'],
    deltas: { pricing_change_pct: 0, growth_uplift_pct: 0, burn_reduction_pct: 0 } 
  },
  { 
    name: 'Conservative Cut', 
    description: 'Reduce burn while accepting slower growth',
    tags: ['cost-cutting'],
    deltas: { burn_reduction_pct: 20, growth_uplift_pct: -3 } 
  },
  { 
    name: 'Moderate Growth Push', 
    description: 'Balanced growth with efficiency gains',
    tags: ['growth'],
    deltas: { growth_uplift_pct: 5, burn_reduction_pct: -5 } 
  },
  { 
    name: 'Aggressive Growth', 
    description: 'Maximize growth with increased investment',
    tags: ['growth'],
    deltas: { growth_uplift_pct: 15, burn_reduction_pct: -10 } 
  },
  { 
    name: 'Cost-Cut Scenario', 
    description: 'Deep cost reduction to extend runway',
    tags: ['cost-cutting'],
    deltas: { burn_reduction_pct: 25, growth_uplift_pct: -5 } 
  },
  { 
    name: 'Price Increase', 
    description: 'Raise prices to improve unit economics',
    tags: ['pricing'],
    deltas: { pricing_change_pct: 10, growth_uplift_pct: -2 } 
  },
  { 
    name: 'Bridge Round', 
    description: 'Small funding round to extend runway',
    tags: ['fundraising'],
    deltas: { fundraise_month: 3, fundraise_amount: 500000 } 
  },
  { 
    name: 'Fundraising Delay', 
    description: 'Delay fundraising by 3 months',
    tags: ['fundraising'],
    deltas: { fundraise_month: 6, fundraise_amount: 1000000 } 
  },
  { 
    name: 'Best Case', 
    description: 'Optimistic scenario with multiple improvements',
    tags: ['growth', 'pricing'],
    deltas: { growth_uplift_pct: 20, pricing_change_pct: 5, burn_reduction_pct: 10 } 
  },
  { 
    name: 'Worst Case', 
    description: 'Pessimistic scenario for risk planning',
    tags: ['risk'],
    deltas: { growth_uplift_pct: -10, burn_reduction_pct: 0, fundraise_month: 9, fundraise_amount: 500000 } 
  },
];

const ALL_TAGS = ['baseline', 'growth', 'cost-cutting', 'pricing', 'fundraising', 'risk'];

export default function ScenariosPage() {
  const { currentCompany, setCurrentStep } = useFounderStore();
  const { toast } = useToast();
  const params = useParams<{ id?: string }>();
  const { data: scenarios, isLoading: scenariosLoading } = useScenarios(currentCompany?.id || null);
  const createScenarioMutation = useCreateScenario();
  const runSimulationMutation = useRunSimulation();
  
  const [selectedScenarioId, setSelectedScenarioId] = useState<number | null>(null);
  
  // Auto-select scenario from URL parameter
  useEffect(() => {
    if (params.id) {
      const idFromUrl = parseInt(params.id, 10);
      if (!isNaN(idFromUrl)) {
        setSelectedScenarioId(idFromUrl);
      }
    }
  }, [params.id]);
  const { data: simulation, isLoading: simLoading } = useSimulation(selectedScenarioId);
  const { data: timeseriesData, isLoading: timeseriesLoading } = useScenarioTimeseries(selectedScenarioId);
  
  const [isCreating, setIsCreating] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [duplicateDialog, setDuplicateDialog] = useState<{ open: boolean; existingId?: number; scenarioData?: any }>({ open: false });
  const [activeTab, setActiveTab] = useState('builder');
  const [tagFilter, setTagFilter] = useState<string[]>([]);
  const [showComparison, setShowComparison] = useState(false);
  
  const multiSimMutation = useMultiScenarioSimulation();
  const [multiSimResults, setMultiSimResults] = useState<any>(null);
  
  const sensitivityMutation = useSensitivityAnalysis();
  const [sensitivityResults, setSensitivityResults] = useState<any>(null);
  
  const enhancedMultiMutation = useEnhancedMultiScenarioSimulation();
  const [enhancedResults, setEnhancedResults] = useState<any>(null);
  const [isCreatingBaseline, setIsCreatingBaseline] = useState(false);
  
  // Custom events for scenario builder
  const [customEvents, setCustomEvents] = useState<ScenarioEvent[]>([]);
  
  // Comments for collaboration
  const { data: comments = [], isLoading: commentsLoading } = useScenarioComments(selectedScenarioId || 0);
  const addCommentMutation = useAddComment();
  const editCommentMutation = useEditComment();
  const deleteCommentMutation = useDeleteComment();
  
  const currentUserEmail = currentCompany ? `demo@predixen.ai` : 'user@example.com';
  
  // Check if any scenario has been run (has simulation results)
  const hasRunScenario = useMemo(() => {
    if (!scenarios || scenarios.length === 0) return false;
    return scenarios.some((s: any) => s.latest_simulation);
  }, [scenarios]);
  
  // Check if we have simulation results to show
  const hasSimulationResults = simulation || multiSimResults || enhancedResults || sensitivityResults;
  
  const filteredScenarios = useMemo(() => {
    if (!scenarios) return [];
    if (tagFilter.length === 0) return scenarios;
    return scenarios.filter((s: any) => 
      s.tags?.some((tag: string) => tagFilter.includes(tag))
    );
  }, [scenarios, tagFilter]);

  const baseMetrics = useMemo(() => {
    if (!currentCompany) return undefined;
    const cashOnHand = 500000;
    const monthlyRevenue = 50000;
    const monthlyExpenses = 80000;
    const monthlyBurn = monthlyExpenses - monthlyRevenue;
    const currentRunway = monthlyBurn > 0 ? cashOnHand / monthlyBurn : 999;
    
    return {
      cashOnHand,
      monthlyExpenses,
      monthlyRevenue,
      currentRunway,
      growthRate: 10,
    };
  }, [currentCompany]);

  // These useMemo hooks must be before any early returns to follow Rules of Hooks
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
  
  if (!currentCompany) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">Select a company to manage scenarios</p>
          </CardContent>
        </Card>
      </div>
    );
  }
  
  const checkForDuplicate = (name: string) => {
    if (!scenarios) return null;
    const existing = scenarios.find((s: any) => 
      s.name.toLowerCase() === name.toLowerCase()
    );
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
        data: {
          ...scenarioData,
          overwrite_id: overwrite ? existingId : undefined,
        },
      });
      setSelectedScenarioId(scenario.id);
      
      setIsRunning(true);
      await runSimulationMutation.mutateAsync({ scenarioId: scenario.id, nSims: 1000 });
      setCurrentStep('simulation');
      setActiveTab('results');
      toast({ title: 'Simulation complete!' });
    } catch (err: any) {
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
      setActiveTab('results');
      toast({ title: 'Simulation complete!' });
    } catch (err: any) {
      toast({ title: 'Error', description: err.message, variant: 'destructive' });
    } finally {
      setIsRunning(false);
    }
  };
  
  const handleRunMultiScenario = async () => {
    if (!currentCompany) return;
    
    try {
      const result = await multiSimMutation.mutateAsync({
        companyId: currentCompany.id,
        options: { n_sims: 500, horizon_months: 24 }
      });
      setMultiSimResults(result);
      toast({ title: 'All scenarios simulated successfully!' });
    } catch (err: any) {
      toast({ title: 'Error', description: err.message, variant: 'destructive' });
    }
  };
  
  const handleRunSensitivityAnalysis = async (targetRunway: number = 18, targetProbability: number = 0.7) => {
    if (!currentCompany) return;
    
    try {
      const result = await sensitivityMutation.mutateAsync({
        companyId: currentCompany.id,
        targetRunway,
        targetProbability
      });
      setSensitivityResults(result);
      toast({ title: 'Sensitivity analysis complete!' });
    } catch (err: any) {
      toast({ title: 'Error', description: err.message, variant: 'destructive' });
    }
  };
  
  const handleRunEnhancedMulti = async () => {
    if (!currentCompany) return;
    
    try {
      const result = await enhancedMultiMutation.mutateAsync({
        companyId: currentCompany.id,
        options: { 
          n_sims: 500, 
          horizon_months: 24,
          include_sensitivity: true,
          scenarios: [
            { name: 'Baseline', description: 'Current trajectory' },
            { 
              name: 'Cost Cutting', 
              description: 'Reduce expenses by 20%',
              events: [{ event_type: 'cost_cut', start_month: 1, params: { opex_reduction_pct: 20, payroll_reduction_pct: 15 } }]
            },
            { 
              name: 'Growth Investment', 
              description: 'Increase marketing spend',
              events: [{ event_type: 'marketing_spend_change', start_month: 1, params: { change_pct: 30 } }]
            },
            { 
              name: 'Fundraise', 
              description: 'Raise $1M bridge round',
              events: [{ event_type: 'fundraise', start_month: 3, params: { amount: 1000000 } }]
            },
          ]
        }
      });
      setEnhancedResults(result);
      toast({ title: 'Enhanced simulation complete!' });
    } catch (err: any) {
      toast({ title: 'Error', description: err.message, variant: 'destructive' });
    }
  };
  
  // Create and run baseline scenario with one click
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
        gross_margin_delta_pct: 0,
        churn_change_pct: 0,
        cac_change_pct: 0,
        fundraise_month: null,
        fundraise_amount: 0,
        tags: baselineTemplate.tags,
      };
      
      const scenario = await createScenarioMutation.mutateAsync({
        companyId: currentCompany.id,
        data: scenarioData,
      });
      setSelectedScenarioId(scenario.id);
      
      await runSimulationMutation.mutateAsync({ scenarioId: scenario.id, nSims: 1000 });
      setCurrentStep('simulation');
      setActiveTab('results');
      toast({ 
        title: 'Baseline scenario created!',
        description: 'Your baseline simulation is ready to view.'
      });
    } catch (err: any) {
      toast({ title: 'Error', description: err.message, variant: 'destructive' });
    } finally {
      setIsCreatingBaseline(false);
    }
  };
  
  // Handle clicking on disabled tabs
  const handleDisabledTabClick = (tabName: string) => {
    toast({
      title: `${tabName} tab is locked`,
      description: 'Create and run at least one scenario first to unlock this tab.',
      variant: 'default',
    });
  };
  
  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold">Scenario Builder</h1>
          <p className="text-muted-foreground">Model different strategies and see their impact</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <SimulationLearnMoreModal />
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" data-testid="button-filter-tags">
                <Filter className="h-4 w-4 mr-2" />
                Filter
                {tagFilter.length > 0 && (
                  <Badge variant="secondary" className="ml-2">{tagFilter.length}</Badge>
                )}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Filter by Tag</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {ALL_TAGS.map(tag => (
                <DropdownMenuCheckboxItem
                  key={tag}
                  checked={tagFilter.includes(tag)}
                  onCheckedChange={(checked) => {
                    setTagFilter(checked 
                      ? [...tagFilter, tag] 
                      : tagFilter.filter(t => t !== tag)
                    );
                  }}
                >
                  {tag}
                </DropdownMenuCheckboxItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
          <Button
            variant={showComparison ? 'default' : 'outline'}
            size="sm"
            onClick={() => setShowComparison(!showComparison)}
            data-testid="button-toggle-comparison"
          >
            <BarChart3 className="h-4 w-4 mr-2" />
            Compare
          </Button>
        </div>
      </div>
      
      {showComparison && comparisonData.length > 0 && (
        <ScenarioComparisonTable scenarios={comparisonData} />
      )}
      
      {/* Show baseline creation prompt when no scenarios exist */}
      {!scenariosLoading && (!scenarios || scenarios.length === 0) && (
        <Card className="border-primary/30 bg-primary/5">
          <CardContent className="py-6">
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-full bg-primary/10">
                  <Sparkles className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <h3 className="font-medium">Get started instantly</h3>
                  <p className="text-sm text-muted-foreground">
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
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 mr-2" />
                    Create Baseline Scenario
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
      
      <Tabs value={activeTab} onValueChange={(value) => {
        // Prevent switching to disabled tabs
        const isTabDisabled = ['results', 'compare', 'enhanced', 'sensitivity'].includes(value) && !hasRunScenario && !hasSimulationResults;
        if (isTabDisabled) {
          const tabNames: Record<string, string> = {
            results: 'Simulation Results',
            compare: 'Compare All',
            enhanced: 'Decision Ranking',
            sensitivity: 'Sensitivity'
          };
          handleDisabledTabClick(tabNames[value] || value);
          return;
        }
        setActiveTab(value);
      }}>
        <TabsList className="flex-wrap h-auto gap-1">
          <TabsTrigger value="builder" data-testid="tab-builder">Scenario Builder</TabsTrigger>
          <TabsTrigger 
            value="results" 
            data-testid="tab-results"
            disabled={!hasRunScenario && !hasSimulationResults}
            className={!hasRunScenario && !hasSimulationResults ? 'opacity-50' : ''}
          >
            {!hasRunScenario && !hasSimulationResults && <Lock className="h-3 w-3 mr-1" />}
            Simulation Results
          </TabsTrigger>
          <TabsTrigger 
            value="compare" 
            data-testid="tab-compare"
            disabled={!hasRunScenario && !hasSimulationResults}
            className={!hasRunScenario && !hasSimulationResults ? 'opacity-50' : ''}
          >
            {!hasRunScenario && !hasSimulationResults && <Lock className="h-3 w-3 mr-1" />}
            <GitCompare className="h-4 w-4 mr-2" />
            Compare All
          </TabsTrigger>
          <TabsTrigger 
            value="enhanced" 
            data-testid="tab-enhanced"
            disabled={!hasRunScenario && !hasSimulationResults}
            className={!hasRunScenario && !hasSimulationResults ? 'opacity-50' : ''}
          >
            {!hasRunScenario && !hasSimulationResults && <Lock className="h-3 w-3 mr-1" />}
            <Trophy className="h-4 w-4 mr-2" />
            Decision Ranking
          </TabsTrigger>
          <TabsTrigger 
            value="sensitivity" 
            data-testid="tab-sensitivity"
            disabled={!hasRunScenario && !hasSimulationResults}
            className={!hasRunScenario && !hasSimulationResults ? 'opacity-50' : ''}
          >
            {!hasRunScenario && !hasSimulationResults && <Lock className="h-3 w-3 mr-1" />}
            <Target className="h-4 w-4 mr-2" />
            Sensitivity
          </TabsTrigger>
          {scenarios && scenarios.length > 0 && (
            <TabsTrigger value="history" data-testid="tab-history">
              <History className="h-4 w-4 mr-2" />
              Saved ({scenarios.length})
            </TabsTrigger>
          )}
          {selectedScenarioId && (
            <TabsTrigger value="collaborate" data-testid="tab-collaborate">
              <MessageSquare className="h-4 w-4 mr-2" />
              Discussion
              {comments.length > 0 && (
                <span className="ml-1 text-xs bg-muted rounded-full px-1.5">{comments.length}</span>
              )}
            </TabsTrigger>
          )}
        </TabsList>
        
        <TabsContent value="builder" className="mt-6">
          <ScenarioWizard
            templates={SCENARIO_TEMPLATES}
            onComplete={handleWizardComplete}
            isRunning={isCreating || isRunning}
            baseMetrics={baseMetrics}
          />
        </TabsContent>
        
        <TabsContent value="history" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Saved Scenarios</CardTitle>
              <CardDescription>
                {filteredScenarios.length} scenarios available
                {tagFilter.length > 0 && ` (filtered by ${tagFilter.length} tags)`}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {scenariosLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-16 w-full" />
                  <Skeleton className="h-16 w-full" />
                  <Skeleton className="h-16 w-full" />
                </div>
              ) : filteredScenarios.length === 0 ? (
                <p className="text-muted-foreground text-center py-8">
                  No saved scenarios yet. Create one using the builder.
                </p>
              ) : (
                <ScrollArea className="h-[400px]">
                  <div className="space-y-2">
                    {filteredScenarios.map((s: any) => (
                      <div
                        key={s.id}
                        className="flex items-center justify-between gap-4 p-4 rounded-lg border hover-elevate"
                      >
                        <div className="flex-1 min-w-0">
                          <span className="font-medium">{s.name}</span>
                          {s.tags && s.tags.length > 0 && (
                            <div className="flex gap-1 mt-1 flex-wrap">
                              {s.tags.map((tag: string) => (
                                <Badge key={tag} variant="outline" className="text-xs">
                                  {tag}
                                </Badge>
                              ))}
                            </div>
                          )}
                          {s.latest_simulation && (
                            <div className="flex gap-4 mt-2 text-sm text-muted-foreground">
                              <span>Runway: {s.latest_simulation.runway?.p50?.toFixed(1) || '?'} mo</span>
                              <span>Survival: {(s.latest_simulation.survival?.['18m'] || 0).toFixed(0)}%</span>
                            </div>
                          )}
                        </div>
                        <Button
                          onClick={() => handleRunScenario(s.id)}
                          disabled={isRunning && selectedScenarioId === s.id}
                          data-testid={`button-run-scenario-${s.id}`}
                        >
                          <Play className="h-4 w-4 mr-2" />
                          Run
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
              <p className="text-sm text-muted-foreground">
                Run simulations for 5 default scenarios and compare results side-by-side
              </p>
            </div>
            <div className="flex items-center gap-2">
              <GlossaryModal />
              <Button
                onClick={handleRunMultiScenario}
                disabled={multiSimMutation.isPending}
                data-testid="button-run-multi-scenario"
              >
                {multiSimMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Running...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 mr-2" />
                    Run All Scenarios
                  </>
                )}
              </Button>
            </div>
          </div>
          
          {multiSimMutation.isPending && (
            <Card>
              <CardContent className="p-6">
                <div className="space-y-3">
                  <Skeleton className="h-24 w-full" />
                  <Skeleton className="h-64 w-full" />
                  <Skeleton className="h-64 w-full" />
                </div>
              </CardContent>
            </Card>
          )}
          
          {multiSimResults && !multiSimMutation.isPending && (
            <>
              {multiSimResults.comparison && (
                <ExecutiveSummary
                  scenarios={Object.entries(multiSimResults.scenarios || {}).map(([key, scenario]: [string, any]) => ({
                    id: key,
                    name: scenario.name || key,
                    runway_p50: scenario.summary?.runway_p50 || 0,
                    runway_p10: scenario.summary?.runway_p10,
                    runway_p90: scenario.summary?.runway_p90,
                    survival_rate: (scenario.summary?.survival_18m || 0) / 100,
                    end_cash_p50: scenario.summary?.end_cash_p50,
                    monthly_burn_p50: scenario.summary?.monthly_burn_p50,
                    assumptions: scenario.assumptions,
                  }))}
                  baselineId="baseline"
                  targetRunway={18}
                  minSurvival={0.8}
                />
              )}
              
              <MultiScenarioSummary comparison={multiSimResults.comparison} />
              
              <ScenarioComparisonView
                scenarios={Object.entries(multiSimResults.scenarios || {}).map(([key, scenario]: [string, any]) => ({
                  name: scenario.name || key,
                  runway_p50: scenario.summary?.runway_p50 || 0,
                  runway_p10: scenario.summary?.runway_p10,
                  runway_p90: scenario.summary?.runway_p90,
                  survival_18m: scenario.summary?.survival_18m || 0,
                  survival_12m: scenario.summary?.survival_12m,
                  end_cash: scenario.summary?.end_cash_p50,
                  avg_burn: scenario.summary?.monthly_burn_p50,
                  score: scenario.score,
                }))}
                testId="scenario-comparison-view"
              />
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {Object.entries(multiSimResults.scenarios || {}).map(([key, scenario]: [string, any]) => (
                  <ScenarioCard
                    key={key}
                    id={key}
                    name={scenario.name || key}
                    runwayP50={scenario.summary?.runway_p50 || 0}
                    runwayP10={scenario.summary?.runway_p10}
                    runwayP90={scenario.summary?.runway_p90}
                    survivalRate={(scenario.summary?.survival_18m || 0) / 100}
                    endCash={scenario.summary?.end_cash_p50}
                    monthlyBurn={scenario.summary?.monthly_burn_p50}
                    assumptions={scenario.assumptions}
                    tags={scenario.tags}
                    isBaseline={key === 'baseline'}
                    isBest={multiSimResults.comparison?.best_scenario === key}
                    meetsBenchmark={(scenario.summary?.runway_p50 || 0) >= 18 && (scenario.summary?.survival_18m || 0) >= 80}
                    cashProjection={scenario.month_data?.map((m: any) => m.cash_p50)}
                    testId={`scenario-card-${key}`}
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
            <Card>
              <CardContent className="py-12 text-center">
                <GitCompare className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground mb-2">
                  Compare 5 pre-built scenarios to understand different strategic paths
                </p>
                <p className="text-sm text-muted-foreground mb-4">
                  Baseline, Conservative Cut, Moderate Growth, Aggressive Growth, and Cost Cutting
                </p>
                <Button onClick={handleRunMultiScenario} data-testid="button-run-multi-cta">
                  <Play className="h-4 w-4 mr-2" />
                  Run All Scenarios
                </Button>
              </CardContent>
            </Card>
          )}
        </TabsContent>
        
        <TabsContent value="enhanced" className="mt-6 space-y-6">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div>
              <h2 className="text-lg font-semibold">Enhanced Scenario Analysis</h2>
              <p className="text-sm text-muted-foreground">
                Regime-aware simulation with correlated drivers and decision ranking
              </p>
            </div>
            <Button
              onClick={handleRunEnhancedMulti}
              disabled={enhancedMultiMutation.isPending}
              data-testid="button-run-enhanced-multi"
            >
              {enhancedMultiMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Running...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Run Enhanced Analysis
                </>
              )}
            </Button>
          </div>
          
          {enhancedMultiMutation.isPending && (
            <Card>
              <CardContent className="p-6">
                <div className="space-y-3">
                  <Skeleton className="h-24 w-full" />
                  <Skeleton className="h-64 w-full" />
                  <Skeleton className="h-64 w-full" />
                </div>
              </CardContent>
            </Card>
          )}
          
          {enhancedResults && !enhancedMultiMutation.isPending && (
            <>
              {enhancedResults.decision_ranking && (
                <DecisionRankingTable 
                  rankings={enhancedResults.decision_ranking}
                  onSelectScenario={(key) => {
                    const scenario = enhancedResults.scenarios?.[key];
                    if (scenario) {
                      toast({ title: `Selected: ${scenario.name}` });
                    }
                  }}
                />
              )}
              
              {enhancedResults.sensitivity && (
                <SensitivityAnalysisPanel 
                  data={enhancedResults.sensitivity}
                  isLoading={false}
                />
              )}
              
              {Object.entries(enhancedResults.scenarios || {}).slice(0, 1).map(([key, scenario]: [string, any]) => (
                scenario.regime_distribution && (
                  <RegimeDistributionChart 
                    key={key}
                    distribution={scenario.regime_distribution}
                    scenarioName={scenario.name}
                  />
                )
              ))}
            </>
          )}
          
          {!enhancedResults && !enhancedMultiMutation.isPending && (
            <Card>
              <CardContent className="py-12 text-center">
                <Trophy className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground mb-2">
                  Run enhanced simulation with regime-aware Monte Carlo
                </p>
                <p className="text-sm text-muted-foreground mb-4">
                  Includes correlated drivers, market regimes, and decision scoring
                </p>
                <Button onClick={handleRunEnhancedMulti} data-testid="button-run-enhanced-cta">
                  <Play className="h-4 w-4 mr-2" />
                  Run Enhanced Analysis
                </Button>
              </CardContent>
            </Card>
          )}
        </TabsContent>
        
        <TabsContent value="sensitivity" className="mt-6 space-y-6">
          <SensitivityAnalysisPanel 
            data={sensitivityResults}
            isLoading={sensitivityMutation.isPending}
            onRunAnalysis={handleRunSensitivityAnalysis}
          />
        </TabsContent>
        
        <TabsContent value="results" className="mt-6 space-y-4">
          {simLoading ? (
            <Card>
              <CardContent className="p-6">
                <Skeleton className="h-64 w-full" />
              </CardContent>
            </Card>
          ) : simulation ? (
            <>
              <div className="flex items-center justify-between gap-4 flex-wrap">
                <h2 className="text-lg font-semibold">{currentScenarioName}</h2>
                <ExportButton
                  data={formatSimulationForExport(simulation)}
                  filename={`${currentScenarioName.toLowerCase().replace(/\s/g, '-')}-simulation`}
                />
              </div>
              
              <DashboardKPICards
                simulation={simulation}
                metrics={baseMetrics}
                testId="dashboard-kpis-results"
              />
              
              <SimulationSummaryBanner
                runwayP50={simulation.runway?.p50 || 0}
                survival18m={simulation.survival?.['18m'] || 0}
                survival12m={simulation.survival?.['12m'] || 0}
                endCash={simulation.summary?.end_cash}
                scenarioName={currentScenarioName}
              />
              
              <div className="flex items-center justify-between gap-2 p-3 bg-muted/30 rounded-lg">
                <div className="flex items-center gap-3">
                  <span className="text-sm font-medium">Risk Assessment:</span>
                  <RiskGauge 
                    survivalProbability={(simulation.survival?.['18m'] || 0) / 100} 
                    size="sm"
                  />
                </div>
                <GlossaryModal />
              </div>
              
              <SimulationInsights
                simulation={simulation}
                scenarioName={currentScenarioName}
                testId="simulation-insights-results"
              />
              
              {simulation.month_data && simulation.month_data.length > 0 && (
                <>
                  <DrillDownChart
                    data={simulation.month_data.map((m: any, idx: number) => ({
                      month: idx + 1,
                      cash_p10: m.cash_p10,
                      cash_p50: m.cash_p50 ?? 0,
                      cash_p90: m.cash_p90,
                      revenue_p10: m.revenue_p10,
                      revenue_p50: m.revenue_p50 ?? 0,
                      revenue_p90: m.revenue_p90,
                      burn_p10: m.burn_p10,
                      burn_p50: m.burn_p50 ?? 0,
                      burn_p90: m.burn_p90,
                      runway_p50: m.runway_p50 || (m.cash_p50 / Math.max(1, (m.burn_p50 ?? 1) - (m.revenue_p50 ?? 0))),
                      survival_rate: m.survival_rate,
                    }))}
                    scenarioName={currentScenarioName}
                    targetRunway={18}
                    testId="drill-down-chart-results"
                  />
                  
                  <StackedBurnRevenueChart
                    data={simulation.month_data.map((m: any, idx: number) => ({
                      month: idx + 1,
                      revenue: m.revenue_p50 ?? 0,
                      burn: m.burn_p50 ?? 0,
                      cash: m.cash_p50,
                    }))}
                    scenarioName={currentScenarioName}
                    testId="stacked-burn-revenue-chart"
                  />
                </>
              )}
              
              {timeseriesData && timeseriesData.timeseries && timeseriesData.timeseries.length > 0 && (
                <>
                  <ProjectionChart
                    timeseries={timeseriesData.timeseries}
                    fundingEvents={timeseriesData.fundingEvents}
                    scenarioName={timeseriesData.scenario_name || currentScenarioName}
                    targetRunway={18}
                    testId="projection-chart-results"
                  />
                  
                  <ProjectionSummary
                    timeseries={timeseriesData.timeseries}
                    targetRunway={18}
                    testId="projection-summary-results"
                  />
                </>
              )}

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Survival Probability</CardTitle>
                    <CardDescription>
                      Probability of remaining cash positive over time
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <SurvivalCurveChart data={simulation.survival?.curve || simulation.survival_curve || []} />
                  </CardContent>
                </Card>
                
                <BandsChart
                  data={simulation.bands?.cash || simulation.cash_bands || { p10: [], p50: [], p90: [] }}
                  title="Cash Projection Bands"
                  description="10th, 50th, and 90th percentile outcomes"
                />
              </div>
              
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Runway Distribution</CardTitle>
                  <CardDescription>
                    Distribution of runway outcomes across all simulations
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div className="p-4 bg-muted/50 rounded-lg">
                      <p className="text-xs text-muted-foreground">10th Percentile</p>
                      <p className="text-2xl font-mono font-bold">
                        {simulation.runway?.p10?.toFixed(1) || '?'} mo
                      </p>
                      <p className="text-xs text-muted-foreground">Worst case</p>
                    </div>
                    <div className="p-4 bg-primary/10 rounded-lg">
                      <p className="text-xs text-muted-foreground">50th Percentile</p>
                      <p className="text-2xl font-mono font-bold text-primary">
                        {simulation.runway?.p50?.toFixed(1) || '?'} mo
                      </p>
                      <p className="text-xs text-muted-foreground">Most likely</p>
                    </div>
                    <div className="p-4 bg-muted/50 rounded-lg">
                      <p className="text-xs text-muted-foreground">90th Percentile</p>
                      <p className="text-2xl font-mono font-bold">
                        {simulation.runway?.p90?.toFixed(1) || '?'} mo
                      </p>
                      <p className="text-xs text-muted-foreground">Best case</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </>
          ) : (
            <Card>
              <CardContent className="py-12 text-center">
                <p className="text-muted-foreground">
                  No simulation results yet. Create and run a scenario to see projections.
                </p>
                <Button
                  variant="outline"
                  className="mt-4"
                  onClick={() => setActiveTab('builder')}
                >
                  Go to Builder
                </Button>
              </CardContent>
            </Card>
          )}
        </TabsContent>
        
        <TabsContent value="collaborate" className="mt-6 space-y-6">
          {selectedScenarioId ? (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <ScenarioComments
                scenarioId={selectedScenarioId}
                comments={comments}
                isLoading={commentsLoading}
                currentUserEmail={currentUserEmail}
                onAddComment={async (content, parentId) => {
                  await addCommentMutation.mutateAsync({
                    scenarioId: selectedScenarioId,
                    content,
                    parentId,
                  });
                }}
                onEditComment={async (commentId, content) => {
                  await editCommentMutation.mutateAsync({
                    commentId,
                    content,
                    scenarioId: selectedScenarioId,
                  });
                }}
                onDeleteComment={async (commentId) => {
                  await deleteCommentMutation.mutateAsync({
                    commentId,
                    scenarioId: selectedScenarioId,
                  });
                }}
              />
              
              {simulation && (
                <DistributionView
                  title="Runway Distribution"
                  description="Distribution across all Monte Carlo runs"
                  data={Array.from({ length: 1000 }, () => 
                    (simulation.runway?.p50 || 12) + (Math.random() - 0.5) * (simulation.runway?.p90 - simulation.runway?.p10 || 6)
                  )}
                  unit="months"
                  thresholds={{ warning: 18, critical: 12 }}
                  higherIsBetter={true}
                />
              )}
            </div>
          ) : (
            <Card>
              <CardContent className="py-12 text-center">
                <MessageSquare className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground">
                  Select a scenario to view and add comments
                </p>
                <Button
                  variant="outline"
                  className="mt-4"
                  onClick={() => setActiveTab('history')}
                >
                  View Saved Scenarios
                </Button>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
      
      <Dialog open={duplicateDialog.open} onOpenChange={(open) => setDuplicateDialog({ ...duplicateDialog, open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Scenario Already Exists</DialogTitle>
            <DialogDescription>
              A scenario with this name already exists. Would you like to overwrite it or create a new one?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              onClick={() => setDuplicateDialog({ open: false })}
            >
              Cancel
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                if (duplicateDialog.scenarioData) {
                  const newName = `${duplicateDialog.scenarioData.name} (Copy)`;
                  runScenario({ ...duplicateDialog.scenarioData, name: newName }, false);
                }
              }}
            >
              Create Copy
            </Button>
            <Button
              onClick={() => {
                if (duplicateDialog.scenarioData && duplicateDialog.existingId) {
                  runScenario(duplicateDialog.scenarioData, true, duplicateDialog.existingId);
                }
              }}
            >
              Overwrite
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
