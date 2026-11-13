import crypto from "crypto";
import type { Request, Response, NextFunction } from "express";

// Guards the /internal/* routes the Python processes (FastAPI, simulation
// worker) call to push WebSocket broadcasts. Callers send
// `x-internal-secret: $INTERNAL_API_SECRET`.
//
// - Secret set: the header must match (constant-time), in every environment.
// - Secret unset: allowed only when NODE_ENV is "development" or "test";
//   anywhere else (production, staging, unset) the routes fail closed (503).
const OPEN_WHEN_UNSET = new Set(["development", "test"]);

export function requireInternalAuth(req: Request, res: Response, next: NextFunction) {
  const secret = process.env.INTERNAL_API_SECRET;
  if (!secret) {
    if (OPEN_WHEN_UNSET.has(process.env.NODE_ENV ?? "")) return next();
    return res.status(503).json({ error: "Internal routes not configured" });
  }
  const provided = req.headers["x-internal-secret"];
  const given = crypto.createHash("sha256").update(typeof provided === "string" ? provided : "", "utf8").digest();
  const expected = crypto.createHash("sha256").update(secret, "utf8").digest();
  if (typeof provided !== "string" || !crypto.timingSafeEqual(given, expected)) {
    return res.status(401).json({ error: "Unauthorized" });
  }
  next();
}
