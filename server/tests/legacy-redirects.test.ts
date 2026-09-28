// /runway-calculator was a soft 404 (200 + SPA "Page not found"); it must 301
// to the live tool and keep UTM/query params so shared links still attribute.
//
// Run: npx tsx --test server/tests/legacy-redirects.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import express from "express";
import type { Server } from "http";
import { legacyRedirects } from "../middleware/legacyRedirects";

function startServer(): Promise<{ base: string; server: Server }> {
  const app = express();
  app.use(legacyRedirects());
  app.use("*", (_req, res) => {
    res.status(200).send("PAGE");
  });
  return new Promise((resolve) => {
    const server = app.listen(0, () => {
      resolve({ base: `http://127.0.0.1:${(server.address() as any).port}`, server });
    });
  });
}

test("legacy redirects", async (t) => {
  const { base, server } = await startServer();
  t.after(() => server.close());
  const get = (p: string, method = "GET") => fetch(base + p, { method, redirect: "manual" });

  await t.test("bare /runway-calculator 301s to the tool", async () => {
    const r = await get("/runway-calculator");
    assert.equal(r.status, 301);
    assert.equal(r.headers.get("location"), "/tools/runway-calculator");
  });

  await t.test("trailing slash and case are normalised", async () => {
    for (const p of ["/runway-calculator/", "/Runway-Calculator"]) {
      const r = await get(p);
      assert.equal(r.status, 301, p);
      assert.equal(r.headers.get("location"), "/tools/runway-calculator");
    }
  });

  await t.test("query string is preserved", async () => {
    const r = await get("/runway-calculator?utm_source=x&ref=tw");
    assert.equal(r.headers.get("location"), "/tools/runway-calculator?utm_source=x&ref=tw");
  });

  await t.test("HEAD redirects too; POST passes through", async () => {
    assert.equal((await get("/runway-calculator", "HEAD")).status, 301);
    assert.equal((await get("/runway-calculator", "POST")).status, 200);
  });

  await t.test("the live tool and other paths are untouched", async () => {
    for (const p of ["/tools/runway-calculator", "/runway/saas", "/survival-simulator"]) {
      assert.equal((await get(p)).status, 200, p);
    }
  });
});
