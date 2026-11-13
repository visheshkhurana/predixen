// HAG-294 server half — classifying crawler traffic so "From search or AI" stops
// being an unmeasurable zero.
//
// The client half is already built and shipped: `client/src/lib/posthog.ts` tags
// a pageview from `document.referrer`. That cannot ever see a crawler, because a
// crawler never runs the bundle — it fetches HTML and leaves. So the channel read
// a hard zero while GPTBot and Googlebot read the site daily. The gateway is the
// only layer that sees the raw request, which is what this pins.
//
// What is worth testing here, and why each one is not obvious:
//
//   1. The classification table, on real User-Agent strings. The one ordering
//      dependency is `applebot-extended` vs `applebot` — get it backwards and
//      Apple's AI-training crawler is silently counted as Apple's search crawler,
//      which is the exact conflation the metric exists to undo.
//   2. That no entry is shadowed by another. A table matched first-wins rots
//      quietly: adding a broad token above a narrow one turns the narrow one into
//      dead config that still looks live.
//   3. That a browser is silent. This middleware runs on every production request;
//      if it ever fails open it does not break, it floods.
//   4. That the response is untouched. The whole change is supposed to be
//      measurement only, and "measurement only" is a claim about behaviour, so it
//      is asserted rather than asserted-in-a-comment.
//
// Run: npx tsx --test server/tests/ai-agent-log.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import express from "express";
import type { Server } from "http";
import { aiAgentLog, classifyUserAgent, KNOWN_AGENTS } from "../middleware/aiAgentLog";

const CHROME_UA =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36";

/** Real strings, verbatim from the vendors' published UA docs. */
const REAL_UA = {
  gptbot: "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; GPTBot/1.2; +https://openai.com/gptbot",
  chatgptUser: "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; ChatGPT-User/1.0; +https://openai.com/bot",
  oaiSearchBot: "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; OAI-SearchBot/1.0; +https://openai.com/searchbot",
  perplexityBot: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36; compatible; PerplexityBot/1.0; +https://perplexity.ai/perplexitybot",
  claudeBot: "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; ClaudeBot/1.0; +claudebot@anthropic.com",
  googlebot: "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/140.0.0.0 Safari/537.36",
  googleExtended: "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Google-Extended/2.1; +http://www.google.com/bot.html) Chrome/140.0.0.0 Safari/537.36",
  applebotExtended: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Applebot-Extended/0.1",
  applebot: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Applebot/0.1",
};

test("classifies the crawlers the AI metric exists to see", () => {
  const cases: Array<[keyof typeof REAL_UA, string, string]> = [
    ["gptbot", "GPTBot", "ai_agent"],
    ["chatgptUser", "ChatGPT-User", "ai_agent"],
    ["oaiSearchBot", "OAI-SearchBot", "ai_agent"],
    ["perplexityBot", "PerplexityBot", "ai_agent"],
    ["claudeBot", "ClaudeBot", "ai_agent"],
    ["googleExtended", "Google-Extended", "ai_agent"],
    ["googlebot", "Googlebot", "search_crawler"],
  ];

  for (const [key, agent, cls] of cases) {
    const got = classifyUserAgent(REAL_UA[key]);
    assert.ok(got, `${key} classified as nothing`);
    assert.equal(got.agent, agent, `${key} → ${got.agent}`);
    assert.equal(got.class, cls, `${key} → class ${got.class}`);
  }
});

test("Applebot-Extended is not counted as Applebot — the one ordering dependency", () => {
  // `applebot-extended` contains `applebot`, so a naive table that lists the
  // short token first reports Google's competitor AI-training crawler as a plain
  // search crawl. That is the same conflation as folding crawlers into `Direct`.
  const extended = classifyUserAgent(REAL_UA.applebotExtended);
  assert.equal(extended?.agent, "Applebot-Extended");
  assert.equal(extended?.class, "ai_agent");

  // And the plain one still resolves, or the fix would just have moved the bug.
  const plain = classifyUserAgent(REAL_UA.applebot);
  assert.equal(plain?.agent, "Applebot");
  assert.equal(plain?.class, "search_crawler");
});

test("no table entry is shadowed by an earlier one", () => {
  // First-match-wins tables rot silently: insert a broad token above a narrow one
  // and the narrow one becomes dead config that still reads as live. Each token
  // is fed in alone, so the only entry that can match is the one being asked
  // about — unless something earlier swallows it.
  const dead: string[] = [];
  for (const entry of KNOWN_AGENTS) {
    const got = classifyUserAgent(entry.token);
    if (got?.agent !== entry.agent) {
      dead.push(`${entry.token} → ${got ? got.agent : "null"}`);
    }
  }
  assert.deepEqual(dead, [], `these entries can never match:\n  ${dead.join("\n  ")}`);
});

