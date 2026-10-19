import { useMemo, useState } from "react";
import { Link } from "wouter";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
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
  TrendingDown,
  AlertTriangle,
  Check,
  Info,
} from "lucide-react";
import {
  bandFor,
  computeBurnMultiple,
  WORKED_EXAMPLE,
  type BurnMultipleInputs,
} from "@/lib/tools/burnMultiple";

/**
 * HAG-163, tool 1 of 3: /tools/burn-multiple.
 *
 * The maths is in `client/src/lib/tools/burnMultiple.ts` and is transcribed from
 * `hive/reports/quant-forge-tools-maths.md` (Quant lane, HAG-172) rather than
 * invented here. That module is the only place a formula lives, so the page and
 * its test cannot disagree about one.
 *
 * The fields hold TEXT, not numbers. `Number("")` is 0, so a field bound
 * directly to a number snaps back to "0" the moment a visitor clears it — the
 * defect fixed on /tools/runway-calculator. Parsing on read avoids it here too.
 */

type FieldKey = keyof Omit<BurnMultipleInputs, "starting_arr" | "ending_arr">;

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
    key: "new_arr",
    label: "New ARR won",
    unit: "USD in the period",
    help: "ARR from customers who were not customers before.",
    testId: "input-bm-new-arr",
  },
  {
    key: "expansion_arr",
    label: "Expansion ARR",
    unit: "USD in the period",
    help: "ARR added by customers you already had — upgrades, seats, usage.",
    testId: "input-bm-expansion-arr",
  },
  {
    key: "churned_arr",
    label: "Churned ARR",
    unit: "USD in the period",
    help: "ARR lost to customers who left.",
    testId: "input-bm-churned-arr",
  },
  {
    key: "contraction_arr",
    label: "Contraction ARR",
    unit: "USD in the period",
    help: "ARR lost to downgrades from customers who stayed.",
    testId: "input-bm-contraction-arr",
  },
  {
    key: "cash_out",
    label: "Cash out",
    unit: "USD in the period",
    help: "Operating cash spent: payroll, tools, ads, rent. Not a bank-balance drop and not a financing inflow.",
    testId: "input-bm-cash-out",
  },
  {
    key: "cash_in",
    label: "Cash in",
    unit: "USD in the period",
    help: "Cash actually collected from customers in the same window.",
    testId: "input-bm-cash-in",
  },
  {
    key: "period_months",
    label: "Window",
    unit: "whole months",
    help: "The trailing 3 complete months are the default. One month of ARR movement is noise.",
    choice:
      "Chosen: net burn is cash out minus cash in, not gross burn — a dollar of revenue banked is a dollar not burned.",
    testId: "input-bm-period-months",
  },
];

