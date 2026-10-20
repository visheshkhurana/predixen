// Tokens in the address bar must not reach PostHog or GA4.
//
// $pageview sends window.location.href as $current_url. The SDK also attaches
// $referrer, $initial_current_url, $initial_referrer, $set / $set_once copies,
// and session-replay href. /verify-email, /unsubscribe, /reset-password, and
// /auth/callback put a credential in that query string.
//
// utm_* / fbclid / gclid are campaign properties (PR #186 first-touch). Cleaning
// the URL must leave those properties in place.
//
// Run: npx tsx --test server/tests/posthog-url-token.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  beforeSendPostHog,
  gtagPageFields,
  type PostHogBeforeSendEvent,
} from "../../client/src/lib/analytics-url";

const ATTRIBUTION_KEYS = [
  "utm_source",
  "utm_medium",
  "utm_campaign",
  "utm_content",
  "utm_term",
  "fbclid",
  "gclid",
] as const;

/**
 * PR #186 captureFirstTouch: first query wins for the tab, including a landing
 * that had no parameters. Reimplemented here so this leak fix does not depend
 * on that branch, and so before_send cannot "fix" the leak by deleting utm_*.
 */
function captureFirstTouch(
  storage: Map<string, string>,
  search: string,
): Record<string, string> {
  const existing = storage.get("fc_first_touch_attribution");
  if (existing !== undefined) return JSON.parse(existing) as Record<string, string>;
  const params = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);
  const captured: Record<string, string> = {};
  for (const key of ATTRIBUTION_KEYS) {
    const value = params.get(key);
    if (value) captured[key] = value;
  }
  storage.set("fc_first_touch_attribution", JSON.stringify(captured));
  return captured;
}

function leakyProperties(href: string): Record<string, unknown> {
  const url = new URL(href);
  const pathWithSecret = `${url.pathname}${url.search}${url.hash}`;
  return {
    $current_url: href,
    $referrer: href,
    $initial_referrer: href,
    $initial_current_url: href,
    $session_entry_url: href,
    $pathname: pathWithSecret,
    path: pathWithSecret,
    href,
    $set: {
      $current_url: href,
      $initial_current_url: href,
      utm_source: "newsletter",
    },
    $set_once: {
      $initial_current_url: href,
      $initial_referrer: href,
      $initial_utm_source: "newsletter",
      $initial_pathname: pathWithSecret,
    },
    utm_source: "newsletter",
  };
}

function replayEvent(href: string): PostHogBeforeSendEvent {
  return {
    event: "$snapshot",
    properties: {
      $current_url: href,
      $snapshot_data: [
        { type: 4, data: { href, width: 800, height: 600 } },
        {
          type: 2,
          data: {
            node: {
              type: 2,
              tagName: "a",
              attributes: { href },
              childNodes: [],
            },
          },
        },
      ],
    },
  };
}

function assertNoSecret(value: unknown, needles: string[]) {
  const blob = JSON.stringify(value);
  for (const needle of needles) {
    assert.equal(blob.includes(needle), false, `still contains ${needle}: ${blob}`);
  }
  assert.equal(blob.includes("?"), false, blob);
  assert.equal(blob.includes("#"), false, blob);
}

const TOKEN_PAGES: Array<{ href: string; pathname: string; needles: string[] }> = [
  {
    href: "https://founderconsole.ai/verify-email?token=abc#x",
    pathname: "/verify-email",
    needles: ["token=abc", "token=", "#x"],
  },
  {
    href: "https://founderconsole.ai/unsubscribe?token=abc",
    pathname: "/unsubscribe",
    needles: ["token=abc", "token="],
  },
  {
    href: "https://founderconsole.ai/reset-password?token=abc",
    pathname: "/reset-password",
    needles: ["token=abc", "token="],
  },
  {
    href: "https://founderconsole.ai/auth/callback?code=abc",
    pathname: "/auth/callback",
    needles: ["code=abc", "code="],
  },
];

