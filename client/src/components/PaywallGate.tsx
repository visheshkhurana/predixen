// Paywall is currently DISABLED — every user has access to every feature.
// To re-enable, restore the original gating logic from git history (commit 60e89bef).

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

interface PaywallGateProps {
  feature: string;
  children: React.ReactNode;
  fallback?: React.ReactNode;
  inline?: boolean;
}

export function PaywallGate({ children }: PaywallGateProps) {
  return <>{children}</>;
}

export function TrialBanner() {
  return null;
}

export function useHasFeature(_feature: string): { hasAccess: boolean; isLoading: boolean } {
  return { hasAccess: true, isLoading: false };
}

export function UpgradeButton({ feature }: { feature: string }) {
  const [, navigate] = useLocation();
  const featureInfo = FEATURE_PLAN_MAP[feature];
  if (!featureInfo) return null;
  return (
    <button
      onClick={() => navigate('/billing')}
      className="inline-flex items-center gap-2 px-4 py-2 rounded-lg
        bg-white/[0.08] border border-white/[0.1] text-white/80
        hover:bg-white/[0.12] hover:text-white transition-all text-sm font-medium"
      data-testid={`paywall-upgrade-${feature}`}
    >
      <Sparkles className="h-4 w-4" />
      <span>Upgrade to {featureInfo.minPlanName}</span>
      <ArrowRight className="h-3.5 w-3.5" />
      <Lock className="h-3.5 w-3.5 sr-only" />
    </button>
  );
}
