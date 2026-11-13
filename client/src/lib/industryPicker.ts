/**
 * When the "What kind of business do you run?" picker may open, and how the
 * visitor's choice is remembered.
 *
 * Pure functions plus two storage helpers, with no "@/" imports, so
 * `server/tests/industry-homepage.test.ts` can import and run them under tsx.
 *
 * The rule, in one place:
 *   - Only on the bare homepage (`/`). Deep links (`/pricing`, `/for/saas`, a
 *     `#section` anchor, a `?industry=` link) never open it.
 *   - Never for crawlers, link unfurlers or headless browsers: the user agent
 *     is checked against `BOT_UA`. The SSR body never contains the picker in
 *     the first place; this keeps a JS-executing crawler from seeing it too.
 *   - Never once the visitor has chosen (an industry or "show me everything"),
 *     or dismissed it earlier in the same tab session.
 */
import { INDUSTRY_SKIPPED, INDUSTRY_STORAGE_KEY, getIndustryPage } from "../data/industry-pages";

/**
 * Crawler / unfurler / headless detection for the client.
 *
 * Mirrors the generic heuristic in server/middleware/botUserAgent.ts (which
 * the client bundle cannot import) and adds the named AI and social crawlers
 * whose user agents do not contain "bot" as a word on its own boundary.
 * A false positive only means someone does not see the picker and gets the
 * full general homepage, which is the safe direction.
 */
export const BOT_UA =
  /(bot\b|\bbot|crawler|spider|crawl|fetcher|scraper|monitor|preview|validator|feedparser|headlesschrome|python-requests|curl\/|wget\/|axios\/|go-http-client|okhttp|java\/|libwww|undici|node-fetch|^node$|gptbot|chatgpt|oai-searchbot|claudebot|claude-web|anthropic-ai|perplexity|google-extended|googleother|bingpreview|facebookexternalhit|slurp|duckduckgo|baiduspider|yandex|bytespider|ccbot|lighthouse|pagespeed|prerender)/i;

export function isBotUserAgent(ua: string | null | undefined): boolean {
  if (!ua) return true; // no UA at all is not a browser
  return BOT_UA.test(ua);
}

export type IndustrySource = "modal" | "pill" | "url";

export interface PickerContext {
  userAgent: string | null | undefined;
  pathname: string;
  search: string;
  hash: string;
  /** What `readStoredIndustry()` returned. */
  stored: string | null;
  /** The visitor closed the picker earlier in this tab session. */
  dismissedThisSession: boolean;
}

/** `?industry=` value from a query string, or null. */
export function industryParam(search: string): string | null {
  try {
    const value = new URLSearchParams(search).get("industry");
    return value ? value.trim().toLowerCase() : null;
  } catch {
    return null;
  }
}

export function shouldShowIndustryPicker(ctx: PickerContext): boolean {
  const path = ctx.pathname.replace(/\/+$/, "") || "/";
  if (path !== "/") return false;
  if (ctx.hash && ctx.hash !== "#") return false;
  if (industryParam(ctx.search) !== null) return false;
  if (isBotUserAgent(ctx.userAgent)) return false;
  if (ctx.stored) return false;
  if (ctx.dismissedThisSession) return false;
  return true;
}

const SESSION_DISMISSED_KEY = "fc_industry_picker_dismissed";

/** A known industry slug, "all" (skipped) or null. Never throws. */
export function readStoredIndustry(): string | null {
  try {
    const value = window.localStorage.getItem(INDUSTRY_STORAGE_KEY);
    if (!value) return null;
    if (value === INDUSTRY_SKIPPED) return value;
    return getIndustryPage(value) ? value : null;
  } catch {
    return null;
  }
}

/** Remember an industry slug or "all". Unknown slugs are ignored. Never throws. */
export function storeIndustry(value: string): void {
  if (value !== INDUSTRY_SKIPPED && !getIndustryPage(value)) return;
  try {
    window.localStorage.setItem(INDUSTRY_STORAGE_KEY, value);
  } catch {
    // private mode / blocked storage: the choice just is not remembered
  }
}

export function readDismissedThisSession(): boolean {
  try {
    return window.sessionStorage.getItem(SESSION_DISMISSED_KEY) === "1";
  } catch {
    return false;
  }
}

export function markDismissedThisSession(): void {
  try {
    window.sessionStorage.setItem(SESSION_DISMISSED_KEY, "1");
  } catch {
    // ignore
  }
}

/**
 * Analytics consent as recorded by CookieConsent.tsx. Only an explicit
 * "declined" suppresses the event; that banner is the only consent signal on
 * this branch.
 */
export function analyticsDeclined(): boolean {
  try {
    return window.localStorage.getItem("cookie-consent") === "declined";
  } catch {
    return false;
  }
}

/**
 * The industry the onboarding "Industry" select should start on, if any:
 * a `?industry=` param wins, then the stored choice. Returns the onboarding
 * select's value (e.g. "general_saas"), or "" when nothing maps.
 */
export function onboardingIndustryPrefill(search: string, stored: string | null): string {
  const slug = industryParam(search) ?? stored;
  return getIndustryPage(slug)?.onboardingIndustry ?? "";
}
