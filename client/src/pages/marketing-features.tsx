import { Link } from "wouter";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  BarChart3,
  Bot,
  ShieldCheck,
  PiggyBank,
  Cable,
  BrainCircuit,
  CheckCircle2,
  ArrowRight,
} from "lucide-react";

const features = [
  {
    icon: BarChart3,
    title: "Simulation Engine",
    description:
      "Run thousands of Monte Carlo simulations to stress-test your financial plan. See P10, P50, and P90 outcomes so you can plan for the best case, the base case, and the worst case.",
    bullets: [
      "Monte Carlo with P10/P50/P90 confidence bands",
      "Side-by-side scenario comparison",
      "Sensitivity analysis on every key driver",
      "Tornado charts to identify top-risk levers",
    ],
  },
  {
    icon: Bot,
    title: "AI Copilot",
    description:
      "Ask questions in plain English and get grounded, data-backed answers. The Copilot draws on your financials, market benchmarks, and real-time web research to advise you like a seasoned CFO.",
    bullets: [
      "Multi-LLM routing (GPT-4, Claude, Gemini)",
      "Web research powered by Perplexity",
      "Strategic recommendations with citations",
      "Conversation memory across sessions",
    ],
  },
  {
    icon: ShieldCheck,
    title: "Truth Scan",
    description:
      "Validate every data point before it enters your model. Truth Scan flags anomalies, missing fields, and inconsistencies so your simulations start from a foundation of clean data.",
    bullets: [
      "Automated data validation pipeline",
      "Z-score anomaly detection on every metric",
      "Confidence scoring for each data source",
      "Actionable fix suggestions for flagged items",
    ],
  },
  {
    icon: PiggyBank,
    title: "Fundraising OS",
    description:
      "Model your next round from term sheet to cap table. Simulate SAFE conversions, priced rounds, and dilution scenarios to walk into negotiations fully prepared.",
    bullets: [
      "Cap table management with full history",
      "SAFE and convertible note conversion modeling",
      "Dilution impact analysis for every scenario",
      "Investor pipeline tracking and outreach",
    ],
  },
  {
    icon: Cable,
    title: "Data Connectors",
    description:
      "Connect your accounting, banking, payroll, and product analytics tools in minutes. FounderConsole pulls live data so your dashboards and simulations are always current.",
    bullets: [
      "37 integrations including QuickBooks, Stripe, and Gusto",
      "Automatic daily sync with change detection",
      "Multi-currency normalization built in",
      "One-click OAuth for most platforms",
    ],
  },
  {
    icon: BrainCircuit,
    title: "Decision Engine",
    description:
      "Move from data to action. The Decision Engine synthesizes your financials, simulations, and market context into ranked strategic recommendations with clear risk assessments.",
    bullets: [
      "Strategic briefings tailored to your stage",
      "Ranked recommendations with confidence scores",
      "Risk assessment with second-order effects",
      "Decision journal to track outcomes over time",
    ],
  },
];

export default function MarketingFeaturesPage() {
  return (
    <MarketingLayout>
      <section className="py-20 px-4" data-testid="section-features-hero">
        <div className="max-w-4xl mx-auto text-center">
          <h1
            className="text-4xl md:text-5xl font-bold tracking-tight mb-6"
            data-testid="text-features-headline"
          >
            Every Tool Founders Need to Survive and Scale
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            From Monte Carlo simulations to AI-powered strategic advice,
            FounderConsole gives you the financial intelligence stack that
            used to require a full finance team.
          </p>
        </div>
      </section>

      <section
        className="pb-24 px-4"
        data-testid="section-feature-details"
      >
        <div className="max-w-5xl mx-auto space-y-20">
          {features.map((feature, index) => {
            const Icon = feature.icon;
            const isReversed = index % 2 === 1;
            return (
              <div
                key={feature.title}
                className={`flex flex-col gap-8 md:flex-row md:items-center ${
                  isReversed ? "md:flex-row-reverse" : ""
                }`}
                data-testid={`feature-block-${index}`}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-4 flex-wrap">
                    <div className="flex items-center justify-center w-10 h-10 rounded-md bg-primary/10">
                      <Icon className="w-5 h-5 text-foreground" />
                    </div>
                    <h2 className="text-2xl font-semibold">{feature.title}</h2>
                  </div>
                  <p className="text-muted-foreground mb-5 leading-relaxed">
                    {feature.description}
                  </p>
                  <ul className="space-y-2">
                    {feature.bullets.map((bullet) => (
                      <li
                        key={bullet}
                        className="flex items-start gap-2 text-sm"
                      >
                        <CheckCircle2 className="w-4 h-4 mt-0.5 text-chart-2 shrink-0" />
                        <span>{bullet}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <Card className="flex-1 min-w-0">
                  <CardContent className="p-8 flex items-center justify-center min-h-[200px]">
                    <div className="w-full h-full flex flex-col items-center justify-center gap-3 text-muted-foreground">
                      <Icon className="w-12 h-12 opacity-20" />
                      <span className="text-xs uppercase tracking-widest opacity-40">
                        {feature.title}
                      </span>
                    </div>
                  </CardContent>
                </Card>
              </div>
            );
          })}
        </div>
      </section>

      <section
        className="py-20 px-4 border-t"
        data-testid="section-features-cta"
      >
        <div className="max-w-3xl mx-auto text-center space-y-6">
          <h2 className="text-3xl font-bold">
            Start using FounderConsole today
          </h2>
          <p className="text-muted-foreground text-lg">
            It's free during beta. No credit card required.
          </p>
          <Link href="/auth">
            <Button data-testid="button-features-cta">
              Get Started Free
              <ArrowRight className="w-4 h-4" />
            </Button>
          </Link>
        </div>
      </section>
    </MarketingLayout>
  );
}
