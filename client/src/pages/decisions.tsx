import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { RefreshCw, ArrowRight, Brain, Copy, Check, AlertTriangle, XCircle, Send, Mail, Loader2, CheckCircle2 } from 'lucide-react';
import { useFounderStore } from '@/store/founderStore';
import { useDecisions, useScenarios, useGenerateDecisions, useRunSimulation, useCreateScenario, useStrategicDiagnosisQuery } from '@/api/hooks';
import { useToast } from '@/hooks/use-toast';
import { useQueryClient } from '@tanstack/react-query';
import { apiRequest } from '@/lib/queryClient';

const LOADING_STEPS = [
  { label: 'Analyzing financial data', duration: 3000 },
  { label: 'Evaluating growth trajectory', duration: 4000 },
  { label: 'Identifying key risks', duration: 5000 },
  { label: 'Assessing risks & alternatives', duration: 4000 },
];

const TOC_SECTIONS = [
  { id: 'section-situation', label: 'The Situation', num: 1 },
  { id: 'section-recommendation', label: 'What We Recommend', num: 2 },
  { id: 'section-inaction', label: 'If You Do Nothing', num: 3 },
  { id: 'section-key-risks', label: 'Key Risks', num: 4 },
  { id: 'section-alt-paths', label: 'Alternative Paths', num: 5 },
];

interface ShareModalData {
  contentType: 'risk' | 'recommendation' | 'full_briefing' | 'custom';
  subject: string;
  contentData: Record<string, any>;
}

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
    }, 30000);
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
            The AI analysis timed out after 30 seconds. This can happen when the system is under heavy load.
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

