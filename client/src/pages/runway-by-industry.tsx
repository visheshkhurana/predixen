import { useMemo, useState } from "react";
import { useRoute, Link } from "wouter";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { useSEO } from "@/lib/seo";
import { ArrowRight, Calculator, TrendingUp, AlertTriangle } from "lucide-react";
import { RUNWAY_INDUSTRIES, getIndustry, type IndustryProfile } from "@/data/runway-industries";
import NotFound from "@/pages/not-found";
import { simpleRunway, formatRunway, runwayVerdict, toNumber, type RunwayVerdict } from "@/lib/tools/runway";

const VERDICT_TONE: Record<RunwayVerdict, string> = {
  Profitable: "bg-emerald-600/30 text-emerald-300",
  Healthy: "bg-emerald-600/30 text-emerald-300",
  Watch: "bg-amber-600/30 text-amber-200",
  "Raise soon": "bg-orange-600/30 text-orange-200",
  Critical: "bg-red-600/30 text-red-200",
};

function buildJsonLd(name: string, slug: string) {
  return {
    "@context": "https://schema.org",
    "@type": "WebApplication",
    name,
    url: `https://founderconsole.ai/runway/${slug}`,
    applicationCategory: "BusinessApplication",
    operatingSystem: "Web",
    offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
  };
}

export default function RunwayByIndustryPage() {
  const [, params] = useRoute("/runway/:slug");
  const slug = params?.slug || "";
  const industry = getIndustry(slug);

  if (!industry) {
    return <NotFound />;
  }
  // Keyed by slug: moving from /runway/saas to /runway/fintech remounts the
  // calculator, so its inputs start from the new industry's defaults instead of
  // keeping the last one's. The early return above sits before any hook.
  return <IndustryRunwayCalculator key={industry.slug} industry={industry} />;
}

