// Cookie consent gates GA4 and the Meta pixel.
//
// The banner stores localStorage["cookie-consent"] but used to be ignored:
// index.html injected gtag.js on every page, and MarketingLayout injected
// fbevents.js on every marketing page. The loader must:
//   - inject neither script before a choice, or after a rejection
//   - inject both as soon as the choice becomes "accepted" on a marketing surface
//   - never inject the pixel on core-app routes, even after accept
//
// Run: npx tsx --test server/tests/consent-tracking.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  COOKIE_CONSENT_EVENT,
  COOKIE_CONSENT_KEY,
  GA4_MEASUREMENT_ID,
  GA4_SCRIPT_SRC,
  META_PIXEL_ID,
  META_PIXEL_SCRIPT_SRC,
  mountConsentTracking,
  type ConsentTracker,
  type ConsentWindow,
} from "../../client/src/lib/consentTracking";
import { metaPageView, metaTrack } from "../../client/src/lib/metaPixel";

type ScriptEl = { src: string; async: boolean; onerror: (() => void) | null };

function createHost(initial: string | null) {
  const scripts: ScriptEl[] = [];
  const listeners = new Map<string, Array<(event?: { key?: string | null }) => void>>();
  let consent = initial;

  const win: ConsentWindow = {
    localStorage: {
      getItem: (key: string) => (key === COOKIE_CONSENT_KEY ? consent : null),
    },
    addEventListener(type, listener) {
      const list = listeners.get(type) ?? [];
      list.push(listener);
      listeners.set(type, list);
    },
  };

  const hostDocument = {
    createElement(_tag: string): ScriptEl {
      return { src: "", async: false, onerror: null };
    },
    head: {
      appendChild(node: unknown) {
        scripts.push(node as ScriptEl);
      },
    },
  };

  function dispatch(type: string, event?: { key?: string | null }) {
    for (const listener of listeners.get(type) ?? []) listener(event);
  }

  return {
    scripts,
    window: win,
    mount(): ConsentTracker {
      return mountConsentTracking({
        window: win,
        document: hostDocument,
        getConsent: () => consent,
      });
    },
    accept() {
      consent = "accepted";
      dispatch(COOKIE_CONSENT_EVENT);
    },
    reject(value = "declined") {
      consent = value;
      dispatch(COOKIE_CONSENT_EVENT);
    },
    fromOtherTab(value: string | null) {
      consent = value;
      dispatch("storage", { key: COOKIE_CONSENT_KEY });
    },
  };
}

function srcs(scripts: ScriptEl[]) {
  return scripts.map((script) => script.src);
}

test("no fbevents or gtag script before consent on a marketing surface", () => {
  const host = createHost(null);
  const tracker = host.mount();
  tracker.setSurface("marketing");

  assert.deepEqual(srcs(host.scripts), []);
  assert.equal(host.window.gtag, undefined);
  assert.equal(host.window.fbq, undefined);
  assert.equal(host.window.__fcConsentMetaPixel, undefined);
});

test("both GA4 and the Meta pixel load immediately when consent is accepted", () => {
  const host = createHost(null);
  const tracker = host.mount();
  tracker.setSurface("marketing");
  assert.equal(host.scripts.length, 0);

  host.accept();

  assert.deepEqual(srcs(host.scripts), [GA4_SCRIPT_SRC, META_PIXEL_SCRIPT_SRC]);
  assert.equal(host.scripts.every((script) => script.async), true);
  assert.equal(typeof host.window.gtag, "function");
  assert.equal(host.window.__fcConsentMetaPixel, true);

  const layer = (host.window.dataLayer ?? []).map((entry) => {
    const args = entry as unknown as { [index: number]: unknown };
    return [args[0], args[1]];
  });
  assert.equal(layer[0][0], "js");
  assert.deepEqual(layer[1], ["config", GA4_MEASUREMENT_ID]);

  const queue = host.window.fbq?.queue ?? [];
  const init = queue[0] as unknown as { [index: number]: unknown };
  const pageView = queue[1] as unknown as { [index: number]: unknown };
  assert.deepEqual([init[0], init[1]], ["init", META_PIXEL_ID]);
  assert.equal(pageView[0], "track");
  assert.equal(pageView[1], "PageView");

  host.accept();
  assert.equal(host.scripts.length, 2, "a second accept must not inject either tag again");
});

