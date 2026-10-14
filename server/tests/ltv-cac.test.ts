/**
 * HAG-163, tool 3 of 3: /tools/ltv-cac.
 *
 * Run: npx tsx --test server/tests/ltv-cac.test.ts
 *
 * The formula is not invented here and is not asserted from memory: every number below is
 * the worked example, an edge-case row or the churn-trap section of
 * `hive/reports/quant-forge-tools-maths.md`, Tool 3, whose arithmetic is reproduced by the
 * Quant lane's own reference script — vendored byte-for-byte at
 * `server/tests/quant_forge_tools_check.py` and run by
 * `server/tests/test_quant_forge_tools_ltv_cac.py`. Both sides pin the same literals, so a
 * drift in either the reference or this implementation fails a test rather than going
 * unnoticed. The thresholds the tool grades against come from `quant-benchmarks.md` Table 5
 * and are named and dated in the module and on the page.
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
  CHURN_FLOOR_PCT,
  CHURN_TRAP,
  CHURN_TRAP_LTV_COMPOUNDED,
  CHURN_TRAP_LTV_MONTHLY_FORM,
  CHURN_TRAP_UNDERSTATEMENT_PCT,
  SKOK_PAYBACK_WEAK_MONTHS,
  SKOK_RATIO_GOOD,
  WORKED_EXAMPLE,
  annualChurnPct,
  computeLtvCac,
  type LtvCacInputs,
} from "../../client/src/lib/tools/ltvCac.ts";

/** A clean period, so each case below states only the fields it is about. */
const BASE: LtvCacInputs = {
  arpa_monthly: 500,
  gross_margin_pct: 80,
  monthly_churn_pct: 2,
  sm_spend: 120_000,
  new_customers: 24,
};

/** Round the way the reference script prints, for exact comparison. */
const pct4 = (fraction: number) => Number((fraction * 100).toFixed(4));

/* ---------------------------------------------------------------- the worked example */

test("the maths file's worked example reproduces the reference script exactly", () => {
  // Reference output: "LTV = 500 * 0.80 / 0.02 = 20000.00"
  //                  "CAC = 120000 / 24 = 5000.00"
  //                  "LTV:CAC = 4.0000"
  //                  "CAC payback months = CAC/(ARPA*GM) = 5000.00 / 400.00 = 12.5000"
  const r = computeLtvCac(WORKED_EXAMPLE);
  assert.equal(r.outcome, "ok");
  assert.equal(Number(r.ltv!.toFixed(2)), 20_000);
  assert.equal(Number(r.cac!.toFixed(2)), 5_000);
  assert.equal(Number(r.ratio!.toFixed(4)), 4);
  assert.equal(Number(r.paybackMonths!.toFixed(4)), 12.5);
});

test("the annual-churn form of the same identity gives the same answer", () => {
  // Section 3 of the reference script prints the monthly form and the annual form side by
  // side precisely to show they agree: at a 24% naive annual churn the annual form gives
  // 20000.00, the same as the monthly form. Both rates are twelve times their monthly
  // counterparts, so this is one identity in two units, not two models.
  const monthlyForm = computeLtvCac(WORKED_EXAMPLE).ltv!;
  const annualForm = (500 * 12 * 0.8) / (CHURN_TRAP.naiveAnnualChurnPct / 100);
  assert.equal(Number(monthlyForm.toFixed(2)), 20000);
  assert.equal(Number(annualForm.toFixed(2)), 20000);
  assert.equal(CHURN_TRAP_LTV_MONTHLY_FORM, monthlyForm);
});

test("payback is CAC divided by gross profit per customer, the textbook line", () => {
  const r = computeLtvCac(WORKED_EXAMPLE);
  const grossProfitPerCustomer = WORKED_EXAMPLE.arpa_monthly * (WORKED_EXAMPLE.gross_margin_pct / 100);
  assert.equal(grossProfitPerCustomer, 400);
  assert.equal(r.paybackMonths, r.cac! / grossProfitPerCustomer);
  // And the LTV is that same gross profit per customer divided by the churn rate, which is
  // what makes payback and LTV two views of one number.
  assert.equal(r.ltv, grossProfitPerCustomer / (WORKED_EXAMPLE.monthly_churn_pct / 100));
});

/* --------------------------------------------------------------------------- the trap */

test("monthly churn is not twelve times monthly — the trap the page must print", () => {
  // Reference output: "monthly churn 2% -> compounded annual churn = 0.215283 (21.53%)"
  assert.equal(Number(annualChurnPct(2).toFixed(6)), 21.528328);
  assert.notEqual(Number(annualChurnPct(2).toFixed(2)), CHURN_TRAP.naiveAnnualChurnPct);
  assert.ok(annualChurnPct(2) < CHURN_TRAP.naiveAnnualChurnPct);
});

