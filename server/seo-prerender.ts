import { blogPosts, blogPostContent } from "./seo-data";
// Relative, not the "@/" alias: this module is bundled by esbuild from
// server/index.ts and a path alias is one more thing that can silently resolve
// differently at build time. runway-industries.ts is pure data with no imports
// of its own, so pulling it in costs the server bundle nothing and means the
// eight vertical pages cannot drift between what the page renders and what a
// crawler is served.
import { RUNWAY_INDUSTRIES } from "../client/src/data/runway-industries";

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
<p>Monte Carlo simulation with P10/P50/P90 confidence bands, the AI copilot, Truth Scan data validation, cap table and dilution modelling, the fundraising CRM, board deck generation, and all 37 data connectors.</p>
<h2>What happens after the beta</h2>
<p>Paid tiers will be introduced once the beta ends. Anyone using FounderConsole during the beta keeps access to their data and will be told well before anything changes.</p>
<h2>Free tools that need no account at all</h2>
<p>The runway calculator and the default alive test are open to anyone, with no signup and no email required to see your result.</p>
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
<p>The free runway calculator gives you months of runway and a cash-out date from four numbers, with no account required.</p>
</article>`;
}

function buildIndustryBodyContent(slug: string): string | null {
  const ind = RUNWAY_INDUSTRIES.find((i) => i.slug === slug);
  if (!ind) return null;
  const notes = ind.notes.map((n) => `<li>${esc(n)}</li>`).join("");
  const risks = ind.primaryRiskFactors.map((r) => `<li>${esc(r)}</li>`).join("");
  return `<article>
<h1>${esc(ind.name)}</h1>
<p>Calculate runway against real ${esc(ind.shortName.toLowerCase())} benchmarks. The relevant benchmark here is ${esc(ind.benchmarkRunway)}.</p>
<h2>What ${esc(ind.shortName)} founders should watch</h2>
<ul>${notes}</ul>
<h2>Burn multiple</h2>
<p>${esc(ind.burnMultipleNotes)}</p>
<h2>When to raise</h2>
<p>${esc(ind.fundraisingNotes)}</p>
<h2>What usually goes wrong</h2>
<ul>${risks}</ul>
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
<p><a href="/auth">Get Started Free</a> · Prefer a quick answer first? Try the <a href="/tools/runway-calculator">runway calculator</a> or <a href="/default-alive">default alive test</a> with no signup.</p>
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
<h3>Transparency</h3>
<p>Every recommendation comes with an explanation. No black boxes. You should always understand why.</p>
<h3>Data-Driven</h3>
<p>Confidence intervals make risk measurable. Probability replaces intuition when the stakes are highest.</p>
<h3>Founder-First</h3>
<p>Built by founders who've lived the uncertainty. Every feature exists because we needed it ourselves.</p>
<h3>Privacy-First</h3>
<p>Your financial data is encrypted at rest and in transit. Read-only integrations. No data resale. Ever.</p>
<h2>Join us on our mission</h2>
<p>We're building the financial intelligence layer for the next generation of startups.</p>
<p><a href="/contact">Contact us</a> · Or try the <a href="/tools/runway-calculator">runway calculator</a> free, no signup.</p>
</article>`;
}

function buildFaqBodyContent(): string {
  return `<article>
<h1>Frequently Asked Questions</h1>
<p>Clear answers, organized by what founders actually ask.</p>

