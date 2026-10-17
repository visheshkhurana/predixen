// Frontend audit (2026-10-16) guards:
//  1. the tsc error budget was lowered to the real count and stays there;
//  2. /integrations ships no fake connect / fake sync copy;
//  5. failed queries toast (deduped, not 401, opt-out via meta);
//  6. copilot keeps the unsent question across a 401 and login returns via ?next=.
//
// Run: npx tsx --test server/tests/frontend-audit-ux.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync, statSync, existsSync } from "fs";
import { join } from "path";
import {
  shouldToastQueryError,
  createDedupedNotifier,
} from "../../client/src/lib/queryErrorToast.ts";
import { safeNextPath, buildExpiredLoginUrl, readNextFromSearch } from "../../client/src/lib/loginNext.ts";
import {
  saveCopilotDraft,
  loadCopilotDraft,
  clearCopilotDraft,
  COPILOT_DRAFT_KEY,
} from "../../client/src/lib/copilotDraft.ts";

const read = (p: string) => readFileSync(p, "utf8");

function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) walk(p, out);
    else if (/\.(tsx?|jsx?)$/.test(name)) out.push(p);
  }
  return out;
}

// ---- 1. tsc budget -------------------------------------------------------

test("tsc error budget is lowered to the current count (0)", () => {
  const wf = read(".github/workflows/pr-checks.yml");
  const m = wf.match(/TSC_ERROR_BUDGET:\s*"(\d+)"/);
  assert.ok(m, "TSC_ERROR_BUDGET must be set in pr-checks.yml");
  assert.equal(Number(m![1]), 0, "budget was 82; system-tools typing fixes brought it to 0");
});

