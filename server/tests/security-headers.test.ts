// The gateway's CSP/HSTS policy (server/middleware/securityHeaders.ts).
// Production must not allow a WebSocket to any host; development keeps what
// Vite's HMR needs. Everything else is pinned byte-for-byte to the policy that
// lived inline in server/index.ts before it moved, so the move cannot drop a
// source an analytics or payments script depends on.
//
// Run: npx tsx --test server/tests/security-headers.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import express from "express";
import type { Server } from "http";
import { buildCsp, securityHeaders, HSTS_VALUE } from "../middleware/securityHeaders";

// The policy as server/index.ts built it before the move (dev and prod alike),
// keyed "<razorpay>-<isEmbed>".
const BEFORE: Record<string, string> = {
  "false-false": "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://us.posthog.com https://us-assets.i.posthog.com https://www.google-analytics.com https://www.googletagmanager.com https://connect.facebook.net https://static.ads-twitter.com https://analytics.twitter.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob: https://us.posthog.com https://www.facebook.com https://t.co https://analytics.twitter.com https://static.ads-twitter.com; connect-src 'self' ws: wss: https://us.posthog.com https://us.i.posthog.com https://us-assets.i.posthog.com https://www.google-analytics.com https://*.google-analytics.com https://analytics.google.com https://*.analytics.google.com https://stats.g.doubleclick.net https://www.google.com https://accounts.google.com https://oauth.platform.intuit.com https://quickbooks.api.intuit.com https://analytics.twitter.com https://t.co https://static.ads-twitter.com; frame-src https://accounts.google.com",
  "false-true": "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://us.posthog.com https://us-assets.i.posthog.com https://www.google-analytics.com https://www.googletagmanager.com https://connect.facebook.net https://static.ads-twitter.com https://analytics.twitter.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob: https://us.posthog.com https://www.facebook.com https://t.co https://analytics.twitter.com https://static.ads-twitter.com; connect-src 'self' ws: wss: https://us.posthog.com https://us.i.posthog.com https://us-assets.i.posthog.com https://www.google-analytics.com https://*.google-analytics.com https://analytics.google.com https://*.analytics.google.com https://stats.g.doubleclick.net https://www.google.com https://accounts.google.com https://oauth.platform.intuit.com https://quickbooks.api.intuit.com https://analytics.twitter.com https://t.co https://static.ads-twitter.com; frame-ancestors *",
  "true-false": "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://us.posthog.com https://us-assets.i.posthog.com https://www.google-analytics.com https://www.googletagmanager.com https://connect.facebook.net https://static.ads-twitter.com https://analytics.twitter.com https://checkout.razorpay.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob: https://us.posthog.com https://www.facebook.com https://t.co https://analytics.twitter.com https://static.ads-twitter.com https://cdn.razorpay.com; connect-src 'self' ws: wss: https://us.posthog.com https://us.i.posthog.com https://us-assets.i.posthog.com https://www.google-analytics.com https://*.google-analytics.com https://analytics.google.com https://*.analytics.google.com https://stats.g.doubleclick.net https://www.google.com https://accounts.google.com https://oauth.platform.intuit.com https://quickbooks.api.intuit.com https://analytics.twitter.com https://t.co https://static.ads-twitter.com https://api.razorpay.com https://lumberjack.razorpay.com; frame-src https://accounts.google.com https://api.razorpay.com https://checkout.razorpay.com",
  "true-true": "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://us.posthog.com https://us-assets.i.posthog.com https://www.google-analytics.com https://www.googletagmanager.com https://connect.facebook.net https://static.ads-twitter.com https://analytics.twitter.com https://checkout.razorpay.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob: https://us.posthog.com https://www.facebook.com https://t.co https://analytics.twitter.com https://static.ads-twitter.com https://cdn.razorpay.com; connect-src 'self' ws: wss: https://us.posthog.com https://us.i.posthog.com https://us-assets.i.posthog.com https://www.google-analytics.com https://*.google-analytics.com https://analytics.google.com https://*.analytics.google.com https://stats.g.doubleclick.net https://www.google.com https://accounts.google.com https://oauth.platform.intuit.com https://quickbooks.api.intuit.com https://analytics.twitter.com https://t.co https://static.ads-twitter.com https://api.razorpay.com https://lumberjack.razorpay.com; frame-ancestors *"
};

const directive = (csp: string, name: string) =>
  (csp.split("; ").find((d) => d.startsWith(name + " ")) || "").split(" ").slice(1);

test("development policy is unchanged from the inline original", () => {
  for (const razorpay of [false, true]) {
    for (const isEmbed of [false, true]) {
      assert.equal(buildCsp({ isEmbed, razorpay, dev: true }), BEFORE[`${razorpay}-${isEmbed}`]);
    }
  }
});

test("production policy differs only in its socket sources", () => {
  delete process.env.APP_BASE_URL;
  for (const razorpay of [false, true]) {
    for (const isEmbed of [false, true]) {
      const prod = buildCsp({ isEmbed, razorpay, dev: false });
      assert.equal(
        prod,
        BEFORE[`${razorpay}-${isEmbed}`].replace("connect-src 'self' ws: wss: ", "connect-src 'self' wss://founderconsole.ai "),
      );
    }
  }
});

test("production connect-src allows no wildcard sockets", () => {
  delete process.env.APP_BASE_URL;
  const connect = directive(buildCsp({ isEmbed: false, razorpay: true, dev: false }), "connect-src");
  assert.ok(!connect.includes("ws:") && !connect.includes("wss:"), connect.join(" "));
  assert.ok(connect.includes("'self'"));
  assert.ok(connect.includes("wss://founderconsole.ai"));
});

test("the socket origin follows APP_BASE_URL", () => {
  process.env.APP_BASE_URL = "https://staging.example.com";
  try {
    const connect = directive(buildCsp({ isEmbed: false, razorpay: false, dev: false }), "connect-src");
    assert.ok(connect.includes("wss://staging.example.com"));
  } finally {
    delete process.env.APP_BASE_URL;
  }
});

test("development keeps Vite HMR sockets", () => {
  assert.ok(directive(buildCsp({ isEmbed: false, razorpay: false, dev: true }), "connect-src").includes("ws:"));
});

test("HSTS is two years, same as FastAPI", () => {
  assert.equal(HSTS_VALUE, "max-age=63072000; includeSubDomains; preload");
});

test("middleware sets the headers; embeds may be framed, pages may not", { timeout: 10_000 }, async () => {
  const app = express();
  app.use(securityHeaders({ razorpay: false, dev: false }));
  app.get("*", (_req, res) => res.send("ok"));
  const server: Server = await new Promise((r) => {
    const s = app.listen(0, "127.0.0.1", () => r(s));
  });
  try {
    const base = `http://127.0.0.1:${(server.address() as any).port}`;
    const page = await fetch(`${base}/overview`);
    assert.equal(page.headers.get("strict-transport-security"), HSTS_VALUE);
    assert.equal(page.headers.get("x-frame-options"), "DENY");
    assert.ok(!(page.headers.get("content-security-policy") || "").includes("frame-ancestors *"));
    const embed = await fetch(`${base}/embed/survival`);
    assert.equal(embed.headers.get("x-frame-options"), null);
    assert.ok((embed.headers.get("content-security-policy") || "").includes("frame-ancestors *"));
  } finally {
    server.close();
  }
});
