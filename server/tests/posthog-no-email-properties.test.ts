// Signed-in PostHog identify must not attach an email person trait.
// distinct_id stays the numeric user id; role is the only trait.
// trackSignup may still accept email, and must not forward it.
//
// gtag user_email is a separate change and is not scanned here.
//
// Run: npx tsx server/tests/posthog-no-email-properties.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import ts from "typescript";
import { identifyUser, takeQueuedPostHogCallsForTests } from "../../client/src/lib/posthog";

const EMAIL_KEYS = new Set(["email", "$email", "user_email"]);

type Leak = { file: string; line: number; via: string; text: string };

function isEmailKey(name: string): boolean {
  return EMAIL_KEYS.has(name.toLowerCase());
}

function propertyNameText(name: ts.PropertyName): string | null {
  if (ts.isIdentifier(name) || ts.isStringLiteral(name) || ts.isNumericLiteral(name)) {
    return name.text;
  }
  if (ts.isComputedPropertyName(name)) {
    const expr = name.expression;
    if (ts.isStringLiteral(expr) || ts.isNoSubstitutionTemplateLiteral(expr)) return expr.text;
    if (ts.isIdentifier(expr) && isEmailKey(expr.text)) return expr.text;
  }
  return null;
}

function skipNestedFunction(node: ts.Node): boolean {
  return ts.isFunctionLike(node) || ts.isClassLike(node);
}

/** True when an object key in this subtree is email / $email / user_email. */
function subtreeHasEmailField(root: ts.Node): boolean {
  let found = false;
  function visit(node: ts.Node) {
    if (found) return;
    if (node !== root && skipNestedFunction(node)) return;
    if (ts.isObjectLiteralExpression(node)) {
      for (const prop of node.properties) {
        if (ts.isPropertyAssignment(prop) || ts.isShorthandPropertyAssignment(prop)) {
          const name = propertyNameText(prop.name);
          if (name && isEmailKey(name)) {
            found = true;
            return;
          }
        }
      }
    }
    ts.forEachChild(node, visit);
  }
  visit(root);
  return found;
}

function receiverText(expr: ts.Expression): string {
  return expr.getText();
}

function isPeopleReceiver(expr: ts.Expression): boolean {
  if (ts.isIdentifier(expr)) return expr.text === "people";
  if (ts.isPropertyAccessExpression(expr)) return expr.name.text === "people";
  return false;
}

function isPosthogModule(fileName: string): boolean {
  return /(?:^|\/)posthog(?:-queue)?\.ts$/.test(fileName);
}

function posthogReceiver(expr: ts.Expression, fileName: string): boolean {
  const text = receiverText(expr);
  if (text === "posthog" || text.endsWith(".posthog")) return true;
  if (isPosthogModule(fileName) && (text === "client" || text === "sdk")) return true;
  return false;
}

const WRAPPERS = new Set(["trackEvent", "trackFunnel", "posthogTrack", "useViewedOnce", "track"]);

/**
 * PostHog identify / register / capture / people.set / setPersonProperties,
 * plus the client wrappers that forward properties into capture.
 * auth `api.auth.register` is not PostHog. gtag is not PostHog.
 */
function posthogCallee(expr: ts.Expression, fileName: string): string | null {
  if (ts.isIdentifier(expr)) {
    if (expr.text === "setPersonProperties" || WRAPPERS.has(expr.text)) return expr.text;
    return null;
  }
  if (!ts.isPropertyAccessExpression(expr)) return null;
  const name = expr.name.text;
  if (name === "set" && isPeopleReceiver(expr.expression)) return "people.set";
  if (name === "setPersonProperties") return "setPersonProperties";
  // api.auth.register is not PostHog. SDK register is posthog.register / client.register.
  if (name === "register") return posthogReceiver(expr.expression, fileName) ? "register" : null;
  // identify and capture here are the PostHog SDK (posthog.* / client.identify / client.capture).
  // captureException is a different name and is left alone.
  if (name === "identify" || name === "capture") return name;
  return null;
}

function isKindPayload(obj: ts.ObjectLiteralExpression): string | null {
  for (const prop of obj.properties) {
    if (!ts.isPropertyAssignment(prop)) continue;
    const name = propertyNameText(prop.name);
    if (name !== "kind") continue;
    if (!ts.isStringLiteral(prop.initializer)) continue;
    if (prop.initializer.text === "identify" || prop.initializer.text === "capture" || prop.initializer.text === "register") {
      return prop.initializer.text;
    }
  }
  return null;
}

