// Meta pixel: enabled by a code constant, Lead only after a saved /api/leads
// row, CompleteRegistration only after signup, each event tagged with eventID.
// The pixel never receives an email address.
//
// Run: npx tsx server/tests/meta-pixel.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { register } from "node:module";
import React from "react";
import TestRenderer from "react-test-renderer";
import { Router } from "wouter";
import { memoryLocation } from "wouter/memory-location";
import {
  META_PIXEL_ENABLED,
  META_PIXEL_ID,
  createMetaEventId,
  isMetaPixelEnabled,
  metaPageView,
  metaPixelParams,
  metaTrack,
} from "../../client/src/lib/metaPixel.ts";

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

const EMAIL = "founder@startup.com";

function installDom() {
  const g = globalThis as any;
  g.window = g;
  g.location = { host: "founderconsole.ai", href: "https://founderconsole.ai/tools/runway-calculator" };
  g.localStorage = {
    getItem(key: string) {
      if (String(key).includes("posthog")) return JSON.stringify({ distinct_id: "browser-1" });
      return null;
    },
    setItem() {},
    removeItem() {},
  };
  g.scrollTo = g.scrollTo || (() => {});
  if (g.document?.getElementsByTagName) return;
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
    parentNode: { insertBefore() {} },
    async: false,
    src: "",
  });
  g.document = {
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
}

function fbqCalls(): unknown[][] {
  const fbq = (globalThis as any).fbq;
  const queue = fbq?.queue ?? [];
  return [...queue].map((args: ArrayLike<unknown>) => Array.from(args));
}

function tracks(event: string): unknown[][] {
  return fbqCalls().filter((call) => call[0] === "track" && call[1] === event);
}

function assertNoPii(value: unknown) {
  const blob = JSON.stringify(value);
  assert.equal(blob.includes(EMAIL), false, blob);
  assert.equal(blob.toLowerCase().includes("user_id"), false, blob);
  assert.equal(/distinct_id/.test(blob), false, blob);
}

test("enablement is a code constant set to true", () => {
  const src = readFileSync("client/src/lib/metaPixel.ts", "utf8");
  assert.equal(META_PIXEL_ENABLED, true);
  assert.equal(isMetaPixelEnabled(), true);
  assert.equal(META_PIXEL_ID, "872167299140812");
  assert.match(src, /export const META_PIXEL_ENABLED = true\b/);
  assert.doesNotMatch(src, /isMetaPixelEnabled[\s\S]{0,80}=>\s*false/);
  assert.doesNotMatch(src, /import\.meta\.env/);
  assert.doesNotMatch(src, /VITE_META_PIXEL/);
  assert.match(src, /eventID:\s*eventId/);
});

test("metaTrack sends eventID and strips email and other PII", () => {
  installDom();
  assert.equal(isMetaPixelEnabled(), true);

  const stripped = metaPixelParams({
    email: EMAIL,
    user_id: 42,
    distinct_id: "abc",
    method: "email",
    content_name: "runway-calculator",
  });
  assert.deepEqual(stripped, { method: "email", content_name: "runway-calculator" });
  assert.deepEqual(
    metaPixelParams({ note: `reach me at ${EMAIL}` }),
    {},
  );

  const first = metaTrack("Lead", {
    email: EMAIL,
    user_email: EMAIL,
    user_id: 42,
    content_name: "runway-calculator",
    note: `reach me at ${EMAIL}`,
  });
  const second = metaTrack("CompleteRegistration", { method: "email", phone: "+15551212" });
  const page = metaPageView();

  assert.equal(typeof first, "string");
  assert.equal(typeof second, "string");
  assert.equal(typeof page, "string");
  assert.notEqual(first, second);
  assert.notEqual(second, page);
  assert.match(first!, /^[0-9a-f-]{36}$/i);
  assert.match(createMetaEventId(), /^[0-9a-f-]{36}$/i);

  const init = fbqCalls().find((call) => call[0] === "init");
  assert.deepEqual(init, ["init", META_PIXEL_ID]);

  const lead = tracks("Lead");
  assert.equal(lead.length, 1);
  assert.deepEqual(lead[0][2], { content_name: "runway-calculator" });
  assert.deepEqual(lead[0][3], { eventID: first });
  assertNoPii(lead[0]);

  const signup = tracks("CompleteRegistration");
  assert.equal(signup.length, 1);
  assert.deepEqual(signup[0][2], { method: "email" });
  assert.deepEqual(signup[0][3], { eventID: second });
  assertNoPii(signup[0]);

  const views = tracks("PageView");
  assert.equal(views.length, 1);
  assert.deepEqual(views[0][2], {});
  assert.deepEqual(views[0][3], { eventID: page });
});

