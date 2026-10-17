// Auth gates for Express-handled routes (Twilio messaging, Notion, AI governance).
// Verifies the same HS256 JWT the FastAPI backend issues (signed with SECRET_KEY,
// carried in the `auth_token` cookie or an Authorization: Bearer header).
import crypto from "crypto";
import type { Request, Response, NextFunction } from "express";

function b64urlDecode(s: string): Buffer {
  s = s.replace(/-/g, "+").replace(/_/g, "/");
  while (s.length % 4) s += "=";
  return Buffer.from(s, "base64");
}

export function verifyJwtHS256(token: string, secret: string): Record<string, any> | null {
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  const [h, p, sig] = parts;
  // Only HS256 is accepted; a header naming any other alg (e.g. "none") fails.
  try {
    const header = JSON.parse(b64urlDecode(h).toString("utf8"));
    if (!header || header.alg !== "HS256") return null;
  } catch {
    return null;
  }
  const expected = crypto.createHmac("sha256", secret).update(`${h}.${p}`).digest();
  const given = b64urlDecode(sig);
  if (expected.length !== given.length || !crypto.timingSafeEqual(expected, given)) return null;
  let payload: Record<string, any>;
  try {
    payload = JSON.parse(b64urlDecode(p).toString("utf8"));
  } catch {
    return null;
  }
  if (payload.exp && Math.floor(Date.now() / 1000) > Number(payload.exp)) return null;
  return payload;
}

/** The `auth_token` cookie value from a raw Cookie header, if present. */
export function getAuthCookie(cookie: string | string[] | undefined): string | null {
  if (typeof cookie !== "string") return null;
  for (const part of cookie.split(";")) {
    const idx = part.indexOf("=");
    if (idx === -1) continue;
    const k = part.slice(0, idx).trim();
    if (k === "auth_token") {
      try {
        return decodeURIComponent(part.slice(idx + 1).trim());
      } catch {
        return null;
      }
    }
  }
  return null;
}

/** Bearer token first, then the `auth_token` cookie. Works on any IncomingMessage. */
export function getTokenFromHeaders(headers: Record<string, string | string[] | undefined>): string | null {
  const auth = headers["authorization"];
  if (typeof auth === "string" && auth.startsWith("Bearer ")) return auth.slice(7).trim();
  return getAuthCookie(headers["cookie"]);
}

function getToken(req: Request): string | null {
  return getTokenFromHeaders(req.headers);
}

export function getSessionSecret(): string | null {
  return process.env.SECRET_KEY || process.env.SESSION_SECRET || null;
}

/**
 * Verifies a backend-issued session token (signature + exp + non-empty sub).
 * Returns the payload, or null when the token is invalid or auth is unconfigured.
 */
export function verifySessionToken(token: string | null | undefined): Record<string, any> | null {
  if (!token) return null;
  const secret = getSessionSecret();
  if (!secret) return null;
  const payload = verifyJwtHS256(token, secret);
  if (!payload || payload.sub === undefined || payload.sub === null || payload.sub === "") return null;
  return payload;
}

/** True for the master/admin claims that requirePlatformAdmin accepts without a DB lookup. */
export function isMasterPayload(payload: Record<string, any>): boolean {
  return payload.is_master === true || payload.admin === true || payload.sub === "master";
}

function readAuthPayload(req: Request, res: Response): Record<string, any> | null {
  const secret = getSessionSecret();
  if (!secret) {
    res.status(500).json({ error: "Server auth not configured" });
    return null;
  }
  const token = getToken(req);
  if (!token) {
    res.status(401).json({ error: "Authentication required" });
    return null;
  }
  const payload = verifyJwtHS256(token, secret);
  if (!payload || payload.sub === undefined || payload.sub === null || payload.sub === "") {
    res.status(401).json({ error: "Invalid or expired session" });
    return null;
  }
  (req as any).authUser = payload;
  return payload;
}

/** Requires a valid, unexpired, backend-signed session. Blocks unauthenticated access. */
export function requireAuth(req: Request, res: Response, next: NextFunction): void {
  if (!readAuthPayload(req, res)) return;
  next();
}

/**
 * Platform owner only (master JWT or ADMIN_MASTER_EMAIL match).
 * Used for /admin/ai-governance founder-panel routes.
 */
export async function requirePlatformAdmin(
  req: Request,
  res: Response,
  next: NextFunction,
): Promise<void> {
  const payload = readAuthPayload(req, res);
  if (!payload) return;

  if (isMasterPayload(payload)) {
    next();
    return;
  }

  const adminEmail = (process.env.ADMIN_MASTER_EMAIL || "").toLowerCase().trim();
  if (!adminEmail) {
    res.status(503).json({ error: "Admin access is not configured" });
    return;
  }

  const userId = Number(payload.sub);
  if (!Number.isFinite(userId) || userId <= 0) {
    res.status(403).json({ error: "Access denied" });
    return;
  }

  try {
    // Lazy import so plain requireAuth stays usable when DATABASE_URL is unset.
    const { eq } = await import("drizzle-orm");
    const { db } = await import("../db");
    const { users } = await import("../../shared/schema");
    const rows = await db.select().from(users).where(eq(users.id, userId)).limit(1);
    const email = (rows[0]?.email || "").toLowerCase().trim();
    if (!email || email !== adminEmail) {
      res.status(403).json({ error: "Access denied. Only the platform owner can access admin features." });
      return;
    }
    next();
  } catch (err) {
    console.error("[requirePlatformAdmin] lookup failed:", err);
    res.status(500).json({ error: "Failed to verify admin access" });
  }
}