function StickyTOC({ activeSection }: { activeSection: string }) {
  const scrollTo = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <nav className="hidden xl:block fixed right-8 top-32 w-52 z-50" data-testid="toc-sidebar">
      <div className="rounded-md border border-border/50 bg-card/80 p-4" style={{ backdropFilter: 'blur(8px)' }}>
        <p className="text-[10px] uppercase tracking-widest text-muted-foreground/60 mb-4 font-semibold">Contents</p>
        <div className="relative pl-[7px]">
          <div className="absolute left-[7px] top-0 bottom-0 w-px bg-border" />
          <div className="space-y-0">
            {TOC_SECTIONS.map((s) => {
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

function ShareModal({
  open,
  onOpenChange,
  data,
  companyId,
  companyName,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  data: ShareModalData | null;
  companyId: number;
  companyName: string;
}) {
  const { toast } = useToast();
  const [toEmail, setToEmail] = useState('');
  const [subject, setSubject] = useState('');
  const [personalNote, setPersonalNote] = useState('');
  const [isSending, setIsSending] = useState(false);

  useEffect(() => {
    if (data) {
      setSubject(data.subject);
      setToEmail('');
      setPersonalNote('');
    }
  }, [data]);

  const handleSend = async () => {
    if (!toEmail.trim()) {
      toast({ title: 'Email required', description: 'Please enter a recipient email address.', variant: 'destructive' });
      return;
    }
    setIsSending(true);
    try {
      await apiRequest('POST', `/api/companies/${companyId}/share-action-item`, {
        to_email: toEmail.trim(),
        subject: subject || undefined,
        content_type: data?.contentType || 'custom',
        content_data: data?.contentData || {},
        personal_note: personalNote.trim() || undefined,
      });
      toast({ title: 'Sent', description: `Email sent to ${toEmail.trim()}` });
      onOpenChange(false);
    } catch (err: any) {
      toast({ title: 'Failed to send', description: err.message || 'Something went wrong.', variant: 'destructive' });
    } finally {
      setIsSending(false);
    }
  };

  const typeLabels: Record<string, string> = {
    risk: 'Risk Alert',
    recommendation: 'Recommendation',
    full_briefing: 'Full Briefing',
    custom: 'Shared Item',
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md" data-testid="share-modal">
        <DialogHeader>
          <DialogTitle data-testid="share-modal-title">
            Share {typeLabels[data?.contentType || 'custom']}
          </DialogTitle>
          <DialogDescription>
            Send this as a professional email via Predixen.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="share-email">Recipient email</Label>
            <Input
              id="share-email"
              type="email"
              placeholder="team@company.com"
              value={toEmail}
              onChange={(e) => setToEmail(e.target.value)}
              data-testid="input-share-email"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="share-subject">Subject</Label>
            <Input
              id="share-subject"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              data-testid="input-share-subject"
            />
          </div>
          {data?.contentType === 'risk' && data.contentData.risk && (
            <div className="rounded-md bg-muted p-3">
              <p className="text-xs text-muted-foreground mb-1 font-medium">Risk being shared:</p>
              <p className="text-sm text-foreground">{data.contentData.risk}</p>
            </div>
          )}
          {data?.contentType === 'recommendation' && data.contentData.headline && (
            <div className="rounded-md bg-muted p-3">
              <p className="text-xs text-muted-foreground mb-1 font-medium">Recommendation being shared:</p>
              <p className="text-sm text-foreground">{data.contentData.headline}</p>
            </div>
          )}
          {data?.contentType === 'full_briefing' && (
            <div className="rounded-md bg-muted p-3">
              <p className="text-xs text-muted-foreground font-medium">The full strategic briefing will be sent.</p>
            </div>
          )}
          <div className="space-y-2">
            <Label htmlFor="share-note">Personal note (optional)</Label>
            <Textarea
              id="share-note"
              placeholder="Add a message for the recipient..."
              value={personalNote}
              onChange={(e) => setPersonalNote(e.target.value)}
              className="resize-none"
              rows={3}
              data-testid="input-share-note"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} data-testid="button-share-cancel">
            Cancel
          </Button>
          <Button onClick={handleSend} disabled={isSending} data-testid="button-share-send">
            {isSending ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Sending...
              </>
            ) : (
              <>
                <Send className="h-4 w-4 mr-2" />
                Send Email
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
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

  const handleEmailFullBriefing = () => {
    if (!diagnosisData) return;
    const sections: Array<{title: string; text: string}> = [];
    if (diagnosisData.situation_narrative || diagnosisData.diagnosis_narrative) {
      sections.push({ title: 'Section 1: The Situation', text: diagnosisData.situation_narrative || diagnosisData.diagnosis_narrative });
    }
    if (diagnosisData.recommendation_headline) {
      let recText = diagnosisData.recommendation_headline;
      if (diagnosisData.recommendation_narrative) recText += '\n\n' + diagnosisData.recommendation_narrative;
      if (diagnosisData.urgency_text) recText += '\n\nUrgency: ' + diagnosisData.urgency_text;
      sections.push({ title: 'Section 2: What We Recommend', text: recText });
    }
    if (diagnosisData.inaction_narrative) {
      sections.push({ title: 'Section 3: What Happens If You Do Nothing', text: diagnosisData.inaction_narrative });
    }
    if (diagnosisData.key_risks?.length) {
      const riskText = diagnosisData.key_risks.map((item: any, i: number) => {
        let line = `${i + 1}. [${item.likelihood}] ${item.risk}`;
        if (item.contingency) line += `\n   If this happens: ${item.contingency}`;
        if (item.pivot_deadline) line += `\n   When to pivot: ${item.pivot_deadline}`;
        return line;
      }).join('\n\n');
      sections.push({ title: 'Section 4: Key Risks', text: riskText });
    }
    if (diagnosisData.alternative_paths?.length) {
      const altText = diagnosisData.alternative_paths.map((item: any, i: number) => {
        return `${i + 1}. ${item.strategy}\n   Why not now: ${item.why_rejected}\n   Revisit if: ${item.when_it_might_work}`;
      }).join('\n\n');
      sections.push({ title: 'Section 5: Alternative Paths', text: altText });
    }
    openShareModal({
      contentType: 'full_briefing',
      subject: `Strategic Briefing - ${currentCompany?.name || 'Your Company'}`,
      contentData: { sections },
    });
  };

  const handleGenerateDecisions = useCallback(async () => {
    if (!currentCompany) return;
    setIsGenerating(true);
    setGenerationError(null);

    const timeoutMs = 30000;
    let timedOut = false;
    const timeoutId = setTimeout(() => {
      timedOut = true;
      setIsGenerating(false);
      setGenerationError('The analysis timed out after 30 seconds. The AI service may be under heavy load.');
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
      queryClient.invalidateQueries({ queryKey: ['strategic-diagnosis', currentCompany.id] });
      setCurrentStep('decision');
      toast({ title: 'Briefing generated', description: 'Your strategic briefing is ready.' });
    } catch (err: any) {
      if (timedOut) return;
      const message = err.message || 'Something went wrong';
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

  const handleCopyBrief = async () => {
    if (!diagnosisData) return;
    const parts: string[] = [];
    parts.push(`STRATEGIC BRIEFING — ${currentCompany?.name || ''}`);
    parts.push(`Prepared ${diagnosisData.generated_at ? new Date(diagnosisData.generated_at).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' }) : 'today'}`);
    parts.push('');

    if (diagnosisData.situation_narrative || diagnosisData.diagnosis_narrative) {
      parts.push('1. THE SITUATION');
      parts.push(diagnosisData.situation_narrative || diagnosisData.diagnosis_narrative);
      parts.push('');
    }
    if (diagnosisData.recommendation_headline) {
      parts.push('2. WHAT WE RECOMMEND');
      parts.push(diagnosisData.recommendation_headline);
      if (diagnosisData.recommendation_narrative) parts.push(diagnosisData.recommendation_narrative);
      if (diagnosisData.urgency_text) parts.push(`\nURGENCY: ${diagnosisData.urgency_text}`);
      parts.push('');
    }
    if (diagnosisData.inaction_narrative) {
      parts.push('3. WHAT HAPPENS IF YOU DO NOTHING');
      parts.push(diagnosisData.inaction_narrative);
      parts.push('');
    }
    if (diagnosisData.key_risks?.length) {
      parts.push('4. KEY RISKS & CONTINGENCY PLANS');
      diagnosisData.key_risks.forEach((item: any, i: number) => {
        parts.push(`${i + 1}. [${item.likelihood}] ${item.risk}`);
        if (item.contingency) parts.push(`   If this happens: ${item.contingency}`);
        if (item.pivot_deadline) parts.push(`   When to pivot: ${item.pivot_deadline}`);
      });
      parts.push('');
    }
    if (diagnosisData.alternative_paths?.length) {
      parts.push('5. ALTERNATIVE PATHS CONSIDERED');
      diagnosisData.alternative_paths.forEach((item: any, i: number) => {
        parts.push(`${i + 1}. ${item.strategy}`);
        parts.push(`   Why rejected: ${item.why_rejected}`);
        parts.push(`   When it might work: ${item.when_it_might_work}`);
      });
    }

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

  return (
    <div className="p-6 max-w-3xl mx-auto xl:mr-56" data-testid="page-decisions">
      {diagnosisData && <StickyTOC activeSection={activeSection} />}

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
            {diagnosisData && (
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
                  {hasBriefing || diagnosisData ? 'Regenerate Briefing' : 'Generate Briefing'}
                </>
              )}
            </Button>
          </div>
        </div>
        {(diagnosisData || hasBriefing) && (
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
            setGenerationError('The analysis timed out after 30 seconds. The AI service may be under heavy load.');
          }}
          onRetry={handleGenerateDecisions}
        />
      ) : diagnosisError && !diagnosisData ? (
        <Card className="border-destructive/30" data-testid="section-diagnosis-error">
          <CardContent className="py-8 text-center">
            <XCircle className="h-8 w-8 text-destructive mx-auto mb-3" />
            <p className="text-sm font-medium text-foreground mb-1">Unable to load strategic analysis</p>
            <p className="text-xs text-muted-foreground mb-4">
              This may be due to a temporary issue. Try again or regenerate the briefing.
            </p>
            <Button
              variant="outline"
              onClick={() => refetchDiagnosisQuery()}
              data-testid="button-retry-diagnosis"
            >
              <Brain className="h-4 w-4 mr-2" />
              Try Again
            </Button>
          </CardContent>
        </Card>
      ) : (diagnosisData || hasBriefing) ? (
        <article className="space-y-12" data-testid="article-briefing">

          {situationNarrative && (
            <section id="section-situation" data-testid="section-situation">
              <SectionDivider num={1} label="The Situation" />
              <h2 className="text-lg font-semibold mb-4 tracking-tight" data-testid="text-section-1-title">
                The Situation
              </h2>
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
            </section>
          )}

          {(recommendationHeadline || recommendationNarrative) && (
            <section id="section-recommendation" data-testid="section-recommendation">
              <SectionDivider num={2} label="What We Recommend" />
              <div className="flex items-center justify-between gap-3 flex-wrap mb-4">
                <h2 className="text-lg font-semibold tracking-tight" data-testid="text-section-2-title">
                  What We Recommend
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
              </div>
            </section>
          )}

          {inactionNarrative && (
            <section id="section-inaction" data-testid="section-inaction">
              <SectionDivider num={3} label="What Happens If You Do Nothing" />
              <h2 className="text-lg font-semibold mb-4 tracking-tight" data-testid="text-section-3-title">
                What Happens If You Do Nothing
              </h2>
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
            </section>
          )}

          {keyRisks && keyRisks.length > 0 && (
            <section id="section-key-risks" data-testid="section-key-risks">
              <SectionDivider num={4} label="Key Risks & Contingency Plans" />
              <h2 className="text-lg font-semibold mb-4 tracking-tight" data-testid="text-section-4-title">
                Key Risks & Contingency Plans
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

          {alternativePaths && alternativePaths.length > 0 && (
            <section id="section-alt-paths" data-testid="section-alt-paths">
              <SectionDivider num={5} label="Alternative Paths Considered" />
              <h2 className="text-lg font-semibold mb-4 tracking-tight" data-testid="text-section-5-title">
                Alternative Paths Considered
              </h2>
              <p className="text-xs text-muted-foreground mb-6">
                Strategies we evaluated but did not recommend — and when they might become the right call.
              </p>
              <ol className="space-y-6 list-none p-0 m-0">
                {alternativePaths.map((item, i) => (
                  <li
                    key={i}
                    className="relative pl-8"
                    data-testid={`alt-path-${i}`}
                  >
                    <span className="absolute left-0 top-0 text-sm font-semibold text-muted-foreground">
                      {i + 1}.
                    </span>
                    <p className="text-sm font-medium text-foreground mb-2">
                      {item.strategy}
                    </p>
                    <p className="text-sm leading-relaxed text-muted-foreground mb-2" data-testid={`alt-path-rejected-${i}`}>
                      <span className="font-medium text-foreground/70">Why not now:</span> {item.why_rejected}
                    </p>
                    <p className="text-sm leading-relaxed text-muted-foreground" data-testid={`alt-path-when-${i}`}>
                      <span className="font-medium text-foreground/70">Revisit if:</span> {item.when_it_might_work}
                    </p>
                  </li>
                ))}
              </ol>
            </section>
          )}

          {!diagnosisData && rawRecommendations.length > 0 && (
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
