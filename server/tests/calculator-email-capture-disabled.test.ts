// Public calculators show the lead/email opt-in now that consent-true
// POST /api/leads saves succeed. CALCULATOR_EMAIL_CAPTURE_ENABLED is the
// only switch. Results stay on screen next to the form.
//
// Run: npx tsx server/tests/calculator-email-capture-disabled.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { register } from "node:module";
import React from "react";
import TestRenderer from "react-test-renderer";
import { Router } from "wouter";
import { memoryLocation } from "wouter/memory-location";

// Vite replaces import.meta.env and injects the JSX runtime. Bare Node does
// neither, and metaPixel.ts / xads.ts throw on a missing env object. Same
// stand-in as server/tests/ai-citation-ssr.test.ts.
register(
  "data:text/javascript," +
    encodeURIComponent(`
export async function load(url, context, nextLoad) {
  if (!url.includes("/client/src/")) return nextLoad(url, context);
  const r = await nextLoad(url, context);
  let s = r.source ? r.source.toString() : "";
  if (s.includes("import.meta.env")) {
    s = s.split("import.meta.env").join("(globalThis.__VITE_ENV__||{})");
  }
  // This runner has no browser. Skip the PostHog socket, and on the survival
  // page replace the charts and <Helmet> so the email offer can render.
  if (url.endsWith("/lib/posthog.ts")) {
    s = s.replace('const mod = await import("posthog-js");', "return null;");
  }
  if (url.endsWith("/survival-simulator.tsx")) {
    s = s.replace(
      /import\\s*\\{[^}]*\\}\\s*from\\s*["']recharts["'];/,
      [
        "const ResponsiveContainer = ({ children }) => children ?? null;",
        "const AreaChart = () => null;",
        "const Area = () => null;",
        "const BarChart = () => null;",
        "const Bar = () => null;",
        "const XAxis = () => null;",
        "const YAxis = () => null;",
        "const CartesianGrid = () => null;",
        "const Tooltip = () => null;",
        "const Cell = () => null;",
      ].join("\\n"),
    );
    s = s.replace(
      /import\\s*\\{\\s*Helmet\\s*\\}\\s*from\\s*["']react-helmet-async["'];/,
      "const Helmet = ({ children }) => children ?? null;",
    );
  }
  if (url.endsWith(".tsx") && !/import\\s*(?:\\*\\s*as\\s+)?React\\b/.test(s)) {
    s = 'import React from "react";\\n' + s;
  }
  return { ...r, source: s, format: r.format || "module" };
}
`),
);
(globalThis as any).__VITE_ENV__ = {};

function installDom() {
  const g = globalThis as any;
  g.window = g.window || g;
  g.scrollTo = g.scrollTo || (() => {});
  g.matchMedia =
    g.matchMedia ||
    ((query: string) => ({
      matches: true,
      media: query,
      addEventListener() {},
      removeEventListener() {},
      addListener() {},
      removeListener() {},
      dispatchEvent() {
        return false;
      },
    }));
  if (g.document?.createElement) return;
  const node = () => ({
    style: {},
    setAttribute() {},
    getAttribute() {
      return null;
    },
    appendChild() {},
    removeChild() {},
    remove() {},
    addEventListener() {},
    removeEventListener() {},
    classList: { add() {}, remove() {}, contains() { return false; } },
    className: "",
    type: "",
    text: "",
    async: false,
    src: "",
    ownerDocument: null as unknown,
  });
  const documentMock = {
    title: "",
    documentElement: node(),
    head: { appendChild() {}, removeChild() {} },
    body: { appendChild() {}, removeChild() {} },
    createElement: node,
    querySelector() {
      return null;
    },
    querySelectorAll() {
      return [];
    },
    getElementsByTagName() {
      return [{ parentNode: { insertBefore() {} } }];
    },
  };
  g.document = documentMock;
  if (typeof g.ResizeObserver !== "function") {
    g.ResizeObserver = class {
      observe() {}
      unobserve() {}
      disconnect() {}
    };
  }
  if (!g.location) {
    g.location = {
      origin: "https://founderconsole.ai",
      href: "https://founderconsole.ai/",
      pathname: "/",
      host: "founderconsole.ai",
      assign() {},
      replace() {},
    };
  }
  if (typeof g.HTMLElement !== "function") g.HTMLElement = class HTMLElement {};
  if (typeof g.HTMLFormElement !== "function") {
    g.HTMLFormElement = class HTMLFormElement extends g.HTMLElement {};
  }
  if (typeof g.HTMLInputElement !== "function") {
    g.HTMLInputElement = class HTMLInputElement extends g.HTMLElement {};
  }
}

