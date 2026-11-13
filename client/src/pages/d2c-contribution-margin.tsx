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
import { D2C_MARGIN_DEFINITIONS, D2C_MARGIN_FAQS } from "@/data/d2c-margin-content";
import { trackFunnel } from "@/lib/funnel";
import { useCalculatorUsed } from "@/hooks/use-calculator-used";
import { ArrowRight, Calculator, Info, ShoppingBag } from "lucide-react";
import {
  computeD2cMargin,
  D2C_WORKED_EXAMPLE,
  formatInr,
  type D2cMarginInputs,
} from "@/lib/tools/d2cMargin";

/**
 * /tools/d2c-contribution-margin — free CM1/CM2/CM3 calculator for Indian D2C
 * brands. Client-side only; nothing is sent anywhere. The maths lives in
 * `client/src/lib/tools/d2cMargin.ts` and is pinned by
 * `server/tests/d2c-margin.test.ts`.
 *
 * Fields hold TEXT, not numbers, for the same reason as the other calculators:
 * a field bound to a number snaps back to "0" when a visitor clears it.
 */

type FieldKey = keyof D2cMarginInputs;

interface FieldSpec {
  key: FieldKey;
  label: string;
  unit: string;
  help?: string;
}

const GROUPS: ReadonlyArray<{ title: string; fields: readonly FieldSpec[] }> = [
  {
    title: "Orders",
    fields: [
      { key: "aov", label: "Average order value", unit: "₹, ex-GST, after discounts" },
      { key: "orders", label: "Orders shipped", unit: "per month" },
      { key: "rtoPct", label: "RTO rate", unit: "% of shipped", help: "Orders that came back undelivered (return to origin)." },
      { key: "returnPct", label: "Customer returns", unit: "% of delivered", help: "Delivered orders the customer sent back for a refund." },
      { key: "codPct", label: "COD share", unit: "% of orders", help: "Orders paid cash on delivery." },
    ],
  },
  {
    title: "Variable costs",
    fields: [
      { key: "cogsPerOrder", label: "COGS per order", unit: "₹", help: "Landed product cost of one order." },
      { key: "packagingPerOrder", label: "Packaging per order", unit: "₹" },
      { key: "forwardShipping", label: "Forward shipping", unit: "₹ per shipped order" },
      { key: "reverseShipping", label: "Reverse shipping", unit: "₹ per RTO or return" },
      { key: "gatewayPct", label: "Payment gateway fee", unit: "% of prepaid value" },
      { key: "codFee", label: "COD fee", unit: "₹ per delivered COD order" },
    ],
  },
  {
    title: "Marketing",
    fields: [
      { key: "marketing", label: "Marketing spend", unit: "₹ per month", help: "All channels: Meta, Google, influencers, affiliates." },
    ],
  },
];

const DEFAULT_TEXT = Object.fromEntries(
  Object.entries(D2C_WORKED_EXAMPLE).map(([k, v]) => [k, String(v)]),
) as Record<FieldKey, string>;

function toNumber(raw: string): number {
  const trimmed = raw.trim().replace(/[₹,%\s]/g, "");
  if (trimmed === "") return 0;
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : Number.NaN;
}

const pct = (v: number | null) => (v === null ? "n/a" : `${v.toFixed(1)}%`);
const inrOrNa = (v: number | null) => (v === null ? "n/a" : formatInr(v));
const ratio = (v: number | null) => (v === null ? "n/a" : `${v.toFixed(2)}x`);

