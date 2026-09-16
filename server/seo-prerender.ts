import { blogPosts, blogPostContent } from "./seo-data";
// Relative, not the "@/" alias: this module is bundled by esbuild from
// server/index.ts and a path alias is one more thing that can silently resolve
// differently at build time. runway-industries.ts is pure data with no imports
// of its own, so pulling it in costs the server bundle nothing and means the
// eight vertical pages cannot drift between what the page renders and what a
// crawler is served.
import { RUNWAY_INDUSTRIES, RUNWAY_RELATED_FREE_TOOLS } from "../client/src/data/runway-industries";

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
}

const landingFaqs = [
  { q: "What is FounderConsole?", a: "FounderConsole is an AI-powered financial intelligence platform for startups. It connects your financial data, builds a digital twin of your company, runs Monte Carlo simulations, and provides AI-powered strategic recommendations." },
  { q: "Is FounderConsole free?", a: "Yes. All features are free during the public beta, including Monte Carlo simulations, AI copilot, cap table management, 37 data connectors, and board deck generation. No credit card is required." },
  { q: "How does FounderConsole help with fundraising?", a: "FounderConsole includes a Fundraising OS with cap table management, dilution modeling, investor CRM, SAFE conversion modeling, and exit waterfall analysis." },
  { q: "What data sources can I connect?", a: "FounderConsole supports 37 data connectors including Stripe, QuickBooks, Xero, Mercury, Brex, Plaid, Gusto, HubSpot, Shopify, Salesforce, and more." },
  { q: "What is a Monte Carlo simulation?", a: "Monte Carlo simulation runs your financial model thousands of times with slightly different inputs each time, producing a probability distribution instead of a single forecast." },
  { q: "How is this different from a spreadsheet?", a: "Spreadsheets give you one forecast. FounderConsole runs thousands of scenarios, accounts for uncertainty, connects to live data, and uses AI to generate insights." },
  { q: "What is a startup digital twin?", a: "A digital twin is a continuously updated virtual representation of your company that reflects your current financial reality without manual updates." },
  { q: "How long does setup take?", a: "Most founders are up and running in under five minutes. Connect your primary data source and FounderConsole automatically builds your digital twin." },
];

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
<p>No account required. Calculate <a href="/tools/runway-calculator">startup runway</a>, run Paul Graham's <a href="/default-alive">default alive test</a>, or estimate survival odds with the <a href="/survival-simulator">startup survival simulator</a>. See the full product on <a href="/features">features</a> and what's free during beta on <a href="/pricing">pricing</a>. When you're ready for live data and ongoing forecasts, <a href="/auth">get started free</a>.</p>
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
  const content = blogPostContent[slug];
  if (!post) return null;
  const paragraphs = content || [];
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
<p>Also try the <a href="/default-alive">default alive or default dead</a> test and the <a href="/survival-simulator">startup survival simulator</a> — both free, no account required. Explore <a href="/features">features</a> when you want the full product. When you're ready for live data and ongoing forecasts, <a href="/auth">sign up for FounderConsole</a>.</p>
<h2>Industry runway calculators</h2>
<ul>${industryLinks}</ul>
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
<p>Monte Carlo simulation with P10/P50/P90 confidence bands, the AI copilot, Truth Scan data validation, cap table and dilution modelling, the fundraising CRM, board deck generation, and all 37 data connectors. See the full list on <a href="/features">features</a>.</p>
<h2>What happens after the beta</h2>
<p>Paid tiers will be introduced once the beta ends. Anyone using FounderConsole during the beta keeps access to their data and will be told well before anything changes.</p>
<h2>Free tools that need no account at all</h2>
<p>Try these before you sign up — results in under a minute, no email required to see the answer:</p>
<ul>
<li><a href="/tools/runway-calculator">Startup runway calculator</a> — months of runway and a cash-out date from your numbers</li>
<li><a href="/default-alive">Default alive or default dead</a> — Paul Graham's test as a calculator</li>
<li><a href="/survival-simulator">Startup survival simulator</a> — 1,000 Monte Carlo runs for survival probability</li>
</ul>
<p>When you're ready for live connectors and ongoing forecasts, <a href="/auth">get started free</a> — still no credit card during beta.</p>
</article>`;
}

function buildDemoBodyContent(): string {
  return `<article>
