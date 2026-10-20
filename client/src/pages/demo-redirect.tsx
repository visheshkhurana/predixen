import { useEffect, useState, useCallback } from 'react';
import { useLocation, Link } from 'wouter';
import { useToast } from '@/hooks/use-toast';
import { api, ApiError } from '@/api/client';
import { useFounderStore } from '@/store/founderStore';
import { withGtagPage } from '@/lib/analytics-url';
import { Button } from '@/components/ui/button';
import { Loader2, RefreshCw, UserPlus } from 'lucide-react';

/**
 * /demo/enter — the working demo entry point.
 *
 * This component existed but was imported in App.tsx and never routed, so the
 * one thing the site promised — "Try the live demo, sample company, no account
 * needed" — was reachable only by landing on /auth, reading past "Welcome back"
 * and finding the card on the login tab. HAG-449 routes it at `/demo/enter` and
 * points the hero, the header CTA and /demo at it.
 *
 * It logs into the shared sample account, selects the sample company, and lands
 * on /overview. No login form is rendered at any point: while the request is in
 * flight the visitor sees a loading line, and on failure a retry plus a real
 * signup link.
 */
export default function DemoRedirectPage() {
  const [, setLocation] = useLocation();
  const { toast } = useToast();
  const { setUser, setCompanies, setCurrentCompany } = useFounderStore();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loginDemo = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const result = await api.auth.login('demo@founderconsole.ai', 'demo123');

      setUser({ id: result.user_id, email: result.email, role: result.role, is_platform_admin: result.is_platform_admin, is_email_verified: result.is_email_verified });

      if (typeof window !== 'undefined' && (window as any).gtag) {
        (window as any).gtag('config', 'G-NJKW0TGC4C', withGtagPage({ user_id: String(result.user_id) }));
        (window as any).gtag('event', 'login', withGtagPage({ method: 'demo' }));
      }

      // HAG-453: this used to swallow a failed or empty companies.list() and
      // navigate anyway. The demo account was then logged in with no company
      // selected, /overview's AuthenticatedRoute bounced it to /onboarding, and
      // the visitor met a signup wall with no error and no retry — on the page
      // that is the front door. Throwing hands the failure to the outer catch
      // below, which shows "Try Again" and the /signup escape instead.
      const companies = await api.companies.list();
      if (!companies || companies.length === 0) {
        throw new Error('The demo account has no company to open.');
      }
      const demoCompany = companies.find((c: any) => c.name === 'TechFlow Analytics') || companies[0];
      setCompanies(companies);
      setCurrentCompany(demoCompany);

      toast({ title: 'Welcome to the demo!' });
      // /overview is the first screen the sample company has something to show.
      // Landing on `/` works too but relies on PublicOrAuthHome deciding to
      // forward, which is the indirection this route exists to remove.
      setLocation('/overview');
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Unable to load the demo right now. Please try again.';
      setError(message);
      setLoading(false);
    }
  }, [setUser, setCompanies, setCurrentCompany, setLocation, toast]);

  useEffect(() => {
    loginDemo();
  }, []);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-background" data-testid="page-demo-redirect">
      <div className="flex flex-col items-center gap-4">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-8 h-8 rounded-md bg-primary flex items-center justify-center">
            <span className="text-primary-foreground font-bold text-sm">FC</span>
          </div>
          <span className="text-lg font-semibold text-foreground tracking-tight">FounderConsole</span>
        </div>
        {error ? (
          <div className="flex flex-col items-center gap-4 text-center max-w-sm">
            <p className="text-sm text-destructive" data-testid="text-demo-error">{error}</p>
            <div className="flex items-center gap-3">
              <Button onClick={loginDemo} data-testid="button-demo-retry">
                <RefreshCw className="h-4 w-4 mr-2" />
                Try Again
              </Button>
              <Link href="/signup">
                <Button variant="outline" data-testid="button-demo-signup">
                  <UserPlus className="h-4 w-4 mr-2" />
                  Sign Up Instead
                </Button>
              </Link>
            </div>
          </div>
        ) : (
          <>
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground" data-testid="text-demo-loading">Loading demo environment...</p>
          </>
        )}
      </div>
    </div>
  );
}
