import { useSubscription } from '@/hooks/use-subscription';
import { Lock, Sparkles, ArrowRight } from 'lucide-react';
import { useLocation } from 'wouter';

const FEATURE_PLAN_MAP: Record<string, { label: string; minPlan: string; minPlanName: string }> = {
  simulations: { label: 'Monte Carlo Simulations', minPlan: 'starter', minPlanName: 'Starter' },
  copilot: { label: 'AI Copilot', minPlan: 'starter', minPlanName: 'Starter' },
  truth_scan: { label: 'Truth Scan', minPlan: 'starter', minPlanName: 'Starter' },
  stress_tests: { label: 'Stress Tests', minPlan: 'starter', minPlanName: 'Starter' },
  what_if: { label: 'What-If Analysis', minPlan: 'starter', minPlanName: 'Starter' },
  sensitivity_analysis: { label: 'Sensitivity Analysis', minPlan: 'starter', minPlanName: 'Starter' },
  benchmarks: { label: 'Industry Benchmarks', minPlan: 'starter', minPlanName: 'Starter' },
  data_connectors: { label: 'Data Connectors', minPlan: 'growth', minPlanName: 'Growth' },
  fundraising_os: { label: 'Fundraising OS', minPlan: 'growth', minPlanName: 'Growth' },
  cap_table: { label: 'Cap Table', minPlan: 'growth', minPlanName: 'Growth' },
  board_deck: { label: 'Board Deck Export', minPlan: 'growth', minPlanName: 'Growth' },
  email_reports: { label: 'Email Reports', minPlan: 'growth', minPlanName: 'Growth' },
  fundraising_readiness: { label: 'Fundraising Readiness', minPlan: 'growth', minPlanName: 'Growth' },
  hiring_planner: { label: 'Hiring Planner', minPlan: 'scale', minPlanName: 'Scale' },
  flight_simulator: { label: 'Flight Simulator', minPlan: 'scale', minPlanName: 'Scale' },
  document_generator: { label: 'Document Generator', minPlan: 'scale', minPlanName: 'Scale' },
  ai_graphics: { label: 'AI Graphics Studio', minPlan: 'scale', minPlanName: 'Scale' },
  digital_twin: { label: 'Digital Twin', minPlan: 'scale', minPlanName: 'Scale' },
  cross_company_learning: { label: 'Cross-Company Intelligence', minPlan: 'scale', minPlanName: 'Scale' },
  investor_room: { label: 'Investor Room', minPlan: 'scale', minPlanName: 'Scale' },
};

const PLAN_HIERARCHY = ['free', 'starter', 'growth', 'scale'];

function planRank(plan: string): number {
  const idx = PLAN_HIERARCHY.indexOf(plan);
  return idx >= 0 ? idx : 0;
}

interface PaywallGateProps {
  feature: string;
  children: React.ReactNode;
  fallback?: React.ReactNode;
  inline?: boolean;
}

