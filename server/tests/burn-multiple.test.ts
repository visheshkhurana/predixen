/**
 * HAG-163, tool 1 of 3: /tools/burn-multiple.
 *
 * Run: npx tsx --test server/tests/burn-multiple.test.ts
 *
 * The formula is not invented here and is not asserted from memory: every number below is
 * the worked example or an edge-case row of `hive/reports/quant-forge-tools-maths.md`,
 * Tool 1, whose arithmetic is reproduced by the Quant lane's own reference script —
 * vendored byte-for-byte at `server/tests/quant_forge_tools_check.py` and run by
 * `server/tests/test_quant_forge_tools.py`. Both files pin the same literals, so a drift in
 * either the reference or this implementation fails a test rather than going unnoticed.
 *
 * The last three assertions are structural, because the card's own handover fact is that a
 * new page needs TWO edits — the `<Route>` and the `PUBLIC_ROUTES` line — and a page that
 * ships with only one of them is either unreachable or invisible to the sitemap.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "fs";
import {
  BURN_MULTIPLE_BANDS,
  WORKED_EXAMPLE,
  bandFor,
  computeBurnMultiple,
  type BurnMultipleInputs,
} from "../../client/src/lib/tools/burnMultiple.ts";

/** Everything zero, so each case below states only the fields it is about. */
const ZERO: BurnMultipleInputs = {
  new_arr: 0,
  expansion_arr: 0,
  churned_arr: 0,
  contraction_arr: 0,
  cash_out: 0,
  cash_in: 0,
  period_months: 3,
};

/* ---------------------------------------------------------------- the worked example */

test("the maths file's worked example comes out at 3.00x", () => {
  const r = computeBurnMultiple(WORKED_EXAMPLE);
  assert.equal(r.outcome, "ok");
  assert.equal(r.netNewArr, 150_000); // 180,000 + 30,000 - 45,000 - 15,000
  assert.equal(r.netBurn, 450_000); // 600,000 - 150,000
  assert.equal(r.multiple, 3);
  assert.equal(r.multiple!.toFixed(2), "3.00");
  assert.equal(r.reason, null);
});

test("the worked example reconciles, because that is what the maths file checked by hand", () => {
  const r = computeBurnMultiple(WORKED_EXAMPLE);
  assert.equal(r.reconciliation.state, "pass");
});

test("the monthly-average variant cannot move the ratio, so it equals it", () => {
  const r = computeBurnMultiple(WORKED_EXAMPLE);
  assert.equal(r.monthlyAverage.netBurn, 150_000); // 450,000 / 3
  assert.equal(r.monthlyAverage.netNewArr, 50_000); // 150,000 / 3
  assert.equal(r.monthlyAverage.multiple, r.multiple);
});

/* ------------------------------------------------------------------ the edge-case table */

test("flat ARR is n/a with a reason, never Infinity and never 0", () => {
  // new 100k, churned 100k -> net new ARR exactly 0, with burn on top.
  const r = computeBurnMultiple({ ...ZERO, new_arr: 100_000, churned_arr: 100_000, cash_out: 300_000 });
  assert.equal(r.outcome, "not_applicable");
  assert.equal(r.multiple, null);
  assert.match(r.reason!, /no new ARR/);
  assert.ok(!Number.isFinite(r.multiple as number), "a null multiple is not an infinity");
});

test("shrinking ARR is n/a, and the ratio is not reported as a negative good score", () => {
  // new 250k against churn 150k + contraction 150k -> net new ARR -50k.
  const r = computeBurnMultiple({
    ...ZERO,
    new_arr: 250_000,
    churned_arr: 150_000,
    contraction_arr: 150_000,
    cash_out: 300_000,
  });
  assert.equal(r.netNewArr, -50_000);
  assert.equal(r.netBurn, 300_000);
  assert.equal(r.outcome, "not_applicable");
  assert.equal(r.multiple, null);
  assert.match(r.reason!, /ARR is shrinking/);
});

