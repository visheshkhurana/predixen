// Security headers for every Express response (pages, assets and the /api
// proxy). Kept in its own module so the policy can be asserted in a test.
import type { Request, Response, NextFunction } from "express";

/** Same value FastAPI's SecurityHeadersMiddleware sends (two years). */
export const HSTS_VALUE = "max-age=63072000; includeSubDomains; preload";

function isDevelopment(): boolean {
  const env = process.env.NODE_ENV;
  const prod = env === "production" || process.env.ENVIRONMENT === "production";
  return !prod && env !== "test";
}

/**
 * The app's own WebSocket origin(s). 'self' already covers same-origin ws/wss
 * in current browsers; the explicit wss:// entry keeps older engines working.
 */
function ownSocketOrigins(): string[] {
  const out = new Set<string>();
  for (const raw of [process.env.APP_BASE_URL || "https://founderconsole.ai"]) {
    try {
      const u = new URL(raw);
      out.add(`wss://${u.host}`);
    } catch {
      /* ignore malformed */
    }
  }
  return Array.from(out);
}

export function buildCsp(opts: { isEmbed: boolean; dev?: boolean }): string {
  const dev = opts.dev ?? isDevelopment();
  // Vite's dev server needs ws:/wss: for HMR on whatever port it picks.
  const socketSources = dev ? ["ws:", "wss:"] : ownSocketOrigins();
  return [
    "default-src 'self'",
    // us-assets.i.posthog.com serves array.js/recorder.js — the snippet in
    // client/index.html rewrites api_host to it, so omitting it blocks
    // PostHog analytics and session replay entirely.
    // static.ads-twitter.com serves uwt.js (the X Ads pixel). Omitting it means
    // the browser blocks the tag and X reports zero conversions — visually
    // identical to "the ads didn't work", which is the worst kind of bug.
    // 'unsafe-inline' stays for the inline analytics bootstraps in index.html.
    // 'unsafe-eval' is only needed by Vite's dev runtime.
    `script-src 'self' 'unsafe-inline'${dev ? " 'unsafe-eval'" : ""} https://us.posthog.com https://us-assets.i.posthog.com https://www.google-analytics.com https://www.googletagmanager.com https://connect.facebook.net https://static.ads-twitter.com https://analytics.twitter.com`,
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    // X fires its conversion beacons as image/pixel requests to t.co and
    // analytics.twitter.com as well as via fetch.
    "img-src 'self' data: blob: https://us.posthog.com https://www.facebook.com https://t.co https://analytics.twitter.com https://static.ads-twitter.com",
    // GA4 sends /g/collect beacons to analytics.google.com, stats.g.doubleclick.net
    // and www.google.com — not just www.google-analytics.com. Google also routes
    // some traffic through regional endpoints (region1.google-analytics.com /
    // region1.analytics.google.com). Omitting any of them silently drops a
    // share of measurement traffic.
    ["connect-src 'self'", ...socketSources, "https://us.posthog.com https://us.i.posthog.com https://us-assets.i.posthog.com https://www.google-analytics.com https://*.google-analytics.com https://analytics.google.com https://*.analytics.google.com https://stats.g.doubleclick.net https://www.google.com https://accounts.google.com https://oauth.platform.intuit.com https://quickbooks.api.intuit.com https://analytics.twitter.com https://t.co https://static.ads-twitter.com"].join(" "),
    opts.isEmbed ? "frame-ancestors *" : "frame-src https://accounts.google.com",
  ].join("; ");
}

export function securityHeaders() {
  return function securityHeadersMiddleware(req: Request, res: Response, next: NextFunction) {
    const isEmbed = req.path.startsWith("/embed/");
    if (!isEmbed) {
      res.setHeader("X-Frame-Options", "DENY");
    }
    res.setHeader("X-Content-Type-Options", "nosniff");
    res.setHeader("X-XSS-Protection", "0");
    res.setHeader("Referrer-Policy", "strict-origin-when-cross-origin");
    res.setHeader("Permissions-Policy", "camera=(), microphone=(), geolocation=()");
    res.setHeader("Strict-Transport-Security", HSTS_VALUE);
    res.setHeader("Content-Security-Policy", buildCsp({ isEmbed }));
    next();
  };
}
