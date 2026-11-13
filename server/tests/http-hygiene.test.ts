// Errors raised by the static/SPA layer (registered last) must reach a real
// handler: a malformed percent-encoding is a clean 400, and a 500 never echoes
// the error's message. server/index.ts must register the handler after
// serveStatic/setupVite.
//
// Run: npx tsx --test server/tests/http-hygiene.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import express from "express";
import type { Server } from "http";
import { finalErrorHandler } from "../middleware/httpHygiene";

let server: Server;
let base = "";

test.before(async () => {
  const app = express();
  app.get("/api/boom", () => {
    throw new Error("password=hunter2 at /srv/app/server/secret.ts:12");
  });
  app.get("/api/teapot", (_req, _res, next) => {
    next(Object.assign(new Error("Payload Too Large"), { status: 413 }));
  });
  // Same shape as serveStatic's SPA catch-all: a "*" route whose param decode
  // throws on "/%ZZ".
  app.use("*", (_req, res) => res.status(200).send("SPA"));
  app.use(finalErrorHandler);
  await new Promise<void>((r) => {
    server = app.listen(0, "127.0.0.1", () => r());
  });
  base = `http://127.0.0.1:${(server.address() as any).port}`;
});
test.after(() => server.close());

test("malformed URL gets a clean 400", { timeout: 10_000 }, async () => {
  const res = await fetch(`${base}/%ZZ`, { headers: { accept: "text/html" } });
  assert.equal(res.status, 400);
  assert.equal(await res.text(), "Bad Request");
});

test("malformed /api URL gets a JSON 400", { timeout: 10_000 }, async () => {
  const res = await fetch(`${base}/api/%ZZ`);
  assert.equal(res.status, 400);
  assert.deepEqual(await res.json(), { message: "Bad Request" });
});

test("a 500 does not echo the error message", { timeout: 10_000 }, async () => {
  const res = await fetch(`${base}/api/boom`);
  assert.equal(res.status, 500);
  const body = await res.text();
  assert.ok(!body.includes("hunter2") && !body.includes("/srv/app"), body);
  assert.deepEqual(JSON.parse(body), { message: "Internal Server Error" });
});

test("other 4xx keep their status and message", { timeout: 10_000 }, async () => {
  const res = await fetch(`${base}/api/teapot`);
  assert.equal(res.status, 413);
  assert.deepEqual(await res.json(), { message: "Payload Too Large" });
});

test("server/index.ts registers the handler after static and Vite serving", () => {
  const src = readFileSync("server/index.ts", "utf8");
  const handler = src.indexOf("app.use(finalErrorHandler)");
  assert.ok(handler !== -1, "finalErrorHandler is not registered");
  assert.ok(src.indexOf("serveStatic(app)") < handler, "handler must come after serveStatic");
  assert.ok(src.indexOf("setupVite(httpServer, app)") < handler, "handler must come after setupVite");
  assert.ok(!/app\.use\(\(err: any/.test(src), "the old early error handler is still registered");
});
