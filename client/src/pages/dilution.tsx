import { useMemo, useState } from "react";
import { Link } from "wouter";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { CalculatorEmailOptIn } from "@/components/marketing/CalculatorEmailOptIn";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { useSEO } from "@/lib/seo";
import { TOOL_PAGE_META } from "@/data/tool-page-meta";
import { trackFunnel } from "@/lib/funnel";
import { useCalculatorUsed } from "@/hooks/use-calculator-used";
import {
  ArrowRight,
  Calculator,
  Percent,
  AlertTriangle,
  Info,
  PieChart,
} from "lucide-react";
import {
  CUMULATIVE_KEEP_2025,
  computeDilution,
  WORKED_EXAMPLE,
  type DilutionInputs,
} from "@/lib/tools/dilution";

/**
 * HAG-163, tool 2 of 3: /tools/dilution.
 *
 * The maths is in `client/src/lib/tools/dilution.ts` and is transcribed from
 * `hive/reports/quant-forge-tools-maths.md` (Quant lane, HAG-172) rather than invented
 * here. That module is the only place the formula lives, so the page and its test cannot
 * disagree about it.
 *
 * The fields hold TEXT, not numbers. `Number("")` is 0, so a field bound directly to a
 * number snaps back to "0" the moment a visitor clears it — the defect fixed on
 * /tools/runway-calculator. Parsing on read avoids it here too.
 */

type FieldKey = keyof DilutionInputs;

interface FieldSpec {
  key: FieldKey;
  label: string;
  /** printed next to the field, so the unit can never be guessed */
  unit: string;
  help?: string;
  /** a CHOICE from the maths file, stated on the page in one line as the brief requires */
  choice?: string;
  testId: string;
}

const FIELDS: readonly FieldSpec[] = [
  {
    key: "pre_money_valuation",
    label: "Pre-money valuation",
    unit: "USD",
    help: "The valuation agreed with the investor, before their money goes in.",
    testId: "input-dil-pre-money",
  },
  {
    key: "raise_amount",
    label: "Amount raised",
    unit: "USD",
    help: "New money into the company in this round.",
    testId: "input-dil-raise",
  },
  {
    key: "founder_shares",
    label: "Founder shares",
    unit: "shares",
    help: "Founder and employee shares before the round. Only the ratio to the pool matters, so any two numbers with the right ratio work.",
    testId: "input-dil-founder-shares",
  },
  {
    key: "existing_pool_shares",
    label: "Existing option pool",
    unit: "shares",
    help: "Unissued options before the round — granted but not yet exercised.",
    testId: "input-dil-pool-shares",
  },
  {
    key: "pool_target_pct",
    label: "Option pool after the round",
    unit: "% of post-money",
    help: "The pool the round is required to leave behind, as a percentage of the post-money total. 0 means this round creates no pool.",
    choice:
      "Chosen: the pool top-up is created before the money goes in, so it dilutes existing holders and never the new investor — the standard term-sheet practice known as the option pool shuffle. The pool target is a share of post-money, and the top-up never shrinks: this tool will not quietly cancel options you already granted.",
    testId: "input-dil-pool-target",
  },
];

function toNumber(raw: string): number {
  const trimmed = raw.trim().replace(/[$,\s%]/g, "");
  if (trimmed === "") return 0;
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : Number.NaN;
}

