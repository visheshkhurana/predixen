import { Link } from "wouter";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  BarChart3,
  Bot,
  ShieldCheck,
  PieChart,
  Rocket,
  Cable,
  Database,
  Play,
  BrainCircuit,
  ArrowRight,
  CheckCircle,
  Quote,
  Zap,
  TrendingUp,
  Target,
} from "lucide-react";

const features = [
  {
    icon: BarChart3,
    title: "Monte Carlo Simulations",
    description:
      "Run thousands of probabilistic scenarios to understand your startup's range of outcomes with P10, P50, and P90 confidence intervals.",
  },
  {
    icon: Bot,
    title: "AI Copilot",
    description:
      "Get strategic recommendations powered by GPT-4, Claude, and Gemini. Ask questions about your financials in plain English.",
  },
  {
    icon: ShieldCheck,
    title: "Truth Scan",
    description:
      "Validate your financial data with automated anomaly detection, Z-score analysis, and confidence scoring before making decisions.",
  },
  {
    icon: PieChart,
    title: "Cap Table Management",
    description:
      "Model SAFE and note conversions, understand dilution scenarios, and keep your cap table clean for fundraising readiness.",
  },
  {
    icon: Rocket,
    title: "Fundraising OS",
    description:
      "Track investor pipeline, generate data-backed pitch materials, and model fundraise outcomes with intelligent scenario planning.",
  },
  {
    icon: Cable,
    title: "Data Connectors",
    description:
      "Sync financial data from 37+ integrations including Stripe, QuickBooks, Gusto, Mercury, and more — automatically.",
  },
];

const integrations = [
  "Stripe",
  "QuickBooks",
  "Gusto",
  "Mercury",
  "Brex",
  "Plaid",
];

const steps = [
  {
    icon: Database,
    title: "Connect Data",
    description:
      "Link your financial accounts and data sources in minutes. We support 37+ integrations out of the box.",
  },
  {
    icon: BrainCircuit,
    title: "Run Simulations",
    description:
      "Our engine runs thousands of Monte Carlo scenarios to map your startup's probability landscape.",
  },
  {
    icon: Target,
    title: "Make Decisions",
    description:
      "Get AI-powered strategic recommendations backed by your real data and simulation results.",
  },
];

const stats = [
  { value: "2.4M+", label: "Scenarios Simulated" },
  { value: "37", label: "Integrations" },
  { value: "$2.1B+", label: "Revenue Analyzed" },
  { value: "P10/P50/P90", label: "Confidence Intervals" },
];

