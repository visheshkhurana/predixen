import { useState, useMemo } from 'react';
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
import { MonthlyResultsTable } from '@/components/MonthlyResultsTable';
import { ScenarioComparisonChart } from '@/components/ScenarioComparisonChart';
import { MultiScenarioSummary } from '@/components/MultiScenarioSummary';
import { Play, Filter, BarChart3, History, GitCompare, Loader2 } from 'lucide-react';
import { useFounderStore } from '@/store/founderStore';
import { useScenarios, useCreateScenario, useRunSimulation, useSimulation, useMultiScenarioSimulation } from '@/api/hooks';
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
  const { data: scenarios, isLoading: scenariosLoading } = useScenarios(currentCompany?.id || null);
  const createScenarioMutation = useCreateScenario();
  const runSimulationMutation = useRunSimulation();
  
  const [selectedScenarioId, setSelectedScenarioId] = useState<number | null>(null);
  const { data: simulation, isLoading: simLoading } = useSimulation(selectedScenarioId);
  
  const [isCreating, setIsCreating] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [duplicateDialog, setDuplicateDialog] = useState<{ open: boolean; existingId?: number; scenarioData?: any }>({ open: false });
  const [activeTab, setActiveTab] = useState('builder');
  const [tagFilter, setTagFilter] = useState<string[]>([]);
  const [showComparison, setShowComparison] = useState(false);
  
  const multiSimMutation = useMultiScenarioSimulation();
  const [multiSimResults, setMultiSimResults] = useState<any>(null);
  
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
      
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="flex-wrap h-auto gap-1">
          <TabsTrigger value="builder" data-testid="tab-builder">Scenario Builder</TabsTrigger>
          <TabsTrigger value="results" data-testid="tab-results">Simulation Results</TabsTrigger>
          <TabsTrigger value="compare" data-testid="tab-compare">
            <GitCompare className="h-4 w-4 mr-2" />
            Compare All
          </TabsTrigger>
          {scenarios && scenarios.length > 0 && (
            <TabsTrigger value="history" data-testid="tab-history">
              <History className="h-4 w-4 mr-2" />
              Saved ({scenarios.length})
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
                              <span>Survival: {((s.latest_simulation.survival?.['18m'] || 0) * 100).toFixed(0)}%</span>
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
              
              <SimulationSummaryBanner
                runwayP50={simulation.runway?.p50 || 0}
                survival18m={(simulation.survival?.['18m'] || 0) * 100}
                survival12m={(simulation.survival?.['12m'] || 0) * 100}
                endCash={simulation.summary?.end_cash}
                scenarioName={currentScenarioName}
              />
              
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Survival Probability</CardTitle>
                    <CardDescription>
                      Probability of remaining cash positive over time
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <SurvivalCurveChart data={simulation.survival_curve || []} />
                  </CardContent>
                </Card>
                
                <BandsChart
                  data={simulation.cash_bands || { p10: [], p50: [], p90: [] }}
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
