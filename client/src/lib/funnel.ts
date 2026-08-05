import { trackEvent as posthogTrack } from './posthog';

/**
 * Fire a marketing-funnel step to GA4 (gtag) and PostHog.
 * Funnel: page_view → cta_click → signup_view → signup_start → sign_up
 *         → onboarding_complete → purchase_subscription
 * Safe no-op when gtag isn't loaded (e.g. ad-blockers, SSR).
 */
export function trackFunnel(name: string, params: Record<string, unknown> = {}) {
  if (typeof window !== 'undefined' && (window as any).gtag) {
    (window as any).gtag('event', name, params);
  }
  posthogTrack(name, params as Record<string, any>);
}
