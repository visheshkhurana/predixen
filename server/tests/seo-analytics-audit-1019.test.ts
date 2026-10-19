// Audit 10-19: share pages are noindex; tool titles have one source shared by
// prerender and client; every free tool sends calculator_used once per view,
// and a survival run is tracked.
//
// Run: npx tsx --test server/tests/seo-analytics-audit-1019.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "fs";
import { injectSEO, pageHttpStatus } from "../seo-prerender";
import { RUNWAY_INDUSTRIES } from "../../client/src/data/runway-industries";
import { TOOL_PAGE_META, runwayIndustryPageMeta } from "../../client/src/data/tool-page-meta";
import { createCalculatorUsedController } from "../../client/src/lib/calculator-used";

const SHELL = readFileSync("client/index.html", "utf8");
const page = (name: string) => readFileSync(`client/src/pages/${name}.tsx`, "utf8");

function robots(html: string): string | null {
  return html.match(/<meta name="robots" content="([^"]*)"/)?.[1] ?? null;
}
function title(html: string): string | null {
  return html.match(/<title>([^<]*)<\/title>/)?.[1] ?? null;
}
const unescape = (s: string) => s.replace(/&quot;/g, '"').replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&");

test("a share token must be a safe alphabet or the page is a 404", () => {
  const ok = "/simulate-v2/shared/tok_EN-x";
  assert.equal(pageHttpStatus(ok), 200, ok);
  assert.match(
    injectSEO(SHELL, ok),
    /rel="canonical" href="https:\/\/founderconsole\.ai\/simulate-v2\/shared\/tok_EN-x"/,
  );

  const evil = "/scenarios/shared/abc\"<img>";
  assert.equal(pageHttpStatus(evil), 404, evil);
  const html = injectSEO(SHELL, evil);
  assert.match(html, /<h1>Page not found<\/h1>/);
  assert.equal(html.includes("<img>"), false);
  assert.match(html, /rel="canonical" href="https:\/\/founderconsole\.ai\/scenarios"/);

  const src = readFileSync("server/seo-prerender.ts", "utf8");
  assert.match(src, /escapeHtml\(token\)/);
});

test("share pages are noindex, follow", () => {
  for (const path of ["/survival/abc123", "/scenarios/shared/4f1c-uuid", "/simulate-v2/shared/tok_EN-x"]) {
    assert.equal(robots(injectSEO(SHELL, path)), "noindex, follow", path);
  }
  // A real tool page is still indexable.
  assert.equal(robots(injectSEO(SHELL, "/tools/dilution")), "index, follow");
});

test("prerendered tool titles match the shared meta", () => {
  for (const [path, meta] of Object.entries(TOOL_PAGE_META)) {
    assert.equal(unescape(title(injectSEO(SHELL, path)) ?? ""), meta.title, path);
  }
  for (const ind of RUNWAY_INDUSTRIES) {
    assert.equal(
      unescape(title(injectSEO(SHELL, `/runway/${ind.slug}`)) ?? ""),
      runwayIndustryPageMeta(ind).title,
      ind.slug,
    );
  }
});

test("client tool pages take title/description from the shared meta", () => {
  const pages: Record<string, string> = {
    "runway-calculator": "/tools/runway-calculator",
    "burn-multiple": "/tools/burn-multiple",
    dilution: "/tools/dilution",
    "ltv-cac": "/tools/ltv-cac",
    "tools-index": "/tools",
  };
  for (const [name, path] of Object.entries(pages)) {
    const src = page(name);
    const call = src.slice(src.indexOf("useSEO({"), src.indexOf("useSEO({") + 200);
    assert.ok(call.includes(`...TOOL_PAGE_META["${path}"]`), name);
    assert.ok(!/\n\s+title:/.test(call.split("path:")[0]), `${name} still hardcodes a title`);
  }
  assert.ok(page("runway-by-industry").includes("...runwayIndustryPageMeta(industry)"));
});

function fakeTimers() {
  let next = 1;
  const pending = new Map<number, () => void>();
  return {
    setTimer: (fn: () => void) => {
      const id = next++;
      pending.set(id, fn);
      return id as unknown as ReturnType<typeof setTimeout>;
    },
    clearTimer: (h: ReturnType<typeof setTimeout>) => {
      pending.delete(h as unknown as number);
    },
    flush: () => {
      const fns = [...pending.values()];
      pending.clear();
      fns.forEach((f) => f());
    },
    get size() {
      return pending.size;
    },
  };
}

test("calculator_used fires once, after a pause, only with a result", () => {
  const timers = fakeTimers();
  const events: Array<[string, Record<string, unknown>]> = [];
  const c = createCalculatorUsedController({
    calculator: "dilution",
    emit: (e, p) => events.push([e, p]),
    setTimer: timers.setTimer,
    clearTimer: timers.clearTimer,
  });

  c.update(false, true); // defaults: nothing
  assert.equal(timers.size, 0);
  c.update(true, false); // edited, but no result
  assert.equal(timers.size, 0);

  c.update(true, true);
  c.update(true, true); // keystrokes restart the timer
  c.update(true, true);
  assert.equal(timers.size, 1);
  timers.flush();
  assert.deepEqual(events, [["calculator_used", { calculator: "dilution" }]]);

  c.update(true, true);
  timers.flush();
  assert.equal(events.length, 1, "once per page view");
});

test("every free tool wires calculator_used; survival run is tracked", () => {
  for (const name of ["burn-multiple", "dilution", "ltv-cac", "runway-by-industry", "embed-survival"]) {
    assert.match(page(name), /useCalculatorUsed\(\s*\n?\s*"/, name);
  }
  const survival = page("survival-simulator");
  const onSuccess = survival.slice(survival.indexOf("onSuccess: (data) =>"), survival.indexOf("onError:"));
  assert.ok(onSuccess.includes('trackFunnel("survival_simulation_run"'));
  assert.ok(onSuccess.includes('trackFunnel("calculator_used", { calculator: "survival-simulator" })'));
});
