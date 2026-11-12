// Audit 09-16 finding 17: the What-If explorer turned a -56% gross margin into
// -5600% (`gm > 1 ? gm : gm * 100`) and its slider floor of 30% showed a
// loss-making company as profitable.
import assert from "assert";
import { readFileSync } from "fs";
import { grossMarginSliderMin, normalizeGrossMarginPct } from "../../client/src/lib/finance";

assert.equal(normalizeGrossMarginPct(-56), -56, "percent stays percent");
assert.ok(Math.abs((normalizeGrossMarginPct(-0.56) ?? 0) + 56) < 1e-9, "negative fraction becomes percent");
assert.ok(Math.abs((normalizeGrossMarginPct(0.72) ?? 0) - 72) < 1e-9);
assert.equal(normalizeGrossMarginPct(72), 72);
assert.equal(normalizeGrossMarginPct(null), null);

assert.equal(grossMarginSliderMin(72), 30, "healthy companies keep the old floor");
assert.equal(grossMarginSliderMin(-56), -70, "baseline sits inside the slider range");
assert.equal(grossMarginSliderMin(-500), -200, "never below the server floor");

const src = readFileSync("client/src/components/simulation/WhatIfExplorer.tsx", "utf8");
assert.ok(!/grossMargin > 1 \?/.test(src), "the one-sided fraction check is gone");

console.log("PASS  whatif-gross-margin");