const PAGES: { file: string; path: string; resultTestId: string }[] = [
  {
    file: "client/src/pages/runway-calculator.tsx",
    path: "/tools/runway-calculator",
    resultTestId: "text-runway-months",
  },
  {
    file: "client/src/pages/survival-simulator.tsx",
    path: "/survival-simulator",
    resultTestId: "results-card",
  },
  {
    file: "client/src/pages/burn-multiple.tsx",
    path: "/tools/burn-multiple",
    resultTestId: "text-bm-multiple",
  },
  {
    file: "client/src/pages/dilution.tsx",
    path: "/tools/dilution",
    resultTestId: "text-dil-founder-pct",
  },
  {
    file: "client/src/pages/ltv-cac.tsx",
    path: "/tools/ltv-cac",
    resultTestId: "text-ltv-ratio",
  },
  {
    file: "client/src/pages/default-alive.tsx",
    path: "/default-alive",
    resultTestId: "text-da-verdict",
  },
];

test("email capture renders alongside calculator results", async () => {
  installDom();

  const optInMod = await import("../../client/src/components/marketing/CalculatorEmailOptIn.tsx");
  assert.equal(optInMod.CALCULATOR_EMAIL_CAPTURE_ENABLED, true);

  let optIn!: TestRenderer.ReactTestRenderer;
  TestRenderer.act(() => {
    optIn = TestRenderer.create(
      React.createElement(
        Router,
        { hook: memoryLocation({ path: "/tools/runway-calculator" }).hook },
        React.createElement(optInMod.CalculatorEmailOptIn, {
          source: "runway-calculator",
          sourcePage: "/tools/runway-calculator",
          notes: "Runway 12 months",
          visible: true,
        }),
      ),
    );
  });
  assert.ok(optIn.root.findByProps({ "data-testid": "input-lead-email" }));
  assert.ok(optIn.root.findByProps({ "data-testid": "email-result-panel" }));
  assert.ok(optIn.root.findByProps({ "data-testid": "checkbox-lead-consent" }));

  // Every calculator that shows the box does it through this one component,
  // and each still has its result markup. The form test id lives only in the
  // shared component, which rendered above.
  for (const page of PAGES) {
    const src = readFileSync(page.file, "utf8");
    assert.match(src, /CalculatorEmailOptIn/, `${page.path} must keep the shared opt-in`);
    assert.match(
      src,
      new RegExp(`data-testid="${page.resultTestId}"`),
      `${page.path} must still render ${page.resultTestId}`,
    );
    assert.doesNotMatch(src, /data-testid="input-lead-email"/);
  }

  const { default: RunwayCalculatorPage } = await import(
    "../../client/src/pages/runway-calculator.tsx"
  );
  let page!: TestRenderer.ReactTestRenderer;
  TestRenderer.act(() => {
    page = TestRenderer.create(
      React.createElement(
        Router,
        { hook: memoryLocation({ path: "/tools/runway-calculator" }).hook },
        React.createElement(RunwayCalculatorPage),
      ),
    );
  });

  const months = page.root.findByProps({ "data-testid": "text-runway-months" });
  const monthsText = months.children.map(String).join("");
  assert.match(monthsText, /^(36\+|\d+)$/, "runway months must still render");
  assert.ok(page.root.findByProps({ "data-testid": "text-runway-date" }));
  assert.ok(page.root.findByProps({ "data-testid": "chart-runway" }));

  assert.ok(page.root.findByProps({ "data-testid": "input-lead-email" }));
  assert.ok(page.root.findByProps({ "data-testid": "section-email-opt-in" }));
  const rendered = JSON.stringify(page.toJSON());
  assert.match(rendered, /input-lead-email/);
  assert.match(rendered, /email-result-panel/);
});

const CALCULATOR_PAGES: {
  path: string;
  file: string;
  load: () => Promise<{ default: React.ComponentType }>;
}[] = [
  {
    path: "/tools/runway-calculator",
    file: "client/src/pages/runway-calculator.tsx",
    load: () => import("../../client/src/pages/runway-calculator.tsx"),
  },
  {
    path: "/survival-simulator",
    file: "client/src/pages/survival-simulator.tsx",
    load: () => import("../../client/src/pages/survival-simulator.tsx"),
  },
  {
    path: "/tools/burn-multiple",
    file: "client/src/pages/burn-multiple.tsx",
    load: () => import("../../client/src/pages/burn-multiple.tsx"),
  },
  {
    path: "/tools/dilution",
    file: "client/src/pages/dilution.tsx",
    load: () => import("../../client/src/pages/dilution.tsx"),
  },
  {
    path: "/tools/ltv-cac",
    file: "client/src/pages/ltv-cac.tsx",
    load: () => import("../../client/src/pages/ltv-cac.tsx"),
  },
  {
    path: "/default-alive",
    file: "client/src/pages/default-alive.tsx",
    load: () => import("../../client/src/pages/default-alive.tsx"),
  },
];

