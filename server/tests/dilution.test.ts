/**
 * HAG-163, tool 2 of 3: /tools/dilution.
 *
 * Run: npx tsx --test server/tests/dilution.test.ts
 *
 * The formula is not invented here and is not asserted from memory: every number below is
 * the worked example or an edge-case row of `hive/reports/quant-forge-tools-maths.md`,
 * Tool 2, whose arithmetic is reproduced by the Quant lane's own reference script —
 * vendored byte-for-byte at `server/tests/quant_forge_tools_check.py` and run by
 * `server/tests/test_quant_forge_tools_dilution.py`. Both sides pin the same literals, so
 * a drift in either the reference or this implementation fails a test rather than going
 * unnoticed.
 *
 * The last group of assertions is structural: the card's own handover fact is that a new
 * public page needs THREE edits — the `<Route>`, the `PUBLIC_ROUTES` line and a
 * `getPageMeta` entry — and a page that ships with only two of them is either unreachable,
 * invisible to the sitemap, or served with the homepage canonical as a soft duplicate.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "fs";
import {
  CUMULATIVE_KEEP_2025,
  WORKED_EXAMPLE,
  computeDilution,
  type DilutionInputs,
} from "../../client/src/lib/tools/dilution.ts";

/** A round with nothing in it, so each case below states only the fields it is about. */
const BASE: DilutionInputs = {
  pre_money_valuation: 8_000_000,
  raise_amount: 2_000_000,
  founder_shares: 8_000_000,
  existing_pool_shares: 1_000_000,
  pool_target_pct: 0,
};

/** Round a percentage the way the reference script prints it, for exact comparison. */
const pct4 = (fraction: number) => Number((fraction * 100).toFixed(4));

/* ---------------------------------------------------------------- the worked example */

test("the maths file's worked example reproduces the reference script to the cent", () => {
  // Reference output: "pool to 12%:  dP=411765 N=2352941 post=11764706
  //                    investor%=0.2000 founder%=0.6800 pool%=0.1200"
  const r = computeDilution(WORKED_EXAMPLE);
  assert.equal(r.outcome, "ok");
  assert.ok(r.shares);
  // The maths file's hand-computed values are 411,764.71 / 2,352,941.18 / 11,764,705.88;
  // the reference prints them rounded to the nearest share.
  assert.equal(Math.round(r.shares!.newPoolShares), 411_765);
  assert.equal(Math.round(r.shares!.investorShares), 2_352_941);
  assert.equal(Math.round(r.shares!.postMoneyTotal), 11_764_706);
  assert.equal(pct4(r.investorPct!), 20);
  assert.equal(pct4(r.founderPct!), 68);
  assert.equal(pct4(r.poolPct!), 12);
});

test("the investor's share is exactly R / (V_pre + R), whatever the pool target is", () => {
  // This is the TEXTBOOK row, and the reason the page can say the investor's percentage
  // does not move when the pool target does. Swept rather than spot-checked, because the
  // identity is meant to hold for every p.
  for (const pool_target_pct of [0, 1, 5, 12, 15, 25, 40, 60, 79]) {
    const r = computeDilution({ ...WORKED_EXAMPLE, pool_target_pct });
    assert.equal(r.outcome, "ok", `p = ${pool_target_pct}%`);
    // Compared with a tolerance, not exactly: the identity `N/post = R/(V_pre+R)` is exact
    // in algebra, but the two sides reach it through different float operations and differ
    // in the last bit. 1e-12 is far tighter than any percentage a page could print.
    assert.ok(
      Math.abs(r.investorPct! - r.simpleInvestorPct) < 1e-12,
      `p = ${pool_target_pct}%: investor share ${r.investorPct} must equal R/(V_pre+R) ${r.simpleInvestorPct}`,
    );
    assert.equal(pct4(r.investorPct!), 20);
  }
});

