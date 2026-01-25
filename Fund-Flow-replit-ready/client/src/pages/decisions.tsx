import { useState, useEffect, useRef, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Progress } from '@/components/ui/progress';
import { DecisionCard, DecisionStatus } from '@/components/DecisionCard';
import { SurvivalCurveChart } from '@/components/SurvivalCurveChart';
import { BandsChart } from '@/components/BandsChart';
import { 
  RefreshCw, ArrowRight, Trophy, TrendingUp, Clock, 
  BarChart3, HelpCircle, Calendar, Target, Zap, Scale
} from 'lucide-react';
import { useFounderStore } from '@/store/founderStore';
import { useDecisions, useSimulation, useScenarios, useGenerateDecisions, useRunSimulation, useCreateScenario } from '@/api/hooks';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';

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

function normalizeRecommendation(rec: any): any {
  const expectedImpact = rec.expected_impact || {
    delta_survival_18m: rec.details?.survival_18m_delta || 0,
    delta_runway_p50: rec.details?.runway_delta || 0,
  };
  
  const risks = rec.risks || rec.details?.suggested_cuts || [];
  const rationale = rec.rationale || rec.impact_summary || '';
  const keyAssumption = rec.key_assumption || `Assumes ${rec.effort || 'medium'} effort over ${rec.timeline || '2-4 weeks'}`;
  
  return {
    ...rec,
    id: rec.id || rec.action_id || `rec-${rec.rank}`,
    expected_impact: expectedImpact,
    risks: Array.isArray(risks) ? risks : [risks],
    rationale,
    key_assumption: keyAssumption,
  };
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

function ComparisonBar({ 
  recommendations 
}: { 
  recommendations: any[] 
}) {
  if (!Array.isArray(recommendations) || recommendations.length < 2) return null;

  const maxSurvival = Math.max(...recommendations.map(r => Math.abs(r.expected_impact?.delta_survival_18m || 0)));
  const maxRunway = Math.max(...recommendations.map(r => Math.abs(r.expected_impact?.delta_runway_p50 || 0)));

  return (
    <Card className="mb-6">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <Scale className="h-5 w-5 text-primary" />
          <CardTitle className="text-lg">Quick Comparison</CardTitle>
          <Tooltip>
            <TooltipTrigger asChild>
              <HelpCircle className="h-4 w-4 text-muted-foreground cursor-help" />
            </TooltipTrigger>
            <TooltipContent className="max-w-xs">
              <p className="text-sm">Compare all options at a glance. Green bars show positive impact, red shows negative. Longer bars indicate larger effects.</p>
            </TooltipContent>
          </Tooltip>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <p className="text-sm font-medium text-muted-foreground mb-3 flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              Survival Impact (18 months)
            </p>
            <div className="space-y-3">
              {recommendations.map((rec, idx) => {
                const value = rec.expected_impact.delta_survival_18m;
                const isPositive = value >= 0;
                const percentage = maxSurvival > 0 ? (Math.abs(value) / maxSurvival) * 100 : 0;
                
                return (
                  <div key={rec.id} className="space-y-1">
                    <div className="flex items-center justify-between text-sm">
                      <span className="flex items-center gap-2">
                        {idx === 0 && <Trophy className="h-4 w-4 text-emerald-500" />}
                        {idx === 1 && <Target className="h-4 w-4 text-primary" />}
                        {idx === 2 && <Zap className="h-4 w-4 text-slate-400" />}
                        <span className="truncate max-w-[200px]">{rec.title}</span>
                      </span>
                      <span className={cn(
                        "font-mono font-semibold",
                        isPositive ? "text-emerald-500" : "text-red-500"
                      )}>
                        {isPositive ? '+' : ''}{value.toFixed(1)}%
                      </span>
                    </div>
                    <div className="h-2 bg-secondary rounded-full overflow-hidden">
                      <div 
                        className={cn(
                          "h-full rounded-full transition-all duration-700",
                          isPositive ? "bg-emerald-500" : "bg-red-500"
                        )}
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
          
          <div>
            <p className="text-sm font-medium text-muted-foreground mb-3 flex items-center gap-2">
              <Clock className="h-4 w-4" />
              Runway Change (months)
            </p>
            <div className="space-y-3">
              {recommendations.map((rec, idx) => {
                const value = rec.expected_impact.delta_runway_p50;
                const isPositive = value >= 0;
                const percentage = maxRunway > 0 ? (Math.abs(value) / maxRunway) * 100 : 0;
                
                return (
                  <div key={rec.id} className="space-y-1">
                    <div className="flex items-center justify-between text-sm">
                      <span className="flex items-center gap-2">
                        {idx === 0 && <Trophy className="h-4 w-4 text-emerald-500" />}
                        {idx === 1 && <Target className="h-4 w-4 text-primary" />}
                        {idx === 2 && <Zap className="h-4 w-4 text-slate-400" />}
                        <span className="truncate max-w-[200px]">{rec.title}</span>
                      </span>
                      <span className={cn(
                        "font-mono font-semibold",
                        isPositive ? "text-emerald-500" : "text-red-500"
                      )}>
                        {isPositive ? '+' : ''}{value.toFixed(1)} mo
                      </span>
                    </div>
                    <div className="h-2 bg-secondary rounded-full overflow-hidden">
                      <div 
                        className={cn(
                          "h-full rounded-full transition-all duration-700",
                          isPositive ? "bg-emerald-500" : "bg-red-500"
                        )}
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function MilestoneTimeline({ recommendations }: { recommendations: any[] }) {
  const milestones = useMemo(() => {
    const events: { week: number; event: string; type: 'decision' | 'milestone' }[] = [];
    
    if (!Array.isArray(recommendations)) return events;
    
    recommendations.forEach((rec, idx) => {
      const weekStart = idx === 0 ? 1 : idx === 1 ? 2 : 4;
      events.push({
        week: weekStart,
        event: `Begin: ${rec.title}`,
        type: 'decision',
      });
    });
    
    events.push({ week: 6, event: 'First results checkpoint', type: 'milestone' });
    events.push({ week: 12, event: 'Quarterly review', type: 'milestone' });
    
    return events.sort((a, b) => a.week - b.week);
  }, [recommendations]);

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <Calendar className="h-5 w-5 text-primary" />
          <CardTitle className="text-lg">Implementation Timeline</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <div className="relative">
          <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-border" />
          <div className="space-y-4">
            {milestones.map((milestone, idx) => (
              <div key={idx} className="flex items-start gap-4 pl-2">
                <div className={cn(
                  "w-5 h-5 rounded-full flex items-center justify-center z-10",
                  milestone.type === 'decision' ? "bg-primary" : "bg-emerald-500"
                )}>
                  <div className="w-2 h-2 rounded-full bg-white" />
                </div>
                <div className="flex-1 pb-2">
                  <p className="text-xs text-muted-foreground">Week {milestone.week}</p>
                  <p className="text-sm font-medium">{milestone.event}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
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

  const recommendationsData = decisions?.recommendations;
  const rawRecommendations = Array.isArray(recommendationsData) 
    ? recommendationsData 
    : Array.isArray(recommendationsData?.recommendations) 
      ? recommendationsData.recommendations 
      : [];
  const recommendations = rawRecommendations.map(normalizeRecommendation);
  
  const maxImpactValues = useMemo(() => {
    if (!Array.isArray(recommendations) || recommendations.length === 0) {
      return { survival: 20, runway: 12 };
    }
    const survivalValues = recommendations.map((r: any) => Math.abs(r.expected_impact?.delta_survival_18m || 0));
    const runwayValues = recommendations.map((r: any) => Math.abs(r.expected_impact?.delta_runway_p50 || 0));
    return {
      survival: Math.max(20, ...survivalValues),
      runway: Math.max(12, ...runwayValues),
    };
  }, [recommendations]);

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

    if (!Array.isArray(recommendations) || recommendations.length === 0 || previousRecs.length === 0) {
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
    
    toast({
      title: 'Status Updated',
      description: `Decision marked as ${status}`,
    });
  };

  const handleAdoptPlan = (rec: any) => {
    handleStatusChange(rec.id, 'adopted');
    toast({
      title: 'Plan Adopted',
      description: `"${rec.title}" has been marked as your chosen strategy.`,
    });
  };

  const handleRunScenario = (rec: any) => {
    toast({
      title: 'Running Scenario',
      description: `Simulating "${rec.title}" with current assumptions...`,
    });
  };

  const handleRefineAssumptions = (recId: string, assumptions: Record<string, number>) => {
    console.log('Refining assumptions for', recId, assumptions);
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
      toast({ title: 'Decisions generated!', description: 'New recommendations are ready for review.' });
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
  
  const survivalCurve = simulation?.survival?.curve || [];
  const bands = simulation?.bands || {};
  
  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-3xl font-bold">Decision Recommendations</h1>
          <p className="text-muted-foreground mt-1">
            Top 3 strategic actions ranked by expected impact on survival and growth
          </p>
        </div>
        <Button
          onClick={handleGenerateDecisions}
          disabled={isGenerating}
          size="lg"
          data-testid="button-generate-decisions"
        >
          {isGenerating ? (
            <>
              <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
              Analyzing...
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
        <div className="space-y-6">
          <Card>
            <CardContent className="p-6">
              <Skeleton className="h-6 w-48 mb-4" />
              <div className="grid grid-cols-2 gap-6">
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-24 w-full" />
              </div>
            </CardContent>
          </Card>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {Array(3).fill(0).map((_, i) => (
              <Card key={i} className="overflow-visible">
                <CardContent className="p-6">
                  <Skeleton className="h-8 w-24 mb-4" />
                  <Skeleton className="h-6 w-full mb-2" />
                  <Skeleton className="h-4 w-3/4 mb-4" />
                  <Skeleton className="h-24 w-full mb-4" />
                  <Skeleton className="h-10 w-32" />
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      ) : recommendations.length > 0 ? (
        <>
          <ComparisonBar recommendations={recommendations} />
          
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
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
                onAdoptPlan={() => handleAdoptPlan(rec)}
                onRunScenario={() => handleRunScenario(rec)}
                onRefineAssumptions={(assumptions) => handleRefineAssumptions(rec.id, assumptions)}
                isNew={newIds.has(rec.id)}
                isChanged={changedIds.has(rec.id)}
                maxSurvivalImpact={maxImpactValues.survival}
                maxRunwayChange={maxImpactValues.runway}
                testId={`decision-${rec.rank}`}
              />
            ))}
          </div>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <MilestoneTimeline recommendations={recommendations} />
            
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5 text-primary" />
                  <CardTitle className="text-lg">Key Performance Indicators</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                    <p className="text-xs text-muted-foreground mb-1">Best Survival Impact</p>
                    <p className="text-2xl font-bold text-emerald-500">
                      +{(recommendations.length > 0 ? Math.max(...recommendations.map((r: any) => r.expected_impact?.delta_survival_18m || 0)) : 0).toFixed(1)}%
                    </p>
                  </div>
                  <div className="p-4 rounded-xl bg-primary/10 border border-primary/20">
                    <p className="text-xs text-muted-foreground mb-1">Best Runway Extension</p>
                    <p className="text-2xl font-bold text-primary">
                      +{(recommendations.length > 0 ? Math.max(...recommendations.map((r: any) => r.expected_impact?.delta_runway_p50 || 0)) : 0).toFixed(1)} mo
                    </p>
                  </div>
                  <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20">
                    <p className="text-xs text-muted-foreground mb-1">Decisions Pending</p>
                    <p className="text-2xl font-bold text-amber-500">
                      {recommendations.length > 0 ? recommendations.filter((r: any) => (decisionStatuses[r.id] || 'pending') === 'pending').length : 0}
                    </p>
                  </div>
                  <div className="p-4 rounded-xl bg-secondary">
                    <p className="text-xs text-muted-foreground mb-1">Plans Adopted</p>
                    <p className="text-2xl font-bold">
                      {recommendations.length > 0 ? recommendations.filter((r: any) => decisionStatuses[r.id] === 'adopted').length : 0}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
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
        <Card className="border-dashed border-2">
          <CardContent className="py-16 text-center">
            <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
              <BarChart3 className="h-8 w-8 text-primary" />
            </div>
            <h2 className="text-2xl font-bold mb-2">No Decisions Yet</h2>
            <p className="text-muted-foreground mb-6 max-w-md mx-auto">
              Run a Monte Carlo simulation to generate AI-powered recommendations ranked by expected impact on your survival and growth.
            </p>
            <Button 
              onClick={handleGenerateDecisions} 
              disabled={isGenerating} 
              size="lg"
              data-testid="button-first-decision"
            >
              {isGenerating ? 'Generating...' : 'Generate Decisions'}
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
