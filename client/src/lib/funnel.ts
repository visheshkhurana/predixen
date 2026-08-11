import { trackEvent as posthogTrack } from './posthog';
import { trackXConversion } from './xads';

/**
 * Fire a marketing-funnel step to GA4 (gtag), PostHog and X Ads.
 * Funnel: page_view → cta_click → signup_view → signup_start → sign_up
 *         → onboarding_complete → purchase_subscription
 *
 * Every ad platform hangs off this one function on purpose. Sprinkling
 * platform-specific calls through the pages is how a funnel ends up half
 * instrumented — some steps reported to one network and not another, with no
 * way to tell from the outside which. Add networks here, not at call sites.
 *
 * Safe no-op when a destination isn't loaded (ad-blockers, SSR, no pixel id).
 */
export function trackFunnel(name: string, params: Record<string, unknown> = {}) {
  if (typeof window !== 'undefined' && (window as any).gtag) {
    (window as any).gtag('event', name, params);
  }
  posthogTrack(name, params as Record<string, any>);
  trackXConversion(name, params);
}
