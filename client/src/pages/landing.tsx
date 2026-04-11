import { Link } from "wouter";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useSEO } from "@/lib/seo";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import {
  Plane,
  Sparkles,
  Target,
  Database,
  ArrowRight,
  Upload,
  ScanSearch,
  BarChart3,
  FlaskConical,
  MessageSquare,
  Gauge,
  TrendingUp,
  Shield,
  Zap,
  CheckCircle2,
  Check,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { useState } from "react";

const integrations = ["Stripe", "QuickBooks", "Gusto", "Mercury", "Brex", "Plaid", "Xero", "Shopify"];

const coreFeatures = [
  {
    icon: Database,
    title: "Digital Twin",
    description: "Your company modeled in real time. Every financial metric, team member, and data source unified into a living digital representation of your startup.",
    gradient: "from-blue-500/10 to-cyan-500/10",
  },
  {
    icon: FlaskConical,
    title: "Monte Carlo Simulator",
    description: "Test decisions before making them. Run thousands of scenarios to see P10/P50/P90 outcomes — replace guesswork with confidence bands investors respect.",
    gradient: "from-violet-500/10 to-purple-500/10",
  },
  {
    icon: Sparkles,
    title: "AI Founder Copilot",
    description: "Ask strategic questions in plain English. Get recommendations from parallel AI agents specialized in finance, strategy, and market analysis.",
    gradient: "from-amber-500/10 to-orange-500/10",
  },
  {
    icon: Target,
    title: "Decision Engine",
    description: "Track every decision with full context. Learn from outcomes, compare scenarios, and build an institutional memory for your company.",
    gradient: "from-emerald-500/10 to-green-500/10",
  },
];

const howItWorks = [
  {
    step: 1,
    icon: Upload,
    title: "Connect your data",
    description: "Link Stripe, QuickBooks, or upload a CSV. Your financial data flows in automatically.",
  },
  {
    step: 2,
    icon: ScanSearch,
    title: "Your company becomes a Digital Twin",
    description: "We build a live model of your startup — validated, structured, and ready for simulation.",
  },
  {
    step: 3,
    icon: FlaskConical,
    title: "Run simulations",
    description: "Test hiring plans, pricing changes, fundraising timing, and growth strategies before committing.",
  },
  {
    step: 4,
    icon: Sparkles,
    title: "AI recommends decisions",
    description: "Get ranked recommendations backed by data, with narratives you can defend to your board.",
  },
];

const differentiators = [
  {
    icon: Gauge,
    label: "Spreadsheets show the past",
    description: "Static snapshots that are outdated the moment you save them.",
    negative: true,
  },
  {
    icon: TrendingUp,
    label: "FounderConsole predicts the future",
    description: "Monte Carlo simulations, probabilistic forecasting, and AI-powered strategy.",
    negative: false,
  },
];

const landingFaqs = [
  {
    q: "What is FounderConsole?",
    a: "FounderConsole is an AI-powered financial intelligence platform for startups. It connects your financial data, builds a digital twin of your company, runs Monte Carlo simulations, and provides AI-powered strategic recommendations — replacing spreadsheets with simulations.",
  },
  {
    q: "Is FounderConsole free?",
    a: "Yes. All features are free during the public beta, including Monte Carlo simulations, AI copilot, cap table management, 37 data connectors, and board deck generation. No credit card is required.",
  },
  {
    q: "How does FounderConsole help with fundraising?",
    a: "FounderConsole includes a Fundraising OS with cap table management, dilution modeling, investor CRM, SAFE conversion modeling, and exit waterfall analysis. The AI copilot generates investor-ready reports, one-pagers, and board decks automatically.",
  },
  {
    q: "What data sources can I connect?",
    a: "FounderConsole supports 37 data connectors including Stripe, QuickBooks, Xero, Mercury, Brex, Plaid, Gusto, HubSpot, Shopify, Salesforce, and more. You can also upload CSV files or enter data manually.",
  },
  {
    q: "What is a Monte Carlo simulation?",
    a: "Monte Carlo simulation runs your financial model thousands of times with slightly different inputs each time, producing a probability distribution instead of a single forecast. You see P10 (pessimistic), P50 (median), and P90 (optimistic) outcomes for your runway and other metrics.",
  },
  {
    q: "How is this different from a spreadsheet?",
    a: "Spreadsheets give you one forecast based on one set of assumptions. FounderConsole runs thousands of scenarios, accounts for uncertainty, connects to live data sources, and uses AI to generate insights. It is the difference between a paper map and GPS navigation.",
  },
  {
    q: "What is a startup digital twin?",
    a: "A digital twin is a continuously updated virtual representation of your company. FounderConsole ingests data from your accounting, payment, banking, and payroll systems to create a live financial model that reflects your current reality — no manual updates needed.",
  },
  {
    q: "How long does setup take?",
    a: "Most founders are up and running in under five minutes. Connect your primary data source (Stripe, QuickBooks, or CSV), and FounderConsole automatically builds your digital twin and generates your first simulation.",
  },
];

const pricingTiers = [
  {
    name: "Free Beta",
    price: "$0",
    period: "",
    description: "All features unlocked during beta",
    features: [
      "Monte Carlo simulations",
      "AI Copilot (all LLMs)",
      "37 data connectors",
      "Cap table & fundraising",
      "Board deck generator",
      "Digital twin",
      "Team collaboration",
    ],
    highlighted: true,
  },
  {
    name: "Pro",
    price: "$49",
    period: "/month",
    description: "For scaling startups",
    features: [
      "Everything in Free",
      "Unlimited simulations",
      "Priority AI processing",
      "Custom connectors",
      "Advanced analytics",
      "Dedicated support",
      "API access",
    ],
    highlighted: false,
  },
];

const stats = [
  { value: "2.4M+", label: "Scenarios Simulated" },
  { value: "37+", label: "Data Connectors" },
  { value: "P10/P50/P90", label: "Confidence Bands" },
  { value: "<3s", label: "Simulation Time" },
];

const testimonials = [
  {
    quote: "FounderConsole replaced our entire spreadsheet stack. The Monte Carlo simulations gave us the confidence to time our Series A perfectly.",
    name: "Priya Sharma",
    role: "Co-founder & CEO, NovaPay",
  },
  {
    quote: "It's like having a CFO, strategist, and data scientist on call 24/7. The AI Copilot caught a burn rate issue we completely missed.",
    name: "Marcus Chen",
    role: "Founder, DataSync Labs",
  },
];

function PricingPreview() {
  return (
    <section className="border-t bg-card/30">
      <div className="mx-auto max-w-6xl px-4 py-20 md:py-24">
        <div className="text-center mb-14">
          <h2 className="text-3xl font-bold tracking-tight text-foreground" data-testid="text-pricing-heading">
            Simple, transparent pricing
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-muted-foreground">
            Start free. Upgrade when you need more power.
          </p>
        </div>
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 max-w-3xl mx-auto">
          {pricingTiers.map((tier) => (
            <Card
              key={tier.name}
              className={tier.highlighted ? "border-primary/40 shadow-lg shadow-primary/5" : ""}
              data-testid={`card-pricing-${tier.name.toLowerCase().replace(/\s+/g, "-")}`}
            >
              <CardHeader>
                {tier.highlighted && (
                  <Badge className="w-fit mb-2" data-testid="badge-popular">Most Popular</Badge>
                )}
                <CardTitle className="text-xl">{tier.name}</CardTitle>
                <div className="flex items-baseline gap-1 mt-2">
                  <span className="text-4xl font-bold text-foreground">{tier.price}</span>
                  <span className="text-muted-foreground">{tier.period}</span>
                </div>
                <p className="text-sm text-muted-foreground mt-1">{tier.description}</p>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2.5">
                  {tier.features.map((f) => (
                    <li key={f} className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Check className="h-4 w-4 text-primary flex-shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>
              </CardContent>
              <CardFooter>
                <Button
                  asChild
                  className="w-full"
                  variant={tier.highlighted ? "default" : "outline"}
                  data-testid={`button-pricing-${tier.name.toLowerCase().replace(/\s+/g, "-")}`}
                >
                  <Link href="/auth">
                    {tier.highlighted ? "Start Free" : "Get Started"}
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>
        <p className="mt-6 text-center text-xs text-muted-foreground">
          <Link href="/pricing" className="text-primary hover:underline">View full pricing details</Link>
        </p>
      </div>
    </section>
  );
}

function FAQSection() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <section className="border-t">
      <div className="mx-auto max-w-3xl px-4 py-20 md:py-24">
        <div className="text-center mb-14">
          <h2 className="text-3xl font-bold tracking-tight text-foreground" data-testid="text-faq-heading">
            Frequently asked questions
          </h2>
          <p className="mx-auto mt-3 max-w-lg text-muted-foreground">
            Everything you need to know about FounderConsole.
          </p>
        </div>
        <div className="space-y-3">
          {landingFaqs.map((faq, i) => (
            <div
              key={i}
              className="rounded-xl border bg-card/50 overflow-hidden"
              data-testid={`faq-item-${i}`}
            >
              <button
                className="flex w-full items-center justify-between p-5 text-left"
                onClick={() => setOpenIndex(openIndex === i ? null : i)}
                data-testid={`button-faq-${i}`}
              >
                <span className="font-medium text-foreground text-sm">{faq.q}</span>
                {openIndex === i ? (
                  <ChevronUp className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                ) : (
                  <ChevronDown className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                )}
              </button>
              {openIndex === i && (
                <div className="px-5 pb-5 text-sm text-muted-foreground leading-relaxed">
                  {faq.a}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export default function LandingPage() {
  useSEO({
    title: "FounderConsole — AI Decision Simulator for Founders",
    description:
      "FounderConsole is the AI-powered decision simulator for startup founders. Monte Carlo simulations, AI copilot, fundraising CRM, and 37 data connectors — replace spreadsheets with simulations.",
    path: "/",
    jsonLd: [
      {
        "@context": "https://schema.org",
        "@type": "Organization",
        name: "FounderConsole",
        url: "https://founderconsole.ai",
        logo: "https://founderconsole.ai/og-image.png",
        description: "AI-powered financial intelligence platform for startups. Investor-grade diligence, probabilistic simulation, and ranked decision recommendations.",
        sameAs: [
          "https://twitter.com/founderconsole",
          "https://linkedin.com/company/founderconsole",
          "https://github.com/founderconsole",
        ],
      },
      {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        name: "FounderConsole",
        applicationCategory: "BusinessApplication",
        operatingSystem: "Web",
        url: "https://founderconsole.ai",
        description: "AI-powered financial intelligence platform for startups with Monte Carlo simulations, fundraising CRM, and 37 data connectors.",
        offers: {
          "@type": "Offer",
          price: "0",
          priceCurrency: "USD",
          description: "Free during public beta — all features unlocked, no credit card required",
        },
        featureList: "Monte Carlo Simulation, AI Copilot, Fundraising CRM, Cap Table Management, 37 Data Connectors, Digital Twin, Strategic Briefings",
        screenshot: "https://founderconsole.ai/og-image.png",
      },
      {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        mainEntity: landingFaqs.map((faq) => ({
          "@type": "Question",
          name: faq.q,
          acceptedAnswer: { "@type": "Answer", text: faq.a },
        })),
      },
    ],
  });

  return (
    <MarketingLayout>
      <section className="relative">
        <div className="relative mx-auto max-w-6xl px-4 py-20 md:py-32 text-center">
          <Badge variant="secondary" className="mb-6 text-xs font-medium" data-testid="badge-hero-label">
            <Plane className="mr-1.5 h-3 w-3" />
            Financial Intelligence Platform
          </Badge>
          <h1 className="text-4xl font-bold tracking-tight text-foreground md:text-6xl lg:text-7xl leading-tight" data-testid="text-hero-title">
            The Flight Simulator
            <br />
            <span className="bg-gradient-to-r from-primary to-violet-500 bg-clip-text text-transparent">
              for Founders
            </span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg md:text-xl text-muted-foreground leading-relaxed" data-testid="text-hero-subtitle">
            Connect your company data, simulate the future, and get AI-powered decisions.
            <br className="hidden md:block" />
            Run your startup like a simulation.
          </p>
          <div className="mt-10 flex flex-wrap justify-center gap-4">
            <Button size="lg" className="h-12 px-8 text-base" asChild data-testid="button-hero-start-simulation">
              <Link href="/auth">
                Start Simulation
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button size="lg" variant="outline" className="h-12 px-8 text-base" asChild data-testid="button-hero-view-demo">
              <Link href="/demo">View Demo</Link>
            </Button>
          </div>
          <div className="mt-16 mx-auto max-w-3xl">
            <div className="rounded-xl border bg-card/80 backdrop-blur-sm p-6 md:p-8 shadow-lg">
              <div className="grid grid-cols-3 gap-6">
                <div className="text-center">
                  <p className="text-2xl md:text-3xl font-bold font-mono text-foreground" data-testid="text-preview-runway">18.2</p>
                  <p className="text-xs text-muted-foreground mt-1">Months Runway</p>
                  <div className="mt-2 h-1.5 bg-muted rounded-full overflow-hidden">
                    <div className="h-full bg-emerald-500 rounded-full" style={{ width: "72%" }} />
                  </div>
                </div>
                <div className="text-center">
                  <p className="text-2xl md:text-3xl font-bold font-mono text-foreground" data-testid="text-preview-growth">23%</p>
                  <p className="text-xs text-muted-foreground mt-1">MoM Growth</p>
                  <div className="mt-2 h-1.5 bg-muted rounded-full overflow-hidden">
                    <div className="h-full bg-primary rounded-full" style={{ width: "65%" }} />
                  </div>
                </div>
                <div className="text-center">
                  <p className="text-2xl md:text-3xl font-bold font-mono text-foreground" data-testid="text-preview-survival">84%</p>
                  <p className="text-xs text-muted-foreground mt-1">Survival (P50)</p>
                  <div className="mt-2 h-1.5 bg-muted rounded-full overflow-hidden">
                    <div className="h-full bg-violet-500 rounded-full" style={{ width: "84%" }} />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-10" data-testid="section-logo-cloud">
          <p className="text-center text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Connect your financial stack
          </p>
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
            <Badge variant="outline" className="text-muted-foreground">
              +29 more
            </Badge>
          </div>
        </div>
      </section>

      <section className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-20 md:py-24">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold tracking-tight text-foreground" data-testid="text-how-heading">
              How it works
            </h2>
            <p className="mx-auto mt-3 max-w-lg text-muted-foreground">
              From raw data to defensible decisions in four steps.
            </p>
          </div>
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
            {howItWorks.map((item) => (
              <div
                key={item.step}
                className="relative rounded-xl border bg-card/50 p-6"
                data-testid={`card-step-${item.step}`}
              >
                <div className="flex items-center gap-3 mb-4">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground text-sm font-bold">
                    {item.step}
                  </div>
                  <item.icon className="h-5 w-5 text-muted-foreground" />
                </div>
                <h3 className="font-semibold text-foreground">{item.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground leading-relaxed">{item.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t bg-card/20">
        <div className="mx-auto max-w-6xl px-4 py-20 md:py-24">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold tracking-tight text-foreground" data-testid="text-features-heading">
              Core capabilities
            </h2>
            <p className="mx-auto mt-3 max-w-xl text-muted-foreground">
              Everything you need to understand your runway, test decisions, and get AI strategy advice.
            </p>
          </div>
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            {coreFeatures.map((f) => (
              <div
                key={f.title}
                className={`rounded-xl border p-8 bg-gradient-to-br ${f.gradient}`}
                data-testid={`card-feature-${f.title.toLowerCase().replace(/\s+/g, "-")}`}
              >
                <f.icon className="h-6 w-6 text-primary" />
                <h3 className="mt-4 text-lg font-semibold text-foreground">{f.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground leading-relaxed">{f.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-20 md:py-24">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold tracking-tight text-foreground" data-testid="text-diff-heading">
              Replace spreadsheets with simulations
            </h2>
            <p className="mx-auto mt-3 max-w-xl text-muted-foreground">
              Most financial tools show you the past. FounderConsole predicts the future.
            </p>
          </div>
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 max-w-3xl mx-auto">
            {differentiators.map((d) => (
              <div
                key={d.label}
                className={`rounded-xl border p-6 ${d.negative ? "bg-muted/30 opacity-60" : "bg-gradient-to-br from-primary/5 to-violet-500/5 border-primary/20"}`}
                data-testid={`card-diff-${d.negative ? "old" : "new"}`}
              >
                <div className="flex items-center gap-3 mb-3">
                  <d.icon className={`h-5 w-5 ${d.negative ? "text-muted-foreground" : "text-primary"}`} />
                  <span className={`font-semibold ${d.negative ? "text-muted-foreground line-through" : "text-foreground"}`}>
                    {d.label}
                  </span>
                </div>
                <p className="text-sm text-muted-foreground">{d.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t bg-card/20">
        <div className="mx-auto max-w-6xl px-4 py-16 md:py-20">
          <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
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
        <div className="mx-auto max-w-6xl px-4 py-16 md:py-20">
          <div className="grid grid-cols-1 gap-8 md:grid-cols-2">
            {testimonials.map((t) => (
              <blockquote
                key={t.name}
                className="rounded-xl border bg-card/50 p-8"
                data-testid={`testimonial-${t.name.toLowerCase().replace(/\s+/g, "-")}`}
              >
                <p className="text-foreground leading-relaxed italic">
                  &ldquo;{t.quote}&rdquo;
                </p>
                <footer className="mt-4">
                  <p className="font-semibold text-foreground text-sm">{t.name}</p>
                  <p className="text-xs text-muted-foreground">{t.role}</p>
                </footer>
              </blockquote>
            ))}
          </div>
        </div>
      </section>

      <PricingPreview />
      <FAQSection />

      <section className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-20 md:py-24 text-center">
          <Zap className="mx-auto h-8 w-8 text-primary mb-4" />
          <h2 className="text-3xl font-bold tracking-tight text-foreground" data-testid="text-cta-heading">
            Run your startup like a simulation
          </h2>
          <p className="mx-auto mt-3 max-w-lg text-muted-foreground">
            Understand your runway. Test decisions before making them. Get AI strategy advice.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-4">
            <Button size="lg" className="h-12 px-8 text-base" asChild data-testid="button-bottom-start-trial">
              <Link href="/auth">
                Start Free Trial
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </div>
          <p className="mt-4 text-xs text-muted-foreground">
            No credit card required. Free tier includes 50 simulations/month.
          </p>
        </div>
      </section>
    </MarketingLayout>
  );
}