for (const page of TOKEN_PAGES) {
  test(`before_send strips ${page.pathname} secrets from every URL property`, () => {
    const sent = beforeSendPostHog({
      event: "$pageview",
      properties: leakyProperties(page.href),
    });
    assert.ok(sent);
    assert.equal(sent.event, "$pageview");
    assert.equal(sent.properties?.$current_url, `https://founderconsole.ai${page.pathname}`);
    assert.equal(sent.properties?.utm_source, "newsletter");
    assert.equal((sent.properties?.$set as { utm_source?: string }).utm_source, "newsletter");
    assert.equal(
      (sent.properties?.$set_once as { $initial_utm_source?: string }).$initial_utm_source,
      "newsletter",
    );
    assertNoSecret(sent.properties, page.needles);

    const snapshot = beforeSendPostHog(replayEvent(page.href));
    assert.ok(snapshot);
    assert.equal(snapshot.event, "$snapshot");
    assertNoSecret(snapshot.properties, page.needles);
  });
}

test("landing on /?utm_source=x keeps the property and #186 first-touch", () => {
  const storage = new Map<string, string>();
  const landing = "https://founderconsole.ai/?utm_source=x#hero";
  const first = captureFirstTouch(storage, new URL(landing).search);
  const second = captureFirstTouch(storage, "?utm_source=later&token=abc");
  assert.equal(first.utm_source, "x");
  assert.equal(second.utm_source, "x");
  assert.equal(second.utm_medium, undefined);

  const sent = beforeSendPostHog({
    event: "$pageview",
    properties: {
      $current_url: "https://founderconsole.ai/verify-email?token=abc#x",
      $referrer: landing,
      $initial_current_url: landing,
      $initial_referrer: "https://ads.example/click?utm_source=x&gclid=click#ad",
      ...first,
      gclid: "click",
      $set: {
        utm_source: first.utm_source,
        $current_url: landing,
      },
      $set_once: {
        $initial_utm_source: "x",
        $initial_current_url: landing,
        $initial_referrer: "https://ads.example/click?utm_source=x",
      },
    },
  });

  assert.ok(sent);
  assert.equal(sent.event, "$pageview");
  assert.equal(sent.properties?.$current_url, "https://founderconsole.ai/verify-email");
  assert.equal(sent.properties?.utm_source, "x");
  assert.equal(sent.properties?.gclid, "click");
  assert.equal((sent.properties?.$set as { utm_source?: string }).utm_source, "x");
  assert.equal(
    (sent.properties?.$set as { $current_url?: string }).$current_url,
    "https://founderconsole.ai/",
  );
  assert.equal(
    (sent.properties?.$set_once as { $initial_utm_source?: string }).$initial_utm_source,
    "x",
  );
  const blob = JSON.stringify(sent.properties);
  assert.match(blob, /"utm_source":"x"/);
  assert.equal(blob.includes("utm_source=x"), false);
  assert.equal(blob.includes("token="), false);
  assert.equal(blob.includes("#"), false);
  assert.equal(blob.includes("gclid=click"), false);
});

test("before_send keeps non-pageview names and does not drop events", () => {
  const sent = beforeSendPostHog({
    event: "cta_click",
    properties: {
      location: "navbar",
      $current_url: "https://founderconsole.ai/tools/runway-calculator?cash=10&burn=2#result",
    },
  });
  assert.ok(sent);
  assert.equal(sent.event, "cta_click");
  assert.equal(
    sent.properties?.$current_url,
    "https://founderconsole.ai/tools/runway-calculator",
  );
  assert.equal(sent.properties?.location, "navbar");
  assert.equal(beforeSendPostHog(null), null);
  const clean = beforeSendPostHog({
    event: "$pageview",
    properties: { $current_url: "https://founderconsole.ai/pricing", utm_source: "x" },
  });
  assert.equal(clean?.properties?.utm_source, "x");
  assert.equal(clean?.properties?.$current_url, "https://founderconsole.ai/pricing");
});

