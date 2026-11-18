import { useLocation } from 'wouter';
import { UserPlus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useFounderStore } from '@/store/founderStore';
import { isDemoEmail } from '@/lib/demo';
import { trackEvent } from '@/lib/posthog';

/**
 * "Run this on your own numbers" prompt shown after a simulation result in a
 * demo session. Real accounts never see it.
 *
 * Signing out first is what makes the link work: with the demo session still
 * active, /signup bounces straight back to /overview (same reason as the demo
 * banner in App.tsx).
 */
export function DemoSignupCTA({ show = true, placement, className = '' }: { show?: boolean; placement: string; className?: string }) {
  const user = useFounderStore((s) => s.user);
  const [, navigate] = useLocation();
  if (!show || !isDemoEmail(user?.email)) return null;

  const onClick = async () => {
    try { trackEvent('demo_signup_cta_clicked', { placement }); } catch {}
    try { await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' }); } catch {}
    useFounderStore.getState().logout();
    navigate('/signup');
  };

  return (
    <div
      className={`flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-lg border border-primary/20 bg-primary/[0.05] p-4 ${className}`}
      data-testid={`demo-signup-cta-${placement}`}
    >
      <div className="min-w-0">
        <p className="text-sm font-medium">Create your free account to run this on your numbers</p>
        <p className="text-xs text-muted-foreground mt-0.5">
          This result uses the sample company. Add your own revenue, costs and cash to see your runway.
        </p>
      </div>
      <Button size="sm" onClick={onClick} className="shrink-0" data-testid={`button-demo-signup-cta-${placement}`}>
        <UserPlus className="h-3.5 w-3.5 mr-1.5" />
        Create free account
      </Button>
    </div>
  );
}