function formatCurrency(value: number): string {
  const sign = value < 0 ? "-" : "";
  const abs = Math.abs(value);
  if (abs >= 1_000_000) return `${sign}$${(abs / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000) return `${sign}$${(abs / 1_000).toFixed(0)}K`;
  return `${sign}$${abs.toFixed(0)}`;
}

function formatShares(value: number): string {
  return Math.round(value).toLocaleString("en-US");
}

function formatPct(fraction: number, digits = 2): string {
  return `${(fraction * 100).toFixed(digits)}%`;
}

/** Percentage points, for the "founders lose 32 points, not 20" sentence. */
function points(fraction: number): string {
  return `${(fraction * 100).toFixed(1)}`;
}

const DEFAULT_TEXT: Record<FieldKey, string> = {
  pre_money_valuation: String(WORKED_EXAMPLE.pre_money_valuation),
  raise_amount: String(WORKED_EXAMPLE.raise_amount),
  founder_shares: String(WORKED_EXAMPLE.founder_shares),
  existing_pool_shares: String(WORKED_EXAMPLE.existing_pool_shares),
  pool_target_pct: String(WORKED_EXAMPLE.pool_target_pct),
};

export default function DilutionPage() {
  const [text, setText] = useState<Record<FieldKey, string>>(DEFAULT_TEXT);

  const set = (key: FieldKey, value: string) => setText((prev) => ({ ...prev, [key]: value }));

  const result = useMemo(
    () =>
      computeDilution({
        pre_money_valuation: toNumber(text.pre_money_valuation),
        raise_amount: toNumber(text.raise_amount),
        founder_shares: toNumber(text.founder_shares),
        existing_pool_shares: toNumber(text.existing_pool_shares),
        pool_target_pct: toNumber(text.pool_target_pct),
      }),
    [text],
  );

  const shares = result.shares;
  const hasModel = result.founderPct !== null && result.investorPct !== null;
  useCalculatorUsed("dilution", JSON.stringify(text) !== JSON.stringify(DEFAULT_TEXT), hasModel, text);

  useSEO({
    ...TOOL_PAGE_META["/tools/dilution"],
    path: "/tools/dilution",
    jsonLd: [
      {
        "@context": "https://schema.org",
        "@type": "WebApplication",
        name: "Dilution Calculator",
        url: "https://founderconsole.ai/tools/dilution",
        applicationCategory: "BusinessApplication",
        operatingSystem: "Web",
        offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
        description:
          "Free startup dilution calculator. Models the option pool shuffle, so the founder, investor and option pool percentages all come out of one exact share count.",
        creator: {
          "@type": "Organization",
          name: "FounderConsole",
          url: "https://founderconsole.ai",
        },
      },
    ],
  });

  return (
    <MarketingLayout>
      <section className="border-b">
        <div className="mx-auto max-w-6xl px-4 py-16 md:py-20">
          <div className="flex items-center gap-2 mb-4">
            <Badge variant="secondary" className="text-xs" data-testid="badge-free-tool">
              <Calculator className="mr-1 h-3 w-3" />
              Free Tool
            </Badge>
          </div>
          <h1
            className="text-3xl font-bold tracking-tight text-foreground md:text-4xl lg:text-5xl"
            data-testid="text-calculator-title"
          >
            Dilution Calculator
          </h1>
          <p
            className="mt-3 max-w-2xl text-lg text-muted-foreground"
            data-testid="text-calculator-subtitle"
          >
            Enter one round and see exactly who owns what afterwards. Most calculators show
            the investor's share and stop. The number that actually costs you is your own,
            and it is smaller than the simple formula suggests — because the option pool
            comes out of your side, not theirs.
          </p>
        </div>
      </section>

      <section className="border-b">
        <div className="mx-auto max-w-6xl px-4 py-12">
          <div className="grid gap-8 lg:grid-cols-5">
            <div className="lg:col-span-2 space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Percent className="h-4 w-4 text-primary" />
                    One round
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {FIELDS.map((field) => (
                    <div key={field.key} className="space-y-1.5">
                      <div className="flex items-baseline justify-between gap-2">
                        <Label htmlFor={field.testId}>{field.label}</Label>
                        <span className="text-xs text-muted-foreground">{field.unit}</span>
                      </div>
                      <Input
                        id={field.testId}
                        inputMode="decimal"
                        value={text[field.key]}
                        onChange={(e) => set(field.key, e.target.value)}
                        data-testid={field.testId}
                        aria-describedby={field.help ? `${field.testId}-help` : undefined}
                      />
                      {field.help && (
                        <p
                          id={`${field.testId}-help`}
                          className="text-xs text-muted-foreground leading-relaxed"
                        >
                          {field.help}
                        </p>
                      )}
                      {field.choice && (
                        <p className="text-xs text-muted-foreground leading-relaxed border-l-2 border-primary/40 pl-2">
                          {field.choice}
                        </p>
                      )}
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>

            <div className="lg:col-span-3 space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Who owns what after the round</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {result.outcome === "invalid" && (
                    <p className="text-sm text-destructive" data-testid="text-dil-invalid">
                      {result.reason}
                    </p>
                  )}

                  {result.outcome === "unreachable" && (
                    <div className="space-y-2" data-testid="text-dil-unreachable">
                      <p className="flex items-start gap-2 text-sm text-amber-600 dark:text-amber-500">
                        <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
                        {result.reason}
                      </p>
                      {result.notes.map((note) => (
                        <p key={note} className="text-xs text-muted-foreground leading-relaxed">
                          {note}
                        </p>
                      ))}
                    </div>
                  )}

                  {hasModel && (
                    <>
                      <div className="grid gap-4 sm:grid-cols-3">
                        <div>
                          <p className="text-xs text-muted-foreground">Founders after</p>
                          <p
                            className="text-3xl font-bold tracking-tight text-foreground"
                            data-testid="text-dil-founder-pct"
                          >
                            {formatPct(result.founderPct as number)}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground">Investor</p>
                          <p
                            className="text-3xl font-bold tracking-tight text-foreground"
                            data-testid="text-dil-investor-pct"
                          >
                            {formatPct(result.investorPct as number)}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground">Option pool</p>
                          <p
                            className="text-3xl font-bold tracking-tight text-foreground"
                            data-testid="text-dil-pool-pct"
                          >
                            {formatPct(result.poolPct as number)}
                          </p>
                        </div>
                      </div>

                      <p
                        className="rounded-lg border border-primary/30 bg-primary/5 p-3 text-sm leading-relaxed"
                        data-testid="text-dil-headline"
                      >
                        A simple calculator would tell you the raise costs founders{" "}
                        <span className="font-medium text-foreground">
                          {points(result.simpleInvestorPct)} points
                        </span>{" "}
                        — that is just the investor's{" "}
                        {formatPct(result.investorPct as number)}. You
                        actually give up{" "}
                        <span className="font-medium text-foreground">
                          {points(1 - (result.founderPct as number))} points
                        </span>
                        , because the option pool is carved out of your side of the cap table
                        before the money lands.
                      </p>

                      {shares && (
                        <dl className="grid grid-cols-2 gap-3 pt-2 text-sm">
                          <div>
                            <dt className="text-muted-foreground">Price per share</dt>
                            <dd className="font-medium" data-testid="text-dil-price">
                              ${shares.pricePerShare.toFixed(2)}
                            </dd>
                          </div>
                          <div>
                            <dt className="text-muted-foreground">New pool shares</dt>
                            <dd className="font-medium" data-testid="text-dil-new-pool-shares">
                              {formatShares(shares.newPoolShares)}
                            </dd>
                          </div>
                          <div>
                            <dt className="text-muted-foreground">Shares the investor buys</dt>
                            <dd className="font-medium" data-testid="text-dil-investor-shares">
                              {formatShares(shares.investorShares)}
                            </dd>
                          </div>
                          <div>
                            <dt className="text-muted-foreground">Shares after the round</dt>
                            <dd className="font-medium" data-testid="text-dil-post-shares">
                              {formatShares(shares.postMoneyTotal)}
                            </dd>
                          </div>
                        </dl>
                      )}

                      {result.notes.map((note) => (
                        <p
                          key={note}
                          className="flex items-start gap-2 text-xs text-muted-foreground leading-relaxed"
                          data-testid="text-dil-note"
                        >
                          <Info className="h-3.5 w-3.5 mt-0.5 shrink-0" />
                          {note}
                        </p>
                      ))}
                    </>
                  )}

                </CardContent>
              </Card>

              <CalculatorEmailOptIn
                source="dilution"
                sourcePage="/tools/dilution"
                plan="dilution"
                resultByEmail={false}
                visible={result.outcome !== "invalid"}
                notes={`Dilution ${result.outcome}. Founder ${result.founderPct === null ? "n/a" : formatPct(result.founderPct)}, investor ${result.investorPct === null ? "n/a" : formatPct(result.investorPct)}.`}
              />

              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <PieChart className="h-4 w-4 text-primary" />
                    What this tool chose, and what is not a choice
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-sm text-muted-foreground leading-relaxed">
                  <p>
                    <span className="font-medium text-foreground">Textbook:</span> the
                    investor's share is the amount raised divided by the post-money valuation,
                    and post-money is pre-money plus the raise. That is arithmetic, not a
                    choice — and it is why the investor's percentage here does not move when
                    you change the pool target.
                  </p>
                  <p>
                    <span className="font-medium text-foreground">Chosen:</span> the option
                    pool top-up is created before the investment, so it dilutes existing
                    holders and never the new investor. This is standard US term-sheet practice
                    — the option pool shuffle — and it is the reason your own number is worse
                    than the simple formula suggests.
                  </p>
                  <p>
                    <span className="font-medium text-foreground">Chosen:</span> the pool
                    target is a percentage of post-money and the top-up never shrinks. If your
                    pool is already above target this round creates no new pool shares and the
                    page says so, rather than clawing options back.
                  </p>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </section>

      <section className="border-b">
        <div className="mx-auto max-w-6xl px-4 py-12 text-center">
          <div className="rounded-xl border bg-card/50 p-8 max-w-2xl mx-auto">
            <h3 className="text-xl font-semibold text-foreground" data-testid="text-cta-heading">
              See your whole cap table, not one round
            </h3>
            <p className="mt-2 text-sm text-muted-foreground max-w-lg mx-auto">
              This calculator models a single round. FounderConsole keeps the real cap table —
              every round, every grant, every SAFE — and shows what the next one does to your
              ownership before you sign it.
            </p>
            <Button asChild className="mt-4" data-testid="button-cta-connect">
              <Link
                href="/signup"
                onClick={() => trackFunnel("cta_click", { location: "dilution" })}
              >
                Connect Your Real Data
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </section>

      <section>
        <div className="mx-auto max-w-4xl px-4 py-16 md:py-20">
          <article className="prose prose-sm dark:prose-invert max-w-none">
            <h2 className="text-2xl font-bold text-foreground mb-4" data-testid="text-seo-heading-1">
              How startup dilution actually works
            </h2>
            <p className="text-muted-foreground leading-relaxed mb-4">
              Dilution is the share of the company you no longer own after a round. The
              investor's slice is easy: the amount raised divided by the post-money valuation.
              Raise $2M at an $8M pre-money and the post-money is $10M, so the investor owns
              20% and your slice of the old total falls by 20%. That part is arithmetic and
              every calculator agrees on it.
            </p>
            <p className="text-muted-foreground leading-relaxed mb-4">
              The part they disagree on is the option pool. Investors almost always require
              the company to leave the round with an unissued option pool already in place —
              typically 10% to 15% of post-money — to cover hiring until the next raise. That
              pool is created <em>before</em> the investment is priced, which means the shares
              are carved out of the existing holders. You pay for it. The investor's 20% is
              unaffected.
            </p>

            <h3 className="text-xl font-semibold text-foreground mt-8 mb-3">
              The option pool shuffle, in one example
            </h3>
            <p className="text-muted-foreground leading-relaxed mb-4">
              Take 8,000,000 founder shares and a 1,000,000-share option pool, a $8M pre-money
              valuation, a $2M raise, and a 12% post-money pool target. The round issues
              411,765 new pool shares before the investment, and the investor buys 2,352,941
              shares at the resulting price. The investor still owns exactly 20%. But the
              founders finish at <strong className="font-medium text-foreground">68%</strong>,
              not the 71.1% the simple formula implies — a 32-point loss, not 20. Twelve of
              those points went to the pool, and they came out of the founders' column.
            </p>
            <p className="text-muted-foreground leading-relaxed mb-4">
              That gap is the whole reason this page exists. A calculator that shows only the
              investor's share understates founder dilution by 60% in this example.
            </p>

            <h3 className="text-xl font-semibold text-foreground mt-8 mb-3">
              When the arithmetic has no answer
            </h3>
            <p className="text-muted-foreground leading-relaxed mb-4">
              A pool target is not always achievable. If a round adds 25% to the share count,
              there is no share count that leaves a 90% post-money pool behind — the algebra
              has no solution. This calculator says so plainly instead of printing a negative
              number of shares. The same is true of a pool that is already above target: the
              round creates no new pool shares, and the page says that rather than pretending
              options were cancelled.
            </p>

            <h3 className="text-xl font-semibold text-foreground mt-8 mb-3">
              Dilution compounds across rounds
            </h3>
            <p className="text-muted-foreground leading-relaxed mb-4">
              One round is rarely the problem; the sequence is. At the 2025 median round sizes,
              a seed round, a Series A and a Series B leave pre-seed holders with{" "}
              {(CUMULATIVE_KEEP_2025 * 100).toFixed(1)}% of the company they started with —
              cumulative dilution of {(100 - CUMULATIVE_KEEP_2025 * 100).toFixed(1)}%, from
              three rounds that each looked survivable on its own. That is why the tool models
              one round at a time and why the number to watch is the one you end up with, not
              the one this round costs.
            </p>

            <p className="text-xs text-muted-foreground leading-relaxed mt-8">
              Formulas on this page are transcribed from the Quant lane's derivation in{" "}
              <code>hive/reports/quant-forge-tools-maths.md</code>, which labels each formula
              textbook or chosen and states the reason for each choice. The multi-round figure
              is that file's cumulative-keep calculation over the medians in{" "}
              <code>hive/reports/quant-benchmarks.md</code>, Table 6. Every number this page
              computes is pinned by a test to that file's worked example.
            </p>
          </article>
        </div>
      </section>
    </MarketingLayout>
  );
}
