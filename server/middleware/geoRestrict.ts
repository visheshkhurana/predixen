// Country restriction for public page requests.
//
// Deliberately fail-open at every step: an unknown IP, a failed lookup, or a
// thrown error all ALLOW the request. A geo gate that fails closed turns a
// GeoIP hiccup into a total outage, and the cost of letting a bot through is
// far lower than the cost of turning away a real founder.
//
// Env:
//   GEO_RESTRICTION_ENABLED=false  kill switch — disables the gate entirely
//   GEO_ALLOWED_COUNTRIES=US,IN,GB extra/override allowlist (ISO-3166 alpha-2)
import type { Request, Response, NextFunction } from "express";
import crypto from "crypto";

const DEFAULT_ALLOWED = ["US", "IN"];

function allowedCountries(): Set<string> {
  const raw = process.env.GEO_ALLOWED_COUNTRIES;
  const list = raw
    ? raw.split(",").map((c) => c.trim().toUpperCase()).filter(Boolean)
    : DEFAULT_ALLOWED;
  return new Set(list.length ? list : DEFAULT_ALLOWED);
}

// Paths that must never be geo-gated.
//   /api/          - authenticated app traffic and webhooks (Stripe, Twilio,
//                    QuickBooks) originate from provider IPs in arbitrary
//                    countries; gating them breaks billing and integrations.
//   /embed/        - the survival widget is meant to run on third-party sites
//                    anywhere. Gating it silently breaks other people's pages.
//   health/probe   - Railway's checks come from internal addresses.
//   robots/sitemap - must stay reachable for crawlers regardless of resolution.
const EXEMPT_PREFIXES = ["/api/", "/embed/", "/healthz", "/health", "/assets/"];
const EXEMPT_EXACT = new Set(["/robots.txt", "/sitemap.xml", "/favicon.ico", "/og-image.png"]);

// Search, ad and AI crawlers — never geo-blocked.
//
// This list is generous on purpose. Getting it wrong in the strict direction
// has already cost real money once: the first version matched "googlebot" but
// not "adsbot-google", so Google's ad landing-page crawler hit a 403 from a
// non-allowed country and disapproved every ad in the account with
// "Destination not working". Ad delivery stopped for two days.
//
// The asymmetry is the whole point. Letting a crawler through costs nothing —
// they are not the traffic this gate exists to stop. Blocking one silently
// breaks ads, search indexing or link previews, and the symptom shows up days
// later somewhere else entirely.
const CRAWLER_UA =
  new RegExp(
    [
      // Google — search, ads, and infrastructure. AdsBot verifies ad landing
      // pages; Mediapartners serves AdSense; the rest verify or fetch.
      "googlebot", "adsbot-google", "mediapartners-google", "google-inspectiontool",
      "google-extended", "google-site-verification", "apis-google", "feedfetcher-google",
      "storebot-google", "google-safety", "google-read-aloud", "googleother",
      // Bing, including its ads crawler
      "bingbot", "adidxbot", "bingpreview",
      // Other search
      "slurp", "duckduckbot", "baiduspider", "yandex", "applebot", "seznambot", "naver",
      // Social / link unfurling
      "facebookexternalhit", "facebookcatalog", "twitterbot", "linkedinbot", "slackbot",
      "discordbot", "telegrambot", "whatsapp", "embedly", "quora link preview",
      "redditbot", "pinterest", "tiktok",
      // AI crawlers robots.txt explicitly invites
      "gptbot", "chatgpt-user", "oai-searchbot", "claudebot", "claude-web", "anthropic-ai",
      "perplexitybot", "ccbot", "cohere-ai", "diffbot",
      // SEO tooling the team may run
      "ahrefsbot", "semrushbot", "screaming frog", "mj12bot", "dotbot",
      // Misc
      "bytespider", "petalbot", "uptimerobot", "pingdom", "statuscake",
    ].join("|"),
    "i",
  );

/**
 * Generic non-browser heuristic, applied after the explicit list above.
 *
 * A backstop for the crawler we have not thought of yet. Given the gate fails
 * open everywhere else, letting an unrecognised bot through is consistent and
 * costs nothing; blocking one is what breaks things quietly.
 */
const GENERIC_BOT_UA =
  /(bot\b|\bbot|crawler|spider|crawl|fetcher|scraper|monitor|preview|validator|feedparser|headlesschrome|python-requests|curl\/|wget\/|axios\/|go-http-client|okhttp|java\/|libwww|undici|node-fetch|^node$)/i;

/**
 * Private, loopback, link-local and carrier-grade-NAT ranges.
 *
 * This guard is load-bearing, not defensive padding: fast-geoip does not
 * special-case reserved space and returns real-looking answers for it —
 * 127.0.0.1 resolves to "JP" and 192.168.1.1 to "IT". Without this check the
 * gate would block localhost and Railway's internal health checks.
 */
