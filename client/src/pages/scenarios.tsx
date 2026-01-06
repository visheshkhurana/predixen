import { useState, useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { SurvivalCurveChart } from '@/components/SurvivalCurveChart';
import { BandsChart } from '@/components/BandsChart';
import { AnnotatedSlider } from '@/components/AnnotatedSlider';
import { ExportButton } from '@/components/ExportButton';
import { ScenarioComparisonTable } from '@/components/ScenarioComparisonTable';
import { SimulationSummaryBanner } from '@/components/SimulationSummaryBanner';
import { SimulationLearnMoreModal } from '@/components/SimulationLearnMoreModal';
import { Play, Plus, Info, Filter, BarChart3 } from 'lucide-react';
import { useFounderStore } from '@/store/founderStore';
import { useScenarios, useCreateScenario, useRunSimulation, useSimulation } from '@/api/hooks';
import { useToast } from '@/hooks/use-toast';
import { SCENARIO_SLIDER_TOOLTIPS } from '@/lib/metricDefinitions';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
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
  
  const [newScenario, setNewScenario] = useState({
    name: 'Custom Scenario',
    pricing_change_pct: 0,
    growth_uplift_pct: 0,
    burn_reduction_pct: 0,
    fundraise_month: null as number | null,
    fundraise_amount: 0,
    gross_margin_delta_pct: 0,
    tags: [] as string[],
  });
  
  const [isCreating, setIsCreating] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [duplicateDialog, setDuplicateDialog] = useState<{ open: boolean; existingId?: number }>({ open: false });
  const [activeTab, setActiveTab] = useState('builder');
  const [tagFilter, setTagFilter] = useState<string[]>([]);
  const [showComparison, setShowComparison] = useState(false);
  
  const filteredTemplates = useMemo(() => {
    if (tagFilter.length === 0) return SCENARIO_TEMPLATES;
    return SCENARIO_TEMPLATES.filter(t => 
      t.tags.some(tag => tagFilter.includes(tag))
    );
  }, [tagFilter]);
  
  const filteredScenarios = useMemo(() => {
    if (!scenarios) return [];
    if (tagFilter.length === 0) return scenarios;
    return scenarios.filter((s: any) => 
      s.tags?.some((tag: string) => tagFilter.includes(tag))
    );
  }, [scenarios, tagFilter]);
  
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
  
  const checkForDuplicate = () => {
    if (!scenarios) return null;
    const existing = scenarios.find((s: any) => 
      s.name.toLowerCase() === newScenario.name.toLowerCase()
    );
    return existing?.id || null;
  };
  
  const handleCreateAndRun = async (overwrite: boolean = false) => {
    if (!currentCompany) return;
    
    const existingId = checkForDuplicate();
    if (existingId && !overwrite) {
      setDuplicateDialog({ open: true, existingId });
      return;
    }
    
    setDuplicateDialog({ open: false });
    setIsCreating(true);
    
    try {
      const scenario = await createScenarioMutation.mutateAsync({
        companyId: currentCompany.id,
        data: {
          ...newScenario,
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
  
  const applyTemplate = (template: typeof SCENARIO_TEMPLATES[0]) => {
    setNewScenario({
      ...newScenario,
      name: template.name,
      pricing_change_pct: 0,
      growth_uplift_pct: 0,
      burn_reduction_pct: 0,
      fundraise_month: null,
      fundraise_amount: 0,
      tags: template.tags,
      ...template.deltas,
    });
    toast({ title: `Applied "${template.name}" template` });
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
    if (!selectedScenarioId || !scenarios) return newScenario.name;
    const selected = scenarios.find((s: any) => s.id === selectedScenarioId);
    return selected?.name || newScenario.name;
  }, [selectedScenarioId, scenarios, newScenario.name]);
  
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
        <TabsList>
          <TabsTrigger value="builder" data-testid="tab-builder">Scenario Builder</TabsTrigger>
          <TabsTrigger value="results" data-testid="tab-results">Simulation Results</TabsTrigger>
        </TabsList>
        
        <TabsContent value="builder" className="mt-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-1 space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Quick Templates</CardTitle>
                  <CardDescription>
                    {filteredTemplates.length} templates available
                    {tagFilter.length > 0 && ` (filtered)`}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-2 max-h-80 overflow-y-auto">
                  {filteredTemplates.map((template) => (
                    <div
                      key={template.name}
                      className="p-3 rounded-lg border hover-elevate cursor-pointer"
                      onClick={() => applyTemplate(template)}
                      data-testid={`template-${template.name.toLowerCase().replace(/\s/g, '-')}`}
                    >
                      <div className="flex items-center justify-between gap-2 flex-wrap">
                        <span className="font-medium text-sm">{template.name}</span>
                        <div className="flex gap-1 flex-wrap">
                          {template.tags.map(tag => (
                            <Badge key={tag} variant="outline" className="text-xs">
                              {tag}
                            </Badge>
                          ))}
                        </div>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">{template.description}</p>
                    </div>
                  ))}
                </CardContent>
              </Card>
              
              {scenarios && scenarios.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Saved Scenarios</CardTitle>
                    <CardDescription>{filteredScenarios.length} scenarios</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-2 max-h-60 overflow-y-auto">
                    {scenariosLoading ? (
                      <Skeleton className="h-10 w-full" />
                    ) : (
                      filteredScenarios.map((s: any) => (
                        <div
                          key={s.id}
                          className="flex items-center justify-between gap-2 p-2 rounded-lg bg-secondary"
                        >
                          <div className="flex-1 min-w-0">
                            <span className="text-sm font-medium truncate block">{s.name}</span>
                            {s.tags && s.tags.length > 0 && (
                              <div className="flex gap-1 mt-1 flex-wrap">
                                {s.tags.slice(0, 2).map((tag: string) => (
                                  <Badge key={tag} variant="outline" className="text-xs">
                                    {tag}
                                  </Badge>
                                ))}
                              </div>
                            )}
                          </div>
                          <Button
                            size="icon"
                            variant="ghost"
                            onClick={() => handleRunScenario(s.id)}
                            disabled={isRunning && selectedScenarioId === s.id}
                            data-testid={`button-run-scenario-${s.id}`}
                            aria-label={`Run ${s.name} scenario`}
                          >
                            <Play className="h-4 w-4" />
                          </Button>
                        </div>
                      ))
                    )}
                  </CardContent>
                </Card>
              )}
            </div>
            
            <div className="lg:col-span-2">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Configure Scenario</CardTitle>
                  <CardDescription>Adjust parameters to model different strategies</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Scenario Name</Label>
                      <Input
                        value={newScenario.name}
                        onChange={(e) => setNewScenario({ ...newScenario, name: e.target.value })}
                        data-testid="input-scenario-name"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Tags</Label>
                      <div className="flex gap-1 flex-wrap">
                        {ALL_TAGS.map(tag => (
                          <Badge
                            key={tag}
                            variant={newScenario.tags.includes(tag) ? 'default' : 'outline'}
                            className="cursor-pointer"
                            onClick={() => {
                              setNewScenario({
                                ...newScenario,
                                tags: newScenario.tags.includes(tag)
                                  ? newScenario.tags.filter(t => t !== tag)
                                  : [...newScenario.tags, tag],
                              });
                            }}
                            data-testid={`tag-${tag}`}
                          >
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <AnnotatedSlider
                      label="Pricing Change"
                      value={newScenario.pricing_change_pct}
                      onChange={(v) => setNewScenario({ ...newScenario, pricing_change_pct: v })}
                      min={-20}
                      max={30}
                      tooltip={SCENARIO_SLIDER_TOOLTIPS.pricing_change_pct?.description}
                      markers={SCENARIO_SLIDER_TOOLTIPS.pricing_change_pct?.markers || []}
                      testId="slider-pricing"
                    />
                    
                    <AnnotatedSlider
                      label="Growth Uplift"
                      value={newScenario.growth_uplift_pct}
                      onChange={(v) => setNewScenario({ ...newScenario, growth_uplift_pct: v })}
                      min={-10}
                      max={20}
                      tooltip={SCENARIO_SLIDER_TOOLTIPS.growth_uplift_pct?.description}
                      markers={SCENARIO_SLIDER_TOOLTIPS.growth_uplift_pct?.markers || []}
                      testId="slider-growth"
                    />
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <AnnotatedSlider
                      label="Burn Reduction"
                      value={newScenario.burn_reduction_pct}
                      onChange={(v) => setNewScenario({ ...newScenario, burn_reduction_pct: v })}
                      min={-20}
                      max={40}
                      tooltip={SCENARIO_SLIDER_TOOLTIPS.burn_reduction_pct?.description}
                      markers={SCENARIO_SLIDER_TOOLTIPS.burn_reduction_pct?.markers || []}
                      testId="slider-burn"
                    />
                    
                    <AnnotatedSlider
                      label="Gross Margin Change"
                      value={newScenario.gross_margin_delta_pct}
                      onChange={(v) => setNewScenario({ ...newScenario, gross_margin_delta_pct: v })}
                      min={-10}
                      max={20}
                      tooltip="Adjustment to gross margin percentage. Positive values improve profitability per dollar of revenue."
                      markers={[
                        { value: -10, label: '-10%' },
                        { value: 0, label: '0' },
                        { value: 10, label: '+10%' },
                        { value: 20, label: '+20%' },
                      ]}
                      testId="slider-margin"
                    />
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <div className="flex items-center gap-1.5">
                        <Label>Fundraise Month</Label>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <button type="button" className="inline-flex" data-testid="tooltip-fundraise-month">
                              <Info className="h-3.5 w-3.5 text-muted-foreground" />
                            </button>
                          </TooltipTrigger>
                          <TooltipContent className="max-w-xs">
                            <p className="text-sm">Month in projection when funding is received (1-24). Leave empty for no fundraise.</p>
                          </TooltipContent>
                        </Tooltip>
                      </div>
                      <Input
                        type="number"
                        value={newScenario.fundraise_month || ''}
                        onChange={(e) => setNewScenario({
                          ...newScenario,
                          fundraise_month: e.target.value ? Number(e.target.value) : null,
                        })}
                        min={1}
                        max={24}
                        placeholder="None"
                        data-testid="input-fundraise-month"
                      />
                    </div>
                    <div className="space-y-2">
                      <div className="flex items-center gap-1.5">
                        <Label>Amount ($)</Label>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <button type="button" className="inline-flex" data-testid="tooltip-fundraise-amount">
                              <Info className="h-3.5 w-3.5 text-muted-foreground" />
                            </button>
                          </TooltipTrigger>
                          <TooltipContent className="max-w-xs">
                            <p className="text-sm">Amount of funding to model (e.g., 500000 for a $500K bridge round).</p>
                          </TooltipContent>
                        </Tooltip>
                      </div>
                      <Input
                        type="number"
                        value={newScenario.fundraise_amount || ''}
                        onChange={(e) => setNewScenario({
                          ...newScenario,
                          fundraise_amount: Number(e.target.value),
                        })}
                        min={0}
                        placeholder="0"
                        data-testid="input-fundraise-amount"
                      />
                    </div>
                  </div>
                  
                  <Button
                    className="w-full"
                    onClick={() => handleCreateAndRun(false)}
                    disabled={isCreating || isRunning}
                    data-testid="button-run-scenario"
                  >
                    <Play className="h-4 w-4 mr-2" />
                    {isCreating || isRunning ? 'Running Simulation...' : 'Run Simulation (1,000 scenarios)'}
                  </Button>
                </CardContent>
              </Card>
            </div>
          </div>
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
              <SimulationSummaryBanner
                runwayP50={simulation.runway?.p50 || 0}
                survival18m={simulation.survival?.['18m'] || 0}
                survival12m={simulation.survival?.['12m'] || 0}
                endCash={simulation.summary?.end_cash}
                scenarioName={currentScenarioName}
              />
              
              <div className="flex justify-end">
                <ExportButton
                  data={simulation}
                  filename={`simulation-${currentScenarioName.toLowerCase().replace(/\s+/g, '-')}`}
                  formatForCSV={formatSimulationForExport}
                  testId="export-simulation"
                />
              </div>
              
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card className="overflow-visible">
                  <CardContent className="p-4">
                    <p className="text-sm text-muted-foreground">Runway P50</p>
                    <p className="text-2xl font-bold font-mono" data-testid="text-sim-runway">
                      {simulation.runway?.p50?.toFixed(1)} mo
                    </p>
                  </CardContent>
                </Card>
                <Card className="overflow-visible">
                  <CardContent className="p-4">
                    <p className="text-sm text-muted-foreground">Survival 12m</p>
                    <p className="text-2xl font-bold font-mono" data-testid="text-sim-survival-12">
                      {simulation.survival?.['12m']?.toFixed(0)}%
                    </p>
                  </CardContent>
                </Card>
                <Card className="overflow-visible">
                  <CardContent className="p-4">
                    <p className="text-sm text-muted-foreground">Survival 18m</p>
                    <p className="text-2xl font-bold font-mono" data-testid="text-sim-survival-18">
                      {simulation.survival?.['18m']?.toFixed(0)}%
                    </p>
                  </CardContent>
                </Card>
                <Card className="overflow-visible">
                  <CardContent className="p-4">
                    <p className="text-sm text-muted-foreground">Revenue @18m</p>
                    <p className="text-2xl font-bold font-mono" data-testid="text-sim-revenue">
                      ${(simulation.summary?.revenue_18m_median / 1000).toFixed(0)}k
                    </p>
                  </CardContent>
                </Card>
              </div>
              
              {simulation.survival?.curve && (
                <SurvivalCurveChart
                  data={simulation.survival.curve}
                  title="Survival Probability"
                  testId="chart-sim-survival"
                />
              )}
              
              {simulation.bands?.revenue && (
                <BandsChart
                  data={simulation.bands.revenue}
                  title="Revenue Projection (P10/P50/P90)"
                  testId="chart-sim-revenue"
                />
              )}
              
              {simulation.bands?.cash && (
                <BandsChart
                  data={simulation.bands.cash}
                  title="Cash Balance"
                  testId="chart-sim-cash"
                />
              )}
            </>
          ) : (
            <Card>
              <CardContent className="py-12 text-center">
                <h2 className="text-xl font-semibold mb-2">No Simulation Results</h2>
                <p className="text-muted-foreground mb-4">
                  Configure a scenario and run simulation to see projections
                </p>
                <Button onClick={() => setActiveTab('builder')}>
                  Go to Scenario Builder
                </Button>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
      
      <Dialog open={duplicateDialog.open} onOpenChange={(open) => setDuplicateDialog({ open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Scenario Already Exists</DialogTitle>
            <DialogDescription>
              A scenario named "{newScenario.name}" already exists. Would you like to overwrite it or rename your scenario?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setDuplicateDialog({ open: false })}>
              Rename
            </Button>
            <Button onClick={() => handleCreateAndRun(true)}>
              Overwrite
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