<h2>Getting Started</h2>
<h3>What is FounderConsole?</h3>
<p>FounderConsole is an AI-powered financial intelligence platform built specifically for startup founders. It replaces spreadsheet-based forecasting with Monte Carlo simulations, giving you probability-based outcomes (P10/P50/P90) instead of a single-point guess. It includes an AI copilot, fundraising CRM, cap table management, 37 data connectors, and strategic briefings — everything a founder needs to make data-driven decisions.</p>
<h3>How does FounderConsole help founders?</h3>
<p>FounderConsole helps founders by transforming financial uncertainty into measurable probability. Instead of relying on gut feelings, you get Monte Carlo simulations that show the range of possible outcomes, an AI copilot that answers financial questions using your real data, automated data validation (Truth Scan) that catches errors before they reach your board, and strategic briefings that explain your risks and opportunities in plain English. It reduces the time spent on financial analysis from days to minutes.</p>
<h3>What metrics does FounderConsole track?</h3>
<p>FounderConsole tracks over 24 financial health metrics including MRR, ARR, runway, burn rate, CAC, LTV, LTV:CAC ratio, churn rate, gross margin, NRR, ARPU, active customers, and headcount. It automatically derives metrics from connected data sources, validates them with cross-reference checks, and flags anomalies using Z-score detection. Each metric includes a confidence score showing how reliable the data is.</p>
<h3>Is FounderConsole free?</h3>
<p>Yes — FounderConsole is completely free while we're in early access. Every feature is unlocked and no credit card is required. The plans on our pricing page (Starter $29, Growth $49, Scale $99 per month) are our planned pricing for when we exit early access; we'll give plenty of notice before anything changes.</p>
<h3>What is a startup digital twin?</h3>
<p>A startup digital twin is a continuously-updated virtual representation of your company inside FounderConsole. It integrates your real financial data, simulation results, strategic decisions, and alerts into a single live model with health scoring and risk indicators. Think of it as a real-time mirror of your company's financial state that lets you test scenarios and see impacts before making actual decisions. The twin tracks metrics like cash balance, burn rate, revenue, and runway, and alerts you when key indicators change.</p>
<h3>How do I get started?</h3>
<p>Sign up for free (no credit card required), connect one or more data sources like QuickBooks, Stripe, or Mercury, and you'll have a baseline forecast with confidence intervals within 5 minutes.</p>
<h3>Is there a demo I can try?</h3>
<p>Yes — you can sign in with demo credentials or watch our product walkthrough on the Demo page. The demo includes sample company data so you can explore simulations, the AI copilot, and reporting features without connecting your own data.</p>

<h2>Simulation Engine</h2>
<h3>How is this different from a spreadsheet forecast?</h3>
<p>Spreadsheets typically show one outcome. Monte Carlo simulation shows the range of possible outcomes (P10/P50/P90) and the probability of hitting key targets, while explainability tells you which variables are driving the risk.</p>
<h3>Why do confidence intervals matter?</h3>
<p>Confidence intervals make risk measurable. Instead of hoping your single-point forecast is right, you can quantify the probability of different outcomes and make decisions with clearer tradeoffs. Investors and board members understand probability — gut feelings, not so much.</p>
<h3>How many simulations can I run?</h3>
<p>Each Monte Carlo simulation runs 100 to 10,000 iterations depending on your settings. While we're in early access you can run unlimited scenarios, compare them side by side, and version your work over time.</p>

<h2>Data &amp; Security</h2>
<h3>How is my financial data protected?</h3>
<p>All data is encrypted using AES-256 at rest and TLS in transit. Integrations use OAuth2 with read-only access where possible. Credentials are stored with envelope encryption. We never sell or share your data with third parties.</p>
<h3>Where is my data stored?</h3>
<p>Your data is stored in US-based PostgreSQL databases with automated daily backups and point-in-time recovery. Infrastructure is hosted on secure, SOC2-compliant cloud providers with strict access controls and audit logging.</p>
<h3>What compliance standards do you follow?</h3>
<p>We are fully GDPR compliant and are actively working toward SOC2 Type II certification. We conduct regular security audits, enforce role-based access controls, and maintain detailed audit logs of all data access. You can request a full data export or deletion at any time.</p>

<h2>Pricing &amp; Plans</h2>
<h3>Do I need to pay anything right now?</h3>
<p>No. Everything is free while we're in early access — every feature is unlocked, with no credit card required. We'll announce paid plans well in advance before anything changes.</p>
<h3>What will the paid plans cost later?</h3>
<p>Our planned pricing is Starter $29/month (50 simulations, 100 copilot messages, 2 connectors, Truth Scan, benchmarks), Growth $49/month (up to 3 companies, unlimited simulations and copilot, 10 connectors, Fundraising OS, board deck export), and Scale $99/month (unlimited companies and connectors, AI-agent Flight Simulator, Digital Twin, Investor Room, and cross-company intelligence). None of this is active yet — it's what we intend to charge once we exit early access.</p>
<h3>Do you offer enterprise pricing?</h3>
<p>Yes — if you need custom integrations, dedicated support, or team-level access controls, contact us to discuss enterprise options.</p>

