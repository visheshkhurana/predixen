import { useState } from 'react';
import { useSubscription, usePlans, useStartTrial, type PlanData } from '@/hooks/use-subscription';
import { useToast } from '@/hooks/use-toast';
import { Check, Sparkles, Zap, Crown, ArrowRight, Clock, CreditCard, AlertCircle } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';

const PLAN_ICONS: Record<string, typeof Sparkles> = {
  free: Zap,
  starter: Sparkles,
  growth: Sparkles,
  scale: Crown,
};

const PLAN_ACCENTS: Record<string, string> = {
  free: 'border-white/[0.06]',
  starter: 'border-white/[0.08]',
  growth: 'border-emerald-500/30 ring-1 ring-emerald-500/10',
  scale: 'border-white/[0.08]',
};

const PLAN_HIERARCHY = ['free', 'starter', 'growth', 'scale'];

function planRank(plan: string): number {
  const idx = PLAN_HIERARCHY.indexOf(plan);
  return idx >= 0 ? idx : 0;
}

function PlanCard({
  plan,
  currentPlan,
  isActive,
  isTrial,
  onSelect,
  popular,
}: {
  plan: PlanData;
  currentPlan: string;
  isActive: boolean;
  isTrial: boolean;
  onSelect: (planId: string) => void;
  popular?: boolean;
}) {
  const isCurrent = isActive && currentPlan === plan.id;
  const isUpgrade = planRank(plan.id) > planRank(isActive ? currentPlan : 'free');
  const isDowngrade = isActive && planRank(plan.id) < planRank(currentPlan);
  const Icon = PLAN_ICONS[plan.id] || Sparkles;

  return (
    <div
      className={`relative rounded-xl border bg-white/[0.02] p-6 flex flex-col
        ${PLAN_ACCENTS[plan.id] || 'border-white/[0.06]'}
        ${popular ? 'bg-emerald-500/[0.03]' : ''}
        transition-all hover:bg-white/[0.04]`}
      data-testid={`plan-card-${plan.id}`}
    >
      {popular && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full
          bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 text-[10px] font-medium uppercase tracking-wider">
          Most popular
        </div>
      )}

      <div className="flex items-center gap-2.5 mb-4">
        <div className={`h-8 w-8 rounded-lg flex items-center justify-center
          ${popular ? 'bg-emerald-500/10' : 'bg-white/[0.06]'}`}>
          <Icon className={`h-4 w-4 ${popular ? 'text-emerald-400' : 'text-white/50'}`} />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-white/90">{plan.name}</h3>
          <p className="text-[11px] text-white/40">{plan.tagline}</p>
        </div>
      </div>

      <div className="mb-5">
        {plan.price_monthly === 0 ? (
          <div className="text-2xl font-bold text-white/80">Free</div>
        ) : (
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-bold text-white/90">${plan.price_monthly}</span>
            <span className="text-xs text-white/40">/mo</span>
          </div>
        )}
        {plan.price_annual > 0 && (
          <p className="text-[11px] text-white/30 mt-0.5">
            ${plan.price_annual}/yr (save ${plan.price_monthly * 12 - plan.price_annual})
          </p>
        )}
      </div>

      <ul className="space-y-2 mb-6 flex-1">
        {plan.highlights.map((h, i) => (
          <li key={i} className="flex items-start gap-2 text-xs text-white/60">
            <Check className={`h-3.5 w-3.5 mt-0.5 shrink-0 ${popular ? 'text-emerald-400' : 'text-white/30'}`} />
            <span>{h}</span>
          </li>
        ))}
      </ul>

      {isCurrent ? (
        <div className="flex items-center justify-center gap-2 py-2.5 rounded-lg
          bg-white/[0.06] border border-white/[0.08] text-white/50 text-sm"
          data-testid={`plan-current-${plan.id}`}
        >
          <Check className="h-4 w-4" />
          <span>Current plan{isTrial ? ' (trial)' : ''}</span>
        </div>
      ) : plan.price_monthly === 0 ? (
        <div className="py-2.5 text-center text-white/30 text-sm">
          Free forever
        </div>
      ) : (
        <button
          onClick={() => onSelect(plan.id)}
          className={`flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium transition-all
            ${popular
              ? 'bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/30'
              : 'bg-white/[0.06] border border-white/[0.08] text-white/70 hover:bg-white/[0.1] hover:text-white'
            }`}
          data-testid={`plan-select-${plan.id}`}
        >
          {isDowngrade ? 'Downgrade' : 'Upgrade'}
          <ArrowRight className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  );
}

export default function BillingPage() {
  const { data: sub, isLoading: subLoading } = useSubscription();
  const { data: plansData, isLoading: plansLoading } = usePlans();
  const startTrial = useStartTrial();
  const { toast } = useToast();
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null);

  const plans = plansData?.plans || [];
  const isLoading = subLoading || plansLoading;

  const handleSelectPlan = (planId: string) => {
    setSelectedPlan(planId);
    toast({
      title: 'Stripe not connected yet',
      description: 'Payment processing will be available soon. You can start a free trial in the meantime.',
    });
  };

  const handleStartTrial = () => {
    startTrial.mutate(undefined, {
      onSuccess: (data) => {
        toast({ title: data.message || 'Trial started!' });
      },
      onError: (err: Error) => {
        toast({ title: 'Could not start trial', description: err.message, variant: 'destructive' });
      },
    });
  };

  if (isLoading) {
    return (
      <div className="p-6 max-w-5xl mx-auto space-y-8">
        <Skeleton className="h-10 w-64" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-96 rounded-xl" />)}
        </div>
      </div>
    );
  }

  const effectivePlan = sub?.is_active ? (sub?.effective_plan || sub?.plan || 'free') : 'free';
  const showTrialCta = !sub?.is_active || sub?.status === 'none';

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-8" data-testid="page-billing">
      <div className="space-y-1">
        <h1 className="text-xl font-semibold tracking-tight text-white/90">Plans & Billing</h1>
        <p className="text-sm text-white/40">Choose the plan that fits your stage</p>
      </div>

      {sub?.is_trial && sub.trial_days_remaining > 0 && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-xl
          bg-emerald-500/[0.06] border border-emerald-500/20"
          data-testid="trial-status"
        >
          <Clock className="h-4 w-4 text-emerald-400 shrink-0" />
          <div className="flex-1">
            <p className="text-sm font-medium text-emerald-400">
              Free trial — {sub.trial_days_remaining} days remaining
            </p>
            <p className="text-xs text-white/40">
              All Scale features are unlocked. Add a payment method to keep access after your trial ends.
            </p>
          </div>
        </div>
      )}

      {sub && !sub.is_active && sub.status !== 'none' && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-xl
          bg-amber-500/[0.06] border border-amber-500/20"
          data-testid="trial-expired"
        >
          <AlertCircle className="h-4 w-4 text-amber-400 shrink-0" />
          <div className="flex-1">
            <p className="text-sm font-medium text-amber-400">
              Your trial has ended
            </p>
            <p className="text-xs text-white/40">
              Upgrade to a paid plan to regain access to premium features.
            </p>
          </div>
        </div>
      )}

      {showTrialCta && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-xl
          bg-white/[0.02] border border-white/[0.06]"
          data-testid="trial-cta"
        >
          <Sparkles className="h-4 w-4 text-emerald-400 shrink-0" />
          <div className="flex-1">
            <p className="text-sm font-medium text-white/80">
              Try all features free for 30 days
            </p>
            <p className="text-xs text-white/40">
              No credit card required. Full access to every feature on the Scale plan.
            </p>
          </div>
          <button
            onClick={handleStartTrial}
            disabled={startTrial.isPending}
            className="px-4 py-2 rounded-lg bg-emerald-500/20 border border-emerald-500/30
              text-emerald-400 text-sm font-medium hover:bg-emerald-500/30 transition-all
              disabled:opacity-50"
            data-testid="button-start-trial"
          >
            {startTrial.isPending ? 'Starting...' : 'Start free trial'}
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {plans.map(plan => (
          <PlanCard
            key={plan.id}
            plan={plan}
            currentPlan={effectivePlan}
            isActive={sub?.is_active || false}
            isTrial={sub?.is_trial || false}
            onSelect={handleSelectPlan}
            popular={plan.id === 'growth'}
          />
        ))}
      </div>

      <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-5 space-y-3">
        <div className="flex items-center gap-2">
          <CreditCard className="h-4 w-4 text-white/40" />
          <h3 className="text-sm font-medium text-white/70">Payment</h3>
        </div>
        <p className="text-xs text-white/40">
          Stripe integration coming soon. When connected, you'll be able to manage your payment
          method, view invoices, and switch plans seamlessly. During the beta, start a free trial
          to access all features.
        </p>
      </div>

      {sub?.is_active && effectivePlan !== 'free' && (
        <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-5 space-y-3"
          data-testid="current-plan-details"
        >
          <h3 className="text-sm font-medium text-white/70">Current Plan Details</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
            <div>
              <p className="text-white/30 mb-1">Plan</p>
              <p className="text-white/70 font-medium">{sub.plan_name}</p>
            </div>
            <div>
              <p className="text-white/30 mb-1">Status</p>
              <p className={`font-medium ${sub.is_trial ? 'text-emerald-400' : 'text-white/70'}`}>
                {sub.is_trial ? 'Trial' : sub.status}
              </p>
            </div>
            <div>
              <p className="text-white/30 mb-1">Price</p>
              <p className="text-white/70 font-medium">
                {sub.plan_price > 0 ? `$${sub.plan_price}/mo` : 'Free'}
              </p>
            </div>
            {sub.trial_end && (
              <div>
                <p className="text-white/30 mb-1">{sub.is_trial ? 'Trial ends' : 'Next billing'}</p>
                <p className="text-white/70 font-medium">
                  {new Date(sub.trial_end).toLocaleDateString()}
                </p>
              </div>
            )}
          </div>
          {sub.plan_highlights && (
            <div className="pt-2 border-t border-white/[0.04]">
              <p className="text-white/30 text-[11px] mb-2">Included features</p>
              <div className="flex flex-wrap gap-1.5">
                {sub.plan_highlights.map((h, i) => (
                  <span key={i} className="px-2 py-0.5 rounded-md bg-white/[0.04] text-white/50 text-[11px]">
                    {h}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
