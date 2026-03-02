import { Link } from "wouter";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
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
} from "lucide-react";

const features = [
  {
    icon: BarChart3,
    title: "Real-time forecasting",
    headline: "Your forecast stays current. Automatically.",
    description:
      "Connect revenue, expense, and payroll sources to reduce manual work and keep forecasts current. No more stale spreadsheets or quarterly updates.",
    bullets: [
      "Holt-Winters exponential smoothing + linear regression",
      "24-month forward projections updated in real time",
      "Multi-currency support with automatic conversion",
      "Anomaly alerts when actuals deviate from forecast",
    ],
  },
  {
    icon: BarChart3,
    title: "Monte Carlo confidence intervals",
    headline: "Probability replaces guesswork.",
    description:
      "See P10/P50/P90 outcomes so risk becomes measurable. Run thousands of simulations to understand the range of what could happen — not just a single best guess.",
    bullets: [
      "100–10,000 iteration simulations",
      "Custom event modeling and sensitivity analysis",
      "Scenario versioning and comparison",
      "Before/after delta cards with payback calculations",
    ],
  },
  {
    icon: PieChart,
    title: "Scenario comparison",
    headline: "Compare decisions with clear tradeoffs.",
    description:
      "Compare decisions like hiring timing, fundraising size, pricing changes, and investment bets. See ranked recommendations with confidence scores.",
    bullets: [
      "Side-by-side scenario comparison",
      "GO / CONDITIONAL / NO-GO verdicts",
      "Second-order effects detection",
      "Risk-adjusted decision scoring",
    ],
  },
  {
    icon: Bot,
    title: "Explainable AI decisions",
    headline: "Defend choices to boards and investors.",
    description:
      "Narratives explain what drives risk so you can defend choices. Multi-LLM copilot uses GPT-4, Claude, and Gemini with web research via Perplexity.",
    bullets: [
      "Strategic briefings with executive summaries",
      "Data-backed recommendations with citations",
      "Conversational Q&A about your financials",
      "Market benchmark comparisons via web research",
    ],
  },
  {
    icon: FileText,
    title: "Investor-ready reporting",
    headline: "Turn insight into consistent summaries.",
    description:
      "Reduce update-time drag. Generate investor memos, data room checklists, and fundraising materials that build trust through transparency.",
    bullets: [
      "Automated investor memo generation",
      "Data room checklist with completion tracking",
      "Cap table management with dilution modeling",
      "SAFE/Note conversion modeling",
    ],
  },
  {
    icon: Cable,
    title: "37 data connectors",
    headline: "Connect everything. Auto-sync.",
    description:
      "QuickBooks, Stripe, Gusto, Mercury, Brex, Plaid, and 31 more. One-click connections with real API integrations — not CSV imports.",
    bullets: [
      "Real OAuth2 integrations (not screen scraping)",
      "Automatic data refresh and sync",
      "Multi-currency handling across sources",
      "Encrypted credential storage",
    ],
  },
];

export default function MarketingFeaturesPage() {
  useSEO({
    title: "Features | FounderConsole",
    description:
      "FounderConsole features: real-time forecasting, Monte Carlo confidence intervals, scenario comparison, explainability, and investor-ready reporting.",
  });

  return (
    <MarketingLayout>
      <section>
        <div className="mx-auto max-w-6xl px-4 py-16 md:py-20">
          <h1 className="text-3xl font-bold tracking-tight text-foreground md:text-4xl" data-testid="text-features-title">
            Every tool founders need to survive and scale
          </h1>
          <p className="mt-3 max-w-2xl text-lg text-muted-foreground">
            Built for founders who make decisions under uncertainty. Forecast, simulate, compare, explain, and report — all in one place.
          </p>
        </div>
      </section>

      <section className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-10">
          <div className="space-y-12">
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
