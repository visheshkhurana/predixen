import { useState, useEffect } from 'react';
import { useLocation } from 'wouter';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Loader2, CheckCircle, AlertCircle, Sparkles } from 'lucide-react';
import { useFounderStore } from '@/store/founderStore';

export default function VerifyEmailPage() {
  const [, setLocation] = useLocation();
  const { user, setUser } = useFounderStore();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');

    if (!token) {
      setStatus('error');
      setMessage('Invalid verification link. No token provided.');
      return;
    }

    fetch(`/api/auth/verify-email?token=${encodeURIComponent(token)}`)
      .then(async (res) => {
        const data = await res.json();
        if (res.ok) {
          setStatus('success');
          setMessage(data.message || 'Email verified successfully.');
          if (user) {
            setUser({ ...user, is_email_verified: true });
          }
        } else {
          setStatus('error');
          setMessage(data.detail || 'Verification failed.');
        }
      })
      .catch(() => {
        setStatus('error');
        setMessage('Something went wrong. Please try again.');
      });
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardContent className="p-6 text-center space-y-4">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center mx-auto mb-2">
            <Sparkles className="h-5 w-5 text-white" />
          </div>

          {status === 'loading' && (
            <>
              <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
              <h2 className="text-xl font-semibold">Verifying your email...</h2>
              <p className="text-sm text-muted-foreground">Please wait while we verify your email address.</p>
            </>
          )}

          {status === 'success' && (
            <>
              <div className="w-12 h-12 rounded-full bg-emerald-500/10 flex items-center justify-center mx-auto">
                <CheckCircle className="h-6 w-6 text-emerald-500" />
              </div>
              <h2 className="text-xl font-semibold" data-testid="text-verify-success">Email Verified</h2>
              <p className="text-sm text-muted-foreground">{message}</p>
              <Button className="w-full" onClick={() => setLocation('/')} data-testid="button-go-dashboard">
                Go to Dashboard
              </Button>
            </>
          )}

          {status === 'error' && (
            <>
              <div className="w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center mx-auto">
                <AlertCircle className="h-6 w-6 text-red-500" />
              </div>
              <h2 className="text-xl font-semibold" data-testid="text-verify-error">Verification Failed</h2>
              <p className="text-sm text-muted-foreground">{message}</p>
              <Button className="w-full" onClick={() => setLocation('/auth')} data-testid="button-back-login">
                Back to Sign In
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
