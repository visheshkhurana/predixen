import { Link } from "wouter";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { Button } from "@/components/ui/button";
import { useSEO } from "@/lib/seo";
import { ArrowRight } from "lucide-react";

export default function ProductPage() {
  useSEO({
    title: "Product — Financial Intelligence for Startup Founders | FounderConsole",
    description:
      "FounderConsole is an AI-powered financial intelligence platform for startup founders. Monte Carlo P10/P50/P90, AI copilot, connectors, and Fundraising OS — free during early access.",
    path: "/product",
    jsonLd: {
      "@context": "https://schema.org",
      "@type": "WebPage",
      name: "FounderConsole Product",
      description:
        "FounderConsole is an AI-powered financial intelligence platform for startup founders. Monte Carlo P10/P50/P90, AI copilot, connectors, and Fundraising OS — free during early access.",
      url: "https://founderconsole.ai/product",
      isPartOf: { "@type": "WebSite", name: "FounderConsole", url: "https://founderconsole.ai" },
    },
  });

  return (
    <MarketingLayout>
      <article className="mx-auto max-w-3xl px-4 py-16 md:py-20">
        <h1 className="text-3xl font-bold tracking-tight text-foreground md:text-4xl" data-testid="text-product-title">
          FounderConsole — financial intelligence for startup founders
        </h1>
        <p className="mt-4 text-lg text-muted-foreground">
          FounderConsole is an AI-powered financial intelligence platform built for startup founders. Connect your data, run Monte Carlo simulations with P10/P50/P90 bands, ask an AI copilot against your own numbers, and manage fundraising from one place — without a spreadsheet as the source of truth.
        </p>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          Who it is for
        </h2>
        <p className="mt-3 text-muted-foreground">
          Founders who are asked to be CFO and CEO at once: operators without a finance team who need a range they can defend to a board rather than a single cash-out date. This page is the product overview. The deeper catalog lives on{" "}
          <Link href="/features" className="text-primary hover:underline" data-testid="link-product-features">
            features
          </Link>
          .
        </p>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          What you get
        </h2>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-muted-foreground">
          <li>
            <strong className="text-foreground">Monte Carlo P10/P50/P90</strong> — thousands of runs produce a runway distribution instead of one forecast.
          </li>
          <li>
            <strong className="text-foreground">AI copilot</strong> — strategic questions in plain English, grounded in your connected financials.
          </li>
          <li>
            <strong className="text-foreground">Connectors</strong> — 37 data connectors for the tools founders already use, or upload a CSV so the model stays current.
          </li>
          <li>
            <strong className="text-foreground">Fundraising OS</strong> — cap table, dilution modeling, and investor-ready materials in one place.
          </li>
        </ul>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          Free during early access
        </h2>
        <p className="mt-3 text-muted-foreground">
          Every feature is free while we are in early access — no credit card required. Planned paid tiers after early access are on the{" "}
          <Link href="/pricing" className="text-primary hover:underline" data-testid="link-product-pricing">
            pricing
          </Link>{" "}
          page.
        </p>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          Related pages and free tools
        </h2>
        <p className="mt-3 text-muted-foreground">
          See how we stack up on{" "}
          <Link href="/compare" className="text-primary hover:underline" data-testid="link-product-compare">
            compare
          </Link>
          . Try these with no account: the{" "}
          <Link href="/tools/runway-calculator" className="text-primary hover:underline" data-testid="link-product-runway">
            startup runway calculator
          </Link>
          , the{" "}
          <Link href="/survival-simulator" className="text-primary hover:underline" data-testid="link-product-survival">
            startup survival simulator
          </Link>
          , or the{" "}
          <Link href="/default-alive" className="text-primary hover:underline" data-testid="link-product-default-alive">
            default alive test
          </Link>
          .
        </p>
        <div className="mt-8">
          <Button asChild data-testid="button-product-auth">
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
