import { publicEventProperties } from './calculator-analytics';
import { trackEvent as posthogTrack } from './posthog';
import { trackXConversion } from './xads';

/**
 * Fire a marketing-funnel step to GA4 (gtag), PostHog and X Ads.
 * Funnel: page_view → cta_click → signup_view → signup_start → sign_up
 *         → signup_completed → founder_activated → onboarding_complete
 *         → purchase_subscription
 *
 * Every ad platform hangs off this one function on purpose. Sprinkling
 * platform-specific calls through the pages is how a funnel ends up half
 * instrumented — some steps reported to one network and not another, with no
 * way to tell from the outside which. Add networks here, not at call sites.
 *
 * PostHog goes first, in its own try. gtag used to run before it with no
 * guard, so a throw from the Google tag skipped the capture entirely and the
 * caller's catch treated a saved lead as a failed one.
 *
 * publicEventProperties is an allow-list and it runs before any destination.
 * The same filtered object is what PostHog, gtag, and X receive. Calculator
 * result numbers never leave this function.
 *
 * Safe no-op when a destination isn't loaded (ad-blockers, SSR, no pixel id).
 */
export function trackFunnel(name: string, params: Record<string, unknown> = {}) {
  const safe = publicEventProperties(params);
  try {
    posthogTrack(name, safe);
  } catch (err) {
    console.debug('[funnel] PostHog capture failed', name, err);
  }
  try {
    if (typeof window !== 'undefined' && (window as any).gtag) {
      (window as any).gtag('event', name, safe);
    }
  } catch (err) {
    console.debug('[funnel] gtag failed', name, err);
  }
  try {
    trackXConversion(name, safe);
  } catch (err) {
    console.debug('[funnel] x conversion failed', name, err);
  }
}

const FOUNDER_ACTIVATED_KEY = 'fc_founder_activated';

/**
 * Product-bet activation. Client complement to the server first-success
 * emitter. Sample companies must never count — require an explicit
 * is_sample === false so a stale store object without the flag cannot
 * turn a #21 sample first-run into founder_activated.
 */
export function trackFounderActivated(params: {
  source: 'truth_scan' | 'simulation';
  company_id: number;
  is_sample?: boolean;
}) {
  if (params.is_sample !== false) return;
  if (typeof window !== 'undefined') {
    try {
      if (window.localStorage.getItem(FOUNDER_ACTIVATED_KEY)) return;
      window.localStorage.setItem(FOUNDER_ACTIVATED_KEY, '1');
    } catch {
      // private mode / blocked storage: still emit this session
    }
  }
  trackFunnel('founder_activated', {
    source: params.source,
    company_id: params.company_id,
    is_sample: false,
  });
}
