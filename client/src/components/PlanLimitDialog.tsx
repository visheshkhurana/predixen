import { useEffect, useState } from 'react';
import { useLocation } from 'wouter';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { trackEvent } from '@/lib/posthog';
import { PLAN_LIMIT_EVENT, planLimitNoun, type PlanLimitInfo } from '@/lib/planLimit';

/** Opens when any request hits 402 plan_limit_reached; offers the upgrade. */
export function PlanLimitDialog() {
  const [, setLocation] = useLocation();
  const [info, setInfo] = useState<PlanLimitInfo | null>(null);

  useEffect(() => {
    const onLimit = (e: Event) => {
      const next = (e as CustomEvent<PlanLimitInfo>).detail;
      if (!next) return;
      setInfo(next);
      trackEvent('plan_limit_shown', { limit: next.limit, plan: next.currentPlan, used: next.used, max: next.max });
    };
    window.addEventListener(PLAN_LIMIT_EVENT, onLimit);
    return () => window.removeEventListener(PLAN_LIMIT_EVENT, onLimit);
  }, []);

  const close = () => setInfo(null);

  return (
    <Dialog open={info !== null} onOpenChange={(open) => !open && close()}>
      <DialogContent data-testid="dialog-plan-limit">
        <DialogHeader>
          <DialogTitle>You've used this month's {info ? planLimitNoun(info.limit) : 'allowance'}</DialogTitle>
          <DialogDescription data-testid="text-plan-limit-message">{info?.message}</DialogDescription>
        </DialogHeader>
        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" onClick={close} data-testid="button-plan-limit-dismiss">
            Not now
          </Button>
          <Button
            onClick={() => {
              trackEvent('upgrade_click', { source: 'plan_limit', limit: info?.limit, plan: info?.currentPlan });
              close();
              setLocation('/billing');
            }}
            data-testid="button-plan-limit-upgrade"
          >
            See plans
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
