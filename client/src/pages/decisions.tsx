import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

import { RefreshCw, ArrowRight, Brain, Copy, Check, AlertTriangle, XCircle, Send, Mail, Loader2, CheckCircle2 } from 'lucide-react';
import { useFounderStore } from '@/store/founderStore';
import { useDecisions, useScenarios, useGenerateDecisions, useRunSimulation, useCreateScenario, useStrategicDiagnosisQuery } from '@/api/hooks';
import { useToast } from '@/hooks/use-toast';
import { useQueryClient } from '@tanstack/react-query';
import { apiRequest } from '@/lib/queryClient';
import { api } from '@/api/client';
import { ShareModal, type ShareModalData } from '@/components/ShareModal';

const LOADING_STEPS = [
  { label: 'Analyzing financial data', duration: 8000 },
  { label: 'Evaluating growth trajectory', duration: 15000 },
  { label: 'Identifying key risks', duration: 20000 },
  { label: 'Generating strategic briefing', duration: 30000 },
];

const TOC_SECTIONS = [
  { id: 'section-situation', label: 'Executive Summary', num: 1 },
  { id: 'section-metrics', label: 'Key Metrics Overview', num: 2 },
  { id: 'section-key-risks', label: 'Risk Assessment', num: 3 },
  { id: 'section-recommendation', label: 'Recommended Actions', num: 4 },
  { id: 'section-milestones', label: 'Upcoming Milestones', num: 5 },
];

