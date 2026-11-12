/**
 * Industry homepages: one config entry per `/for/<slug>` page.
 *
 * This file is the single source of truth for every industry variant. Three
 * things read it, so they cannot drift apart:
 *
 *   1. `client/src/pages/industry-landing.tsx` renders the page a visitor sees.
 *   2. `server/seo-prerender.ts` renders the HTML a crawler (or a no-JS visitor)
 *      gets: title, description, canonical, JSON-LD and visible body.
 *   3. `scripts/generate-sitemap.ts` writes one sitemap entry per slug.
 *
 * Adding an industry means adding one entry to `INDUSTRY_PAGES`. Nothing else
 * has to be edited: the route is `/for/:slug`, the picker lists every entry,
 * and `server/tests/industry-homepage.test.ts` checks that each entry has a
 * route, SSR meta and a sitemap entry.
 *
 * Honesty rules for the copy below (the tests check the mechanical parts):
 *   - Features named here exist in the product today: Truth Scan, Scenarios,
 *     the Monte Carlo simulator, the AI copilot, the KPI board with its built-in
 *     metrics, custom metrics, the hiring planner, alerts, the Fundraising OS
 *     (CRM, cap table, dilution), the Investor Room and the 34 read-only
 *     connectors. Connector names come from server/connectors/__init__.py.
 *   - A metric is tagged `built-in` only if it is in the product's metric
 *     definitions (client/src/lib/metricDefinitions.ts). Industry metrics the
 *     product does not compute (GMV, take rate, utilisation, ...) are tagged
 *     `custom`: you can track them as a custom metric, and the page says so.
 *   - No customer logos, counts, testimonials or invented benchmarks. The
 *     product is free during the public beta and that is the only price claim.
 *
 * Keep this file free of imports (and of "@/" aliases in particular): the
 * server bundle and the sitemap script import it by relative path.
 */

export type IndustryIconName = "ShoppingBag" | "Cloud" | "Store" | "Briefcase" | "Landmark" | "Rocket";

/**
 * Where a metric comes from, shown as a small tag on the metrics strip:
 *   built-in   computed by the product (KPI board / metric definitions)
 *   free-tool  computed by one of the free calculators, no account needed
 *   custom     not computed for you; track it as a custom metric
 */
export type MetricSource = "built-in" | "free-tool" | "custom";

export interface IndustryMetric {
  label: string;
  hint: string;
  source: MetricSource;
}

export interface IndustryPain {
  /** The problem, in the founder's own words. */
  pain: string;
  /** A real product feature (see the header). */
  feature: string;
  /** How the feature helps with that pain. */
  detail: string;
  /** Optional public page that demonstrates it (a free tool, never an app route). */
  href?: string;
}

export interface IndustryLink {
  label: string;
  href: string;
  kind: "tool" | "post" | "page";
}

export interface IndustryFaq {
  q: string;
  a: string;
}

export interface IndustryPage {
  slug: string;
  /** Picker label and pill label. */
  label: string;
  /** One line under the label in the picker. */
  pickerHint: string;
  icon: IndustryIconName;
  /**
   * The value of the onboarding "Industry" select this maps to, if any. Used to
   * PREFILL that field after signup; never forced. Omit when nothing fits.
   */
  onboardingIndustry?: string;
  /** <title> and meta description, served by SSR and set by the client. */
  title: string;
  description: string;
  /** Who the page is for, used in JSON-LD `audience`. */
  audience: string;
  eyebrow: string;
  headline: string;
  subhead: string;
  pains: IndustryPain[];
  metrics: IndustryMetric[];
  /** Connector display names, all registered in server/connectors. */
  connectors: string[];
  links: IndustryLink[];
  faqs: IndustryFaq[];
}

export const SITE_URL = "https://founderconsole.ai";

/** localStorage key that remembers the visitor's choice ("all" = skipped). */
export const INDUSTRY_STORAGE_KEY = "fc_industry";
/** Value stored when the visitor chose "just show me everything". */
export const INDUSTRY_SKIPPED = "all";

