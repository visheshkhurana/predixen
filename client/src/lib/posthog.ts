import posthog from 'posthog-js';

// PostHog client tokens are public by design (they ship in the JS bundle).
// The default below is the real project token — the VITE_POSTHOG_KEY that was
// previously configured at build time pointed at a nonexistent project, so
// PostHog rejected every event with 401 and no analytics were ever ingested.
const POSTHOG_KEY = 'phc_C3jjovUPQChwDJoJdCp6E7adYRKBYSPETq5bNJw7pt6M';
const POSTHOG_HOST = import.meta.env.VITE_POSTHOG_HOST || 'https://us.i.posthog.com';

let initialized = false;

export function initPostHog() {
  if (initialized || !POSTHOG_KEY) return;
  posthog.init(POSTHOG_KEY, {
    api_host: POSTHOG_HOST,
    // Send over XMLHttpRequest rather than fetch. A number of common browser
    // extensions (privacy blockers, anti-fingerprinting shims) monkey-patch
    // window.fetch and throw inside it, which silently kills every capture on
    // the default fetch transport while XHR sails through.
    api_transport: 'XHR',
    capture_pageview: true,
    capture_pageleave: true,
    // Without this, $exception is never ingested and a JS error on the signup
    // page is completely invisible to us — we would see the drop-off and have
    // no way to tell a broken form from a bored visitor. Cheap insurance on the
    // one funnel step we cannot afford to be blind on.
    capture_exceptions: true,
    persistence: 'localStorage',
    // Session replay: record marketing + auth funnel sessions so we can watch
    // where ad visitors drop off. Inputs are masked by default for privacy.
    disable_session_recording: false,
    session_recording: {
      maskAllInputs: true,
    },
  });
  initialized = true;
}

export function identifyUser(userId: number, email: string, role?: string) {
  if (!POSTHOG_KEY) return;
  posthog.identify(String(userId), { email, role: role || 'viewer' });
}

export function resetUser() {
  if (!POSTHOG_KEY) return;
  posthog.reset();
}

export function trackPageView(path: string) {
  if (!POSTHOG_KEY) return;
  posthog.capture('$pageview', { $current_url: window.location.href, path });
}

export function trackEvent(event: string, properties?: Record<string, any>) {
  if (!POSTHOG_KEY) return;
  posthog.capture(event, properties);
}

export const isPostHogEnabled = () => !!POSTHOG_KEY;