function IndustryRunwayCalculator({ industry }: { industry: IndustryProfile }) {
  // Inputs hold text so a cleared field stays empty instead of snapping to 0.
  const [cashText, setCashText] = useState("500000");
  const [burnText, setBurnText] = useState(String(industry.defaultBurn));
  const [revenueText, setRevenueText] = useState(String(industry.defaultRevenue));

  const result = useMemo(
    () => simpleRunway(toNumber(cashText), toNumber(burnText), toNumber(revenueText)),
    [cashText, burnText, revenueText],
  );
  const netBurn = Math.max(0, result.netBurn);
  const verdictLabel = runwayVerdict(result);
  const verdict = { label: verdictLabel, tone: VERDICT_TONE[verdictLabel] };

  useSEO({
    title: `${industry.name} | FounderConsole`,
    description: `Free ${industry.shortName} startup runway calculator with industry benchmarks. ${industry.benchmarkRunway}. Run a Monte Carlo simulation tuned to ${industry.shortName} economics.`,
    path: `/runway/${industry.slug}`,
    jsonLd: buildJsonLd(industry.name, industry.slug),
  });

  return (
    <MarketingLayout>
      <section className="mx-auto max-w-5xl px-4 py-16 md:py-20" data-testid={`runway-industry-${industry.slug}`}>
        <Badge variant="secondary" className="mb-4">{industry.shortName} benchmarks</Badge>
        <h1 className="text-3xl md:text-4xl font-bold tracking-tight" data-testid="runway-industry-title">
          {industry.name}
        </h1>
        <p className="mt-3 text-lg text-muted-foreground max-w-3xl">
          Calculate runway against real {industry.shortName.toLowerCase()} benchmarks. Then run a full
          Monte Carlo simulation that accounts for the burn-rate curves, working-capital cycles, and
          fundraising timing unique to {industry.shortName.toLowerCase()} startups.
        </p>

        <Card className="mt-8 border-zinc-800 bg-zinc-900/60">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Calculator className="h-4 w-4 text-primary" /> Quick {industry.shortName} runway calculator
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <Label htmlFor="cash">Cash on hand ($)</Label>
                <Input
                  id="cash" type="number" inputMode="decimal" value={cashText}
                  onChange={(e) => setCashText(e.target.value)}
                  data-testid="input-runway-cash"
                />
              </div>
              <div>
                <Label htmlFor="burn">Monthly gross burn ($)</Label>
                <Input
                  id="burn" type="number" inputMode="decimal" value={burnText}
                  onChange={(e) => setBurnText(e.target.value)}
                  data-testid="input-runway-burn"
                />
              </div>
              <div>
                <Label htmlFor="revenue">Monthly revenue ($)</Label>
                <Input
                  id="revenue" type="number" inputMode="decimal" value={revenueText}
                  onChange={(e) => setRevenueText(e.target.value)}
                  data-testid="input-runway-revenue"
                />
              </div>
            </div>

            <div className="mt-6 flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-950/50 p-5">
              <div>
                <div className="text-sm text-muted-foreground">Estimated runway</div>
                <div className="text-3xl font-bold mt-1" data-testid="runway-result-months">
                  {formatRunway(result)}
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  Net burn: ${netBurn.toLocaleString()}/mo · Benchmark: {industry.benchmarkRunway}
                </div>
              </div>
              <Badge className={verdict.tone} data-testid="runway-verdict">{verdict.label}</Badge>
            </div>

            <div className="mt-4 flex flex-col sm:flex-row gap-3">
              <Link href="/survival-simulator" data-testid="link-survival-sim">
                <Button className="w-full sm:w-auto">
                  Run full Monte Carlo simulation <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
              <Link href="/auth?mode=signup" data-testid="link-signup">
                <Button variant="outline" className="w-full sm:w-auto">
                  Get the AI copilot for {industry.shortName}
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>

        <div className="mt-10 grid gap-6 md:grid-cols-2">
          <Card className="border-zinc-800 bg-zinc-900/40">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-primary" /> What's specific to {industry.shortName}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm">
                {industry.notes.map((n, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-primary">·</span>
                    <span className="text-muted-foreground">{n}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          <Card className="border-zinc-800 bg-zinc-900/40">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-500" /> Top risk factors
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm">
                {industry.primaryRiskFactors.map((r, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-amber-500">·</span>
                    <span className="text-muted-foreground">{r}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>

        <article className="mt-12 prose prose-invert max-w-none">
          <h2 className="text-2xl font-semibold mt-8">How to read your {industry.shortName} runway</h2>
          <p className="text-muted-foreground">
            Net burn is the difference between your monthly gross burn and your monthly revenue.
            Runway is your cash on hand divided by net burn. For {industry.shortName.toLowerCase()},
            the relevant benchmark is <strong>{industry.benchmarkRunway}</strong>.
          </p>
          <h3 className="text-xl font-semibold mt-6">Burn multiple — the {industry.shortName} view</h3>
          <p className="text-muted-foreground">{industry.burnMultipleNotes}</p>
          <h3 className="text-xl font-semibold mt-6">When to raise as a {industry.shortName} founder</h3>
          <p className="text-muted-foreground">{industry.fundraisingNotes}</p>
          <h3 className="text-xl font-semibold mt-6">Why a single-point runway estimate is dangerous</h3>
          <p className="text-muted-foreground">
            A point estimate assumes burn and revenue stay constant. They never do.
            FounderConsole runs a thousand Monte Carlo paths against your real numbers,
            tuned for {industry.shortName.toLowerCase()} economics, and gives you P10 / P50 / P90 outcomes.
          </p>
          <p className="mt-4">
            <Link href="/survival-simulator" className="text-primary underline" data-testid="link-survival-bottom">
              Run the full simulator &rarr;
            </Link>
          </p>
        </article>

        <div className="mt-16 border-t border-zinc-800 pt-8">
          <h3 className="text-sm font-semibold text-muted-foreground tracking-wider uppercase">
            Other industry calculators
          </h3>
          <div className="mt-4 flex flex-wrap gap-2">
            {RUNWAY_INDUSTRIES.filter((i) => i.slug !== industry.slug).map((i) => (
              <Link key={i.slug} href={`/runway/${i.slug}`} data-testid={`link-runway-${i.slug}`}>
                <Badge variant="outline" className="cursor-pointer hover:bg-primary/10">{i.shortName}</Badge>
              </Link>
            ))}
          </div>
        </div>
      </section>
    </MarketingLayout>
  );
}