function LoadingProgress({ onTimeout, onRetry }: { onTimeout?: () => void; onRetry?: () => void }) {
  const [activeStep, setActiveStep] = useState(0);
  const [timedOut, setTimedOut] = useState(false);
  const [progressPct, setProgressPct] = useState(0);

  useEffect(() => {
    let timeout: ReturnType<typeof setTimeout>;
    const totalDuration = LOADING_STEPS.reduce((s, step) => s + step.duration, 0);
    let elapsed = 0;
    const advance = (step: number) => {
      if (step < LOADING_STEPS.length) {
        timeout = setTimeout(() => {
          elapsed += LOADING_STEPS[step].duration;
          const pct = step + 1 >= LOADING_STEPS.length ? 100 : Math.min((elapsed / totalDuration) * 95, 95);
          setProgressPct(pct);
          setActiveStep(step + 1);
          advance(step + 1);
        }, LOADING_STEPS[step].duration);
      }
    };
    advance(0);
    return () => clearTimeout(timeout);
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      setTimedOut(true);
      onTimeout?.();
    }, 120000);
    return () => clearTimeout(timer);
  }, [onTimeout]);

  if (timedOut) {
    return (
      <div className="py-16 flex flex-col items-center gap-6 animate-in fade-in duration-500" data-testid="loading-timeout">
        <div className="h-14 w-14 rounded-full bg-destructive/10 flex items-center justify-center">
          <XCircle className="h-7 w-7 text-destructive" />
        </div>
        <div className="text-center">
          <p className="text-sm font-semibold text-foreground mb-1">Analysis is taking longer than expected</p>
          <p className="text-xs text-muted-foreground max-w-sm">
            The AI analysis timed out. This can happen when the system is under heavy load.
          </p>
        </div>
        {onRetry && (
          <Button variant="outline" onClick={onRetry} data-testid="button-retry-timeout">
            <RefreshCw className="h-4 w-4 mr-2" />
            Try Again
          </Button>
        )}
      </div>
    );
  }

  return (
    <div className="py-16 flex flex-col items-center gap-8 animate-in fade-in duration-500" data-testid="loading-progress">
      <div className="relative">
        <div className="h-16 w-16 rounded-full flex items-center justify-center" style={{ background: 'linear-gradient(135deg, hsl(var(--primary) / 0.15), hsl(var(--primary) / 0.05))' }}>
          <Brain className="h-7 w-7 text-primary animate-pulse" />
        </div>
        <div className="absolute -inset-1 rounded-full border border-primary/20 animate-ping" style={{ animationDuration: '2s' }} />
      </div>

      <div className="text-center">
        <p className="text-sm font-semibold text-foreground mb-1">Generating your strategic briefing</p>
        <p className="text-xs text-muted-foreground">Analyzing your financial data with AI</p>
      </div>

      <div className="w-full max-w-xs">
        <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden mb-6">
          <div
            className="h-full rounded-full transition-all duration-1000 ease-out"
            style={{
              width: `${progressPct}%`,
              background: 'linear-gradient(90deg, hsl(var(--primary)), hsl(var(--primary) / 0.7))',
            }}
            data-testid="loading-progress-bar"
          />
        </div>

        <div className="space-y-2.5">
          {LOADING_STEPS.map((step, i) => {
            const isActive = i === activeStep;
            const isDone = i < activeStep;
            return (
              <div
                key={i}
                className="flex items-center gap-3 transition-all duration-500"
                style={{
                  opacity: isDone ? 1 : isActive ? 1 : 0.3,
                  transform: isActive ? 'translateX(4px)' : 'translateX(0)',
                }}
                data-testid={`loading-step-${i}`}
              >
                <div className="flex-shrink-0 w-5 h-5 flex items-center justify-center">
                  {isDone ? (
                    <CheckCircle2 className="h-4 w-4 text-green-500 animate-in zoom-in duration-300" />
                  ) : isActive ? (
                    <div className="h-2.5 w-2.5 rounded-full bg-primary animate-pulse" />
                  ) : (
                    <div className="h-2 w-2 rounded-full bg-muted-foreground/20" />
                  )}
                </div>
                <span className={`text-xs transition-colors duration-300 ${isDone ? 'text-muted-foreground line-through' : isActive ? 'text-foreground font-medium' : 'text-muted-foreground/40'}`}>
                  {step.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function StickyTOC({ activeSection, visibleSections }: { activeSection: string; visibleSections: typeof TOC_SECTIONS }) {
  const scrollTo = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  if (visibleSections.length === 0) return null;

  return (
    <nav className="hidden xl:block fixed right-8 top-32 w-52 z-50" data-testid="toc-sidebar">
      <div className="rounded-md border border-border/50 bg-card/80 p-4" style={{ backdropFilter: 'blur(8px)' }}>
        <p className="text-[10px] uppercase tracking-widest text-muted-foreground/60 mb-4 font-semibold">Contents</p>
        <div className="relative pl-[7px]">
          <div className="absolute left-[7px] top-0 bottom-0 w-px bg-border" />
          <div className="space-y-0">
            {visibleSections.map((s) => {
              const isActive = activeSection === s.id;
              return (
                <button
                  key={s.id}
                  onClick={() => scrollTo(s.id)}
                  className="relative flex items-center gap-3 w-full text-left py-1.5 hover-elevate rounded-md"
                  data-testid={`toc-link-${s.id}`}
                >
                  {isActive && (
                    <div className="absolute left-0 top-1 bottom-1 w-px bg-primary transition-all duration-300" />
                  )}
                  <div className={`h-[13px] w-[13px] rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-all duration-300 ${isActive ? 'border-primary bg-primary' : 'border-muted-foreground/30 bg-card'}`}>
                    {isActive && <div className="h-1 w-1 rounded-full bg-primary-foreground" />}
                  </div>
                  <span className={`text-xs transition-colors duration-300 ${isActive ? 'text-foreground font-medium' : 'text-muted-foreground/60'}`}>
                    {s.label}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </nav>
  );
}

function SectionDivider({ num, label }: { num: number; label: string }) {
  return (
    <div className="flex items-center gap-3 mb-5">
      <div className="h-6 w-6 rounded-full flex items-center justify-center flex-shrink-0 bg-primary/10 border border-primary/20">
        <span className="text-[10px] font-bold text-primary">{num}</span>
      </div>
      <span className="text-[10px] uppercase tracking-widest text-muted-foreground/60 font-semibold whitespace-nowrap">
        {label}
      </span>
      <div className="flex-1 h-px" style={{ background: 'linear-gradient(90deg, hsl(var(--border)), transparent)' }} />
    </div>
  );
}

function LikelihoodBadge({ likelihood }: { likelihood: string }) {
  const l = likelihood.toLowerCase();
  if (l === 'high') {
    return <Badge variant="destructive" className="text-[10px]" data-testid="badge-likelihood-high">High</Badge>;
  }
  if (l === 'medium') {
    return <Badge className="text-[10px] bg-amber-500/15 text-amber-400 border-amber-500/30" data-testid="badge-likelihood-medium">Medium</Badge>;
  }
  return <Badge variant="secondary" className="text-[10px] bg-green-500/15 text-green-400 border-green-500/30" data-testid="badge-likelihood-low">Low</Badge>;
}

export default function DecisionsPage() {
  const { currentCompany, setCurrentStep } = useFounderStore();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { data: scenarios } = useScenarios(currentCompany?.id || null);
  const latestScenarioId = scenarios?.[0]?.id;
  const { data: decisions, isLoading, refetch } = useDecisions(currentCompany?.id || null);

  const createScenarioMutation = useCreateScenario();
  const runSimulationMutation = useRunSimulation();
  const generateDecisionsMutation = useGenerateDecisions();

  const [isGenerating, setIsGenerating] = useState(false);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState('section-situation');
  const [copied, setCopied] = useState(false);
  const [shareModalOpen, setShareModalOpen] = useState(false);
  const [shareModalData, setShareModalData] = useState<ShareModalData | null>(null);

  const recommendationsData = decisions?.recommendations;
  const rawRecommendations = Array.isArray(recommendationsData)
    ? recommendationsData
    : Array.isArray(recommendationsData?.recommendations)
      ? recommendationsData.recommendations
      : [];

  const hasBriefing = rawRecommendations.length > 0;

  const {
    data: diagnosisData,
    isLoading: isDiagnosisLoading,
    isError: diagnosisError,
    isFetching: isDiagnosisFetching,
    refetch: refetchDiagnosisQuery,
  } = useStrategicDiagnosisQuery(currentCompany?.id || null, !!currentCompany?.id);

  const isAnalyzing = isDiagnosisLoading && !diagnosisData;
  const isUpdating = isDiagnosisFetching && !!diagnosisData;

  const handleGenerateDecisions = useCallback(async () => {
    if (!currentCompany) return;
    setIsGenerating(true);
    setGenerationError(null);

    const timeoutMs = 120000;
    let timedOut = false;
    const timeoutId = setTimeout(() => {
      timedOut = true;
      setIsGenerating(false);
      setGenerationError('The analysis timed out. The AI service may be under heavy load. Please try again.');
    }, timeoutMs);

    try {
      let scenarioId = latestScenarioId;

      if (!scenarioId) {
        const scenario = await createScenarioMutation.mutateAsync({
          companyId: currentCompany.id,
          data: { name: 'Baseline Scenario' },
        });
        scenarioId = scenario.id;
      }

      if (timedOut) return;

      const simResult = await runSimulationMutation.mutateAsync({ scenarioId, nSims: 1000 });

      if (timedOut) return;

      await generateDecisionsMutation.mutateAsync(simResult.id);

      if (timedOut) return;

      await refetch();

      if (timedOut) return;

      const diagnosisResult = await api.decisions.regenerateDiagnosis(currentCompany.id);
      queryClient.setQueryData(['strategic-diagnosis', currentCompany.id], diagnosisResult);

      setCurrentStep('decision');
      toast({ title: 'Briefing generated', description: 'Your strategic briefing is ready.' });
    } catch (err: any) {
      if (timedOut) return;
      const message = (err instanceof Error ? err.message : typeof err === 'string' ? err : '') || 'Something went wrong';
      if (message.includes('authentication') || message.includes('credentials') || err.status === 401) {
        toast({
          title: 'Session Expired',
          description: 'Please sign in again to continue.',
          variant: 'destructive'
        });
      } else {
        setGenerationError(message);
        toast({ title: 'Generation failed', description: message, variant: 'destructive' });
      }
    } finally {
      clearTimeout(timeoutId);
      if (!timedOut) {
        setIsGenerating(false);
      }
    }
  }, [currentCompany, latestScenarioId, createScenarioMutation, runSimulationMutation, generateDecisionsMutation, refetch, queryClient, setCurrentStep, toast]);

  const [autoGenTriggered, setAutoGenTriggered] = useState(false);
  useEffect(() => {
    if (
      currentCompany?.id &&
      !isLoading &&
      !isDiagnosisLoading &&
      !isGenerating &&
      !autoGenTriggered &&
      !diagnosisData &&
      !hasBriefing &&
      !generationError
    ) {
      setAutoGenTriggered(true);
      handleGenerateDecisions();
    }
  }, [currentCompany?.id, isLoading, isDiagnosisLoading, isGenerating, autoGenTriggered, diagnosisData, hasBriefing, generationError, handleGenerateDecisions]);

  useEffect(() => {
    const sectionIds = TOC_SECTIONS.map((s) => s.id);
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.id);
          }
        }
      },
      { rootMargin: '-20% 0px -60% 0px', threshold: 0 }
    );

    const timeout = setTimeout(() => {
      sectionIds.forEach((id) => {
        const el = document.getElementById(id);
        if (el) observer.observe(el);
      });
    }, 500);

    return () => {
      clearTimeout(timeout);
      observer.disconnect();
    };
  }, [diagnosisData]);

  const openShareModal = (data: ShareModalData) => {
    setShareModalData(data);
    setShareModalOpen(true);
  };

  const handleShareRisk = (item: any) => {
    openShareModal({
      contentType: 'risk',
      subject: `Risk Alert from ${currentCompany?.name || 'Your Company'}`,
      contentData: {
        risk: item.risk || '',
        likelihood: item.likelihood || '',
        contingency: item.contingency || '',
        pivot_deadline: item.pivot_deadline || '',
      },
    });
  };

  const handleShareRecommendation = () => {
    if (!diagnosisData) return;
    openShareModal({
      contentType: 'recommendation',
      subject: `Strategic Recommendation from ${currentCompany?.name || 'Your Company'}`,
      contentData: {
        headline: diagnosisData.recommendation_headline || '',
        narrative: diagnosisData.recommendation_narrative || '',
        urgency: diagnosisData.urgency_text || '',
      },
    });
  };

  const _buildBriefingSections = () => {
    if (!diagnosisData) return [];
    const sections: Array<{title: string; text: string}> = [];
    let num = 0;
    if (diagnosisData.situation_narrative || diagnosisData.diagnosis_narrative) {
      num++;
      let text = diagnosisData.situation_narrative || diagnosisData.diagnosis_narrative;
      if (diagnosisData.urgency_text) text += '\n\nUrgency: ' + diagnosisData.urgency_text;
      sections.push({ title: `Section ${num}: Executive Summary`, text });
    }
    if (diagnosisData.key_metrics_overview?.length) {
      num++;
      const metricsText = diagnosisData.key_metrics_overview.map((m: any) => {
        let line = `${m.label}: ${m.value}`;
        if (m.note) line += ` (${m.note})`;
        return line;
      }).join('\n');
      sections.push({ title: `Section ${num}: Key Metrics Overview`, text: metricsText });
    }
    if (diagnosisData.key_risks?.length) {
      num++;
      const riskText = diagnosisData.key_risks.map((item: any, i: number) => {
        let line = `${i + 1}. [${item.likelihood}] ${item.risk}`;
        if (item.contingency) line += `\n   If this happens: ${item.contingency}`;
        if (item.pivot_deadline) line += `\n   When to pivot: ${item.pivot_deadline}`;
        return line;
      }).join('\n\n');
      sections.push({ title: `Section ${num}: Risk Assessment`, text: riskText });
    }
    if (diagnosisData.recommendation_headline || diagnosisData.recommendation_narrative) {
      num++;
      let recText = diagnosisData.recommendation_headline || '';
      if (diagnosisData.recommendation_narrative) recText += '\n\n' + diagnosisData.recommendation_narrative;
      if (diagnosisData.execution_playbook?.length) {
        recText += '\n\nExecution Playbook:';
        diagnosisData.execution_playbook.forEach((item: any, i: number) => {
          recText += `\n${i + 1}. ${item.action} (${item.timeline || ''})`;
        });
      }
      if (diagnosisData.inaction_narrative) {
        recText += '\n\nIf you do nothing:\n' + diagnosisData.inaction_narrative;
      }
      sections.push({ title: `Section ${num}: Recommended Actions`, text: recText });
    }
    if (diagnosisData.milestones?.length) {
      num++;
      const milText = diagnosisData.milestones.map((item: any, i: number) => {
        return `${i + 1}. ${item.title} — ${item.target_date}\n   ${item.description}`;
      }).join('\n\n');
      sections.push({ title: `Section ${num}: Upcoming Milestones`, text: milText });
    }
    if (diagnosisData.alternative_paths?.length) {
      num++;
      const altText = diagnosisData.alternative_paths.map((item: any, i: number) => {
        return `${i + 1}. ${item.strategy}\n   Why not now: ${item.why_rejected}\n   Revisit if: ${item.when_it_might_work}`;
      }).join('\n\n');
      sections.push({ title: `Section ${num}: Alternative Paths`, text: altText });
    }
    return sections;
  };

  const handleEmailFullBriefing = () => {
    const sections = _buildBriefingSections();
    if (sections.length === 0) return;
    openShareModal({
      contentType: 'full_briefing',
      subject: `Strategic Briefing - ${currentCompany?.name || 'Your Company'}`,
      contentData: { sections },
    });
  };

  const handleCopyBrief = async () => {
    const sections = _buildBriefingSections();
    if (sections.length === 0) return;
    const parts: string[] = [];
    parts.push(`STRATEGIC BRIEFING — ${currentCompany?.name || ''}`);
    parts.push(`Prepared ${diagnosisData?.generated_at ? new Date(diagnosisData.generated_at).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' }) : 'today'}`);
    parts.push('');
    sections.forEach(s => {
      parts.push(s.title.toUpperCase());
      parts.push(s.text);
      parts.push('');
    });

    try {
      await navigator.clipboard.writeText(parts.join('\n'));
      setCopied(true);
      toast({ title: 'Copied to clipboard', description: 'The full briefing has been copied as plain text.' });
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast({ title: 'Copy failed', description: 'Unable to copy to clipboard.', variant: 'destructive' });
    }
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

  const situationNarrative = diagnosisData?.situation_narrative || diagnosisData?.diagnosis_narrative || null;
  const recommendationHeadline = diagnosisData?.recommendation_headline || null;
  const recommendationNarrative = diagnosisData?.recommendation_narrative || null;
  const urgencyText = diagnosisData?.urgency_text || null;
  const inactionNarrative = diagnosisData?.inaction_narrative || null;
  const keyRisks: Array<{risk: string; likelihood: string; impact: string; contingency: string; pivot_deadline?: string}> | null = diagnosisData?.key_risks || null;
  const alternativePaths: Array<{strategy: string; why_rejected: string; when_it_might_work: string}> | null = diagnosisData?.alternative_paths || null;
  const keyMetricsOverview: Array<{label: string; value: string; trend: string; note: string}> | null = diagnosisData?.key_metrics_overview || null;
  const milestones: Array<{title: string; target_date: string; description: string; status: string}> | null = diagnosisData?.milestones || null;
  const executionPlaybook: Array<{phase: string; action: string; owner: string; timeline: string; definition_of_done?: string}> | null = diagnosisData?.execution_playbook || null;
  const healthScore: number | null = diagnosisData?.health_score || null;
  const healthLabel: string | null = diagnosisData?.health_label || null;
  const companyStageLabel: string | null = diagnosisData?.company_stage_label || null;

  const hasMeaningfulDiagnosis = !!(
    situationNarrative ||
    recommendationHeadline ||
    recommendationNarrative ||
    inactionNarrative ||
    (keyRisks && keyRisks.length > 0) ||
    (alternativePaths && alternativePaths.length > 0) ||
    (keyMetricsOverview && keyMetricsOverview.length > 0)
  );

  const visibleSections = TOC_SECTIONS.filter(s => {
    if (s.id === 'section-situation') return !!situationNarrative;
    if (s.id === 'section-metrics') return !!(keyMetricsOverview && keyMetricsOverview.length > 0);
    if (s.id === 'section-key-risks') return !!(keyRisks && keyRisks.length > 0);
    if (s.id === 'section-recommendation') return !!(recommendationHeadline || recommendationNarrative || (executionPlaybook && executionPlaybook.length > 0));
    if (s.id === 'section-milestones') return !!(milestones && milestones.length > 0);
    return true;
  }).map((s, i) => ({ ...s, num: i + 1 }));

  const sectionNum = (id: string) => {
    const found = visibleSections.find(s => s.id === id);
    return found?.num ?? 0;
  };

  return (
    <div className="p-6 max-w-3xl mx-auto xl:mr-56" data-testid="page-decisions">
      {hasMeaningfulDiagnosis && <StickyTOC activeSection={activeSection} visibleSections={visibleSections} />}

      <ShareModal
        open={shareModalOpen}
        onOpenChange={setShareModalOpen}
        data={shareModalData}
        companyId={currentCompany.id}
        companyName={currentCompany.name}
      />

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
              {isUpdating && (
                <Badge variant="secondary" className="ml-2 text-[10px]" data-testid="badge-updating">Updating</Badge>
              )}
            </p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {hasMeaningfulDiagnosis && (
              <>
                <Button
                  variant="outline"
                  onClick={handleCopyBrief}
                  disabled={copied}
                  data-testid="button-copy-brief"
                >
                  {copied ? (
                    <>
                      <Check className="h-4 w-4 mr-2" />
                      Copied
                    </>
                  ) : (
                    <>
                      <Copy className="h-4 w-4 mr-2" />
                      Copy Brief
                    </>
                  )}
                </Button>
                <Button
                  variant="outline"
                  onClick={handleEmailFullBriefing}
                  data-testid="button-email-briefing"
                >
                  <Mail className="h-4 w-4 mr-2" />
                  Email Briefing
                </Button>
              </>
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
                  {hasBriefing || hasMeaningfulDiagnosis ? 'Regenerate Briefing' : 'Generate Briefing'}
                </>
              )}
            </Button>
          </div>
        </div>
        {(hasMeaningfulDiagnosis || hasBriefing) && (
          <div className="mt-6 border-b border-border" />
        )}
      </header>

      {generationError ? (
        <Card className="border-destructive/30" data-testid="section-generation-error">
          <CardContent className="py-8 text-center">
            <XCircle className="h-8 w-8 text-destructive mx-auto mb-3" />
            <p className="text-sm font-medium text-foreground mb-1">Briefing generation failed</p>
            <p className="text-xs text-muted-foreground mb-4 max-w-sm mx-auto">
              {generationError}
            </p>
            <Button
              onClick={handleGenerateDecisions}
              disabled={isGenerating}
              data-testid="button-retry-generation"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </CardContent>
        </Card>
      ) : isLoading || isAnalyzing || isGenerating ? (
        <LoadingProgress
          onTimeout={() => {
            setIsGenerating(false);
            setGenerationError('The analysis timed out. The AI service may be under heavy load. Please try again.');
          }}
          onRetry={handleGenerateDecisions}
        />
      ) : (diagnosisError && !diagnosisData && !hasBriefing) || (!hasMeaningfulDiagnosis && !hasBriefing && !isAnalyzing && !isGenerating) ? (
        <Card data-testid="section-no-briefing">
          <CardContent className="py-12 text-center">
            <Brain className="h-10 w-10 text-muted-foreground mx-auto mb-4" />
            <p className="text-sm font-medium text-foreground mb-1">No briefing generated yet</p>
            <p className="text-xs text-muted-foreground mb-5 max-w-sm mx-auto">
              Click "Generate Briefing" to create your first strategic briefing with AI-powered analysis of your company's financial data.
            </p>
            <Button
              onClick={handleGenerateDecisions}
              disabled={isGenerating}
              data-testid="button-generate-first-briefing"
            >
              <Brain className="h-4 w-4 mr-2" />
              Generate Briefing
            </Button>
          </CardContent>
        </Card>
      ) : (hasMeaningfulDiagnosis || hasBriefing) ? (
        <article className="space-y-12" data-testid="article-briefing">

          {situationNarrative && (
            <section id="section-situation" data-testid="section-situation">
              <SectionDivider num={sectionNum('section-situation')} label="Executive Summary" />
              <h2 className="text-lg font-semibold mb-4 tracking-tight" data-testid="text-section-1-title">
                Executive Summary
              </h2>
              {(healthLabel || companyStageLabel) && (
                <div className="flex items-center gap-2 mb-4 flex-wrap">
                  {healthLabel && (
                    <Badge variant="outline" className={
                      healthLabel === 'Critical' ? 'border-red-500/50 text-red-400' :
                      healthLabel === 'Concerning' ? 'border-amber-500/50 text-amber-400' :
                      healthLabel === 'Stable' ? 'border-blue-500/50 text-blue-400' :
                      'border-emerald-500/50 text-emerald-400'
                    } data-testid="badge-health-label">
                      {healthLabel}{healthScore ? ` (${healthScore}/100)` : ''}
                    </Badge>
                  )}
                  {companyStageLabel && (
                    <Badge variant="outline" className="text-muted-foreground" data-testid="badge-stage-label">
                      {companyStageLabel}
                    </Badge>
                  )}
                </div>
              )}
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
              {urgencyText && (
                <div
                  className="mt-4 rounded-md border border-amber-500/30 bg-amber-500/10 px-4 py-3"
                  data-testid="callout-urgency"
                >
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="h-4 w-4 text-amber-400 mt-0.5 flex-shrink-0" />
                    <p className="text-sm font-medium text-amber-300">
                      {urgencyText}
                    </p>
                  </div>
                </div>
              )}
            </section>
          )}

          {keyMetricsOverview && keyMetricsOverview.length > 0 && (
            <section id="section-metrics" data-testid="section-metrics">
              <SectionDivider num={sectionNum('section-metrics')} label="Key Metrics Overview" />
              <h2 className="text-lg font-semibold mb-4 tracking-tight" data-testid="text-section-2-title">
                Key Metrics Overview
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {keyMetricsOverview.map((metric, i) => (
                  <div
                    key={i}
                    className="rounded-lg border border-border bg-card p-3"
                    data-testid={`metric-card-${i}`}
                  >
                    <p className="text-xs text-muted-foreground mb-1">{metric.label}</p>
                    <div className="flex items-baseline gap-2">
                      <p className="text-lg font-semibold text-foreground">{metric.value}</p>
                      {metric.trend && metric.trend !== 'neutral' && metric.trend !== 'flat' && (
                        <span className={`text-xs font-medium ${metric.trend === 'up' ? 'text-emerald-500' : 'text-red-500'}`}>
                          {metric.trend === 'up' ? '↑' : '↓'}
                        </span>
                      )}
                    </div>
                    {metric.note && <p className="text-xs text-muted-foreground mt-1">{metric.note}</p>}
                  </div>
                ))}
              </div>
            </section>
          )}

          {keyRisks && keyRisks.length > 0 && (
            <section id="section-key-risks" data-testid="section-key-risks">
              <SectionDivider num={sectionNum('section-key-risks')} label="Risk Assessment" />
              <h2 className="text-lg font-semibold mb-4 tracking-tight" data-testid="text-section-3-title">
                Risk Assessment
              </h2>
              <p className="text-xs text-muted-foreground mb-6">
                The most significant risks facing your company, with specific action plans if they materialize.
              </p>
              <ol className="space-y-8 list-none p-0 m-0">
                {keyRisks.map((item, i) => {
                  const risk = item?.risk || '';
                  const likelihood = item?.likelihood || '';
                  const contingency = item?.contingency || '';
                  const pivotDeadline = (item as any)?.pivot_deadline || '';
                  if (!risk) return null;
                  return (
                    <li
                      key={i}
                      className="relative pl-8 pr-8"
                      data-testid={`risk-item-${i}`}
                    >
                      <span className="absolute left-0 top-0 text-sm font-semibold text-muted-foreground">
                        {i + 1}.
                      </span>
                      <button
                        onClick={() => handleShareRisk(item)}
                        className="absolute right-0 top-0 text-muted-foreground/40 hover:text-foreground transition-colors"
                        title="Share this risk"
                        data-testid={`button-share-risk-${i}`}
                      >
                        <Send className="h-3.5 w-3.5" />
                      </button>
                      <div className="flex items-center gap-2 mb-2 flex-wrap">
                        {likelihood && <LikelihoodBadge likelihood={likelihood} />}
                      </div>
                      <p className="text-sm leading-relaxed text-muted-foreground mb-2" data-testid={`risk-scenario-${i}`}>
                        {risk}
                      </p>
                      {contingency && (
                        <p className="text-sm leading-relaxed text-muted-foreground mb-2" data-testid={`risk-contingency-${i}`}>
                          <span className="font-medium text-foreground/70">If this happens:</span> {contingency}
                        </p>
                      )}
                      {pivotDeadline && (
                        <p className="text-sm leading-relaxed text-muted-foreground" data-testid={`risk-pivot-${i}`}>
                          <span className="font-medium text-foreground/70">When to pivot:</span> {pivotDeadline}
                        </p>
                      )}
                    </li>
                  );
                })}
              </ol>
            </section>
          )}

          {(recommendationHeadline || recommendationNarrative || (executionPlaybook && executionPlaybook.length > 0)) && (
            <section id="section-recommendation" data-testid="section-recommendation">
              <SectionDivider num={sectionNum('section-recommendation')} label="Recommended Actions" />
              <div className="flex items-center justify-between gap-3 flex-wrap mb-4">
                <h2 className="text-lg font-semibold tracking-tight" data-testid="text-section-4-title">
                  Recommended Actions
                </h2>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleShareRecommendation}
                  data-testid="button-share-recommendation"
                >
                  <Send className="h-3 w-3 mr-1.5" />
                  Share
                </Button>
              </div>
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
              </div>
              {executionPlaybook && executionPlaybook.length > 0 && (
                <div className="mt-6">
                  <h3 className="text-sm font-semibold mb-3 text-foreground/80" data-testid="text-playbook-title">Execution Playbook</h3>
                  <div className="space-y-3">
                    {executionPlaybook.map((item, i) => (
                      <div key={i} className="rounded-lg border border-border bg-card/50 p-3" data-testid={`playbook-item-${i}`}>
                        <div className="flex items-start justify-between gap-2 mb-1">
                          <p className="text-sm font-medium text-foreground">{item.action}</p>
                        </div>
                        <div className="flex items-center gap-3 flex-wrap">
                          {item.owner && <Badge variant="outline" className="text-xs">{item.owner}</Badge>}
                          {item.timeline && <span className="text-xs text-muted-foreground">{item.timeline}</span>}
                          {item.phase && <span className="text-xs text-muted-foreground/60">{item.phase}</span>}
                        </div>
                        {item.definition_of_done && (
                          <p className="text-xs text-muted-foreground mt-2">
                            <span className="font-medium text-foreground/60">Done when:</span> {item.definition_of_done}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {inactionNarrative && (
                <div className="mt-6 rounded-md border border-red-500/20 bg-red-500/5 px-4 py-3" data-testid="section-inaction">
                  <h3 className="text-sm font-semibold mb-2 text-red-400">What Happens If You Do Nothing</h3>
                  <div className="space-y-3">
                    {inactionNarrative.split('\n\n').map((paragraph: string, i: number) => (
                      <p
                        key={i}
                        className="text-xs leading-relaxed text-muted-foreground"
                        data-testid={`text-inaction-p${i}`}
                      >
                        {paragraph}
                      </p>
                    ))}
                  </div>
                </div>
              )}
            </section>
          )}

          {milestones && milestones.length > 0 && (
            <section id="section-milestones" data-testid="section-milestones">
              <SectionDivider num={sectionNum('section-milestones')} label="Upcoming Milestones" />
              <h2 className="text-lg font-semibold mb-4 tracking-tight" data-testid="text-section-5-title">
                Upcoming Milestones
              </h2>
              <div className="space-y-4">
                {milestones.map((item, i) => (
                  <div key={i} className="flex gap-4" data-testid={`milestone-${i}`}>
                    <div className="flex flex-col items-center">
                      <div className={`w-3 h-3 rounded-full mt-1 ${
                        item.status === 'completed' ? 'bg-emerald-500' :
                        item.status === 'in_progress' ? 'bg-blue-500' :
                        'bg-muted-foreground/30'
                      }`} />
                      {i < milestones.length - 1 && <div className="w-px flex-1 bg-border mt-1" />}
                    </div>
                    <div className="pb-4 flex-1">
                      <div className="flex items-baseline gap-2 mb-1 flex-wrap">
                        <p className="text-sm font-medium text-foreground">{item.title}</p>
                        <span className="text-xs text-muted-foreground">{item.target_date}</span>
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">{item.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {alternativePaths && alternativePaths.length > 0 && (
            <section data-testid="section-alt-paths">
              <h3 className="text-sm font-semibold mb-3 text-foreground/80">Alternative Paths Considered</h3>
              <div className="space-y-4">
                {alternativePaths.map((item, i) => (
                  <div key={i} className="rounded-lg border border-border bg-card/50 p-3" data-testid={`alt-path-${i}`}>
                    <p className="text-sm font-medium text-foreground mb-1">{item.strategy}</p>
                    <p className="text-xs text-muted-foreground mb-1">
                      <span className="font-medium text-foreground/60">Why not now:</span> {item.why_rejected}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      <span className="font-medium text-foreground/60">Revisit if:</span> {item.when_it_might_work}
                    </p>
                  </div>
                ))}
              </div>
            </section>
          )}

          <footer className="pt-6 border-t border-border" data-testid="section-footer">
            <p className="text-xs text-muted-foreground">
              This briefing was generated using your company's financial data and AI-powered analysis.
              {diagnosisData?.model_used && diagnosisData.model_used !== 'fallback' && (
                <span> Model: {diagnosisData.model_used}.</span>
              )}
              {diagnosisData?.generated_at && (
                <span> Generated: {new Date(diagnosisData.generated_at).toLocaleDateString()}.</span>
              )}
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
