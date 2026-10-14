import { Link } from "wouter";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { Button } from "@/components/ui/button";
import { useSEO } from "@/lib/seo";
import { ArrowRight } from "lucide-react";

/**
 * /vs/ comparison page — council idea 1, the page half.
 *
 * The visitor search is "runway calculator vs spreadsheet": a founder who
 * already keeps runway in a sheet and is comparing the two. So the page has to
 * do the one thing a comparison page usually refuses to do — say where the
 * spreadsheet wins. A page that only argues for the product answers a question
 * the visitor did not ask and reads as an advert.
 *
 * No competitor is named and no competitor feature, price or market claim is
 * asserted, following the rule /alternatives already states on the page.
 * Everything asserted about FounderConsole here is already published on
 * /compare and /features; the free tools are live and linked.
 */
export default function VsRunwayCalculatorVsSpreadsheetPage() {
  useSEO({
    title: "Runway Calculator vs Spreadsheet — Which Should You Use? | FounderConsole",
    description:
      "Runway calculator or spreadsheet? A sheet gives you full control and one cash-out date; a calculator gives you a benchmarked answer in seconds. Where each one wins, and when you outgrow both.",
    path: "/vs/runway-calculator-vs-spreadsheet",
    jsonLd: {
      "@context": "https://schema.org",
      "@type": "WebPage",
      name: "Runway Calculator vs Spreadsheet — Which Should You Use? | FounderConsole",
      description:
        "Where a spreadsheet wins for runway modelling, where it breaks, and what a calculator gives you instead.",
      url: "https://founderconsole.ai/vs/runway-calculator-vs-spreadsheet",
      isPartOf: { "@type": "WebSite", name: "FounderConsole", url: "https://founderconsole.ai" },
    },
  });

  return (
    <MarketingLayout>
      <article className="mx-auto max-w-3xl px-4 py-16 md:py-20">
        <h1
          className="text-3xl font-bold tracking-tight text-foreground md:text-4xl"
          data-testid="text-vs-title"
        >
          Runway calculator vs spreadsheet: which one should you use?
        </h1>
        <p className="mt-4 text-lg text-muted-foreground">
          A spreadsheet is the right tool for your first runway model, and it is still the right tool for a
          one-off static plan. It stops being the right tool at a specific point: when you need a range rather
          than a date, when an input changes and you have to re-derive the answer by hand, or when someone asks
          you how confident you are in the number. This page is the honest comparison — including the rows where
          the spreadsheet wins.
        </p>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          The short answer
        </h2>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-muted-foreground">
          <li>
            <strong className="text-foreground">Use a spreadsheet</strong> if the model is yours, the plan is
            static, and nobody outside the company has to rely on the output.
          </li>
          <li>
            <strong className="text-foreground">Use a calculator</strong> when you want the answer now, with
            benchmarked starting assumptions and no chance of a broken formula.
          </li>
          <li>
            <strong className="text-foreground">Outgrow both</strong> when the question stops being{" "}
            <em>what is my runway?</em> and becomes <em>how likely is it that I run out, and what moves the
            date?</em> A single number — from a sheet or from a calculator — cannot answer that.
          </li>
        </ul>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          Side by side
        </h2>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full border-collapse text-left text-sm" data-testid="table-vs-comparison">
            <thead>
              <tr className="border-b border-border">
                <th className="py-3 pr-4 font-semibold text-foreground">&nbsp;</th>
                <th className="py-3 pr-4 font-semibold text-foreground">Spreadsheet</th>
                <th className="py-3 pr-4 font-semibold text-foreground">Free runway calculator</th>
                <th className="py-3 font-semibold text-foreground">FounderConsole</th>
              </tr>
            </thead>
            <tbody className="text-muted-foreground">
              <tr className="border-b border-border align-top">
                <td className="py-3 pr-4 font-medium text-foreground">Time to a first answer</td>
                <td className="py-3 pr-4">Whatever it takes to build the model — tens of minutes to hours</td>
                <td className="py-3 pr-4">Seconds, with no account</td>
                <td className="py-3">Minutes once your data is connected</td>
              </tr>
              <tr className="border-b border-border align-top">
                <td className="py-3 pr-4 font-medium text-foreground">What you get back</td>
                <td className="py-3 pr-4">One cash-out date from the assumptions you typed</td>
                <td className="py-3 pr-4">Months of runway and a cash-out date, from bench-marked inputs</td>
                <td className="py-3">A distribution — P10/P50/P90 bands, not one date</td>
              </tr>
              <tr className="border-b border-border align-top">
                <td className="py-3 pr-4 font-medium text-foreground">When an input changes</td>
                <td className="py-3 pr-4">You edit cells and re-check the downstream formula</td>
                <td className="py-3 pr-4">Change the field, the answer updates</td>
                <td className="py-3">The forecast updates from your connected data</td>
              </tr>
              <tr className="border-b border-border align-top">
                <td className="py-3 pr-4 font-medium text-foreground">Formula risk</td>
                <td className="py-3 pr-4">Real: a hardcoded cell or a broken range silently changes the date</td>
                <td className="py-3 pr-4">None you can introduce — the arithmetic is fixed</td>
                <td className="py-3">None you can introduce</td>
              </tr>
              <tr className="border-b border-border align-top">
                <td className="py-3 pr-4 font-medium text-foreground">Where the assumptions come from</td>
                <td className="py-3 pr-4">You, from memory or from the last plan</td>
                <td className="py-3 pr-4">Benchmarked starting inputs you can override</td>
                <td className="py-3">Your own connected financials</td>
              </tr>
              <tr className="border-b border-border align-top">
                <td className="py-3 pr-4 font-medium text-foreground">Sharing it</td>
                <td className="py-3 pr-4">Attach the file; the reader may not know which cell drives the answer</td>
                <td className="py-3 pr-4">Send a link</td>
                <td className="py-3">Share the scenario, with reasoning you can show a board</td>
              </tr>
              <tr className="align-top">
                <td className="py-3 pr-4 font-medium text-foreground">Cost</td>
                <td className="py-3 pr-4">Free if you already have it</td>
                <td className="py-3 pr-4">Free, no account</td>
                <td className="py-3">Every feature is free during early access</td>
              </tr>
            </tbody>
          </table>
        </div>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          Where the spreadsheet wins
        </h2>
        <p className="mt-3 text-muted-foreground">
          It is your model. Nobody else's tool decides what a line item means, how you treat a grant, or whether
          a hire lands in month 3 or month 4. A spreadsheet handles the irregular thing — a deferred payment, a
          one-off invoice, a seasonal month — without asking you to bend it into someone's form. It works
          offline, it is on your machine, and for a static plan you intend to look at once, building the model
          is not wasted effort: it is how you learn your own business. All of that stays true.
        </p>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          Where the spreadsheet breaks
        </h2>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-muted-foreground">
          <li>
            <strong className="text-foreground">It gives you a date, and a date reads like a fact.</strong> The
            arithmetic is a straight line: $120,000 in the bank against $20,000 of net burn is six months. Real
            burn is not a straight line, so the honest output is a range of dates and a probability of running
            out — which a single-cell answer cannot express, however correct the cell is.
          </li>
          <li>
            <strong className="text-foreground">It goes stale the day you build it.</strong> The model is
            correct as of the numbers you typed. The bank balance moves on Monday.
          </li>
          <li>
            <strong className="text-foreground">The failure is silent.</strong> A hardcoded cell, a drag that
            stopped one row short, a formula copied across a column it should not have been — the sheet still
            returns a number, and the number still looks fine. Nothing warns you.
          </li>
          <li>
            <strong className="text-foreground">It has no benchmark.</strong> A sheet will tell you what your
            assumptions imply. It will not tell you that the assumption itself is unusual for a company at your
            stage, because it has nothing to compare against.
          </li>
          <li>
            <strong className="text-foreground">Reading it is a skill.</strong> Handing the file to a board
            member or a new hire transfers the model, not the understanding — including the part where you know
            which three cells actually matter.
          </li>
        </ul>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          The honest limit of a free calculator
        </h2>
        <p className="mt-3 text-muted-foreground">
          A calculator fixes the formula risk and the staleness, and it gives you a benchmarked starting point
          instead of a blank grid. What it does not fix is the thing at the top of that list:{" "}
          <strong className="text-foreground">it still returns one number</strong>, because you are still
          entering one set of assumptions. Moving the arithmetic out of your spreadsheet is worth doing — but if
          the only change is that a website does the multiplication, you have not yet answered the question your
          investor is asking.
        </p>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          What a range looks like instead
        </h2>
        <p className="mt-3 text-muted-foreground">
          FounderConsole runs Monte Carlo simulations over your own connected numbers — thousands of runs
          produce P10/P50/P90 bands, so runway is a distribution rather than a date, and you can see which
          assumption moves it. The AI copilot answers strategic questions against the same numbers, with
          reasoning you can show a board. What FounderConsole ships is already set out on{" "}
          <Link href="/compare" className="text-primary hover:underline" data-testid="link-vs-compare">
            compare
          </Link>{" "}
          and{" "}
          <Link href="/features" className="text-primary hover:underline" data-testid="link-vs-features">
            features
          </Link>
          , and every feature is free during early access — see{" "}
          <Link href="/pricing" className="text-primary hover:underline" data-testid="link-vs-pricing">
            pricing
          </Link>
          .
        </p>

        <h2 className="mt-10 text-2xl font-semibold tracking-tight text-foreground">
          Try the free side of the comparison first
        </h2>
        <p className="mt-3 text-muted-foreground">
          No account required. Enter your cash, burn and revenue on the{" "}
          <Link
            href="/tools/runway-calculator"
            className="text-primary hover:underline"
            data-testid="link-vs-runway"
          >
            startup runway calculator
          </Link>{" "}
          and compare its answer with your sheet — if the two disagree, one of them has a broken assumption and
          it is worth knowing which. Paul Graham's{" "}
          <Link href="/default-alive" className="text-primary hover:underline" data-testid="link-vs-default-alive">
            default alive or default dead
          </Link>{" "}
          test asks the harder question behind the arithmetic, and the{" "}
          <Link
            href="/survival-simulator"
            className="text-primary hover:underline"
            data-testid="link-vs-survival"
          >
            startup survival simulator
          </Link>{" "}
          estimates odds of survival rather than months. If you want industry-tuned starting inputs, start from
          the{" "}
          <Link href="/runway/saas" className="text-primary hover:underline" data-testid="link-vs-saas">
            SaaS runway calculator
          </Link>
          .
        </p>
        <div className="mt-8">
          <Button asChild data-testid="button-vs-auth">
            <Link href="/auth?tab=register">
              Get started free
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </div>

        <p className="mt-8 text-sm text-muted-foreground">
          This page compares a spreadsheet with a calculator and with FounderConsole. It does not name or make
          claims about any other software vendor, and it does not restate competitor pricing, market share, or
          product status.
        </p>
      </article>
    </MarketingLayout>
  );
}
