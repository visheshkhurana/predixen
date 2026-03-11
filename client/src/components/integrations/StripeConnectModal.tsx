import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Shield, Eye, EyeOff, Loader2, AlertCircle, CheckCircle, Zap, ArrowRight, RefreshCw } from 'lucide-react';
import { SiStripe } from 'react-icons/si';
import { apiRequest } from '@/lib/queryClient';
import { useToast } from '@/hooks/use-toast';
import { getErrorMessage } from '@/lib/errors';

interface StripeConnectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConnected?: (metrics: Record<string, any>) => void;
  companyId?: number;
}

type ModalStep = 'input' | 'testing' | 'success' | 'error';

export function StripeConnectModal({
  isOpen,
  onClose,
  onConnected,
  companyId = 1,
}: StripeConnectModalProps) {
  const { toast } = useToast();
  const [apiKey, setApiKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [step, setStep] = useState<ModalStep>('input');
  const [errorMessage, setErrorMessage] = useState('');
  const [syncProgress, setSyncProgress] = useState(0);

  useEffect(() => {
    if (!isOpen) {
      setApiKey('');
      setShowKey(false);
      setStep('input');
      setErrorMessage('');
      setSyncProgress(0);
    }
  }, [isOpen]);

  const isValidKey = apiKey.startsWith('sk_live_') || apiKey.startsWith('sk_test_') || apiKey.startsWith('rk_live_') || apiKey.startsWith('rk_test_');

  const handleTestConnection = async () => {
    if (!apiKey.trim()) {
      setErrorMessage('Please enter your Stripe API key.');
      return;
    }
    if (!isValidKey) {
      setErrorMessage('Invalid key format. Stripe keys start with sk_live_, sk_test_, rk_live_, or rk_test_.');
      return;
    }

    setStep('testing');
    setErrorMessage('');
    setSyncProgress(0);

    const progressInterval = setInterval(() => {
      setSyncProgress(prev => {
        if (prev >= 90) {
          clearInterval(progressInterval);
          return 90;
        }
        return prev + Math.random() * 15;
      });
    }, 400);

    try {
      const res = await apiRequest('POST', `/api/connectors/companies/${companyId}/connect`, {
        provider_id: 'stripe',
        credentials: { api_key: apiKey },
      });
      const data = await res.json();

      clearInterval(progressInterval);
      setSyncProgress(100);

      setTimeout(() => {
        setStep('success');
        onConnected?.({});
      }, 500);
    } catch (err: any) {
      clearInterval(progressInterval);
      setSyncProgress(0);

      let msg = getErrorMessage(err, 'Connection test failed');
      if (err?.status === 401 || msg.toLowerCase().includes('auth')) {
        msg = 'Invalid API key. Please check your key and try again.';
      }

      setErrorMessage(msg);
      setStep('error');
    }
  };

  const handleTriggerSync = async () => {
    try {
      await apiRequest('POST', `/api/connectors/companies/${companyId}/sync/stripe`, {});
      toast({
        title: 'Sync Started',
        description: 'Initial data sync has been triggered. Metrics will update shortly.',
      });
      onClose();
    } catch (err) {
      toast({
        title: 'Sync Failed',
        description: getErrorMessage(err, 'Could not trigger sync'),
        variant: 'destructive',
      });
    }
  };

  const handleRetry = () => {
    setStep('input');
    setErrorMessage('');
    setSyncProgress(0);
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-md" data-testid="modal-stripe-connect">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 flex-wrap">
            <SiStripe className="h-5 w-5 text-[#635bff]" />
            Connect Stripe
          </DialogTitle>
          <DialogDescription>
            {step === 'input' && 'Enter your Stripe secret key to connect your payment data.'}
            {step === 'testing' && 'Testing connection and syncing your data...'}
            {step === 'success' && 'Stripe connected successfully.'}
            {step === 'error' && 'Connection failed. Please check your credentials.'}
          </DialogDescription>
        </DialogHeader>

        {step === 'input' && (
          <div className="space-y-4">
            <Card className="p-3">
              <div className="flex items-start gap-2">
                <Shield className="w-4 h-4 text-primary mt-0.5 shrink-0" />
                <p className="text-xs text-muted-foreground">
                  Your API key is encrypted at rest and never shared. We use read-only access to pull revenue, subscription, and customer metrics.
                </p>
              </div>
            </Card>

            <div className="space-y-2">
              <Label htmlFor="stripe-api-key">Stripe Secret Key <span className="text-destructive">*</span></Label>
              <div className="relative">
                <Input
                  id="stripe-api-key"
                  type={showKey ? 'text' : 'password'}
                  placeholder="sk_live_..."
                  value={apiKey}
                  onChange={(e) => {
                    setApiKey(e.target.value);
                    if (errorMessage) setErrorMessage('');
                  }}
                  className={errorMessage ? 'border-destructive pr-10' : 'pr-10'}
                  data-testid="input-stripe-api-key"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="absolute right-0 top-0 h-full"
                  onClick={() => setShowKey(!showKey)}
                  data-testid="button-toggle-stripe-key"
                >
                  {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </Button>
              </div>
              {errorMessage && (
                <p className="text-xs text-destructive flex items-center gap-1" data-testid="text-stripe-error">
                  <AlertCircle className="w-3 h-3 shrink-0" />
                  {errorMessage}
                </p>
              )}
              <p className="text-xs text-muted-foreground">
                Find your key in{' '}
                <a
                  href="https://dashboard.stripe.com/apikeys"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline"
                  data-testid="link-stripe-dashboard"
                >
                  Stripe Dashboard &rarr; Developers &rarr; API Keys
                </a>
              </p>
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground font-medium">Data we sync</Label>
              <div className="flex flex-wrap gap-1">
                {['MRR', 'ARR', 'Customers', 'Churn', 'Refunds', 'ARPU', 'Revenue'].map(m => (
                  <Badge key={m} variant="secondary" className="text-xs">
                    {m}
                  </Badge>
                ))}
              </div>
            </div>
          </div>
        )}

        {step === 'testing' && (
          <div className="py-6 flex flex-col items-center gap-4">
            <div className="relative">
              <Loader2 className="w-10 h-10 animate-spin text-[#635bff]" />
            </div>
            <div className="text-center space-y-1">
              <p className="text-sm font-medium" data-testid="text-stripe-testing">Testing connection...</p>
              <p className="text-xs text-muted-foreground">
                Verifying API key and pulling initial metrics
              </p>
            </div>
            <div className="w-full max-w-xs">
              <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                <div
                  className="h-full rounded-full bg-[#635bff] transition-all duration-300"
                  style={{ width: `${Math.min(syncProgress, 100)}%` }}
                  data-testid="progress-stripe-sync"
                />
              </div>
              <p className="text-xs text-muted-foreground text-center mt-1">
                {Math.round(Math.min(syncProgress, 100))}%
              </p>
            </div>
          </div>
        )}

        {step === 'success' && (
          <div className="py-6 flex flex-col items-center gap-4">
            <div className="rounded-full bg-chart-2/15 p-3">
              <CheckCircle className="w-8 h-8 text-chart-2" />
            </div>
            <div className="text-center space-y-1">
              <p className="text-sm font-medium" data-testid="text-stripe-success">Connected to Stripe</p>
              <p className="text-xs text-muted-foreground">
                Your payment data is now linked. Metrics will refresh automatically.
              </p>
            </div>

          </div>
        )}

        {step === 'error' && (
          <div className="py-6 flex flex-col items-center gap-4">
            <div className="rounded-full bg-destructive/15 p-3">
              <AlertCircle className="w-8 h-8 text-destructive" />
            </div>
            <div className="text-center space-y-1">
              <p className="text-sm font-medium" data-testid="text-stripe-error-title">Connection Failed</p>
              <p className="text-xs text-muted-foreground">
                {errorMessage || 'Could not connect to Stripe. Please verify your API key.'}
              </p>
            </div>
          </div>
        )}

        <DialogFooter>
          {step === 'input' && (
            <>
              <Button variant="outline" onClick={onClose} data-testid="button-stripe-cancel">
                Cancel
              </Button>
              <Button
                onClick={handleTestConnection}
                disabled={!apiKey.trim()}
                data-testid="button-stripe-test"
              >
                <Zap className="w-4 h-4 mr-1" />
                Test Connection
              </Button>
            </>
          )}
          {step === 'success' && (
            <>
              <Button variant="outline" onClick={onClose} data-testid="button-stripe-done">
                Done
              </Button>
              <Button onClick={handleTriggerSync} data-testid="button-stripe-sync">
                <RefreshCw className="w-4 h-4 mr-1" />
                Sync Now
              </Button>
            </>
          )}
          {step === 'error' && (
            <>
              <Button variant="outline" onClick={onClose} data-testid="button-stripe-close">
                Close
              </Button>
              <Button onClick={handleRetry} data-testid="button-stripe-retry">
                <ArrowRight className="w-4 h-4 mr-1" />
                Try Again
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default StripeConnectModal;
