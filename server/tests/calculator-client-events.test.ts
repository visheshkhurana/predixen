// Client PostHog: lead_captured after a successful save, calculator_used once
// per page load on the first input change. No email or other PII in properties.
//
// Run: npx tsx --test server/tests/calculator-client-events.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { publicEventProperties } from "../../client/src/lib/calculator-analytics";
import { createCalculatorUsedController } from "../../client/src/lib/calculator-used";

const optIn = readFileSync("client/src/components/marketing/CalculatorEmailOptIn.tsx", "utf8");
const funnel = readFileSync("client/src/lib/funnel.ts", "utf8");
const page = (name: string) => readFileSync(`client/src/pages/${name}.tsx`, "utf8");

const CALCULATORS: Record<string, string> = {
  "runway-calculator": "runway",
  "survival-simulator": "survival-simulator",
  "burn-multiple": "burn-multiple",
  dilution: "dilution",
  "ltv-cac": "ltv-cac",
  "default-alive": "default-alive",
};

test("public event properties keep the calculator name and drop email", () => {
  const safe = publicEventProperties({
    location: "runway-calculator",
    calculator: "runway",
    host: "founderconsole.ai",
    runway_months: 14,
    grade: "B",
    email: "founder@example.com",
    notes: "Cash 500000, founder@example.com",
    distinct_id: "anon",
    name: "Ada",
    leaked: "founder@example.com",
  });
  assert.deepEqual(safe, {
    location: "runway-calculator",
    calculator: "runway",
    host: "founderconsole.ai",
    runway_months: 14,
    grade: "B",
  });
  assert.equal(JSON.stringify(safe).includes("@"), false);
  assert.equal(JSON.stringify(safe).toLowerCase().includes("founder@example.com"), false);
});

test("calculator_used fires once per page load on the first input change", () => {
  const events: Array<[string, Record<string, unknown>]> = [];
  const tracker = createCalculatorUsedController({
    calculator: "burn-multiple",
    emit: (event, properties) => events.push([event, properties]),
  });

  tracker.update(false, false);
  assert.equal(events.length, 0);
  tracker.onInputChange();
  tracker.onInputChange();
  tracker.update(true, true);
  assert.deepEqual(events, [["calculator_used", { calculator: "burn-multiple" }]]);
  assert.equal(JSON.stringify(events).includes("@"), false);
});

test("a calculator name that is an email is not sent", () => {
  const events: string[] = [];
  const tracker = createCalculatorUsedController({
    calculator: "founder@example.com",
    emit: (event) => events.push(event),
  });
  tracker.onInputChange();
  assert.deepEqual(events, []);
});

test("the six calculator pages capture calculator_used on the first input", () => {
  for (const [file, calculator] of Object.entries(CALCULATORS)) {
    const src = page(file);
    assert.match(src, new RegExp(`useCalculatorUsedOnce\\(\\s*"${calculator}"\\s*\\)`), file);
    assert.match(src, /onCalculatorInput/, file);
  }
});

test("lead_captured is sent only after a successful save, without the address", () => {
  const handler = optIn.slice(optIn.indexOf("async function handleEmailResult"), optIn.indexOf("if (!visible)"));
  const failure = handler.indexOf('setSendState("error")');
  const capture = handler.indexOf('trackFunnel("lead_captured"');
  assert.ok(failure !== -1 && capture > failure, "capture runs after the save failure path, so a failed POST does not emit");
  assert.match(handler, /if \(!saved\) return/);
  assert.match(handler, /publicEventProperties\(/);
  assert.match(handler, /host: window\.location\.host/);
  const eventArgs = handler.split('trackFunnel("lead_captured"', 1)[1]?.split("}));", 1)[0] ?? "";
  assert.equal(eventArgs.toLowerCase().includes("email"), false);
  assert.doesNotMatch(eventArgs, /notes/);
});

test("trackFunnel sends PostHog before gtag and strips PII first", () => {
  const body = funnel.slice(funnel.indexOf("export function trackFunnel"), funnel.indexOf("const FOUNDER_ACTIVATED_KEY"));
  const posthogAt = body.indexOf("posthogTrack(name, safe)");
  const gtagAt = body.indexOf("gtag('event', name, safe)");
  assert.ok(posthogAt !== -1 && gtagAt !== -1 && posthogAt < gtagAt);
  assert.match(body, /const safe = publicEventProperties\(params\)/);
  assert.match(body, /try \{[\s\S]*posthogTrack\(name, safe\)/);
  assert.match(body, /try \{[\s\S]*gtag\('event', name, safe\)/);
});
