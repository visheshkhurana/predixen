import posthog from 'posthog-js';

const POSTHOG_KEY = import.meta.env.VITE_POSTHOG_KEY || '';
const POSTHOG_HOST = import.meta.env.VITE_POSTHOG_HOST || 'https://us.i.posthog.com';

let initialized = false;

export function initPostHog() {
  if (initialized || !POSTHOG_KEY) return;
  posthog.init(POSTHOG_KEY, {
    api_host: POSTHOG_HOST,
    capture_pageview: false,
    capture_pageleave: true,
    persistence: 'localStorage',
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
