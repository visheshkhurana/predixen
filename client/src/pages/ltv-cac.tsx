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
import { useCalculatorUsedOnce } from "@/hooks/use-calculator-used";
import {
  ArrowRight,
  Calculator,
  TrendingUp,
  AlertTriangle,
  Info,
  Scale,
} from "lucide-react";
import {
  CHURN_FLOOR_PCT,
  CHURN_TRAP,
  CHURN_TRAP_LTV_COMPOUNDED,
  CHURN_TRAP_LTV_MONTHLY_FORM,
  CHURN_TRAP_UNDERSTATEMENT_PCT,
  SKOK_BENCHMARK,
  computeLtvCac,
  WORKED_EXAMPLE,
  type LtvCacInputs,
} from "@/lib/tools/ltvCac";

/**
 * HAG-163, tool 3 of 3: /tools/ltv-cac.
 *
 * The maths is in `client/src/lib/tools/ltvCac.ts` and is transcribed from
 * `hive/reports/quant-forge-tools-maths.md` (Quant lane, HAG-172) rather than invented
 * here. The thresholds it grades against come from `hive/reports/quant-benchmarks.md`,
 * Table 5, and are named and dated on the page — that file is explicit that a tool which
 * grades a founder must say which benchmark it used and when it was written.
 *
 * The fields hold TEXT, not numbers. `Number("")` is 0, so a field bound directly to a
 * number snaps back to "0" the moment a visitor clears it — the defect fixed on
 * /tools/runway-calculator. Parsing on read avoids it here too.
 */

type FieldKey = keyof LtvCacInputs;

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
    key: "arpa_monthly",
    label: "Revenue per customer",
    unit: "USD / month",
    help: "Average revenue per account, per month. Use the same month for every field below.",
    testId: "input-ltv-arpa",
  },
  {
    key: "gross_margin_pct",
    label: "Gross margin",
    unit: "%",
    help: "Revenue less the cost of serving that customer, as a share of revenue.",
    testId: "input-ltv-gross-margin",
  },
  {
    key: "monthly_churn_pct",
    label: "Monthly churn",
    unit: "% per month",
    help: "The share of customers you lose each month. Do not convert this to a yearly figure — the tool does that for you, and the two are not the same number.",
    choice: `Chosen: churn is entered in one unit only — per month — and is floored at ${CHURN_FLOOR_PCT}% per month. A churn of zero would make LTV infinite, and an infinite LTV:CAC would print the best possible score for a business that simply has not been running long enough to lose anyone. The floor is applied and labelled, never hidden.`,
    testId: "input-ltv-churn",
  },
  {
    key: "sm_spend",
    label: "Sales & marketing spend",
    unit: "USD, in the period",
    help: "Fully loaded: salaries, tools, agency fees and ad spend together. Not ad spend alone.",
    choice:
      "Chosen: CAC is fully loaded sales and marketing divided by the customers won in the same period. It is the only version that stops a company grading itself on ad spend while ignoring the salaries that generated the pipeline.",
    testId: "input-ltv-sm-spend",
  },
  {
    key: "new_customers",
    label: "New customers won",
    unit: "count, same period",
    help: "Customers won in the same period as the spend above.",
    testId: "input-ltv-new-customers",
  },
];

function toNumber(raw: string): number {
  const trimmed = raw.trim().replace(/[$,\s%]/g, "");
  if (trimmed === "") return 0;
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : Number.NaN;
}

/** Exact dollars, not "$20K": the worked example's headline is $20,000 and rounding it hides the point. */
function formatCurrency(value: number): string {
  return `$${Math.round(value).toLocaleString("en-US")}`;
}

function formatPct(value: number, digits = 2): string {
  return `${value.toFixed(digits)}%`;
}

const DEFAULT_TEXT: Record<FieldKey, string> = {
  arpa_monthly: String(WORKED_EXAMPLE.arpa_monthly),
  gross_margin_pct: String(WORKED_EXAMPLE.gross_margin_pct),
  monthly_churn_pct: String(WORKED_EXAMPLE.monthly_churn_pct),
  sm_spend: String(WORKED_EXAMPLE.sm_spend),
  new_customers: String(WORKED_EXAMPLE.new_customers),
};

