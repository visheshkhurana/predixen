// Overview top Suggested Action card.
//
// Reuses generateSuggestedActions (no second ranking). Renders one card only
// for a completed non-sample Truth Scan when FEATURE_FLAGS.OVERVIEW_SUGGESTED_ACTION
// is on. The CTA deep-links to /simulate?from=overview_suggested_action.
//
// Run: npx tsx server/tests/overview-suggested-action.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import React from "react";
import { readFileSync } from "fs";
import TestRenderer from "react-test-renderer";
import {
  generateSuggestedActions,
  buildSimulateUrl,
  parseSimulatePrefill,
  attributionFromPrefill,
  OVERVIEW_SUGGESTED_ACTION_FROM,
  TRUTH_SCAN_SIM_SOURCE,
  TRUTH_SCAN_SIM_FROM,
  resolveOverviewSuggestedAction,
} from "../../client/src/lib/truthScanSuggestedActions.ts";

const g = globalThis as any;
g.window = g.window || g;
g.location = g.location || {
  pathname: "/overview",
  search: "",
  hash: "",
  href: "http://localhost/overview",
};
g.history = g.history || {
  state: null,
  pushState() {},
  replaceState() {},
  go() {},
  back() {},
  forward() {},
};
g.addEventListener = g.addEventListener || (() => {});
g.removeEventListener = g.removeEventListener || (() => {});
g.dispatchEvent = g.dispatchEvent || (() => true);
if (!g.sessionStorage) {
  const store = new Map<string, string>();
  g.sessionStorage = {
    getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
    setItem: (k: string, v: string) => store.set(k, v),
    removeItem: (k: string) => store.delete(k),
  };
}

const { OverviewSuggestedActionCard } = await import(
  "../../client/src/components/TruthScanSuggestedActions.tsx"
);

const RED_SCAN = {
  metrics: {
    runway_p50: 4.2,
    runway_sustainable: false,
    burn_multiple: 3.8,
    gross_margin: 48,
    churn_rate_customer: 0.12,
  },
  flags: [] as unknown[],
};

const HEALTHY_SCAN = {
  metrics: {
    runway_p50: 24,
    runway_sustainable: true,
    burn_multiple: 1.1,
    gross_margin: 78,
    churn_rate_customer: 0.03,
  },
  flags: [] as unknown[],
};

type Tracked = { event: string; properties?: Record<string, any> };

function renderCard(
  props: {
    enabled: boolean;
    isSample?: boolean;
    scan: typeof RED_SCAN | null;
    companyId?: number;
  },
  events: Tracked[],
) {
  const track = (event: string, properties?: Record<string, any>) => {
    events.push({ event, properties });
  };
  let renderer!: TestRenderer.ReactTestRenderer;
  TestRenderer.act(() => {
    renderer = TestRenderer.create(
      React.createElement(OverviewSuggestedActionCard, { ...props, track }),
    );
  });
  return renderer;
}

function impressions(events: Tracked[]) {
  return events.filter((e) => e.event === "suggested_action_impression");
}

test("card renders the top action and fires the impression exactly once per view", () => {
  const events: Tracked[] = [];
  const renderer = renderCard(
    { enabled: true, isSample: false, scan: RED_SCAN, companyId: 42 },
    events,
  );

  const card = renderer.root.findByProps({ "data-testid": "card-overview-suggested-action" });
  assert.ok(card);
  const top = generateSuggestedActions(RED_SCAN.metrics, []);
  assert.equal(top[0].id, "action-runway");
  assert.match(JSON.stringify(renderer.toJSON()), /Model Fundraising Round/);

  const seen = impressions(events);
  assert.equal(seen.length, 1);
  assert.deepEqual(seen[0].properties, {
    location: "overview",
    action_id: "action-runway",
    action_type: "runway",
  });

  TestRenderer.act(() => {
    renderer.update(
      React.createElement(OverviewSuggestedActionCard, {
        enabled: true,
        isSample: false,
        scan: { metrics: { ...RED_SCAN.metrics }, flags: [] },
        companyId: 42,
        track: (event: string, properties?: Record<string, any>) => {
          events.push({ event, properties });
        },
      }),
    );
  });
  assert.equal(impressions(events).length, 1, "refetch/rerender must not re-fire the impression");
});

test("renders nothing and does not track when there are no actions", () => {
  const events: Tracked[] = [];
  const renderer = renderCard(
    { enabled: true, isSample: false, scan: HEALTHY_SCAN, companyId: 42 },
    events,
  );
  assert.equal(renderer.toJSON(), null);
  assert.equal(impressions(events).length, 0);
  assert.equal(
    resolveOverviewSuggestedAction({ enabled: true, isSample: false, scan: HEALTHY_SCAN }),
    null,
  );
});

test("renders nothing for sample data (is_sample=true)", () => {
  const events: Tracked[] = [];
  const renderer = renderCard(
    { enabled: true, isSample: true, scan: RED_SCAN, companyId: 42 },
    events,
  );
  assert.equal(renderer.toJSON(), null);
  assert.equal(impressions(events).length, 0);
});

