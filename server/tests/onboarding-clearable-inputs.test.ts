// Guards the onboarding Number("") snap fix.
//
// Session 01a08122 @ t=50s: Number(e.target.value) on #payroll / #opex /
// #gross-margin in section-manual-inputs snapped a cleared field back to 0.
// Same pattern Conversion Eng shipped on the runway calculator.
//
// Run: npx tsx server/tests/onboarding-clearable-inputs.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "fs";
import { toNumber } from "../../client/src/lib/clearableNumber.ts";

const page = readFileSync("client/src/pages/onboarding.tsx", "utf8");

test("toNumber treats a cleared field as 0 without writing 0 back into the input", () => {
  assert.equal(toNumber(""), 0);
  assert.equal(toNumber("45000"), 45000);
  assert.equal(toNumber("12.5"), 12.5);
  assert.equal(toNumber("."), 0);
  assert.equal(toNumber("abc"), 0);
});

test("onboarding manual optional fields keep string state (no Number() snap)", () => {
  assert.match(page, /data-testid="section-manual-inputs"/);
  assert.match(page, /import \{ toNumber \} from '@\/lib\/clearableNumber'/);
  assert.match(page, /const \[baselineText, setBaselineText\]/);

  // The calculator-era snap: parse on every keystroke so "" becomes 0 and
  // the controlled input refuses to stay empty.
  assert.doesNotMatch(
    page,
    /onChange=\{\(e\) => updateBaseline\(\{ \w+: Number\(e\.target\.value\) \}\)\}/,
  );
  assert.doesNotMatch(page, /onChange=\{\(e\) => updateBaselineText\(\{ \w+: Number\(/);

  // Rage-clicked ids from 01a08122, plus the other optional numeric fields
  // in section-manual-inputs that used the same Number() onChange.
  const fields: Array<{ id: string; key: string }> = [
    { id: "gross-margin", key: "gross_margin_pct" },
    { id: "opex", key: "opex" },
    { id: "payroll", key: "payroll" },
    { id: "revenue", key: "monthly_revenue" },
    { id: "other-costs", key: "other_costs" },
    { id: "cash", key: "cash_balance" },
    { id: "headcount", key: "headcount" },
  ];
  for (const { id, key } of fields) {
    assert.match(page, new RegExp(`id="${id}"`));
    assert.match(
      page,
      new RegExp(`onChange=\\{\\(e\\) => updateBaselineText\\(\\{ ${key}: e\\.target\\.value \\}\\)\\}`),
      `${id} must keep the raw string on change`,
    );
  }
});

test("onboarding still parses to numbers on save, not as the input value", () => {
  assert.match(page, /data: baselineTextToNumbers\(baselineText\)/);
  assert.match(page, /STEPS = \[/);
  assert.match(page, /id: 1, title: 'Welcome'/);
  assert.match(page, /id: 5, title: 'AI Copilot'/);
});
