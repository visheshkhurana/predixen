import { useState, useMemo, useEffect, useRef } from "react";
import { Link } from "wouter";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { useSEO } from "@/lib/seo";
import { trackFunnel } from "@/lib/funnel";
import {
  ArrowRight,
  Calculator,
  TrendingDown,
  Calendar,
  DollarSign,
  Percent,
  BarChart3,
} from "lucide-react";

function formatCurrency(val: number): string {
  if (val >= 1_000_000) return `$${(val / 1_000_000).toFixed(1)}M`;
  if (val >= 1_000) return `$${(val / 1_000).toFixed(0)}K`;
  return `$${val.toFixed(0)}`;
}

function formatDate(months: number): string {
  const d = new Date();
  d.setMonth(d.getMonth() + Math.floor(months));
  return d.toLocaleDateString("en-US", { month: "short", year: "numeric" });
}

const DEFAULTS = { cash: 500000, revenue: 20000, expenses: 60000, growthRate: 5 };

export default function RunwayCalculatorPage() {
  const [cash, setCash] = useState(DEFAULTS.cash);
  const [revenue, setRevenue] = useState(DEFAULTS.revenue);
  const [expenses, setExpenses] = useState(DEFAULTS.expenses);
  const [growthRate, setGrowthRate] = useState(DEFAULTS.growthRate);

  // Fire once, the first time a visitor changes any input away from the
  // pre-filled example.
  //
  // Page views told us nothing useful: 28 people viewed this page and 26 never
  // touched it, which is invisible if the only event is the CTA click at the
  // bottom. This is the step that separates "landed here" from "actually asked
  // the question", and it is the signal ad platforms should optimise toward —
  // waiting for signups gives them almost no data to learn from.
  const usageTracked = useRef(false);
  useEffect(() => {
    if (usageTracked.current) return;
    const touched =
      cash !== DEFAULTS.cash ||
      revenue !== DEFAULTS.revenue ||
      expenses !== DEFAULTS.expenses ||
      growthRate !== DEFAULTS.growthRate;
    if (!touched) return;
    usageTracked.current = true;
    trackFunnel("calculator_used", { calculator: "runway" });
  }, [cash, revenue, expenses, growthRate]);

  const results = useMemo(() => {
    const monthlyBurn = expenses - revenue;
    const months: { month: number; cashRemaining: number; burn: number; rev: number }[] = [];
    let remaining = cash;
    let currentRev = revenue;
    let runwayMonths = 0;

    for (let m = 0; m <= 36; m++) {
      const currentBurn = expenses - currentRev;
      months.push({ month: m, cashRemaining: remaining, burn: currentBurn, rev: currentRev });
      if (remaining <= 0 && runwayMonths === 0) {
        runwayMonths = m;
      }
      remaining -= currentBurn;
      currentRev *= 1 + growthRate / 100;
    }

    if (runwayMonths === 0) runwayMonths = 36;

    const runwayDate = formatDate(runwayMonths);
    const maxCash = Math.max(...months.map((m) => m.cashRemaining), cash);

    return { monthlyBurn, runwayMonths, runwayDate, months, maxCash };
  }, [cash, revenue, expenses, growthRate]);

  useSEO({
    title: "Free Startup Runway Calculator — How Long Until You Run Out of Cash | FounderConsole",
    description:
      "Calculate your startup runway in seconds. Enter cash on hand, monthly revenue, expenses, and growth rate to see how many months until you need to raise. Free interactive tool with chart.",
    path: "/tools/runway-calculator",
    jsonLd: {
      "@context": "https://schema.org",
      "@type": "WebApplication",
      name: "Startup Runway Calculator",
      url: "https://founderconsole.ai/tools/runway-calculator",
      applicationCategory: "BusinessApplication",
      operatingSystem: "Web",
      offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
      description:
        "Free interactive runway calculator for startup founders. Enter your financials and instantly see months of runway remaining, projected cash balance, and runway date.",
      creator: {
        "@type": "Organization",
        name: "FounderConsole",
        url: "https://founderconsole.ai",
      },
    },
  });

  const chartHeight = 200;
  const chartData = results.months.slice(0, Math.min(results.runwayMonths + 6, 37));
  const maxVal = results.maxCash > 0 ? results.maxCash : 1;

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
            Startup Runway Calculator
          </h1>
          <p
            className="mt-3 max-w-2xl text-lg text-muted-foreground"
            data-testid="text-calculator-subtitle"
          >
            Enter your financials to instantly see how many months of runway you
            have, when you&apos;ll run out of cash, and how growth affects your
            timeline.
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
                    <DollarSign className="h-4 w-4 text-primary" />
                    Your Financials
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-5">
                  <div>
                    <Label htmlFor="cash" className="text-sm font-medium">
                      Cash on Hand
                    </Label>
                    <div className="relative mt-1.5">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">
                        $
                      </span>
                      <Input
                        id="cash"
                        type="number"
                        value={cash}
                        onChange={(e) => setCash(Number(e.target.value))}
                        className="pl-7"
                        data-testid="input-cash"
                      />
                    </div>
                  </div>
                  <div>
                    <Label htmlFor="revenue" className="text-sm font-medium">
                      Monthly Revenue
                    </Label>
                    <div className="relative mt-1.5">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">
                        $
                      </span>
                      <Input
                        id="revenue"
                        type="number"
                        value={revenue}
                        onChange={(e) => setRevenue(Number(e.target.value))}
                        className="pl-7"
                        data-testid="input-revenue"
                      />
                    </div>
                  </div>
                  <div>
                    <Label htmlFor="expenses" className="text-sm font-medium">
                      Monthly Expenses
                    </Label>
                    <div className="relative mt-1.5">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">
                        $
                      </span>
                      <Input
                        id="expenses"
                        type="number"
                        value={expenses}
                        onChange={(e) => setExpenses(Number(e.target.value))}
                        className="pl-7"
                        data-testid="input-expenses"
                      />
                    </div>
                  </div>
                  <div>
                    <Label htmlFor="growth" className="text-sm font-medium">
                      Monthly Revenue Growth Rate
                    </Label>
                    <div className="relative mt-1.5">
                      <Input
                        id="growth"
                        type="number"
                        value={growthRate}
                        onChange={(e) => setGrowthRate(Number(e.target.value))}
                        className="pr-7"
                        data-testid="input-growth"
                      />
                      <span className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">
                        <Percent className="h-3.5 w-3.5" />
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="lg:col-span-3 space-y-6">
              <div className="grid grid-cols-3 gap-4">
                <Card>
                  <CardContent className="pt-6 text-center">
                    <TrendingDown className="mx-auto h-5 w-5 text-orange-500 mb-2" />
                    <p className="text-2xl font-bold font-mono text-foreground" data-testid="text-burn-rate">
                      {formatCurrency(results.monthlyBurn)}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">Monthly Net Burn</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-6 text-center">
                    <BarChart3 className="mx-auto h-5 w-5 text-primary mb-2" />
                    <p className="text-2xl font-bold font-mono text-foreground" data-testid="text-runway-months">
                      {results.runwayMonths >= 36 ? "36+" : results.runwayMonths}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">Months of Runway</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-6 text-center">
                    <Calendar className="mx-auto h-5 w-5 text-emerald-500 mb-2" />
                    <p className="text-2xl font-bold font-mono text-foreground" data-testid="text-runway-date">
                      {results.runwayMonths >= 36 ? "36+ mo" : results.runwayDate}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">Runway Until</p>
                  </CardContent>
                </Card>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Projected Cash Balance</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="relative" style={{ height: chartHeight + 40 }}>
                    <svg
                      width="100%"
                      height={chartHeight + 40}
                      viewBox={`0 0 ${chartData.length * 24} ${chartHeight + 40}`}
                      preserveAspectRatio="none"
                      data-testid="chart-runway"
                    >
                      <defs>
                        <linearGradient id="cashGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity="0.3" />
                          <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity="0" />
                        </linearGradient>
                      </defs>
                      <line
                        x1="0"
                        y1={chartHeight}
                        x2={chartData.length * 24}
                        y2={chartHeight}
                        stroke="hsl(var(--border))"
                        strokeWidth="1"
                      />
                      <path
                        d={
                          chartData
                            .map((d, i) => {
                              const x = i * 24;
                              const y = chartHeight - (Math.max(d.cashRemaining, 0) / maxVal) * (chartHeight - 20);
                              return `${i === 0 ? "M" : "L"}${x},${y}`;
                            })
                            .join(" ") +
                          ` L${(chartData.length - 1) * 24},${chartHeight} L0,${chartHeight} Z`
                        }
                        fill="url(#cashGrad)"
                      />
                      <path
                        d={chartData
                          .map((d, i) => {
                            const x = i * 24;
                            const y = chartHeight - (Math.max(d.cashRemaining, 0) / maxVal) * (chartHeight - 20);
                            return `${i === 0 ? "M" : "L"}${x},${y}`;
                          })
                          .join(" ")}
                        fill="none"
                        stroke="hsl(var(--primary))"
                        strokeWidth="2"
                      />
                      {chartData
                        .filter((_, i) => i % 6 === 0)
                        .map((d) => (
                          <text
                            key={d.month}
                            x={d.month * 24}
                            y={chartHeight + 16}
                            fill="hsl(var(--muted-foreground))"
                            fontSize="10"
                            textAnchor="middle"
                          >
                            M{d.month}
                          </text>
                        ))}
                    </svg>
                  </div>
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
              This calculator uses a simple linear model. FounderConsole connects
              your real financial data and runs Monte Carlo simulations with P10/P50/P90
              confidence bands — so you know your true runway probability.
            </p>
            <Button asChild className="mt-4" data-testid="button-cta-connect">
              <Link href="/auth?tab=register" onClick={() => trackFunnel("cta_click", { location: "runway-calculator" })}>
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
              How to Calculate Startup Runway: The Complete Guide
            </h2>
            <p className="text-muted-foreground leading-relaxed mb-4">
              Startup runway is the number of months your company can continue operating before it runs out of cash, assuming no additional funding. It is one of the most important metrics for any early-stage founder because it determines how much time you have to achieve product-market fit, hit growth milestones, or close your next fundraising round. Calculating runway accurately is not optional — it is essential for survival.
            </p>
            <p className="text-muted-foreground leading-relaxed mb-4">
              The basic runway formula is simple: divide your current cash balance by your monthly net burn rate. Net burn is the difference between your monthly expenses (salaries, rent, software, marketing, hosting, legal) and your monthly revenue. If you have $500,000 in the bank and you burn $40,000 per month net, your runway is 12.5 months.
            </p>

            <h3 className="text-xl font-semibold text-foreground mt-8 mb-3" data-testid="text-seo-heading-2">
              Why Simple Runway Calculations Are Dangerous
            </h3>
            <p className="text-muted-foreground leading-relaxed mb-4">
              The problem with the simple formula is that it assumes a constant burn rate. In reality, expenses increase as you hire, revenue fluctuates month-to-month, and unexpected costs arise. A single-point runway estimate gives you false confidence. If your runway calculation says 14 months but your revenue drops 30% next quarter, you might actually have 9 months — and by the time you realize it, fundraising takes another 4-6 months, putting you in a very dangerous position.
            </p>
            <p className="text-muted-foreground leading-relaxed mb-4">
              This is why sophisticated founders use probabilistic methods. Instead of calculating one runway number, you calculate a range of outcomes using Monte Carlo simulation. A Monte Carlo simulation runs your financial model thousands of times with slightly different assumptions each time — varying revenue growth, churn rate, hiring pace, and other variables within realistic ranges. The result is a probability distribution showing your P10 (pessimistic), P50 (median), and P90 (optimistic) runway.
            </p>

            <h3 className="text-xl font-semibold text-foreground mt-8 mb-3" data-testid="text-seo-heading-3">
              Factors That Affect Your Runway
            </h3>
            <p className="text-muted-foreground leading-relaxed mb-4">
              Several factors significantly impact your startup runway. Revenue growth rate is the most important lever — even modest month-over-month growth compounds rapidly and can extend your runway dramatically. Gross margin matters because not all revenue contributes equally to covering fixed costs; a SaaS company with 80% gross margins keeps much more of each dollar than a marketplace with 15% take rates.
            </p>
            <p className="text-muted-foreground leading-relaxed mb-4">
              Hiring pace is often the largest controllable expense. Each new hire increases your monthly burn by $8,000 to $25,000+ depending on role and location. Customer churn directly reduces revenue and shortens runway. Payment terms and accounts receivable affect when cash actually arrives in your bank account versus when you recognize revenue.
            </p>

            <h3 className="text-xl font-semibold text-foreground mt-8 mb-3" data-testid="text-seo-heading-4">
              When to Start Fundraising Based on Runway
            </h3>
            <p className="text-muted-foreground leading-relaxed mb-4">
              Most venture capital firms recommend starting your fundraise when you have 9 to 12 months of runway remaining. This gives you enough time to run a proper process — creating your data room, meeting 30-50 investors, negotiating terms, and closing — without the desperation that comes from having only 3 months of cash left. Investors can sense urgency, and it weakens your negotiating position.
            </p>
            <p className="text-muted-foreground leading-relaxed mb-4">
              The runway calculator above gives you a starting point, but for critical decisions like fundraising timing, you need more sophisticated tools. FounderConsole connects to your actual financial data sources — Stripe, QuickBooks, Mercury, Brex, and 33 more — and runs Monte Carlo simulations to show you probabilistic runway projections. Instead of a single number, you get confidence bands that account for revenue variability, seasonal patterns, and growth uncertainty.
            </p>

            <h3 className="text-xl font-semibold text-foreground mt-8 mb-3" data-testid="text-seo-heading-5">
              Beyond the Calculator: What FounderConsole Offers
            </h3>
            <p className="text-muted-foreground leading-relaxed mb-4">
              While this free calculator provides a useful estimate, FounderConsole goes much further. It creates a digital twin of your company — a live financial model that updates automatically as new data flows in. You can run what-if scenarios (what happens if we hire two engineers next month? what if our largest customer churns?) and see the impact on your runway distribution instantly. The AI Copilot can analyze your financials and proactively alert you when your runway drops below safe thresholds, giving you more time to react.
            </p>
            <p className="text-muted-foreground leading-relaxed mb-4">
              All features are free during the public beta. Connect your data, run your first simulation, and get a defensible runway forecast in under five minutes — no spreadsheets required.
            </p>
          </article>
        </div>
      </section>
    </MarketingLayout>
  );
}