test("renders nothing when the overview flag is off", () => {
  const events: Tracked[] = [];
  const renderer = renderCard(
    { enabled: false, isSample: false, scan: RED_SCAN, companyId: 42 },
    events,
  );
  assert.equal(renderer.toJSON(), null);
  assert.equal(impressions(events).length, 0);
});

test("renders nothing when there is no completed scan", () => {
  const events: Tracked[] = [];
  const renderer = renderCard(
    { enabled: true, isSample: false, scan: null, companyId: 42 },
    events,
  );
  assert.equal(renderer.toJSON(), null);
  assert.equal(impressions(events).length, 0);
});

test("CTA href carries from=overview_suggested_action and the prefill params", () => {
  const events: Tracked[] = [];
  const renderer = renderCard(
    { enabled: true, isSample: false, scan: RED_SCAN, companyId: 42 },
    events,
  );
  const link = renderer.root.findByProps({ "data-testid": "link-overview-suggested-action" });
  const href = String(link.props.href);
  assert.match(href, /^\/simulate\?/);
  const url = new URL(href, "http://localhost");
  assert.equal(url.searchParams.get("from"), "overview_suggested_action");
  assert.equal(url.searchParams.get("action"), "action-runway");
  assert.equal(url.searchParams.get("action_type"), "runway");
  assert.equal(url.searchParams.get("goal"), "balance");
  assert.equal(url.searchParams.get("strategy"), "balance_bridge");
  assert.equal(url.searchParams.get("scenario"), "bridge-round");
  assert.equal(url.searchParams.get("fundraise_month"), "3");
  assert.equal(url.searchParams.get("fundraise_amount"), "500000");
  assert.equal(url.searchParams.get("growth_uplift_pct"), "10");
  assert.equal(url.searchParams.get("company"), "42");

  const prefill = parseSimulatePrefill(url.search);
  assert.ok(prefill);
  assert.equal(prefill.from, OVERVIEW_SUGGESTED_ACTION_FROM);
  assert.equal(prefill.actionId, "action-runway");
  assert.equal(prefill.strategyId, "balance_bridge");
  assert.equal(prefill.params.fundraise_amount, 500000);
  assert.equal(prefill.params.fundraise_month, 3);

  const attr = attributionFromPrefill(prefill);
  assert.equal(attr.source, "overview_suggested_action");
  assert.equal(attr.from, "overview_suggested_action");
  assert.equal(attr.action_id, "action-runway");
  assert.equal(attr.action_type, "runway");

  TestRenderer.act(() => {
    link.props.onClick({ preventDefault() {} });
  });
  const clicks = events.filter((e) => e.event === "cta_click");
  assert.equal(clicks.length, 1);
  assert.equal(clicks[0].properties?.location, "overview_suggested_action");
  assert.equal(clicks[0].properties?.action_id, "action-runway");
  assert.equal(clicks[0].properties?.action_type, "runway");
});

test("truth_scan prefills still parse and keep their source", () => {
  const [action] = generateSuggestedActions({ runway_p50: 5, runway_sustainable: false }, []);
  const url = buildSimulateUrl(action, 7);
  const prefill = parseSimulatePrefill(url.split("?")[1]);
  assert.ok(prefill);
  assert.equal(prefill.from, TRUTH_SCAN_SIM_SOURCE);
  const attr = attributionFromPrefill(prefill);
  assert.equal(attr.source, TRUTH_SCAN_SIM_SOURCE);
  assert.equal(attr.from, TRUTH_SCAN_SIM_FROM);
  assert.doesNotMatch(url, /overview_suggested_action/);
});

test("overview card is gated by its own flag, not the /truth flag", () => {
  const features = readFileSync("client/src/config/features.ts", "utf8");
  const overview = readFileSync("client/src/pages/overview.tsx", "utf8");
  const scenarios = readFileSync("client/src/pages/scenarios.tsx", "utf8");
  const hooks = readFileSync("client/src/api/hooks.ts", "utf8");
  const suggested = readFileSync("client/src/components/TruthScanSuggestedActions.tsx", "utf8");

  assert.match(features, /OVERVIEW_SUGGESTED_ACTION:\s*true/);
  assert.match(overview, /FEATURE_FLAGS\.OVERVIEW_SUGGESTED_ACTION/);
  assert.match(overview, /OverviewSuggestedActionCard/);
  assert.doesNotMatch(overview, /TRUTH_SCAN_SUGGESTED_ACTIONS/);
  assert.match(scenarios, /parseSimulatePrefill\(window\.location\.search\)/);
  assert.doesNotMatch(scenarios, /TRUTH_SCAN_SUGGESTED_ACTIONS/);
  assert.match(scenarios, /OVERVIEW_SUGGESTED_ACTION_FROM/);
  assert.match(hooks, /source: OVERVIEW_SUGGESTED_ACTION_FROM/);
  assert.match(hooks, /trackEvent\(\s*'simulation_started'/);
  assert.match(hooks, /trackEvent\(\s*'simulation_run'/);
  assert.match(hooks, /trackFounderActivated\(\{\s*source: 'simulation'/);
  assert.match(suggested, /location: 'overview'/);
  assert.match(suggested, /location: 'overview_suggested_action'/);
  assert.match(suggested, /track = trackEvent/);
  assert.doesNotMatch(suggested, /trackEvent\(\s*['"]simulation_started['"]/);
});
