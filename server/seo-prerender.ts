import { blogPosts } from "./seo-data";
// Relative, not the "@/" alias: this module is bundled by esbuild from
// server/index.ts and a path alias is one more thing that can silently resolve
// differently at build time. runway-industries.ts is pure data with no imports
// of its own, so pulling it in costs the server bundle nothing and means the
// eight vertical pages cannot drift between what the page renders and what a
// crawler is served.
import { RUNWAY_INDUSTRIES, RUNWAY_RELATED_FREE_TOOLS } from "../client/src/data/runway-industries";
// Same rule as runway-industries above: import the shared data so the Q&A a crawler is
// served and the FAQPage markup beside it cannot drift from what the page renders.
import { founderFaqs } from "../client/src/data/founder-faqs";
// Same rule again: the "Cite FounderConsole" block a crawler is served and the one the
// React footer renders come from one string, so they cannot drift.
import { aiCitation } from "../client/src/data/ai-citation";

const SITE_URL = "https://founderconsole.ai";
const OG_IMAGE = `${SITE_URL}/og-image.png`;

interface PageMeta {
  title: string;
  description: string;
  canonical: string;
  ogType?: string;
  ogImage?: string;
  robots?: string;
  jsonLd?: object[];
  bodyContent?: string;
  /** HTTP status the HTML response should carry. Omitted means 200. */
  statusCode?: number;
}

const landingFaqs = [
  { q: "What is FounderConsole?", a: "FounderConsole is an AI-powered financial intelligence platform for startups. It connects your financial data, builds a digital twin of your company, runs Monte Carlo simulations, and provides AI-powered strategic recommendations." },
  { q: "Is FounderConsole free?", a: "Yes. All features are free during the public beta, including Monte Carlo simulations, AI copilot, cap table management, 34 data connectors, and board deck generation. No credit card is required." },
  { q: "How does FounderConsole help with fundraising?", a: "FounderConsole includes a Fundraising OS with cap table management, dilution modeling, investor CRM, SAFE conversion modeling, and exit waterfall analysis." },
  { q: "What data sources can I connect?", a: "FounderConsole supports 34 data connectors including Stripe, QuickBooks, Xero, Mercury, Brex, Plaid, Gusto, HubSpot, Shopify, Salesforce, and more." },
  { q: "What is a Monte Carlo simulation?", a: "Monte Carlo simulation runs your financial model thousands of times with slightly different inputs each time, producing a probability distribution instead of a single forecast." },
  { q: "How is this different from a spreadsheet?", a: "Spreadsheets give you one forecast. FounderConsole runs thousands of scenarios, accounts for uncertainty, connects to live data, and uses AI to generate insights." },
  { q: "What is a startup digital twin?", a: "A digital twin is a continuously updated virtual representation of your company that reflects your current financial reality without manual updates." },
  { q: "How long does setup take?", a: "Most founders are up and running in under five minutes. Connect your primary data source and FounderConsole automatically builds your digital twin." },
];

/**
 * Council 2026-10-15 item 1, the crawler half: the block an AI assistant reading the served
 * HTML can quote back. GPTBot does not run the bundle, so the React footer's copy of this
 * does not exist for it — the crawler's only chance is the prerender.
 *
 * Emitted centrally in `injectSEO` for every route that has a `bodyContent`, not from one
 * page builder. The first version of this called it from `buildLandingBodyContent()` alone
 * and therefore reached 1 of the 46 prerendered routes that emit a body — the homepage
 * only. Nothing in it is page-specific: `ai-citation.ts` carries no figures and points at
 * `llms.txt` rather than restating it. So per-page placement had no reason behind it, and
 * `/tools/runway-calculator` is the clearest cost — it is one of the block's own two links
 * and it could not cite back.
 *
 * Module scope rather than a function local, because `injectSEO` is the only emit site now.
 */
const citationBlock = `<h2>${escapeHtml(aiCitation.heading)}</h2>
<p>${escapeHtml(aiCitation.lede)} ${escapeHtml(aiCitation.attribution)}</p>
<ul>${aiCitation.links
  .map((l) => `<li><a href="${escapeHtml(l.href)}">${escapeHtml(l.label)}</a></li>`)
  .join("")}</ul>`;

function buildLandingBodyContent(): string {
  const faqHtml = landingFaqs.map((f) =>
    `<section><h3>${escapeHtml(f.q)}</h3><p>${escapeHtml(f.a)}</p></section>`
  ).join("");

  return `<article>
<h1>FounderConsole — The Flight Simulator for Founders</h1>
<p>FounderConsole is the AI-powered decision simulator for startup founders. Connect your company data, simulate the future, and get AI-powered decisions. Run your startup like a simulation.</p>
<h2>How it works</h2>
<ol>
<li><strong>Connect your data</strong> — Link Stripe, QuickBooks, or upload a CSV. Your financial data flows in automatically.</li>
<li><strong>Your company becomes a Digital Twin</strong> — We build a live model of your startup, validated, structured, and ready for simulation.</li>
<li><strong>Run simulations</strong> — Test hiring plans, pricing changes, fundraising timing, and growth strategies before committing.</li>
<li><strong>AI recommends decisions</strong> — Get ranked recommendations backed by data, with narratives you can defend to your board.</li>
</ol>
<h2>Core capabilities</h2>
<ul>
<li><strong>Digital Twin</strong> — Your company modeled in real time. Every financial metric, team member, and data source unified into a living digital representation.</li>
<li><strong>Monte Carlo Simulator</strong> — Test decisions before making them. Run thousands of scenarios to see P10/P50/P90 outcomes.</li>
<li><strong>AI Founder Copilot</strong> — Ask strategic questions in plain English. Get recommendations from parallel AI agents specialized in finance, strategy, and market analysis.</li>
<li><strong>Decision Engine</strong> — Track every decision with full context. Learn from outcomes, compare scenarios, and build institutional memory.</li>
</ul>
<h2>Frequently Asked Questions</h2>
${faqHtml}
<h2>Try a free tool first</h2>
<p>No account required. Calculate <a href="/tools/runway-calculator">startup runway</a>, run Paul Graham's <a href="/default-alive">default alive test</a>, or estimate survival odds with the <a href="/survival-simulator">startup survival simulator</a>. <a href="/tools">Browse all the free tools</a>. See the full product on <a href="/features">features</a> and what's free during beta on <a href="/pricing">pricing</a>. When you're ready for live data and ongoing forecasts, <a href="/signup">get started free</a>.</p>
</article>`;
}

function buildBlogListBodyContent(): string {
  const postsHtml = blogPosts.map((p) =>
    `<article><h2><a href="/blog/${escapeHtml(p.slug)}">${escapeHtml(p.title)}</a></h2><p>${escapeHtml(p.excerpt)}</p><span>${escapeHtml(p.date)} — ${escapeHtml(p.author)}</span></article>`
  ).join("");
  return `<section><h1>Insights for Founders</h1><p>Practical decision science for founders. Runway, fundraising, hiring, and strategy — through the lens of probability.</p>${postsHtml}</section>`;
}

/**
 * Escape first, then promote the two inline markdown constructs the client
 * renderer supports: **bold** and [text](/path).
 *
 * Order matters. Everything is HTML-escaped up front, so nothing a post author
 * writes can inject markup; only the escaped forms of our own two patterns are
 * turned back into tags afterwards. Without this, crawlers and the AI assistants
 * that read these pages without executing JavaScript saw literal asterisks, and
 * internal links between articles were invisible to them — which defeats the
 * point of adding the links.
 */
