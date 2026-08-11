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

// Search and AI crawlers. robots.txt explicitly invites GPTBot, ClaudeBot and
// PerplexityBot; geo-blocking them would contradict that and quietly undo the
// SEO/GEO work. Googlebot in particular crawls from shifting IP ranges, and a
// blocked crawl is indistinguishable from a dead site.
const CRAWLER_UA =
  /(googlebot|google-inspectiontool|google-extended|bingbot|slurp|duckduckbot|baiduspider|yandex(bot)?|applebot|facebookexternalhit|twitterbot|linkedinbot|slackbot|discordbot|telegrambot|whatsapp|embedly|quora link preview|redditbot|gptbot|chatgpt-user|oai-searchbot|claudebot|claude-web|anthropic-ai|perplexitybot|ccbot|bytespider|petalbot|ahrefsbot|semrushbot|screaming frog)/i;

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
      if (CRAWLER_UA.test(ua)) return next();

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
