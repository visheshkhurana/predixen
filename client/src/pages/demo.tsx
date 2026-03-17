import { Link } from "wouter";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { Button } from "@/components/ui/button";
import { useSEO } from "@/lib/seo";
import { Play, ArrowRight, CheckCircle } from "lucide-react";

const chapters = [
  { time: "0:00", label: "Connect data (Stripe, QuickBooks, Gusto, Mercury)" },
  { time: "0:20", label: "Baseline forecast in real time" },
  { time: "0:40", label: "Monte Carlo confidence intervals (P10/P50/P90)" },
  { time: "1:05", label: "Explainability: what drives the risk" },
  { time: "1:30", label: "Scenario comparison and decision scoring" },
  { time: "2:00", label: "Investor-ready summary and reporting" },
];

export default function DemoPage() {
  useSEO({
    title: "Demo | FounderConsole",
    description: "Watch the FounderConsole demo: connect data, forecast, simulate confidence intervals, decide.",
    path: "/demo",
  });

  return (
    <MarketingLayout>
      <section>
        <div className="mx-auto max-w-6xl px-4 py-16 md:py-20">
          <h1 className="text-3xl font-bold tracking-tight text-foreground md:text-4xl" data-testid="text-demo-title">
            See FounderConsole in action
          </h1>
          <p className="mt-3 max-w-2xl text-lg text-muted-foreground">
            A fast walkthrough for founders. See how you go from raw data to defensible decisions in under 5 minutes.
          </p>
        </div>
      </section>

      <section className="border-t">
        <div className="mx-auto max-w-4xl px-4 py-10">
          <div className="rounded-xl border bg-card overflow-hidden">
            <div className="aspect-video flex items-center justify-center bg-gradient-to-br from-primary/10 to-primary/5">
              <div className="text-center">
                <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-primary/20" role="img" aria-label="Demo video placeholder" data-testid="icon-play-demo">
                  <Play className="h-8 w-8 text-primary ml-1" />
                </div>
                <p className="mt-4 text-sm text-muted-foreground">Product demo video coming soon</p>
              </div>
            </div>

            <div className="p-6">
              <h2 className="text-base font-semibold text-foreground">Chapters</h2>
              <ul className="mt-4 space-y-3">
                {chapters.map((ch) => (
                  <li key={ch.time} className="flex gap-3 text-sm" data-testid={`text-chapter-${ch.time.replace(":", "")}`}>
                    <span className="font-mono text-primary shrink-0 w-10">{ch.time}</span>
                    <span className="text-muted-foreground">{ch.label}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="mt-10 grid gap-6 md:grid-cols-2">
            <div className="rounded-xl border bg-card p-6">
              <h3 className="text-base font-semibold text-foreground">Try it yourself</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                Sign in with demo credentials to explore simulations, the AI copilot, and reporting features with sample company data.
              </p>
              <div className="mt-4">
                <Button asChild data-testid="button-demo-try">
                  <Link href="/auth">
                    Try the Demo
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
              </div>
            </div>

            <div className="rounded-xl border bg-card p-6">
              <h3 className="text-base font-semibold text-foreground">What you'll see</h3>
              <ul className="mt-3 space-y-2">
                {[
                  "Real-time forecast with connected data sources",
                  "Monte Carlo simulation with confidence bands",
                  "AI-generated risk narratives",
                  "Scenario comparison and decision scoring",
                ].map((item) => (
                  <li key={item} className="flex gap-2 text-sm text-muted-foreground">
                    <CheckCircle className="mt-0.5 h-4 w-4 shrink-0 text-primary/70" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>
    </MarketingLayout>
  );
}
