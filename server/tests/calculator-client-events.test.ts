// calculator_used once per page load on the first input change.
// lead_captured is server-only (one per successful /api/leads save).
// The client sends lead_form_submitted with location and host only.
// trackFunnel allow-lists properties before PostHog, gtag, and X.
//
// Run: npx tsx --test server/tests/calculator-client-events.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { publicEventProperties } from "../../client/src/lib/calculator-analytics";
import { createCalculatorUsedController } from "../../client/src/lib/calculator-used";

const optIn = readFileSync("client/src/components/marketing/CalculatorEmailOptIn.tsx", "utf8");
const funnel = readFileSync("client/src/lib/funnel.ts", "utf8");
const leads = readFileSync("server/api/leads.py", "utf8");
const page = (name: string) => readFileSync(`client/src/pages/${name}.tsx`, "utf8");

const CALCULATORS: Record<string, string> = {
  "runway-calculator": "runway",
  "survival-simulator": "survival-simulator",
  "burn-multiple": "burn-multiple",
  dilution: "dilution",
  "ltv-cac": "ltv-cac",
  "default-alive": "default-alive",
};

test("public event properties allow only calculator, location, host, and known enums", () => {
  const safe = publicEventProperties({
    location: " runway-calculator ",
    calculator: "runway",
    host: "founderconsole.ai",
    method: "google",
    source: "truth_scan",
    is_sample: false,
    runway_months: 14,
    grade: "B",
    survival_12m: 62,
    user_id: 7,
    company_id: 3,
    email: "founder@example.com",
    notes: "Cash 500000, founder@example.com",
    distinct_id: "anon",
    name: "Ada",
    leaked: "founder@example.com",
    value: 14,
  });
  assert.deepEqual(safe, {
    location: "runway-calculator",
    calculator: "runway",
    host: "founderconsole.ai",
    method: "google",
    source: "truth_scan",
    is_sample: false,
  });
  assert.equal(JSON.stringify(safe).includes("@"), false);
  assert.equal("runway_months" in safe, false);
  assert.equal("grade" in safe, false);
  assert.equal("survival_12m" in safe, false);
});

test("enum keys reject values outside the known set, and emails never pass", () => {
  const safe = publicEventProperties({
    method: "stripe_checkout",
    source: "runway-calculator",
    calculator: "founder@example.com",
    location: "ada@startup.com",
    host: "founder@example.com",
    is_sample: "false",
    runway_months: "14",
    grade: "A",
  });
  assert.deepEqual(safe, {});
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

test("lead_form_submitted is location and host only, after a successful save", () => {
  const handler = optIn.slice(optIn.indexOf("async function handleEmailResult"), optIn.indexOf("if (!visible)"));
  const failure = handler.indexOf('setSendState("error")');
  const capture = handler.indexOf('trackFunnel("lead_form_submitted"');
  assert.ok(failure !== -1 && capture > failure, "the form event runs after the save failure path");
  assert.match(handler, /if \(!saved\) return/);
  assert.doesNotMatch(handler, /lead_captured/);
  assert.doesNotMatch(handler, /trackExtra/);
  const eventArgs = handler.split('trackFunnel("lead_form_submitted"')[1]?.split("});")[0] ?? "";
  assert.doesNotMatch(eventArgs, /runway_months|grade|survival_12m/);
  assert.match(eventArgs, /location:\s*source/);
  assert.match(eventArgs, /host:\s*window\.location\.host/);
  assert.equal(eventArgs.toLowerCase().includes("email"), false);
  assert.doesNotMatch(optIn, /lead_captured/);
  assert.doesNotMatch(optIn, /trackExtra/);
});

test("exactly one lead_captured per successful save, and it is the server emit", () => {
  const captures = leads.match(/posthog_capture\(\s*"lead_captured"/g) ?? [];
  const queues = leads.match(/add_task\(_emit_lead_captured,/g) ?? [];
  assert.equal(captures.length, 1);
  assert.equal(queues.length, 1);
  const commitAt = leads.indexOf("db.commit()");
  const queueAt = leads.indexOf("background.add_task(_emit_lead_captured,");
  const rollbackAt = leads.indexOf("db.rollback()");
  assert.ok(commitAt !== -1 && queueAt > commitAt, "emit is queued only after commit");
  assert.ok(rollbackAt !== -1 && rollbackAt < queueAt);
  assert.match(leads, /except SQLAlchemyError:[\s\S]*raise HTTPException\(status_code=503/);
  assert.doesNotMatch(optIn, /["']lead_captured["']/);
  for (const file of Object.keys(CALCULATORS)) {
    assert.doesNotMatch(page(file), /["']lead_captured["']/, file);
  }
});

test("trackFunnel allow-lists once, then sends that object to PostHog, gtag, and X", () => {
  const body = funnel.slice(funnel.indexOf("export function trackFunnel"), funnel.indexOf("const FOUNDER_ACTIVATED_KEY"));
  const filterAt = body.indexOf("const safe = publicEventProperties(params)");
  const posthogAt = body.indexOf("posthogTrack(name, safe)");
  const gtagAt = body.indexOf("gtag('event', name, safe)");
  const xAt = body.indexOf("trackXConversion(name, safe)");
  assert.ok(filterAt !== -1 && posthogAt > filterAt && gtagAt > posthogAt && xAt > gtagAt);
  assert.match(body, /try \{[\s\S]*posthogTrack\(name, safe\)/);
  assert.match(body, /try \{[\s\S]*gtag\('event', name, safe\)/);
  assert.match(body, /try \{[\s\S]*trackXConversion\(name, safe\)/);
});
