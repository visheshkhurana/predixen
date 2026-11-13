// Per-user fixed window for Express routes that call a paid LLM.
// Must run after requireAuth, which sets req.authUser from the session JWT.
import type { Request, Response, NextFunction } from "express";

export interface AiRateLimitOptions {
  /** Requests allowed per user per window. Defaults to AI_RATE_LIMIT_PER_USER or 20. */
  limit?: number;
  /** Window length in milliseconds. Default 60s. */
  windowMs?: number;
  now?: () => number;
}

interface Bucket {
  count: number;
  resetAt: number;
}

function defaultLimit(): number {
  const raw = process.env.AI_RATE_LIMIT_PER_USER;
  const parsed = raw ? Number(raw) : 20;
  if (!Number.isFinite(parsed) || parsed < 1) return 20;
  return Math.floor(parsed);
}

export function aiUserRateLimit(options: AiRateLimitOptions = {}) {
  const limit = options.limit ?? defaultLimit();
  const windowMs = options.windowMs ?? 60_000;
  const now = options.now ?? (() => Date.now());
  const buckets = new Map<string, Bucket>();

  return function aiUserRateLimitMiddleware(req: Request, res: Response, next: NextFunction): void {
    const sub = (req as Request & { authUser?: { sub?: unknown } }).authUser?.sub;
    if (sub === undefined || sub === null || sub === "") {
      res.status(401).json({ error: "Authentication required" });
      return;
    }

    const key = String(sub);
    const t = now();
    if (buckets.size > 1000) {
      const expired: string[] = [];
      buckets.forEach((bucket, id) => {
        if (t >= bucket.resetAt) expired.push(id);
      });
      for (let i = 0; i < expired.length; i++) buckets.delete(expired[i]);
    }

    let bucket = buckets.get(key);
    if (!bucket || t >= bucket.resetAt) {
      bucket = { count: 0, resetAt: t + windowMs };
      buckets.set(key, bucket);
    }

    if (bucket.count >= limit) {
      const retryAfter = Math.max(1, Math.ceil((bucket.resetAt - t) / 1000));
      res.setHeader("Retry-After", String(retryAfter));
      res.status(429).json({
        error: "Too many AI requests. Try again shortly.",
        retryAfter,
      });
      return;
    }

    bucket.count += 1;
    res.setHeader("X-RateLimit-Limit", String(limit));
    res.setHeader("X-RateLimit-Remaining", String(Math.max(0, limit - bucket.count)));
    next();
  };
}
