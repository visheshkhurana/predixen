import { Link } from "wouter";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useSEO } from "@/lib/seo";
import { ArrowRight, Calculator } from "lucide-react";

/**
 * HAG-449: `/tools` was a 404.
 *
 * Nothing linked to it — not the nav, not the footer, not the sitemap, not any
 * in-app link — so this is a page that was never built rather than a broken
 * link to one. Before this, a visitor who trimmed
 * `/tools/runway-calculator` back to `/tools` got the not-found page whose only
 * advice was "browse the free runway calculator instead"; the sitemap listed the
 * individual tools, so a crawler had the leaves and no hub.
 *
 * The four calculators under `/tools/` are listed first because they share the
 * URL segment. The two other free calculators live at the site root and get
 * their own group rather than being quietly omitted from a page called "tools".
 *
 * `/ai-cfo` is NOT in that group. It is the product, not a no-account tool: its
 * own page excludes itself from the no-account list and its only CTA is `/auth`.
 * A card promising "no account, no card" that lands on a signup is the same
 * false-promise shape this page exists to remove, so it is linked from the
 * closing ("when you are ready") section instead.
 */

interface ToolEntry {
  href: string;
  name: string;
  /** what goes in, in the visitor's words */
  input: string;
  /** what comes out, in one line */
  output: string;
}

const PRIMARY_TOOLS: readonly ToolEntry[] = [
  {
    href: "/tools/runway-calculator",
    name: "Startup Runway Calculator",
    input: "Cash on hand, monthly revenue, monthly expenses, growth rate",
    output: "Months of runway and the month your cash runs out",
  },
  {
    href: "/tools/burn-multiple",
    name: "Burn Multiple Calculator",
    input: "New and total ARR at the start and end of a period, plus net burn",
    output: "How many dollars of burn bought each dollar of net new ARR",
  },
  {
    href: "/tools/dilution",
    name: "Dilution Calculator",
    input: "Pre-money valuation, amount raised, existing option pool",
    output: "The percentage of the company a round costs you, and post-round ownership",
  },
  {
    href: "/tools/ltv-cac",
    name: "LTV:CAC Calculator",
    input: "ARPU, gross margin, churn, marketing spend, new customers",
    output: "Lifetime value against acquisition cost — graded separately from payback",
  },
];

const MORE_TOOLS: readonly ToolEntry[] = [
  {
    href: "/default-alive",
    name: "Default Alive Test",
    input: "Cash, revenue, expenses and growth rate",
    output: "Paul Graham's default alive or default dead verdict, with what would flip it",
  },
  {
    href: "/survival-simulator",
    name: "Startup Survival Simulator",
    input: "Your financials",
    output: "A Monte Carlo survival probability rather than a single point estimate",
  },
];

function ToolGrid({ tools }: { tools: readonly ToolEntry[] }) {
  return (
    <div className="grid gap-6 md:grid-cols-2">
      {tools.map((tool) => (
        <Link key={tool.href} href={tool.href}>
          <Card
            className="h-full transition-colors hover:border-primary/50"
            data-testid={`card-tool-${tool.href.split("/").pop()}`}
          >
            <CardHeader>
              <CardTitle className="flex items-center justify-between gap-3 text-lg">
                {tool.name}
                <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground" />
              </CardTitle>
              <CardDescription>
                <span className="text-foreground/80">In:</span> {tool.input}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">{tool.output}</p>
            </CardContent>
          </Card>
        </Link>
      ))}
    </div>
  );
}

export default function ToolsIndexPage() {
  useSEO({
    title: "Free Startup Finance Tools — Runway, Burn, Dilution, LTV:CAC | FounderConsole",
    description:
      "Four free startup finance calculators and two more free tools. Runway, burn multiple, dilution and LTV:CAC — no account, no card, no demo call.",
    path: "/tools",
    jsonLd: [
      {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        name: "Free Startup Finance Tools",
        url: "https://founderconsole.ai/tools",
      },
      {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        itemListElement: [
          { "@type": "ListItem", position: 1, name: "Home", item: "https://founderconsole.ai/" },
          { "@type": "ListItem", position: 2, name: "Free tools", item: "https://founderconsole.ai/tools" },
        ],
      },
    ],
  });

  return (
    <MarketingLayout>
      <section className="border-b">
        <div className="mx-auto max-w-6xl px-4 py-16 md:py-20">
          <div className="mb-4 flex items-center gap-2">
            <Badge variant="secondary" className="text-xs" data-testid="badge-free-tools">
              <Calculator className="mr-1 h-3 w-3" />
              Free tools
            </Badge>
          </div>
          <h1
            className="text-3xl font-bold tracking-tight text-foreground md:text-4xl lg:text-5xl"
            data-testid="text-tools-title"
          >
            Free startup finance tools
          </h1>
          <p className="mt-3 max-w-2xl text-lg text-muted-foreground">
            The four numbers that decide how long a company has left: runway, burn multiple,
            dilution and LTV:CAC. Each one is a calculator you can finish in under a minute —
            no account, no card, no demo call.
          </p>
        </div>
      </section>

      <section className="border-b">
        <div className="mx-auto max-w-6xl px-4 py-12">
          <h2 className="mb-6 text-2xl font-semibold tracking-tight text-foreground">
            The four calculators
          </h2>
          <ToolGrid tools={PRIMARY_TOOLS} />
        </div>
      </section>

      <section className="border-b">
        <div className="mx-auto max-w-6xl px-4 py-12">
          <h2 className="mb-2 text-2xl font-semibold tracking-tight text-foreground">
            Two more free tools
          </h2>
          <p className="mb-6 max-w-2xl text-muted-foreground">
            These do not sit under <code>/tools</code>, but they are free in the same way — no
            account, no card — and they answer the same kind of question.
          </p>
          <ToolGrid tools={MORE_TOOLS} />
        </div>
      </section>

      <section>
        <div className="mx-auto max-w-6xl px-4 py-12">
          <div className="rounded-lg border bg-muted/30 p-8">
            <h2 className="text-2xl font-semibold tracking-tight text-foreground">
              From a single answer to a range
            </h2>
            <p className="mt-3 max-w-2xl text-muted-foreground">
              Every calculator here holds your inputs steady and returns one number. Real
              revenue is lumpy, so the month that decides the answer is rarely the average
              month. FounderConsole connects to your actual financial data and runs the same
              question thousands of times, so you get a distribution with P10/P50/P90 bands
              instead of a single date.
            </p>
            <p className="mt-3 max-w-2xl text-muted-foreground">
              When you want that answer from your own connected numbers rather than a form, the{" "}
              <Link href="/ai-cfo" className="text-primary underline underline-offset-4">
                AI CFO
              </Link>{" "}
              is the next step.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link href="/auth?tab=register">
                <Button data-testid="button-tools-signup">
                  Get started free
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
              <Link href="/pricing">
                <Button variant="outline" data-testid="button-tools-pricing">
                  See pricing
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>
    </MarketingLayout>
  );
}
