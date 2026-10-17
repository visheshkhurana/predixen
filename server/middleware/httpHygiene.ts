// Small HTTP correctness pieces shared by the dev and production servers.
import type { Request, Response, NextFunction, Express } from "express";

/** /favicon.ico has no file; browsers and crawlers still ask for it. */
export function registerFaviconAlias(app: Express): void {
  app.get("/favicon.ico", (_req, res) => {
    res.setHeader("Cache-Control", "public, max-age=86400");
    res.redirect(301, "/favicon.png");
  });
}

/**
 * Last error handler, registered after static/SPA serving. Malformed URLs
 * (e.g. "/%ZZ") surface as a URIError or status 400 from param decoding and
 * get a clean 400; anything else becomes a generic 500 with no stack.
 */
export function finalErrorHandler(err: any, req: Request, res: Response, next: NextFunction): void {
  if (res.headersSent) {
    next(err);
    return;
  }
  const raw = Number(err?.status || err?.statusCode);
  const status = err instanceof URIError ? 400 : raw >= 400 && raw < 600 ? raw : 500;
  if (status >= 500) {
    console.error(`[error] ${status} ${req.method} ${req.path}:`, err?.stack || err);
  }
  const message = status === 400 ? "Bad Request" : status >= 500 ? "Internal Server Error" : String(err?.message || "Error");
  const wantsJson = req.originalUrl.startsWith("/api") || !(req.headers.accept || "").includes("text/html");
  res.status(status);
  res.setHeader("Cache-Control", "no-store");
  if (wantsJson) {
    res.json({ message });
  } else {
    res.type("text/plain").send(message);
  }
}
