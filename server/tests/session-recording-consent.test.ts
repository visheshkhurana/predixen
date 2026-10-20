// Session replay must not record founder books.
//
// Recording is disabled at init. It starts only on a public marketing route
// after localStorage cookie-consent === "accepted", and stopSessionRecording
// runs on the way into the core app. Autocapture stays off so clicked element
// text is not collected. $pageview and named events are unchanged.
//
// The embed widget sends visitors to
// /survival-simulator?cash=&burn=&revenue= — those query strings are stripped
// from PostHog URL properties.
//
// Run: npx tsx --test server/tests/session-recording-consent.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  beforeSendPostHog,
  createRecordingRuntime,
  type RecordingRuntime,
  type SessionRecordingControls,
  setSurface,
  setTrackingSurface,
  surfaceForPath,
  syncSessionRecording,
} from "../../client/src/lib/sessionRecording";

const posthogLib = readFileSync("client/src/lib/posthog.ts", "utf8");
const recordingLib = readFileSync("client/src/lib/sessionRecording.ts", "utf8");
const app = readFileSync("client/src/App.tsx", "utf8");
const embed = readFileSync("client/src/pages/embed-survival.tsx", "utf8");
const runway = readFileSync("client/src/pages/runway-calculator.tsx", "utf8");
const funnel = readFileSync("client/src/lib/funnel.ts", "utf8");
const leadsOptIn = readFileSync("client/src/components/marketing/CalculatorEmailOptIn.tsx", "utf8");

const CORE_ROUTES = [
  "/overview",
  "/simulate",
  "/billing",
  "/settings",
  "/settings/notifications",
  "/copilot",
  "/onboarding",
  "/auth",
  "/auth/callback",
  "/auth/callback?code=oauth-secret",
  "/signup",
  "/login",
  "/register",
  "/dashboard",
  "/admin",
  "/admin/billing",
  "/scenarios/shared/abc",
  "/owner-console",
  "/onboard",
];

function recorder(consent: string | null): {
  calls: string[];
  overrides: unknown[];
  runtime: RecordingRuntime;
  setConsent: (value: string | null) => void;
} {
  const calls: string[] = [];
  const overrides: unknown[] = [];
  let current = consent;
  const client: SessionRecordingControls = {
    startSessionRecording(override?: unknown) {
      calls.push("start");
      overrides.push(override);
    },
    stopSessionRecording() {
      calls.push("stop");
    },
  };
  return {
    calls,
    overrides,
    runtime: createRecordingRuntime(() => current, client),
    setConsent(value: string | null) {
      current = value;
    },
  };
}

