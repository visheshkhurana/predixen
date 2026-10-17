// Cookie-authenticated writes must come from the app's own origin.
//
// Run: npx tsx --test server/tests/origin-check.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import express from "express";
import type { Server } from "http";
import { originCheck } from "../middleware/originCheck";

let server: Server;
let base = "";
let self = "";

test.before(async () => {
  process.env.APP_BASE_URL = "https://founderconsole.ai";
  process.env.CORS_ORIGINS = "https://app.example.com";
  const app = express();
  app.set("trust proxy", true);
  app.use(originCheck());
  app.all("*", (_req, res) => res.status(200).json({ ok: true }));
  await new Promise<void>((r) => {
    server = app.listen(0, "127.0.0.1", () => r());
  });
  const port = (server.address() as any).port;
  base = `http://127.0.0.1:${port}`;
  self = base;
});
test.after(() => server.close());

const COOKIE = { cookie: "auth_token=x.y.z" };
const post = (path: string, headers: Record<string, string>) =>
  fetch(base + path, { method: "POST", headers, body: "{}" }).then((r) => r.status);

test("cross-site cookie POST is rejected", { timeout: 10_000 }, async () => {
  assert.equal(await post("/api/companies", { ...COOKIE, origin: "https://evil.example" }), 403);
  assert.equal(await post("/api/companies", { ...COOKIE, referer: "https://evil.example/x" }), 403);
  assert.equal(await post("/api/companies", { ...COOKIE, origin: "null" }), 403);
});

test("cookie POST with no Origin or Referer is rejected", { timeout: 10_000 }, async () => {
  assert.equal(await post("/api/companies", COOKIE), 403);
});

test("same-origin and configured origins are allowed", { timeout: 10_000 }, async () => {
  assert.equal(await post("/api/companies", { ...COOKIE, origin: self }), 200);
  assert.equal(await post("/api/companies", { ...COOKIE, referer: `${self}/overview` }), 200);
  assert.equal(await post("/api/companies", { ...COOKIE, origin: "https://founderconsole.ai" }), 200);
  assert.equal(await post("/api/companies", { ...COOKIE, origin: "https://app.example.com" }), 200);
});

test("Bearer, cookieless and safe-method requests are not checked", { timeout: 10_000 }, async () => {
  assert.equal(await post("/api/companies", { ...COOKIE, authorization: "Bearer abc", origin: "https://evil.example" }), 200);
  assert.equal(await post("/api/auth/login", { origin: "https://evil.example" }), 200);
  const res = await fetch(base + "/api/companies", { headers: { ...COOKIE, origin: "https://evil.example" } });
  assert.equal(res.status, 200);
});

test("webhook receivers are exempt", { timeout: 10_000 }, async () => {
  for (const p of [
    "/api/billing/webhook",
    "/api/slack/events",
    "/api/notifications/resend-webhook",
    "/email-tracking/webhooks/resend",
    "/webhooks/lead-gen/ingest",
    "/internal/broadcast/simulation",
  ]) {
    assert.equal(await post(p, { ...COOKIE, origin: "https://hooks.example" }), 200, p);
  }
});
