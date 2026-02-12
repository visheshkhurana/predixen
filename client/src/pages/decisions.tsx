import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { RefreshCw, ArrowRight, Brain, Copy, Check, AlertTriangle, XCircle, Send, Mail, Loader2 } from 'lucide-react';
import { useFounderStore } from '@/store/founderStore';
import { useDecisions, useScenarios, useGenerateDecisions, useRunSimulation, useCreateScenario, useStrategicDiagnosisQuery } from '@/api/hooks';
import { useToast } from '@/hooks/use-toast';
import { useQueryClient } from '@tanstack/react-query';
import { apiRequest } from '@/lib/queryClient';

const LOADING_STEPS = [
  { label: 'Analyzing financial data', duration: 3000 },
  { label: 'Evaluating growth trajectory', duration: 4000 },
  { label: 'Building execution playbook', duration: 5000 },
  { label: 'Assessing risks & alternatives', duration: 4000 },
];

const TOC_SECTIONS = [
  { id: 'section-situation', label: 'The Situation', num: 1 },
  { id: 'section-recommendation', label: 'What We Recommend', num: 2 },
  { id: 'section-inaction', label: 'If You Do Nothing', num: 3 },
  { id: 'section-playbook', label: 'Execution Playbook', num: 4 },
  { id: 'section-key-risks', label: 'Key Risks', num: 5 },
  { id: 'section-alt-paths', label: 'Alternative Paths', num: 6 },
];

interface ShareModalData {
  contentType: 'playbook_item' | 'risk' | 'recommendation' | 'full_briefing' | 'custom';
  subject: string;
  contentData: Record<string, any>;
}