test("init disables autocapture and session recording, and masks text", () => {
  assert.match(posthogLib, /autocapture:\s*false/);
  assert.doesNotMatch(posthogLib, /autocapture:\s*true/);
  assert.match(posthogLib, /disable_session_recording:\s*true/);
  assert.doesNotMatch(posthogLib, /disable_session_recording:\s*false/);
  assert.match(posthogLib, /maskAllInputs:\s*true/);
  assert.match(posthogLib, /maskAllText:\s*true/);
  assert.match(posthogLib, /maskTextSelector:\s*["']\*["']/);
  assert.match(posthogLib, /mask_all_text:\s*true/);
  assert.match(posthogLib, /before_send:\s*beforeSendPostHog/);
  assert.match(posthogLib, /syncSessionRecording\(window\.location\.pathname\)/);
  assert.match(recordingLib, /startSessionRecording\?\.\(true\)/);
  assert.match(recordingLib, /stopSessionRecording\?\.\(\)/);
  // Manual pageviews stay manual. Named capture is untouched.
  assert.match(posthogLib, /capture_pageview:\s*false/);
  assert.doesNotMatch(posthogLib, /capture_pageview:\s*true/);
  assert.match(posthogLib, /capture_pageleave:\s*true/);
  assert.match(posthogLib, /capture_exceptions:\s*true/);
});

test("SPA route changes sync recording, and named events are not gated", () => {
  assert.match(app, /syncSessionRecording\(location\)/);
  assert.match(app, /useEffect\(\(\) => \{\s*trackPageView\(location\);/);

  const trackPage = posthogLib.slice(
    posthogLib.indexOf("export function trackPageView"),
    posthogLib.indexOf("export function trackEvent"),
  );
  const trackEvent = posthogLib.slice(posthogLib.indexOf("export function trackEvent"));
  assert.match(trackPage, /event:\s*"\$pageview"/);
  assert.match(trackEvent, /kind:\s*"capture",\s*event,\s*properties/);
  assert.doesNotMatch(trackPage, /cookie-consent|stopSessionRecording|autocapture/);
  assert.doesNotMatch(trackEvent, /cookie-consent|shouldRecordSession|autocapture/);
  assert.doesNotMatch(posthogLib, /founder_activated|lead_captured|calculator_used/);
  assert.match(runway, /calculator_used/);
  assert.match(leadsOptIn, /lead_captured/);
  assert.match(funnel, /posthogTrack\(name/);
});

test("recording starts only on marketing with consent, and stops on core routes", () => {
  const accepted = recorder("accepted");
  for (const path of ["/", "/pricing", "/features", "/blog/runway", "/tools/runway-calculator", "/survival-simulator"]) {
    assert.equal(surfaceForPath(path), "marketing", path);
    assert.equal(syncSessionRecording(path, accepted.runtime), "start", path);
  }
  assert.ok(accepted.calls.every((call) => call === "start"));
  assert.ok(accepted.overrides.every((override) => override === true));

  const onCore = recorder("accepted");
  for (const path of CORE_ROUTES) {
    assert.equal(surfaceForPath(path), "core", path);
    assert.equal(syncSessionRecording(path, onCore.runtime), "stop", path);
  }
  assert.deepEqual(onCore.calls, CORE_ROUTES.map(() => "stop"));
  assert.ok(!onCore.calls.includes("start"));

  // /simulate is the product. /survival-simulator is the public calculator.
  assert.equal(surfaceForPath("/simulate"), "core");
  assert.equal(surfaceForPath("/simulator"), "core");
  assert.equal(surfaceForPath("/simulate-v2"), "core");
  assert.equal(surfaceForPath("/survival-simulator"), "marketing");
  assert.equal(surfaceForPath("/security"), "marketing");
  assert.equal(surfaceForPath("/settings"), "core");
});

test("recording never starts without cookie-consent === accepted", () => {
  for (const consent of [null, "", "declined", "rejected", "Accepted"]) {
    const session = recorder(consent);
    assert.equal(syncSessionRecording("/", session.runtime), "stop");
    assert.equal(syncSessionRecording("/pricing", session.runtime), "stop");
    assert.equal(syncSessionRecording("/overview", session.runtime), "stop");
    assert.equal(setTrackingSurface("marketing", session.runtime), "stop");
    assert.deepEqual(session.calls, ["stop", "stop", "stop", "stop"]);
  }
});

test("marketing -> core -> marketing turns recording on, off, and on again only with consent", () => {
  const accepted = recorder("accepted");
  assert.equal(syncSessionRecording("/pricing", accepted.runtime), "start");
  assert.equal(syncSessionRecording("/overview", accepted.runtime), "stop");
  assert.equal(syncSessionRecording("/blog/how-to-calculate-runway", accepted.runtime), "start");
  assert.deepEqual(accepted.calls, ["start", "stop", "start"]);

  // Same transition through the surface hook #188 can call.
  const viaHook = recorder("accepted");
  assert.equal(setTrackingSurface("marketing", viaHook.runtime), "start");
  assert.equal(setTrackingSurface("core", viaHook.runtime), "stop");
  assert.equal(setSurface("marketing", viaHook.runtime), "start");
  assert.deepEqual(viaHook.calls, ["start", "stop", "start"]);

  const denied = recorder(null);
  assert.equal(syncSessionRecording("/pricing", denied.runtime), "stop");
  assert.equal(syncSessionRecording("/copilot", denied.runtime), "stop");
  assert.equal(syncSessionRecording("/", denied.runtime), "stop");
  assert.equal(setSurface("marketing", denied.runtime), "stop");
  assert.deepEqual(denied.calls, ["stop", "stop", "stop", "stop"]);
  assert.ok(!denied.calls.includes("start"));

  // Consent withdrawn on the way back to marketing does not resume recording.
  const withdrawn = recorder("accepted");
  syncSessionRecording("/features", withdrawn.runtime);
  syncSessionRecording("/billing", withdrawn.runtime);
  withdrawn.setConsent("declined");
  syncSessionRecording("/features", withdrawn.runtime);
  assert.deepEqual(withdrawn.calls, ["start", "stop", "stop"]);
});

test("calculator query strings are stripped from PostHog URL properties", () => {
  // Real leak: the embed CTA puts cash, burn, and revenue on the simulator URL.
  assert.match(embed, /survival-simulator\?cash=\$\{cash\}&burn=\$\{burn\}&revenue=\$\{revenue\}/);

  const leaked = "https://founderconsole.ai/survival-simulator?cash=100000&burn=80000&revenue=20000&utm_source=embed&utm_medium=widget";
  const pageview = beforeSendPostHog({
    event: "$pageview",
    properties: {
      $current_url: leaked,
      $referrer: "https://founderconsole.ai/embed/survival?cash=100000&burn=80000&revenue=20000",
      $pathname: "/survival-simulator",
      path: "/survival-simulator",
    },
  });
  assert.equal(pageview?.event, "$pageview");
  assert.equal(pageview?.properties?.$current_url, "https://founderconsole.ai/survival-simulator");
  assert.equal(pageview?.properties?.$referrer, "https://founderconsole.ai/embed/survival");
  assert.equal(pageview?.properties?.path, "/survival-simulator");

  const example = beforeSendPostHog({
    event: "$pageview",
    properties: {
      $current_url: "https://founderconsole.ai/tools/runway-calculator?runway_months=4&cash=100000",
      $referrer: "https://www.google.com/search?q=startup+runway",
      $session_entry_url: "/tools/dilution?pre=20&post=100",
    },
  });
  assert.equal(
    example?.properties?.$current_url,
    "https://founderconsole.ai/tools/runway-calculator",
  );
  assert.equal(example?.properties?.$referrer, "https://www.google.com/search?q=startup+runway");
  assert.equal(example?.properties?.$session_entry_url, "/tools/dilution");

  const named = beforeSendPostHog({
    event: "calculator_used",
    properties: { calculator: "runway", runway_months: 4, cash: 100000 },
  });
  assert.equal(named?.event, "calculator_used");
  assert.equal(named?.properties?.runway_months, 4);
  assert.equal(named?.properties?.cash, 100000);

  for (const event of ["founder_activated", "lead_captured", "calculator_used"]) {
    const sent = beforeSendPostHog({
      event,
      properties: { source: "test", $current_url: "https://founderconsole.ai/pricing?utm_source=ads" },
    });
    assert.equal(sent?.event, event);
    assert.equal(sent?.properties?.$current_url, "https://founderconsole.ai/pricing?utm_source=ads");
  }

  // Core-app query strings are a different tracking surface; this hook only
  // scrubs calculator pages.
  const core = beforeSendPostHog({
    event: "$pageview",
    properties: { $current_url: "https://founderconsole.ai/overview?company=42" },
  });
  assert.equal(core?.properties?.$current_url, "https://founderconsole.ai/overview?company=42");

  const snapshot = beforeSendPostHog({
    event: "$snapshot",
    properties: {
      $current_url: leaked,
      $snapshot_data: [
        { type: 4, data: { href: leaked, width: 1200, height: 800 } },
        { type: 2, data: { node: { id: 1 } } },
      ],
    },
  });
  assert.equal(snapshot?.event, "$snapshot");
  assert.equal(snapshot?.properties?.$current_url, "https://founderconsole.ai/survival-simulator");
  const frames = snapshot?.properties?.$snapshot_data as { data: { href?: string; node?: unknown } }[];
  assert.equal(frames[0].data.href, "https://founderconsole.ai/survival-simulator");
  assert.equal(frames[0].data.width, 1200);
  assert.deepEqual(frames[1].data.node, { id: 1 });
});
