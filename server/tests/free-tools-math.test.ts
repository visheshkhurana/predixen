/**
 * Free-tool math and copy fixes (audit 2026-10-18).
 *
 * Run: npx tsx --test server/tests/free-tools-math.test.ts
 *
 * - /tools/runway-calculator showed "36+" months for $0 cash and "$-20000" burn
 *   for a profitable company; /runway/:slug and /embed/survival floored months.
 *   All runway tools now share client/src/lib/tools/runway.ts.
 * - /default-alive called a profitable company with $0 cash "dead", and its
 *   fields snapped to 0 when cleared.
 * - /runway/:slug kept the last industry's inputs on slug change and returned
 *   before its hooks.
 * - /embed/survival's CTA query string was ignored by /survival-simulator.
 * - Landing promised a 30-day trial /pricing does not offer, and "37 one-click
 *   OAuth integrations" (16 are OAuth).
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "fs";
import {
  formatRunway,
  projectRunway,
  runwayVerdict,
  simpleRunway,
} from "../../client/src/lib/tools/runway.ts";
import { computeVerdict } from "../../client/src/lib/tools/defaultAlive.ts";
import { simulatorPrefillFromSearch } from "../../client/src/lib/tools/simulatorPrefill.ts";

const read = (p: string) => readFileSync(p, "utf8");

/* ------------------------------------------------------------------ runway */

test("runway is cash / net burn, one decimal", () => {
  const r = simpleRunway(500_000, 60_000, 24_000);
  assert.equal(r.kind, "months");
  assert.equal(formatRunway(r), "13.9 months");
  assert.equal(formatRunway(r, "mo"), "13.9 mo");
});

test("no cash while burning is 0 months, not 36+", () => {
  assert.equal(formatRunway(simpleRunway(0, 60_000, 20_000)), "0 months");
  assert.equal(formatRunway(projectRunway(0, 60_000, 20_000, 5)), "0 months");
  assert.equal(runwayVerdict(projectRunway(0, 60_000, 20_000, 5)), "Critical");
});

test("revenue covering costs is Profitable, never a negative burn or a month count", () => {
  for (const r of [simpleRunway(0, 20_000, 40_000), projectRunway(0, 20_000, 40_000, 0), projectRunway(100_000, 20_000, 40_000, 5)]) {
    assert.equal(r.kind, "profitable");
    assert.equal(formatRunway(r), "Profitable");
    assert.equal(runwayVerdict(r), "Profitable");
  }
});

test("at 0% growth the calculator's projection equals the simple formula the other tools use", () => {
  for (const [cash, exp, rev] of [
    [500_000, 60_000, 20_000],
    [120_000, 45_000, 5_000],
    [1_000_000, 80_000, 20_000],
    [7_777, 3_000, 1_000],
  ]) {
    const a = simpleRunway(cash, exp, rev);
    const b = projectRunway(cash, exp, rev, 0);
    assert.equal(a.kind, "months");
    assert.equal(b.kind, "months");
    assert.ok(Math.abs((a as { months: number }).months - (b as { months: number }).months) < 1e-9);
    assert.equal(formatRunway(a), formatRunway(b));
  }
});

test("growth extends the projection; cash left at the horizon reads 36+", () => {
  const flat = projectRunway(500_000, 60_000, 20_000, 0);
  const growing = projectRunway(500_000, 60_000, 20_000, 3);
  assert.equal(flat.kind, "months");
  assert.ok(growing.kind !== "months" || growing.months > (flat as { months: number }).months);
  const beyond = projectRunway(10_000_000, 60_000, 20_000, 0);
  assert.equal(beyond.kind, "beyond");
  assert.equal(formatRunway(beyond), "36+ months");
});

test("verdict thresholds match the ones /runway/:slug and /embed/survival always used", () => {
  assert.equal(runwayVerdict(simpleRunway(18 * 10_000, 10_000, 0)), "Healthy");
  assert.equal(runwayVerdict(simpleRunway(12 * 10_000, 10_000, 0)), "Watch");
  assert.equal(runwayVerdict(simpleRunway(6 * 10_000, 10_000, 0)), "Raise soon");
  assert.equal(runwayVerdict(simpleRunway(5 * 10_000, 10_000, 0)), "Critical");
});

test("every runway tool imports the shared formula instead of its own copy", () => {
  for (const page of [
    "client/src/pages/runway-calculator.tsx",
    "client/src/pages/runway-by-industry.tsx",
    "client/src/pages/embed-survival.tsx",
  ]) {
    assert.match(read(page), /from "@\/lib\/tools\/runway"/, page);
  }
  const calc = read("client/src/pages/runway-calculator.tsx");
  // The old display paths.
  assert.doesNotMatch(calc, /runwayMonths === 0\) runwayMonths = 36/);
  assert.match(calc, /function formatNetBurn/);
});

