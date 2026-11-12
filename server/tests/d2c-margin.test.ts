// /tools/d2c-contribution-margin: the maths, the published worked example, and
// the prerendered page. The worked example is quoted in the blog posts and in
// llms.txt, so its numbers are pinned here: change the maths and this fails
// before a published figure goes stale.
//
// Run: npx tsx --test server/tests/d2c-margin.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "fs";
import {
  computeD2cMargin,
  D2C_WORKED_EXAMPLE,
  formatInr,
} from "../../client/src/lib/tools/d2cMargin";
import { renderHtmlPage } from "../seo-prerender";
import { TOOL_PAGE_META } from "../../client/src/data/tool-page-meta";

const SHELL = readFileSync("client/index.html", "utf8");
const near = (a: number | null, b: number, eps = 0.01) =>
  assert.ok(a !== null && Math.abs(a - b) < eps, `${a} != ${b}`);

test("worked example: ₹1,200 AOV, 2,000 orders, 18% RTO, 55% COD", () => {
  const r = computeD2cMargin(D2C_WORKED_EXAMPLE);
  assert.equal(r.outcome, "ok");
  near(r.rtoOrders, 360);
  near(r.deliveredOrders, 1640);
  near(r.returnedOrders, 82);
  near(r.keptOrders, 1558);
  near(r.netRevenue, 1869600);
  near(r.cogs, 654360);
  near(r.cm1, 1215240);
  near(r.fulfilment, 230940);
  near(r.paymentCosts, 57680);
  near(r.cm2, 926620);
  near(r.cm3, 326620);
  near(r.cm1Pct, 65.0, 0.05);
  near(r.cm2Pct, 49.56, 0.01);
  near(r.cm3Pct, 17.47, 0.01);
  near(r.cm3PerOrder, 199.16, 0.01);
  near(r.mer, 3.12, 0.01);
  near(r.breakEvenMer, 2.02, 0.01);
  near(r.rtoLogisticsCost, 61200);
});

test("RTO 18% -> 30% cuts CM3 from ₹3.27 L to ₹1.38 L (the RTO post's example)", () => {
  const r = computeD2cMargin({ ...D2C_WORKED_EXAMPLE, rtoPct: 30 });
  near(r.cm3, 138100);
  near(r.netRevenue, 1596000);
  near(r.mer, 2.66, 0.01);
  assert.equal(formatInr(r.cm3), "₹1.38 L");
  assert.equal(formatInr(computeD2cMargin(D2C_WORKED_EXAMPLE).cm3), "₹3.27 L");
});

test("CM3 is exactly zero at the break-even MER", () => {
  const base = computeD2cMargin(D2C_WORKED_EXAMPLE);
  const marketing = base.netRevenue / (base.breakEvenMer as number);
  const r = computeD2cMargin({ ...D2C_WORKED_EXAMPLE, marketing });
  near(r.cm3, 0, 0.001);
});

test("degenerate inputs are invalid or n/a, never Infinity", () => {
  assert.equal(computeD2cMargin({ ...D2C_WORKED_EXAMPLE, rtoPct: 120 }).outcome, "invalid");
  assert.equal(computeD2cMargin({ ...D2C_WORKED_EXAMPLE, aov: -1 }).outcome, "invalid");
  assert.equal(computeD2cMargin({ ...D2C_WORKED_EXAMPLE, aov: Number.NaN }).outcome, "invalid");
  const noMarketing = computeD2cMargin({ ...D2C_WORKED_EXAMPLE, marketing: 0 });
  assert.equal(noMarketing.mer, null);
  const allRto = computeD2cMargin({ ...D2C_WORKED_EXAMPLE, rtoPct: 100 });
  assert.equal(allRto.cm3PerOrder, null);
  assert.equal(allRto.cm1Pct, null);
});

test("₹ formatting uses lakh and crore", () => {
  assert.equal(formatInr(420), "₹420");
  assert.equal(formatInr(61200), "₹61,200");
  assert.equal(formatInr(1869600), "₹18.70 L");
  assert.equal(formatInr(15000000), "₹1.50 Cr");
  assert.equal(formatInr(-326620), "−₹3.27 L");
});

test("the page is prerendered with its own title, canonical, body and JSON-LD", () => {
  const page = renderHtmlPage(SHELL, "/tools/d2c-contribution-margin");
  assert.equal(page.status, 200);
  const meta = TOOL_PAGE_META["/tools/d2c-contribution-margin"];
  assert.ok(page.html.includes(`<title>${meta.title}</title>`));
  assert.match(page.html, /<link rel="canonical" href="https:\/\/founderconsole\.ai\/tools\/d2c-contribution-margin" \/>/);
  assert.match(page.html, /<h1>D2C Contribution Margin Calculator/);
  assert.match(page.html, /CM1/);
  assert.match(page.html, /"@type":"FAQPage"/);
  assert.match(page.html, /"@type":"BreadcrumbList"/);
  assert.doesNotMatch(page.html, /noindex/);
});
