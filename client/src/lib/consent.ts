// Cookie / tracking consent. One source of truth for the banner and every tag.
//
// Until the visitor accepts:
//   - GA4 runs in Google Consent Mode with storage denied (set in index.html);
//   - Meta and X pixels are not loaded at all;
//   - PostHog keeps its id in memory only (no cookie, no localStorage) and does
//     not record sessions.
// "Declined" keeps that state. "Accepted" upgrades each tag in place, so the
// visit that accepts is counted without a reload.
//
// The choice is kept in localStorage AND in a first-party cookie scoped to the
// parent domain. localStorage alone is per-origin, so a choice made on the
// marketing site (www.) was unknown to the app (app.) and the banner came back
// on every visit; it can also be unavailable or wiped (private mode, storage
// clearing). Either copy is enough to never show the banner again.

export type ConsentChoice = "accepted" | "declined";

export const CONSENT_STORAGE_KEY = "cookie-consent";
const STORAGE_KEY = CONSENT_STORAGE_KEY;
const COOKIE_NAME = "fc_cookie_consent";
const COOKIE_MAX_AGE = 60 * 60 * 24 * 365; // one year
const CHANGE_EVENT = "fc:consent-change";

function asChoice(value: string | null | undefined): ConsentChoice | null {
  return value === "accepted" || value === "declined" ? value : null;
}

/** The cookie domain shared by the marketing site and the app (".example.com"), or null for localhost / IPs. */
export function consentCookieDomain(hostname: string): string | null {
  const host = (hostname || "").toLowerCase();
  if (!host || host === "localhost" || /^[\d.]+$/.test(host) || host.includes(":")) return null;
  const parts = host.split(".");
  if (parts.length < 2) return null;
  // Hosting suffixes where the parent domain is shared with other tenants.
  const shared = ["railway.app", "up.railway.app", "vercel.app", "replit.app", "repl.co", "replit.dev"];
  if (shared.some((s) => host === s || host.endsWith(`.${s}`))) return null;
  // example.co.in / example.com.sg: keep three labels, not the public suffix.
  const take = parts.length >= 3 && /^(co|com|net|org|gov|ac|edu)$/.test(parts[parts.length - 2]) ? 3 : 2;
  return `.${parts.slice(-take).join(".")}`;
}

export function parseConsentCookie(cookieHeader: string | null | undefined): ConsentChoice | null {
  if (!cookieHeader) return null;
  for (const part of cookieHeader.split(";")) {
    const [name, ...rest] = part.trim().split("=");
    if (name === COOKIE_NAME) return asChoice(decodeURIComponent(rest.join("=")));
  }
  return null;
}

function readCookie(): ConsentChoice | null {
  try {
    return parseConsentCookie(document.cookie);
  } catch {
    return null;
  }
}

function writeCookie(choice: ConsentChoice) {
  try {
    const domain = consentCookieDomain(window.location.hostname);
    const secure = window.location.protocol === "https:" ? "; Secure" : "";
    document.cookie =
      `${COOKIE_NAME}=${choice}; Max-Age=${COOKIE_MAX_AGE}; Path=/; SameSite=Lax${secure}` +
      (domain ? `; Domain=${domain}` : "");
  } catch {
    // Cookies blocked: localStorage still holds the choice.
  }
}

export function readConsent(): ConsentChoice | null {
  let stored: ConsentChoice | null = null;
  try {
    stored = asChoice(window.localStorage.getItem(STORAGE_KEY));
  } catch {
    stored = null;
  }
  if (stored) return stored;
  const fromCookie = readCookie();
  if (fromCookie) {
    // Copy it back so code that reads localStorage directly agrees.
    try {
      window.localStorage.setItem(STORAGE_KEY, fromCookie);
    } catch {
      // ignore
    }
  }
  return fromCookie;
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
    // Private mode: the cookie (or, failing that, this visit) keeps the choice.
  }
  writeCookie(choice);
  applyGoogleConsent(choice === "accepted");
  window.dispatchEvent(new CustomEvent<ConsentChoice>(CHANGE_EVENT, { detail: choice }));
}

export function onConsentChange(listener: (choice: ConsentChoice) => void): () => void {
  const handler = (event: Event) => listener((event as CustomEvent<ConsentChoice>).detail);
  window.addEventListener(CHANGE_EVENT, handler);
  return () => window.removeEventListener(CHANGE_EVENT, handler);
}
