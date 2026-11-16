// The onboarding Health Check must agree with what the server stores
// (split_cogs_from_entered_costs in server/api/datasets.py), say "not burning"
// for a profitable company, and convert example figures into the chosen currency.
import assert from "assert";
import { exampleAmount, summarizeBaseline } from "../../client/src/lib/onboarding-baseline";

const base = { monthly_revenue: 0, gross_margin_pct: 0, opex: 0, payroll: 0, other_costs: 0, cash_balance: 0 };

// COGS fits inside opex + other: total is what was typed.
let s = summarizeBaseline({ ...base, monthly_revenue: 100_000, gross_margin_pct: 70, opex: 50_000, payroll: 80_000, other_costs: 10_000, cash_balance: 1_200_000 });
assert.equal(s.cogs, 30_000);
assert.equal(s.totalCosts, 140_000);
assert.equal(s.netBurn, 40_000);
assert.equal(s.runwayMonths, 30);
assert.equal(s.notBurning, false);

// D2C, margin implies more COGS than opex + other hold: total rises
// (₹25L revenue, 55% GM -> ₹11.25L COGS vs ₹11L opex+other). Server: 19.25L.
s = summarizeBaseline({ ...base, monthly_revenue: 2_500_000, gross_margin_pct: 55, opex: 900_000, payroll: 800_000, other_costs: 200_000, cash_balance: 30_000_000 });
assert.equal(s.totalCosts, 1_925_000);
assert.equal(s.netBurn, -575_000);
assert.equal(s.runwayMonths, null);
assert.equal(s.notBurning, true);

// Pre-revenue: burn is all costs.
s = summarizeBaseline({ ...base, opex: 5_000, other_costs: 2_000, cash_balance: 70_000 });
assert.equal(s.netBurn, 7_000);
assert.equal(s.runwayMonths, 10);

// Nothing entered: neither burning nor "not burning".
s = summarizeBaseline(base);
assert.equal(s.notBurning, false);
assert.equal(s.runwayMonths, null);

// A margin typed as a fraction means the same as the percentage (server rule).
assert.equal(summarizeBaseline({ ...base, monthly_revenue: 100_000, gross_margin_pct: 0.7, opex: 50_000 }).cogs, 30_000);

// Example figures follow the chosen currency.
assert.equal(exampleAmount(25_000, "USD"), 25_000);
assert.equal(exampleAmount(25_000, "INR"), 2_100_000);
assert.equal(exampleAmount(1_000_000, "INR"), 85_000_000);
assert.equal(exampleAmount(0, "INR"), 0);
assert.equal(exampleAmount(15_000, "XYZ"), 15_000);

console.log("onboarding-baseline: ok");