/* ------------------------------------------------------------ default alive */

test("a profitable company with $0 cash is default alive", () => {
  const v = computeVerdict(0, 50_000, 40_000, 0, 0);
  assert.equal(v.alive, true);
  assert.equal(v.profitableMonth, 0);
  assert.equal(v.outOfCashMonth, null);
});

test("burning with $0 cash is dead at month 0", () => {
  const v = computeVerdict(0, 20_000, 40_000, 5, 0);
  assert.equal(v.alive, false);
  assert.equal(v.outOfCashMonth, 0);
});

test("reaching profit while cash remains is alive; running out first is dead", () => {
  // $25K revenue growing 8%/mo against $75K costs crosses into profit around month 15.
  assert.equal(computeVerdict(500_000, 25_000, 75_000, 8, 0).alive, true);
  assert.equal(computeVerdict(100_000, 25_000, 75_000, 8, 0).alive, false);
});

/* --------------------------------------------------------- cleared fields */

test("no free-tool field snaps to 0 when cleared", () => {
  for (const page of [
    "client/src/pages/default-alive.tsx",
    "client/src/pages/runway-by-industry.tsx",
    "client/src/pages/embed-survival.tsx",
  ]) {
    const src = read(page);
    assert.doesNotMatch(src, /set\w+\(Number\(e\.target\.value\)(\s*\|\|\s*0)?\)/, page);
  }
});

/* ------------------------------------------------------- runway by industry */

test("/runway/:slug remounts per slug and has no hook after an early return", () => {
  const src = read("client/src/pages/runway-by-industry.tsx");
  assert.match(src, /<IndustryRunwayCalculator key=\{industry\.slug\}/);
  // The exported page holds no state; the keyed inner component does.
  const page = src.slice(src.indexOf("export default function RunwayByIndustryPage"), src.indexOf("function IndustryRunwayCalculator"));
  assert.doesNotMatch(page, /useState|useMemo|useSEO/);
});

/* ------------------------------------------------------- embed -> simulator */

test("the simulator reads the embed CTA's cash, burn and revenue", () => {
  assert.deepEqual(simulatorPrefillFromSearch("?cash=250000&burn=60000&revenue=15000&utm_source=embed"), {
    cash_on_hand: 250_000,
    monthly_expenses: 60_000,
    monthly_revenue: 15_000,
  });
  assert.deepEqual(simulatorPrefillFromSearch("?cash=abc&burn=-5&revenue="), {});
  assert.match(read("client/src/pages/survival-simulator.tsx"), /simulatorPrefillFromSearch\(window\.location\.search\)/);
  // And the widget still sends those names.
  assert.match(read("client/src/pages/embed-survival.tsx"), /survival-simulator\?cash=\$\{cash\}&burn=\$\{burn\}&revenue=\$\{revenue\}/);
});

/* -------------------------------------------------------------------- copy */

test("no page promises a 30-day trial or a Start Free Trial button", () => {
  for (const page of ["client/src/pages/landing.tsx", "client/src/pages/ai-cfo.tsx"]) {
    const src = read(page);
    assert.doesNotMatch(src, /30-day trial/i, page);
    assert.doesNotMatch(src, /Start Free Trial/, page);
  }
  assert.match(read("client/src/pages/landing.tsx"), /free while in early access/);
});

test("connector copy matches the catalog: 37 connectors, 16 via OAuth", () => {
  const catalog = read("server/api/connector_catalog.py");
  const total = (catalog.match(/^\s+id="/gm) || []).length;
  const oauth = (catalog.match(/auth_type="oauth"/g) || []).length;
  assert.equal(total, 37);
  assert.equal(oauth, 16);
  for (const f of ["client/src/pages/marketing-features.tsx", "server/seo-prerender.ts", "client/src/pages/landing.tsx"]) {
    const src = read(f);
    assert.doesNotMatch(src, /37 (real OAuth2 integrations|integrations with one-click OAuth)/, f);
  }
  assert.match(read("client/src/pages/marketing-features.tsx"), /16 with one-click OAuth/);
});

test("security copy names the cipher the code uses (Fernet), not envelope encryption", () => {
  assert.match(read("server/core/encryption.py"), /from cryptography\.fernet import Fernet/);
  for (const f of ["client/src/pages/faq.tsx", "server/seo-prerender.ts", "client/src/pages/security.tsx"]) {
    const src = read(f);
    assert.doesNotMatch(src, /envelope encryption/i, f);
    assert.match(src, /Fernet \(AES-128-CBC with an HMAC-SHA256 integrity check\)/, f);
  }
});

test("/demo lists tour stops, not timestamps for a video that does not exist", () => {
  const src = read("client/src/pages/demo.tsx");
  assert.doesNotMatch(src, /time: "\d+:\d\d"/);
  assert.match(src, /tourStops/);
});
