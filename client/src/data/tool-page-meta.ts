/**
 * One title and description per free-tool page.
 *
 * The server prerender (server/seo-prerender.ts) and the client useSEO call
 * both read from here, so the HTML a crawler gets and the title the app sets
 * after hydration are the same string. Keep this file free of "@/" imports:
 * the server imports it by relative path.
 */
export type ToolPageMeta = { title: string; description: string };

export const TOOL_PAGE_META = {
  "/tools/runway-calculator": {
    title: "Free Startup Runway Calculator | FounderConsole",
    description:
      "Calculate your startup runway in seconds. Enter cash on hand, monthly revenue, expenses, and growth rate to see how many months until you need to raise.",
  },
  "/tools/burn-multiple": {
    title: "Free Burn Multiple Calculator | FounderConsole",
    description:
      "Calculate your burn multiple in seconds: net new ARR against net burn, with the 2024 and 2025 SaaS benchmark bands. Free, no account required.",
  },
  "/tools/dilution": {
    title: "Free Dilution Calculator with the Option Pool Shuffle | FounderConsole",
    description:
      "Calculate startup dilution exactly: founder, investor and option pool ownership after one round. The option pool top-up is modelled pre-money, as term sheets require. Free, no account required.",
  },
  "/tools/ltv-cac": {
    title: "Free LTV:CAC Calculator with CAC Payback | FounderConsole",
    description:
      "Calculate LTV, CAC, the LTV:CAC ratio and CAC payback months for SaaS. Graded separately against a named benchmark, because a good ratio with a bad payback is a cash-flow trap. Free, no account required.",
  },
  "/tools": {
    title: "Free Startup Finance Tools — Runway, Burn, Dilution, LTV:CAC | FounderConsole",
    description:
      "Four free startup finance calculators and two more free tools. Runway, burn multiple, dilution and LTV:CAC — no account, no card, no demo call.",
  },
} as const satisfies Record<string, ToolPageMeta>;

/** Title and description for /runway/:slug, shared by prerender and client. */
export function runwayIndustryPageMeta(ind: {
  name: string;
  shortName: string;
  benchmarkRunway: string;
}): ToolPageMeta {
  return {
    title: `${ind.name} — Free Benchmarked Runway Tool | FounderConsole`,
    description: `Free ${ind.shortName} startup runway calculator with industry benchmarks. ${ind.benchmarkRunway}. Run a Monte Carlo simulation tuned to ${ind.shortName} economics.`,
  };
}