const FREE_DURING_BETA_FAQ: IndustryFaq = {
  q: "Is FounderConsole free?",
  a: "Yes. Every feature is free during the public beta, and no credit card is required. The free calculators linked on this page need no account at all.",
};

export const INDUSTRY_PAGES: readonly IndustryPage[] = [
  {
    slug: "d2c",
    label: "D2C & e-commerce",
    pickerHint: "CM1/CM2/CM3, RTO, ad efficiency, inventory",
    icon: "ShoppingBag",
    onboardingIndustry: "d2c",
    title: "AI CFO for D2C Brands in India: CM1/CM2/CM3, RTO and Runway | FounderConsole",
    description:
      "Free AI CFO for Indian D2C and e-commerce brands. See CM1, CM2 and CM3 in ₹, what RTO and COD cost you, MER, and how much runway your inventory leaves. Connects Shopify, WooCommerce, Tally and Zoho Books. Free during public beta.",
    audience: "D2C and e-commerce brand founders",
    eyebrow: "For D2C & e-commerce brands",
    headline: "Know which orders actually make you money",
    subhead:
      "A free AI CFO for Indian D2C brands. See CM1, CM2 and CM3 in ₹, what RTO and COD really cost, and how many months of runway are left once your next inventory buy is paid for.",
    pains: [
      {
        pain: "Shopify says one number, the bank account says another.",
        feature: "Truth Scan",
        detail:
          "Connect Shopify or WooCommerce alongside Tally or Zoho Books. Truth Scan checks your numbers against each other and flags the gaps before you plan on them.",
      },
      {
        pain: "RTO and COD are eating margin you cannot see.",
        feature: "Free CM1/CM2/CM3 calculator",
        detail:
          "Enter AOV, RTO %, COD share, COGS, shipping and ad spend to get contribution per order in ₹ and your break-even MER. No account needed.",
        href: "/tools/d2c-contribution-margin",
      },
      {
        pain: "One big inventory buy could leave you short in three months.",
        feature: "Scenarios and Monte Carlo runway",
        detail:
          "Model a stock purchase, a sale or a cut in ad spend, and see runway as a P10 / P50 / P90 range instead of one hopeful number.",
      },
      {
        pain: "You need a straight answer before the festive-season ad push.",
        feature: "AI copilot",
        detail:
          "Ask what happens to runway if ad spend goes up 30% next month. The copilot works from your own numbers and shows its assumptions.",
      },
    ],
    metrics: [
      { label: "CM1 / CM2 / CM3", hint: "Contribution after COGS, fulfilment and marketing", source: "free-tool" },
      { label: "MER", hint: "Net revenue ÷ total marketing spend", source: "free-tool" },
      { label: "RTO %", hint: "Orders that come back undelivered", source: "free-tool" },
      { label: "COD share", hint: "Orders paid on delivery", source: "free-tool" },
      { label: "Gross margin", hint: "Revenue left after cost of goods", source: "built-in" },
      { label: "Net burn", hint: "Cash out minus cash in, per month", source: "built-in" },
      { label: "Runway", hint: "Months of cash at current burn", source: "built-in" },
    ],
    connectors: ["Shopify", "WooCommerce", "RazorpayX", "Tally", "Zoho Books", "Google Sheets", "Keka", "greytHR"],
    links: [
      { label: "D2C contribution margin calculator (CM1, CM2, CM3)", href: "/tools/d2c-contribution-margin", kind: "tool" },
      { label: "CM1, CM2, CM3 with a worked ₹ example", href: "/blog/cm1-cm2-cm3-contribution-margin-d2c", kind: "post" },
      { label: "How RTO and COD eat your D2C margins", href: "/blog/rto-cod-d2c-margins", kind: "post" },
      { label: "MER vs ROAS: which ad metric to run on", href: "/blog/mer-vs-roas-d2c", kind: "post" },
      { label: "Runway for a D2C brand that carries inventory", href: "/blog/d2c-runway-with-inventory", kind: "post" },
      { label: "A per-order D2C P&L you can copy", href: "/blog/d2c-unit-economics-india", kind: "post" },
      { label: "Shopify sales vs real revenue", href: "/blog/shopify-sales-vs-net-revenue-d2c", kind: "post" },
      { label: "E-commerce runway calculator", href: "/runway/ecommerce", kind: "tool" },
    ],
    faqs: [
      {
        q: "Does FounderConsole work in rupees?",
        a: "Yes. You can set your company currency to INR, and the free D2C contribution margin calculator works in ₹ throughout. The D2C guides on the blog use lakh and crore.",
      },
      {
        q: "What is the difference between CM1, CM2 and CM3?",
        a: "CM1 is net revenue minus cost of goods. CM2 also subtracts fulfilment and payment costs: shipping, packaging, RTO and return logistics, gateway and COD fees. CM3 also subtracts marketing, so it is what each order contributes to fixed costs and profit.",
      },
      {
        q: "Which D2C tools does it connect to?",
        a: "Shopify, WooCommerce, RazorpayX, Tally, Zoho Books and Google Sheets are among the 34 read-only data connectors, along with Keka and greytHR for payroll. You can also upload a CSV or type numbers in.",
      },
      {
        q: "Does it publish D2C margin benchmarks?",
        a: "No. We have not found a sourced benchmark for Indian D2C contribution margins that we are willing to quote, so we do not invent one. The calculator shows your own numbers and the arithmetic behind them.",
      },
      FREE_DURING_BETA_FAQ,
    ],
  },
  {
    slug: "saas",
    label: "SaaS / B2B software",
    pickerHint: "MRR, churn, NRR, burn multiple, CAC payback",
    icon: "Cloud",
    onboardingIndustry: "general_saas",
    title: "AI CFO for SaaS Startups: MRR, NRR, Burn Multiple and Runway | FounderConsole",
    description:
      "Free AI CFO for SaaS and B2B software startups. Track MRR, ARR, churn, net revenue retention, burn multiple and CAC payback from Stripe and QuickBooks, and simulate runway to your next round. Free during public beta.",
    audience: "SaaS and B2B software founders",
    eyebrow: "For SaaS & B2B software",
    headline: "Your burn multiple, NRR and runway, from live billing data",
    subhead:
      "Connect Stripe and QuickBooks and FounderConsole tracks MRR, churn, net revenue retention, burn multiple and CAC payback, then simulates how long your cash lasts before the next round.",
    pains: [
      {
        pain: "The MRR spreadsheet is a month out of date.",
        feature: "Connectors and Truth Scan",
        detail:
          "Pull revenue from Stripe, Chargebee, Recurly or ProfitWell and spend from QuickBooks, Xero or NetSuite. Truth Scan flags numbers that do not reconcile.",
      },
      {
        pain: "Investors ask for burn multiple and CAC payback, and you are estimating.",
        feature: "KPI board with built-in SaaS metrics",
        detail:
          "MRR, ARR, churn, NRR, burn multiple, LTV:CAC and CAC payback are built in and update as your data does.",
      },
      {
        pain: "You do not know when to start raising.",
        feature: "Monte Carlo runway and the Fundraising OS",
        detail:
          "See runway as P10 / P50 / P90 and plan the round with the investor CRM, cap table and dilution modelling.",
      },
      {
        pain: "Every hire changes the math.",
        feature: "Scenarios and the hiring planner",
        detail:
          "Test a hiring plan, a price change or a churn improvement and compare the runway of each side by side.",
      },
    ],
    metrics: [
      { label: "MRR / ARR", hint: "Recurring revenue, monthly and annualised", source: "built-in" },
      { label: "Net revenue retention", hint: "Revenue kept and expanded from existing customers", source: "built-in" },
      { label: "Churn", hint: "Customers or revenue lost per month", source: "built-in" },
      { label: "Burn multiple", hint: "Net burn ÷ net new ARR", source: "built-in" },
      { label: "CAC payback", hint: "Months to earn back acquisition cost", source: "built-in" },
      { label: "LTV:CAC", hint: "Lifetime value against acquisition cost", source: "built-in" },
      { label: "Runway", hint: "Months of cash at current burn", source: "built-in" },
    ],
    connectors: ["Stripe", "Chargebee", "Recurly", "ProfitWell", "QuickBooks", "Xero", "HubSpot", "Salesforce"],
    links: [
      { label: "Burn multiple calculator", href: "/tools/burn-multiple", kind: "tool" },
      { label: "LTV:CAC and CAC payback calculator", href: "/tools/ltv-cac", kind: "tool" },
      { label: "Dilution calculator", href: "/tools/dilution", kind: "tool" },
      { label: "SaaS runway calculator", href: "/runway/saas", kind: "tool" },
      { label: "What is a good burn multiple?", href: "/blog/what-is-a-good-burn-multiple", kind: "post" },
      { label: "Seed-stage SaaS benchmarks 2026", href: "/blog/seed-stage-saas-benchmarks-2026", kind: "post" },
      { label: "LTV:CAC ratio explained", href: "/blog/ltv-cac-ratio-explained", kind: "post" },
      { label: "When to raise: timing your Series A", href: "/blog/timing-series-a", kind: "post" },
    ],
    faqs: [
      {
        q: "What is burn multiple?",
        a: "Burn multiple is net burn divided by net new ARR over the same period. It tells you how many dollars you burn to add one dollar of ARR, so lower is better. FounderConsole computes it from your connected data, and the free burn multiple calculator works without an account.",
      },
      {
        q: "Can it read my Stripe subscriptions?",
        a: "Yes. Stripe is one of 34 read-only data connectors, along with Chargebee, Recurly and ProfitWell for billing and QuickBooks, Xero and NetSuite for accounting.",
      },
      {
        q: "How much runway should a SaaS startup have?",
        a: "A common rule of thumb is 18 to 24 months after a seed round and 12 to 18 months after a Series A, and starting a raise with at least 9 to 12 months left. FounderConsole shows your runway as a range so you can see how much margin you really have.",
      },
      FREE_DURING_BETA_FAQ,
    ],
  },
  {
    slug: "marketplace",
    label: "Marketplace / platform",
    pickerHint: "GMV vs take rate vs net revenue, subsidies",
    icon: "Store",
    onboardingIndustry: "marketplace",
    title: "Financial Planning for Marketplaces: GMV, Take Rate and Unit Economics | FounderConsole",
    description:
      "Free AI CFO for marketplace and platform startups. Separate GMV from take rate and net revenue, price supply and demand incentives, and see contribution per order and runway before you expand. Free during public beta.",
    audience: "Marketplace and platform founders",
    eyebrow: "For marketplaces & platforms",
    headline: "GMV is not revenue. See what your marketplace keeps.",
    subhead:
      "Separate GMV, take rate and net revenue, put a price on buyer and seller incentives, and see contribution per order and runway before you open the next city or category.",
    pains: [
      {
        pain: "Headline GMV growth hides a thin take rate.",
        feature: "Custom metrics on the KPI board",
        detail:
          "Track GMV, take rate and contribution per order as custom metrics next to the built-in revenue, gross margin and burn, so the board sees all of them together.",
      },
      {
        pain: "Incentives for both sides blur your unit economics.",
        feature: "Scenarios",
        detail:
          "Model cutting incentives, changing the commission or adding a fee, and see what each does to burn and runway before you change anything live.",
      },
      {
        pain: "Expansion is a bet on demand you have not seen yet.",
        feature: "Monte Carlo simulator",
        detail:
          "Run thousands of futures for a launch and look at the downside case, not just the plan.",
      },
      {
        pain: "Payments, product analytics and the books all live in different tools.",
        feature: "34 read-only connectors",
        detail:
          "Stripe for payments, Mixpanel, Amplitude or Google Analytics for activity, QuickBooks or Xero for spend, and a REST API for anything else.",
      },
    ],
    metrics: [
      { label: "GMV", hint: "Total value transacted on the platform", source: "custom" },
      { label: "Take rate", hint: "Net revenue ÷ GMV", source: "custom" },
      { label: "Contribution per order", hint: "Net revenue per order minus variable cost and incentives", source: "custom" },
      { label: "Gross margin", hint: "Revenue left after direct costs", source: "built-in" },
      { label: "Customer concentration", hint: "Share of revenue from your top five", source: "built-in" },
      { label: "Net burn", hint: "Cash out minus cash in, per month", source: "built-in" },
      { label: "Runway", hint: "Months of cash at current burn", source: "built-in" },
    ],
    connectors: ["Stripe", "Mixpanel", "Amplitude", "Google Analytics", "QuickBooks", "Xero", "Google Sheets", "REST API"],
    links: [
      { label: "Marketplace runway calculator", href: "/runway/marketplace", kind: "tool" },
      { label: "LTV:CAC and CAC payback calculator", href: "/tools/ltv-cac", kind: "tool" },
      { label: "Startup survival simulator", href: "/survival-simulator", kind: "tool" },
      { label: "The founder's guide to unit economics", href: "/blog/unit-economics-guide", kind: "post" },
      { label: "What-if analysis for startups", href: "/blog/what-if-analysis-for-startups", kind: "post" },
      { label: "Monte Carlo simulations: a founder's guide", href: "/blog/monte-carlo-founders-guide", kind: "post" },
    ],
    faqs: [
      {
        q: "What is the difference between GMV and net revenue?",
        a: "GMV is the total value of transactions on your platform. Net revenue is the part you keep: your commission and fees, after refunds and any incentives you pay out. Investors value a marketplace on net revenue and contribution, not GMV.",
      },
      {
        q: "Does FounderConsole calculate take rate for me?",
        a: "Not automatically. Take rate and GMV are not built-in metrics today. You can add them as custom metrics on the KPI board and track them next to the built-in revenue, margin, burn and runway figures.",
      },
      {
        q: "Can I model a change in commission or incentives?",
        a: "Yes. Scenarios let you change pricing, growth, costs and margins and compare the effect on burn and runway, and the Monte Carlo simulator shows the range of outcomes rather than a single forecast.",
      },
      FREE_DURING_BETA_FAQ,
    ],
  },
  {
    slug: "agency",
    label: "Agency / services",
    pickerHint: "Utilisation, project margins, cash-flow gaps",
    icon: "Briefcase",
    onboardingIndustry: "agency",
    title: "Cash Flow, Margin and Hiring Planning for Agencies | FounderConsole",
    description:
      "Free AI CFO for agencies and services firms. Track utilisation and project margins, see the gap between invoicing and getting paid, and test whether you can afford the next hire. Connects QuickBooks, Xero, Zoho Books and FreshBooks. Free during public beta.",
    audience: "Agency and professional services founders",
    eyebrow: "For agencies & services firms",
    headline: "Keep the team busy and cash ahead of payroll",
    subhead:
      "For agencies and services firms: see project margins, the gap between sending an invoice and getting paid, and whether to hire ahead of the pipeline or stay lean.",
    pains: [
      {
        pain: "Clients pay in 60 days. Payroll is every month.",
        feature: "Monte Carlo runway and alerts",
        detail:
          "See where your cash bottoms out, not just the month-end balance, and set alerts on runway and burn so a slow-paying client is not a surprise.",
      },
      {
        pain: "You cannot tell which clients are actually profitable.",
        feature: "Custom metrics and the AI copilot",
        detail:
          "Track utilisation, project margin and receivable days as custom metrics, then ask the copilot where the margin is going.",
      },
      {
        pain: "Hire ahead of the pipeline, or risk people on the bench?",
        feature: "Hiring planner and scenarios",
        detail:
          "Model the hire with and without the big deal closing, and compare the runway of each before you send the offer.",
      },
      {
        pain: "Books in one tool, invoices in another, payroll in a third.",
        feature: "34 read-only connectors",
        detail:
          "QuickBooks, Xero, Zoho Books, FreshBooks or Wave for the books, HubSpot or Pipedrive for the pipeline, Gusto, Deel or Keka for payroll.",
      },
    ],
    metrics: [
      { label: "Utilisation", hint: "Billable hours ÷ available hours", source: "custom" },
      { label: "Project margin", hint: "Fee minus delivery cost, per project", source: "custom" },
      { label: "Receivable days", hint: "How long clients take to pay", source: "custom" },
      { label: "Client concentration", hint: "Share of revenue from your top five", source: "built-in" },
      { label: "Gross margin", hint: "Revenue left after delivery costs", source: "built-in" },
      { label: "Net burn", hint: "Cash out minus cash in, per month", source: "built-in" },
      { label: "Runway", hint: "Months of cash at current burn", source: "built-in" },
    ],
    connectors: ["QuickBooks", "Xero", "Zoho Books", "FreshBooks", "Wave", "HubSpot", "Pipedrive", "Gusto", "Deel", "Keka"],
    links: [
      { label: "13-week cash flow model template", href: "/blog/13-week-cash-flow-template", kind: "post" },
      { label: "How to calculate your true runway", href: "/blog/calculate-true-runway", kind: "post" },
      { label: "Free runway calculator", href: "/tools/runway-calculator", kind: "tool" },
      { label: "Default alive or default dead?", href: "/default-alive", kind: "tool" },
      { label: "Startup survival simulator", href: "/survival-simulator", kind: "tool" },
    ],
    faqs: [
      {
        q: "Is FounderConsole only for venture-backed startups?",
        a: "No. Runway, cash flow and scenario modelling work for any business with cash, revenue and costs. Agency-specific numbers such as utilisation and project margin can be added as custom metrics.",
      },
      {
        q: "How do I track utilisation and project margins?",
        a: "Add them as custom metrics on the KPI board. They sit next to the built-in gross margin, burn and runway figures, and the AI copilot can answer questions about them.",
      },
      {
        q: "Which accounting tools does it connect to?",
        a: "QuickBooks, Xero, Zoho Books, FreshBooks, Wave and NetSuite, plus HubSpot and Pipedrive for pipeline and Gusto, Deel, Rippling and Keka for payroll. All 34 connectors are read-only. CSV upload and manual entry also work.",
      },
      FREE_DURING_BETA_FAQ,
    ],
  },
  {
    slug: "fintech",
    label: "Fintech",
    pickerHint: "Per-user unit economics, capital, CAC vs LTV",
    icon: "Landmark",
    onboardingIndustry: "fintech",
    title: "Financial Planning for Fintech Startups: Unit Economics, Capital and Burn | FounderConsole",
    description:
      "Free AI CFO for fintech startups. Track unit economics per user, LTV against CAC and CAC payback, keep your regulatory capital requirement in view, and stress-test runway with Monte Carlo simulation. Free during public beta.",
    audience: "Fintech founders",
    eyebrow: "For fintech founders",
    headline: "Per-user economics, capital buffers and burn in one model",
    subhead:
      "Track LTV against CAC for every user you acquire, keep the capital your licence requires in view, and see how long your runway lasts under stress.",
    pains: [
      {
        pain: "Some of your cash is not really yours to spend.",
        feature: "Custom metrics and scenarios",
        detail:
          "Add your regulatory capital requirement as a custom metric and run scenarios on the cash above it, so the plan is built on money you can actually use.",
      },
      {
        pain: "CAC keeps rising and LTV is a guess.",
        feature: "Built-in LTV:CAC and CAC payback",
        detail:
          "Both are built-in metrics, and the free LTV:CAC calculator grades the ratio and the payback separately.",
        href: "/tools/ltv-cac",
      },
      {
        pain: "The board wants a stress test, not a single forecast.",
        feature: "Monte Carlo simulator",
        detail:
          "Thousands of runs with realistic uncertainty give you P10 / P50 / P90 outcomes for runway and cash.",
      },
      {
        pain: "Diligence will question every number.",
        feature: "Truth Scan and the Investor Room",
        detail:
          "Truth Scan flags inconsistencies and anomalies in your data before an investor finds them, and the Investor Room drafts an investor memo and answers to likely diligence questions.",
      },
    ],
    metrics: [
      { label: "LTV:CAC", hint: "Lifetime value against acquisition cost", source: "built-in" },
      { label: "CAC payback", hint: "Months to earn back acquisition cost", source: "built-in" },
      { label: "Contribution per user", hint: "Revenue per user minus variable cost", source: "custom" },
      { label: "Capital buffer", hint: "Cash held above your regulatory requirement", source: "custom" },
      { label: "Churn", hint: "Users or revenue lost per month", source: "built-in" },
      { label: "Burn multiple", hint: "Net burn ÷ net new ARR", source: "built-in" },
      { label: "Runway", hint: "Months of cash at current burn", source: "built-in" },
    ],
    connectors: ["Stripe", "Plaid", "Mercury", "Brex", "NetSuite", "QuickBooks", "Mixpanel", "Amplitude", "REST API"],
    links: [
      { label: "LTV:CAC and CAC payback calculator", href: "/tools/ltv-cac", kind: "tool" },
      { label: "Burn multiple calculator", href: "/tools/burn-multiple", kind: "tool" },
      { label: "Fintech runway calculator", href: "/runway/fintech", kind: "tool" },
      { label: "LTV:CAC ratio explained", href: "/blog/ltv-cac-ratio-explained", kind: "post" },
      { label: "Monte Carlo simulations: a founder's guide", href: "/blog/monte-carlo-founders-guide", kind: "post" },
      { label: "The founder's guide to unit economics", href: "/blog/unit-economics-guide", kind: "post" },
    ],
    faqs: [
      {
        q: "Does FounderConsole calculate regulatory capital?",
        a: "No. Capital rules depend on your licence and jurisdiction, so the product does not compute them. You can add your requirement as a custom metric and plan runway on the cash above it.",
      },
      {
        q: "Which banking and payments data can it read?",
        a: "Stripe, Plaid, Mercury, Brex and RazorpayX are among the 34 read-only connectors, plus NetSuite and QuickBooks for accounting and a REST API for internal systems.",
      },
      {
        q: "How is a Monte Carlo stress test different from a downside case?",
        a: "A downside case is one set of bad assumptions you picked. Monte Carlo runs your model thousands of times with varied inputs and shows how often each outcome happens, so you see the P10 case as well as the median.",
      },
      FREE_DURING_BETA_FAQ,
    ],
  },
  {
    slug: "startup",
    label: "Early-stage startup",
    pickerHint: "Pre-revenue? Runway, burn, hires, when to raise",
    icon: "Rocket",
    onboardingIndustry: "startup",
    title: "Runway, Burn and Fundraising Planner for Early-Stage Startups | FounderConsole",
    description:
      "Free AI CFO for early-stage and pre-revenue startups. Know your runway and burn, plan hires, and see your fundraising timeline as a range, not a guess. Monte Carlo simulation and an AI copilot. Free during public beta.",
    audience: "Early-stage and pre-revenue startup founders",
    eyebrow: "For early-stage & pre-revenue startups",
    headline: "Know how many months you have, and when to start raising",
    subhead:
      "Pre-revenue or just getting started? Put in your cash and burn, plan your hires, and see runway and your fundraising timeline as a range instead of a guess.",
    pains: [
      {
        pain: "You recompute runway every Sunday night.",
        feature: "Connectors and the KPI board",
        detail:
          "Connect Mercury, Brex or Ramp, or a Google Sheet, and cash, burn and runway update on their own.",
      },
      {
        pain: "Every hire shortens runway. By how much?",
        feature: "Hiring planner",
        detail:
          "Lay out who you plan to hire and when, and see the effect on burn and runway month by month.",
      },
      {
        pain: "Raise too late and you raise from weakness.",
        feature: "Monte Carlo runway and the Fundraising OS",
        detail:
          "See when runway gets tight across thousands of simulated futures, then run the raise with the investor CRM, cap table and dilution modelling.",
      },
      {
        pain: "There is no CFO to sanity-check you.",
        feature: "AI copilot",
        detail:
          "Ask plain-English questions about burn, hiring and fundraising and get answers worked from your own numbers, with the assumptions shown.",
      },
    ],
    metrics: [
      { label: "Runway", hint: "Months of cash at current burn", source: "built-in" },
      { label: "Net burn", hint: "Cash out minus cash in, per month", source: "built-in" },
      { label: "Cash balance", hint: "What is in the bank today", source: "built-in" },
      { label: "Default alive?", hint: "Do you reach profitability on current cash?", source: "free-tool" },
      { label: "Survival odds", hint: "Probability of still operating at 12 and 24 months", source: "free-tool" },
      { label: "Dilution", hint: "Ownership after your next round", source: "free-tool" },
    ],
    connectors: ["Mercury", "Brex", "Ramp", "Gusto", "Deel", "QuickBooks", "Stripe", "Google Sheets"],
    links: [
      { label: "Free runway calculator", href: "/tools/runway-calculator", kind: "tool" },
      { label: "Default alive or default dead?", href: "/default-alive", kind: "tool" },
      { label: "Startup survival simulator", href: "/survival-simulator", kind: "tool" },
      { label: "Dilution calculator", href: "/tools/dilution", kind: "tool" },
      { label: "How to calculate startup runway", href: "/blog/how-to-calculate-startup-runway", kind: "post" },
      { label: "When to raise: timing your Series A", href: "/blog/timing-series-a", kind: "post" },
      { label: "5 cap table mistakes", href: "/blog/cap-table-mistakes", kind: "post" },
    ],
    faqs: [
      {
        q: "Is FounderConsole useful before I have revenue?",
        a: "Yes. Runway, burn, the hiring planner and fundraising timing only need your cash and your costs. Revenue metrics such as MRR and burn multiple switch on once you have revenue.",
      },
      {
        q: "How do I know when to start fundraising?",
        a: "Raising usually takes months, so most founders start with plenty of runway left. FounderConsole shows runway as a P10 / P50 / P90 range, so you can see when the pessimistic case gets tight and plan the raise before then.",
      },
      {
        q: "Do I need to connect anything to start?",
        a: "No. You can type in your numbers or upload a CSV. Connecting a bank or accounting tool through one of the 34 read-only connectors keeps them up to date.",
      },
      FREE_DURING_BETA_FAQ,
    ],
  },
];