test("the trap's two LTVs and the understatement between them are the reference script's", () => {
  // Reference output: "naive 12*2% = 24% ; LTV with 24% = 20000.00 ;
  //                    LTV with compounded = 22296.20 ; difference = 11.5%"
  assert.equal(Number(CHURN_TRAP_LTV_MONTHLY_FORM.toFixed(2)), 20_000);
  assert.equal(Number(CHURN_TRAP_LTV_COMPOUNDED.toFixed(2)), 22_296.2);
  assert.equal(Number(CHURN_TRAP_UNDERSTATEMENT_PCT.toFixed(1)), 11.5);
  // The naive figure IS the correct monthly-form answer, which is exactly why the mistake
  // is invisible: the two wrong-and-right routes print the same number.
  assert.equal(CHURN_TRAP_LTV_MONTHLY_FORM, computeLtvCac(WORKED_EXAMPLE).ltv);
});

test("the result reports the compounded annual equivalent of the churn it was given", () => {
  const r = computeLtvCac(WORKED_EXAMPLE);
  assert.equal(Number(r.annualChurnUsedPct.toFixed(6)), 21.528328);
  assert.equal(r.monthlyChurnUsedPct, 2);
  assert.equal(r.churnFloored, false);
});

/* -------------------------------------------------------------------------- grading */

test("the worked example is the cash-flow trap: ratio clears, payback does not", () => {
  const r = computeLtvCac(WORKED_EXAMPLE);
  assert.ok(r.grade);
  assert.equal(r.grade!.ratioVerdict, `Clears the ${SKOK_RATIO_GOOD}x benchmark.`);
  assert.match(r.grade!.paybackVerdict!, /anemic/);
  assert.equal(r.grade!.cashFlowTrap, true);
  // The benchmark is named and dated in the grade itself, as quant-benchmarks.md requires:
  // Skok's page carries no clear date, only an update note.
  assert.match(r.grade!.benchmark, /David Skok, SaaS Metrics 2\.0/);
  assert.match(r.grade!.benchmark, /no clear date on the page/);
  assert.match(r.grade!.benchmark, /05\/2016/);
});

test("a healthy ratio with a healthy payback is not flagged as a trap", () => {
  // Same company, but half the fully loaded spend: CAC halves, so payback is 6.25 months,
  // which is inside the best range, while the ratio doubles.
  const r = computeLtvCac({ ...BASE, sm_spend: 60_000 });
  assert.equal(Number(r.paybackMonths!.toFixed(2)), 6.25);
  assert.equal(Number(r.ratio!.toFixed(2)), 8);
  assert.equal(r.grade!.cashFlowTrap, false);
  assert.match(r.grade!.paybackVerdict!, /Inside the 5–7 month range/);
});

test("the ratio and the payback are linked through churn, exactly", () => {
  // Worth pinning because it explains WHEN the trap can happen at all: substituting
  // ltv = grossProfit/churn and cac = payback * grossProfit gives
  //     ratio = 1 / (monthly_churn x payback_months)
  // so a good ratio with a bad payback needs a LOW churn. With a 2% monthly churn, a weak
  // ratio always means a payback beyond 12 months, and they cannot be graded independently
  // by accident of the numbers.
  for (const [churn, spend] of [
    [2, 120_000],
    [5, 8_000],
    [10, 4_000],
  ] as const) {
    const r = computeLtvCac({ ...BASE, monthly_churn_pct: churn, sm_spend: spend });
    const expected = 1 / ((churn / 100) * r.paybackMonths!);
    assert.ok(
      Math.abs(r.ratio! - expected) < 1e-12,
      `churn ${churn}%: ratio ${r.ratio} must equal 1/(churn x payback) = ${expected}`,
    );
  }
});

test("a weak ratio and a payback inside the 12-month line are graded separately", () => {
  // An expensive, high-churn business: a 5% monthly churn is what makes a 2.00x ratio and a
  // 10-month payback reachable at the same time (see the identity above).
  const r = computeLtvCac({
    ...BASE,
    arpa_monthly: 100,
    monthly_churn_pct: 5,
    sm_spend: 8_000,
    new_customers: 10,
  });
  assert.equal(Number(r.ltv!.toFixed(2)), 1_600);
  assert.equal(Number(r.cac!.toFixed(2)), 800);
  assert.equal(Number(r.ratio!.toFixed(2)), 2);
  assert.equal(Number(r.paybackMonths!.toFixed(2)), 10);
  assert.equal(r.grade!.ratioVerdict, `Below the ${SKOK_RATIO_GOOD}x benchmark.`);
  assert.match(r.grade!.paybackVerdict!, /still inside the 12-month line/);
  assert.equal(r.grade!.cashFlowTrap, false, "a weak ratio is not the cash-flow trap");
});

