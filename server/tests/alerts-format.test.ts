// Audit 2026-10-15 (P0 #43): /alerts crashed for any company under 18 months of
// runway, because server/api/smart_alerts.py sends changePercent: null and the
// page called .toFixed on it. Runway on the metric-health cards rendered as "$12".
import assert from "assert";
import { readFileSync } from "fs";
import {
  formatAlertValue,
  formatMetricChange,
  safeFormat,
} from "../../client/src/lib/alertFormat";

// The runway alert exactly as smart_alerts.py builds it.
const runwayAlert = { currentValue: 11.6, previousValue: null, changePercent: null };
assert.equal(formatMetricChange(runwayAlert.changePercent), null);
assert.equal(formatMetricChange(undefined), null);
assert.equal(formatMetricChange(3.21), "+3.2%");
assert.equal(formatMetricChange(-1), "-1.0%");

const runway = safeFormat((v) => v.toFixed(1));
assert.equal(runway(null), "N/A");
assert.equal(runway(Number.NaN), "N/A");
assert.equal(runway(12.5), "12.5");

assert.equal(formatAlertValue(11.6, "runway_months"), "11.6 mo", "runway is months, not dollars");
assert.equal(formatAlertValue(null, "runway_months"), "N/A");
assert.equal(formatAlertValue(1.8, "burn_multiple"), "1.80x");
assert.equal(formatAlertValue(0.032, "churn_rate"), "3.2%");
assert.equal(formatAlertValue(64980, "net_burn"), "$65.0K");
assert.equal(formatAlertValue(-2016, "net_burn"), "-$2.0K", "negatives keep their scale");
assert.equal(formatAlertValue(815430, "cash_balance"), "$815.4K");

const page = readFileSync("client/src/pages/alerts.tsx", "utf8");
assert.doesNotMatch(page, /changePercent\.toFixed/, "no bare .toFixed on a nullable field");
assert.doesNotMatch(page, /health\.z_score\.toFixed\(2\)\}/, "z_score must be guarded");
assert.match(page, /from "@\/lib\/alertFormat"/);

console.log("PASS  alerts-format");
