import { useState, useEffect, useRef } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { RefreshCw, ArrowRight, Brain } from 'lucide-react';
import { useFounderStore } from '@/store/founderStore';
import { useDecisions, useScenarios, useGenerateDecisions, useRunSimulation, useCreateScenario, useStrategicDiagnosis } from '@/api/hooks';
import { useToast } from '@/hooks/use-toast';

export default function DecisionsPage() {
  const { currentCompany, setCurrentStep } = useFounderStore();
  const { toast } = useToast();
  const { data: scenarios } = useScenarios(currentCompany?.id || null);
  const latestScenarioId = scenarios?.[0]?.id;
  const { data: decisions, isLoading, refetch } = useDecisions(currentCompany?.id || null);

  const createScenarioMutation = useCreateScenario();
  const runSimulationMutation = useRunSimulation();
  const generateDecisionsMutation = useGenerateDecisions();
  const strategicDiagnosisMutation = useStrategicDiagnosis();

  const [isGenerating, setIsGenerating] = useState(false);
  const [diagnosisData, setDiagnosisData] = useState<any>(null);
  const hasInitialized = useRef(false);

  const recommendationsData = decisions?.recommendations;
  const rawRecommendations = Array.isArray(recommendationsData)
    ? recommendationsData
    : Array.isArray(recommendationsData?.recommendations)
      ? recommendationsData.recommendations
      : [];

  useEffect(() => {
    if (currentCompany && !hasInitialized.current) {
      hasInitialized.current = true;
    }
  }, [currentCompany]);

  const [diagnosisError, setDiagnosisError] = useState(false);
  const diagnosisFetchedRef = useRef(false);
  const lastCompanyIdRef = useRef<number | null>(null);

  useEffect(() => {
    const companyId = currentCompany?.id || null;
    if (companyId !== lastCompanyIdRef.current) {
      lastCompanyIdRef.current = companyId;
      diagnosisFetchedRef.current = false;
      setDiagnosisData(null);
      setDiagnosisError(false);
    }
  }, [currentCompany]);

  useEffect(() => {
    if (
      currentCompany &&
      rawRecommendations.length > 0 &&
      !diagnosisData &&
      !diagnosisError &&
      !diagnosisFetchedRef.current &&
      !strategicDiagnosisMutation.isPending
    ) {
      diagnosisFetchedRef.current = true;
      strategicDiagnosisMutation.mutate(currentCompany.id, {
        onSuccess: (data) => {
          setDiagnosisData(data);
          setDiagnosisError(false);
        },
        onError: () => {
          diagnosisFetchedRef.current = false;
          setDiagnosisError(true);
        },
      });
    }
  }, [currentCompany, rawRecommendations.length, diagnosisData, diagnosisError]);

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

      setDiagnosisError(false);
      diagnosisFetchedRef.current = true;
      strategicDiagnosisMutation.mutate(currentCompany.id, {
        onSuccess: (data) => {
          setDiagnosisData(data);
          setDiagnosisError(false);
        },
        onError: () => {
          diagnosisFetchedRef.current = false;
          setDiagnosisError(true);
        },
      });

      await refetch();
      setCurrentStep('decision');
      toast({ title: 'Briefing generated', description: 'Your strategic briefing is ready.' });
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

  const handleRefreshDiagnosis = () => {
    if (!currentCompany) return;
    setDiagnosisError(false);
    diagnosisFetchedRef.current = true;
    strategicDiagnosisMutation.mutate(currentCompany.id, {
      onSuccess: (data) => {
        setDiagnosisData(data);
        setDiagnosisError(false);
      },
      onError: () => {
        diagnosisFetchedRef.current = false;
        setDiagnosisError(true);
      },
    });
  };

  if (!currentCompany) {
    return (
      <div className="p-6 max-w-3xl mx-auto">
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground" data-testid="text-no-company">Select a company to view your strategic briefing.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const hasBriefing = rawRecommendations.length > 0;
  const isAnalyzing = strategicDiagnosisMutation.isPending;

  const situationNarrative = diagnosisData?.situation_narrative || diagnosisData?.diagnosis_narrative || null;
  const recommendationHeadline = diagnosisData?.recommendation_headline || null;
  const recommendationNarrative = diagnosisData?.recommendation_narrative || null;
  const urgencyText = diagnosisData?.urgency_text || null;
  const inactionNarrative = diagnosisData?.inaction_narrative || null;
  const inactionProjection = diagnosisData?.inaction_projection || null;
  const executionPlaybook: Array<{phase?: string; action: string; owner: string; timeline: string; definition_of_done?: string; expected_outcome?: string}> | null = diagnosisData?.execution_playbook || null;

  return (
    <div className="p-6 max-w-3xl mx-auto" data-testid="page-decisions">
      <header className="mb-10">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <p className="text-xs uppercase tracking-widest text-muted-foreground mb-2" data-testid="text-document-label">
              Strategic Briefing
            </p>
            <h1 className="text-3xl font-bold tracking-tight" data-testid="text-page-title">
              {currentCompany.name}
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              {diagnosisData?.generated_at
                ? `Prepared ${new Date(diagnosisData.generated_at).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}`
                : 'Founder\u2019s Briefing Document'}
            </p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {hasBriefing && (
              <Button
                variant="outline"
                onClick={handleRefreshDiagnosis}
                disabled={isAnalyzing}
                data-testid="button-refresh-diagnosis"
              >
                {isAnalyzing ? (
                  <>
                    <Brain className="h-4 w-4 mr-2 animate-spin" />
                    Updating...
                  </>
                ) : (
                  <>
                    <Brain className="h-4 w-4 mr-2" />
                    Refresh Briefing
                  </>
                )}
              </Button>
            )}
            <Button
              onClick={handleGenerateDecisions}
              disabled={isGenerating}
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
                  {hasBriefing ? 'Regenerate Briefing' : 'Generate Briefing'}
                </>
              )}
            </Button>
          </div>
        </div>
        {hasBriefing && (
          <div className="mt-6 border-b border-border" />
        )}
      </header>

      {isLoading ? (
        <div className="space-y-8">
          <div>
            <Skeleton className="h-5 w-40 mb-4" />
            <Skeleton className="h-4 w-full mb-2" />
            <Skeleton className="h-4 w-full mb-2" />
            <Skeleton className="h-4 w-5/6 mb-2" />
            <Skeleton className="h-4 w-4/6" />
          </div>
          <div>
            <Skeleton className="h-5 w-56 mb-4" />
            <Skeleton className="h-4 w-full mb-2" />
            <Skeleton className="h-4 w-full mb-2" />
            <Skeleton className="h-4 w-full mb-2" />
            <Skeleton className="h-4 w-3/4" />
          </div>
        </div>
      ) : hasBriefing ? (
        <article className="space-y-10" data-testid="article-briefing">

          {diagnosisError && !isAnalyzing && !diagnosisData && (
            <div className="text-center py-8" data-testid="section-diagnosis-error">
              <p className="text-sm text-muted-foreground mb-4">
                The strategic analysis could not be loaded. Click below to try again.
              </p>
              <Button
                variant="outline"
                onClick={handleRefreshDiagnosis}
                data-testid="button-retry-diagnosis"
              >
                <Brain className="h-4 w-4 mr-2" />
                Retry Analysis
              </Button>
            </div>
          )}

          {(situationNarrative || isAnalyzing) && (
            <section data-testid="section-situation">
              <h2 className="text-lg font-semibold mb-4 tracking-tight" data-testid="text-section-1-title">
                The Situation
              </h2>
              {isAnalyzing ? (
                <div className="space-y-2">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-5/6" />
                  <Skeleton className="h-4 w-4/6" />
                </div>
              ) : (
                <div className="space-y-4">
                  {situationNarrative.split('\n\n').map((paragraph: string, i: number) => (
                    <p
                      key={i}
                      className="text-sm leading-relaxed text-muted-foreground"
                      data-testid={`text-situation-p${i}`}
                    >
                      {paragraph}
                    </p>
                  ))}
                </div>
              )}
            </section>
          )}

          {(recommendationHeadline || recommendationNarrative || isAnalyzing) && (
            <section data-testid="section-recommendation">
              <h2 className="text-lg font-semibold mb-4 tracking-tight" data-testid="text-section-2-title">
                What We Recommend
              </h2>
              {isAnalyzing ? (
                <div className="space-y-3">
                  <Skeleton className="h-6 w-3/4" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-5/6" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-4/6" />
                </div>
              ) : (
                <div className="space-y-4">
                  {recommendationHeadline && (
                    <p
                      className="text-base font-semibold text-foreground"
                      data-testid="text-recommendation-headline"
                    >
                      {recommendationHeadline}
                    </p>
                  )}
                  {recommendationNarrative && recommendationNarrative.split('\n\n').map((paragraph: string, i: number) => (
                    <p
                      key={i}
                      className="text-sm leading-relaxed text-muted-foreground"
                      data-testid={`text-recommendation-p${i}`}
                    >
                      {paragraph}
                    </p>
                  ))}
                  {urgencyText && (
                    <p
                      className="text-sm font-medium text-foreground italic"
                      data-testid="text-urgency"
                    >
                      {urgencyText}
                    </p>
                  )}
                </div>
              )}
            </section>
          )}

          {(inactionNarrative || isAnalyzing) && (
            <section data-testid="section-inaction">
              <h2 className="text-lg font-semibold mb-4 tracking-tight" data-testid="text-section-3-title">
                What Happens If You Do Nothing
              </h2>
              {isAnalyzing ? (
                <div className="space-y-2">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-5/6" />
                  <Skeleton className="h-4 w-4/6" />
                </div>
              ) : (
                <div className="space-y-4">
                  {inactionNarrative.split('\n\n').map((paragraph: string, i: number) => (
                    <p
                      key={i}
                      className="text-sm leading-relaxed text-muted-foreground"
                      data-testid={`text-inaction-p${i}`}
                    >
                      {paragraph}
                    </p>
                  ))}
                </div>
              )}
            </section>
          )}

          {hasBriefing && (executionPlaybook || isAnalyzing) && (
            <section data-testid="section-playbook">
              <h2 className="text-lg font-semibold mb-4 tracking-tight" data-testid="text-section-4-title">
                Execution Playbook
              </h2>
              <p className="text-xs text-muted-foreground mb-6">
                Forward this to your team. Each item is a specific action with an owner, deadline, and definition of done.
              </p>
              {isAnalyzing ? (
                <div className="space-y-6">
                  {[0, 1, 2, 3, 4].map((i) => (
                    <div key={i} className="space-y-2">
                      <Skeleton className="h-4 w-full" />
                      <div className="flex gap-4 flex-wrap">
                        <Skeleton className="h-3 w-24" />
                        <Skeleton className="h-3 w-32" />
                      </div>
                      <Skeleton className="h-3 w-4/5" />
                    </div>
                  ))}
                </div>
              ) : executionPlaybook && executionPlaybook.length > 0 ? (
                (() => {
                  const hasPhases = executionPlaybook.some(item => item?.phase);
                  if (hasPhases) {
                    const phases: Record<string, typeof executionPlaybook> = {};
                    const phaseOrder: string[] = [];
                    executionPlaybook.forEach(item => {
                      const phase = item?.phase || 'Actions';
                      if (!phases[phase]) {
                        phases[phase] = [];
                        phaseOrder.push(phase);
                      }
                      phases[phase].push(item);
                    });
                    let globalIndex = 0;
                    const phaseSort = (a: string, b: string) => {
                      const num = (s: string) => { const m = s.match(/Phase\s*(\d+)/i); return m ? parseInt(m[1]) : 99; };
                      return num(a) - num(b);
                    };
                    phaseOrder.sort(phaseSort);
                    return (
                      <div className="space-y-8">
                        {phaseOrder.map((phase, phaseIdx) => (
                          <div key={phase} data-testid={`playbook-phase-${phaseIdx}`}>
                            <h3 className="text-sm font-semibold text-foreground mb-4 tracking-tight">
                              {phase}
                            </h3>
                            <ol className="space-y-5 list-none p-0 m-0">
                              {phases[phase].map((item) => {
                                const idx = globalIndex++;
                                const action = (item as any)?.action || (item as any)?.description || '';
                                const owner = (item as any)?.owner || (item as any)?.responsible || 'Team Lead';
                                const timeline = (item as any)?.timeline || (item as any)?.deadline || 'This week';
                                const dod = (item as any)?.definition_of_done || '';
                                const outcome = (item as any)?.expected_outcome || (item as any)?.outcome || '';
                                if (!action) return null;
                                return (
                                  <li
                                    key={idx}
                                    className="relative pl-8"
                                    data-testid={`playbook-item-${idx}`}
                                  >
                                    <span className="absolute left-0 top-0 text-sm font-semibold text-muted-foreground">
                                      {idx + 1}.
                                    </span>
                                    <p className="text-sm font-medium text-foreground leading-relaxed mb-2">
                                      {action}
                                    </p>
                                    <div className="flex gap-4 flex-wrap text-xs text-muted-foreground mb-1">
                                      <span data-testid={`playbook-owner-${idx}`}>
                                        <span className="font-medium text-foreground/70">Owner:</span> {owner}
                                      </span>
                                      <span data-testid={`playbook-timeline-${idx}`}>
                                        <span className="font-medium text-foreground/70">Timeline:</span> {timeline}
                                      </span>
                                    </div>
                                    {dod && (
                                      <p className="text-xs text-muted-foreground mt-1" data-testid={`playbook-dod-${idx}`}>
                                        <span className="font-medium text-foreground/70">Done when:</span> {dod}
                                      </p>
                                    )}
                                    {!dod && outcome && (
                                      <p className="text-xs text-muted-foreground italic mt-1" data-testid={`playbook-outcome-${idx}`}>
                                        Expected outcome: {outcome}
                                      </p>
                                    )}
                                  </li>
                                );
                              })}
                            </ol>
                          </div>
                        ))}
                      </div>
                    );
                  }
                  return (
                    <ol className="space-y-6 list-none p-0 m-0">
                      {executionPlaybook.map((item, i) => {
                        const action = (item as any)?.action || (item as any)?.description || '';
                        const owner = (item as any)?.owner || (item as any)?.responsible || 'Team Lead';
                        const timeline = (item as any)?.timeline || (item as any)?.deadline || 'This week';
                        const dod = (item as any)?.definition_of_done || '';
                        const outcome = (item as any)?.expected_outcome || (item as any)?.outcome || '';
                        if (!action) return null;
                        return (
                          <li
                            key={i}
                            className="relative pl-8"
                            data-testid={`playbook-item-${i}`}
                          >
                            <span className="absolute left-0 top-0 text-sm font-semibold text-muted-foreground">
                              {i + 1}.
                            </span>
                            <p className="text-sm font-medium text-foreground leading-relaxed mb-2">
                              {action}
                            </p>
                            <div className="flex gap-4 flex-wrap text-xs text-muted-foreground mb-1">
                              <span data-testid={`playbook-owner-${i}`}>
                                <span className="font-medium text-foreground/70">Owner:</span> {owner}
                              </span>
                              <span data-testid={`playbook-timeline-${i}`}>
                                <span className="font-medium text-foreground/70">Timeline:</span> {timeline}
                              </span>
                            </div>
                            {dod && (
                              <p className="text-xs text-muted-foreground mt-1" data-testid={`playbook-dod-${i}`}>
                                <span className="font-medium text-foreground/70">Done when:</span> {dod}
                              </p>
                            )}
                            {!dod && outcome && (
                              <p className="text-xs text-muted-foreground italic mt-1" data-testid={`playbook-outcome-${i}`}>
                                Expected outcome: {outcome}
                              </p>
                            )}
                          </li>
                        );
                      })}
                    </ol>
                  );
                })()
              ) : null}
            </section>
          )}

          {!diagnosisData && !isAnalyzing && rawRecommendations.length > 0 && (
            <section data-testid="section-fallback">
              <h2 className="text-lg font-semibold mb-4 tracking-tight">
                The Situation
              </h2>
              {rawRecommendations.map((rec: any, i: number) => {
                const rationale = rec.rationale || rec.impact_summary || '';
                return (
                  <div key={rec.id || i} className="mb-6" data-testid={`text-recommendation-fallback-${i}`}>
                    <p className="text-base font-semibold text-foreground mb-2">
                      {i + 1}. {rec.title}
                    </p>
                    {rationale && (
                      <p className="text-sm leading-relaxed text-muted-foreground">
                        {rationale}
                      </p>
                    )}
                  </div>
                );
              })}
            </section>
          )}

          <footer className="pt-6 border-t border-border" data-testid="section-footer">
            <p className="text-xs text-muted-foreground">
              This briefing was generated using your company's financial data and AI-powered analysis.
              {diagnosisData?.model_used && diagnosisData.model_used !== 'fallback' && (
                <span> Model: {diagnosisData.model_used}.</span>
              )}
              {' '}Refresh to update with the latest data.
            </p>
          </footer>
        </article>
      ) : (
        <div className="text-center py-16" data-testid="section-empty">
          <p className="text-lg font-semibold mb-2">No briefing yet</p>
          <p className="text-sm text-muted-foreground mb-6 max-w-md mx-auto">
            Generate a strategic briefing to get a written assessment of your company's
            situation, a recommended course of action, and a projection of what happens
            if you do nothing.
          </p>
          <Button
            onClick={handleGenerateDecisions}
            disabled={isGenerating}
            data-testid="button-first-decision"
          >
            {isGenerating ? 'Generating...' : 'Generate Strategic Briefing'}
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        </div>
      )}
    </div>
  );
}
