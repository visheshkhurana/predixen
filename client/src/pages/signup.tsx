import { Link } from "wouter";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { Button } from "@/components/ui/button";
import { useSEO } from "@/lib/seo";
import { ArrowRight } from "lucide-react";

export default function SignupPage() {
  useSEO({
    title: "Get Started — Create a Free FounderConsole Account",
    description:
      "Create a free FounderConsole account to connect live data and run ongoing runway forecasts. Every feature is free during early access — no credit card required. Prefer a quick answer first? Try the free tools with no account.",
    path: "/signup",
    jsonLd: {
      "@context": "https://schema.org",
      "@type": "WebPage",
      name: "Get Started — Create a Free FounderConsole Account",
      description:
        "Create a free FounderConsole account to connect live data and run ongoing runway forecasts. Every feature is free during early access — no credit card required.",
      url: "https://founderconsole.ai/signup",
      isPartOf: { "@type": "WebSite", name: "FounderConsole", url: "https://founderconsole.ai" },
    },
  });

  return (
    <MarketingLayout>
      <article className="mx-auto max-w-3xl px-4 py-16 md:py-20">
        <h1 className="text-3xl font-bold tracking-tight text-foreground md:text-4xl" data-testid="text-signup-title">
          Get started with FounderConsole
        </h1>
        <p className="mt-4 text-lg text-muted-foreground">
          This is the create-account page. Create a free FounderConsole account when you want live connectors and ongoing runway forecasts. During early access every feature is free, and no credit card is required — the same terms already on{" "}
          <Link href="/pricing" className="text-primary hover:underline" data-testid="link-signup-pricing">
            pricing
          </Link>
          .
        </p>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          Create a free account
        </h2>
        <p className="mt-3 text-muted-foreground">
          Sign up to connect your data (or upload a CSV), run Monte Carlo simulations with P10/P50/P90 bands, and ask the copilot against your own numbers. Read the{" "}
          <Link href="/product" className="text-primary hover:underline" data-testid="link-signup-product">
            product
          </Link>{" "}
          overview and the{" "}
          <Link href="/features" className="text-primary hover:underline" data-testid="link-signup-features">
            features
          </Link>{" "}
          catalog if you want more detail first.
        </p>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          Prefer a free tool first
        </h2>
        <p className="mt-3 text-muted-foreground">
          No account required. Try the{" "}
          <Link href="/tools/runway-calculator" className="text-primary hover:underline" data-testid="link-signup-runway">
            startup runway calculator
          </Link>
          , the{" "}
          <Link href="/survival-simulator" className="text-primary hover:underline" data-testid="link-signup-survival">
            startup survival simulator
          </Link>
          , or the{" "}
          <Link href="/default-alive" className="text-primary hover:underline" data-testid="link-signup-default-alive">
            default alive test
          </Link>
          .
        </p>
        <div className="mt-8 flex flex-wrap items-center gap-3">
          <Button asChild data-testid="button-signup-register">
            <Link href="/auth?tab=register">
              Create a free account
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
          <Button asChild variant="outline" data-testid="button-signup-runway">
            <Link href="/tools/runway-calculator">Try the runway calculator</Link>
          </Button>
        </div>
      </article>
    </MarketingLayout>
  );
}
