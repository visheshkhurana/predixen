import { Link } from "wouter";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { Button } from "@/components/ui/button";
import { useSEO } from "@/lib/seo";
import { Eye, BarChart3, Rocket, Lock, ArrowRight } from "lucide-react";

const values = [
  {
    icon: Eye,
    title: "Transparency",
    description: "Every recommendation comes with an explanation. No black boxes. You should always understand why.",
  },
  {
    icon: BarChart3,
    title: "Data-Driven",
    description: "Confidence intervals make risk measurable. Probability replaces intuition when the stakes are highest.",
  },
  {
    icon: Rocket,
    title: "Founder-First",
    description: "Built by founders who've lived the uncertainty. Every feature exists because we needed it ourselves.",
  },
  {
    icon: Lock,
    title: "Privacy-First",
    description: "Your financial data is encrypted at rest and in transit. Read-only integrations. No data resale. Ever.",
  },
];

const team = [
  { initials: "NK", name: "Nikita Kapoor", role: "CEO & Co-Founder" },
  { initials: "AR", name: "Arjun Rao", role: "CTO & Co-Founder" },
  { initials: "PS", name: "Priya Sharma", role: "Head of Product" },
  { initials: "DM", name: "Dev Mehta", role: "Lead Engineer" },
];

export default function AboutPage() {
  useSEO({
    title: "About | FounderConsole",
    description: "Why FounderConsole exists: founders need explainable financial clarity under uncertainty.",
  });

  return (
    <MarketingLayout>
      <section>
        <div className="mx-auto max-w-6xl px-4 py-16 md:py-20">
          <h1 className="text-3xl font-bold tracking-tight text-foreground md:text-4xl" data-testid="text-about-title">
            Built by Founders, for Founders
          </h1>
          <p className="mt-3 max-w-2xl text-lg text-muted-foreground">
            Founders are asked to be CFO + CEO at once. That's why we built this.
          </p>
        </div>
      </section>

      <section className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-16">
          <div className="max-w-3xl space-y-5 text-muted-foreground">
            <p>
              FounderConsole exists because uncertainty shouldn't force founders into gut decisions or fragile spreadsheets.
              Forecasting should be real-time. Risk should be measurable. Decisions should be explainable.
            </p>
            <p>
              Monte Carlo simulation + explainability is our north star. When you can show investors and board members the
              range of outcomes and the drivers behind them, you can defend decisions and move faster without adding hidden risk.
            </p>
            <p>
              We believe every founder deserves the same financial intelligence that well-funded companies get from expensive
              consultants and CFOs. That means investor-grade diligence, probabilistic simulations, and ranked decision
              recommendations — accessible to everyone, not just those who can afford a finance team.
            </p>
          </div>
        </div>
      </section>

      <section className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-16">
          <h2 className="text-2xl font-semibold tracking-tight text-foreground" data-testid="text-values-heading">
            Our values
          </h2>
          <div className="mt-8 grid gap-6 sm:grid-cols-2">
            {values.map((v) => (
              <div
                key={v.title}
                className="rounded-xl border bg-card/50 p-6"
                data-testid={`card-value-${v.title.toLowerCase()}`}
              >
                <v.icon className="h-5 w-5 text-primary" />
                <h3 className="mt-3 text-base font-semibold text-foreground">{v.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{v.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-16">
          <h2 className="text-2xl font-semibold tracking-tight text-foreground" data-testid="text-team-heading">
            Our team
          </h2>
          <div className="mt-8 grid grid-cols-2 gap-6 md:grid-cols-4">
            {team.map((member) => (
              <div key={member.name} className="flex flex-col items-center text-center" data-testid={`card-team-${member.initials.toLowerCase()}`}>
                <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
                  <span className="text-lg font-semibold text-muted-foreground">{member.initials}</span>
                </div>
                <h3 className="mt-3 text-sm font-semibold text-foreground">{member.name}</h3>
                <p className="text-sm text-muted-foreground">{member.role}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-16 md:py-20 text-center">
          <h2 className="text-2xl font-semibold text-foreground" data-testid="text-about-cta">
            Join us on our mission
          </h2>
          <p className="mx-auto mt-2 max-w-lg text-muted-foreground">
            We're building the financial intelligence layer for the next generation of startups.
          </p>
          <div className="mt-6 flex justify-center gap-3 flex-wrap">
            <Button size="lg" asChild data-testid="button-about-contact">
              <Link href="/contact">
                Join Us
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </section>
    </MarketingLayout>
  );
}
