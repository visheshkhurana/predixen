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
  Rocket,
  Cable,
  ArrowRight,
  Zap,
  TrendingUp,
  Target,
  CheckCircle,
} from "lucide-react";

const integrations = ["Stripe", "QuickBooks", "Gusto", "Mercury", "Brex", "Plaid"];

const features = [
  {
    icon: TrendingUp,
    title: "Runway in real time",
    description: "Connect key systems and see runway with explainable context. No more stale spreadsheets.",
  },
  {
    icon: BarChart3,
    title: "Confidence intervals",
    description: "Monte Carlo simulation gives you P10/P50/P90 outcomes so risk becomes measurable, not guesswork.",
  },
  {
    icon: Target,
    title: "Decisions, not dashboards",
    description: "Compare scenarios like hiring timing or fundraising targets with clear tradeoffs and ranked recommendations.",
  },
  {
    icon: Bot,
    title: "AI Copilot",
    description: "Get strategic recommendations powered by GPT-4, Claude, and Gemini. Ask questions in plain English.",
  },
  {
    icon: ShieldCheck,
    title: "Truth Scan",
    description: "Validate your financial data with automated anomaly detection and confidence scoring before decisions.",
  },
  {
    icon: Cable,
    title: "37 Integrations",
    description: "Connect QuickBooks, Stripe, Gusto, Mercury, and 33 more sources. Auto-sync with multi-currency support.",
  },
];

const steps = [
  { title: "Connect", description: "Stripe, QuickBooks, Gusto, Mercury and more. One-click sync." },
  { title: "Forecast", description: "Baseline forecast that stays current as new data flows in." },
  { title: "Simulate", description: "Confidence intervals show a range of outcomes, not a single guess." },
  { title: "Decide", description: "Recommendations and explainability you can defend to investors." },
];

const stats = [
  { value: "2.4M+", label: "Scenarios Simulated" },
  { value: "37", label: "Data Integrations" },
  { value: "$2.1B+", label: "Revenue Analyzed" },
  { value: "P10/P50/P90", label: "Confidence Bands" },
];

