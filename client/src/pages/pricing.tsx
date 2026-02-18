import { useState } from "react";
import { useLocation } from "wouter";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Check, Sparkles, ArrowRight } from "lucide-react";

const tiers = [
  {
    name: "Starter",
    price: { monthly: 0, annual: 0 },
    description: "For early-stage founders exploring their first scenarios.",
    features: [
      "1 company",
      "Manual data input",
      "Basic scenarios (3 max)",
      "Community support",
    ],
    cta: "Get Started",
    ctaVariant: "outline" as const,
    highlighted: false,
  },
  {
    name: "Pro",
    price: { monthly: 49, annual: 39 },
    description: "For growth-stage teams running serious financial simulations.",
    features: [
      "Unlimited companies",
      "CSV + API data import",
      "Unlimited scenarios & simulations",
      "AI Copilot with 500 queries/mo",
      "Truth Scan validation",
      "Priority email support",
    ],
    cta: "Start Free Trial",
    ctaVariant: "default" as const,
    highlighted: true,
  },
  {
    name: "Enterprise",
    price: { monthly: -1, annual: -1 },
    description: "For organizations needing custom integrations and compliance.",
    features: [
      "Everything in Pro",
      "Custom data connectors",
      "RBAC & team management",
      "Dedicated CSM",
      "SLA & audit logs",
      "White-label options",
    ],
    cta: "Contact Sales",
    ctaVariant: "outline" as const,
    highlighted: false,
  },
];

export default function PricingPage() {
  const [isAnnual, setIsAnnual] = useState(false);
  const [, navigate] = useLocation();

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between gap-4 flex-wrap">
          <button
            type="button"
            className="flex items-center gap-2 cursor-pointer bg-transparent border-0 p-0"
            onClick={() => navigate("/")}
            data-testid="link-home"
          >
            <div className="h-8 w-8 rounded-md bg-primary/20 flex items-center justify-center">
              <Sparkles className="h-4 w-4 text-primary" />
            </div>
            <span className="text-lg font-bold" data-testid="text-brand">FounderConsole</span>
          </button>
          <div className="flex items-center gap-2 flex-wrap">
            <Button variant="ghost" onClick={() => navigate("/auth")} data-testid="button-login">
              Sign In
            </Button>
            <Button onClick={() => navigate("/auth")} data-testid="button-signup">
              Get Started
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-16">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold mb-3" data-testid="text-pricing-title">
            Simple, transparent pricing
          </h1>
          <p className="text-lg text-muted-foreground max-w-xl mx-auto" data-testid="text-pricing-subtitle">
            Start free and scale as your decision-making needs grow. No hidden fees.
          </p>

          <div className="flex items-center justify-center gap-3 mt-8" data-testid="toggle-billing-period">
            <span className={`text-sm font-medium ${!isAnnual ? "text-foreground" : "text-muted-foreground"}`}>
              Monthly
            </span>
            <button
              type="button"
              role="switch"
              aria-checked={isAnnual}
              onClick={() => setIsAnnual(!isAnnual)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                isAnnual ? "bg-primary" : "bg-muted"
              }`}
              data-testid="switch-billing-period"
            >
              <span
                className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${
                  isAnnual ? "translate-x-6" : "translate-x-1"
                }`}
              />
            </button>
            <span className={`text-sm font-medium ${isAnnual ? "text-foreground" : "text-muted-foreground"}`}>
              Annual
            </span>
            {isAnnual && (
              <Badge variant="secondary" className="text-xs" data-testid="badge-annual-savings">
                Save 20%
              </Badge>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {tiers.map((tier) => {
            const price = isAnnual ? tier.price.annual : tier.price.monthly;
            const isCustom = price < 0;

            return (
              <Card
                key={tier.name}
                className={`hover-elevate flex flex-col ${
                  tier.highlighted ? "border-primary" : ""
                }`}
                data-testid={`card-tier-${tier.name.toLowerCase()}`}
              >
                <CardHeader className="gap-2">
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <CardTitle className="text-xl">{tier.name}</CardTitle>
                    {tier.highlighted && (
                      <Badge variant="secondary" data-testid="badge-recommended">
                        Recommended
                      </Badge>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground">{tier.description}</p>
                </CardHeader>

                <CardContent className="flex-1">
                  <div className="mb-6" data-testid={`text-price-${tier.name.toLowerCase()}`}>
                    {isCustom ? (
                      <span className="text-3xl font-bold">Custom</span>
                    ) : price === 0 ? (
                      <span className="text-3xl font-bold">Free</span>
                    ) : (
                      <div className="flex items-baseline gap-1">
                        <span className="text-3xl font-bold">${price}</span>
                        <span className="text-sm text-muted-foreground">/mo</span>
                      </div>
                    )}
                    {isAnnual && !isCustom && price > 0 && (
                      <p className="text-xs text-muted-foreground mt-1">
                        Billed annually at ${price * 12}/yr
                      </p>
                    )}
                  </div>

                  <ul className="space-y-3">
                    {tier.features.map((feature) => (
                      <li key={feature} className="flex items-start gap-2 text-sm">
                        <Check className="h-4 w-4 text-primary mt-0.5 shrink-0" />
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>

                <CardFooter>
                  <Button
                    variant={tier.ctaVariant}
                    className="w-full gap-2"
                    onClick={() => navigate("/auth")}
                    data-testid={`button-cta-${tier.name.toLowerCase()}`}
                  >
                    {tier.cta}
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </CardFooter>
              </Card>
            );
          })}
        </div>

        <div className="text-center mt-16">
          <p className="text-sm text-muted-foreground" data-testid="text-pricing-footer">
            All plans include SSL encryption, daily backups, and 99.9% uptime SLA.
          </p>
        </div>
      </main>
    </div>
  );
}
