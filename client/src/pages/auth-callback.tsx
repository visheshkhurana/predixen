import { useEffect, useState } from 'react';
import { useLocation } from 'wouter';
import { useFounderStore } from '@/store/founderStore';
import { useToast } from '@/hooks/use-toast';
import { api } from '@/api/client';
import { Loader2 } from 'lucide-react';

export default function AuthCallback() {
  const [, setLocation] = useLocation();
  const { setToken, setUser, setCurrentCompany, setCompanies } = useFounderStore();
  const { toast } = useToast();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');
    const userId = params.get('user_id');
    const email = params.get('email');
    const role = params.get('role');
    const isAdmin = params.get('is_platform_admin') === 'true';
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
        github_profile_failed: 'Could not retrieve your GitHub profile',
      };
      setError(messages[errorParam] || 'Sign-in failed. Please try again.');
      toast({ title: 'Sign-in failed', description: messages[errorParam] || errorParam, variant: 'destructive' });
      setTimeout(() => setLocation('/auth'), 2000);
      return;
    }

    if (!token || !userId || !email) {
      setError('Invalid callback. Missing authentication data.');
      setTimeout(() => setLocation('/auth'), 2000);
      return;
    }

    localStorage.setItem('founderconsole-token', token);
    setToken(token);
    setUser({
      id: parseInt(userId),
      email,
      role: role || 'viewer',
      is_platform_admin: isAdmin,
    });

    if (typeof window !== 'undefined' && (window as any).gtag) {
      (window as any).gtag('config', 'G-NJKW0TGC4C', { user_id: userId });
      (window as any).gtag('event', 'login', { method: 'oauth' });
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
