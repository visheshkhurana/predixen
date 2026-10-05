// Growth E4: lead form view → capture. lead_captured already fires on submit
// through trackFunnel (PostHog + GA4 + X). The view must be PostHog-only, once
// per mount, and only after the form is actually on screen.
//
// Run: npx tsx server/tests/lead-form-viewed.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  createViewedOnceController,
  observeViewedOnce,
  VIEWED_ONCE_THRESHOLD,
} from "../../client/src/hooks/viewed-once";

const runway = readFileSync("client/src/pages/runway-calculator.tsx", "utf8");
const survival = readFileSync("client/src/pages/survival-simulator.tsx", "utf8");
const hook = readFileSync("client/src/hooks/use-viewed-once.ts", "utf8");
const observer = readFileSync("client/src/hooks/viewed-once.ts", "utf8");

type FakeEntry = { isIntersecting: boolean; intersectionRatio: number; target: unknown };

class FakeIntersectionObserver {
  static instances: FakeIntersectionObserver[] = [];
  callback: (entries: FakeEntry[]) => void;
  threshold: number | number[];
  observed: unknown[] = [];
  disconnected = false;
  constructor(callback: (entries: FakeEntry[]) => void, options?: { threshold?: number | number[] }) {
    this.callback = callback;
    this.threshold = options?.threshold ?? 0;
    FakeIntersectionObserver.instances.push(this);
  }
  observe(el: unknown) {
    this.observed.push(el);
  }
  disconnect() {
    this.disconnected = true;
  }
  unobserve() {}
  takeRecords() {
    return [];
  }
  emit(ratio: number, isIntersecting = ratio > 0) {
    this.callback([
      { isIntersecting, intersectionRatio: ratio, target: this.observed[0] },
    ]);
  }
}

function withMockObserver(fn: () => void) {
  const previous = globalThis.IntersectionObserver;
  FakeIntersectionObserver.instances = [];
  globalThis.IntersectionObserver = FakeIntersectionObserver as unknown as typeof IntersectionObserver;
  try {
    fn();
  } finally {
    globalThis.IntersectionObserver = previous;
    FakeIntersectionObserver.instances = [];
  }
}

