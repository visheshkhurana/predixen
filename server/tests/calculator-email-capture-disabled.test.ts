// Public calculators hide the lead/email opt-in while POST /api/leads
// (consent true) returns 503. The shared component is the only form, and
// CALCULATOR_EMAIL_CAPTURE_ENABLED is the only switch. Results stay on screen.
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

test("email capture is not rendered and calculator results still are", async () => {
  installDom();

  const optInMod = await import("../../client/src/components/marketing/CalculatorEmailOptIn.tsx");
  assert.equal(optInMod.CALCULATOR_EMAIL_CAPTURE_ENABLED, false);

  let optIn!: TestRenderer.ReactTestRenderer;
  TestRenderer.act(() => {
    optIn = TestRenderer.create(
      React.createElement(optInMod.CalculatorEmailOptIn, {
        source: "runway-calculator",
        sourcePage: "/tools/runway-calculator",
        notes: "Runway 12 months",
        visible: true,
      }),
    );
  });
  assert.equal(optIn.toJSON(), null, "the email capture box must not render");
  assert.throws(() => optIn.root.findByProps({ "data-testid": "input-lead-email" }));
  assert.throws(() => optIn.root.findByProps({ "data-testid": "email-result-panel" }));
  assert.throws(() => optIn.root.findByProps({ "data-testid": "checkbox-lead-consent" }));

  // Every calculator that shows the box does it through this one component,
  // and each still has its result markup. The form test id lives only in the
  // shared component, which rendered nothing above.
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

  const rendered = JSON.stringify(page.toJSON());
  assert.doesNotMatch(rendered, /input-lead-email/);
  assert.doesNotMatch(rendered, /email-result-panel/);
  assert.doesNotMatch(rendered, /checkbox-lead-consent/);
  assert.doesNotMatch(rendered, /section-email-opt-in/);
  assert.doesNotMatch(rendered, /Email me this result/);
});
