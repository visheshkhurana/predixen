import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { Badge } from "@/components/ui/badge";
import { useSEO } from "@/lib/seo";
import { Clock } from "lucide-react";

const posts = [
  {
    title: "Runway planning (without lying to yourself)",
    excerpt: "Why a single forecast is a trap, and how to build defensible runway scenarios using confidence intervals instead of gut feel.",
    category: "Financial Planning",
    readTime: "8 min",
    date: "Feb 2026",
  },
  {
    title: "Fundraising timing under uncertainty",
    excerpt: "How confidence intervals help you avoid raising too early or too late. A data-driven approach to the most consequential timing decision founders face.",
    category: "Fundraising",
    readTime: "6 min",
    date: "Feb 2026",
  },
  {
    title: "Hiring decisions with measurable downside",
    excerpt: "Hiring is the biggest leverage point. Compare timing decisions like April vs June with Monte Carlo simulations and see the real cost of getting it wrong.",
    category: "Financial Planning",
    readTime: "7 min",
    date: "Jan 2026",
  },
  {
    title: "Monte Carlo for founders (plain-English)",
    excerpt: "A simple explanation that turns Monte Carlo from intimidating to practical. No PhD required — just founders making better decisions.",
    category: "Product Updates",
    readTime: "5 min",
    date: "Jan 2026",
  },
  {
    title: "Investor reporting templates that build trust",
    excerpt: "Present risk, assumptions, and decisions in a way investors respect. How to turn uncertainty into a trust-building narrative.",
    category: "Fundraising",
    readTime: "6 min",
    date: "Dec 2025",
  },
  {
    title: "5 cap table mistakes that cost founders millions",
    excerpt: "From uncapped SAFEs to missing pro-rata rights — the most common equity mistakes early-stage founders make and how to avoid them.",
    category: "Founder Stories",
    readTime: "9 min",
    date: "Dec 2025",
  },
];

const categoryColors: Record<string, string> = {
  "Financial Planning": "bg-blue-500/10 text-blue-400 border-blue-500/20",
  Fundraising: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  "Product Updates": "bg-purple-500/10 text-purple-400 border-purple-500/20",
  "Founder Stories": "bg-amber-500/10 text-amber-400 border-amber-500/20",
};

export default function BlogPage() {
  useSEO({
    title: "Blog | FounderConsole",
    description:
      "FounderConsole blog: runway planning, fundraising timing, hiring decisions under uncertainty, Monte Carlo explainers, investor reporting templates.",
  });

  return (
    <MarketingLayout>
      <section>
        <div className="mx-auto max-w-6xl px-4 py-16 md:py-20">
          <h1 className="text-3xl font-bold tracking-tight text-foreground md:text-4xl" data-testid="text-blog-title">
            Insights for Founders
          </h1>
          <p className="mt-3 max-w-2xl text-lg text-muted-foreground">
            Practical decision science for founders. Runway, fundraising, hiring, and strategy — through the lens of probability.
          </p>
        </div>
      </section>

      <section className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-10">
          <div className="grid gap-6 md:grid-cols-2">
            {posts.map((post) => (
              <article
                key={post.title}
                className="group rounded-xl border bg-card p-6 transition-colors hover:border-primary/30"
                data-testid={`card-blog-${post.title.toLowerCase().replace(/\s+/g, "-").slice(0, 30)}`}
              >
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className={categoryColors[post.category] || ""}>
                    {post.category}
                  </Badge>
                  <Badge variant="outline" className="text-muted-foreground">
                    Coming Soon
                  </Badge>
                </div>
                <h2 className="mt-3 text-base font-semibold text-foreground">{post.title}</h2>
                <p className="mt-2 text-sm text-muted-foreground line-clamp-2">{post.excerpt}</p>
                <div className="mt-4 flex items-center gap-3 text-xs text-muted-foreground">
                  <span>{post.date}</span>
                  <span>·</span>
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {post.readTime}
                  </span>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>
    </MarketingLayout>
  );
}