test("when the pool is reachable it lands exactly on target", () => {
  // E + dP must equal p * post. If this drifts, the pool target on the page is a lie.
  // Every target below is above the 1,000,000 shares already in the pool, so none of them
  // clamps — the clamping case is its own test further down.
  const r = computeDilution(WORKED_EXAMPLE);
  assert.equal(pct4(r.poolPct!), 12);
  for (const pool_target_pct of [12, 15, 20, 33.3]) {
    const swept = computeDilution({ ...WORKED_EXAMPLE, pool_target_pct });
    assert.equal(swept.shares!.poolClamped, false, `${pool_target_pct}% must not clamp`);
    assert.equal(
      pct4(swept.poolPct!),
      Number(pool_target_pct.toFixed(4)),
      `pool must land on ${pool_target_pct}%`,
    );
  }
});

test("with no pool target the round reduces to the simple formula, and founders lose only the investor's share", () => {
  // Reference output: "no pool change: dP=0 N=2250000 post=11250000 investor%=0.2000 founder%=0.7111"
  const r = computeDilution(BASE);
  assert.equal(r.outcome, "ok");
  assert.equal(r.shares!.newPoolShares, 0);
  assert.equal(Math.round(r.shares!.investorShares), 2_250_000);
  assert.equal(Math.round(r.shares!.postMoneyTotal), 11_250_000);
  assert.equal(pct4(r.founderPct!), 71.1111);
});

test("the headline gap is real: the pool costs the founders more than the investor does", () => {
  // 20 points to the investor, 32 to the founders. The page prints both numbers.
  const r = computeDilution(WORKED_EXAMPLE);
  const lostPoints = (1 - r.founderPct!) * 100;
  assert.equal(Number(lostPoints.toFixed(2)), 32);
  assert.ok(
    lostPoints > r.simpleInvestorPct * 100,
    "founder dilution must exceed the naive investor share when a pool is required",
  );
});

test("the multi-round figure is the reference script's own cumulative keep", () => {
  // Reference output: "cumulative keep (0.81*0.82*0.85) = 0.564570 -> cumulative dilution = 0.4354"
  assert.equal(Number(CUMULATIVE_KEEP_2025.toFixed(6)), 0.56457);
  assert.equal(Number((1 - CUMULATIVE_KEEP_2025).toFixed(4)), 0.4354);
});

/* ------------------------------------------------------------------ the edge-case table */

test("a negative pre-money valuation is rejected outright", () => {
  const r = computeDilution({ ...BASE, pre_money_valuation: -1_000_000 });
  assert.equal(r.outcome, "invalid");
  assert.equal(r.shares, null);
  assert.equal(r.founderPct, null);
});

test("a negative raise, negative share counts and a pool target outside [0, 100) are rejected", () => {
  assert.equal(computeDilution({ ...BASE, raise_amount: -1 }).outcome, "invalid");
  assert.equal(computeDilution({ ...BASE, founder_shares: -1 }).outcome, "invalid");
  assert.equal(computeDilution({ ...BASE, existing_pool_shares: -1 }).outcome, "invalid");
  assert.equal(computeDilution({ ...BASE, pool_target_pct: 100 }).outcome, "invalid");
  assert.equal(computeDilution({ ...BASE, pool_target_pct: 120 }).outcome, "invalid");
});

test("a zero pre-money with money coming in is SHOWN as 100%, not refused, with a warning", () => {
  // The maths file asks for exactly this: "Show 100% and a warning."
  const r = computeDilution({ ...BASE, pre_money_valuation: 0, raise_amount: 2_000_000 });
  assert.equal(r.outcome, "ok");
  assert.equal(r.investorPct, 1);
  assert.equal(r.founderPct, 0);
  assert.equal(r.shares, null, "there is no price per share at a zero valuation");
  assert.equal(r.notes.length, 1);
  assert.match(r.notes[0], /buys 100% of the company/);
});

