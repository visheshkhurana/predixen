import { Link } from "wouter";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { Button } from "@/components/ui/button";
import { useSEO } from "@/lib/seo";
import { ArrowRight } from "lucide-react";

export default function CustomersPage() {
  useSEO({
    title: "Who FounderConsole Is For — Seed and Series A Founders",
    description:
      "FounderConsole is for seed and Series A founders who need runway confidence. We are in early access and have not published logos or case studies — evaluate with free tools, product pages, and a free account.",
    path: "/customers",
    jsonLd: {
      "@context": "https://schema.org",
      "@type": "WebPage",
      name: "Who FounderConsole Is For — Seed and Series A Founders",
      description:
        "FounderConsole is for seed and Series A founders who need runway confidence. Evaluate with free tools and product pages — we have not published customer logos or case studies.",
      url: "https://founderconsole.ai/customers",
      isPartOf: { "@type": "WebSite", name: "FounderConsole", url: "https://founderconsole.ai" },
    },
  });

  return (
    <MarketingLayout>
      <article className="mx-auto max-w-3xl px-4 py-16 md:py-20">
        <h1 className="text-3xl font-bold tracking-tight text-foreground md:text-4xl" data-testid="text-customers-title">
          Who FounderConsole is for
        </h1>
        <p className="mt-4 text-lg text-muted-foreground">
          FounderConsole is built for seed and Series A founders who need runway confidence — a range they can defend to a board, not a single spreadsheet cash-out date. If you are the operator asked to be CFO and CEO at once, this page is the audience overview.
        </p>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          Seed and Series A founders who need a defensible range
        </h2>
        <p className="mt-3 text-muted-foreground">
          The product is for founders who still run finance themselves: people who have to hire, cut burn, or time a raise without a dedicated FP&A team. Monte Carlo P10/P50/P90 bands, an AI copilot grounded in your numbers, and free tools exist so you can see the range before you commit live data.
        </p>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-muted-foreground">
          <li>Seed and Series A operators who need a runway distribution instead of one cash-out date.</li>
          <li>Founders answering board and investor questions without a finance team behind them.</li>
          <li>People deciding whether to hire, cut spend, or raise — and wanting the simulation to show the range of outcomes.</li>
        </ul>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          No published logos or case studies yet
        </h2>
        <p className="mt-3 text-muted-foreground">
          We are in early access. We have not published customer names, logos, quotes, or case studies, and this page does not invent them. Evaluate FounderConsole on the product itself, not on unnamed social proof.
        </p>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          How to evaluate without a testimonial wall
        </h2>
        <p className="mt-3 text-muted-foreground">
          Read the{" "}
          <Link href="/product" className="text-primary hover:underline" data-testid="link-customers-product">
            product
          </Link>{" "}
          overview, the{" "}
          <Link href="/features" className="text-primary hover:underline" data-testid="link-customers-features">
            features
          </Link>{" "}
          catalog,{" "}
          <Link href="/compare" className="text-primary hover:underline" data-testid="link-customers-compare">
            compare
          </Link>
          , and{" "}
          <Link href="/pricing" className="text-primary hover:underline" data-testid="link-customers-pricing">
            pricing
          </Link>{" "}
          (every feature is free during early access). Try these with no account: the{" "}
          <Link href="/tools/runway-calculator" className="text-primary hover:underline" data-testid="link-customers-runway">
            startup runway calculator
          </Link>
          , the{" "}
          <Link href="/survival-simulator" className="text-primary hover:underline" data-testid="link-customers-survival">
            startup survival simulator
          </Link>
          , or the{" "}
          <Link href="/default-alive" className="text-primary hover:underline" data-testid="link-customers-default-alive">
            default alive test
          </Link>
          .
        </p>
        <div className="mt-8">
          <Button asChild data-testid="button-customers-auth">
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
