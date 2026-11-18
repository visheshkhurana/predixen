// Tester-reported UX batch: hiring planner follows the company currency, the
// cookie choice persists across subdomains, the goals page saves to a real
// API, the connector page never flashes "0 connectors", and the Health Check
// page has one name in the app.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { hiringMarketFor, localSalary, monthlySalaryFor } from "../../client/src/lib/hiringMarkets";
import { consentCookieDomain, parseConsentCookie } from "../../client/src/lib/consent";

test("an INR company plans hires in rupees for Indian cities, not San Francisco", () => {
  const m = hiringMarketFor("INR");
  assert.equal(m.currency, "INR");
  assert.equal(m.locations[0].label, "Bengaluru");
  assert.ok(!m.locations.some((l) => /San Francisco/.test(l.label)));
  // Senior engineer US band 150-200K -> roughly ₹27L-₹36L a year.
  assert.equal(localSalary(150_000, m), 2_700_000);
  assert.equal(monthlySalaryFor(150_000, 200_000, m, "bengaluru"), Math.round(3_150_000 / 12));
  // Unknown location id falls back to the market's first location.
  assert.equal(monthlySalaryFor(150_000, 200_000, m, "sf"), monthlySalaryFor(150_000, 200_000, m, "bengaluru"));
});

test("USD keeps the US market; AED gets Dubai; unknown currencies fall back to US in USD", () => {
  assert.equal(hiringMarketFor("USD").locations[0].label, "San Francisco");
  assert.equal(hiringMarketFor("usd").currency, "USD");
  assert.equal(hiringMarketFor("AED").locations[0].label, "Dubai");
  const cad = hiringMarketFor("CAD");
  assert.equal(cad.currency, "USD");
  assert.equal(cad.fallback, true);
  assert.equal(hiringMarketFor(null).currency, "USD");
});

test("hiring planner page formats money in the market currency, never a hardcoded $", () => {
  const src = readFileSync("client/src/pages/hiring-planner.tsx", "utf8");
  assert.doesNotMatch(src, /"San Francisco"/);
  assert.doesNotMatch(src, /location: "sf"/);
  assert.doesNotMatch(src, /Equipment \$2K/);
  assert.match(src, /hiringMarketFor\(currentCompany\?\.currency\)/);
  assert.match(src, /formatCurrencyAbbrev\(value, market\.currency\)/);
});

test("consent cookie is shared across the marketing site and the app", () => {
  assert.equal(consentCookieDomain("app.founderconsole.ai"), ".founderconsole.ai");
  assert.equal(consentCookieDomain("www.founderconsole.ai"), ".founderconsole.ai");
  assert.equal(consentCookieDomain("founderconsole.ai"), ".founderconsole.ai");
  assert.equal(consentCookieDomain("app.example.co.in"), ".example.co.in");
  assert.equal(consentCookieDomain("localhost"), null);
  assert.equal(consentCookieDomain("127.0.0.1"), null);
  assert.equal(consentCookieDomain("my-app.up.railway.app"), null);
  assert.equal(parseConsentCookie("a=1; fc_cookie_consent=accepted; b=2"), "accepted");
  assert.equal(parseConsentCookie("fc_cookie_consent=declined"), "declined");
  assert.equal(parseConsentCookie("fc_cookie_consent=maybe"), null);
  assert.equal(parseConsentCookie(""), null);
});

test("cookie banner sits bottom-left and the head script also reads the cookie", () => {
  const banner = readFileSync("client/src/components/CookieConsent.tsx", "utf8");
  assert.match(banner, /md:left-4 md:right-auto/);
  assert.doesNotMatch(banner, /md:right-5/);
  const html = readFileSync("client/index.html", "utf8");
  assert.match(html, /fc_cookie_consent=/);
  const ask = readFileSync("client/src/components/AskAIButton.tsx", "utf8");
  assert.match(ask, /location === "\/copilot"/, "Ask AI button hides on Copilot so it cannot cover the question box");
});

test("goals page saves through the goals API and shows errors", () => {
  const src = readFileSync("client/src/pages/goals.tsx", "utf8");
  assert.match(src, /apiRequest\("POST", `\/api\/companies\/\$\{companyId\}\/goals`/);
  assert.match(src, /Couldn't save goal/);
  const main = readFileSync("server/main.py", "utf8");
  assert.match(main, /app\.include_router\(goals_api\.router\)/);
});

test("connector counts show placeholders until the catalog loads", () => {
  const src = readFileSync("client/src/pages/connector-marketplace.tsx", "utf8");
  assert.match(src, /stat\(connectors\.length\)/);
  assert.match(src, /Loading connectors…/);
  const integ = readFileSync("client/src/pages/integrations.tsx", "utf8");
  assert.match(integ, /data-testid="connectors-loading"/);
});

test("in-app labels call the page Health Check, and Marketplace and Billing are in the sidebar", () => {
  for (const f of [
    "client/src/components/Layout/Stepper.tsx",
    "client/src/components/Breadcrumbs.tsx",
    "client/src/components/PaywallGate.tsx",
    "client/src/components/ContextBar.tsx",
    "client/src/components/TruthScanGate.tsx",
    "client/src/pages/alerts.tsx",
  ]) {
    const src = readFileSync(f, "utf8");
    assert.doesNotMatch(src, /Know Your Truth|['">]Truth Scan|Run Truth Scan|a Truth Scan/, f);
  }
  const sidebar = readFileSync("client/src/components/app-sidebar.tsx", "utf8");
  assert.match(sidebar, /data-testid="nav-marketplace"/);
  assert.match(sidebar, /data-testid="nav-billing"/);
  const docs = readFileSync("client/src/pages/docs.tsx", "utf8");
  assert.doesNotMatch(docs, /Coming Soon<\/Badge>\s*<\/Button>/);
});