test("cash-flow positive is n/a — a negative burn multiple is not an achievement", () => {
  const r = computeBurnMultiple({ ...ZERO, new_arr: 100_000, cash_out: 80_000, cash_in: 100_000 });
  assert.equal(r.netBurn, -20_000);
  assert.equal(r.outcome, "not_applicable");
  assert.equal(r.multiple, null);
  assert.match(r.reason!, /cash-flow positive/);
});

test("zero burn against real growth is a legitimate 0.00, not an error", () => {
  const r = computeBurnMultiple({ ...ZERO, new_arr: 100_000, cash_out: 0, cash_in: 0 });
  assert.equal(r.outcome, "ok");
  assert.equal(r.multiple, 0);
  assert.equal(r.multiple!.toFixed(2), "0.00");
});

test("a negative input is rejected rather than computed", () => {
  for (const key of [
    "new_arr",
    "expansion_arr",
    "churned_arr",
    "contraction_arr",
    "cash_out",
    "cash_in",
  ] as const) {
    const r = computeBurnMultiple({ ...ZERO, new_arr: 100_000, cash_out: 10_000, [key]: -1 });
    assert.equal(r.outcome, "invalid", `${key} = -1 must be rejected`);
    assert.equal(r.multiple, null);
  }
});

test("a window shorter than one whole month is rejected", () => {
  for (const months of [0, -3, 1.5]) {
    const r = computeBurnMultiple({ ...ZERO, new_arr: 100_000, cash_out: 10_000, period_months: months });
    assert.equal(r.outcome, "invalid", `period_months = ${months} must be rejected`);
  }
});

test("a blank field reads as invalid, not as zero", () => {
  // `Number("")` is 0, which is the trap the page's text-held fields exist to avoid: a
  // blanked field must not silently become a legitimate zero.
  const r = computeBurnMultiple({ ...ZERO, new_arr: Number.NaN, cash_out: 10_000 });
  assert.equal(r.outcome, "invalid");
});

/* ----------------------------------------------------------------- the reconciliation */

test("mixed definitions of ARR fail the check instead of quietly printing a ratio", () => {
  // The maths file's own first draft made this mistake: a net new ARR of 150k against an
  // ARR that moved by 400k.
  const r = computeBurnMultiple({ ...WORKED_EXAMPLE, ending_arr: 1_600_000 });
  assert.equal(r.reconciliation.state, "fail");
  assert.equal(r.reconciliation.state === "fail" && r.reconciliation.expectedEndingArr, 1_350_000);
  // The ratio still computes — the check warns, it does not hide the number.
  assert.equal(r.multiple, 3);
});

test("omitting the ARR pair reports the check as not run, not as passing", () => {
  const r = computeBurnMultiple({
    new_arr: 180_000,
    expansion_arr: 30_000,
    churned_arr: 45_000,
    contraction_arr: 15_000,
    cash_out: 600_000,
    cash_in: 150_000,
    period_months: 3,
  });
  assert.equal(r.reconciliation.state, "not_run");
});

test("a rounding-level difference passes, because founders enter rounded ARR", () => {
  const r = computeBurnMultiple({ ...WORKED_EXAMPLE, ending_arr: 1_350_000.4 });
  assert.equal(r.reconciliation.state, "pass");
});

/* ---------------------------------------------------------------------- never a bad float */

test("no input produces Infinity, NaN or a negative multiple presented as a score", () => {
  const values = [0, 1, 5_000, 150_000, 1_000_000];
  for (const new_arr of values) {
    for (const churned of values) {
      for (const cash_out of values) {
        for (const cash_in of values) {
          const r = computeBurnMultiple({
            ...ZERO,
            new_arr,
            churned_arr: churned,
            cash_out,
            cash_in,
          });
          if (r.multiple !== null) {
            assert.ok(Number.isFinite(r.multiple), `infinity from ${new_arr}/${churned}/${cash_out}/${cash_in}`);
            assert.ok(r.multiple >= 0, `negative multiple ${r.multiple} from ${new_arr}/${churned}/${cash_out}/${cash_in}`);
          } else {
            assert.ok(r.reason, "a null multiple must always carry its reason");
          }
        }
      }
    }
  }
});