test("a zero pre-money with nothing raised is refused rather than divided by zero", () => {
  // Row 1's real condition: the denominator V_pre + R must be positive.
  const r = computeDilution({ ...BASE, pre_money_valuation: 0, raise_amount: 0 });
  assert.equal(r.outcome, "invalid");
  assert.equal(r.shares, null);
});

test("no shares at all is refused: there is no price per share", () => {
  const r = computeDilution({ ...BASE, founder_shares: 0, existing_pool_shares: 0 });
  assert.equal(r.outcome, "invalid");
  assert.match(r.reason!, /shares outstanding/);
});

test("a pool target the raise cannot reach is 'unreachable', never a negative share count", () => {
  // The maths file's own example: p = 0.90, k = 1.25 -> p*k = 1.1250.
  const r = computeDilution({ ...WORKED_EXAMPLE, pool_target_pct: 90 });
  assert.equal(r.outcome, "unreachable");
  assert.equal(r.shares, null);
  assert.match(r.reason!, /unreachable at this raise size/i);
  // The boundary itself is also no solution: p*k = 1 makes the denominator zero.
  assert.equal(computeDilution({ ...WORKED_EXAMPLE, pool_target_pct: 80 }).outcome, "unreachable");
});

test("a pool already above target clamps to zero and says so, rather than cancelling options", () => {
  // The maths file: "Verified: p=0.05 -> dP = 0.00".
  const r = computeDilution({ ...WORKED_EXAMPLE, pool_target_pct: 5 });
  assert.equal(r.outcome, "ok");
  assert.equal(r.shares!.newPoolShares, 0);
  assert.equal(r.shares!.poolClamped, true);
  assert.ok(r.poolPct! > 0.05, "the pool stays above target, it is not shrunk to it");
  assert.ok(r.notes.some((n) => /already at or above/.test(n)));
});

test("a round that raises nothing changes nothing", () => {
  const r = computeDilution({ ...BASE, raise_amount: 0 });
  assert.equal(r.outcome, "ok");
  assert.equal(r.investorPct, 0);
  assert.equal(r.simpleInvestorPct, 0);
});

test("entering no founder shares is allowed, and flagged", () => {
  // The maths file: "T = E; percentages still compute. Allowed, but flag that there are
  // no founder shares entered."
  const r = computeDilution({ ...BASE, founder_shares: 0 });
  assert.equal(r.outcome, "ok");
  assert.equal(r.founderPct, 0);
  assert.ok(r.notes.some((n) => /No founder shares entered/.test(n)));
});

test("a blank field reads as invalid, not as zero", () => {
  // `Number("")` is 0, which is the trap the page's text-held fields exist to avoid.
  const r = computeDilution({ ...BASE, pre_money_valuation: Number.NaN });
  assert.equal(r.outcome, "invalid");
});

/* ---------------------------------------------------------------------- never a bad float */

test("no input produces Infinity, NaN or a negative share count", () => {
  const valuations = [0, 1, 500_000, 8_000_000];
  const raises = [0, 1, 250_000, 2_000_000];
  const targets = [0, 1, 12, 49, 79];
  for (const pre_money_valuation of valuations) {
    for (const raise_amount of raises) {
      for (const pool_target_pct of targets) {
        const r = computeDilution({ ...BASE, pre_money_valuation, raise_amount, pool_target_pct });
        const label = `${pre_money_valuation}/${raise_amount}/${pool_target_pct}`;
        if (r.outcome === "ok") {
          for (const value of [r.founderPct!, r.poolPct!, r.investorPct!]) {
            assert.ok(Number.isFinite(value), `non-finite percentage from ${label}`);
            assert.ok(value >= 0 && value <= 1, `percentage outside [0,1] from ${label}`);
          }
          // A zero pre-money is `ok` with no share model — there is no price per share —
          // so the share-count checks only apply when there is one.
          if (r.shares) {
            for (const key of [
              "newPoolShares",
              "investorShares",
              "postMoneyTotal",
              "pricePerShare",
            ] as const) {
              const value = r.shares[key];
              assert.ok(Number.isFinite(value), `non-finite ${key} from ${label}`);
              assert.ok(value >= 0, `negative ${key} from ${label}`);
            }
            for (const key of ["newPoolShares", "investorShares", "postMoneyTotal"] as const) {
              assert.ok(!Object.is(r.shares[key], -0), `negative zero for ${key} from ${label}`);
            }
          }
        } else {
          assert.ok(r.reason, `a ${r.outcome} result must carry its reason (${label})`);
          assert.equal(r.shares, null, `${label} must not print a share model`);
        }
      }
    }
  }
});

