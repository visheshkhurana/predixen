import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Loader2, Mail, Plus, X, Send, AlertTriangle, CheckCircle, Target, TrendingUp, Shield, BarChart3, Users } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { apiRequest } from '@/lib/queryClient';

export type ShareContentType =
  | 'risk'
  | 'recommendation'
  | 'full_briefing'
  | 'playbook_item'
  | 'simulation_summary'
  | 'ai_decision'
  | 'counter_move'
  | 'custom';

export interface ShareModalData {
  contentType: ShareContentType;
  subject: string;
  contentData: Record<string, any>;
}

interface ShareModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  data: ShareModalData | null;
  companyId: number;
  companyName: string;
}

const TYPE_LABELS: Record<ShareContentType, string> = {
  risk: 'Risk Alert',
  recommendation: 'Recommendation',
  full_briefing: 'Full Briefing',
  playbook_item: 'Action Item',
  simulation_summary: 'Simulation Results',
  ai_decision: 'AI Decision Summary',
  counter_move: 'Counter-Move',
  custom: 'Shared Item',
};

const TYPE_ICONS: Record<ShareContentType, typeof Mail> = {
  risk: AlertTriangle,
  recommendation: Target,
  full_briefing: BarChart3,
  playbook_item: CheckCircle,
  simulation_summary: TrendingUp,
  ai_decision: Shield,
  counter_move: TrendingUp,
  custom: Mail,
};

