import { Link } from "wouter";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { Button } from "@/components/ui/button";
import { useSEO } from "@/lib/seo";
import { ArrowRight } from "lucide-react";

export default function HowItWorksPage() {
  useSEO({
    title: "How FounderConsole Works — Connect, Validate, Simulate, Decide",
    description:
      "How FounderConsole works: connect or upload data, Truth Scan validation, Monte Carlo P10/P50/P90 simulation, AI copilot decisions, and fundraising tools. A capability walkthrough — no invented timings or case studies.",
    path: "/how-it-works",
    jsonLd: {
      "@context": "https://schema.org",
      "@type": "WebPage",
      name: "How FounderConsole Works — Connect, Validate, Simulate, Decide",
      description:
        "How FounderConsole works: connect or upload data, Truth Scan validation, Monte Carlo P10/P50/P90 simulation, AI copilot decisions, and fundraising tools.",
      url: "https://founderconsole.ai/how-it-works",
      isPartOf: { "@type": "WebSite", name: "FounderConsole", url: "https://founderconsole.ai" },
    },
  });

  return (
    <MarketingLayout>
      <article className="mx-auto max-w-3xl px-4 py-16 md:py-20">
        <h1 className="text-3xl font-bold tracking-tight text-foreground md:text-4xl" data-testid="text-how-it-works-title">
          How FounderConsole works
        </h1>
        <p className="mt-4 text-lg text-muted-foreground">
          FounderConsole turns connected financial data into a range you can defend. This page walks through the product in the order it actually runs: connect or upload data, validate with Truth Scan, simulate with Monte Carlo P10/P50/P90, ask the AI copilot, then use fundraising tools. It is a capability walkthrough — not a timeline, a success rate, or a customer story.
        </p>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          1. Connect or upload data
        </h2>
        <p className="mt-3 text-muted-foreground">
          Link the tools founders already use, or upload a CSV. FounderConsole has 37 data connectors, including QuickBooks, Stripe, Gusto, Mercury, Brex, and Plaid. You can also start without connecting anything: try the{" "}
          <Link href="/tools/runway-calculator" className="text-primary hover:underline" data-testid="link-hiw-runway">
            startup runway calculator
          </Link>
          , the{" "}
          <Link href="/survival-simulator" className="text-primary hover:underline" data-testid="link-hiw-survival">
            startup survival simulator
          </Link>
          , or the{" "}
          <Link href="/default-alive" className="text-primary hover:underline" data-testid="link-hiw-default-alive">
            default alive test
          </Link>{" "}
          with no account.
        </p>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          2. Truth Scan validation
        </h2>
        <p className="mt-3 text-muted-foreground">
          Truth Scan is multi-stage data validation. It catches errors, inconsistencies, and anomalies before numbers reach a board deck. Z-score anomaly detection flags outliers, and confidence scoring quantifies how reliable each metric is. Automated reconciliation between accounting and bank feeds is part of the same validation path.
        </p>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          3. Monte Carlo simulation (P10/P50/P90)
        </h2>
        <p className="mt-3 text-muted-foreground">
          The simulation engine runs thousands of Monte Carlo iterations so runway is a distribution, not a single spreadsheet cash-out date. P10/P50/P90 confidence bands make the range visible. Side-by-side scenarios let you test hiring plans, pricing, fundraising timing, and growth assumptions before you commit. The deeper catalog is on{" "}
          <Link href="/features" className="text-primary hover:underline" data-testid="link-hiw-features">
            features
          </Link>
          ; jobs this maps to are on{" "}
          <Link href="/use-cases" className="text-primary hover:underline" data-testid="link-hiw-use-cases">
            use cases
          </Link>
          .
        </p>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          4. AI copilot and decisions
        </h2>
        <p className="mt-3 text-muted-foreground">
          A multi-LLM copilot answers strategic questions in plain English, grounded in your connected financials. Simulation results become narrative briefings and ranked recommendations (GO / CONDITIONAL / NO-GO). Every answer shows its reasoning, assumptions, and data sources — so you can defend the decision, not just the chart.
        </p>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          5. Fundraising tools
        </h2>
        <p className="mt-3 text-muted-foreground">
          Fundraising OS covers cap table management, SAFE and convertible note conversion modeling, dilution modeling, and an investor room with secure document sharing. Use these after you have a range from the simulation — not instead of it. The product overview is on{" "}
          <Link href="/product" className="text-primary hover:underline" data-testid="link-hiw-product">
            product
          </Link>
          .
        </p>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          Evaluate the product, not a timeline
        </h2>
        <p className="mt-3 text-muted-foreground">
          Read the{" "}
          <Link href="/product" className="text-primary hover:underline" data-testid="link-hiw-product-eval">
            product
          </Link>{" "}
          overview, the{" "}
          <Link href="/features" className="text-primary hover:underline" data-testid="link-hiw-features-eval">
            features
          </Link>{" "}
          catalog,{" "}
          <Link href="/use-cases" className="text-primary hover:underline" data-testid="link-hiw-use-cases-eval">
            use cases
          </Link>
          , and{" "}
          <Link href="/pricing" className="text-primary hover:underline" data-testid="link-hiw-pricing">
            pricing
          </Link>{" "}
          (every feature is free during early access).
        </p>
        <div className="mt-8">
          <Button asChild data-testid="button-hiw-auth">
            <Link href="/auth?tab=register">
              Get started free
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </div>
      </article>
    </MarketingLayout>
  );
}
