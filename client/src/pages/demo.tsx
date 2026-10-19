import { Link } from "wouter";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { Button } from "@/components/ui/button";
import { useSEO } from "@/lib/seo";
import { ArrowRight, CheckCircle, Sparkles } from "lucide-react";

/**
 * /demo — HAG-449.
 *
 * This page used to promise a video: "a fast walkthrough in under 5 minutes",
 * six chapter timestamps, and a play triangle on an empty 16:9 box. There was
 * no <video> and no <iframe> behind any of it, and the play icon was a
 * decorative SVG. The only working link went to /auth, which opens on "Welcome
 * back" — so the site's second CTA, the one for visitors who are interested but
 * not convinced, ended in a login form.
 *
 * The recording does not exist, and inventing a promise we cannot keep is the
 * bug. So the player and the timestamps are gone, and the page now does what
 * the product can actually do: one button into the sample workspace, in Demo
 * Mode, with no account.
 */
export default function DemoPage() {
  useSEO({
    title: "Demo | FounderConsole",
    description:
      "Open a live FounderConsole workspace preloaded with a sample company. Forecasts, Monte Carlo simulations and the AI copilot, with no account needed.",
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
            Open a real workspace loaded with a sample company. No account, no card, no call.
          </p>
        </div>
      </section>

      <section className="border-t">
        <div className="mx-auto max-w-4xl px-4 py-10">
          <div className="rounded-xl border bg-card overflow-hidden">
            <div className="px-6 py-14 text-center">
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-primary/20" role="img" aria-label="Live demo" data-testid="icon-play-demo">
                <Sparkles className="h-8 w-8 text-primary" />
              </div>
              <p className="mt-4 text-base font-semibold text-foreground">Take the live demo</p>
              <p className="mx-auto mt-1 max-w-md text-sm text-muted-foreground">
                Explore a founder workspace preloaded with sample company data — forecasts,
                simulations, and the AI copilot. It opens straight into the product.
              </p>
              <div className="mt-5">
                <Button asChild data-testid="button-demo-launch">
                  <Link href="/demo/enter">
                    Launch the live demo
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
              </div>
              <p className="mt-3 text-xs text-muted-foreground">No account needed. Nothing you do here is saved to your data.</p>
            </div>

            <div className="border-t p-6">
              <h2 className="text-base font-semibold text-foreground">What the demo covers</h2>
              <ul className="mt-4 grid gap-3 sm:grid-cols-2">
                {[
                  "The baseline forecast built from the sample company's numbers",
                  "Monte Carlo confidence intervals (P10/P50/P90) instead of one runway date",
                  "Explainability: what is actually driving the risk",
                  "Scenario comparison and decision scoring",
                  "The AI copilot answering a question about the model",
                  "An investor-ready summary",
                ].map((item) => (
                  <li key={item} className="flex gap-2 text-sm text-muted-foreground">
                    <CheckCircle className="mt-0.5 h-4 w-4 shrink-0 text-primary/70" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="mt-10 rounded-xl border bg-card p-6">
            <h3 className="text-base font-semibold text-foreground">Want your own numbers instead?</h3>
            <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
              The free calculators need no account and answer in under a minute. Or create an
              account to connect live data and get an ongoing forecast.
            </p>
            <div className="mt-4 flex flex-wrap gap-3">
              <Button asChild data-testid="button-demo-try">
                <Link href="/demo/enter">
                  Launch the live demo
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
              <Button variant="outline" asChild>
                <Link href="/signup">Create a free account</Link>
              </Button>
              <Button variant="ghost" asChild>
                <Link href="/tools/runway-calculator">Free runway calculator</Link>
              </Button>
            </div>
          </div>
        </div>
      </section>
    </MarketingLayout>
  );
}