export default function LandingPage() {
  useSEO({
    title: "Financial Intelligence for Founders | FounderConsole",
    description:
      "AI-powered simulation, forecasting, and decision support that gives founders the financial clarity to build with confidence.",
  });

  return (
    <MarketingLayout>
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-primary/5 to-transparent pointer-events-none" />
        <div className="relative mx-auto max-w-6xl px-4 py-16 md:py-24">
          <p className="text-xs font-semibold uppercase tracking-wide text-primary" data-testid="text-trust-tagline">
            Trusted by 500+ startups
          </p>
          <h1 className="mt-3 text-4xl font-bold tracking-tight text-foreground md:text-5xl lg:text-6xl" data-testid="text-hero-title">
            Financial Intelligence
            <br />
            for Founders
          </h1>
          <p className="mt-4 max-w-2xl text-lg text-muted-foreground" data-testid="text-hero-subtitle">
            AI-powered simulation, forecasting, and decision support that gives founders the financial clarity to build with confidence.
          </p>

          <div className="mt-8 flex flex-wrap gap-3">
            <Button size="lg" asChild data-testid="button-hero-get-started">
              <Link href="/auth">
                Get Started Free
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button size="lg" variant="outline" asChild data-testid="button-hero-watch-demo">
              <Link href="/demo">Watch Demo</Link>
            </Button>
          </div>

          <div className="mt-10 rounded-lg border bg-card/50 p-4" data-testid="section-integrations">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Powering insights from</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {integrations.map((name) => (
                <span
                  key={name}
                  className="inline-flex items-center rounded-md border bg-background px-3 py-1.5 text-sm font-medium text-foreground"
                  data-testid={`badge-integration-${name.toLowerCase()}`}
                >
                  {name}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-16 md:py-20">
          <div className="max-w-3xl">
            <h2 className="text-2xl font-semibold tracking-tight text-foreground" data-testid="text-features-heading">
              Built for founders who make decisions under uncertainty
            </h2>
            <p className="mt-2 text-muted-foreground">
              Everything you need to forecast, simulate, compare, explain, and report — in one place.
            </p>
          </div>
          <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((f) => (
              <div
                key={f.title}
                className="rounded-xl border bg-card p-6 transition-colors hover:border-primary/30"
                data-testid={`card-feature-${f.title.toLowerCase().replace(/\s+/g, "-")}`}
              >
                <f.icon className="h-5 w-5 text-primary" />
                <h3 className="mt-3 text-base font-semibold text-foreground">{f.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{f.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-16 md:py-20">
          <div className="max-w-3xl">
            <h2 className="text-2xl font-semibold tracking-tight text-foreground" data-testid="text-how-heading">
              How it works
            </h2>
            <p className="mt-2 text-muted-foreground">Minimal setup. Maximum clarity.</p>
          </div>
          <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {steps.map((step, i) => (
              <div
                key={step.title}
                className="rounded-xl border bg-card/50 p-6"
                data-testid={`card-step-${i + 1}`}
              >
                <p className="text-xs font-semibold text-primary">Step {i + 1}</p>
                <h3 className="mt-2 text-base font-semibold text-foreground">{step.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{step.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t bg-card/30">
        <div className="mx-auto max-w-6xl px-4 py-16 md:py-20">
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {stats.map((stat) => (
              <div key={stat.label} className="text-center" data-testid={`stat-${stat.label.toLowerCase().replace(/\s+/g, "-")}`}>
                <p className="text-3xl font-bold font-mono text-foreground">{stat.value}</p>
                <p className="mt-1 text-sm text-muted-foreground">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t">
        <ScenarioCompare />
      </section>

      <section className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-16 md:py-20">
          <div className="max-w-3xl">
            <h2 className="text-2xl font-semibold tracking-tight text-foreground" data-testid="text-value-heading">
              What you get in the first 5 minutes
            </h2>
            <p className="mt-2 text-muted-foreground">Transparent tiers + fast time-to-value.</p>
          </div>
          <div className="mt-10 grid gap-6 md:grid-cols-2">
            <div className="rounded-xl border bg-card p-6">
              <h3 className="text-base font-semibold text-foreground">Immediate deliverables</h3>
              <ul className="mt-4 space-y-3 text-sm text-muted-foreground">
                {[
                  "Baseline forecast from connected sources",
                  "One scenario simulation with confidence bands",
                  "AI narrative explaining risk drivers",
                  "An investor-ready summary draft",
                ].map((item) => (
                  <li key={item} className="flex gap-2">
                    <CheckCircle className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="rounded-xl border bg-card p-6">
              <h3 className="text-base font-semibold text-foreground">Risk reduction matters</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                The value isn't a prettier chart. It's defendable decisions. Confidence intervals + explainability help you move fast without adding hidden risk.
              </p>
              <div className="mt-6 flex flex-wrap gap-3">
                <Button size="sm" asChild data-testid="button-see-pricing">
                  <Link href="/pricing">See pricing</Link>
                </Button>
                <Button size="sm" variant="outline" asChild data-testid="button-read-faq">
                  <Link href="/faq">Read FAQ</Link>
                </Button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-16 md:py-20 text-center">
          <Zap className="mx-auto h-8 w-8 text-primary" />
          <h2 className="mt-4 text-2xl font-semibold tracking-tight text-foreground" data-testid="text-cta-heading">
            Ready to see your startup's future?
          </h2>
          <p className="mx-auto mt-2 max-w-lg text-muted-foreground">
            Join 500+ founders using FounderConsole to make explainable, data-driven decisions under uncertainty.
          </p>
          <div className="mt-6 flex justify-center gap-3">
            <Button size="lg" asChild data-testid="button-bottom-get-started">
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
