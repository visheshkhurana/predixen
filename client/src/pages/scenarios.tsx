import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Skeleton } from '@/components/ui/skeleton';
import { SurvivalCurveChart } from '@/components/SurvivalCurveChart';
import { BandsChart } from '@/components/BandsChart';
import { Play, Plus } from 'lucide-react';
import { useFounderStore } from '@/store/founderStore';
import { useScenarios, useCreateScenario, useRunSimulation, useSimulation } from '@/api/hooks';
import { useToast } from '@/hooks/use-toast';

const SCENARIO_TEMPLATES = [
  { name: 'Conservative Cut', deltas: { burn_reduction_pct: 20, growth_uplift_pct: -3 } },
  { name: 'Growth Push', deltas: { growth_uplift_pct: 10, burn_reduction_pct: -15 } },
  { name: 'Price Increase', deltas: { pricing_change_pct: 10, growth_uplift_pct: -2 } },
  { name: 'Bridge Round', deltas: { fundraise_month: 3, fundraise_amount: 500000 } },
];

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
  });
  
  const [isCreating, setIsCreating] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  
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
  
  const handleCreateAndRun = async () => {
    if (!currentCompany) return;
    setIsCreating(true);
    
    try {
      const scenario = await createScenarioMutation.mutateAsync({
        companyId: currentCompany.id,
        data: newScenario,
      });
      setSelectedScenarioId(scenario.id);
      
      setIsRunning(true);
      await runSimulationMutation.mutateAsync({ scenarioId: scenario.id, nSims: 1000 });
      setCurrentStep('simulation');
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
      ...template.deltas,
    });
  };
  
  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Scenario Builder</h1>
        <p className="text-muted-foreground">Model different strategies and see their impact</p>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Quick Templates</CardTitle>
              <CardDescription>Start with a preset scenario</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {SCENARIO_TEMPLATES.map((template) => (
                <Button
                  key={template.name}
                  variant="outline"
                  className="w-full justify-start"
                  onClick={() => applyTemplate(template)}
                  data-testid={`template-${template.name.toLowerCase().replace(/\s/g, '-')}`}
                >
                  <Plus className="h-4 w-4 mr-2" />
                  {template.name}
                </Button>
              ))}
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">New Scenario</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Scenario Name</Label>
                <Input
                  value={newScenario.name}
                  onChange={(e) => setNewScenario({ ...newScenario, name: e.target.value })}
                  data-testid="input-scenario-name"
                />
              </div>
              
              <div className="space-y-2">
                <Label>Pricing Change: {newScenario.pricing_change_pct}%</Label>
                <Slider
                  value={[newScenario.pricing_change_pct]}
                  onValueChange={([v]) => setNewScenario({ ...newScenario, pricing_change_pct: v })}
                  min={-20}
                  max={30}
                  step={1}
                  data-testid="slider-pricing"
                />
              </div>
              
              <div className="space-y-2">
                <Label>Growth Uplift: {newScenario.growth_uplift_pct}%</Label>
                <Slider
                  value={[newScenario.growth_uplift_pct]}
                  onValueChange={([v]) => setNewScenario({ ...newScenario, growth_uplift_pct: v })}
                  min={-10}
                  max={20}
                  step={1}
                  data-testid="slider-growth"
                />
              </div>
              
              <div className="space-y-2">
                <Label>Burn Reduction: {newScenario.burn_reduction_pct}%</Label>
                <Slider
                  value={[newScenario.burn_reduction_pct]}
                  onValueChange={([v]) => setNewScenario({ ...newScenario, burn_reduction_pct: v })}
                  min={-20}
                  max={40}
                  step={1}
                  data-testid="slider-burn"
                />
              </div>
              
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-2">
                  <Label>Fundraise Month</Label>
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
                  <Label>Amount ($)</Label>
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
                onClick={handleCreateAndRun}
                disabled={isCreating || isRunning}
                data-testid="button-run-scenario"
              >
                <Play className="h-4 w-4 mr-2" />
                {isCreating || isRunning ? 'Running...' : 'Run Simulation'}
              </Button>
            </CardContent>
          </Card>
          
          {scenarios && scenarios.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Saved Scenarios</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {scenariosLoading ? (
                  <Skeleton className="h-10 w-full" />
                ) : (
                  scenarios.map((s: any) => (
                    <div
                      key={s.id}
                      className="flex items-center justify-between p-2 rounded-lg bg-secondary"
                    >
                      <span className="text-sm font-medium">{s.name}</span>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleRunScenario(s.id)}
                        disabled={isRunning && selectedScenarioId === s.id}
                        data-testid={`button-run-scenario-${s.id}`}
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
        
        <div className="lg:col-span-2 space-y-4">
          {simLoading ? (
            <Card>
              <CardContent className="p-6">
                <Skeleton className="h-64 w-full" />
              </CardContent>
            </Card>
          ) : simulation ? (
            <>
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
                <p className="text-muted-foreground">
                  Configure a scenario and run simulation to see projections
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