function snippet(node: ts.Node): string {
  return node.getText().replace(/\s+/g, " ").slice(0, 180);
}

function findEmailLeaks(fileName: string, source: string): Leak[] {
  const scriptKind = fileName.endsWith(".tsx")
    ? ts.ScriptKind.TSX
    : fileName.endsWith(".jsx")
      ? ts.ScriptKind.JSX
      : fileName.endsWith(".js")
        ? ts.ScriptKind.JS
        : ts.ScriptKind.TS;
  const sf = ts.createSourceFile(fileName, source, ts.ScriptTarget.Latest, true, scriptKind);
  if (sf.parseDiagnostics.length > 0) {
    const first = sf.parseDiagnostics[0];
    const message = ts.flattenDiagnosticMessageText(first.messageText, "\n");
    throw new Error(`${fileName} failed to parse: ${message}`);
  }

  const leaks: Leak[] = [];
  const seen = new Set<string>();

  function report(node: ts.Node, via: string) {
    const line = sf.getLineAndCharacterOfPosition(node.getStart(sf)).line + 1;
    const key = `${line}:${via}:${node.getStart(sf)}`;
    if (seen.has(key)) return;
    seen.add(key);
    leaks.push({ file: fileName, line, via, text: snippet(node) });
  }

  function visit(node: ts.Node) {
    if (ts.isCallExpression(node)) {
      const via = posthogCallee(node.expression, fileName);
      if (via && node.arguments.some((arg) => subtreeHasEmailField(arg))) {
        report(node, via);
      }
    }
    if (ts.isObjectLiteralExpression(node)) {
      const kind = isKindPayload(node);
      if (kind && subtreeHasEmailField(node)) {
        report(node, `kind:${kind}`);
      }
    }
    ts.forEachChild(node, visit);
  }
  visit(sf);
  return leaks;
}

function walkClient(dir: string, acc: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    if (name === "node_modules" || name === "dist" || name === "build") continue;
    const path = join(dir, name);
    if (statSync(path).isDirectory()) walkClient(path, acc);
    else if (/\.(tsx?|jsx?)$/.test(name)) acc.push(path);
  }
  return acc;
}

test("scanner rejects an email field on identify, register, capture, and person sets", () => {
  const bad = [
    `posthog.identify(id, { email: "a@b.c", role: "viewer" })`,
    `posthog.capture("e", { email })`,
    `client.identify(String(userId), { role, email })`,
    `posthog.register({ user_email: email })`,
    `posthog.setPersonProperties({ $email: email })`,
    `posthog.people.set({ email: "a@b.c" })`,
    `dispatch({ kind: "identify", distinctId: String(userId), traits: { email, role: role || "viewer" } })`,
    `trackEvent("signup", { email: user.email })`,
    `trackFunnel("sign_up", { method, email })`,
    `posthogTrack(name, { user_email: "a@b.c" })`,
    `export function identifyUser(userId: number, email: string, role?: string) {
      dispatch({
        kind: "identify",
        distinctId: String(userId),
        traits: { email, role: role || "viewer" },
      });
    }`,
  ];
  for (const sample of bad) {
    const fileName = sample.includes("client.identify") ? "client/src/lib/posthog-queue.ts" : "fixture.ts";
    const leaks = findEmailLeaks(fileName, sample);
    assert.ok(leaks.length > 0, `expected a leak in: ${sample}`);
  }
});

test("scanner allows the kept signature, gtag, and non-email PostHog properties", () => {
  const ok = [
    `identifyUser(user.id, user.email, user.role);`,
    `trackSignup(result.user_id, result.email);`,
    `(window as any).gtag('set', 'user_properties', { user_email: email });`,
    `(window as any).gtag('set', 'user_properties', { user_email: user.email });`,
    `api.auth.register(registerForm.email, registerForm.password, distinctId);`,
    `trackFunnel('sign_up', { method, user_id: userId });`,
    `trackFunnel('signup_completed', { method, user_id: userId });`,
    `trackEvent('decision_emailed', { company_id: currentCompany?.id });`,
    `trackEvent("x", { method: "email" });`,
    `posthog.capture("decision_emailed", { company_id: 1 });`,
    `dispatch({ kind: "identify", distinctId: String(userId), traits: { role: role || "viewer" } })`,
    `dispatch({ kind: "capture", event, properties });`,
    `client.identify(call.distinctId, call.traits);`,
    `client.capture(call.event, call.properties);`,
    `const trackSignup = (userId: number, email: string, method = 'email') => {
      void email;
      trackFunnel('sign_up', { method, user_id: userId });
    };`,
    `posthog.identify(id, { role: "viewer" });`,
    `// posthog.identify(id, { email: "hidden@example.com" })
     trackEvent("x", { path });`,
    `export function identifyUser(userId: number, email: string, role?: string) {
      void email;
      dispatch({
        kind: "identify",
        distinctId: String(userId),
        traits: { role: role || "viewer" },
      });
    }`,
  ];
  for (const sample of ok) {
    const fileName = sample.includes("client.identify") || sample.includes("client.capture")
      ? "client/src/lib/posthog-queue.ts"
      : "fixture.ts";
    const leaks = findEmailLeaks(fileName, sample);
    assert.deepEqual(leaks, [], `false positive in: ${sample}\n${JSON.stringify(leaks, null, 2)}`);
  }
});

