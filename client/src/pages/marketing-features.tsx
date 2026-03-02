import { Link } from "wouter";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { ScenarioCompare } from "@/components/ScenarioCompare";
import { Button } from "@/components/ui/button";
import { useSEO } from "@/lib/seo";
import {
  BarChart3,
  Bot,
  ShieldCheck,
  PieChart,
  Cable,
  FileText,
  ArrowRight,
  CheckCircle,
  TrendingUp,
} from "lucide-react";

const features = [
  {
    icon: TrendingUp,
    title: "Real-time forecasting",
    headline: "Your forecast stays current. Automatically.",
    description:
      "Connect revenue, expense, and payroll sources to reduce manual work and keep forecasts current. No more stale spreadsheets or quarterly updates.",
    bullets: [
      "Holt-Winters smoothing keeps projections accurate as data flows in",
      "24-month forward view so you catch problems early",
      "Multi-currency support — no manual conversion tables",
      "Anomaly alerts flag deviations before they compound",
    ],
  },
  {
    icon: BarChart3,
    title: "Monte Carlo simulation",
    headline: "Probability replaces guesswork.",
    description:
      "See P10/P50/P90 outcomes so risk becomes measurable. Run thousands of simulations to understand the range of what could happen — not just a single best guess.",
    bullets: [
      "100–10,000 iterations reveal the full distribution of outcomes",
      "Sensitivity analysis shows which lever moves risk most",
      "Tornado charts instantly identify your top 3 risk drivers",
      "Before/after delta cards quantify the impact of each decision",
    ],
  },
  {
    icon: PieChart,
    title: "Scenario comparison",
    headline: "Compare decisions with clear tradeoffs.",
    description:
      "Compare decisions like hiring timing, fundraising size, pricing changes, and investment bets. See ranked recommendations with confidence scores so you know why one path beats another.",
    bullets: [
      "Side-by-side comparison with GO / CONDITIONAL / NO-GO verdicts",
      "Second-order effects detection catches downstream surprises",
      "Risk-adjusted scoring lets you weigh speed vs. safety",
      "Scenario versioning so you can revisit past analyses",
    ],
  },
  {
    icon: Bot,
    title: "Explainable AI copilot",
    headline: "Defend choices to boards and investors.",
    description:
      "Multi-LLM copilot uses GPT-4, Claude, and Gemini to answer strategic questions. Perplexity-powered web research adds market benchmarks. Every answer shows its reasoning.",
    bullets: [
      "\"Why this answer\" — top drivers + assumptions are always visible",
      "Data freshness indicator shows when sources last synced",
      "Citations link back to the underlying data or market source",
      "Conversational Q&A — ask in plain English, get structured output",
    ],
  },
  {
    icon: FileText,
    title: "Investor-ready reporting",
    headline: "Turn insight into consistent summaries.",
    description:
      "Reduce update-time drag. Generate investor memos, data room checklists, and fundraising materials that build trust through transparency and consistent language.",
    bullets: [
      "Automated investor memo generation from simulation results",
      "Cap table management with dilution modeling and SAFE conversion",
      "Data room checklist with completion tracking",
      "Fundraising pipeline to track investor conversations",
    ],
  },
  {
    icon: Cable,
    title: "37 data connectors",
    headline: "Connect everything. Auto-sync.",
    description:
      "QuickBooks, Stripe, Gusto, Mercury, Brex, Plaid, and 31 more. Real OAuth2 integrations — not CSV imports or screen scraping.",
    bullets: [
      "One-click OAuth connections with automatic data refresh",
      "Multi-currency handling across all connected sources",
      "Encrypted credential storage — your keys never leave our vault",
      "New connectors added monthly based on founder requests",
    ],
  },
];

const fiveMinuteItems = [
  "Baseline forecast from connected sources",
  "One scenario simulation with P10/P50/P90 confidence bands",
  "AI narrative explaining your top risk drivers",
  "An investor-ready summary draft you can share immediately",
];