export default function LtvCacPage() {
  const [text, setText] = useState<Record<FieldKey, string>>(DEFAULT_TEXT);

  const set = (key: FieldKey, value: string) => setText((prev) => ({ ...prev, [key]: value }));

  const result = useMemo(
    () =>
      computeLtvCac({
        arpa_monthly: toNumber(text.arpa_monthly),
        gross_margin_pct: toNumber(text.gross_margin_pct),
        monthly_churn_pct: toNumber(text.monthly_churn_pct),
        sm_spend: toNumber(text.sm_spend),
        new_customers: toNumber(text.new_customers),
      }),
    [text],
  );

  const grade = result.grade;
  const onCalculatorInput = useCalculatorUsedOnce("ltv-cac");

  useSEO({
    ...TOOL_PAGE_META["/tools/ltv-cac"],
    path: "/tools/ltv-cac",
    jsonLd: [
      {
        "@context": "https://schema.org",
        "@type": "WebApplication",
        name: "LTV:CAC Calculator",
        url: "https://founderconsole.ai/tools/ltv-cac",
        applicationCategory: "BusinessApplication",
        operatingSystem: "Web",
        offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
        description:
          "Free LTV:CAC calculator with gross-profit LTV, fully loaded CAC and CAC payback months, graded separately against a named benchmark.",
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
            LTV:CAC Calculator
          </h1>
          <p
            className="mt-3 max-w-2xl text-lg text-muted-foreground"
            data-testid="text-calculator-subtitle"
          >
            Two numbers, graded separately — because a healthy LTV:CAC with a bad payback is
            the most common way a growing company runs out of cash. Most calculators give you
            the ratio and stop there.
          </p>
        </div>
      </section>

      <section className="border-b">
        <div className="mx-auto max-w-6xl px-4 py-12">
          <div className="grid gap-8 lg:grid-cols-5">
            <div className="lg:col-span-2 space-y-6" onInput={onCalculatorInput}>
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Scale className="h-4 w-4 text-primary" />
                    One period
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
                  <CardTitle className="text-lg">What one customer is worth, and what one costs</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {result.outcome === "invalid" && (
                    <p className="text-sm text-destructive" data-testid="text-ltv-invalid">
                      {result.reason}
                    </p>
                  )}

                  {result.outcome !== "invalid" && result.ltv !== null && (
                    <>
                      <div className="grid gap-4 sm:grid-cols-3">
                        <div>
                          <p className="text-xs text-muted-foreground">LTV</p>
                          <p
                            className="text-3xl font-bold tracking-tight text-foreground"
                            data-testid="text-ltv-ltv"
                          >
                            {formatCurrency(result.ltv)}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground">CAC</p>
                          <p
                            className="text-3xl font-bold tracking-tight text-foreground"
                            data-testid="text-ltv-cac"
                          >
                            {result.cac === null ? (
                              <span className="text-xl text-muted-foreground">n/a</span>
                            ) : (
                              formatCurrency(result.cac)
                            )}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground">LTV:CAC</p>
                          <p
                            className="text-3xl font-bold tracking-tight text-foreground"
                            data-testid="text-ltv-ratio"
                          >
                            {result.ratio === null ? (
                              <span className="text-xl text-muted-foreground">n/a</span>
                            ) : (
                              `${result.ratio.toFixed(2)}x`
                            )}
                          </p>
                        </div>
                      </div>

                      {result.cacUnavailableReason && (
                        <p
                          className="flex items-start gap-2 text-sm text-amber-600 dark:text-amber-500"
                          data-testid="text-ltv-cac-na"
                        >
                          <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
                          {result.cacUnavailableReason}
                        </p>
                      )}

                      <div className="rounded-lg border p-3 text-sm">
                        <p className="text-muted-foreground">
                          CAC payback{" "}
                          <span className="font-medium text-foreground" data-testid="text-ltv-payback">
                            {result.paybackMonths === null
                              ? "never at this margin"
                              : `${result.paybackMonths.toFixed(1)} months`}
                          </span>
                        </p>
                        {grade && (
                          <div className="mt-2 space-y-1">
                            <p className="text-xs" data-testid="text-ltv-grade-ratio">
                              <span className="font-medium text-foreground">Ratio:</span>{" "}
                              {grade.ratioVerdict}
                            </p>
                            <p className="text-xs" data-testid="text-ltv-grade-payback">
                              <span className="font-medium text-foreground">Payback:</span>{" "}
                              {grade.paybackVerdict}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              Graded against {SKOK_BENCHMARK}.
                            </p>
                          </div>
                        )}
                      </div>

                      {grade?.cashFlowTrap && (
                        <p
                          className="rounded-lg border border-amber-500/40 bg-amber-500/5 p-3 text-sm leading-relaxed"
                          data-testid="text-ltv-trap"
                        >
                          <span className="font-medium text-foreground">
                            The cash-flow trap:
                          </span>{" "}
                          your ratio clears the benchmark and your payback does not. The ratio
                          is a lifetime figure; the payback is what your bank account feels.
                          You can be profitable on paper and still run out of cash growing
                          this way.
                        </p>
                      )}

                      <p className="text-xs text-muted-foreground" data-testid="text-ltv-churn-annual">
                        The churn you entered compounds to{" "}
                        <span className="font-medium text-foreground">
                          {formatPct(result.annualChurnUsedPct)}
                        </span>{" "}
                        a year — not {formatPct(result.monthlyChurnUsedPct * 12)}, which is what
                        multiplying the monthly figure by twelve would give. Carry the
                        compounded number into a spreadsheet, never the multiplied one.
                      </p>

                      {result.notes.map((note) => (
                        <p
                          key={note}
                          className="flex items-start gap-2 text-xs text-muted-foreground leading-relaxed"
                          data-testid="text-ltv-note"
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
                source="ltv-cac"
                sourcePage="/tools/ltv-cac"
                plan="ltv-cac"
                resultByEmail={false}
                visible={result.outcome !== "invalid" && result.ltv !== null}
                notes={`LTV ${result.ltv === null ? "n/a" : formatCurrency(result.ltv)}, CAC ${result.cac === null ? "n/a" : formatCurrency(result.cac)}, ratio ${result.ratio === null ? "n/a" : `${result.ratio.toFixed(2)}x`}.`}
              />

              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <TrendingUp className="h-4 w-4 text-primary" />
                    What this tool chose, and what is not a choice
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-sm text-muted-foreground leading-relaxed">
                  <p>
                    <span className="font-medium text-foreground">Textbook:</span> the ratio is
                    LTV divided by CAC, and payback is CAC divided by your gross profit per
                    customer per month. Both are arithmetic.
                  </p>
                  <p>
                    <span className="font-medium text-foreground">Chosen:</span> LTV here is{" "}
                    <span className="font-medium text-foreground">gross-profit based</span> —
                    revenue per customer times gross margin, divided by monthly churn used as a
                    simple decay rate. Every free calculator and most founders already know this
                    form. The alternative, a discounted-cash-flow LTV, needs a discount rate and
                    a revenue-growth assumption this tool will not ask you for, and it gives a
                    different answer — so if you compare against another calculator, check which
                    form it used before you believe the difference.
                  </p>
                  <p>
                    <span className="font-medium text-foreground">Chosen:</span> CAC is{" "}
                    <span className="font-medium text-foreground">fully loaded</span>. Ad spend
                    alone is not CAC, and a tool that reports it as the default flatters every
                    company that pays salaries.
                  </p>
                  <p>
                    <span className="font-medium text-foreground">Chosen:</span> churn is floored
                    at {CHURN_FLOOR_PCT}% per month and the floor is labelled when it applies. A
                    churn of zero gives an infinite LTV and an infinitely good score, which is
                    what a company that has not been running long enough to lose anyone would
                    otherwise be told.
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
              See whether growth is actually paying for itself
            </h3>
            <p className="mt-2 text-sm text-muted-foreground max-w-lg mx-auto">
              This calculator works one period at a time from numbers you type. FounderConsole
              reads your real revenue, margin and spend, and shows the month your cash runs out
              while this ratio still looks healthy.
            </p>
            <Button asChild className="mt-4" data-testid="button-cta-connect">
              <Link
                href="/signup"
                onClick={() => trackFunnel("cta_click", { location: "ltv-cac" })}
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
              How to read your LTV:CAC
            </h2>
            <p className="text-muted-foreground leading-relaxed mb-4">
              LTV is what one customer is worth to you over their life. CAC is what you paid to
              win them. Divide one by the other and you have the ratio every investor asks
              about. The benchmark most quoted is David Skok&apos;s: above 3x, and{" "}
              <em>sometimes as high as 7 or 8</em>. Worked example: $500 a month per customer at
              an 80% gross margin and 2% monthly churn gives an LTV of $20,000. Winning 24
              customers on $120,000 of fully loaded sales and marketing gives a CAC of $5,000.
              The ratio is 4.00x, which clears the benchmark.
            </p>

            <h3 className="text-xl font-semibold text-foreground mt-8 mb-3">
              Why the ratio alone is not enough
            </h3>
            <p className="text-muted-foreground leading-relaxed mb-4">
              That same example takes <strong className="font-medium text-foreground">12.5
              months</strong> to recover the CAC. Skok calls the best businesses 5 to 7 months
              and profitability <em>anemic</em> once payback goes beyond 12. So this company has
              a good ratio and a weak payback at the same time — and that pair is not a
              contradiction, it is the cash-flow trap. The ratio is a lifetime figure. The
              payback is what your bank account feels. A company can grow profitably on paper
              and still run out of cash doing it, because every new customer costs money
              months before they return it.
            </p>
            <p className="text-muted-foreground leading-relaxed mb-4">
              That is why this tool grades the two numbers separately instead of scoring them
              together. A blended score would tell the company above that it is doing well.
            </p>

            <h3 className="text-xl font-semibold text-foreground mt-8 mb-3">
              The mistake that quietly understates your LTV
            </h3>
            <p className="text-muted-foreground leading-relaxed mb-4">
              Monthly churn is not twelve times monthly. At 2% a month, customers do not all
              leave by month twelve — the loss compounds, and the true annual churn is{" "}
              <strong className="font-medium text-foreground">21.53%</strong>, not 24%. The
              difference matters because LTV is inversely proportional to churn: entering 24%
              into an annual formula gives an LTV of{" "}
              {formatCurrency(CHURN_TRAP_LTV_MONTHLY_FORM)}, while the compounded rate gives{" "}
              {formatCurrency(CHURN_TRAP_LTV_COMPOUNDED)} — the naive route understates LTV by{" "}
              <strong className="font-medium text-foreground">
                {CHURN_TRAP_UNDERSTATEMENT_PCT.toFixed(1)}%
              </strong>
              . Worse, the naive answer is the <em>same number</em> the correct monthly formula
              produces, so the mistake is invisible unless you check which unit you are in.
              This tool takes churn per month only, prints the unit next to the field, and shows
              the compounded annual equivalent of whatever you entered — so the figure you carry
              into a spreadsheet is the right one. A monthly churn of {CHURN_TRAP.monthly_churn_pct}%
              is the example above.
            </p>

            <h3 className="text-xl font-semibold text-foreground mt-8 mb-3">
              When the answer is not a number
            </h3>
            <p className="text-muted-foreground leading-relaxed mb-4">
              Two real months have no CAC at all. Win no new customers and there is nothing to
              divide the spend by — the tool says <em>n/a — no new customers</em> rather than
              printing a CAC of zero, which would flatter a month in which nothing was won. Spend
              nothing and there is no measurable acquisition cost to report. A zero gross margin
              is a legitimate business — a reseller with no markup — and it gets a real answer:
              an LTV of zero, and a flat statement that no marketing spend can ever pay back,
              rather than a division by zero.
            </p>

            <p className="text-xs text-muted-foreground leading-relaxed mt-8">
              Formulas on this page are transcribed from the Quant lane&apos;s derivation in{" "}
              <code>hive/reports/quant-forge-tools-maths.md</code>, which labels each formula
              textbook or chosen and states the reason for each choice. The benchmark quoted is
              from <code>hive/reports/quant-benchmarks.md</code>, Table 5 —{" "}
              {SKOK_BENCHMARK}. That file records that the source page carries no clear
              publication date, and that Benchmarkit&apos;s 2025 median payback of about 12
              months was written a decade later and does not agree with it on what normal looks
              like; this tool grades against Skok&apos;s pair only, and says so, rather than
              blending two benchmarks. Every number this page computes is pinned by a test to
              that file&apos;s worked example.
            </p>
          </article>
        </div>
      </section>
    </MarketingLayout>
  );
}
