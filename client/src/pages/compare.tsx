import { Link } from "wouter";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { Button } from "@/components/ui/button";
import { useSEO } from "@/lib/seo";
import { ArrowRight } from "lucide-react";

export default function ComparePage() {
  useSEO({
    title: "Compare FounderConsole to Startup FP&A and Runway Tools",
    description:
      "See how FounderConsole compares to startup FP&A and runway tools: Monte Carlo P10/P50/P90 forecasts, an AI copilot, and free tools — plus the Finmark sunset and Causal absorption notes we already published.",
    path: "/compare",
    jsonLd: {
      "@context": "https://schema.org",
      "@type": "WebPage",
      name: "Compare FounderConsole to Startup FP&A and Runway Tools",
      description:
        "How FounderConsole compares to startup FP&A and runway tools: Monte Carlo P10/P50/P90, AI copilot, and free tools.",
      url: "https://founderconsole.ai/compare",
      isPartOf: { "@type": "WebSite", name: "FounderConsole", url: "https://founderconsole.ai" },
    },
  });

  return (
    <MarketingLayout>
      <article className="mx-auto max-w-3xl px-4 py-16 md:py-20">
        <h1 className="text-3xl font-bold tracking-tight text-foreground md:text-4xl" data-testid="text-compare-title">
          Compare FounderConsole to startup FP&A and runway tools
        </h1>
        <p className="mt-4 text-lg text-muted-foreground">
          Founders comparing startup financial-planning and runway tools usually want a range they can defend, not a single spreadsheet date. This page states what FounderConsole already ships — Monte Carlo P10/P50/P90 bands, an AI copilot, and free tools that need no account — and points to the longer comparison we published.
        </p>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          What FounderConsole is built to do
        </h2>
        <p className="mt-3 text-muted-foreground">
          FounderConsole is an AI-powered financial intelligence platform for startup founders. Connect your data (or upload a CSV), run Monte Carlo simulations, and ask the copilot questions against your own numbers.
        </p>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-muted-foreground">
          <li>
            <strong className="text-foreground">Monte Carlo with P10/P50/P90</strong> — thousands of runs produce a runway distribution instead of one cash-out date.
          </li>
          <li>
            <strong className="text-foreground">AI copilot</strong> — strategic questions in plain English, grounded in your connected financials, with reasoning you can show a board.
          </li>
          <li>
            <strong className="text-foreground">Free tools</strong> — runway, default-alive, and survival calculators you can use without signing up.
          </li>
        </ul>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          The comparison we already published
        </h2>
        <p className="mt-3 text-muted-foreground">
          Read{" "}
          <Link href="/blog/founderconsole-vs-sturppy-vs-finmark-vs-causal" className="text-primary hover:underline" data-testid="link-compare-blog">
            FounderConsole vs Sturppy vs Finmark vs Causal
          </Link>{" "}
          for the sourced product-status notes. As of August 2026, Finmark has been sunset and Causal has been absorbed into an enterprise suite.
        </p>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          Related free tools
        </h2>
        <p className="mt-3 text-muted-foreground">
          Try these with no account: the{" "}
          <Link href="/tools/runway-calculator" className="text-primary hover:underline" data-testid="link-compare-runway">
            startup runway calculator
          </Link>
          , the{" "}
          <Link href="/survival-simulator" className="text-primary hover:underline" data-testid="link-compare-survival">
            startup survival simulator
          </Link>
          , or the{" "}
          <Link href="/default-alive" className="text-primary hover:underline" data-testid="link-compare-default-alive">
            default alive test
          </Link>
          . See the full product on{" "}
          <Link href="/features" className="text-primary hover:underline" data-testid="link-compare-features">
            features
          </Link>
          .
        </p>
        <div className="mt-8">
          <Button asChild data-testid="button-compare-auth">
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