test("client PostHog calls do not pass an email field", () => {
  const leaks: Leak[] = [];
  for (const path of walkClient("client")) {
    leaks.push(...findEmailLeaks(path, readFileSync(path, "utf8")));
  }
  assert.deepEqual(
    leaks,
    [],
    leaks.map((leak) => `${leak.file}:${leak.line} ${leak.via} ${leak.text}`).join("\n"),
  );
});

test("identifyUser sends the numeric id and role only", () => {
  const src = readFileSync("client/src/lib/posthog.ts", "utf8");
  const start = src.indexOf("export function identifyUser");
  assert.ok(start >= 0, "identifyUser must exist");
  const end = src.indexOf("export function distinctIdFromPersistence");
  assert.ok(end > start);
  const fn = src.slice(start, end);
  assert.match(fn, /email:\s*string/, "signature keeps the email argument");
  assert.match(fn, /const id = Number\(userId\);/);
  assert.match(fn, /if\s*\(\s*!Number\.isFinite\(id\)\s*\)\s*return;/);
  assert.match(fn, /distinctId:\s*String\(id\)/);
  assert.doesNotMatch(fn, /distinctId:\s*String\(userId\)/);
  assert.match(fn, /traits:\s*\{\s*role:\s*role\s*\|\|\s*["']viewer["']\s*\}/);
  const body = fn.slice(fn.indexOf("{"));
  assert.doesNotMatch(body, /\b(?:email|user_email|\$email)\s*(?:,|:|\})/);
  assert.deepEqual(findEmailLeaks("client/src/lib/posthog.ts", src), []);
});

test("identifyUser does not identify a non-finite user id", () => {
  takeQueuedPostHogCallsForTests();
  const missing = [
    undefined,
    Number.NaN,
    Number.POSITIVE_INFINITY,
    Number.NEGATIVE_INFINITY,
    "undefined",
    "not-a-number",
  ];
  for (const userId of missing) {
    identifyUser(userId as unknown as number, "person@example.com", "owner");
  }
  assert.deepEqual(
    takeQueuedPostHogCallsForTests(),
    [],
    "a missing id must not be queued as distinct_id \"undefined\"",
  );

  identifyUser(42, "person@example.com", "owner");
  identifyUser("15" as unknown as number, "person@example.com");
  const queued = takeQueuedPostHogCallsForTests();
  assert.deepEqual(
    queued.map((call) => (call.kind === "identify" ? { id: call.distinctId, traits: call.traits } : call)),
    [
      { id: "42", traits: { role: "owner" } },
      { id: "15", traits: { role: "viewer" } },
    ],
  );
  for (const call of queued) {
    assert.equal(call.kind, "identify");
    if (call.kind === "identify") {
      assert.equal(call.distinctId.includes("undefined"), false);
      assert.equal(Object.hasOwn(call.traits, "email"), false);
    }
  }
});

test("trackSignup keeps email on the signature and does not send it", () => {
  const src = readFileSync("client/src/pages/auth.tsx", "utf8");
  const start = src.indexOf("const trackSignup = ");
  assert.ok(start >= 0);
  const end = src.indexOf("function AnimatedMetric");
  assert.ok(end > start);
  const fn = src.slice(start, end);
  assert.match(fn, /email:\s*string/);
  assert.match(fn, /trackFunnel\(\s*['"]signup_completed['"]\s*,\s*\{\s*method,\s*user_id:\s*userId\s*\}/);
  assert.match(fn, /trackFunnel\(\s*['"]sign_up['"]\s*,\s*\{\s*method,\s*user_id:\s*userId\s*\}/);
  assert.doesNotMatch(fn, /trackFunnel\([\s\S]*\bemail\b/);
  assert.deepEqual(findEmailLeaks("client/src/pages/auth.tsx", fn), []);
});
