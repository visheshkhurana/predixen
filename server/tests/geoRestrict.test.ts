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

const BROWSER_UA =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36";

/**
 * Defaults to a real browser user agent.
 *
 * Node's fetch otherwise sends "node", which the gate correctly treats as a
 * bot and lets through — so every block-expecting assertion would silently
 * pass for the wrong reason. Tests that care about bot handling pass their own
 * user-agent header.
 */
async function status(path: string, headers: Record<string, string> = {}): Promise<number> {
  const { base, server } = await startServer();
  try {
    const res = await fetch(base + path, {
      headers: { "user-agent": BROWSER_UA, ...headers },
    });
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

test("never blocks AD crawlers — regression, this broke production", async () => {
  // The first version of CRAWLER_UA matched "googlebot" but not
  // "adsbot-google". Google's ad landing-page crawler hit a 403 from a
  // non-allowed country and disapproved every ad in the account with
  // "Destination not working". Ad delivery stopped for two days before anyone
  // noticed, because the site itself looked perfectly healthy.
  const agents = [
    "AdsBot-Google (+http://www.google.com/adsbot.html)",
    "Mozilla/5.0 (Linux; Android 6.0.1;) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Mobile Safari/537.36 (compatible; AdsBot-Google-Mobile; +http://www.google.com/mobile/adsbot.html)",
    "AdsBot-Google-Mobile-Apps",
    "Mediapartners-Google",
    "adidxbot/2.0",
  ];
  for (const ua of agents) {
    assert.equal(
      await status("/", { "x-forwarded-for": IP.china, "user-agent": ua }),
      200,
      `expected ${ua} allowed — a blocked ad crawler disapproves the whole account`,
    );
  }
});

test("falls open for unrecognised bots", async () => {
  // Backstop for the crawler nobody thought of. Consistent with the gate
  // failing open everywhere else: letting a bot through costs nothing.
  const agents = ["SomeNewCrawler/1.0", "acme-monitor", "curl/8.4.0", "python-requests/2.31"];
  for (const ua of agents) {
    assert.equal(
      await status("/", { "x-forwarded-for": IP.china, "user-agent": ua }),
      200,
      `expected "${ua}" allowed`,
    );
  }
});

test("falls open when there is no user agent at all", async () => {
  // Uses raw http rather than fetch: node's fetch always sends "node" as the
  // UA, so it cannot express a genuinely absent header.
  const { base, server } = await startServer();
  try {
    const http = await import("node:http");
    const url = new URL(base);
    const code: number = await new Promise((resolve, reject) => {
      const req = http.request(
        {
          host: url.hostname,
          port: url.port,
          path: "/",
          headers: { "x-forwarded-for": IP.china },
        },
        (res) => {
          res.resume();
          resolve(res.statusCode ?? 0);
        },
      );
      req.on("error", reject);
      req.end();
    });
    assert.equal(code, 200);
  } finally {
    server.close();
  }
});

test("still blocks a real browser from a disallowed country", async () => {
  // The bot heuristics must not swallow the actual use case.
  const chrome =
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36";
  assert.equal(await status("/", { "x-forwarded-for": IP.china, "user-agent": chrome }), 403);
  assert.equal(await status("/", { "x-forwarded-for": IP.us, "user-agent": chrome }), 200);
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