test("Lead fires only after /api/leads succeeds, and the pixel has no email", async () => {
  installDom();
  const before = tracks("Lead").length;
  const { CalculatorEmailOptIn } = await import(
    "../../client/src/components/marketing/CalculatorEmailOptIn.tsx"
  );

  let tree!: TestRenderer.ReactTestRenderer;
  await TestRenderer.act(async () => {
    tree = TestRenderer.create(
      React.createElement(
        Router,
        { hook: memoryLocation({ path: "/tools/runway-calculator" }).hook },
        React.createElement(CalculatorEmailOptIn, {
          source: "runway-calculator",
          sourcePage: "/tools/runway-calculator",
          notes: "Runway 12 months",
          visible: true,
        }),
      ),
    );
  });

  const input = tree.root.findByProps({ "data-testid": "input-lead-email" });
  const consent = tree.root.findByProps({ "data-testid": "checkbox-lead-consent" });
  await TestRenderer.act(async () => {
    input.props.onChange({ target: { value: EMAIL } });
    consent.props.onCheckedChange(true);
  });

  const form = tree.root.findByType("form");
  let posts = 0;
  (globalThis as any).fetch = async (url: string, init?: RequestInit) => {
    posts += 1;
    assert.equal(url, "/api/leads");
    const body = JSON.parse(String(init?.body));
    assert.equal(body.email, EMAIL);
    assert.equal(body.consent, true);
    if (posts === 1) return { ok: false, status: 500 };
    return { ok: true, status: 200 };
  };

  await TestRenderer.act(async () => {
    await form.props.onSubmit({ preventDefault() {} });
  });
  assert.equal(posts, 1);
  assert.equal(tracks("Lead").length, before, "a failed save must not fire Lead");

  const formAfterError = tree.root.findByType("form");
  await TestRenderer.act(async () => {
    await formAfterError.props.onSubmit({ preventDefault() {} });
  });
  assert.equal(posts, 2);
  const leads = tracks("Lead");
  assert.equal(leads.length, before + 1);
  const fired = leads[leads.length - 1];
  assert.equal((fired[2] as { content_name?: string }).content_name, "runway-calculator");
  assert.match(String((fired[3] as { eventID?: string }).eventID), /^[0-9a-f-]{36}$/i);
  assertNoPii(fired);
  assert.equal(JSON.stringify(fbqCalls()).includes(EMAIL), false);
});

function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    if (name === "node_modules" || name === "dist") continue;
    const path = join(dir, name);
    if (statSync(path).isDirectory()) walk(path, out);
    else if (/\.(ts|tsx)$/.test(name)) out.push(path);
  }
  return out;
}

test("every /api/leads form fires Lead only on the success path", () => {
  const files = walk("client/src").filter((file) => {
    const src = readFileSync(file, "utf8");
    return src.includes('fetch("/api/leads"') || src.includes("fetch('/api/leads'");
  });
  assert.deepEqual(
    files.map((file) => file.replaceAll("\\", "/")),
    ["client/src/components/marketing/CalculatorEmailOptIn.tsx"],
  );
  for (const file of files) {
    const src = readFileSync(file, "utf8");
    const handler = src.slice(src.indexOf("async function handleEmailResult"), src.indexOf("if (!visible)"));
    const ok = handler.indexOf("if (!res.ok)");
    const lead = handler.search(/metaTrack\(\s*["']Lead["']/);
    const catchAt = handler.indexOf("} catch");
    assert.ok(ok !== -1 && lead > ok, `${file} must fire Lead after the response is ok`);
    assert.ok(catchAt === -1 || lead < catchAt, `${file} must not fire Lead from catch`);
    const statement = handler.slice(lead, handler.indexOf(";", lead));
    assert.match(statement, /content_name:\s*source/);
    assert.doesNotMatch(statement, /email/);
    assert.equal((src.match(/metaTrack\(\s*["']Lead["']/g) || []).length, 1);
  }
});

test("signup completion fires CompleteRegistration without the address", () => {
  const auth = readFileSync("client/src/pages/auth.tsx", "utf8");
  const signup = auth.slice(auth.indexOf("const trackSignup"), auth.indexOf("function AnimatedMetric"));
  const call = signup.match(/metaTrack\(\s*['"]CompleteRegistration['"][\s\S]*?\);/)?.[0] ?? "";
  assert.match(call, /\{\s*method\s*\}/);
  assert.doesNotMatch(call, /email/);

  const register = auth.slice(auth.indexOf("const handleRegister"), auth.indexOf("const handleDemoLogin"));
  const saved = register.indexOf("await api.auth.register");
  const tracked = register.indexOf("trackSignup(");
  const catchAt = register.indexOf("} catch");
  assert.ok(saved !== -1 && tracked > saved && tracked < catchAt);

  const demo = auth.slice(auth.indexOf("const handleDemoLogin"), auth.indexOf("const handleSocialLogin"));
  assert.doesNotMatch(demo, /metaTrack|trackSignup|CompleteRegistration/);

  const callback = readFileSync("client/src/pages/auth-callback.tsx", "utf8");
  const pixel = callback.match(/metaTrack\(\s*['"]CompleteRegistration['"][\s\S]*?\);/)?.[0] ?? "";
  assert.match(pixel, /method:\s*['"]google['"]/);
  assert.doesNotMatch(pixel, /email/);
  const after = callback.slice(callback.indexOf(pixel));
  assert.doesNotMatch(after.slice(after.indexOf("} else {")), /metaTrack|CompleteRegistration/);
});

test("marketing layout does not boot a second pixel", () => {
  const layout = readFileSync("client/src/components/marketing/MarketingLayout.tsx", "utf8");
  assert.match(layout, /metaPageView\(\)/);
  assert.doesNotMatch(layout, /fbq\(/);
  assert.doesNotMatch(layout, /connect\.facebook\.net/);
  assert.doesNotMatch(layout, /872167299140812/);
});
