// Unknown tool and industry URLs were HTTP 200 with the SPA shell (or a
// noindex title and an empty body). They must be a real 404: status and SSR.
// Valid slugs stay 200.
//
// Run: npx tsx --test server/tests/soft-404-status.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import express from "express";
import { readFileSync } from "fs";
import type { Server } from "http";
import { RUNWAY_INDUSTRIES } from "../../client/src/data/runway-industries";
import { renderHtmlPage } from "../seo-prerender";

const SHELL = readFileSync("client/index.html", "utf8");

const NOT_FOUND = ["/tools/unknown", "/tools/", "/tools", "/runway/not-a-real-industry"];
const TOOLS = [
  "/tools/runway-calculator",
  "/tools/burn-multiple",
  "/tools/dilution",
  "/tools/ltv-cac",
];

function startServer(): Promise<{ base: string; server: Server }> {
  const app = express();
  app.use("*", (req, res) => {
    const pathname = req.originalUrl.split("?")[0].split("#")[0];
    const page = renderHtmlPage(SHELL, pathname);
    res.status(page.status).type("html").send(page.html);
  });
  return new Promise((resolve) => {
    const server = app.listen(0, () => {
      resolve({ base: `http://127.0.0.1:${(server.address() as any).port}`, server });
    });
  });
}

test("unknown tool and industry URLs are HTTP 404 with a not-found document", async (t) => {
  const { base, server } = await startServer();
  t.after(() => server.close());

  for (const path of NOT_FOUND) {
    const response = await fetch(base + path);
    const html = await response.text();
    assert.equal(response.status, 404, path);
    assert.match(html, /<h1>Page not found<\/h1>/, path);
    assert.match(html, /content="noindex, follow"/, path);
    assert.doesNotMatch(html, /Flight Simulator for Founders/, path);
  }
});

test("valid tool and industry slugs stay 200, including a trailing slash", async (t) => {
  const { base, server } = await startServer();
  t.after(() => server.close());

  for (const path of TOOLS) {
    for (const suffix of ["", "/"]) {
      const response = await fetch(base + path + suffix);
      const html = await response.text();
      assert.equal(response.status, 200, path + suffix);
      assert.match(html, /<h1>/, path + suffix);
      assert.doesNotMatch(html, /<h1>Page not found<\/h1>/, path + suffix);
    }
  }

  for (const industry of RUNWAY_INDUSTRIES) {
    const response = await fetch(base + "/runway/" + industry.slug);
    const html = await response.text();
    assert.equal(response.status, 200, industry.slug);
    assert.match(html, new RegExp(`<h1>${industry.name}</h1>`));
    assert.doesNotMatch(html, /<h1>Page not found<\/h1>/);
  }

  const appShell = await fetch(base + "/overview");
  assert.equal(appShell.status, 200);
});

test("production HTML catch-alls use renderHtmlPage for the status", () => {
  const staticSrc = readFileSync("server/static.ts", "utf8");
  const viteSrc = readFileSync("server/vite.ts", "utf8");
  assert.match(staticSrc, /renderHtmlPage\(indexHtml, pathname\)/);
  assert.match(staticSrc, /res\.status\(page\.status\)/);
  assert.match(viteSrc, /renderHtmlPage\(page, cleanPath\)/);
  assert.match(viteSrc, /res\.status\(rendered\.status\)/);
  assert.doesNotMatch(staticSrc, /res\.status\(200\)/);
  assert.doesNotMatch(viteSrc, /res\.status\(200\)/);
});
