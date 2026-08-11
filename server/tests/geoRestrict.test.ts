// Regression tests for the country gate.
//
// The blast radius here is the whole site: a gate that fails closed, mis-parses
// X-Forwarded-For, or catches Googlebot takes down traffic or search visibility
// with no obvious symptom. Every case below has already broken once in
// development or is a documented footgun of the underlying library.
//
// Run: npx tsx --test server/tests/geoRestrict.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import express from "express";
import type { Server } from "http";
import { geoRestrict } from "../middleware/geoRestrict";

function startServer(): Promise<{ base: string; server: Server }> {
  const app = express();
  app.set("trust proxy", true);
  app.use(geoRestrict());
  app.use("*", (_req, res) => {
    res.status(200).send("PAGE");
  });
  return new Promise((resolve) => {
    const server = app.listen(0, () => {
      const port = (server.address() as any).port;
      resolve({ base: `http://127.0.0.1:${port}`, server });
    });
  });
}

async function status(path: string, headers: Record<string, string> = {}): Promise<number> {
  const { base, server } = await startServer();
  try {
    const res = await fetch(base + path, { headers });
    return res.status;
  } finally {
    server.close();
  }
}

// Public addresses used below, verified against the bundled dataset.
const IP = {
  us: "8.8.8.8",
  india: "103.48.196.1",
  china: "1.2.4.8",
  uk: "81.2.69.142",
  canada: "24.48.0.1",
  uae: "94.200.0.1",
};

test("allows the configured countries", async () => {
  assert.equal(await status("/", { "x-forwarded-for": IP.us }), 200);
  assert.equal(await status("/", { "x-forwarded-for": IP.india }), 200);
});

test("blocks everything else", async () => {
  for (const ip of [IP.china, IP.uk, IP.canada, IP.uae]) {
    assert.equal(await status("/", { "x-forwarded-for": ip }), 403, `expected ${ip} blocked`);
  }
});

test("never blocks search or AI crawlers", async () => {
  // robots.txt invites GPTBot/ClaudeBot/PerplexityBot by name; a geo block that
  // caught them would silently contradict it. Googlebot crawls from shifting
  // ranges, and a blocked crawl looks identical to a dead site.
  const agents = [
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Mozilla/5.0 (compatible; bingbot/2.0)",
    "ClaudeBot/1.0",
    "GPTBot/1.1",
    "PerplexityBot/1.0",
  ];
  for (const ua of agents) {
    assert.equal(
      await status("/", { "x-forwarded-for": IP.china, "user-agent": ua }),
      200,
      `expected ${ua} allowed`,
    );
  }
});

test("never locks out an existing signed-in user abroad", async () => {
  assert.equal(
    await status("/overview", { "x-forwarded-for": IP.china, cookie: "auth_token=a.b.c" }),
    200,
  );
});

test("exempts API, embeds and crawler files", async () => {
  const h = { "x-forwarded-for": IP.china };
  for (const p of ["/api/health", "/embed/survival", "/robots.txt", "/sitemap.xml", "/favicon.ico"]) {
    assert.equal(await status(p, h), 200, `expected ${p} exempt`);
  }
});

test("fails open on private, missing and malformed addresses", async () => {
  // fast-geoip does not guard reserved space — it answers "JP" for 127.0.0.1
  // and "IT" for 192.168.1.1. Without the private-range check the gate would
  // block localhost and Railway's own health checks.
  assert.equal(await status("/"), 200);
  assert.equal(await status("/", { "x-forwarded-for": "10.0.0.5" }), 200);
  assert.equal(await status("/", { "x-forwarded-for": "127.0.0.1" }), 200);
  assert.equal(await status("/", { "x-forwarded-for": "192.168.1.1" }), 200);
  assert.equal(await status("/", { "x-forwarded-for": "not-an-ip" }), 200);
});

test("reads the client from the left of a proxy chain", async () => {
  assert.equal(await status("/", { "x-forwarded-for": `${IP.china}, 10.0.0.5` }), 403);
  assert.equal(await status("/", { "x-forwarded-for": `${IP.us}, 10.0.0.5` }), 200);
});

test("the kill switch disables the gate", async () => {
  process.env.GEO_RESTRICTION_ENABLED = "false";
  try {
    assert.equal(await status("/", { "x-forwarded-for": IP.china }), 200);
  } finally {
    delete process.env.GEO_RESTRICTION_ENABLED;
  }
});

test("GEO_ALLOWED_COUNTRIES overrides the default list", async () => {
  process.env.GEO_ALLOWED_COUNTRIES = "US,IN,AE";
  try {
    assert.equal(await status("/", { "x-forwarded-for": IP.uae }), 200);
    assert.equal(await status("/", { "x-forwarded-for": IP.china }), 403);
  } finally {
    delete process.env.GEO_ALLOWED_COUNTRIES;
  }
});
