import { useEffect, useRef } from "react";
import { Link, useLocation } from "wouter";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Check, ArrowRight, CheckCircle } from "lucide-react";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { useSEO } from "@/lib/seo";
import { FadeIn, ScrollReveal, StaggerChildren, StaggerItem } from '@/components/ui/motion-primitives';
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

// FounderConsole is free. One plan, every feature, no limits, no card.
const tiers = [
  {
    name: "Free",
    price: "$0",
    period: "",
    bullet: "All features, no credit card.",
    features: [
      "Every feature unlocked",
      "Unlimited companies",
      "Unlimited simulations & copilot",
      "All data connectors",
      "Truth Scan, stress tests & benchmarks",
      "Fundraising OS, cap table & investor room",
      "Document generator & AI graphics",
      "Board deck & PDF export",
    ],
    highlighted: true,
    cta: "Get Started Free",
  },
];

gsap.registerPlugin(ScrollTrigger);

export default function PricingPage() {
  const [, navigate] = useLocation();
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
    if (prefersReducedMotion || !containerRef.current) return;

    const ctx = gsap.context(() => {
      gsap.utils.toArray<HTMLElement>(".pricing-benefit-card").forEach((card) => {
        gsap.fromTo(card,
          { y: 20, opacity: 0.85 },
          {
            y: 0,
            opacity: 1,
            ease: "none",
            scrollTrigger: {
              trigger: card,
              start: "top 90%",
              end: "top 55%",
              scrub: 0.6,
            },
          }
        );
      });
    }, containerRef);

    return () => ctx.revert();
  }, []);

  useSEO({
    title: "Pricing | FounderConsole",
    description: "FounderConsole is free — every feature unlocked, unlimited companies, simulations and copilot, no credit card required.",
    path: "/pricing",
    jsonLd: {
      "@context": "https://schema.org",
      "@type": "SoftwareApplication",
      name: "FounderConsole",
      applicationCategory: "BusinessApplication",
      operatingSystem: "Web",
      offers: {
        "@type": "Offer",
        name: "Free",
        price: "0",
        priceCurrency: "USD",
        description: "Free — all features, no credit card.",
      },
    },
  });

  return (
    <MarketingLayout>
      <div ref={containerRef}>
      <FadeIn delay={0.05} duration={0.5}>
      <section>
        <div className="mx-auto max-w-6xl px-4 py-16 md:py-20 text-center">
          <Badge className="mb-4 bg-emerald-500/10 text-emerald-500 border-emerald-500/20 hover:bg-emerald-500/10" data-testid="badge-free">
            Free — No Credit Card
          </Badge>
          <h1 className="text-3xl font-bold tracking-tight text-foreground md:text-4xl" data-testid="text-pricing-title">
            FounderConsole is free
          </h1>
          <p className="mt-3 max-w-xl mx-auto text-lg text-muted-foreground" data-testid="text-pricing-subtitle">
            One plan: Free — all features, no credit card. No trials, no tiers, no usage caps.
          </p>
        </div>
      </section>
      </FadeIn>

      <ScrollReveal>
      <section className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-10">
          <StaggerChildren className="mx-auto grid max-w-md gap-6" staggerDelay={0.1}>
            {tiers.map((tier) => (
              <StaggerItem key={tier.name}>
              <Card
                className={`flex flex-col h-full ${tier.highlighted ? "border-primary" : ""}`}
                data-testid={`card-tier-${tier.name.toLowerCase().replace(/\s+/g, "-")}`}
              >
                <CardHeader>
                  <div className="flex items-center justify-between gap-2">
                    <CardTitle className="text-lg">{tier.name}</CardTitle>
                  </div>
                  <p className="text-sm text-muted-foreground">{tier.bullet}</p>
                </CardHeader>

                <CardContent className="flex-1">
                  <div className="mb-6">
                    <span className="text-3xl font-bold text-foreground">{tier.price}</span>
                    {tier.period && <span className="text-sm text-muted-foreground ml-1">{tier.period}</span>}
                    {!tier.period && <span className="text-sm text-muted-foreground ml-1">forever</span>}
                  </div>

                  <ul className="space-y-3">
                    {tier.features.map((feature) => (
                      <li key={feature} className="flex items-start gap-2 text-sm">
                        <Check className="h-4 w-4 text-primary mt-0.5 shrink-0" />
                        <span className="text-muted-foreground">{feature}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>

                <CardFooter>
                  <Button
                    variant={tier.highlighted ? "default" : "outline"}
                    className="w-full gap-2"
                    onClick={() => navigate("/signup")}
                    data-testid={`button-cta-${tier.name.toLowerCase().replace(/\s+/g, "-")}`}
                  >
                    {tier.cta}
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </CardFooter>
              </Card>
              </StaggerItem>
            ))}
          </StaggerChildren>
        </div>
      </section>
      </ScrollReveal>

      <ScrollReveal delay={0.1}>
      <section className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-16">
          <h2 className="text-2xl font-semibold tracking-tight text-foreground" data-testid="text-5min-heading">
            What you get in 5 minutes
          </h2>
          <p className="mt-2 text-muted-foreground">Designed to reduce risk, not add complexity.</p>
          <div className="mt-8 grid gap-6 md:grid-cols-2">
            <div className="pricing-benefit-card rounded-xl border bg-card/50 p-6">
              <h3 className="text-base font-semibold text-foreground">Immediate deliverables</h3>
              <ul className="mt-4 space-y-3 text-sm text-muted-foreground">
                {[
                  "Baseline forecast from connected sources",
                  "Confidence interval simulation band",
                  "AI narrative summarizing key risk drivers",
                  "Investor-ready summary draft",
                ].map((x) => (
                  <li key={x} className="flex gap-2">
                    <CheckCircle className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                    <span>{x}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="pricing-benefit-card rounded-xl border bg-card/50 p-6">
              <h3 className="text-base font-semibold text-foreground">What this does for founders</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                Founders can't waste hours building spreadsheets and making decisions off a single outcome. The value is turning uncertainty into an explainable, defensible decision language that investors and boards respect.
              </p>
              <div className="mt-6">
                <Button variant="outline" size="sm" asChild data-testid="button-pricing-demo">
                  <Link href="/demo/enter">Live Demo</Link>
                </Button>
              </div>
            </div>
          </div>
        </div>
      </section>
      </ScrollReveal>

      <section className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-10 text-center">
          <p className="text-sm text-muted-foreground" data-testid="text-pricing-footer">
            Includes SSL encryption, daily backups, and reliable cloud hosting. Free — all features, no credit card.
          </p>
        </div>
      </section>
      </div>
    </MarketingLayout>
  );
}