<h2>Still have questions?</h2>
<p>We're happy to help. Reach out and we'll get back to you within 24 hours.</p>
<p><a href="/contact">Contact Us</a></p>
</article>`;
}

function buildContactBodyContent(): string {
  return `<article>
<h1>Get in Touch</h1>
<p>Questions, feedback, or partnership inquiries — we'd love to hear from you.</p>
<h2>Send us a message</h2>
<p>Use the contact form on this page with your name, email, subject (General Inquiry, Sales, Support, or Partnership), and message. We use it for product questions, support, sales, and partnership requests.</p>
<h2>Contact info</h2>
<p><strong>Email:</strong> <a href="mailto:hello@founderconsole.ai">hello@founderconsole.ai</a></p>
<p><strong>Response time:</strong> Within 24 hours</p>
<p>Prefer to try the product first? The <a href="/tools/runway-calculator">runway calculator</a> and <a href="/default-alive">default alive test</a> need no account.</p>
</article>`;
}

function buildPrivacyBodyContent(): string {
  return `<article>
<h1>Privacy Policy</h1>
<p>Last updated: March 2026</p>
<p>FounderConsole ("we", "our", "us") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, store, and protect your information when you use our platform.</p>

<h2>Information We Collect</h2>
<p>We collect the following types of information:</p>
<ul>
<li><strong>Account Information:</strong> Your email address, name, and password when you register.</li>
<li><strong>Company Financial Data:</strong> Revenue, expenses, cash balances, invoices, and other financial metrics you enter manually or sync through connected integrations (QuickBooks, Stripe, Gusto).</li>
<li><strong>Usage Data:</strong> Pages visited, features used, simulation runs, and interaction patterns to improve the platform.</li>
<li><strong>Authentication Data:</strong> OAuth tokens when you sign in via Google.</li>
</ul>

<h2>How We Use Your Data</h2>
<p>Your data is used to:</p>
<ul>
<li>Provide financial dashboards, simulations, and AI-powered insights.</li>
<li>Run Monte Carlo simulations and scenario modeling on your financial data.</li>
<li>Generate recommendations and risk assessments through our AI copilot.</li>
<li>Send transactional emails (verification, password reset, alerts).</li>
<li>Improve the platform based on aggregate, anonymized usage patterns.</li>
</ul>
<p>We never sell your data to third parties. Your financial data is only used to provide services directly to you.</p>

<h2>Third-Party Services</h2>
<p>We use the following third-party services:</p>
<ul>
<li><strong>Google Analytics:</strong> Website traffic measurement and visitor behavior analysis. Google may use cookies and collect IP addresses, browser type, pages visited, and session duration. Data is processed by Google LLC under their Privacy Policy.</li>
<li><strong>Meta (Facebook) Pixel:</strong> Conversion tracking and audience measurement on our marketing pages. Meta may collect page visit data, browser information, and IP addresses. Data is processed by Meta Platforms, Inc. under their Privacy Policy. You can opt out via Facebook Ad Settings.</li>
<li><strong>PostHog:</strong> Product analytics to understand feature usage (anonymized).</li>
<li><strong>Google OAuth:</strong> Social login authentication.</li>
<li><strong>QuickBooks Online:</strong> Sync accounting data (P&amp;L, balance sheet, invoices) when you connect your account.</li>
<li><strong>Stripe:</strong> Sync payment and revenue data when you connect your account.</li>
<li><strong>Gusto:</strong> Sync payroll data when you connect your account.</li>
<li><strong>Resend:</strong> Transactional email delivery.</li>
<li><strong>OpenAI, Anthropic, Google Gemini:</strong> AI model providers for copilot and analysis features. Financial data may be sent to these providers to generate insights; data is not retained by them beyond the request.</li>
</ul>

