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

const tiers = [
  {
    name: "Free Beta",
    price: "$0",
    period: "",
    bullet: "Best for founders who want immediate insight.",
    features: [
      "Connect key integrations",
      "Baseline forecast",
      "One scenario simulation",
      "AI explanation summary",
      "Unlimited scenarios during beta",
      "Data connectors & integrations",
      "Team collaboration",
      "Priority support",
    ],
    highlighted: true,
  },
  {
    name: "Startup",
    price: "$49",
    period: "/month",
    bullet: "Best for teams who make weekly decisions.",
    features: [
      "All free beta features",
      "Unlimited scenarios",
      "Investor report templates",
      "Priority support",
      "Email briefings",
      "Saved scenarios & exports",
    ],
    highlighted: false,
  },
  {
    name: "Growth",
    price: "$129",
    period: "/month",
    bullet: "Best for revenue-finance collaboration.",
    features: [
      "All startup features",
      "Advanced scenario compare",
      "Team access controls",
      "Custom reporting",
      "Dedicated support",
      "API access",
    ],
    highlighted: false,
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
    description: "FounderConsole pricing tiers with fast time-to-value. All features free during public beta. No credit card required.",
    path: "/pricing",
    jsonLd: {
      "@context": "https://schema.org",
      "@type": "SoftwareApplication",
      name: "FounderConsole",
      applicationCategory: "BusinessApplication",
      operatingSystem: "Web",
      offers: [
        {
          "@type": "Offer",
          name: "Free Beta",
          price: "0",
          priceCurrency: "USD",
          description: "All features free during public beta. No credit card required.",
        },
        {
          "@type": "Offer",
          name: "Startup",
          price: "49",
          priceCurrency: "USD",
          billingIncrement: "month",
          description: "Full platform access for growing startups.",
        },
        {
          "@type": "Offer",
          name: "Growth",
          price: "129",
          priceCurrency: "USD",
          billingIncrement: "month",
          description: "Advanced features for scaling companies.",
        },
      ],
    },
  });

  return (
    <MarketingLayout>
      <div ref={containerRef}>
      <FadeIn delay={0.05} duration={0.5}>
      <section>
        <div className="mx-auto max-w-6xl px-4 py-16 md:py-20 text-center">
          <Badge className="mb-4 bg-emerald-500/10 text-emerald-500 border-emerald-500/20 hover:bg-emerald-500/10" data-testid="badge-free-beta">
            Free During Public Beta
          </Badge>
          <h1 className="text-3xl font-bold tracking-tight text-foreground md:text-4xl" data-testid="text-pricing-title">
            Choose the plan that matches how often you make hard decisions
          </h1>
          <p className="mt-3 max-w-xl mx-auto text-lg text-muted-foreground" data-testid="text-pricing-subtitle">
            All features are unlocked during our public beta. Sign up and start making smarter financial decisions today.
          </p>
        </div>
      </section>
      </FadeIn>

      <ScrollReveal>
      <section className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-10">
          <StaggerChildren className="grid gap-6 md:grid-cols-3" staggerDelay={0.1}>
            {tiers.map((tier) => (
              <StaggerItem key={tier.name}>
              <Card
                className={`flex flex-col h-full ${tier.highlighted ? "border-primary" : ""}`}
                data-testid={`card-tier-${tier.name.toLowerCase().replace(/\s+/g, "-")}`}
              >
                <CardHeader>
                  <div className="flex items-center justify-between gap-2">
                    <CardTitle className="text-lg">{tier.name}</CardTitle>
                    {tier.highlighted && (
                      <Badge variant="secondary" className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20">
                        Free Now
                      </Badge>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground">{tier.bullet}</p>
                </CardHeader>

                <CardContent className="flex-1">
                  <div className="mb-6">
                    <span className="text-3xl font-bold text-foreground">{tier.price}</span>
                    {tier.period && <span className="text-sm text-muted-foreground ml-1">{tier.period}</span>}
                    {!tier.period && <span className="text-sm text-muted-foreground ml-1">during beta</span>}
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
                    onClick={() => navigate("/auth")}
                    data-testid={`button-cta-${tier.name.toLowerCase().replace(/\s+/g, "-")}`}
                  >
                    {tier.highlighted ? "Get Started Free" : "Coming Soon"}
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
                  <Link href="/demo">Watch Demo</Link>
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
            All features include SSL encryption, daily backups, and 99.9% uptime SLA. Free during beta — no credit card required.
          </p>
        </div>
      </section>
      </div>
    </MarketingLayout>
  );
}