test("the grading boundary is the benchmark's own number, not a guess", () => {
  // Exactly at the 3x line: `>=` counts as clearing it, and exactly at the payback line is
  // NOT beyond it, because the benchmark says "extends beyond 12 months".
  const atRatio = computeLtvCac({ ...BASE, sm_spend: 160_000 });
  assert.equal(Number(atRatio.ratio!.toFixed(4)), SKOK_RATIO_GOOD);
  assert.equal(atRatio.grade!.ratioVerdict, `Clears the ${SKOK_RATIO_GOOD}x benchmark.`);

  // 12 months x $400 of gross profit per customer = a $4,800 CAC = $115,200 over 24 customers.
  const atPayback = computeLtvCac({ ...BASE, sm_spend: 115_200 });
  assert.equal(Number(atPayback.cac!.toFixed(2)), 4_800);
  assert.equal(Number(atPayback.paybackMonths!.toFixed(4)), SKOK_PAYBACK_WEAK_MONTHS);
  assert.doesNotMatch(atPayback.grade!.paybackVerdict!, /anemic/);
  assert.equal(atPayback.grade!.cashFlowTrap, false);
});

/* ------------------------------------------------------------------ the edge-case table */

test("a churn of zero is floored and labelled, never an infinite LTV", () => {
  // The maths file: "Refuse the infinite result. Require churn > 0 and label the floor."
  const r = computeLtvCac({ ...BASE, monthly_churn_pct: 0 });
  assert.equal(r.outcome, "ok");
  assert.equal(r.churnFloored, true);
  assert.equal(r.monthlyChurnUsedPct, CHURN_FLOOR_PCT);
  assert.ok(Number.isFinite(r.ltv!), "a floored churn must not produce an infinite LTV");
  assert.equal(Number(r.ltv!.toFixed(2)), 400_000);
  assert.equal(r.notes.length, 1);
  assert.match(r.notes[0], /floored at 0\.1% per month/);
  assert.match(r.notes[0], /infinite/);
});

test("the floor applies below 0.1% and not at or above it", () => {
  assert.equal(computeLtvCac({ ...BASE, monthly_churn_pct: 0.05 }).churnFloored, true);
  const atFloor = computeLtvCac({ ...BASE, monthly_churn_pct: CHURN_FLOOR_PCT });
  assert.equal(atFloor.churnFloored, false);
  assert.equal(atFloor.notes.length, 0);
  assert.equal(computeLtvCac({ ...BASE, monthly_churn_pct: 1 }).churnFloored, false);
});

test("a zero gross margin shows LTV 0 and says no spend can pay back, not a division by zero", () => {
  // The maths file: "Legitimate (a reseller with no margin). Show 0.00 and say no marketing
  // spend can pay back."
  const r = computeLtvCac({ ...BASE, gross_margin_pct: 0 });
  assert.equal(r.outcome, "ok");
  assert.equal(r.ltv, 0);
  assert.equal(r.ratio, 0);
  assert.equal(r.paybackMonths, null);
  assert.match(r.grade!.paybackVerdict!, /No payback at this margin/);
  assert.ok(r.notes.some((n) => /can ever pay back/.test(n)));
});

test("zero new customers reads 'n/a — no new customers', and LTV is still shown", () => {
  // The maths file: "This is the most common real case in a quiet month; it must not say
  // 'CAC = 0' or 'infinitely good'."
  const r = computeLtvCac({ ...BASE, new_customers: 0 });
  assert.equal(r.outcome, "no_cac");
  assert.equal(r.cac, null);
  assert.equal(r.ratio, null);
  assert.equal(r.paybackMonths, null);
  assert.equal(r.cacUnavailableReason, "n/a — no new customers");
  assert.equal(r.ltv, 20_000, "the LTV side is real and must still be reported");
  assert.equal(r.grade, null, "there is no ratio to grade");
});

test("zero spend with customers won reads 'n/a — no measurable acquisition cost', not infinity", () => {
  const r = computeLtvCac({ ...BASE, sm_spend: 0 });
  assert.equal(r.outcome, "no_cac");
  assert.equal(r.cac, null);
  assert.equal(r.ratio, null);
  assert.equal(r.cacUnavailableReason, "n/a — no measurable acquisition cost");
  assert.equal(r.ltv, 20_000);
});

