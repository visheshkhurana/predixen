/**
 * Which paths this server answers with the app shell.
 *
 * HAG-162. `static.ts` used to answer EVERY path it did not recognise with the
 * prerendered shell and an implicit 200. React Router has a catch-all
 * (`<Route component={NotFound} />`, client/src/App.tsx:600), so the body was
 * already "not found" -- only the status code lied. Two consequences, and the
 * second is the expensive one:
 *
 *   1. A typo'd or retired URL is a 200, so Google keeps it and keeps crawling it.
 *   2. `injectSEO` returns the shell UNTOUCHED when `getPageMeta` has no entry
 *      for the path (`seo-prerender.ts`), so that 200 carried the HOMEPAGE
 *      title, the HOMEPAGE canonical and `index, follow`. Every dead URL was
 *      therefore a duplicate of the homepage competing with it in the index.
 *      New tool and landing URLs could not out-rank them.
 *
 * The trap: `getPageMeta` knows only the marketing/SEO routes, while the client
 * declares every route below. 404-ing what `getPageMeta` does not recognise
 * would break ~100 logged-in pages. So the app's own route table is the
 * allowlist, and `server/tests/test_route_allowlist_covers_client_app.py`
 * re-reads `client/src/App.tsx` and fails when a route is added under a new
 * prefix without being added here. The list is enforced, not remembered.
 *
 * Static files never reach this check: `express.static` and the `/assets`
 * mount run first, and `serveStatic` is registered last (server/index.ts:873),
 * after every `/api` mount.
 */

/** Every route the client router declares, as Express-style patterns. */
export const APP_ROUTE_PATTERNS: readonly string[] = [
  "/",
  "/about",
  "/account/notifications",
  "/add-data-source",
  "/admin",
  "/admin/activity",
  "/admin/ai-governance",
  "/admin/billing",
  "/admin/companies",
  "/admin/email-templates",
  "/admin/email-tracking",
  "/admin/evals",
  "/admin/growth",
  "/admin/invites",
  "/admin/lead-gen",
  "/admin/lead-gen/campaigns",
  "/admin/lead-gen/leads",
  "/admin/lead-gen/settings",
  "/admin/lead-gen/templates",
  "/admin/llm-audit",
  "/admin/login",
  "/admin/login-history",
  "/admin/messaging",
  "/admin/metrics",
  "/admin/system",
  "/admin/team",
  "/admin/users",
  "/ai-cfo",
  "/ai-graphics",
  "/alerts",
  "/alternatives",
  "/apply",
  "/auth",
  "/auth/callback",
  "/billing",
  "/blog",
  "/blog/:slug",
  "/cap-table",
  "/companies/:companyId/scenarios",
  "/compare",
  "/competition",
  "/contact",
  "/copilot",
  "/customers",
  "/dashboard",
  "/dashboard/:id",
  "/dashboards",
  "/data",
  "/data-input",
  "/data-source/:id",
  "/data/verify/:sessionId",
  "/decisions",
  "/default-alive",
  "/demo",
  "/digital-twin",
  "/doc-generator",
  "/docs",
  "/embed/survival",
  "/faq",
  "/features",
  "/fundraising",
  "/goals",
  "/health-check",
  "/help",
  "/hiring-planner",
  "/how-it-works",
  "/ingest",
  "/integrations",
  "/intelligence",
  "/investor-room",
  "/join",
  "/journal",
  "/kpi-board",
  "/login",
  "/marketplace",
  "/matches",
  "/metrics",
  "/onboard",
  "/onboarding",
  "/overview",
  "/owner-console",
  "/pricing",
  "/privacy",
  "/product",
  "/profile",
  "/qa",
  "/referral",
  "/register",
  "/reset-password",
  "/runway/:slug",
  "/scenarios",
  "/scenarios/:id",
  "/scenarios/shared/:uuid",
  "/security",
  "/settings",
  "/settings/notifications",
  "/signup",
  "/simulate",
  "/simulate-v2",
  "/simulate-v2/shared/:token",
  "/simulation",
  "/simulator",
  "/suggested-metrics",
  "/survival-simulator",
  "/survival/:simId",
  "/templates",
  "/terms",
  "/tools/runway-calculator",
  "/truth",
  "/truth-scan",
  "/unsubscribe",
  "/use-cases",
  "/verify-email",
];

function segments(value: string): string[] {
  return value.split("/").filter((s) => s.length > 0);
}

/**
 * Segment-wise match, so `/pricing` does not swallow `/pricing/bogus`.
 *
 * `:param` matches exactly one non-empty segment, and a literal compares
 * case-insensitively because both Express and React Router route that way, so
 * `/Pricing` resolves in the browser and must not 404 here. A trailing slash is
 * tolerated (`segments` drops empty parts), which matches what the router does.
 */
export function matchesRoutePattern(pathname: string, pattern: string): boolean {
  const got = segments(pathname);
  const want = segments(pattern);
  if (got.length !== want.length) {
    return false;
  }
  for (let i = 0; i < want.length; i += 1) {
    const expected = want[i];
    if (expected.startsWith(":")) {
      if (got[i].length === 0) {
        return false;
      }
      continue;
    }
    if (expected.toLowerCase() !== got[i].toLowerCase()) {
      return false;
    }
  }
  return true;
}

/** True when the client router has a route for this pathname. */
export function isKnownAppRoute(pathname: string): boolean {
  return APP_ROUTE_PATTERNS.some((pattern) => matchesRoutePattern(pathname, pattern));
}
