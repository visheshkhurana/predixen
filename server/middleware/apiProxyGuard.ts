// Does this process answer the request itself, or does FastAPI?
//
// `server/index.ts` mounts the FastAPI proxy on `/api` *before* the Express API
// routes exist: `registerRoutes` runs later, inside the startup IIFE, and the two
// AI routes are registered from there too. So the proxy is the first thing to see
// every `/api/*` request, and it needed a way to hand some of them back.
//
// It used a hardcoded list of prefixes -- `["/ai/", "/notion/", "/messaging/"]` --
// and a prefix list cannot express this question. It is wrong in both directions:
//
//   * A prefix with no complete local route behind it swallows paths that only
//     FastAPI serves. `POST /api/ai/feedback` and `GET /api/ai/feedback/stats`
//     are FastAPI's (`server/api/domain/ai_router.py`), but `/api/ai/` was
//     skipped wholesale, so the Copilot feedback button and the admin feedback
//     stats both 404'd against an Express router that has no such route.
//   * A locally served path that is not in the list is proxied to a backend
//     that does not have it. `/api/ai/` is served by exactly two routes --
//     `POST /api/ai/chat` and `POST /api/ai/quick-answer`, both in
//     `server/replit_integrations/chat/routes.ts` -- so the prefix protects
//     2 routes and shadows everything else under it.
//
// So the question is put to the router instead: is one of *this app's* routes a
// match for this request? That is correct in both directions and stays correct
// as routes are added, because the routes are the answer.

import type { Application, RequestHandler } from "express";

/** The parts of an Express 4 `Layer` this needs; the rest is not ours to rely on. */
interface RouterLayer {
  /** Present only on `app.get/post/...` layers, absent on `app.use(...)`. */
  route?: { methods?: Record<string, boolean> };
  /** The layer's own path, compiled by Express (so it carries Express's flags). */
  regexp?: RegExp;
  handle?: { stack?: unknown[] };
}

function stackOf(app: Application): RouterLayer[] {
  // Express 4 hangs the router off `_router`; 5 calls it `router`. Read both
  // rather than pinning the guard to one internal name.
  const anyApp = app as unknown as { _router?: { stack?: RouterLayer[] }; router?: { stack?: RouterLayer[] } };
  return anyApp._router?.stack ?? anyApp.router?.stack ?? [];
}

/**
 * Is `method url` handled by a route this app registered?
 *
 * `url` is the full path including the mount, e.g. `/api/ai/chat` -- Express
 * compiles route paths whole, so a guard mounted at `/api` must pass
 * `req.baseUrl + req.path` rather than the mount-relative `req.path`.
 *
 * Layers that are not routes are deliberately not matches: the JSON body parser,
 * the request logger and the static-file handler are all `app.use(...)` with no
 * sub-router behind them, and counting them would make every path local. A
 * catch-all fallback is excluded for the same reason, which is why the three
 * conditions below are load-bearing rather than an over-tight check.
 */
export function isAnsweredLocally(app: Application, method: string, url: string): boolean {
  const verb = method.toLowerCase();

  for (const layer of stackOf(app)) {
    const regexp = layer.regexp;
    if (!regexp || !regexp.test(url)) continue;

    if (layer.route) {
      if (layer.route.methods?.[verb]) return true;
      continue; // the path matches but this verb does not, e.g. GET where only POST is routed
    }

    // A mounted sub-router or sub-app: it owns everything under its mount path,
    // and only it can say whether it has a route for this path.
    if (Array.isArray(layer.handle?.stack)) return true;
  }

  return false;
}

/**
 * The `/api` middleware: hand locally served requests back to Express, proxy the
 * rest. Takes the app because the verdict is a property of the app's routes.
 */
export function apiProxyGuard(app: Application, apiProxy: RequestHandler): RequestHandler {
  return (req, res, next) => {
    if (isAnsweredLocally(req.app, req.method, req.baseUrl + req.path)) {
      return next();
    }
    return apiProxy(req, res, next);
  };
}
