// Cookie / tracking consent. One source of truth for the banner and every tag.
//
// Until the visitor accepts:
//   - GA4 runs in Google Consent Mode with storage denied (set in index.html);
//   - Meta and X pixels are not loaded at all;
//   - PostHog keeps its id in memory only (no cookie, no localStorage) and does
//     not record sessions.
// "Declined" keeps that state. "Accepted" upgrades each tag in place, so the
// visit that accepts is counted without a reload.

export type ConsentChoice = "accepted" | "declined";

const STORAGE_KEY = "cookie-consent";
const CHANGE_EVENT = "fc:consent-change";

export function readConsent(): ConsentChoice | null {
  try {
    const value = window.localStorage.getItem(STORAGE_KEY);
    return value === "accepted" || value === "declined" ? value : null;
  } catch {
    return null;
  }
}

export function hasTrackingConsent(): boolean {
  return typeof window !== "undefined" && readConsent() === "accepted";
}

function applyGoogleConsent(granted: boolean) {
  const gtag = (window as any).gtag;
  if (typeof gtag !== "function") return;
  const state = granted ? "granted" : "denied";
  gtag("consent", "update", {
    analytics_storage: state,
    ad_storage: state,
    ad_user_data: state,
    ad_personalization: state,
  });
}

export function saveConsent(choice: ConsentChoice) {
  try {
    window.localStorage.setItem(STORAGE_KEY, choice);
  } catch {
    // Private mode: the choice still applies to this visit.
  }
  applyGoogleConsent(choice === "accepted");
  window.dispatchEvent(new CustomEvent<ConsentChoice>(CHANGE_EVENT, { detail: choice }));
}

export function onConsentChange(listener: (choice: ConsentChoice) => void): () => void {
  const handler = (event: Event) => listener((event as CustomEvent<ConsentChoice>).detail);
  window.addEventListener(CHANGE_EVENT, handler);
  return () => window.removeEventListener(CHANGE_EVENT, handler);
}
