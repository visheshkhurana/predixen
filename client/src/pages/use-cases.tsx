import { Link } from "wouter";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { Button } from "@/components/ui/button";
import { useSEO } from "@/lib/seo";
import { ArrowRight } from "lucide-react";

export default function UseCasesPage() {
  useSEO({
    title: "Use Cases — Runway, Hiring, Fundraising, and Board Readiness | FounderConsole",
    description:
      "How founders use FounderConsole: runway planning, hiring and fundraising scenario simulation, board and investor readiness, and default-alive checks. No invented case studies — evaluate with the product and free tools.",
    path: "/use-cases",
    jsonLd: {
      "@context": "https://schema.org",
      "@type": "WebPage",
      name: "Use Cases — Runway, Hiring, Fundraising, and Board Readiness | FounderConsole",
      description:
        "How founders use FounderConsole: runway planning, hiring and fundraising scenario simulation, board and investor readiness, and default-alive checks. No invented case studies.",
      url: "https://founderconsole.ai/use-cases",
      isPartOf: { "@type": "WebSite", name: "FounderConsole", url: "https://founderconsole.ai" },
    },
  });

  return (
    <MarketingLayout>
      <article className="mx-auto max-w-3xl px-4 py-16 md:py-20">
        <h1 className="text-3xl font-bold tracking-tight text-foreground md:text-4xl" data-testid="text-use-cases-title">
          FounderConsole use cases — runway, hiring, fundraising, and board readiness
        </h1>
        <p className="mt-4 text-lg text-muted-foreground">
          This page maps FounderConsole to founder jobs the product already covers: runway planning, hiring and fundraising scenario simulation, board and investor readiness, and default-alive checks. It is not a case-study wall — we have not published customer stories or outcome metrics, and this page does not invent them.
        </p>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          Runway planning
        </h2>
        <p className="mt-3 text-muted-foreground">
          Founders need a range they can defend, not a single spreadsheet cash-out date. FounderConsole runs Monte Carlo simulations with P10/P50/P90 bands so runway is a distribution. Start without an account on the{" "}
          <Link href="/tools/runway-calculator" className="text-primary hover:underline" data-testid="link-use-cases-runway">
            startup runway calculator
          </Link>
          , or use the{" "}
          <Link href="/runway/saas" className="text-primary hover:underline" data-testid="link-use-cases-saas">
            SaaS runway calculator
          </Link>{" "}
          when you want industry-tuned starting inputs.
        </p>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          Hiring and fundraising scenario simulation
        </h2>
        <p className="mt-3 text-muted-foreground">
          The simulation engine is built to test decisions before you commit: hiring plans, fundraising timing, and growth assumptions. Connect data (or upload a CSV) and compare scenarios side by side instead of rewriting a model for each what-if. The deeper catalog is on{" "}
          <Link href="/features" className="text-primary hover:underline" data-testid="link-use-cases-features">
            features
          </Link>
          ; the product overview is on{" "}
          <Link href="/product" className="text-primary hover:underline" data-testid="link-use-cases-product">
            product
          </Link>
          .
        </p>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          Board and investor readiness
        </h2>
        <p className="mt-3 text-muted-foreground">
          When the question is what to show a board or an investor, FounderConsole turns simulation results into narrative briefings and investor-ready materials — Fundraising OS covers cap table, dilution modeling, and related reports. Truth Scan exists so numbers are validated before they land in a deck. None of that is a published customer result; it is what the product ships.
        </p>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          Default-alive checks
        </h2>
        <p className="mt-3 text-muted-foreground">
          Paul Graham's default-alive test asks whether you reach profitability on the money you already have. Run it with no account on the{" "}
          <Link href="/default-alive" className="text-primary hover:underline" data-testid="link-use-cases-default-alive">
            default alive test
          </Link>
          . For a probabilistic survival view, use the{" "}
          <Link href="/survival-simulator" className="text-primary hover:underline" data-testid="link-use-cases-survival">
            startup survival simulator
          </Link>{" "}
          (1,000 Monte Carlo runs).
        </p>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          Evaluate the product, not unnamed stories
        </h2>
        <p className="mt-3 text-muted-foreground">
          Read the{" "}
          <Link href="/product" className="text-primary hover:underline" data-testid="link-use-cases-product-eval">
            product
          </Link>{" "}
          overview, the{" "}
          <Link href="/features" className="text-primary hover:underline" data-testid="link-use-cases-features-eval">
            features
          </Link>{" "}
          catalog, and{" "}
          <Link href="/pricing" className="text-primary hover:underline" data-testid="link-use-cases-pricing">
            pricing
          </Link>{" "}
          (every feature is free during early access).
        </p>
        <div className="mt-8">
          <Button asChild data-testid="button-use-cases-auth">
            <Link href="/auth">
              Get started free
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </div>
      </article>
    </MarketingLayout>
  );
}
