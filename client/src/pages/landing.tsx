import { Link } from "wouter";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useSEO } from "@/lib/seo";
import {
  Plane,
  Sparkles,
  Target,
  Database,
  ArrowRight,
  Upload,
  ScanSearch,
  FlaskConical,
  Gauge,
  TrendingUp,
  Zap,
  Check,
  ChevronDown,
} from "lucide-react";
import { useRef, useState } from "react";
import {
  AnimatePresence,
  motion,
  useReducedMotion,
  useScroll,
  useSpring,
  useTransform,
} from "framer-motion";
import { NumberTicker } from "@/components/ui/motion-primitives";
import { Tilt3D, Magnetic } from "@/components/marketing/redesign/Tilt3D";
import { MonteCarloDemo } from "@/components/marketing/redesign/MonteCarloDemo";
import { CopilotDemo } from "@/components/marketing/redesign/CopilotDemo";
import { TwinDashboardDemo } from "@/components/marketing/redesign/TwinDashboardDemo";
import { Marquee } from "@/components/marketing/redesign/Marquee";
import { trackFunnel } from "@/lib/funnel";

const integrations = [
  "Stripe", "QuickBooks", "Gusto", "Mercury", "Brex", "Plaid", "Xero", "Shopify",
  "HubSpot", "Salesforce", "Ramp", "Deel",
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

const landingFaqs = [
  {
    q: "What is FounderConsole?",
    a: "FounderConsole is an AI-powered financial intelligence platform for startups. It connects your financial data, builds a digital twin of your company, runs Monte Carlo simulations, and provides AI-powered strategic recommendations — replacing spreadsheets with simulations.",
  },
  {
    q: "Is there a free trial?",
    a: "Yes. Every new account starts with a free 30-day trial with full access to every feature — no credit card required. After the trial you can continue on the Free plan or subscribe to Starter ($29), Growth ($49), or Scale ($99) per month.",
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
    name: "Free",
    price: "$0",
    period: "",
    description: "Explore the platform at your own pace.",
    features: ["1 company", "3 simulations / month", "10 copilot messages / month", "CSV upload & manual entry", "Basic dashboard"],
    highlighted: false,
    cta: "Get Started Free",
  },
  {
    name: "Starter",
    price: "$29",
    period: "/month",
    description: "For early-stage founders finding their footing.",
    features: ["50 simulations / month", "100 copilot messages / month", "2 data connectors", "Truth Scan & Stress Tests", "Industry benchmarks"],
    highlighted: false,
    cta: "Start Free Trial",
  },
  {
    name: "Growth",
    price: "$49",
    period: "/month",
    description: "For scaling startups that decide weekly.",
    features: ["Up to 3 companies", "Unlimited simulations & copilot", "10 data connectors", "Fundraising OS & cap table", "Board deck export"],
    highlighted: true,
    cta: "Start Free Trial",
  },
  {
    name: "Scale",
    price: "$99",
    period: "/month",
    description: "Full power for serious founders.",
    features: ["Unlimited companies & connectors", "Flight Simulator (AI agents)", "Digital Twin & Investor Room", "Hiring Planner", "Cross-company intelligence"],
    highlighted: false,
    cta: "Start Free Trial",
  },
];

const stats = [
  { value: 37, suffix: "+", label: "Data Connectors" },
  { value: 24, suffix: "+", label: "Metrics Tracked" },
  { value: 3, suffix: " bands", label: "P10 / P50 / P90" },
  { value: 10, suffix: "K runs", label: "Per Simulation" },
];

/* ---------------------------------- hero ---------------------------------- */

function HeroTitle() {
  const reduced = useReducedMotion();
  const lines: [string, boolean][] = [
    ["The Flight Simulator", false],
    ["for Founders", true],
  ];
  return (
    <h1
      className="text-4xl font-bold tracking-tight text-foreground md:text-6xl lg:text-7xl leading-[1.05]"
      data-testid="text-hero-title"
    >
      {lines.map(([line, gradient], li) => (
        <span key={line} className="block overflow-hidden pb-1">
          {line.split(" ").map((word, wi) => (
            <motion.span
              key={word + wi}
              className={`inline-block mr-[0.24em] ${
                gradient
                  ? "bg-gradient-to-r from-primary via-violet-500 to-primary bg-[length:200%_auto] bg-clip-text text-transparent animate-[shimmer_3s_linear_infinite]"
                  : ""
              }`}
              initial={reduced ? false : { y: "110%", opacity: 0 }}
              animate={{ y: "0%", opacity: 1 }}
              transition={{ duration: 0.7, delay: 0.15 + li * 0.18 + wi * 0.07, ease: [0.22, 1, 0.36, 1] }}
            >
              {word}
            </motion.span>
          ))}
        </span>
      ))}
    </h1>
  );
}

function Hero() {
  const reduced = useReducedMotion();
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end start"] });
  const heroY = useTransform(scrollYProgress, [0, 1], ["0%", "12%"]);
  const heroOpacity = useTransform(scrollYProgress, [0, 0.9], [1, 0.35]);
  const demoY = useTransform(scrollYProgress, [0, 1], ["0%", "-6%"]);

  return (
    <section ref={ref} className="relative overflow-hidden">
      <div className="aurora-hero" aria-hidden />
      <div className="grid-floor" aria-hidden />
      <motion.div
        style={reduced ? undefined : { y: heroY, opacity: heroOpacity }}
        className="relative mx-auto max-w-6xl px-4 pt-20 md:pt-28 pb-10 text-center"
      >
        <motion.div
          initial={reduced ? false : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <Badge variant="secondary" className="mb-6 text-xs font-medium" data-testid="badge-hero-label">
            <Plane className="mr-1.5 h-3 w-3" />
            Financial Intelligence Platform
          </Badge>
        </motion.div>

        <HeroTitle />

        <motion.p
          initial={reduced ? false : { opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.55 }}
          className="mx-auto mt-6 max-w-2xl text-lg md:text-xl text-muted-foreground leading-relaxed"
          data-testid="text-hero-subtitle"
        >
          Know your real runway, pressure-test every big decision before you commit, and get AI strategy
          you can take to your board. Run your startup like a simulation.
        </motion.p>

        <motion.div
          initial={reduced ? false : { opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.7 }}
          className="mt-10 flex flex-wrap justify-center gap-4"
        >
          <Magnetic>
            <Button
              size="lg"
              className="h-12 px-8 text-base shadow-lg shadow-primary/25 hover:shadow-xl hover:shadow-primary/40 transition-shadow duration-300"
              asChild
              data-testid="button-hero-start-simulation"
            >
              <Link href="/auth?tab=register" onClick={() => trackFunnel("cta_click", { location: "hero" })}>
                Start Simulation
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </Magnetic>
          <Button size="lg" variant="outline" className="h-12 px-8 text-base backdrop-blur" asChild data-testid="button-hero-view-demo">
            <Link href="/demo">View Demo</Link>
          </Button>
        </motion.div>
        <motion.p
          initial={reduced ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.9 }}
          className="mt-4 text-xs text-muted-foreground"
        >
          Free 30-day trial · No credit card required
        </motion.p>
      </motion.div>

      <motion.div
        style={reduced ? undefined : { y: demoY }}
        initial={reduced ? false : { opacity: 0, y: 60, rotateX: 14 }}
        animate={{ opacity: 1, y: 0, rotateX: 0 }}
        transition={{ duration: 0.9, delay: 0.9, ease: [0.22, 1, 0.36, 1] }}
        className="relative mx-auto max-w-4xl px-4 pb-20"
        data-testid="hero-demo-wrapper"
      >
        <TwinDashboardDemo />
      </motion.div>
    </section>
  );
}

/* ------------------------------ how it works ------------------------------ */

function HowItWorks() {
  const reduced = useReducedMotion();
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start 75%", "end 60%"] });
  const line = useSpring(scrollYProgress, { stiffness: 90, damping: 25 });

  return (
    <section className="border-t">
      <div className="mx-auto max-w-6xl px-4 py-20 md:py-24">
        <motion.div
          initial={reduced ? false : { opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-10%" }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-foreground" data-testid="text-how-heading">
            How it works
          </h2>
          <p className="mx-auto mt-3 max-w-lg text-muted-foreground">From raw data to defensible decisions in four steps.</p>
        </motion.div>

        <div ref={ref} className="relative">
          <div className="absolute left-[19px] md:left-1/2 top-0 bottom-0 w-px bg-border md:-translate-x-1/2" aria-hidden />
          <motion.div
            className="absolute left-[19px] md:left-1/2 top-0 bottom-0 w-px bg-gradient-to-b from-primary to-violet-500 md:-translate-x-1/2 origin-top"
            style={reduced ? { scaleY: 1 } : { scaleY: line }}
            aria-hidden
          />
          <div className="space-y-10 md:space-y-16">
            {howItWorks.map((item, i) => {
              const left = i % 2 === 0;
              return (
                <motion.div
                  key={item.step}
                  initial={reduced ? false : { opacity: 0, y: 32, x: 0 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: "-12%" }}
                  transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
                  className={`relative flex md:items-center gap-6 ${left ? "md:flex-row" : "md:flex-row-reverse"}`}
                  data-testid={`card-step-${item.step}`}
                >
                  <div className="relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground text-sm font-bold shadow-lg shadow-primary/30 md:absolute md:left-1/2 md:-translate-x-1/2">
                    {item.step}
                  </div>
                  <div className={`flex-1 md:w-[calc(50%-3rem)] md:flex-none ${left ? "md:mr-auto md:pr-14 md:text-right" : "md:ml-auto md:pl-14"}`}>
                    <div className="rounded-xl glass-subtle p-6 hover:shadow-lg transition-shadow duration-300">
                      <div className={`flex items-center gap-2.5 mb-2 ${left ? "md:justify-end" : ""}`}>
                        <item.icon className="h-5 w-5 text-primary" />
                        <h3 className="font-semibold text-foreground">{item.title}</h3>
                      </div>
                      <p className="text-sm text-muted-foreground leading-relaxed">{item.description}</p>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}

/* ------------------------------- demo rows -------------------------------- */

function DemoRow({
  eyebrow,
  title,
  copy,
  bullets,
  demo,
  flip = false,
  testId,
}: {
  eyebrow: string;
  title: string;
  copy: string;
  bullets: string[];
  demo: React.ReactNode;
  flip?: boolean;
  testId: string;
}) {
  const reduced = useReducedMotion();
  return (
    <div className={`grid items-center gap-10 lg:grid-cols-2 ${flip ? "lg:[&>*:first-child]:order-2" : ""}`} data-testid={testId}>
      <motion.div
        initial={reduced ? false : { opacity: 0, x: flip ? 40 : -40 }}
        whileInView={{ opacity: 1, x: 0 }}
        viewport={{ once: true, margin: "-15%" }}
        transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
      >
        <p className="text-xs font-semibold uppercase tracking-widest text-primary">{eyebrow}</p>
        <h3 className="mt-2 text-2xl md:text-3xl font-bold tracking-tight text-foreground">{title}</h3>
        <p className="mt-4 text-muted-foreground leading-relaxed">{copy}</p>
        <ul className="mt-6 space-y-2.5">
          {bullets.map((b) => (
            <li key={b} className="flex items-start gap-2.5 text-sm text-muted-foreground">
              <Check className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
              {b}
            </li>
          ))}
        </ul>
      </motion.div>
      <motion.div
        initial={reduced ? false : { opacity: 0, y: 40, scale: 0.96 }}
        whileInView={{ opacity: 1, y: 0, scale: 1 }}
        viewport={{ once: true, margin: "-15%" }}
        transition={{ duration: 0.7, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
      >
        <Tilt3D maxTilt={5}>{demo}</Tilt3D>
      </motion.div>
    </div>
  );
}

function FeatureDemos() {
  return (
    <section className="border-t bg-card/20">
      <div className="mx-auto max-w-6xl px-4 py-20 md:py-28 space-y-24 md:space-y-32">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-10%" }}
          transition={{ duration: 0.6 }}
          className="text-center"
        >
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-foreground" data-testid="text-demos-heading">
            See it think
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-muted-foreground">
            These aren't screenshots — they're live, working previews of what FounderConsole does with your numbers.
          </p>
        </motion.div>

        <DemoRow
          eyebrow="Monte Carlo Simulator"
          title="10,000 futures, before you commit"
          copy="One forecast is a guess. FounderConsole runs your model ten thousand times with realistic uncertainty, so every big decision comes with confidence bands investors respect."
          bullets={[
            "P10 / P50 / P90 runway outcomes, not single-point guesses",
            "Stress-test hiring, pricing, and fundraising timing",
            "Results in seconds, on live data",
          ]}
          demo={<MonteCarloDemo />}
          testId="row-demo-monte-carlo"
        />

        <DemoRow
          flip
          eyebrow="AI Founder Copilot"
          title="Board-level answers in plain English"
          copy="Ask strategic questions the way you'd ask a CFO. The copilot reads your digital twin, runs the numbers, and answers with evidence — impact quantified, assumptions stated."
          bullets={[
            "Parallel AI agents for finance, strategy, and market analysis",
            "Every answer is backed by your live simulation data",
            "Export narratives straight into board decks",
          ]}
          demo={<CopilotDemo />}
          testId="row-demo-copilot"
        />

        <DemoRow
          eyebrow="Decision Engine"
          title="Institutional memory for every call you make"
          copy="Track each decision with its context, compare the scenarios you considered, and learn from outcomes. Your company stops repeating mistakes — and starts compounding judgment."
          bullets={[
            "Ranked recommendations with full reasoning trails",
            "Compare scenarios side by side before committing",
            "Outcome tracking closes the loop automatically",
          ]}
          demo={<DecisionMini />}
          testId="row-demo-decisions"
        />
      </div>
    </section>
  );
}

function DecisionMini() {
  const reduced = useReducedMotion();
  const options = [
    { label: "Hire 2 engineers in Q4", score: 86, tone: "bg-emerald-500" },
    { label: "Stagger hires 8 weeks apart", score: 92, tone: "bg-primary" },
    { label: "Delay until Series A closes", score: 61, tone: "bg-amber-500" },
  ];
  return (
    <div className="rounded-2xl glass-medium p-5 md:p-6" data-testid="demo-decisions">
      <div className="flex items-center gap-2 mb-4">
        <div className="h-7 w-7 rounded-md bg-emerald-500/15 flex items-center justify-center">
          <Target className="h-3.5 w-3.5 text-emerald-400" />
        </div>
        <span className="text-sm font-medium text-foreground">Decision — Q4 hiring plan</span>
      </div>
      <div className="space-y-3">
        {options
          .slice()
          .sort((a, b) => b.score - a.score)
          .map((o, i) => (
            <motion.div
              key={o.label}
              initial={reduced ? false : { opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true, margin: "-10%" }}
              transition={{ delay: i * 0.15, duration: 0.5 }}
              className={`rounded-xl border p-4 ${i === 0 ? "border-primary/40 bg-primary/5" : "bg-card/60"}`}
            >
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm text-foreground">{o.label}</span>
                {i === 0 && (
                  <span className="rounded-full bg-primary/15 border border-primary/25 px-2 py-0.5 text-[10px] font-semibold text-primary">
                    Recommended
                  </span>
                )}
              </div>
              <div className="mt-2.5 flex items-center gap-3">
                <div className="h-1.5 flex-1 rounded-full bg-muted overflow-hidden">
                  <motion.div
                    className={`h-full rounded-full ${o.tone}`}
                    initial={reduced ? { width: `${o.score}%` } : { width: 0 }}
                    whileInView={{ width: `${o.score}%` }}
                    viewport={{ once: true, margin: "-10%" }}
                    transition={{ duration: 1, delay: 0.2 + i * 0.15, ease: "easeOut" }}
                  />
                </div>
                <span className="text-xs font-mono font-bold text-muted-foreground w-8 text-right">{o.score}</span>
              </div>
            </motion.div>
          ))}
      </div>
    </div>
  );
}

/* ----------------------------- comparison / stats ----------------------------- */

function Comparison() {
  const reduced = useReducedMotion();
  const items = [
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
  return (
    <section className="border-t">
      <div className="mx-auto max-w-6xl px-4 py-20 md:py-24">
        <div className="text-center mb-14">
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-foreground" data-testid="text-diff-heading">
            Replace spreadsheets with simulations
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-muted-foreground">
            Most financial tools show you the past. FounderConsole predicts the future.
          </p>
        </div>
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 max-w-3xl mx-auto">
          {items.map((d, i) => (
            <motion.div
              key={d.label}
              initial={reduced ? false : { opacity: 0, y: 24, rotateY: d.negative ? -6 : 6 }}
              whileInView={{ opacity: 1, y: 0, rotateY: 0 }}
              viewport={{ once: true, margin: "-15%" }}
              transition={{ duration: 0.6, delay: i * 0.15 }}
              className={`rounded-xl border p-6 transition-all duration-300 hover:shadow-md ${
                d.negative
                  ? "bg-muted/30 opacity-60"
                  : "bg-gradient-to-br from-primary/5 to-violet-500/5 border-primary/20 hover:-translate-y-0.5"
              }`}
              data-testid={`card-diff-${d.negative ? "old" : "new"}`}
            >
              <div className="flex items-center gap-3 mb-3">
                <d.icon className={`h-5 w-5 ${d.negative ? "text-muted-foreground" : "text-primary"}`} />
                <span className={`font-semibold ${d.negative ? "text-muted-foreground line-through" : "text-foreground"}`}>
                  {d.label}
                </span>
              </div>
              <p className="text-sm text-muted-foreground">{d.description}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

function StatsBand() {
  const reduced = useReducedMotion();
  return (
    <section className="border-t bg-card/20">
      <div className="mx-auto max-w-6xl px-4 py-16 md:py-20">
        <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
          {stats.map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={reduced ? false : { opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-10%" }}
              transition={{ duration: 0.5, delay: i * 0.08 }}
              className="text-center"
              data-testid={`stat-${stat.label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
            >
              <p className="text-3xl font-bold font-mono text-foreground">
                <NumberTicker value={stat.value} />
                {stat.suffix}
              </p>
              <p className="mt-1 text-sm text-muted-foreground">{stat.label}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ------------------------------ pricing / faq ------------------------------ */

function PricingPreview() {
  const reduced = useReducedMotion();
  return (
    <section className="border-t bg-card/30">
      <div className="mx-auto max-w-6xl px-4 py-20 md:py-24">
        <div className="text-center mb-14">
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-foreground" data-testid="text-pricing-heading">
            Simple, transparent pricing
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-muted-foreground">
            Start with a free 30-day trial of everything — no credit card required. Founding accounts keep their
            complimentary access.
          </p>
        </div>
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4 max-w-6xl mx-auto">
          {pricingTiers.map((tier, i) => (
            <motion.div
              key={tier.name}
              initial={reduced ? false : { opacity: 0, y: 32 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-10%" }}
              transition={{ duration: 0.55, delay: i * 0.08 }}
              whileHover={reduced ? undefined : { y: -6 }}
              className={`relative flex flex-col rounded-xl border bg-card p-6 ${
                tier.highlighted ? "border-primary/60 shadow-xl shadow-primary/10 ring-1 ring-primary/20" : ""
              }`}
              data-testid={`card-pricing-${tier.name.toLowerCase().replace(/\s+/g, "-")}`}
            >
              {tier.highlighted && (
                <Badge className="absolute -top-3 left-1/2 -translate-x-1/2 shadow-md shadow-primary/20" data-testid="badge-popular">
                  Most Popular
                </Badge>
              )}
              <h3 className="text-xl font-semibold text-foreground">{tier.name}</h3>
              <div className="flex items-baseline gap-1 mt-2">
                <span className="text-4xl font-bold text-foreground">{tier.price}</span>
                <span className="text-muted-foreground">{tier.period}</span>
              </div>
              <p className="text-sm text-muted-foreground mt-1">{tier.description}</p>
              <ul className="space-y-2.5 mt-5 mb-6">
                {tier.features.map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Check className="h-4 w-4 text-primary flex-shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
              <Button
                asChild
                className="w-full mt-auto"
                variant={tier.highlighted ? "default" : "outline"}
                data-testid={`button-pricing-${tier.name.toLowerCase().replace(/\s+/g, "-")}`}
              >
                <Link href="/auth?tab=register" onClick={() => trackFunnel("cta_click", { location: `pricing-${tier.name.toLowerCase()}` })}>
                  {tier.cta}
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
            </motion.div>
          ))}
        </div>
        <p className="mt-6 text-center text-xs text-muted-foreground">
          <Link href="/pricing" className="text-primary hover:underline">
            View full pricing details
          </Link>
        </p>
      </div>
    </section>
  );
}

function FAQSection() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  const reduced = useReducedMotion();

  return (
    <section className="border-t">
      <div className="mx-auto max-w-3xl px-4 py-20 md:py-24">
        <div className="text-center mb-14">
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-foreground" data-testid="text-faq-heading">
            Frequently asked questions
          </h2>
          <p className="mx-auto mt-3 max-w-lg text-muted-foreground">Everything you need to know about FounderConsole.</p>
        </div>
        <div className="space-y-3">
          {landingFaqs.map((faq, i) => (
            <div key={i} className="rounded-xl border bg-card/50 overflow-hidden" data-testid={`faq-item-${i}`}>
              <button
                className="flex w-full items-center justify-between p-5 text-left"
                onClick={() => setOpenIndex(openIndex === i ? null : i)}
                data-testid={`button-faq-${i}`}
                aria-expanded={openIndex === i}
              >
                <span className="font-medium text-foreground text-sm">{faq.q}</span>
                <motion.span animate={{ rotate: openIndex === i ? 180 : 0 }} transition={{ duration: reduced ? 0 : 0.25 }}>
                  <ChevronDown className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                </motion.span>
              </button>
              <AnimatePresence initial={false}>
                {openIndex === i && (
                  <motion.div
                    key="content"
                    initial={reduced ? false : { height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={reduced ? undefined : { height: 0, opacity: 0 }}
                    transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
                    className="overflow-hidden"
                  >
                    <div className="px-5 pb-5 text-sm text-muted-foreground leading-relaxed">{faq.a}</div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* --------------------------------- page ---------------------------------- */

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
        description:
          "AI-powered financial intelligence platform for startups. Investor-grade diligence, probabilistic simulation, and ranked decision recommendations.",
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
        description:
          "AI-powered financial intelligence platform for startups with Monte Carlo simulations, fundraising CRM, and 37 data connectors.",
        offers: {
          "@type": "Offer",
          price: "0",
          priceCurrency: "USD",
          description: "Free 30-day trial with full access — no credit card required. Paid plans from $29/month.",
        },
        featureList:
          "Monte Carlo Simulation, AI Copilot, Fundraising CRM, Cap Table Management, 37 Data Connectors, Digital Twin, Strategic Briefings",
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
      <Hero />

      <section className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-10" data-testid="section-logo-cloud">
          <p className="text-center text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-4">
            Connect your financial stack — 37 connectors
          </p>
          <Marquee>
            {integrations.map((name) => (
              <Badge
                key={name}
                variant="secondary"
                className="text-muted-foreground whitespace-nowrap px-4 py-1.5"
                data-testid={`badge-integration-${name.toLowerCase()}`}
              >
                {name}
              </Badge>
            ))}
          </Marquee>
        </div>
      </section>

      <HowItWorks />
      <FeatureDemos />
      <Comparison />
      <StatsBand />
      <PricingPreview />
      <FAQSection />

      <section className="relative border-t overflow-hidden">
        <div className="aurora-hero" style={{ opacity: 0.3 }} aria-hidden />
        <div className="relative mx-auto max-w-6xl px-4 py-20 md:py-28 text-center">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-10%" }}
            transition={{ duration: 0.6 }}
          >
            <Zap className="mx-auto h-8 w-8 text-primary mb-4" />
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-foreground" data-testid="text-cta-heading">
              Run your startup like a simulation
            </h2>
            <p className="mx-auto mt-3 max-w-lg text-muted-foreground">
              Understand your runway. Test decisions before making them. Get AI strategy advice.
            </p>
            <div className="mt-8 flex flex-wrap justify-center gap-4">
              <Magnetic>
                <Button
                  size="lg"
                  className="h-12 px-8 text-base shadow-lg shadow-primary/25 hover:shadow-xl hover:shadow-primary/40 transition-shadow duration-300"
                  asChild
                  data-testid="button-bottom-start-trial"
                >
                  <Link href="/auth?tab=register" onClick={() => trackFunnel("cta_click", { location: "footer-cta" })}>
                    Get Started Free
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
              </Magnetic>
            </div>
            <p className="mt-4 text-xs text-muted-foreground">Free 30-day trial · No credit card required.</p>
          </motion.div>
        </div>
      </section>
    </MarketingLayout>
  );
}