test("a browser is silent, and an absent header is silent", () => {
  // This runs on every production request. Failing open here does not throw, it
  // floods — every pageview becomes a line.
  assert.equal(classifyUserAgent(CHROME_UA), null);
  assert.equal(classifyUserAgent(""), null);
  assert.equal(classifyUserAgent(undefined), null);
  assert.equal(classifyUserAgent(null), null);
});

test("an unknown non-browser client is logged with its User-Agent", () => {
  // The backstop. A brand-new agent — the next ChatGPT-User — is not in the
  // table, and "unclassified" must not be indistinguishable from "did not visit",
  // which is the failure mode this whole change undoes.
  const got = classifyUserAgent("SomeNewAgent/0.9 (+https://example.com/crawler)");
  assert.equal(got?.class, "other_bot");
  assert.match(got!.ua!, /somenewagent/);
});

/** Boots a real Express app so the assertions run against real HTTP, not a mock. */
function startServer(
  onLine: (line: string) => void
): Promise<{ base: string; server: Server }> {
  const app = express();
  app.use(aiAgentLog({ write: onLine }));
  app.get("/tools/runway-calculator", (_req, res) => res.status(200).send("PAGE"));
  app.use("*", (_req, res) => res.status(404).send("NOT FOUND"));
  return new Promise((resolve) => {
    const server = app.listen(0, () => {
      const port = (server.address() as any).port;
      resolve({ base: `http://127.0.0.1:${port}`, server });
    });
  });
}

test("emits exactly one line per crawler request, reporting the finished status", async () => {
  const lines: string[] = [];
  const { base, server } = await startServer((l) => lines.push(l));
  try {
    const res = await fetch(`${base}/tools/runway-calculator?utm_source=x`, {
      headers: { "user-agent": REAL_UA.gptbot, "x-request-id": "req-abc" },
    });
    assert.equal(res.status, 200);
    assert.equal(lines.length, 1, `expected 1 line, got ${lines.length}`);

    const line = JSON.parse(lines[0]);
    assert.equal(line.event, "ai_agent_hit");
    assert.equal(line.agent, "GPTBot");
    assert.equal(line.ua_class, "ai_agent");
    assert.equal(line.method, "GET");
    assert.equal(line.status, 200);
    assert.equal(line.request_id, "req-abc");
    assert.equal(typeof line.ms, "number");
    assert.match(line.ts, /^\d{4}-\d{2}-\d{2}T/);

    // The query string is dropped. `/auth?email=…` style values live there, and
    // no metric here needs them — the same reason the client address is absent.
    assert.equal(line.path, "/tools/runway-calculator");
    assert.ok(!lines[0].includes("?utm_source"), "the query string was logged");
    assert.ok(!("ip" in line) && !lines[0].includes("127.0.0.1"), "an address was logged");
  } finally {
    server.close();
  }
});

test("the status is the real one — a 404 from a crawler is logged as 404", async () => {
  // Written on `res.on("finish")` rather than on entry for exactly this: "GPTBot
  // fetched a page" and "GPTBot fetched a 404" are different findings, and a log
  // written on the way in cannot tell them apart.
  const lines: string[] = [];
  const { base, server } = await startServer((l) => lines.push(l));
  try {
    const res = await fetch(`${base}/no-such-page`, {
      headers: { "user-agent": REAL_UA.googlebot },
    });
    assert.equal(res.status, 404);
    const line = JSON.parse(lines[0]);
    assert.equal(line.status, 404);
    // And the path survives a wildcard layer — see the next test for why that is
    // a separate assertion and not a freebie.
    assert.equal(line.path, "/no-such-page");
  } finally {
    server.close();
  }
});

test("the path is the real path even when a wildcard layer answers", async () => {
  // The bug this pins was found by running the real server, not by these tests,
  // which is why it is written down at this length.
  //
  // Express rewrites `req.url` while dispatching `app.use("*", …)`: once that
  // layer matches, `req.path` reads `"/"` and only `req.originalUrl` still holds
  // the real path. In production nearly every page is answered by exactly such a
  // layer — the SPA catch-all in `static.ts` — so a `req.path` read inside the
  // `res.on("finish")` callback logged `path:"/"` for every crawler hit. The
  // agent and the status were right, and the page was silently wrong, which is
  // the worst shape for a metric: it looks like it works.
  //
  // First run against the real server: four crawlers requested four different
  // paths and all four lines said `"path":"/"`.
  const lines: string[] = [];
  const { base, server } = await startServer((l) => lines.push(l));
  try {
    for (const path of ["/tools/runway-calculator", "/no-such-page", "/deep/unknown/route"]) {
      await fetch(base + path, { headers: { "user-agent": REAL_UA.perplexityBot } });
    }
    assert.equal(lines.length, 3);
    assert.deepEqual(
      lines.map((l) => JSON.parse(l).path),
      ["/tools/runway-calculator", "/no-such-page", "/deep/unknown/route"],
      "a wildcard layer clobbered the logged path"
    );
  } finally {
    server.close();
  }
});

