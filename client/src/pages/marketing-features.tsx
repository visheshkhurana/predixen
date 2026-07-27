import { useEffect, useRef } from "react";
import { Link } from "wouter";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { Button } from "@/components/ui/button";
import { useSEO } from "@/lib/seo";
import { FadeIn, ScrollReveal, StaggerChildren, StaggerItem } from '@/components/ui/motion-primitives';
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import {
  BarChart3,
  Sparkles,
  ShieldCheck,
  DollarSign,
  Plug,
  Brain,
  ArrowRight,
  CheckCircle,
} from "lucide-react";

const features = [
  {
    icon: BarChart3,
    title: "Simulation Engine",
    screenshot: "/images/features/simulation-engine.png",
    headline: "Probability replaces guesswork.",
    description:
      "Run thousands of Monte Carlo simulations to understand the full range of outcomes for your startup. See P10/P50/P90 confidence bands so risk becomes measurable, not hypothetical.",
    bullets: [
      "Monte Carlo P10/P50/P90 confidence bands across all key metrics",
      "Side-by-side scenario comparison with ranked recommendations",
      "Sensitivity analysis reveals which levers move risk the most",
      "24-month forward projections updated as new data flows in",
    ],
  },
  {
    icon: Sparkles,
    title: "AI Copilot",
    screenshot: "/images/features/ai-copilot.png",
    headline: "Defend every decision with data.",
    description:
      "A multi-LLM copilot that routes queries across GPT-4, Claude, and Gemini to deliver the best answer. Perplexity-powered web research adds real-time market benchmarks and competitor context.",
    bullets: [
      "Multi-LLM routing selects the best model for each query type",
      "Perplexity web research surfaces live market data and benchmarks",
      "Context-aware strategic recommendations grounded in your financials",
      "Every answer shows its reasoning, assumptions, and data sources",
    ],
  },
  {
    icon: ShieldCheck,
    title: "Truth Scan",
    screenshot: "/images/features/truth-scan.png",
    headline: "Trust your numbers before sharing them.",
    description:
      "Multi-stage data validation catches errors, inconsistencies, and anomalies before they reach your board deck. Z-score anomaly detection flags outliers automatically so nothing slips through.",
    bullets: [
      "Multi-stage data validation across all connected sources",
      "Z-score anomaly detection surfaces statistical outliers instantly",
      "Confidence scoring quantifies how reliable each metric is",
      "Automated reconciliation between accounting and bank feeds",
    ],
  },
  {
    icon: DollarSign,
    title: "Fundraising OS",
    screenshot: "/images/features/fundraising-os.png",
    headline: "From cap table to term sheet, covered.",
    description:
      "Manage your cap table, model SAFE and convertible note conversions, and understand dilution impact before you sign. Generate investor-ready materials and track your fundraising pipeline in one place.",
    bullets: [
      "Cap table management with real-time ownership visualization",
      "SAFE and convertible note conversion modeling",
      "Dilution modeling shows impact of each fundraising scenario",
      "Investor room with secure document sharing and activity tracking",
    ],
  },
  {
    icon: Plug,
    title: "Data Connectors",
    screenshot: "/images/features/data-connectors.png",
    headline: "Connect everything. Auto-sync.",
    description:
      "37 real OAuth2 integrations with the tools founders already use. QuickBooks, Stripe, Gusto, Mercury, Brex, Plaid, and more. No CSV imports or screen scraping required.",
    bullets: [
      "37 integrations with one-click OAuth connections",
      "QuickBooks, Stripe, Gusto, Mercury, Brex, and Plaid supported",
      "Auto-sync keeps your data fresh without manual intervention",
      "Multi-currency handling across all connected sources",
    ],
  },
  {
    icon: Brain,
    title: "Decision Engine",
    screenshot: "/images/features/decision-engine.png",
    headline: "Strategic clarity, not just charts.",
    description:
      "Transform simulation results into narrative strategic briefings that boards and investors understand. Ranked recommendations with confidence scores explain why one path beats another.",
    bullets: [
      "Narrative strategic briefings written in plain English",
      "Ranked recommendations with GO / CONDITIONAL / NO-GO verdicts",
      "Risk assessment with second-order effects detection",
      "Second-order effect analysis catches downstream surprises early",
    ],
  },
];

gsap.registerPlugin(ScrollTrigger);

export default function MarketingFeaturesPage() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
    if (prefersReducedMotion || !containerRef.current) return;

    const ctx = gsap.context(() => {
      gsap.utils.toArray<HTMLElement>(".feature-image").forEach((img) => {
        gsap.fromTo(img, 
          { y: 30, scale: 0.95 },
          {
            y: -20,
            scale: 1,
            ease: "none",
            scrollTrigger: {
              trigger: img,
              start: "top 85%",
              end: "bottom 15%",
              scrub: 0.8,
            },
          }
        );
      });
    }, containerRef);

    return () => ctx.revert();
  }, []);

  useSEO({
    title: "Features — Simulation, AI Copilot, Fundraising CRM & More | FounderConsole",
    description:
      "Monte Carlo simulation engine, multi-LLM AI copilot, Truth Scan data validation, Fundraising OS with CRM, 37 data connectors, and AI strategic briefings — built for startup founders.",
    path: "/features",
    jsonLd: {
      "@context": "https://schema.org",
      "@type": "WebPage",
      name: "FounderConsole Features",
      description: "Complete feature overview of FounderConsole: Monte Carlo simulations, AI copilot, data validation, fundraising tools, and 37 data connectors.",
      url: "https://founderconsole.ai/features",
      isPartOf: {
        "@type": "WebSite",
        name: "FounderConsole",
        url: "https://founderconsole.ai",
      },
    },
  });

  return (
    <MarketingLayout>
      <div ref={containerRef}>
      <FadeIn delay={0.05} duration={0.5}>
      <section>
        <div className="mx-auto max-w-6xl px-4 py-16 md:py-20">
          <h1 className="text-3xl font-bold tracking-tight text-foreground md:text-4xl" data-testid="text-features-title">
            Every tool founders need to survive and scale
          </h1>
          <p className="mt-3 max-w-2xl text-lg text-muted-foreground" data-testid="text-features-subtitle">
            From Monte Carlo simulations to AI-powered strategic briefings — know your runway, your risks, and your next move.
          </p>
        </div>
      </section>
      </FadeIn>

      <section className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-10">
          <div className="space-y-16">
            {features.map((f, i) => (
              <ScrollReveal key={f.title} delay={0.05}>
              <div
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
                  <img
                    src={f.screenshot}
                    alt={`${f.title} — ${f.headline}`}
                    className="feature-image rounded-xl border shadow-lg w-full object-cover"
                    loading="lazy"
                    data-testid={`img-feature-${f.title.toLowerCase().replace(/\s+/g, "-")}`}
                  />
                </div>
              </div>
              </ScrollReveal>
            ))}
          </div>
        </div>
      </section>

      <ScrollReveal delay={0.1}>
      <section className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-16 md:py-20 text-center">
          <h2 className="text-2xl font-semibold text-foreground" data-testid="text-features-cta">
            Start using FounderConsole today
          </h2>
          <p className="mx-auto mt-2 max-w-lg text-muted-foreground">
            Every feature is free while we're in early access — no credit card required. Connect your data and get your first forecast in under 5 minutes.
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
      </ScrollReveal>
      </div>
    </MarketingLayout>
  );
}