test("a cross-tab storage update loads on accept and stays empty on reject", () => {
  const accepted = createHost(null);
  const tracker = accepted.mount();
  tracker.setSurface("marketing");
  accepted.fromOtherTab("accepted");
  assert.deepEqual(srcs(accepted.scripts), [GA4_SCRIPT_SRC, META_PIXEL_SCRIPT_SRC]);

  const rejected = createHost(null);
  rejected.mount().setSurface("marketing");
  rejected.fromOtherTab("declined");
  assert.deepEqual(srcs(rejected.scripts), []);

  const unrelated = createHost("accepted");
  const core = unrelated.mount();
  core.setSurface("core");
  assert.deepEqual(srcs(unrelated.scripts), [GA4_SCRIPT_SRC]);
});

test("nothing loads after reject, including a repeated consent event", () => {
  for (const choice of ["declined", "rejected", ""]) {
    const host = createHost(choice);
    const tracker = host.mount();
    tracker.setSurface("marketing");
    host.reject(choice);
    assert.deepEqual(srcs(host.scripts), [], choice);
    assert.equal(host.window.gtag, undefined, choice);
    assert.equal(host.window.fbq, undefined, choice);
  }

  const later = createHost(null);
  const tracker = later.mount();
  tracker.setSurface("marketing");
  later.reject("declined");
  assert.deepEqual(srcs(later.scripts), []);
});

test("the Meta pixel never loads on core-app routes", () => {
  const accepted = createHost("accepted");
  const tracker = accepted.mount();
  tracker.setSurface("core");
  accepted.accept();

  assert.deepEqual(srcs(accepted.scripts), [GA4_SCRIPT_SRC]);
  assert.equal(accepted.window.fbq, undefined);
  assert.equal(accepted.window.__fcConsentMetaPixel, undefined);

  const implicit = createHost("accepted");
  implicit.mount();
  assert.deepEqual(
    srcs(implicit.scripts),
    [GA4_SCRIPT_SRC],
    "the default surface is the core app, so the pixel stays unloaded",
  );
});

test("meta helpers do not inject fbevents when the consent loader has not", () => {
  const previousWindow = globalThis.window;
  const previousDocument = globalThis.document;
  const scripts: string[] = [];
  const fakeDocument = {
    createElement() {
      return { src: "", async: false };
    },
    head: {
      appendChild(el: { src?: string }) {
        if (el?.src) scripts.push(el.src);
      },
    },
    getElementsByTagName() {
      return [{ parentNode: { insertBefore(el: { src?: string }) { if (el?.src) scripts.push(el.src); } } }];
    },
  };
  Object.assign(globalThis, { window: globalThis, document: fakeDocument });
  try {
    metaPageView();
    metaTrack("CompleteRegistration", { method: "email" });
    metaTrack("Subscribe", { method: "stripe_checkout" });
    assert.deepEqual(scripts, []);
    assert.equal((globalThis as { fbq?: unknown }).fbq, undefined);
  } finally {
    Object.assign(globalThis, { window: previousWindow, document: previousDocument });
  }
});

test("index.html no longer hardcodes GA4, and only the consent loader injects the tags", () => {
  const html = readFileSync("client/index.html", "utf8");
  const layout = readFileSync("client/src/components/marketing/MarketingLayout.tsx", "utf8");
  const pixel = readFileSync("client/src/lib/metaPixel.ts", "utf8");
  const loader = readFileSync("client/src/lib/consentTracking.ts", "utf8");
  const app = readFileSync("client/src/App.tsx", "utf8");
  const banner = readFileSync("client/src/components/CookieConsent.tsx", "utf8");

  assert.doesNotMatch(html, /googletagmanager\.com/);
  assert.doesNotMatch(html, /gtag\/js/);
  assert.doesNotMatch(html, /G-NJKW0TGC4C/);
  assert.doesNotMatch(html, /fbevents/);

  assert.doesNotMatch(layout, /fbevents/);
  assert.doesNotMatch(layout, /872167299140812/);
  assert.match(layout, /setTrackingSurface\(\s*"marketing"\s*\)/);
  assert.match(layout, /return \(\) => setTrackingSurface\(\s*"core"\s*\)/);

  assert.doesNotMatch(pixel, /fbevents/);
  assert.doesNotMatch(pixel, /createElement/);
  assert.match(pixel, /__fcConsentMetaPixel/);

  assert.match(loader, new RegExp(GA4_MEASUREMENT_ID));
  assert.match(loader, new RegExp(META_PIXEL_ID));
  assert.match(loader, /fbevents\.js/);
  assert.match(loader, /gtag\/js/);

  assert.match(app, /installConsentTracking\(\)/);
  assert.match(banner, /COOKIE_CONSENT_EVENT/);
  assert.match(banner, /dispatchEvent/);
});
