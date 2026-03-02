import { useState, useMemo } from "react";
import { Link } from "wouter";
import { cn } from "@/lib/utils";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Slider } from "@/components/ui/slider";

type Scenario = {
  id: string;
  label: string;
  description: string;
  baselineRisk: number;
  bestCaseRisk: number;
};

const scenarios: Scenario[] = [
  {
    id: "hire-april",
    label: "Hire in April",
    description: "Faster execution, higher burn earlier.",
    baselineRisk: 0.42,
    bestCaseRisk: 0.22,
  },
  {
    id: "hire-june",
    label: "Hire in June",
    description: "Delay headcount to reduce risk; speed slows slightly.",
    baselineRisk: 0.30,
    bestCaseRisk: 0.16,
  },
  {
    id: "raise-now",
    label: "Raise now",
    description: "Liquidity increases immediately; risk drops quickly.",
    baselineRisk: 0.18,
    bestCaseRisk: 0.10,
  },
];

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t;
}

function pct(n: number) {
  return `${Math.round(n * 100)}%`;
}

export function ScenarioCompare() {
  const [scenarioId, setScenarioId] = useState<Scenario["id"]>("hire-april");
  const [confidence, setConfidence] = useState<number>(0.6);

  const scenario = scenarios.find((s) => s.id === scenarioId)!;
  const risk = lerp(scenario.baselineRisk, scenario.bestCaseRisk, confidence);

  const confidenceLabel = useMemo(() => {
    if (confidence < 0.2) return "P10 (cautious worst-case)";
    if (confidence < 0.6) return "P50 (most likely)";
    return "P90 (optimistic best-case)";
  }, [confidence]);

  return (
    <section className="py-10 md:py-12">
      <div className="mx-auto max-w-6xl px-4">
        <div className="max-w-3xl">
          <h2 className="text-2xl font-semibold tracking-tight text-foreground" data-testid="text-scenario-heading">
            Scenario compare demo
          </h2>
          <p className="mt-2 text-muted-foreground">
            Drag the confidence to see how risk changes. This is a simplified demo — your real model will use live data and full simulations.
          </p>
        </div>

        <div className="mt-8 grid gap-6 md:grid-cols-[1fr,1.2fr]">
          <div className="space-y-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Pick a scenario</CardTitle>
                <p className="text-sm text-muted-foreground">
                  One click to compare decisions. Great for founders evaluating headcount + fundraising timing.
                </p>
              </CardHeader>
              <CardContent className="grid gap-3">
                {scenarios.map((s) => {
                  const active = s.id === scenario.id;
                  return (
                    <button
                      key={s.id}
                      className={cn(
                        "w-full rounded-xl border px-4 py-3 text-left transition",
                        active
                          ? "border-primary/40 bg-primary/10"
                          : "border-border bg-background hover:border-primary/20"
                      )}
                      onClick={() => setScenarioId(s.id)}
                      data-testid={`button-scenario-${s.id}`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-foreground">{s.label}</span>
                        <Badge variant={active ? "default" : "outline"} data-testid={`badge-scenario-${s.id}`}>
                          {active ? "Active" : "Compare"}
                        </Badge>
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground">{s.description}</p>
                    </button>
                  );
                })}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Confidence slider</CardTitle>
                <p className="text-sm text-muted-foreground" data-testid="text-confidence-label">{confidenceLabel}</p>
              </CardHeader>
              <CardContent className="pt-2">
                <Slider
                  defaultValue={[confidence * 100]}
                  min={0}
                  max={100}
                  step={1}
                  onValueChange={(vals) => setConfidence((vals[0] ?? 0) / 100)}
                  aria-label="Confidence level"
                  data-testid="slider-confidence"
                />
              </CardContent>
            </Card>
          </div>

          <div className="space-y-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Risk output</CardTitle>
                <p className="text-sm text-muted-foreground">
                  Estimated probability of running negative runway by month 12 (demo).
                </p>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4">
                  <div className="rounded-lg border bg-muted/50 p-4">
                    <p className="text-sm text-muted-foreground">Baseline</p>
                    <p className="mt-1 text-2xl font-semibold font-mono text-foreground" data-testid="text-risk-baseline">
                      {pct(scenario.baselineRisk)}
                    </p>
                  </div>
                  <div className="rounded-lg border border-primary/30 bg-primary/10 p-4">
                    <p className="text-sm text-muted-foreground">Current (demo)</p>
                    <p className="mt-1 text-2xl font-semibold font-mono text-foreground" data-testid="text-risk-current">
                      {pct(risk)}
                    </p>
                  </div>
                </div>

                <div className="mt-6 rounded-lg border bg-muted/50 p-4">
                  <p className="text-sm text-muted-foreground">
                    In the real product, this section becomes investor-ready explainability: "this scenario is risky
                    because burn accelerates before revenue, headcount timing increases volatility, and runway confidence drops."
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="border-primary/30 bg-primary/5">
              <CardContent className="pt-6">
                <h3 className="text-base font-semibold text-foreground" data-testid="text-try-real-data">Try it with real data</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  Connect Stripe/QuickBooks/Gusto to run real simulations and get an investor-ready summary.
                </p>
                <div className="mt-4 flex gap-3">
                  <Button asChild data-testid="button-scenario-get-started">
                    <Link href="/auth">Get Started Free</Link>
                  </Button>
                  <Button variant="outline" asChild data-testid="button-scenario-watch-demo">
                    <Link href="/demo">Watch Demo</Link>
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </section>
  );
}