function ContentPreview({ data }: { data: ShareModalData }) {
  const { contentType, contentData } = data;

  if (contentType === 'risk' && contentData.risk) {
    const likelihoodColors: Record<string, string> = {
      high: 'text-red-500',
      medium: 'text-amber-500',
      low: 'text-emerald-500',
    };
    return (
      <div className="rounded-md bg-muted p-3 space-y-2" data-testid="share-preview-risk">
        <p className="text-xs text-muted-foreground font-medium">Risk being shared:</p>
        <p className="text-sm text-foreground font-medium">{contentData.risk}</p>
        {contentData.likelihood && (
          <p className={`text-xs font-semibold ${likelihoodColors[contentData.likelihood.toLowerCase()] || 'text-muted-foreground'}`}>
            Likelihood: {contentData.likelihood}
          </p>
        )}
        {contentData.contingency && (
          <p className="text-xs text-muted-foreground">Contingency: {contentData.contingency}</p>
        )}
      </div>
    );
  }

  if (contentType === 'recommendation' && contentData.headline) {
    return (
      <div className="rounded-md bg-muted p-3 space-y-2" data-testid="share-preview-recommendation">
        <p className="text-xs text-muted-foreground font-medium">Recommendation being shared:</p>
        <p className="text-sm text-foreground font-medium">{contentData.headline}</p>
        {contentData.urgency && (
          <p className="text-xs text-amber-500">{contentData.urgency}</p>
        )}
      </div>
    );
  }

  if (contentType === 'full_briefing') {
    return (
      <div className="rounded-md bg-muted p-3" data-testid="share-preview-briefing">
        <p className="text-xs text-muted-foreground font-medium">The full strategic briefing will be sent.</p>
        {contentData.sections?.length > 0 && (
          <p className="text-xs text-muted-foreground mt-1">{contentData.sections.length} sections included</p>
        )}
      </div>
    );
  }

  if (contentType === 'playbook_item') {
    return (
      <div className="rounded-md bg-muted p-3 space-y-1" data-testid="share-preview-playbook">
        <p className="text-xs text-muted-foreground font-medium">Action item being shared:</p>
        <p className="text-sm text-foreground font-medium">{contentData.action || contentData.title}</p>
        <div className="flex flex-wrap gap-2 mt-1">
          {contentData.owner && <Badge variant="secondary" className="text-[10px]"><Users className="h-3 w-3 mr-1" />{contentData.owner}</Badge>}
          {contentData.timeline && <Badge variant="secondary" className="text-[10px]">{contentData.timeline}</Badge>}
        </div>
      </div>
    );
  }

  if (contentType === 'ai_decision') {
    const verdictColors: Record<string, string> = {
      GO: 'text-emerald-500',
      'NO-GO': 'text-red-500',
      'CONDITIONAL GO': 'text-amber-500',
    };
    return (
      <div className="rounded-md bg-muted p-3 space-y-2" data-testid="share-preview-ai-decision">
        <p className="text-xs text-muted-foreground font-medium">AI Decision Summary:</p>
        <p className="text-sm text-foreground font-medium">{contentData.recommendation}</p>
        <div className="flex items-center gap-3">
          {contentData.verdict && (
            <span className={`text-xs font-bold ${verdictColors[contentData.verdict] || 'text-muted-foreground'}`}>
              {contentData.verdict}
            </span>
          )}
          {contentData.score != null && (
            <span className="text-xs text-muted-foreground">Score: {contentData.score}/10</span>
          )}
        </div>
        {contentData.bullets?.length > 0 && (
          <ul className="text-xs text-muted-foreground space-y-0.5 mt-1">
            {contentData.bullets.map((b: string, i: number) => (
              <li key={i}>{b}</li>
            ))}
          </ul>
        )}
      </div>
    );
  }

  if (contentType === 'simulation_summary') {
    return (
      <div className="rounded-md bg-muted p-3 space-y-2" data-testid="share-preview-simulation">
        <p className="text-xs text-muted-foreground font-medium">Simulation results being shared:</p>
        <p className="text-sm text-foreground font-medium">{contentData.scenario_name || 'Scenario'}</p>
        <div className="grid grid-cols-2 gap-2 mt-1">
          {contentData.runway_p50 != null && (
            <div>
              <p className="text-[10px] text-muted-foreground">Runway (P50)</p>
              <p className="text-xs font-mono font-medium">{contentData.runway_p50} months</p>
            </div>
          )}
          {contentData.survival_18m != null && (
            <div>
              <p className="text-[10px] text-muted-foreground">Survival (18m)</p>
              <p className="text-xs font-mono font-medium">{contentData.survival_18m}%</p>
            </div>
          )}
          {contentData.end_cash != null && (
            <div>
              <p className="text-[10px] text-muted-foreground">End Cash</p>
              <p className="text-xs font-mono font-medium">{contentData.end_cash_formatted || `$${(contentData.end_cash / 1000).toFixed(0)}k`}</p>
            </div>
          )}
          {contentData.monthly_burn != null && (
            <div>
              <p className="text-[10px] text-muted-foreground">Monthly Burn</p>
              <p className="text-xs font-mono font-medium">{contentData.monthly_burn_formatted || `$${(contentData.monthly_burn / 1000).toFixed(0)}k`}</p>
            </div>
          )}
        </div>
      </div>
    );
  }

  if (contentType === 'counter_move') {
    return (
      <div className="rounded-md bg-muted p-3 space-y-2" data-testid="share-preview-counter-move">
        <p className="text-xs text-muted-foreground font-medium">Counter-move being shared:</p>
        <p className="text-sm text-foreground font-medium">{contentData.name}</p>
        {contentData.runway_delta != null && (
          <p className={`text-xs font-medium ${contentData.runway_delta >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
            Runway impact: {contentData.runway_delta >= 0 ? '+' : ''}{contentData.runway_delta.toFixed(1)} months
          </p>
        )}
        {contentData.survival_delta != null && (
          <p className={`text-xs ${contentData.survival_delta >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
            Survival impact: {contentData.survival_delta >= 0 ? '+' : ''}{contentData.survival_delta.toFixed(0)}%
          </p>
        )}
      </div>
    );
  }

  if (contentData.title || contentData.description) {
    return (
      <div className="rounded-md bg-muted p-3" data-testid="share-preview-custom">
        {contentData.title && <p className="text-sm text-foreground font-medium">{contentData.title}</p>}
        {contentData.description && <p className="text-xs text-muted-foreground mt-1">{contentData.description}</p>}
      </div>
    );
  }

  return null;
}

export function ShareModal({ open, onOpenChange, data, companyId, companyName }: ShareModalProps) {
  const { toast } = useToast();
  const [recipients, setRecipients] = useState<string[]>(['']);
  const [subject, setSubject] = useState('');
  const [personalNote, setPersonalNote] = useState('');
  const [isSending, setIsSending] = useState(false);

  useEffect(() => {
    if (data) {
      setSubject(data.subject);
      setRecipients(['']);
      setPersonalNote('');
    }
  }, [data]);

  const updateRecipient = (index: number, value: string) => {
    setRecipients(prev => {
      const next = [...prev];
      next[index] = value;
      return next;
    });
  };

  const addRecipient = () => {
    if (recipients.length < 10) {
      setRecipients(prev => [...prev, '']);
    }
  };

  const removeRecipient = (index: number) => {
    if (recipients.length > 1) {
      setRecipients(prev => prev.filter((_, i) => i !== index));
    }
  };

  const handleSend = async () => {
    const validEmails = recipients.map(r => r.trim()).filter(Boolean);
    if (validEmails.length === 0) {
      toast({ title: 'Email required', description: 'Please enter at least one recipient email address.', variant: 'destructive' });
      return;
    }

    const emailRegex = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
    const invalidEmails = validEmails.filter(e => !emailRegex.test(e));
    if (invalidEmails.length > 0) {
      toast({ title: 'Invalid email', description: `Please fix: ${invalidEmails.join(', ')}`, variant: 'destructive' });
      return;
    }

    setIsSending(true);
    try {
      const results = await Promise.allSettled(
        validEmails.map(email =>
          apiRequest('POST', `/api/companies/${companyId}/share-action-item`, {
            to_email: email,
            subject: subject || undefined,
            content_type: data?.contentType || 'custom',
            content_data: data?.contentData || {},
            personal_note: personalNote.trim() || undefined,
          })
        )
      );

      const successes = results.filter(r => r.status === 'fulfilled').length;
      const failures = results.filter(r => r.status === 'rejected').length;

      if (failures === 0) {
        toast({ title: 'Sent', description: `Email sent to ${successes} recipient${successes > 1 ? 's' : ''}` });
      } else if (successes > 0) {
        toast({ title: 'Partially sent', description: `Sent to ${successes}, failed for ${failures} recipient${failures > 1 ? 's' : ''}`, variant: 'destructive' });
      } else {
        toast({ title: 'Failed to send', description: 'Could not send to any recipient.', variant: 'destructive' });
      }

      if (successes > 0) {
        onOpenChange(false);
      }
    } catch (err: any) {
      toast({ title: 'Failed to send', description: err.message || 'Something went wrong.', variant: 'destructive' });
    } finally {
      setIsSending(false);
    }
  };

  const Icon = TYPE_ICONS[data?.contentType || 'custom'];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md" data-testid="share-modal">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2" data-testid="share-modal-title">
            <Icon className="h-4 w-4 text-primary" />
            Share {TYPE_LABELS[data?.contentType || 'custom']}
          </DialogTitle>
          <DialogDescription>
            Send this as a professional email via Predixen.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label>Recipients</Label>
            {recipients.map((email, i) => (
              <div key={i} className="flex items-center gap-2">
                <Input
                  type="email"
                  placeholder="team@company.com"
                  value={email}
                  onChange={(e) => updateRecipient(i, e.target.value)}
                  data-testid={`input-share-email-${i}`}
                />
                {recipients.length > 1 && (
                  <Button size="icon" variant="ghost" onClick={() => removeRecipient(i)} data-testid={`button-remove-recipient-${i}`}>
                    <X className="h-4 w-4" />
                  </Button>
                )}
              </div>
            ))}
            {recipients.length < 10 && (
              <Button variant="ghost" size="sm" onClick={addRecipient} className="text-xs" data-testid="button-add-recipient">
                <Plus className="h-3 w-3 mr-1" />
                Add recipient
              </Button>
            )}
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

          {data && <ContentPreview data={data} />}

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
