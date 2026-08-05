import { Link } from "wouter";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useSEO } from "@/lib/seo";
import { ArrowRight, Check, Sparkles, Brain, Gauge, ShieldCheck } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";
import { Magnetic } from "@/components/marketing/redesign/Tilt3D";
import { TwinDashboardDemo } from "@/components/marketing/redesign/TwinDashboardDemo";
import { CopilotDemo } from "@/components/marketing/redesign/CopilotDemo";
import { trackFunnel } from "@/lib/funnel";

/**
 * Message-matched landing page for the "AI CFO" search ad group.
 * Same components as the main landing page, headline swapped to mirror
 * the query the visitor just typed.
 */

const capabilities = [
  { icon: Gauge, title: "Runway & burn, live", description: "Connects Stripe, QuickBooks and your bank. Your true runway, always current — no spreadsheet updates." },
  { icon: Brain, title: "Answers like a CFO", description: "Ask in plain English: \"Can we afford two engineers?\" Get board-ready answers backed by 10,000 simulations." },
  { icon: Sparkles, title: "Decisions, stress-tested", description: "Hiring, pricing, fundraise timing — simulated across thousands of futures before you commit." },
  { icon: ShieldCheck, title: "A fraction of the cost", description: "Fractional CFOs run $3–10k/month. FounderConsole starts free, then from $29/month." },
];

const bullets = [
  "Free 30-day trial — no credit card required",
  "Set up in under 5 minutes",
  "37 data connectors incl. Stripe, QuickBooks, Mercury",
  "Monte Carlo P10/P50/P90 runway bands",
];

export default function AiCfoPage() {
  const reduced = useReducedMotion();

  useSEO({
    title: "AI CFO for Startups — FounderConsole",
    description:
      "FounderConsole is the AI CFO for startup founders: live runway and burn tracking, Monte Carlo forecasting, and plain-English financial answers. Free 30-day trial, no credit card.",
    path: "/ai-cfo",
    jsonLd: [
      {
        "@context": "https://schema.org",
        "@type": "Product",
        name: "FounderConsole — AI CFO",
        description: "AI CFO for startups: runway tracking, Monte Carlo simulation, and strategic financial answers.",
        offers: {
          "@type": "Offer",
          price: "0",
          priceCurrency: "USD",
          description: "Free 30-day trial with full access — no credit card required. Paid plans from $29/month.",
        },
      },
    ],
  });

  const cta = (location: string) => () => trackFunnel("cta_click", { location });

  return (
    <MarketingLayout>
      {/* hero */}
      <section className="relative overflow-hidden aurora-hero">
        <div className="mx-auto max-w-6xl px-4 pt-20 pb-16 text-center md:pt-28">
          <motion.div
            initial={reduced ? false : { opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <Badge variant="secondary" className="mb-6" data-testid="badge-aicfo-eyebrow">
              <Sparkles className="mr-1.5 h-3 w-3" />
              Your finance co-pilot, on demand
            </Badge>
          </motion.div>
          <motion.h1
            className="text-4xl font-bold tracking-tight md:text-6xl leading-[1.08]"
            initial={reduced ? false : { opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            data-testid="text-aicfo-title"
          >
            The AI CFO{" "}
            <span className="bg-gradient-to-r from-primary via-violet-500 to-primary bg-[length:200%_auto] bg-clip-text text-transparent animate-[shimmer_3s_linear_infinite]">
              for Startups
            </span>
          </motion.h1>
          <motion.p
            className="mx-auto mt-6 max-w-2xl text-base text-muted-foreground md:text-lg"
            initial={reduced ? false : { opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.25 }}
          >
            Know your runway, simulate every big decision, and get CFO-grade answers
            in plain English — without paying CFO-grade salaries.
          </motion.p>
          <motion.div
            className="mt-9 flex flex-wrap justify-center gap-4"
            initial={reduced ? false : { opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
          >
            <Magnetic>
              <Button size="lg" className="h-12 px-8 text-base shadow-lg shadow-primary/25" asChild data-testid="button-aicfo-hero-cta">
                <Link href="/auth?tab=register" onClick={cta("aicfo-hero")}>
                  Start Free Trial
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
            </Magnetic>
            <Button size="lg" variant="outline" className="h-12 px-8 text-base backdrop-blur" asChild data-testid="button-aicfo-demo">
              <Link href="/demo">Watch Demo</Link>
            </Button>
          </motion.div>
          <p className="mt-4 text-xs text-muted-foreground">Free 30-day trial · No credit card required</p>
        </div>
      </section>

      {/* live demo */}
      <section className="mx-auto max-w-5xl px-4 pb-8">
        <TwinDashboardDemo />
      </section>

      {/* capabilities */}
      <section className="mx-auto max-w-6xl px-4 py-16">
        <h2 className="text-center text-2xl font-bold tracking-tight md:text-4xl" data-testid="text-aicfo-capabilities-title">
          Everything a CFO does. Minus the retainer.
        </h2>
        <div className="mt-10 grid gap-6 sm:grid-cols-2">
          {capabilities.map((c, i) => (
            <motion.div
              key={c.title}
              className="rounded-2xl border bg-card/60 p-6"
              initial={reduced ? false : { opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-10%" }}
              transition={{ duration: 0.5, delay: i * 0.08 }}
            >
              <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <c.icon className="h-5 w-5 text-primary" />
              </div>
              <h3 className="font-semibold">{c.title}</h3>
              <p className="mt-1.5 text-sm text-muted-foreground leading-relaxed">{c.description}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* copilot demo */}
      <section className="mx-auto max-w-5xl px-4 pb-4">
        <h2 className="mb-6 text-center text-2xl font-bold tracking-tight md:text-3xl">
          Ask it what you'd ask a CFO
        </h2>
        <CopilotDemo />
      </section>

      {/* final CTA */}
      <section className="mx-auto max-w-3xl px-4 py-16 text-center">
        <h2 className="text-2xl font-bold tracking-tight md:text-4xl">Hire your AI CFO today</h2>
        <ul className="mx-auto mt-6 inline-flex flex-col items-start gap-2 text-left">
          {bullets.map((b) => (
            <li key={b} className="flex items-center gap-2 text-sm text-muted-foreground">
              <Check className="h-4 w-4 shrink-0 text-emerald-500" />
              {b}
            </li>
          ))}
        </ul>
        <div className="mt-8">
          <Magnetic>
            <Button size="lg" className="h-12 px-8 text-base shadow-lg shadow-primary/25" asChild data-testid="button-aicfo-final-cta">
              <Link href="/auth?tab=register" onClick={cta("aicfo-final")}>
                Start Free Trial
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </Magnetic>
        </div>
      </section>
    </MarketingLayout>
  );
}