function LoadingProgress() {
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    let timeout: ReturnType<typeof setTimeout>;
    const advance = (step: number) => {
      if (step < LOADING_STEPS.length) {
        timeout = setTimeout(() => {
          setActiveStep(step + 1);
          advance(step + 1);
        }, LOADING_STEPS[step].duration);
      }
    };
    advance(0);
    return () => clearTimeout(timeout);
  }, []);

  return (
    <div className="py-16 flex flex-col items-center gap-6" data-testid="loading-progress">
      <Brain className="h-8 w-8 text-muted-foreground animate-pulse" />
      <p className="text-sm font-medium text-foreground">Generating your strategic briefing</p>
      <div className="w-full max-w-sm space-y-3">
        {LOADING_STEPS.map((step, i) => {
          const isActive = i === activeStep;
          const isDone = i < activeStep;
          return (
            <div
              key={i}
              className={`flex items-center gap-3 transition-opacity duration-500 ${isDone ? 'opacity-100' : isActive ? 'opacity-100' : 'opacity-30'}`}
              data-testid={`loading-step-${i}`}
            >
              <div className={`h-2 w-2 rounded-full flex-shrink-0 transition-colors duration-300 ${isDone ? 'bg-green-500' : isActive ? 'bg-amber-400 animate-pulse' : 'bg-muted-foreground/30'}`} />
              <span className={`text-xs ${isDone ? 'text-muted-foreground' : isActive ? 'text-foreground font-medium' : 'text-muted-foreground/50'}`}>
                {step.label}
                {isDone && <Check className="inline h-3 w-3 ml-1 text-green-500" />}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function StickyTOC({ activeSection }: { activeSection: string }) {
  const scrollTo = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <nav className="hidden xl:block fixed right-8 top-32 w-48 space-y-1" data-testid="toc-sidebar">
      <p className="text-[10px] uppercase tracking-widest text-muted-foreground/60 mb-3 font-medium">Contents</p>
      {TOC_SECTIONS.map((s) => (
        <button
          key={s.id}
          onClick={() => scrollTo(s.id)}
          className={`block w-full text-left text-xs py-1.5 px-2 rounded-md transition-colors ${activeSection === s.id ? 'text-foreground bg-muted font-medium' : 'text-muted-foreground/70 hover:text-foreground'}`}
          data-testid={`toc-link-${s.id}`}
        >
          <span className="text-muted-foreground/50 mr-1.5">{s.num}.</span>
          {s.label}
        </button>
      ))}
    </nav>
  );
}

function SectionDivider({ num, label }: { num: number; label: string }) {
  return (
    <div className="flex items-center gap-3 mb-4">
      <span className="text-[10px] uppercase tracking-widest text-muted-foreground/50 font-medium whitespace-nowrap">
        Section {num}
      </span>
      <div className="flex-1 border-b border-border" />
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
    playbook_item: 'Action Item',
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
          {data?.contentType === 'playbook_item' && data.contentData.action && (
            <div className="rounded-md bg-muted p-3">
              <p className="text-xs text-muted-foreground mb-1 font-medium">Action item being shared:</p>
              <p className="text-sm text-foreground">{data.contentData.action}</p>
              {data.contentData.owner && <p className="text-xs text-muted-foreground mt-1">Owner: {data.contentData.owner}</p>}
            </div>
          )}
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

function usePlaybookChecks(companyId: number | null) {
  const storageKey = companyId ? `predixen-playbook-checks-${companyId}` : null;

  const [checked, setChecked] = useState<Record<number, boolean>>(() => {
    if (!storageKey) return {};
    try {
      const stored = localStorage.getItem(storageKey);
      return stored ? JSON.parse(stored) : {};
    } catch { return {}; }
  });

  useEffect(() => {
    if (storageKey) {
      localStorage.setItem(storageKey, JSON.stringify(checked));
    }
  }, [checked, storageKey]);

  const toggle = useCallback((idx: number) => {
    setChecked((prev) => ({ ...prev, [idx]: !prev[idx] }));
  }, []);

  const count = Object.values(checked).filter(Boolean).length;

  return { checked, toggle, count };
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

  const { checked, toggle, count: checkedCount } = usePlaybookChecks(currentCompany?.id || null);

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

  const handleSharePlaybookItem = (item: any) => {
    openShareModal({
      contentType: 'playbook_item',
      subject: `Action Item from ${currentCompany?.name || 'Your Company'}`,
      contentData: {
        action: item.action || item.description || '',
        owner: item.owner || item.responsible || '',
        timeline: item.timeline || item.deadline || '',
        done_when: item.definition_of_done || '',
        phase: item.phase || '',
      },
    });
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
    if (diagnosisData.execution_playbook?.length) {
      const pbText = diagnosisData.execution_playbook.map((item: any, i: number) => {
        let line = `${i + 1}. ${item.action || item.description || ''}`;
        if (item.owner) line += ` (Owner: ${item.owner})`;
        if (item.timeline) line += ` - ${item.timeline}`;
        if (item.definition_of_done) line += ` | Done when: ${item.definition_of_done}`;
        return line;
      }).join('\n');
      sections.push({ title: 'Section 4: Execution Playbook', text: pbText });
    }
    if (diagnosisData.key_risks?.length) {
      const riskText = diagnosisData.key_risks.map((item: any, i: number) => {
        let line = `${i + 1}. [${item.likelihood}] ${item.risk}`;
        if (item.contingency) line += `\n   If this happens: ${item.contingency}`;
        if (item.pivot_deadline) line += `\n   When to pivot: ${item.pivot_deadline}`;
        return line;
      }).join('\n\n');
      sections.push({ title: 'Section 5: Key Risks', text: riskText });
    }
    if (diagnosisData.alternative_paths?.length) {
      const altText = diagnosisData.alternative_paths.map((item: any, i: number) => {
        return `${i + 1}. ${item.strategy}\n   Why not now: ${item.why_rejected}\n   Revisit if: ${item.when_it_might_work}`;
      }).join('\n\n');
      sections.push({ title: 'Section 6: Alternative Paths', text: altText });
    }
    openShareModal({
      contentType: 'full_briefing',
      subject: `Strategic Briefing - ${currentCompany?.name || 'Your Company'}`,
      contentData: { sections },
    });
  };

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
      queryClient.invalidateQueries({ queryKey: ['strategic-diagnosis', currentCompany.id] });
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
    if (diagnosisData.execution_playbook?.length) {
      parts.push('4. EXECUTION PLAYBOOK');
      diagnosisData.execution_playbook.forEach((item: any, i: number) => {
        parts.push(`${i + 1}. ${item.action || item.description || ''}`);
        parts.push(`   Owner: ${item.owner || 'TBD'} | Timeline: ${item.timeline || 'TBD'}`);
        if (item.definition_of_done) parts.push(`   Done when: ${item.definition_of_done}`);
      });
      parts.push('');
    }
    if (diagnosisData.key_risks?.length) {
      parts.push('5. KEY RISKS & CONTINGENCY PLANS');
      diagnosisData.key_risks.forEach((item: any, i: number) => {
        parts.push(`${i + 1}. [${item.likelihood}] ${item.risk}`);
        if (item.contingency) parts.push(`   If this happens: ${item.contingency}`);
        if (item.pivot_deadline) parts.push(`   When to pivot: ${item.pivot_deadline}`);
      });
      parts.push('');
    }
    if (diagnosisData.alternative_paths?.length) {
      parts.push('6. ALTERNATIVE PATHS CONSIDERED');
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
  const executionPlaybook: Array<{phase?: string; action: string; owner: string; timeline: string; definition_of_done?: string; expected_outcome?: string}> | null = diagnosisData?.execution_playbook || null;
  const keyRisks: Array<{risk: string; likelihood: string; impact: string; contingency: string; pivot_deadline?: string}> | null = diagnosisData?.key_risks || null;
  const alternativePaths: Array<{strategy: string; why_rejected: string; when_it_might_work: string}> | null = diagnosisData?.alternative_paths || null;

  const totalPlaybookItems = executionPlaybook?.length || 0;

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

      {isLoading || isAnalyzing ? (
        <LoadingProgress />
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
        <article className="space-y-10" data-testid="article-briefing">

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
              <div className="flex items-center justify-between gap-4 flex-wrap mb-4">
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

          {executionPlaybook && executionPlaybook.length > 0 && (
            <section id="section-playbook" data-testid="section-playbook">
              <SectionDivider num={4} label="Execution Playbook" />
              <div className="flex items-center justify-between gap-4 flex-wrap mb-4">
                <h2 className="text-lg font-semibold tracking-tight" data-testid="text-section-4-title">
                  Execution Playbook
                </h2>
                {totalPlaybookItems > 0 && (
                  <span className="text-xs text-muted-foreground" data-testid="text-playbook-progress">
                    {checkedCount} of {totalPlaybookItems} completed
                  </span>
                )}
              </div>
              <p className="text-xs text-muted-foreground mb-6">
                Forward this to your team. Check off items as they are completed.
              </p>
              {(() => {
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
                              const isChecked = !!checked[idx];
                              if (!action) return null;
                              return (
                                <li
                                  key={idx}
                                  className={`relative pl-10 pr-8 transition-opacity ${isChecked ? 'opacity-50' : ''}`}
                                  data-testid={`playbook-item-${idx}`}
                                >
                                  <div className="absolute left-0 top-0.5">
                                    <Checkbox
                                      checked={isChecked}
                                      onCheckedChange={() => toggle(idx)}
                                      data-testid={`playbook-check-${idx}`}
                                    />
                                  </div>
                                  <button
                                    onClick={() => handleSharePlaybookItem(item)}
                                    className="absolute right-0 top-0 text-muted-foreground/40 hover:text-foreground transition-colors"
                                    title="Share this action item"
                                    data-testid={`button-share-playbook-${idx}`}
                                  >
                                    <Send className="h-3.5 w-3.5" />
                                  </button>
                                  <p className={`text-sm font-medium text-foreground leading-relaxed mb-2 ${isChecked ? 'line-through' : ''}`}>
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
                                    <p className={`text-xs text-muted-foreground mt-1 ${isChecked ? 'line-through' : ''}`} data-testid={`playbook-dod-${idx}`}>
                                      <span className="font-medium text-foreground/70">Done when:</span> {dod}
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
                      const isChecked = !!checked[i];
                      if (!action) return null;
                      return (
                        <li
                          key={i}
                          className={`relative pl-10 pr-8 transition-opacity ${isChecked ? 'opacity-50' : ''}`}
                          data-testid={`playbook-item-${i}`}
                        >
                          <div className="absolute left-0 top-0.5">
                            <Checkbox
                              checked={isChecked}
                              onCheckedChange={() => toggle(i)}
                              data-testid={`playbook-check-${i}`}
                            />
                          </div>
                          <button
                            onClick={() => handleSharePlaybookItem(item)}
                            className="absolute right-0 top-0 text-muted-foreground/40 hover:text-foreground transition-colors"
                            title="Share this action item"
                            data-testid={`button-share-playbook-${i}`}
                          >
                            <Send className="h-3.5 w-3.5" />
                          </button>
                          <p className={`text-sm font-medium text-foreground leading-relaxed mb-2 ${isChecked ? 'line-through' : ''}`}>
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
                            <p className={`text-xs text-muted-foreground mt-1 ${isChecked ? 'line-through' : ''}`} data-testid={`playbook-dod-${i}`}>
                              <span className="font-medium text-foreground/70">Done when:</span> {dod}
                            </p>
                          )}
                        </li>
                      );
                    })}
                  </ol>
                );
              })()}
            </section>
          )}

          {keyRisks && keyRisks.length > 0 && (
            <section id="section-key-risks" data-testid="section-key-risks">
              <SectionDivider num={5} label="Key Risks & Contingency Plans" />
              <h2 className="text-lg font-semibold mb-4 tracking-tight" data-testid="text-section-5-title">
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
              <SectionDivider num={6} label="Alternative Paths Considered" />
              <h2 className="text-lg font-semibold mb-4 tracking-tight" data-testid="text-section-6-title">
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