export const INDUSTRY_SLUGS: readonly string[] = INDUSTRY_PAGES.map((p) => p.slug);

export function getIndustryPage(slug: string | null | undefined): IndustryPage | undefined {
  if (!slug) return undefined;
  const wanted = slug.toLowerCase();
  return INDUSTRY_PAGES.find((p) => p.slug === wanted);
}

export function industryPath(slug: string): string {
  return `/for/${slug}`;
}

/** The "Start free" CTA. Carries the industry so onboarding can prefill it. */
export function industrySignupHref(slug: string): string {
  return `/signup?industry=${encodeURIComponent(slug)}`;
}

export const METRIC_SOURCE_LABEL: Record<MetricSource, string> = {
  "built-in": "Built in",
  "free-tool": "Free calculator",
  custom: "Custom metric",
};

/**
 * JSON-LD for one industry page. Shared by the SSR prerender and the client's
 * useSEO call so the structured data a crawler sees is the data the page sets.
 */
export function industryJsonLd(page: IndustryPage): object[] {
  const url = `${SITE_URL}${industryPath(page.slug)}`;
  return [
    {
      "@context": "https://schema.org",
      "@type": "WebPage",
      name: page.title,
      description: page.description,
      url,
      inLanguage: "en",
      isPartOf: { "@type": "WebSite", name: "FounderConsole", url: SITE_URL },
      about: {
        "@type": "SoftwareApplication",
        name: "FounderConsole",
        applicationCategory: "BusinessApplication",
        operatingSystem: "Web",
        url: SITE_URL,
        offers: {
          "@type": "Offer",
          price: "0",
          priceCurrency: "USD",
          description: "Free during public beta — no credit card required",
        },
        audience: { "@type": "BusinessAudience", audienceType: page.audience },
      },
    },
    {
      "@context": "https://schema.org",
      "@type": "BreadcrumbList",
      itemListElement: [
        { "@type": "ListItem", position: 1, name: "Home", item: `${SITE_URL}/` },
        { "@type": "ListItem", position: 2, name: page.eyebrow, item: url },
      ],
    },
    {
      "@context": "https://schema.org",
      "@type": "FAQPage",
      mainEntity: page.faqs.map((f) => ({
        "@type": "Question",
        name: f.q,
        acceptedAnswer: { "@type": "Answer", text: f.a },
      })),
    },
  ];
}