function renderInlineHtml(text: string): string {
  const escaped = escapeHtml(text);
  return escaped
    // [label](href) — href is restricted to a safe subset, so no javascript: URLs.
    .replace(
      /\[([^\]]+)\]\((\/[A-Za-z0-9\-._~/?#=&%]*|https?:&#x2F;&#x2F;[^)]+|https?:\/\/[^)]+)\)/g,
      (_m, label, href) => `<a href="${href}">${label}</a>`,
    )
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
}

function buildBlogPostBodyContent(slug: string): string | null {
  const post = blogPosts.find((p) => p.slug === slug);
  if (!post) return null;
  const paragraphs = post.content || [];
  const bodyParagraphs = paragraphs.map((p: string) => {
    if (p.startsWith("## ")) return `<h2>${escapeHtml(p.replace("## ", ""))}</h2>`;
    return `<p>${renderInlineHtml(p)}</p>`;
  }).join("");
  return `<article><h1>${escapeHtml(post.title)}</h1><p><em>By ${escapeHtml(post.author)} — ${escapeHtml(post.date)}</em></p>${bodyParagraphs}</article>`;
}

function buildRunwayCalculatorBodyContent(): string {
  // Industry hrefs come from the typed array at runtime so the hub cannot
  // drift from runway-industries.ts. Do not list slugs here — same rule as
  // E10.2 siblings on the vertical pages.
  const industryLinks = RUNWAY_INDUSTRIES.map(
    (i) => `<li><a href="/runway/${esc(i.slug)}">${esc(i.shortName)}</a></li>`,
  ).join("");
  return `<article>
<h1>Startup Runway Calculator</h1>
<p>Enter your financials to instantly see how many months of runway you have, when you'll run out of cash, and how growth affects your timeline.</p>
<h2>How to Calculate Startup Runway: The Complete Guide</h2>
<p>Startup runway is the number of months your company can continue operating before it runs out of cash, assuming no additional funding. It is one of the most important metrics for any early-stage founder because it determines how much time you have to achieve product-market fit, hit growth milestones, or close your next fundraising round.</p>
<p>The basic runway formula is simple: divide your current cash balance by your monthly net burn rate. Net burn is the difference between your monthly expenses and your monthly revenue. If you have $500,000 in the bank and you burn $40,000 per month net, your runway is 12.5 months.</p>
<h3>Why Simple Runway Calculations Are Dangerous</h3>
<p>The problem with the simple formula is that it assumes a constant burn rate. In reality, expenses increase as you hire, revenue fluctuates month-to-month, and unexpected costs arise. A single-point runway estimate gives you false confidence.</p>
<h3>Factors That Affect Your Runway</h3>
<p>Revenue growth rate is the single biggest lever. Customer churn works in the opposite direction. Hiring pace is usually the largest controllable expense. Payment terms and accounts receivable also matter.</p>
<h3>When to Start Fundraising Based on Runway</h3>
<p>Most venture capital firms recommend starting your fundraise when you have 9 to 12 months of runway remaining. This gives you enough time to run a proper process without the desperation that comes from having only 3 months of cash left.</p>
<p>FounderConsole connects to your actual financial data sources and runs Monte Carlo simulations to show you probabilistic runway projections with P10/P50/P90 confidence bands.</p>
<h2>Related free tools</h2>
<p>Also try the <a href="/default-alive">default alive or default dead</a> test and the <a href="/survival-simulator">startup survival simulator</a> — both free, no account required. <a href="/tools">See all the free tools in one place</a>. Explore <a href="/features">features</a> when you want the full product. When you're ready for live data and ongoing forecasts, <a href="/signup">sign up for FounderConsole</a>.</p>
<h2>Industry runway calculators</h2>
<ul>${industryLinks}</ul>
<h2>Founder questions about runway, burn and fundraising</h2>
${founderFaqs
  .map((f) => `<h3>${esc(f.question)}</h3>\n<p>${esc(f.answer)}</p>`)
  .join("\n")}
</article>`;
}

function buildToolsIndexBodyContent(): string {
  // HAG-449: `/tools` used to be a deliberate 404 (the soft-404 work listed it
  // beside `/tools/unknown`), which made it a dead end for anyone who trimmed a
  // tool URL. The four links below are the four `/tools/*` routes `App.tsx`
  // registers; `server/tests/soft-404-status.test.ts` fails if that set drifts,
  // so a new tool page cannot ship and leave the hub pointing at three of four.
  //
  // The two other free calculators live at the site root. They are listed in
  // their own group rather than omitted: a page called "free tools" that hides
  // half the free tools sends a visitor to a search engine instead. `/ai-cfo` is
  // deliberately NOT in that group — it is the product, not a no-account tool,
  // and its own page says so. It is linked from the closing paragraph instead.
  return `<article>
<h1>Free Startup Finance Tools</h1>
<p>Four free calculators for the numbers that decide how long a company has left, and two more free tools that answer the same kind of question. No account, no card, no demo call.</p>
<h2>The four calculators</h2>
<ul>
<li><a href="/tools/runway-calculator">Startup runway calculator</a> — enter cash on hand, monthly revenue, monthly expenses and growth rate to get your months of runway and the month the cash runs out.</li>
<li><a href="/tools/burn-multiple">Burn multiple calculator</a> — how many dollars of burn bought each dollar of net new ARR, from new and total ARR at the start and end of a period.</li>
<li><a href="/tools/dilution">Dilution calculator</a> — the percentage of the company a round costs you, from pre-money valuation, amount raised and the existing option pool.</li>
<li><a href="/tools/ltv-cac">LTV:CAC calculator</a> — lifetime value against acquisition cost, graded separately from payback, because a healthy ratio with a slow payback is how a growing company runs out of cash.</li>
</ul>
<h2>Two more free tools</h2>
<ul>
<li><a href="/default-alive">Default alive or default dead test</a> — Paul Graham's question, answered on your own numbers, with what it would take to flip the answer.</li>
<li><a href="/survival-simulator">Startup survival simulator</a> — a Monte Carlo survival probability rather than a single point estimate.</li>
</ul>
<h2>One number is not a forecast</h2>
<p>Every calculator here holds your inputs steady and returns a single answer. Real revenue is lumpy, and the month that decides the outcome is rarely the average month. FounderConsole connects to your actual financial data and runs the same question thousands of times, so runway comes back as a distribution with P10/P50/P90 bands instead of one date.</p>
<h2>Where these formulas come from</h2>
<p>Each calculator states its formula and its benchmark on the page, records whether the formula is textbook or a stated choice, and pins a worked example in a test. Where a common shortcut is wrong — monthly churn multiplied by twelve instead of compounded, for instance — the page shows the size of the error rather than hiding it.</p>
<p>When you are ready for live data and ongoing forecasts, the <a href="/ai-cfo">AI CFO</a> answers a financial question from your own connected numbers, and you can <a href="/signup">get started free</a>. See <a href="/pricing">pricing</a> for what is included during early access.</p>
</article>`;
}

function buildBurnMultipleBodyContent(): string {
  // The formula and the benchmark bands are not written from memory here: they are the
  // published formulas and sourced figures from `hive/reports/quant-forge-tools-maths.md`
  // (Tool 1) and its source table `hive/reports/quant-benchmarks.md` (Table 1, burn
  // multiple). The page itself is `client/src/pages/burn-multiple.tsx`; this text is what a
  // crawler reads, and `server/tests/burn-multiple.test.ts` pins the arithmetic.
  return `<article>
<h1>Burn Multiple Calculator</h1>
<p>Enter four ARR movements and two cash figures to get your burn multiple — how many dollars of net burn bought each dollar of net new ARR.</p>
<h2>What the burn multiple measures</h2>
<p>The burn multiple divides the cash a company consumed in a period by the recurring revenue it added in that same period. A burn multiple of 2.0 means the company spent two dollars of net burn for every one dollar of net new annual recurring revenue. Lower is better: it is a capital-efficiency ratio, not a growth rate.</p>
<h3>The formulas</h3>
<p>Net new ARR is new ARR plus expansion ARR, minus churned ARR, minus contraction ARR. Net burn is cash out minus cash in. The burn multiple is net burn divided by net new ARR. The result is not annualised and not averaged across the window: the ratio uses the whole period's net burn and whole period's net new ARR, and dividing both by the same number of months leaves the ratio unchanged.</p>
<h3>The three reviewable choices on this page</h3>
<p>First, this calculator uses net burn — cash out minus cash in — rather than gross burn, so revenue collected in the window offsets spend. Second, the default window is the trailing three complete months; monthly figures are noisy and a single month is not a trend. Third, if you supply your starting and ending ARR, the page checks that starting ARR plus net new ARR equals ending ARR, because a burn multiple computed from two different definitions of ARR is not a real number.</p>
<h2>Where the numbers stop making sense</h2>
<p>Burn multiple is undefined when a period added no net new ARR, and it is not a score at all when ARR is shrinking or when the period was cash-flow positive. The page reports those cases as "n/a" with the reason rather than printing an infinity, a negative ratio, or a misleading zero.</p>
<h2>Burn multiple benchmarks</h2>
<p>Two published sources inform the bands on this page. Scale VP's 2025 Whisper Numbers put the 2024 median burn multiple at 2.3x, down from 3.3x in 2023, with a 2025 outlook near 1.0x (<a href="https://www.scalevp.com/blog/2025-whisper-numbers-the-era-of-efficiency-is-here">scalevp.com</a>). Benchmarkit's 2025 B2B SaaS Performance Metrics reports figures below 1.0 at $25M to $50M ARR (<a href="https://www.benchmarkit.ai/2025benchmarks">benchmarkit.ai</a>). Neither source publishes a sample size, so both are directional rather than precise, and the page says so.</p>
<h2>Related free tools</h2>
<p>Also try the <a href="/tools/runway-calculator">startup runway calculator</a> and the <a href="/default-alive">default alive or default dead</a> test — both free, no account required. When you're ready for live data and ongoing forecasts, <a href="/signup">sign up for FounderConsole</a>.</p>
</article>`;
}

function buildDilutionBodyContent(): string {
  // The formula and the choices are not written from memory here: they are the published
  // derivation in `hive/reports/quant-forge-tools-maths.md` (Tool 2, Dilution), whose
  // arithmetic is reproduced by `server/tests/quant_forge_tools_check.py`. The page itself
  // is `client/src/pages/dilution.tsx`; this text is what a crawler reads, and
  // `server/tests/dilution.test.ts` pins the arithmetic.
  return `<article>
<h1>Dilution Calculator</h1>
<p>Enter one funding round — pre-money valuation, amount raised, shares outstanding and the option pool target — to see what the founders, the investor and the option pool each own afterwards.</p>
<h2>How startup dilution works</h2>
<p>The investor's share is the amount raised divided by the post-money valuation, and post-money is pre-money plus the raise. Raise $2M at an $8M pre-money valuation and the investor owns 20% of the $10M post-money company. That part is arithmetic and every calculator agrees on it.</p>
<h3>The option pool shuffle</h3>
<p>Investors usually require the company to leave the round with an unissued option pool already in place, typically 10% to 15% of post-money. That pool is created before the investment is priced, so those shares are carved out of the existing holders rather than the new investor. In the worked example on the page — 8,000,000 founder shares, a 1,000,000-share pool, an $8M pre-money valuation, a $2M raise and a 12% post-money pool target — the investor still owns exactly 20%, but the founders finish at 68% rather than the 71.1% the simple formula implies. The founders lose 32 percentage points, not 20, and the extra 12 points go to the pool.</p>
<h2>The formulas</h2>
<p>With F founder shares, E existing pool shares, T = F + E, V the pre-money valuation, R the amount raised and p the pool target as a fraction of post-money: k = 1 + R / V; the new pool shares are dP = max(0, (p * T * k - E) / (1 - p * k)); the shares the investor buys are N = R * (T + dP) / V; and the post-money share count is T + dP + N. The investor's share, N divided by the post-money total, always equals R / (V + R), whatever the pool target is.</p>
<h2>The choices this calculator states, and what is not a choice</h2>
<p>Textbook, not a choice: the investor's share is the raise divided by the post-money valuation. Chosen: the pool top-up is created pre-money, so it dilutes existing holders and never the new investor, which is standard US term-sheet practice. Chosen: the pool target is a percentage of post-money and the top-up never shrinks, because a tool must not quietly cancel options a company already granted.</p>
<h2>When the arithmetic has no answer</h2>
<p>If the pool target times k reaches 1, no share count satisfies it and the page reports the target as unreachable rather than printing a negative number of shares. A pool already at or above target creates no new pool shares, and the page says so. A negative pre-money valuation is rejected outright, and a pre-money valuation of exactly zero is shown as the investor taking 100% with a warning, because that is what the arithmetic gives.</p>
<h2>Related free tools</h2>
<p>Also try the <a href="/tools/burn-multiple">burn multiple calculator</a>, the <a href="/tools/runway-calculator">startup runway calculator</a> and the <a href="/default-alive">default alive or default dead</a> test — all free, no account required. When you're ready for a live cap table and forecasts, <a href="/signup">sign up for FounderConsole</a>.</p>
</article>`;
}

function buildLtvCacBodyContent(): string {
  // Formula, thresholds and the churn trap are not written from memory here: they are the
  // published derivation in `hive/reports/quant-forge-tools-maths.md` (Tool 3, LTV:CAC) and
  // the benchmarks in `hive/reports/quant-benchmarks.md` (Table 5), whose arithmetic is
  // reproduced by `server/tests/quant_forge_tools_check.py`. The page itself is
  // `client/src/pages/ltv-cac.tsx`; `server/tests/ltv-cac.test.ts` pins the arithmetic.
  return `<article>
<h1>LTV:CAC Calculator</h1>
<p>Enter revenue per customer, gross margin, monthly churn, fully loaded sales and marketing spend, and the customers won in the same period, to see LTV, CAC, the LTV:CAC ratio and the months it takes to recover CAC.</p>
<h2>How to read your LTV:CAC</h2>
<p>LTV is what one customer is worth over their life, CAC is what you paid to win them, and the ratio is one divided by the other. The benchmark most often quoted is David Skok's: above 3x, sometimes as high as 7 or 8. In the worked example on the page — $500 a month per customer, an 80% gross margin, 2% monthly churn, $120,000 of fully loaded sales and marketing, and 24 customers won — LTV is $20,000, CAC is $5,000, and the ratio is 4.00x, which clears the benchmark.</p>
<h3>Why the ratio alone is not enough</h3>
<p>That same example takes 12.5 months to recover CAC. Skok calls the best businesses 5 to 7 months and profitability anemic once payback passes 12 months, so this company has a good ratio and a weak payback at the same time. That is not a contradiction, it is the cash-flow trap: the ratio is a lifetime figure while the payback is what the bank account feels, and a company can grow profitably on paper and still run out of cash. This calculator grades the two numbers separately for that reason.</p>
<h2>The mistake that understates LTV</h2>
<p>Monthly churn is not twelve times monthly. A 2% monthly churn compounds to 21.53% a year, not 24%, and because LTV is inversely proportional to churn, entering 24% into an annual formula gives an LTV of $20,000 where the compounded rate gives $22,296 — the naive route understates LTV by 11.5%. The naive answer is also the same number the correct monthly formula produces, so the error is invisible unless you track the unit. This tool accepts churn per month only and prints the compounded annual equivalent of whatever was entered.</p>
<h2>The formulas</h2>
<p>LTV = revenue per customer times gross margin divided by monthly churn. CAC = fully loaded sales and marketing divided by customers won in the same period. The ratio is LTV divided by CAC. Payback in months is CAC divided by the gross profit per customer per month.</p>
<h2>The choices this calculator states, and what is not a choice</h2>
<p>Textbook, not a choice: the ratio is LTV divided by CAC, and payback is CAC divided by gross profit per customer per month. Chosen: LTV is gross-profit based with monthly churn used as a simple decay rate, the form every free calculator and most founders already know, rather than a discounted-cash-flow LTV that would need a discount rate and a growth assumption. Chosen: CAC is fully loaded, because ad spend alone flatters every company that pays salaries. Chosen: churn is floored at 0.1% per month and the floor is labelled, because a churn of zero makes LTV infinite and would print the best possible score for a business that has not been running long enough to lose anyone.</p>
<h2>When the answer is not a number</h2>
<p>Win no new customers and there is nothing to divide the spend by, so the calculator reports no new customers rather than a CAC of zero. Spend nothing and there is no measurable acquisition cost to report. A zero gross margin is legitimate and gets a real answer: an LTV of zero and a statement that no marketing spend can ever pay back, rather than a division by zero.</p>
<h2>Related free tools</h2>
<p>Also try the <a href="/tools/dilution">dilution calculator</a>, the <a href="/tools/runway-calculator">startup runway calculator</a> and the <a href="/default-alive">default alive or default dead</a> test — all free, no account required. When you're ready to see whether growth is paying for itself against real numbers, <a href="/signup">sign up for FounderConsole</a>.</p>
</article>`;
}

function buildVsRunwaySpreadsheetBodyContent(): string {
  // Comparison copy only — no competitor is named and no competitor claim is made,
  // the same rule /alternatives states on the page itself. Everything asserted about
  // FounderConsole here is already published on /compare and /features. The page is
  // client/src/pages/vs-runway-calculator-vs-spreadsheet.tsx.
  return `<article>
<h1>Runway calculator vs spreadsheet: which one should you use?</h1>
<p>A spreadsheet is the right tool for your first runway model, and it is still the right tool for a one-off static plan. It stops being the right tool at a specific point: when you need a range rather than a date, when an input changes and you have to re-derive the answer by hand, or when someone asks how confident you are in the number. This page is the honest comparison, including the rows where the spreadsheet wins.</p>
<h2>The short answer</h2>
<ul>
<li>Use a spreadsheet if the model is yours, the plan is static, and nobody outside the company has to rely on the output.</li>
<li>Use a calculator when you want the answer now, with benchmarked starting assumptions and no chance of a broken formula.</li>
<li>Outgrow both when the question stops being "what is my runway?" and becomes "how likely is it that I run out, and what moves the date?" A single number — from a sheet or from a calculator — cannot answer that.</li>
</ul>
<h2>Side by side</h2>
<p>Time to a first answer: a spreadsheet takes whatever it takes to build the model, tens of minutes to hours; the free calculator takes seconds with no account; FounderConsole takes minutes once data is connected. What you get back: the sheet returns one cash-out date from the assumptions you typed; the calculator returns months of runway and a cash-out date from benchmarked inputs; FounderConsole returns a distribution — P10/P50/P90 bands, not one date. When an input changes: you edit cells and re-check the downstream formula; on the calculator you change the field and the answer updates; in FounderConsole the forecast updates from your connected data. Formula risk: real in a sheet, where a hardcoded cell or a broken range silently changes the date; none you can introduce in either tool. Where the assumptions come from: you, from memory or the last plan; benchmarked starting inputs you can override; your own connected financials. Sharing it: attach the file and hope the reader finds the cell that matters; send a link; share the scenario with reasoning you can show a board. Cost: free if you already have it; free with no account; every feature free during early access.</p>
<h2>Where the spreadsheet wins</h2>
<p>It is your model. Nobody else's tool decides what a line item means, how you treat a grant, or whether a hire lands in month 3 or month 4. A spreadsheet handles the irregular thing — a deferred payment, a one-off invoice, a seasonal month — without asking you to bend it into someone's form. It works offline, it is on your machine, and for a static plan you intend to look at once, building the model is not wasted effort: it is how you learn your own business. All of that stays true.</p>
<h2>Where the spreadsheet breaks</h2>
<ul>
<li><strong>It gives you a date, and a date reads like a fact.</strong> The arithmetic is a straight line: $120,000 in the bank against $20,000 of net burn is six months. Real burn is not a straight line, so the honest output is a range of dates and a probability of running out — which a single-cell answer cannot express, however correct the cell is.</li>
<li><strong>It goes stale the day you build it.</strong> The model is correct as of the numbers you typed. The bank balance moves on Monday.</li>
<li><strong>The failure is silent.</strong> A hardcoded cell, a drag that stopped one row short, a formula copied across a column it should not have been — the sheet still returns a number, and the number still looks fine. Nothing warns you.</li>
<li><strong>It has no benchmark.</strong> A sheet will tell you what your assumptions imply. It will not tell you that the assumption itself is unusual for a company at your stage, because it has nothing to compare against.</li>
<li><strong>Reading it is a skill.</strong> Handing the file to a board member or a new hire transfers the model, not the understanding — including the part where you know which three cells actually matter.</li>
</ul>
<h2>The honest limit of a free calculator</h2>
<p>A calculator fixes the formula risk and the staleness, and it gives you a benchmarked starting point instead of a blank grid. What it does not fix is the thing at the top of that list: it still returns one number, because you are still entering one set of assumptions. Moving the arithmetic out of your spreadsheet is worth doing — but if the only change is that a website does the multiplication, you have not yet answered the question your investor is asking.</p>
<h2>What a range looks like instead</h2>
<p>FounderConsole runs Monte Carlo simulations over your own connected numbers — thousands of runs produce P10/P50/P90 bands, so runway is a distribution rather than a date, and you can see which assumption moves it. The AI copilot answers strategic questions against the same numbers, with reasoning you can show a board. What FounderConsole ships is already set out on <a href="/compare">compare</a> and <a href="/features">features</a>, and every feature is free during early access — see <a href="/pricing">pricing</a>.</p>
<h2>Try the free side of the comparison first</h2>
<p>No account required. Enter your cash, burn and revenue on the <a href="/tools/runway-calculator">startup runway calculator</a> and compare its answer with your sheet — if the two disagree, one of them has a broken assumption and it is worth knowing which. Paul Graham's <a href="/default-alive">default alive or default dead</a> test asks the harder question behind the arithmetic, and the <a href="/survival-simulator">startup survival simulator</a> estimates odds of survival rather than months. If you want industry-tuned starting inputs, start from the <a href="/runway/saas">SaaS runway calculator</a>. When you want the range rather than the date, <a href="/signup">get started free</a>.</p>
</article>`;
}

function esc(t: string): string {
  return t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function buildPricingBodyContent(): string {
  return `<article>
<h1>Pricing</h1>
<p>Every FounderConsole feature is free during the public beta. No credit card is required to start, and there is no trial clock running in the background.</p>
<h2>What is included</h2>
<p>Monte Carlo simulation with P10/P50/P90 confidence bands, the AI copilot, Truth Scan data validation, cap table and dilution modelling, the fundraising CRM, board deck generation, and all 34 data connectors. See the full list on <a href="/features">features</a>.</p>
<h2>What happens after the beta</h2>
<p>Paid tiers will be introduced once the beta ends. Anyone using FounderConsole during the beta keeps access to their data and will be told well before anything changes.</p>
<h2>Free tools that need no account at all</h2>
<p>Try these before you sign up — results in under a minute, no email required to see the answer:</p>
<ul>
<li><a href="/tools/runway-calculator">Startup runway calculator</a> — months of runway and a cash-out date from your numbers</li>
<li><a href="/default-alive">Default alive or default dead</a> — Paul Graham's test as a calculator</li>
<li><a href="/survival-simulator">Startup survival simulator</a> — 1,000 Monte Carlo runs for survival probability</li>
<li><a href="/tools">All free tools</a> — the full index, including the burn multiple, dilution and LTV:CAC calculators</li>
</ul>
<p>When you're ready for live connectors and ongoing forecasts, <a href="/signup">get started free</a> — still no credit card during beta.</p>
</article>`;
}

function buildDemoBodyContent(): string {
  return `<article>
<h1>See FounderConsole in action</h1>
<p>A live workspace preloaded with a sample company, so you can see how simulation, the AI copilot and the fundraising tools fit together before connecting any of your own data. No account needed.</p>
<p><a href="/demo/enter">Launch the live demo</a> — it opens straight into the product.</p>
<h2>What the demo covers</h2>
<p>Building a digital twin from connected financial data, running a Monte Carlo simulation to get a probabilistic runway rather than a single number, asking the copilot a question about the model, and exporting a board-ready summary.</p>
<h2>Prefer to try something immediately</h2>
<p>The runway calculator and the default alive test are free, need no account, and give you a real answer about your own numbers in under a minute. <a href="/tools">Browse all the free tools</a>.</p>
</article>`;
}

function buildAiCfoBodyContent(): string {
  return `<article>
<h1>AI CFO for startups</h1>
<p>FounderConsole answers the financial questions a founder actually asks — how long the money lasts, what a hire costs in runway, when to start raising — using your connected data rather than a spreadsheet you have to maintain.</p>
<h2>What it does</h2>
<p>It connects your financial sources, keeps a continuously updated model of the company, runs Monte Carlo simulations so the answer is a probability rather than a single guess, and explains its reasoning in plain language.</p>
<h2>What it does not do</h2>
<p>It is not a replacement for an accountant, a bookkeeper or a tax advisor. It is a decision tool for the questions between those things: pacing, hiring, pricing and timing.</p>
<h2>Start without connecting anything</h2>
<p>Try free tools with no account: the <a href="/tools/runway-calculator">startup runway calculator</a>, the <a href="/survival-simulator">startup survival simulator</a>, or the <a href="/default-alive">default alive test</a> — answers from your numbers in under a minute. When you are ready for live data and ongoing forecasts, <a href="/signup">get started free</a>.</p>
</article>`;
}

function buildFeaturesBodyContent(): string {
  return `<article>
<h1>Every tool founders need to survive and scale</h1>
<p>From Monte Carlo simulations to AI-powered strategic briefings — know your runway, your risks, and your next move.</p>

<h2>Simulation Engine</h2>
<p><strong>Probability replaces guesswork.</strong> Run thousands of Monte Carlo simulations to understand the full range of outcomes for your startup. See P10/P50/P90 confidence bands so risk becomes measurable, not hypothetical.</p>
<ul>
<li>Monte Carlo P10/P50/P90 confidence bands across all key metrics</li>
<li>Side-by-side scenario comparison with ranked recommendations</li>
<li>Sensitivity analysis reveals which levers move risk the most</li>
<li>24-month forward projections updated as new data flows in</li>
</ul>

<h2>AI Copilot</h2>
<p><strong>Defend every decision with data.</strong> A multi-LLM copilot that routes queries across GPT-4, Claude, and Gemini to deliver the best answer. Perplexity-powered web research adds real-time market benchmarks and competitor context.</p>
<ul>
<li>Multi-LLM routing selects the best model for each query type</li>
<li>Perplexity web research surfaces live market data and benchmarks</li>
<li>Context-aware strategic recommendations grounded in your financials</li>
<li>Every answer shows its reasoning, assumptions, and data sources</li>
</ul>

<h2>Truth Scan</h2>
<p><strong>Trust your numbers before sharing them.</strong> Multi-stage data validation catches errors, inconsistencies, and anomalies before they reach your board deck. Z-score anomaly detection flags outliers automatically so nothing slips through.</p>
<ul>
<li>Multi-stage data validation across all connected sources</li>
<li>Z-score anomaly detection surfaces statistical outliers instantly</li>
<li>Confidence scoring quantifies how reliable each metric is</li>
<li>Automated reconciliation between accounting and bank feeds</li>
</ul>

<h2>Fundraising OS</h2>
<p><strong>From cap table to term sheet, covered.</strong> Manage your cap table, model SAFE and convertible note conversions, and understand dilution impact before you sign. Generate investor-ready materials and track your fundraising pipeline in one place.</p>
<ul>
<li>Cap table management with real-time ownership visualization</li>
<li>SAFE and convertible note conversion modeling</li>
<li>Dilution modeling shows impact of each fundraising scenario</li>
<li>Investor room with secure document sharing and activity tracking</li>
</ul>

<h2>Data Connectors</h2>
<p><strong>Connect everything. Auto-sync.</strong> 34 real OAuth2 integrations with the tools founders already use. QuickBooks, Stripe, Gusto, Mercury, Brex, Plaid, and more. No CSV imports or screen scraping required.</p>
<ul>
<li>34 integrations with one-click OAuth connections</li>
<li>QuickBooks, Stripe, Gusto, Mercury, Brex, and Plaid supported</li>
<li>Auto-sync keeps your data fresh without manual intervention</li>
<li>Multi-currency handling across all connected sources</li>
</ul>

<h2>Decision Engine</h2>
<p><strong>Strategic clarity, not just charts.</strong> Transform simulation results into narrative strategic briefings that boards and investors understand. Ranked recommendations with confidence scores explain why one path beats another.</p>
<ul>
<li>Narrative strategic briefings written in plain English</li>
<li>Ranked recommendations with GO / CONDITIONAL / NO-GO verdicts</li>
<li>Risk assessment with second-order effects detection</li>
<li>Second-order effect analysis catches downstream surprises early</li>
</ul>

<h2>Start using FounderConsole today</h2>
<p>Every feature is free while we're in early access — no credit card required. Connect your data and get your first forecast in under 5 minutes.</p>
<p><a href="/signup">Get Started Free</a> · Prefer a quick answer first? Try the <a href="/tools/runway-calculator">runway calculator</a>, the <a href="/default-alive">default alive test</a>, or the <a href="/survival-simulator">survival simulator</a> with no signup.</p>
</article>`;
}

function buildProductBodyContent(): string {
  return `<article>
<h1>FounderConsole — financial intelligence for startup founders</h1>
<p>FounderConsole is an AI-powered financial intelligence platform built for startup founders. Connect your data, run Monte Carlo simulations with P10/P50/P90 bands, ask an AI copilot against your own numbers, and manage fundraising from one place — without a spreadsheet as the source of truth.</p>
<h2>Who it is for</h2>
<p>Founders who are asked to be CFO and CEO at once: operators without a finance team who need a range they can defend to a board rather than a single cash-out date. This page is the product overview. The deeper catalog lives on <a href="/features">features</a>.</p>
<h2>What you get</h2>
<ul>
<li><strong>Monte Carlo P10/P50/P90</strong> — thousands of runs produce a runway distribution instead of one forecast.</li>
<li><strong>AI copilot</strong> — strategic questions in plain English, grounded in your connected financials.</li>
<li><strong>Connectors</strong> — 34 data connectors for the tools founders already use, or upload a CSV so the model stays current.</li>
<li><strong>Fundraising OS</strong> — cap table, dilution modeling, and investor-ready materials in one place.</li>
</ul>
<h2>Free during early access</h2>
<p>Every feature is free while we are in early access — no credit card required. Planned paid tiers after early access are on the <a href="/pricing">pricing</a> page.</p>
<h2>Related pages and free tools</h2>
<p>See how we stack up on <a href="/compare">compare</a>. Try these with no account: the <a href="/tools/runway-calculator">startup runway calculator</a>, the <a href="/survival-simulator">startup survival simulator</a>, or the <a href="/default-alive">default alive test</a>. When you are ready for live data and ongoing forecasts, <a href="/signup">get started free</a>.</p>
</article>`;
}

function buildHowItWorksBodyContent(): string {
  return `<article>
<h1>How FounderConsole works</h1>
<p>FounderConsole turns connected financial data into a range you can defend. This page walks through the product in the order it actually runs: connect or upload data, validate with Truth Scan, simulate with Monte Carlo P10/P50/P90, ask the AI copilot, then use fundraising tools. It is a capability walkthrough — not a timeline, a success rate, or a customer story.</p>
<h2>1. Connect or upload data</h2>
<p>Link the tools founders already use, or upload a CSV. FounderConsole has 34 data connectors, including QuickBooks, Stripe, Gusto, Mercury, Brex, and Plaid. You can also start without connecting anything: try the <a href="/tools/runway-calculator">startup runway calculator</a>, the <a href="/survival-simulator">startup survival simulator</a>, or the <a href="/default-alive">default alive test</a> with no account.</p>
<h2>2. Truth Scan validation</h2>
<p>Truth Scan is multi-stage data validation. It catches errors, inconsistencies, and anomalies before numbers reach a board deck. Z-score anomaly detection flags outliers, and confidence scoring quantifies how reliable each metric is. Automated reconciliation between accounting and bank feeds is part of the same validation path.</p>
<h2>3. Monte Carlo simulation (P10/P50/P90)</h2>
<p>The simulation engine runs thousands of Monte Carlo iterations so runway is a distribution, not a single spreadsheet cash-out date. P10/P50/P90 confidence bands make the range visible. Side-by-side scenarios let you test hiring plans, pricing, fundraising timing, and growth assumptions before you commit. The deeper catalog is on <a href="/features">features</a>; jobs this maps to are on <a href="/use-cases">use cases</a>.</p>
<h2>4. AI copilot and decisions</h2>
<p>A multi-LLM copilot answers strategic questions in plain English, grounded in your connected financials. Simulation results become narrative briefings and ranked recommendations (GO / CONDITIONAL / NO-GO). Every answer shows its reasoning, assumptions, and data sources — so you can defend the decision, not just the chart.</p>
<h2>5. Fundraising tools</h2>
<p>Fundraising OS covers cap table management, SAFE and convertible note conversion modeling, dilution modeling, and an investor room with secure document sharing. Use these after you have a range from the simulation — not instead of it. The product overview is on <a href="/product">product</a>.</p>
<h2>Evaluate the product, not a timeline</h2>
<p>Read the <a href="/product">product</a> overview, the <a href="/features">features</a> catalog, <a href="/use-cases">use cases</a>, and <a href="/pricing">pricing</a> (every feature is free during early access). When you are ready for live data and ongoing forecasts, <a href="/signup">get started free</a>.</p>
</article>`;
}

function buildUseCasesBodyContent(): string {
  return `<article>
<h1>FounderConsole use cases — runway, hiring, fundraising, and board readiness</h1>
<p>This page maps FounderConsole to founder jobs the product already covers: runway planning, hiring and fundraising scenario simulation, board and investor readiness, and default-alive checks. It is not a case-study wall — we have not published customer stories or outcome metrics, and this page does not invent them.</p>
<h2>Runway planning</h2>
<p>Founders need a range they can defend, not a single spreadsheet cash-out date. FounderConsole runs Monte Carlo simulations with P10/P50/P90 bands so runway is a distribution. Start without an account on the <a href="/tools/runway-calculator">startup runway calculator</a>, or use the <a href="/runway/saas">SaaS runway calculator</a> when you want industry-tuned starting inputs.</p>
<h2>Hiring and fundraising scenario simulation</h2>
<p>The simulation engine is built to test decisions before you commit: hiring plans, fundraising timing, and growth assumptions. Connect data (or upload a CSV) and compare scenarios side by side instead of rewriting a model for each what-if. The deeper catalog is on <a href="/features">features</a>; the product overview is on <a href="/product">product</a>.</p>
<h2>Board and investor readiness</h2>
<p>When the question is what to show a board or an investor, FounderConsole turns simulation results into narrative briefings and investor-ready materials — Fundraising OS covers cap table, dilution modeling, and related reports. Truth Scan exists so numbers are validated before they land in a deck. None of that is a published customer result; it is what the product ships.</p>
<h2>Default-alive checks</h2>
<p>Paul Graham's default-alive test asks whether you reach profitability on the money you already have. Run it with no account on the <a href="/default-alive">default alive test</a>. For a probabilistic survival view, use the <a href="/survival-simulator">startup survival simulator</a> (1,000 Monte Carlo runs).</p>
<h2>Evaluate the product, not unnamed stories</h2>
<p>Read the <a href="/product">product</a> overview, the <a href="/features">features</a> catalog, and <a href="/pricing">pricing</a> (every feature is free during early access). When you are ready for live data and ongoing forecasts, <a href="/signup">get started free</a>.</p>
</article>`;
}

function buildCustomersBodyContent(): string {
  return `<article>
<h1>Who FounderConsole is for</h1>
<p>FounderConsole is built for seed and Series A founders who need runway confidence — a range they can defend to a board, not a single spreadsheet cash-out date. If you are the operator asked to be CFO and CEO at once, this page is the audience overview.</p>
<h2>Seed and Series A founders who need a defensible range</h2>
<p>The product is for founders who still run finance themselves: people who have to hire, cut burn, or time a raise without a dedicated FP&amp;A team. Monte Carlo P10/P50/P90 bands, an AI copilot grounded in your numbers, and free tools exist so you can see the range before you commit live data.</p>
<ul>
<li>Seed and Series A operators who need a runway distribution instead of one cash-out date.</li>
<li>Founders answering board and investor questions without a finance team behind them.</li>
<li>People deciding whether to hire, cut spend, or raise — and wanting the simulation to show the range of outcomes.</li>
</ul>
<h2>No published logos or case studies yet</h2>
<p>We are in early access. We have not published customer names, logos, quotes, or case studies, and this page does not invent them. Evaluate FounderConsole on the product itself, not on unnamed social proof.</p>
<h2>How to evaluate without a testimonial wall</h2>
<p>Read the <a href="/product">product</a> overview, the <a href="/features">features</a> catalog, <a href="/compare">compare</a>, and <a href="/pricing">pricing</a> (every feature is free during early access). Try these with no account: the <a href="/tools/runway-calculator">startup runway calculator</a>, the <a href="/survival-simulator">startup survival simulator</a>, or the <a href="/default-alive">default alive test</a>. When you are ready for live data and ongoing forecasts, <a href="/signup">get started free</a>.</p>
</article>`;
}

function buildCompareBodyContent(): string {
  return `<article>
<h1>Compare FounderConsole to startup FP&amp;A and runway tools</h1>
<p>Founders comparing startup financial-planning and runway tools usually want a range they can defend, not a single spreadsheet date. This page states what FounderConsole already ships — Monte Carlo P10/P50/P90 bands, an AI copilot, and free tools that need no account — and points to the longer comparison we published.</p>
<h2>What FounderConsole is built to do</h2>
<p>FounderConsole is an AI-powered financial intelligence platform for startup founders. Connect your data (or upload a CSV), run Monte Carlo simulations, and ask the copilot questions against your own numbers.</p>
<ul>
<li><strong>Monte Carlo with P10/P50/P90</strong> — thousands of runs produce a runway distribution instead of one cash-out date.</li>
<li><strong>AI copilot</strong> — strategic questions in plain English, grounded in your connected financials, with reasoning you can show a board.</li>
<li><strong>Free tools</strong> — runway, default-alive, and survival calculators you can use without signing up.</li>
</ul>
<h2>The comparison we already published</h2>
<p>Read <a href="/blog/founderconsole-vs-sturppy-vs-finmark-vs-causal">FounderConsole vs Sturppy vs Finmark vs Causal</a> for the sourced product-status notes. As of August 2026, Finmark has been sunset and Causal has been absorbed into an enterprise suite.</p>
<h2>Spreadsheet or calculator?</h2>
<p>If the question you are weighing is a spreadsheet against a purpose-built tool, we wrote that comparison out in full — including the parts where the <a href="/vs/runway-calculator-vs-spreadsheet">spreadsheet is the better choice</a>.</p>
<h2>Related free tools</h2>
<p>Try these with no account: the <a href="/tools/runway-calculator">startup runway calculator</a>, the <a href="/survival-simulator">startup survival simulator</a>, or the <a href="/default-alive">default alive test</a>. See the full product on <a href="/features">features</a>. When you are ready for live data and ongoing forecasts, <a href="/signup">get started free</a>.</p>
</article>`;
}

function buildAlternativesBodyContent(): string {
  return `<article>
<h1>Startup FP&amp;A alternatives — after Finmark, Causal, and the rest</h1>
<p>This is a category page for founders looking for an alternative to the startup FP&amp;A tools that disappeared. BILL sunset Finmark. Causal was absorbed into Lucanet. The sourced notes live on pages we already published — this page summarizes that consolidation and points to FounderConsole as a seed-stage option. It does not invent competitor pricing, market share, or new product-status claims.</p>
<h2>What happened to the category</h2>
<p>As of August 2026, the seed-stage FP&amp;A field is thinner than it was. We tracked the timeline in full:</p>
<ul>
<li>BILL sunset Finmark on 1 April 2026. finmark.com redirects to bill.com with no destination page or migration guide. If Finmark is the tool you lost, read <a href="/blog/finmark-shut-down-alternative">where your runway model goes next</a>.</li>
<li>Causal joined Lucanet in October 2024 and redirects to an enterprise Extended Planning &amp; Analysis page rather than a founder product.</li>
<li>Pry was acquired by Brex. Mosaic was acquired by HiBob. In July 2026 Runway Financial lost the runway.com domain to an AI video company.</li>
</ul>
<p>The full sequence, with what each redirect lands on, is in <a href="/blog/startup-fpa-tools-acquired-timeline">Every Startup FP&amp;A Tool Got Acquired. Here's the Timeline.</a></p>
<h2>The comparison we already published</h2>
<p>Product-versus-product notes — including that Sturppy is still aimed at early-stage companies — are on <a href="/compare">compare</a> and in <a href="/blog/founderconsole-vs-sturppy-vs-finmark-vs-causal">FounderConsole vs Sturppy vs Finmark vs Causal</a>. We do not repeat competitor pricing here; those posts are the source.</p>
<h2>What FounderConsole ships</h2>
<p>FounderConsole is an AI-powered financial intelligence platform for startup founders. Connect data (or upload a CSV), run Monte Carlo simulations, and ask an AI copilot against your own numbers.</p>
<ul>
<li><strong>Monte Carlo with P10/P50/P90</strong> — thousands of runs produce a runway distribution instead of one cash-out date.</li>
<li><strong>AI copilot</strong> — strategic questions in plain English, grounded in your connected financials.</li>
<li><strong>34 data connectors</strong> — or a CSV of monthly actuals so you can reconstruct a model after an acquired tool goes away.</li>
</ul>
<p>The product overview is on <a href="/product">product</a>. The deeper catalog is on <a href="/features">features</a>. Every feature is free during early access — see <a href="/pricing">pricing</a>.</p>
<h2>Try a free tool first</h2>
<p>No account required: the <a href="/tools/runway-calculator">startup runway calculator</a>, the <a href="/survival-simulator">startup survival simulator</a>, or the <a href="/default-alive">default alive test</a>. When you are ready for live data and ongoing forecasts, <a href="/signup">get started free</a>.</p>
</article>`;
}

function buildSignupBodyContent(): string {
  return `<article>
<h1>Get started with FounderConsole</h1>
<p>This is the create-account page. Create a free FounderConsole account when you want live connectors and ongoing runway forecasts. During early access every feature is free, and no credit card is required — the same terms already on <a href="/pricing">pricing</a>.</p>
<h2>Create a free account</h2>
<p>Sign up to connect your data (or upload a CSV), run Monte Carlo simulations with P10/P50/P90 bands, and ask the copilot against your own numbers. Read the <a href="/product">product</a> overview and the <a href="/features">features</a> catalog if you want more detail first.</p>
<p><a href="/signup">Create a free account</a> — no credit card during early access.</p>
<h2>Prefer a free tool first</h2>
<p>No account required. Try the <a href="/tools/runway-calculator">startup runway calculator</a>, the <a href="/survival-simulator">startup survival simulator</a>, or the <a href="/default-alive">default alive test</a>.</p>
</article>`;
}

function buildSecurityBodyContent(): string {
  return `<article>
<h1>Security at FounderConsole</h1>
<p>FounderConsole is privacy-first: your financial data is encrypted at rest and in transit. Read-only integrations. No data resale. Ever. This page restates the security claims already published on our FAQ, Privacy Policy, and About pages.</p>
<h2>Encryption at rest and in transit</h2>
<p>All data is encrypted using AES-256 at rest and TLS in transit. All connections use HTTPS/TLS encryption in transit.</p>
<h2>Integrations and credentials</h2>
<p>Integrations use OAuth2 with read-only access where possible. Credentials are stored encrypted. Passwords are hashed using bcrypt before storage.</p>
<h2>Where data is stored</h2>
<p>Your data is stored in US-based PostgreSQL databases with automated daily backups. See the <a href="/product">product</a> overview for what the platform does with connected data.</p>
<h2>Compliance</h2>
<p>We are fully GDPR compliant and are actively working toward SOC2 Type II certification. We do not claim SOC2 certification. You can request a full data export or deletion at any time.</p>
<h2>No data resale</h2>
<p>We never sell your data to third parties. No data resale. Ever. The full legal text is on our <a href="/privacy">Privacy Policy</a> and <a href="/terms">Terms of Service</a>.</p>
<h2>Questions</h2>
<p><a href="/contact">Contact us</a> if you have a privacy or security question. When you are ready to connect live data, <a href="/signup">get started free</a>.</p>
</article>`;
}

function buildAboutBodyContent(): string {
  return `<article>
<h1>Built by Founders, for Founders</h1>
<p>Founders are asked to be CFO + CEO at once. That's why we built this.</p>
<p>FounderConsole exists because uncertainty shouldn't force founders into gut decisions or fragile spreadsheets. Forecasting should be real-time. Risk should be measurable. Decisions should be explainable.</p>
<p>Monte Carlo simulation + explainability is our north star. When you can show investors and board members the range of outcomes and the drivers behind them, you can defend decisions and move faster without adding hidden risk.</p>
<p>We believe every founder deserves the same financial intelligence that well-funded companies get from expensive consultants and CFOs. That means investor-grade diligence, probabilistic simulations, and ranked decision recommendations — accessible to everyone, not just those who can afford a finance team.</p>
<h2>Our values</h2>
<ul>
<li><strong>Transparency</strong> — Every recommendation comes with an explanation. No black boxes. You should always understand why.</li>
<li><strong>Data-Driven</strong> — Confidence intervals make risk measurable. Probability replaces intuition when the stakes are highest.</li>
<li><strong>Founder-First</strong> — Built by founders who've lived the uncertainty. Every feature exists because we needed it ourselves.</li>
<li><strong>Privacy-First</strong> — Your financial data is encrypted at rest and in transit. Read-only integrations. No data resale. Ever.</li>
</ul>
<h2>Join us on our mission</h2>
<p>We're building the financial intelligence layer for the next generation of startups.</p>
<p>Try a free tool with no signup: <a href="/tools/runway-calculator">runway calculator</a>, <a href="/default-alive">default alive test</a>, or <a href="/survival-simulator">survival simulator</a>. Browse <a href="/features">features</a>, <a href="/contact">get in touch</a>, or <a href="/signup">get started free</a>.</p>
</article>`;
}

const faqSections = [
  {
    title: "Getting Started",
    items: [
      { q: "What is FounderConsole?", a: "FounderConsole is an AI-powered financial intelligence platform built specifically for startup founders. It replaces spreadsheet-based forecasting with Monte Carlo simulations, giving you probability-based outcomes (P10/P50/P90) instead of a single-point guess. It includes an AI copilot, fundraising CRM, cap table management, 34 data connectors, and strategic briefings — everything a founder needs to make data-driven decisions." },
      { q: "How does FounderConsole help founders?", a: "FounderConsole helps founders by transforming financial uncertainty into measurable probability. Instead of relying on gut feelings, you get Monte Carlo simulations that show the range of possible outcomes, an AI copilot that answers financial questions using your real data, automated data validation (Truth Scan) that catches errors before they reach your board, and strategic briefings that explain your risks and opportunities in plain English." },
      { q: "What metrics does FounderConsole track?", a: "FounderConsole tracks over 24 financial health metrics including MRR, ARR, runway, burn rate, CAC, LTV, LTV:CAC ratio, churn rate, gross margin, NRR, ARPU, active customers, and headcount. Each metric includes a confidence score showing how reliable the data is." },
      { q: "Is FounderConsole free?", a: "Yes — FounderConsole is completely free while we're in early access. Every feature is unlocked and no credit card is required. Planned pricing after early access is shown on the pricing page; we'll give plenty of notice before anything changes." },
      { q: "What is a startup digital twin?", a: "A startup digital twin is a continuously-updated virtual representation of your company inside FounderConsole. It integrates your real financial data, simulation results, strategic decisions, and alerts into a single live model with health scoring and risk indicators." },
      { q: "How do I get started?", a: "Sign up for free (no credit card required), connect one or more data sources like QuickBooks, Stripe, or Mercury, and you'll have a baseline forecast with confidence intervals within 5 minutes." },
      { q: "Is there a demo I can try?", a: "Yes — you can sign in with demo credentials or watch our product walkthrough on the Demo page. The demo includes sample company data so you can explore simulations, the AI copilot, and reporting features without connecting your own data." },
    ],
  },
  {
    title: "Simulation Engine",
    items: [
      { q: "How is this different from a spreadsheet forecast?", a: "Spreadsheets typically show one outcome. Monte Carlo simulation shows the range of possible outcomes (P10/P50/P90) and the probability of hitting key targets, while explainability tells you which variables are driving the risk." },
      { q: "Why do confidence intervals matter?", a: "Confidence intervals make risk measurable. Instead of hoping your single-point forecast is right, you can quantify the probability of different outcomes and make decisions with clearer tradeoffs." },
      { q: "How many simulations can I run?", a: "Each Monte Carlo simulation runs 100 to 10,000 iterations depending on your settings. While we're in early access you can run unlimited scenarios, compare them side by side, and version your work over time." },
    ],
  },
  {
    title: "Data & Security",
    items: [
      { q: "How is my financial data protected?", a: "All data is encrypted using AES-256 at rest and TLS in transit. Integrations use OAuth2 with read-only access where possible. Credentials are stored with envelope encryption. We never sell or share your data with third parties." },
      { q: "Where is my data stored?", a: "Your data is stored in US-based PostgreSQL databases with automated daily backups and point-in-time recovery. Infrastructure is hosted on secure, SOC2-compliant cloud providers with strict access controls and audit logging." },
      { q: "What compliance standards do you follow?", a: "We are fully GDPR compliant and are actively working toward SOC2 Type II certification. You can request a full data export or deletion at any time." },
    ],
  },
  {
    title: "Pricing & Plans",
    items: [
      { q: "Do I need to pay anything right now?", a: "No. Everything is free while we're in early access — every feature is unlocked, with no credit card required. We'll announce paid plans well in advance before anything changes." },
      { q: "What will the paid plans cost later?", a: "Our planned pricing is Starter $29/month, Growth $49/month, and Scale $99/month. None of this is active yet — it's what we intend to charge once we exit early access." },
      { q: "Do you offer enterprise pricing?", a: "Yes — if you need custom integrations, dedicated support, or team-level access controls, contact us to discuss enterprise options." },
    ],
  },
];

function buildFaqBodyContent(): string {
  const sectionsHtml = faqSections.map((section) => {
    const items = section.items.map((item) =>
      `<section><h3>${escapeHtml(item.q)}</h3><p>${escapeHtml(item.a)}</p></section>`
    ).join("");
    return `<h2>${escapeHtml(section.title)}</h2>${items}`;
  }).join("");
  return `<article>
<h1>Frequently Asked Questions</h1>
<p>Clear answers, organized by what founders actually ask.</p>
${sectionsHtml}
<h2>Still have questions?</h2>
<p>We're happy to help. Reach out and we'll get back to you within 24 hours. <a href="/contact">Contact Us</a></p>
<h2>Related free tools</h2>
<p>Try a free tool with no account required: the <a href="/tools/runway-calculator">startup runway calculator</a>, the <a href="/survival-simulator">startup survival simulator</a>, or the <a href="/default-alive">default alive test</a>. When you want live connected data, <a href="/signup">get started free</a>.</p>
</article>`;
}

function buildFaqJsonLd(): object {
  const mainEntity = faqSections.flatMap((s) =>
    s.items.map((item) => ({
      "@type": "Question",
      name: item.q,
      acceptedAnswer: { "@type": "Answer", text: item.a },
    }))
  );
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity,
  };
}

function buildContactBodyContent(): string {
  return `<article>
<h1>Get in Touch</h1>
<p>Questions, feedback, or partnership inquiries — we'd love to hear from you. Whether you need product help, want to talk sales, or are exploring a partnership, the FounderConsole team reads every message.</p>
<h2>Send us a message</h2>
<p>Use the contact form on this page. Choose a subject so we can route you correctly:</p>
<ul>
<li><strong>General Inquiry</strong> — product questions, feedback, or anything that does not fit the other buckets</li>
<li><strong>Sales</strong> — pricing after beta, team plans, or enterprise options</li>
<li><strong>Support</strong> — account help, data connectors, or troubleshooting</li>
<li><strong>Partnership</strong> — integrations, co-marketing, or other collaborations</li>
</ul>
<p>Include your name, work email, and a short note so we know how to help. We respond within 24 hours.</p>
<h2>Contact info</h2>
<ul>
<li><strong>Email</strong> — <a href="mailto:hello@founderconsole.ai">hello@founderconsole.ai</a></li>
<li><strong>Response time</strong> — Within 24 hours</li>
</ul>
<p>Prefer email? Write <a href="mailto:hello@founderconsole.ai">hello@founderconsole.ai</a> directly and use the same subjects above in your subject line.</p>
<h2>Prefer to explore first?</h2>
<p>Try free tools with no account: the <a href="/tools/runway-calculator">startup runway calculator</a>, the <a href="/default-alive">default alive test</a>, or the <a href="/survival-simulator">startup survival simulator</a>. See what is included on <a href="/features">features</a> and <a href="/pricing">pricing</a>, or walk through the <a href="/demo">interactive demo</a>. When you are ready for live data and ongoing forecasts, <a href="/signup">get started free</a>.</p>
</article>`;
}

function buildPrivacyBodyContent(): string {
  return `<article>
<h1>Privacy Policy</h1>
<p>Last updated: March 2026</p>
<p>FounderConsole ("we", "our", "us") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, store, and protect your information when you use our platform.</p>
<h2>Information We Collect</h2>
<ul>
<li><strong>Account Information:</strong> Your email address, name, and password when you register.</li>
<li><strong>Company Financial Data:</strong> Revenue, expenses, cash balances, invoices, and other financial metrics you enter manually or sync through connected integrations (QuickBooks, Stripe, Gusto).</li>
<li><strong>Usage Data:</strong> Pages visited, features used, simulation runs, and interaction patterns to improve the platform.</li>
<li><strong>Authentication Data:</strong> OAuth tokens when you sign in via Google.</li>
</ul>
<h2>How We Use Your Data</h2>
<ul>
<li>Provide financial dashboards, simulations, and AI-powered insights.</li>
<li>Run Monte Carlo simulations and scenario modeling on your financial data.</li>
<li>Generate recommendations and risk assessments through our AI copilot.</li>
<li>Send transactional emails (verification, password reset, alerts).</li>
<li>Improve the platform based on aggregate, anonymized usage patterns.</li>
</ul>
<p>We never sell your data to third parties. Your financial data is only used to provide services directly to you.</p>
<h2>Data Storage &amp; Security</h2>
<ul>
<li>Passwords are hashed using bcrypt before storage.</li>
<li>All connections use HTTPS/TLS encryption in transit.</li>
<li>Integration credentials (OAuth tokens) are stored encrypted.</li>
<li>JWT-based authentication with httpOnly cookies.</li>
<li>CSRF protection on all state-changing requests.</li>
<li>Rate limiting on authentication and simulation endpoints.</li>
</ul>
<h2>Your Rights</h2>
<p>You may access, correct, delete, or export your data, and withdraw consent for integrations or analytics at any time. Contact <a href="mailto:hello@founderconsole.ai">hello@founderconsole.ai</a>. See also our <a href="/terms">Terms of Service</a>.</p>
</article>`;
}

function buildTermsBodyContent(): string {
  return `<article>
<h1>Terms of Service</h1>
<p>Last updated: July 2026</p>
<p>These Terms of Service ("Terms") govern your use of FounderConsole ("the Service"), operated by FounderConsole ("we", "our", "us"). By accessing or using the Service, you agree to be bound by these Terms.</p>
<h2>Service Description</h2>
<p>FounderConsole is an AI-powered financial intelligence platform for startups. The Service provides financial dashboards and KPI tracking, Monte Carlo simulations and scenario modeling, an AI-powered copilot for financial analysis, data integrations with accounting, payroll, and payment platforms, and cap table management and fundraising tools.</p>
<h2>Subscriptions &amp; Billing</h2>
<p>The Service offers a Free plan and paid subscription plans. New accounts may start a one-time 30-day free trial with full feature access. Payments are processed securely by Stripe. Subscriptions renew automatically until cancelled. Founding accounts created before paid plans launched retain complimentary access at our discretion with at least 30 days' notice before changes.</p>
<h2>Service Disclaimer</h2>
<p>The Service is under active development and may contain bugs or incomplete functionality. AI-generated insights, simulations, and recommendations are informational only and should not be the sole basis for financial, investment, or business decisions. FounderConsole does not provide financial, legal, or investment advice.</p>
<h2>Account Terms &amp; Acceptable Use</h2>
<p>You must be at least 18 years of age. You are responsible for your login credentials and all activity under your account. Use the Service only for lawful business purposes; do not reverse-engineer, upload malware, or process data you do not have the right to use.</p>
<h2>Limitation of Liability</h2>
<p>The Service is provided "as is" and "as available" without warranties of any kind. Our total liability is limited to the greater of the amount you paid for the Service in the 12 months preceding the claim, or US $100. You are solely responsible for financial decisions made based on information from the Service.</p>
<h2>Data Rights &amp; Intellectual Property</h2>
<p>You retain full ownership of data you upload. We claim a limited license to process it solely to provide the Service. We will not sell or rent your data except as described in our <a href="/privacy">Privacy Policy</a>. The Service's design, code, algorithms, and AI models are owned by FounderConsole.</p>
<h2>Governing Law</h2>
<p>These Terms are governed by the laws of the State of California, United States. Contact <a href="mailto:hello@founderconsole.ai">hello@founderconsole.ai</a> with questions.</p>
</article>`;
}

function buildSurvivalSimulatorBodyContent(): string {
  return `<article>
<h1>Startup Survival Simulator</h1>
<p>Free tool — no login required. Run 1,000 Monte Carlo simulations to calculate your startup's probability of survival. Get AI-powered recommendations in seconds.</p>
<ul>
<li>No data stored</li>
<li>Results in about 3 seconds</li>
<li>1,000 simulations per run</li>
</ul>
<h2>What you enter</h2>
<p>Cash on hand, monthly revenue, monthly expenses, growth rate, monthly churn, planned hires, and optional fundraising timing and amount. The simulator models 1,000 possible futures from your current numbers.</p>
<h2>What you get</h2>
<ul>
<li><strong>Monte Carlo Engine</strong> — 1,000 probabilistic simulations model uncertainty in growth, margins, and costs.</li>
<li><strong>Survival Probability</strong> — Odds of survival at 6, 12, 18, and 24 months with confidence intervals and runway P10/P50/P90 bands.</li>
<li><strong>AI Recommendations</strong> — Strategic recommendations based on your specific financial trajectory.</li>
</ul>
<h2>Related free tools</h2>
<p>Also try the <a href="/tools/runway-calculator">startup runway calculator</a> and the <a href="/default-alive">default alive or default dead</a> test — both free, no account required. When you're ready for live data and ongoing forecasts, <a href="/signup">sign up for FounderConsole</a>.</p>
</article>`;
}

function buildIndustryBodyContent(slug: string): string | null {
  const ind = RUNWAY_INDUSTRIES.find((i) => i.slug === slug);
  if (!ind) return null;
  const notes = ind.notes.map((n) => `<li>${esc(n)}</li>`).join("");
  const risks = ind.primaryRiskFactors.map((r) => `<li>${esc(r)}</li>`).join("");
  const burn = esc(ind.defaultBurn.toLocaleString("en-US"));
  const revenue = esc(ind.defaultRevenue.toLocaleString("en-US"));
  const margin = esc(String(ind.grossMargin));
  const growth = esc(String(ind.growthRate));
  const relatedTools = RUNWAY_RELATED_FREE_TOOLS.map(
    (t) => `<a href="${esc(t.href)}">${esc(t.label)}</a>`,
  );
  const relatedList =
    relatedTools.length <= 2
      ? relatedTools.join(" and the ")
      : `${relatedTools.slice(0, -1).join(", the ")}, and the ${relatedTools[relatedTools.length - 1]}`;
  // Sibling hrefs come from the typed array at runtime so a new IndustryProfile
  // cannot appear on one page and be missing from the others. Do not list slugs
  // here — RUNWAY_INDUSTRIES is the source of truth.
  const siblings = RUNWAY_INDUSTRIES.filter((i) => i.slug !== ind.slug)
    .map((i) => `<li><a href="/runway/${esc(i.slug)}">${esc(i.shortName)}</a></li>`)
    .join("");
  return `<article>
<h1>${esc(ind.name)}</h1>
<p>Calculate runway against real ${esc(ind.shortName.toLowerCase())} benchmarks. The relevant benchmark here is ${esc(ind.benchmarkRunway)}.</p>
<h2>Typical starting inputs</h2>
<p>This page starts from $${burn}/mo burn, $${revenue}/mo revenue, ${margin}% gross margin, and ${growth}% monthly growth — adjust them to match your books.</p>
<h2>What ${esc(ind.shortName)} founders should watch</h2>
<ul>${notes}</ul>
<h2>Burn multiple</h2>
<p>${esc(ind.burnMultipleNotes)}</p>
<h2>When to raise</h2>
<p>${esc(ind.fundraisingNotes)}</p>
<h2>What usually goes wrong</h2>
<ul>${risks}</ul>
<h2>Related free tools</h2>
<p>Also try the ${relatedList} — all free, no account required. When you're ready for live data and ongoing forecasts, <a href="/signup">sign up for FounderConsole</a>.</p>
<h2>Other industry runway calculators</h2>
<ul>${siblings}</ul>
</article>`;
}

function stripTrailingSlash(path: string): string {
  if (path.length > 1 && path.endsWith("/")) {
    return path.replace(/\/+$/, "");
  }
  return path;
}

/** HTML status for a pathname. Unknown app routes stay 200 (the SPA shell). */
export function pageHttpStatus(path: string): number {
  return getPageMeta(path)?.statusCode ?? 200;
}

/** Status and body the SPA catch-all should send for one pathname. */
export function renderHtmlPage(shell: string, path: string): { status: number; html: string } {
  return { status: pageHttpStatus(path), html: injectSEO(shell, path) };
}

function notFoundMeta(canonical: string, description: string): PageMeta {
  return {
    title: "Page not found | FounderConsole",
    description,
    canonical,
    robots: "noindex, follow",
    statusCode: 404,
    bodyContent: `<article><h1>Page not found</h1><p>${escapeHtml(description)}</p></article>`,
  };
}

function getPageMeta(path: string): PageMeta | null {
  path = stripTrailingSlash(path);
  if (path === "/" || path === "") {
    return {
      title: "FounderConsole — AI Decision Simulator for Founders",
      description: "FounderConsole is the AI-powered decision simulator for startup founders. Monte Carlo simulations, AI copilot, fundraising CRM, and 34 data connectors — replace spreadsheets with simulations.",
      canonical: SITE_URL + "/",
      bodyContent: buildLandingBodyContent(),
      jsonLd: [
        {
          "@context": "https://schema.org",
          "@type": "Organization",
          name: "FounderConsole",
          url: SITE_URL,
          logo: OG_IMAGE,
          description: "AI-powered financial intelligence platform for startups.",
          sameAs: ["https://twitter.com/founderconsole", "https://linkedin.com/company/founderconsole"],
        },
        {
          "@context": "https://schema.org",
          "@type": "SoftwareApplication",
          name: "FounderConsole",
          applicationCategory: "BusinessApplication",
          operatingSystem: "Web",
          url: SITE_URL,
          offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
          featureList: "Monte Carlo Simulation, AI Copilot, Fundraising CRM, Cap Table Management, 34 Data Connectors, Digital Twin",
        },
        {
          "@context": "https://schema.org",
          "@type": "FAQPage",
          mainEntity: landingFaqs.map((f) => ({
            "@type": "Question",
            name: f.q,
            acceptedAnswer: { "@type": "Answer", text: f.a },
          })),
        },
      ],
    };
  }

  if (path === "/features") {
    return {
      title: "Features — Simulation, AI Copilot, Fundraising CRM & More | FounderConsole",
      description: "Monte Carlo simulation engine, multi-LLM AI copilot, Truth Scan data validation, Fundraising OS with CRM, 34 data connectors, and AI strategic briefings.",
      canonical: SITE_URL + "/features",
      bodyContent: buildFeaturesBodyContent(),
      jsonLd: [{
        "@context": "https://schema.org",
        "@type": "WebPage",
        name: "FounderConsole Features",
        description: "Complete feature overview of FounderConsole: Monte Carlo simulations, AI copilot, data validation, fundraising tools, and 34 data connectors.",
        url: SITE_URL + "/features",
        isPartOf: { "@type": "WebSite", name: "FounderConsole", url: SITE_URL },
      }],
    };
  }

  if (path === "/pricing") {
    return {
      title: "Pricing | FounderConsole",
      description: "FounderConsole pricing tiers with fast time-to-value. All features free during public beta — no credit card required.",
      canonical: SITE_URL + "/pricing",
      bodyContent: buildPricingBodyContent(),
      jsonLd: [{
        "@context": "https://schema.org",
        "@type": "WebPage",
        name: "Pricing | FounderConsole",
        url: SITE_URL + "/pricing",
        description: "FounderConsole pricing tiers with fast time-to-value. All features free during public beta — no credit card required.",
        isPartOf: { "@type": "WebSite", name: "FounderConsole", url: SITE_URL },
      }],
    };
  }

  if (path === "/about") {
    return {
      title: "About | FounderConsole",
      description: "Learn about FounderConsole — the AI-powered financial intelligence platform built for startup founders.",
      canonical: SITE_URL + "/about",
      bodyContent: buildAboutBodyContent(),
      jsonLd: [{
        "@context": "https://schema.org",
        "@type": "Organization",
        name: "FounderConsole",
        url: SITE_URL,
        logo: OG_IMAGE,
        description: "AI-powered financial intelligence platform for startups built by founders who lived the uncertainty.",
      }],
    };
  }

  if (path === "/product") {
    return {
      title: "Product — Financial Intelligence for Startup Founders | FounderConsole",
      description: "FounderConsole is an AI-powered financial intelligence platform for startup founders. Monte Carlo P10/P50/P90, AI copilot, connectors, and Fundraising OS — free during early access.",
      canonical: SITE_URL + "/product",
      bodyContent: buildProductBodyContent(),
      jsonLd: [{
        "@context": "https://schema.org",
        "@type": "WebPage",
        name: "FounderConsole Product",
        description: "FounderConsole is an AI-powered financial intelligence platform for startup founders. Monte Carlo P10/P50/P90, AI copilot, connectors, and Fundraising OS — free during early access.",
        url: SITE_URL + "/product",
        isPartOf: { "@type": "WebSite", name: "FounderConsole", url: SITE_URL },
      }],
    };
  }

  if (path === "/how-it-works") {
    return {
      title: "How FounderConsole Works — Connect, Validate, Simulate, Decide",
      description: "How FounderConsole works: connect or upload data, Truth Scan validation, Monte Carlo P10/P50/P90 simulation, AI copilot decisions, and fundraising tools. A capability walkthrough — no invented timings or case studies.",
      canonical: SITE_URL + "/how-it-works",
      bodyContent: buildHowItWorksBodyContent(),
      jsonLd: [{
        "@context": "https://schema.org",
        "@type": "WebPage",
        name: "How FounderConsole Works — Connect, Validate, Simulate, Decide",
        description: "How FounderConsole works: connect or upload data, Truth Scan validation, Monte Carlo P10/P50/P90 simulation, AI copilot decisions, and fundraising tools.",
        url: SITE_URL + "/how-it-works",
        isPartOf: { "@type": "WebSite", name: "FounderConsole", url: SITE_URL },
      }],
    };
  }

  if (path === "/use-cases") {
    return {
      title: "Use Cases — Runway, Hiring, Fundraising, and Board Readiness | FounderConsole",
      description: "How founders use FounderConsole: runway planning, hiring and fundraising scenario simulation, board and investor readiness, and default-alive checks. No invented case studies — evaluate with the product and free tools.",
      canonical: SITE_URL + "/use-cases",
      bodyContent: buildUseCasesBodyContent(),
      jsonLd: [{
        "@context": "https://schema.org",
        "@type": "WebPage",
        name: "Use Cases — Runway, Hiring, Fundraising, and Board Readiness | FounderConsole",
        description: "How founders use FounderConsole: runway planning, hiring and fundraising scenario simulation, board and investor readiness, and default-alive checks. No invented case studies.",
        url: SITE_URL + "/use-cases",
        isPartOf: { "@type": "WebSite", name: "FounderConsole", url: SITE_URL },
      }],
    };
  }

  if (path === "/customers") {
    return {
      title: "Who FounderConsole Is For — Seed and Series A Founders",
      description: "FounderConsole is for seed and Series A founders who need runway confidence. We are in early access and have not published logos or case studies — evaluate with free tools, product pages, and a free account.",
      canonical: SITE_URL + "/customers",
      bodyContent: buildCustomersBodyContent(),
      jsonLd: [{
        "@context": "https://schema.org",
        "@type": "WebPage",
        name: "Who FounderConsole Is For — Seed and Series A Founders",
        description: "FounderConsole is for seed and Series A founders who need runway confidence. Evaluate with free tools and product pages — we have not published customer logos or case studies.",
        url: SITE_URL + "/customers",
        isPartOf: { "@type": "WebSite", name: "FounderConsole", url: SITE_URL },
      }],
    };
  }

  if (path === "/compare") {
    return {
      title: "Compare FounderConsole to Startup FP&A and Runway Tools",
      description: "See how FounderConsole compares to startup FP&A and runway tools: Monte Carlo P10/P50/P90 forecasts, an AI copilot, and free tools — plus the Finmark sunset and Causal absorption notes we already published.",
      canonical: SITE_URL + "/compare",
      bodyContent: buildCompareBodyContent(),
      jsonLd: [{
        "@context": "https://schema.org",
        "@type": "WebPage",
        name: "Compare FounderConsole to Startup FP&A and Runway Tools",
        description: "How FounderConsole compares to startup FP&A and runway tools: Monte Carlo P10/P50/P90, AI copilot, and free tools.",
        url: SITE_URL + "/compare",
        isPartOf: { "@type": "WebSite", name: "FounderConsole", url: SITE_URL },
      }],
    };
  }

  if (path === "/alternatives") {
    return {
      title: "Startup FP&A Alternatives — After Finmark and Causal | FounderConsole",
      description: "Looking for a Finmark or Causal alternative? BILL sunset Finmark; Causal joined Lucanet. This page summarizes the FP&A consolidation we already published and what FounderConsole ships — Monte Carlo P10/P50/P90, an AI copilot, and free tools.",
      canonical: SITE_URL + "/alternatives",
      bodyContent: buildAlternativesBodyContent(),
      jsonLd: [{
        "@context": "https://schema.org",
        "@type": "WebPage",
        name: "Startup FP&A Alternatives — After Finmark and Causal | FounderConsole",
        description: "Looking for a Finmark or Causal alternative? BILL sunset Finmark; Causal joined Lucanet. Summarizes the FP&A consolidation we already published and what FounderConsole ships.",
        url: SITE_URL + "/alternatives",
        isPartOf: { "@type": "WebSite", name: "FounderConsole", url: SITE_URL },
      }],
    };
  }

  if (path === "/signup") {
    return {
      title: "Get Started — Create a Free FounderConsole Account",
      description: "Create a free FounderConsole account to connect live data and run ongoing runway forecasts. Every feature is free during early access — no credit card required. Prefer a quick answer first? Try the free tools with no account.",
      canonical: SITE_URL + "/signup",
      bodyContent: buildSignupBodyContent(),
      jsonLd: [{
        "@context": "https://schema.org",
        "@type": "WebPage",
        name: "Get Started — Create a Free FounderConsole Account",
        description: "Create a free FounderConsole account to connect live data and run ongoing runway forecasts. Every feature is free during early access — no credit card required.",
        url: SITE_URL + "/signup",
        isPartOf: { "@type": "WebSite", name: "FounderConsole", url: SITE_URL },
      }],
    };
  }

  if (path === "/security") {
    return {
      title: "Security — Encryption, Privacy, and Compliance | FounderConsole",
      description: "How FounderConsole protects your data: AES-256 at rest, TLS in transit, OAuth2 read-only integrations, encrypted credentials, bcrypt passwords, US PostgreSQL with backups, GDPR, and work toward SOC2 Type II. We do not sell your data.",
      canonical: SITE_URL + "/security",
      bodyContent: buildSecurityBodyContent(),
      jsonLd: [{
        "@context": "https://schema.org",
        "@type": "WebPage",
        name: "Security — Encryption, Privacy, and Compliance | FounderConsole",
        description: "How FounderConsole protects your data: AES-256 at rest, TLS in transit, OAuth2 read-only integrations, US PostgreSQL with backups, GDPR, and work toward SOC2 Type II. We do not sell your data.",
        url: SITE_URL + "/security",
        isPartOf: { "@type": "WebSite", name: "FounderConsole", url: SITE_URL },
      }],
    };
  }

  if (path === "/contact") {
    return {
      title: "Contact | FounderConsole",
      description: "Contact FounderConsole at hello@founderconsole.ai for general inquiries, sales, support, or partnerships. We typically respond within 24 hours.",
      canonical: SITE_URL + "/contact",
      bodyContent: buildContactBodyContent(),
      jsonLd: [{
        "@context": "https://schema.org",
        "@type": "ContactPage",
        name: "Contact FounderConsole",
        url: SITE_URL + "/contact",
        description: "Contact FounderConsole at hello@founderconsole.ai for general inquiries, sales, support, or partnerships. We typically respond within 24 hours.",
      }],
    };
  }

  if (path === "/faq") {
    return {
      title: "FAQ | FounderConsole",
      description: "FounderConsole FAQ: product, data, pricing, accuracy, and explainability.",
      canonical: SITE_URL + "/faq",
      bodyContent: buildFaqBodyContent(),
      jsonLd: [buildFaqJsonLd()],
    };
  }

  if (path === "/demo") {
    return {
      title: "Demo | FounderConsole",
      description: "Open a live FounderConsole workspace preloaded with a sample company. Forecasts, Monte Carlo simulations and the AI copilot, with no account needed.",
      canonical: SITE_URL + "/demo",
      bodyContent: buildDemoBodyContent(),
    };
  }

  // /demo/enter is an action, not a page: it logs into the shared sample account
  // and forwards to /overview. It gets a real 200 and a plain body so a visitor
  // without JavaScript still sees what is happening, but it is noindex — a
  // forwarding route has nothing to rank for, and indexing it would put a login
  // action in the results instead of the page that explains the demo.
  if (path === "/demo/enter") {
    return {
      title: "Opening the live demo | FounderConsole",
      description: "Opening a live FounderConsole workspace with sample company data. No account needed.",
      canonical: SITE_URL + "/demo",
      robots: "noindex, follow",
      bodyContent: `<article>
<h1>Opening the live demo</h1>
<p>You are being taken into a FounderConsole workspace preloaded with a sample company, in Demo Mode. No account is needed and nothing you do there touches real data.</p>
<p>If nothing happens, the demo could not be reached. <a href="/demo/enter">Try again</a>, or <a href="/signup">create a free account</a>. Read more <a href="/demo">about the demo</a>.</p>
</article>`,
    };
  }

  if (path === "/ai-cfo") {
    return {
      title: "AI CFO for Startups — Runway, Burn and Hiring Answers | FounderConsole",
      description: "An AI CFO for founders without a finance team. Ask about runway, burn rate and hiring, and get answers from your real numbers with Monte Carlo confidence bands.",
      canonical: SITE_URL + "/ai-cfo",
      bodyContent: buildAiCfoBodyContent(),
      jsonLd: [{
        "@context": "https://schema.org",
        "@type": "WebApplication",
        name: "AI CFO for Startups",
        url: SITE_URL + "/ai-cfo",
        applicationCategory: "BusinessApplication",
        operatingSystem: "Web",
        offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
        description: "An AI CFO for founders without a finance team. Ask about runway, burn rate and hiring, and get answers from your real numbers with Monte Carlo confidence bands.",
      }],
    };
  }

  // The eight industry pages had no entry here at all, which meant no title, no
  // description, no canonical and no server-rendered text — eight programmatic
  // pages competing for search traffic while presenting a crawler with an empty
  // div and the generic site title.
  if (path.startsWith("/runway/")) {
    const slug = path.slice("/runway/".length).replace(/\/+$/, "");
    const ind = RUNWAY_INDUSTRIES.find((i) => i.slug === slug);
    if (!ind) {
      // Unknown vertical renders the app's not-found page. The HTML and the
      // status must both be a 404 — noindex on a 200 is still a soft 404.
      return notFoundMeta(
        SITE_URL + "/tools/runway-calculator",
        "This page does not exist. Browse the free runway calculator and industry benchmarks instead.",
      );
    }
    return {
      title: `${ind.name} — Free Benchmarked Runway Tool | FounderConsole`,
      description: `Free ${ind.shortName} startup runway calculator with industry benchmarks. ${ind.benchmarkRunway}. Run a Monte Carlo simulation tuned to ${ind.shortName} economics.`,
      canonical: `${SITE_URL}/runway/${ind.slug}`,
      bodyContent: buildIndustryBodyContent(ind.slug) || undefined,
      // Reachable handler. A later /runway/:slug block used to emit this
      // WebApplication graph, but it sat after this early return so live
      // pages shipped ld_count=0. Name and url come from IndustryProfile only.
      // BreadcrumbList sits alongside it: Home → hub → this vertical, with
      // the last name/url from the typed profile and every URL via SITE_URL.
      jsonLd: [{
        "@context": "https://schema.org",
        "@type": "WebApplication",
        name: ind.name,
        url: `${SITE_URL}/runway/${ind.slug}`,
        applicationCategory: "BusinessApplication",
        operatingSystem: "Web",
        offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
      }, {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        itemListElement: [
          { "@type": "ListItem", position: 1, name: "Home", item: `${SITE_URL}/` },
          { "@type": "ListItem", position: 2, name: "Runway calculator", item: `${SITE_URL}/tools/runway-calculator` },
          { "@type": "ListItem", position: 3, name: ind.name, item: `${SITE_URL}/runway/${ind.slug}` },
        ],
      }],
    };
  }

  if (path === "/blog") {
    return {
      title: "Blog — Startup Finance, Runway Planning & AI Strategy | FounderConsole",
      description: "Insights for startup founders: runway planning, Monte Carlo simulations, SaaS benchmarks, cap table management, and AI-powered financial tools.",
      canonical: SITE_URL + "/blog",
      bodyContent: buildBlogListBodyContent(),
      jsonLd: [{
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        name: "FounderConsole Blog",
        url: SITE_URL + "/blog",
      }],
    };
  }

  if (path === "/tools/runway-calculator") {
    return {
      title: "Free Startup Runway Calculator | FounderConsole",
      description: "Calculate your startup runway in seconds. Enter cash on hand, monthly revenue, expenses, and growth rate to see how many months until you need to raise.",
      canonical: SITE_URL + "/tools/runway-calculator",
      bodyContent: buildRunwayCalculatorBodyContent(),
      jsonLd: [{
        "@context": "https://schema.org",
        "@type": "WebApplication",
        name: "Startup Runway Calculator",
        url: SITE_URL + "/tools/runway-calculator",
        applicationCategory: "BusinessApplication",
        operatingSystem: "Web",
        offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
      }, {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        mainEntity: founderFaqs.map((f) => ({
          "@type": "Question",
          name: f.question,
          acceptedAnswer: { "@type": "Answer", text: f.answer },
        })),
      }],
    };
  }

  if (path === "/tools/burn-multiple") {
    return {
      title: "Free Burn Multiple Calculator | FounderConsole",
      description: "Calculate your burn multiple in seconds: net new ARR against net burn, with the 2024 and 2025 SaaS benchmark bands. Free, no account required.",
      canonical: SITE_URL + "/tools/burn-multiple",
      bodyContent: buildBurnMultipleBodyContent(),
      jsonLd: [{
        "@context": "https://schema.org",
        "@type": "WebApplication",
        name: "Burn Multiple Calculator",
        url: SITE_URL + "/tools/burn-multiple",
        applicationCategory: "BusinessApplication",
        operatingSystem: "Web",
        offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
      }, {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        itemListElement: [
          { "@type": "ListItem", position: 1, name: "Home", item: `${SITE_URL}/` },
          { "@type": "ListItem", position: 2, name: "Runway calculator", item: `${SITE_URL}/tools/runway-calculator` },
          { "@type": "ListItem", position: 3, name: "Burn multiple calculator", item: `${SITE_URL}/tools/burn-multiple` },
        ],
      }],
    };
  }

  if (path === "/tools/dilution") {
    return {
      title: "Free Dilution Calculator with the Option Pool Shuffle | FounderConsole",
      description: "Calculate startup dilution exactly: founder, investor and option pool ownership after one round. The option pool top-up is modelled pre-money, as term sheets require. Free, no account required.",
      canonical: SITE_URL + "/tools/dilution",
      bodyContent: buildDilutionBodyContent(),
      jsonLd: [{
        "@context": "https://schema.org",
        "@type": "WebApplication",
        name: "Dilution Calculator",
        url: SITE_URL + "/tools/dilution",
        applicationCategory: "BusinessApplication",
        operatingSystem: "Web",
        offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
      }, {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        itemListElement: [
          { "@type": "ListItem", position: 1, name: "Home", item: `${SITE_URL}/` },
          { "@type": "ListItem", position: 2, name: "Runway calculator", item: `${SITE_URL}/tools/runway-calculator` },
          { "@type": "ListItem", position: 3, name: "Dilution calculator", item: `${SITE_URL}/tools/dilution` },
        ],
      }],
    };
  }
  if (path === "/tools/ltv-cac") {
    return {
      title: "Free LTV:CAC Calculator with CAC Payback | FounderConsole",
      description: "Calculate LTV, CAC, the LTV:CAC ratio and CAC payback months for SaaS. Graded separately against a named benchmark, because a good ratio with a bad payback is a cash-flow trap. Free, no account required.",
      canonical: SITE_URL + "/tools/ltv-cac",
      bodyContent: buildLtvCacBodyContent(),
      jsonLd: [{
        "@context": "https://schema.org",
        "@type": "WebApplication",
        name: "LTV:CAC Calculator",
        url: SITE_URL + "/tools/ltv-cac",
        applicationCategory: "BusinessApplication",
        operatingSystem: "Web",
        offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
      }, {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        itemListElement: [
          { "@type": "ListItem", position: 1, name: "Home", item: `${SITE_URL}/` },
          { "@type": "ListItem", position: 2, name: "Runway calculator", item: `${SITE_URL}/tools/runway-calculator` },
          { "@type": "ListItem", position: 3, name: "LTV:CAC calculator", item: `${SITE_URL}/tools/ltv-cac` },
        ],
      }],
    };
  }
  if (path === "/vs/runway-calculator-vs-spreadsheet") {
    return {
      title: "Runway Calculator vs Spreadsheet - Which Should You Use? | FounderConsole",
      description: "Runway calculator or spreadsheet? A sheet gives you full control and one cash-out date; a calculator gives you a benchmarked answer in seconds. Where each one wins, and when you outgrow both.",
      canonical: SITE_URL + "/vs/runway-calculator-vs-spreadsheet",
      bodyContent: buildVsRunwaySpreadsheetBodyContent(),
      jsonLd: [{
        "@context": "https://schema.org",
        "@type": "WebPage",
        name: "Runway Calculator vs Spreadsheet - Which Should You Use? | FounderConsole",
        description: "Where a spreadsheet wins for runway modelling, where it breaks, and what a calculator gives you instead.",
        url: SITE_URL + "/vs/runway-calculator-vs-spreadsheet",
        isPartOf: { "@type": "WebSite", name: "FounderConsole", url: SITE_URL },
      }, {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        itemListElement: [
          { "@type": "ListItem", position: 1, name: "Home", item: `${SITE_URL}/` },
          { "@type": "ListItem", position: 2, name: "Runway calculator", item: `${SITE_URL}/tools/runway-calculator` },
          { "@type": "ListItem", position: 3, name: "Runway calculator vs spreadsheet", item: `${SITE_URL}/vs/runway-calculator-vs-spreadsheet` },
        ],
      }],
    };
  }
  if (path === "/embed/survival") {
    return {
      title: "Startup Runway Widget — FounderConsole",
      description: "Embeddable startup runway calculator widget powered by FounderConsole.",
      canonical: `${SITE_URL}/embed/survival`,
      robots: "noindex, follow",
    };
  }

  if (path === "/survival-simulator") {
    return {
      title: "Startup Survival Simulator | FounderConsole",
      description: "Free startup survival probability calculator. Enter your financials and get AI-powered survival analysis with Monte Carlo simulations.",
      canonical: SITE_URL + "/survival-simulator",
      bodyContent: buildSurvivalSimulatorBodyContent(),
      jsonLd: [{
        "@context": "https://schema.org",
        "@type": "WebApplication",
        name: "Startup Survival Simulator",
        url: SITE_URL + "/survival-simulator",
        applicationCategory: "BusinessApplication",
        operatingSystem: "Web",
        offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
        description: "Free Monte Carlo simulation tool to calculate startup survival probability and runway projections.",
      }],
    };
  }

  if (path === "/default-alive") {
    return {
      title: "Default Alive or Default Dead? Free Calculator for Founders | FounderConsole",
      description: "Paul Graham's default alive test, as a calculator. Enter cash, revenue, expenses and growth rate to find out whether you reach profitability before the money runs out — and what it would take to flip the answer.",
      canonical: SITE_URL + "/default-alive",
      // Server-rendered body so the page is legible to crawlers and to the AI
      // assistants that increasingly answer "am I default alive" without
      // executing JavaScript. The interactive verdict is the client's job.
      bodyContent: `<article>
<h1>Default Alive or Default Dead?</h1>
<p>Paul Graham's test, in 30 seconds: at your current growth rate and current expenses, do you reach profitability before the money runs out?</p>
<h2>What default alive actually means</h2>
<p>Paul Graham coined the term in 2015. The question is simple: assuming your current expenses and current growth rate, would you make it to profitability on the money you already have?</p>
<p>If yes, you are default alive. Raising becomes a choice about going faster rather than a condition of survival, and that changes how you negotiate.</p>
<p>If no, you are default dead, and the important part is that most founders in that position do not know it. The number feels abstract until you watch the date land in a specific month.</p>
<h2>The caveat most calculators leave out</h2>
<p>The test assumes expenses stay flat while revenue compounds. Almost no growing company works that way — you hire, and costs climb with revenue. This calculator lets you switch expense growth on. If your verdict flips the moment you allow expenses to grow at all, the "alive" answer was fragile to begin with.</p>
<h2>The three levers</h2>
<p>If you come out default dead, there are only three things that change the answer: cut expenses, grow faster, or raise more. The calculator shows how far each one would have to move on your specific numbers — how large a cut, what growth rate, and how much cash.</p>
<h2>Why a single projection is not enough</h2>
<p>This calculator holds one growth rate steady. Real revenue is lumpy, and the month your biggest customer churns is not the average month. FounderConsole runs the same question thousands of times over your actual financials and returns the odds rather than one line.</p>
<h2>Related free tools</h2>
<p>Also try the <a href="/tools/runway-calculator">startup runway calculator</a> and the <a href="/survival-simulator">startup survival simulator</a> — both free, no account required. See <a href="/features">features</a> for the full platform. When you're ready for live data and ongoing forecasts, <a href="/signup">sign up for FounderConsole</a>.</p>
</article>`,
      jsonLd: [
        {
          "@context": "https://schema.org",
          "@type": "WebApplication",
          name: "Default Alive or Default Dead Calculator",
          url: SITE_URL + "/default-alive",
          applicationCategory: "BusinessApplication",
          operatingSystem: "Web",
          offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
          description: "Free calculator implementing Paul Graham's default alive test.",
          creator: { "@type": "Organization", name: "FounderConsole", url: SITE_URL },
        },
        {
          "@context": "https://schema.org",
          "@type": "FAQPage",
          mainEntity: [
            {
              "@type": "Question",
              name: "What does default alive mean?",
              acceptedAnswer: {
                "@type": "Answer",
                text: "A startup is default alive if, at its current growth rate and current expenses, it would reach profitability on the money it already has — without raising again.",
              },
            },
            {
              "@type": "Question",
              name: "What does default dead mean?",
              acceptedAnswer: {
                "@type": "Answer",
                text: "A startup is default dead if it runs out of cash before reaching profitability on its current trajectory. Survival then depends on raising more money, cutting expenses, or growing faster.",
              },
            },
            {
              "@type": "Question",
              name: "Who coined default alive or default dead?",
              acceptedAnswer: {
                "@type": "Answer",
                text: "Paul Graham, co-founder of Y Combinator, introduced the framing in a 2015 essay as a way for founders to know whether raising money is a choice or a necessity.",
              },
            },
          ],
        },
      ],
    };
  }

  const survivalShareMatch = path.match(/^\/survival\/([A-Za-z0-9_-]+)$/);
  if (survivalShareMatch) {
    const simId = survivalShareMatch[1];
    return {
      title: "My Startup Survival Score — FounderConsole",
      description: "I just simulated my startup's survival probability with FounderConsole. Run yours free in 60 seconds.",
      canonical: `${SITE_URL}/survival/${simId}`,
      ogType: "article",
      ogImage: `${SITE_URL}/api/survival-sim/og-image/${simId}.png`,
    };
  }

  if (path === "/privacy") {
    return {
      title: "Privacy Policy | FounderConsole",
      description: "FounderConsole privacy policy. How we handle your data.",
      canonical: SITE_URL + "/privacy",
      robots: "noindex, follow",
      bodyContent: buildPrivacyBodyContent(),
    };
  }

  if (path === "/terms") {
    return {
      title: "Terms of Service | FounderConsole",
      description: "FounderConsole terms of service.",
      canonical: SITE_URL + "/terms",
      robots: "noindex, follow",
      bodyContent: buildTermsBodyContent(),
    };
  }

  const blogMatch = path.match(/^\/blog\/(.+)$/);
  if (blogMatch) {
    const slug = blogMatch[1];
    const post = blogPosts.find((p) => p.slug === slug);
    if (post) {
      const isoDate = new Date(post.date).toISOString().split("T")[0];
      return {
        title: `${post.title} | FounderConsole`,
        description: post.excerpt,
        canonical: `${SITE_URL}/blog/${slug}`,
        ogType: "article",
        bodyContent: buildBlogPostBodyContent(slug) || undefined,
        jsonLd: [{
          "@context": "https://schema.org",
          "@type": "Article",
          headline: post.title,
          description: post.excerpt,
          datePublished: isoDate,
          author: { "@type": "Person", name: post.author },
          publisher: { "@type": "Organization", name: "FounderConsole", logo: { "@type": "ImageObject", url: OG_IMAGE } },
          image: OG_IMAGE,
          mainEntityOfPage: `${SITE_URL}/blog/${slug}`,
        }],
      };
    }
    // Unknown slug. Without this the request falls through to the untouched
    // index.html, which advertises "index, follow" and a canonical pointing at
    // the homepage — a soft 404 that invites Google to crawl every mistyped or
    // retired blog URL. The React app already renders "Article not found" here.
    return {
      title: "Article not found | FounderConsole",
      description: "The article you're looking for doesn't exist.",
      canonical: `${SITE_URL}/blog`,
      robots: "noindex, follow",
      statusCode: 404,
      bodyContent: `<article><h1>Article not found</h1><p>The article you're looking for doesn't exist.</p></article>`,
    };
  }

  // HAG-449: the hub itself. Everything above this line is a leaf, so `/tools`
  // and `/tools/` (trailing slash stripped above) land here instead of on the
  // 404 that used to own this path.
  if (path === "/tools") {
    return {
      title: "Free Startup Finance Tools — Runway, Burn, Dilution, LTV:CAC | FounderConsole",
      description: "Four free startup finance calculators and two more free tools. Runway, burn multiple, dilution and LTV:CAC — no account, no card, no demo call.",
      canonical: SITE_URL + "/tools",
      bodyContent: buildToolsIndexBodyContent(),
      jsonLd: [{
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        name: "Free Startup Finance Tools",
        url: SITE_URL + "/tools",
        hasPart: [
          `${SITE_URL}/tools/runway-calculator`,
          `${SITE_URL}/tools/burn-multiple`,
          `${SITE_URL}/tools/dilution`,
          `${SITE_URL}/tools/ltv-cac`,
          `${SITE_URL}/default-alive`,
          `${SITE_URL}/survival-simulator`,
          `${SITE_URL}/ai-cfo`,
        ].map((url) => ({ "@type": "WebPage", url })),
      }, {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        itemListElement: [
          { "@type": "ListItem", position: 1, name: "Home", item: `${SITE_URL}/` },
          { "@type": "ListItem", position: 2, name: "Free tools", item: `${SITE_URL}/tools` },
        ],
      }],
    };
  }

  // Known tool slugs return above and the hub returns just above. Anything else
  // under /tools is not a page: /tools/<unknown> used to fall through to the
  // homepage shell with HTTP 200 and must stay a real 404.
  if (path.startsWith("/tools/")) {
    return notFoundMeta(
      SITE_URL + "/tools",
      "This page does not exist. Browse the free startup finance tools instead.",
    );
  }

  return null;
}

function escapeHtml(str: string): string {
  return str.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

export function injectSEO(html: string, path: string): string {
  const meta = getPageMeta(path);
  if (!meta) {
    return html;
  }

  const ogType = meta.ogType || "website";
  const robots = meta.robots || "index, follow";
  const safeTitle = escapeHtml(meta.title);
  const safeDesc = escapeHtml(meta.description);

  let result = html;

  result = result.replace(/<title>[^<]*<\/title>/, `<title>${safeTitle}</title>`);

  result = result.replace(
    /<meta\s+name="description"\s+content="[^"]*"\s*\/?>/,
    `<meta name="description" content="${safeDesc}" />`
  );

  result = result.replace(
    /<link\s+rel="canonical"\s+href="[^"]*"\s*\/?>/,
    `<link rel="canonical" href="${meta.canonical}" />`
  );

  result = result.replace(
    /<meta\s+name="robots"\s+content="[^"]*"\s*\/?>/,
    `<meta name="robots" content="${robots}" />`
  );

  result = result.replace(
    /<meta\s+property="og:title"\s+content="[^"]*"\s*\/?>/,
    `<meta property="og:title" content="${safeTitle}" />`
  );
  result = result.replace(
    /<meta\s+property="og:description"\s+content="[^"]*"\s*\/?>/,
    `<meta property="og:description" content="${safeDesc}" />`
  );
  result = result.replace(
    /<meta\s+property="og:url"\s+content="[^"]*"\s*\/?>/,
    `<meta property="og:url" content="${meta.canonical}" />`
  );
  result = result.replace(
    /<meta\s+property="og:type"\s+content="[^"]*"\s*\/?>/,
    `<meta property="og:type" content="${ogType}" />`
  );

  result = result.replace(
    /<meta\s+name="twitter:title"\s+content="[^"]*"\s*\/?>/,
    `<meta name="twitter:title" content="${safeTitle}" />`
  );
  result = result.replace(
    /<meta\s+name="twitter:description"\s+content="[^"]*"\s*\/?>/,
    `<meta name="twitter:description" content="${safeDesc}" />`
  );

  if (meta.ogImage) {
    const safeImg = escapeHtml(meta.ogImage);
    result = result.replace(
      /<meta\s+property="og:image"\s+content="[^"]*"\s*\/?>/,
      `<meta property="og:image" content="${safeImg}" />`
    );
    result = result.replace(
      /<meta\s+name="twitter:image"\s+content="[^"]*"\s*\/?>/,
      `<meta name="twitter:image" content="${safeImg}" />`
    );
  }

  // Always clear shell homepage JSON-LD when this path has none of its own,
  // otherwise /pricing /privacy /terms (etc.) inherit Organization+SoftwareApplication for "/".
  {
    const newLdScripts =
      meta.jsonLd && meta.jsonLd.length > 0
        ? meta.jsonLd.map((ld) => `<script type="application/ld+json">${JSON.stringify(ld)}</script>`).join("\n    ")
        : "";
    let replaced = false;
    result = result.replace(/<script\s+type="application\/ld\+json">[\s\S]*?<\/script>/g, () => {
      if (!replaced) {
        replaced = true;
        return newLdScripts;
      }
      return "";
    });
  }

  if (meta.bodyContent) {
    // Rendered INSIDE #root, and visibly.
    //
    // This content used to sit outside #root at left:-9999px — present for
    // crawlers, invisible to people. The consequence was that a human saw a
    // blank white page until ~890KB of JavaScript downloaded and parsed, which
    // on a mid-tier phone is several seconds. Measured behaviour matched:
    // 21 of 21 mobile visitors left without reaching a second page, and typical
    // sessions were 4-20 seconds — at or below time-to-interactive.
    //
    // createRoot() (not hydrateRoot) discards whatever is in #root on its first
    // render, so this needs no hydration, no matching markup, and no extra
    // JavaScript: the browser paints real text as soon as CSS lands, and React
    // silently replaces it on mount.
    //
    // Styles are inline on purpose. The stylesheet is render-blocking and
    // large; relying on a class from it would reintroduce the very dependency
    // this is meant to remove.
    //
    // Bonus: if JS fails outright — stale chunk, blocked bundle, dead network —
    // the visitor now keeps a readable page instead of a white screen.
    // `${citationBlock}` is appended HERE, at the single point where every route with a
    // bodyContent emits one, rather than from any individual page builder. That is what
    // makes "every prerendered page can be cited" a property of the code rather than a
    // list of routes somebody remembered to update — the failure mode `blogPosts` had in
    // `seo-data.ts`, where a second hand-maintained list silently fell two posts behind.
    const preview = `<div id="ssr-content" style="max-width:46rem;margin:0 auto;padding:5rem 1.25rem;font-family:Inter,system-ui,-apple-system,Segoe UI,sans-serif;line-height:1.65;color:#1a1d24">${meta.bodyContent}${citationBlock}</div>`;
    result = result.replace('<div id="root"></div>', `<div id="root">${preview}</div>`);
  }

  return result;
}