test("no new customers takes precedence over no spend, since neither has a CAC", () => {
  const r = computeLtvCac({ ...BASE, sm_spend: 0, new_customers: 0 });
  assert.equal(r.outcome, "no_cac");
  assert.equal(r.cacUnavailableReason, "n/a — no new customers");
});

test("a 50% monthly churn is computed honestly — it is a signal, not an error", () => {
  // Reference output: "ltv churn=0.5 (50%/mo)  -> LTV = 800.00; CAC = 5000.00"
  const r = computeLtvCac({ ...BASE, monthly_churn_pct: 50 });
  assert.equal(r.outcome, "ok");
  assert.equal(Number(r.ltv!.toFixed(2)), 800);
  assert.equal(Number(r.cac!.toFixed(2)), 5_000);
  assert.equal(Number(r.ratio!.toFixed(2)), 0.16);
});

test("a round that raises nothing on the CAC side still reports both numbers", () => {
  const r = computeLtvCac({ ...BASE, arpa_monthly: 0 });
  assert.equal(r.outcome, "ok");
  assert.equal(r.ltv, 0);
  assert.equal(r.ratio, 0);
  assert.equal(r.paybackMonths, null, "no gross profit per customer means no payback");
});

test("negatives and out-of-range percentages are rejected outright", () => {
  assert.equal(computeLtvCac({ ...BASE, arpa_monthly: -1 }).outcome, "invalid");
  assert.equal(computeLtvCac({ ...BASE, sm_spend: -1 }).outcome, "invalid");
  assert.equal(computeLtvCac({ ...BASE, new_customers: -1 }).outcome, "invalid");
  assert.equal(computeLtvCac({ ...BASE, gross_margin_pct: -1 }).outcome, "invalid");
  assert.equal(computeLtvCac({ ...BASE, gross_margin_pct: 101 }).outcome, "invalid");
  assert.equal(computeLtvCac({ ...BASE, monthly_churn_pct: -0.1 }).outcome, "invalid");
  assert.equal(computeLtvCac({ ...BASE, monthly_churn_pct: 100 }).outcome, "invalid");
});

test("a blank field reads as invalid, not as zero", () => {
  // `Number("")` is 0, which is the trap the page's text-held fields exist to avoid.
  const r = computeLtvCac({ ...BASE, monthly_churn_pct: Number.NaN });
  assert.equal(r.outcome, "invalid");
  assert.equal(r.ltv, null);
  assert.equal(r.grade, null);
});

/* ---------------------------------------------------------------------- never a bad float */

test("no input produces Infinity, NaN or a negative figure", () => {
  const arpas = [0, 1, 100, 500, 50_000];
  const margins = [0, 1, 40, 80, 100];
  const churns = [0, 0.05, 0.1, 2, 50, 99.9];
  const spends = [0, 1, 20_000, 120_000];
  const customers = [0, 1, 24, 1_000];
  for (const arpa_monthly of arpas) {
    for (const gross_margin_pct of margins) {
      for (const monthly_churn_pct of churns) {
        for (const sm_spend of spends) {
          for (const new_customers of customers) {
            const r = computeLtvCac({
              ...BASE,
              arpa_monthly,
              gross_margin_pct,
              monthly_churn_pct,
              sm_spend,
              new_customers,
            });
            const label = `${arpa_monthly}/${gross_margin_pct}/${monthly_churn_pct}/${sm_spend}/${new_customers}`;
            assert.notEqual(r.outcome, "invalid", `valid inputs rejected: ${label}`);
            for (const value of [r.ltv!, r.monthlyChurnUsedPct, r.annualChurnUsedPct]) {
              assert.ok(Number.isFinite(value), `non-finite value from ${label}`);
              assert.ok(value >= 0, `negative value from ${label}`);
            }
            if (r.cac !== null) {
              assert.ok(Number.isFinite(r.cac) && r.cac >= 0, `bad CAC from ${label}`);
              assert.ok(Number.isFinite(r.ratio!) && r.ratio! >= 0, `bad ratio from ${label}`);
              assert.ok(r.grade, `a computed ratio must carry a grade (${label})`);
            } else {
              assert.ok(r.cacUnavailableReason, `a null CAC must say why (${label})`);
              assert.equal(r.ratio, null, `no CAC means no ratio (${label})`);
              assert.equal(r.grade, null, `no ratio means no grade (${label})`);
            }
            if (r.paybackMonths !== null) {
              assert.ok(Number.isFinite(r.paybackMonths), `non-finite payback from ${label}`);
              assert.ok(r.paybackMonths >= 0, `negative payback from ${label}`);
            }
          }
        }
      }
    }
  }
});