test("both lead forms wire lead_form_viewed with the lead_captured location", () => {
  assert.match(
    runway,
    /useViewedOnce\(\s*"lead_form_viewed",\s*\{\s*location:\s*"runway-calculator",?\s*\}\s*\)/,
  );
  assert.match(
    survival,
    /useViewedOnce\(\s*"lead_form_viewed",\s*\{\s*location:\s*"survival-simulator",?\s*\}\s*\)/,
  );
  assert.match(runway, /import\s*\{\s*useViewedOnce\s*\}\s*from\s*["']@\/hooks\/use-viewed-once["']/);
  assert.match(survival, /import\s*\{\s*useViewedOnce\s*\}\s*from\s*["']@\/hooks\/use-viewed-once["']/);
  assert.match(runway, /<form ref=\{leadFormRef\}/);
  assert.match(survival, /<form ref=\{leadFormRef\}/);

  // Capture stays on trackFunnel. The view must not join that path.
  assert.match(runway, /trackFunnel\(\s*"lead_captured"/);
  assert.match(survival, /trackFunnel\(\s*"lead_captured"/);
  assert.doesNotMatch(runway, /trackFunnel\(\s*"lead_form_viewed"/);
  assert.doesNotMatch(survival, /trackFunnel\(\s*"lead_form_viewed"/);
  assert.match(runway, /location:\s*"runway-calculator"/);
  assert.match(survival, /location:\s*"survival-simulator"/);
});

test("the hook sends the view through trackEvent, not trackFunnel", () => {
  assert.match(hook, /import\s*\{\s*trackEvent\s*\}\s*from\s*["']@\/lib\/posthog["']/);
  assert.match(hook, /emit:\s*trackEvent/);
  assert.doesNotMatch(hook, /trackFunnel\s*\(/);
  assert.doesNotMatch(hook, /from\s*["']@\/lib\/funnel["']/);
  assert.doesNotMatch(hook, /gtag\s*\(/);
  assert.doesNotMatch(hook, /trackXConversion\s*\(/);
  assert.match(observer, /new IntersectionObserver/);
  assert.match(observer, /observer\.disconnect\(\)/);
  assert.match(observer, /typeof IntersectionObserver === ["']undefined["']/);
  assert.equal(VIEWED_ONCE_THRESHOLD, 0.5);
});

test("useViewedOnce fires exactly once when the element intersects repeatedly", () => {
  withMockObserver(() => {
    const seen: { event: string; properties?: Record<string, unknown> }[] = [];
    const el = {} as Element;
    const controller = createViewedOnceController({
      event: "lead_form_viewed",
      getProperties: () => ({ location: "runway-calculator" }),
      emit: (event, properties) => seen.push({ event, properties }),
    });

    controller.ref(el);
    const observer = FakeIntersectionObserver.instances[0];
    assert.ok(observer, "expected an IntersectionObserver");
    assert.equal(observer.threshold, 0.5);
    assert.equal(observer.observed.length, 1);

    observer.emit(0.1);
    observer.emit(0.49);
    observer.emit(0.5, false);
    assert.equal(seen.length, 0, "below the threshold must not count as a view");

    observer.emit(0.5);
    assert.equal(seen.length, 1);
    assert.deepEqual(seen[0], {
      event: "lead_form_viewed",
      properties: { location: "runway-calculator" },
    });
    assert.equal(observer.disconnected, true);

    // Scroll away, back, and a callback that was already queued.
    observer.emit(0);
    observer.emit(1);
    observer.emit(0.8);
    controller.ref(null);
    controller.ref(el);
    const after = FakeIntersectionObserver.instances.at(-1)!;
    after.emit(1);
    assert.equal(seen.length, 1, "a second intersection must not fire again");
    assert.equal(FakeIntersectionObserver.instances.length, 1, "must not re-observe after firing");
  });
});

test("disconnecting before the threshold drops a late callback, then one view still fires", () => {
  withMockObserver(() => {
    const seen: string[] = [];
    const el = {} as Element;
    const controller = createViewedOnceController({
      event: "lead_form_viewed",
      getProperties: () => ({ location: "survival-simulator" }),
      emit: () => seen.push("survival-simulator"),
    });

    controller.ref(el);
    const first = FakeIntersectionObserver.instances[0];
    controller.ref(null);
    first.emit(1);
    assert.equal(seen.length, 0, "a callback after disconnect must not fire");

    controller.ref(el);
    const second = FakeIntersectionObserver.instances[1];
    second.emit(0.2);
    second.emit(0.75);
    second.emit(0.9);
    assert.deepEqual(seen, ["survival-simulator"]);
  });
});

test("two mounts each fire once (viewed → captured stays per page)", () => {
  withMockObserver(() => {
    const seen: string[] = [];
    const make = (location: string) =>
      createViewedOnceController({
        event: "lead_form_viewed",
        getProperties: () => ({ location }),
        emit: (_event, properties) => seen.push(String(properties?.location)),
      });

    const runwayController = make("runway-calculator");
    const survivalController = make("survival-simulator");
    runwayController.ref({} as Element);
    survivalController.ref({} as Element);
    FakeIntersectionObserver.instances[0].emit(1);
    FakeIntersectionObserver.instances[0].emit(1);
    FakeIntersectionObserver.instances[1].emit(1);
    FakeIntersectionObserver.instances[1].emit(0.6);
    assert.deepEqual(seen, ["runway-calculator", "survival-simulator"]);
  });
});

test("missing IntersectionObserver is a no-op", () => {
  const previous = globalThis.IntersectionObserver;
  // @ts-expect-error — simulating a browser that has no IntersectionObserver
  delete globalThis.IntersectionObserver;
  try {
    const seen: string[] = [];
    assert.doesNotThrow(() => {
      const stop = observeViewedOnce({} as Element, () => seen.push("view"));
      stop();
      const controller = createViewedOnceController({
        event: "lead_form_viewed",
        getProperties: () => ({ location: "runway-calculator" }),
        emit: () => seen.push("emit"),
      });
      controller.ref({} as Element);
      controller.disconnect();
    });
    assert.deepEqual(seen, []);
  } finally {
    globalThis.IntersectionObserver = previous;
  }
});
