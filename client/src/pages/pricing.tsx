import { useState } from "react";
import { useLocation } from "wouter";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Check, Sparkles, ArrowRight, Loader2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";

const tiers = [
  {
    name: "Beta",
    price: { monthly: 0, annual: 0 },
    description: "All features unlocked free during public beta.",
    features: [
      "Unlimited scenarios & simulations",
      "AI Decision Copilot",
      "Saved scenarios & exports",
      "Email briefings",
      "Data connectors & integrations",
      "Team collaboration",
      "Priority support",
    ],
    cta: "Get Started Free",
    ctaVariant: "default" as const,
    highlighted: true,
  },
];

export default function PricingPage() {
  const [isAnnual, setIsAnnual] = useState(false);
  const [, navigate] = useLocation();
  const { toast } = useToast();
  const [betaOpen, setBetaOpen] = useState(false);
  const [betaPlan, setBetaPlan] = useState("");
  const [betaEmail, setBetaEmail] = useState("");
  const [betaCompany, setBetaCompany] = useState("");
  const [betaSubmitting, setBetaSubmitting] = useState(false);

  const handleTierClick = () => {
    navigate("/auth");
  };

  const handleBetaSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!betaEmail) return;
    setBetaSubmitting(true);
    try {
      await apiRequest("POST", "/api/leads", {
        email: betaEmail,
        company: betaCompany,
        plan: betaPlan,
      });
      toast({ title: "You're on the list!", description: `We'll reach out when ${betaPlan} is available.` });
      setBetaOpen(false);
      setBetaEmail("");
      setBetaCompany("");
    } catch {
      toast({ title: "Something went wrong", description: "Please try again.", variant: "destructive" });
    } finally {
      setBetaSubmitting(false);
    }
  };

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
          <Badge className="mb-4 bg-emerald-500/10 text-emerald-500 border-emerald-500/20 hover:bg-emerald-500/10" data-testid="badge-free-beta">
            Free During Public Beta
          </Badge>
          <h1 className="text-4xl font-bold mb-3" data-testid="text-pricing-title">
            Everything free, no credit card required
          </h1>
          <p className="text-lg text-muted-foreground max-w-xl mx-auto" data-testid="text-pricing-subtitle">
            All features are unlocked during our public beta. Sign up and start making smarter financial decisions today.
          </p>
        </div>

        <div className="grid grid-cols-1 max-w-md mx-auto gap-6">
          {tiers.map((tier) => {
            const price = isAnnual ? tier.price.annual : tier.price.monthly;

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
                    <Badge variant="secondary" className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20" data-testid="badge-free">
                      Free
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">{tier.description}</p>
                </CardHeader>

                <CardContent className="flex-1">
                  <div className="mb-6" data-testid={`text-price-${tier.name.toLowerCase()}`}>
                    <span className="text-3xl font-bold">$0</span>
                    <span className="text-sm text-muted-foreground ml-1">during beta</span>
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
                    onClick={() => handleTierClick()}
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

        <div className="text-center mt-10">
          <button
            type="button"
            className="text-sm text-primary hover:underline"
            onClick={() => navigate("/demo")}
            data-testid="link-start-demo"
          >
            Start with Demo &rarr;
          </button>
        </div>

        <div className="text-center mt-16">
          <p className="text-sm text-muted-foreground" data-testid="text-pricing-footer">
            All features include SSL encryption, daily backups, and 99.9% uptime SLA. Free during beta — no credit card required.
          </p>
        </div>
      </main>

      <Dialog open={betaOpen} onOpenChange={setBetaOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Request Beta Access</DialogTitle>
            <DialogDescription>
              Enter your details and we'll notify you when the {betaPlan} plan is available.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleBetaSubmit} className="space-y-4 mt-2">
            <div className="space-y-2">
              <Label htmlFor="beta-email">Email</Label>
              <Input
                id="beta-email"
                type="email"
                required
                placeholder="you@company.com"
                value={betaEmail}
                onChange={(e) => setBetaEmail(e.target.value)}
                data-testid="input-beta-email"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="beta-company">Company name</Label>
              <Input
                id="beta-company"
                placeholder="Acme Inc."
                value={betaCompany}
                onChange={(e) => setBetaCompany(e.target.value)}
                data-testid="input-beta-company"
              />
            </div>
            <Button type="submit" className="w-full gap-2" disabled={betaSubmitting} data-testid="button-beta-submit">
              {betaSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Submitting...
                </>
              ) : (
                "Request Access"
              )}
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