export default function MarketingFeaturesPage() {
  useSEO({
    title: "Features | FounderConsole",
    description:
      "Real-time forecasting, Monte Carlo simulation, explainable AI copilot, scenario comparison, and investor-ready reporting — built for founders.",
  });

  return (
    <MarketingLayout>
      <section>
        <div className="mx-auto max-w-6xl px-4 py-16 md:py-20">
          <h1 className="text-3xl font-bold tracking-tight text-foreground md:text-4xl" data-testid="text-features-title">
            Every tool founders need to survive and scale
          </h1>
          <p className="mt-3 max-w-2xl text-lg text-muted-foreground">
            Know your runway confidence band and the tradeoffs of hiring, fundraising, and pricing — in minutes.
          </p>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            2-minute setup &middot; Connect Stripe &middot; Get a baseline forecast
          </p>
        </div>
      </section>

      <section className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-10">
          <div className="space-y-16">
            {features.map((f, i) => (
              <div
                key={f.title}
                className={`flex flex-col gap-8 md:flex-row md:items-start ${i % 2 === 1 ? "md:flex-row-reverse" : ""}`}
                data-testid={`section-feature-${f.title.toLowerCase().replace(/\s+/g, "-")}`}
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2 text-primary">
                    <f.icon className="h-5 w-5" />
                    <span className="text-xs font-semibold uppercase tracking-wide">{f.title}</span>
                  </div>
                  <h2 className="mt-2 text-xl font-semibold text-foreground">{f.headline}</h2>
                  <p className="mt-3 text-sm text-muted-foreground">{f.description}</p>
                  <ul className="mt-4 space-y-2">
                    {f.bullets.map((b) => (
                      <li key={b} className="flex gap-2 text-sm text-muted-foreground">
                        <CheckCircle className="mt-0.5 h-4 w-4 shrink-0 text-primary/70" />
                        <span>{b}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="flex-1">
                  <div className="rounded-xl border bg-card/50 p-8 flex items-center justify-center min-h-[180px]">
                    <f.icon className="h-16 w-16 text-primary/20" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-12">
          <div className="rounded-xl border bg-card p-6 md:p-8">
            <p className="text-xs font-semibold uppercase tracking-wide text-primary">Real example</p>
            <h3 className="mt-2 text-lg font-semibold text-foreground" data-testid="text-case-snippet">
              Delay a hire by 3 weeks → risk drops from 42% to 18%
            </h3>
            <p className="mt-2 text-sm text-muted-foreground max-w-2xl">
              A seed-stage SaaS team used FounderConsole to compare hiring timelines. The simulation showed that
              pushing a senior hire by 3 weeks extended runway past their next fundraise milestone, cutting negative-runway
              probability by more than half — without slowing product velocity.
            </p>
          </div>
        </div>
      </section>

      <section className="border-t">
        <ScenarioCompare />
      </section>

      <section className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-12">
          <div className="max-w-3xl">
            <h2 className="text-2xl font-semibold tracking-tight text-foreground" data-testid="text-five-min-heading">
              What you get in the first 5 minutes
            </h2>
            <p className="mt-2 text-muted-foreground">Connect one source. Get a complete picture.</p>
          </div>
          <ul className="mt-6 grid gap-3 sm:grid-cols-2">
            {fiveMinuteItems.map((item) => (
              <li key={item} className="flex gap-2 text-sm text-muted-foreground">
                <CheckCircle className="mt-0.5 h-4 w-4 shrink-0 text-primary/70" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-16 md:py-20 text-center">
          <ShieldCheck className="mx-auto h-8 w-8 text-primary" />
          <h2 className="mt-4 text-2xl font-semibold text-foreground" data-testid="text-features-cta">
            Start using FounderConsole today — it's free during beta
          </h2>
          <p className="mx-auto mt-2 max-w-lg text-muted-foreground">
            All features are unlocked. No credit card required. Connect your data and get your first forecast in under 5 minutes.
          </p>
          <div className="mt-6">
            <Button size="lg" asChild data-testid="button-features-get-started">
              <Link href="/auth">
                Get Started Free
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </section>
    </MarketingLayout>
  );
}