<h2>Data Storage &amp; Security</h2>
<p>Your data is stored in an encrypted PostgreSQL database. We implement the following security measures:</p>
<ul>
<li>Passwords are hashed using bcrypt before storage.</li>
<li>All connections use HTTPS/TLS encryption in transit.</li>
<li>Integration credentials (OAuth tokens) are stored encrypted.</li>
<li>JWT-based authentication with httpOnly cookies.</li>
<li>CSRF protection on all state-changing requests.</li>
<li>Rate limiting on authentication and simulation endpoints.</li>
</ul>

<h2>Data Retention</h2>
<p>We retain your data for as long as your account is active. Specifically:</p>
<ul>
<li>Account data is retained until you request deletion.</li>
<li>Financial data and simulation results are retained while your account is active.</li>
<li>Analytics data is retained in anonymized form for up to 24 months.</li>
<li>Upon account deletion, all personally identifiable data is permanently removed within 30 days.</li>
</ul>

<h2>Your Rights</h2>
<p>You have the right to:</p>
<ul>
<li><strong>Access:</strong> Request a copy of all data we hold about you.</li>
<li><strong>Correct:</strong> Update or correct inaccurate data.</li>
<li><strong>Delete:</strong> Request permanent deletion of your account and all associated data.</li>
<li><strong>Export:</strong> Download your financial data in standard formats (CSV, PDF).</li>
<li><strong>Withdraw Consent:</strong> Disconnect integrations or opt out of analytics at any time.</li>
</ul>
<p>To exercise any of these rights, contact us at the email below.</p>

<h2>Cookies</h2>
<p>We use the following cookies:</p>
<ul>
<li><strong>Session Cookies:</strong> Essential for authentication and CSRF protection.</li>
<li><strong>Google Analytics (_ga, _gid):</strong> Traffic measurement and visitor behavior analysis. Retained for up to 2 years. Can be blocked without affecting functionality.</li>
<li><strong>Meta Pixel (_fbp):</strong> Conversion tracking on marketing pages. Retained for up to 90 days. Active on public marketing pages and the subscription checkout confirmation, not elsewhere inside the app. Can be blocked without affecting functionality.</li>
<li><strong>PostHog Analytics:</strong> Anonymous usage tracking to improve the platform. Can be blocked without affecting functionality.</li>
</ul>

<h2>Contact</h2>
<p>If you have questions about this Privacy Policy or wish to exercise your data rights, contact us at <a href="mailto:hello@founderconsole.ai">hello@founderconsole.ai</a>.</p>
<p><a href="/terms">Terms of Service</a> · <a href="/">Back to FounderConsole</a></p>
</article>`;
}

function buildTermsBodyContent(): string {
  return `<article>
<h1>Terms of Service</h1>
<p>Last updated: July 2026</p>
<p>These Terms of Service ("Terms") govern your use of FounderConsole ("the Service"), operated by FounderConsole ("we", "our", "us"). By accessing or using the Service, you agree to be bound by these Terms.</p>

<h2>Service Description</h2>
<p>FounderConsole is an AI-powered financial intelligence platform for startups. The Service provides:</p>
<ul>
<li>Financial dashboards and KPI tracking.</li>
<li>Monte Carlo simulations and scenario modeling.</li>
<li>AI-powered copilot for financial analysis and recommendations.</li>
<li>Data integrations with accounting, payroll, and payment platforms.</li>
<li>Cap table management and fundraising tools.</li>
</ul>

