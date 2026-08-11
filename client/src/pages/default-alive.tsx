import { useState, useMemo, useEffect, useRef } from "react";
import { Link } from "wouter";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { useSEO } from "@/lib/seo";
import { trackFunnel } from "@/lib/funnel";
import { trackEvent } from "@/lib/posthog";
import {
  ArrowRight,
  DollarSign,
  Percent,
  HeartPulse,
  Skull,
  TrendingUp,
  Scissors,
  Landmark,
} from "lucide-react";

const HORIZON = 60;

function formatCurrency(val: number): string {
  const sign = val < 0 ? "-" : "";
  const v = Math.abs(val);
  if (v >= 1_000_000) return `${sign}$${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `${sign}$${(v / 1_000).toFixed(0)}K`;
  return `${sign}$${v.toFixed(0)}`;
}

function monthLabel(monthsFromNow: number): string {
  const d = new Date();
  d.setMonth(d.getMonth() + Math.floor(monthsFromNow));
  return d.toLocaleDateString("en-US", { month: "short", year: "numeric" });
}

type Verdict = {
  alive: boolean;
  profitableMonth: number | null;
  outOfCashMonth: number | null;
  lowestCash: number;
  series: { month: number; cash: number; rev: number; exp: number }[];
};

/**
 * Paul Graham's default alive test: at your current growth rate and current
 * expenses, do you reach profitability before the money runs out?
 *
 * The honest caveat, which most calculators of this shape omit: PG's original
 * framing holds expenses flat, and almost nobody's expenses stay flat while
 * revenue compounds. The expenseGrowth toggle exists so a founder can see how
 * fragile the "alive" verdict is once hiring is included — it very often flips.
 */
function computeVerdict(
  cash: number,
  revenue: number,
  expenses: number,
  growthPct: number,
  expenseGrowthPct: number,
): Verdict {
  const g = growthPct / 100;
  const eg = expenseGrowthPct / 100;

  let remaining = cash;
  let profitableMonth: number | null = null;
  let outOfCashMonth: number | null = null;
  let lowestCash = cash;
  const series: Verdict["series"] = [];

  for (let m = 0; m <= HORIZON; m++) {
    const rev = revenue * Math.pow(1 + g, m);
    const exp = expenses * Math.pow(1 + eg, m);

    if (profitableMonth === null && rev >= exp) profitableMonth = m;

    series.push({ month: m, cash: remaining, rev, exp });
    if (remaining < lowestCash) lowestCash = remaining;
    if (remaining <= 0 && outOfCashMonth === null) outOfCashMonth = m;

    remaining += rev - exp;
  }

  // Alive means you cross into profit while there is still money in the bank.
  const alive =
    profitableMonth !== null &&
    (outOfCashMonth === null || profitableMonth < outOfCashMonth);

  return { alive, profitableMonth, outOfCashMonth, lowestCash, series };
}

const DA_DEFAULTS = { cash: 500000, revenue: 25000, expenses: 75000, growthRate: 8 };

export default function DefaultAlivePage() {
  const [cash, setCash] = useState(DA_DEFAULTS.cash);
  const [revenue, setRevenue] = useState(DA_DEFAULTS.revenue);
  const [expenses, setExpenses] = useState(DA_DEFAULTS.expenses);
  const [growthRate, setGrowthRate] = useState(DA_DEFAULTS.growthRate);
  const [includeExpenseGrowth, setIncludeExpenseGrowth] = useState(false);
  const [expenseGrowth, setExpenseGrowth] = useState(3);

  // See the matching comment in runway-calculator.tsx: a page view here says
  // nothing about whether the visitor actually asked the question. This is the
  // first real signal of intent on the page.
  const usageTracked = useRef(false);
  useEffect(() => {
    if (usageTracked.current) return;
    const touched =
      cash !== DA_DEFAULTS.cash ||
      revenue !== DA_DEFAULTS.revenue ||
      expenses !== DA_DEFAULTS.expenses ||
      growthRate !== DA_DEFAULTS.growthRate ||
      includeExpenseGrowth;
    if (!touched) return;
    usageTracked.current = true;
    trackFunnel("calculator_used", { calculator: "default-alive" });
  }, [cash, revenue, expenses, growthRate, includeExpenseGrowth]);

  const effectiveExpenseGrowth = includeExpenseGrowth ? expenseGrowth : 0;

  const verdict = useMemo(
    () => computeVerdict(cash, revenue, expenses, growthRate, effectiveExpenseGrowth),
    [cash, revenue, expenses, growthRate, effectiveExpenseGrowth],
  );

  // What each of the three levers would have to do to flip a dead verdict.
  const levers = useMemo(() => {
    if (verdict.alive) return null;

    // 1. Cut expenses: find the smallest cut that flips the verdict.
    let cutNeeded: number | null = null;
    for (let pct = 5; pct <= 80; pct += 5) {
      const t = computeVerdict(cash, revenue, expenses * (1 - pct / 100), growthRate, effectiveExpenseGrowth);
      if (t.alive) {
        cutNeeded = pct;
        break;
      }
    }

    // 2. Grow faster: smallest monthly growth rate that flips it.
    let growthNeeded: number | null = null;
    for (let g = growthRate + 1; g <= 60; g += 1) {
      const t = computeVerdict(cash, revenue, expenses, g, effectiveExpenseGrowth);
      if (t.alive) {
        growthNeeded = g;
        break;
      }
    }

    // 3. Raise: how much cash makes the current trajectory survivable.
    let raiseNeeded: number | null = null;
    for (let mult = 1.25; mult <= 10; mult += 0.25) {
      const t = computeVerdict(cash * mult, revenue, expenses, growthRate, effectiveExpenseGrowth);
      if (t.alive) {
        raiseNeeded = cash * mult - cash;
        break;
      }
    }

    return { cutNeeded, growthNeeded, raiseNeeded };
  }, [verdict.alive, cash, revenue, expenses, growthRate, effectiveExpenseGrowth]);

  useSEO({
    title: "Default Alive or Default Dead? Free Calculator for Founders | FounderConsole",
    description:
      "Paul Graham's default alive test, as a calculator. Enter cash, revenue, expenses and growth rate to find out whether you reach profitability before the money runs out — and what it would take to flip the answer.",
    path: "/default-alive",
    jsonLd: {
      "@context": "https://schema.org",
      "@type": "WebApplication",
      name: "Default Alive or Default Dead Calculator",
      url: "https://founderconsole.ai/default-alive",
      applicationCategory: "BusinessApplication",
      operatingSystem: "Web",
      offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
      description:
        "Free calculator implementing Paul Graham's default alive test. Determines whether a startup reaches profitability on current cash and growth rate before running out of money.",
      creator: { "@type": "Organization", name: "FounderConsole", url: "https://founderconsole.ai" },
    },
  });

  const alive = verdict.alive;

  return (
    <MarketingLayout>
      <section className="border-b">
        <div className="mx-auto max-w-6xl px-4 py-16 md:py-20">
          <div className="flex items-center gap-2 mb-4">
            <Badge variant="secondary" className="text-xs" data-testid="badge-free-tool">
              <HeartPulse className="mr-1 h-3 w-3" />
              Free Tool — No Signup
            </Badge>
          </div>
          <h1
            className="text-3xl font-bold tracking-tight text-foreground md:text-4xl lg:text-5xl"
            data-testid="text-default-alive-title"
          >
            Default Alive or Default Dead?
          </h1>
          <p className="mt-3 max-w-2xl text-lg text-muted-foreground" data-testid="text-default-alive-subtitle">
            Paul Graham&apos;s test, in 30 seconds: at your current growth rate and
            current expenses, do you reach profitability before the money runs out?
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
                    Your Numbers
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-5">
                  <div>
                    <Label htmlFor="da-cash" className="text-sm font-medium">Cash in the Bank</Label>
                    <div className="relative mt-1.5">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">$</span>
                      <Input id="da-cash" type="number" value={cash} onChange={(e) => setCash(Number(e.target.value))} className="pl-7" data-testid="input-da-cash" />
                    </div>
                  </div>
                  <div>
                    <Label htmlFor="da-revenue" className="text-sm font-medium">Monthly Revenue</Label>
                    <div className="relative mt-1.5">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">$</span>
                      <Input id="da-revenue" type="number" value={revenue} onChange={(e) => setRevenue(Number(e.target.value))} className="pl-7" data-testid="input-da-revenue" />
                    </div>
                  </div>
                  <div>
                    <Label htmlFor="da-expenses" className="text-sm font-medium">Monthly Expenses</Label>
                    <div className="relative mt-1.5">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">$</span>
                      <Input id="da-expenses" type="number" value={expenses} onChange={(e) => setExpenses(Number(e.target.value))} className="pl-7" data-testid="input-da-expenses" />
                    </div>
                  </div>
                  <div>
                    <Label htmlFor="da-growth" className="text-sm font-medium">Monthly Revenue Growth</Label>
                    <div className="relative mt-1.5">
                      <Input id="da-growth" type="number" value={growthRate} onChange={(e) => setGrowthRate(Number(e.target.value))} className="pr-8" data-testid="input-da-growth" />
                      <span className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                        <Percent className="h-3.5 w-3.5" />
                      </span>
                    </div>
                  </div>

                  <div className="rounded-lg border border-white/[0.08] p-3 space-y-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <Label htmlFor="da-expense-growth-toggle" className="text-sm font-medium">
                          Let expenses grow too
                        </Label>
                        <p className="text-xs text-muted-foreground mt-1">
                          PG&apos;s original test holds expenses flat. Almost nobody&apos;s
                          actually are.
                        </p>
                      </div>
                      <Switch
                        id="da-expense-growth-toggle"
                        checked={includeExpenseGrowth}
                        onCheckedChange={(v) => {
                          setIncludeExpenseGrowth(v);
                          trackEvent("default_alive_expense_growth_toggled", { enabled: v });
                        }}
                        data-testid="switch-da-expense-growth"
                      />
                    </div>
                    {includeExpenseGrowth && (
                      <div>
                        <Label htmlFor="da-expense-growth" className="text-xs text-muted-foreground">
                          Monthly expense growth
                        </Label>
                        <div className="relative mt-1.5">
                          <Input id="da-expense-growth" type="number" value={expenseGrowth} onChange={(e) => setExpenseGrowth(Number(e.target.value))} className="pr-8" data-testid="input-da-expense-growth" />
                          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                            <Percent className="h-3.5 w-3.5" />
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="lg:col-span-3 space-y-6">
              <Card
                className={alive ? "border-emerald-500/40 bg-emerald-500/[0.06]" : "border-destructive/40 bg-destructive/[0.06]"}
                data-testid="card-da-verdict"
              >
                <CardContent className="p-8 text-center">
                  <div className="flex justify-center mb-4">
                    {alive ? (
                      <HeartPulse className="h-10 w-10 text-emerald-500" />
                    ) : (
                      <Skull className="h-10 w-10 text-destructive" />
                    )}
                  </div>
                  <p
                    className={`text-3xl md:text-4xl font-bold tracking-tight ${alive ? "text-emerald-500" : "text-destructive"}`}
                    data-testid="text-da-verdict"
                  >
                    {alive ? "Default Alive" : "Default Dead"}
                  </p>
                  <p className="mt-3 text-sm text-muted-foreground max-w-md mx-auto" data-testid="text-da-explanation">
                    {alive ? (
                      <>
                        On these numbers you turn profitable in{" "}
                        <strong className="text-foreground">{monthLabel(verdict.profitableMonth ?? 0)}</strong>
                        {verdict.profitableMonth !== null && verdict.profitableMonth > 0 && (
                          <> — month {verdict.profitableMonth}</>
                        )}
                        , with{" "}
                        <strong className="text-foreground">{formatCurrency(verdict.lowestCash)}</strong>{" "}
                        as your lowest point. You do not need to raise to survive.
                      </>
                    ) : verdict.outOfCashMonth !== null ? (
                      <>
                        You run out of cash in{" "}
                        <strong className="text-foreground">{monthLabel(verdict.outOfCashMonth)}</strong> — month{" "}
                        {verdict.outOfCashMonth} — before reaching profitability. On these
                        numbers, survival depends on raising or changing something.
                      </>
                    ) : (
                      <>
                        You don&apos;t run out of cash within {HORIZON} months, but you never
                        reach profitability either. That is not default alive — it just means
                        the reckoning is further out than this horizon.
                      </>
                    )}
                  </p>
                  {includeExpenseGrowth && (
                    <p className="mt-4 text-xs text-muted-foreground" data-testid="text-da-expense-note">
                      Including {expenseGrowth}% monthly expense growth. Turn it off to see
                      the classic version of the test.
                    </p>
                  )}
                </CardContent>
              </Card>

              {!alive && levers && (
                <Card data-testid="card-da-levers">
                  <CardHeader>
                    <CardTitle className="text-lg">What would flip it</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-start gap-3" data-testid="lever-cut">
                      <Scissors className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
                      <p className="text-sm">
                        {levers.cutNeeded !== null ? (
                          <>
                            <strong>Cut expenses by {levers.cutNeeded}%</strong> — to about{" "}
                            {formatCurrency(expenses * (1 - levers.cutNeeded / 100))}/month.
                          </>
                        ) : (
                          <>No realistic expense cut alone gets you there.</>
                        )}
                      </p>
                    </div>
                    <div className="flex items-start gap-3" data-testid="lever-growth">
                      <TrendingUp className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
                      <p className="text-sm">
                        {levers.growthNeeded !== null ? (
                          <>
                            <strong>Grow at {levers.growthNeeded}% a month</strong> instead of{" "}
                            {growthRate}%.
                          </>
                        ) : (
                          <>Growth alone can&apos;t save this within {HORIZON} months.</>
                        )}
                      </p>
                    </div>
                    <div className="flex items-start gap-3" data-testid="lever-raise">
                      <Landmark className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
                      <p className="text-sm">
                        {levers.raiseNeeded !== null ? (
                          <>
                            <strong>Raise about {formatCurrency(levers.raiseNeeded)}</strong> to
                            buy enough time at this trajectory.
                          </>
                        ) : (
                          <>Raising alone doesn&apos;t fix it — the trajectory has to change.</>
                        )}
                      </p>
                    </div>
                    <p className="text-xs text-muted-foreground pt-1">
                      Each lever is calculated in isolation. In practice founders pull two at
                      once, which is usually cheaper than pulling either one to its extreme.
                    </p>
                  </CardContent>
                </Card>
              )}

              <Card>
                <CardContent className="p-6">
                  <p className="text-sm text-muted-foreground">
                    This is a single-path projection: one growth rate, held steady. Real
                    revenue is lumpy, and the month your biggest customer churns is not the
                    average month. FounderConsole runs the same question thousands of times
                    over your actual financials and gives you the odds rather than one line.
                  </p>
                  <div className="mt-4 flex flex-wrap gap-3">
                    <Button asChild data-testid="button-da-cta">
                      <Link
                        href="/auth?tab=register"
                        onClick={() => trackFunnel("cta_click", { location: "default-alive" })}
                      >
                        Run it on your real numbers
                        <ArrowRight className="ml-1.5 h-4 w-4" />
                      </Link>
                    </Button>
                    <Button variant="outline" asChild data-testid="button-da-runway">
                      <Link href="/tools/runway-calculator">Runway calculator</Link>
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </section>

      <section>
        <div className="mx-auto max-w-3xl px-4 py-16">
          <h2 className="text-2xl font-bold tracking-tight">What default alive actually means</h2>
          <div className="mt-4 space-y-4 text-muted-foreground">
            <p>
              Paul Graham coined the term in 2015. The question is simple: assuming your
              current expenses and current growth rate, would you make it to profitability
              on the money you already have?
            </p>
            <p>
              If yes, you are default alive. Raising becomes a choice about going faster
              rather than a condition of survival, and that changes how you negotiate.
            </p>
            <p>
              If no, you are default dead, and the important part is that most founders in
              that position do not know it. The number feels abstract until you watch the
              date land in a specific month.
            </p>
            <p>
              One honest caveat about the test itself: it assumes expenses stay flat while
              revenue compounds. Almost no growing company works that way — you hire, and
              costs climb with revenue. That is why the toggle above exists. If your verdict
              flips the moment you allow expenses to grow at all, the &quot;alive&quot;
              answer was fragile to begin with, and it is better to know that now.
            </p>
          </div>
        </div>
      </section>
    </MarketingLayout>
  );
}