/* ---------------------------------------------------------------------- structural checks */

const app = readFileSync("client/src/App.tsx", "utf8");
const sitemapGenerator = readFileSync("scripts/generate-sitemap.ts", "utf8");
const sitemap = readFileSync("client/public/sitemap.xml", "utf8");
const page = readFileSync("client/src/pages/dilution.tsx", "utf8");
const seoPrerender = readFileSync("server/seo-prerender.ts", "utf8");

test("App.tsx registers /tools/dilution and lazy-imports the page", () => {
  assert.match(app, /<Route path="\/tools\/dilution">/);
  assert.match(app, /lazy\(\(\) => import\("@\/pages\/dilution"\)\)/);
});

test("the route is declared in PUBLIC_ROUTES, which is the second edit a page needs", () => {
  assert.match(sitemapGenerator, /path: "\/tools\/dilution"/);
});

test("the committed sitemap carries the new loc, so the page is not shipped invisible", () => {
  assert.match(sitemap, /<loc>https:\/\/founderconsole\.ai\/tools\/dilution<\/loc>/);
});

test("the route is server-rendered, so a crawler does not get the homepage canonical", () => {
  // The third edit, and the one that is easy to forget: `injectSEO` returns the shell
  // untouched for a path it does not know, and that shell is `index, follow` with the
  // homepage canonical — so an unmapped growth page ships as a soft duplicate of `/`.
  assert.match(seoPrerender, /path === "\/tools\/dilution"/);
  assert.match(seoPrerender, /canonical: SITE_URL \+ "\/tools\/dilution"/);
  assert.match(seoPrerender, /function buildDilutionBodyContent\(\): string \{/);
  assert.match(seoPrerender, /bodyContent: buildDilutionBodyContent\(\)/);
});

test("the server-rendered text carries the formula, the choice and a signup link", () => {
  const body = seoPrerender.slice(seoPrerender.indexOf("function buildDilutionBodyContent"));
  assert.match(body, /amount raised divided by the post-money valuation/);
  assert.match(body, /option pool/i);
  assert.match(body, /dilutes existing holders and never the new investor/);
  assert.match(body, /href="\/signup"/);
});

test("the page ends in the same signup CTA as /tools/runway-calculator", () => {
  assert.match(page, /href="\/signup"/);
  assert.match(page, /data-testid="button-cta-connect"/);
  assert.match(page, /location: "dilution"/);
});

test("the page states each CHOICE in one line, as the brief requires", () => {
  // Tool 2's two choices, each visible to a reader rather than only in a comment.
  assert.match(page, /the pool top-up is created before the money goes in/);
  assert.match(page, /The pool target is a share of post-money, and the top-up never shrinks/);
});

test("the page names the number that matters: founder points lost, not the investor's share", () => {
  assert.match(page, /data-testid="text-dil-founder-pct"/);
  assert.match(page, /data-testid="text-dil-headline"/);
  // Matched as the source writes it: the sentence wraps across two JSX lines, so a
  // regex spanning the break would fail on a purely cosmetic re-wrap.
  assert.match(page, /actually give up/);
  assert.match(page, /points\(result\.simpleInvestorPct\)/);
});

test("the page quotes no benchmark number it has not attributed", () => {
  assert.match(page, /quant-forge-tools-maths\.md/);
  assert.match(page, /quant-benchmarks\.md/);
});