export default function LandingPage() {
  return (
    <MarketingLayout>
      <section
        data-testid="section-hero"
        className="relative py-20 md:py-32 overflow-hidden"
      >
        <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-transparent to-primary/5 pointer-events-none" />
        <div className="relative max-w-6xl mx-auto px-4 sm:px-6 text-center">
          <Badge variant="secondary" className="mb-6" data-testid="badge-social-proof-top">
            <CheckCircle className="mr-1.5 w-3 h-3" />
            Trusted by 500+ startups
          </Badge>
          <h1
            className="text-4xl md:text-6xl font-bold tracking-tight mb-6"
            data-testid="text-hero-headline"
          >
            Financial Intelligence
            <br />
            <span className="text-primary">for Founders</span>
          </h1>
          <p
            className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-10"
            data-testid="text-hero-subheadline"
          >
            AI-powered simulation, forecasting, and decision support that gives
            founders the financial clarity to build with confidence.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-4">
            <Link href="/auth">
              <Button size="lg" data-testid="button-hero-start-free">
                Start Free
                <ArrowRight className="ml-1" />
              </Button>
            </Link>
            <Link href="/demo">
              <Button
                size="lg"
                variant="outline"
                data-testid="button-hero-watch-demo"
              >
                <Play className="mr-1" />
                Watch Demo
              </Button>
            </Link>
          </div>
        </div>
      </section>

      <section
        data-testid="section-logo-cloud"
        className="py-12 border-y border-border"
      >
        <div className="max-w-6xl mx-auto px-4 sm:px-6 text-center">
          <p className="text-sm text-muted-foreground mb-6">
            Powering insights from
          </p>
          <div className="flex flex-wrap items-center justify-center gap-4">
            {integrations.map((name) => (
              <Badge
                key={name}
                variant="secondary"
                className="text-muted-foreground no-default-hover-elevate"
                data-testid={`badge-integration-${name.toLowerCase()}`}
              >
                {name}
              </Badge>
            ))}
          </div>
        </div>
      </section>

      <section
        data-testid="section-features"
        className="py-20 md:py-28"
      >
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-14">
            <h2 className="text-3xl md:text-4xl font-bold mb-4" data-testid="text-features-headline">
              Everything You Need to Navigate Uncertainty
            </h2>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              From real-time data ingestion to Monte Carlo simulations, FounderConsole
              gives you the tools that used to be reserved for CFOs at public
              companies.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature) => (
              <Card
                key={feature.title}
                data-testid={`card-feature-${feature.title.toLowerCase().replace(/\s+/g, "-")}`}
              >
                <CardContent className="p-6">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="flex items-center justify-center w-10 h-10 rounded-md bg-primary/10">
                      <feature.icon className="w-5 h-5 text-primary" />
                    </div>
                    <h3 className="font-semibold text-lg">{feature.title}</h3>
                  </div>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {feature.description}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <section
        data-testid="section-how-it-works"
        className="py-20 md:py-28 bg-muted/30"
      >
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-14">
            <h2 className="text-3xl md:text-4xl font-bold mb-4" data-testid="text-how-it-works-headline">
              How It Works
            </h2>
            <p className="text-muted-foreground max-w-xl mx-auto">
              Three steps to turn your raw financial data into actionable intelligence.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {steps.map((step, index) => (
              <div
                key={step.title}
                className="text-center"
                data-testid={`step-${index + 1}`}
              >
                <div className="flex items-center justify-center w-14 h-14 rounded-full bg-primary/10 mx-auto mb-5">
                  <span className="text-primary font-bold text-lg">{index + 1}</span>
                </div>
                <div className="flex items-center justify-center mb-3">
                  <step.icon className="w-6 h-6 text-primary mr-2" />
                  <h3 className="font-semibold text-lg">{step.title}</h3>
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed max-w-xs mx-auto">
                  {step.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section
        data-testid="section-metrics"
        className="py-20 md:py-28"
      >
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 md:gap-8">
            {stats.map((stat) => (
              <div
                key={stat.label}
                className="text-center"
                data-testid={`stat-${stat.label.toLowerCase().replace(/[\s\/]+/g, "-")}`}
              >
                <div className="text-3xl md:text-4xl font-bold text-primary mb-2 font-mono">
                  {stat.value}
                </div>
                <div className="text-sm text-muted-foreground">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section
        data-testid="section-testimonial"
        className="py-20 md:py-28 bg-muted/30"
      >
        <div className="max-w-3xl mx-auto px-4 sm:px-6 text-center">
          <Quote className="w-10 h-10 text-primary/30 mx-auto mb-6" />
          <blockquote
            className="text-xl md:text-2xl font-medium leading-relaxed mb-6"
            data-testid="text-testimonial-quote"
          >
            "FounderConsole replaced three spreadsheets, two consultants, and weeks
            of manual modeling. Now I can see my startup's future in minutes, not
            months."
          </blockquote>
          <div data-testid="text-testimonial-author">
            <p className="font-semibold">Priya Sharma</p>
            <p className="text-sm text-muted-foreground">
              CEO & Co-Founder, NovaTech Solutions
            </p>
          </div>
        </div>
      </section>

      <section
        data-testid="section-cta"
        className="py-20 md:py-28"
      >
        <div className="max-w-3xl mx-auto px-4 sm:px-6 text-center">
          <Zap className="w-10 h-10 text-primary mx-auto mb-6" />
          <h2
            className="text-3xl md:text-4xl font-bold mb-4"
            data-testid="text-cta-headline"
          >
            Ready to see your startup's future?
          </h2>
          <p className="text-muted-foreground mb-8 max-w-lg mx-auto">
            Join hundreds of founders who use FounderConsole to make
            data-driven decisions with confidence. Free during beta.
          </p>
          <Link href="/auth">
            <Button size="lg" data-testid="button-cta-get-started">
              Get Started Free
              <ArrowRight className="ml-1" />
            </Button>
          </Link>
        </div>
      </section>
    </MarketingLayout>
  );
}