test("gtag page_location and page_referrer drop secrets and the hash", () => {
  for (const page of TOKEN_PAGES) {
    const fields = gtagPageFields(page.href, page.href);
    assert.equal(fields.page_location, `https://founderconsole.ai${page.pathname}`);
    assert.equal(fields.page_referrer, `https://founderconsole.ai${page.pathname}`);
    assertNoSecret(fields, page.needles);
  }
  const utm = gtagPageFields(
    "https://founderconsole.ai/?utm_source=x",
    "https://google.com/search?q=runway#top",
  );
  assert.equal(utm.page_location, "https://founderconsole.ai/?utm_source=x");
  assert.equal(utm.page_referrer, "https://google.com/search");
});

test("GA landing keeps utm_source and drops token; PostHog URL stays origin+path", () => {
  const href = "https://founderconsole.ai/?utm_source=x&token=y";
  const fields = gtagPageFields(href, "https://ads.example/click?utm_source=x&token=y#ad");
  assert.equal(fields.page_location, "https://founderconsole.ai/?utm_source=x");
  assert.equal(fields.page_referrer, "https://ads.example/click?utm_source=x");
  assert.equal(JSON.stringify(fields).includes("token"), false);
  assert.equal(JSON.stringify(fields).includes("#"), false);

  const kept = gtagPageFields(
    "https://founderconsole.ai/pricing?code=abc&utm_medium=cpc&utm_source=x&utm_campaign=spring&utm_term=runway&utm_content=hero&gclid=g&fbclid=f&token=y#section",
  );
  assert.equal(
    kept.page_location,
    "https://founderconsole.ai/pricing?utm_source=x&utm_medium=cpc&utm_campaign=spring&utm_term=runway&utm_content=hero&gclid=g&fbclid=f",
  );

  const sent = beforeSendPostHog({
    event: "$pageview",
    properties: { $current_url: href, utm_source: "x" },
  });
  assert.equal(sent?.event, "$pageview");
  assert.equal(sent?.properties?.$current_url, "https://founderconsole.ai/");
  assert.equal(sent?.properties?.utm_source, "x");
  assert.equal(JSON.stringify(sent?.properties).includes("token"), false);
  assert.equal(JSON.stringify(sent?.properties).includes("utm_source=x"), false);
});

test("PostHog init uses before_send and still emits $pageview", () => {
  const posthogLib = readFileSync("client/src/lib/posthog.ts", "utf8");
  assert.match(posthogLib, /before_send:\s*beforeSendPostHog/);
  assert.match(posthogLib, /capture_pageview:\s*false/);
  assert.match(posthogLib, /event:\s*"\$pageview"/);
});

test("every gtag config and page hit sets a filtered page_location", () => {
  const indexHtml = readFileSync("client/index.html", "utf8");
  assert.match(indexHtml, /function fcGaUrl\(raw\)/);
  for (const key of ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "gclid", "fbclid"]) {
    assert.match(indexHtml, new RegExp(key));
  }
  assert.match(indexHtml, /page_location:\s*fcGaUrl\(location\.href\)/);
  assert.match(indexHtml, /page_referrer:\s*fcGaUrl\(document\.referrer/);
  assert.doesNotMatch(indexHtml, /page_location:\s*location\.href/);
  assert.doesNotMatch(indexHtml, /gtag\(\s*'config'\s*,\s*'G-NJKW0TGC4C'\s*\)/);

  const files = [
    "client/src/App.tsx",
    "client/src/pages/auth.tsx",
    "client/src/pages/auth-callback.tsx",
    "client/src/pages/demo-redirect.tsx",
    "client/src/pages/onboarding.tsx",
    "client/src/lib/funnel.ts",
  ];
  for (const file of files) {
    const source = readFileSync(file, "utf8");
    const calls = source
      .split("\n")
      .filter((line) => line.includes(".gtag(") || line.includes("gtag('"));
    assert.ok(calls.length > 0, `${file} should send gtag`);
    for (const line of calls) {
      assert.match(line, /withGtagPage\(/, `${file}: ${line.trim()}`);
    }
  }
});