<h2>Subscriptions &amp; Billing</h2>
<ul>
<li><strong>Plans:</strong> The Service offers a Free plan and paid subscription plans (currently Starter, Growth, and Scale), billed monthly or annually. Current pricing and plan features are shown on our <a href="/pricing">pricing page</a> and in-app.</li>
<li><strong>Free trial:</strong> New accounts may start a one-time 30-day free trial with full feature access. No payment method is required to start a trial. When the trial ends, your account reverts to the Free plan unless you subscribe.</li>
<li><strong>Payment:</strong> Payments are processed securely by Stripe. We do not store your full card or payment details on our servers.</li>
<li><strong>Renewal:</strong> Subscriptions renew automatically at the end of each billing period (monthly or annual) until cancelled. Charges may be converted to your local currency at the prevailing exchange rate.</li>
<li><strong>Cancellation:</strong> You may cancel at any time through the in-app billing portal. Cancellation takes effect at the end of the current billing period; you keep paid access until then.</li>
<li><strong>Refunds:</strong> If you are unhappy with your first subscription payment, contact us within 14 days of that payment for a full refund. Renewal payments and partial billing periods are otherwise non-refundable, except where required by law.</li>
<li><strong>Plan changes:</strong> Upgrades take effect immediately with prorated billing handled by Stripe; downgrades take effect at the next billing period.</li>
<li><strong>Price changes:</strong> We may change prices with at least 30 days' notice by email; changes apply from your next billing period after the notice period.</li>
<li><strong>Failed payments:</strong> If a renewal payment fails, we may retry it and may downgrade or suspend paid features until payment succeeds.</li>
<li><strong>Founding accounts:</strong> Accounts created before our paid plans launched retain complimentary access at our discretion; we will give at least 30 days' notice before changing this.</li>
</ul>

<h2>Service Disclaimer</h2>
<ul>
<li>The Service is under active development and may contain bugs, errors, or incomplete functionality.</li>
<li>Features may be added, modified, or removed; material changes affecting paid plans will be communicated with reasonable notice.</li>
<li>Data loss, while unlikely, is possible. We maintain backups, but recommend keeping your own copies of critical financial records.</li>
<li>AI-generated insights, simulations, and recommendations are informational only and should not be the sole basis for financial, investment, or business decisions. FounderConsole does not provide financial, legal, or investment advice.</li>
</ul>

<h2>Account Terms</h2>
<ul>
<li>You must be at least <strong>18 years of age</strong> to use the Service.</li>
<li>You are responsible for maintaining the confidentiality of your login credentials.</li>
<li>You are responsible for all activity that occurs under your account.</li>
<li>You must provide accurate and complete information when creating your account.</li>
<li>You must notify us immediately of any unauthorized use of your account.</li>
<li>One person or legal entity may not maintain more than one account.</li>
</ul>

<h2>Acceptable Use</h2>
<p>You agree to:</p>
<ul>
<li>Provide accurate information when creating your account.</li>
<li>Keep your login credentials secure and confidential.</li>
<li>Use the Service only for lawful business purposes.</li>
<li>Not attempt to reverse-engineer, decompile, or exploit the Service.</li>
<li>Not upload malicious content, malware, or automated scripts.</li>
<li>Not use the Service to store or process data you do not have the right to use.</li>
<li>Not share your account with unauthorized users.</li>
</ul>

<h2>Limitation of Liability</h2>
<p>To the maximum extent permitted by law:</p>
<ul>
<li>The Service is provided <strong>"as is"</strong> and <strong>"as available"</strong> without warranties of any kind.</li>
<li>We do not guarantee the accuracy, completeness, or reliability of AI-generated insights, simulations, or recommendations.</li>
<li>We are not liable for any direct, indirect, incidental, or consequential damages arising from your use of the Service.</li>
<li>Our total liability is limited to the greater of the amount you paid for the Service in the 12 months preceding the claim, or US $100.</li>
<li>You are solely responsible for financial decisions made based on information from the Service.</li>
</ul>

<h2>Data Rights</h2>
<ul>
<li><strong>Your Data:</strong> You retain full ownership of all data you upload to the Service, including financial records, documents, and company information.</li>
<li><strong>Our License:</strong> By using the Service, you grant us a limited license to process, store, and analyze your data solely to provide the Service to you.</li>
<li>We will not sell, rent, or share your data with third parties except as described in our <a href="/privacy">Privacy Policy</a>.</li>
<li>You may export your data at any time using the built-in export features.</li>
<li>We may use anonymized, aggregate data to improve the Service.</li>
</ul>