export function PaywallGate({ feature, children, fallback, inline = false }: PaywallGateProps) {
  const { data: sub, isLoading } = useSubscription();
  const [, navigate] = useLocation();

  if (isLoading) {
    if (inline) return null;
    return <div className="p-6"><div className="h-32 rounded-xl bg-white/[0.02] animate-pulse" /></div>;
  }

  const featureInfo = FEATURE_PLAN_MAP[feature];
  if (!featureInfo) return <>{children}</>;

  const effectivePlan = sub?.is_active ? (sub?.effective_plan || sub?.plan || 'free') : 'free';
  const userRank = planRank(effectivePlan);
  const requiredRank = planRank(featureInfo.minPlan);

  if (userRank >= requiredRank) return <>{children}</>;

  if (fallback) return <>{fallback}</>;

  if (inline) {
    return (
      <button
        onClick={() => navigate('/billing')}
        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md
          bg-white/[0.04] border border-white/[0.08] text-white/40
          hover:bg-white/[0.06] hover:text-white/60 transition-all text-xs"
        data-testid={`paywall-inline-${feature}`}
      >
        <Lock className="h-3 w-3" />
        <span>{featureInfo.minPlanName} plan</span>
      </button>
    );
  }

  return (
    <div
      className="relative rounded-xl border border-white/[0.06] bg-white/[0.02] p-6 text-center"
      data-testid={`paywall-gate-${feature}`}
    >
      <div className="flex flex-col items-center gap-3">
        <div className="h-10 w-10 rounded-full bg-white/[0.06] flex items-center justify-center">
          <Lock className="h-5 w-5 text-white/40" />
        </div>
        <div>
          <p className="text-sm font-medium text-white/70">{featureInfo.label}</p>
          <p className="text-xs text-white/40 mt-1">
            Available on the {featureInfo.minPlanName} plan and above
          </p>
        </div>
        <button
          onClick={() => navigate('/billing')}
          className="mt-2 inline-flex items-center gap-2 px-4 py-2 rounded-lg
            bg-white/[0.08] border border-white/[0.1] text-white/80
            hover:bg-white/[0.12] hover:text-white transition-all text-sm font-medium"
          data-testid={`paywall-upgrade-${feature}`}
        >
          <Sparkles className="h-4 w-4" />
          <span>Upgrade to {featureInfo.minPlanName}</span>
          <ArrowRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}

export function TrialBanner() {
  const { data: sub, isLoading } = useSubscription();
  const [, navigate] = useLocation();

  if (isLoading || !sub) return null;

  if (sub.is_trial && sub.trial_days_remaining > 0) {
    const urgent = sub.trial_days_remaining <= 7;
    return (
      <div
        className={`flex items-center justify-between px-4 py-2 text-xs border-b
          ${urgent
            ? 'bg-amber-500/[0.08] border-amber-500/20 text-amber-400'
            : 'bg-emerald-500/[0.06] border-emerald-500/15 text-emerald-400'
          }`}
        data-testid="banner-trial"
      >
        <div className="flex items-center gap-2">
          <Sparkles className="h-3.5 w-3.5" />
          <span>
            {urgent
              ? `Trial ending in ${sub.trial_days_remaining} day${sub.trial_days_remaining !== 1 ? 's' : ''}`
              : `Free trial — ${sub.trial_days_remaining} days remaining`
            }
          </span>
        </div>
        <button
          onClick={() => navigate('/billing')}
          className="flex items-center gap-1 px-2.5 py-1 rounded-md
            bg-white/[0.08] hover:bg-white/[0.12] text-white/70 hover:text-white transition-all"
          data-testid="button-upgrade-trial"
        >
          <span>View plans</span>
          <ArrowRight className="h-3 w-3" />
        </button>
      </div>
    );
  }

  if (!sub.is_active && sub.status !== 'none') {
    return (
      <div
        className="flex items-center justify-between px-4 py-2 text-xs border-b
          bg-red-500/[0.06] border-red-500/15 text-red-400"
        data-testid="banner-expired"
      >
        <div className="flex items-center gap-2">
          <Lock className="h-3.5 w-3.5" />
          <span>Your trial has ended — upgrade to continue using all features</span>
        </div>
        <button
          onClick={() => navigate('/billing')}
          className="flex items-center gap-1 px-2.5 py-1 rounded-md
            bg-white/[0.08] hover:bg-white/[0.12] text-white/70 hover:text-white transition-all"
          data-testid="button-upgrade-expired"
        >
          <span>Upgrade now</span>
          <ArrowRight className="h-3 w-3" />
        </button>
      </div>
    );
  }

  return null;
}

export function useHasFeature(feature: string): { hasAccess: boolean; isLoading: boolean } {
  const { data: sub, isLoading } = useSubscription();

  if (isLoading || !sub) return { hasAccess: true, isLoading: true };

  const featureInfo = FEATURE_PLAN_MAP[feature];
  if (!featureInfo) return { hasAccess: true, isLoading: false };

  const effectivePlan = sub.is_active ? (sub.effective_plan || sub.plan || 'free') : 'free';
  const userRank = planRank(effectivePlan);
  const requiredRank = planRank(featureInfo.minPlan);

  return { hasAccess: userRank >= requiredRank, isLoading: false };
}
