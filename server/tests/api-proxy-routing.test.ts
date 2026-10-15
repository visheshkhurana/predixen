// HAG-270. The Copilot feedback button is dead on main.
//
// `server/index.ts` mounts the FastAPI proxy on `/api` before the Express API
// routes are registered, so the proxy decides, for every `/api/*` request,
// whether to serve it here or forward it to FastAPI. It decided with a prefix
// list -- `["/ai/", "/notion/", "/messaging/"]` -- and the list is wrong in both
// directions at once:
//
//   * `/api/ai/` protected two routes and swallowed everything else under the
//     prefix. `POST /api/ai/feedback` and `GET /api/ai/feedback/stats` are
//     FastAPI's (`server/api/domain/ai_router.py:59` and `:84`); the client's
//     `FeedbackButton` calls the first and `admin/system-tools.tsx` calls the
//     second. Neither reached FastAPI: the skip handed them to an Express router
//     with no such route, and the request died there.
//   * The defence of the list is also its defect. Dropping `/ai/` to un-shadow
//     the feedback routes would have proxied the two routes the prefix exists to
//     protect -- `POST /api/ai/chat` and `POST /api/ai/quick-answer`, registered
//     from `server/replit_integrations/chat/routes.ts` -- to a backend that has
//     no `/ai/chat`.
//
// So the list cannot be fixed by editing the list. The guard asks the router
// whether one of the app's own routes matches the request, which is the only
// phrasing that is right in both directions.
//
// The app is driven through `app.handle` rather than `app.listen`, so this runs
// without binding a port and exercises the real middleware chain, real route
// matching and a real `req.baseUrl`.
//
// Run: npx tsx --test server/tests/api-proxy-routing.test.ts

import test from "node:test";
import assert from "node:assert/strict";
import express from "express";
import type { Application } from "express";
import { apiProxyGuard, isAnsweredLocally } from "../middleware/apiProxyGuard";
import { registerChatRoutes } from "../replit_integrations/chat/routes";

/**
 * The two branches answer differently, so a test can say which one ran.
 *
 * The proxy is stubbed rather than pointed at FastAPI: what is under test is the
 * routing decision, not the forward.
 */
const PROXIED = "PROXIED-TO-FASTAPI";

/**
 * One request through the real Express chain, without a listening socket.
 *
 * `app.handle` is what the http server calls, and Express's own `expressInit`
 * fills in `req.res`, `res.req` and `req.next`, so the only things missing are
 * the socket writes -- stubbed below, because nothing here inspects the wire.
 */
function routed(app: Application, method: string, url: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const req: any = Object.create(app.request);
    req.app = app;
    req.method = method;
    req.url = url;
    req.originalUrl = url;
    req.headers = {};
    req.socket = { remoteAddress: "127.0.0.1" };
    req.connection = req.socket;

    const res: any = Object.create(app.response);
    res.app = app;
    res.statusCode = 200;
    res.setHeader = () => res;
    res.getHeader = () => undefined;
    res.removeHeader = () => {};
    res.writeHead = () => res;
    res.end = (chunk: unknown) => {
      resolve(chunk === undefined || chunk === null ? "" : String(chunk));
      return res;
    };

    try {
      app.handle(req, res, (err: unknown) => (err ? reject(err) : resolve("")));
    } catch (err) {
      reject(err);
    }
  });
}

/** The app under test: a route registered after the guard, a mounted router, and the guard. */
function buildApp(): Application {
  const app = express();

  // Registered *after* the guard, exactly as `registerRoutes` is in
  // `server/index.ts` -- the guard has to see it anyway.
  app.post("/api/ai/chat", (_req, res) => {
    res.json({ served: "express" });
  });

  // And one mounted router, the shape `/api/notion/pages` uses.
  const notion = express.Router();
  notion.get("/", (_req, res) => {
    res.json({ served: "express" });
  });
  app.use("/api/notion/pages", notion);

  app.use("/api", apiProxyGuard(app, ((_req: any, res: any) => {
    res.status(200).send(PROXIED);
  }) as any));

  return app;
}

const servedBy = (method: string, url: string) =>
  routed(buildApp(), method, url).then((body) => {
    if (body.includes(PROXIED)) return PROXIED;
    if (body.includes('"served":"express"')) return "express";
    // Nothing answered: Express ran out of handlers, which is the shape of the
    // defect. Named rather than folded into "express", so a test asserting a
    // local route cannot pass because the request went nowhere.
    return "UNROUTED";
  });

test("a FastAPI-only /api/ai path reaches FastAPI instead of dying on the skip", async () => {
  // The defect. `POST /api/ai/feedback` is the Copilot feedback button.
  assert.equal(await servedBy("POST", "/api/ai/feedback"), PROXIED);
});

test("the second shadowed path reaches FastAPI too", async () => {
  // `GET /api/ai/feedback/stats`, the admin System Tools tab.
  assert.equal(await servedBy("GET", "/api/ai/feedback/stats"), PROXIED);
});

test("a locally routed path is still served here, though it is registered after the guard", async () => {
  assert.equal(await servedBy("POST", "/api/ai/chat"), "express");
});

test("the check is per verb, not per path", async () => {
  // `/api/ai/chat` is POST-only here. A GET on it matches no local route, so it
  // must not be claimed locally by a path-only match.
  assert.equal(await servedBy("GET", "/api/ai/chat"), PROXIED);
});

test("a mounted local router still wins over the proxy", async () => {
  assert.equal(await servedBy("GET", "/api/notion/pages"), "express");
});

test("a path with no local route in either app is proxied", async () => {
  // `/api/llm/*` is FastAPI's (`server/api/llm.py`). It was never in the old
  // list, so it is proxied today -- locked in here, because the guard must not
  // become a whitelist pointing the other way.
  assert.equal(await servedBy("POST", "/api/llm/chat"), PROXIED);
});

test("the verdict is asked of the real AI routes, not a fixture of them", () => {
  // `registerChatRoutes` is the file that serves `/api/ai/*` on the real app.
  const app = express();
  registerChatRoutes(app);

  assert.equal(isAnsweredLocally(app, "POST", "/api/ai/chat"), true);
  assert.equal(isAnsweredLocally(app, "POST", "/api/ai/quick-answer"), true);

  // The two the prefix list shadowed. Neither is here, so neither may be
  // claimed local -- this is the assertion a prefix list cannot satisfy.
  assert.equal(isAnsweredLocally(app, "POST", "/api/ai/feedback"), false);
  assert.equal(isAnsweredLocally(app, "GET", "/api/ai/feedback/stats"), false);
});