test("a browser writes nothing", async () => {
  const lines: string[] = [];
  const { base, server } = await startServer((l) => lines.push(l));
  try {
    await fetch(`${base}/tools/runway-calculator`, { headers: { "user-agent": CHROME_UA } });
    assert.deepEqual(lines, []);
  } finally {
    server.close();
  }
});

test("the container's own liveness probe is not logged, but a real crawler on /health is", async () => {
  // `Dockerfile:64` curls `http://localhost:5000/health` every 30s. Logged, that
  // is 2,880 of our own health checks a day burying the traffic this exists to
  // show. The exemption is scoped to the backstop only — a known crawler asking
  // for /health is a real finding and stays visible.
  const lines: string[] = [];
  const { base, server } = await startServer((l) => lines.push(l));
  try {
    await fetch(`${base}/health`, { headers: { "user-agent": "curl/8.7.1" } });
    assert.deepEqual(lines, [], "the liveness probe was logged");

    await fetch(`${base}/health`, { headers: { "user-agent": REAL_UA.gptbot } });
    assert.equal(lines.length, 1, "a known crawler on /health must still be logged");
    const line = JSON.parse(lines[0]);
    assert.equal(line.agent, "GPTBot");
    assert.equal(line.path, "/health");
  } finally {
    server.close();
  }
});

/**
 * Response headers set by the HTTP layer per connection, not by the app.
 *
 * `Date` is a wall-clock stamp and `Connection`/`Keep-Alive` describe the socket,
 * so two requests to two servers can never agree on them and comparing them
 * would fail for a reason that has nothing to do with the middleware. Everything
 * else is kept, `Content-Length` included: a differing length is exactly the
 * kind of change this test exists to catch.
 */
const TRANSPORT_HEADERS = new Set(["date", "connection", "keep-alive"]);

/** Derived from `fetch` rather than named `Response`, so this file needs no
 *  global-type dependency to compile. */
type FetchResponse = Awaited<ReturnType<typeof fetch>>;

function headersOf(res: FetchResponse): Record<string, string> {
  const out: Record<string, string> = {};
  res.headers.forEach((value, key) => {
    if (TRANSPORT_HEADERS.has(key.toLowerCase())) return;
    out[key.toLowerCase()] = value;
  });
  return out;
}

test("the response is byte-identical with and without the middleware", async () => {
  // "Measurement only" is a claim about behaviour, so it is measured. Same app,
  // same routes, one with the middleware mounted and one without: every case a
  // crawler exercises must come back the same status, the same headers and the
  // same body.
  //
  // The headers half is why this test exists at all. An earlier version of it
  // compared status and body only, while the docstring above promises "It never
  // touches the response — no status, no header, no body". The header is the one
  // claim the old assertions could not see, so a `res.setHeader(...)` added to
  // the middleware — the exact way this guarantee would break in practice —
  // passed the suite. A test named for a property it does not measure is worse
  // than no test, because it gets quoted as coverage.
  async function withAndWithout(ua: string, path: string) {
    const withMw = express();
    withMw.use(aiAgentLog({ write: () => {} }));
    withMw.get("/tools/runway-calculator", (_req, res) => res.status(200).send("PAGE"));
    withMw.use("*", (_req, res) => res.status(404).send("NOT FOUND"));

    const without = express();
    without.get("/tools/runway-calculator", (_req, res) => res.status(200).send("PAGE"));
    without.use("*", (_req, res) => res.status(404).send("NOT FOUND"));

    const boot = (app: express.Express) =>
      new Promise<{ base: string; server: Server }>((resolve) => {
        const server = app.listen(0, () => {
          const port = (server.address() as any).port;
          resolve({ base: `http://127.0.0.1:${port}`, server });
        });
      });

    const a = await boot(withMw);
    const b = await boot(without);
    try {
      const [ra, rb] = await Promise.all([
        fetch(a.base + path, { headers: { "user-agent": ua } }),
        fetch(b.base + path, { headers: { "user-agent": ua } }),
      ]);
      return {
        a: { status: ra.status, headers: headersOf(ra), body: await ra.text() },
        b: { status: rb.status, headers: headersOf(rb), body: await rb.text() },
      };
    } finally {
      a.server.close();
      b.server.close();
    }
  }

  for (const ua of [REAL_UA.gptbot, REAL_UA.googlebot, CHROME_UA, "curl/8.7.1"]) {
    for (const path of ["/tools/runway-calculator", "/no-such-page"]) {
      const { a, b } = await withAndWithout(ua, path);
      assert.equal(a.status, b.status, `${ua} ${path}: status changed`);
      assert.deepEqual(a.headers, b.headers, `${ua} ${path}: a response header changed`);
      assert.equal(a.body, b.body, `${ua} ${path}: body changed`);
    }
  }
});