const SURVIVAL_RESULT = {
  simulation_id: "sim-test",
  inputs: {
    cash_on_hand: 500000,
    monthly_revenue: 25000,
    monthly_expenses: 45000,
    growth_rate: 8,
    monthly_churn: 3,
    planned_hires: 2,
    avg_hire_cost: 8000,
    fundraising_month: null,
    fundraising_amount: 0,
  },
  runway: { p10: 8, p50: 14, p90: 22, simple: 25 },
  survival: {
    "6m": 90,
    "12m": 70,
    "18m": 50,
    "24m": 30,
    curve: [{ month: 1, survival_rate: 99 }],
  },
  grade: { letter: "B", label: "Moderate", color: "yellow" },
  histogram: [{ range_start: 0, range_end: 3, count: 10 }],
  burn_trajectory: [{ month: 1, p10: 1, p50: 2, p90: 3 }],
  cash_trajectory: [{ month: 1, p10: 1000, p50: 2000, p90: 3000 }],
  revenue_trajectory: [{ month: 1, p10: 1, p50: 2, p90: 3 }],
  recommendations: [
    {
      priority: "info",
      title: "Hold burn",
      description: "Keep expenses flat.",
      icon: "check-circle",
    },
  ],
  n_simulations: 1000,
  created_at: "2026-10-20T00:00:00Z",
};

test("calculator pages do not promise to email the result", async () => {
  installDom();

  const optIn = readFileSync("client/src/components/marketing/CalculatorEmailOptIn.tsx", "utf8");
  assert.match(optIn, /resultByEmail = false/);
  assert.doesNotMatch(optIn, /resultByEmail = true/);

  const { QueryClient, QueryClientProvider } = await import("@tanstack/react-query");
  const { HelmetProvider } = await import("react-helmet-async");
  const previousFetch = globalThis.fetch;
  globalThis.fetch = (async (input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    if (url.includes("/api/survival-sim/run")) {
      return { ok: true, status: 200, json: async () => SURVIVAL_RESULT };
    }
    return { ok: false, status: 404, json: async () => ({}), text: async () => "" };
  }) as typeof fetch;

  try {
    for (const page of CALCULATOR_PAGES) {
      const src = readFileSync(page.file, "utf8");
      assert.match(src, /resultByEmail=\{false\}/, `${page.path} must pass resultByEmail={false}`);

      const mod = await page.load();
      const client = new QueryClient({
        defaultOptions: {
          queries: { retry: false, gcTime: 0 },
          mutations: { retry: false, gcTime: 0 },
        },
      });
      let tree!: TestRenderer.ReactTestRenderer;
      await TestRenderer.act(async () => {
        tree = TestRenderer.create(
          React.createElement(
            HelmetProvider,
            null,
            React.createElement(
              QueryClientProvider,
              { client },
              React.createElement(
                Router,
                { hook: memoryLocation({ path: page.path }).hook },
                React.createElement(mod.default),
              ),
            ),
          ),
        );
      });

      if (page.path === "/survival-simulator") {
        const button = tree.root.findByProps({ "data-testid": "button-run-simulation" });
        await TestRenderer.act(async () => {
          button.props.onClick();
        });
        for (let i = 0; i < 20; i++) {
          const shown = tree.root.findAllByProps({ "data-testid": "email-result-panel" });
          if (shown.length > 0) break;
          await TestRenderer.act(async () => {
            await new Promise((resolve) => setTimeout(resolve, 0));
          });
        }
      }

      assert.ok(
        tree.root.findAllByProps({ "data-testid": "email-result-panel" }).length > 0,
        `${page.path} must show the opt-in`,
      );
      const rendered = JSON.stringify(tree.toJSON());
      assert.doesNotMatch(rendered, /Email me this result/, `${page.path} must not promise a result email`);
      assert.match(rendered, /keep you posted/, `${page.path} must say it will keep you posted`);
      tree.unmount();
      client.clear();
    }
  } finally {
    globalThis.fetch = previousFetch;
  }
});
