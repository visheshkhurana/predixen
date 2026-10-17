// Cross-site request defence for cookie-authenticated writes.
//
// The session lives in the `auth_token` cookie, which the browser attaches on
// its own. For a state-changing request that is authenticated ONLY by that
// cookie, require the Origin (or, failing that, the Referer) to be this app.
// Browsers always send Origin on non-GET fetches, and the client calls the API
// with same-origin relative URLs, so legitimate requests are unaffected.
//
// Not checked: safe methods, Bearer-token requests (not ambient), requests
// with no session cookie, and server-to-server webhook receivers — each of
// those verifies its own signature or shared secret.
import type { Request, Response, NextFunction } from "express";
import { getAuthCookie } from "./requireAuth";

const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

/** Webhook / server-to-server receivers, as Express sees the path. */
export const ORIGIN_CHECK_EXEMPT_PREFIXES = [
  "/api/billing/webhook", // Stripe (signature-verified)
  "/api/slack/", // Slack commands/events/interactions (signing secret)
  "/api/notifications/resend-webhook", // Resend (Svix signature)
  "/notifications/resend-webhook",
  "/api/email-tracking/webhooks/", // Resend email events (Svix signature)
  "/email-tracking/webhooks/",
  "/webhooks/", // lead-gen HMAC receivers and connector ingest webhooks
  "/api/webhooks/",
  "/internal/", // FastAPI -> Express broadcasts (shared secret)
];

function originOf(value: string | undefined): string | null {
  if (!value) return null;
  try {
    const u = new URL(value);
    return `${u.protocol}//${u.host}`.toLowerCase();
  } catch {
    return null;
  }
}

export function allowedOrigins(req: Request): Set<string> {
  const out = new Set<string>();
  const add = (v: string | undefined) => {
    const o = originOf(v?.trim());
    if (o) out.add(o);
  };
  for (const o of (process.env.CORS_ORIGINS || "").split(",")) add(o);
  add(process.env.APP_BASE_URL || "https://founderconsole.ai");
  // The host the browser actually addressed (behind Railway, req.protocol
  // reflects X-Forwarded-Proto because trust proxy is on). A cross-site page
  // cannot choose this value for the victim's request.
  const host = req.headers.host;
  if (host) add(`${req.protocol}://${host}`);
  return out;
}

export function originCheck() {
  return function originCheckMiddleware(req: Request, res: Response, next: NextFunction) {
    if (!UNSAFE_METHODS.has(req.method)) return next();
    const path = req.path || "";
    if (ORIGIN_CHECK_EXEMPT_PREFIXES.some((p) => path.startsWith(p))) return next();

    const authz = req.headers["authorization"];
    if (typeof authz === "string" && /^Bearer\s+\S/i.test(authz)) return next();
    if (!getAuthCookie(req.headers["cookie"])) return next();

    const origin = req.headers["origin"];
    const source =
      typeof origin === "string" && origin !== "null"
        ? originOf(origin)
        : originOf(typeof req.headers["referer"] === "string" ? req.headers["referer"] : undefined);

    if (source && allowedOrigins(req).has(source)) return next();

    res.status(403).json({ detail: "Cross-site request rejected" });
  };
}
