// FounderConsole is free — every user has access to every feature. These
// components are pass-throughs kept so existing call sites compile.

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

// Nothing to upgrade to: FounderConsole is free. Kept as a no-op so any caller
// still compiles.
export function UpgradeButton(_props: { feature: string }) {
  return null;
}
