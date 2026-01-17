import { useState, useEffect, useRef } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { DecisionCard, DecisionStatus } from '@/components/DecisionCard';
import { SurvivalCurveChart } from '@/components/SurvivalCurveChart';
import { BandsChart } from '@/components/BandsChart';
import { RefreshCw, ArrowRight } from 'lucide-react';
import { useFounderStore } from '@/store/founderStore';
import { useDecisions, useSimulation, useScenarios, useGenerateDecisions, useRunSimulation, useCreateScenario } from '@/api/hooks';
import { useToast } from '@/hooks/use-toast';

interface StoredDecisionStatus {
  [decisionId: string]: DecisionStatus;
}

interface PreviousRecommendation {
  id: string;
  title: string;
  rank: number;
  expectedImpact: {
    delta_survival_18m: number;
    delta_runway_p50: number;
  };
}

const STORAGE_KEY_PREFIX = 'decision_statuses_';
const PREV_RECS_KEY_PREFIX = 'prev_recommendations_';

function getStorageKey(companyId: number): string {
  return `${STORAGE_KEY_PREFIX}${companyId}`;
}

function getPrevRecsKey(companyId: number): string {
  return `${PREV_RECS_KEY_PREFIX}${companyId}`;
}

function loadDecisionStatuses(companyId: number): StoredDecisionStatus {
  try {
    const stored = localStorage.getItem(getStorageKey(companyId));
    return stored ? JSON.parse(stored) : {};
  } catch {
    return {};
  }
}

function saveDecisionStatuses(companyId: number, statuses: StoredDecisionStatus): void {
  try {
    localStorage.setItem(getStorageKey(companyId), JSON.stringify(statuses));
  } catch {
    console.warn('Failed to save decision statuses to localStorage');
  }
}

function loadPreviousRecommendations(companyId: number): PreviousRecommendation[] {
  try {
    const stored = localStorage.getItem(getPrevRecsKey(companyId));
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
}

function savePreviousRecommendations(companyId: number, recs: PreviousRecommendation[]): void {
  try {
    localStorage.setItem(getPrevRecsKey(companyId), JSON.stringify(recs));
  } catch {
    console.warn('Failed to save previous recommendations to localStorage');
  }
}

function getTimeHorizon(rank: number): string {
  switch (rank) {
    case 1: return '1-2 weeks';
    case 2: return '2-4 weeks';
    case 3: return '4-8 weeks';
    default: return '2-4 weeks';
  }
}

function getDependencies(title: string): string[] {
  const lowerTitle = title.toLowerCase();
  if (lowerTitle.includes('hire') || lowerTitle.includes('team')) {
    return ['Budget approval', 'Job description finalization', 'Interview process setup'];
  }
  if (lowerTitle.includes('revenue') || lowerTitle.includes('sales')) {
    return ['Sales team capacity', 'Marketing materials', 'CRM setup'];
  }
  if (lowerTitle.includes('cost') || lowerTitle.includes('expense') || lowerTitle.includes('reduce')) {
    return ['Vendor contract review', 'Team communication plan'];
  }
  if (lowerTitle.includes('fund') || lowerTitle.includes('raise')) {
    return ['Pitch deck update', 'Financial model preparation', 'Investor list'];
  }
  return [];
}

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
  const [decisionStatuses, setDecisionStatuses] = useState<StoredDecisionStatus>({});
  const [previousRecs, setPreviousRecs] = useState<PreviousRecommendation[]>([]);
  const [changedIds, setChangedIds] = useState<Set<string>>(new Set());
  const [newIds, setNewIds] = useState<Set<string>>(new Set());
  const hasInitialized = useRef(false);

  useEffect(() => {
    if (currentCompany && !hasInitialized.current) {
      const loadedStatuses = loadDecisionStatuses(currentCompany.id);
      const loadedPrevRecs = loadPreviousRecommendations(currentCompany.id);
      setDecisionStatuses(loadedStatuses);
      setPreviousRecs(loadedPrevRecs);
      hasInitialized.current = true;
    }
  }, [currentCompany]);

  useEffect(() => {
    if (!hasInitialized.current) return;

    const recommendations = decisions?.recommendations || [];
    if (recommendations.length === 0 || previousRecs.length === 0) {
      setChangedIds(new Set());
      setNewIds(new Set());
      return;
    }

    const prevMap = new Map(previousRecs.map(r => [r.id, r]));
    const prevTitles = new Set(previousRecs.map(r => r.title));
    
    const newSet = new Set<string>();
    const changedSet = new Set<string>();

    for (const rec of recommendations) {
      const prevRec = prevMap.get(rec.id);
      
      if (!prevRec && !prevTitles.has(rec.title)) {
        newSet.add(rec.id);
      } else if (prevRec) {
        const prevImpact = prevRec.expectedImpact;
        const currImpact = rec.expected_impact;
        if (
          prevRec.rank !== rec.rank ||
          Math.abs(prevImpact.delta_survival_18m - currImpact.delta_survival_18m) > 0.1 ||
          Math.abs(prevImpact.delta_runway_p50 - currImpact.delta_runway_p50) > 0.1
        ) {
          changedSet.add(rec.id);
        }
      }
    }

    setNewIds(newSet);
    setChangedIds(changedSet);
  }, [decisions, previousRecs]);
  
  const handleStatusChange = (decisionId: string, status: DecisionStatus) => {
    if (!currentCompany) return;
    
    const updated = { ...decisionStatuses, [decisionId]: status };
    setDecisionStatuses(updated);
    saveDecisionStatuses(currentCompany.id, updated);
  };

  const handleGenerateDecisions = async () => {
    if (!currentCompany) return;
    setIsGenerating(true);
    
    const currentRecs = decisions?.recommendations || [];
    if (currentRecs.length > 0) {
      const prevRecsData: PreviousRecommendation[] = currentRecs.map((r: any) => ({
        id: r.id,
        title: r.title,
        rank: r.rank,
        expectedImpact: r.expected_impact,
      }));
      setPreviousRecs(prevRecsData);
      savePreviousRecommendations(currentCompany.id, prevRecsData);
    }
    
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
      const message = err.message || 'Something went wrong';
      if (message.includes('authentication') || message.includes('credentials') || err.status === 401) {
        toast({ 
          title: 'Session Expired', 
          description: 'Please sign in again to continue.',
          variant: 'destructive' 
        });
      } else {
        toast({ title: 'Error', description: message, variant: 'destructive' });
      }
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
                id={rec.id}
                rank={rec.rank}
                title={rec.title}
                rationale={rec.rationale}
                expectedImpact={rec.expected_impact}
                risks={rec.risks}
                keyAssumption={rec.key_assumption}
                timeHorizon={getTimeHorizon(rec.rank)}
                dependencies={getDependencies(rec.title)}
                detailedRiskFactors={rec.detailed_risks || rec.risks}
                runwayImpactDetails={rec.runway_impact_details}
                survivalImpactDetails={rec.survival_impact_details}
                status={decisionStatuses[rec.id] || 'pending'}
                onStatusChange={(status) => handleStatusChange(rec.id, status)}
                isNew={newIds.has(rec.id)}
                isChanged={changedIds.has(rec.id)}
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
