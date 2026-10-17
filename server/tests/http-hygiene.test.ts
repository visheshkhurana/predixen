// Errors raised by the static/SPA layer (registered last) must reach a real
// handler: a malformed percent-encoding is a clean 400, not a stack trace.
// /favicon.ico resolves to the icon that exists.
//
// Run: npx tsx --test server/tests/http-hygiene.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import express from "express";
import type { Server } from "http";
import { finalErrorHandler, registerFaviconAlias } from "../middleware/httpHygiene";

let server: Server;
let base = "";

test.before(async () => {
  const app = express();
  registerFaviconAlias(app);
  // Same shape as serveStatic's SPA catch-all: a "*" route whose param decode
  // throws on "/%ZZ".
  app.use("*", (_req, res) => res.status(200).send("SPA"));
  app.get("/boom", () => {
    throw new Error("secret internals");
  });
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
  const body = await res.text();
  assert.equal(body, "Bad Request");
});

test("malformed /api URL gets a JSON 400", { timeout: 10_000 }, async () => {
  const res = await fetch(`${base}/api/%ZZ`);
  assert.equal(res.status, 400);
  assert.deepEqual(await res.json(), { message: "Bad Request" });
});

test("/favicon.ico redirects to the existing favicon.png", { timeout: 10_000 }, async () => {
  const res = await fetch(`${base}/favicon.ico`, { redirect: "manual" });
  assert.equal(res.status, 301);
  assert.equal(res.headers.get("location"), "/favicon.png");
});
