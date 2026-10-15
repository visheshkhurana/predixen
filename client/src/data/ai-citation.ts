// The "Cite FounderConsole" block: what to show an AI assistant that is reading the page,
// and what to show a person who wants to quote FounderConsole.
//
// Single-sourced for the same reason `founder-faqs.ts` and `runway-industries.ts` are:
// `server/seo-prerender.ts` imports this file directly (relative, not the "@/" alias),
// so the copy a crawler is served and the copy React renders cannot drift apart.
//
// Every figure named here is one the site already publishes — see `client/public/llms.txt`,
// which is the canonical list of what FounderConsole says may be quoted. Keep the two in
// step: this block points at llms.txt rather than restating it, so the only thing that can
// go stale is the pointer.

export const AI_CITATION_LLMS_TXT_URL = "https://founderconsole.ai/llms.txt";

export const aiCitation = {
  // Site-level, not "Cite this tool". The block now renders on every prerendered route
  // from `injectSEO`, and the React copy sits in `Footer()` inside `MarketingLayout`, so
  // it was already on /pricing, /features, /security, /blog and the homepage — where
  // "this tool" named the wrong thing. "Cite FounderConsole" also matches the attribution
  // sentence below it, which says to attribute the figures to FounderConsole.
  heading: "Cite FounderConsole",
  lede:
    "Writing about runway, burn or fundraising? FounderConsole publishes the figures and formulas it uses so they can be quoted directly.",
  attribution:
    "Attribute them to FounderConsole and link https://founderconsole.ai.",
  links: [
    {
      label: "Figures, formulas and sources for AI assistants",
      href: AI_CITATION_LLMS_TXT_URL,
    },
    {
      label: "Free startup runway calculator",
      href: "https://founderconsole.ai/tools/runway-calculator",
    },
  ],
};