<h1>See FounderConsole in action</h1>
<p>An interactive walkthrough of the product using a sample company, so you can see how simulation, the AI copilot and the fundraising tools fit together before connecting any of your own data.</p>
<h2>What the demo covers</h2>
<p>Building a digital twin from connected financial data, running a Monte Carlo simulation to get a probabilistic runway rather than a single number, asking the copilot a question about the model, and exporting a board-ready summary.</p>
<h2>Prefer to try something immediately</h2>
<p>The runway calculator and the default alive test are free, need no account, and give you a real answer about your own numbers in under a minute.</p>
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
<p>Try free tools with no account: the <a href="/tools/runway-calculator">startup runway calculator</a>, the <a href="/survival-simulator">startup survival simulator</a>, or the <a href="/default-alive">default alive test</a> — answers from your numbers in under a minute. When you are ready for live data and ongoing forecasts, <a href="/auth">get started free</a>.</p>
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
<p><strong>Connect everything. Auto-sync.</strong> 37 real OAuth2 integrations with the tools founders already use. QuickBooks, Stripe, Gusto, Mercury, Brex, Plaid, and more. No CSV imports or screen scraping required.</p>
<ul>
<li>37 integrations with one-click OAuth connections</li>
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
<p><a href="/auth">Get Started Free</a> · Prefer a quick answer first? Try the <a href="/tools/runway-calculator">runway calculator</a>, the <a href="/default-alive">default alive test</a>, or the <a href="/survival-simulator">survival simulator</a> with no signup.</p>
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
<h2>Related free tools</h2>
<p>Try these with no account: the <a href="/tools/runway-calculator">startup runway calculator</a>, the <a href="/survival-simulator">startup survival simulator</a>, or the <a href="/default-alive">default alive test</a>. See the full product on <a href="/features">features</a>. When you are ready for live data and ongoing forecasts, <a href="/auth">get started free</a>.</p>
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
<p>Try a free tool with no signup: <a href="/tools/runway-calculator">runway calculator</a>, <a href="/default-alive">default alive test</a>, or <a href="/survival-simulator">survival simulator</a>. Browse <a href="/features">features</a>, <a href="/contact">get in touch</a>, or <a href="/auth">get started free</a>.</p>
</article>`;
}

const faqSections = [
  {
    title: "Getting Started",
    items: [
      { q: "What is FounderConsole?", a: "FounderConsole is an AI-powered financial intelligence platform built specifically for startup founders. It replaces spreadsheet-based forecasting with Monte Carlo simulations, giving you probability-based outcomes (P10/P50/P90) instead of a single-point guess. It includes an AI copilot, fundraising CRM, cap table management, 37 data connectors, and strategic briefings — everything a founder needs to make data-driven decisions." },
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
<p>Try a free tool with no account required: the <a href="/tools/runway-calculator">startup runway calculator</a>, the <a href="/survival-simulator">startup survival simulator</a>, or the <a href="/default-alive">default alive test</a>. When you want live connected data, <a href="/auth">get started free</a>.</p>
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
<p>Try free tools with no account: the <a href="/tools/runway-calculator">startup runway calculator</a>, the <a href="/default-alive">default alive test</a>, or the <a href="/survival-simulator">startup survival simulator</a>. See what is included on <a href="/features">features</a> and <a href="/pricing">pricing</a>, or walk through the <a href="/demo">interactive demo</a>. When you are ready for live data and ongoing forecasts, <a href="/auth">get started free</a>.</p>
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
<p>Also try the <a href="/tools/runway-calculator">startup runway calculator</a> and the <a href="/default-alive">default alive or default dead</a> test — both free, no account required. When you're ready for live data and ongoing forecasts, <a href="/auth">sign up for FounderConsole</a>.</p>
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
<p>Also try the ${relatedList} — all free, no account required. When you're ready for live data and ongoing forecasts, <a href="/auth">sign up for FounderConsole</a>.</p>
<h2>Other industry runway calculators</h2>
<ul>${siblings}</ul>
</article>`;
}

function getPageMeta(path: string): PageMeta | null {
  if (path === "/" || path === "") {
    return {
      title: "FounderConsole — AI Decision Simulator for Founders",
      description: "FounderConsole is the AI-powered decision simulator for startup founders. Monte Carlo simulations, AI copilot, fundraising CRM, and 37 data connectors — replace spreadsheets with simulations.",
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
          sameAs: ["https://twitter.com/founderconsole", "https://linkedin.com/company/founderconsole", "https://github.com/founderconsole"],
        },
        {
          "@context": "https://schema.org",
          "@type": "SoftwareApplication",
          name: "FounderConsole",
          applicationCategory: "BusinessApplication",
          operatingSystem: "Web",
          url: SITE_URL,
          offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
          featureList: "Monte Carlo Simulation, AI Copilot, Fundraising CRM, Cap Table Management, 37 Data Connectors, Digital Twin",
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
      description: "Monte Carlo simulation engine, multi-LLM AI copilot, Truth Scan data validation, Fundraising OS with CRM, 37 data connectors, and AI strategic briefings.",
      canonical: SITE_URL + "/features",
      bodyContent: buildFeaturesBodyContent(),
      jsonLd: [{
        "@context": "https://schema.org",
        "@type": "WebPage",
        name: "FounderConsole Features",
        description: "Complete feature overview of FounderConsole: Monte Carlo simulations, AI copilot, data validation, fundraising tools, and 37 data connectors.",
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
      description: "See FounderConsole in action with an interactive demo.",
      canonical: SITE_URL + "/demo",
      bodyContent: buildDemoBodyContent(),
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
      // Unknown vertical renders the app's not-found page. Saying "index" here
      // would ask Google to index a 404 that answers with HTTP 200.
      return {
        title: "Page not found | FounderConsole",
        description: "This page does not exist. Browse the free runway calculator and industry benchmarks instead.",
        canonical: SITE_URL + "/tools/runway-calculator",
        robots: "noindex, follow",
      };
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
<p>Also try the <a href="/tools/runway-calculator">startup runway calculator</a> and the <a href="/survival-simulator">startup survival simulator</a> — both free, no account required. See <a href="/features">features</a> for the full platform. When you're ready for live data and ongoing forecasts, <a href="/auth">sign up for FounderConsole</a>.</p>
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
    };
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
    const preview = `<div id="ssr-content" style="max-width:46rem;margin:0 auto;padding:5rem 1.25rem;font-family:Inter,system-ui,-apple-system,Segoe UI,sans-serif;line-height:1.65;color:#1a1d24">${meta.bodyContent}</div>`;
    result = result.replace('<div id="root"></div>', `<div id="root">${preview}</div>`);
  }

  return result;
}