function toNumber(raw: string): number {
  const trimmed = raw.trim().replace(/[$,\s]/g, "");
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

const DEFAULT_TEXT: Record<FieldKey, string> = {
  new_arr: String(WORKED_EXAMPLE.new_arr),
  expansion_arr: String(WORKED_EXAMPLE.expansion_arr),
  churned_arr: String(WORKED_EXAMPLE.churned_arr),
  contraction_arr: String(WORKED_EXAMPLE.contraction_arr),
  cash_out: String(WORKED_EXAMPLE.cash_out),
  cash_in: String(WORKED_EXAMPLE.cash_in),
  period_months: String(WORKED_EXAMPLE.period_months),
};

export default function BurnMultiplePage() {
  const [text, setText] = useState<Record<FieldKey, string>>(DEFAULT_TEXT);
  const [arrText, setArrText] = useState({ starting_arr: "1200000", ending_arr: "1350000" });

  const set = (key: FieldKey, value: string) => setText((prev) => ({ ...prev, [key]: value }));

  const results = useMemo(() => {
    const inputs: BurnMultipleInputs = {
      new_arr: toNumber(text.new_arr),
      expansion_arr: toNumber(text.expansion_arr),
      churned_arr: toNumber(text.churned_arr),
      contraction_arr: toNumber(text.contraction_arr),
      cash_out: toNumber(text.cash_out),
      cash_in: toNumber(text.cash_in),
      period_months: toNumber(text.period_months),
      starting_arr: arrText.starting_arr.trim() === "" ? null : toNumber(arrText.starting_arr),
      ending_arr: arrText.ending_arr.trim() === "" ? null : toNumber(arrText.ending_arr),
    };
    return { inputs, result: computeBurnMultiple(inputs) };
  }, [text, arrText]);

  const { result } = results;
  const band = result.multiple === null ? null : bandFor(result.multiple);
  useCalculatorUsed(
    "burn-multiple",
    JSON.stringify(text) !== JSON.stringify(DEFAULT_TEXT) ||
      arrText.starting_arr !== "1200000" ||
      arrText.ending_arr !== "1350000",
    result.multiple !== null,
    [text, arrText],
  );

  useSEO({
    ...TOOL_PAGE_META["/tools/burn-multiple"],
    path: "/tools/burn-multiple",
    jsonLd: [
      {
        "@context": "https://schema.org",
        "@type": "WebApplication",
        name: "Burn Multiple Calculator",
        url: "https://founderconsole.ai/tools/burn-multiple",
        applicationCategory: "BusinessApplication",
        operatingSystem: "Web",
        offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
        description:
          "Free burn multiple calculator for SaaS founders. Net burn divided by net new ARR, with the net-burn definition, the window, and the ARR reconciliation check all stated on the page.",
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
            Burn Multiple Calculator
          </h1>
          <p
            className="mt-3 max-w-2xl text-lg text-muted-foreground"
            data-testid="text-calculator-subtitle"
          >
            Burn multiple is the dollars of net burn it took to buy one dollar of net new
            ARR. Lower is better. Enter one window and see your multiple, whether your ARR
            actually reconciles, and how the number reads against the published benchmarks.
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
                    <TrendingDown className="h-4 w-4 text-primary" />
                    One window
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

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">ARR reconciliation (optional)</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Chosen: net new ARR must reconcile to the ARR change —
                    starting ARR plus net new ARR must equal ending ARR. If it does not, your
                    inputs are using two different definitions of ARR, and the ratio below
                    would be measuring the difference rather than your efficiency.
                  </p>
                  <div className="flex items-baseline justify-between gap-2">
                    <Label htmlFor="input-bm-starting-arr">Starting ARR</Label>
                    <span className="text-xs text-muted-foreground">USD</span>
                  </div>
                  <Input
                    id="input-bm-starting-arr"
                    inputMode="decimal"
                    value={arrText.starting_arr}
                    onChange={(e) =>
                      setArrText((prev) => ({ ...prev, starting_arr: e.target.value }))
                    }
                    data-testid="input-bm-starting-arr"
                  />
                  <div className="flex items-baseline justify-between gap-2">
                    <Label htmlFor="input-bm-ending-arr">Ending ARR</Label>
                    <span className="text-xs text-muted-foreground">USD</span>
                  </div>
                  <Input
                    id="input-bm-ending-arr"
                    inputMode="decimal"
                    value={arrText.ending_arr}
                    onChange={(e) => setArrText((prev) => ({ ...prev, ending_arr: e.target.value }))}
                    data-testid="input-bm-ending-arr"
                  />
                </CardContent>
              </Card>
            </div>

            <div className="lg:col-span-3 space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Your burn multiple</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {result.outcome === "invalid" ? (
                    <p className="text-sm text-destructive" data-testid="text-bm-invalid">
                      {result.reason}
                    </p>
                  ) : (
                    <>
                      <div className="flex items-baseline gap-3">
                        <span
                          className="text-4xl font-bold tracking-tight text-foreground"
                          data-testid="text-bm-multiple"
                        >
                          {result.multiple === null ? "n/a" : `${result.multiple.toFixed(2)}x`}
                        </span>
                        {band && (
                          <Badge variant="outline" data-testid="text-bm-band">
                            {band.label}
                          </Badge>
                        )}
                      </div>

                      {result.reason && (
                        <p className="text-sm text-muted-foreground" data-testid="text-bm-reason">
                          {result.reason}
                        </p>
                      )}
                      {band && (
                        <p className="text-xs text-muted-foreground" data-testid="text-bm-band-source">
                          {band.detail}
                        </p>
                      )}

                      <dl className="grid grid-cols-2 gap-3 pt-2 text-sm">
                        <div>
                          <dt className="text-muted-foreground">Net new ARR</dt>
                          <dd className="font-medium" data-testid="text-bm-net-new-arr">
                            {formatCurrency(result.netNewArr)}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-muted-foreground">Net burn</dt>
                          <dd className="font-medium" data-testid="text-bm-net-burn">
                            {formatCurrency(result.netBurn)}
                          </dd>
                        </div>
                      </dl>

                      <p
                        className="text-xs text-muted-foreground leading-relaxed"
                        data-testid="text-bm-monthly-average"
                      >
                        Monthly-average variant: burn per month{" "}
                        {formatCurrency(result.monthlyAverage.netBurn)}, ARR per month{" "}
                        {formatCurrency(result.monthlyAverage.netNewArr)} — the same{" "}
                        {result.multiple === null ? "n/a" : `${result.multiple.toFixed(2)}x`}.
                        Dividing both sides by the same window length cannot change a ratio,
                        so{" "}
                        <strong className="font-medium text-foreground">
                          the window you pick does not move your score
                        </strong>
                        .
                      </p>
                    </>
                  )}

                  <div className="pt-2 border-t">
                    {result.reconciliation.state === "pass" && (
                      <p
                        className="flex items-start gap-2 text-sm text-foreground"
                        data-testid="text-bm-reconcile"
                      >
                        <Check className="h-4 w-4 mt-0.5 shrink-0 text-emerald-500" />
                        ARR reconciles: starting ARR plus net new ARR equals ending ARR.
                      </p>
                    )}
                    {result.reconciliation.state === "fail" && (
                      <p
                        className="flex items-start gap-2 text-sm text-amber-600 dark:text-amber-500"
                        data-testid="text-bm-reconcile"
                      >
                        <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
                        <span>
                          ARR does not reconcile. Your inputs imply an ending ARR of{" "}
                          {formatCurrency(result.reconciliation.expectedEndingArr)}, which is{" "}
                          {formatCurrency(Math.abs(result.reconciliation.difference))}{" "}
                          {result.reconciliation.difference > 0 ? "below" : "above"} the ending
                          ARR you entered. Check that both figures use the same definition of
                          ARR before trusting the ratio above.
                        </span>
                      </p>
                    )}
                    {result.reconciliation.state === "not_run" && (
                      <p
                        className="flex items-start gap-2 text-sm text-muted-foreground"
                        data-testid="text-bm-reconcile"
                      >
                        <Info className="h-4 w-4 mt-0.5 shrink-0" />
                        Enter a starting and ending ARR to run the reconciliation check.
                      </p>
                    )}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <Info className="h-4 w-4 text-primary" />
                    What this tool chose, and what is not a choice
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-sm text-muted-foreground leading-relaxed">
                  <p>
                    <span className="font-medium text-foreground">Textbook:</span> net new ARR
                    is new plus expansion minus churned minus contraction — net, not gross new
                    ARR. Burn multiple is net burn divided by net new ARR.
                  </p>
                  <p>
                    <span className="font-medium text-foreground">Chosen:</span> the default
                    window is the trailing 3 complete months, because one month of ARR movement
                    is noise and a single good month can make a struggling company look
                    efficient.
                  </p>
                  <p>
                    <span className="font-medium text-foreground">Chosen:</span> the pool of
                    inputs is validated as non-negative and the window as at least one whole
                    month; every other degenerate case below reads as{" "}
                    <span className="font-medium text-foreground">n/a</span> with its reason,
                    never as Infinity and never as a negative score presented as an
                    achievement.
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
              Get more accurate projections with FounderConsole
            </h3>
            <p className="mt-2 text-sm text-muted-foreground max-w-lg mx-auto">
              This calculator takes one window you type in. FounderConsole connects your real
              financial data and runs Monte Carlo simulations with P10/P50/P90 confidence
              bands — so you know your true runway probability.
            </p>
            <Button asChild className="mt-4" data-testid="button-cta-connect">
              <Link
                href="/signup"
                onClick={() => trackFunnel("cta_click", { location: "burn-multiple" })}
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
              What is burn multiple?
            </h2>
            <p className="text-muted-foreground leading-relaxed mb-4">
              Burn multiple is the number of dollars of net burn it costs to buy one dollar of
              net new ARR in a period. A burn multiple of 2.0x means you spent two dollars of
              cash to add one dollar of recurring revenue. It was popularised as the efficiency
              metric for SaaS because it collapses growth and spend into a single number: rapid
              growth funded by a furnace scores badly, and slow growth bought cheaply scores
              well.
            </p>
            <p className="text-muted-foreground leading-relaxed mb-4">
              The formula is net burn divided by net new ARR. Net new ARR is new ARR plus
              expansion ARR, minus churned ARR, minus contraction ARR — the actual change in
              your recurring revenue, not the gross that marketing would like to quote. Net
              burn is cash out minus cash in over the same window.
            </p>

            <h3 className="text-xl font-semibold text-foreground mt-8 mb-3">
              The three mistakes this calculator is built to stop
            </h3>
            <p className="text-muted-foreground leading-relaxed mb-4">
              <strong className="font-medium text-foreground">Gross new ARR.</strong> Quoting
              new logos while ignoring churn and downgrades makes a leaking bucket look like a
              growing one. The reconciliation check above exists for this: if starting ARR plus
              net new ARR does not equal ending ARR, two different definitions of ARR are in
              play, and the ratio is measuring the difference between them.
            </p>
            <p className="text-muted-foreground leading-relaxed mb-4">
              <strong className="font-medium text-foreground">Gross burn.</strong> Payroll,
              ads and rent are only half the picture; a dollar of revenue in the bank is a
              dollar not burned. Gross burn makes a profitable-but-slow-paying company look
              like a furnace.
            </p>
            <p className="text-muted-foreground leading-relaxed mb-4">
              <strong className="font-medium text-foreground">A one-month window.</strong> One
              month of ARR movement is noise. A single good month can flatter a struggling
              company, and a single bad one can bury a healthy one — which is why the default
              here is the trailing three complete months.
            </p>

            <h3 className="text-xl font-semibold text-foreground mt-8 mb-3">
              What counts as a good burn multiple?
            </h3>
            <p className="text-muted-foreground leading-relaxed mb-4">
              Scale Venture Partners put the 2024 median at 2.3x, down from 3.3x in 2023, and
              described a 2025 outlook of roughly 1.0x — trading a dollar of burn for a dollar
              of ARR. Benchmarkit's 2025 target for a company at $25M–$50M ARR is under 1.0x.
              Both figures are published without a sample size, so read them as directional
              rather than as a measured median of a stated population.
            </p>
            <p className="text-muted-foreground leading-relaxed mb-4">
              Sources:{" "}
              <a
                className="text-primary underline underline-offset-2"
                href="https://www.scalevp.com/blog/2025-whisper-numbers-the-era-of-efficiency-is-here"
                rel="noopener noreferrer"
                target="_blank"
              >
                Scale Venture Partners, 2025 Whisper Numbers
              </a>{" "}
              and{" "}
              <a
                className="text-primary underline underline-offset-2"
                href="https://www.benchmarkit.ai/2025benchmarks"
                rel="noopener noreferrer"
                target="_blank"
              >
                Benchmarkit, 2025 B2B SaaS Performance Metrics
              </a>
              .
            </p>

            <h3 className="text-xl font-semibold text-foreground mt-8 mb-3">
              How this calculator compares to a runway projection
            </h3>
            <p className="text-muted-foreground leading-relaxed mb-4">
              Burn multiple is an efficiency ratio for a window that has already happened. It
              says nothing about how long your cash lasts, and a good multiple does not mean
              you have time. If you want the other number, start with the{" "}
              <Link
                className="text-primary underline underline-offset-2"
                href="/tools/runway-calculator"
              >
                free startup runway calculator
              </Link>
              , and read the{" "}
              <Link className="text-primary underline underline-offset-2" href="/blog">
                blog
              </Link>{" "}
              for how the two fit together.
            </p>

            <p className="text-xs text-muted-foreground leading-relaxed mt-8">
              Formulas on this page are transcribed from the Quant lane's derivation in{" "}
              <code>hive/reports/quant-forge-tools-maths.md</code>, which labels each formula
              textbook or chosen and states the reason for each choice. Benchmark figures are
              from <code>hive/reports/quant-benchmarks.md</code>, Table 1. Every number this
              page computes is pinned by a test to that file's worked example.
            </p>
          </article>
        </div>
      </section>
    </MarketingLayout>
  );
}
