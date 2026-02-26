import { useState, useEffect, useCallback } from 'react';
import { AlertTriangle, RefreshCw, SlidersHorizontal, X } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';

const POLL_INTERVAL_DOWN = 10_000;
const POLL_INTERVAL_UP = 60_000;
const CONSECUTIVE_FAILURES_THRESHOLD = 2;

export function BackendStatusBanner() {
  const [isDown, setIsDown] = useState(false);
  const [consecutiveFailures, setConsecutiveFailures] = useState(0);
  const [dismissed, setDismissed] = useState(false);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const checkHealth = useCallback(async () => {
    try {
      const res = await fetch('/health', { signal: AbortSignal.timeout(5000) });
      if (res.ok) {
        const data = await res.json();
        if (data.fastapi === 'up') {
          setConsecutiveFailures(0);
          if (isDown) {
            setIsDown(false);
            setDismissed(false);
          }
        } else {
          setConsecutiveFailures(prev => {
            const next = prev + 1;
            if (next >= CONSECUTIVE_FAILURES_THRESHOLD) setIsDown(true);
            return next;
          });
        }
      } else {
        setConsecutiveFailures(prev => {
          const next = prev + 1;
          if (next >= CONSECUTIVE_FAILURES_THRESHOLD) setIsDown(true);
          return next;
        });
      }
    } catch {
      setConsecutiveFailures(prev => {
        const next = prev + 1;
        if (next >= CONSECUTIVE_FAILURES_THRESHOLD) setIsDown(true);
        return next;
      });
    }
    setLastChecked(new Date());
  }, [isDown]);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, isDown ? POLL_INTERVAL_DOWN : POLL_INTERVAL_UP);
    return () => clearInterval(interval);
  }, [isDown, checkHealth]);

  if (!isDown || dismissed) return null;

  return (
    <Alert
      variant="destructive"
      className="rounded-none border-x-0 border-t-0 bg-amber-50 dark:bg-amber-950/50 border-amber-300 dark:border-amber-700 py-2 px-4"
      data-testid="banner-backend-status"
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400 shrink-0" />
          <AlertDescription className="text-amber-800 dark:text-amber-200 text-sm">
            <span className="font-medium">Simulation engine temporarily unavailable.</span>{' '}
            Your data is safe. Use the manual sensitivity sliders for quick estimates, or try again in a few minutes.
          </AlertDescription>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-amber-700 dark:text-amber-300 hover:bg-amber-100 dark:hover:bg-amber-900/50"
            onClick={checkHealth}
            data-testid="button-retry-connection"
          >
            <RefreshCw className="h-3.5 w-3.5 mr-1" />
            Retry
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-amber-700 dark:text-amber-300 hover:bg-amber-100 dark:hover:bg-amber-900/50"
            onClick={() => setDismissed(true)}
            data-testid="button-dismiss-banner"
          >
            <X className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
    </Alert>
  );
}
