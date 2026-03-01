import { useEffect, useState, useCallback } from 'react';
import { useLocation, Link } from 'wouter';
import { useToast } from '@/hooks/use-toast';
import { api, ApiError } from '@/api/client';
import { useFounderStore } from '@/store/founderStore';
import { Button } from '@/components/ui/button';
import { Loader2, RefreshCw, UserPlus } from 'lucide-react';

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

      setUser({ id: result.user_id, email: result.email, role: result.role, is_platform_admin: result.is_platform_admin });

      if (typeof window !== 'undefined' && (window as any).gtag) {
        (window as any).gtag('config', 'G-NJKW0TGC4C', { user_id: String(result.user_id) });
        (window as any).gtag('set', 'user_properties', { user_email: result.email });
        (window as any).gtag('event', 'login', { method: 'demo' });
      }
      if (typeof window !== 'undefined' && (window as any).fbq) {
        (window as any).fbq('init', '872167299140812', { em: result.email });
      }

      try {
        const companies = await api.companies.list();
        if (companies && companies.length > 0) {
          const demoCompany = companies.find((c: any) => c.name === 'TechFlow Analytics') || companies[0];
          setCompanies(companies);
          setCurrentCompany(demoCompany);
        }
      } catch {
        console.warn('Failed to auto-select demo company');
      }

      toast({ title: 'Welcome to the demo!' });
      setLocation('/');
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
              <Link href="/auth">
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
