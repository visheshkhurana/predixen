import { useState } from 'react';
import { MessageSquare, X, Send, Loader2, CheckCircle, Bug, Lightbulb, MessageCircle, HelpCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';
import { useFounderStore } from '@/store/founderStore';

function getCSRFToken(): string | null {
  const name = 'X-CSRF-Token=';
  const cookies = document.cookie.split(';');
  for (const c of cookies) {
    const trimmed = c.trim();
    if (trimmed.startsWith(name)) return trimmed.substring(name.length);
  }
  return null;
}

type FeedbackType = 'bug' | 'feature' | 'general' | 'question';

const TYPES: { value: FeedbackType; label: string; icon: any }[] = [
  { value: 'bug', label: 'Bug Report', icon: Bug },
  { value: 'feature', label: 'Feature Request', icon: Lightbulb },
  { value: 'general', label: 'General', icon: MessageCircle },
  { value: 'question', label: 'Question', icon: HelpCircle },
];

export function FeedbackWidget() {
  const [open, setOpen] = useState(false);
  const [type, setType] = useState<FeedbackType>('general');
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const { toast } = useToast();
  const { token } = useFounderStore();

  const handleSubmit = async () => {
    if (!message.trim()) return;
    setSending(true);
    try {
      const csrfToken = getCSRFToken();
      const res = await fetch('/api/feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}),
        },
        body: JSON.stringify({ type, message: message.trim(), page: window.location.pathname }),
      });
      if (!res.ok) throw new Error('Failed to send feedback');
      setSent(true);
      setTimeout(() => {
        setOpen(false);
        setSent(false);
        setMessage('');
        setType('general');
      }, 1800);
    } catch {
      toast({ title: 'Could not send feedback', description: 'Please try again later.', variant: 'destructive' });
    } finally {
      setSending(false);
    }
  };

  if (sent) {
    return (
      <div className="fixed bottom-24 right-6 z-40 w-80 rounded-xl border bg-background shadow-2xl p-6 text-center space-y-3" data-testid="feedback-success">
        <CheckCircle className="h-10 w-10 text-emerald-500 mx-auto" />
        <p className="text-sm font-medium">Thanks for your feedback!</p>
        <p className="text-xs text-muted-foreground">We read every submission and use it to improve FounderConsole.</p>
      </div>
    );
  }

  return (
    <>
      {open && (
        <div className="fixed bottom-24 right-6 z-40 w-80 rounded-xl border bg-background shadow-2xl" data-testid="feedback-panel">
          <div className="flex items-center justify-between px-4 py-3 border-b">
            <h3 className="text-sm font-semibold">Send Feedback</h3>
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setOpen(false)} data-testid="button-feedback-close">
              <X className="h-4 w-4" />
            </Button>
          </div>
          <div className="p-4 space-y-4">
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Type</Label>
              <div className="grid grid-cols-2 gap-2">
                {TYPES.map((t) => (
                  <button
                    key={t.value}
                    onClick={() => setType(t.value)}
                    className={`flex-1 text-xs py-1.5 px-2 rounded-md border transition-colors flex items-center justify-center gap-1.5 ${
                      type === t.value
                        ? 'border-indigo-500 bg-indigo-500/10 text-indigo-400'
                        : 'border-border hover:border-border/80 text-muted-foreground'
                    }`}
                    data-testid={`button-feedback-type-${t.value}`}
                  >
                    <t.icon className="h-3 w-3" />
                    {t.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="feedback-msg" className="text-xs font-medium">Message</Label>
              <Textarea
                id="feedback-msg"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Tell us what you think..."
                className="min-h-[100px] text-sm resize-none"
                data-testid="input-feedback-message"
              />
            </div>
            <Button
              className="w-full h-9 text-sm bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700"
              disabled={!message.trim() || sending}
              onClick={handleSubmit}
              data-testid="button-feedback-submit"
            >
              {sending ? (
                <><Loader2 className="h-4 w-4 animate-spin mr-2" /> Sending...</>
              ) : (
                <><Send className="h-4 w-4 mr-2" /> Submit Feedback</>
              )}
            </Button>
            <p className="text-[10px] text-muted-foreground/60 text-center">
              Your feedback is stored securely and reviewed by our team.
            </p>
          </div>
        </div>
      )}

      <Button
        onClick={() => setOpen(!open)}
        className="fixed bottom-24 right-6 z-30 rounded-full shadow-lg h-12 px-4 gap-2 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white"
        data-testid="button-feedback"
      >
        <MessageSquare className="h-4 w-4" />
        <span className="text-sm font-medium">Feedback</span>
      </Button>
    </>
  );
}