export default function D2cContributionMarginPage() {
  const [text, setText] = useState<Record<FieldKey, string>>(DEFAULT_TEXT);
  const set = (key: FieldKey, value: string) => setText((prev) => ({ ...prev, [key]: value }));

  const result = useMemo(() => {
    const inputs = Object.fromEntries(
      Object.entries(text).map(([k, v]) => [k, toNumber(v)]),
    ) as unknown as D2cMarginInputs;
    return computeD2cMargin(inputs);
  }, [text]);

  useCalculatorUsed(
    "d2c-contribution-margin",
    JSON.stringify(text) !== JSON.stringify(DEFAULT_TEXT),
    result.outcome === "ok",
    text,
  );

  useSEO({
    ...TOOL_PAGE_META["/tools/d2c-contribution-margin"],
    path: "/tools/d2c-contribution-margin",
    jsonLd: [
      {
        "@context": "https://schema.org",
        "@type": "WebApplication",
        name: "D2C Contribution Margin Calculator",
        url: "https://founderconsole.ai/tools/d2c-contribution-margin",
        applicationCategory: "BusinessApplication",
        operatingSystem: "Web",
        offers: { "@type": "Offer", price: "0", priceCurrency: "INR" },
        description:
          "Free CM1, CM2 and CM3 contribution margin calculator for Indian D2C brands, with RTO, COD, MER and break-even MER.",
        creator: { "@type": "Organization", name: "FounderConsole", url: "https://founderconsole.ai" },
      },
      {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        mainEntity: D2C_MARGIN_FAQS.map((f) => ({
          "@type": "Question",
          name: f.question,
          acceptedAnswer: { "@type": "Answer", text: f.answer },
        })),
      },
    ],
  });

  const rows: ReadonlyArray<{ label: string; value: string; strong?: boolean; testId: string }> = [
    { label: "Net revenue (delivered and kept)", value: formatInr(result.netRevenue), testId: "text-d2c-net-revenue" },
    { label: "− COGS", value: formatInr(result.cogs), testId: "text-d2c-cogs" },
    { label: "CM1", value: `${formatInr(result.cm1)} · ${pct(result.cm1Pct)}`, strong: true, testId: "text-d2c-cm1" },
    { label: "− Fulfilment (shipping, packaging, RTO and return logistics)", value: formatInr(result.fulfilment), testId: "text-d2c-fulfilment" },
    { label: "− Payment costs (gateway + COD fees)", value: formatInr(result.paymentCosts), testId: "text-d2c-payment" },
    { label: "CM2", value: `${formatInr(result.cm2)} · ${pct(result.cm2Pct)}`, strong: true, testId: "text-d2c-cm2" },
    { label: "− Marketing", value: formatInr(toNumber(text.marketing) || 0), testId: "text-d2c-marketing" },
    { label: "CM3", value: `${formatInr(result.cm3)} · ${pct(result.cm3Pct)}`, strong: true, testId: "text-d2c-cm3" },
  ];

  return (
    <MarketingLayout>
      <section className="border-b">
        <div className="mx-auto max-w-6xl px-4 py-16 md:py-20">
          <div className="flex items-center gap-2 mb-4">
            <Badge variant="secondary" className="text-xs" data-testid="badge-free-tool">
              <Calculator className="mr-1 h-3 w-3" />
              Free Tool · for D2C brands
            </Badge>
          </div>
          <h1
            className="text-3xl font-bold tracking-tight text-foreground md:text-4xl lg:text-5xl"
            data-testid="text-calculator-title"
          >
            D2C Contribution Margin Calculator (CM1, CM2, CM3)
          </h1>
          <p className="mt-3 max-w-2xl text-lg text-muted-foreground" data-testid="text-calculator-subtitle">
            See what each order really earns after COGS, shipping, RTO, COD and ad spend, in ₹.
            CM1 = net revenue − COGS. CM2 = CM1 − fulfilment and payment costs. CM3 = CM2 −
            marketing. Everything runs in your browser; nothing is stored.
          </p>
        </div>
      </section>

      <section className="border-b">
        <div className="mx-auto max-w-6xl px-4 py-12">
          <div className="grid gap-8 lg:grid-cols-5">
            <div className="lg:col-span-2 space-y-6">
              {GROUPS.map((group) => (
                <Card key={group.title}>
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <ShoppingBag className="h-4 w-4 text-primary" />
                      {group.title}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {group.fields.map((field) => {
                      const id = `input-d2c-${field.key}`;
                      return (
                        <div key={field.key} className="space-y-1.5">
                          <div className="flex items-baseline justify-between gap-2">
                            <Label htmlFor={id}>{field.label}</Label>
                            <span className="text-xs text-muted-foreground">{field.unit}</span>
                          </div>
                          <Input
                            id={id}
                            inputMode="decimal"
                            value={text[field.key]}
                            onChange={(e) => set(field.key, e.target.value)}
                            data-testid={id}
                          />
                          {field.help && (
                            <p className="text-xs text-muted-foreground leading-relaxed">{field.help}</p>
                          )}
                        </div>
                      );
                    })}
                  </CardContent>
                </Card>
              ))}
            </div>

            <div className="lg:col-span-3 space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Your monthly contribution margin</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {result.outcome === "invalid" ? (
                    <p className="text-sm text-destructive" data-testid="text-d2c-invalid">
                      {result.reason}
                    </p>
                  ) : (
                    <>
                      <div className="grid grid-cols-3 gap-3">
                        {[
                          { k: "CM1 / order", v: inrOrNa(result.cm1PerOrder) },
                          { k: "CM2 / order", v: inrOrNa(result.cm2PerOrder) },
                          { k: "CM3 / order", v: inrOrNa(result.cm3PerOrder) },
                        ].map((t) => (
                          <div key={t.k} className="rounded-lg border p-3">
                            <div className="text-xs text-muted-foreground">{t.k}</div>
                            <div className="text-xl font-bold tracking-tight text-foreground">{t.v}</div>
                          </div>
                        ))}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Per delivered order ({Math.round(result.deliveredOrders).toLocaleString("en-IN")} delivered
                        of {toNumber(text.orders).toLocaleString("en-IN")} shipped).
                      </p>
                      <dl className="divide-y text-sm">
                        {rows.map((r) => (
                          <div key={r.label} className="flex items-baseline justify-between gap-4 py-2">
                            <dt className={r.strong ? "font-semibold text-foreground" : "text-muted-foreground"}>{r.label}</dt>
                            <dd className={r.strong ? "font-semibold text-foreground" : "text-foreground"} data-testid={r.testId}>
                              {r.value}
                            </dd>
                          </div>
                        ))}
                      </dl>
                      <dl className="grid grid-cols-3 gap-3 pt-2 text-sm">
                        <div>
                          <dt className="text-muted-foreground">MER</dt>
                          <dd className="font-medium" data-testid="text-d2c-mer">{ratio(result.mer)}</dd>
                        </div>
                        <div>
                          <dt className="text-muted-foreground">Break-even MER</dt>
                          <dd className="font-medium" data-testid="text-d2c-breakeven-mer">{ratio(result.breakEvenMer)}</dd>
                        </div>
                        <div>
                          <dt className="text-muted-foreground">RTO logistics cost</dt>
                          <dd className="font-medium" data-testid="text-d2c-rto-cost">{formatInr(result.rtoLogisticsCost)}</dd>
                        </div>
                      </dl>
                      {result.cm3 < 0 && (
                        <p className="text-sm text-amber-600 dark:text-amber-500" data-testid="text-d2c-negative">
                          CM3 is negative: at these numbers, every extra order makes the monthly loss bigger.
                          Look at RTO, COD share and MER before spending more on ads.
                        </p>
                      )}
                    </>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <Info className="h-4 w-4 text-primary" />
                    Assumptions this calculator makes
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm text-muted-foreground leading-relaxed">
                  <p>AOV is ex-GST and after discounts. GST you collect is owed to the government, not revenue.</p>
                  <p>RTO'd and returned goods go back into sellable stock, so they carry no COGS. Damaged returns would make real CM1 lower.</p>
                  <p>Every shipped order pays forward shipping and packaging, including the ones that come back as RTO.</p>
                  <p>RTO is spread evenly across COD and prepaid orders. In practice most RTO comes from COD, so if your COD share is high, your real numbers are likely worse.</p>
                  <p>The defaults are an illustrative brand, not a benchmark.</p>
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
              Stop rebuilding this spreadsheet every month
            </h3>
            <p className="mt-2 text-sm text-muted-foreground max-w-lg mx-auto">
              FounderConsole connects your store and finance data and turns margin, burn and cash into
              runway you can plan against. Free during the public beta, no credit card required.
            </p>
            <Button asChild className="mt-4" data-testid="button-cta-connect">
              <Link href="/signup" onClick={() => trackFunnel("cta_click", { location: "d2c-contribution-margin" })}>
                Start free
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </section>

      <section>
        <div className="mx-auto max-w-4xl px-4 py-16 md:py-20">
          <article className="prose prose-sm dark:prose-invert max-w-none">
            <h2 className="text-2xl font-bold text-foreground mb-4">CM1, CM2 and CM3, defined</h2>
            <dl className="space-y-3 mb-8">
              {D2C_MARGIN_DEFINITIONS.map((d) => (
                <div key={d.term}>
                  <dt className="font-semibold text-foreground">{d.term}</dt>
                  <dd className="text-muted-foreground leading-relaxed">{d.definition}</dd>
                </div>
              ))}
            </dl>

            <h2 className="text-2xl font-bold text-foreground mb-4">Worked example</h2>
            <p className="text-muted-foreground leading-relaxed mb-4">
              The defaults above are an illustrative brand: ₹1,200 AOV, 2,000 orders a month, 18% RTO,
              5% returns, 55% COD, ₹420 COGS, ₹70 each way shipping, ₹30 packaging, 2% gateway fee,
              ₹40 COD fee and ₹6 lakh of marketing. That brand delivers 1,640 orders and keeps 1,558.
              Net revenue is ₹18.70 lakh, CM1 is ₹12.15 lakh (65%), CM2 is ₹9.27 lakh (49.6%) and CM3 is
              ₹3.27 lakh (17.5%), or about ₹199 per delivered order. MER is 3.12x against a break-even
              MER of 2.02x. If RTO rises to 30% with nothing else changed, CM3 falls to ₹1.38 lakh.
            </p>
            <p className="text-muted-foreground leading-relaxed mb-4">
              Read the full walk-through in{" "}
              <Link className="text-primary underline underline-offset-2" href="/blog/cm1-cm2-cm3-contribution-margin-d2c">
                CM1, CM2, CM3 for D2C brands
              </Link>
              , and what to do about RTO in{" "}
              <Link className="text-primary underline underline-offset-2" href="/blog/rto-cod-d2c-margins">
                how RTO and COD eat D2C margins
              </Link>
              . Once you know CM3, the next question is how long your cash lasts: try the{" "}
              <Link className="text-primary underline underline-offset-2" href="/tools/runway-calculator">
                free runway calculator
              </Link>
              .
            </p>

            <h2 className="text-2xl font-bold text-foreground mt-8 mb-4">Questions D2C founders ask</h2>
            {D2C_MARGIN_FAQS.map((f) => (
              <div key={f.question} className="mb-4">
                <h3 className="text-lg font-semibold text-foreground mb-1">{f.question}</h3>
                <p className="text-muted-foreground leading-relaxed">{f.answer}</p>
              </div>
            ))}
          </article>
        </div>
      </section>
    </MarketingLayout>
  );
}
