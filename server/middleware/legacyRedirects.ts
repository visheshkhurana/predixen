import type { Request, Response, NextFunction } from "express";

// Old or guessable paths that shared links still point at. Without these the
// SPA catch-all answers 200 with "Page not found" — a soft 404 that neither
// users nor Google can recover from, and the bare path gets no SSR.
export const LEGACY_REDIRECTS: Record<string, string> = {
  "/runway-calculator": "/tools/runway-calculator",
};

export function legacyRedirects() {
  return (req: Request, res: Response, next: NextFunction) => {
    if (req.method !== "GET" && req.method !== "HEAD") return next();
    const path = req.path.length > 1 ? req.path.replace(/\/+$/, "") : req.path;
    const target = LEGACY_REDIRECTS[path.toLowerCase()];
    if (!target) return next();
    const qs = req.originalUrl.indexOf("?");
    return res.redirect(301, qs === -1 ? target : target + req.originalUrl.slice(qs));
  };
}
