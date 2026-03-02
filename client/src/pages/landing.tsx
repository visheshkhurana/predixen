import { Link } from "wouter";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useSEO } from "@/lib/seo";
import {
  Dice5,
  Sparkles,
  ShieldCheck,
  PieChart,
  TrendingUp,
  Plug,
  Database,
  Play,
  CheckCircle,
  ArrowRight,
} from "lucide-react";

const integrations = ["Stripe", "QuickBooks", "Gusto", "Mercury", "Brex", "Plaid"];

const features = [
  {
    icon: Dice5,
    title: "Monte Carlo Simulations",
    description: "Run thousands of scenarios to see P10/P50/P90 outcomes. Replace single-point guesses with confidence bands that investors respect.",
  },
  {
    icon: Sparkles,
    title: "AI Copilot",
    description: "Ask strategic questions in plain English. Get recommendations powered by multi-LLM routing across GPT-4, Claude, and Gemini.",
  },
  {
    icon: ShieldCheck,
    title: "Truth Scan",
    description: "Validate your financial data with automated Z-score anomaly detection, multi-stage checks, and confidence scoring before every decision.",
  },
  {
    icon: PieChart,
    title: "Cap Table",
    description: "Model SAFE and note conversions, visualize dilution, and maintain a clean cap table that's always ready for due diligence.",
  },
  {
    icon: TrendingUp,
    title: "Fundraising OS",
    description: "Time your raise with data, not intuition. Investor room, pitch-ready reports, and scenario-backed fundraising strategy.",
  },
  {
    icon: Plug,
    title: "Data Connectors",
    description: "Connect 37 integrations including QuickBooks, Stripe, Gusto, and Mercury. Auto-sync with multi-currency support.",
  },
];

const steps = [
  {
    icon: Database,
    title: "Connect Your Data",
    description: "Link your financial tools in one click. Stripe, QuickBooks, Gusto, Mercury, and 33 more.",
  },
  {
    icon: Play,
    title: "Run Simulations",
    description: "Monte Carlo engine generates thousands of outcomes with P10/P50/P90 confidence bands.",
  },
  {
    icon: CheckCircle,
    title: "Make Decisions",
    description: "Get ranked recommendations with explainable AI narratives you can defend to investors and your board.",
  },
];

const stats = [
  { value: "2.4M+", label: "Scenarios Simulated" },
  { value: "37", label: "Integrations" },
  { value: "$2.1B+", label: "Revenue Analyzed" },
  { value: "P10/P50/P90", label: "Confidence Bands" },
];

export default function LandingPage() {
  useSEO({
    title: "FounderConsole — AI Financial Intelligence for Startups",
    description:
      "AI-powered simulation, forecasting, and decision support that gives founders the financial clarity to build with confidence.",
  });

  return (
    <MarketingLayout>
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-primary/5 to-transparent pointer-events-none" />
        <div className="relative mx-auto max-w-6xl px-4 py-16 md:py-24 text-center">
          <p className="text-xs font-semibold uppercase tracking-wide text-primary" data-testid="text-trust-tagline">
            Trusted by 500+ startups
          </p>
          <h1 className="mt-3 text-4xl font-bold tracking-tight text-foreground md:text-5xl lg:text-6xl" data-testid="text-hero-title">
            Financial Intelligence
            <br />
            for Founders
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-muted-foreground" data-testid="text-hero-subtitle">
            AI-powered simulation, forecasting, and decision support that gives founders the financial clarity to build with confidence.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
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
        </div>
      </section>

      <section className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-10" data-testid="section-logo-cloud">
          <p className="text-center text-xs font-semibold uppercase tracking-wide text-muted-foreground">Powering insights from</p>
          <div className="mt-4 flex flex-wrap justify-center gap-2">
            {integrations.map((name) => (
              <Badge
                key={name}
                variant="secondary"
                className="text-muted-foreground"
                data-testid={`badge-integration-${name.toLowerCase()}`}
              >
                {name}
              </Badge>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-16 md:py-20">
          <h2 className="text-center text-2xl font-semibold tracking-tight text-foreground" data-testid="text-features-heading">
            Everything founders need to decide with confidence
          </h2>
          <p className="mx-auto mt-2 max-w-xl text-center text-muted-foreground">
            Forecast, simulate, compare, explain, and report — in one place.
          </p>
          <div className="mt-10 grid grid-cols-1 gap-6 md:grid-cols-3">
            {features.map((f) => (
              <div
                key={f.title}
                className="rounded-xl border bg-card/50 p-6"
                data-testid={`card-feature-${f.title.toLowerCase().replace(/\s+/g, "-")}`}
              >
                <f.icon className="h-5 w-5 text-primary" />
                <h3 className="mt-3 font-semibold text-foreground">{f.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{f.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t bg-card/30">
        <div className="mx-auto max-w-6xl px-4 py-16 md:py-20">
          <h2 className="text-center text-2xl font-semibold tracking-tight text-foreground" data-testid="text-how-heading">
            How it works
          </h2>
          <p className="mx-auto mt-2 max-w-lg text-center text-muted-foreground">
            Three steps from raw data to defensible decisions.
          </p>
          <div className="mt-10 grid grid-cols-1 gap-8 md:grid-cols-3">
            {steps.map((step, i) => (
              <div key={step.title} className="text-center" data-testid={`card-step-${i + 1}`}>
                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-primary text-primary-foreground">
                  <span className="text-lg font-bold">{i + 1}</span>
                </div>
                <step.icon className="mx-auto mt-4 h-6 w-6 text-muted-foreground" />
                <h3 className="mt-3 font-semibold text-foreground">{step.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{step.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-16 md:py-20">
          <div className="grid grid-cols-2 gap-6 md:grid-cols-4">
            {stats.map((stat) => (
              <div key={stat.label} className="text-center" data-testid={`stat-${stat.label.toLowerCase().replace(/\s+/g, "-")}`}>
                <p className="text-3xl font-bold font-mono text-foreground">{stat.value}</p>
                <p className="mt-1 text-sm text-muted-foreground">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t bg-card/30">
        <div className="mx-auto max-w-6xl px-4 py-16 md:py-20">
          <blockquote className="mx-auto max-w-2xl text-center" data-testid="section-testimonial">
            <p className="text-lg italic text-foreground">
              &ldquo;FounderConsole replaced our entire spreadsheet stack. The Monte Carlo simulations gave us the confidence to time our Series A perfectly — and the AI narrative helped us explain our decision to the board in five minutes.&rdquo;
            </p>
            <footer className="mt-4">
              <p className="font-semibold text-foreground" data-testid="text-testimonial-name">Priya Sharma</p>
              <p className="text-sm text-muted-foreground" data-testid="text-testimonial-company">Co-founder &amp; CEO, NovaPay</p>
            </footer>
          </blockquote>
        </div>
      </section>

      <section className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-16 md:py-20 text-center">
          <h2 className="text-2xl font-semibold tracking-tight text-foreground" data-testid="text-cta-heading">
            Ready to see your startup's future?
          </h2>
          <p className="mx-auto mt-2 max-w-lg text-muted-foreground">
            Join 500+ founders using FounderConsole to make explainable, data-driven decisions under uncertainty.
          </p>
          <div className="mt-6 flex justify-center">
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