<h2>Intellectual Property</h2>
<ul>
<li><strong>Our IP:</strong> The Service, including its design, code, algorithms, and AI models, is owned by FounderConsole. You may not copy, modify, or distribute any part of the Service.</li>
<li><strong>Your Data:</strong> You retain full ownership of all financial data, documents, and content you upload to the Service. We claim no ownership over your data.</li>
<li>We may use anonymized, aggregate data to improve the Service.</li>
</ul>

<h2>Termination</h2>
<ul>
<li>You may delete your account at any time by contacting us; any active subscription is cancelled effective at the end of the current billing period.</li>
<li>We may suspend or terminate your account if you violate these Terms.</li>
<li>Upon termination, you may request an export of your data within 30 days.</li>
<li>After 30 days, your data will be permanently deleted.</li>
<li>Provisions regarding liability, intellectual property, and governing law survive termination.</li>
</ul>

<h2>Changes to Terms</h2>
<ul>
<li>We may update these Terms from time to time to reflect changes in the Service or legal requirements.</li>
<li>We will notify you of material changes by email at least 30 days before they take effect.</li>
<li>Continued use of the Service after changes take effect constitutes acceptance of the updated Terms.</li>
<li>If you do not agree to the updated Terms, you may terminate your account before they take effect.</li>
</ul>

<h2>Governing Law</h2>
<p>These Terms are governed by and construed in accordance with the laws of the State of California, United States, without regard to conflict of law principles. Any disputes arising from these Terms shall be resolved in the state or federal courts located in San Francisco County, California.</p>

<h2>Contact</h2>
<p>For questions about these Terms, contact us at <a href="mailto:hello@founderconsole.ai">hello@founderconsole.ai</a>.</p>
<p><a href="/privacy">Privacy Policy</a> · <a href="/">Back to FounderConsole</a></p>
</article>`;
}

function buildSurvivalSimulatorBodyContent(): string {
  return `<article>
<h1>Startup Survival Simulator</h1>
<p>Free tool — no login required. Run 1,000 Monte Carlo simulations to calculate your startup's probability of survival. Get AI-powered recommendations in seconds.</p>
<p>No data stored · Results in about 3 seconds · 1,000 simulations</p>

<h2>What it is</h2>
<p>A free Monte Carlo survival calculator for founders. Enter your current financials and see runway projections, survival odds at 6 / 12 / 18 / 24 months, and ranked strategic recommendations — without connecting accounts first.</p>

<h2>How it works</h2>
<p>Enter your startup's financials. The engine runs 1,000 probabilistic simulations that model uncertainty in growth, margins, and costs, then returns P10 / P50 / P90 runway, a survival curve, and AI recommendations based on your trajectory.</p>

<h2>What the inputs mean</h2>
<ul>
<li><strong>Cash on Hand</strong> — Current cash balance available to operate.</li>
<li><strong>Monthly Revenue</strong> — Current monthly revenue run rate.</li>
<li><strong>Monthly Expenses</strong> — Current monthly operating expenses.</li>
<li><strong>Growth Rate</strong> — Expected monthly revenue growth rate (%).</li>
<li><strong>Monthly Churn</strong> — Expected monthly customer/revenue churn (%).</li>
<li><strong>Planned Hires (next 12 months)</strong> — Optional. Headcount you expect to add.</li>
<li><strong>Avg Monthly Cost per Hire</strong> — Optional. Fully loaded monthly cost per new hire.</li>
<li><strong>Fundraising Month (1–24)</strong> — Optional. Month in the projection when you expect to close a round; leave blank if not raising.</li>
<li><strong>Fundraising Amount</strong> — Optional. Expected raise size if a fundraising month is set.</li>
</ul>

<h2>What you get</h2>
<ul>
<li><strong>Monte Carlo Engine</strong> — 1,000 probabilistic simulations model uncertainty in growth, margins, and costs.</li>
<li><strong>Survival Probability</strong> — Odds of survival at 6, 12, 18, and 24 months with confidence intervals.</li>
<li><strong>AI Recommendations</strong> — Strategic recommendations based on your specific financial trajectory.</li>
<li><strong>Runway distribution &amp; cash trajectory</strong> — Charts of how cash and runway behave across scenarios (interactive on the page).</li>
</ul>

