// The dashboard Profit-per-order card: empty, incomplete, or the latest month's CM2/CM3.
import assert from "assert";
import { isGoodsIndustry, latestProfitSummary } from "../../client/src/lib/d2cProfitSummary";

assert.deepEqual(latestProfitSummary([]), { state: "empty" });
assert.deepEqual(latestProfitSummary(undefined), { state: "empty" });
assert.deepEqual(
  latestProfitSummary([{ period: "2026-10-01", unit_economics: null, missing: ["orders_shipped"] }]),
  { state: "incomplete", period: "2026-10" },
);
const s = latestProfitSummary([
  { period: "2026-09-01", unit_economics: { cm2_per_order: 500, cm3_per_order: 200, cm2_pct: 0.4, cm3_pct: 0.16, delivered_orders: 1500 } },
  { period: "2026-10-01", unit_economics: { cm2_per_order: 558.8, cm3_per_order: 264.7, cm2_pct: 0.447, cm3_pct: 0.212, delivered_orders: 1700 } },
  { period: "2026-11-01", unit_economics: null },
]);
assert.equal(s.state, "ready");
if (s.state === "ready") {
  assert.equal(s.period, "2026-10", "latest month that has numbers");
  assert.equal(s.cm2PerOrder, 558.8);
  assert.equal(s.cm3PerOrder, 264.7);
  assert.equal(s.deliveredOrders, 1700);
}
assert.ok(isGoodsIndustry("d2c") && isGoodsIndustry("E-commerce".toLowerCase().replace("-", "")) && isGoodsIndustry("food"));
assert.ok(!isGoodsIndustry("general_saas") && !isGoodsIndustry(null));
console.log("d2c-profit-card: ok");
