import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

export interface SubscriptionData {
  plan: string;
  effective_plan: string;
  status: string;
  is_trial: boolean;
  trial_days_remaining: number;
  trial_end: string | null;
  is_active: boolean;
  has_payment_method: boolean;
  current_period_end: string | null;
  plan_name: string;
  plan_price: number;
  plan_highlights: string[];
  trial_duration_days: number;
  grandfathered?: boolean;
  payments_enabled?: boolean;
  free_mode?: boolean;
  legacy_paid_subscription?: boolean;
}

export interface PlanData {
  id: string;
  name: string;
  price_monthly: number;
  price_annual: number;
  tagline: string;
  max_companies: number;
  max_simulations_per_month: number;
  max_copilot_messages_per_month: number;
  max_connectors: number;
  highlights: string[];
  features: string[];
}

export function useSubscription() {
  return useQuery<SubscriptionData>({
    queryKey: ['/api/billing/subscription'],
    retry: false,
    staleTime: 60_000,
  });
}

export function usePlans() {
  return useQuery<{ plans: PlanData[] }>({
    queryKey: ['/api/billing/plans'],
    staleTime: 300_000,
  });
}

// FounderConsole is free: there is no trial to start and no plan to buy, so the
// start-trial / subscribe hooks are gone (the endpoints return 410). The
// billing portal hook stays for subscriptions bought before the switch.

export function useBillingPortal() {
  return useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/billing/portal', {
        method: 'POST',
        credentials: 'include',
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Could not open billing portal' }));
        throw new Error(typeof err.detail === 'string' ? err.detail : 'Could not open billing portal');
      }
      return res.json() as Promise<{ portal_url: string }>;
    },
  });
}

export function useFeatureAccess(_feature: string) {
  // Every user has every feature.
  return { hasAccess: true, isLoading: false };
}
