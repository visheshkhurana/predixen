import { Link } from "wouter";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Eye, BarChart3, Heart, ShieldCheck } from "lucide-react";

const values = [
  {
    icon: Eye,
    title: "Transparency",
    description:
      "Every metric, every assumption, every projection is traceable back to its source. No black boxes, no hidden logic.",
  },
  {
    icon: BarChart3,
    title: "Data-Driven",
    description:
      "Decisions should be grounded in evidence, not gut feelings. We surface the signal in your financial noise.",
  },
  {
    icon: Heart,
    title: "Founder-First",
    description:
      "Built by operators who've lived the fundraising grind. Every feature is designed for the people actually running the company.",
  },
  {
    icon: ShieldCheck,
    title: "Privacy-First",
    description:
      "Your financial data is sacred. End-to-end encryption, SOC 2 practices, and zero data selling. Period.",
  },
];

const team = [
  { name: "Nikita Sharma", role: "Founder & CEO" },
  { name: "Arjun Mehta", role: "CTO" },
  { name: "Priya Kapoor", role: "Head of Product" },
  { name: "Ravi Anand", role: "Head of Data Science" },
];

export default function AboutPage() {
  return (
    <MarketingLayout>
      <section className="py-20 sm:py-28" data-testid="section-about-hero">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center">
          <h1
            className="text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl"
            data-testid="text-about-headline"
          >
            Built by Founders, for Founders
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground" data-testid="text-about-subheadline">
            We believe every startup deserves the same financial intelligence that billion-dollar companies take for
            granted.
          </p>
        </div>
      </section>

      <section className="pb-20" data-testid="section-mission">
        <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl font-semibold mb-6" data-testid="text-mission-title">
            Our Mission
          </h2>
          <div className="space-y-4 text-muted-foreground leading-relaxed">
            <p data-testid="text-mission-p1">
              The startup ecosystem has a fundamental information asymmetry problem. Investors have decades of pattern
              recognition, proprietary benchmarks, and armies of analysts. Founders have a spreadsheet and a dream.
              FounderConsole exists to close that gap.
            </p>
            <p data-testid="text-mission-p2">
              We&apos;re building the financial intelligence layer that every startup deserves — one that combines
              real-time data ingestion, Monte Carlo simulations, and AI-driven insights to give founders the clarity
              they need to make confident decisions about hiring, fundraising, and growth.
            </p>
            <p data-testid="text-mission-p3">
              Our platform doesn&apos;t just show you what happened. It shows you what&apos;s likely to happen next,
              across thousands of simulated futures, so you can plan for the best case while preparing for the worst.
            </p>
          </div>
        </div>
      </section>

      <section className="pb-20" data-testid="section-values">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl font-semibold mb-8 text-center" data-testid="text-values-title">
            Our Values
          </h2>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {values.map((v) => (
              <Card key={v.title} data-testid={`card-value-${v.title.toLowerCase().replace(/[^a-z]+/g, "-")}`}>
                <CardContent className="pt-6">
                  <v.icon className="h-8 w-8 text-primary mb-4" />
                  <h3 className="text-lg font-semibold mb-2">{v.title}</h3>
                  <p className="text-sm text-muted-foreground">{v.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <section className="pb-20" data-testid="section-team">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl font-semibold mb-8 text-center" data-testid="text-team-title">
            The Team
          </h2>
          <div className="grid grid-cols-2 gap-6 sm:grid-cols-4">
            {team.map((member) => (
              <div
                key={member.name}
                className="flex flex-col items-center text-center"
                data-testid={`card-team-${member.name.toLowerCase().replace(/\s+/g, "-")}`}
              >
                <div className="mb-3 flex h-20 w-20 items-center justify-center rounded-full bg-muted text-muted-foreground text-xl font-semibold">
                  {member.name
                    .split(" ")
                    .map((n) => n[0])
                    .join("")}
                </div>
                <h3 className="text-sm font-semibold">{member.name}</h3>
                <p className="text-xs text-muted-foreground">{member.role}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="pb-20" data-testid="section-about-cta">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-2xl font-semibold mb-4" data-testid="text-about-cta-title">
            Join Us on Our Mission
          </h2>
          <p className="mb-6 text-muted-foreground">
            Want to help democratize financial intelligence for startups?
          </p>
          <Button asChild data-testid="button-about-contact">
            <Link href="/contact">Get in Touch</Link>
          </Button>
        </div>
      </section>
    </MarketingLayout>
  );
}
