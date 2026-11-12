import { useEffect, useState } from 'react';
import { useLocation } from 'wouter';
import { useFounderStore } from '@/store/founderStore';
import { useToast } from '@/hooks/use-toast';
import { api } from '@/api/client';
import { trackFunnel } from '@/lib/funnel';
import { metaTrack } from '@/lib/metaPixel';
import { Loader2 } from 'lucide-react';

export default function AuthCallback() {
  const [, setLocation] = useLocation();
  const { setUser, setCurrentCompany, setCompanies } = useFounderStore();
  const { toast } = useToast();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const userId = params.get('user_id');
    const email = params.get('email');
    const role = params.get('role');
    const isAdmin = params.get('is_platform_admin') === 'true';
    // Set by the server only when this callback created the account.
    const isNewUser = params.get('new_user') === '1';
    const errorParam = params.get('error');

    if (errorParam) {
      const messages: Record<string, string> = {
        google_denied: 'Google sign-in was cancelled',
        github_denied: 'GitHub sign-in was cancelled',
        google_token_failed: 'Could not complete Google sign-in. Please try again.',
        github_token_failed: 'Could not complete GitHub sign-in. Please try again.',
        google_no_email: 'No email found on your Google account',
        github_no_email: 'No email found on your GitHub account. Make sure your email is public or verified.',
        google_profile_failed: 'Could not retrieve your Google profile',
        google_unverified_email: 'Your Google account email is not verified. Verify it with Google, then try again.',
        google_account_mismatch: 'This email is already linked to a different Google account.',
        github_profile_failed: 'Could not retrieve your GitHub profile',
      };
      setError(messages[errorParam] || 'Sign-in failed. Please try again.');
      toast({ title: 'Sign-in failed', description: messages[errorParam] || errorParam, variant: 'destructive' });
      setTimeout(() => setLocation('/auth'), 2000);
      return;
    }

    if (!userId || !email) {
      setError('Invalid callback. Missing authentication data.');
      setTimeout(() => setLocation('/auth'), 2000);
      return;
    }

    setUser({
      id: parseInt(userId),
      email,
      role: role || 'viewer',
      is_platform_admin: isAdmin,
    });

    if (typeof window !== 'undefined' && (window as any).gtag) {
      (window as any).gtag('config', 'G-NJKW0TGC4C', { user_id: userId });
      if (!isNewUser) (window as any).gtag('event', 'login', { method: 'oauth' });
    }

    if (isNewUser) {
      // Same conversion set as the email signup in auth.tsx, so Google signups
      // (the main path) count in GA4, Meta and PostHog.
      metaTrack('CompleteRegistration', { method: 'google' });
      trackFunnel('signup_completed', { method: 'google', user_id: parseInt(userId) });
      trackFunnel('sign_up', { method: 'google', user_id: parseInt(userId) });
    }

    (async () => {
      try {
        const companies = await api.companies.list();
        if (companies && companies.length > 0) {
          setCompanies(companies);
          setCurrentCompany(companies[0]);
        }
        toast({ title: 'Welcome!' });
        if (!isAdmin && (!companies || companies.length === 0)) {
          // No company yet: finish onboarding. The signup conversion fired
          // above from new_user, so a returning user who never onboarded is
          // not counted twice.
          setLocation('/onboarding');
        } else {
          setLocation('/');
        }
      } catch {
        toast({ title: 'Welcome!' });
        setLocation('/');
      }
    })();
  }, []);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center space-y-4">
          <p className="text-destructive text-lg font-medium">{error}</p>
          <p className="text-muted-foreground text-sm">Redirecting to sign in...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="text-center space-y-4">
        <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
        <p className="text-muted-foreground">Completing sign-in...</p>
      </div>
    </div>
  );
}