test("system-tools queries are typed (no untyped useQuery returning {})", () => {
  const src = read("client/src/pages/admin/system-tools.tsx");
  const untyped = src.match(/useQuery\(\{/g) || [];
  assert.equal(untyped.length, 0, "every useQuery in system-tools.tsx needs a response type");
});

// ---- 2. no fake integration success -------------------------------------

test("no fake-success integration copy ships in the client", () => {
  const banned = [
    "Initial sync started",
    "Company Financials 2024",
    "Data will sync on schedule",
    "Data will sync shortly",
  ];
  for (const f of walk("client/src")) {
    const s = read(f);
    for (const b of banned) {
      assert.ok(!s.includes(b), `${f} still contains fake-success text "${b}"`);
    }
  }
});

test("integration modals do not simulate a connect with a timer", () => {
  assert.equal(existsSync("client/src/components/integrations/OAuthConnectModal.tsx"), false);
  assert.equal(existsSync("client/src/components/integrations/GoogleSheetsConfigModal.tsx"), false);
  const apiKey = read("client/src/components/integrations/ApiKeyConnectModal.tsx");
  assert.doesNotMatch(apiKey, /setTimeout\(resolve/, "ApiKeyConnectModal must await the real request");
  const page = read("client/src/pages/integrations.tsx");
  assert.match(page, /\/api\/connectors\/companies\/\$\{companyId\}\/connect/);
  assert.doesNotMatch(page, /useState\(1\)/, "companyId must come from the current company, not a literal 1");
});

test("registry integrations without a backend connector are Coming Soon", () => {
  const reg = read("client/src/lib/integrations/registry.ts");
  for (const id of ["google-sheets", "google-analytics-4", "chartmogul"]) {
    const start = reg.indexOf(`id: '${id}'`);
    assert.ok(start >= 0, id);
    const block = reg.slice(start, start + 600);
    assert.match(block, /isComingSoon: true/, `${id} must be Coming Soon`);
  }
  const mp = reg.slice(reg.indexOf("id: 'mixpanel'"), reg.indexOf("id: 'mixpanel'") + 600);
  assert.match(mp, /connectorProviderId: 'mixpanel'/);
});

// ---- 5. query error toast -------------------------------------------------

test("query errors toast except 401/403/404 and opted-out queries", () => {
  assert.equal(shouldToastQueryError({ status: 500, message: "500: boom" }), true);
  assert.equal(shouldToastQueryError({ status: 0, message: "Network request failed" }), true);
  assert.equal(shouldToastQueryError(new Error("parse")), true);
  assert.equal(shouldToastQueryError({ status: 401 }), false);
  assert.equal(shouldToastQueryError({ status: 403 }), false);
  assert.equal(shouldToastQueryError({ status: 404 }), false);
  assert.equal(shouldToastQueryError({ status: 500 }, { suppressErrorToast: true }), false);
});

test("query error toasts are deduped within the window", () => {
  let t = 0;
  const shown: string[] = [];
  const notify = createDedupedNotifier((d) => shown.push(d), 10_000, () => t);
  const err = Object.assign(new Error("500: Internal Server Error"), { status: 500 });
  assert.equal(notify(err), true);
  assert.equal(notify(err), false);
  t = 5_000;
  assert.equal(notify(err), false);
  t = 10_001;
  assert.equal(notify(err), true);
  assert.equal(notify({ status: 401 }), false);
  assert.equal(shown.length, 2);
});

test("queryClient installs the QueryCache onError toast", () => {
  const qc = read("client/src/lib/queryClient.ts");
  assert.match(qc, /new QueryCache\(\{/);
  assert.match(qc, /notifyQueryError\(error, query\.meta\)/);
});

// ---- 6. copilot draft + ?next= -------------------------------------------

function memoryStorage() {
  const m = new Map<string, string>();
  return {
    getItem: (k: string) => (m.has(k) ? m.get(k)! : null),
    setItem: (k: string, v: string) => void m.set(k, v),
    removeItem: (k: string) => void m.delete(k),
    m,
  };
}

test("copilot draft round-trips and tolerates broken storage", () => {
  const s = memoryStorage();
  saveCopilotDraft("What is my runway?", s);
  assert.equal(s.m.get(COPILOT_DRAFT_KEY), "What is my runway?");
  assert.equal(loadCopilotDraft(s), "What is my runway?");
  clearCopilotDraft(s);
  assert.equal(loadCopilotDraft(s), null);
  const broken = {
    getItem: () => { throw new Error("blocked"); },
    setItem: () => { throw new Error("blocked"); },
    removeItem: () => { throw new Error("blocked"); },
  };
  assert.doesNotThrow(() => saveCopilotDraft("x", broken));
  assert.equal(loadCopilotDraft(broken), null);
  assert.doesNotThrow(() => clearCopilotDraft(broken));
  assert.equal(loadCopilotDraft(null), null);
});

test("copilot saves the draft before clearing the input", () => {
  const src = read("client/src/pages/copilot.tsx");
  const save = src.indexOf("saveCopilotDraft(messageText);");
  assert.ok(save > 0, "sendMessage must save the draft");
  assert.ok(src.indexOf("setInput('');", save) > save, "draft is saved before the input is cleared");
  assert.match(src, /useState\(\(\) => loadCopilotDraft\(\) \?\? ''\)/, "draft restored on return");
});

test("?next= only accepts same-origin app paths", () => {
  assert.equal(safeNextPath("/copilot"), "/copilot");
  assert.equal(safeNextPath("/scenarios/12?tab=a"), "/scenarios/12?tab=a");
  for (const bad of ["//evil.com", "/\\evil.com", "https://evil.com", "evil", "", null, "/auth", "/auth?expired=1"]) {
    assert.equal(safeNextPath(bad as string | null), null, String(bad));
  }
  assert.equal(buildExpiredLoginUrl("/copilot"), "/auth?expired=1&next=%2Fcopilot");
  assert.equal(buildExpiredLoginUrl("/"), "/auth?expired=1");
  assert.equal(readNextFromSearch("?expired=1&next=%2Fcopilot"), "/copilot");
  assert.equal(readNextFromSearch("?next=%2F%2Fevil.com"), null);
});

test("session expiry redirect carries next, and login honours it", () => {
  const session = read("client/src/lib/authSession.ts");
  assert.match(session, /buildExpiredLoginUrl\(window\.location\.pathname \+ window\.location\.search\)/);
  const auth = read("client/src/pages/auth.tsx");
  assert.match(auth, /readNextFromSearch\(window\.location\.search\) \?\? '\/'/);
});
