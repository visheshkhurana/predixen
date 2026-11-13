// The last error handler, registered after static/SPA serving (server/index.ts).
//
// It used to be registered before serveStatic/setupVite, so an error raised in
// that layer (a malformed percent-encoding such as "/%ZZ" throws a URIError
// while the SPA catch-all decodes its param) skipped it and reached Express's
// default handler. It also echoed err.message on 500s, which can carry
// internals (file paths, upstream errors, SQL). Now: malformed URLs get a clean
// 400, 5xx get a generic body and the details go to the log only.
import type { Request, Response, NextFunction } from "express";

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
  const message =
    status === 400 ? "Bad Request" : status >= 500 ? "Internal Server Error" : String(err?.message || "Error");
  const wantsJson = req.originalUrl.startsWith("/api") || !(req.headers.accept || "").includes("text/html");
  res.status(status);
  res.setHeader("Cache-Control", "no-store");
  if (wantsJson) {
    res.json({ message });
  } else {
    res.type("text/plain").send(message);
  }
}