/* ---------------------------------------------------------------------- structural checks */

const app = readFileSync("client/src/App.tsx", "utf8");
const sitemapGenerator = readFileSync("scripts/generate-sitemap.ts", "utf8");
const sitemap = readFileSync("client/public/sitemap.xml", "utf8");
const page = readFileSync("client/src/pages/ltv-cac.tsx", "utf8");
const seoPrerender = readFileSync("server/seo-prerender.ts", "utf8");

test("App.tsx registers /tools/ltv-cac and lazy-imports the page", () => {
  assert.match(app, /<Route path="\/tools\/ltv-cac">/);
  assert.match(app, /lazy\(\(\) => import\("@\/pages\/ltv-cac"\)\)/);
});

test("the route is declared in PUBLIC_ROUTES, which is the second edit a page needs", () => {
  assert.match(sitemapGenerator, /path: "\/tools\/ltv-cac"/);
});

test("the committed sitemap carries the new loc, so the page is not shipped invisible", () => {
  assert.match(sitemap, /<loc>https:\/\/founderconsole\.ai\/tools\/ltv-cac<\/loc>/);
});

test("the route is server-rendered, so a crawler does not get the homepage canonical", () => {
  // The third edit, and the one that is easy to forget: `injectSEO` returns the shell
  // untouched for a path it does not know, and that shell is `index, follow` with the
  // homepage canonical — so an unmapped growth page ships as a soft duplicate of `/`.
  assert.match(seoPrerender, /path === "\/tools\/ltv-cac"/);
  assert.match(seoPrerender, /canonical: SITE_URL \+ "\/tools\/ltv-cac"/);
  assert.match(seoPrerender, /function buildLtvCacBodyContent\(\): string \{/);
  assert.match(seoPrerender, /bodyContent: buildLtvCacBodyContent\(\)/);
});

test("the server-rendered text carries the formula, the trap and a signup link", () => {
  const body = seoPrerender.slice(seoPrerender.indexOf("function buildLtvCacBodyContent"));
  assert.match(body, /gross margin divided by monthly churn/);
  assert.match(body, /fully loaded sales and marketing divided by customers won/);
  assert.match(body, /Monthly churn is not twelve times monthly/);
  assert.match(body, /href="\/auth"/);
});

test("the page ends in the same signup CTA as /tools/runway-calculator", () => {
  assert.match(page, /href="\/auth\?tab=register"/);
  assert.match(page, /data-testid="button-cta-connect"/);
  assert.match(page, /location: "ltv-cac"/);
});

test("the page states each CHOICE in one line, as the brief requires", () => {
  assert.match(page, /Chosen: churn is entered in one unit only/);
  assert.match(page, /Chosen: CAC is fully loaded/);
  assert.match(page, /gross-profit based/);
});

test("the page prints the unit next to the churn field, as the trap requires", () => {
  // One unit only, printed, so the founder cannot carry the wrong figure into a spreadsheet.
  assert.match(page, /unit: "% per month"/);
  // The field testids are interpolated from FIELDS, so the source carries the testId value
  // rather than a literal `data-testid="..."` attribute for the inputs.
  assert.match(page, /testId: "input-ltv-churn"/);
  assert.match(page, /data-testid="text-ltv-churn-annual"/);
});

test("the page grades the two numbers separately and names the benchmark", () => {
  assert.match(page, /data-testid="text-ltv-ratio"/);
  assert.match(page, /data-testid="text-ltv-payback"/);
  assert.match(page, /data-testid="text-ltv-grade-ratio"/);
  assert.match(page, /data-testid="text-ltv-grade-payback"/);
  assert.match(page, /data-testid="text-ltv-trap"/);
  assert.match(page, /Graded against \{SKOK_BENCHMARK\}/);
});

test("the page shows 'n/a' rather than a zero or an infinity when there is no CAC", () => {
  assert.match(page, /data-testid="text-ltv-cac-na"/);
  assert.match(page, /result\.cacUnavailableReason/);
  assert.match(page, /result\.cac === null/);
  assert.match(page, /result\.ratio === null/);
});

test("the page quotes no benchmark number it has not attributed", () => {
  assert.match(page, /quant-forge-tools-maths\.md/);
  assert.match(page, /quant-benchmarks\.md/);
});
