// Audit 2026-10-15 (P0 #32): the hiring planner read p50_runway / runway_p50
// while POST /hiring-plans/{id}/simulate returns runway.{p10,p50,p90}, so the
// headline number was always "N/A"; 12-month survival never rendered either.
import assert from "assert";
import { formatRunway, survival12mPct } from "../../client/src/lib/hiringSimResults";

// Shape returned by server/api/hiring_planner.py simulate_hiring_plan.
const apiResponse = {
  runway: { p10: 5.1, p50: 6.5, p90: 8.25 },
  survival: { "6m": 92.4, "12m": 18.0, "18m": 0, "24m": 0 },
};

const p50 = apiResponse.runway?.p50 ?? (apiResponse as any).p50_runway;
assert.equal(formatRunway(p50), "6.5", "headline P50 must come from runway.p50");
assert.equal(formatRunway(apiResponse.runway.p90), "8.3");
assert.equal(formatRunway(undefined), "N/A");
assert.equal(formatRunway(Number.NaN), "N/A");
assert.equal(formatRunway("6.5"), "N/A", "strings are not silently shown as months");

assert.equal(survival12mPct(apiResponse), 18.0, "survival['12m'] is already a percentage");
assert.equal(survival12mPct({ survival: { "12m": 0 } }), 0, "0% survival still renders");
assert.equal(survival12mPct({ survival_probability: 0.42 }), 42, "legacy fraction key");
assert.equal(survival12mPct({}), null);

console.log("PASS  hiring-sim-results");