function isPrivateAddress(ip: string): boolean {
  if (!ip) return true;
  const v = ip.toLowerCase();
  if (v === "::1" || v === "::" || v === "0.0.0.0" || v === "localhost") return true;
  if (v.startsWith("fc") || v.startsWith("fd") || v.startsWith("fe80:")) return true;

  const parts = v.split(".");
  if (parts.length !== 4) return false;
  const [a, b] = parts.map((n) => Number.parseInt(n, 10));
  if (!Number.isFinite(a) || !Number.isFinite(b)) return true;
  if (a === 10 || a === 127 || a === 0) return true;
  if (a === 172 && b >= 16 && b <= 31) return true;
  if (a === 192 && b === 168) return true;
  if (a === 169 && b === 254) return true;
  if (a === 100 && b >= 64 && b <= 127) return true; // CGNAT
  return false;
}

/** Left-most public address in X-Forwarded-For, else the socket address. */
export function clientIp(req: Request): string {
  const xff = req.headers["x-forwarded-for"];
  const chain =
    typeof xff === "string" ? xff.split(",") : Array.isArray(xff) ? xff : [];
  for (const hop of chain) {
    const ip = hop.trim().replace(/^\[|\]$/g, "").replace(/^::ffff:/, "");
    if (ip && !isPrivateAddress(ip)) return ip;
  }
  const direct = (req.socket?.remoteAddress || "").replace(/^::ffff:/, "");
  return direct;
}

function hasSessionCookie(req: Request): boolean {
  // Presence check only — the real verification lives in requireAuth. An
  // existing customer travelling abroad should reach the app; a forged cookie
  // buys nothing beyond the marketing pages, which are public anyway.
  const cookie = req.headers["cookie"];
  if (typeof cookie !== "string") return false;
  return /(?:^|;)\s*auth_token=/.test(cookie);
}

function blockedPage(country: string): string {
  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<title>Not available in your region — FounderConsole</title>
<style>
 body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
      background:#0b0d12;color:#e6e8ee;font:16px/1.6 system-ui,-apple-system,Segoe UI,sans-serif}
 main{max-width:32rem;padding:2rem;text-align:center}
 h1{font-size:1.35rem;margin:0 0 .75rem}
 p{color:#9aa3b2;margin:0 0 1rem}
 a{color:#7aa2ff}
</style></head><body><main>
<h1>FounderConsole isn't available in your region yet</h1>
<p>We currently serve founders in the United States and India. If you think you're
seeing this by mistake, or you'd like access from ${country === "??" ? "your country" : country}, email
<a href="mailto:hello@founderconsole.ai">hello@founderconsole.ai</a> and we'll sort it out.</p>
</main></body></html>`;
}

export function geoRestrict() {
  // Loaded lazily so a missing/corrupt dataset degrades to "allow everything"
  // rather than crashing the server at boot.
  let lookup: ((ip: string) => Promise<{ country?: string } | null>) | null = null;
  let loadFailed = false;

  async function getLookup() {
    if (lookup || loadFailed) return lookup;
    try {
      const mod: any = await import("fast-geoip");
      lookup = (mod.default ?? mod).lookup;
    } catch (err) {
      loadFailed = true;
      console.error("[geo] fast-geoip unavailable, allowing all traffic:", err);
    }
    return lookup;
  }

  return async function geoRestrictMiddleware(req: Request, res: Response, next: NextFunction) {
    try {
      if (process.env.GEO_RESTRICTION_ENABLED === "false") return next();

      const path = req.path || "";
      if (EXEMPT_EXACT.has(path)) return next();
      if (EXEMPT_PREFIXES.some((p) => path.startsWith(p))) return next();

      const ua = String(req.headers["user-agent"] || "");
      if (!ua) return next(); // no UA at all → treat as a tool, not a visitor
      if (CRAWLER_UA.test(ua)) return next();
      if (GENERIC_BOT_UA.test(ua)) return next();

      if (hasSessionCookie(req)) return next();

      const ip = clientIp(req);
      if (!ip || isPrivateAddress(ip)) return next();

      const fn = await getLookup();
      if (!fn) return next();

      const geo = await fn(ip);
      const country = (geo?.country || "").toUpperCase();
      if (!country) return next(); // unknown → allow

      if (allowedCountries().has(country)) return next();

      res
        .status(403)
        .setHeader("X-Robots-Tag", "noindex")
        .setHeader("Cache-Control", "no-store")
        .type("html")
        .send(blockedPage(country || "??"));
    } catch (err) {
      console.error("[geo] check failed, allowing request:", err);
      next();
    }
  };
}