/* ------------------------------------------------------------------------------ the bands */

test("the benchmark bands break where quant-benchmarks.md Table 1 says", () => {
  assert.equal(bandFor(0.99).id, "efficient");
  assert.equal(bandFor(1).id, "median-2024");
  assert.equal(bandFor(2.3).id, "median-2024");
  assert.equal(bandFor(2.31).id, "above-median");
  assert.equal(bandFor(3).id, "above-median"); // the worked example
  assert.equal(BURN_MULTIPLE_BANDS.length, 3);
  for (const band of BURN_MULTIPLE_BANDS) {
    assert.ok(band.detail.length > 0, `${band.id} must state its source on the page`);
  }
});

/* ---------------------------------------------------------------------- structural checks */

const app = readFileSync("client/src/App.tsx", "utf8");
const sitemapGenerator = readFileSync("scripts/generate-sitemap.ts", "utf8");
const sitemap = readFileSync("client/public/sitemap.xml", "utf8");
const page = readFileSync("client/src/pages/burn-multiple.tsx", "utf8");
const seoPrerender = readFileSync("server/seo-prerender.ts", "utf8");

test("App.tsx registers /tools/burn-multiple", () => {
  assert.match(app, /<Route path="\/tools\/burn-multiple">/);
});

test("the route is declared in PUBLIC_ROUTES, which is the second edit a page needs", () => {
  assert.match(sitemapGenerator, /path: "\/tools\/burn-multiple"/);
});

test("the committed sitemap carries the new loc, so the page is not shipped invisible", () => {
  assert.match(sitemap, /<loc>https:\/\/founderconsole\.ai\/tools\/burn-multiple<\/loc>/);
});

test("the page ends in the same signup CTA as /tools/runway-calculator", () => {
  assert.match(page, /href="\/auth\?tab=register"/);
  assert.match(page, /data-testid="button-cta-connect"/);
  assert.match(page, /location: "burn-multiple"/);
});

test("the page states each CHOICE in one line, as the brief requires", () => {
  // The three choices of Tool 1, each visible to a reader rather than only in a comment.
  assert.match(page, /net burn is cash out minus cash in, not gross burn/);
  assert.match(page, /starting ARR plus net new ARR must equal ending ARR/);
  assert.match(page, /trailing 3 complete months/);
});

test("the page cites the benchmark sources it quotes", () => {
  assert.match(page, /scalevp\.com/);
  assert.match(page, /benchmarkit\.ai/);
});

test("the route is server-rendered, so a crawler does not get the homepage canonical", () => {
  // The third edit a page needs, and the one that is easy to forget: `injectSEO` returns
  // the shell untouched for a path it does not know, and that shell is `index, follow`
  // with the homepage canonical — so an unmapped growth page ships as a soft duplicate of
  // `/`. The siblings `/tools/runway-calculator`, `/default-alive` and `/survival-simulator`
  // all have an entry; this asserts the new one does too.
  assert.match(seoPrerender, /path === "\/tools\/burn-multiple"/);
  assert.match(seoPrerender, /canonical: SITE_URL \+ "\/tools\/burn-multiple"/);
  assert.match(seoPrerender, /function buildBurnMultipleBodyContent\(\): string \{/);
  assert.match(seoPrerender, /bodyContent: buildBurnMultipleBodyContent\(\)/);
});

test("the server-rendered text carries the formula and both sources", () => {
  // A crawler should read the same substance the page shows, including the citation.
  const body = seoPrerender.slice(seoPrerender.indexOf("function buildBurnMultipleBodyContent"));
  assert.match(body, /new ARR plus expansion ARR, minus churned ARR, minus contraction ARR/);
  assert.match(body, /cash out minus cash in/);
  assert.match(body, /scalevp\.com/);
  assert.match(body, /benchmarkit\.ai/);
  assert.match(body, /href="\/auth"/);
});
