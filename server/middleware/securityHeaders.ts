// Security headers for every Express response (pages, assets and the /api
// proxy). Moved out of server/index.ts so the policy can be asserted in a test
// (server/tests/security-headers.test.ts). The directives are unchanged except
// connect-src's socket sources: production no longer allows a WebSocket to
// any host (`ws: wss:`), only this app's own origin.
import type { Request, Response, NextFunction } from "express";

/** Two years. FastAPI's SecurityHeadersMiddleware sends the same value. */
export const HSTS_VALUE = "max-age=63072000; includeSubDomains; preload";

export function isProductionEnv(env: NodeJS.ProcessEnv = process.env): boolean {
  return env.NODE_ENV === "production" || env.ENVIRONMENT === "production";
}

/**
 * The app's own WebSocket origin. 'self' already covers a same-origin ws/wss
 * connection in current browsers (the client opens `${location.host}/ws`); the
 * explicit wss:// entry keeps engines that predate that rule working.
 */
export function ownSocketOrigins(env: NodeJS.ProcessEnv = process.env): string[] {
  try {
    return [`wss://${new URL(env.APP_BASE_URL || "https://founderconsole.ai").host}`];
  } catch {
    return ["wss://founderconsole.ai"];
  }
}

export interface CspOptions {
  isEmbed: boolean;
  /** Razorpay Checkout origins; see server/billing-gate.ts. */
  razorpay: boolean;
  /** Development (Vite HMR) keeps `ws: wss:`. Defaults to !isProductionEnv(). */
  dev?: boolean;
}

export function buildCsp(opts: CspOptions): string {
  const dev = opts.dev ?? !isProductionEnv();
  const rzp = (sources: string) => (opts.razorpay ? ` ${sources}` : "");
  // Vite's dev server needs ws:/wss: for HMR on whatever port it picks.
  const sockets = dev ? "ws: wss:" : ownSocketOrigins().join(" ");
  return [
    "default-src 'self'",
    // us-assets.i.posthog.com serves array.js/recorder.js — the snippet in
    // client/index.html rewrites api_host to it, so omitting it blocks
    // PostHog analytics and session replay entirely.
    // static.ads-twitter.com serves uwt.js (the X Ads pixel). Omitting it means
    // the browser blocks the tag and X reports zero conversions — visually
    // identical to "the ads didn't work", which is the worst kind of bug.
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://us.posthog.com https://us-assets.i.posthog.com https://www.google-analytics.com https://www.googletagmanager.com https://connect.facebook.net https://static.ads-twitter.com https://analytics.twitter.com" + rzp("https://checkout.razorpay.com"),
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    // X fires its conversion beacons as image/pixel requests to t.co and
    // analytics.twitter.com as well as via fetch.
    "img-src 'self' data: blob: https://us.posthog.com https://www.facebook.com https://t.co https://analytics.twitter.com https://static.ads-twitter.com" + rzp("https://cdn.razorpay.com"),
    // GA4 sends /g/collect beacons to analytics.google.com, stats.g.doubleclick.net
    // and www.google.com — not just www.google-analytics.com. Google also routes
    // some traffic through regional endpoints (region1.google-analytics.com /
    // region1.analytics.google.com). Omitting any of them silently drops a
    // share of measurement traffic.
    `connect-src 'self' ${sockets} https://us.posthog.com https://us.i.posthog.com https://us-assets.i.posthog.com https://www.google-analytics.com https://*.google-analytics.com https://analytics.google.com https://*.analytics.google.com https://stats.g.doubleclick.net https://www.google.com https://accounts.google.com https://oauth.platform.intuit.com https://quickbooks.api.intuit.com https://analytics.twitter.com https://t.co https://static.ads-twitter.com` + rzp("https://api.razorpay.com https://lumberjack.razorpay.com"),
    opts.isEmbed ? "frame-ancestors *" : "frame-src https://accounts.google.com" + rzp("https://api.razorpay.com https://checkout.razorpay.com"),
  ].join("; ");
}

export function securityHeaders(opts: { razorpay: boolean; dev?: boolean }) {
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
    res.setHeader("Content-Security-Policy", buildCsp({ isEmbed, razorpay: opts.razorpay, dev: opts.dev }));
    next();
  };
}
