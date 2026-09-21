import { Link } from "wouter";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { Button } from "@/components/ui/button";
import { useSEO } from "@/lib/seo";
import { ArrowRight } from "lucide-react";

export default function AlternativesPage() {
  useSEO({
    title: "Startup FP&A Alternatives — After Finmark and Causal | FounderConsole",
    description:
      "Looking for a Finmark or Causal alternative? BILL sunset Finmark; Causal joined Lucanet. This page summarizes the FP&A consolidation we already published and what FounderConsole ships — Monte Carlo P10/P50/P90, an AI copilot, and free tools.",
    path: "/alternatives",
    jsonLd: {
      "@context": "https://schema.org",
      "@type": "WebPage",
      name: "Startup FP&A Alternatives — After Finmark and Causal | FounderConsole",
      description:
        "Looking for a Finmark or Causal alternative? BILL sunset Finmark; Causal joined Lucanet. Summarizes the FP&A consolidation we already published and what FounderConsole ships.",
      url: "https://founderconsole.ai/alternatives",
      isPartOf: { "@type": "WebSite", name: "FounderConsole", url: "https://founderconsole.ai" },
    },
  });

  return (
    <MarketingLayout>
      <article className="mx-auto max-w-3xl px-4 py-16 md:py-20">
        <h1 className="text-3xl font-bold tracking-tight text-foreground md:text-4xl" data-testid="text-alternatives-title">
          Startup FP&A alternatives — after Finmark, Causal, and the rest
        </h1>
        <p className="mt-4 text-lg text-muted-foreground">
          This is a category page for founders looking for an alternative to the startup FP&A tools that disappeared. BILL sunset Finmark. Causal was absorbed into Lucanet. The sourced notes live on pages we already published — this page summarizes that consolidation and points to FounderConsole as a seed-stage option. It does not invent competitor pricing, market share, or new product-status claims.
        </p>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          What happened to the category
        </h2>
        <p className="mt-3 text-muted-foreground">
          As of August 2026, the seed-stage FP&A field is thinner than it was. We tracked the timeline in full:
        </p>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-muted-foreground">
          <li>
            BILL sunset Finmark on 1 April 2026. finmark.com redirects to bill.com with no destination page or migration guide. If Finmark is the tool you lost, read{" "}
            <Link href="/blog/finmark-shut-down-alternative" className="text-primary hover:underline" data-testid="link-alt-finmark-blog">
              where your runway model goes next
            </Link>
            .
          </li>
          <li>
            Causal joined Lucanet in October 2024 and redirects to an enterprise Extended Planning & Analysis page rather than a founder product.
          </li>
          <li>
            Pry was acquired by Brex. Mosaic was acquired by HiBob. In July 2026 Runway Financial lost the runway.com domain to an AI video company.
          </li>
        </ul>
        <p className="mt-3 text-muted-foreground">
          The full sequence, with what each redirect lands on, is in{" "}
          <Link href="/blog/startup-fpa-tools-acquired-timeline" className="text-primary hover:underline" data-testid="link-alt-timeline-blog">
            Every Startup FP&A Tool Got Acquired. Here's the Timeline.
          </Link>
        </p>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          The comparison we already published
        </h2>
        <p className="mt-3 text-muted-foreground">
          Product-versus-product notes — including that Sturppy is still aimed at early-stage companies — are on{" "}
          <Link href="/compare" className="text-primary hover:underline" data-testid="link-alt-compare">
            compare
          </Link>{" "}
          and in{" "}
          <Link href="/blog/founderconsole-vs-sturppy-vs-finmark-vs-causal" className="text-primary hover:underline" data-testid="link-alt-vs-blog">
            FounderConsole vs Sturppy vs Finmark vs Causal
          </Link>
          . We do not repeat competitor pricing here; those posts are the source.
        </p>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          What FounderConsole ships
        </h2>
        <p className="mt-3 text-muted-foreground">
          FounderConsole is an AI-powered financial intelligence platform for startup founders. Connect data (or upload a CSV), run Monte Carlo simulations, and ask an AI copilot against your own numbers.
        </p>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-muted-foreground">
          <li>
            <strong className="text-foreground">Monte Carlo with P10/P50/P90</strong> — thousands of runs produce a runway distribution instead of one cash-out date.
          </li>
          <li>
            <strong className="text-foreground">AI copilot</strong> — strategic questions in plain English, grounded in your connected financials.
          </li>
          <li>
            <strong className="text-foreground">37 data connectors</strong> — or a CSV of monthly actuals so you can reconstruct a model after an acquired tool goes away.
          </li>
        </ul>
        <p className="mt-3 text-muted-foreground">
          The product overview is on{" "}
          <Link href="/product" className="text-primary hover:underline" data-testid="link-alt-product">
            product
          </Link>
          . The deeper catalog is on{" "}
          <Link href="/features" className="text-primary hover:underline" data-testid="link-alt-features">
            features
          </Link>
          . Every feature is free during early access — see{" "}
          <Link href="/pricing" className="text-primary hover:underline" data-testid="link-alt-pricing">
            pricing
          </Link>
          .
        </p>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          Try a free tool first
        </h2>
        <p className="mt-3 text-muted-foreground">
          No account required: the{" "}
          <Link href="/tools/runway-calculator" className="text-primary hover:underline" data-testid="link-alt-runway">
            startup runway calculator
          </Link>
          , the{" "}
          <Link href="/survival-simulator" className="text-primary hover:underline" data-testid="link-alt-survival">
            startup survival simulator
          </Link>
          , or the{" "}
          <Link href="/default-alive" className="text-primary hover:underline" data-testid="link-alt-default-alive">
            default alive test
          </Link>
          .
        </p>
        <div className="mt-8">
          <Button asChild data-testid="button-alt-auth">
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
