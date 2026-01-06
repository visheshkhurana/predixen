import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { DecisionCard } from '@/components/DecisionCard';
import { SurvivalCurveChart } from '@/components/SurvivalCurveChart';
import { BandsChart } from '@/components/BandsChart';
import { RefreshCw, ArrowRight } from 'lucide-react';
import { useFounderStore } from '@/store/founderStore';
import { useDecisions, useSimulation, useScenarios, useGenerateDecisions, useRunSimulation, useCreateScenario } from '@/api/hooks';
import { useToast } from '@/hooks/use-toast';

export default function DecisionsPage() {
  const { currentCompany, setCurrentStep } = useFounderStore();
  const { toast } = useToast();
  const { data: scenarios } = useScenarios(currentCompany?.id || null);
  const latestScenarioId = scenarios?.[0]?.id;
  const { data: simulation } = useSimulation(latestScenarioId || null);
  const { data: decisions, isLoading, refetch } = useDecisions(currentCompany?.id || null);
  
  const createScenarioMutation = useCreateScenario();
  const runSimulationMutation = useRunSimulation();
  const generateDecisionsMutation = useGenerateDecisions();
  
  const [isGenerating, setIsGenerating] = useState(false);
  
  const handleGenerateDecisions = async () => {
    if (!currentCompany) return;
    setIsGenerating(true);
    
    try {
      let scenarioId = latestScenarioId;
      
      if (!scenarioId) {
        const scenario = await createScenarioMutation.mutateAsync({
          companyId: currentCompany.id,
          data: { name: 'Baseline Scenario' },
        });
        scenarioId = scenario.id;
      }
      
      const simResult = await runSimulationMutation.mutateAsync({ scenarioId, nSims: 1000 });
      await generateDecisionsMutation.mutateAsync(simResult.id);
      
      await refetch();
      setCurrentStep('decision');
      toast({ title: 'Decisions generated!' });
    } catch (err: any) {
      toast({ title: 'Error', description: err.message, variant: 'destructive' });
    } finally {
      setIsGenerating(false);
    }
  };
  
  if (!currentCompany) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">Select a company to view decisions</p>
          </CardContent>
        </Card>
      </div>
    );
  }
  
  const recommendations = decisions?.recommendations || [];
  const survivalCurve = simulation?.survival?.curve || [];
  const bands = simulation?.bands || {};
  
  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold">Decision Recommendations</h1>
          <p className="text-muted-foreground">Top 3 actions ranked by expected impact</p>
        </div>
        <Button
          onClick={handleGenerateDecisions}
          disabled={isGenerating}
          data-testid="button-generate-decisions"
        >
          {isGenerating ? (
            <>
              <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <RefreshCw className="h-4 w-4 mr-2" />
              Regenerate Decisions
            </>
          )}
        </Button>
      </div>
      
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Array(3).fill(0).map((_, i) => (
            <Card key={i} className="overflow-visible">
              <CardContent className="p-6">
                <Skeleton className="h-6 w-32 mb-4" />
                <Skeleton className="h-4 w-full mb-2" />
                <Skeleton className="h-4 w-3/4 mb-4" />
                <Skeleton className="h-20 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : recommendations.length > 0 ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {recommendations.map((rec: any) => (
              <DecisionCard
                key={rec.id}
                rank={rec.rank}
                title={rec.title}
                rationale={rec.rationale}
                expectedImpact={rec.expected_impact}
                risks={rec.risks}
                keyAssumption={rec.key_assumption}
                testId={`decision-${rec.rank}`}
              />
            ))}
          </div>
          
          {simulation && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {survivalCurve.length > 0 && (
                <SurvivalCurveChart
                  data={survivalCurve}
                  title="Baseline Survival Curve"
                  testId="chart-survival"
                />
              )}
              
              {bands.revenue && (
                <BandsChart
                  data={bands.revenue}
                  title="Revenue Projection (P10/P50/P90)"
                  testId="chart-revenue-bands"
                />
              )}
              
              {bands.cash && (
                <BandsChart
                  data={bands.cash}
                  title="Cash Balance Projection"
                  testId="chart-cash-bands"
                />
              )}
              
              {bands.burn && (
                <BandsChart
                  data={bands.burn}
                  title="Monthly Burn Projection"
                  testId="chart-burn-bands"
                />
              )}
            </div>
          )}
        </>
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <h2 className="text-xl font-semibold mb-2">No Decisions Yet</h2>
            <p className="text-muted-foreground mb-4">
              Run a simulation to generate ranked recommendations
            </p>
            <Button onClick={handleGenerateDecisions} disabled={isGenerating} data-testid="button-first-decision">
              {isGenerating ? 'Generating...' : 'Generate Decisions'}
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
