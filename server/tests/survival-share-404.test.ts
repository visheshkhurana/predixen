// /survival/:id answers 404 when the backend says the simulation does not
// exist; any backend failure keeps the old 200 + noindex shell.
//
// Run: npx tsx --test server/tests/survival-share-404.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "fs";
import {
  clearSurvivalShareCache,
  renderHtmlPageWithLookups,
  survivalShareExists,
  survivalShareId,
} from "../survival-share-status";

const SHELL = readFileSync("client/index.html", "utf8");
const robots = (html: string) => html.match(/<meta name="robots" content="([^"]*)"/)?.[1] ?? null;

function fakeFetch(status: number | "throw" | "hang", calls: string[] = []): typeof fetch {
  return (async (url: any, init?: any) => {
    calls.push(String(url));
    if (status === "throw") throw new Error("ECONNREFUSED");
    if (status === "hang") {
      return await new Promise((_, reject) => {
        init?.signal?.addEventListener("abort", () => reject(new Error("aborted")));
      });
    }
    return new Response(status === 200 ? "{}" : "{\"detail\":\"x\"}", { status });
  }) as typeof fetch;
}

test("only /survival/<id> is looked up", () => {
  assert.equal(survivalShareId("/survival/abc_123"), "abc_123");
  assert.equal(survivalShareId("/survival/abc/"), "abc");
  assert.equal(survivalShareId("/survival-simulator"), null);
  assert.equal(survivalShareId("/survival/a/b"), null);
});

test("unknown id -> 404 noindex", async () => {
  clearSurvivalShareCache();
  const calls: string[] = [];
  const page = await renderHtmlPageWithLookups(SHELL, "/survival/nope1", { fetchImpl: fakeFetch(404, calls), baseUrl: "http://be" });
  assert.equal(page.status, 404);
  assert.equal(robots(page.html), "noindex, follow");
  assert.match(page.html, /Page not found/);
  assert.deepEqual(calls, ["http://be/survival-sim/results/nope1"]);
});

test("existing id -> 200 share page", async () => {
  clearSurvivalShareCache();
  const page = await renderHtmlPageWithLookups(SHELL, "/survival/yes1", { fetchImpl: fakeFetch(200), baseUrl: "http://be" });
  assert.equal(page.status, 200);
  assert.equal(robots(page.html), "noindex, follow");
  assert.match(page.html, /og-image\/yes1\.png/);
});

test("backend 5xx / network error / timeout -> 200 noindex fallback", async () => {
  for (const s of [500, 502, "throw", "hang"] as const) {
    clearSurvivalShareCache();
    const page = await renderHtmlPageWithLookups(SHELL, "/survival/maybe1", {
      fetchImpl: fakeFetch(s), baseUrl: "http://be", timeoutMs: 50,
    });
    assert.equal(page.status, 200, String(s));
    assert.equal(robots(page.html), "noindex, follow");
  }
});

test("results are cached; failures are not", async () => {
  clearSurvivalShareCache();
  const calls: string[] = [];
  const opts = { fetchImpl: fakeFetch(404, calls), baseUrl: "http://be" };
  assert.equal(await survivalShareExists("c1", opts), "missing");
  assert.equal(await survivalShareExists("c1", opts), "missing");
  assert.equal(calls.length, 1);

  const errCalls: string[] = [];
  const errOpts = { fetchImpl: fakeFetch("throw", errCalls), baseUrl: "http://be" };
  assert.equal(await survivalShareExists("c2", errOpts), "unknown");
  assert.equal(await survivalShareExists("c2", errOpts), "unknown");
  assert.equal(errCalls.length, 2);

  // Negative entries expire.
  let t = 0;
  const tOpts = { fetchImpl: fakeFetch(404, calls), baseUrl: "http://be", now: () => t };
  clearSurvivalShareCache();
  await survivalShareExists("c3", tOpts);
  t = 61_000;
  await survivalShareExists("c3", tOpts);
  assert.equal(calls.filter((u) => u.endsWith("/c3")).length, 2);
});

test("non-survival paths never hit the backend", async () => {
  const calls: string[] = [];
  const page = await renderHtmlPageWithLookups(SHELL, "/tools/dilution", { fetchImpl: fakeFetch(404, calls) });
  assert.equal(page.status, 200);
  assert.equal(calls.length, 0);
});