<h2>Try it free</h2>
<p>Use the simulator on this page — free, no login required to run. After you get a result, you can email the summary to yourself (same lead-capture pattern as the runway calculator): runway, survival odds, and key assumptions, with no account needed.</p>
<p>Want a quicker single-number check first? Try the <a href="/tools/runway-calculator">runway calculator</a> or the <a href="/default-alive">default alive test</a> — both free, no signup.</p>
<p>This calculator models uncertainty with Monte Carlo. FounderConsole can go further with live data connections and ongoing forecasts when you are ready — without requiring signup to use this free tool.</p>
<p>Built by FounderConsole — The Flight Simulator for Founders. This tool provides estimates based on probabilistic modeling and should not be considered financial advice.</p>
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
    };
  }

  if (path === "/pricing") {
    return {
      title: "Pricing | FounderConsole",
      description: "FounderConsole pricing tiers with fast time-to-value. All features free during public beta — no credit card required.",
      canonical: SITE_URL + "/pricing",
      bodyContent: buildPricingBodyContent(),
    };
  }

  if (path === "/about") {
    return {
      title: "About | FounderConsole",
      description: "Learn about FounderConsole — the AI-powered financial intelligence platform built for startup founders.",
      canonical: SITE_URL + "/about",
      bodyContent: buildAboutBodyContent(),
    };
  }

  if (path === "/contact") {
    return {
      title: "Contact | FounderConsole",
      description: "Get in touch with the FounderConsole team.",
      canonical: SITE_URL + "/contact",
      bodyContent: buildContactBodyContent(),
    };
  }

  if (path === "/faq") {
    return {
      title: "FAQ | FounderConsole",
      description: "FounderConsole FAQ: product, data, pricing, accuracy, and explainability.",
      canonical: SITE_URL + "/faq",
      bodyContent: buildFaqBodyContent(),
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

  const runwayIndustryMatch = path.match(/^\/runway\/([a-z0-9-]+)$/);
  if (runwayIndustryMatch) {
    const slug = runwayIndustryMatch[1];
    const known = ["saas","ecommerce","fintech","marketplace","ai","hardware","biotech","devtools"];
    if (known.includes(slug)) {
      const titleMap: Record<string,string> = {
        saas: "SaaS Startup Runway Calculator",
        ecommerce: "Ecommerce Startup Runway Calculator",
        fintech: "Fintech Startup Runway Calculator",
        marketplace: "Marketplace Startup Runway Calculator",
        ai: "AI Startup Runway Calculator",
        hardware: "Hardware Startup Runway Calculator",
        biotech: "Biotech Startup Runway Calculator",
        devtools: "Developer Tools Startup Runway Calculator",
      };
      const title = titleMap[slug];
      return {
        title: `${title} | FounderConsole`,
        description: `Free ${slug} startup runway calculator with industry benchmarks, Monte Carlo simulation, and AI-powered recommendations tuned for ${slug} economics.`,
        canonical: `${SITE_URL}/runway/${slug}`,
        jsonLd: [{
          "@context": "https://schema.org",
          "@type": "WebApplication",
          name: title,
          url: `${SITE_URL}/runway/${slug}`,
          applicationCategory: "BusinessApplication",
          operatingSystem: "Web",
          offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
        }],
      };
    }
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
      bodyContent: buildPrivacyBodyContent(),
      robots: "noindex, follow",
    };
  }

  if (path === "/terms") {
    return {
      title: "Terms of Service | FounderConsole",
      description: "FounderConsole terms of service.",
      canonical: SITE_URL + "/terms",
      bodyContent: buildTermsBodyContent(),
      robots: "noindex, follow",
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

  if (meta.jsonLd && meta.jsonLd.length > 0) {
    const newLdScripts = meta.jsonLd.map((ld) => `<script type="application/ld+json">${JSON.stringify(ld)}</script>`).join("\n    ");
    let replaced = false;
    result = result.replace(/<script\s+type="application\/ld\+json">[\s\S]*?<\/script>/g, (match) => {
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
